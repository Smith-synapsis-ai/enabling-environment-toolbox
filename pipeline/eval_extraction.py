"""
Evaluation script for the metadata extraction pipeline.

Loads the test dataset, runs the extractor on each item, compares results
against expected values, logs results to the database, and prints a summary.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.extractor import extract_metadata

DB_DSN = "postgresql://ee_user:ee_dev_password@localhost:5433/ee_toolbox"


def jaccard_similarity(predicted: list, expected: list) -> float:
    """Calculate Jaccard similarity between two lists treated as sets."""
    if not predicted and not expected:
        return 1.0
    if not predicted or not expected:
        return 0.0
    pred_set = set(predicted)
    exp_set = set(expected)
    intersection = pred_set & exp_set
    union = pred_set | exp_set
    return len(intersection) / len(union) if union else 0.0


def exact_match(predicted, expected) -> float:
    """Return 1.0 if predicted equals expected, else 0.0."""
    if predicted is None and expected is None:
        return 1.0
    if predicted is None or expected is None:
        return 0.0
    return 1.0 if predicted.strip().lower() == expected.strip().lower() else 0.0


def is_non_empty_string(value) -> float:
    """Return 1.0 if value is a non-empty string."""
    return 1.0 if isinstance(value, str) and len(value.strip()) > 0 else 0.0


def evaluate_item(predicted: dict, expected: dict) -> dict:
    """
    Evaluate a single extraction result against expected values.

    Returns a dict with per-field scores and an overall score.
    """
    scores = {}

    # Array fields - Jaccard similarity
    for field in ["pillars", "domains", "geography"]:
        pred_vals = predicted.get(field, [])
        exp_vals = expected.get(field, [])
        scores[field] = jaccard_similarity(pred_vals, exp_vals)

    # Target users - only score if expected is non-empty
    exp_users = expected.get("target_users", [])
    if exp_users:
        scores["target_users"] = jaccard_similarity(
            predicted.get("target_users", []), exp_users
        )

    # Single-value fields - exact match
    for field in ["type", "stage"]:
        scores[field] = exact_match(
            predicted.get(field), expected.get(field)
        )

    # Text fields - non-empty check
    for field in ["summary", "what_it_does", "when_to_use_it", "who_its_for"]:
        scores[field] = is_non_empty_string(predicted.get(field))

    # Overall score: average of all scored fields
    all_scores = list(scores.values())
    scores["overall"] = sum(all_scores) / len(all_scores) if all_scores else 0.0

    return scores


def get_prompt_version_id() -> str:
    """Get the active metadata_extraction prompt version ID."""
    conn = psycopg2.connect(DB_DSN)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM prompt_versions "
            "WHERE prompt_name = 'metadata_extraction' AND is_active = true "
            "ORDER BY version DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("No active metadata_extraction prompt found")
        return str(row[0])
    finally:
        conn.close()


def log_result_to_db(
    prompt_version_id: str,
    input_data: dict,
    output_data: dict,
    expected_output: dict,
    is_correct: bool,
    score: float,
    latency_ms: int,
    model_used: str,
):
    """Log an eval result to the prompt_eval_results table."""
    conn = psycopg2.connect(DB_DSN)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO prompt_eval_results
                (id, prompt_version_id, input_data, output_data, expected_output,
                 is_correct, score, latency_ms, model_used, evaluated_at, evaluated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                prompt_version_id,
                psycopg2.extras.Json(input_data),
                psycopg2.extras.Json(output_data),
                psycopg2.extras.Json(expected_output),
                is_correct,
                score,
                latency_ms,
                model_used,
                datetime.now(timezone.utc),
                "automated",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def main():
    # Load test dataset
    test_data_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_data",
        "extraction_test_set.json",
    )
    with open(test_data_path) as f:
        test_set = json.load(f)

    # Parse command-line limit
    max_items = int(sys.argv[1]) if len(sys.argv) > 1 else len(test_set)
    test_set = test_set[:max_items]

    prompt_version_id = get_prompt_version_id()
    print(f"Using prompt version: {prompt_version_id}")
    print(f"Evaluating {len(test_set)} items\n")

    # ── Run extractions and evaluate ──────────────────────────────────────

    all_scores = []
    all_latencies = []
    all_warnings = []
    pillar_zero_overlap = []
    errors = []

    for i, item in enumerate(test_set):
        item_id = item.get("id", f"item-{i}")
        input_data = item["input"]
        expected = item["expected"]

        try:
            result = extract_metadata(
                title=input_data["title"],
                authors=input_data["authors"],
                date=input_data["date"],
                abstract=input_data["abstract"],
                full_text=input_data.get("full_text", ""),
            )

            # Extract metadata fields (remove internal fields)
            latency_ms = result.pop("_latency_ms", 0)
            model_used = result.pop("_model", "unknown")
            result.pop("_prompt_version_id", None)
            warnings = result.pop("_warnings", [])
            all_warnings.extend(warnings)

            # Evaluate
            scores = evaluate_item(result, expected)
            overall_score = scores["overall"]
            is_correct = overall_score >= 0.7
            all_scores.append(scores)
            all_latencies.append(latency_ms)

            # Check for zero pillar overlap
            pred_pillars = set(result.get("pillars", []))
            exp_pillars = set(expected.get("pillars", []))
            if pred_pillars and exp_pillars and not (pred_pillars & exp_pillars):
                pillar_zero_overlap.append({
                    "id": item_id,
                    "title": input_data["title"],
                    "predicted": list(pred_pillars),
                    "expected": list(exp_pillars),
                })

            # Progress output
            n_pillars = len(result.get("pillars", []))
            n_domains = len(result.get("domains", []))
            pred_type = result.get("type", "?")
            type_check = "ok" if scores.get("type", 0) == 1.0 else "MISS"
            print(
                f"[{i+1}/{len(test_set)}] {input_data['title']} -> "
                f"{n_pillars} pillars, {n_domains} domains, "
                f"type={pred_type} {type_check}, "
                f"score={overall_score:.2f}, "
                f"{latency_ms}ms"
            )
            if warnings:
                for w in warnings:
                    print(f"    WARN: {w}")

            # Log to database
            log_result_to_db(
                prompt_version_id=prompt_version_id,
                input_data=input_data,
                output_data=result,
                expected_output=expected,
                is_correct=is_correct,
                score=round(overall_score, 4),
                latency_ms=latency_ms,
                model_used=model_used,
            )

        except Exception as e:
            print(f"[{i+1}/{len(test_set)}] {input_data['title']} -> ERROR: {e}")
            errors.append({"id": item_id, "title": input_data["title"], "error": str(e)})

    # ── Summary ────────────────────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    if not all_scores:
        print("No items were successfully evaluated!")
        return

    n = len(all_scores)

    # Per-field averages
    field_names = ["pillars", "domains", "type", "stage", "geography",
                   "summary", "what_it_does", "when_to_use_it", "who_its_for"]

    print(f"\nPer-field accuracy ({n} items):")
    print("-" * 50)
    for field in field_names:
        field_scores = [s[field] for s in all_scores if field in s]
        if field_scores:
            avg = sum(field_scores) / len(field_scores)
            metric = "Jaccard" if field in ("pillars", "domains", "geography") else \
                     "exact match" if field in ("type", "stage") else "non-empty"
            print(f"  {field:25s}: {avg:.1%}  ({metric}, n={len(field_scores)})")

    # Target users (only where expected is non-empty)
    tu_scores = [s["target_users"] for s in all_scores if "target_users" in s]
    if tu_scores:
        avg = sum(tu_scores) / len(tu_scores)
        print(f"  {'target_users':25s}: {avg:.1%}  (Jaccard, n={len(tu_scores)})")

    # Overall
    overall_scores = [s["overall"] for s in all_scores]
    overall_avg = sum(overall_scores) / len(overall_scores)
    print(f"\n  {'OVERALL':25s}: {overall_avg:.1%}")

    # Correct items (score >= 0.7)
    n_correct = sum(1 for s in overall_scores if s >= 0.7)
    print(f"\n  Items >= 0.7 threshold : {n_correct}/{n} ({n_correct/n:.0%})")

    # Taxonomy warnings
    print(f"\n  Taxonomy warnings      : {len(all_warnings)}")
    if all_warnings:
        # Show unique warnings
        unique_warnings = sorted(set(all_warnings))
        for w in unique_warnings[:20]:
            print(f"    - {w}")
        if len(unique_warnings) > 20:
            print(f"    ... and {len(unique_warnings) - 20} more")

    # Latency
    if all_latencies:
        avg_lat = sum(all_latencies) / len(all_latencies)
        print(f"\n  Average latency        : {avg_lat:.0f} ms")
        print(f"  Min/Max latency        : {min(all_latencies)} / {max(all_latencies)} ms")

    # Zero pillar overlap
    if pillar_zero_overlap:
        print(f"\n  ZERO PILLAR OVERLAP ({len(pillar_zero_overlap)} items):")
        for item in pillar_zero_overlap:
            print(f"    - {item['title']}")
            print(f"      predicted: {item['predicted']}")
            print(f"      expected:  {item['expected']}")

    # Errors
    if errors:
        print(f"\n  ERRORS ({len(errors)} items):")
        for err in errors:
            print(f"    - {err['title']}: {err['error'][:100]}")

    # DB log count
    conn = psycopg2.connect(DB_DSN)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prompt_eval_results WHERE evaluated_by = 'automated'")
        total_logged = cur.fetchone()[0]
        print(f"\n  Total eval results in DB: {total_logged}")
    finally:
        conn.close()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
