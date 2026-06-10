"""Hybrid retrieval v1 for the EE Toolbox (Task A4).

Semantic (Qwen/Qwen3-Embedding-0.6B, 1024-dim) + BM25 keyword search over the
100 wiki-page tool summaries, fused with weighted normalized scores, served
from an in-memory NumPy index and exposed as MCP tools.

Modules:
    corpus         -- load the 100 profiles and build embed/BM25 texts
    build_index    -- offline index builder (writes artifacts/)
    hybrid_search  -- in-memory hybrid search over the artifacts
    mcp_server     -- stdio MCP server (search_tool_corpus, get_tool_profile)

NOTE on data source (92-vs-100 reconciliation, directive from Jose):
    `data/batch-results-parsed.json` (100 wiki profiles) is the source of
    truth and wins over `data/seed.sql` (92 tools -- a stale subset).
    All 100 profiles are indexed. seed.sql is intentionally NOT modified
    here; DB reconciliation is a later task.

This package deliberately does NOT use the legacy `pipeline/embeddings.py` /
`pipeline/search.py` (OpenAI 1536-dim + pgvector), which were ruled
non-compliant in the project audit. No pgvector, no vector DB: at ~100 docs
x 1024 dims the dense matrix is ~400 KB and brute-force cosine is exact
and instant.
"""
