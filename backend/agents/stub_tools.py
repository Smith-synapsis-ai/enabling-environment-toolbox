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
  - mcp__ee__evidence_drilldown  (Evidence Drill-Down) -- REAL B1 evidence-store
                                                     FTS (see evidence_tools.py)
  - mcp__ee__report_get          (orchestrator) -- current report draft (A5)
  - mcp__ee__report_update       (orchestrator) -- patch the report draft (A5)
  - mcp__ee__report_render       (orchestrator) -- render draft to markdown (A5)
"""

import json
import logging
from typing import Any, Awaitable, Callable

from claude_agent_sdk import create_sdk_mcp_server, tool

from agents.evidence_tools import evidence_drilldown
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
#
# evidence_drilldown -- REAL B1 evidence-store FTS drill-down
# Implemented in agents/evidence_tools.py and registered below.
# ---------------------------------------------------------------------------


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
            "type": ["array", "string"],
            "description": (
                "Sections to add or update by id. Each item: {id, heading, "
                "body_md, sources?: [links]}. Existing sections with the same "
                "id are updated in place; others are appended. A JSON-encoded "
                "string of the same array is also accepted (harness "
                "workaround) and decoded server-side."
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
            "type": ["array", "string"],
            "items": {"type": "string"},
            "description": (
                "Section ids to remove. A JSON-encoded string of the same "
                "array is also accepted and decoded server-side."
            ),
        },
        "upsert_candidate_tools": {
            "type": ["array", "string"],
            "description": (
                "Candidate-tool entries to add or update by id. Each item: "
                "{id, title?, status?: candidate|accepted|rejected}. A JSON-"
                "encoded string of the same array is also accepted (harness "
                "workaround) and decoded server-side."
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
            "type": ["array", "string"],
            "items": {"type": "string"},
            "description": (
                "Candidate-tool ids to remove from the draft. A JSON-encoded "
                "string of the same array is also accepted and decoded "
                "server-side."
            ),
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

# Array-typed report_update params that the SDK tool harness has been observed
# to serialize as JSON-encoded STRINGS (A6 live-run defect: "not of type
# array" rejections left the draft stuck at revision 1). _coerce_array_params
# decodes such strings back to lists before the patch is applied (A10 fix,
# sibling to the A6 unknown-key rejection).
_ARRAY_PARAMS = (
    "upsert_sections",
    "remove_section_ids",
    "upsert_candidate_tools",
    "remove_tool_ids",
)


def _coerce_array_params(args: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Decode JSON-string values for array params; never mutates the input.

    Returns (coerced_args, error_message). error_message is None on success;
    on failure the caller must reject the call WITHOUT modifying the draft.
    """
    coerced = dict(args)
    for key in _ARRAY_PARAMS:
        value = coerced.get(key)
        if value is None or isinstance(value, list):
            continue
        if not isinstance(value, str):
            return coerced, (
                f"report_update rejected: '{key}' must be a JSON array (or a "
                f"JSON-encoded string of one), got {type(value).__name__}."
            )
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            return coerced, (
                f"report_update rejected: '{key}' was a string that is not "
                f"valid JSON ({exc.msg} at pos {exc.pos}). Pass a JSON array, "
                f"e.g. {key}=[{{...}}]."
            )
        if not isinstance(decoded, list):
            return coerced, (
                f"report_update rejected: '{key}' decoded to "
                f"{type(decoded).__name__}, expected a JSON array."
            )
        coerced[key] = decoded
        logger.info(
            "report_update: coerced %s from JSON string to array (%d items)",
            key,
            len(decoded),
        )
    return coerced, None


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
    # --- A6: reject unknown top-level keys explicitly ---------------------
    # Previously unknown keys (e.g. "sections" instead of "upsert_sections")
    # were SILENTLY ignored while the revision still bumped; now the tool
    # errors out (no save, no revision bump) so the model self-corrects.
    allowed_keys = set(_REPORT_UPDATE_SCHEMA["properties"])
    unknown = set(args) - allowed_keys
    if unknown:
        return _text_result(
            "report_update rejected: unknown top-level key(s): "
            f"{', '.join(sorted(unknown))}. Allowed keys: "
            f"{', '.join(sorted(allowed_keys))}. The draft was NOT modified "
            "(revision unchanged). Retry using only allowed keys (e.g. use "
            "upsert_sections, not sections).",
            is_error=True,
        )
    # --- end A6 ------------------------------------------------------------
    # --- A10: coerce JSON-string array params back to arrays ---------------
    # The SDK tool harness sometimes serializes array params as JSON-encoded
    # strings ("not of type array" in the A6 live run). Decode them here; on
    # any decode failure reject explicitly (no save, no revision bump).
    args, coercion_error = _coerce_array_params(args)
    if coercion_error:
        return _text_result(
            coercion_error + " The draft was NOT modified (revision unchanged).",
            is_error=True,
        )
    # --- end A10 ------------------------------------------------------------
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
    # B1: one-shot S3 cold-load of retrieval + evidence artifacts. No-op
    # unless EE_RETRIEVAL_S3 is set (local mode keeps default repo paths).
    from agents.artifact_loader import init_from_env

    init_from_env()
    return create_sdk_mcp_server(
        name="ee",
        version="0.4.0",
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
# (corpus_search / get_tool_profile names are exported by retrieval_tools.py;
#  evidence_drilldown's name is exported by evidence_tools.py.)
TOOL_ASK_USER = "mcp__ee__ask_user_question"
TOOL_REPORT_GET = "mcp__ee__report_get"
TOOL_REPORT_UPDATE = "mcp__ee__report_update"
TOOL_REPORT_RENDER = "mcp__ee__report_render"
