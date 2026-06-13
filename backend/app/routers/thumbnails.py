"""Admin-gated AI-thumbnail pipeline router (C6 Wave B / Thread 3).

A BUDGET-CONTROLLED, REVIEWABLE pipeline (Jose feedback item 7):

  1. Operator triggers a SMALL batch from the admin Thumbnails tab
     -> POST /api/admin/thumbnails/generate  (enqueues 'requested' jobs)
  2. The CONTROLLED agent/CI path (NOT long-lived backend write-IAM) fulfils
     pending jobs: it reads them, calls the synapsis image_generate MCP tool,
     uploads PNGs to thumbnails-staging/<cgspace_id>.png, and reports back
     -> GET  /api/admin/thumbnails/pending   (controlled path reads work)
     -> POST /api/admin/thumbnails/staged     (controlled path reports results)
  3. Operator reviews the staged grid and decides per tool
     -> GET  /api/admin/thumbnails            (review grid)
     -> POST /api/admin/thumbnails/{cgspace_id}/approve  (promote + cover_image_url)
     -> POST /api/admin/thumbnails/{cgspace_id}/reject
     -> POST /api/admin/thumbnails/{cgspace_id}/regenerate

Storage convention (deterministic, decision Q4): a dedicated public-read bucket
``ee-toolbox-thumbnails-<acct>`` with live key ``thumbnails/<cgspace_id>.png``
and staging key ``thumbnails-staging/<cgspace_id>.png``. The frontend derives
the live URL from cgspace_id with an onError letter-avatar fallback, so no
tools.ts regeneration is needed; approve also sets cover_image_url in the DB.

All endpoints reuse ``verify_admin_token``. The backend NEVER writes to S3 (no
new long-lived IAM); the staging->live promotion is done by the controlled CI
publish path. Purely additive.
"""

from __future__ import annotations

import logging
import os
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.routers.admin import verify_admin_token
from app.services.thumbnail_prompts import build_thumbnail_prompt
from persistence.durable import (
    approve_thumbnail,
    enqueue_thumbnail_jobs,
    get_unthumbnailed_tools,
    list_thumbnail_jobs,
    mark_thumbnail_failed,
    mark_thumbnail_staged,
    reject_thumbnail,
)

logger = logging.getLogger("ee.thumbnails")

router = APIRouter()

# Bucket + URL convention. Region/account come from env (set in the container);
# defaults are the mgmt-account values so the deterministic URL is correct even
# if the env var is unset.
_THUMB_BUCKET = os.environ.get("THUMBNAILS_BUCKET", "ee-toolbox-thumbnails-919959486181")
_THUMB_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")

# Cap per batch — budget guard (small batches per Jose).
_MAX_BATCH = 10


def _s3_url(key: str) -> str:
    return f"https://{_THUMB_BUCKET}.s3.{_THUMB_REGION}.amazonaws.com/{key}"


def _live_key(cgspace_id: str) -> str:
    return f"thumbnails/{cgspace_id}.png"


def _staging_key(cgspace_id: str) -> str:
    return f"thumbnails-staging/{cgspace_id}.png"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GenerateBatchRequest(BaseModel):
    # Either an explicit set of cgspace_ids, or "next N unthumbnailed tools".
    cgspace_ids: list[str] | None = None
    count: int = 5


class StagedReport(BaseModel):
    cgspace_id: str
    cost_usd: float | None = None
    error: str | None = None


class StagedBatchReport(BaseModel):
    results: list[StagedReport]


# ---------------------------------------------------------------------------
# 1. Operator: trigger a batch (enqueue 'requested' jobs)
# ---------------------------------------------------------------------------

@router.post("/admin/thumbnails/generate")
async def generate_batch(
    body: GenerateBatchRequest,
    user: str = Depends(verify_admin_token),
) -> dict:
    """Enqueue a SMALL batch of thumbnail-generation jobs (budget guard).

    Returns the batch_id, the enqueued tools, and each tool's templated prompt.
    Generation itself is performed by the controlled agent/CI path; this only
    records intent (no image generation, no S3 writes happen here).
    """
    count = max(1, min(int(body.count or 5), _MAX_BATCH))

    if body.cgspace_ids:
        if len(body.cgspace_ids) > _MAX_BATCH:
            raise HTTPException(
                status_code=400,
                detail=f"Batch too large (max {_MAX_BATCH} per budget guard).",
            )
        # Fetch metadata for the explicit ids (only those still un-thumbnailed
        # are eligible; but allow explicit ids through with whatever metadata).
        pool = await get_unthumbnailed_tools(limit=1000)
        by_id = {t["cgspace_id"]: t for t in pool}
        tools = [by_id[c] for c in body.cgspace_ids if c in by_id]
    else:
        tools = await get_unthumbnailed_tools(limit=count)

    if not tools:
        return {"batch_id": None, "enqueued": 0, "tools": [], "note": "no eligible tools"}

    batch_id = f"batch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{_uuid.uuid4().hex[:6]}"

    enriched = []
    for t in tools:
        prompt = build_thumbnail_prompt(
            title=t.get("title"),
            type_=t.get("type"),
            pillars=t.get("pillars"),
            domains=t.get("domains"),
            summary=t.get("summary"),
        )
        enriched.append(
            {
                "cgspace_id": t["cgspace_id"],
                "tool_title": t.get("title"),
                "prompt": prompt,
            }
        )

    enqueued = await enqueue_thumbnail_jobs(
        batch_id=batch_id, tools=enriched, requested_by=user
    )

    return {
        "batch_id": batch_id,
        "enqueued": enqueued,
        "bucket": _THUMB_BUCKET,
        "tools": [
            {
                "cgspace_id": e["cgspace_id"],
                "tool_title": e["tool_title"],
                "prompt": e["prompt"],
                "staging_key": _staging_key(e["cgspace_id"]),
                "live_key": _live_key(e["cgspace_id"]),
            }
            for e in enriched
        ],
    }


