"""End-to-end ingestion pipeline for the Enabling Environment Toolbox.

Takes raw document metadata (title, abstract, authors, etc.), classifies
relevance via the LLM, extracts structured metadata, and stores the result
in the tools table.  Every public function is synchronous and uses psycopg2
for database access, consistent with the rest of the pipeline package.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

from pipeline.classifier import classify_relevance
from pipeline.config import DATABASE_URL_SYNC, DEFAULT_MODEL
from pipeline.embeddings import embed_tool_fields
from pipeline.extractor import extract_metadata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class IngestResult:
    title: str
    status: str = "pending"  # "stored", "skipped_irrelevant", "failed"
    tool_id: Optional[str] = None
    relevance_confidence: float = 0.0
    relevance_reasoning: str = ""
    confidence_tier: str = ""  # "auto-publish", "review", "auto-reject"
    extraction_warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    stages_completed: list[str] = field(default_factory=list)
    total_latency_ms: int = 0


@dataclass
class BatchResult:
    total: int = 0
    stored: int = 0
    skipped: int = 0
    failed: int = 0
    results: list[IngestResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_cgspace_id(item: dict) -> str:
    """Produce a deterministic cgspace_id for a document.

    Priority:
    1. Explicit ``cgspace_id`` key in the item dict.
    2. Path extracted from a cgspace.cgiar.org URL.
    3. SHA-256 hash prefix of the title.
    """
    if item.get("cgspace_id"):
        return item["cgspace_id"]

    url = item.get("url", "")
    if "cgspace.cgiar.org" in url:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path:
            return path

    title = item.get("title", "")
    return "hash-" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:16]


def _parse_authors(authors_raw) -> list[str]:
    """Normalise an authors value into a Python list of strings."""
    if isinstance(authors_raw, list):
        return [a.strip() for a in authors_raw if a and a.strip()]
    if isinstance(authors_raw, str) and authors_raw.strip():
        return [a.strip() for a in authors_raw.split(",") if a.strip()]
    return []


def _parse_date(date_raw) -> Optional[date]:
    """Parse a date string into a ``datetime.date``, tolerating several formats."""
    if isinstance(date_raw, date):
        return date_raw
    if not date_raw or not isinstance(date_raw, str):
        return None
    date_str = date_raw.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date: %s", date_str)
    return None


def _ensure_list(value) -> list:
    """Guarantee that *value* is a Python list (for PostgreSQL ARRAY columns)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return [str(value)]


def _determine_visibility(confidence: float) -> tuple[bool, bool]:
    """Determine is_visible and needs_review based on confidence score.

    Returns:
        Tuple of (is_visible, needs_review)
    """
    if confidence >= 0.75:
        return True, False       # Auto-publish
    elif confidence >= 0.50:
        return True, True        # Flag for review
    else:
        return False, False      # Auto-reject


