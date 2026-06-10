"""In-process (SDK) MCP server assembling the EE Toolbox agent tools.

Read-only posture: no tool here creates, modifies, or deletes catalog data,
user data, or repo files. The ONLY writes are the report_* tools persisting
the assistant's OWN report-draft state to backend/data/report_drafts/ (Task
A5 iterative report flow) -- that is the assistant's working memory, not a
data mutation. Full safety hooks are Task A8.

Tool names as seen by agents (server registered as "ee"):
  - mcp__ee__ask_user_question   (Triage)         -- stub callback (real in A6)
  - mcp__ee__corpus_search       (Corpus Search)  -- REAL A4 hybrid retrieval
                                                     (see retrieval_tools.py, Step 0)
  - mcp__ee__get_tool_profile    (full wiki profile by id, A4 / Step 0)
  - mcp__ee__evidence_drilldown  (Evidence Drill-Down) -- stub, deep corpus is B1
  - mcp__ee__report_get          (orchestrator) -- current report draft (A5)
  - mcp__ee__report_update       (orchestrator) -- patch the report draft (A5)
  - mcp__ee__report_render       (orchestrator) -- render draft to markdown (A5)
"""

import json
import logging
from typing import Any, Awaitable, Callable

from claude_agent_sdk import create_sdk_mcp_server, tool

from agents.report_state import ReportDraft, get_report_store
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


# ---------------------------------------------------------------------------
# report_get / report_update / report_render -- iterative report flow (A5)
#
# Session binding: the orchestrator process handles ONE session per
# run_challenge call (documented assumption -- run_challenge sets the current
# session below at session start). Each tool also accepts an explicit
# session_id argument as an override, which the orchestrator prompt instructs
# the model to pass; the module-level default is the safety net.
# ---------------------------------------------------------------------------

_current_report_session: str | None = None
_current_report_turn: int = 1


def set_current_report_session(session_id: str, turn: int = 1) -> None:
    """Bind report tools to a session (called by run_challenge at turn start)."""
    global _current_report_session, _current_report_turn
    _current_report_session = session_id
    _current_report_turn = turn


def _resolve_session_id(args: dict[str, Any]) -> str | None:
    explicit = str(args.get("session_id") or "").strip()
    return explicit or _current_report_session


def _text_result(payload: str, is_error: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"content": [{"type": "text", "text": payload}]}
    if is_error:
        out["is_error"] = True
    return out


async def _load_draft(session_id: str) -> ReportDraft | None:
    raw = await get_report_store().load_draft(session_id)
    return ReportDraft.from_json(raw) if raw is not None else None


@tool(
    "report_get",
    "Get the current report draft for this session as JSON (the report-in-"
    "progress: title, challenge summary, sections, candidate tools, revision, "
    "changelog). Returns {\"exists\": false} if no draft exists yet. "
    "Orchestrator-only.",
    {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session id override; omit to use the current session.",
            },
        },
        "required": [],
    },
)
async def report_get(args: dict[str, Any]) -> dict[str, Any]:
    sid = _resolve_session_id(args)
    if not sid:
        return _text_result("No session bound for report tools.", is_error=True)
    draft = await _load_draft(sid)
    if draft is None:
        return _text_result(json.dumps({"exists": False, "session_id": sid}))
    return _text_result(draft.to_json())


_REPORT_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session id override; omit to use the current session.",
        },
        "title": {"type": "string", "description": "Set/replace the report title."},
        "challenge_summary": {
            "type": "string",
            "description": "Set/replace the one-paragraph challenge summary.",
        },
        "upsert_sections": {
            "type": "array",
            "description": (
                "Sections to add or update by id. Each item: {id, heading, "
                "body_md, sources?: [links]}. Existing sections with the same "
                "id are updated in place; others are appended."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "heading": {"type": "string"},
                    "body_md": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id"],
            },
        },
        "remove_section_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Section ids to remove.",
        },
        "upsert_candidate_tools": {
            "type": "array",
            "description": (
                "Candidate-tool entries to add or update by id. Each item: "
                "{id, title?, status?: candidate|accepted|rejected}."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["candidate", "accepted", "rejected"],
                    },
                },
                "required": ["id"],
            },
        },
        "remove_tool_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Candidate-tool ids to remove from the draft.",
        },
        "changelog_summary": {
            "type": "string",
            "description": (
                "REQUIRED: one-line summary of what this update changed "
                "(recorded in the draft changelog)."
            ),
        },
    },
    "required": ["changelog_summary"],
}


