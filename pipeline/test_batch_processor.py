"""Integration tests for the EE Toolbox batch processing pipeline.

Exercises all batch processing features in mock mode:
  - Batch processing with concurrency
  - Resumability from saved state
  - Progress tracking (progress.json)
  - Error handling and retry infrastructure
  - Report statistics and taxonomy distribution
  - Scale test (1,000 items)

Run as::

    python -m pipeline.test_batch_processor

Each test uses an isolated temporary directory for state files so tests
never interfere with each other or with production state.
"""

import json
import os
import shutil
import sys
import time
import traceback

from pipeline.batch_processor import BatchConfig, BatchProcessor

# ---------------------------------------------------------------------------
# Test item generator
# ---------------------------------------------------------------------------

TOPICS = [
    "Climate-Smart Agriculture Assessment",
    "Gender-Responsive Value Chain Analysis",
    "Participatory Monitoring Framework",
    "Digital Extension Service Platform",
    "Seed System Resilience Toolkit",
    "Market Access Scorecard",
    "Policy Coherence Evaluation Method",
    "Nutrition-Sensitive Irrigation Guide",
    "Farmer Organization Strengthening Manual",
    "Livestock Health Surveillance Scale",
]

DOC_TYPES = ["Framework", "Method", "Tool", "Guide", "Manual", "Toolkit", "Report"]


def make_test_items(n: int, prefix: str = "test") -> list[dict]:
    """Generate *n* simple test items for batch processing tests."""
    items = []
    for i in range(n):
        topic = TOPICS[i % len(TOPICS)]
        items.append(
            {
                "title": f"{topic} - Variant {i + 1}",
                "abstract": (
                    f"This document presents a {topic.lower()} for agricultural "
                    f"development. It provides practitioners with structured "
                    f"approaches for implementation. Developed through extensive "
                    f"field testing across multiple regions."
                ),
                "doc_type": DOC_TYPES[i % len(DOC_TYPES)],
                "authors": f"Author {i + 1}, CGIAR Research Center",
                "date": str(2015 + (i % 10)),
                "url": f"https://cgspace.cgiar.org/handle/10568/{50000 + i}",
                "cgspace_id": f"{prefix}-{i + 1:04d}",
            }
        )
    return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prepare_state_dir(path: str) -> None:
    """Remove *path* if it exists, then create it fresh."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def _load_json(path: str) -> dict:
    """Load and return a JSON file."""
    with open(path, "r") as fp:
        return json.load(fp)


def _section(title: str) -> None:
    """Print a clearly visible section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


# ---------------------------------------------------------------------------
# Test 1: Mock mode batch processing (50 items)
# ---------------------------------------------------------------------------


def test_1_mock_mode_batch() -> bool:
    """Process 50 items in mock mode and verify output files."""
    _section("TEST 1: Mock Mode Batch Processing (50 items)")
    state_dir = "/tmp/ee_batch_test_1"
    _prepare_state_dir(state_dir)

    items = make_test_items(50, prefix="mock50")

    config = BatchConfig(
        batch_id="test1-mock50",
        llm_concurrency=3,
        mock_mode=True,
        state_dir=state_dir,
    )
    processor = BatchProcessor(config)
    report = processor.process_batch(items)

    # -- Verify output files exist --
    progress_path = os.path.join(state_dir, "progress.json")
    state_path = os.path.join(state_dir, "batch_state.json")
    report_path = os.path.join(state_dir, "batch_report.json")

    for label, path in [
        ("progress.json", progress_path),
        ("batch_state.json", state_path),
        ("batch_report.json", report_path),
    ]:
        if not os.path.exists(path):
            print(f"  FAIL: {label} not found at {path}")
            return False
        print(f"  OK: {label} exists")

    # -- Verify counts --
    stored = report["stored"]
    skipped = report["skipped_irrelevant"]
    failed = report["failed"]
    total = report["total_items"]

    if stored + skipped + failed != total:
        print(
            f"  FAIL: stored({stored}) + skipped({skipped}) + failed({failed}) "
            f"!= total({total})"
        )
        return False
    print(f"  OK: stored({stored}) + skipped({skipped}) + failed({failed}) == total({total})")

    # -- Verify progress shows 100% --
    progress = _load_json(progress_path)
    if progress["percent_complete"] != 100.0:
        print(f"  FAIL: percent_complete is {progress['percent_complete']}, expected 100.0")
        return False
    print(f"  OK: progress shows 100% complete")

    if progress["status"] != "completed":
        print(f"  FAIL: progress status is '{progress['status']}', expected 'completed'")
        return False
    print(f"  OK: progress status is 'completed'")

    # -- Summary --
    print(f"\n  Summary: {total} items processed in mock mode")
    print(f"    Stored:  {stored}")
    print(f"    Skipped: {skipped}")
    print(f"    Failed:  {failed}")
    print(f"\n  PASS")
    return True


