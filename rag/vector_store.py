from typing import List, Dict
import chromadb

import config


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=config.VECTOR_DB_DIR
        )

        self.collection = self.client.get_or_create_collection(
            name="rars1_collection"
        )

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
    ):
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(self, query_embedding: List[float], top_k: int = 5):
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )
        return results