"""Production batch processing engine for the EE Toolbox ingestion pipeline.

Wraps the existing classify -> extract -> embed -> store pipeline with:
  - Configurable concurrency via ThreadPoolExecutor
  - Per-stage retry with exponential backoff
  - Rate limiting for LLM and embedding API calls
  - Atomic progress/state file writes for crash-safe resumability
  - Mock mode for infrastructure testing without API costs
  - Comprehensive batch reporting with taxonomy distribution

Usage::

    from pipeline.batch_processor import BatchProcessor, BatchConfig

    config = BatchConfig(llm_concurrency=2, mock_mode=True)
    processor = BatchProcessor(config)
    report = processor.process_batch(items, resume=False)

All public methods are synchronous.  Thread safety is achieved through
``threading.Lock`` for shared counters and file writes.
"""

import json
import logging
import os
import random
import tempfile
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pipeline.classifier import classify_relevance
from pipeline.config import DEFAULT_MODEL
from pipeline.embeddings import embed_tool_fields
from pipeline.extractor import extract_metadata
from pipeline.ingest import _derive_cgspace_id, _store_tool
from pipeline.taxonomy import (
    DOMAINS,
    GEOGRAPHY,
    PILLARS,
    STAGES,
    TARGET_USERS,
    TYPES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class BatchConfig:
    """Configuration for a batch processing run.

    Attributes:
        batch_id: Unique identifier for this run.  Auto-generated from the
            current timestamp when left empty.
        max_retries: Maximum number of retry attempts per pipeline stage.
        retry_base_delay: Base delay in seconds for exponential backoff
            (actual delay = base * 2^attempt).
        llm_delay: Minimum seconds between consecutive LLM API calls
            (classify or extract).  Prevents rate-limit errors.
        embedding_delay: Minimum seconds between consecutive embedding API
            calls.
        llm_concurrency: Number of worker threads processing items in
            parallel.  Each worker runs the full classify->extract->embed->
            store pipeline for one item.  Values 1-5 are supported.
        model: LLM model identifier forwarded to classifier and extractor.
        mock_mode: When True, replace all API calls with fast synthetic
            responses.  Useful for testing infrastructure at scale.
        state_dir: Directory for progress, state, and report files.
            Defaults to the ``pipeline/`` package directory.
        progress_file: Path to the progress JSON file.  Auto-derived from
            *state_dir* when empty.
        state_file: Path to the batch state JSON file.  Auto-derived from
            *state_dir* when empty.
        report_file: Path to the batch report JSON file.  Auto-derived from
            *state_dir* when empty.
    """

    batch_id: str = ""
    max_retries: int = 3
    retry_base_delay: float = 2.0
    llm_delay: float = 1.0
    embedding_delay: float = 0.2
    llm_concurrency: int = 1
    model: str = DEFAULT_MODEL
    mock_mode: bool = False
    state_dir: str = ""
    progress_file: str = ""
    state_file: str = ""
    report_file: str = ""

    def __post_init__(self) -> None:
        if not self.batch_id:
            self.batch_id = "batch-" + datetime.now(timezone.utc).strftime(
                "%Y%m%d-%H%M%S"
            )
        if not self.state_dir:
            self.state_dir = _PIPELINE_DIR
        if not self.progress_file:
            self.progress_file = os.path.join(self.state_dir, "progress.json")
        if not self.state_file:
            self.state_file = os.path.join(self.state_dir, "batch_state.json")
        if not self.report_file:
            self.report_file = os.path.join(self.state_dir, "batch_report.json")
        # Clamp concurrency to a safe range.
        self.llm_concurrency = max(1, min(5, self.llm_concurrency))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _atomic_write_json(path: str, data: Any) -> None:
    """Write *data* as JSON to *path* atomically.

    Writes to a temporary file in the same directory, then renames to the
    target path.  This guarantees that readers never see a partially-written
    file, even if the process is killed mid-write.
    """
    directory = os.path.dirname(path) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=directory)
        with os.fdopen(fd, "w") as fp:
            json.dump(data, fp, indent=2, default=str)
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# BatchProcessor
# ---------------------------------------------------------------------------


