"""Pre-launch cleanup of clearly-labeled test/sentinel rows (durable Postgres).

WHY
---
Prior QA waves wrote test/sentinel rows into the durable Postgres business
store. They now skew the launch admin dashboard (token-usage cost, analytics
counts_by_event, survey average, governance proposal queue). This script
removes ONLY those clearly-labeled test/sentinel rows so the dashboard shows
real, launch-ready numbers.

SAFETY (read carefully)
-----------------------
- This is NOT a bulk wipe. Every DELETE targets an EXPLICIT, named sentinel
  marker or a KNOWN QA-test session id. Real data is never matched.
- The 5,000-KPI access-event count is 0/real and is left untouched — there is
  NO delete touching event_name = 'access_event'.
- Idempotent: re-running deletes nothing further (rows already gone).
- DRY RUN by default. Pass --apply to actually delete. Always prints
  before/after counts and the exact rows removed.
- Run through CI (ops-cleanup-sentinel-data.yml) against the live DB via the
  same async engine the app uses — never a manual ad-hoc DB edit.

The targeted sentinel/test identifiers below come from the pre-G2 QA report
and live verification on 2026-06-13/14.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import text


def _session_factory():
    """Return an async session factory.

    Preferred path: reuse the app's configured engine (app.database), so the
    connection uses exactly the same DATABASE_URL/SSL the live app uses.

    Fallback: when run via `docker exec` (a fresh process that did NOT inherit
    the container's runtime-exported DATABASE_URL), the caller passes the raw
    URL in EE_CLEANUP_DATABASE_URL. We build a dedicated engine from it with
    ssl=require in connect_args (RDS rejects unencrypted), avoiding any URL/shell
    quoting of the password.
    """
    raw = os.environ.get("EE_CLEANUP_DATABASE_URL", "").strip()
    if raw:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        # Strip any ssl/sslmode query param — we pass SSL via connect_args so a
        # password containing URL-special chars is never re-parsed.
        base = raw.split("?", 1)[0]
        engine = create_async_engine(
            base, echo=False, connect_args={"ssl": "require"}
        )
        return async_sessionmaker(bind=engine, expire_on_commit=False)

    from app.database import AsyncSessionLocal

    return AsyncSessionLocal


AsyncSessionLocal = _session_factory()

# --- Known sentinel / QA-test identifiers (explicit, never wildcards) --------

# Sentinel analytics events (clearly labeled, not real user events).
SENTINEL_EVENT_NAMES = [
    "wave_a_durable_pg_proof_20260613T205445Z",
]

# The sentinel pulse-survey row(s): "Wave A durable survey proof".
SENTINEL_SURVEY_SESSION_IDS = [
    "wave-a-survey-proof",
]

# Known QA-test assistant session UUIDs (the only sessions that exist pre-launch;
# all created by QA over wss://.../ws/challenge on 2026-06-13). Their
# assistant_session_started analytics events and token_usage rows are test data.
QA_TEST_SESSION_IDS = [
    "819b25aa-8dde-4b63-baa7-8c1f974b22a6",
    "8ed02235-6ed2-41c8-8c01-a49d8bf2820c",
    "60d407d2-7154-4147-b160-7a3a8c5f3f71",
    "8f8caccd-588e-41b7-a815-8f1d289594c6",
    "7c63485f-5868-4a92-8054-e6546ecd7a49",
    "3511d77d-55d5-4290-ba16-aafb933c9443",
]

# Test/demo governance proposals (deploy-probe sentinel, C7 governance demo,
# reject-tester, demo-restore). Targeted by explicit primary-key id.
TEST_PROPOSAL_IDS = [
    "f50f5f90-64b3-4af0-888d-854d0002b833",  # admin (demo-restore) — approved
    "46e46718-cde2-4117-bd88-3c4e66c3b121",  # reject-tester "SHOULD NOT BE APPLIED" — rejected
    "0b4477ed-bb88-4ede-85e7-374fa4c876a8",  # [C7 GOVERNANCE DEMO ...] — approved
    "3bc43a13-6ca1-42a9-871c-80efcbda65df",  # deploy-probe sentinel — pending
]


async def _scalar(db, sql: str, params: dict | None = None) -> int:
    res = await db.execute(text(sql), params or {})
    return int(res.scalar() or 0)


async def counts(db) -> dict[str, int]:
    return {
        "analytics_events": await _scalar(db, "SELECT COUNT(*) FROM analytics_events"),
        "token_usage": await _scalar(db, "SELECT COUNT(*) FROM token_usage"),
        "content_proposals": await _scalar(db, "SELECT COUNT(*) FROM content_proposals"),
        "pulse_survey_responses": await _scalar(
            db, "SELECT COUNT(*) FROM pulse_survey_responses"
        ),
        "access_event (PROTECTED)": await _scalar(
            db, "SELECT COUNT(*) FROM analytics_events WHERE event_name = 'access_event'"
        ),
    }


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        print("=== BEFORE counts ===")
        before = await counts(db)
        for k, v in before.items():
            print(f"  {k}: {v}")

        removed: dict[str, int] = {}

        # 1. Sentinel analytics events by explicit event_name.
        for name in SENTINEL_EVENT_NAMES:
            n = await _scalar(
                db,
                "SELECT COUNT(*) FROM analytics_events WHERE event_name = :n",
                {"n": name},
            )
            removed[f"analytics_events event_name={name}"] = n
            if apply and n:
                await db.execute(
                    text("DELETE FROM analytics_events WHERE event_name = :n"),
                    {"n": name},
                )

        # 2. Sentinel pulse-survey analytics events (event_name='pulse_survey',
        #    only the named sentinel session(s)).
        for sid in SENTINEL_SURVEY_SESSION_IDS:
            n = await _scalar(
                db,
                "SELECT COUNT(*) FROM analytics_events "
                "WHERE event_name = 'pulse_survey' AND session_id = :s",
                {"s": sid},
            )
            removed[f"analytics_events pulse_survey session_id={sid}"] = n
            if apply and n:
                await db.execute(
                    text(
                        "DELETE FROM analytics_events "
                        "WHERE event_name = 'pulse_survey' AND session_id = :s"
                    ),
                    {"s": sid},
                )

        # 3. QA-test assistant_session_started events for known QA sessions.
        for sid in QA_TEST_SESSION_IDS:
            n = await _scalar(
                db,
                "SELECT COUNT(*) FROM analytics_events "
                "WHERE event_name = 'assistant_session_started' AND session_id = :s",
                {"s": sid},
            )
            if n:
                removed[f"analytics_events assistant_session_started session_id={sid}"] = n
            if apply and n:
                await db.execute(
                    text(
                        "DELETE FROM analytics_events "
                        "WHERE event_name = 'assistant_session_started' AND session_id = :s"
                    ),
                    {"s": sid},
                )

        # 4. token_usage rows for known QA-test sessions.
        for sid in QA_TEST_SESSION_IDS:
            n = await _scalar(
                db,
                "SELECT COUNT(*) FROM token_usage WHERE session_id = :s",
                {"s": sid},
            )
            if n:
                removed[f"token_usage session_id={sid}"] = n
            if apply and n:
                await db.execute(
                    text("DELETE FROM token_usage WHERE session_id = :s"),
                    {"s": sid},
                )

        # 5. Test/demo governance proposals by explicit id.
        for pid in TEST_PROPOSAL_IDS:
            n = await _scalar(
                db,
                "SELECT COUNT(*) FROM content_proposals WHERE id = :p",
                {"p": pid},
            )
            removed[f"content_proposals id={pid}"] = n
            if apply and n:
                await db.execute(
                    text("DELETE FROM content_proposals WHERE id = :p"),
                    {"p": pid},
                )

        # 6. Legacy sentinel pulse_survey_responses rows (deprecated table).
        for sid in SENTINEL_SURVEY_SESSION_IDS:
            n = await _scalar(
                db,
                "SELECT COUNT(*) FROM pulse_survey_responses WHERE session_id = :s",
                {"s": sid},
            )
            removed[f"pulse_survey_responses session_id={sid}"] = n
            if apply and n:
                await db.execute(
                    text("DELETE FROM pulse_survey_responses WHERE session_id = :s"),
                    {"s": sid},
                )

        if apply:
            await db.commit()

        print()
        print("=== ROWS TARGETED (and removed if --apply) ===")
        total = 0
        for k, v in removed.items():
            total += v
            print(f"  {v:>4}  {k}")
        print(f"  ----  TOTAL: {total}")

        print()
        print(f"=== AFTER counts ({'APPLIED' if apply else 'DRY RUN — no changes'}) ===")
        after = await counts(db)
        for k, v in after.items():
            print(f"  {k}: {v}")

        # Hard safety assertion: never let access_event change.
        assert before["access_event (PROTECTED)"] == after["access_event (PROTECTED)"], (
            "access_event count changed — ABORT (this should be impossible)"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete (default is a dry run that only reports counts).",
    )
    args = ap.parse_args()
    asyncio.run(main(args.apply))