# ---------------------------------------------------------------------------
# 2. Controlled agent/CI path: read pending work + report staged results
# ---------------------------------------------------------------------------

@router.get("/admin/thumbnails/pending")
async def pending_jobs(_user: str = Depends(verify_admin_token)) -> dict:
    """Pending ('requested') jobs for the controlled generation path to fulfil.

    Each item carries the templated prompt and the exact S3 keys to upload to.
    """
    jobs = await list_thumbnail_jobs(status="requested")
    return {
        "bucket": _THUMB_BUCKET,
        "region": _THUMB_REGION,
        "pending": [
            {
                "cgspace_id": j["cgspace_id"],
                "tool_title": j["tool_title"],
                "prompt": j["prompt"],
                "staging_key": _staging_key(j["cgspace_id"]),
                "staging_url": _s3_url(_staging_key(j["cgspace_id"])),
            }
            for j in jobs
        ],
    }


@router.post("/admin/thumbnails/staged")
async def report_staged(
    body: StagedBatchReport,
    _user: str = Depends(verify_admin_token),
) -> dict:
    """Controlled path reports which tools were staged (or failed)."""
    staged, failed = 0, 0
    for r in body.results:
        if r.error:
            await mark_thumbnail_failed(cgspace_id=r.cgspace_id, error=r.error)
            failed += 1
        else:
            sk = _staging_key(r.cgspace_id)
            await mark_thumbnail_staged(
                cgspace_id=r.cgspace_id,
                staging_key=sk,
                staging_url=_s3_url(sk),
                cost_usd=r.cost_usd,
            )
            staged += 1
    return {"staged": staged, "failed": failed}


# ---------------------------------------------------------------------------
# 3. Operator: review grid + per-tool decisions
# ---------------------------------------------------------------------------

@router.get("/admin/thumbnails")
async def review_grid(
    status: str | None = Query(None),
    _user: str = Depends(verify_admin_token),
) -> dict:
    """Review grid: all thumbnail jobs (optionally filtered by status)."""
    jobs = await list_thumbnail_jobs(status=status)
    return {"bucket": _THUMB_BUCKET, "total": len(jobs), "jobs": jobs}


@router.post("/admin/thumbnails/{cgspace_id}/approve")
async def approve(cgspace_id: str, _user: str = Depends(verify_admin_token)) -> dict:
    """Approve a staged thumbnail: set cover_image_url to the LIVE url and flip
    the job to approved. The S3 staging->live copy is done by the controlled CI
    publish path (publish-thumbnails.yml); this records the live url + DB update.
    """
    lk = _live_key(cgspace_id)
    lu = _s3_url(lk)
    matched = await approve_thumbnail(cgspace_id=cgspace_id, live_key=lk, live_url=lu)
    return {
        "cgspace_id": cgspace_id,
        "status": "approved",
        "live_key": lk,
        "live_url": lu,
        "tool_updated": matched,
    }


@router.post("/admin/thumbnails/{cgspace_id}/reject")
async def reject(cgspace_id: str, _user: str = Depends(verify_admin_token)) -> dict:
    """Reject a staged thumbnail."""
    await reject_thumbnail(cgspace_id=cgspace_id)
    return {"cgspace_id": cgspace_id, "status": "rejected"}


@router.post("/admin/thumbnails/{cgspace_id}/regenerate")
async def regenerate(cgspace_id: str, user: str = Depends(verify_admin_token)) -> dict:
    """Re-enqueue a single tool for regeneration (back to 'requested')."""
    pool = await get_unthumbnailed_tools(limit=1000)
    by_id = {t["cgspace_id"]: t for t in pool}
    t = by_id.get(cgspace_id)
    # If the tool is not in the un-thumbnailed pool (e.g. it has a staged job),
    # still re-enqueue with whatever metadata we can recover from existing jobs.
    if t is None:
        jobs = await list_thumbnail_jobs()
        existing = next((j for j in jobs if j["cgspace_id"] == cgspace_id), None)
        prompt = existing["prompt"] if existing else None
        title = existing["tool_title"] if existing else None
        tools = [{"cgspace_id": cgspace_id, "tool_title": title, "prompt": prompt}]
    else:
        prompt = build_thumbnail_prompt(
            title=t.get("title"),
            type_=t.get("type"),
            pillars=t.get("pillars"),
            domains=t.get("domains"),
            summary=t.get("summary"),
        )
        tools = [
            {"cgspace_id": cgspace_id, "tool_title": t.get("title"), "prompt": prompt}
        ]

    batch_id = f"regen-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    await enqueue_thumbnail_jobs(batch_id=batch_id, tools=tools, requested_by=user)
    return {"cgspace_id": cgspace_id, "status": "requested", "batch_id": batch_id}
