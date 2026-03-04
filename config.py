# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VECTOR_DB_DIR = os.path.join(BASE_DIR, "data", "processed", "vector_store")

NCBI_EMAIL = "ender2543178@gmail.com"
NCBI_TOOL = "GenomicRAG_RARS1"

SEARCH_TERM = "RARS1[Title/Abstract]"
MAX_RESULTS = 30

DATA_DIR = "data/raw"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

EMBEDDING_MODEL = "BAAI/bge-large-en"