class BatchProcessor:
    """Production-grade batch processor for the EE Toolbox ingestion pipeline.

    Processes a list of item dicts through the full classify -> extract ->
    embed -> store pipeline with retry logic, rate limiting, progress
    tracking, resumability, and optional mock mode.

    Thread safety:
        Shared mutable state (counters, file writes, rate-limit timestamps)
        is protected by ``threading.Lock`` instances so that multiple worker
        threads can operate concurrently.

    Example::

        processor = BatchProcessor(BatchConfig(mock_mode=True))
        report = processor.process_batch(items)
        print(f"Stored: {report['stored']}, Failed: {report['failed']}")
    """

    def __init__(self, config: BatchConfig) -> None:
        self.config = config

        # -- Shared mutable state (protected by _state_lock) --
        import threading

        self._state_lock = threading.Lock()
        self._progress_lock = threading.Lock()
        self._rate_lock = threading.Lock()

        # Counters
        self._processed = 0
        self._stored = 0
        self._skipped = 0
        self._failed = 0

        # Per-item results: cgspace_id -> result dict
        self._results: dict[str, dict] = {}
        self._processed_ids: set[str] = set()

        # Latency tracking: stage_name -> list of latency_ms values
        self._latencies: dict[str, list[int]] = defaultdict(list)

        # Retry tracking
        self._total_retries = 0
        self._retries_by_stage: dict[str, int] = defaultdict(int)

        # Failure reasons: reason_string -> count
        self._failure_reasons: dict[str, int] = defaultdict(int)

        # Taxonomy distribution tracking
        self._taxonomy_dist: dict[str, dict[str, int]] = {
            "pillars": defaultdict(int),
            "domains": defaultdict(int),
            "types": defaultdict(int),
            "stages": defaultdict(int),
        }

        # Rate limiting timestamps
        self._last_llm_call_time: float = 0.0
        self._last_embedding_call_time: float = 0.0

        # Batch metadata
        self._started_at: Optional[str] = None
        self._current_item: str = ""
        self._total_items: int = 0
        self._interrupted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_batch(
        self, items: list[dict], resume: bool = False
    ) -> dict:
        """Process a list of documents through the full ingestion pipeline.

        Args:
            items: List of item dicts, each with at least ``title`` and
                typically ``abstract``, ``authors``, ``date``, ``url``,
                ``doc_type``, and optionally ``full_text``.
            resume: When True, load the previous ``batch_state.json`` and
                skip items whose ``cgspace_id`` has already been processed.

        Returns:
            A report dict with summary statistics, latency breakdowns,
            retry stats, failure reasons, and taxonomy distributions.
            The same dict is also written to ``batch_report.json``.
        """
        self._total_items = len(items)
        self._started_at = datetime.now(timezone.utc).isoformat()

        mode_label = "MOCK" if self.config.mock_mode else "LIVE"
        logger.info(
            "Starting batch %s (%s mode): %d items, concurrency=%d",
            self.config.batch_id,
            mode_label,
            self._total_items,
            self.config.llm_concurrency,
        )
        print(
            f"\n{'='*70}\n"
            f"Batch {self.config.batch_id} ({mode_label} mode)\n"
            f"Items: {self._total_items} | Concurrency: {self.config.llm_concurrency} | "
            f"Retries: {self.config.max_retries}\n"
            f"{'='*70}"
        )

        # -- Resume: load previous state --
        if resume:
            self._load_state()
            already = len(self._processed_ids)
            if already > 0:
                logger.info(
                    "Resuming: %d items already processed, skipping them.",
                    already,
                )
                print(f"Resuming from previous run: {already} items already processed.")

        # -- Filter to unprocessed items --
        work_items = []
        for item in items:
            cgspace_id = _derive_cgspace_id(item)
            if cgspace_id not in self._processed_ids:
                work_items.append(item)

        remaining = len(work_items)
        if remaining == 0:
            logger.info("All items already processed.  Nothing to do.")
            print("All items already processed. Nothing to do.")
            return self._generate_report()

        logger.info("Processing %d remaining items.", remaining)
        print(f"Processing {remaining} remaining items...\n")

        # -- Write initial progress --
        self._write_progress("running")

        # -- Process with thread pool --
        try:
            with ThreadPoolExecutor(
                max_workers=self.config.llm_concurrency
            ) as executor:
                futures = {
                    executor.submit(self._process_single_item, item): item
                    for item in work_items
                }

                for future in as_completed(futures):
                    if self._interrupted:
                        break
                    item = futures[future]
                    title = item.get("title", "(untitled)")
                    try:
                        future.result()
                    except Exception as exc:
                        # This should not happen because _process_single_item
                        # catches all exceptions internally, but guard anyway.
                        logger.exception(
                            "Unexpected error processing '%s'", title
                        )
                        cgspace_id = _derive_cgspace_id(item)
                        with self._state_lock:
                            self._failed += 1
                            self._processed += 1
                            self._processed_ids.add(cgspace_id)
                            self._results[cgspace_id] = {
                                "status": "failed",
                                "error": str(exc),
                            }
                            reason = type(exc).__name__ + ": " + str(exc)[:100]
                            self._failure_reasons[reason] += 1
                        self._write_progress("running")
                        self._write_state()

        except KeyboardInterrupt:
            self._interrupted = True
            logger.warning(
                "KeyboardInterrupt received. Saving state and generating "
                "partial report..."
            )
            print(
                "\n\nInterrupted!  Saving state and generating partial report..."
            )
            self._write_progress("interrupted")
            self._write_state()

        # -- Final writes --
        final_status = "interrupted" if self._interrupted else "completed"
        self._write_progress(final_status)
        self._write_state()
        report = self._generate_report()
        _atomic_write_json(self.config.report_file, report)

        # -- Summary --
        print(
            f"\n{'='*70}\n"
            f"Batch {self.config.batch_id} {final_status.upper()}\n"
            f"Stored: {self._stored} | Skipped: {self._skipped} | "
            f"Failed: {self._failed} | "
            f"Total processed: {self._processed}/{self._total_items}\n"
            f"Report: {self.config.report_file}\n"
            f"{'='*70}\n"
        )

        return report

    # ------------------------------------------------------------------
    # Single-item processing
    # ------------------------------------------------------------------

    def _process_single_item(self, item: dict) -> None:
        """Run the full pipeline for one item.  Never raises.

        Stages:
            1. Classify relevance (with retry)
            2. Extract metadata (with retry) -- skipped if irrelevant
            3. Generate embedding (with retry, non-fatal)
            4. Store in database (with retry) -- skipped in mock mode

        Updates shared counters and writes progress/state after completion.
        """
        title = item.get("title", "(untitled)")
        cgspace_id = _derive_cgspace_id(item)
        item_start = time.time()

        with self._state_lock:
            self._current_item = title

        stage_latencies: dict[str, int] = {}
        embedding = None
        extraction: Optional[dict] = None

        try:
            # ---- Stage 1: Classify ----
            classify_start = time.time()
            if self.config.mock_mode:
                rel = self._mock_classify(item)
            else:
                self._wait_for_llm_rate_limit()
                rel = self._retry_with_backoff(
                    classify_relevance,
                    "classify",
                    title,
                    title=item.get("title", ""),
                    authors=item.get("authors", ""),
                    date=item.get("date", ""),
                    abstract=item.get("abstract", ""),
                    doc_type=item.get("doc_type", ""),
                    url=item.get("url", ""),
                    model=self.config.model,
                )
            classify_ms = int((time.time() - classify_start) * 1000)
            stage_latencies["classify"] = classify_ms

            # Check for classification error.
            if rel.get("error"):
                raise RuntimeError(f"Classification error: {rel['error']}")

            # If irrelevant, mark skipped and return.
            if not rel.get("relevant"):
                total_ms = int((time.time() - item_start) * 1000)
                stage_latencies["total"] = total_ms
                with self._state_lock:
                    self._skipped += 1
                    self._processed += 1
                    self._processed_ids.add(cgspace_id)
                    self._results[cgspace_id] = {
                        "status": "skipped_irrelevant",
                        "confidence": rel.get("confidence", 0.0),
                    }
                    self._latencies["classify"].append(classify_ms)
                    self._latencies["total"].append(total_ms)

                logger.info(
                    "Skipped (irrelevant, conf=%.2f): %s",
                    rel.get("confidence", 0.0),
                    title,
                )
                print(
                    f"  [{self._processed}/{self._total_items}] "
                    f"{title[:60]} -> skipped_irrelevant "
                    f"(conf={rel.get('confidence', 0.0):.2f}, {total_ms}ms)"
                )
                self._write_progress("running")
                self._write_state()
                return

            # ---- Stage 2: Extract metadata ----
            extract_start = time.time()
            if self.config.mock_mode:
                extraction = self._mock_extract(item)
            else:
                self._wait_for_llm_rate_limit()
                extraction = self._retry_with_backoff(
                    extract_metadata,
                    "extract",
                    title,
                    title=item.get("title", ""),
                    authors=item.get("authors", ""),
                    date=item.get("date", ""),
                    abstract=item.get("abstract", ""),
                    full_text=item.get("full_text", ""),
                    model=self.config.model,
                )
            extract_ms = int((time.time() - extract_start) * 1000)
            stage_latencies["extract"] = extract_ms

            # ---- Stage 3: Generate embedding (non-fatal) ----
            embed_ms = 0
            if self.config.mock_mode:
                embedding = None
                embed_ms = random.randint(1, 5)
            else:
                try:
                    embed_start = time.time()
                    self._wait_for_embedding_rate_limit()
                    embedding = self._retry_with_backoff(
                        embed_tool_fields,
                        "embed",
                        title,
                        title=item.get("title", ""),
                        summary=extraction.get("summary", ""),
                        what_it_does=extraction.get("what_it_does", ""),
                        when_to_use_it=extraction.get("when_to_use_it", ""),
                        who_its_for=extraction.get("who_its_for", ""),
                    )
                    embed_ms = int((time.time() - embed_start) * 1000)
                except Exception as exc:
                    embed_ms = int((time.time() - embed_start) * 1000)
                    logger.warning(
                        "Embedding failed for '%s' (non-fatal): %s",
                        title,
                        exc,
                    )
            stage_latencies["embed"] = embed_ms

            # ---- Stage 4: Store in database ----
            store_ms = 0
            tool_id: Optional[str] = None
            if self.config.mock_mode:
                tool_id = str(uuid.uuid4())
                store_ms = random.randint(1, 5)
            else:
                store_start = time.time()
                tool_id = self._retry_with_backoff(
                    _store_tool,
                    "store",
                    title,
                    item,
                    extraction,
                    rel.get("confidence", 0.0),
                    embedding,
                )
                store_ms = int((time.time() - store_start) * 1000)
            stage_latencies["store"] = store_ms

            # ---- Success ----
            total_ms = int((time.time() - item_start) * 1000)
            stage_latencies["total"] = total_ms

            with self._state_lock:
                self._stored += 1
                self._processed += 1
                self._processed_ids.add(cgspace_id)
                self._results[cgspace_id] = {
                    "status": "stored",
                    "tool_id": tool_id,
                }
                for stage_name, ms in stage_latencies.items():
                    self._latencies[stage_name].append(ms)
                # Track taxonomy distribution from extraction.
                if extraction:
                    self._update_taxonomy_distribution(extraction)

            logger.info(
                "Stored tool %s for '%s' (%dms)", tool_id, title, total_ms
            )
            print(
                f"  [{self._processed}/{self._total_items}] "
                f"{title[:60]} -> stored "
                f"(conf={rel.get('confidence', 0.0):.2f}, {total_ms}ms)"
            )

        except Exception as exc:
            total_ms = int((time.time() - item_start) * 1000)
            stage_latencies["total"] = total_ms

            with self._state_lock:
                self._failed += 1
                self._processed += 1
                self._processed_ids.add(cgspace_id)
                self._results[cgspace_id] = {
                    "status": "failed",
                    "error": str(exc),
                }
                for stage_name, ms in stage_latencies.items():
                    self._latencies[stage_name].append(ms)
                reason = str(exc)[:120]
                self._failure_reasons[reason] += 1

            logger.error(
                "Failed processing '%s': %s (%dms)", title, exc, total_ms
            )
            print(
                f"  [{self._processed}/{self._total_items}] "
                f"{title[:60]} -> FAILED: {str(exc)[:80]} ({total_ms}ms)"
            )

        # Always write progress and state after each item.
        self._write_progress("running")
        self._write_state()

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    def _retry_with_backoff(
        self,
        func: Any,
        stage_name: str,
        item_title: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call *func* with exponential-backoff retry.

        Args:
            func: Callable to invoke.
            stage_name: Human-readable stage name for logging (e.g.
                ``"classify"``, ``"extract"``).
            item_title: Title of the item being processed, for log context.
            *args, **kwargs: Forwarded to *func*.

        Returns:
            The return value of *func* on the first successful call.

        Raises:
            The exception from the last attempt if all retries are exhausted.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt == self.config.max_retries:
                    raise
                delay = self.config.retry_base_delay * (2 ** attempt)
                logger.warning(
                    "Retry %d/%d for %s on '%s': %s. Waiting %.1fs...",
                    attempt + 1,
                    self.config.max_retries,
                    stage_name,
                    item_title,
                    exc,
                    delay,
                )
                with self._state_lock:
                    self._total_retries += 1
                    self._retries_by_stage[stage_name] += 1
                time.sleep(delay)
        # Should not be reached, but satisfy type checker.
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _wait_for_llm_rate_limit(self) -> None:
        """Block until enough time has elapsed since the last LLM call."""
        with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_llm_call_time
            if elapsed < self.config.llm_delay:
                wait = self.config.llm_delay - elapsed
                time.sleep(wait)
            self._last_llm_call_time = time.time()

    def _wait_for_embedding_rate_limit(self) -> None:
        """Block until enough time has elapsed since the last embedding call."""
        with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_embedding_call_time
            if elapsed < self.config.embedding_delay:
                wait = self.config.embedding_delay - elapsed
                time.sleep(wait)
            self._last_embedding_call_time = time.time()

    # ------------------------------------------------------------------
    # Mock implementations
    # ------------------------------------------------------------------

    def _mock_classify(self, item: dict) -> dict:
        """Return a synthetic classification result for mock mode."""
        time.sleep(random.uniform(0.01, 0.05))
        return {
            "relevant": random.random() > 0.3,
            "confidence": round(random.uniform(0.5, 0.99), 4),
            "reasoning": "Mock classification",
            "latency_ms": random.randint(100, 500),
            "error": None,
        }

    def _mock_extract(self, item: dict) -> dict:
        """Return a synthetic extraction result for mock mode."""
        time.sleep(random.uniform(0.01, 0.05))
        pillars_list = list(PILLARS)
        domains_list = list(DOMAINS)
        types_list = list(TYPES)
        stages_list = list(STAGES)
        target_users_list = list(TARGET_USERS)
        geography_list = list(GEOGRAPHY)

        return {
            "pillars": random.sample(
                pillars_list, k=random.randint(1, min(3, len(pillars_list)))
            ),
            "domains": random.sample(
                domains_list, k=random.randint(1, min(2, len(domains_list)))
            ),
            "type": random.choice(types_list),
            "stage": random.choice(stages_list),
            "target_users": random.sample(
                target_users_list,
                k=random.randint(1, min(3, len(target_users_list))),
            ),
            "geography": random.sample(
                geography_list,
                k=random.randint(1, min(2, len(geography_list))),
            ),
            "summary": f"Mock summary for: {item.get('title', 'untitled')}",
            "what_it_does": "Provides a mock analytical framework.",
            "when_to_use_it": "When testing the batch processing pipeline.",
            "who_its_for": "Pipeline developers and testers.",
            "_warnings": [],
            "_latency_ms": random.randint(100, 500),
        }

    # ------------------------------------------------------------------
    # Taxonomy distribution tracking
    # ------------------------------------------------------------------

    def _update_taxonomy_distribution(self, extraction: dict) -> None:
        """Update taxonomy counters from a successful extraction.

        Must be called while holding ``_state_lock``.
        """
        for pillar in extraction.get("pillars", []):
            self._taxonomy_dist["pillars"][pillar] += 1
        for domain in extraction.get("domains", []):
            self._taxonomy_dist["domains"][domain] += 1
        tool_type = extraction.get("type")
        if tool_type:
            self._taxonomy_dist["types"][tool_type] += 1
        stage = extraction.get("stage")
        if stage:
            self._taxonomy_dist["stages"][stage] += 1

    # ------------------------------------------------------------------
    # Progress / state persistence
    # ------------------------------------------------------------------

    def _write_progress(self, status: str) -> None:
        """Write the current progress snapshot to ``progress.json``."""
        with self._progress_lock:
            now = datetime.now(timezone.utc).isoformat()
            elapsed = 0.0
            if self._started_at:
                try:
                    start_dt = datetime.fromisoformat(self._started_at)
                    elapsed = (
                        datetime.now(timezone.utc) - start_dt
                    ).total_seconds()
                except (ValueError, TypeError):
                    pass

            # Compute derived metrics.
            total_latencies = self._latencies.get("total", [])
            avg_latency_ms = (
                int(sum(total_latencies) / len(total_latencies))
                if total_latencies
                else 0
            )

            items_per_minute = 0.0
            estimated_remaining = 0.0
            if elapsed > 0 and self._processed > 0:
                items_per_minute = round(
                    self._processed / (elapsed / 60.0), 2
                )
                remaining_items = self._total_items - self._processed
                if items_per_minute > 0:
                    estimated_remaining = round(
                        remaining_items / items_per_minute * 60.0, 1
                    )

            percent = round(
                (self._processed / self._total_items * 100.0)
                if self._total_items > 0
                else 0.0,
                1,
            )

            progress = {
                "batch_id": self.config.batch_id,
                "status": status,
                "started_at": self._started_at,
                "updated_at": now,
                "total": self._total_items,
                "processed": self._processed,
                "stored": self._stored,
                "skipped": self._skipped,
                "failed": self._failed,
                "percent_complete": percent,
                "avg_latency_ms": avg_latency_ms,
                "estimated_remaining_seconds": estimated_remaining,
                "current_item": self._current_item,
                "items_per_minute": items_per_minute,
            }

            try:
                _atomic_write_json(self.config.progress_file, progress)
            except Exception as exc:
                logger.error("Failed to write progress file: %s", exc)

    def _write_state(self) -> None:
        """Write the batch state to ``batch_state.json`` for resumability."""
        with self._state_lock:
            state = {
                "batch_id": self.config.batch_id,
                "config": asdict(self.config),
                "processed_ids": sorted(self._processed_ids),
                "results": dict(self._results),
            }

        try:
            _atomic_write_json(self.config.state_file, state)
        except Exception as exc:
            logger.error("Failed to write state file: %s", exc)

    def _load_state(self) -> None:
        """Load previously saved batch state for resumability.

        Populates ``_processed_ids``, ``_results``, and the summary
        counters so that ``process_batch`` can skip already-handled items.
        """
        path = self.config.state_file
        if not os.path.exists(path):
            logger.info("No previous state file found at %s", path)
            return

        try:
            with open(path, "r") as fp:
                state = json.load(fp)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Could not load state file %s: %s.  Starting fresh.", path, exc
            )
            return

        # Restore processed IDs and per-item results.
        self._processed_ids = set(state.get("processed_ids", []))
        self._results = state.get("results", {})

        # Recompute counters from results.
        for cgspace_id, result in self._results.items():
            status = result.get("status", "")
            if status == "stored":
                self._stored += 1
            elif status == "skipped_irrelevant":
                self._skipped += 1
            elif status == "failed":
                self._failed += 1
        self._processed = len(self._processed_ids)

        logger.info(
            "Loaded state: %d processed (%d stored, %d skipped, %d failed)",
            self._processed,
            self._stored,
            self._skipped,
            self._failed,
        )

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _generate_report(self) -> dict:
        """Build and return the final batch report dict.

        The report includes summary counts, per-stage latency averages,
        retry statistics, failure reasons, and taxonomy distributions.
        """
        completed_at = datetime.now(timezone.utc).isoformat()
        elapsed = 0.0
        if self._started_at:
            try:
                start_dt = datetime.fromisoformat(self._started_at)
                elapsed = round(
                    (datetime.now(timezone.utc) - start_dt).total_seconds(), 2
                )
            except (ValueError, TypeError):
                pass

        # Compute average latencies per stage.
        avg_latency: dict[str, int] = {}
        for stage in ("classify", "extract", "embed", "store", "total"):
            values = self._latencies.get(stage, [])
            avg_latency[stage] = (
                int(sum(values) / len(values)) if values else 0
            )

        # Success rate: stored / (stored + failed), excluding skipped.
        denominator = self._stored + self._failed
        success_rate = (
            round(self._stored / denominator, 4) if denominator > 0 else 0.0
        )

        report = {
            "batch_id": self.config.batch_id,
            "started_at": self._started_at,
            "completed_at": completed_at,
            "elapsed_seconds": elapsed,
            "total_items": self._total_items,
            "stored": self._stored,
            "skipped_irrelevant": self._skipped,
            "failed": self._failed,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
            "retry_stats": {
                "total_retries": self._total_retries,
                "retries_by_stage": dict(self._retries_by_stage),
            },
            "failure_reasons": dict(self._failure_reasons),
            "taxonomy_distribution": {
                key: dict(counts)
                for key, counts in self._taxonomy_dist.items()
            },
        }

        return report
