# guardrails/hallucination_checker.py

import re
from typing import List, Dict, Any


# Broader HGVS-ish match; we will still ground by context
HGVS_CORE_PATTERN = r"(c\.[0-9+_\-]+[A-Za-z0-9>_]+)"


def extract_hgvs_cdna_variants(text: str) -> List[str]:
    """
    Extracts cDNA HGVS variants from a string.
    Handles cases like:
      - "c.1535G>A (p.Arg512Gln)"
      - "c.1535G>A (p.Arg512Gln) and c.1382G>A (p.Arg461His)"
      - "c.1535G>A; c.1382G>A"
    Returns list of 'c....' strings only (protein annotations removed).
    """
    if not text or not isinstance(text, str):
        return []

    # remove whitespace noise
    text = text.strip()

    # Find all cDNA occurrences
    found = re.findall(HGVS_CORE_PATTERN, text)

    # De-duplicate while preserving order
    out = []
    seen = set()
    for v in found:
        v = v.strip()
        if v and v not in seen:
            out.append(v)
            seen.add(v)
    return out


def normalize_for_match(s: str) -> str:
    """
    Make matching tolerant:
    - lower
    - remove spaces
    - remove common punctuation
    """
    if not s:
        return ""
    s = s.lower()
    s = s.replace(" ", "")
    # remove punctuation that might differ between LLM and text
    s = re.sub(r"[()\[\]{};:,]", "", s)
    return s


def variant_exists_in_context(variant: str, retrieved_chunks: List[str]) -> bool:
    """
    Ensures the variant appears in context (tolerant match).
    """
    v = normalize_for_match(variant)
    if not v:
        return False

    for chunk in retrieved_chunks:
        if v in normalize_for_match(chunk):
            return True
    return False


def filter_and_expand_variants(
    variant_entries: List[Dict[str, Any]],
    retrieved_chunks: List[str],
) -> List[Dict[str, Any]]:
    """
    Takes LLM 'variants' entries, and:
      - Reads variant string from entry["variant"] or entry["name"]
      - Splits multiple variants into multiple entries
      - Strips protein annotation by extracting only cDNA HGVS
      - Grounds each variant against retrieved context
    Keeps original fields but ensures each entry corresponds to ONE cDNA variant.
    """
    validated: List[Dict[str, Any]] = []

    for entry in variant_entries:
        raw_name = entry.get("variant") or entry.get("name") or ""
        cdna_variants = extract_hgvs_cdna_variants(raw_name)

        # If LLM didn't produce any c. variant, reject
        if not cdna_variants:
            continue

        for cdna in cdna_variants:
            if not variant_exists_in_context(cdna, retrieved_chunks):
                continue

            # create a copy per variant
            e = dict(entry)
            # standardize a canonical key while keeping "name" if you want
            e["variant"] = cdna
            # also keep a cleaner "name" if it existed
            e["name"] = cdna
            validated.append(e)

    return validated