# ---------------------------------------------------------------------------
# Test 2: Resumability
# ---------------------------------------------------------------------------


def test_2_resumability() -> bool:
    """Verify that resume=True skips already-processed items."""
    _section("TEST 2: Resumability Test (30 items, two-phase)")
    state_dir = "/tmp/ee_batch_test_2"
    _prepare_state_dir(state_dir)

    all_items = make_test_items(30, prefix="resume-test")
    first_half = all_items[:15]

    # -- Phase A: Process the first 15 items --
    print("  Phase A: Processing first 15 items...")
    config_a = BatchConfig(
        batch_id="test2-resume",
        llm_concurrency=2,
        mock_mode=True,
        state_dir=state_dir,
    )
    processor_a = BatchProcessor(config_a)
    report_a = processor_a.process_batch(first_half, resume=False)

    processed_a = report_a["stored"] + report_a["skipped_irrelevant"] + report_a["failed"]
    if processed_a != 15:
        print(f"  FAIL: Phase A processed {processed_a} items, expected 15")
        return False
    print(f"  OK: Phase A processed {processed_a} items")

    # Verify state file has 15 processed IDs
    state = _load_json(os.path.join(state_dir, "batch_state.json"))
    if len(state["processed_ids"]) != 15:
        print(
            f"  FAIL: State file has {len(state['processed_ids'])} processed IDs, "
            f"expected 15"
        )
        return False
    print(f"  OK: State file has 15 processed IDs")

    # -- Phase B: Resume with all 30 items --
    print("\n  Phase B: Resuming with all 30 items (15 should be skipped)...")
    config_b = BatchConfig(
        batch_id="test2-resume",
        llm_concurrency=2,
        mock_mode=True,
        state_dir=state_dir,
    )
    processor_b = BatchProcessor(config_b)
    report_b = processor_b.process_batch(all_items, resume=True)

    # The total_items in report_b reflects all 30 passed in, but only the
    # new 15 should have been actually processed during this run.
    # The state file should now have all 30 processed IDs.
    state_b = _load_json(os.path.join(state_dir, "batch_state.json"))
    if len(state_b["processed_ids"]) != 30:
        print(
            f"  FAIL: After resume, state has {len(state_b['processed_ids'])} "
            f"processed IDs, expected 30"
        )
        return False
    print(f"  OK: After resume, state has 30 processed IDs")

    # Verify progress shows all 30 completed
    progress = _load_json(os.path.join(state_dir, "progress.json"))
    if progress["processed"] != 30:
        print(f"  FAIL: progress.processed is {progress['processed']}, expected 30")
        return False
    print(f"  OK: progress shows 30 items processed")

    if progress["status"] != "completed":
        print(f"  FAIL: progress status is '{progress['status']}', expected 'completed'")
        return False
    print(f"  OK: progress status is 'completed'")

    print(f"\n  PASS")
    return True


# ---------------------------------------------------------------------------
# Test 3: Progress tracking verification
# ---------------------------------------------------------------------------


