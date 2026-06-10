"""JSONL audit logger for agent tool invocations (Task A8).

Every tool call the agent makes (PreToolUse decision AND PostToolUse
completion) is appended as one JSON line to::

    backend/data/audit/agent_audit.jsonl

Entry shape (see /analysis/task-a8-safety-hooks.md and wave3-interfaces.md):

    {"ts": "ISO-8601", "session_id": "<normalized uuid>",
     "event": "pre_tool_use|post_tool_use", "tool_name": "...",
     "args_sha256": "<hex>", "decision": "allow|deny",
     "reason": "<only when deny>"}

PRIVACY BY DESIGN: raw tool arguments are NEVER written to the audit log --
inputs may contain user text (the scaling challenge, follow-up answers).
Only a sha256 hash of the canonical JSON of the tool input is recorded,
which is enough to correlate/verify calls without retaining content.
Tool results are likewise never logged (only an optional size field).

Session binding: SDK hooks do not natively receive our application-level
session id, so the orchestrator process (one session per ``run_challenge``
call -- same assumption A5 uses) binds it via ``set_audit_session()``,
called from ``safety_hooks.build_safety_hooks(session_id)`` which the
orchestrator's fenced A8 wiring invokes inside ``build_options()``.

Stdlib-only on purpose; independent of A5/A7 modules.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# backend/data/audit/agent_audit.jsonl  (path fixed by wave3-interfaces.md §2)
_BACKEND_DIR: Path = Path(__file__).resolve().parents[1]
AUDIT_LOG_PATH: Path = _BACKEND_DIR / "data" / "audit" / "agent_audit.jsonl"

# Module-level current session id (normalized UUID string produced by
# orchestrator._normalize_session_id). One orchestrator process handles one
# session per run_challenge call, so a module-level binding is safe here.
_current_session_id: str | None = None


def set_audit_session(session_id: str) -> None:
    """Bind the application-level session id for subsequent audit entries."""
    global _current_session_id
    _current_session_id = session_id


def get_audit_session() -> str | None:
    """Return the currently bound session id (None if never set)."""
    return _current_session_id


def args_sha256(tool_input: Any) -> str:
    """sha256 hex digest of the canonical JSON (sorted keys) of a tool input.

    Hash, never raw args -- inputs may contain user text. Non-JSON-serializable
    values are stringified (``default=str``) so hashing never raises.
    """
    canonical = json.dumps(
        tool_input if tool_input is not None else {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def log_event(
    event: str,
    tool_name: str,
    tool_input: Any,
    decision: str,
    reason: str | None = None,
    fallback_session_id: str | None = None,
    result_bytes: int | None = None,
) -> dict[str, Any]:
    """Append one audit entry; return the entry dict (handy for tests).

    Args:
        event: "pre_tool_use" or "post_tool_use".
        tool_name: name of the tool invoked.
        tool_input: raw tool input (hashed here; never stored).
        decision: "allow" or "deny".
        reason: denial reason -- included only when decision == "deny".
        fallback_session_id: session id from the SDK hook payload, used only
            when no session was bound via set_audit_session().
        result_bytes: optional size of the tool result (post_tool_use only;
            result CONTENT is never logged).
    """
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": _current_session_id or fallback_session_id or "unknown",
        "event": event,
        "tool_name": tool_name,
        "args_sha256": args_sha256(tool_input),
        "decision": decision,
    }
    if decision == "deny" and reason:
        entry["reason"] = reason
    if result_bytes is not None:
        entry["result_bytes"] = result_bytes

    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Append-only, one json.dumps per line, flushed per write.
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
    except OSError as e:
        # An audit-write failure must never break the agent's tool pipeline.
        logger.warning("Audit log write failed: %s", e)
    return entry
