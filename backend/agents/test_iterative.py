"""Live multi-turn test for the iterative report flow (Task A5).

ONE session, fixed session id, THREE successive turns against the REAL
Anthropic API. Each turn must demonstrably refine/extend the persisted
report draft (revision increments, real content changes). Between turns the
PERSISTED draft JSON is printed by reading the store file directly; after
turn 3 a fresh store instance simulates a session reload and prints the
draft again (persistence proof).

Run:
    cd backend && python3 agents/test_iterative.py

Auth: ANTHROPIC_API_KEY may be absent -- the SDK rides the authenticated
`claude` CLI. Expect roughly $0.6 per turn.
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
from agents.report_state import (  # noqa: E402
    DEFAULT_DRAFTS_DIR,
    JsonFileReportStore,
    ReportDraft,
)

SESSION_ID = "7a5e0000-a5a5-4a5a-8a5a-000000000a51"  # fixed: one report, many turns

TURNS = [
    # Turn 1 -- draft created
    "Smallholder dairy farmers in Kenya can't access affordable credit to "
    "adopt improved forage varieties -- what enabling-environment "
    "interventions should we consider?",
    # Turn 2 -- draft deepened
    "Deepen the financial-services side: what does the evidence say about "
    "credit scorecards and index insurance specifically?",
    # Turn 3 -- scope adjusted
    "Add a gender-equality dimension and trim the report to the 3 strongest "
    "tools.",
]

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


def _print_persisted_draft(label: str) -> dict | None:
    """Read the PERSISTED draft JSON straight off disk and print it."""
    path = DEFAULT_DRAFTS_DIR / f"{SESSION_ID}.json"
    if not path.is_file():
        _hr(label)
        print("  (no draft file on disk)")
        return None
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    _hr(f"{label} (revision {data.get('revision')})")
    print(raw)
    return data


async def run_turn(n: int, text: str) -> dict | None:
    _hr(f"TURN {n} -- USER")
    print(_wrap(text))
    final_event = None
    async for event in run_challenge(text, SESSION_ID):
        etype = event["type"]
        ts = _now()
        if etype == "session_start":
            print(f"[{ts}] session_start: session_id={event['session_id']} "
                  f"orchestrator={event['orchestrator_model']} "
                  f"subagent={event['subagent_model']}")
        elif etype == "report_state":
            print(f"[{ts}] report_state: exists={event['exists']} "
                  f"revision={event['revision']} turn={event['turn']}")
        elif etype == "orchestrator_text":
            _hr(f"TURN {n} -- ORCHESTRATOR")
            print(_wrap(event["text"]))
        elif etype == "subagent_invocation":
            print(f"\n[{ts}] SUBAGENT -> {event['subagent_type']} "
                  f"({event['tool_use_id']})")
            print(_wrap(event["prompt"][:600], prefix="    "))
        elif etype == "subagent_text":
            print(f"\n[{ts}] SUBAGENT OUTPUT (parent {event['parent_tool_use_id']}):")
            print(_wrap(event["text"][:1200], prefix="    "))
        elif etype == "tool_call":
            parent = event.get("parent_tool_use_id")
            who = f"subagent {parent}" if parent else "orchestrator"
            print(f"\n[{ts}] TOOL CALL ({who}): {event['tool']}")
            print(_wrap(json.dumps(event["input"], indent=1)[:1200], prefix="    "))
        elif etype == "tool_result":
            flag = " [ERROR]" if event["is_error"] else ""
            print(f"\n[{ts}] TOOL RESULT{flag} (for {event['tool_use_id']}):")
            print(_wrap(str(event["content"])[:1200], prefix="    "))
        elif etype == "result":
            final_event = event
            _hr(f"TURN {n} -- RESULT")
            print(f"[{ts}] is_error      : {event['is_error']}")
            print(f"[{ts}] num_turns     : {event['num_turns']}")
            print(f"[{ts}] duration_ms   : {event['duration_ms']}")
            print(f"[{ts}] total_cost_usd: {event['total_cost_usd']}")
    return final_event


async def main() -> int:
    print(f"[{_now()}] EE Toolbox A5 iterative-report test starting")
    print(f"[{_now()}] Fixed session id: {SESSION_ID}")

    # Clean slate so the run is reproducible evidence.
    stale = DEFAULT_DRAFTS_DIR / f"{SESSION_ID}.json"
    if stale.is_file():
        stale.unlink()
        print(f"[{_now()}] removed stale draft {stale}")

    failures: list[str] = []
    revisions: list[int] = []

    for n, text in enumerate(TURNS, start=1):
        final_event = await run_turn(n, text)
        if final_event is None:
            failures.append(f"turn {n}: no result event")
        elif final_event["is_error"]:
            failures.append(f"turn {n}: result reported is_error=True")
        data = _print_persisted_draft(f"DRAFT AFTER TURN {n}")
        if data is None:
            failures.append(f"turn {n}: no persisted draft on disk")
        else:
            rev = int(data.get("revision", 0))
            if revisions and rev <= revisions[-1]:
                failures.append(
                    f"turn {n}: revision did not increase "
                    f"({revisions[-1]} -> {rev})"
                )
            revisions.append(rev)

    # --- session reload: fresh store instance, re-read persisted state ---
    fresh_store = JsonFileReportStore()
    raw = await fresh_store.load_draft(SESSION_ID)
    _hr("DRAFT AFTER RELOAD")
    if raw is None:
        print("  (load_draft returned None)")
        failures.append("reload: fresh store returned None")
    else:
        reloaded = ReportDraft.from_json(raw)
        print(raw)
        print(f"\n[{_now()}] reload check: revision={reloaded.revision} "
              f"turn_count={reloaded.turn_count} "
              f"sections={[s.get('id') for s in reloaded.sections]} "
              f"tools={len(reloaded.candidate_tools)}")
        if revisions and reloaded.revision != revisions[-1]:
            failures.append(
                f"reload: revision {reloaded.revision} != last persisted "
                f"{revisions[-1]}"
            )

    _hr("SUMMARY")
    print(f"revisions after each turn: {revisions}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: draft evolved across 3 turns and survived a reload")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
