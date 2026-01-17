"""
ChromaDB Indexer for IAMI Memory System

This module provides ChromaDB-based vector indexing for conversation histories
and unstructured content. Works alongside LightRAG for hybrid retrieval.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChromaDBIndexer:
    """
    ChromaDB indexer for IAMI memory system.

    Specialized for:
    - Conversation histories
    - Unstructured notes
    - Temporal memory snapshots
    """

    def __init__(
        self,
        persist_directory: str = "./memory/vector_store",
        collection_name: str = "iami_conversations",
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        Initialize ChromaDB indexer.

        Args:
            persist_directory: Path to persist ChromaDB data
            collection_name: Name of the ChromaDB collection
            embedding_model: OpenAI embedding model to use
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_base=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
        )

        # Initialize LangChain Chroma wrapper
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings
        )

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )

    async def add_conversation(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Add a conversation to the vector store.

        Args:
            content: Conversation content
            metadata: Optional metadata (timestamp, participants, etc.)
            conversation_id: Optional conversation ID

        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}

        # Add timestamp if not present
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().isoformat()

        # Add document type
        metadata["doc_type"] = "conversation"

        # Generate ID if not provided
        if conversation_id is None:
            conversation_id = f"conv_{datetime.now().timestamp()}"

        # Split text if too long
        chunks = self.text_splitter.split_text(content)

        if len(chunks) == 1:
            # Single chunk - add directly
            self.vectorstore.add_texts(
                texts=[content],
                metadatas=[metadata],
                ids=[conversation_id]
            )
            return conversation_id
        else:
            # Multiple chunks - add with chunk IDs
            chunk_ids = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{conversation_id}_chunk_{i}"
                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(chunks)

                self.vectorstore.add_texts(
                    texts=[chunk],
                    metadatas=[chunk_metadata],
                    ids=[chunk_id]
                )
                chunk_ids.append(chunk_id)

            return conversation_id

    async def add_memory_snapshot(
        self,
        memory_type: str,
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a memory snapshot (personality, values, etc.) to the vector store.

        Args:
            memory_type: Type of memory (personality, values, thinking_patterns, etc.)
            content: Memory content (can be JSON string or text)
            timestamp: ISO format timestamp
            metadata: Additional metadata

        Returns:
            Document ID
        """
        if metadata is None:
            metadata = {}

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        metadata.update({
            "doc_type": "memory_snapshot",
            "memory_type": memory_type,
            "timestamp": timestamp
        })

        doc_id = f"snapshot_{memory_type}_{timestamp}"

        self.vectorstore.add_texts(
            texts=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )

        return doc_id

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.

        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of documents with content and metadata
        """
        # Build filter if provided
        if filter_dict:
            results = self.vectorstore.similarity_search(
                query,
                k=k,
                filter=filter_dict
            )
        else:
            results = self.vectorstore.similarity_search(query, k=k)

        # Format results
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })

        return formatted_results

    async def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with similarity scores.

        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of documents with content, metadata, and similarity scores
        """
        if filter_dict:
            results = self.vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict
            )
        else:
            results = self.vectorstore.similarity_search_with_score(query, k=k)

        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(score)
            })

        return formatted_results

    async def delete_by_id(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted successfully
        """
        try:
            self.vectorstore.delete([doc_id])
            return True
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
            return False

    async def reset_collection(self) -> bool:
        """
        Reset (delete) the entire collection.

        Returns:
            True if reset successfully
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            # Recreate the vectorstore
            self.vectorstore = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
            return True
        except Exception as e:
            print(f"Error resetting collection: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection stats
        """
        collection = self.client.get_collection(name=self.collection_name)
        count = collection.count()

        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_directory": self.persist_directory
        }


# Convenience function for initialization
def create_chroma_indexer(
    persist_directory: str = "./memory/vector_store",
    collection_name: str = "iami_conversations"
) -> ChromaDBIndexer:
    """
    Create and return a ChromaDB indexer instance.

    Args:
        persist_directory: Path to persist ChromaDB data
        collection_name: Name of the ChromaDB collection

    Returns:
        ChromaDBIndexer instance
    """
    return ChromaDBIndexer(
        persist_directory=persist_directory,
        collection_name=collection_name
    )
