"""
IAMI 故事模式 Agent

通过沉浸式的故事和角色扮演来分析用户的人格特征。
每次都是全新生成的故事，用户的选择会影响剧情走向。
"""

import os
import json
import random
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI
from .iami_agents import IAMIBaseAgent


class StoryGenre:
    """故事类型定义"""
    SCIFI = "科幻"
    FANTASY = "奇幻"
    MYSTERY = "悬疑"
    MODERN = "现代"
    HISTORICAL = "历史"
    SURVIVAL = "生存"
    ROMANCE = "浪漫"
    THRILLER = "惊悚"
    ADVENTURE = "冒险"

    @classmethod
    def all_genres(cls):
        return [
            cls.SCIFI, cls.FANTASY, cls.MYSTERY, cls.MODERN,
            cls.HISTORICAL, cls.SURVIVAL, cls.ROMANCE, cls.THRILLER, cls.ADVENTURE
        ]


class StoryState:
    """故事状态"""
    def __init__(self):
        self.story_id = f"story_{datetime.now().timestamp()}"
        self.genre = ""
        self.setting = {}
        self.protagonist = {}
        self.current_scene = 0
        self.scenes = []
        self.choices_made = []
        self.npcs = {}
        self.world_state = {}  # 世界状态变量
        self.relationships = {}  # 人物关系
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "genre": self.genre,
            "setting": self.setting,
            "protagonist": self.protagonist,
            "current_scene": self.current_scene,
            "scenes": self.scenes,
            "choices_made": self.choices_made,
            "npcs": self.npcs,
            "world_state": self.world_state,
            "relationships": self.relationships,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        state = cls()
        for key, value in data.items():
            setattr(state, key, value)
        return state


