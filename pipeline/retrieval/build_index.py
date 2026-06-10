#!/usr/bin/env python3
"""Build the hybrid retrieval index for the EE Toolbox (Task A4).

Ported from the proven reference implementation at
~/workspace/knowledge-infrastructure/scripts/build_embeddings.py (same model,
same MPS memory settings, same chunk-and-pool strategy for over-length texts).
Simplified here because the corpus is exactly the 100 wiki-page tool
summaries (~300-700 tokens each), not arbitrary documents.

Source of truth: data/batch-results-parsed.json (100 profiles). seed.sql's
92 tools are a stale subset and are deliberately ignored (Jose's directive;
see pipeline/retrieval/__init__.py and the A4 contract doc).

Artifacts written to pipeline/retrieval/artifacts/ (total well under 5 MB,
so they are committed to git):
    embeddings.npy  -- float32 (100, 1024), L2-normalized rows
    corpus.json     -- per-doc records: id, title, pillars, thematic areas,
                       countries, regions, summary snippet, bm25_text
    profiles.json   -- full wiki profiles keyed by id (for get_tool_profile)
    manifest.json   -- model name, dim, count, source path, build timestamp

Deterministic and re-runnable: same input file -> same artifacts (embedding
inference is deterministic for a fixed model version and device class).

Rebuild command (from repo root):
    python3 -m pipeline.retrieval.build_index
"""

# MPS memory watermarks must be set BEFORE importing torch (per reference).
import os

os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.9")
os.environ.setdefault("PYTORCH_MPS_LOW_WATERMARK_RATIO", "0.7")

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pipeline.retrieval.corpus import (
    ARTIFACTS_DIR,
    DEFAULT_DATA_PATH,
    build_embed_text,
    build_record,
    load_profiles,
    profile_id,
)

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
EMBED_DIM = 1024

# Chunk-and-pool parameters from the reference script. Wiki summaries are
# far shorter than 2048 tokens, so chunking is a defensive fallback only.
CHUNK_TOKENS = 2048
OVERLAP_TOKENS = 256


def encode_with_chunking(text: str, model) -> np.ndarray:
    """Encode one text; chunk-and-pool if it exceeds CHUNK_TOKENS.

    Direct port of the reference implementation: overlapping token-level
    chunks, mean-pooled and L2-normalized. Short texts encode directly.
    """
    tokenizer = model.tokenizer
    stride = CHUNK_TOKENS - OVERLAP_TOKENS
    token_ids = tokenizer.encode(text, add_special_tokens=False)

    if len(token_ids) <= CHUNK_TOKENS:
        vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vec, dtype=np.float32)

    chunk_vectors = []
    for start in range(0, len(token_ids), stride):
        end = min(start + CHUNK_TOKENS, len(token_ids))
        chunk_text = tokenizer.decode(token_ids[start:end], skip_special_tokens=True)
        vec = model.encode(chunk_text, normalize_embeddings=False, show_progress_bar=False)
        chunk_vectors.append(np.asarray(vec, dtype=np.float32))
        if end >= len(token_ids):
            break

    mean_vec = np.mean(np.stack(chunk_vectors, axis=0), axis=0)
    norm = np.linalg.norm(mean_vec)
    if norm > 1e-12:
        mean_vec = mean_vec / norm
    return mean_vec.astype(np.float32)


def load_model():
    """Load Qwen3-Embedding-0.6B via sentence-transformers (MPS if available)."""
    import torch
    from sentence_transformers import SentenceTransformer

    if hasattr(torch, "mps") and torch.backends.mps.is_available():
        torch.mps.empty_cache()

    model = SentenceTransformer(MODEL_NAME, model_kwargs={"torch_dtype": "auto"})
    dim = model.get_sentence_embedding_dimension()
    if dim != EMBED_DIM:
        raise RuntimeError(f"Expected {EMBED_DIM}-dim embeddings, got {dim}")
    return model


def main():
    parser = argparse.ArgumentParser(description="Build EE Toolbox hybrid retrieval index")
    parser.add_argument(
        "--data-path",
        default=str(DEFAULT_DATA_PATH),
        help="Path to batch-results-parsed.json (default: data/batch-results-parsed.json)",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=str(ARTIFACTS_DIR),
        help="Output directory for index artifacts",
    )
    args = parser.parse_args()

    data_path = Path(args.data_path)
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading profiles from {data_path}")
    profiles = load_profiles(data_path)
    print(f"  {len(profiles)} profiles loaded (source of truth; seed.sql ignored)")

    ids = [profile_id(p) for p in profiles]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate profile ids in catalog")

    records = [build_record(p) for p in profiles]
    embed_texts = [build_embed_text(p) for p in profiles]

    print(f"Loading embedding model {MODEL_NAME} ...")
    t0 = time.time()
    model = load_model()
    print(f"  model loaded in {time.time() - t0:.1f}s")

    print("Encoding documents ...")
    t0 = time.time()
    vectors = np.zeros((len(profiles), EMBED_DIM), dtype=np.float32)
    for i, text in enumerate(embed_texts):
        vectors[i] = encode_with_chunking(text, model)
        if (i + 1) % 20 == 0 or (i + 1) == len(embed_texts):
            print(f"  {i + 1}/{len(embed_texts)} encoded ({time.time() - t0:.1f}s)")

    # Re-normalize in float32: the model runs in reduced precision (bf16 on
    # MPS), so returned norms drift slightly (~1e-3). Exact unit norms make
    # the dot product in hybrid_search a true cosine similarity.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if (norms < 1e-6).any():
        raise RuntimeError("Zero embedding vector encountered")
    vectors = vectors / norms

    emb_path = artifacts_dir / "embeddings.npy"
    np.save(emb_path, vectors)

    corpus_path = artifacts_dir / "corpus.json"
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    profiles_path = artifacts_dir / "profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({profile_id(p): p for p in profiles}, f, ensure_ascii=False, indent=1)

    manifest = {
        "model": MODEL_NAME,
        "embedding_dim": EMBED_DIM,
        "count": len(profiles),
        "source": str(data_path),
        "source_note": (
            "data/batch-results-parsed.json (100 wiki profiles) is the source "
            "of truth; data/seed.sql (92 tools) is a stale subset and ignored."
        ),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            "embeddings": emb_path.name,
            "corpus": corpus_path.name,
            "profiles": profiles_path.name,
        },
    }
    manifest_path = artifacts_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    for p in (emb_path, corpus_path, profiles_path, manifest_path):
        print(f"  wrote {p} ({p.stat().st_size / 1024:.1f} KB)")
    print("Done.")


if __name__ == "__main__":
    main()
