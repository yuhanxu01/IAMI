"""
IAMI 专属 Agent 系统

包含三个核心代理：
1. IAMILearningAgent - 学习模式（提问、记录、分析）
2. IAMISimulationAgent - 模拟模式（以用户思维回答）
3. IAMIAnalysisAgent - 分析模式（生成洞察）
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from graphrag.indexer.hybrid_indexer import HybridIndexer


class IAMIBaseAgent:
    """IAMI 代理基类"""

    def __init__(self, indexer: HybridIndexer = None):
        self.indexer = indexer
        self.llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            temperature=0.7,
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        )

    def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """加载 JSON 文件"""
        path = Path(file_path)
        if not path.exists():
            return {}

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json_file(self, file_path: str, data: Dict[str, Any]):
        """保存 JSON 文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_md_file(self, file_path: str) -> str:
        """读取 Markdown 文件"""
        path = Path(file_path)
        if not path.exists():
            return ""

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()


class IAMILearningAgent(IAMIBaseAgent):
    """
    IAMI 学习模式代理

    功能：
    1. 基于学术框架生成问题
    2. 分析用户回答，提取特征
    3. 更新记忆文件
    4. 追踪问题历史
    """

    def __init__(self, indexer: HybridIndexer = None):
        super().__init__(indexer)
        self.questions_file = "questions/asked_history.json"
        self.categories_file = "questions/categories.md"

    async def generate_question(
        self,
        category: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成下一个问题

        Args:
            category: 问题类别（personality, values, thinking_patterns 等）
            context: 额外上下文信息

        Returns:
            包含问题和元数据的字典
        """
        # 读取问题历史
        asked_history = self._load_json_file(self.questions_file)
        asked_questions = asked_history.get("questions", [])

        # 读取问题类别
        categories = self._read_md_file(self.categories_file)

        # 如果未指定类别，智能选择
        if not category:
            category = await self._select_category(asked_history)

        # 构建提示词
        prompt = f"""你是 IAMI 系统的学习代理。你的任务是生成一个具体的、基于真实情境的问题，用于了解用户的{category}。

## 核心原则
1. **具体化**：不问抽象问题（如"你的价值观是什么？"），而是通过具体情境判断题
2. **真实性**：优先询问真实经历，而非假设性问题
3. **学术基础**：基于心理学/社会学研究框架（见下方）

## 问题类别框架
{categories}

## 已问过的问题（避免重复）
{json.dumps([q.get("question", "") for q in asked_questions[-10:]], ensure_ascii=False, indent=2)}

## 额外上下文
{context or "无"}

请生成一个新问题。返回 JSON 格式：
{{
    "question": "具体问题",
    "category": "{category}",
    "reasoning": "为什么问这个问题（简短说明）",
    "follow_up_hints": ["可能的追问方向1", "可能的追问方向2"]
}}
"""

        response = await self.llm.ainvoke(prompt)

        try:
            # 解析 JSON
            content = response.content
            # 提取 JSON（可能被包裹在代码块中）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            question_data = json.loads(content)

            # 添加元数据
            question_data["timestamp"] = datetime.now().isoformat()
            question_data["id"] = f"q_{len(asked_questions) + 1}"

            return question_data

        except json.JSONDecodeError as e:
            # 回退方案
            return {
                "question": response.content,
                "category": category,
                "reasoning": "自动生成",
                "follow_up_hints": [],
                "timestamp": datetime.now().isoformat(),
                "id": f"q_{len(asked_questions) + 1}"
            }

    async def _select_category(self, asked_history: Dict[str, Any]) -> str:
        """智能选择下一个问题类别"""
        # 统计各类别已问问题数量
        category_counts = {}
        for q in asked_history.get("questions", []):
            cat = q.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # 优先级列表（基于 IAMI 核心维度）
        priority_categories = [
            "personality",      # Big Five
            "values",          # Schwartz
            "thinking_patterns",
            "moral_foundations",
            "relationships",
            "environment",
            "language_style"
        ]

        # 选择问得最少的类别
        for cat in priority_categories:
            if category_counts.get(cat, 0) < 5:  # 每个类别至少 5 个问题
                return cat

        # 如果都达到最小数量，选择总数最少的
        return min(priority_categories, key=lambda c: category_counts.get(c, 0))

    async def analyze_answer(
        self,
        question: Dict[str, Any],
        answer: str
    ) -> Dict[str, Any]:
        """
        分析用户回答，提取特征

        Args:
            question: 问题数据
            answer: 用户回答

        Returns:
            分析结果
        """
        category = question.get("category", "unknown")

        prompt = f"""分析以下用户回答，提取关键特征。

## 问题
{question.get("question", "")}

## 类别
{category}

## 用户回答
{answer}

请提取：
1. 核心特征（personality traits, values, thinking patterns 等）
2. 具体证据（用户回答中的关键句子）
3. 置信度（1-5，5最高）
4. 建议的追问（如果需要更多信息）

返回 JSON 格式：
{{
    "features": [
        {{
            "trait": "特征名称",
            "value": "特征值或描述",
            "evidence": "支持证据",
            "confidence": 4
        }}
    ],
    "follow_up_needed": true/false,
    "suggested_follow_up": "追问问题（如果需要）"
}}
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)

            # 添加元数据
            analysis["question_id"] = question.get("id")
            analysis["category"] = category
            analysis["timestamp"] = datetime.now().isoformat()

            return analysis

        except json.JSONDecodeError:
            return {
                "features": [],
                "follow_up_needed": False,
                "suggested_follow_up": "",
                "raw_analysis": response.content,
                "question_id": question.get("id"),
                "category": category,
                "timestamp": datetime.now().isoformat()
            }

    async def update_memory(
        self,
        analysis: Dict[str, Any],
        answer: str
    ) -> Dict[str, Any]:
        """
        更新记忆文件

        Args:
            analysis: 分析结果
            answer: 原始回答

        Returns:
            更新结果
        """
        category = analysis.get("category", "unknown")
        timestamp = datetime.now().isoformat()

        results = {
            "updated_files": [],
            "indexed_documents": []
        }

        # 根据类别更新相应的记忆文件
        if category == "personality":
            file_path = "memory/long_term/personality.json"
            data = self._load_json_file(file_path)

            # 添加新特征到历史
            if "history" not in data:
                data["history"] = []

            for feature in analysis.get("features", []):
                data["history"].append({
                    "timestamp": timestamp,
                    "trait": feature.get("trait"),
                    "value": feature.get("value"),
                    "evidence": feature.get("evidence"),
                    "confidence": feature.get("confidence")
                })

            self._save_json_file(file_path, data)
            results["updated_files"].append(file_path)

        elif category == "values":
            file_path = "memory/long_term/values.json"
            data = self._load_json_file(file_path)

            if "history" not in data:
                data["history"] = []

            for feature in analysis.get("features", []):
                data["history"].append({
                    "timestamp": timestamp,
                    "value_type": feature.get("trait"),
                    "description": feature.get("value"),
                    "evidence": feature.get("evidence"),
                    "confidence": feature.get("confidence")
                })

            self._save_json_file(file_path, data)
            results["updated_files"].append(file_path)

        # 可以继续添加其他类别...

        # 保存对话记录
        conv_file = f"memory/conversations/learning_{timestamp.split('T')[0]}.md"
        conv_path = Path(conv_file)
        conv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(conv_path, 'a', encoding='utf-8') as f:
            f.write(f"\n## {timestamp}\n\n")
            f.write(f"**问题**: {analysis.get('question_id')}\n\n")
            f.write(f"**回答**: {answer}\n\n")
            f.write(f"**分析**: {json.dumps(analysis.get('features', []), ensure_ascii=False, indent=2)}\n\n")
            f.write("---\n\n")

        results["updated_files"].append(conv_file)

        # 索引到混合系统
        if self.indexer:
            # 索引对话
            doc = {
                "id": f"conv_{timestamp}",
                "type": "conversation",
                "content": f"问题：{analysis.get('question_id')}\n回答：{answer}",
                "timestamp": timestamp,
                "metadata": {
                    "category": category,
                    "features": analysis.get("features", [])
                }
            }

            index_result = await self.indexer.index_document(doc)
            results["indexed_documents"].append(index_result)

        # 更新问题历史
        asked_history = self._load_json_file(self.questions_file)
        if "questions" not in asked_history:
            asked_history["questions"] = []

        asked_history["questions"].append({
            "question": analysis.get("question_id"),
            "category": category,
            "timestamp": timestamp,
            "answered": True,
            "analysis_summary": {
                "features_count": len(analysis.get("features", [])),
                "confidence_avg": sum(f.get("confidence", 0) for f in analysis.get("features", [])) / max(len(analysis.get("features", [])), 1)
            }
        })

        self._save_json_file(self.questions_file, asked_history)
        results["updated_files"].append(self.questions_file)

        return results

    async def get_learning_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        asked_history = self._load_json_file(self.questions_file)
        questions = asked_history.get("questions", [])

        # 按类别统计
        category_stats = {}
        for q in questions:
            cat = q.get("category", "unknown")
            if cat not in category_stats:
                category_stats[cat] = {
                    "count": 0,
                    "avg_confidence": 0,
                    "features_count": 0
                }

            category_stats[cat]["count"] += 1
            summary = q.get("analysis_summary", {})
            category_stats[cat]["avg_confidence"] += summary.get("confidence_avg", 0)
            category_stats[cat]["features_count"] += summary.get("features_count", 0)

        # 计算平均值
        for cat in category_stats:
            count = category_stats[cat]["count"]
            if count > 0:
                category_stats[cat]["avg_confidence"] /= count

        return {
            "total_questions": len(questions),
            "category_breakdown": category_stats,
            "last_question_time": questions[-1].get("timestamp") if questions else None,
            "completion_rate": self._calculate_completion_rate(category_stats)
        }

    def _calculate_completion_rate(self, category_stats: Dict[str, Any]) -> float:
        """计算学习完成度（基于每个类别至少5个问题）"""
        target_per_category = 5
        priority_categories = [
            "personality", "values", "thinking_patterns",
            "moral_foundations", "relationships", "environment"
        ]

        total_target = len(priority_categories) * target_per_category
        actual_count = sum(
            min(category_stats.get(cat, {}).get("count", 0), target_per_category)
            for cat in priority_categories
        )

        return (actual_count / total_target) * 100 if total_target > 0 else 0


