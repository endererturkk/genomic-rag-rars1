import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from Bio import Entrez
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

import config


# -----------------------------
# Helpers
# -----------------------------

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    return str(x).strip()


def extract_doi_from_article(article: Dict[str, Any]) -> Optional[str]:
    """
    Tries to extract DOI from PubMed record if available.
    """
    # PubmedData -> ArticleIdList (contains DOI entries)
    pubmed_data = article.get("PubmedData", {})
    article_id_list = pubmed_data.get("ArticleIdList", [])
    for item in article_id_list:
        try:
            # Biopython can represent as something like: {'IdType': 'doi', '_': '10.XXXX/YYY'}
            id_type = getattr(item, "attributes", {}).get("IdType") if hasattr(item, "attributes") else None
            if id_type == "doi":
                return _safe_text(item)
        except Exception:
            continue

    # Fallback: scan abstract text (sometimes DOI appears in text)
    abstract = extract_abstract(article)
    m = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", abstract, flags=re.IGNORECASE)
    if m:
        return m.group(0)

    return None


def extract_title(article: Dict[str, Any]) -> str:
    medline = article.get("MedlineCitation", {})
    art = medline.get("Article", {})
    return _safe_text(art.get("ArticleTitle"))


def extract_abstract(article: Dict[str, Any]) -> str:
    medline = article.get("MedlineCitation", {})
    art = medline.get("Article", {})
    abstract = art.get("Abstract", {})
    parts = abstract.get("AbstractText", [])
    if isinstance(parts, list):
        return " ".join(_safe_text(p) for p in parts if _safe_text(p))
    return _safe_text(parts)


def extract_pub_year(article: Dict[str, Any]) -> Optional[str]:
    medline = article.get("MedlineCitation", {})
    art = medline.get("Article", {})
    journal = art.get("Journal", {})
    issue = journal.get("JournalIssue", {})
    pubdate = issue.get("PubDate", {})

    # Prefer Year if available
    y = pubdate.get("Year")
    if y:
        return _safe_text(y)

    # Sometimes MedlineDate exists (e.g., "2023 Jan-Feb")
    medline_date = pubdate.get("MedlineDate")
    if medline_date:
        m = re.search(r"\b(19|20)\d{2}\b", _safe_text(medline_date))
        if m:
            return m.group(0)

    return None


def extract_authors(article: Dict[str, Any]) -> List[str]:
    medline = article.get("MedlineCitation", {})
    art = medline.get("Article", {})
    author_list = art.get("AuthorList", [])
    out = []
    for a in author_list:
        last = _safe_text(a.get("LastName"))
        fore = _safe_text(a.get("ForeName"))
        collective = _safe_text(a.get("CollectiveName"))
        if collective:
            out.append(collective)
        elif last or fore:
            out.append((" ".join([fore, last])).strip())
    return out


# -----------------------------
# NCBI Entrez calls (rate-limited + retry)
# -----------------------------

class EntrezTransientError(RuntimeError):
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    retry=retry_if_exception_type((EntrezTransientError, TimeoutError, OSError)),
)
def entrez_esearch(term: str, retmax: int) -> List[str]:
    try:
        with Entrez.esearch(
            db="pubmed",
            term=term,
            retmax=retmax,
            sort="pub+date",  # newest first
        ) as handle:
            result = Entrez.read(handle)
        ids = result.get("IdList", [])
        return [str(x) for x in ids]
    except Exception as e:
        # Treat as transient (network / NCBI hiccup)
        raise EntrezTransientError(str(e))


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    retry=retry_if_exception_type((EntrezTransientError, TimeoutError, OSError)),
)
def entrez_efetch(pmids: List[str]) -> List[Dict[str, Any]]:
    try:
        # Use XML mode for richer fields (incl. PubmedData)
        with Entrez.efetch(
            db="pubmed",
            id=",".join(pmids),
            rettype="abstract",
            retmode="xml",
        ) as handle:
            records = Entrez.read(handle)
        # Expected: PubmedArticle list
        return records.get("PubmedArticle", [])
    except Exception as e:
        raise EntrezTransientError(str(e))


def chunk_list(items: List[str], n: int) -> List[List[str]]:
    return [items[i : i + n] for i in range(0, len(items), n)]


def ingest_latest_pubmed_rars1(
    term: str,
    max_results: int,
    out_path: str,
    batch_size: int = 10,
    sleep_seconds: float = 0.34,
) -> Dict[str, Any]:
    """
    Fetch latest PubMed records for a search term and write normalized JSON.
    """
    ensure_dir(os.path.dirname(out_path))

    pmids = entrez_esearch(term=term, retmax=max_results)

    normalized: List[Dict[str, Any]] = []
    # Fetch in batches to be gentle
    for batch in tqdm(chunk_list(pmids, batch_size), desc="Fetching PubMed batches"):
        time.sleep(sleep_seconds)  # NCBI rate-limit friendly
        articles = entrez_efetch(batch)

        for art in articles:
            medline = art.get("MedlineCitation", {})
            pmid = _safe_text(medline.get("PMID"))

            title = extract_title(art)
            abstract = extract_abstract(art)

            # Skip empty abstracts (some records have none)
            if not abstract:
                continue

            year = extract_pub_year(art)
            doi = extract_doi_from_article(art)
            authors = extract_authors(art)

            normalized.append(
                {
                    "pmid": pmid,
                    "doi": doi,
                    "year": year,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "source": "pubmed",
                    "fetched_at": now_iso(),
                }
            )

    payload = {
        "query": term,
        "max_results": max_results,
        "returned": len(normalized),
        "generated_at": now_iso(),
        "items": normalized,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload


def main() -> None:
    # Configure Entrez identity
    Entrez.email = config.NCBI_EMAIL
    Entrez.tool = getattr(config, "NCBI_TOOL", "GenomicRAG")

    out_file = os.path.join(config.DATA_DIR, "pubmed_rars1_latest.json")
    payload = ingest_latest_pubmed_rars1(
        term=config.SEARCH_TERM,
        max_results=config.MAX_RESULTS,
        out_path=out_file,
    )

    print(f"\nSaved: {out_file}")
    print(f"Returned abstracts: {payload['returned']}")


if __name__ == "__main__":
    main()