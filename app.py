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

# 初始化 Django
try:
    from django_setup import setup_django
    setup_django()
    from accounts.services import login_user, register_user
except ImportError:
    st.error("Django 环境初始化失败")

# 页面配置
st.set_page_config(
    page_title="我即是我 - 个人智能系统",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS - 现代化设计
st.markdown("""
<style>
    /* 全局样式 */
    * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
    }
    
    /* 主容器背景渐变 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background_attachment: fixed;
    }
    
    .block-container {
        background: rgba(15, 18, 25, 0.7);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 2.5rem;
        box-shadow: 0 8px 48px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #efefef !important;
    }
    
    /* 移动端适配 */
    @media (max-width: 768px) {
        .block-container {
            padding: 1.2rem;
            border-radius: 12px;
            margin-top: 0.5rem;
        }
        
        .main-header {
            font-size: 2.2rem !important;
        }
        
        .sub-header {
            font-size: 1.1rem !important;
            margin-bottom: 1.5rem !important;
        }
        
        .stats-card {
            padding: 1.5rem !important;
        }
        
        .stats-number {
            font-size: 2.2rem !important;
        }
        
        /* 强制所有列在手机上堆叠 */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 1rem;
        }
    }
    
    /* 主标题 */
    .main-header {
        font-size: 3.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a5b4fc 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        text-align: center;
        animation: gradient-shift 3s ease infinite;
        background-size: 200% 200%;
        text-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    
    /* 副标题 */
    .sub-header {
        font-size: 1.3rem;
        color: #cbd5e1;
        margin-bottom: 2.5rem;
        text-align: center;
        font-weight: 400;
    }
    
    /* 统计卡片 - 玻璃态效果 */
    .stats-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(12px);
        padding: 2.2rem;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        margin-bottom: 1.5rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .stats-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }
    
    .stats-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 16px 48px rgba(102, 126, 234, 0.25);
    }
    
    .stats-card:hover::before {
        transform: scaleX(1);
    }
    
    /* 统计数字 */
    .stats-number {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    /* 统计标签 */
    .stats-label {
        font-size: 0.95rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* 记忆卡片 */
    .memory-card {
        background: rgba(30, 41, 59, 0.4);
        padding: 1.8rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 1.2rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        color: #e2e8f0;
    }
    
    .memory-card::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        transform: scaleY(0);
        transition: transform 0.3s ease;
    }
    
    .memory-card:hover {
        border-color: #667eea;
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
        transform: translateX(8px);
    }
    
    .memory-card:hover::after {
        transform: scaleY(1);
    }
    
    /* 问题卡片 */
    .question-card {
        background: linear-gradient(135deg, rgba(252, 211, 77, 0.1) 0%, rgba(245, 158, 11, 0.1) 100%);
        padding: 2rem;
        border-radius: 18px;
        border-left: 6px solid #fbbf24;
        border-right: 1px solid rgba(251, 191, 36, 0.2);
        border-top: 1px solid rgba(251, 191, 36, 0.2);
        border-bottom: 1px solid rgba(251, 191, 36, 0.2);
        margin: 1.8rem 0;
        box-shadow: 0 8px 32px rgba(251, 191, 36, 0.08);
        transition: all 0.3s ease;
        color: #fef3c7;
    }
    
    .question-card:hover {
        box-shadow: 0 8px 24px rgba(255, 215, 0, 0.2);
        transform: translateY(-4px);
    }
    
    /* 答案卡片 */
    .answer-card {
        background: linear-gradient(135deg, rgba(96, 165, 250, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%);
        padding: 2rem;
        border-radius: 18px;
        border-left: 6px solid #3b82f6;
        border-right: 1px solid rgba(59, 130, 246, 0.2);
        border-top: 1px solid rgba(59, 130, 246, 0.2);
        border-bottom: 1px solid rgba(59, 130, 246, 0.2);
        margin: 1.8rem 0;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.08);
        transition: all 0.3s ease;
        color: #dbeafe;
    }
    
    .answer-card:hover {
        box-shadow: 0 8px 24px rgba(24, 144, 255, 0.2);
        transform: translateY(-4px);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    @media (max-width: 768px) {
        .stButton > button {
            padding: 0.6rem 1.2rem !important;
            font-size: 0.9rem !important;
            width: 100% !important;
        }
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* 侧边栏样式增强 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1c24 0%, #2d3436 100%) !important;
        box-shadow: 4px 0 25px rgba(0, 0, 0, 0.5);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* 隐藏默认导航 */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: white !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
    }
    
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            width: 80% !important;
        }
    }

    /* 优化侧边栏内的 option_menu */
    .nav-link {
        border-radius: 12px !important;
        margin: 8px 0 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid transparent !important;
        padding: 12px 18px !important;
        color: white !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
    }

    .nav-link:hover {
        background-color: rgba(255, 255, 255, 0.2) !important;
        transform: translateX(10px) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
        color: white !important;
    }

    .nav-link-selected {
        background: rgba(102, 126, 234, 0.3) !important;
        border: 1px solid rgba(165, 180, 252, 0.5) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3) !important;
        font-weight: 700 !important;
        color: white !important;
    }

    /* 彻底清除 option_menu 的背景并修复圆角白边 */
    div[data-component-base="streamlit_option_menu.option_menu"],
    div[data-component-base="streamlit_option_menu.option_menu"] > div,
    iframe[title="streamlit_option_menu.option_menu"] {
        background-color: transparent !important;
        background: transparent !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        border: none !important;
    }

    /* 优化侧边栏内的文本一致性 */
    [data-testid="stSidebar"] section {
        background-color: transparent !important;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: rgba(30, 41, 59, 0.5) !important;
        color: white !important;
        border-radius: 10px;
        border: 2px solid rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #818cf8;
        box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2);
        background-color: rgba(30, 41, 59, 0.7) !important;
    }
    
    /* 警报/提示框样式 */
    .stAlert {
        background-color: rgba(30, 41, 59, 0.8) !important;
        color: white !important;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* 成功消息 */
    .stSuccess {
        background: linear-gradient(135deg, rgba(82, 196, 26, 0.1) 0%, rgba(82, 196, 26, 0.05) 100%);
        border-left: 4px solid #52c41a;
    }
    
    /* 警告消息 */
    .stWarning {
        background: linear-gradient(135deg, rgba(250, 173, 20, 0.1) 0%, rgba(250, 173, 20, 0.05) 100%);
        border-left: 4px solid #faad14;
    }
    
    /* 错误消息 */
    .stError {
        background: linear-gradient(135deg, rgba(255, 77, 79, 0.1) 0%, rgba(255, 77, 79, 0.05) 100%);
        border-left: 4px solid #ff4d4f;
    }
    
    /* 信息消息 */
    .stInfo {
        background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(24, 144, 255, 0.05) 100%);
        border-left: 4px solid #1890ff;
    }
    
    /* 彻底隐藏顶部白条和部署按钮 */
    /* Hide top decoration bar */
    [data-testid="stDecoration"] {
        display: none;
    }
    
    /* Hide deploy button */
    .stDeployButton {
        display: none;
    }
    
    /* Make header transparent but keep it rendered so toggle button exists */
    [data-testid="stHeader"] {
        background: transparent;
    }
    
    /* Ensure no white gap */
    header {
        background: transparent;
    }

    /* 加载动画 */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .stSpinner > div {
        border-color: #667eea !important;
        border-right-color: transparent !important;
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
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.user_id = None


def load_agents():
    """加载 IAMI agents"""
    if not st.session_state.logged_in:
        return False

    if not st.session_state.agents_loaded:
        try:
            from graphrag.indexer.hybrid_indexer import HybridIndexer
            from graphrag.indexer.graph_indexer import IndexConfig
            from graphrag.agents import (
                IAMILearningAgent,
                IAMISimulationAgent,
                IAMIAnalysisAgent
            )

            user_id = st.session_state.user_id
            base_user_dir = Path(f"data/users/{user_id}")
            
            # 创建混合索引器 (使用用户隔离路径)
            st.session_state.indexer = HybridIndexer(
                user_id=user_id,
                chroma_persist_dir=str(base_user_dir / "memory/vector_store"),
                chroma_collection=f"iami_conversations_{user_id}"
            )

            # 创建代理
            st.session_state.learning_agent = IAMILearningAgent(user_id=user_id, indexer=st.session_state.indexer)
            st.session_state.simulation_agent = IAMISimulationAgent(user_id=user_id, indexer=st.session_state.indexer)
            st.session_state.analysis_agent = IAMIAnalysisAgent(user_id=user_id, indexer=st.session_state.indexer)

            st.session_state.agents_loaded = True

            return True

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            st.error(f"加载代理失败: {e}")
            with st.expander("查看错误详情"):
                st.code(error_details)
            return False

    return True


def sidebar_menu():
    """侧边栏菜单"""
    with st.sidebar:
        st.markdown("# ◇ 我即是我")
        st.markdown("### 个人智能系统")
        st.markdown("---")

        selected = option_menu(
            menu_title=None,
            options=["首页", "个人档案", "学习模式", "日记模式", "记忆浏览", "模拟模式", "故事模式", "索引管理", "可视化", "统计"],
            icons=["house", "person-badge", "mortarboard", "book", "database", "chat", "book", "gear", "graph-up", "bar-chart-line"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {
                    "padding": "10px !important", 
                    "background-color": "#1a1c24 !important",
                    "border": "1px solid rgba(255, 255, 255, 0.1) !important",
                    "border-radius": "16px !important",
                    "overflow": "hidden !important"
                },
                "icon": {"color": "#e2e8f0", "font-size": "1.1rem"}, 
                "nav-link": {
                    "font-size": "1rem", 
                    "text-align": "left", 
                    "margin": "4px 0px", 
                    "color": "#e2e8f0",
                    "background-color": "transparent !important",
                    "transition": "all 0.3s ease",
                    "border-radius": "10px !important"
                },
                "nav-link-selected": {
                    "background-color": "rgba(102, 126, 234, 0.25) !important",
                    "color": "white !important"
                },
            }
        )

        st.markdown("---")

        # 显示系统状态
        st.markdown("### 系统状态")

        if os.getenv("DEEPSEEK_API_KEY"):
            st.success("◈ 接口密钥已配置")
        else:
            st.error("◇ 接口密钥未配置")

        if st.session_state.agents_loaded:
            st.success("✓ 代理已加载")

            if st.session_state.indexer:
                try:
                    stats = st.session_state.indexer.get_stats()
                    st.info(f"◈ 知识图谱: {stats.get('lightrag', {}).get('element_count', 0)} 实体")
                    st.info(f"◈ 对话记忆: {stats.get('chromadb', {}).get('document_count', 0)} 文档")
                except:
                    pass
        else:
            st.warning("⚠ 代理未加载")

        if st.session_state.logged_in:
            if st.button("退出登录", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.user_id = None
                st.session_state.agents_loaded = False
                st.rerun()

        return selected


def home_page():
    """首页"""
    st.markdown('<p class="main-header">◇ 我即是我 - 个人智能系统</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">让 AI 学习并模拟你的思维模式</p>', unsafe_allow_html=True)

    # 核心理念
    st.markdown("### ◈ 核心理念")
    st.info("""
    **人的思想是动态的，会随时间变化。**
    本系统不只记录"你是谁"，更追踪"你如何变化"。
    """)

    # 功能介绍
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ◈ 学习模式")
        st.markdown("""
        - 基于学术框架（大五人格、施瓦茨价值观）提问
        - 通过具体情境了解你的思维
        - 自动提取并存储人格特征
        - 追踪你的思想演变
        """)

        st.markdown("#### ◈ 日记模式")
        st.markdown("""
        - AI 辅助写作（续写、润色、启发）
        - 自动分析情绪、主题和成长轨迹
        - 提取新的人格特征
        - 生成周期性洞察报告
        """)

        st.markdown("#### ◈ 模拟模式")
        st.markdown("""
        - 以你的思维模式回答问题
        - 考虑你的性格、价值观、语言风格
        - 反映你的最新思想状态
        - 测试 AI 对你的理解程度
        """)

    with col2:
        st.markdown("#### ◈ 故事模式")
        st.markdown("""
        - 沉浸式故事角色扮演
        - 每次全新生成的原创剧情
        - 你的选择真正影响剧情走向
        - 通过行为自然分析性格
        """)

        st.markdown("#### ◈ 记忆系统")
        st.markdown("""
        - **长期记忆**: 性格、价值观、思维模式
        - **短期记忆**: 最近的对话和想法
        - **关系网络**: 重要人物及其影响
        - **时间轴**: 思想演变的历史快照
        """)

        st.markdown("#### ◈ 混合检索")
        st.markdown("""
        - **轻量级图谱**: 知识图谱，理解概念关系
        - **向量存储**: 向量检索，找到相似对话
        - **智能流**: 自适应工作流，智能路由
        """)

    # 学术框架
    st.markdown("---")
    st.markdown("### ◈ 学术框架")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**个体心理学**")
        st.markdown("""
        - 大五人格问卷
        - 施瓦茨价值观调查
        - 道德基础理论
        - 政治罗盘
        """)

    with col2:
        st.markdown("**社会心理学**")
        st.markdown("""
        - 布朗芬布伦纳生态系统
        - 社会认同理论
        - 社会网络分析
        - 社会资本理论
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
    st.markdown("### ◈ 快速开始")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("开始学习", use_container_width=True, type="primary"):
            st.session_state.selected_page = "学习模式"
            st.rerun()

    with col2:
        if st.button("写日记", use_container_width=True, type="primary"):
            st.session_state.selected_page = "日记模式"
            st.rerun()

    with col3:
        if st.button("故事冒险", use_container_width=True, type="primary"):
            st.session_state.selected_page = "故事模式"
            st.rerun()

    with col4:
        if st.button("测试模拟", use_container_width=True):
            st.session_state.selected_page = "模拟模式"
            st.rerun()

    with col5:
        if st.button("浏览记忆", use_container_width=True):
            st.session_state.selected_page = "记忆浏览"
            st.rerun()

    # 统计信息
    if st.session_state.agents_loaded:
        st.markdown("---")
        st.markdown("### ◈ 学习进度")

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
                    st.markdown('<div class="stats-label">记忆文档</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"无法加载统计信息: {e}")


def login_page():
    """登录/注册页面"""
    st.markdown('<p class="main-header">◇ 我即是我</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">请登录以开始记录你的思想演变</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submit = st.form_submit_button("登录", use_container_width=True)

            if submit:
                from accounts.services import login_user
                user, message = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.user_id = f"user_{user.id}"
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("新用户名")
            new_password = st.text_input("新密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            register_submit = st.form_submit_button("注册", use_container_width=True)

            if register_submit:
                if new_password != confirm_password:
                    st.error("两次密码输入不一致")
                else:
                    from accounts.services import register_user
                    success, message = register_user(new_username, new_password)
                    if success:
                        st.success(message + "，请切换到登录标签进行登录")
                    else:
                        st.error(message)


def main():
    """主函数"""
    # 初始化
    init_session_state()

    # 如果未登录，显示登录页面
    if not st.session_state.logged_in:
        login_page()
        return

    # 加载代理
    if not load_agents():
        st.error("⚠️ 系统初始化失败，请检查配置")
        st.stop()

    # 侧边栏菜单
    selected = sidebar_menu()

    # 检查是否有快速开始按钮设置的页面跳转
    if st.session_state.get("selected_page"):
        selected = st.session_state.selected_page
        # 清除跳转标记，避免每次 rerun 都跳转
        st.session_state.selected_page = None

    # 路由到对应页面
    if selected == "首页":
        home_page()
    elif selected == "个人档案":
        from pages import user_profile
        user_profile.render()
    elif selected == "学习模式":
        from pages import learning_mode
        learning_mode.render()
    elif selected == "日记模式":
        from pages import diary_mode
        diary_mode.render()
    elif selected == "故事模式":
        from pages import story_mode
        story_mode.render()
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
    elif selected == "统计":
        from pages import usage_dashboard
        usage_dashboard.render()


if __name__ == "__main__":
    main()
