"""
SKT-AI-LABS Vector Store
Multi-backend vector storage (ChromaDB, pgvector, FAISS, Redis)
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import structlog
from langchain_core.documents import Document

logger = structlog.get_logger("skt_ai_labs.memory")


class SKTVectorStore:
    """
    Unified vector store interface.

    Supports:
    - ChromaDB (default, local)
    - PostgreSQL + pgvector (production)
    - FAISS (fast, in-memory)
    - Redis (caching + vectors)
    """

    def __init__(self,
                 store_type: str = "chroma",
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 collection_name: str = "skt_default",
                 persist_directory: Optional[str] = None,
                 connection_string: Optional[str] = None):

        self.store_type = store_type.lower()
        self.collection_name = collection_name
        self.persist_directory = persist_directory or "./skt_vector_db"
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        self._logger = logger

        # Initialize embedding model
        self._init_embeddings(embedding_model)

        # Initialize store
        self._store = self._init_store()

    def _init_embeddings(self, model_name: str):
        """Initialize embedding model"""
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        except ImportError:
            try:
                from langchain_openai import OpenAIEmbeddings
                self.embeddings = OpenAIEmbeddings()
            except:
                self._logger.error("No embedding provider available")
                raise

    def _init_store(self):
        """Initialize vector store backend"""
        if self.store_type == "chroma":
            return self._init_chroma()
        elif self.store_type == "pgvector":
            return self._init_pgvector()
        elif self.store_type == "faiss":
            return self._init_faiss()
        elif self.store_type == "redis":
            return self._init_redis()
        else:
            raise ValueError(f"Unknown store type: {self.store_type}")

    def _init_chroma(self):
        try:
            from langchain_chroma import Chroma
            return Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
        except ImportError:
            from langchain_community.vectorstores import Chroma
            return Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )

    def _init_pgvector(self):
        try:
            from langchain_postgres import PGVector
            return PGVector(
                connection=self.connection_string,
                embeddings=self.embeddings,
                collection_name=self.collection_name,
            )
        except ImportError:
            from langchain_community.vectorstores import PGVector
            return PGVector(
                connection_string=self.connection_string,
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
            )

    def _init_faiss(self):
        try:
            from langchain_community.vectorstores import FAISS
            # FAISS is in-memory, will be created on first add
            return None  # Lazy init
        except ImportError:
            self._logger.error("faiss not installed")
            raise

    def _init_redis(self):
        try:
            from langchain_redis import RedisVectorStore
            return RedisVectorStore(
                embeddings=self.embeddings,
                index_name=self.collection_name,
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            )
        except ImportError:
            self._logger.error("redis vector store not installed")
            raise

    async def add_documents(self, documents: List[Document]):
        """Add documents to vector store"""
        if self.store_type == "faiss" and self._store is None:
            from langchain_community.vectorstores import FAISS
            self._store = await FAISS.afrom_documents(documents, self.embeddings)
        else:
            await self._store.aadd_documents(documents)

        self._logger.info("documents_added", count=len(documents), store=self.store_type)

    async def similarity_search(self, query: str, k: int = 5, filter: Optional[Dict] = None) -> List[Document]:
        """Search similar documents"""
        if self._store is None:
            return []

        try:
            results = await self._store.asimilarity_search(query, k=k, filter=filter)
            return results
        except Exception as e:
            self._logger.error("search_failed", error=str(e)[:100])
            return []

    async def delete_collection(self):
        """Delete entire collection"""
        if hasattr(self._store, 'delete_collection'):
            await self._store.adelete_collection()

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        return {
            "store_type": self.store_type,
            "collection": self.collection_name,
            "persist_dir": self.persist_directory,
        }