class IAMIStoryAgent(IAMIBaseAgent):
    """
    IAMI 故事模式代理

    功能：
    1. 生成全新的故事设定
    2. 动态推进剧情
    3. 管理 NPC 和对话
    4. 分析用户选择
    5. 生成故事报告
    """

    def __init__(self, indexer=None):
        super().__init__(indexer)
        self.stories_dir = Path("memory/stories")
        self.stories_dir.mkdir(parents=True, exist_ok=True)

    async def generate_story_setting(
        self,
        genre: Optional[str] = None,
        theme: Optional[str] = None
    ) -> StoryState:
        """
        生成全新的故事设定

        Args:
            genre: 故事类型（可选，随机）
            theme: 故事主题（可选）

        Returns:
            StoryState 对象
        """
        # 随机选择类型
        if not genre:
            genre = random.choice(StoryGenre.all_genres())

        # 构建提示词
        prompt = f"""你是一个创意无限的故事设计师。请创造一个**全新的、原创的**{genre}类型故事。

## 要求
1. **原创性**：不要使用已知的小说、电影、游戏剧情
2. **细节丰富**：场景描写要细致入微，有画面感
3. **人物立体**：主角和 NPC 要有鲜明的性格
4. **冲突明确**：要有核心冲突和矛盾
5. **选择空间**：要有多种可能的发展方向

{f'## 主题：{theme}' if theme else ''}

请生成以下内容（返回 JSON 格式）：

{{
    "genre": "{genre}",
    "title": "故事标题",
    "setting": {{
        "world": "世界观描述（200-300字）",
        "time_period": "时间背景",
        "location": "初始地点",
        "atmosphere": "氛围描述"
    }},
    "protagonist": {{
        "name": "主角名字",
        "background": "主角背景（100-150字）",
        "current_situation": "当前处境",
        "goal": "主角目标",
        "personality_hint": "性格暗示"
    }},
    "initial_scene": {{
        "description": "开场场景描写（300-400字，细致入微）",
        "environment": "环境细节",
        "mood": "情绪氛围",
        "hook": "吸引点/悬念"
    }},
    "key_npcs": [
        {{
            "name": "NPC名字",
            "role": "角色定位",
            "personality": "性格特点",
            "relationship": "与主角的关系"
        }}
    ],
    "central_conflict": "核心冲突",
    "potential_themes": ["可能探索的主题1", "主题2", "主题3"]
}}
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            story_data = json.loads(content)

            # 创建故事状态
            state = StoryState()
            state.genre = genre
            state.setting = story_data.get("setting", {})
            state.protagonist = story_data.get("protagonist", {})

            # 添加初始场景
            initial_scene = {
                "scene_number": 0,
                "title": story_data.get("title", ""),
                "description": story_data.get("initial_scene", {}).get("description", ""),
                "environment": story_data.get("initial_scene", {}).get("environment", ""),
                "mood": story_data.get("initial_scene", {}).get("mood", ""),
                "timestamp": datetime.now().isoformat()
            }
            state.scenes.append(initial_scene)

            # 添加 NPC
            for npc_data in story_data.get("key_npcs", []):
                npc_name = npc_data.get("name", "")
                state.npcs[npc_name] = npc_data

            # 初始化世界状态
            state.world_state = {
                "central_conflict": story_data.get("central_conflict", ""),
                "themes": story_data.get("potential_themes", []),
                "tension_level": 1  # 1-10
            }

            return state

        except json.JSONDecodeError as e:
            # 回退方案
            state = StoryState()
            state.genre = genre
            state.setting = {"world": response.content}
            return state

    async def generate_next_scene(
        self,
        state: StoryState,
        previous_choice: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        根据当前状态生成下一个场景

        Args:
            state: 当前故事状态
            previous_choice: 上一个选择（如果有）

        Returns:
            场景数据（包含描述和选项）
        """
        # 构建上下文
        context = self._build_story_context(state)

        prompt = f"""你是故事的推进者。基于当前故事状态和用户的选择，生成下一个场景。

## 当前故事状态
{context}

{f'''## 用户上一个选择
选项: {previous_choice.get("option_text", "")}
后果: {previous_choice.get("consequence", "")}
''' if previous_choice else ''}

## 要求
1. **延续性**：场景要自然承接上文
2. **细节**：场景描写要细致入微（环境、氛围、人物动作、对话）
3. **推进**：剧情要有实质性进展
4. **选择**：提供 3-4 个有意义的选项
5. **心理测试**：每个选项应反映不同的价值观/性格特征

返回 JSON 格式：
{{
    "scene_number": {state.current_scene + 1},
    "title": "场景标题",
    "description": "场景描写（400-500字，包含环境、人物、对话、动作等）",
    "environment_details": "环境细节",
    "character_emotions": "角色情绪",
    "key_moment": "关键时刻/冲突点",
    "choices": [
        {{
            "id": 1,
            "text": "选项描述（第一人称）",
            "motivation": "这个选择反映的动机",
            "psychological_dimension": "对应的心理学维度（如：Openness, Benevolence, Harm/Care）",
            "potential_consequence": "可能的后果提示（模糊）"
        }}
    ],
    "npcs_present": ["在场的 NPC 名字"],
    "tension_change": "+1 或 -1 或 0（紧张度变化）"
}}
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            scene_data = json.loads(content)

            # 更新世界状态
            tension_change = scene_data.get("tension_change", 0)
            state.world_state["tension_level"] = max(1, min(10,
                state.world_state.get("tension_level", 5) + tension_change
            ))

            return scene_data

        except json.JSONDecodeError:
            return {
                "scene_number": state.current_scene + 1,
                "title": "下一章节",
                "description": response.content,
                "choices": []
            }

    def _build_story_context(self, state: StoryState) -> str:
        """构建故事上下文摘要"""
        context_parts = []

        # 故事设定
        context_parts.append(f"**类型**: {state.genre}")
        context_parts.append(f"**世界观**: {state.setting.get('world', '')[:200]}...")

        # 主角
        context_parts.append(f"\n**主角**: {state.protagonist.get('name', '')}")
        context_parts.append(f"背景: {state.protagonist.get('background', '')[:100]}...")

        # 最近的场景
        if state.scenes:
            recent_scenes = state.scenes[-3:]  # 最近3个场景
            context_parts.append(f"\n**最近场景**:")
            for scene in recent_scenes:
                context_parts.append(f"- 场景{scene['scene_number']}: {scene['title']}")

        # 最近的选择
        if state.choices_made:
            recent_choices = state.choices_made[-5:]  # 最近5个选择
            context_parts.append(f"\n**最近选择**:")
            for choice in recent_choices:
                context_parts.append(f"- {choice.get('option_text', '')[:50]}...")

        # NPC
        if state.npcs:
            context_parts.append(f"\n**关键角色**: {', '.join(state.npcs.keys())}")

        # 世界状态
        context_parts.append(f"\n**紧张度**: {state.world_state.get('tension_level', 5)}/10")
        context_parts.append(f"**核心冲突**: {state.world_state.get('central_conflict', '')}")

        return "\n".join(context_parts)

    async def process_choice(
        self,
        state: StoryState,
        choice: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理用户选择，生成后果

        Args:
            state: 故事状态
            choice: 选择数据

        Returns:
            选择后果和分析
        """
        # 生成选择后果
        prompt = f"""用户在以下场景做出了选择。请生成后果和心理分析。

## 场景
{state.scenes[-1].get('description', '')[:300]}

## 用户选择
{choice.get('text', '')}

## 选择动机
{choice.get('motivation', '')}

## 心理维度
{choice.get('psychological_dimension', '')}

请返回 JSON：
{{
    "immediate_consequence": "立即后果（100-150字，具体描写）",
    "long_term_impact": "长期影响（提示）",
    "npc_reactions": {{
        "NPC名字": "反应描述"
    }},
    "world_state_changes": {{
        "变量名": "变化"
    }},
    "psychological_analysis": {{
        "trait_revealed": "揭示的特征",
        "value_reflected": "反映的价值观",
        "moral_stance": "道德立场",
        "decision_style": "决策风格",
        "confidence": 4
    }}
}}
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            result = json.loads(content)

            # 记录选择
            choice_record = {
                "scene_number": state.current_scene,
                "choice": choice,
                "consequence": result.get("immediate_consequence", ""),
                "analysis": result.get("psychological_analysis", {}),
                "timestamp": datetime.now().isoformat()
            }

            state.choices_made.append(choice_record)

            # 更新世界状态
            world_changes = result.get("world_state_changes", {})
            state.world_state.update(world_changes)

            return result

        except json.JSONDecodeError:
            return {
                "immediate_consequence": response.content,
                "psychological_analysis": {}
            }

    async def generate_npc_dialogue(
        self,
        state: StoryState,
        npc_name: str,
        context: str
    ) -> str:
        """
        生成 NPC 对话

        Args:
            state: 故事状态
            npc_name: NPC 名字
            context: 对话上下文

        Returns:
            NPC 对话内容
        """
        npc = state.npcs.get(npc_name, {})

        prompt = f"""你是 {npc_name}，以下是你的信息：

