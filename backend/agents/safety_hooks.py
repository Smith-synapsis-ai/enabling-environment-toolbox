"""Programmatic read-only enforcement hooks for the EE Toolbox agent (A8).

The EE assistant is a READ-ONLY advisory assistant: it searches a local
corpus and answers questions. It has no legitimate need to write files,
run shell commands, or fetch arbitrary URLs. This module enforces that
posture PROGRAMMATICALLY via Claude Agent SDK PreToolUse hooks -- not just
via prompts or the orchestrator's ``disallowed_tools`` list (belt and
braces). Hooks fire regardless of ``permission_mode="bypassPermissions"``,
so they remain the enforcement layer even with permissions bypassed.

Policy (deny-by-default):
  - DENY mutating built-ins: Write, Edit, MultiEdit, NotebookEdit.
  - DENY Bash entirely (no legitimate shell need; simpler and safer than
    command parsing), plus its companions BashOutput / KillShell.
  - DENY any ``mcp__*`` tool whose server prefix is not on the approved
    list. Approved: ``mcp__ee__*`` (read-only corpus tools) and --
    forward-compatible, landing in this same wave (A7) -- ``mcp__memory__*``:
    memory_store/forget mutate ONLY the agent's own SQLite store, which is
    by-design writable; that is the single sanctioned write surface.
  - WebFetch: DENY unless the URL's host is on APPROVED_HTTP_HOSTS
    (exact match or subdomain). Empirically the PreToolUse hook input for
    WebFetch carries the URL at ``tool_input["url"]``.
  - WebSearch: DENY outright for now -- the corpus is local and WebSearch
    exposes no single host to validate.
  - ALLOW read-only built-ins: Read, Glob, Grep, Task/Agent (subagent
    dispatch), TodoWrite (agent-internal scratchpad, not a file write).
  - Anything else: DENY with reason "not on read-only allowlist".

Every decision (allow AND deny) is written to the JSONL audit log
(see agents.audit_log). Denials are returned to the SDK using the
PreToolUse ``hookSpecificOutput.permissionDecision = "deny"`` shape
(verified against installed claude_agent_sdk 0.1.72 types), so the model
receives the denial reason as the tool outcome and can continue read-only.

Stdlib + claude_agent_sdk only; independent of A5/A7 modules.
"""

from typing import Any
from urllib.parse import urlparse

from claude_agent_sdk import HookContext, HookMatcher

from agents.audit_log import log_event, set_audit_session

# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------

# Built-in tools that can mutate state -- always denied, with specific reasons.
DENY_WRITE_TOOLS: dict[str, str] = {
    "Write": "read-only assistant: file writes are blocked",
    "Edit": "read-only assistant: file edits are blocked",
    "MultiEdit": "read-only assistant: file edits are blocked",
    "NotebookEdit": "read-only assistant: notebook edits are blocked",
    "Bash": "read-only assistant: shell access is blocked entirely",
    "BashOutput": "read-only assistant: shell access is blocked entirely",
    "KillShell": "read-only assistant: shell access is blocked entirely",
}

# Read-only built-ins the agent may use freely. "Agent" is the current CLI
# name for subagent dispatch; "Task" the historical one (orchestrator accepts
# both). TodoWrite is the agent-internal todo scratchpad, not a file write.
ALLOW_READONLY_TOOLS: frozenset[str] = frozenset(
    {
        "Read", "Glob", "Grep", "Task", "Agent", "TodoWrite",
        # ToolSearch is a harness-internal read-only meta-tool: it loads deferred
        # tool schemas from the SDK registry. Subagents legitimately call it to
        # discover available tools; it performs no writes and hits no external hosts.
        "ToolSearch",
        # ListMCPServers is another harness-internal read-only meta-tool: it
        # enumerates connected MCP servers so subagents can discover tool namespaces.
        "ListMCPServers",
    }
)

# Approved MCP server prefixes. mcp__memory__* is forward-compatible for
# A7's memory tools (memory_store/forget mutate only the agent's own SQLite
# store, which is by-design writable -- documented exception).
APPROVED_MCP_PREFIXES: tuple[str, ...] = ("mcp__ee__", "mcp__memory__")

