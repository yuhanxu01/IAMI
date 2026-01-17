#!/usr/bin/env python3
"""
IAMI GraphRAG MCP Server
用于 Claude Code 集成的 Model Context Protocol 服务器
"""
import os
import sys
import json
import asyncio
from typing import Any, Dict, List
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP not available. Install with: pip install mcp")

from graphrag.indexer.data_loader import IAMIDataLoader
from graphrag.indexer.graph_indexer import IAMIGraphIndexer, IndexConfig
from graphrag.indexer.hybrid_indexer import HybridIndexer
from graphrag.agents import AdaptiveRAGAgent


class IAMIGraphRAGServer:
    """IAMI GraphRAG MCP 服务器"""

    def __init__(self):
        self.server = Server("iami-graphrag")
        self.indexer = None
        self.hybrid_indexer = None
        self.adaptive_agent = None
        self.loader = IAMIDataLoader()

        # 初始化索引器
        self._init_indexer()

        # 注册工具
        self._register_tools()

    def _init_indexer(self):
        """初始化 GraphRAG 索引器"""
        config = IndexConfig(
            working_dir=os.getenv("GRAPHRAG_INDEX_DIR", "./graphrag/storage/index"),
            llm_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            api_base=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )

        # 初始化 LightRAG 索引器（向后兼容）
        self.indexer = IAMIGraphIndexer(config)

        # 初始化混合索引器（LightRAG + ChromaDB）
        self.hybrid_indexer = HybridIndexer(
            lightrag_config=config,
            chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./memory/vector_store"),
            chroma_collection=os.getenv("CHROMA_COLLECTION", "iami_conversations")
        )

        # 初始化自适应 RAG 代理
        self.adaptive_agent = AdaptiveRAGAgent(self.hybrid_indexer)

    def _register_tools(self):
        """注册 MCP 工具"""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """列出所有可用工具"""
            return [
                types.Tool(
                    name="iami_query",
                    description="查询 IAMI 知识图谱。支持关于用户的性格、价值观、思维模式、人际关系、环境等各方面的问题。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "要查询的问题"
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["naive", "local", "global", "hybrid"],
                                "description": "查询模式：naive(简单), local(局部), global(全局), hybrid(混合，推荐)",
                                "default": "hybrid"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回结果数量",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="iami_rebuild_index",
                    description="重建 IAMI 知识图谱索引。当记忆数据更新时使用此工具重新索引。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "force": {
                                "type": "boolean",
                                "description": "是否强制重建（即使索引已存在）",
                                "default": False
                            }
                        }
                    }
                ),
                types.Tool(
                    name="iami_get_relationships",
                    description="获取用户的人际关系网络信息。返回关系图谱数据。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "person_name": {
                                "type": "string",
                                "description": "特定人物名称（可选）"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="iami_get_timeline",
                    description="获取用户思想演变的时间轴。查看用户思想如何随时间变化。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "起始日期（可选，ISO格式）"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "结束日期（可选，ISO格式）"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="iami_get_profile",
                    description="获取用户的综合人物画像。包括性格、价值观、思维模式等核心特征。",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="iami_index_stats",
                    description="获取索引统计信息。查看当前索引状态和文档数量。",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="iami_adaptive_query",
                    description="使用自适应 RAG 策略查询。自动选择最佳检索策略（LightRAG 图谱 + ChromaDB 向量），智能路由和相关性评估。推荐用于复杂查询。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "要查询的问题"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="iami_index_hybrid",
                    description="使用混合索引器索引文档。自动将文档路由到 LightRAG（结构化记忆）或 ChromaDB（对话历史）。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_type": {
                                "type": "string",
                                "description": "文档类型（personality, values, conversation 等）"
                            },
                            "content": {
                                "type": "string",
                                "description": "文档内容"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "文档元数据（可选）",
                                "additionalProperties": True
                            }
                        },
                        "required": ["doc_type", "content"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """处理工具调用"""

            if not arguments:
                arguments = {}

            try:
                if name == "iami_query":
                    return await self._handle_query(arguments)

                elif name == "iami_rebuild_index":
                    return await self._handle_rebuild_index(arguments)

                elif name == "iami_get_relationships":
                    return await self._handle_get_relationships(arguments)

                elif name == "iami_get_timeline":
                    return await self._handle_get_timeline(arguments)

                elif name == "iami_get_profile":
                    return await self._handle_get_profile(arguments)

                elif name == "iami_index_stats":
                    return await self._handle_index_stats(arguments)

                elif name == "iami_adaptive_query":
                    return await self._handle_adaptive_query(arguments)

                elif name == "iami_index_hybrid":
                    return await self._handle_index_hybrid(arguments)

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _handle_query(self, args: dict) -> list[types.TextContent]:
        """处理查询请求"""
        query = args.get("query", "")
        mode = args.get("mode", "hybrid")
        top_k = args.get("top_k", 5)

        result = await self.indexer.query(query, mode=mode, top_k=top_k)

        if result["success"]:
            response = f"# 查询结果\n\n**问题**: {query}\n**模式**: {mode}\n\n{result['result']}"
        else:
            response = f"查询失败: {result.get('error', 'Unknown error')}"

        return [types.TextContent(type="text", text=response)]

    async def _handle_rebuild_index(self, args: dict) -> list[types.TextContent]:
        """处理重建索引请求"""
        force = args.get("force", False)

        # 加载所有文档
        documents = self.loader.load_all_data()

        # 索引文档
        results = await self.indexer.index_documents(documents)

        response = f"""# 索引重建完成

- 总文档数: {results['total']}
- 成功: {results['success']}
- 失败: {results['failed']}

"""
        if results['errors']:
            response += "## 错误:\n"
            for error in results['errors'][:5]:  # 只显示前5个错误
                response += f"- {error['doc_id']}: {error['error']}\n"

        return [types.TextContent(type="text", text=response)]

    async def _handle_get_relationships(self, args: dict) -> list[types.TextContent]:
        """处理获取关系网络请求"""
        person_name = args.get("person_name")

        # 读取关系网络文件
        network_file = Path("memory/relationships/network.json")

        if not network_file.exists():
            return [types.TextContent(
                type="text",
                text="关系网络文件不存在"
            )]

        with open(network_file, 'r', encoding='utf-8') as f:
            network_data = json.load(f)

        if person_name:
            # 查询特定人物
            response = f"# {person_name} 的关系信息\n\n"
            response += json.dumps(network_data, ensure_ascii=False, indent=2)
        else:
            # 返回整个网络概览
            response = "# 人际关系网络\n\n"
            response += json.dumps(network_data, ensure_ascii=False, indent=2)

        return [types.TextContent(type="text", text=response)]

    async def _handle_get_timeline(self, args: dict) -> list[types.TextContent]:
        """处理获取时间轴请求"""
        snapshots_file = Path("memory/timeline/snapshots.json")

        if not snapshots_file.exists():
            return [types.TextContent(
                type="text",
                text="时间轴文件不存在"
            )]

        with open(snapshots_file, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)

        response = "# 思想演变时间轴\n\n"
        response += json.dumps(timeline_data, ensure_ascii=False, indent=2)

        return [types.TextContent(type="text", text=response)]

    async def _handle_get_profile(self, args: dict) -> list[types.TextContent]:
        """处理获取人物画像请求"""
        profile_file = Path("analysis/profile.json")

        if not profile_file.exists():
            return [types.TextContent(
                type="text",
                text="人物画像文件不存在"
            )]

        with open(profile_file, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)

        response = "# 综合人物画像\n\n"
        response += json.dumps(profile_data, ensure_ascii=False, indent=2)

        return [types.TextContent(type="text", text=response)]

    async def _handle_index_stats(self, args: dict) -> list[types.TextContent]:
        """处理获取索引统计请求"""
        stats = self.indexer.get_stats()

        response = f"""# 索引统计信息

- 工作目录: {stats['working_dir']}
- 存在: {stats['exists']}
- 文件数: {len(stats['files'])}

## 文件列表:
"""
        for f in stats['files']:
            response += f"- {f}\n"

        return [types.TextContent(type="text", text=response)]

    async def _handle_adaptive_query(self, args: dict) -> list[types.TextContent]:
        """处理自适应查询请求"""
        query = args.get("query", "")

        if not self.adaptive_agent:
            return [types.TextContent(
                type="text",
                text="自适应代理未初始化"
            )]

        try:
            # 使用自适应 RAG 代理查询
            result = await self.adaptive_agent.query(query)

            response = f"""# 自适应查询结果

**问题**: {query}

**查询计划**:
- 使用 LightRAG: {result['query_plan'].get('use_lightrag', False)}
- 使用 ChromaDB: {result['query_plan'].get('use_chromadb', False)}
- LightRAG 模式: {result['query_plan'].get('lightrag_mode', 'N/A')}
- ChromaDB 结果数: {result['query_plan'].get('chromadb_k', 0)}

**检索到的文档数**: {result['num_results']}

---

{result['final_answer']}

---

**相关文档**:
"""
            # 添加相关文档信息
            for i, doc in enumerate(result.get('relevant_docs', [])[:3], 1):
                source = doc.get('source', 'unknown')
                score = doc.get('relevance_score', 0)
                response += f"\n{i}. [{source}] 相关度: {score:.3f}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"自适应查询失败: {str(e)}"
            )]

    async def _handle_index_hybrid(self, args: dict) -> list[types.TextContent]:
        """处理混合索引请求"""
        doc_type = args.get("doc_type", "")
        content = args.get("content", "")
        metadata = args.get("metadata", {})

        if not self.hybrid_indexer:
            return [types.TextContent(
                type="text",
                text="混合索引器未初始化"
            )]

        try:
            # 构建文档对象
            doc = {
                "id": f"{doc_type}_{hash(content) % 10000}",
                "type": doc_type,
                "content": content,
                "metadata": metadata
            }

            # 添加时间戳
            from datetime import datetime
            doc["timestamp"] = datetime.now().isoformat()

            # 索引文档
            result = await self.hybrid_indexer.index_document(doc)

            response = f"""# 混合索引结果

**文档类型**: {doc_type}
**文档 ID**: {result['doc_id']}

**索引状态**:
- LightRAG: {'✓' if result['lightrag'] else '✗'}
- ChromaDB: {'✓' if result['chromadb'] else '✗'}
"""

            if result['errors']:
                response += "\n**错误**:\n"
                for error in result['errors']:
                    response += f"- {error}\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"混合索引失败: {str(e)}"
            )]

    async def run(self):
        """运行 MCP 服务器"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="iami-graphrag",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """主函数"""
    if not MCP_AVAILABLE:
        print("Error: MCP not installed. Install with: pip install mcp")
        sys.exit(1)

    server = IAMIGraphRAGServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
