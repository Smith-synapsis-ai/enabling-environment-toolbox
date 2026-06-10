"""Live round-trip test for the EE Toolbox agent scaffold (Task A2).

Sends one realistic scaling challenge through the full orchestrator +
subagent team against the REAL Anthropic API and prints the entire event
stream: orchestrator turns, every subagent invocation (name, input,
output), tool calls/results, and the final synthesized answer.

Run:
    cd backend && python3 agents/test_roundtrip.py

Expected to run on FALLBACK_PROMPT system prompts until the A3-authored
files land in backend/agents/prompts/.
"""

import asyncio
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

# backend/ on sys.path (same pattern as backend/scripts/*).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.orchestrator import run_challenge  # noqa: E402

CHALLENGE = (
    "Smallholder dairy farmers in Kenya can't access affordable credit to "
    "adopt improved forage varieties -- what enabling-environment "
    "interventions should we consider?"
)

_WRAP = 100


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _hr(label: str) -> None:
    print(f"\n{'=' * 12} {label} {'=' * 12}")


def _wrap(text: str, prefix: str = "  ") -> str:
    out = []
    for line in (text or "").splitlines():
        out.extend(textwrap.wrap(line, _WRAP, initial_indent=prefix,
                                 subsequent_indent=prefix) or [prefix])
    return "\n".join(out)


async def main() -> int:
    print(f"[{_now()}] EE Toolbox A2 round-trip test starting")
    print(f"[{_now()}] Challenge: {CHALLENGE}")

    final_event = None
    async for event in run_challenge(CHALLENGE):
        etype = event["type"]
        ts = _now()
        if etype == "session_start":
            _hr("SESSION START")
            print(f"[{ts}] session_id          : {event['session_id']}")
            print(f"[{ts}] orchestrator model  : {event['orchestrator_model']}")
            print(f"[{ts}] subagent model      : {event['subagent_model']}")
            print(f"[{ts}] prompt sources      : {json.dumps(event['prompt_sources'])}")
        elif etype == "orchestrator_text":
            _hr("ORCHESTRATOR")
            print(f"[{ts}]")
            print(_wrap(event["text"]))
        elif etype == "subagent_invocation":
            _hr(f"SUBAGENT INVOCATION -> {event['subagent_type']}")
            print(f"[{ts}] tool_use_id: {event['tool_use_id']}")
            print("  input prompt:")
            print(_wrap(event["prompt"], prefix="    "))
        elif etype == "subagent_text":
            _hr(f"SUBAGENT OUTPUT (parent {event['parent_tool_use_id']})")
            print(f"[{ts}]")
            print(_wrap(event["text"]))
        elif etype == "tool_call":
            parent = event.get("parent_tool_use_id")
            who = f"subagent {parent}" if parent else "orchestrator"
            print(f"\n[{ts}] TOOL CALL ({who}): {event['tool']}")
            print(_wrap(json.dumps(event["input"], indent=1)[:1500], prefix="    "))
        elif etype == "tool_result":
            flag = " [ERROR]" if event["is_error"] else ""
            print(f"\n[{ts}] TOOL RESULT{flag} (for {event['tool_use_id']}):")
            print(_wrap(str(event["content"])[:1500], prefix="    "))
        elif etype == "result":
            final_event = event
            _hr("FINAL RESULT")
            print(f"[{ts}] is_error      : {event['is_error']}")
            print(f"[{ts}] num_turns     : {event['num_turns']}")
            print(f"[{ts}] duration_ms   : {event['duration_ms']}")
            print(f"[{ts}] total_cost_usd: {event['total_cost_usd']}")
            print("\n----- FINAL ANSWER -----")
            print(event["final_text"])

    print(f"\n[{_now()}] round-trip test finished")
    if final_event is None:
        print("FAIL: no result event received")
        return 1
    if final_event["is_error"]:
        print("FAIL: result reported is_error=True")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
