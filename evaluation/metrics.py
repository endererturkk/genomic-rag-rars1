import json
from pathlib import Path


def evaluate(eval_path: Path):

    data = json.loads(eval_path.read_text(encoding="utf-8"))

    tests = data.get("tests", [])

    metrics = {
        "total_tests": len(tests),
        "structured_tests": 0,
        "fallback_tests": 0,
        "trick_passed": False,
        "negative_passed": False,
        "normal_has_variants": False,
        "overall_score": 0.0
    }

    for test in tests:

        label = test.get("label")
        result_type = test.get("type")
        summary = test.get("summary", {})

        if result_type == "structured_extraction":
            metrics["structured_tests"] += 1

        if result_type == "fallback_answer":
            metrics["fallback_tests"] += 1

        # Trick test must fallback
        if label == "trick":
            if result_type == "fallback_answer":
                metrics["trick_passed"] = True

        # Negative test must fallback
        if label == "negative":
            if result_type == "fallback_answer":
                metrics["negative_passed"] = True

        # Normal test must contain variants
        if label == "normal":
            if summary.get("variants_count", 0) > 0:
                metrics["normal_has_variants"] = True

    # -----------------------------
    # Compute score (simple logic)
    # -----------------------------

    score = 0

    if metrics["trick_passed"]:
        score += 1

    if metrics["negative_passed"]:
        score += 1

    if metrics["normal_has_variants"]:
        score += 1

    metrics["overall_score"] = round(score / 3, 2)

    return metrics


def main():
    project_root = Path(__file__).resolve().parents[1]
    eval_file = project_root / "eval_results.json"

    if not eval_file.exists():
        print("eval_results.json not found.")
        return

    metrics = evaluate(eval_file)

    print("\n=== EVALUATION METRICS ===\n")
    for k, v in metrics.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()