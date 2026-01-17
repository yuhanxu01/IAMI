#!/usr/bin/env python3
"""
IAMI Streamlit 应用

一个交互式 Web 界面，用于：
1. 学习模式 - 通过对话了解用户
2. 模拟模式 - 以用户思维模式对话
3. 记忆浏览 - 查看已存储的记忆
4. 可视化 - 知识图谱和演变分析
5. 索引管理 - 管理 RAG 系统
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from streamlit_option_menu import option_menu
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="IAMI - I Am My Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stats-card {
        background: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    .stats-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    .stats-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
    }
    .memory-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
        transition: all 0.3s;
    }
    .memory-card:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
    }
    .question-card {
        background: #fff9e6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #ffd700;
        margin: 1rem 0;
    }
    .answer-card {
        background: #e6f7ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1890ff;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.learning_history = []
        st.session_state.simulation_history = []
        st.session_state.current_question = None
        st.session_state.indexer = None
        st.session_state.agents_loaded = False


def load_agents():
    """加载 IAMI agents"""
    if not st.session_state.agents_loaded:
        try:
            from graphrag.indexer.hybrid_indexer import HybridIndexer
            from graphrag.indexer.graph_indexer import IndexConfig
            from graphrag.agents import (
                IAMILearningAgent,
                IAMISimulationAgent,
                IAMIAnalysisAgent
            )

            # 创建混合索引器
            config = IndexConfig(
                working_dir=os.getenv("GRAPHRAG_INDEX_DIR", "./graphrag/storage/index"),
                api_key=os.getenv("DEEPSEEK_API_KEY")
            )

            st.session_state.indexer = HybridIndexer(
                lightrag_config=config,
                chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./memory/vector_store"),
                chroma_collection=os.getenv("CHROMA_COLLECTION", "iami_conversations")
            )

            # 创建代理
            st.session_state.learning_agent = IAMILearningAgent(st.session_state.indexer)
            st.session_state.simulation_agent = IAMISimulationAgent(st.session_state.indexer)
            st.session_state.analysis_agent = IAMIAnalysisAgent(st.session_state.indexer)

            st.session_state.agents_loaded = True

            return True

        except Exception as e:
            st.error(f"加载代理失败: {e}")
            return False

    return True


def sidebar_menu():
    """侧边栏菜单"""
    with st.sidebar:
        st.markdown("# 🧠 IAMI")
        st.markdown("### I Am My Intelligence")
        st.markdown("---")

        selected = option_menu(
            menu_title=None,
            options=["首页", "学习模式", "模拟模式", "记忆浏览", "可视化", "索引管理"],
            icons=["house", "mortarboard", "chat", "database", "graph-up", "gear"],
            menu_icon="cast",
            default_index=0,
        )

        st.markdown("---")

        # 显示系统状态
        st.markdown("### 系统状态")

        # 检查 API key
        if os.getenv("DEEPSEEK_API_KEY"):
            st.success("✓ API Key 已配置")
        else:
            st.error("✗ API Key 未配置")

        # 显示索引状态
        if st.session_state.agents_loaded:
            st.success("✓ 代理已加载")

            if st.session_state.indexer:
                try:
                    stats = st.session_state.indexer.get_stats()
                    st.info(f"📊 LightRAG: {len(stats.get('lightrag', {}).get('files', []))} 文件")
                    st.info(f"📊 ChromaDB: {stats.get('chromadb', {}).get('document_count', 0)} 文档")
                except:
                    pass
        else:
            st.warning("⚠ 代理未加载")

        return selected


def home_page():
    """首页"""
    st.markdown('<p class="main-header">🧠 IAMI - I Am My Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">我即是我 - 让 AI 学习并模拟你的思维模式</p>', unsafe_allow_html=True)

    # 核心理念
    st.markdown("### 🎯 核心理念")
    st.info("""
    **人的思想是动态的，会随时间变化。**
    本系统不只记录"你是谁"，更追踪"你如何变化"。
    """)

    # 功能介绍
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📚 学习模式")
        st.markdown("""
        - 基于学术框架（Big Five、Schwartz Values）提问
        - 通过具体情境了解你的思维
        - 自动提取并存储人格特征
        - 追踪你的思想演变
        """)

        st.markdown("#### 💬 模拟模式")
        st.markdown("""
        - 以你的思维模式回答问题
        - 考虑你的性格、价值观、语言风格
        - 反映你的最新思想状态
        - 测试 AI 对你的理解程度
        """)

    with col2:
        st.markdown("#### 🗄️ 记忆系统")
        st.markdown("""
        - **长期记忆**: 性格、价值观、思维模式
        - **短期记忆**: 最近的对话和想法
        - **关系网络**: 重要人物及其影响
        - **时间轴**: 思想演变的历史快照
        """)

        st.markdown("#### 📊 混合检索")
        st.markdown("""
        - **LightRAG**: 知识图谱，理解概念关系
        - **ChromaDB**: 向量检索，找到相似对话
        - **LangGraph**: 自适应工作流，智能路由
        """)

    # 学术框架
    st.markdown("---")
    st.markdown("### 🎓 学术框架")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**个体心理学**")
        st.markdown("""
        - Big Five Inventory (BFI-2)
        - Schwartz Value Survey
        - Moral Foundations Theory
        - Political Compass
        """)

    with col2:
        st.markdown("**社会心理学**")
        st.markdown("""
        - Bronfenbrenner 生态系统
        - Social Identity Theory
        - Social Network Analysis
        - Social Capital Theory
        """)

    with col3:
        st.markdown("**方法论**")
        st.markdown("""
        - 情境判断测试
        - 真实经历追溯
        - 时间序列分析
        - 多维度建模
        """)

    # 快速开始
    st.markdown("---")
    st.markdown("### 🚀 快速开始")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📚 开始学习", use_container_width=True, type="primary"):
            st.session_state.selected_page = "学习模式"
            st.rerun()

    with col2:
        if st.button("💬 测试模拟", use_container_width=True):
            st.session_state.selected_page = "模拟模式"
            st.rerun()

    with col3:
        if st.button("🗄️ 浏览记忆", use_container_width=True):
            st.session_state.selected_page = "记忆浏览"
            st.rerun()

    # 统计信息
    if st.session_state.agents_loaded:
        st.markdown("---")
        st.markdown("### 📊 学习进度")

        try:
            stats = asyncio.run(st.session_state.learning_agent.get_learning_stats())

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown('<div class="stats-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="stats-number">{stats.get("total_questions", 0)}</div>', unsafe_allow_html=True)
                st.markdown('<div class="stats-label">已回答问题</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="stats-card">', unsafe_allow_html=True)
                completion = stats.get("completion_rate", 0)
                st.markdown(f'<div class="stats-number">{completion:.1f}%</div>', unsafe_allow_html=True)
                st.markdown('<div class="stats-label">完成度</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col3:
                st.markdown('<div class="stats-card">', unsafe_allow_html=True)
                category_count = len(stats.get("category_breakdown", {}))
                st.markdown(f'<div class="stats-number">{category_count}</div>', unsafe_allow_html=True)
                st.markdown('<div class="stats-label">涉及类别</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col4:
                st.markdown('<div class="stats-card">', unsafe_allow_html=True)
                if st.session_state.indexer:
                    idx_stats = st.session_state.indexer.get_stats()
                    doc_count = idx_stats.get('chromadb', {}).get('document_count', 0)
                    st.markdown(f'<div class="stats-number">{doc_count}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="stats-label">索引文档</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"无法加载统计信息: {e}")


def main():
    """主函数"""
    # 初始化
    init_session_state()

    # 加载代理
    if not load_agents():
        st.error("⚠️ 系统初始化失败，请检查配置")
        st.stop()

    # 侧边栏菜单
    selected = sidebar_menu()

    # 路由到对应页面
    if selected == "首页":
        home_page()
    elif selected == "学习模式":
        from pages import learning_mode
        learning_mode.render()
    elif selected == "模拟模式":
        from pages import simulation_mode
        simulation_mode.render()
    elif selected == "记忆浏览":
        from pages import memory_browser
        memory_browser.render()
    elif selected == "可视化":
        from pages import visualization
        visualization.render()
    elif selected == "索引管理":
        from pages import index_manager
        index_manager.render()


if __name__ == "__main__":
    main()