# Hosts WebFetch may reach (module-level constant; extend as needed).
APPROVED_HTTP_HOSTS: frozenset[str] = frozenset(
    {"cgspace.cgiar.org", "hdl.handle.net"}
)


# ---------------------------------------------------------------------------
# Pure decision function (unit-testable without the SDK runtime)
# ---------------------------------------------------------------------------

def evaluate_tool_use(tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str | None]:
    """Return ("allow"|"deny", reason-or-None) for one prospective tool call."""
    # 1. Explicit mutating built-ins
    if tool_name in DENY_WRITE_TOOLS:
        return "deny", DENY_WRITE_TOOLS[tool_name]

    # 2. MCP tools: prefix allowlist
    if tool_name.startswith("mcp__"):
        if tool_name.startswith(APPROVED_MCP_PREFIXES):
            return "allow", None
        return "deny", (
            f"MCP tool '{tool_name}' is not on the approved server allowlist "
            f"({', '.join(p + '*' for p in APPROVED_MCP_PREFIXES)})"
        )

    # 3. HTTP restriction
    if tool_name == "WebFetch":
        url = str((tool_input or {}).get("url", ""))
        host = (urlparse(url).hostname or "").lower()
        if host and any(
            host == approved or host.endswith("." + approved)
            for approved in APPROVED_HTTP_HOSTS
        ):
            return "allow", None
        return "deny", (
            f"WebFetch host '{host or 'unknown'}' is not on APPROVED_HTTP_HOSTS "
            f"({', '.join(sorted(APPROVED_HTTP_HOSTS))})"
        )
    if tool_name == "WebSearch":
        return "deny", (
            "WebSearch is disabled: the EE corpus is local and WebSearch "
            "exposes no host to validate"
        )

    # 4. Read-only built-ins
    if tool_name in ALLOW_READONLY_TOOLS:
        return "allow", None

    # 5. Deny-by-default for anything unknown
    return "deny", f"tool '{tool_name}' is not on the read-only allowlist"


# ---------------------------------------------------------------------------
# SDK hook callbacks
# ---------------------------------------------------------------------------

async def pre_tool_use_hook(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """PreToolUse: evaluate the policy, audit the decision, deny if needed."""
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {}) or {}
    decision, reason = evaluate_tool_use(tool_name, tool_input)

    log_event(
        event="pre_tool_use",
        tool_name=tool_name,
        tool_input=tool_input,
        decision=decision,
        reason=reason,
        fallback_session_id=input_data.get("session_id"),
    )

    if decision == "deny":
        # Programmatic denial: the model receives this reason as the tool
        # outcome (SDK 0.1.72 PreToolUseHookSpecificOutput shape).
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Blocked by EE read-only policy: {reason}",
            }
        }
    return {}


async def post_tool_use_hook(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """PostToolUse: audit completion (args hash + result size; never content)."""
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {}) or {}
    try:
        result_bytes = len(str(input_data.get("tool_response", "")))
    except Exception:
        result_bytes = -1

    log_event(
        event="post_tool_use",
        tool_name=tool_name,
        tool_input=tool_input,
        decision="allow",  # it executed; denied calls never reach PostToolUse
        fallback_session_id=input_data.get("session_id"),
        result_bytes=result_bytes,
    )
    return {}


# ---------------------------------------------------------------------------
# Factory for ClaudeAgentOptions(hooks=...)
# ---------------------------------------------------------------------------

def build_safety_hooks(session_id: str | None = None) -> dict[str, list[HookMatcher]]:
    """Return the ``hooks=`` value for ClaudeAgentOptions.

    Binds ``session_id`` (the normalized UUID from
    orchestrator._normalize_session_id) to the audit logger -- hooks do not
    natively receive our application session id, and the orchestrator
    process handles one session per run_challenge call.

    matcher=None matches ALL tools, so every tool call (orchestrator and
    subagents alike) passes through policy + audit.
    """
    if session_id:
        set_audit_session(session_id)
    return {
        "PreToolUse": [HookMatcher(matcher=None, hooks=[pre_tool_use_hook])],
        "PostToolUse": [HookMatcher(matcher=None, hooks=[post_tool_use_hook])],
    }