class IAMISimulationAgent(IAMIBaseAgent):
    """
    IAMI 模拟模式代理

    功能：
    1. 读取所有记忆文件
    2. 以用户的思维模式回答问题
    3. 考虑时间演变
    """

    async def simulate_response(
        self,
        query: str,
        use_latest_only: bool = True
    ) -> Dict[str, Any]:
        """
        以用户的思维模式回答问题

        Args:
            query: 用户问题
            use_latest_only: 是否只使用最新的记忆（考虑演变）

        Returns:
            模拟回答及元数据
        """
        # 读取所有记忆
        memories = await self._load_all_memories(use_latest_only)

        # 构建人物画像摘要
        profile_summary = self._build_profile_summary(memories)

        # 使用混合检索器获取相关记忆
        relevant_context = ""
        if self.indexer:
            query_result = await self.indexer.query(
                query=query,
                use_lightrag=True,
                use_chromadb=True,
                lightrag_mode="hybrid",
                chromadb_k=5
            )

            if query_result.get("lightrag_result", {}).get("success"):
                relevant_context += "\n\n## LightRAG 检索结果\n"
                relevant_context += query_result["lightrag_result"].get("result", "")

            if query_result.get("chromadb_results"):
                relevant_context += "\n\n## 相关对话历史\n"
                for doc in query_result["chromadb_results"][:3]:
                    relevant_context += f"- {doc.get('content', '')}\n"

        # 生成模拟回答
        prompt = f"""你现在要以"用户"的身份和思维模式回答问题。

## 用户人物画像
{profile_summary}

## 相关记忆上下文
{relevant_context}

## 问题
{query}

请以用户的语言风格、思维方式、价值观来回答这个问题。
- 使用用户习惯的表达方式
- 体现用户的性格特征
- 反映用户的价值观和思维模式
- 如果用户对此话题有明确立场，应体现出来

直接给出回答，不要加"作为用户，我会..."这样的前缀。
"""

        response = await self.llm.ainvoke(prompt)

        return {
            "query": query,
            "simulated_response": response.content,
            "profile_summary": profile_summary,
            "timestamp": datetime.now().isoformat(),
            "memories_used": len(memories),
            "retrieval_context_length": len(relevant_context)
        }

    async def _load_all_memories(self, use_latest_only: bool) -> Dict[str, Any]:
        """加载所有记忆文件"""
        memories = {}

        memory_files = {
            "personality": "memory/long_term/personality.json",
            "values": "memory/long_term/values.json",
            "thinking_patterns": "memory/long_term/thinking_patterns.json",
            "language_style": "memory/long_term/language_style.json",
            "knowledge": "memory/long_term/knowledge.json"
        }

        for key, file_path in memory_files.items():
            data = self._load_json_file(file_path)

            if use_latest_only and "history" in data:
                # 只取最近的记录
                data["history"] = sorted(
                    data["history"],
                    key=lambda x: x.get("timestamp", ""),
                    reverse=True
                )[:10]  # 最近10条

            memories[key] = data

        return memories

    def _build_profile_summary(self, memories: Dict[str, Any]) -> str:
        """构建人物画像摘要"""
        summary_parts = []

        # 性格特征
        if "personality" in memories and memories["personality"].get("history"):
            traits = memories["personality"]["history"][:5]
            summary_parts.append("### 性格特征")
            for trait in traits:
                summary_parts.append(f"- {trait.get('trait')}: {trait.get('value')} (置信度: {trait.get('confidence')}/5)")

        # 价值观
        if "values" in memories and memories["values"].get("history"):
            values = memories["values"]["history"][:5]
            summary_parts.append("\n### 价值观")
            for value in values:
                summary_parts.append(f"- {value.get('value_type')}: {value.get('description')}")

        # 思维模式
        if "thinking_patterns" in memories and memories["thinking_patterns"].get("history"):
            patterns = memories["thinking_patterns"]["history"][:3]
            summary_parts.append("\n### 思维模式")
            for pattern in patterns:
                summary_parts.append(f"- {pattern.get('pattern')}: {pattern.get('description')}")

        return "\n".join(summary_parts) if summary_parts else "暂无充足的人物画像数据"


