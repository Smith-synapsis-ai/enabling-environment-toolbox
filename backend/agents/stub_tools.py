"""In-process (SDK) MCP server assembling the EE Toolbox agent tools.

Read-only posture: every tool here only reads committed repo data or returns
canned responses. No tool writes anywhere (full safety hooks are Task A8 --
do not add write-capable tools to this server).

Tool names as seen by agents (server registered as "ee"):
  - mcp__ee__ask_user_question   (Triage)         -- stub callback (real in A6)
  - mcp__ee__corpus_search       (Corpus Search)  -- REAL A4 hybrid retrieval
                                                     (see retrieval_tools.py, Step 0)
  - mcp__ee__get_tool_profile    (full wiki profile by id, A4 / Step 0)
  - mcp__ee__evidence_drilldown  (Evidence Drill-Down) -- stub, deep corpus is B1
"""

import logging
from typing import Any, Awaitable, Callable

from claude_agent_sdk import create_sdk_mcp_server, tool

from agents.retrieval_tools import corpus_search, get_tool_profile

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
# corpus_search / get_tool_profile -- REAL A4 hybrid retrieval (Step 0)
# Implemented in agents/retrieval_tools.py and registered below.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# evidence_drilldown -- stub
# ---------------------------------------------------------------------------

@tool(
    "evidence_drilldown",
    "Fetch deep evidence for a specific EE Toolbox tool from the source-"
    "document evidence corpus. NOTE: backend not yet wired (Task B1). For "
    "the full wiki profile of a tool, use get_tool_profile instead.",
    {"tool_id": str, "question": str},
)
async def evidence_drilldown(args: dict[str, Any]) -> dict[str, Any]:
    # STUB: the deep evidence corpus lands with Task B1. Summary-level data
    # is already available: corpus_search (hybrid retrieval) and
    # get_tool_profile (full wiki profile) are real.
    return {
        "content": [{
            "type": "text",
            "text": (
                "Deep evidence drill-down (source-document corpus) is not yet "
                "wired -- it arrives with Task B1. For the full wiki profile "
                "of this tool, call mcp__ee__get_tool_profile with its id; "
                "otherwise use the summary-level catalog information you "
                "already have and state that deeper evidence retrieval is "
                "pending."
            ),
        }]
    }


def build_ee_mcp_server():
    """Create the in-process MCP server registered as 'ee' on the session."""
    return create_sdk_mcp_server(
        name="ee",
        version="0.2.0",
        tools=[ask_user_question, corpus_search, get_tool_profile, evidence_drilldown],
    )


# Fully-qualified tool names for AgentDefinition tool lists.
# (corpus_search / get_tool_profile names are exported by retrieval_tools.py.)
TOOL_ASK_USER = "mcp__ee__ask_user_question"
TOOL_EVIDENCE_DRILLDOWN = "mcp__ee__evidence_drilldown"
