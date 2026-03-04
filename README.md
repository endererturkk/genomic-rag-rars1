# 🧬 Ilyome Biomedical RAG System

![Python](https://img.shields.io/badge/python-3.10-blue)
![RAG](https://img.shields.io/badge/RAG-Biomedical-green)
![VectorDB](https://img.shields.io/badge/VectorDB-Chroma-orange)
![LLM](https://img.shields.io/badge/LLM-Ollama-purple)
![Status](https://img.shields.io/badge/status-research--prototype-lightgrey)

A guarded Retrieval-Augmented Generation (RAG) system for extracting **RARS1 gene variants, diseases, and phenotypes** from PubMed literature with **citation grounding and hallucination guardrails**.

---

# Overview

This project implements a guarded Retrieval-Augmented Generation (RAG) system for structured extraction of biomedical knowledge from **PubMed literature related to the RARS1 gene**.

The system retrieves recent scientific abstracts from PubMed and extracts structured biomedical information, including:

- 🧬 **cDNA HGVS variants**
- 🦠 **Associated diseases**
- 🧠 **Associated phenotypes**
- 📄 **Grounded PubMed citations (PMIDs)**

The architecture prioritizes:

- Evidence grounding  
- Hallucination prevention  
- Adversarial robustness  
- Explicit safe fallback behavior  

This is **not a general-purpose chatbot**.  
It is a **controlled biomedical extraction pipeline designed to ensure traceable and verifiable outputs**.

---

# 🏗 System Architecture
PubMed API
↓
Abstract Ingestion
↓
Variant-Safe Chunking
↓
BGE-large Embeddings
↓
Chroma Vector Store
↓
Retriever
↓
Local LLM (Ollama)
↓
Guardrail Validation
↓
Structured Biomedical Output



---

# 1️⃣ Data Ingestion

The ingestion pipeline retrieves biomedical literature from PubMed using the following query:
RARS1[Title/Abstract]

The system retrieves the **most recent publications (configured to 30 results)**.

For each article, the following metadata is extracted:

- PMID
- DOI
- Title
- Authors
- Publication year
- Abstract text

The retrieved records are normalized into structured JSON format and stored in:
data/raw/pubmed_rars1_latest.json


This approach ensures the system operates on **recent biomedical literature instead of static datasets**.

---

# PubMed API Rate Limiting

The ingestion pipeline respects **NCBI API usage policies**.

To ensure stable and compliant API usage:

- A **0.34 second delay** is introduced between requests.
- The **Tenacity library** implements exponential backoff retry logic.

This handles transient failures such as:

- network errors  
- temporary API interruptions  
- NCBI throttling  

---

# 2️⃣ Knowledge Processing & Storage

## Variant-Safe Chunking

Medical abstracts are split into chunks before embedding.

Special care is taken to avoid splitting HGVS variant expressions such as:
c.1535G>A



Variant patterns are detected before chunk boundaries are applied to ensure mutation identifiers remain intact.

Chunk configuration;
Chunk size: 500 characters
Overlap: 50 characters



---

## Embeddings

Embedding model used: BAAI/bge-large-en



This model was selected because it provides **strong semantic retrieval performance for scientific text**.

Its dense embedding representations are well suited for **biomedical literature search tasks**.

---

## Vector Store

The processed chunks are indexed into a **persistent Chroma vector database**.

Stored metadata includes:

- PMID  
- DOI  
- Publication year  
- Source  

This allows efficient **similarity-based retrieval of relevant scientific evidence**.

---

# 3️⃣ Retrieval Layer

The retrieval pipeline operates as follows:
Query
↓
Embedding
↓
Similarity Search
↓
Top-K Relevant Chunks




Retrieved chunks are formatted as:
[PMID: XXXXXXXX]
Abstract text



Only retrieved context is passed to the language model.

The LLM **cannot access external knowledge**.

---

# 4️⃣ Local LLM Extraction

The extraction step is performed using a **locally hosted language model via Ollama**.

Using a local LLM ensures:

- No external API dependency  
- Full control over inference behavior  
- Reproducible results  

Before running the system, ensure **Ollama is installed** and a compatible model is available.

Example:  ollama run llama3


---

# 5️⃣ Strict Extraction Contract

The language model operates under a **strict prompt contract**.

Rules:

- Only use provided context  
- No external knowledge  
- No inference beyond text  
- JSON-only output  
- No explanations  
- No markdown  
- No fabricated citations  

Each variant must:

- Contain exactly **one cDNA HGVS notation** (e.g., `c.1535G>A`)
- Exclude protein annotations
- Include PMIDs as a **list of strings**

If no evidence is found, the system returns a safe fallback:
{
"answer": "No evidence found in retrieved literature.",
"confidence": "high",
"citations": []
}




---

# 🛡 Guardrail Layer

After extraction, multiple validation layers are applied.

### Variant Processing

- multi-variant splitting  
- protein annotation removal  
- context existence validation  
- citation validation against retrieved metadata  
- duplicate variant merging (PMID union + sorting)

### Disease & Phenotype Validation

Additional checks include:

- citation validation  
- context grounding verification  
- disease mention validation  

### Generic Disease Association Guard

If a query asks about disease associations such as:

- "associated with X"  
- "linked to X"  
- "related to X"  
- "causes X"  

and the disease does not appear in validated literature, the system returns a **safe fallback**.

This prevents **false-positive disease associations**.

---

# 📊 Evaluation

Evaluation is fully automated.

Scripts:
evaluation/run_eval.py
evaluation/metrics.py



Test categories include:

| Test Type | Purpose |
|-----------|--------|
| Normal Query | Structured extraction |
| Trick Query | Detect hallucinated associations |
| Negative Query | Safe fallback behavior |
| Variant Query | Variant extraction validation |

Example metrics output:
total_tests: 4
structured_tests: 2
fallback_tests: 2
trick_passed: True
negative_passed: True
normal_has_variants: True
overall_score: 1.0



Evaluation verifies that the system:

- extracts valid variants  
- avoids hallucinated disease associations  
- returns safe fallbacks for unsupported queries  

---

# 🔒 Safety Guarantees

The system enforces:

- No hallucinated PMIDs  
- No unsupported disease associations  
- No cross-document citation leakage  
- Explicit abstention when evidence is insufficient  
- Deduplicated and normalized variant output  

The model is **allowed to abstain rather than speculate**.

Precision is prioritized over recall.

---

# 🧠 Design Philosophy

This system demonstrates:

- Structured biomedical information extraction  
- Evidence-grounded language model outputs  
- Contract-based LLM control  
- Multi-layer guardrails  
- Adversarial query handling  
- Automated evaluation scoring  

The design aims to **minimize hallucination risk while preserving traceable biomedical evidence**.

---

# ⚙️ How to Run

Follow the steps below to run the system locally.

1️⃣ Activate environment

conda activate ilyome-rag



2️⃣ Retrieve PubMed data

python ingest.py


3️⃣ Run the RAG pipeline

python main.py


4️⃣ Run evaluation
Run the automated evaluation suite.
python evaluation/run_eval.py
python evaluation/metrics.py

📂 Outputs
The evaluation process generates the following file:
eval_results.json




Fetch the latest RARS1-related abstracts from PubMed.

Metrics summary is printed in the terminal.

---

# ⚠️ Final Note

In biomedical systems, generating incorrect scientific claims is **more harmful than returning no answer**.

This system is designed to **prefer abstention over hallucination**, ensuring that all extracted knowledge remains **grounded in verifiable scientific literature**.







