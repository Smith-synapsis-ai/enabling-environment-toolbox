"""Idempotent seed script for the agent store (Task A7).

Pre-loads the eight-pillar EE taxonomy and the tool-metadata schema into the
``seed_knowledge`` table (reference knowledge OUTSIDE the fixed Wave-3 memory
category list -- decision documented in
/Users/smithai/workspace/analysis/a7-persistence-decision.md). Seeded entries
surface through ``MemoryStore.recall`` / mcp__memory__memory_recall results
with source "seed_knowledge".

Run from backend/:  python3 scripts/seed_memory.py
Running it twice does not duplicate rows: each entry has a UNIQUE ``key`` and
is classified inserted / updated / unchanged.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from persistence.db import DB_PATH, ensure_db, get_db, utc_now_iso  # noqa: E402

# The canonical pillar names (master plan) with the abbreviated labels used in
# the retrieval catalog (pipeline/retrieval/artifacts/corpus.json) included as
# aliases so FTS recall matches either phrasing.
PILLARS: list[tuple[str, str, str]] = [
    (
        "pillar:policy-and-regulatory",
        "Policy and Regulatory",
        "Policy and Regulatory (catalog label: 'Policy & Regulatory'): the "
        "laws, policies, regulations and governance arrangements that shape "
        "whether agricultural innovations can be adopted and scaled. Covers "
        "policy analysis, regulatory reform and advocacy tools.",
    ),
    (
        "pillar:market-systems",
        "Market Systems",
        "Market Systems: the value chains, market actors and commercial "
        "incentives an innovation depends on. Covers market analysis, value "
        "chain development and private-sector engagement tools.",
    ),
    (
        "pillar:gender-equality-and-social-inclusion",
        "Gender Equality and Social Inclusion",
        "Gender Equality and Social Inclusion (catalog label: 'Gender "
        "Equality & Social Inclusion', GESI): ensuring women, youth and "
        "marginalized groups can access and benefit from innovations. Covers "
        "gender analysis, inclusion frameworks and equity-focused design "
        "tools.",
    ),
    (
        "pillar:monitoring-evaluation-and-learning",
        "Monitoring, Evaluation and Learning",
        "Monitoring, Evaluation and Learning (catalog label: 'M&E & "
        "Learning', MEL): tracking whether scaling efforts work and feeding "
        "evidence back into decisions. Covers indicator frameworks, "
        "evaluation designs and adaptive-learning tools.",
    ),
    (
        "pillar:digital",
        "Digital",
        "Digital: the digital infrastructure, data systems and digital "
        "services that enable innovations to reach users at scale. Covers "
        "digital advisory, data governance and ICT-for-agriculture tools.",
    ),
    (
        "pillar:financial-services",
        "Financial Services",
        "Financial Services: access to credit, insurance, savings and "
        "investment that farmers and agribusinesses need to adopt "
        "innovations. Covers rural finance, blended finance and risk-sharing "
        "tools.",
    ),
    (
        "pillar:climate-resilience",
        "Climate Resilience",
        "Climate Resilience: helping agricultural systems anticipate, absorb "
        "and adapt to climate shocks and stresses. Covers climate risk "
        "assessment, climate-smart agriculture and adaptation-planning "
        "tools.",
    ),
    (
        "pillar:scaling-innovations",
        "Scaling Innovations",
        "Scaling Innovations: the strategies, pathways and partnerships for "
        "taking a proven innovation from pilot to wide use. Covers scaling "
        "readiness, scaling strategy and partnership-brokering tools.",
    ),
]

TOOL_PROFILE_SCHEMA = (
    "key: schema:tool_profile -- Tool-metadata schema: every EE Toolbox tool "
    "profile carries the fields id (catalog identifier, e.g. '10568-100094'), "
    "title, pillars (one or more of the eight EE pillars), thematic_areas, "
    "countries, regions, resource_type, and summary (short description of "
    "what the tool does and when to use it)."
)


def _entries() -> list[tuple[str, str, str]]:
    """(key, kind, content) rows to seed."""
    rows = [
        (key, "pillar", content)
        for key, _name, content in PILLARS
    ]
    rows.append(("schema:tool_profile", "schema", TOOL_PROFILE_SCHEMA))
    return rows


async def seed(db_path=None) -> dict[str, int]:
    await ensure_db(db_path)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    now = utc_now_iso()
    async with get_db(db_path) as db:
        for key, kind, content in _entries():
            cursor = await db.execute(
                "SELECT id, kind, content FROM seed_knowledge WHERE key = ?",
                (key,),
            )
            row = await cursor.fetchone()
            if row is None:
                await db.execute(
                    """INSERT INTO seed_knowledge
                       (key, kind, content, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (key, kind, content, now, now),
                )
                counts["inserted"] += 1
                status = "inserted "
            elif row["kind"] != kind or row["content"] != content:
                await db.execute(
                    """UPDATE seed_knowledge
                       SET kind = ?, content = ?, updated_at = ?
                       WHERE key = ?""",
                    (kind, content, now, key),
                )
                counts["updated"] += 1
                status = "updated  "
            else:
                counts["unchanged"] += 1
                status = "unchanged"
            print(f"  [{status}] {key}")
        await db.commit()
        cursor = await db.execute("SELECT COUNT(*) AS n FROM seed_knowledge")
        total = (await cursor.fetchone())["n"]
    counts["total_rows"] = total
    return counts


def main() -> None:
    print(f"Seeding agent store: {DB_PATH}")
    counts = asyncio.run(seed())
    print(
        f"Done. inserted={counts['inserted']} updated={counts['updated']} "
        f"unchanged={counts['unchanged']} "
        f"(seed_knowledge total rows: {counts['total_rows']})"
    )


if __name__ == "__main__":
    main()
