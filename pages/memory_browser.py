"""
记忆浏览页面

功能：
1. 查看长期记忆（性格、价值观等）
2. 查看短期记忆
3. 查看关系网络
4. 查看时间轴
"""

import json
import streamlit as st
from pathlib import Path


def render():
    """渲染记忆浏览页面"""
    st.markdown("# ◇ 记忆浏览")
    st.markdown("查看已存储的记忆数据")
    st.markdown("---")

    if "user_id" not in st.session_state or not st.session_state.user_id:
        st.error("请先登录")
        return

    user_id = st.session_state.user_id
    base_user_path = Path(f"data/users/{user_id}")

    # 选择记忆类型
    memory_type = st.selectbox(
        "选择记忆类型",
        options=[
            "性格特征 (Personality)",
            "价值观 (Values)",
            "思维模式 (Thinking Patterns)",
            "语言风格 (Language Style)",
            "知识储备 (Knowledge)",
            "人际关系 (Relationships)",
            "时间轴 (Timeline)",
            "对话记录 (Conversations)",
            "故事经历 (Stories)"
        ]
    )

    if "Personality" in memory_type:
        show_personality(base_user_path)
    elif "Values" in memory_type:
        show_values(base_user_path)
    elif "Thinking" in memory_type:
        show_thinking_patterns(base_user_path)
    elif "Language" in memory_type:
        show_language_style(base_user_path)
    elif "Knowledge" in memory_type:
        show_knowledge(base_user_path)
    elif "Relationships" in memory_type:
        show_relationships(base_user_path)
    elif "Timeline" in memory_type:
        show_timeline(base_user_path)
    elif "Conversations" in memory_type:
        show_conversations(base_user_path)
    elif "Stories" in memory_type:
        show_stories()


def load_json_safely(file_path: str):
    """安全加载 JSON 文件"""
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载文件失败: {e}")
        return None


def show_personality(base_user_path):
    """显示性格特征"""
    st.markdown("### ◈ 性格特征")

    data = load_json_safely(base_user_path / "memory/long_term/personality.json")

    if not data:
        st.info("暂无性格数据，请先使用学习模式")
        return

    # 显示历史记录
    history = data.get("history", [])

    if history:
        st.markdown(f"共有 {len(history)} 条记录")

        # 分组显示
        traits_map = {}
        for item in history:
            trait = item.get("trait", "unknown")
            if trait not in traits_map:
                traits_map[trait] = []
            traits_map[trait].append(item)

        for trait, items in traits_map.items():
            with st.expander(f"**{trait}** ({len(items)} 条记录)", expanded=False):
                for item in sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**值**: {item.get('value', '')}")
                        st.markdown(f"**证据**: {item.get('evidence', '')}")
                    with col2:
                        confidence = "✦" * item.get("confidence", 0)
                        st.markdown(f"**置信度**: {confidence}")
                        st.markdown(f"**时间**: {item.get('timestamp', '')[:10]}")
                    st.markdown("---")
    else:
        st.info("暂无历史记录")


def show_values(base_user_path):
    """显示价值观"""
    st.markdown("### ◈ 价值观")

    data = load_json_safely(base_user_path / "memory/long_term/values.json")

    if not data:
        st.info("暂无价值观数据，请先使用学习模式")
        return

    history = data.get("history", [])

    if history:
        st.markdown(f"共有 {len(history)} 条记录")

        for item in sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)[:20]:
            st.markdown(f"**{item.get('value_type', 'unknown')}**")
            st.markdown(f"描述: {item.get('description', '')}")
            st.markdown(f"证据: {item.get('evidence', '')}")
            confidence = "✦" * item.get("confidence", 0)
            st.markdown(f"置信度: {confidence} | 时间: {item.get('timestamp', '')[:10]}")
            st.markdown("---")
    else:
        st.info("暂无历史记录")


def show_thinking_patterns(base_user_path):
    """显示思维模式"""
    st.markdown("### ◈ 思维模式")

    data = load_json_safely(base_user_path / "memory/long_term/thinking_patterns.json")

    if not data:
        st.info("暂无思维模式数据")
        return

    st.json(data)


