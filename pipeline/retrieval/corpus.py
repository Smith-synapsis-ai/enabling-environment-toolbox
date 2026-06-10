"""Corpus loading and text construction for hybrid retrieval.

Loads the 100 wiki-page tool profiles from `data/batch-results-parsed.json`
and builds two text views per profile:

  * embed_text -- a structured natural-language summary fed to the embedding
    model (Qwen3-Embedding-0.6B, 32K context; these texts are ~300-700 tokens
    so no chunking is normally needed).
  * bm25_text  -- embed_text plus extra metadata terms (development stage,
    publishing organization, agro-ecological context) for keyword matching
    over summaries + metadata, per the task spec.

SOURCE-OF-TRUTH NOTE (92 vs 100): `data/batch-results-parsed.json` contains
the 100 wiki profiles and is the authoritative catalog per Jose's directive.
`data/seed.sql` only carries 92 tools (a stale subset) and must not be used
or modified by this package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Repo root = two levels up from this file (pipeline/retrieval/corpus.py).
REPO_ROOT = Path(__file__).resolve().parents[2]

# The 100-profile wiki catalog -- source of truth (NOT seed.sql).
DEFAULT_DATA_PATH = REPO_ROOT / "data" / "batch-results-parsed.json"

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Minimal stopword list -- enough to keep BM25 from rewarding glue words,
# small enough to stay deterministic and dependency-free.
STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in is it its of on or
    that the their this to was were what when where which who will with the
    not can may also more most other such than then there these those""".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenizer with stopword removal."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _join(values, sep: str = ", ") -> str:
    if not values:
        return ""
    return sep.join(str(v) for v in values if v)


def load_profiles(data_path: Path | None = None) -> list[dict]:
    """Load the 100 wiki profiles. Raises if the count is unexpected."""
    path = Path(data_path) if data_path else DEFAULT_DATA_PATH
    with open(path, encoding="utf-8") as f:
        profiles = json.load(f)
    if not isinstance(profiles, list) or len(profiles) == 0:
        raise ValueError(f"Unexpected catalog format in {path}")
    # Guard: the authoritative catalog has exactly 100 profiles. A mismatch
    # means someone swapped in a different file (e.g., the stale 92-tool set).
    if len(profiles) != 100:
        print(
            f"WARNING: expected 100 profiles in {path}, found {len(profiles)}. "
            "data/batch-results-parsed.json is the source of truth (seed.sql's "
            "92 tools are a stale subset)."
        )
    return profiles


def profile_id(profile: dict) -> str:
    """Stable unique id: the CGSpace handle code, e.g. '10568-100094'."""
    return str(profile.get("_result_code", "")).strip()


def profile_title(profile: dict) -> str:
    return str(profile.get("_title_meta", "")).strip() or "(untitled)"


def build_embed_text(profile: dict) -> str:
    """Structured summary text used for both embedding and BM25 base."""
    cls = profile.get("classification") or {}
    who = profile.get("who_its_for") or {}
    where = profile.get("where_it_applies") or {}
    how = profile.get("how_it_works") or {}
    outcomes = profile.get("expected_outcomes") or {}
    rtype = (profile.get("resource_type") or {}).get("primary_type", "")

    parts = [
        f"Title: {profile_title(profile)}",
        f"Resource type: {rtype}" if rtype else "",
        f"EE pillars: {_join(cls.get('ee_pillars'))}",
        f"Thematic areas: {_join(cls.get('thematic_areas'))}",
        f"Overview: {profile.get('overview', '')}",
        (
            "Audience: "
            f"{who.get('primary_audience', '')}; "
            f"{who.get('expertise_level', '')}; "
            f"{who.get('organizational_context', '')}"
        ),
        (
            "Where it applies: "
            f"countries: {_join(where.get('countries'))}; "
            f"regions: {_join(where.get('regions'))}; "
            f"context: {where.get('agro_ecological_context', '')}; "
            f"scale: {where.get('scale_of_application', '')}"
        ),
        f"How it works: {how.get('approach_summary', '')}",
        f"Key steps: {_join(how.get('key_steps'), sep='. ')}",
        (
            "Expected outcomes: "
            f"{outcomes.get('direct_outputs', '')}; "
            f"{outcomes.get('intended_impact', '')}"
        ),
        f"Key takeaways: {_join(profile.get('key_takeaways'), sep='. ')}",
    ]
    return "\n".join(p for p in parts if p and not p.endswith(": "))


def build_bm25_text(profile: dict) -> str:
    """embed_text plus extra metadata fields for keyword matching."""
    cls = profile.get("classification") or {}
    where = profile.get("where_it_applies") or {}
    src = profile.get("source_and_citation") or {}
    extra = [
        f"Development stage: {cls.get('development_stage', '')}",
        f"Agro-ecological context: {where.get('agro_ecological_context', '')}",
        f"Publisher: {src.get('publishing_organization', '')}",
    ]
    return build_embed_text(profile) + "\n" + "\n".join(e for e in extra if not e.endswith(": "))


def build_record(profile: dict) -> dict:
    """Compact per-document record persisted in corpus.json."""
    cls = profile.get("classification") or {}
    where = profile.get("where_it_applies") or {}
    overview = str(profile.get("overview", ""))
    return {
        "id": profile_id(profile),
        "title": profile_title(profile),
        "resource_type": (profile.get("resource_type") or {}).get("primary_type", ""),
        "pillars": cls.get("ee_pillars") or [],
        "thematic_areas": cls.get("thematic_areas") or [],
        "countries": where.get("countries") or [],
        "regions": where.get("regions") or [],
        "summary_snippet": overview[:300] + ("..." if len(overview) > 300 else ""),
        "bm25_text": build_bm25_text(profile),
    }
