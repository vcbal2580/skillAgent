"""
Knowledge manager - high-level API for knowledge CRUD operations.
"""

import hashlib
import time
from knowledge.vector_store import VectorStore


class KnowledgeManager:
    """Manages personal knowledge with vector storage."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.store = VectorStore()
        self._initialized = True

    def save(self, content: str, tags: list[str] = None, source: str = "user") -> str:
        """
        Save a piece of knowledge.
        
        Args:
            content: The knowledge text to store
            tags: Optional tags for categorization
            source: Source of the knowledge (user/web/etc.)
            
        Returns:
            The document ID
        """
        doc_id = self._generate_id(content)
        metadata = {
            "tags": ",".join(tags) if tags else "",
            "source": source,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.store.add(doc_id, content, metadata)
        return doc_id

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """Search knowledge by semantic similarity."""
        return self.store.query(query, top_k)

    def delete(self, doc_id: str) -> bool:
        """Delete a knowledge entry by ID."""
        return self.store.delete(doc_id)

    def list_all(self, limit: int = 50) -> list[dict]:
        """List all stored knowledge entries."""
        return self.store.list_all(limit)

    def count(self) -> int:
        """Get total knowledge count."""
        return self.store.count()

    @staticmethod
    def _generate_id(content: str) -> str:
        """Generate a deterministic ID from content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]
