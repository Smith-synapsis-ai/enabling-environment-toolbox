"""Real corpus retrieval tools for the EE Toolbox agent team (Step 0).

Replaces the keyword stub from Task A2 with the A4 hybrid retrieval engine
(Qwen3-Embedding-0.6B semantic + BM25 keyword, weighted normalized fusion
0.6/0.4) over the 100 wiki-page tool summaries. The engine is wrapped
IN-PROCESS via its Python API (``pipeline.retrieval.hybrid_search``) instead
of mounting the stdio MCP server, so the existing ``mcp__ee__*`` tool names
stay stable and no subprocess lifecycle is needed. The stdio server
(``python3 -m pipeline.retrieval.mcp_server``) remains available for other
consumers and is not touched here.

Tools defined here (registered on the in-process "ee" server by
``stub_tools.build_ee_mcp_server``):
  - mcp__ee__corpus_search     -- hybrid search, 5-15 ranked candidates
  - mcp__ee__get_tool_profile  -- full wiki profile for one tool id

Read-only posture: both tools only read committed index artifacts under
``pipeline/retrieval/artifacts/``; nothing is written anywhere.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import path: the backend runs with backend/ on sys.path (see
# test_roundtrip.py / backend scripts), but the A4 engine lives in pipeline/
# at the REPO ROOT, which is not necessarily importable from that process.
# Add the repo root (backend/agents/retrieval_tools.py -> parents[2]) so
# ``import pipeline.retrieval...`` works regardless of how the backend was
# launched. Same derivation as orchestrator.REPO_ROOT.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# sentence-transformers issues HF Hub HEAD requests at model load even when
# the model is fully cached (~/.cache/huggingface). Force cache-only operation
# so retrieval works offline and never blocks on the network; setdefault so an
# operator can still override from the environment.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

RETRIEVAL_MODE = "hybrid (semantic Qwen3 + BM25, weighted fusion)"
CATALOG_SIZE = 100


def _run_search(
    query: str,
    pillar: str | None,
    geography: str | None,
    top_k_max: int,
) -> dict[str, Any]:
    """Synchronous search against the A4 engine; returns the result payload.

    Result records are passed through VERBATIM from
    ``pipeline.retrieval.hybrid_search.search`` (rank, id, title, pillars,
    thematic_areas, countries, regions, resource_type,
    scores{fused, semantic_cosine, semantic_norm, bm25_raw, bm25_norm},
    summary_snippet).
    """
    # Imported lazily so module import stays light; the embedding model itself
    # lazy-loads inside the engine on the first search (~8 s warm from cache).
    from pipeline.retrieval.hybrid_search import search

    filters: dict[str, str] = {}
    if pillar:
        filters["pillar"] = pillar
    if geography:
        filters["geography"] = geography

    results = search(
        query,
        top_k_min=5,
        top_k_max=top_k_max,
        filters=filters or None,
    )
    return {
        "query": query,
        "retrieval_mode": RETRIEVAL_MODE,
        "catalog_size": CATALOG_SIZE,
        "filters": filters or None,
        "count": len(results),
        "results": results,
    }


# Full JSON Schema (not the simple {name: type} dict) so that only "query"
# is required -- the simple dict form marks every parameter required.
_CORPUS_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "The challenge statement or search phrasing to match against "
                "the tool corpus (free text; 1-3 sentences works best)."
            ),
        },
        "pillar": {
            "type": "string",
            "description": (
                "Optional EE pillar filter, case-insensitive substring "
                "(e.g. 'Policy', 'Market Systems', 'Gender')."
            ),
        },
        "geography": {
            "type": "string",
            "description": (
                "Optional country/region filter, case-insensitive substring "
                "over countries and regions (e.g. 'Kenya', 'Asia')."
            ),
        },
        "top_k_max": {
            "type": "integer",
            "description": "Maximum number of candidates to return (default 15).",
        },
    },
    "required": ["query"],
}


@tool(
    "corpus_search",
    "Hybrid search over the EE Toolbox catalog (100 curated "
    "enabling-environment tool profiles): Qwen3 semantic embeddings + BM25 "
    "keyword matching, weighted-fusion ranked. Returns 5-15 candidates with "
    "per-channel and fused relevance scores, pillars, thematic areas, "
    "geography, resource type and a summary snippet. Optional pillar and "
    "geography filters.",
    _CORPUS_SEARCH_SCHEMA,
)
async def corpus_search(args: dict[str, Any]) -> dict[str, Any]:
    # Accept "challenge_text" as an alias for "query" (the A4 stdio server's
    # parameter name), so either phrasing from the agent works.
    query = str(args.get("query") or args.get("challenge_text") or "").strip()
    if not query:
        return {
            "content": [{
                "type": "text",
                "text": "Error: 'query' must be a non-empty string.",
            }],
            "is_error": True,
        }
    pillar = (str(args.get("pillar") or "").strip()) or None
    geography = (str(args.get("geography") or "").strip()) or None
    try:
        top_k_max = int(args.get("top_k_max") or 15)
    except (TypeError, ValueError):
        top_k_max = 15
    top_k_max = max(5, min(top_k_max, 15))

    try:
        # Off the event loop: the first call loads the embedding model (~8 s)
        # and every call does CPU-bound encoding.
        payload = await asyncio.to_thread(
            _run_search, query, pillar, geography, top_k_max
        )
    except Exception as exc:  # surface engine errors to the agent, readably
        logger.exception("corpus_search failed for query %r", query)
        return {
            "content": [{"type": "text", "text": f"corpus_search error: {exc}"}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=1)}]}


@tool(
    "get_tool_profile",
    "Fetch the FULL wiki-page profile for one EE Toolbox tool by id (as "
    "returned by corpus_search, e.g. '10568-100094'): overview, "
    "classification, who it's for, where it applies, how it works, what "
    "you'll need, expected outcomes, practical examples, limitations, key "
    "takeaways, source and citation.",
    {"tool_id": str},
)
async def get_tool_profile(args: dict[str, Any]) -> dict[str, Any]:
    tool_id = str(args.get("tool_id") or "").strip()
    if not tool_id:
        return {
            "content": [{
                "type": "text",
                "text": "Error: 'tool_id' must be a non-empty string.",
            }],
            "is_error": True,
        }
    try:
        from pipeline.retrieval.hybrid_search import get_index

        profile = await asyncio.to_thread(get_index().get_profile, tool_id)
    except Exception as exc:
        logger.exception("get_tool_profile failed for id %r", tool_id)
        return {
            "content": [{"type": "text", "text": f"get_tool_profile error: {exc}"}],
            "is_error": True,
        }
    if profile is None:
        # Same error-dict shape as the A4 stdio server.
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({"error": f"Unknown tool_id: {tool_id}"}),
            }],
            "is_error": True,
        }
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(profile, ensure_ascii=False, indent=1),
        }]
    }


# Fully-qualified tool names for AgentDefinition tool lists.
TOOL_CORPUS_SEARCH = "mcp__ee__corpus_search"
TOOL_GET_PROFILE = "mcp__ee__get_tool_profile"
