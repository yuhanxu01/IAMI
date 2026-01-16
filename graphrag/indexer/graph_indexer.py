"""
IAMI Graph Indexer - 使用 LightRAG 构建知识图谱
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm import openai_complete_if_cache, openai_embedding
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    print("Warning: LightRAG not installed. Install with: pip install lightrag")


@dataclass
class IndexConfig:
    """索引配置"""
    working_dir: str = "./graphrag/storage/index"
    llm_model: str = "deepseek-chat"
    embedding_model: str = "text-embedding-3-small"
    api_base: str = "https://api.deepseek.com/v1"
    api_key: Optional[str] = None


class IAMIGraphIndexer:
    """IAMI 知识图谱索引器"""

    def __init__(self, config: IndexConfig):
        self.config = config
        self.rag = None

        if not LIGHTRAG_AVAILABLE:
            raise ImportError("LightRAG is required. Install with: pip install lightrag")

        # 确保工作目录存在
        os.makedirs(config.working_dir, exist_ok=True)

        # 初始化 LightRAG
        self._init_lightrag()

    def _init_lightrag(self):
        """初始化 LightRAG 实例"""

        # 设置 API key
        if self.config.api_key:
            os.environ["OPENAI_API_KEY"] = self.config.api_key

        # 自定义 LLM 函数（适配 DeepSeek）
        async def deepseek_llm_func(
            prompt, system_prompt=None, history_messages=[], **kwargs
        ) -> str:
            return await openai_complete_if_cache(
                model=self.config.llm_model,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                **kwargs
            )

        # 自定义 Embedding 函数
        async def deepseek_embedding_func(texts: list[str]) -> list[list[float]]:
            return await openai_embedding(
                texts=texts,
                model=self.config.embedding_model,
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )

        # 初始化 LightRAG
        self.rag = LightRAG(
            working_dir=self.config.working_dir,
            llm_model_func=deepseek_llm_func,
            embedding_func=deepseek_embedding_func,
        )

    async def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """索引文档列表"""
        if not self.rag:
            raise RuntimeError("LightRAG not initialized")

        results = {
            "total": len(documents),
            "success": 0,
            "failed": 0,
            "errors": []
        }

        for doc in documents:
            try:
                # 准备文档文本
                text = self._prepare_document_text(doc)

                # 插入到 LightRAG
                await self.rag.ainsert(text)

                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "doc_id": doc.get("id"),
                    "error": str(e)
                })
                print(f"Error indexing document {doc.get('id')}: {e}")

        return results

    def _prepare_document_text(self, doc: Dict[str, Any]) -> str:
        """准备文档文本用于索引"""
        parts = []

        # 添加文档类型和ID
        parts.append(f"[文档类型: {doc.get('type', 'unknown')}]")
        parts.append(f"[文档ID: {doc.get('id', 'unknown')}]")

        # 添加时间戳
        if 'timestamp' in doc:
            parts.append(f"[时间: {doc['timestamp']}]")

        # 添加分类
        if 'category' in doc:
            parts.append(f"[分类: {doc['category']}]")

        # 添加人物名称（如果是人物档案）
        if doc.get('type') == 'person_profile' and 'person_name' in doc:
            parts.append(f"[人物: {doc['person_name']}]")

        # 添加内容
        parts.append("\n---\n")
        parts.append(doc.get('content', ''))

        return "\n".join(parts)

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """查询知识图谱"""
        if not self.rag:
            raise RuntimeError("LightRAG not initialized")

        try:
            # LightRAG 查询模式：naive, local, global, hybrid
            result = await self.rag.aquery(
                query=query,
                param=QueryParam(mode=mode, top_k=top_k)
            )

            return {
                "success": True,
                "query": query,
                "mode": mode,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }

    async def update_document(self, doc: Dict[str, Any]) -> bool:
        """更新单个文档"""
        try:
            text = self._prepare_document_text(doc)
            await self.rag.ainsert(text)
            return True
        except Exception as e:
            print(f"Error updating document {doc.get('id')}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        working_dir = Path(self.config.working_dir)

        stats = {
            "working_dir": str(working_dir),
            "exists": working_dir.exists(),
            "files": []
        }

        if working_dir.exists():
            stats["files"] = [f.name for f in working_dir.iterdir()]

        return stats


# 同步包装器
class IAMIGraphIndexerSync:
    """同步版本的索引器"""

    def __init__(self, config: IndexConfig):
        self.indexer = IAMIGraphIndexer(config)

    def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        return asyncio.run(self.indexer.index_documents(documents))

    def query(self, query: str, mode: str = "hybrid", top_k: int = 5) -> Dict[str, Any]:
        return asyncio.run(self.indexer.query(query, mode, top_k))

    def update_document(self, doc: Dict[str, Any]) -> bool:
        return asyncio.run(self.indexer.update_document(doc))

    def get_stats(self) -> Dict[str, Any]:
        return self.indexer.get_stats()


if __name__ == "__main__":
    # 测试
    from data_loader import IAMIDataLoader

    config = IndexConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        working_dir="./graphrag/storage/test_index"
    )

    indexer = IAMIGraphIndexerSync(config)

    # 加载数据
    loader = IAMIDataLoader()
    docs = loader.load_all_data()

    print(f"Indexing {len(docs)} documents...")
    results = indexer.index_documents(docs)
    print(f"Results: {results}")

    # 测试查询
    print("\nTesting query...")
    result = indexer.query("用户的性格特征是什么？")
    print(result)