**角色**: {npc.get('role', '')}
**性格**: {npc.get('personality', '')}
**与主角关系**: {npc.get('relationship', '')}

**当前情境**:
{context}

请生成符合角色性格的对话（100-150字）。对话要：
1. 符合角色性格
2. 推进剧情
3. 有感情色彩
4. 细节丰富（动作、表情等）

直接返回对话内容，不要JSON格式。
"""

        response = await self.llm.ainvoke(prompt)
        return response.content

    async def generate_story_analysis(
        self,
        state: StoryState
    ) -> Dict[str, Any]:
        """
        生成故事结束后的综合分析

        Args:
            state: 故事状态

        Returns:
            综合分析报告
        """
        # 收集所有选择的分析
        all_analyses = [
            choice.get("analysis", {})
            for choice in state.choices_made
        ]

        prompt = f"""基于用户在整个故事中的选择，生成综合人格分析。

## 故事信息
类型: {state.genre}
场景数: {len(state.scenes)}
选择数: {len(state.choices_made)}

## 所有选择及分析
{json.dumps(all_analyses, ensure_ascii=False, indent=2)}

请生成综合分析（返回 JSON）：
{{
    "overall_personality": {{
        "openness": "评分和描述",
        "conscientiousness": "评分和描述",
        "extraversion": "评分和描述",
        "agreeableness": "评分和描述",
        "neuroticism": "评分和描述"
    }},
    "core_values": ["识别出的核心价值观"],
    "moral_foundations": {{
        "harm_care": "评分",
        "fairness": "评分",
        "ingroup_loyalty": "评分",
        "authority": "评分",
        "purity": "评分"
    }},
    "decision_patterns": ["决策模式总结"],
    "key_moments": [
        {{
            "scene": "场景号",
            "choice": "关键选择",
            "significance": "重要性说明"
        }}
    ],
    "character_arc": "角色成长轨迹描述",
    "recommendations": "基于分析的建议"
}}
"""

        response = await self.llm.ainvoke(prompt)

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()

            analysis = json.loads(content)
            analysis["story_id"] = state.story_id
            analysis["generated_at"] = datetime.now().isoformat()

            return analysis

        except json.JSONDecodeError:
            return {
                "raw_analysis": response.content,
                "story_id": state.story_id,
                "generated_at": datetime.now().isoformat()
            }

    def save_story(self, state: StoryState):
        """保存故事到文件"""
        file_path = self.stories_dir / f"{state.story_id}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    def load_story(self, story_id: str) -> Optional[StoryState]:
        """加载故事"""
        file_path = self.stories_dir / f"{story_id}.json"

        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return StoryState.from_dict(data)

    def list_stories(self) -> List[Dict[str, Any]]:
        """列出所有故事"""
        stories = []

        for file_path in self.stories_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                stories.append({
                    "story_id": data.get("story_id"),
                    "genre": data.get("genre"),
                    "timestamp": data.get("timestamp"),
                    "scenes_count": len(data.get("scenes", [])),
                    "choices_count": len(data.get("choices_made", []))
                })
            except Exception:
                continue

        return sorted(stories, key=lambda x: x.get("timestamp", ""), reverse=True)
