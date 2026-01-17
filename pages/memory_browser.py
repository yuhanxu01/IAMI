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
    st.markdown("# 🗄️ 记忆浏览")
    st.markdown("查看已存储的记忆数据")
    st.markdown("---")

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
            "对话记录 (Conversations)"
        ]
    )

    if "Personality" in memory_type:
        show_personality()
    elif "Values" in memory_type:
        show_values()
    elif "Thinking" in memory_type:
        show_thinking_patterns()
    elif "Language" in memory_type:
        show_language_style()
    elif "Knowledge" in memory_type:
        show_knowledge()
    elif "Relationships" in memory_type:
        show_relationships()
    elif "Timeline" in memory_type:
        show_timeline()
    elif "Conversations" in memory_type:
        show_conversations()


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


def show_personality():
    """显示性格特征"""
    st.markdown("### 🎭 性格特征 (Big Five)")

    data = load_json_safely("memory/long_term/personality.json")

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
                        confidence = "⭐" * item.get("confidence", 0)
                        st.markdown(f"**置信度**: {confidence}")
                        st.markdown(f"**时间**: {item.get('timestamp', '')[:10]}")
                    st.markdown("---")
    else:
        st.info("暂无历史记录")


def show_values():
    """显示价值观"""
    st.markdown("### 💎 价值观 (Schwartz Values)")

    data = load_json_safely("memory/long_term/values.json")

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
            confidence = "⭐" * item.get("confidence", 0)
            st.markdown(f"置信度: {confidence} | 时间: {item.get('timestamp', '')[:10]}")
            st.markdown("---")
    else:
        st.info("暂无历史记录")


def show_thinking_patterns():
    """显示思维模式"""
    st.markdown("### 🧠 思维模式")

    data = load_json_safely("memory/long_term/thinking_patterns.json")

    if not data:
        st.info("暂无思维模式数据")
        return

    st.json(data)


def show_language_style():
    """显示语言风格"""
    st.markdown("### 💬 语言风格")

    data = load_json_safely("memory/long_term/language_style.json")

    if not data:
        st.info("暂无语言风格数据")
        return

    st.json(data)


def show_knowledge():
    """显示知识储备"""
    st.markdown("### 📚 知识储备")

    data = load_json_safely("memory/long_term/knowledge.json")

    if not data:
        st.info("暂无知识数据")
        return

    st.json(data)


def show_relationships():
    """显示人际关系"""
    st.markdown("### 👥 人际关系网络")

    data = load_json_safely("memory/relationships/network.json")

    if not data:
        st.info("暂无关系网络数据")
        return

    st.json(data)


def show_timeline():
    """显示时间轴"""
    st.markdown("### ⏰ 思想演变时间轴")

    data = load_json_safely("memory/timeline/snapshots.json")

    if not data:
        st.info("暂无时间轴数据")
        return

    snapshots = data.get("snapshots", [])

    if snapshots:
        st.markdown(f"共有 {len(snapshots)} 个时间快照")

        for snapshot in sorted(snapshots, key=lambda x: x.get("timestamp", ""), reverse=True):
            with st.expander(f"📸 {snapshot.get('timestamp', '')[:10]}", expanded=False):
                st.json(snapshot)
    else:
        st.info("暂无快照")


def show_conversations():
    """显示对话记录"""
    st.markdown("### 💬 对话记录")

    conv_dir = Path("memory/conversations")

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
