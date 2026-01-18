"""
IAMI 故事模式 Agent

通过沉浸式的故事和角色扮演来分析用户的人格特征。
每次都是全新生成的故事，用户的选择会影响剧情走向。
"""

import os
import json
import logging
import random
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI
from asgiref.sync import sync_to_async
from accounts.models import StoryTemplate, UserStory
from django.contrib.auth.models import User
from .iami_agents import IAMIBaseAgent

# 配置日志
logger = logging.getLogger(__name__)


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

    def __init__(self, user_id: str = "default", indexer=None):
        super().__init__(user_id=user_id, indexer=indexer)
        # self.stories_dir is no longer needed for primary storage, but keeping for backward compat if needed?
        # Let's fully switch to DB.


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

        response = await self.invoke_llm(prompt, call_type="story_generate_setting")

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            story_data = json.loads(content)

            # 创建故事状态
            # 查找或创建 StoryTemplate
            # 将生成的设定保存为 StoryTemplate
            setting_data = {
                "genre": genre,
                "title": story_data.get("title", "未命名"),
                "setting": story_data.get("setting", {}),
                "protagonist": story_data.get("protagonist", {}),
                "initial_scene": story_data.get("initial_scene", {}),
                "key_npcs": story_data.get("key_npcs", []),
                "central_conflict": story_data.get("central_conflict", ""),
                "potential_themes": story_data.get("potential_themes", [])
            }

            @sync_to_async
            def save_template_and_story(user_id_str, setting_dict):
                # 解析 ID
                try:
                    uid = int(user_id_str.replace("user_", ""))
                    user = User.objects.get(id=uid)
                except (ValueError, User.DoesNotExist) as e:
                    # Fallback for default/test user
                    logger.warning(f"User lookup failed for {user_id_str}: {e}")
                    user = User.objects.get(username="renqing") if User.objects.filter(username="renqing").exists() else User.objects.first()

                # 创建模板
                template = StoryTemplate.objects.create(
                    title=setting_dict["title"],
                    genre=setting_dict["genre"],
                    description=setting_dict["setting"].get("world", "")[:200],
                    source_data=setting_dict,
                    created_by=user,
                    is_public=False # 默认私有
                )
                
                # 创建用户故事
                state = StoryState()
                state.story_id = f"db_{template.id}_{datetime.now().timestamp()}"
                state.genre = setting_dict["genre"]
                state.setting = setting_dict["setting"]
                state.protagonist = setting_dict["protagonist"]
                
                # 初始场景
                initial_scene = {
                    "scene_number": 0,
                    "title": setting_dict["title"],
                    "description": setting_dict["initial_scene"].get("description", ""),
                    "environment": setting_dict["initial_scene"].get("environment", ""),
                    "mood": setting_dict["initial_scene"].get("mood", ""),
                    "timestamp": datetime.now().isoformat()
                }
                state.scenes.append(initial_scene)
                
                # NPC
                for npc_data in setting_dict.get("key_npcs", []):
                    state.npcs[npc_data.get("name", "")] = npc_data
                    
                # World State
                state.world_state = {
                    "central_conflict": setting_dict.get("central_conflict", ""),
                    "themes": setting_dict.get("potential_themes", []),
                    "tension_level": 1
                }

                # 保存到 UserStory
                user_story = UserStory.objects.create(
                    user=user,
                    template=template,
                    current_state=state.to_dict(),
                    is_active=True
                )
                
                # 更新 ID 以匹配 DB
                state.story_id = str(user_story.id)
                return state

            return await save_template_and_story(self.user_id, setting_data)

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
    "immediate_consequence": "对上一个选择的立即后果描写（150-200字，细致感人），如果你是开场第一章，这里可以为空字符串",
    "description": "新的场景描写（400-500字，包含环境、人物、对话、动作等）",
    "environment_details": "环境细节",
    "character_emotions": "角色情绪",
    "npc_reactions": {{
        "NPC名字": "基于上一个选择的反应描述"
    }},
    "world_state_changes": {{
        "tension_level": "更新后的数值(1-10)",
        "其他变量": "数值或状态变化"
    }},
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

        response = await self.invoke_llm(prompt, call_type="story_generate_scene")

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            scene_data = json.loads(content)

            # 更新世界状态
            try:
                tension_change = int(scene_data.get("tension_change", 0))
            except (ValueError, TypeError) as e:
                # 如果无法转换为整数，尝试提取数字或默认为 0
                logger.warning(f"Failed to parse tension_change: {e}")
                val = str(scene_data.get("tension_change", "0"))
                match = re.search(r'[-+]?\d+', val)
                tension_change = int(match.group()) if match else 0

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

