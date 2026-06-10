"""Smoke tests for the assistant router (Task A6) — zero API cost.

``run_challenge`` is monkeypatched with a canned async generator, so NO live
orchestrator turn (and no Anthropic API call) ever happens here.

Run:
    cd backend && python3 -m pytest app/test_assistant_ws.py -v -s
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from agents.report_state import ReportDraft, set_report_store  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import assistant as assistant_module  # noqa: E402
from persistence.store import SqliteReportStore  # noqa: E402

SESSION_ID = str(uuid.uuid4())

CANNED_EVENTS = [
    {
        "type": "session_start",
        "session_id": SESSION_ID,
        "orchestrator_model": "test-orchestrator",
        "subagent_model": "test-subagent",
        "prompt_sources": {},
    },
    {"type": "report_state", "session_id": SESSION_ID, "revision": 0,
     "turn": 1, "exists": False},
    {"type": "orchestrator_text", "text": "Let me analyze your challenge."},
    {"type": "tool_call", "tool_use_id": "tu_1", "tool": "mcp__ee__report_update",
     "input": {"title": "Draft", "changelog_summary": "init"},
     "parent_tool_use_id": None},
    {"type": "tool_result", "tool_use_id": "tu_1",
     "content": [{"type": "text", "text": "{\"revision\": 1}"}],
     "is_error": False},
    {"type": "result", "session_id": "sdk-internal-id", "is_error": False,
     "duration_ms": 1234, "num_turns": 3, "total_cost_usd": 0.0,
     "usage": {}, "final_text": "Here is the initial pathway."},
]


def _fake_run_challenge(challenge_text: str, session_id: str | None = None):
    """Canned replacement for run_challenge (async generator)."""

    async def gen():
        for event in CANNED_EVENTS:
            await asyncio.sleep(0)  # yield control like the real stream
            yield event

    return gen()


def test_ws_challenge_streams_events_and_turn_complete(monkeypatch) -> None:
    monkeypatch.setattr(assistant_module, "run_challenge", _fake_run_challenge)
    client = TestClient(app)

    with client.websocket_connect("/ws/challenge") as ws:
        ws.send_text(json.dumps({
            "challenge_text": "How do I scale seed systems in Ethiopia?",
            "session_id": SESSION_ID,
        }))

        frames = []
        while True:
            frame = json.loads(ws.receive_text())
            frames.append(frame)
            if frame.get("type") == "turn_complete":
                break

        types = [f["type"] for f in frames]
        print("\nframe order:", " -> ".join(types))
        assert types == [
            "session_start", "report_state", "orchestrator_text",
            "tool_call", "tool_result", "result", "turn_complete",
        ]
        # Events forwarded verbatim
        assert frames[0]["session_id"] == SESSION_ID
        assert frames[3]["tool"] == "mcp__ee__report_update"
        assert frames[5]["final_text"] == "Here is the initial pathway."

        # Socket stays open for multi-turn: send a second message.
        ws.send_text(json.dumps({
            "challenge_text": "I approve this pathway.",
            "session_id": SESSION_ID,
        }))
        second = []
        while True:
            frame = json.loads(ws.receive_text())
            second.append(frame)
            if frame.get("type") == "turn_complete":
                break
        print("second-turn frames:", len(second))
        assert [f["type"] for f in second][-1] == "turn_complete"
        assert len(second) == len(CANNED_EVENTS) + 1


def test_ws_invalid_session_id_and_empty_text(monkeypatch) -> None:
    monkeypatch.setattr(assistant_module, "run_challenge", _fake_run_challenge)
    client = TestClient(app)

    with client.websocket_connect("/ws/challenge") as ws:
        # Non-UUID session id -> error frame, no orchestrator call.
        ws.send_text(json.dumps({
            "challenge_text": "hello", "session_id": "not-a-uuid",
        }))
        err = json.loads(ws.receive_text())
        sentinel = json.loads(ws.receive_text())
        print("\ninvalid-uuid error:", err)
        assert err["type"] == "error" and "UUID" in err["message"]
        assert sentinel["type"] == "turn_complete"

        # Empty challenge text -> error frame.
        ws.send_text(json.dumps({"challenge_text": "", "session_id": None}))
        err2 = json.loads(ws.receive_text())
        sentinel2 = json.loads(ws.receive_text())
        assert err2["type"] == "error"
        assert sentinel2["type"] == "turn_complete"


def test_ws_run_challenge_exception_sends_error_not_crash(monkeypatch) -> None:
    def _boom(challenge_text: str, session_id: str | None = None):
        async def gen():
            yield {"type": "orchestrator_text", "text": "starting..."}
            raise RuntimeError("synthetic failure")

        return gen()

    monkeypatch.setattr(assistant_module, "run_challenge", _boom)
    client = TestClient(app)

    with client.websocket_connect("/ws/challenge") as ws:
        ws.send_text(json.dumps({
            "challenge_text": "trigger failure", "session_id": SESSION_ID,
        }))
        first = json.loads(ws.receive_text())
        err = json.loads(ws.receive_text())
        sentinel = json.loads(ws.receive_text())
        print("\nerror frame:", err)
        assert first["type"] == "orchestrator_text"
        assert err["type"] == "error" and "synthetic failure" in err["message"]
        assert sentinel["type"] == "turn_complete"

        # Socket still usable after the error.
        monkeypatch.setattr(assistant_module, "run_challenge", _fake_run_challenge)
        ws.send_text(json.dumps({
            "challenge_text": "retry", "session_id": SESSION_ID,
        }))
        frame = json.loads(ws.receive_text())
        assert frame["type"] == "session_start"


def test_sessions_and_draft_endpoints(tmp_path) -> None:
    store = SqliteReportStore(db_path=tmp_path / "endpoint_test.db")
    set_report_store(store)

    sid = str(uuid.uuid4())
    draft = ReportDraft(session_id=sid, title="Endpoint test report")
    draft.upsert_section("intro", "Introduction", "Some **markdown** body.")
    draft.upsert_candidate_tool("tool-1", "Seed System Framework", "candidate")
    draft.bump(turn=1, changelog_summary="initial")
    asyncio.run(store.save_draft(sid, draft.to_json()))

    client = TestClient(app)

    # GET /api/assistant/sessions
    res = client.get("/api/assistant/sessions")
    print("\nsessions response:", res.json())
    assert res.status_code == 200
    assert sid in res.json()["sessions"]

    # GET /api/assistant/sessions/{sid}/draft
    res = client.get(f"/api/assistant/sessions/{sid}/draft")
    assert res.status_code == 200
    body = res.json()
    print("draft keys:", sorted(body.keys()))
    assert body["session_id"] == sid
    assert body["revision"] == 1
    assert body["title"] == "Endpoint test report"
    assert "rendered_markdown" in body
    assert "# Endpoint test report" in body["rendered_markdown"]
    assert "Seed System Framework" in body["rendered_markdown"]
    print("rendered_markdown head:",
          body["rendered_markdown"].splitlines()[0])

    # 404 for an unknown session
    res = client.get(f"/api/assistant/sessions/{uuid.uuid4()}/draft")
    assert res.status_code == 404
    print("unknown-session draft status:", res.status_code)
