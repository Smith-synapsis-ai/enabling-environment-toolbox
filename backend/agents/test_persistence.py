"""Restart test for Task A7: persistence across SEPARATE OS processes.

Parent harness spawns two sequential ``python3`` subprocesses against the
REAL store (backend/data/agent_store.db):

  --phase write : init DB, create a session (fixed UUID), append 3 messages,
                  save a report draft, store 2 memories, demonstrate
                  invalid-category rejection, print PID, EXIT.
  --phase read  : a FRESH process reloads session + messages + draft and
                  recalls a stored memory via FTS5; prints PID + everything
                  recalled verbatim.

Different PIDs prove the data survived a full process exit (i.e. a backend
restart). Run from backend/:  python3 agents/test_persistence.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

SESSION_ID = "7a7a7a7a-0000-4000-8000-a7a7a7a7a7a7"  # fixed UUID for the test

MESSAGES = [
    ("user", "We struggle to scale climate-smart maize varieties in Kenya.", ""),
    ("assistant", "Searching the EE toolbox for relevant pathways...", "agent_text"),
    ("assistant", "Recommended: policy engagement + seed-system finance tools.", "agent_text"),
]

DRAFT_JSON = json.dumps(
    {
        "title": "Scaling climate-smart maize in Kenya",
        "sections": ["challenge", "pathways"],
        "status": "draft",
    },
    sort_keys=True,
)

MEMORIES = [
    (
        "challenge_context",
        "User's challenge: scaling climate-smart maize varieties in Kenya; "
        "main blockers are seed regulation and smallholder finance.",
    ),
    (
        "accepted_pathways",
        "User accepted the pathway combining policy engagement on seed "
        "regulation with blended-finance instruments for smallholders.",
    ),
]


async def phase_write() -> None:
    from persistence import (
        MemoryStore,
        SessionStore,
        SqliteReportStore,
        get_db,
        init_db,
    )

    pid = os.getpid()
    print(f"[write] PID={pid}")
    await init_db()

    # Re-runnable: clear any rows from a previous test run (fixed UUID).
    async with get_db() as db:
        await db.execute("DELETE FROM messages WHERE session_id = ?", (SESSION_ID,))
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (SESSION_ID,))
        await db.execute("DELETE FROM report_drafts WHERE session_id = ?", (SESSION_ID,))
        await db.execute("DELETE FROM memories WHERE session_id = ?", (SESSION_ID,))
        await db.commit()

    sessions = SessionStore()
    row = await sessions.create_session(SESSION_ID, title="A7 restart test")
    print(f"[write] created session: {dict(row)}")

    for role, content, event_type in MESSAGES:
        msg_id = await sessions.append_message(SESSION_ID, role, content, event_type)
        print(f"[write] appended message id={msg_id} role={role!r}: {content!r}")

    reports = SqliteReportStore()
    await reports.save_draft(SESSION_ID, DRAFT_JSON)
    print(f"[write] saved report draft: {DRAFT_JSON}")

    memory = MemoryStore()
    for category, content in MEMORIES:
        result = await memory.store(category, content, session_id=SESSION_ID)
        print(f"[write] stored memory: {result}")

    # Category validation: must be REJECTED with an error dict.
    bad = await memory.store("random_thoughts", "this must be rejected")
    assert "error" in bad, f"invalid category was accepted: {bad}"
    print(f"[write] invalid-category rejection: {bad}")

    print(f"[write] PID={pid} exiting -- data must survive this process.")


async def phase_read() -> None:
    from persistence import MemoryStore, SessionStore, SqliteReportStore

    pid = os.getpid()
    print(f"[read] PID={pid} (fresh process)")

    sessions = SessionStore()
    session = await sessions.get_session(SESSION_ID)
    assert session is not None, "session not found after restart"
    print(f"[read] recalled session: {session}")

    history = await sessions.get_history(SESSION_ID)
    assert [(m["role"], m["content"]) for m in history] == [
        (r, c) for r, c, _ in MESSAGES
    ], f"history mismatch: {history}"
    print(f"[read] recalled {len(history)} messages:")
    for m in history:
        print(f"[read]   {m}")

    reports = SqliteReportStore()
    draft = await reports.load_draft(SESSION_ID)
    assert draft == DRAFT_JSON, f"draft mismatch: {draft!r}"
    print(f"[read] recalled report draft: {draft}")
    print(f"[read] report-store sessions: {await reports.list_sessions()}")

    memory = MemoryStore()
    recall = await memory.recall("climate-smart maize Kenya", limit=5)
    hits = [r for r in recall["results"] if r["source"] == "memory"]
    assert any(
        "climate-smart maize" in r["content"] for r in hits
    ), f"FTS recall missed the stored memory: {recall}"
    print(f"[read] memory_recall('climate-smart maize Kenya') -> "
          f"{len(recall['results'])} results:")
    for r in recall["results"]:
        print(f"[read]   {r}")

    print(f"[read] PID={pid}: ALL RECALL CHECKS PASSED")


def main() -> None:
    if "--phase" in sys.argv:
        phase = sys.argv[sys.argv.index("--phase") + 1]
        asyncio.run(phase_write() if phase == "write" else phase_read())
        return

    parent_pid = os.getpid()
    print(f"[parent] PID={parent_pid}; spawning two SEPARATE subprocesses\n")
    for phase in ("write", "read"):
        print(f"[parent] --- subprocess: --phase {phase} ---")
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--phase", phase],
            cwd=str(BACKEND_DIR),
        )
        if proc.returncode != 0:
            print(f"[parent] phase {phase!r} FAILED (rc={proc.returncode})")
            sys.exit(proc.returncode)
        print()
    print("[parent] RESTART TEST PASSED: two distinct PIDs, "
          "all data persisted across process exit.")


if __name__ == "__main__":
    main()
