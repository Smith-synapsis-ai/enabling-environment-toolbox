"""In-process (SDK) MCP server exposing the EE Toolbox stub tools.

Read-only posture: every tool here only reads committed repo data or returns
canned responses. No tool writes anywhere (full safety hooks are Task A8 --
do not add write-capable tools to this server).

Tool names as seen by agents (server registered as "ee"):
  - mcp__ee__ask_user_question   (Triage)         -- stub callback
  - mcp__ee__corpus_search       (Corpus Search)  -- # STUB: replaced by A4 hybrid retrieval
  - mcp__ee__evidence_drilldown  (Evidence Drill-Down) -- stub, not yet wired (A4/B1)
"""

import json
import logging
from typing import Any, Awaitable, Callable

from claude_agent_sdk import create_sdk_mcp_server, tool

from agents.corpus_stub import search_corpus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ask_user_question -- stub callback
#
# The real implementation arrives with the WebSocket transport (Task A6),
# which will register a callback that round-trips the question to the user.
# Until then the default callback returns an "unavailable" notice so the
# Triage agent proceeds on stated assumptions.
# ---------------------------------------------------------------------------

AskUserCallback = Callable[[str, list[str] | None], Awaitable[str]]


async def _default_ask_user_callback(question: str, options: list[str] | None) -> str:
    # STUB callback: interactive user input is wired in Task A6 (WebSocket).
    logger.info("ask_user_question (stubbed): %s", question)
    return (
        "Interactive user input is not available in this session (transport "
        "arrives in Task A6). Do not wait for an answer: proceed with the "
        "information already given, stating your assumptions explicitly."
    )


_ask_user_callback: AskUserCallback = _default_ask_user_callback


def set_ask_user_callback(callback: AskUserCallback) -> None:
    """Register the real ask-user callback (used by the A6 transport layer)."""
    global _ask_user_callback
    _ask_user_callback = callback


@tool(
    "ask_user_question",
    "Ask the end user ONE clarifying question about their scaling challenge. "
    "Use only when essential information is missing. May report that "
    "interactive input is unavailable, in which case proceed on assumptions.",
    {"question": str, "options": list},
)
async def ask_user_question(args: dict[str, Any]) -> dict[str, Any]:
    question = str(args.get("question", "")).strip()
    options = args.get("options") or None
    answer = await _ask_user_callback(question, options)
    return {"content": [{"type": "text", "text": answer}]}


# ---------------------------------------------------------------------------
# corpus_search -- # STUB: replaced by A4 hybrid retrieval
# ---------------------------------------------------------------------------

@tool(
    "corpus_search",
    "Search the EE Toolbox catalog (92 curated enabling-environment tools) "
    "by keywords. Returns the top matching tools with title, summary, "
    "pillars, domains, type, stage, geography and source URL.",
    {"query": str, "top_k": int},
)
async def corpus_search(args: dict[str, Any]) -> dict[str, Any]:
    # STUB: replaced by A4 hybrid retrieval (pgvector + lexical).
    query = str(args.get("query", "")).strip()
    top_k = int(args.get("top_k") or 8)
    top_k = max(1, min(top_k, 20))
    results = search_corpus(query, top_k=top_k)
    payload = {
        "query": query,
        "retrieval_mode": "keyword-stub (A4 hybrid retrieval pending)",
        "result_count": len(results),
        "results": results,
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=1)}]}


# ---------------------------------------------------------------------------
# evidence_drilldown -- stub
# ---------------------------------------------------------------------------

@tool(
    "evidence_drilldown",
    "Fetch deep evidence for a specific EE Toolbox tool (full profile, "
    "source-document context). NOTE: backend not yet wired.",
    {"tool_id": str, "question": str},
)
async def evidence_drilldown(args: dict[str, Any]) -> dict[str, Any]:
    # STUB: deep retrieval lands with A4 (hybrid retrieval) and B1.
    return {
        "content": [{
            "type": "text",
            "text": (
                "drill-down not yet wired (A4/B1). Use the summary-level "
                "catalog information you already have and state that deeper "
                "evidence retrieval is pending."
            ),
        }]
    }


def build_ee_mcp_server():
    """Create the in-process MCP server registered as 'ee' on the session."""
    return create_sdk_mcp_server(
        name="ee",
        version="0.1.0",
        tools=[ask_user_question, corpus_search, evidence_drilldown],
    )


# Fully-qualified tool names for AgentDefinition tool lists.
TOOL_ASK_USER = "mcp__ee__ask_user_question"
TOOL_CORPUS_SEARCH = "mcp__ee__corpus_search"
TOOL_EVIDENCE_DRILLDOWN = "mcp__ee__evidence_drilldown"
