"""Tests for the A6 unknown-key rejection in the report_update tool.

Zero-API-cost: calls the tool handler directly (no model, no run_challenge).

Run:
    cd backend && python3 -m pytest agents/test_report_update_validation.py -v -s
or as a plain script:
    cd backend && python3 agents/test_report_update_validation.py
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
_report_get = stub_tools.report_get.handler


def _fresh_session() -> tuple[str, SqliteReportStore, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    store = SqliteReportStore(db_path=Path(tmp.name) / "test_store.db")
    set_report_store(store)
    sid = str(uuid.uuid4())
    stub_tools.set_current_report_session(sid, turn=1)
    return sid, store, tmp


async def _revision(store: SqliteReportStore, sid: str) -> int | None:
    raw = await store.load_draft(sid)
    if raw is None:
        return None
    return ReportDraft.from_json(raw).revision


def test_alias_sections_accepted_as_upsert_sections() -> None:
    """``sections`` is a legacy alias for ``upsert_sections`` (Fix 3).

    Prior to Fix 3, ``sections`` was an unknown key and the call was rejected.
    After Fix 3 the alias is silently normalised before validation, so the call
    succeeds, the section is created, and the draft is bumped to revision 1.
    """

    async def run() -> None:
        sid, store, tmp = _fresh_session()
        try:
            result = await _report_update({
                "sections": [{"id": "intro", "heading": "Intro", "body_md": "x"}],
                "changelog_summary": "alias key should now succeed",
            })
            print("\n--- alias-accepted payload ---")
            print(json.dumps(result, indent=2))
            assert result.get("is_error") is not True, (
                f"Expected success but got is_error=True: {result}"
            )
            # Draft must have been created at revision 1.
            rev = await _revision(store, sid)
            print(f"draft revision after alias call: {rev} (expected 1)")
            assert rev == 1
            # Section must be present in the saved draft.
            draft = ReportDraft.from_json(await store.load_draft(sid))
            # draft.sections is a list of dicts ({"id": ..., "heading": ..., ...})
            section_ids = [s["id"] for s in draft.sections]
            assert "intro" in section_ids, (
                f"Expected 'intro' section, got ids: {section_ids}"
            )
        finally:
            tmp.cleanup()

    asyncio.run(run())


def test_truly_unknown_key_rejected_no_draft_created() -> None:
    """A call with a genuinely unknown key errors out and creates NO draft."""

    async def run() -> None:
        sid, store, tmp = _fresh_session()
        try:
            result = await _report_update({
                "completely_bogus_field": "should not work",
                "changelog_summary": "bad call with totally unknown key",
            })
            print("\n--- rejection payload (truly unknown key, fresh session) ---")
            print(json.dumps(result, indent=2))
            assert result.get("is_error") is True, (
                f"Expected is_error=True but call succeeded: {result}"
            )
            text = result["content"][0]["text"]
            assert "completely_bogus_field" in text
            # No draft must have been created.
            rev = await _revision(store, sid)
            print(f"draft revision after rejected call: {rev} (expected None)")
            assert rev is None
        finally:
            tmp.cleanup()

    asyncio.run(run())


def test_good_call_succeeds_then_bad_call_does_not_bump() -> None:
    """A valid call bumps to revision 1; a following bad call leaves it at 1."""

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
            print("\n--- good-call payload ---")
            print(json.dumps(ok, indent=2))
            assert ok.get("is_error") is not True
            rev_after_good = await _revision(store, sid)
            print(f"revision after good call: {rev_after_good}")
            assert rev_after_good == 1

            bad = await _report_update({
                "title": "Should not apply",
                "bogus_key": True,
                "changelog_summary": "bad call",
            })
            print("\n--- rejection payload (existing draft) ---")
            print(json.dumps(bad, indent=2))
            assert bad.get("is_error") is True
            assert "bogus_key" in bad["content"][0]["text"]

            rev_after_bad = await _revision(store, sid)
            print(f"revision after rejected call: {rev_after_bad} (must still be 1)")
            assert rev_after_bad == 1

            # Title must not have been touched by the rejected call.
            draft = ReportDraft.from_json(await store.load_draft(sid))
            assert draft.title == "Test report"

            # report_get still returns the intact draft.
            got = await _report_get({})
            assert got.get("is_error") is not True
        finally:
            tmp.cleanup()

    asyncio.run(run())


if __name__ == "__main__":
    test_alias_sections_accepted_as_upsert_sections()
    test_truly_unknown_key_rejected_no_draft_created()
    test_good_call_succeeds_then_bad_call_does_not_bump()
    print("\nAll report_update validation tests passed.")
