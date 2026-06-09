"""Evaluation script for the relevance classifier.

Loads the test dataset, runs the classifier on each item sequentially,
logs results to the prompt_eval_results table, and prints accuracy metrics.
"""

import json
import sys
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from pipeline.classifier import classify_relevance, get_active_prompt
from pipeline.config import DATABASE_URL_SYNC, DEFAULT_MODEL


def load_test_set(path: str) -> list[dict]:
    """Load the test dataset from JSON."""
    with open(path, "r") as f:
        return json.load(f)


def log_result_to_db(conn, result: dict):
    """Insert a single evaluation result into prompt_eval_results."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO prompt_eval_results (
            id, prompt_version_id, input_data, output_data, expected_output,
            is_correct, score, latency_ms, model_used, evaluated_at, evaluated_by
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        """,
        (
            str(uuid.uuid4()),
            result["prompt_version_id"],
            psycopg2.extras.Json(result["input_data"]),
            psycopg2.extras.Json(result["output_data"]),
            psycopg2.extras.Json(result["expected_output"]),
            result["is_correct"],
            result["score"],
            result["latency_ms"],
            result["model_used"],
            datetime.now(timezone.utc),
            "automated",
        ),
    )
    conn.commit()
    cur.close()


def run_evaluation():
    """Run the full evaluation pipeline."""
    test_set_path = "/Users/smithai/workspace/ee-toolbox-app/pipeline/test_data/relevance_test_set.json"

    print("=" * 70)
    print("RELEVANCE CLASSIFIER EVALUATION")
    print("=" * 70)

    # Load test set
    test_set = load_test_set(test_set_path)
    total = len(test_set)
    print(f"\nLoaded {total} test items ({sum(1 for t in test_set if t['expected_relevant'])} positive, {sum(1 for t in test_set if not t['expected_relevant'])} negative)")

    # Get prompt version info
    prompt_version_id, _ = get_active_prompt()
    print(f"Using prompt version: {prompt_version_id}")
    print(f"Model: {DEFAULT_MODEL}")
    print()

    # Connect to database for logging
    conn = psycopg2.connect(DATABASE_URL_SYNC)

    # Track metrics
    results = []
    tp = fp = tn = fn = 0
    errors = 0
    correct_confidences = []
    incorrect_confidences = []
    latencies = []

    false_positives = []
    false_negatives = []

    # Process each item sequentially
    for i, item in enumerate(test_set):
        idx = i + 1
        title = item["title"]
        expected = item["expected_relevant"]

        # Classify
        result = classify_relevance(
            title=item["title"],
            authors=item["authors"],
            date=item["date"],
            abstract=item["abstract"],
            doc_type=item["doc_type"],
            url=item["url"],
            model=DEFAULT_MODEL,
        )

        predicted = result["relevant"]
        confidence = result["confidence"]
        latency = result["latency_ms"]
        latencies.append(latency)

        # Determine correctness
        if result["error"] or predicted is None:
            is_correct = False
            errors += 1
            status_icon = "!!"
            # Count as error in confusion matrix -- treat as wrong prediction
            if expected:
                fn += 1
                false_negatives.append(title)
            else:
                # If expected not-relevant and got error, it's neither TP nor TN
                # But we still count it as incorrect
                fp += 1
                false_positives.append(title)
        else:
            is_correct = predicted == expected
            if is_correct:
                correct_confidences.append(confidence)
                status_icon = "OK"
                if predicted:
                    tp += 1
                else:
                    tn += 1
            else:
                incorrect_confidences.append(confidence)
                status_icon = "XX"
                if predicted and not expected:
                    fp += 1
                    false_positives.append(title)
                elif not predicted and expected:
                    fn += 1
                    false_negatives.append(title)

        # Print progress
        predicted_str = "relevant" if predicted else ("not-relevant" if predicted is not None else "ERROR")
        expected_str = "relevant" if expected else "not-relevant"
        print(
            f"[{idx:>2}/{total}] {title[:55]:55s} -> {predicted_str:14s} "
            f"(conf: {confidence:.2f}) [{status_icon}] {latency}ms"
        )

        # Log to database
        log_entry = {
            "prompt_version_id": result["prompt_version_id"],
            "input_data": {
                "title": item["title"],
                "authors": item["authors"],
                "date": item["date"],
                "abstract": item["abstract"],
                "doc_type": item["doc_type"],
                "url": item["url"],
            },
            "output_data": {
                "relevant": predicted,
                "confidence": confidence,
                "reasoning": result["reasoning"],
                "raw_response": result["raw_response"][:1000] if result["raw_response"] else "",
                "error": result["error"],
            },
            "expected_output": {"relevant": expected},
            "is_correct": is_correct,
            "score": confidence,
            "latency_ms": latency,
            "model_used": result["model"],
        }
        log_result_to_db(conn, log_entry)
        results.append(log_entry)

    conn.close()

    # Print summary
    print()
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total items tested:     {total}")
    print(f"  Positive examples:    {sum(1 for t in test_set if t['expected_relevant'])}")
    print(f"  Negative examples:    {sum(1 for t in test_set if not t['expected_relevant'])}")
    print(f"  Errors:               {errors}")
    print()

    print("Confusion Matrix:")
    print(f"  True Positives (TP):  {tp}")
    print(f"  False Positives (FP): {fp}")
    print(f"  True Negatives (TN):  {tn}")
    print(f"  False Negatives (FN): {fn}")
    print()

    # Calculate metrics
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print("Metrics:")
    print(f"  Accuracy:             {accuracy:.4f} ({accuracy * 100:.1f}%)")
    print(f"  Precision:            {precision:.4f} ({precision * 100:.1f}%)")
    print(f"  Recall:               {recall:.4f} ({recall * 100:.1f}%)")
    print(f"  F1 Score:             {f1:.4f} ({f1 * 100:.1f}%)")
    print()

    avg_correct_conf = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0
    avg_incorrect_conf = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print("Confidence & Latency:")
    print(f"  Avg confidence (correct):   {avg_correct_conf:.3f}")
    print(f"  Avg confidence (incorrect): {avg_incorrect_conf:.3f}")
    print(f"  Avg latency:                {avg_latency:.0f}ms")
    print(f"  Total latency:              {sum(latencies) / 1000:.1f}s")
    print()

    if false_positives:
        print("False Positives (classified relevant but expected not-relevant):")
        for title in false_positives:
            print(f"  - {title}")
        print()

    if false_negatives:
        print("False Negatives (classified not-relevant but expected relevant):")
        for title in false_negatives:
            print(f"  - {title}")
        print()

    print(f"Results logged to database: {len(results)} entries")
    print("=" * 70)

    return {
        "total": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "errors": errors,
    }


if __name__ == "__main__":
    run_evaluation()
