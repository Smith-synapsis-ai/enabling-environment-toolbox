"""Tests for the A10 string->array coercion in the report_update tool.

Reproduces the A6 live-run defect: the SDK tool harness serialized the
array params (upsert_sections, upsert_candidate_tools, ...) as JSON-encoded
STRINGS, which were rejected as "not of type array" and left the draft stuck
at revision 1. After the A10 fix the same payload shape must apply cleanly.

Zero-API-cost: calls the tool handler directly (no model, no run_challenge).

Run:
    cd backend && python3 -m pytest agents/test_report_update_coercion.py -v -s
or as a plain script:
    cd backend && python3 agents/test_report_update_coercion.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import stub_tools  # noqa: E402
from agents.report_state import ReportDraft, set_report_store  # noqa: E402
from persistence.store import SqliteReportStore  # noqa: E402

# The @tool decorator wraps the function in an SdkMcpTool; the original
# coroutine is exposed as .handler.
_report_update = stub_tools.report_update.handler


def _fresh_session() -> tuple[str, SqliteReportStore, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    store = SqliteReportStore(db_path=Path(tmp.name) / "test_store.db")
    set_report_store(store)
    sid = str(uuid.uuid4())
    stub_tools.set_current_report_session(sid, turn=1)
    return sid, store, tmp


async def _draft(store: SqliteReportStore, sid: str) -> ReportDraft | None:
    raw = await store.load_draft(sid)
    return ReportDraft.from_json(raw) if raw is not None else None


def test_string_serialized_arrays_apply_cleanly() -> None:
    """THE previously-failing payload shape: arrays as JSON-encoded strings.

    This is exactly what the harness sent in the A6 live run (turn 2):
    upsert_sections / upsert_candidate_tools arrived as strings and were
    rejected as "not of type array". They must now decode and apply.
    """

    async def run() -> None:
        sid, store, tmp = _fresh_session()
        try:
            result = await _report_update({
                "title": "Enabling Affordable Credit for Forage Adoption",
                "upsert_sections": json.dumps([
                    {
                        "id": "evidence-gaps",
                        "heading": "Six evidence gaps to close",
                        "body_md": "Gap analysis before instrument design.",
                        "sources": ["10568-100343"],
                    },
                    {
                        "id": "pathway",
                        "heading": "Intervention pathway",
                        "body_md": "Credit-guarantee + forage bundling.",
                    },
                ]),
                "upsert_candidate_tools": json.dumps([
                    {"id": "10568-100343", "status": "accepted"},
                    {"id": "10568-100144", "status": "candidate"},
                ]),
                "changelog_summary": "drill-down: evidence gaps + pathway sections",
            })
            print("\n--- string-serialized payload result ---")
            print(json.dumps(result, indent=2))
            assert result.get("is_error") is not True, result
            payload = json.loads(result["content"][0]["text"])
            assert payload["revision"] == 1
            assert set(payload["section_ids"]) == {"evidence-gaps", "pathway"}
            assert payload["candidate_tool_count"] == 2

            draft = await _draft(store, sid)
            assert draft is not None and draft.revision == 1
            assert [s["id"] for s in draft.sections] == ["evidence-gaps", "pathway"]
            assert {t["id"] for t in draft.candidate_tools} == {
                "10568-100343",
                "10568-100144",
            }
            statuses = {t["id"]: t.get("status") for t in draft.candidate_tools}
            assert statuses["10568-100343"] == "accepted"
            print(f"draft revision: {draft.revision}, sections: "
                  f"{[s['id'] for s in draft.sections]}, tools: {sorted(statuses)}")
        finally:
            tmp.cleanup()

    asyncio.run(run())


def test_string_arrays_bump_revision_past_1_on_second_turn() -> None:
    """Turn-2 simulation: a real array call (rev 1), then a STRING-serialized
    call on turn 2 must bump to revision 2 (the A6 live run got stuck at 1)."""

    async def run() -> None:
        sid, store, tmp = _fresh_session()
        try:
            ok = await _report_update({
                "title": "Test report",
                "upsert_sections": [
                    {"id": "intro", "heading": "Intro", "body_md": "Hello."}
                ],
                "changelog_summary": "initial draft",
            })
            assert ok.get("is_error") is not True
            assert json.loads(ok["content"][0]["text"])["revision"] == 1

            stub_tools.set_current_report_session(sid, turn=2)
            bumped = await _report_update({
                "upsert_sections": json.dumps([
                    {"id": "drilldown", "heading": "Drill-down", "body_md": "Deep."}
                ]),
                "remove_section_ids": json.dumps([]),
                "changelog_summary": "turn-2 drill-down via string-serialized arrays",
            })
            print("\n--- turn-2 string-serialized result ---")
            print(json.dumps(bumped, indent=2))
            assert bumped.get("is_error") is not True, bumped
            payload = json.loads(bumped["content"][0]["text"])
            assert payload["revision"] == 2, "revision must bump past 1"
            assert payload["turn"] == 2

            draft = await _draft(store, sid)
            assert draft.revision == 2
            assert [s["id"] for s in draft.sections] == ["intro", "drilldown"]
            print(f"revision after turn-2 string call: {draft.revision} (PASS)")
        finally:
            tmp.cleanup()

    asyncio.run(run())


def test_invalid_json_string_rejected_no_bump() -> None:
    """A string that is not valid JSON must error explicitly with NO save."""

    async def run() -> None:
        sid, store, tmp = _fresh_session()
        try:
            bad = await _report_update({
                "upsert_sections": "[{id: intro, this is not json",
                "changelog_summary": "bad call",
            })
            print("\n--- invalid-JSON rejection payload ---")
            print(json.dumps(bad, indent=2))
            assert bad.get("is_error") is True
            text = bad["content"][0]["text"]
            assert "upsert_sections" in text
            assert "not valid JSON" in text
            assert "NOT modified" in text
            assert await _draft(store, sid) is None  # no draft created
            print("draft after rejected call: None (expected None)")
        finally:
            tmp.cleanup()

    asyncio.run(run())


def test_string_decoding_to_non_array_rejected_no_bump() -> None:
    """Valid JSON that is not an array (e.g. an object) must also reject,
    and an existing draft must keep its revision."""

    async def run() -> None:
        sid, store, tmp = _fresh_session()
        try:
            ok = await _report_update({
                "title": "Test report",
                "changelog_summary": "initial draft",
            })
            assert ok.get("is_error") is not True

            bad = await _report_update({
                "upsert_candidate_tools": json.dumps({"id": "10568-1", "status": "candidate"}),
                "changelog_summary": "object instead of array",
            })
            print("\n--- non-array rejection payload ---")
            print(json.dumps(bad, indent=2))
            assert bad.get("is_error") is True
            assert "decoded to dict" in bad["content"][0]["text"]

            draft = await _draft(store, sid)
            assert draft.revision == 1, "revision must be unchanged"
            assert draft.title == "Test report"
            print(f"revision after rejected call: {draft.revision} (must still be 1)")
        finally:
            tmp.cleanup()

    asyncio.run(run())


if __name__ == "__main__":
    test_string_serialized_arrays_apply_cleanly()
    test_string_arrays_bump_revision_past_1_on_second_turn()
    test_invalid_json_string_rejected_no_bump()
    test_string_decoding_to_non_array_rejected_no_bump()
    print("\nAll report_update coercion tests passed.")
