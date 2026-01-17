"""
LangGraph Retrieval Workflow for IAMI

This module implements an adaptive RAG workflow using LangGraph.
It orchestrates retrieval from multiple sources (LightRAG + ChromaDB)
and intelligently routes queries based on content type.
"""

from typing import TypedDict, Annotated, Dict, Any, List
from langgraph.graph import StateGraph, END
from .nodes import (
    plan_query_node,
    retrieve_lightrag_node,
    retrieve_chromadb_node,
    evaluate_relevance_node,
    generate_answer_node,
    should_retrieve_chromadb
)


class RetrievalState(TypedDict):
    """
    State for the retrieval workflow.

    This state is passed between all nodes in the graph.
    """
    # Input
    query: str
    indexer: Any  # HybridIndexer instance

    # Planning
    query_plan: Dict[str, Any]

    # Retrieved documents
    lightrag_docs: List[Dict[str, Any]]
    chromadb_docs: List[Dict[str, Any]]

    # Evaluated results
    relevant_docs: List[Dict[str, Any]]
    has_sufficient_results: bool

    # Output
    final_answer: str


def build_retrieval_workflow() -> StateGraph:
    """
    Build the LangGraph retrieval workflow.

    Workflow:
    1. Plan Query → Analyze query and determine retrieval strategy
    2. Retrieve (LightRAG) → Get graph-based knowledge
    3. Retrieve (ChromaDB) → Get vector-based conversations
    4. Evaluate Relevance → Score and filter results
    5. Generate Answer → Create final response

    Returns:
        Compiled StateGraph
    """
    # Create workflow
    workflow = StateGraph(RetrievalState)

    # Add nodes
    workflow.add_node("plan_query", plan_query_node)
    workflow.add_node("retrieve_lightrag", retrieve_lightrag_node)
    workflow.add_node("retrieve_chromadb", retrieve_chromadb_node)
    workflow.add_node("evaluate_relevance", evaluate_relevance_node)
    workflow.add_node("generate_answer", generate_answer_node)

    # Set entry point
    workflow.set_entry_point("plan_query")

    # Add edges
    # Plan → Retrieve LightRAG
    workflow.add_edge("plan_query", "retrieve_lightrag")

    # LightRAG → ChromaDB (conditional)
    workflow.add_conditional_edges(
        "retrieve_lightrag",
        should_retrieve_chromadb,
        {
            "retrieve_chromadb": "retrieve_chromadb",
            "evaluate": "evaluate_relevance"
        }
    )

    # ChromaDB → Evaluate
    workflow.add_edge("retrieve_chromadb", "evaluate_relevance")

    # Evaluate → Generate
    workflow.add_edge("evaluate_relevance", "generate_answer")

    # Generate → End
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


class AdaptiveRAGAgent:
    """
    High-level agent interface for adaptive RAG queries.

    This wraps the LangGraph workflow with a simple API.
    """

    def __init__(self, indexer):
        """
        Initialize the agent.

        Args:
            indexer: HybridIndexer instance
        """
        self.indexer = indexer
        self.workflow = build_retrieval_workflow()

    async def query(self, query: str) -> Dict[str, Any]:
        """
        Execute an adaptive RAG query.

        Args:
            query: User query string

        Returns:
            Dictionary with:
            - final_answer: Generated response
            - relevant_docs: Retrieved documents
            - query_plan: Execution plan
        """
        # Initialize state
        initial_state = {
            "query": query,
            "indexer": self.indexer,
            "query_plan": {},
            "lightrag_docs": [],
            "chromadb_docs": [],
            "relevant_docs": [],
            "has_sufficient_results": False,
            "final_answer": ""
        }

        # Run workflow
        final_state = await self.workflow.ainvoke(initial_state)

        # Return results
        return {
            "query": query,
            "final_answer": final_state.get("final_answer", ""),
            "relevant_docs": final_state.get("relevant_docs", []),
            "query_plan": final_state.get("query_plan", {}),
            "num_results": len(final_state.get("relevant_docs", []))
        }

    async def stream_query(self, query: str):
        """
        Stream the workflow execution (for observability).

        Args:
            query: User query string

        Yields:
            State updates as the workflow progresses
        """
        initial_state = {
            "query": query,
            "indexer": self.indexer,
            "query_plan": {},
            "lightrag_docs": [],
            "chromadb_docs": [],
            "relevant_docs": [],
            "has_sufficient_results": False,
            "final_answer": ""
        }

        async for state in self.workflow.astream(initial_state):
            yield state


# Synchronous wrapper
class AdaptiveRAGAgentSync:
    """Synchronous version of AdaptiveRAGAgent"""

    def __init__(self, indexer):
        import asyncio
        self.agent = AdaptiveRAGAgent(indexer)
        self.loop = asyncio.get_event_loop()

    def query(self, query: str) -> Dict[str, Any]:
        """
        Execute a synchronous query.

        Args:
            query: User query string

        Returns:
            Query results
        """
        import asyncio
        return asyncio.run(self.agent.query(query))


# Convenience function
def create_adaptive_agent(indexer):
    """
    Create an adaptive RAG agent.

    Args:
        indexer: HybridIndexer instance

    Returns:
        AdaptiveRAGAgent instance
    """
    return AdaptiveRAGAgent(indexer)
