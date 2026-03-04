import sys
from pathlib import Path

# Add project root to PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import json
from datetime import datetime, timezone

from rag.pipeline import run_query


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_result_record(query: str, result):
    """
    Normalizes run_query output into a consistent record structure for eval_results.json
    """
    record = {
        "query": query,
        "timestamp_utc": now_utc_iso(),
        "raw_result": result,
    }

    # If it's a guardrail fallback response (answer/confidence/citations)
    if isinstance(result, dict) and "answer" in result and "confidence" in result:
        record["type"] = "fallback_answer"
        record["summary"] = {
            "answer": result.get("answer"),
            "confidence": result.get("confidence"),
            "citations_count": len(result.get("citations", [])) if isinstance(result.get("citations"), list) else 0,
        }
        return record

    # Otherwise assume structured JSON with sections
    record["type"] = "structured_extraction"
    variants = (result or {}).get("variants", []) if isinstance(result, dict) else []
    diseases = (result or {}).get("diseases", []) if isinstance(result, dict) else []
    phenotypes = (result or {}).get("phenotypes", []) if isinstance(result, dict) else []

    record["summary"] = {
        "variants_count": len(variants) if isinstance(variants, list) else 0,
        "diseases_count": len(diseases) if isinstance(diseases, list) else 0,
        "phenotypes_count": len(phenotypes) if isinstance(phenotypes, list) else 0,
    }
    return record


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "eval_results.json"

    # --- Evaluation queries ---
    # 1) Normal / non-trick query (should return variants + symptoms/phenotypes)
    normal_query = "What are the most recently reported variants in RARS1 and their associated symptoms?"

    # 2) Trick query (should return explicit 'No evidence found...' and empty citations)
    trick_query = "Is RARS1 associated with cystic fibrosis?"

    # 3) Another negative / adversarial query (pick a clearly unrelated condition)
    extra_negative_query = "Is RARS1 associated with malaria?"

    # 4) Variant-focused query (tests HGVS extraction + citations)
    variant_query = "List reported RARS1 cDNA variants mentioned in the literature and cite PMIDs."

    queries = [
        {"id": "normal_1", "label": "normal", "query": normal_query},
        {"id": "trick_1", "label": "trick", "query": trick_query},
        {"id": "negative_1", "label": "negative", "query": extra_negative_query},
        {"id": "variants_1", "label": "variants", "query": variant_query},
    ]

    results = {
        "generated_at_utc": now_utc_iso(),
        "output_file": str(output_path),
        "tests": [],
    }

    for q in queries:
        query = q["query"]
        print(f"\n=== Running: {q['id']} ({q['label']}) ===")
        print(query)

        try:
            res = run_query(query)
        except Exception as e:
            res = {"error": str(e)}

        rec = {
            "id": q["id"],
            "label": q["label"],
            **to_result_record(query, res),
        }

        results["tests"].append(rec)

    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Wrote: {output_path}")


if __name__ == "__main__":
    main()