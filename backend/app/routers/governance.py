"""Content governance router.

Public endpoints (no auth):
    POST /api/governance/proposals     -- submit a content change proposal

Admin-gated endpoints (Bearer token required):
    GET  /api/admin/governance/proposals          -- list proposals (filter by status/tool_id)
    GET  /api/admin/governance/proposals/{id}     -- get single proposal detail
    POST /api/admin/governance/proposals/{id}/approve  -- approve and apply to live tool
    POST /api/admin/governance/proposals/{id}/reject   -- reject with notes
"""

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.admin import verify_admin_token

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

# ---- Public: submit proposal ----

class ProposalSubmitRequest(BaseModel):
    tool_id: _uuid.UUID | None = None          # None = new-tool proposal
    proposal_type: str = "edit"                # "edit" | "new_tool"
    submitted_by: str | None = None
    provenance: str | None = None              # e.g. "cgspace:10568-100101" | "form" | "manual"
    proposed_fields: dict[str, Any]            # REQUIRED — the fields being proposed


class ProposalSubmitResponse(BaseModel):
    id: _uuid.UUID
    status: str
    submitted_at: datetime


# ---- Admin: list / detail ----

class ProposalRead(BaseModel):
    id: _uuid.UUID
    tool_id: _uuid.UUID | None
    proposal_type: str
    submitted_by: str | None
    provenance: str | None
    proposed_fields: dict[str, Any]
    status: str
    reviewer_notes: str | None
    reviewed_by: str | None
    submitted_at: datetime
    reviewed_at: datetime | None


class ProposalListResponse(BaseModel):
    total: int
    proposals: list[ProposalRead]


# ---- Admin: approve / reject ----

class ApproveRequest(BaseModel):
    reviewed_by: str | None = None


class RejectRequest(BaseModel):
    reviewer_notes: str | None = None
    reviewed_by: str | None = None


# ---------------------------------------------------------------------------
# Allowed tool field names that a proposal may update.
# Prevents injection via arbitrary JSONB keys into the dynamic UPDATE.
# ---------------------------------------------------------------------------
_ALLOWED_TOOL_FIELDS = {
    "title", "summary", "what_it_does", "when_to_use_it", "who_its_for",
    "pillars", "domains", "type", "stage", "target_users", "geography",
    "authors", "date_published", "source_url", "source_organization",
    "cover_image_url", "cgspace_id", "relevance_score", "is_visible",
}


# ---------------------------------------------------------------------------
# POST /api/governance/proposals  (PUBLIC — no auth)
# ---------------------------------------------------------------------------

