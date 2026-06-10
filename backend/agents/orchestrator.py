"""EE Toolbox orchestrator entry point (Task A2).

Transport-agnostic: ``run_challenge(challenge_text, session_id)`` returns an
async iterator of plain event dicts. The WebSocket layer (Task A6) and the
CLI round-trip test (test_roundtrip.py) consume the exact same stream.

Event shapes (all dicts, key "type" discriminates):
  {"type": "session_start", "session_id", "orchestrator_model", "subagent_model",
   "prompt_sources": {...}}
  {"type": "orchestrator_text", "text"}
  {"type": "subagent_text", "parent_tool_use_id", "text"}
  {"type": "subagent_invocation", "tool_use_id", "subagent_type", "prompt"}
  {"type": "tool_call", "tool_use_id", "tool", "input", "parent_tool_use_id"}
  {"type": "tool_result", "tool_use_id", "content", "is_error"}
  {"type": "result", "session_id", "is_error", "duration_ms", "num_turns",
   "total_cost_usd", "usage", "final_text"}
  {"type": "report_state", "session_id", "revision", "turn", "exists"}   (A5)

Read-only posture: the orchestrator may only use Task/TodoWrite plus the
"ee" tools (read-only catalog access + the A5 report-draft tools, which
persist only the assistant's own report state); Write/Edit/Bash and friends
are disallowed. Full enforcement hooks are Task A8.

Iterative report flow (Task A5): a per-session report draft persists in the
ReportStore (see report_state.py). Calling ``run_challenge`` again with the
SAME session_id is a refinement turn: the existing draft is loaded, a
``report_state`` event announces it, and the SDK session is RESUMED so the
model keeps full conversational context. Resume bookkeeping: the CLI may
assign a fresh internal session id on resume, so we track the latest SDK
session id per logical session in ``_RESUME_IDS`` and resume from that. If
the process restarted (no resume id known), we fall back to injecting the
rendered draft + changelog into the new turn -- report state survives via
the store either way.
"""

import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from agents.definitions import build_subagents
from agents.model_config import ORCHESTRATOR_MODEL, SUBAGENT_MODEL
from agents.prompt_loader import load_prompt, prompt_source
from agents.report_state import ReportDraft, get_report_store
from agents.evidence_tools import TOOL_EVIDENCE_DRILLDOWN
from agents.retrieval_tools import TOOL_CORPUS_SEARCH, TOOL_GET_PROFILE
from agents.stub_tools import (
    TOOL_ASK_USER,
    TOOL_REPORT_GET,
    TOOL_REPORT_RENDER,
    TOOL_REPORT_UPDATE,
    build_ee_mcp_server,
    set_current_report_session,
)
# --- A7 wiring ---
from agents.memory_tools import MEMORY_TOOL_NAMES, build_memory_mcp_server
# --- end A7 wiring ---

# --- A8 wiring ---
from agents.safety_hooks import build_safety_hooks
# --- end A8 wiring ---

# --- coordinator (Wave 3 merge): swap default report store to SQLite (A7) ---
# A5 ships JsonFileReportStore as its default; the wave3-interfaces contract
# says the coordinator swaps in A7's SqliteReportStore at merge time so report
# drafts live in the same agent_store.db as sessions/messages/memories.
# SqliteReportStore is self-initializing (ensure_db per call), so a plain
# module-level swap is sufficient.
from persistence.store import SqliteReportStore
from agents.report_state import set_report_store

set_report_store(SqliteReportStore())
# --- end coordinator ---

logger = logging.getLogger(__name__)

REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# Hard cap on orchestrator turns -- a challenge consultation should finish
# well inside this; protects against runaway loops in the prototype.
MAX_TURNS = 30

# Belt-and-braces read-only posture (proper hooks are Task A8).
_DISALLOWED_TOOLS = [
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Bash",
    "BashOutput",
    "KillShell",
    "WebFetch",
    "WebSearch",
]

_ALLOWED_TOOLS = [
    "Task",   # subagent dispatch (older CLI name)
    "Agent",  # subagent dispatch (current CLI name)
    "TodoWrite",
    TOOL_ASK_USER,
    TOOL_CORPUS_SEARCH,
    TOOL_GET_PROFILE,
    TOOL_EVIDENCE_DRILLDOWN,
    TOOL_REPORT_GET,
    TOOL_REPORT_UPDATE,
    TOOL_REPORT_RENDER,
]
# --- A7 wiring ---
_ALLOWED_TOOLS += MEMORY_TOOL_NAMES
# --- end A7 wiring ---

# Logical session id -> latest SDK session id, for resuming multi-turn
# sessions within this process. The CLI can assign a fresh internal session
# id on each resume, so always resume from the LATEST one (resuming the
# original id would drop later turns).
_RESUME_IDS: dict[str, str] = {}

_PROMPT_NAMES = (
    "orchestrator",
    "triage",
    "corpus_search",
    "multi_tool_reasoning",
    "evidence_drill_down",
)


def _normalize_session_id(session_id: str | None) -> str:
    """Return a valid UUID string (the SDK requires UUID session ids)."""
    if session_id:
        try:
            return str(uuid.UUID(str(session_id)))
        except ValueError:
            logger.warning("session_id %r is not a UUID; generating one", session_id)
    return str(uuid.uuid4())


