"""CLI runner for the EE Toolbox batch processing pipeline.

Wraps :class:`~pipeline.batch_processor.BatchProcessor` with an argparse
interface, logging configuration, and input loading from file or on-the-fly
synthetic generation.

Usage::

    # Process items from a JSON file in mock mode
    python -m pipeline.run_batch --input items.json --mock

    # Generate 1000 synthetic items and process in mock mode
    python -m pipeline.run_batch --generate 1000 --mock --concurrency 3

    # Resume a previous batch with live API calls
    python -m pipeline.run_batch --input items.json --resume

    # See all options
    python -m pipeline.run_batch --help
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

from pipeline.batch_processor import BatchConfig, BatchProcessor
from pipeline.config import DEFAULT_MODEL


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(state_dir: str, batch_id: str) -> None:
    """Set up logging to both stdout and a log file in *state_dir*.

    The log file is named ``batch-<batch_id>.log`` and placed inside
    *state_dir*.  Both handlers use the same format.
    """
    os.makedirs(state_dir, exist_ok=True)
    log_file = os.path.join(state_dir, f"batch-{batch_id}.log")

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # Root logger configuration.
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates if re-invoked.
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Stdout handler.
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(stdout_handler)

    # File handler.
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(file_handler)

    logger.info("Logging to %s", log_file)


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def _load_items_from_file(path: str) -> list[dict]:
    """Load items from a JSON file.

    The file must contain a JSON array of item dicts.

    Raises:
        SystemExit: If the file does not exist or cannot be parsed.
    """
    if not os.path.exists(path):
        print(f"Error: input file not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(path, "r") as fp:
            items = json.load(fp)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading input file: {exc}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(items, list):
        print("Error: input file must contain a JSON array.", file=sys.stderr)
        sys.exit(2)

    return items


def _generate_items(count: int) -> list[dict]:
    """Generate synthetic items using the generate_test_data module.

    Raises:
        SystemExit: If generation fails.
    """
    try:
        from pipeline.generate_test_data import generate_items
    except ImportError as exc:
        print(
            f"Error: cannot import generate_test_data module: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)

    logger.info("Generating %d synthetic items...", count)
    items = generate_items(count)
    logger.info("Generated %d items.", len(items))
    return items


# ---------------------------------------------------------------------------
# Report printing
# ---------------------------------------------------------------------------


def _print_report(report: dict) -> None:
    """Print a human-readable summary of the batch report to stdout."""
    print(f"\n{'='*70}")
    print("BATCH REPORT SUMMARY")
    print(f"{'='*70}")
    print(f"  Batch ID:            {report.get('batch_id', 'N/A')}")
    print(f"  Started:             {report.get('started_at', 'N/A')}")
    print(f"  Completed:           {report.get('completed_at', 'N/A')}")
    print(f"  Elapsed:             {report.get('elapsed_seconds', 0):.1f}s")
    print(f"  Total items:         {report.get('total_items', 0)}")
    print(f"  Stored:              {report.get('stored', 0)}")
    print(f"  Skipped (irrelevant):{report.get('skipped_irrelevant', 0)}")
    print(f"  Failed:              {report.get('failed', 0)}")
    print(f"  Success rate:        {report.get('success_rate', 0):.1%}")

    # Latencies.
    avg_lat = report.get("avg_latency_ms", {})
    if avg_lat:
        print(f"\n  Average latencies (ms):")
        for stage in ("classify", "extract", "embed", "store", "total"):
            val = avg_lat.get(stage, 0)
            print(f"    {stage:12s}: {val:>8d}")

    # Retry stats.
    retry_stats = report.get("retry_stats", {})
    total_retries = retry_stats.get("total_retries", 0)
    if total_retries > 0:
        print(f"\n  Retries: {total_retries} total")
        for stage, count in retry_stats.get("retries_by_stage", {}).items():
            print(f"    {stage:12s}: {count}")

    # Failure reasons.
    failure_reasons = report.get("failure_reasons", {})
    if failure_reasons:
        print(f"\n  Failure reasons:")
        for reason, count in sorted(
            failure_reasons.items(), key=lambda x: -x[1]
        ):
            print(f"    [{count:>3d}] {reason[:80]}")

    # Taxonomy distribution.
    tax_dist = report.get("taxonomy_distribution", {})
    if tax_dist:
        for category in ("pillars", "domains", "types", "stages"):
            dist = tax_dist.get(category, {})
            if dist:
                print(f"\n  {category.title()} distribution:")
                for value, count in sorted(
                    dist.items(), key=lambda x: -x[1]
                ):
                    print(f"    {value:50s} {count:>4d}")

    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argparse parser."""
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.run_batch",
        description=(
            "Run the EE Toolbox batch processing pipeline.  Processes a set "
            "of CG Space items through classify -> extract -> embed -> store "
            "with retry, rate limiting, progress tracking, and resumability."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Process items from file in mock mode:\n"
            "  python -m pipeline.run_batch --input items.json --mock\n\n"
            "  # Generate and process 500 synthetic items:\n"
            "  python -m pipeline.run_batch --generate 500 --mock --concurrency 2\n\n"
            "  # Resume a previous run:\n"
            "  python -m pipeline.run_batch --input items.json --resume\n"
        ),
    )

    # Input source (mutually exclusive: --input or --generate).
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input",
        metavar="FILE",
        help="JSON file containing an array of items to process.",
    )
    input_group.add_argument(
        "--generate",
        metavar="N",
        type=int,
        help="Generate N synthetic items instead of reading from a file.",
    )

    # Processing controls.
    parser.add_argument(
        "--batch-size",
        metavar="N",
        type=int,
        default=None,
        help=(
            "Process only the first N items.  Default: all items."
        ),
    )
    parser.add_argument(
        "--concurrency",
        metavar="N",
        type=int,
        default=1,
        help=(
            "Number of worker threads for item processing (1-5, default: 1)."
        ),
    )
    parser.add_argument(
        "--llm-delay",
        metavar="SECS",
        type=float,
        default=1.0,
        help="Minimum seconds between LLM API calls (default: 1.0).",
    )
    parser.add_argument(
        "--embedding-delay",
        metavar="SECS",
        type=float,
        default=0.2,
        help="Minimum seconds between embedding API calls (default: 0.2).",
    )
    parser.add_argument(
        "--max-retries",
        metavar="N",
        type=int,
        default=3,
        help="Maximum retry attempts per pipeline stage (default: 3).",
    )

    # Mode flags.
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from a previous batch state file.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock mode (no actual LLM/embedding/DB calls).",
    )

    # File/path configuration.
    parser.add_argument(
        "--state-dir",
        metavar="DIR",
        type=str,
        default="pipeline/",
        help="Directory for state, progress, and report files (default: pipeline/).",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        type=str,
        default=DEFAULT_MODEL,
        help=f"LLM model identifier (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--batch-id",
        metavar="ID",
        type=str,
        default="",
        help="Custom batch ID (default: auto-generated from timestamp).",
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the CLI runner."""
    parser = _build_parser()
    args = parser.parse_args()

    # -- Resolve batch ID early so logging can use it --
    batch_id = args.batch_id
    if not batch_id:
        batch_id = "batch-" + datetime.now(timezone.utc).strftime(
            "%Y%m%d-%H%M%S"
        )

    # -- Resolve state_dir to absolute path --
    state_dir = os.path.abspath(args.state_dir)

    # -- Configure logging --
    _configure_logging(state_dir, batch_id)

    logger.info("EE Toolbox Batch Runner starting")
    logger.info("Arguments: %s", vars(args))

    # -- Load items --
    if args.input:
        logger.info("Loading items from %s", args.input)
        items = _load_items_from_file(args.input)
        logger.info("Loaded %d items from file.", len(items))
    else:
        items = _generate_items(args.generate)

    if not items:
        print("No items to process.", file=sys.stderr)
        sys.exit(0)

    # -- Apply batch-size limit --
    if args.batch_size is not None:
        original_count = len(items)
        items = items[: args.batch_size]
        logger.info(
            "Batch size limit: processing %d of %d items.",
            len(items),
            original_count,
        )

    # -- Build BatchConfig --
    config = BatchConfig(
        batch_id=batch_id,
        max_retries=args.max_retries,
        llm_delay=args.llm_delay,
        embedding_delay=args.embedding_delay,
        llm_concurrency=args.concurrency,
        model=args.model,
        mock_mode=args.mock,
        state_dir=state_dir,
    )

    logger.info("BatchConfig: %s", config)

    # -- Create processor and run --
    processor = BatchProcessor(config)

    try:
        report = processor.process_batch(items, resume=args.resume)
    except KeyboardInterrupt:
        # The BatchProcessor handles KeyboardInterrupt internally and saves
        # state, but if it propagates here we still want a clean exit.
        logger.warning("Interrupted by user.")
        print("\nInterrupted. State has been saved.")
        sys.exit(1)

    # -- Print final report --
    _print_report(report)

    # -- Exit code: 0 if no failures, 1 if any failures --
    failed = report.get("failed", 0)
    if failed > 0:
        logger.info(
            "Exiting with code 1 (%d items failed).", failed
        )
        sys.exit(1)
    else:
        logger.info("Exiting with code 0 (all items succeeded).")
        sys.exit(0)


if __name__ == "__main__":
    main()
