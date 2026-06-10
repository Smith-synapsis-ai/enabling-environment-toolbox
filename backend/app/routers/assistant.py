"""Assistant router — conversational challenge assistant (Task A6).

Exposes:

* ``WS /ws/challenge`` — streams orchestrator events for a challenge turn.
  The client sends JSON text frames of the shape::

      {"challenge_text": "...", "session_id": "<uuid>"}

  For each message the server iterates ``run_challenge`` and forwards every
  event dict as a single JSON text frame, then sends a
  ``{"type": "turn_complete"}`` sentinel.  The socket stays open so the same
  connection can carry multiple turns (refinement / approval).

* ``GET /api/assistant/sessions`` — lists persisted report-draft sessions.

* ``GET /api/assistant/sessions/{session_id}/draft`` — returns the parsed
  draft JSON plus a ``rendered_markdown`` field.

Concurrency note
----------------
The agent layer binds the active report session via a module-level
``set_current_report_session`` call inside ``run_challenge``, i.e. the
orchestrator can only safely run ONE session at a time per process.  We
therefore serialize all turns through a single global ``asyncio.Lock``
(across all websocket connections).  This is a deliberate, documented
simplification for the prototype: concurrent users queue rather than
corrupt each other's report state.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

# Importing agents.orchestrator also swaps the default in-memory report store
# for the SQLite-backed one (side effect at module import).  run_challenge is
# referenced lazily (module attribute) in the WS handler so tests can
# monkeypatch ``app.routers.assistant.run_challenge``.
from agents.orchestrator import run_challenge  # noqa: F401
from agents.report_state import ReportDraft, get_report_store

logger = logging.getLogger("ee.assistant")

router = APIRouter()

# Global lock: the orchestrator supports one active session per process.
_CHALLENGE_LOCK = asyncio.Lock()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


@router.websocket("/ws/challenge")
async def challenge_ws(websocket: WebSocket) -> None:
    """Multi-turn challenge socket.

    Each inbound JSON message triggers one orchestrator turn.  Events are
    forwarded verbatim; a ``turn_complete`` sentinel marks the end of each
    turn (sent even after errors so the client can unblock its input).
    """
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()

            # -- parse + validate the inbound message -------------------
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps(
                    {"type": "error", "message": "Invalid JSON message."}
                ))
                await websocket.send_text(json.dumps({"type": "turn_complete"}))
                continue

            challenge_text = str(payload.get("challenge_text") or "").strip()
            session_id = payload.get("session_id")

            if not challenge_text:
                await websocket.send_text(json.dumps(
                    {"type": "error", "message": "challenge_text is required."}
                ))
                await websocket.send_text(json.dumps({"type": "turn_complete"}))
                continue

            # The orchestrator silently regenerates non-UUID session ids,
            # which would break resume — fail fast instead.
            if session_id is not None and not _is_uuid(str(session_id)):
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": (
                        "session_id must be a valid UUID "
                        f"(got {session_id!r})."
                    ),
                }))
                await websocket.send_text(json.dumps({"type": "turn_complete"}))
                continue

            # -- run one orchestrator turn (serialized globally) --------
            try:
                async with _CHALLENGE_LOCK:
                    async for event in run_challenge(
                        challenge_text,
                        session_id=str(session_id) if session_id else None,
                    ):
                        await websocket.send_text(
                            json.dumps(event, default=str)
                        )
            except WebSocketDisconnect:
                raise
            except Exception as exc:  # noqa: BLE001 — never crash the socket
                logger.exception("Challenge turn failed")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Turn failed: {exc}",
                    }))
                except Exception:  # socket already gone
                    raise WebSocketDisconnect() from exc

            await websocket.send_text(json.dumps({"type": "turn_complete"}))
    except WebSocketDisconnect:
        logger.info("Challenge websocket disconnected")


@router.get("/api/assistant/sessions")
async def list_sessions() -> dict:
    """List persisted report-draft sessions (most recently updated first)."""
    store = get_report_store()
    sessions = await store.list_sessions()
    return {"sessions": sessions}


@router.get("/api/assistant/sessions/{session_id}/draft")
async def get_session_draft(session_id: str) -> dict:
    """Return the parsed report draft plus rendered markdown, or 404."""
    store = get_report_store()
    raw = await store.load_draft(session_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="No draft for this session")
    draft = ReportDraft.from_json(raw)
    data = json.loads(draft.to_json())
    data["rendered_markdown"] = draft.render_markdown()
    return data
