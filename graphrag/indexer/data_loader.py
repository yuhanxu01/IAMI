"""
IAMI Data Loader - 加载和预处理记忆数据
"""
import json
import glob
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class IAMIDataLoader:
    """加载 IAMI 记忆系统的所有数据"""

    def __init__(self, base_path: str = "./memory"):
        self.base_path = Path(base_path)

    def load_all_data(self) -> List[Dict[str, Any]]:
        """加载所有数据源"""
        documents = []

        # 加载长期记忆
        documents.extend(self._load_long_term_memory())

        # 加载短期记忆
        documents.extend(self._load_short_term_memory())

        # 加载人际关系
        documents.extend(self._load_relationships())

        # 加载环境系统
        documents.extend(self._load_environment())

        # 加载时间轴
        documents.extend(self._load_timeline())

        # 加载对话历史
        documents.extend(self._load_conversations())

        return documents

    def _load_long_term_memory(self) -> List[Dict[str, Any]]:
        """加载长期记忆（性格、价值观、思维模式等）"""
        docs = []
        long_term_path = self.base_path / "long_term"

        if not long_term_path.exists():
            return docs

        for json_file in long_term_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                docs.append({
                    "id": f"long_term_{json_file.stem}",
                    "source": str(json_file),
                    "type": "long_term_memory",
                    "category": json_file.stem,
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": data,
                    "timestamp": data.get("last_updated", datetime.now().isoformat())
                })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        return docs

    def _load_short_term_memory(self) -> List[Dict[str, Any]]:
        """加载短期记忆"""
        docs = []
        short_term_path = self.base_path / "short_term"

        if not short_term_path.exists():
            return docs

        for json_file in short_term_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                docs.append({
                    "id": f"short_term_{json_file.stem}",
                    "source": str(json_file),
                    "type": "short_term_memory",
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": data,
                    "timestamp": data.get("timestamp", datetime.now().isoformat())
                })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        return docs

    def _load_relationships(self) -> List[Dict[str, Any]]:
        """加载人际关系网络"""
        docs = []
        rel_path = self.base_path / "relationships"

        if not rel_path.exists():
            return docs

        # 加载关系网络 JSON
        for json_file in rel_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                docs.append({
                    "id": f"relationship_{json_file.stem}",
                    "source": str(json_file),
                    "type": "relationship_network",
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": data,
                    "timestamp": data.get("last_updated", datetime.now().isoformat())
                })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        # 加载人物档案 Markdown
        for md_file in rel_path.glob("*.md"):
            if md_file.name == "_template.md":
                continue
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                docs.append({
                    "id": f"person_{md_file.stem}",
                    "source": str(md_file),
                    "type": "person_profile",
                    "person_name": md_file.stem,
                    "content": content,
                    "metadata": {"name": md_file.stem},
                    "timestamp": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
                })
            except Exception as e:
                print(f"Error loading {md_file}: {e}")

        return docs

    def _load_environment(self) -> List[Dict[str, Any]]:
        """加载生态环境系统"""
        docs = []
        env_path = self.base_path / "environment"

        if not env_path.exists():
            return docs

        for json_file in env_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                docs.append({
                    "id": f"environment_{json_file.stem}",
                    "source": str(json_file),
                    "type": "environment_system",
                    "category": json_file.stem,
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": data,
                    "timestamp": data.get("last_updated", datetime.now().isoformat())
                })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

        return docs

    def _load_timeline(self) -> List[Dict[str, Any]]:
        """加载思想演变时间轴"""
        docs = []
        timeline_path = self.base_path / "timeline"

        if not timeline_path.exists():
            return docs

        # 加载快照 JSON
        snapshots_file = timeline_path / "snapshots.json"
        if snapshots_file.exists():
            try:
                with open(snapshots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 为每个快照创建单独的文档
                snapshots = data.get("snapshots", []) if isinstance(data, dict) else data
                for i, snapshot in enumerate(snapshots):
                    docs.append({
                        "id": f"snapshot_{i}_{snapshot.get('timestamp', '')}",
                        "source": str(snapshots_file),
                        "type": "timeline_snapshot",
                        "content": json.dumps(snapshot, ensure_ascii=False, indent=2),
                        "metadata": snapshot,
                        "timestamp": snapshot.get("timestamp", datetime.now().isoformat())
                    })
            except Exception as e:
                print(f"Error loading {snapshots_file}: {e}")

        # 加载演变记录 Markdown
        evolution_file = timeline_path / "evolution.md"
        if evolution_file.exists():
            try:
                with open(evolution_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                docs.append({
                    "id": "timeline_evolution",
                    "source": str(evolution_file),
                    "type": "timeline_evolution",
                    "content": content,
                    "metadata": {},
                    "timestamp": datetime.fromtimestamp(evolution_file.stat().st_mtime).isoformat()
                })
            except Exception as e:
                print(f"Error loading {evolution_file}: {e}")

        return docs

    def _load_conversations(self) -> List[Dict[str, Any]]:
        """加载对话历史"""
        docs = []
        conv_path = self.base_path / "conversations"

        if not conv_path.exists():
            return docs

        for md_file in conv_path.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                docs.append({
                    "id": f"conversation_{md_file.stem}",
                    "source": str(md_file),
                    "type": "conversation",
                    "content": content,
                    "metadata": {},
                    "timestamp": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
                })
            except Exception as e:
                print(f"Error loading {md_file}: {e}")

        return docs


if __name__ == "__main__":
    # 测试数据加载
    loader = IAMIDataLoader()
    docs = loader.load_all_data()
    print(f"Loaded {len(docs)} documents")
    for doc in docs[:3]:
        print(f"- {doc['id']} ({doc['type']})")
