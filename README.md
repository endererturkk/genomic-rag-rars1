Ilyome Biomedical RAG System
Overview

This project implements a guarded Retrieval-Augmented Generation (RAG) system for structured extraction of biomedical knowledge from PubMed literature related to the RARS1 gene.

The system retrieves recent scientific abstracts from PubMed and extracts structured biomedical information, including:

cDNA HGVS variants

Associated diseases

Associated phenotypes

Grounded PubMed citations (PMIDs)

The architecture prioritizes:

Evidence grounding

Hallucination prevention

Adversarial robustness

Explicit safe fallback behavior

This is not a general-purpose chatbot. It is a controlled biomedical extraction pipeline designed to ensure traceable and verifiable outputs.




Ilyome Biomedical RAG System
Overview

This project implements a guarded Retrieval-Augmented Generation (RAG) system for structured extraction of biomedical knowledge from PubMed literature related to the RARS1 gene.

The system retrieves recent scientific abstracts from PubMed and extracts structured biomedical information, including:

cDNA HGVS variants

Associated diseases

Associated phenotypes

Grounded PubMed citations (PMIDs)

The architecture prioritizes:

Evidence grounding

Hallucination prevention

Adversarial robustness

Explicit safe fallback behavior

This is not a general-purpose chatbot. It is a controlled biomedical extraction pipeline designed to ensure traceable and verifiable outputs.  RARS1[Title/Abstract]

Retrieve the most recent publications (configured to 30 results).

Fetch abstract metadata including:

PMID

DOI

Title

Authors

Publication year

Abstract text

Normalize the retrieved records into structured JSON format.

Store normalized records in:    data/raw/pubmed_rars1_latest.json

This approach ensures that the system always operates on recent biomedical literature instead of static datasets.





PubMed API Rate Limiting

The ingestion pipeline respects NCBI API policies.

To ensure stable and compliant API usage:

A 0.34 second delay is introduced between requests.

The Tenacity library implements exponential backoff retry logic.

This handles transient errors such as:

network failures

temporary API interruptions

NCBI throttling

2. Knowledge Processing & Storage
Variant-Safe Chunking

Medical abstracts are split into chunks before embedding.

Special care is taken to avoid splitting HGVS variant expressions such as:  c.1535G>A

Variant patterns are detected before chunk boundaries are applied to ensure mutation identifiers remain intact.

Chunk configuration:   Chunk size: 500 characters
                       Overlap: 50 characters



Embeddings

Embedding model used:      BAAI/bge-large-en

This model was selected because it provides strong semantic retrieval performance, especially for scientific and technical text.

Its dense embedding representations are well suited for biomedical literature search tasks.



Vector Store

The processed chunks are indexed into a persistent Chroma vector database.

Stored metadata includes:

PMID

DOI

Publication year

Source

This allows efficient similarity-based retrieval of relevant scientific evidence.




3. Retrieval Layer

User queries are processed using the following pipeline:
Query
 ↓
Embedding
 ↓
Similarity Search
 ↓
Top-K Relevant Chunks




Retrieved chunks are formatted as:  [PMID: XXXXXXXX]
                                     Abstract text



Only retrieved context is passed to the language model.

The LLM cannot access external knowledge.


4. Strict Extraction Contract

The language model operates under a strict prompt contract.

Rules:

Only use provided context

No external knowledge

No inference beyond text

JSON-only output

No explanations

No markdown

No fabricated citations

Each variant must:

Contain exactly one cDNA HGVS notation (e.g., c.1535G>A)

Exclude protein annotation

Include PMIDs as a list of strings

If no evidence is found, the system returns a safe fallback:
{
  "answer": "No evidence found in retrieved literature.",
  "confidence": "high",
  "citations": []
}




Guardrail Layer

After extraction, multiple validation layers are applied.

Variant Processing

Multi-variant splitting

Protein annotation removal

Context existence validation

Citation validation against retrieved metadata

Duplicate variant merging (PMID union + sorting)

Disease & Phenotype Validation

Additional checks include:

citation validation

context grounding verification

disease mention validation

Generic Disease Association Guard

If the query asks about a disease association such as:

"associated with X"

"linked to X"

"related to X"

"causes X"

and the disease does not appear in validated literature, the system returns a safe fallback.

This prevents false-positive disease associations.



Evaluation

Evaluation is fully automated.

Scripts:  evaluation/run_eval.py  evaluation/metrics.py


Test categories include:

Normal query (structured extraction expected)

Trick query (disease not associated with RARS1)

Negative disease query

Variant-focused query

Example metrics output:

total_tests: 4
structured_tests: 2
fallback_tests: 2
trick_passed: True
negative_passed: True
normal_has_variants: True
overall_score: 1.0

The evaluation verifies that the system:

extracts valid variants

avoids hallucinated disease associations

returns safe fallbacks for unsupported queries



Safety Guarantees

The system enforces:

No hallucinated PMIDs

No unsupported disease associations

No cross-document citation leakage

Explicit abstention when evidence is insufficient

Deduplicated and normalized variant output

The model is allowed to abstain rather than speculate.

Precision is prioritized over recall.

Design Philosophy

This system demonstrates:

Structured biomedical information extraction

Evidence-grounded language model outputs

Contract-based LLM control

Multi-layer guardrails

Adversarial query handling

Automated evaluation scoring

The design aims to minimize hallucination risk while preserving traceable biomedical evidence.




How to Run
conda activate ilyome-rag
python ingest.py
python evaluation/run_eval.py
python evaluation/metrics.py

Outputs
eval_results.json
metrics summary in terminal

Final Note

In biomedical systems, generating incorrect scientific claims is more harmful than returning no answer.

This system is designed to prefer abstention over hallucination, ensuring that all extracted knowledge is grounded in verifiable scientific literature.