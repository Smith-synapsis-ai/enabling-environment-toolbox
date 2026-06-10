"""In-memory hybrid search over the EE Toolbox wiki-summary index (Task A4).

Channels:
  * Semantic -- cosine similarity between the Qwen3-Embedding-0.6B query
    vector (encoded with prompt_name="query", per Qwen3 usage) and the
    pre-computed, L2-normalized document matrix (100 x 1024 float32 ~400 KB,
    brute-force exact -- no pgvector, no vector DB).
  * BM25     -- rank_bm25.BM25Okapi over summary + metadata text
    (title, pillars, thematic areas, geography, development stage, publisher).
    The BM25 index is rebuilt from corpus.json at load time (deterministic,
    <10 ms at this corpus size), avoiding pickle artifacts.

Fusion: WEIGHTED NORMALIZED SCORES.
    Each channel's scores are min-max normalized across the full corpus for
    the query, then fused = 0.6 * semantic + 0.4 * bm25.
    Rationale: with a 100-doc corpus we always score every document, so
    min-max normalization is stable and preserves score magnitude (unlike
    RRF, which only sees ranks). Semantic gets the higher weight because
    challenge statements are paraphrases, not keyword queries; BM25 protects
    exact-term matches (crop names, countries, instruments).

Result count: top_k_max (default 15) candidates are taken, then the tail is
trimmed where fused score falls below RELATIVE_CUTOFF x the best fused score,
never going below top_k_min (default 5). This yields 5-15 candidates as
required by the task spec.

Source of truth note: the index is built from data/batch-results-parsed.json
(100 profiles), NOT seed.sql (92, stale). See build_index.py.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from pipeline.retrieval.corpus import ARTIFACTS_DIR, tokenize

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

SEMANTIC_WEIGHT = 0.6
BM25_WEIGHT = 0.4
RELATIVE_CUTOFF = 0.5  # drop tail results with fused < 0.5 * best fused

DEFAULT_TOP_K_MIN = 5
DEFAULT_TOP_K_MAX = 15


def _minmax(scores: np.ndarray) -> np.ndarray:
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-12:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


class HybridIndex:
    """Loads artifacts into memory and serves hybrid queries.

    The embedding model is lazy-loaded on the first query (it is only needed
    to embed query text), keeping import/startup light for the MCP server.
    """

    def __init__(
        self,
        artifacts_dir: Path | None = None,
        *,
        corpus_path: str | Path | None = None,
        embeddings_path: str | Path | None = None,
        profiles_path: str | Path | None = None,
        manifest_path: str | Path | None = None,
    ):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
        self._model = None
        self._model_lock = threading.Lock()

        # Per-file overrides (B1: S3 cold-load cache may hold artifacts at
        # individual paths rather than one directory); default to artifacts_dir.
        _manifest = Path(manifest_path) if manifest_path else self.artifacts_dir / "manifest.json"
        _embeddings = Path(embeddings_path) if embeddings_path else self.artifacts_dir / "embeddings.npy"
        _corpus = Path(corpus_path) if corpus_path else self.artifacts_dir / "corpus.json"
        _profiles = Path(profiles_path) if profiles_path else self.artifacts_dir / "profiles.json"

        with open(_manifest, encoding="utf-8") as f:
            self.manifest = json.load(f)
        self.embeddings = np.load(_embeddings)
        with open(_corpus, encoding="utf-8") as f:
            self.records: list[dict] = json.load(f)
        with open(_profiles, encoding="utf-8") as f:
            self.profiles: dict[str, dict] = json.load(f)

        if self.embeddings.shape[0] != len(self.records):
            raise RuntimeError(
                f"Artifact mismatch: {self.embeddings.shape[0]} embeddings vs "
                f"{len(self.records)} corpus records -- rebuild the index "
                "(python3 -m pipeline.retrieval.build_index)"
            )

        # Deterministic BM25 rebuild from persisted bm25_text.
        self._bm25 = BM25Okapi([tokenize(r["bm25_text"]) for r in self.records])
        self._id_to_idx = {r["id"]: i for i, r in enumerate(self.records)}

    # -- model handling -----------------------------------------------------

    def _get_model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    import os

                    os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.9")
                    os.environ.setdefault("PYTORCH_MPS_LOW_WATERMARK_RATIO", "0.7")
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(
                        MODEL_NAME, model_kwargs={"torch_dtype": "auto"}
                    )
        return self._model

    def embed_query(self, text: str) -> np.ndarray:
        model = self._get_model()
        # Qwen3-Embedding: documents take no prefix; queries use the built-in
        # "query" prompt (same convention as the proven reference pipeline).
        vec = model.encode(
            text, prompt_name="query", normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vec, dtype=np.float32)

    # -- filters ------------------------------------------------------------

    def _filter_mask(self, filters: dict | None) -> np.ndarray:
        """Boolean mask of records matching optional metadata filters.

        Supported keys (case-insensitive substring match):
          pillar    -- against the ee_pillars list
          geography -- against countries + regions lists
        """
        mask = np.ones(len(self.records), dtype=bool)
        if not filters:
            return mask
        pillar = (filters.get("pillar") or "").strip().lower()
        geography = (filters.get("geography") or "").strip().lower()
        for i, r in enumerate(self.records):
            if pillar and not any(pillar in p.lower() for p in r["pillars"]):
                mask[i] = False
                continue
            if geography:
                geo_fields = [*r["countries"], *r["regions"]]
                if not any(geography in g.lower() for g in geo_fields):
                    mask[i] = False
        return mask

    # -- search -------------------------------------------------------------

    def search(
        self,
        challenge_text: str,
        top_k_min: int = DEFAULT_TOP_K_MIN,
        top_k_max: int = DEFAULT_TOP_K_MAX,
        filters: dict | None = None,
    ) -> list[dict]:
        """Hybrid search; returns 5-15 ranked candidate dicts."""
        if not challenge_text or not challenge_text.strip():
            raise ValueError("challenge_text must be a non-empty string")
        top_k_min = max(1, int(top_k_min))
        top_k_max = max(top_k_min, int(top_k_max))

        qvec = self.embed_query(challenge_text)
        sem_raw = self.embeddings @ qvec  # cosine (rows and query normalized)
        bm25_raw = np.asarray(
            self._bm25.get_scores(tokenize(challenge_text)), dtype=np.float32
        )

        sem_n = _minmax(sem_raw)
        bm25_n = _minmax(bm25_raw)
        fused = SEMANTIC_WEIGHT * sem_n + BM25_WEIGHT * bm25_n

        mask = self._filter_mask(filters)
        candidate_idx = np.where(mask)[0]
        if candidate_idx.size == 0:
            return []

        order = candidate_idx[np.argsort(-fused[candidate_idx])][:top_k_max]

        # Trim the weak tail, but keep at least top_k_min results.
        best = float(fused[order[0]]) if order.size else 0.0
        kept = [
            int(i)
            for rank, i in enumerate(order)
            if rank < top_k_min or fused[i] >= RELATIVE_CUTOFF * best
        ]

        results = []
        for rank, i in enumerate(kept, start=1):
            r = self.records[i]
            results.append(
                {
                    "rank": rank,
                    "id": r["id"],
                    "title": r["title"],
                    "pillars": r["pillars"],
                    "thematic_areas": r["thematic_areas"],
                    "countries": r["countries"],
                    "regions": r["regions"],
                    "resource_type": r["resource_type"],
                    "scores": {
                        "fused": round(float(fused[i]), 4),
                        "semantic_cosine": round(float(sem_raw[i]), 4),
                        "semantic_norm": round(float(sem_n[i]), 4),
                        "bm25_raw": round(float(bm25_raw[i]), 4),
                        "bm25_norm": round(float(bm25_n[i]), 4),
                    },
                    "summary_snippet": r["summary_snippet"],
                }
            )
        return results

    def get_profile(self, tool_id: str) -> dict | None:
        """Full wiki profile for one tool id (e.g. '10568-100094')."""
        return self.profiles.get(str(tool_id).strip())


_default_index: HybridIndex | None = None
_default_index_lock = threading.Lock()


def get_index(
    *,
    corpus_path: str | Path | None = None,
    embeddings_path: str | Path | None = None,
    profiles_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> HybridIndex:
    """Process-wide singleton index (artifacts loaded once).

    When any path override is given (B1 S3 cold-load repointing the index at
    cached artifacts), the singleton is (re)built from those paths; otherwise
    the existing singleton (default repo artifacts) is returned unchanged.
    """
    global _default_index
    overrides = any((corpus_path, embeddings_path, profiles_path, manifest_path))
    if _default_index is None or overrides:
        with _default_index_lock:
            if _default_index is None or overrides:
                _default_index = HybridIndex(
                    corpus_path=corpus_path,
                    embeddings_path=embeddings_path,
                    profiles_path=profiles_path,
                    manifest_path=manifest_path,
                )
    return _default_index


def search(
    challenge_text: str,
    top_k_min: int = DEFAULT_TOP_K_MIN,
    top_k_max: int = DEFAULT_TOP_K_MAX,
    filters: dict | None = None,
) -> list[dict]:
    """Module-level convenience wrapper around the singleton index."""
    return get_index().search(challenge_text, top_k_min, top_k_max, filters)