def test_3_progress_tracking() -> bool:
    """Verify progress.json has all required fields with correct values."""
    _section("TEST 3: Progress Tracking Verification (20 items)")
    state_dir = "/tmp/ee_batch_test_3"
    _prepare_state_dir(state_dir)

    items = make_test_items(20, prefix="progress")

    config = BatchConfig(
        batch_id="test3-progress",
        llm_concurrency=2,
        mock_mode=True,
        state_dir=state_dir,
    )
    processor = BatchProcessor(config)
    processor.process_batch(items)

    progress_path = os.path.join(state_dir, "progress.json")
    if not os.path.exists(progress_path):
        print(f"  FAIL: progress.json not found")
        return False

    progress = _load_json(progress_path)

    # -- Check required fields --
    required_fields = [
        "batch_id",
        "status",
        "total",
        "processed",
        "stored",
        "skipped",
        "failed",
        "percent_complete",
        "items_per_minute",
        "estimated_remaining_seconds",
    ]
    missing = [f for f in required_fields if f not in progress]
    if missing:
        print(f"  FAIL: Missing fields in progress.json: {missing}")
        return False
    print(f"  OK: All {len(required_fields)} required fields present")

    # -- Verify status --
    if progress["status"] != "completed":
        print(f"  FAIL: status is '{progress['status']}', expected 'completed'")
        return False
    print(f"  OK: status is 'completed'")

    # -- Verify percent_complete --
    if progress["percent_complete"] != 100.0:
        print(f"  FAIL: percent_complete is {progress['percent_complete']}, expected 100.0")
        return False
    print(f"  OK: percent_complete is 100.0")

    # -- Verify processed == total --
    if progress["processed"] != progress["total"]:
        print(
            f"  FAIL: processed ({progress['processed']}) != total ({progress['total']})"
        )
        return False
    print(f"  OK: processed ({progress['processed']}) == total ({progress['total']})")

    # -- Verify items_per_minute is positive --
    if progress["items_per_minute"] <= 0:
        print(f"  FAIL: items_per_minute is {progress['items_per_minute']}, expected > 0")
        return False
    print(f"  OK: items_per_minute is {progress['items_per_minute']:.1f}")

    # -- Verify batch_id matches --
    if progress["batch_id"] != "test3-progress":
        print(f"  FAIL: batch_id is '{progress['batch_id']}', expected 'test3-progress'")
        return False
    print(f"  OK: batch_id matches")

    print(f"\n  PASS")
    return True


# ---------------------------------------------------------------------------
# Test 4: Error handling and retry infrastructure
# ---------------------------------------------------------------------------


def test_4_error_handling_retry() -> bool:
    """Verify retry infrastructure structures exist in the report."""
    _section("TEST 4: Error Handling and Retry Infrastructure (10 items)")
    state_dir = "/tmp/ee_batch_test_4"
    _prepare_state_dir(state_dir)

    items = make_test_items(10, prefix="retry")

    config = BatchConfig(
        batch_id="test4-retry",
        llm_concurrency=2,
        mock_mode=True,
        max_retries=3,
        retry_base_delay=1.0,
        state_dir=state_dir,
    )
    processor = BatchProcessor(config)
    report = processor.process_batch(items)

    # -- Verify retry_stats structure --
    if "retry_stats" not in report:
        print(f"  FAIL: 'retry_stats' not in report")
        return False
    print(f"  OK: retry_stats present in report")

    retry_stats = report["retry_stats"]
    if "total_retries" not in retry_stats:
        print(f"  FAIL: 'total_retries' not in retry_stats")
        return False
    print(f"  OK: total_retries = {retry_stats['total_retries']}")

    if "retries_by_stage" not in retry_stats:
        print(f"  FAIL: 'retries_by_stage' not in retry_stats")
        return False
    print(f"  OK: retries_by_stage present (value: {dict(retry_stats['retries_by_stage'])})")

    # -- Verify failure_reasons structure --
    if "failure_reasons" not in report:
        print(f"  FAIL: 'failure_reasons' not in report")
        return False
    print(f"  OK: failure_reasons present in report (value: {dict(report['failure_reasons'])})")

    # In mock mode retries should be 0 (no actual failures to retry)
    if retry_stats["total_retries"] != 0:
        print(
            f"  NOTE: total_retries is {retry_stats['total_retries']} "
            f"(expected 0 in mock mode, but not a failure)"
        )
    else:
        print(f"  OK: total_retries is 0 in mock mode (no real API errors to trigger retries)")

    # -- Verify counts are consistent --
    total = report["total_items"]
    stored = report["stored"]
    skipped = report["skipped_irrelevant"]
    failed = report["failed"]
    if stored + skipped + failed != total:
        print(
            f"  FAIL: stored({stored}) + skipped({skipped}) + failed({failed}) "
            f"!= total({total})"
        )
        return False
    print(f"  OK: stored + skipped + failed == total ({total})")

    print(f"\n  PASS")
    return True