def show_language_style(base_user_path):
    """显示语言风格"""
    st.markdown("### ◈ 语言风格")

    data = load_json_safely(base_user_path / "memory/long_term/language_style.json")

    if not data:
        st.info("暂无语言风格数据")
        return

    st.json(data)


def show_knowledge(base_user_path):
    """显示知识储备"""
    st.markdown("### ◈ 知识储备")

    data = load_json_safely(base_user_path / "memory/long_term/knowledge.json")

    if not data:
        st.info("暂无知识数据")
        return

    st.json(data)


def show_relationships(base_user_path):
    """显示人际关系"""
    st.markdown("### ◈ 人际关系网络")

    data = load_json_safely(base_user_path / "memory/relationships/network.json")

    if not data:
        st.info("暂无关系网络数据")
        return

    st.json(data)


def show_timeline(base_user_path):
    """显示时间轴"""
    st.markdown("### ◈ 思想演变时间轴")

    data = load_json_safely(base_user_path / "memory/timeline/snapshots.json")

    if not data:
        st.info("暂无时间轴数据")
        return

    snapshots = data.get("snapshots", [])

    if snapshots:
        st.markdown(f"共有 {len(snapshots)} 个时间快照")

        for snapshot in sorted(snapshots, key=lambda x: x.get("timestamp", ""), reverse=True):
            with st.expander(f"◇ {snapshot.get('timestamp', '')[:10]}", expanded=False):
                st.json(snapshot)
    else:
        st.info("暂无快照")


def show_conversations(base_user_path):
    """显示对话记录"""
    st.markdown("### ◈ 对话记录")

    conv_dir = base_user_path / "memory/conversations"

    if not conv_dir.exists():
        st.info("暂无对话记录目录")
        return

    # 列出所有对话文件
    conv_files = sorted(conv_dir.glob("*.md"), reverse=True)

    if not conv_files:
        st.info("暂无对话记录")
        return

    st.markdown(f"共有 {len(conv_files)} 个对话文件")

    selected_file = st.selectbox(
        "选择对话文件",
        options=[f.name for f in conv_files]
    )

    if selected_file:
        file_path = conv_dir / selected_file

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        st.markdown(content)


def show_stories():
    """显示故事经历"""
    st.markdown("### ◈ 故事经历")
    
    import asyncio
    from graphrag.agents import IAMIStoryAgent
    
    # 初始化代理 (如果需要)
    if "story_agent" not in st.session_state:
        st.session_state.story_agent = IAMIStoryAgent(
            user_id=st.session_state.user_id,
            indexer=st.session_state.indexer
        )
    
    agent = st.session_state.story_agent
    
    # 获取故事列表
    try:
        stories = asyncio.run(agent.list_stories())
    except Exception as e:
        st.error(f"加载故事失败: {e}")
        return

    if not stories:
        st.info("暂无故事记录")
        return

    st.markdown(f"共有 {len(stories)} 个精彩故事")
    
    for story in stories:
        # 加载完整故事以显示更多详情 (可选，如果列表包含了足够信息则不必)
        with st.expander(f"📚 {story['genre']} - {story['timestamp'][:10]}"):
            st.caption(f"ID: {story['story_id']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("章节数", story['scenes_count'])
            with col2:
                st.metric("选择数", story['choices_count'])
            
            if st.button("查看详情", key=f"view_{story['story_id']}"):
                # 加载完整状态
                try:
                    full_story = asyncio.run(agent.load_story(story['story_id']))
                    if full_story and full_story.scenes:
                        st.markdown("---")
                        st.markdown(f"**标题**: {full_story.scenes[0].get('title', '无题')}")
                        st.markdown(f"**背景**: {full_story.setting.get('world', '')}")
                        
                        st.markdown("### 章节回顾")
                        for scene in full_story.scenes:
                            st.text(f"第 {scene['scene_number']+1} 章: {scene['title']}")
                except Exception as e:
                    st.error(f"加载详情失败: {e}")

