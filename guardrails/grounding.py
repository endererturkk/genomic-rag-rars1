# guardrails/grounding.py

import re
from typing import List, Dict, Any


def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def soft_in_context(term: str, chunks: List[str]) -> bool:
    """
    Soft grounding:
    - requires at least one meaningful token from term to appear in context
    - avoids being too strict on full phrase matching
    """
    term_n = normalize_text(term)
    if not term_n:
        return False

    # pick "meaningful" tokens (len>=5) to avoid matching 'with', 'and', etc.
    tokens = [t for t in re.split(r"[^a-z0-9]+", term_n) if len(t) >= 5]
    if not tokens:
        # fallback: require full term
        tokens = [term_n]

    ctx = normalize_text(" ".join(chunks))

    # require at least one token hit
    return any(tok in ctx for tok in tokens)


def filter_grounded_entries(
    entries: List[Dict[str, Any]],
    retrieved_chunks: List[str],
    field_name: str = "name",
) -> List[Dict[str, Any]]:
    """
    Keeps entries if entry[field_name] is softly grounded in context.
    """
    out = []
    for e in entries:
        term = e.get(field_name) or ""
        if soft_in_context(term, retrieved_chunks):
            out.append(e)
    return out