# ---------------------------------------------------------------------------
# Test 5: Report statistics validation
# ---------------------------------------------------------------------------


def test_5_report_statistics() -> bool:
    """Validate batch_report.json fields and taxonomy distribution."""
    _section("TEST 5: Report Statistics Validation (100 items)")
    state_dir = "/tmp/ee_batch_test_5"
    _prepare_state_dir(state_dir)

    items = make_test_items(100, prefix="report")

    config = BatchConfig(
        batch_id="test5-report",
        llm_concurrency=4,
        mock_mode=True,
        state_dir=state_dir,
    )
    processor = BatchProcessor(config)
    report = processor.process_batch(items)

    # Also load from file to verify the file was written correctly
    report_path = os.path.join(state_dir, "batch_report.json")
    if not os.path.exists(report_path):
        print(f"  FAIL: batch_report.json not found")
        return False
    report_from_file = _load_json(report_path)

    # -- Verify total_items --
    if report_from_file["total_items"] != 100:
        print(
            f"  FAIL: total_items in file is {report_from_file['total_items']}, expected 100"
        )
        return False
    print(f"  OK: total_items is 100")

    # -- Verify success_rate --
    sr = report_from_file["success_rate"]
    if not (0.0 <= sr <= 1.0):
        print(f"  FAIL: success_rate is {sr}, expected between 0 and 1")
        return False
    print(f"  OK: success_rate is {sr:.4f}")

    # -- Verify avg_latency_ms has all required stages --
    avg_lat = report_from_file["avg_latency_ms"]
    required_stages = ["classify", "extract", "embed", "store", "total"]
    missing_stages = [s for s in required_stages if s not in avg_lat]
    if missing_stages:
        print(f"  FAIL: avg_latency_ms missing stages: {missing_stages}")
        return False
    print(f"  OK: avg_latency_ms has all stages: {required_stages}")
    for stage in required_stages:
        print(f"       {stage}: {avg_lat[stage]}ms")

    # -- Verify taxonomy_distribution --
    tax = report_from_file.get("taxonomy_distribution")
    if not tax:
        print(f"  FAIL: taxonomy_distribution missing from report")
        return False

    required_tax = ["pillars", "domains", "types", "stages"]
    missing_tax = [t for t in required_tax if t not in tax]
    if missing_tax:
        print(f"  FAIL: taxonomy_distribution missing categories: {missing_tax}")
        return False
    print(f"  OK: taxonomy_distribution has all categories: {required_tax}")

    # -- Verify elapsed_seconds --
    if report_from_file["elapsed_seconds"] <= 0:
        print(f"  FAIL: elapsed_seconds is {report_from_file['elapsed_seconds']}, expected > 0")
        return False
    print(f"  OK: elapsed_seconds is {report_from_file['elapsed_seconds']:.2f}s")

    # -- Print taxonomy distribution --
    print(f"\n  Taxonomy Distribution:")
    for category in required_tax:
        entries = tax[category]
        if entries:
            print(f"    {category}:")
            for key, count in sorted(entries.items(), key=lambda x: -x[1]):
                print(f"      {key}: {count}")
        else:
            print(f"    {category}: (empty)")

    print(f"\n  PASS")
    return True


# ---------------------------------------------------------------------------
# Test 6: Scale test (1,000 items)
# ---------------------------------------------------------------------------


