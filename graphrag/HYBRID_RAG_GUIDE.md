# IAMI 混合 RAG 架构指南

## 📋 概述

IAMI 现在支持混合 RAG 架构，结合了 **LightRAG** (知识图谱) 和 **ChromaDB** (向量数据库) 的优势，并使用 **LangGraph** 实现自适应检索工作流。

## 🏗️ 架构设计

```
┌─────────────────────────────────────┐
│   LangGraph Workflow (Agent 层)    │
│   ├─ Query Planner Agent           │
│   ├─ Memory Retriever Agent        │
│   ├─ Relevance Evaluator Agent     │
│   └─ Response Generator Agent      │
└──────────┬──────────────────────────┘
           │
           ├─► LightRAG (知识图谱检索)
           │   • 结构化记忆
           │   • 实体关系
           │
           ├─► ChromaDB (向量检索)
           │   • 对话历史
           │   • 非结构化内容
           │
           └─► DeepSeek API (LLM)
```

## 🎯 核心组件

### 1. ChromaDB 索引器 (`indexer/chroma/`)
专门用于对话历史和非结构化内容的向量检索。

**适用场景**:
- 对话记录
- 临时笔记
- 时间敏感的查询

### 2. 混合索引器 (`indexer/hybrid_indexer.py`)
智能路由文档到合适的索引系统。

**路由策略**:
- **LightRAG**: personality, values, relationships, thinking_patterns
- **ChromaDB**: conversation, short_term_memory, notes
- **双重索引**: 其他重要文档

### 3. LangGraph 工作流 (`agents/retrieval_workflow.py`)
自适应检索流程编排。

**工作流节点**:
1. **Plan Query** - 分析查询，制定检索策略
2. **Retrieve LightRAG** - 从知识图谱检索
3. **Retrieve ChromaDB** - 从向量库检索
4. **Evaluate Relevance** - 评估结果相关性
5. **Generate Answer** - 生成最终答案

## 📦 安装

### 1. 安装依赖

```bash
cd graphrag
pip install -r requirements.txt
```

新增依赖包括:
- `langgraph` - 工作流编排
- `langchain-core`, `langchain-openai` - LangChain 核心
- `chromadb`, `langchain-chroma` - ChromaDB 向量库

### 2. 环境变量

在 `.env` 文件中添加:

```bash
# DeepSeek API
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# ChromaDB 配置 (可选)
CHROMA_PERSIST_DIR=./memory/vector_store
CHROMA_COLLECTION=iami_conversations

# LightRAG 配置 (可选)
GRAPHRAG_INDEX_DIR=./graphrag/storage/index
```

## 🚀 使用方法

### 方式 1: 通过 MCP Server (推荐)

MCP Server 已更新，现在包含自适应查询工具。

#### 可用工具:

1. **iami_adaptive_query** - 自适应 RAG 查询 (新增)
   ```python
   # 自动选择最佳检索策略
   {
     "query": "用户最近讨论了什么技术？"
   }
   ```

2. **iami_index_hybrid** - 混合索引 (新增)
   ```python
   # 智能路由文档到合适的索引器
   {
     "doc_type": "conversation",
     "content": "今天讨论了 GraphRAG...",
     "metadata": {"topic": "tech"}
   }
   ```

3. **iami_query** - 传统 LightRAG 查询 (保留)
   ```python
   {
     "query": "用户的性格特征？",
     "mode": "hybrid"
   }
   ```

#### 启动 MCP Server:

```bash
python graphrag/server/mcp_server.py
```

### 方式 2: Python API

#### 示例 1: 使用混合索引器

```python
import asyncio
from graphrag.indexer.hybrid_indexer import HybridIndexer
from graphrag.indexer.graph_indexer import IndexConfig

async def main():
    # 创建混合索引器
    config = IndexConfig(api_key="your_key")
    indexer = HybridIndexer(lightrag_config=config)

    # 索引文档
    doc = {
        "id": "conv_123",
        "type": "conversation",
        "content": "用户讨论了机器学习...",
        "timestamp": "2024-01-20T10:00:00"
    }

    result = await indexer.index_document(doc)
    print(result)

    # 查询
    results = await indexer.query(
        query="用户对机器学习的看法？",
        use_lightrag=True,
        use_chromadb=True
    )
    print(results)

asyncio.run(main())
```

#### 示例 2: 使用自适应代理

