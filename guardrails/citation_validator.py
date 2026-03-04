# guardrails/citation_validator.py

import ast
from typing import List, Dict, Any


def normalize_pmid_field(pmid_raw: Any) -> List[str]:
    """
    Accepts:
      - "37186453"
      - 37186453
      - ["37186453", "31814314"]
      - "['37186453','31814314']"
      - "37186453, 31814314"
    Returns list[str] of numeric pmids (no empties).
    """
    if pmid_raw is None:
        return []

    # list already
    if isinstance(pmid_raw, list):
        return [str(x).strip() for x in pmid_raw if str(x).strip().isdigit()]

    # int
    if isinstance(pmid_raw, int):
        return [str(pmid_raw)]

    # string
    if isinstance(pmid_raw, str):
        s = pmid_raw.strip()

        # stringified python list
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip().isdigit()]
            except Exception:
                return []

        # comma-separated
        if "," in s:
            parts = [p.strip() for p in s.split(",")]
            return [p for p in parts if p.isdigit()]

        # single numeric
        if s.isdigit():
            return [s]

    return []


def filter_invalid_citations(entries: List[Dict[str, Any]], retrieved_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keeps only entries whose PMIDs exist in retrieved metadata.
    Sets entry["pmid"] to list[str] of matched pmids.
    """
    valid_pmids = {str(m.get("pmid")) for m in retrieved_metadata if m.get("pmid")}

    out: List[Dict[str, Any]] = []

    for entry in entries:
        pmids = normalize_pmid_field(entry.get("pmid"))

        matched = [p for p in pmids if p in valid_pmids]
        if not matched:
            continue

        e = dict(entry)
        e["pmid"] = matched
        out.append(e)

    return out