def test_6_scale_test() -> bool:
    """Process 1,000 items in mock mode to prove scale handling."""
    _section("TEST 6: Scale Test (1,000 items)")
    state_dir = "/tmp/ee_batch_test_6"
    _prepare_state_dir(state_dir)

    print("  Generating 1,000 test items...")
    items = make_test_items(1000, prefix="scale")
    print(f"  Generated {len(items)} items")

    config = BatchConfig(
        batch_id="test6-scale1k",
        llm_concurrency=5,
        mock_mode=True,
        state_dir=state_dir,
    )
    processor = BatchProcessor(config)

    wall_start = time.time()
    report = processor.process_batch(items)
    wall_elapsed = time.time() - wall_start

    # -- Verify all 1,000 were processed --
    total = report["total_items"]
    stored = report["stored"]
    skipped = report["skipped_irrelevant"]
    failed = report["failed"]
    processed_sum = stored + skipped + failed

    if total != 1000:
        print(f"  FAIL: total_items is {total}, expected 1000")
        return False
    print(f"  OK: total_items is 1000")

    if processed_sum != 1000:
        print(
            f"  FAIL: stored({stored}) + skipped({skipped}) + failed({failed}) "
            f"= {processed_sum}, expected 1000"
        )
        return False
    print(f"  OK: all 1,000 items processed")

    # -- Verify state file --
    state_path = os.path.join(state_dir, "batch_state.json")
    state = _load_json(state_path)
    if len(state["processed_ids"]) != 1000:
        print(
            f"  FAIL: state has {len(state['processed_ids'])} processed IDs, expected 1000"
        )
        return False
    print(f"  OK: state file has 1,000 processed IDs")

    # -- Verify progress --
    progress_path = os.path.join(state_dir, "progress.json")
    progress = _load_json(progress_path)
    if progress["percent_complete"] != 100.0:
        print(f"  FAIL: percent_complete is {progress['percent_complete']}, expected 100.0")
        return False
    print(f"  OK: progress shows 100% complete")

    # -- Timing stats --
    items_per_minute = (1000 / wall_elapsed) * 60.0 if wall_elapsed > 0 else 0
    print(f"\n  Timing Stats:")
    print(f"    Wall-clock elapsed:   {wall_elapsed:.2f}s")
    print(f"    Reported elapsed:     {report['elapsed_seconds']:.2f}s")
    print(f"    Items/minute (wall):  {items_per_minute:.1f}")
    print(f"    Items/minute (report): {progress['items_per_minute']:.1f}")

    # -- Batch report summary --
    print(f"\n  Batch Report Summary:")
    print(f"    Stored:          {stored}")
    print(f"    Skipped:         {skipped}")
    print(f"    Failed:          {failed}")
    print(f"    Success rate:    {report['success_rate']:.4f}")
    print(f"    Total retries:   {report['retry_stats']['total_retries']}")

    avg_lat = report["avg_latency_ms"]
    print(f"\n  Average Latency (ms):")
    for stage in ("classify", "extract", "embed", "store", "total"):
        print(f"    {stage}: {avg_lat.get(stage, 'N/A')}")

    tax = report.get("taxonomy_distribution", {})
    if tax:
        print(f"\n  Taxonomy Distribution (top 3 per category):")
        for category in ("pillars", "domains", "types", "stages"):
            entries = tax.get(category, {})
            top = sorted(entries.items(), key=lambda x: -x[1])[:3]
            top_str = ", ".join(f"{k}: {v}" for k, v in top)
            print(f"    {category}: {top_str}")

    print(f"\n  PASS")
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all_tests() -> None:
    """Execute all six tests sequentially and print a final summary."""
    _section("EE Toolbox Batch Processor Integration Tests")
    print("  Running 6 integration tests in mock mode.\n")

    tests = [
        ("Test 1: Mock Mode Batch Processing (50 items)", test_1_mock_mode_batch),
        ("Test 2: Resumability (30 items)", test_2_resumability),
        ("Test 3: Progress Tracking (20 items)", test_3_progress_tracking),
        ("Test 4: Error Handling / Retry Infrastructure (10 items)", test_4_error_handling_retry),
        ("Test 5: Report Statistics (100 items)", test_5_report_statistics),
        ("Test 6: Scale Test (1,000 items)", test_6_scale_test),
    ]

    results: list[tuple[str, bool]] = []

    for name, test_fn in tests:
        try:
            passed = test_fn()
        except Exception:
            print(f"\n  EXCEPTION in {name}:")
            traceback.print_exc()
            passed = False
        results.append((name, passed))

    # -- Final summary --
    _section("FINAL SUMMARY")
    passed_count = 0
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if passed:
            passed_count += 1

    total_tests = len(results)
    print(f"\n  {passed_count}/{total_tests} tests passed.")

    if passed_count == total_tests:
        print("  All tests passed.\n")
    else:
        print(f"  {total_tests - passed_count} test(s) FAILED.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