@tool(
    "report_update",
    "Apply a structured patch to the session's report draft (creates the "
    "draft on first use). Set title/challenge_summary, upsert or remove "
    "sections by id, upsert/remove candidate tools, and always pass a one-"
    "line changelog_summary. Increments the draft revision and persists it. "
    "Never regenerates the report -- patch only what changed. "
    "Orchestrator-only.",
    _REPORT_UPDATE_SCHEMA,
)
async def report_update(args: dict[str, Any]) -> dict[str, Any]:
    sid = _resolve_session_id(args)
    if not sid:
        return _text_result("No session bound for report tools.", is_error=True)
    changelog_summary = str(args.get("changelog_summary") or "").strip()
    if not changelog_summary:
        return _text_result(
            "report_update requires a non-empty changelog_summary.", is_error=True
        )

    draft = await _load_draft(sid) or ReportDraft(session_id=sid)
    changes: list[str] = []

    title = args.get("title")
    if isinstance(title, str) and title.strip():
        draft.title = title.strip()
        changes.append("title set")
    challenge_summary = args.get("challenge_summary")
    if isinstance(challenge_summary, str) and challenge_summary.strip():
        draft.challenge_summary = challenge_summary.strip()
        changes.append("challenge_summary set")

    for sec in args.get("upsert_sections") or []:
        if not isinstance(sec, dict) or not str(sec.get("id") or "").strip():
            continue
        action = draft.upsert_section(
            str(sec["id"]),
            heading=sec.get("heading"),
            body_md=sec.get("body_md"),
            sources=sec.get("sources"),
        )
        changes.append(f"section {sec['id']} {action}")

    for sec_id in args.get("remove_section_ids") or []:
        if draft.remove_section(str(sec_id)):
            changes.append(f"section {sec_id} removed")

    for entry in args.get("upsert_candidate_tools") or []:
        if not isinstance(entry, dict) or not str(entry.get("id") or "").strip():
            continue
        action = draft.upsert_candidate_tool(
            str(entry["id"]), title=entry.get("title"), status=entry.get("status")
        )
        changes.append(f"tool {entry['id']} {action}")

    for tool_id in args.get("remove_tool_ids") or []:
        if draft.remove_candidate_tool(str(tool_id)):
            changes.append(f"tool {tool_id} removed")

    draft.bump(turn=_current_report_turn, changelog_summary=changelog_summary)
    await get_report_store().save_draft(sid, draft.to_json())
    logger.info("report_update session=%s revision=%d: %s", sid, draft.revision, changes)

    return _text_result(json.dumps({
        "revision": draft.revision,
        "turn": _current_report_turn,
        "diff_summary": changes or ["no field changes (changelog only)"],
        "section_ids": [s.get("id") for s in draft.sections],
        "candidate_tool_count": len(draft.candidate_tools),
    }))


@tool(
    "report_render",
    "Render the session's current report draft to clean markdown for "
    "presenting to the user (title, revision, challenge, tools under "
    "consideration, all sections with sources). Orchestrator-only.",
    {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session id override; omit to use the current session.",
            },
        },
        "required": [],
    },
)
async def report_render(args: dict[str, Any]) -> dict[str, Any]:
    sid = _resolve_session_id(args)
    if not sid:
        return _text_result("No session bound for report tools.", is_error=True)
    draft = await _load_draft(sid)
    if draft is None:
        return _text_result(
            "No report draft exists for this session yet. Create one with "
            "report_update first."
        )
    return _text_result(draft.render_markdown())


def build_ee_mcp_server():
    """Create the in-process MCP server registered as 'ee' on the session."""
    return create_sdk_mcp_server(
        name="ee",
        version="0.3.0",
        tools=[
            ask_user_question,
            corpus_search,
            get_tool_profile,
            evidence_drilldown,
            report_get,
            report_update,
            report_render,
        ],
    )


# Fully-qualified tool names for AgentDefinition tool lists.
# (corpus_search / get_tool_profile names are exported by retrieval_tools.py.)
TOOL_ASK_USER = "mcp__ee__ask_user_question"
TOOL_EVIDENCE_DRILLDOWN = "mcp__ee__evidence_drilldown"
TOOL_REPORT_GET = "mcp__ee__report_get"
TOOL_REPORT_UPDATE = "mcp__ee__report_update"
TOOL_REPORT_RENDER = "mcp__ee__report_render"
