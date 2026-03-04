import json
import os
import uuid
import re
from typing import Dict, Any

from rag.chunker import chunk_text
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.retriever import Retriever

from llm.extractor import LLMExtractor

from guardrails.hallucination_checker import filter_and_expand_variants
from guardrails.citation_validator import filter_invalid_citations
from guardrails.grounding import filter_grounded_entries

import config


# -------------------------------------------------
# DATA LOADING
# -------------------------------------------------

def load_pubmed_data() -> Dict[str, Any]:
    path = os.path.join(config.DATA_DIR, "pubmed_rars1_latest.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# INDEXING PIPELINE
# -------------------------------------------------

def index_documents():
    data = load_pubmed_data()

    embedder = EmbeddingModel()
    vector_store = VectorStore()

    all_chunks = []
    all_embeddings = []
    all_ids = []
    all_metadata = []

    for item in data["items"]:
        abstract = item["abstract"]
        chunks = chunk_text(abstract)

        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            embedding = embedder.embed_texts([chunk])[0]

            metadata = {
                "pmid": item["pmid"],
                "doi": item["doi"],
                "year": item["year"],
                "source": item["source"],
            }

            all_ids.append(chunk_id)
            all_chunks.append(chunk)
            all_embeddings.append(embedding)
            all_metadata.append(metadata)

    vector_store.add_documents(
        ids=all_ids,
        embeddings=all_embeddings,
        documents=all_chunks,
        metadatas=all_metadata,
    )

    print(f"Indexed {len(all_chunks)} chunks.")


# -------------------------------------------------
# CONTEXT BUILDER
# -------------------------------------------------

def build_context(results: Dict[str, Any]) -> str:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    blocks = []

    for doc, meta in zip(documents, metadatas):
        pmid = meta.get("pmid", "Unknown")
        block = f"[PMID: {pmid}]\n{doc}\n"
        blocks.append(block)

    return "\n---\n".join(blocks)


# -------------------------------------------------
# VARIANT MERGE (DEDUPLICATION)
# -------------------------------------------------

def merge_duplicate_variants(variants):

    merged = {}

    for v in variants:
        key = v.get("variant") or v.get("name")
        if not key:
            continue

        pmids = v.get("pmid", [])

        if key not in merged:
            merged[key] = set(pmids)
        else:
            merged[key].update(pmids)

    result = []
    for variant, pmid_set in merged.items():
        result.append({
            "variant": variant,
            "pmid": sorted(list(pmid_set))
        })

    return result


# -------------------------------------------------
# QUERY ENGINE WITH PERFECTION MODE GUARDRAILS
# -------------------------------------------------

def run_query(query: str):

    retriever = Retriever()
    extractor = LLMExtractor()

    # 1️⃣ Retrieve
    results = retriever.retrieve(query)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return {
            "answer": "No evidence found in retrieved literature.",
            "confidence": "high",
            "citations": []
        }

    # 2️⃣ Build context
    context = build_context(results)

    # 3️⃣ Extract structured data
    raw_output = extractor.extract(query, context)

    print("\n--- RAW LLM OUTPUT ---\n")
    print(json.dumps(raw_output, indent=2))

    if not raw_output or "error" in raw_output:
        return {
            "answer": "No valid structured data extracted.",
            "confidence": "low",
            "citations": []
        }

    validated_output = {}

    # -------------------------
    # VARIANTS
    # -------------------------
    if "variants" in raw_output:
        variants = raw_output["variants"]

        variants = filter_and_expand_variants(
            variants,
            documents
        )

        variants = filter_invalid_citations(
            variants,
            metadatas
        )

        variants = merge_duplicate_variants(variants)

        validated_output["variants"] = variants

    # -------------------------
    # DISEASES
    # -------------------------
    if "diseases" in raw_output:
        diseases = raw_output["diseases"]

        diseases = filter_invalid_citations(
            diseases,
            metadatas
        )

        diseases = filter_grounded_entries(
            diseases,
            documents,
            field_name="name"
        )

        validated_output["diseases"] = diseases

    # -------------------------
    # PHENOTYPES
    # -------------------------
    if "phenotypes" in raw_output:
        phenotypes = raw_output["phenotypes"]

        phenotypes = filter_invalid_citations(
            phenotypes,
            metadatas
        )

        phenotypes = filter_grounded_entries(
            phenotypes,
            documents,
            field_name="name"
        )

        validated_output["phenotypes"] = phenotypes

    # -------------------------------------------------
    # GENERIC DISEASE ASSOCIATION GUARD
    # -------------------------------------------------

    query_lower = query.lower()

    association_patterns = [
        r"associated with (.+)\??",
        r"linked to (.+)\??",
        r"related to (.+)\??",
        r"cause[s]? (.+)\??"
    ]

    requested_disease = None

    for pattern in association_patterns:
        match = re.search(pattern, query_lower)
        if match:
            requested_disease = match.group(1).strip()
            break

    if requested_disease:

        returned_diseases = [
            d.get("name", "").lower()
            for d in validated_output.get("diseases", [])
        ]

        if not any(requested_disease in d for d in returned_diseases):
            return {
                "answer": "No evidence found in retrieved literature.",
                "confidence": "high",
                "citations": []
            }

    # -------------------------------------------------
    # If everything empty → explicit safe response
    # -------------------------------------------------

    if not any(validated_output.values()):
        return {
            "answer": "No evidence found in retrieved literature.",
            "confidence": "high",
            "citations": []
        }

    return validated_output


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":
    index_documents()