class IAMIAnalysisAgent(IAMIBaseAgent):
    """
    IAMI 分析代理

    功能：
    1. 生成综合人物画像
    2. 发现思想演变模式
    3. 识别价值观冲突
    """

    async def generate_profile(self) -> Dict[str, Any]:
        """生成综合人物画像"""
        # 加载所有记忆
        simulation_agent = IAMISimulationAgent(self.indexer)
        memories = await simulation_agent._load_all_memories(use_latest_only=False)

        # 使用 LLM 生成综合分析
        prompt = f"""基于以下记忆数据，生成一个综合的人物画像分析。

## 记忆数据
{json.dumps(memories, ensure_ascii=False, indent=2)}

请提供：
1. **核心性格特征**（Big Five 维度）
2. **主要价值观**（Schwartz 价值观）
3. **思维模式总结**
4. **语言风格特点**
5. **知识领域**
6. **整体评价**（200字以内）

返回 JSON 格式。
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            profile = json.loads(content)
            profile["generated_at"] = datetime.now().isoformat()

            # 保存
            self._save_json_file("analysis/profile.json", profile)

            return profile

        except json.JSONDecodeError:
            return {
                "raw_analysis": response.content,
                "generated_at": datetime.now().isoformat()
            }

    async def analyze_evolution(self) -> Dict[str, Any]:
        """分析思想演变"""
        # 读取时间轴
        snapshots = self._load_json_file("memory/timeline/snapshots.json")

        if not snapshots or len(snapshots.get("snapshots", [])) < 2:
            return {
                "evolution_detected": False,
                "message": "需要至少2个时间快照才能分析演变"
            }

        # LLM 分析
        prompt = f"""分析用户思想的演变过程。

## 时间快照
{json.dumps(snapshots, ensure_ascii=False, indent=2)}

请识别：
1. 主要变化维度（性格、价值观、思维方式等）
2. 变化趋势（增强/减弱）
3. 可能的影响因素
4. 关键转折点

返回 JSON 格式。
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            evolution = json.loads(content)
            evolution["analyzed_at"] = datetime.now().isoformat()

            return evolution

        except json.JSONDecodeError:
            return {
                "raw_analysis": response.content,
                "analyzed_at": datetime.now().isoformat()
            }
