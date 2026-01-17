#!/usr/bin/env python3
"""
测试混合 RAG 系统（LightRAG + ChromaDB + LangGraph）

这个脚本测试：
1. ChromaDB 索引器
2. 混合索引器
3. LangGraph 自适应检索工作流
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphrag.indexer.chroma import ChromaDBIndexer
from graphrag.indexer.hybrid_indexer import HybridIndexer
from graphrag.indexer.graph_indexer import IndexConfig
from graphrag.agents import AdaptiveRAGAgent


async def test_chromadb_indexer():
    """测试 ChromaDB 索引器"""
    print("\n" + "=" * 60)
    print("测试 1: ChromaDB 索引器")
    print("=" * 60)

    # 创建 ChromaDB 索引器
    indexer = ChromaDBIndexer(
        persist_directory="./graphrag/test_data/chroma",
        collection_name="test_conversations"
    )

    # 添加测试对话
    print("\n➤ 添加测试对话...")
    conversations = [
        {
            "content": "用户讨论了他对编程的热爱，特别是 Python 和机器学习。",
            "metadata": {"topic": "programming", "date": "2024-01-15"}
        },
        {
            "content": "用户提到他最近在学习 LangGraph 和 RAG 系统，觉得很有趣。",
            "metadata": {"topic": "learning", "date": "2024-01-20"}
        },
        {
            "content": "用户表达了对开源社区的热情，并希望为更多项目做贡献。",
            "metadata": {"topic": "open_source", "date": "2024-01-25"}
        }
    ]

    for i, conv in enumerate(conversations, 1):
        conv_id = await indexer.add_conversation(
            content=conv["content"],
            metadata=conv["metadata"],
            conversation_id=f"test_conv_{i}"
        )
        print(f"  ✓ 添加对话 {conv_id}")

    # 测试搜索
    print("\n➤ 测试搜索...")
    results = await indexer.search_with_score(
        query="用户喜欢什么技术？",
        k=3
    )

    print(f"  搜索到 {len(results)} 条结果:")
    for i, result in enumerate(results, 1):
        print(f"\n  {i}. 相似度: {result['similarity_score']:.4f}")
        print(f"     内容: {result['content'][:100]}...")

    # 获取统计信息
    stats = indexer.get_stats()
    print(f"\n➤ 统计信息:")
    print(f"  - 集合名称: {stats['collection_name']}")
    print(f"  - 文档数量: {stats['document_count']}")

    print("\n✅ ChromaDB 测试完成")
    return indexer


async def test_hybrid_indexer():
    """测试混合索引器"""
    print("\n" + "=" * 60)
    print("测试 2: 混合索引器")
    print("=" * 60)

    # 创建混合索引器
    config = IndexConfig(
        working_dir="./graphrag/test_data/lightrag",
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    indexer = HybridIndexer(
        lightrag_config=config,
        chroma_persist_dir="./graphrag/test_data/chroma_hybrid",
        chroma_collection="test_hybrid"
    )

    # 测试不同类型的文档
    print("\n➤ 索引不同类型的文档...")

    test_docs = [
        {
            "id": "test_personality_1",
            "type": "personality",
            "content": "用户表现出高度的开放性和好奇心，喜欢探索新技术和学习新知识。",
            "timestamp": "2024-01-15T10:00:00"
        },
        {
            "id": "test_conv_1",
            "type": "conversation",
            "content": "今天讨论了 GraphRAG 的实现，用户对知识图谱的应用很感兴趣。",
            "timestamp": "2024-01-20T15:30:00"
        },
        {
            "id": "test_values_1",
            "type": "values",
            "content": "用户重视创新、自主性和智力成就，倾向于追求知识和技术进步。",
            "timestamp": "2024-01-25T09:00:00"
        }
    ]

    for doc in test_docs:
        result = await indexer.index_document(doc)
        print(f"\n  文档: {doc['id']}")
        print(f"  - LightRAG: {'✓' if result['lightrag'] else '✗'}")
        print(f"  - ChromaDB: {'✓' if result['chromadb'] else '✗'}")
        if result['errors']:
            print(f"  - 错误: {result['errors']}")

    # 测试查询
    print("\n➤ 测试混合查询...")

    # 查询结构化记忆（应该主要来自 LightRAG）
    print("\n  查询 1: 结构化记忆（性格特征）")
    result = await indexer.query_structured_memory(
        query="用户的性格特征是什么？"
    )
    if result.get("success"):
        print(f"  ✓ LightRAG 结果: {result['result'][:200]}...")

    # 查询对话（应该来自 ChromaDB）
    print("\n  查询 2: 对话历史")
    results = await indexer.query_conversations(
        query="用户最近讨论了什么技术？",
        k=3
    )
    print(f"  ✓ ChromaDB 找到 {len(results)} 条对话")

    # 统计信息
    stats = indexer.get_stats()
    print(f"\n➤ 统计信息:")
    print(f"  LightRAG:")
    print(f"  - 工作目录: {stats['lightrag']['working_dir']}")
    print(f"  - 文件数: {len(stats['lightrag'].get('files', []))}")
    print(f"  ChromaDB:")
    print(f"  - 集合: {stats['chromadb']['collection_name']}")
    print(f"  - 文档数: {stats['chromadb']['document_count']}")

    print("\n✅ 混合索引器测试完成")
    return indexer


async def test_adaptive_agent(indexer: HybridIndexer):
    """测试自适应 RAG 代理"""
    print("\n" + "=" * 60)
    print("测试 3: 自适应 RAG 代理（LangGraph）")
    print("=" * 60)

    # 创建自适应代理
    agent = AdaptiveRAGAgent(indexer)

    # 测试查询
    test_queries = [
        "用户的性格特征是什么？",
        "用户最近讨论了哪些技术？",
        "用户重视什么价值观？"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n➤ 查询 {i}: {query}")
        print("-" * 60)

        result = await agent.query(query)

        print(f"\n查询计划:")
        plan = result['query_plan']
        print(f"  - 使用 LightRAG: {plan.get('use_lightrag', False)}")
        print(f"  - 使用 ChromaDB: {plan.get('use_chromadb', False)}")
        print(f"  - LightRAG 模式: {plan.get('lightrag_mode', 'N/A')}")

        print(f"\n检索结果:")
        print(f"  - 相关文档数: {result['num_results']}")

        print(f"\n最终答案:")
        print(f"  {result['final_answer']}")

        if result.get('relevant_docs'):
            print(f"\n相关文档（前3个）:")
            for j, doc in enumerate(result['relevant_docs'][:3], 1):
                source = doc.get('source', 'unknown')
                score = doc.get('relevance_score', 0)
                print(f"  {j}. [{source}] 相关度: {score:.3f}")

    print("\n✅ 自适应代理测试完成")


async def test_workflow_visualization():
    """测试工作流可视化（可选）"""
    print("\n" + "=" * 60)
    print("测试 4: 工作流可视化")
    print("=" * 60)

    try:
        from graphrag.agents.retrieval_workflow import build_retrieval_workflow

        # 构建工作流
        workflow = build_retrieval_workflow()

        print("\n➤ 工作流构建成功")
        print("  工作流包含以下节点:")
        print("  1. plan_query - 查询规划")
        print("  2. retrieve_lightrag - LightRAG 检索")
        print("  3. retrieve_chromadb - ChromaDB 检索")
        print("  4. evaluate_relevance - 相关性评估")
        print("  5. generate_answer - 答案生成")

        # 尝试生成图形（如果可用）
        try:
            # LangGraph 可能支持可视化
            print("\n  提示: 可以使用 LangGraph Studio 可视化工作流")
        except Exception as e:
            print(f"\n  注意: 可视化功能不可用 ({e})")

        print("\n✅ 工作流可视化测试完成")

    except Exception as e:
        print(f"\n⚠️  工作流可视化测试跳过: {e}")


async def cleanup():
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("清理测试数据")
    print("=" * 60)

    test_dirs = [
        "./graphrag/test_data/chroma",
        "./graphrag/test_data/chroma_hybrid",
        "./graphrag/test_data/lightrag"
    ]

    import shutil

    for test_dir in test_dirs:
        if Path(test_dir).exists():
            shutil.rmtree(test_dir)
            print(f"  ✓ 删除 {test_dir}")

    print("\n✅ 清理完成")


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("IAMI 混合 RAG 系统测试")
    print("=" * 60)
    print(f"时间: {datetime.now().isoformat()}")

    # 检查环境变量
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("\n⚠️  警告: DEEPSEEK_API_KEY 未设置")
        print("   某些测试可能会失败")

    try:
        # 运行测试
        await test_chromadb_indexer()
        hybrid_indexer = await test_hybrid_indexer()
        await test_adaptive_agent(hybrid_indexer)
        await test_workflow_visualization()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

        # 询问是否清理
        print("\n是否清理测试数据？(y/n): ", end="")
        # response = input().strip().lower()
        # if response == 'y':
        #     await cleanup()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