## 选择动机 (预设)
{choice.get('motivation', '')}

## 可能后果 (预设提示)
{choice.get('potential_consequence', '')}

## 心理维度
{choice.get('psychological_dimension', '')}

请结合上述**预设的动机和后果提示**，分析用户做出此选择的深层心理原因。

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

        response = await self.invoke_llm(prompt, call_type="story_process_choice")

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

        response = await self.invoke_llm(prompt, call_type="story_npc_dialogue")
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

        response = await self.invoke_llm(prompt, call_type="story_analysis")

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

    async def save_story(self, state: StoryState) -> bool:
        """保存故事到数据库，返回是否成功"""
        @sync_to_async
        def _save(sid, state_dict):
            try:
                # 尝试通过 ID 查找
                if sid.isdigit():
                    us = UserStory.objects.get(id=int(sid))
                    us.current_state = state_dict
                    us.save()
                    return True
            except Exception as e:
                print(f"保存故事失败 (ID: {sid}): {e}")
                return False
            return False
        
        return await _save(state.story_id, state.to_dict())

    async def load_story(self, story_id: str) -> Optional[StoryState]:
        """加载故事"""
        @sync_to_async
        def _load(sid):
            try:
                if isinstance(sid, int) or sid.isdigit():
                    us = UserStory.objects.get(id=int(sid))
                    return StoryState.from_dict(us.current_state)
            except Exception:
                pass
            return None

        return await _load(story_id)

    async def list_stories(self) -> List[Dict[str, Any]]:
        """列出所有故事"""
        @sync_to_async
        def _list(user_id_str):
            try:
                uid = int(user_id_str.replace("user_", ""))
                user = User.objects.get(id=uid)
                stories = UserStory.objects.filter(user=user).select_related('template')
                
                results = []
                for s in stories:
                    data = s.current_state
                    results.append({
                        "story_id": str(s.id),
                        "genre": data.get("genre", "Unknown"),
                        "timestamp": s.last_played_at.isoformat(),
                        "scenes_count": len(data.get("scenes", [])),
                        "choices_count": len(data.get("choices_made", []))
                    })
                return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
            except Exception:
                return []

        return await _list(self.user_id)

    async def get_public_templates(self) -> List[Dict[str, Any]]:
        """获取公开的故事模版"""
        @sync_to_async
        def _list_templates():
            templates = StoryTemplate.objects.filter(is_public=True).order_by('-play_count')
            results = []
            for t in templates:
                results.append({
                    "id": t.id,
                    "title": t.title,
                    "genre": t.genre,
                    "description": t.description,
                    "play_count": t.play_count,
                    "author": t.created_by.username
                })
            return results
        return await _list_templates()

    async def create_story_from_template(self, template_id: int) -> StoryState:
        """从模版创建新故事"""
        @sync_to_async
        def _create(tid, user_id_str):
            try:
                template = StoryTemplate.objects.get(id=tid)
                uid = int(user_id_str.replace("user_", ""))
                user = User.objects.get(id=uid)
                
                # 增加游玩计数
                template.play_count += 1
                template.save()
                
                setting_dict = template.source_data
                
                # 初始化 StoryState
                state = StoryState()
                state.genre = setting_dict["genre"]
                state.setting = setting_dict["setting"]
                state.protagonist = setting_dict["protagonist"]
                
                # 初始场景
                initial_scene = {
                    "scene_number": 0,
                    "title": setting_dict["title"],
                    "description": setting_dict["initial_scene"].get("description", ""),
                    "environment": setting_dict["initial_scene"].get("environment", ""),
                    "mood": setting_dict["initial_scene"].get("mood", ""),
                    "timestamp": datetime.now().isoformat()
                }
                state.scenes.append(initial_scene)
                
                for npc_data in setting_dict.get("key_npcs", []):
                    state.npcs[npc_data.get("name", "")] = npc_data
                    
                state.world_state = {
                    "central_conflict": setting_dict.get("central_conflict", ""),
                    "themes": setting_dict.get("potential_themes", []),
                    "tension_level": 1
                }
                
                # 创建 UserStory
                us = UserStory.objects.create(
                    user=user,
                    template=template,
                    current_state=state.to_dict(),
                    is_active=True
                )
                state.story_id = str(us.id)
                return state
            except Exception as e:
                raise e
        
        return await _create(template_id, self.user_id)

    async def prefetch_scenes_for_choices(
        self,
        state: StoryState,
        choices: List[Dict[str, Any]]
    ) -> Dict[int, Dict[str, Any]]:
        """
        预生成每个选择对应的下一场景
        
        Args:
            state: 当前故事状态
            choices: 选择列表
            
        Returns:
            {choice_id: scene_data} 字典
        """
        import asyncio
        
        async def generate_for_choice(choice):
            # 模拟选择，生成对应场景
            simulated_choice = {
                "option_text": choice.get("text", ""),
                "consequence": f"基于选择: {choice.get('text', '')[:50]}...",
                "motivation": choice.get("motivation", "")
            }
            scene = await self.generate_next_scene(state, simulated_choice)
            return (choice.get("id"), scene)
        
        # 并行生成所有选择的场景
        tasks = [generate_for_choice(c) for c in choices]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prefetched = {}
        for result in results:
            if isinstance(result, tuple):
                choice_id, scene = result
                prefetched[choice_id] = scene
        
        return prefetched

    async def process_choice_quick(
        self,
        state: StoryState,
        choice: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        快速处理选择 - 仅生成后果描述，不做深度分析
        
        Args:
            state: 故事状态
            choice: 选择数据
            
        Returns:
            基本后果信息
        """
        # 生成简短的后果描述
        prompt = f"""用户做出了以下选择，请生成简短的后果描述。

## 选择
{choice.get('text', '')}

请返回 JSON（仅包含后果，不需要分析）：
{{
    "immediate_consequence": "后果描述（50-80字）",
    "tension_change": "+1 或 -1 或 0"
}}
"""
        response = await self.invoke_llm(prompt, call_type="story_choice_quick")
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            result = json.loads(content)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse choice response: {e}")
            result = {"immediate_consequence": "你的选择产生了影响...", "tension_change": "0"}
        
        # 快速记录选择（无深度分析）
        choice_record = {
            "scene_number": state.current_scene,
            "choice": choice,
            "consequence": result.get("immediate_consequence", ""),
            "analysis": {},  # 稍后后台填充
            "timestamp": datetime.now().isoformat()
        }
        state.choices_made.append(choice_record)
        
        return result

    async def process_choice_analysis_background(
        self,
        state: StoryState,
        choice_index: int
    ):
        """
        后台深度分析选择（更新已记录的选择）
        
        Args:
            state: 故事状态
            choice_index: 要分析的选择索引
        """
        if choice_index < 0 or choice_index >= len(state.choices_made):
            return
            
        choice_record = state.choices_made[choice_index]
        choice = choice_record.get("choice", {})
        
        prompt = f"""分析用户的选择，提取心理特征。

## 选择
{choice.get('text', '')}

## 预设动机
{choice.get('motivation', '')}

## 预设后果
{choice.get('potential_consequence', '')}

## 心理维度
{choice.get('psychological_dimension', '')}

请结合上述**预设的动机和后果提示**，分析用户做出此选择的深层心理原因。

请返回 JSON：
{{
    "psychological_analysis": {{
        "trait_revealed": "揭示的特征",
        "value_reflected": "反映的价值观",
        "moral_stance": "道德立场",
        "decision_style": "决策风格",
        "confidence": 4
    }}
}}
"""
        response = await self.invoke_llm(prompt, call_type="story_choice_analysis")
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            result = json.loads(content)

            # 更新选择记录
            state.choices_made[choice_index]["analysis"] = result.get("psychological_analysis", {})

            # 保存更新
            await self.save_story(state)
        except (json.JSONDecodeError, KeyError, TypeError, IndexError) as e:
            logger.warning(f"Failed to parse/save choice analysis: {e}")

