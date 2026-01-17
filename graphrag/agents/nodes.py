"""
LangGraph Workflow Nodes for IAMI Adaptive RAG

This module contains individual node functions for the retrieval workflow.
"""

import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI


# Initialize LLM
def get_llm(model: str = "deepseek-chat", temperature: float = 0):
    """Get LLM instance"""
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")
    )


async def plan_query_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the query and plan retrieval strategy.

    This node determines:
    - What type of information is needed
    - Which indexer(s) to use
    - Query parameters
    """
    query = state["query"]

    # Simple heuristics for query planning
    query_lower = query.lower()

    # Determine query type
    query_plan = {
        "use_lightrag": True,  # Default to using both
        "use_chromadb": True,
        "lightrag_mode": "hybrid",
        "chromadb_k": 5
    }

    # If query is about specific structured memory, focus on LightRAG
    structured_keywords = [
        "性格", "personality", "价值观", "values",
        "思维", "thinking", "关系", "relationship",
        "人际", "social", "特征", "traits"
    ]

    if any(keyword in query_lower for keyword in structured_keywords):
        query_plan["lightrag_mode"] = "local"  # Use local mode for specific queries

    # If query is about recent conversations or temporal events
    temporal_keywords = [
        "最近", "recently", "对话", "conversation",
        "说过", "mentioned", "讨论", "discussed"
    ]

    if any(keyword in query_lower for keyword in temporal_keywords):
        # Prioritize ChromaDB for recent conversations
        query_plan["chromadb_k"] = 10
        query_plan["use_lightrag"] = False

    state["query_plan"] = query_plan
    return state


async def retrieve_lightrag_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve from LightRAG (graph-based knowledge).
    """
    query = state["query"]
    query_plan = state.get("query_plan", {})
    indexer = state["indexer"]

    if not query_plan.get("use_lightrag", True):
        state["lightrag_docs"] = []
        return state

    try:
        # Query LightRAG
        result = await indexer.query_structured_memory(
            query=query,
            mode=query_plan.get("lightrag_mode", "hybrid")
        )

        # Extract result text
        if result.get("success"):
            state["lightrag_docs"] = [{
                "content": result.get("result", ""),
                "source": "lightrag",
                "mode": query_plan.get("lightrag_mode", "hybrid")
            }]
        else:
            state["lightrag_docs"] = []

    except Exception as e:
        print(f"LightRAG retrieval error: {e}")
        state["lightrag_docs"] = []

    return state


async def retrieve_chromadb_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve from ChromaDB (vector-based conversations).
    """
    query = state["query"]
    query_plan = state.get("query_plan", {})
    indexer = state["indexer"]

    if not query_plan.get("use_chromadb", True):
        state["chromadb_docs"] = []
        return state

    try:
        # Query ChromaDB
        results = await indexer.query_conversations(
            query=query,
            k=query_plan.get("chromadb_k", 5)
        )

        state["chromadb_docs"] = results

    except Exception as e:
        print(f"ChromaDB retrieval error: {e}")
        state["chromadb_docs"] = []

    return state


async def evaluate_relevance_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate relevance of retrieved documents.

    This node:
    1. Scores each retrieved document
    2. Filters out low-quality results
    3. Determines if results are sufficient
    """
    query = state["query"]
    lightrag_docs = state.get("lightrag_docs", [])
    chromadb_docs = state.get("chromadb_docs", [])

    # Simple relevance scoring based on ChromaDB scores
    relevant_docs = []

    # Add LightRAG results (assume high relevance)
    for doc in lightrag_docs:
        if doc.get("content"):
            relevant_docs.append({
                **doc,
                "relevance_score": 0.9  # High default score for graph results
            })

    # Add ChromaDB results with their similarity scores
    for doc in chromadb_docs:
        # ChromaDB uses distance metrics (lower is better)
        # Convert to similarity score (0-1 range)
        similarity = doc.get("similarity_score", 0)

        # Adjust threshold based on metric
        # For cosine distance, lower is better
        if similarity < 1.5:  # Threshold for relevance
            relevant_docs.append({
                **doc,
                "relevance_score": 1.0 / (1.0 + similarity)  # Convert distance to similarity
            })

    # Sort by relevance score
    relevant_docs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    state["relevant_docs"] = relevant_docs
    state["has_sufficient_results"] = len(relevant_docs) > 0

    return state


async def generate_answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final answer based on retrieved documents.
    """
    query = state["query"]
    relevant_docs = state.get("relevant_docs", [])

    if not relevant_docs:
        state["final_answer"] = "抱歉，我没有找到相关信息来回答这个问题。"
        return state

    # Prepare context from relevant documents
    context_parts = []

    for i, doc in enumerate(relevant_docs[:5], 1):  # Use top 5 results
        content = doc.get("content", "")
        source = doc.get("source", "unknown")
        score = doc.get("relevance_score", 0)

        context_parts.append(
            f"[来源 {i} - {source} - 相关度: {score:.2f}]\n{content}\n"
        )

    context = "\n---\n".join(context_parts)

    # Generate answer using LLM
    llm = get_llm()

    prompt = f"""基于以下检索到的信息，回答用户的问题。

问题: {query}

检索到的信息:
{context}

请提供一个准确、有帮助的答案。如果信息不足以完全回答问题，请诚实说明。
"""

    try:
        response = await llm.ainvoke(prompt)
        state["final_answer"] = response.content
    except Exception as e:
        print(f"Answer generation error: {e}")
        state["final_answer"] = f"生成答案时出错: {str(e)}"

    return state


# Conditional edge functions
def should_retrieve_chromadb(state: Dict[str, Any]) -> str:
    """
    Determine if ChromaDB retrieval is needed.
    """
    query_plan = state.get("query_plan", {})

    if query_plan.get("use_chromadb", True):
        return "retrieve_chromadb"
    else:
        return "evaluate"


def should_retrieve_lightrag(state: Dict[str, Any]) -> str:
    """
    Determine if LightRAG retrieval is needed.
    """
    query_plan = state.get("query_plan", {})

    if query_plan.get("use_lightrag", True):
        return "retrieve_lightrag"
    else:
        return "retrieve_chromadb"
