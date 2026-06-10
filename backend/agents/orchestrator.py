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

Read-only posture: the orchestrator may only use Task/TodoWrite plus the
read-only "ee" stub tools; Write/Edit/Bash and friends are disallowed.
Full enforcement hooks are Task A8.
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
from agents.retrieval_tools import TOOL_CORPUS_SEARCH, TOOL_GET_PROFILE
from agents.stub_tools import (
    TOOL_ASK_USER,
    TOOL_EVIDENCE_DRILLDOWN,
    build_ee_mcp_server,
)

# --- A8 wiring ---
from agents.safety_hooks import build_safety_hooks
# --- end A8 wiring ---

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
]

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


def build_options(session_id: str) -> ClaudeAgentOptions:
    """Assemble ClaudeAgentOptions for one challenge session."""
    return ClaudeAgentOptions(
        model=ORCHESTRATOR_MODEL,
        system_prompt=load_prompt("orchestrator"),
        agents=build_subagents(),
        mcp_servers={"ee": build_ee_mcp_server()},
        allowed_tools=_ALLOWED_TOOLS,
        disallowed_tools=_DISALLOWED_TOOLS,
        permission_mode="bypassPermissions",
        max_turns=MAX_TURNS,
        cwd=str(REPO_ROOT),
        session_id=session_id,
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

    options = build_options(sid)
    final_text_parts: list[str] = []

    async for message in query(prompt=challenge_text, options=options):
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
