"""
find_missing_tools.py
=====================
Identifies tools in batch-results-parsed.json that are missing from seed.sql.

The original seed.sql contains 92 tools — all records with content_richness in
(Rich, Moderate) or extraction_confidence != Low. The 8 records with
content_richness in (Error, Minimal) AND extraction_confidence == Low were
excluded from the initial seed.

This script:
1. Loads batch-results-parsed.json (100 records)
2. Identifies the 8 low-quality / missing records
3. Generates INSERT statements written to data/migrations/001_add_missing_8_tools.sql
4. Prints an audit summary

Usage:
    python3 data/scripts/find_missing_tools.py
"""

import json
import re
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent
BATCH_FILE = DATA_DIR / "batch-results-parsed.json"
SEED_FILE = DATA_DIR / "seed.sql"
OUTPUT_FILE = DATA_DIR / "migrations" / "001_add_missing_8_tools.sql"

# ---------------------------------------------------------------------------
# Pillar name mapping: batch JSON → DB canonical names (matching seed.sql)
# ---------------------------------------------------------------------------
PILLAR_MAP = {
    "M&E & Learning": "Monitoring, Evaluation and Learning",
    "Gender Equality & Social Inclusion": "Gender Equality and Social Inclusion",
    "Policy & Regulatory": "Policy and Regulatory",
    "Digital": "Digital and Financial Services",
    "Market Systems": "Market Systems",
    "Scaling Innovation": "Scaling Innovation",
    "Climate Resilience": "Climate Resilience",
    "Financial Services": "Digital and Financial Services",
}

# Resource type mapping
TYPE_MAP = {
    "Guidelines": "Guidelines",
    "Case Study": "Case Study",
    "Report": "Report",
    "Tool": "Tool",
    "Presentation": "Presentation",
    "Other": "Other",
    "Training Manual": "Training Manual",
}

# Development stage mapping
STAGE_MAP = {
    "Not Determinable": "Prototype",
    "Widely Deployed": "Widely Deployed",
    "Pilot": "Pilot",
    "Conceptual": "Conceptual",
    "Prototype": "Prototype",
}


def pg_escape(s: str) -> str:
    """Escape a string for PostgreSQL single-quoted literals."""
    return s.replace("'", "''")


def pg_array(items: list) -> str:
    """Format a Python list as a PostgreSQL text array literal."""
    if not items:
        return "NULL"
    escaped = [f'"{pg_escape(v)}"' for v in items]
    return "'{" + ",".join(escaped) + "}'"


def map_pillars(raw: list) -> list:
    result = []
    for p in raw:
        mapped = PILLAR_MAP.get(p, p)
        if mapped not in result:
            result.append(mapped)
    return result