def build_options(
    session_id: str,
    *,
    resume_from: str | None = None,
) -> ClaudeAgentOptions:
    """Assemble ClaudeAgentOptions for one challenge session.

    Args:
        session_id: normalized UUID for a NEW SDK session.
        resume_from: when set, RESUME that SDK session instead of starting a
            new one (the SDK forbids combining ``session_id`` and ``resume``,
            so ``session_id`` is ignored in that case).
    """
    return ClaudeAgentOptions(
        model=ORCHESTRATOR_MODEL,
        system_prompt=load_prompt("orchestrator"),
        agents=build_subagents(),
        mcp_servers={
            "ee": build_ee_mcp_server(),
            # --- A7 wiring ---
            "memory": build_memory_mcp_server(),
            # --- end A7 wiring ---
        },
        allowed_tools=_ALLOWED_TOOLS,
        disallowed_tools=_DISALLOWED_TOOLS,
        permission_mode="bypassPermissions",
        max_turns=MAX_TURNS,
        cwd=str(REPO_ROOT),
        session_id=None if resume_from else session_id,
        resume=resume_from,
        # --- A8 wiring ---
        # Programmatic read-only enforcement + JSONL audit (Task A8). Hooks
        # fire regardless of permission_mode="bypassPermissions", so they are
        # the enforcement layer; bypassPermissions stays.
        hooks=build_safety_hooks(session_id),
        # --- end A8 wiring ---
    )


def _block_text(content: Any) -> str:
    """Flatten a ToolResultBlock content payload to readable text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


async def run_challenge(
    challenge_text: str,
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Run one scaling-challenge consultation through the agent team.

    Args:
        challenge_text: the user's scaling challenge, free text.
        session_id: optional UUID string; generated when absent/invalid.

    Yields:
        Plain event dicts (see module docstring) -- safe to JSON-serialize
        for the A6 WebSocket transport.
    """
    sid = _normalize_session_id(session_id)
    yield {
        "type": "session_start",
        "session_id": sid,
        "orchestrator_model": ORCHESTRATOR_MODEL,
        "subagent_model": SUBAGENT_MODEL,
        "prompt_sources": {name: prompt_source(name) for name in _PROMPT_NAMES},
    }

    # --- Report lifecycle (Task A5) -------------------------------------
    # Load any existing draft for this session; a draft means this is a
    # refinement turn, never a restart.
    draft_raw = await get_report_store().load_draft(sid)
    draft = ReportDraft.from_json(draft_raw) if draft_raw else None
    turn = (draft.turn_count + 1) if draft else 1
    # Bind the report tools to this session (one session per run_challenge
    # call by design; the tools also accept an explicit session_id override).
    set_current_report_session(sid, turn=turn)
    yield {
        "type": "report_state",
        "session_id": sid,
        "revision": draft.revision if draft else 0,
        "turn": turn,
        "exists": draft is not None,
    }

    resume_from = _RESUME_IDS.get(sid)
    prompt = challenge_text
    if draft is not None:
        if resume_from:
            # SDK resume keeps full conversational context; a short context
            # block reminds the orchestrator of the draft state.
            prompt = (
                f"[Report context] An existing report draft (revision "
                f"{draft.revision}, turn {turn} of this session) exists -- "
                "refine and extend it with the report tools; do not restart "
                f"the flow.\n\nUser: {challenge_text}"
            )
        else:
            # Process restarted (no SDK session to resume): inject the
            # rendered draft + changelog so the new SDK session still
            # continues the report rather than restarting it.
            changelog = "\n".join(
                f"- rev {c.get('revision')} (turn {c.get('turn')}): {c.get('summary')}"
                for c in draft.changelog
            )
            prompt = (
                f"[Report context] An existing report draft (revision "
                f"{draft.revision}) exists for this session -- refine it, do "
                "not restart. Current draft:\n\n"
                f"{draft.render_markdown()}\n\nChangelog:\n{changelog}\n\n"
                f"User: {challenge_text}"
            )

    options = build_options(sid, resume_from=resume_from)
    final_text_parts: list[str] = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            parent_id = getattr(message, "parent_tool_use_id", None)
            for block in message.content:
                if isinstance(block, TextBlock):
                    if parent_id:
                        yield {
                            "type": "subagent_text",
                            "parent_tool_use_id": parent_id,
                            "text": block.text,
                        }
                    else:
                        final_text_parts.append(block.text)
                        yield {"type": "orchestrator_text", "text": block.text}
                elif isinstance(block, ToolUseBlock):
                    # Subagent dispatch tool: named "Task" historically,
                    # "Agent" in current CLI builds -- accept both.
                    if block.name in ("Task", "Agent"):
                        yield {
                            "type": "subagent_invocation",
                            "tool_use_id": block.id,
                            "subagent_type": (block.input or {}).get("subagent_type"),
                            "prompt": (block.input or {}).get("prompt", ""),
                        }
                    else:
                        yield {
                            "type": "tool_call",
                            "tool_use_id": block.id,
                            "tool": block.name,
                            "input": block.input,
                            "parent_tool_use_id": parent_id,
                        }
        elif isinstance(message, UserMessage):
            content = message.content
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, ToolResultBlock):
                        yield {
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": _block_text(block.content),
                            "is_error": bool(block.is_error),
                        }
        elif isinstance(message, ResultMessage):
            # Track the latest SDK session id so the NEXT run_challenge call
            # for this logical session resumes from it (A5 multi-turn).
            if message.session_id:
                _RESUME_IDS[sid] = message.session_id
            yield {
                "type": "result",
                "session_id": message.session_id,
                "is_error": message.is_error,
                "duration_ms": message.duration_ms,
                "num_turns": message.num_turns,
                "total_cost_usd": message.total_cost_usd,
                "usage": message.usage,
                "final_text": message.result or "\n\n".join(final_text_parts),
            }
        elif isinstance(message, SystemMessage):
            # init/system chatter -- not surfaced to transports for now.
            logger.debug("SystemMessage: %s", getattr(message, "subtype", ""))