```python
import asyncio
from graphrag.agents import AdaptiveRAGAgent
from graphrag.indexer.hybrid_indexer import HybridIndexer

async def main():
    # 创建索引器和代理
    indexer = HybridIndexer()
    agent = AdaptiveRAGAgent(indexer)

    # 自适应查询
    result = await agent.query("用户最近的兴趣爱好是什么？")

    print(f"查询计划: {result['query_plan']}")
    print(f"最终答案: {result['final_answer']}")
    print(f"相关文档: {result['num_results']}")

asyncio.run(main())
```

#### 示例 3: 仅使用 ChromaDB

```python
import asyncio
from graphrag.indexer.chroma import ChromaDBIndexer

async def main():
    # 创建 ChromaDB 索引器
    indexer = ChromaDBIndexer()

    # 添加对话
    conv_id = await indexer.add_conversation(
        content="讨论了 Python 编程...",
        metadata={"topic": "programming"}
    )

    # 搜索
    results = await indexer.search_with_score(
        query="Python 相关的讨论",
        k=5
    )

    for result in results:
        print(f"相似度: {result['similarity_score']}")
        print(f"内容: {result['content']}")

asyncio.run(main())
```

## 🧪 测试

运行测试脚本验证系统:

```bash
python graphrag/test_hybrid_system.py
```

测试内容:
1. ✅ ChromaDB 索引器
2. ✅ 混合索引器路由
3. ✅ 自适应 RAG 代理
4. ✅ LangGraph 工作流

## 📊 查询策略

### 自适应查询规则

系统会根据查询内容自动选择策略:

| 查询类型 | 检索策略 | 示例 |
|---------|---------|------|
| 结构化记忆 | LightRAG (local) | "用户的性格特征？" |
| 对话历史 | ChromaDB only | "最近讨论了什么？" |
| 综合查询 | 两者 (hybrid) | "用户对技术的态度？" |

### 关键词触发

**LightRAG 优先**:
- 性格、personality
- 价值观、values
- 思维、thinking
- 关系、relationship

**ChromaDB 优先**:
- 最近、recently
- 对话、conversation
- 讨论、discussed
- 提到、mentioned

## 🎛️ 配置选项

### 索引器配置

```python
# LightRAG 配置
IndexConfig(
    working_dir="./graphrag/storage/index",
    llm_model="deepseek-chat",
    embedding_model="text-embedding-3-small",
    api_base="https://api.deepseek.com/v1",
    api_key="your_key"
)

# ChromaDB 配置
ChromaDBIndexer(
    persist_directory="./memory/vector_store",
    collection_name="iami_conversations",
    embedding_model="text-embedding-3-small"
)
```

### 查询参数

```python
# LightRAG 查询模式
modes = ["naive", "local", "global", "hybrid"]

# ChromaDB 检索数量
k = 5  # 返回前 5 个结果
```

## 🔍 监控和调试

### 查看索引统计

```python
stats = indexer.get_stats()
print(stats)
# {
#   "lightrag": {...},
#   "chromadb": {...}
# }
```

### 查询执行计划

```python
result = await agent.query("...")
print(result['query_plan'])
# {
#   "use_lightrag": True,
#   "use_chromadb": True,
#   "lightrag_mode": "hybrid",
#   "chromadb_k": 5
# }
```

## 🚨 常见问题

### Q1: ChromaDB 持久化失败
**A**: 确保 `persist_directory` 有写权限，路径存在。

### Q2: LangGraph 导入错误
**A**: 运行 `pip install -r requirements.txt` 安装所有依赖。

### Q3: 查询速度慢
**A**:
- 减少 `chromadb_k` 数量
- 使用 LightRAG 的 `local` 模式
- 只查询必要的索引器

### Q4: 内存占用高
**A**: ChromaDB 会缓存向量，可以定期重启或使用更小的集合。

## 📈 性能优化

1. **批量索引**: 使用 `index_documents()` 而不是多次 `index_document()`
2. **缓存**: LangGraph 节点可以缓存中间结果
3. **并行检索**: LightRAG 和 ChromaDB 可以并行查询
4. **过滤**: 使用 ChromaDB 的 metadata 过滤减少检索范围

## 🔗 参考资料

- [LightRAG 文档](https://github.com/HKUDS/LightRAG)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [local-rag-researcher 参考项目](https://github.com/kaymen99/local-rag-researcher-deepseek)

## 📝 更新日志

### v1.0.0 (2024-01-XX)
- ✅ 添加 ChromaDB 向量索引
- ✅ 实现混合索引器
- ✅ 构建 LangGraph 自适应工作流
- ✅ 更新 MCP Server 工具
- ✅ 添加测试套件

---

**注意**: 这是第一阶段实现。后续可以添加:
- 网络搜索降级（Tavily API）
- 更复杂的相关性评估
- 多轮对话支持
- 可视化监控面板
