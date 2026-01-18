"""
IAMI 专属 Agent 系统

包含三个核心代理：
1. IAMILearningAgent - 学习模式（提问、记录、分析）
2. IAMISimulationAgent - 模拟模式（以用户思维回答）
3. IAMIAnalysisAgent - 分析模式（生成洞察）
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from graphrag.indexer.hybrid_indexer import HybridIndexer
from graphrag.llm_providers import create_llm, LLMProviderFactory

# 配置日志
logger = logging.getLogger(__name__)


class IAMIBaseAgent:
    """IAMI 代理基类"""

    def __init__(self, user_id: str = "default", indexer: HybridIndexer = None, llm_provider: Optional[str] = None):
        """
        初始化IAMI代理基类

        Args:
            user_id: 用户ID
            indexer: 混合索引器实例
            llm_provider: LLM提供者名称 ("deepseek", "glm", "openai")，
                        如果不指定则从环境变量LLM_PROVIDER读取
        """
        self.user_id = user_id
        self.indexer = indexer
        # 如果提供了 indexer，确保其 user_id 一致
        if self.indexer and hasattr(self.indexer, 'user_id'):
            self.user_id = self.indexer.user_id

        self.base_user_dir = Path(f"data/users/{self.user_id}")

        # 使用统一的LLM配置系统
        self.llm = create_llm(llm_provider)

        # 批量Token记录队列
        self._pending_usage_records = []
        self._usage_lock = asyncio.Lock()
        self._flush_interval = 10  # 每10条记录批量写入一次
        self._max_pending_records = 50  # 最多缓存50条记录

    async def invoke_llm(self, prompt: str, call_type: str = "unknown"):
        """
        调用 LLM 并记录 Token 使用情况

        Args:
            prompt: 提示词
            call_type: 调用类型标识（用于统计）

        Returns:
            LLM响应对象
        """
        try:
            response = await self.llm.ainvoke(prompt)
        except Exception as e:
            logger.error(f"LLM invocation failed for call_type '{call_type}': {e}")
            raise

        # 异步记录 Token 使用（不阻塞主流程）
        try:
            await self._queue_usage_record(response, call_type)
        except Exception as e:
            # 记录失败不应影响主流程
            logger.warning(f"Token usage recording failed: {e}")

        return response

    async def _queue_usage_record(self, response, call_type: str):
        """将使用记录加入队列，等待批量写入"""
        async with self._usage_lock:
            self._pending_usage_records.append((response, call_type))

            # 如果达到批量写入阈值，则执行写入
            if len(self._pending_usage_records) >= self._flush_interval:
                await self._flush_usage_records()

    async def _flush_usage_records(self):
        """批量写入Token使用记录到数据库"""
        if not self._pending_usage_records:
            return

        # 复制当前队列并清空
        records_to_write = self._pending_usage_records.copy()
        self._pending_usage_records.clear()

        try:
            from accounts.models import TokenUsage
            from django.contrib.auth.models import User
            from asgiref.sync import sync_to_async

            # 解析 user_id (format: "user_1")
            try:
                if self.user_id.startswith("user_"):
                    uid = int(self.user_id.split("_")[1])
                    user = await sync_to_async(User.objects.get)(pk=uid)
                else:
                    logger.warning(f"Invalid user_id format: {self.user_id}")
                    return
            except (ValueError, User.DoesNotExist) as e:
                logger.warning(f"User not found: {e}")
                return

            # 批量创建记录
            usage_objects = []
            for response, call_type in records_to_write:
                usage_data = response.response_metadata.get("token_usage", {})
                if not usage_data:
                    continue

                usage_objects.append(
                    TokenUsage(
                        user=user,
                        tokens_input=usage_data.get("prompt_tokens", 0),
                        tokens_output=usage_data.get("completion_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0),
                        model_name=response.response_metadata.get("model_name", "unknown"),
                        call_type=call_type
                    )
                )

            # 批量写入数据库
            if usage_objects:
                await sync_to_async(TokenUsage.objects.abulk_create)(usage_objects, batch_size=100)
                logger.info(f"Recorded {len(usage_objects)} token usage records")

        except Exception as e:
            logger.error(f"Error in batch token usage recording: {e}")
            # 如果批量写入失败，将记录放回队列（防止丢失）
            self._pending_usage_records.extend(records_to_write)

    async def cleanup(self):
        """清理资源，刷新剩余的Token记录"""
        await self._flush_usage_records()

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

    def __init__(self, user_id: str = "default", indexer: HybridIndexer = None):
        super().__init__(user_id=user_id, indexer=indexer)
        
        # 用户特定的问题历史
        self.questions_file = str(self.base_user_dir / "questions/asked_history.json")
        # 用户档案文件
        self.profile_file = str(self.base_user_dir / "profile.json")
        # 共享的问题类别（或者也可以是用户特定的，目前选共享）
        self.categories_file = "questions/categories.md"

    async def get_user_profile(self) -> Dict[str, Any]:
        """获取用户档案"""
        return self._load_json_file(self.profile_file)

    async def update_user_profile(self, profile_data: Dict[str, Any]) -> bool:
        """更新用户档案"""
        try:
            current = self._load_json_file(self.profile_file)
            current.update(profile_data)
            current["updated_at"] = datetime.now().isoformat()
            self._save_json_file(self.profile_file, current)
            return True
        except Exception as e:
            print(f"Failed to update profile: {e}")
            return False

    async def generate_question(
        self,
        category: Optional[str] = None,
        context: Optional[str] = None,
        question_type: str = "open",  # "open" or "mcq"
        excluded_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成下一个问题

        Args:
            category: 问题类别（personality, values, thinking_patterns 等）
            context: 额外上下文信息
            question_type: 问题类型 ("open" 问答题, "mcq" 选择题)
            excluded_questions: 需要排除的问题列表（用于异步预生成）

        Returns:
            包含问题和元数据的字典
        """
        # 读取问题历史
        asked_history = self._load_json_file(self.questions_file)
        asked_questions = asked_history.get("questions", [])
        
        # 构建已问问题列表
        # 增加检查范围，避免长周期重复
        # 修改：检查所有已问过的问题文本，而不仅仅是最近 50 个
        already_asked_texts = [q.get("question", "") for q in asked_questions]
        if excluded_questions:
            already_asked_texts.extend(excluded_questions)

        # 读取问题类别
        categories = self._read_md_file(self.categories_file)

        # 如果未指定类别，智能选择
        if not category:
            category = await self._select_category(asked_history)

        # --- Shared Pool Logic Start ---
        shared_pool_file = "data/shared/questions_pool.json"
        shared_pool = self._load_json_file(shared_pool_file)
        if "questions" not in shared_pool:
            shared_pool["questions"] = []

        # 随机化选择，增加多样性
        import random
        suitable_pool_qs = [
            pq for pq in shared_pool["questions"]
            if (pq.get("category") == category and 
                pq.get("type") == question_type and 
                pq.get("question") not in already_asked_texts)
        ]
        
        if suitable_pool_qs:
            pool_q = random.choice(suitable_pool_qs)
            qa_copy = pool_q.copy()
            qa_copy["timestamp"] = datetime.now().isoformat()
            qa_copy["id"] = f"q_{len(asked_questions) + 1}"
            return qa_copy
        # --- Shared Pool Logic End ---

        # 读取用户档案
        user_profile = await self.get_user_profile()
        profile_context = ""
        if user_profile:
            profile_context = f"""
## 用户背景档案 (必须严格基于此背景)
- 年龄: {user_profile.get('age', '未知')}
- 性别: {user_profile.get('gender', '未知')}
- 职业身份: {user_profile.get('occupation', '未知')} (如果是学生，不要问职场管理题；如果是工作党，不要问校园考试题)
- 学历: {user_profile.get('education', '未知')}
- 生活环境: {user_profile.get('environment', '未知')}
- 个人状态: {user_profile.get('status', '未知')}
请确保生成的情境对于该用户背景是合理且常见的。例如：不要问一个没工作过的学生关于“裁员下属”的问题。
"""

        # 类型描述
        type_instruction = ""
        if question_type == "mcq":
            type_instruction = """
4. **选择题格式**：提供 3-4 个互斥且具有代表性的选项，涵盖该维度下的典型表现。
"""
        else:
            type_instruction = """
4. **开放性**：鼓励用户进行叙述性回答，以便提取更多细节。
"""

        # 构建提示词
        prompt = f"""你是 IAMI 系统的学习代理。你的任务是生成一个具体的、基于真实情境的{ "选择题" if question_type == "mcq" else "描述性问题" }，用于了解用户的{category}。

## 核心原则
1. **具体化**：不问抽象问题（如"你的价值观是什么？"），而是通过具体情境判断题
2. **场景多样化**：**严禁**连续生成职场/公司背景的问题。请尝试从以下场景中切换：家庭生活、社交场合、新闻热点、数字生活/互联网事件、旅行见闻、自然环境、消费决策等。
3. **真实性**：优先询问真实经历，而非假设性问题
4. **个性化适配**：必须参考用户的【背景档案】，确保问题场景在用户的生活经验范围内。
5. **学术基础**：基于心理学/社会学研究框架（见下方）
{type_instruction}

## 问题类别框架
{categories}
{profile_context}

## 已问过的问题（避免重复）
{json.dumps(already_asked_texts, ensure_ascii=False, indent=2)}

## 额外上下文
{context or "无"}

请生成一个新问题。返回 JSON 格式：
{{
    "question": "具体问题",
    "type": "{question_type}",
    "category": "{category}",
    "options": { '["选项A", "选项B", "选项C", "选项D"]' if question_type == "mcq" else "[]" },
    "reasoning": "为什么问这个问题（简短说明）",
    "follow_up_hints": ["可能的追问方向1", "可能的追问方向2"]
}}
"""

        response = await self.invoke_llm(prompt, call_type="learning_generate_question")

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

            # --- Save to Shared Pool ---
            # Reload pool to minimise race conditions (simple file lock simulation)
            current_pool = self._load_json_file(shared_pool_file)
            if "questions" not in current_pool:
                current_pool["questions"] = []
            
            # Check for duplicates by text before adding
            if not any(q.get("question") == question_data.get("question") for q in current_pool["questions"]):
                # Save a copy without user-specific ID/Timestamp if desired, 
                # but here we just save the clean data
                pool_entry = {
                    "question": question_data.get("question"),
                    "category": question_data.get("category"),
                    "type": question_data.get("type"),
                    "options": question_data.get("options", []),
                    "reasoning": question_data.get("reasoning", ""),
                    "follow_up_hints": question_data.get("follow_up_hints", []),
                    "created_at": datetime.now().isoformat()
                }
                current_pool["questions"].append(pool_entry)
                self._save_json_file(shared_pool_file, current_pool)
            # --- End Save ---

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
            "language_style",
            "social_hotspots"  # 新增：社会热点
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

        response = await self.invoke_llm(prompt, call_type="learning_analyze_answer")

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)

            # 添加元数据
            analysis["question_id"] = question.get("id")
            analysis["question_text"] = question.get("question", "")
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
                "question_text": question.get("question", ""),
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
            file_path = str(self.base_user_dir / "memory/long_term/personality.json")
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
            file_path = str(self.base_user_dir / "memory/long_term/values.json")
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
        conv_file = str(self.base_user_dir / f"memory/conversations/learning_{timestamp.split('T')[0]}.md")
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
            "question_id": analysis.get("question_id"),
            "question": analysis.get("question_text"),  # 存储文本用于查重
            "answer": answer,  # 新增：存储用户原始回答
            "category": category,
            "timestamp": timestamp,
            "answered": True,
            "analysis_results": analysis.get("features", []),  # 新增：存储分析结果详情
            "analysis_summary": {
                "features_count": len(analysis.get("features", [])),
                "confidence_avg": sum(f.get("confidence", 0) for f in analysis.get("features", [])) / max(len(analysis.get("features", [])), 1)
            }
        })

        self._save_json_file(self.questions_file, asked_history)
        results["updated_files"].append(self.questions_file)

        return results

    async def get_full_history(self) -> List[Dict[str, Any]]:
        """获取完整的问题历史记录，尝试补全缺失的问题文本"""
        asked_history = self._load_json_file(self.questions_file)
        questions = asked_history.get("questions", [])
        
        # 加载共享池用于补全老数据的问题文本
        shared_pool_file = "data/shared/questions_pool.json"
        shared_pool = self._load_json_file(shared_pool_file)
        pool_questions = shared_pool.get("questions", [])
        
        # 创建 ID 到文本的映射 (假设 pool 中没有 ID，可以根据 category/type 或近似匹配，
        # 但既然老数据存储的是 q_1, q_2 这种基于计数生成的 ID，共享池可能没有对应 ID。
        # 因此我们直接遍历 pool，或者如果老数据有文本就用文本)
        
        for q in questions:
            # 如果没有 question 文本或者只有 ID
            if not q.get("question") or q.get("question", "").startswith("q_"):
                q_id = q.get("question_id") or q.get("question")
                # 尝试从 pool 中找出匹配的（这里只能通过某种启发式或者直接按顺序，
                # 但最可靠的是如果 pool 存储了类似结构）
                # 由于 pool 没存 id，我们根据 category 尝试寻找相似问题作为 fallback
                if q_id and q_id.startswith("q_"):
                    try:
                        idx = int(q_id.split("_")[1]) - 1
                        # 如果 pool 很大且顺序对应（概率低），或者直接根据 category 找
                        target_cat = q.get("category")
                        cat_qs = [pq for pq in pool_questions if pq.get("category") == target_cat]
                        # 这是一个有损的 fallback，但在没有文本的情况下比显示 q_2 好
                        if cat_qs:
                            # 简单的启发：如果索引在范围内
                            p_idx = idx % len(cat_qs)
                            if not q.get("question") or q.get("question").startswith("q_"):
                                q["question"] = cat_qs[p_idx].get("question")
                    except:
                        pass
            
            # 进一步补全：如果还是没有 answer 或者是 "未记录回答"，尝试在 md 文件里找
            if not q.get("answer") or q.get("answer") == "未记录回答":
                timestamp = q.get("timestamp")
                if timestamp:
                    date_str = timestamp.split("T")[0]
                    md_file = self.base_user_dir / f"memory/conversations/learning_{date_str}.md"
                    if md_file.exists():
                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # 寻找对应时间戳的小节
                                if timestamp in content:
                                    # 提取该小节
                                    section = content.split(f"## {timestamp}")[1].split("---")[0]
                                    # 提取回答
                                    if "**回答**:" in section:
                                        ans = section.split("**回答**:")[1].split("**分析**:")[0].strip()
                                        q["answer"] = ans
                                    # 如果 JSON 里没存 question 文本，这里也可以尝试从 md 提取（如果 md 存了的话）
                        except:
                            pass
        return questions

    async def delete_history_item(self, timestamp: str) -> bool:
        """删除指定的历史记录"""
        asked_history = self._load_json_file(self.questions_file)
        if "questions" not in asked_history:
            return False
            
        initial_count = len(asked_history["questions"])
        # 根据时间戳过滤掉要删除的记录
        asked_history["questions"] = [q for q in asked_history["questions"] if q.get("timestamp") != timestamp]
        
        if len(asked_history["questions"]) < initial_count:
            self._save_json_file(self.questions_file, asked_history)
            return True
        return False

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

    # ==================== 日记模式辅助方法 ====================

    async def _ai_continue_writing(self, content: str) -> str:
        """AI 辅助续写"""
        prompt = f"""用户正在写日记，已经写了以下内容：

{content}

请以用户的口吻，自然地续写一段（2-3句话）。要求：
1. 保持用户的语言风格和语气
2. 顺势延伸，不要突兀
3. 提供一个新的角度或细节
4. 不要说教或过度解读

直接输出续写内容，不要加任何前缀或解释。
"""
        response = await self.llm.ainvoke(prompt)
        return response.content.strip()

    async def _ai_polish_content(self, content: str) -> str:
        """AI 润色日记"""
        prompt = f"""用户写了一篇日记，请帮忙润色：

原文：
{content}

要求：
1. 保留原意和真实性
2. 修正明显的语法错误
3. 优化表达，使其更流畅
4. 不要改变用户的语气和风格
5. 不要过度修饰，保持自然

直接输出润色后的内容。
"""
        response = await self.llm.ainvoke(prompt)
        return response.content.strip()

    async def _ai_deepen_content(self, content: str) -> str:
        """深入挖掘感受"""
        prompt = f"""用户写了这篇日记：

{content}

请提出1-2个深入的问题，帮助用户挖掘更深层的想法或感受。
要求：
1. 问题要具体，不能空泛
2. 关注"为什么"而不是"是什么"
3. 温和、不侵入
4. 可以关注情绪、动机、价值观等

直接输出问题，不要加前缀。
"""
        response = await self.llm.ainvoke(prompt)
        return response.content.strip()

    async def _ai_generate_insights(self, content: str) -> str:
        """生成启发"""
        prompt = f"""基于用户的日记内容，提供一个有启发性的洞察：

日记：
{content}

要求：
1. 指出用户可能没有意识到的模式或特点
2. 温和、积极，不说教
3. 简洁（1-2句话）
4. 可以提供一个新的视角

直接输出洞察，不要前缀。
"""
        response = await self.llm.ainvoke(prompt)
        return response.content.strip()

    async def _analyze_diary(self, content: str) -> Dict[str, Any]:
        """分析日记内容"""
        prompt = f"""分析以下日记内容：

{content}

请提取：
1. **sentiment**: 情绪倾向（正面/负面/中性）和强度（1-5）
2. **topics**: 主要主题（2-3个，如"工作"、"人际关系"、"自我反思"等）
3. **new_traits**: 可能发现的新人格特征或价值观（2-3个）
4. **key_events**: 关键事件或转折点（如有）

返回 JSON 格式。
"""
        response = await self.llm.ainvoke(prompt)

        try:
            import json
            result_content = response.content
            if "```json" in result_content:
                result_content = result_content.split("```json")[1].split("```")[0].strip()

            analysis = json.loads(result_content)
            return analysis
        except:
            return {
                "sentiment": "中性",
                "topics": ["生活"],
                "new_traits": [],
                "key_events": []
            }


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

        response = await self.invoke_llm(prompt, call_type="simulation_response")

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
            "personality": str(self.base_user_dir / "memory/long_term/personality.json"),
            "values": str(self.base_user_dir / "memory/long_term/values.json"),
            "thinking_patterns": str(self.base_user_dir / "memory/long_term/thinking_patterns.json"),
            "language_style": str(self.base_user_dir / "memory/long_term/language_style.json"),
            "knowledge": str(self.base_user_dir / "memory/long_term/knowledge.json")
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
        simulation_agent = IAMISimulationAgent(user_id=self.user_id, indexer=self.indexer)
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

        response = await self.invoke_llm(prompt, call_type="analysis_profile")

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            profile = json.loads(content)
            profile["generated_at"] = datetime.now().isoformat()

            # 保存
            self._save_json_file(str(self.base_user_dir / "analysis/profile.json"), profile)

            return profile

        except json.JSONDecodeError:
            return {
                "raw_analysis": response.content,
                "generated_at": datetime.now().isoformat()
            }

    async def analyze_evolution(self) -> Dict[str, Any]:
        """分析思想演变"""
        # 读取时间轴
        snapshots = self._load_json_file(str(self.base_user_dir / "memory/timeline/snapshots.json"))

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

        response = await self.invoke_llm(prompt, call_type="analysis_evolution")

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
