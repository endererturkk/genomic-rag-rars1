from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore


class Retriever:
    def __init__(self):
        self.embedder = EmbeddingModel()
        self.vector_store = VectorStore()

    def retrieve(self, query: str, top_k: int = 5):
        query_embedding = self.embedder.embed_texts([query])[0]

        results = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k
        )

        return results