def _store_tool(
    item: dict,
    extraction: dict,
    relevance_score: float,
    embedding: list[float] | None = None,
    is_visible: bool = True,
    needs_review: bool = False,
) -> str:
    """Insert or upsert a tool record into the ``tools`` table.

    Uses ``ON CONFLICT (cgspace_id) DO UPDATE`` so that re-running the
    pipeline on the same document is idempotent.

    Args:
        item: Raw input item dict.
        extraction: Metadata extraction result dict.
        relevance_score: Confidence score from the relevance classifier.
        embedding: Optional 1536-dim embedding vector.  When provided it is
                   stored in the pgvector ``embedding`` column.
        is_visible: Whether the tool should be visible in the UI.
        needs_review: Whether the tool requires manual review before publishing.

    Returns:
        The UUID (as a string) of the inserted/updated row.
    """
    cgspace_id = _derive_cgspace_id(item)
    authors = _parse_authors(item.get("authors"))
    date_published = _parse_date(item.get("date"))

    # Build the fields dict from the extraction, stripping internal keys.
    pillars = _ensure_list(extraction.get("pillars"))
    domains = _ensure_list(extraction.get("domains"))
    tool_type = extraction.get("type") or None
    stage = extraction.get("stage") or None
    target_users = _ensure_list(extraction.get("target_users"))
    geography = _ensure_list(extraction.get("geography"))
    summary = extraction.get("summary") or None
    what_it_does = extraction.get("what_it_does") or None
    when_to_use_it = extraction.get("when_to_use_it") or None
    who_its_for = extraction.get("who_its_for") or None
    source_organization = item.get("source_organization") or None

    # Format embedding as a pgvector literal string, or None.
    embedding_literal = None
    if embedding is not None:
        embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"

    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tools (
                title, summary, what_it_does, when_to_use_it, who_its_for,
                pillars, domains, type, stage, target_users, geography,
                authors, date_published, source_url, source_organization,
                cgspace_id, relevance_score, is_visible, needs_review, embedding
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s::vector
            )
            ON CONFLICT (cgspace_id) DO UPDATE SET
                title            = EXCLUDED.title,
                summary          = EXCLUDED.summary,
                what_it_does     = EXCLUDED.what_it_does,
                when_to_use_it   = EXCLUDED.when_to_use_it,
                who_its_for      = EXCLUDED.who_its_for,
                pillars          = EXCLUDED.pillars,
                domains          = EXCLUDED.domains,
                type             = EXCLUDED.type,
                stage            = EXCLUDED.stage,
                target_users     = EXCLUDED.target_users,
                geography        = EXCLUDED.geography,
                authors          = EXCLUDED.authors,
                date_published   = EXCLUDED.date_published,
                source_url       = EXCLUDED.source_url,
                source_organization = EXCLUDED.source_organization,
                relevance_score  = EXCLUDED.relevance_score,
                is_visible       = EXCLUDED.is_visible,
                needs_review     = EXCLUDED.needs_review,
                embedding        = EXCLUDED.embedding,
                updated_at       = now()
            RETURNING id;
            """,
            (
                item.get("title", ""),
                summary,
                what_it_does,
                when_to_use_it,
                who_its_for,
                pillars,
                domains,
                tool_type,
                stage,
                target_users,
                geography,
                authors,
                date_published,
                item.get("url"),
                source_organization,
                cgspace_id,
                relevance_score,
                is_visible,
                needs_review,
                embedding_literal,
            ),
        )
        row = cur.fetchone()
        tool_id = str(row[0])
        conn.commit()
        cur.close()
        logger.info("Stored tool %s (cgspace_id=%s)", tool_id, cgspace_id)
        return tool_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_item(item: dict, model: str = DEFAULT_MODEL) -> IngestResult:
    """Run the full ingestion pipeline for a single document.

    Stages:
    1. Classify relevance  -- skip if irrelevant, fail on error
    2. Extract metadata    -- fail on error
    3. Store in database   -- fail on error

    Returns an :class:`IngestResult` that is always populated, never raises.
    """
    title = item.get("title", "(untitled)")
    result = IngestResult(title=title)
    start = time.time()

    # ---- Stage 1: Classify relevance ----
    try:
        logger.info("Classifying relevance for: %s", title)
        rel = classify_relevance(
            title=item.get("title", ""),
            authors=item.get("authors", ""),
            date=item.get("date", ""),
            abstract=item.get("abstract", ""),
            doc_type=item.get("doc_type", ""),
            url=item.get("url", ""),
            model=model,
        )
        result.relevance_confidence = rel.get("confidence", 0.0)
        result.relevance_reasoning = rel.get("reasoning", "")
        result.total_latency_ms += rel.get("latency_ms", 0)
        result.stages_completed.append("classify")

        if rel.get("error"):
            result.status = "failed"
            result.error = f"Classification error: {rel['error']}"
            logger.error("Classification failed for '%s': %s", title, rel["error"])
            return result

        if not rel.get("relevant"):
            result.status = "skipped_irrelevant"
            logger.info("Skipped (irrelevant, confidence=%.2f): %s", result.relevance_confidence, title)
            return result

    except Exception as exc:
        result.status = "failed"
        result.error = f"Classification exception: {exc}"
        logger.exception("Classification exception for '%s'", title)
        return result
    finally:
        result.total_latency_ms = int((time.time() - start) * 1000)

    # ---- Stage 2: Extract metadata ----
    try:
        logger.info("Extracting metadata for: %s", title)
        extraction = extract_metadata(
            title=item.get("title", ""),
            authors=item.get("authors", ""),
            date=item.get("date", ""),
            abstract=item.get("abstract", ""),
            full_text=item.get("full_text", ""),
            model=model,
        )
        result.extraction_warnings = extraction.get("_warnings", [])
        result.total_latency_ms += extraction.get("_latency_ms", 0)
        result.stages_completed.append("extract")

    except Exception as exc:
        result.status = "failed"
        result.error = f"Extraction exception: {exc}"
        result.total_latency_ms = int((time.time() - start) * 1000)
        logger.exception("Extraction exception for '%s'", title)
        return result

    # ---- Stage 3: Generate embedding ----
    embedding = None
    try:
        logger.info("Generating embedding for: %s", title)
        embedding = embed_tool_fields(
            title=item.get("title", ""),
            summary=extraction.get("summary", ""),
            what_it_does=extraction.get("what_it_does", ""),
            when_to_use_it=extraction.get("when_to_use_it", ""),
            who_its_for=extraction.get("who_its_for", ""),
        )
        result.stages_completed.append("embed")
        logger.info("Generated %d-dim embedding for '%s'", len(embedding), title)
    except Exception as exc:
        # Embedding failure is non-fatal — store the tool without it.
        logger.warning("Embedding failed for '%s' (will store without): %s", title, exc)

    # ---- Stage 4: Store in database ----
    try:
        logger.info("Storing tool: %s", title)
        is_visible, needs_review = _determine_visibility(result.relevance_confidence)
        tier_label = (
            "auto-publish" if is_visible and not needs_review
            else "review" if needs_review
            else "auto-reject"
        )
        result.confidence_tier = tier_label
        logger.info(
            "Confidence tier for '%s': %.2f -> %s",
            title, result.relevance_confidence, tier_label,
        )
        tool_id = _store_tool(
            item, extraction, result.relevance_confidence,
            embedding=embedding, is_visible=is_visible, needs_review=needs_review,
        )
        result.tool_id = tool_id
        result.status = "stored"
        result.stages_completed.append("store")
        logger.info("Stored tool %s for '%s'", tool_id, title)

    except Exception as exc:
        result.status = "failed"
        result.error = f"Storage exception: {exc}"
        logger.exception("Storage exception for '%s'", title)

    result.total_latency_ms = int((time.time() - start) * 1000)
    return result


def ingest_batch(items: list[dict], model: str = DEFAULT_MODEL) -> BatchResult:
    """Process a list of documents through the ingestion pipeline.

    Items are processed sequentially (LLM calls are rate-limited).  Progress
    is printed to stdout so operators can monitor long-running batches.

    Returns a :class:`BatchResult` with per-item results and summary counts.
    """
    batch = BatchResult(total=len(items))
    batch_start = time.time()

    for idx, item in enumerate(items, 1):
        title = item.get("title", "(untitled)")
        result = ingest_item(item, model=model)
        batch.results.append(result)

        if result.status == "stored":
            batch.stored += 1
        elif result.status == "skipped_irrelevant":
            batch.skipped += 1
        else:
            batch.failed += 1

        # Progress line
        conf_str = f"confidence: {result.relevance_confidence:.2f}"
        print(
            f"[{idx}/{batch.total}] {title} "
            f"-> {result.status} ({conf_str}, {result.total_latency_ms}ms)"
        )

    batch.elapsed_seconds = round(time.time() - batch_start, 2)
    return batch
