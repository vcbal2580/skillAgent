"""
Vector store backed by ChromaDB for semantic knowledge retrieval.
"""

import chromadb
from chromadb.config import Settings
from core.config import config


class VectorStore:
    """ChromaDB-backed vector store for knowledge embeddings."""

    def __init__(self):
        persist_dir = config.get("knowledge.persist_directory", "./data/chromadb")
        collection_name = config.get("knowledge.collection_name", "personal_knowledge")
        self.top_k = config.get("knowledge.top_k", 5)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, doc_id: str, text: str, metadata: dict = None):
        """Add or update a document in the vector store."""
        self.collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def query(self, query_text: str, top_k: int = None) -> list[dict]:
        """
        Query the vector store for similar documents.
        
        Returns:
            List of dicts with keys: id, text, metadata, distance
        """
        k = top_k or self.top_k
        # Ensure we don't query more than we have
        count = self.collection.count()
        if count == 0:
            return []
        k = min(k, count)

        results = self.collection.query(
            query_texts=[query_text],
            n_results=k,
        )

        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
        return docs

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def list_all(self, limit: int = 100) -> list[dict]:
        """List all documents in the store."""
        results = self.collection.get(limit=limit)
        docs = []
        for i in range(len(results["ids"])):
            docs.append({
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
            })
        return docs

    def count(self) -> int:
        """Return total number of documents."""
        return self.collection.count()