def build_insert(record: dict) -> str:
    rc = record.get("_result_code", "")
    title_meta = record.get("_title_meta", "")
    overview = record.get("overview", "") or ""
    sc = record.get("source_and_citation", {}) or {}
    cls = record.get("classification", {}) or {}
    wif = record.get("who_its_for", {}) or {}
    where = record.get("where_it_applies", {}) or {}
    rt = record.get("resource_type", {}) or {}
    kt = record.get("key_takeaways", []) or []

    # Title: use _title_meta (most complete), truncate at 200 chars
    title = (title_meta or overview[:120]).strip()
    if len(title) > 200:
        title = title[:197] + "..."

    # Summary: use overview, fall back to key_takeaways joined
    if overview and not overview.startswith("Unable to provide"):
        summary = overview.strip()
    elif kt:
        summary = " ".join(str(k) for k in kt[:3]).strip()
    else:
        summary = f"Resource from CGSpace: {rc}"

    # What it does
    how = record.get("how_it_works", {}) or {}
    what_it_does = how.get("approach_summary") or ""
    # Don't use audience text as what_it_does

    # When to use it
    when_to_use = ""  # Not well-represented in low-quality records

    # Who it's for
    audience_raw = wif.get("primary_audience") or ""
    # Blank out non-informative audience values
    non_informative = {"not determinable from available information", "not determinable"}
    who_its_for = "" if audience_raw.lower() in non_informative else audience_raw

    # Pillars
    raw_pillars = cls.get("ee_pillars", []) or []
    pillars = map_pillars(raw_pillars)

    # Domains
    domains = cls.get("thematic_areas", []) or []

    # Type
    raw_type = rt.get("primary_type", "Other")
    tool_type = TYPE_MAP.get(raw_type, "Other")

    # Stage
    raw_stage = cls.get("development_stage", "Prototype")
    stage = STAGE_MAP.get(raw_stage, "Prototype")

    # Target users (re-use audience as array, only if informative)
    audience = wif.get("primary_audience", "") or ""
    non_informative = {"not determinable from available information", "not determinable"}
    target_users = [audience] if (audience and len(audience) < 100 and audience.lower() not in non_informative) else []

    # Geography
    countries = where.get("countries", []) or []
    regions = where.get("regions", []) or []
    geography = list(dict.fromkeys(countries + regions))  # deduplicate, preserve order

    # Source info
    source_url = sc.get("source_url") or f"https://hdl.handle.net/{rc}"
    source_org = sc.get("publishing_organization") or ""

    # Generate a deterministic UUID from the result code so re-runs are idempotent
    tool_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://hdl.handle.net/{rc}"))
    cgspace_id = rc

    # Relevance score: 0.70 (below the "good" tools which default to 0.80)
    relevance_score = "0.70"

    def sql_str(s: str) -> str:
        if s is None or s == "":
            return "NULL"
        return f"'{pg_escape(s)}'"

    lines = [
        f"-- {rc}: {title[:80]}",
        f"INSERT INTO public.tools (",
        f"    id, title, summary, what_it_does, when_to_use_it, who_its_for,",
        f"    pillars, domains, type, stage, target_users, geography,",
        f"    authors, date_published, source_url, source_organization,",
        f"    cover_image_url, embedding, average_rating, rating_count, view_count,",
        f"    cgspace_id, relevance_score, is_visible, created_at, updated_at",
        f") VALUES (",
        f"    '{tool_id}',",
        f"    {sql_str(title)},",
        f"    {sql_str(summary)},",
        f"    {sql_str(what_it_does) if what_it_does else 'NULL'},",
        f"    NULL,",  # when_to_use_it
        f"    {sql_str(who_its_for) if who_its_for else 'NULL'},",
        f"    {pg_array(pillars)},",
        f"    {pg_array(domains)},",
        f"    {sql_str(tool_type)},",
        f"    {sql_str(stage)},",
        f"    {pg_array(target_users)},",
        f"    {pg_array(geography)},",
        f"    NULL,",   # authors
        f"    NULL,",   # date_published
        f"    {sql_str(source_url)},",
        f"    {sql_str(source_org) if source_org else 'NULL'},",
        f"    NULL,",   # cover_image_url
        f"    NULL,",   # embedding
        f"    0, 0, 0,",  # average_rating, rating_count, view_count
        f"    {sql_str(cgspace_id)},",
        f"    {relevance_score},",
        f"    true,",
        f"    now(), now()",
        f") ON CONFLICT (cgspace_id) DO NOTHING;",
    ]
    return "\n".join(lines)


def main():
    with open(BATCH_FILE) as f:
        batch = json.load(f)

    # Identify the 8 missing records
    missing = [
        r for r in batch
        if (
            r.get("extraction_metadata", {}).get("content_richness") in ("Error", "Minimal")
            and r.get("extraction_metadata", {}).get("extraction_confidence") == "Low"
        )
    ]

    print(f"Total batch records : {len(batch)}")
    print(f"Missing (low quality): {len(missing)}")
    print()
    for r in missing:
        print(f"  {r['_result_code']} | {r['_title_meta'][:80]}")

    # Build migration SQL
    header = """\
-- Migration 001: Add 8 tools missing from initial seed
-- Generated by: data/scripts/find_missing_tools.py
-- Date: 2026-06-12
-- Source: data/batch-results-parsed.json (100 records) → data/seed.sql (92 rows)
--
-- These 8 records had content_richness in (Error, Minimal) + extraction_confidence == Low
-- and were excluded from the original seed. They are added here for completeness.
-- Embeddings are NULL — they will be generated on first use by the embedding pipeline.
-- All statements use ON CONFLICT (cgspace_id) DO NOTHING for idempotency.
--
-- IDs are deterministic UUIDs (uuid5 of the CGSpace handle URL).
"""

    inserts = []
    for record in missing:
        inserts.append(build_insert(record))

    sql_content = header + "\n\n" + "\n\n".join(inserts) + "\n"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write(sql_content)

    print(f"\nMigration SQL written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
