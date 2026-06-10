#!/usr/bin/env python3
"""Stdio MCP server exposing EE Toolbox hybrid retrieval (Task A4).

Tools:
  * search_tool_corpus -- hybrid (Qwen3 semantic + BM25) search over the 100
    wiki-page tool summaries; returns 5-15 ranked candidates as JSON.
  * get_tool_profile   -- full wiki profile for one tool id.

Run standalone:
    python3 -m pipeline.retrieval.mcp_server

Mounting (for the A2 Corpus Search subagent) -- stdio server config:
    {
      "mcpServers": {
        "ee-toolbox-retrieval": {
          "command": "python3",
          "args": ["-m", "pipeline.retrieval.mcp_server"],
          "cwd": "<repo root>"
        }
      }
    }

Startup is light: artifacts (~1.6 MB JSON + 400 KB NumPy) load at first tool
call; the Qwen3 embedding model lazy-loads on the first search (it is needed
to embed query text). First search therefore takes a few seconds extra.
"""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ee-toolbox-retrieval")


@mcp.tool()
def search_tool_corpus(
    challenge_text: str,
    top_k_min: int = 5,
    top_k_max: int = 15,
    pillar: Optional[str] = None,
    geography: Optional[str] = None,
) -> str:
    """Hybrid search over the 100 EE Toolbox wiki tool summaries.

    Combines Qwen3-Embedding-0.6B semantic similarity with BM25 keyword
    matching (weighted normalized fusion: 0.6 semantic + 0.4 BM25) and
    returns between top_k_min and top_k_max ranked candidates.

    Args:
        challenge_text: The enabling-environment challenge statement to
            match against the tool corpus (free text, 1-3 sentences works
            best).
        top_k_min: Minimum number of candidates to return (default 5).
        top_k_max: Maximum number of candidates to return (default 15).
        pillar: Optional EE pillar filter, case-insensitive substring
            (e.g. "Policy", "Market Systems", "Gender").
        geography: Optional country/region filter, case-insensitive
            substring over countries and regions (e.g. "Kenya", "Asia").

    Returns:
        JSON string: {"query": ..., "filters": ..., "count": N,
        "results": [{rank, id, title, pillars, thematic_areas, countries,
        regions, resource_type, scores{fused, semantic_cosine, semantic_norm,
        bm25_raw, bm25_norm}, summary_snippet}, ...]}
    """
    from pipeline.retrieval.hybrid_search import get_index

    filters = {}
    if pillar:
        filters["pillar"] = pillar
    if geography:
        filters["geography"] = geography

    results = get_index().search(
        challenge_text,
        top_k_min=top_k_min,
        top_k_max=top_k_max,
        filters=filters or None,
    )
    return json.dumps(
        {
            "query": challenge_text,
            "filters": filters or None,
            "count": len(results),
            "results": results,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def get_tool_profile(tool_id: str) -> str:
    """Return the full wiki-page profile for one tool by id.

    Args:
        tool_id: The tool id as returned by search_tool_corpus
            (CGSpace handle code, e.g. "10568-100094").

    Returns:
        JSON string of the full profile (overview, classification, audience,
        geography, how it works, requirements, outcomes, examples,
        limitations, key takeaways, citation), or {"error": ...} if the id
        is unknown.
    """
    from pipeline.retrieval.hybrid_search import get_index

    profile = get_index().get_profile(tool_id)
    if profile is None:
        return json.dumps({"error": f"Unknown tool_id: {tool_id}"})
    return json.dumps(profile, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
