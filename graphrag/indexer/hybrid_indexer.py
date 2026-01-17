"""
Hybrid Indexer - Combines LightRAG and ChromaDB

This module provides intelligent routing between:
- LightRAG: For structured memory (personality, values, relationships)
- ChromaDB: For conversation history and unstructured content
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio

from .graph_indexer import IAMIGraphIndexer, IndexConfig
from .chroma import ChromaDBIndexer


class HybridIndexer:
    """
    Hybrid indexer that intelligently routes documents between
    LightRAG (graph-based) and ChromaDB (vector-based).

    Routing Strategy:
    - Structured memory → LightRAG (personality, values, relationships, etc.)
    - Conversations → ChromaDB
    - Other documents → Both (for enhanced recall)
    """

    # Document types that should use LightRAG
    LIGHTRAG_TYPES = {
        "personality",
        "values",
        "thinking_patterns",
        "language_style",
        "knowledge",
        "person_profile",
        "relationship",
        "ecological_system",
        "social_identity",
        "timeline_snapshot"
    }

    # Document types that should use ChromaDB
    CHROMADB_TYPES = {
        "conversation",
        "short_term_memory",
        "notes"
    }

    def __init__(
        self,
        lightrag_config: Optional[IndexConfig] = None,
        chroma_persist_dir: str = "./memory/vector_store",
        chroma_collection: str = "iami_conversations"
    ):
        """
        Initialize hybrid indexer.

        Args:
            lightrag_config: Configuration for LightRAG indexer
            chroma_persist_dir: ChromaDB persistence directory
            chroma_collection: ChromaDB collection name
        """
        # Initialize LightRAG
        if lightrag_config is None:
            lightrag_config = IndexConfig(
                working_dir="./graphrag/storage/index",
                api_key=os.getenv("DEEPSEEK_API_KEY")
            )
        self.lightrag_indexer = IAMIGraphIndexer(lightrag_config)

        # Initialize ChromaDB
        self.chroma_indexer = ChromaDBIndexer(
            persist_directory=chroma_persist_dir,
            collection_name=chroma_collection
        )

    async def index_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Index a single document using appropriate indexer(s).

        Args:
            doc: Document with 'type', 'content', and optional metadata

        Returns:
            Result dictionary with indexing details
        """
        doc_type = doc.get("type", "unknown")
        result = {
            "doc_id": doc.get("id"),
            "doc_type": doc_type,
            "lightrag": False,
            "chromadb": False,
            "errors": []
        }

        # Route to LightRAG
        if doc_type in self.LIGHTRAG_TYPES:
            try:
                await self.lightrag_indexer.update_document(doc)
                result["lightrag"] = True
            except Exception as e:
                result["errors"].append(f"LightRAG error: {str(e)}")

        # Route to ChromaDB
        if doc_type in self.CHROMADB_TYPES:
            try:
                metadata = doc.get("metadata", {})
                metadata["doc_type"] = doc_type

                if "timestamp" in doc:
                    metadata["timestamp"] = doc["timestamp"]

                if doc_type == "conversation":
                    await self.chroma_indexer.add_conversation(
                        content=doc.get("content", ""),
                        metadata=metadata,
                        conversation_id=doc.get("id")
                    )
                else:
                    # Generic document
                    await self.chroma_indexer.add_memory_snapshot(
                        memory_type=doc_type,
                        content=doc.get("content", ""),
                        timestamp=doc.get("timestamp"),
                        metadata=metadata
                    )

                result["chromadb"] = True
            except Exception as e:
                result["errors"].append(f"ChromaDB error: {str(e)}")

        # For unknown types or important documents, index in both
        if doc_type not in self.LIGHTRAG_TYPES and doc_type not in self.CHROMADB_TYPES:
            # Index in both for better coverage
            try:
                await self.lightrag_indexer.update_document(doc)
                result["lightrag"] = True
            except Exception as e:
                result["errors"].append(f"LightRAG error: {str(e)}")

            try:
                metadata = doc.get("metadata", {})
                metadata["doc_type"] = doc_type
                await self.chroma_indexer.add_memory_snapshot(
                    memory_type=doc_type,
                    content=doc.get("content", ""),
                    timestamp=doc.get("timestamp"),
                    metadata=metadata
                )
                result["chromadb"] = True
            except Exception as e:
                result["errors"].append(f"ChromaDB error: {str(e)}")

        return result

    async def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Index multiple documents.

        Args:
            documents: List of documents

        Returns:
            Summary of indexing results
        """
        results = {
            "total": len(documents),
            "lightrag_count": 0,
            "chromadb_count": 0,
            "both_count": 0,
            "failed": 0,
            "errors": []
        }

        for doc in documents:
            result = await self.index_document(doc)

            if result["lightrag"] and result["chromadb"]:
                results["both_count"] += 1
            elif result["lightrag"]:
                results["lightrag_count"] += 1
            elif result["chromadb"]:
                results["chromadb_count"] += 1
            else:
                results["failed"] += 1

            if result["errors"]:
                results["errors"].extend(result["errors"])

        return results

    async def query(
        self,
        query: str,
        use_lightrag: bool = True,
        use_chromadb: bool = True,
        lightrag_mode: str = "hybrid",
        chromadb_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query both indexers and combine results.

        Args:
            query: Query string
            use_lightrag: Whether to query LightRAG
            use_chromadb: Whether to query ChromaDB
            lightrag_mode: LightRAG query mode (naive, local, global, hybrid)
            chromadb_k: Number of results from ChromaDB

        Returns:
            Combined results from both indexers
        """
        results = {
            "query": query,
            "lightrag_result": None,
            "chromadb_results": None,
            "errors": []
        }

        # Query LightRAG
        if use_lightrag:
            try:
                lightrag_result = await self.lightrag_indexer.query(
                    query=query,
                    mode=lightrag_mode,
                    top_k=chromadb_k
                )
                results["lightrag_result"] = lightrag_result
            except Exception as e:
                results["errors"].append(f"LightRAG query error: {str(e)}")

        # Query ChromaDB
        if use_chromadb:
            try:
                chromadb_results = await self.chroma_indexer.search_with_score(
                    query=query,
                    k=chromadb_k
                )
                results["chromadb_results"] = chromadb_results
            except Exception as e:
                results["errors"].append(f"ChromaDB query error: {str(e)}")

        return results

    async def query_conversations(
        self,
        query: str,
        k: int = 5,
        time_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query only conversations from ChromaDB.

        Args:
            query: Query string
            k: Number of results
            time_filter: Optional timestamp filter (ISO format)

        Returns:
            List of conversation results
        """
        filter_dict = {"doc_type": "conversation"}

        if time_filter:
            # Add time filter if provided
            # ChromaDB supports filters like {"timestamp": {"$gte": "2024-01-01"}}
            pass

        return await self.chroma_indexer.search_with_score(
            query=query,
            k=k,
            filter_dict=filter_dict
        )

    async def query_structured_memory(
        self,
        query: str,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Query only structured memory from LightRAG.

        Args:
            query: Query string
            mode: LightRAG query mode

        Returns:
            LightRAG query result
        """
        return await self.lightrag_indexer.query(query=query, mode=mode)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics from both indexers.

        Returns:
            Combined statistics
        """
        return {
            "lightrag": self.lightrag_indexer.get_stats(),
            "chromadb": self.chroma_indexer.get_stats()
        }


# Synchronous wrapper
class HybridIndexerSync:
    """Synchronous version of HybridIndexer"""

    def __init__(
        self,
        lightrag_config: Optional[IndexConfig] = None,
        chroma_persist_dir: str = "./memory/vector_store",
        chroma_collection: str = "iami_conversations"
    ):
        self.indexer = HybridIndexer(
            lightrag_config=lightrag_config,
            chroma_persist_dir=chroma_persist_dir,
            chroma_collection=chroma_collection
        )

    def index_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return asyncio.run(self.indexer.index_document(doc))

    def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        return asyncio.run(self.indexer.index_documents(documents))

    def query(
        self,
        query: str,
        use_lightrag: bool = True,
        use_chromadb: bool = True,
        lightrag_mode: str = "hybrid",
        chromadb_k: int = 5
    ) -> Dict[str, Any]:
        return asyncio.run(
            self.indexer.query(query, use_lightrag, use_chromadb, lightrag_mode, chromadb_k)
        )

    def query_conversations(
        self,
        query: str,
        k: int = 5,
        time_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return asyncio.run(self.indexer.query_conversations(query, k, time_filter))

    def query_structured_memory(
        self,
        query: str,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        return asyncio.run(self.indexer.query_structured_memory(query, mode))

    def get_stats(self) -> Dict[str, Any]:
        return self.indexer.get_stats()


# Convenience function
def create_hybrid_indexer(
    working_dir: str = "./graphrag/storage/index",
    chroma_dir: str = "./memory/vector_store"
) -> HybridIndexer:
    """
    Create a hybrid indexer with default configuration.

    Args:
        working_dir: LightRAG working directory
        chroma_dir: ChromaDB persistence directory

    Returns:
        HybridIndexer instance
    """
    config = IndexConfig(
        working_dir=working_dir,
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    return HybridIndexer(
        lightrag_config=config,
        chroma_persist_dir=chroma_dir
    )