@router.post("/governance/proposals", response_model=ProposalSubmitResponse, status_code=201)
async def submit_proposal(
    body: ProposalSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a content proposal for a tool (or for a brand-new tool entry).

    No authentication required — anyone can submit. Proposals enter the queue
    with status='pending' and do NOT affect the live catalog until approved
    by an admin.
    """
    if not body.proposed_fields:
        raise HTTPException(status_code=422, detail="proposed_fields must not be empty")

    # Validate that tool_id exists if provided
    if body.tool_id is not None:
        check = await db.execute(
            text("SELECT id FROM tools WHERE id = :tool_id"),
            {"tool_id": str(body.tool_id)},
        )
        if check.fetchone() is None:
            raise HTTPException(status_code=404, detail="Tool not found")

    import json
    result = await db.execute(
        text(
            """
            INSERT INTO content_proposals
                (tool_id, proposal_type, submitted_by, provenance, proposed_fields)
            VALUES
                (:tool_id, :proposal_type, :submitted_by, :provenance, :proposed_fields::jsonb)
            RETURNING id, status, submitted_at
            """
        ),
        {
            "tool_id": str(body.tool_id) if body.tool_id else None,
            "proposal_type": body.proposal_type,
            "submitted_by": body.submitted_by,
            "provenance": body.provenance,
            "proposed_fields": json.dumps(body.proposed_fields),
        },
    )
    row = result.mappings().fetchone()
    await db.commit()

    return ProposalSubmitResponse(
        id=row["id"],
        status=row["status"],
        submitted_at=row["submitted_at"],
    )


# ---------------------------------------------------------------------------
# GET /api/admin/governance/proposals  (ADMIN)
# ---------------------------------------------------------------------------

@router.get("/admin/governance/proposals", response_model=ProposalListResponse)
async def list_proposals(
    status: str | None = Query(None, description="Filter by status: pending|approved|rejected"),
    tool_id: _uuid.UUID | None = Query(None, description="Filter by tool UUID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List content proposals. Filter by status and/or tool_id."""
    conditions = []
    params: dict = {}

    if status:
        conditions.append("status = :status")
        params["status"] = status

    if tool_id:
        conditions.append("tool_id = :tool_id")
        params["tool_id"] = str(tool_id)

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM content_proposals {where_sql}"),
        params,
    )
    total = count_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(
            f"""
            SELECT id, tool_id, proposal_type, submitted_by, provenance,
                   proposed_fields, status, reviewer_notes, reviewed_by,
                   submitted_at, reviewed_at
            FROM content_proposals
            {where_sql}
            ORDER BY submitted_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    rows = result.mappings().all()

    proposals = [
        ProposalRead(
            id=row["id"],
            tool_id=row["tool_id"],
            proposal_type=row["proposal_type"],
            submitted_by=row["submitted_by"],
            provenance=row["provenance"],
            proposed_fields=row["proposed_fields"],
            status=row["status"],
            reviewer_notes=row["reviewer_notes"],
            reviewed_by=row["reviewed_by"],
            submitted_at=row["submitted_at"],
            reviewed_at=row["reviewed_at"],
        )
        for row in rows
    ]

    return ProposalListResponse(total=total, proposals=proposals)


# ---------------------------------------------------------------------------
# GET /api/admin/governance/proposals/{proposal_id}  (ADMIN)
# ---------------------------------------------------------------------------

@router.get("/admin/governance/proposals/{proposal_id}", response_model=ProposalRead)
async def get_proposal(
    proposal_id: _uuid.UUID,
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Get a single proposal by ID."""
    result = await db.execute(
        text(
            """
            SELECT id, tool_id, proposal_type, submitted_by, provenance,
                   proposed_fields, status, reviewer_notes, reviewed_by,
                   submitted_at, reviewed_at
            FROM content_proposals
            WHERE id = :proposal_id
            """
        ),
        {"proposal_id": str(proposal_id)},
    )
    row = result.mappings().fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return ProposalRead(
        id=row["id"],
        tool_id=row["tool_id"],
        proposal_type=row["proposal_type"],
        submitted_by=row["submitted_by"],
        provenance=row["provenance"],
        proposed_fields=row["proposed_fields"],
        status=row["status"],
        reviewer_notes=row["reviewer_notes"],
        reviewed_by=row["reviewed_by"],
        submitted_at=row["submitted_at"],
        reviewed_at=row["reviewed_at"],
    )


# ---------------------------------------------------------------------------
# POST /api/admin/governance/proposals/{proposal_id}/approve  (ADMIN)
# ---------------------------------------------------------------------------

@router.post("/admin/governance/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: _uuid.UUID,
    body: ApproveRequest,
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Approve a proposal — apply proposed_fields to the live tool and stamp last_verified_at.

    Only fields listed in _ALLOWED_TOOL_FIELDS are applied. Status is set to
    'approved' and the tool row is updated atomically.
    """
    # Fetch the proposal
    result = await db.execute(
        text(
            """
            SELECT id, tool_id, proposed_fields, status
            FROM content_proposals
            WHERE id = :proposal_id
            """
        ),
        {"proposal_id": str(proposal_id)},
    )
    row = result.mappings().fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if row["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Proposal is already '{row['status']}' — only pending proposals can be approved",
        )

    if row["tool_id"] is None:
        raise HTTPException(
            status_code=422,
            detail="Cannot approve a 'new_tool' proposal via this endpoint — create the tool via POST /api/admin/tools first",
        )

    # Sanitize proposed_fields — only allow known columns
    proposed = row["proposed_fields"]
    safe_fields = {k: v for k, v in proposed.items() if k in _ALLOWED_TOOL_FIELDS}

    if not safe_fields:
        raise HTTPException(
            status_code=422,
            detail="No valid tool fields in proposed_fields — nothing to apply",
        )

    # Build dynamic UPDATE
    set_clauses = [f"{field} = :{field}" for field in safe_fields]
    set_clauses.append("last_verified_at = now()")
    set_clauses.append("updated_at = now()")
    set_sql = ", ".join(set_clauses)

    update_params = {**safe_fields, "tool_id": str(row["tool_id"])}

    await db.execute(
        text(f"UPDATE tools SET {set_sql} WHERE id = :tool_id"),
        update_params,
    )

    # Mark the proposal approved
    reviewer = body.reviewed_by or _user
    await db.execute(
        text(
            """
            UPDATE content_proposals
            SET status = 'approved',
                reviewed_by = :reviewed_by,
                reviewed_at = now()
            WHERE id = :proposal_id
            """
        ),
        {"proposal_id": str(proposal_id), "reviewed_by": reviewer},
    )
    await db.commit()

    # Return the updated tool + proposal summary
    tool_result = await db.execute(
        text(
            """
            SELECT id, title, summary, last_verified_at, updated_at
            FROM tools WHERE id = :tool_id
            """
        ),
        {"tool_id": str(row["tool_id"])},
    )
    tool_row = tool_result.mappings().fetchone()

    return {
        "proposal_id": str(proposal_id),
        "status": "approved",
        "tool_id": str(row["tool_id"]),
        "fields_applied": list(safe_fields.keys()),
        "tool_title": tool_row["title"] if tool_row else None,
        "last_verified_at": tool_row["last_verified_at"].isoformat() if tool_row and tool_row["last_verified_at"] else None,
    }


# ---------------------------------------------------------------------------
# POST /api/admin/governance/proposals/{proposal_id}/reject  (ADMIN)
# ---------------------------------------------------------------------------

@router.post("/admin/governance/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: _uuid.UUID,
    body: RejectRequest,
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposal. The tool row is NOT modified."""
    result = await db.execute(
        text("SELECT id, status FROM content_proposals WHERE id = :proposal_id"),
        {"proposal_id": str(proposal_id)},
    )
    row = result.mappings().fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if row["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Proposal is already '{row['status']}'",
        )

    reviewer = body.reviewed_by or _user
    await db.execute(
        text(
            """
            UPDATE content_proposals
            SET status = 'rejected',
                reviewer_notes = :reviewer_notes,
                reviewed_by = :reviewed_by,
                reviewed_at = now()
            WHERE id = :proposal_id
            """
        ),
        {
            "proposal_id": str(proposal_id),
            "reviewer_notes": body.reviewer_notes,
            "reviewed_by": reviewer,
        },
    )
    await db.commit()

    return {
        "proposal_id": str(proposal_id),
        "status": "rejected",
        "reviewer_notes": body.reviewer_notes,
    }
