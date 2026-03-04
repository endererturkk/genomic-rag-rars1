import re
from typing import Dict, List, Tuple

import config

# Regex patterns for common HGVS variant formats (not exhaustive, but solid baseline)
VARIANT_PATTERNS = [
    r"c\.\d+[ACGT]?>[ACGT]",               # c.5A>G
    r"c\.\d+_\d+del",                      # c.123_124del
    r"c\.\d+\+\d+[ACGT]?>[ACGT]",          # c.456+1G>A
    r"p\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}",   # p.Met1Thr
]


def find_variants(text: str) -> List[str]:
    matches: List[str] = []
    for pattern in VARIANT_PATTERNS:
        matches.extend(re.findall(pattern, text))
    # unique, stable order
    seen = set()
    uniq = []
    for v in matches:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def protect_variants(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replace detected HGVS-like variants with placeholders before chunking,
    so chunk boundaries never split the variant token.
    """
    variants = find_variants(text)
    mapping: Dict[str, str] = {}

    protected = text
    for i, var in enumerate(variants):
        placeholder = f"§V{i}§"   # short placeholder to reduce chance of being split
        mapping[placeholder] = var
        protected = protected.replace(var, placeholder)

    return protected, mapping


def restore_variants(text: str, mapping: Dict[str, str]) -> str:
    restored = text
    for placeholder, original in mapping.items():
        restored = restored.replace(placeholder, original)
    return restored


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Variant-safe chunking with overlap.
    - Ensures HGVS-like variant strings stay intact.
    - Guards against infinite loops when overlap >= chunk_size.
    - Stops cleanly at end-of-text (no trailing junk chunks).
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    protected_text, mapping = protect_variants(text)

    chunks: List[str] = []
    start = 0
    text_length = len(protected_text)

    step = max(1, chunk_size - overlap)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        chunk = protected_text[start:end]
        chunk = restore_variants(chunk, mapping)
        chunks.append(chunk)

        if end == text_length:
            break

        start += step

    return chunks