"""
可视化页面

功能：
1. 知识图谱可视化
2. 性格特征雷达图
3. 价值观分布
4. 时间演变趋势
"""

import asyncio
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json


def render():
    """渲染可视化页面"""
    st.markdown("# ◇ 可视化")
    st.markdown("图形化展示您的记忆和思想演变")
    st.markdown("---")

    # 选择可视化类型
    viz_type = st.selectbox(
        "选择可视化类型",
        options=[
            "人物画像概览",
            "性格特征雷达图",
            "价值观分布",
            "学习进度",
            "时间演变趋势"
        ]
    )

    if viz_type == "人物画像概览":
        show_profile_overview()
    elif viz_type == "性格特征雷达图":
        show_personality_radar()
    elif viz_type == "价值观分布":
        show_values_distribution()
    elif viz_type == "学习进度":
        show_learning_progress()
    elif viz_type == "时间演变趋势":
        show_evolution_timeline()


def show_profile_overview():
    """显示人物画像概览"""
    st.markdown("### ◈ 人物画像概览")

    # 读取 profile.json
    profile_path = Path("analysis/profile.json")

    if not profile_path.exists():
        st.info("暂无人物画像数据")

        if st.button("生成人物画像"):
            if st.session_state.agents_loaded:
                with st.spinner("正在分析记忆并生成画像..."):
                    try:
                        agent = st.session_state.analysis_agent
                        profile = asyncio.run(agent.generate_profile())

                        st.success("◈ 画像生成成功")
                        st.json(profile)
                    except Exception as e:
                        st.error(f"生成失败: {e}")
            else:
                st.error("代理未加载")
        return

    with open(profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)

    # 显示画像
    col1, col2 = st.columns(2)

    with col1:
        if "core_personality" in profile:
            st.markdown("#### 核心性格特征")
            st.json(profile["core_personality"])

        if "main_values" in profile:
            st.markdown("#### 主要价值观")
            st.json(profile["main_values"])

    with col2:
        if "thinking_patterns" in profile:
            st.markdown("#### 思维模式")
            st.json(profile["thinking_patterns"])

        if "overall_evaluation" in profile:
            st.markdown("#### 整体评价")
            st.info(profile["overall_evaluation"])


def show_personality_radar():
    """显示性格特征雷达图"""
    st.markdown("### ◈ 性格特征雷达图")

    # 读取性格数据
    personality_path = Path("memory/long_term/personality.json")

    if not personality_path.exists():
        st.info("暂无性格数据")
        return

    with open(personality_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    history = data.get("history", [])

    if not history:
        st.info("暂无历史记录")
        return

    # Big Five 维度
    big_five_traits = {
        "Openness": "开放性",
        "Conscientiousness": "尽责性",
        "Extraversion": "外向性",
        "Agreeableness": "宜人性",
        "Neuroticism": "神经质"
    }

    # 聚合数据
    trait_scores = {}
    for item in history:
        trait = item.get("trait", "")
        confidence = item.get("confidence", 0)

        # 简单映射（实际应该更复杂）
        for en_trait, zh_trait in big_five_traits.items():
            if en_trait.lower() in trait.lower() or zh_trait in trait:
                if en_trait not in trait_scores:
                    trait_scores[en_trait] = []
                trait_scores[en_trait].append(confidence)

    # 计算平均分
    avg_scores = {}
    for trait, scores in trait_scores.items():
        avg_scores[trait] = sum(scores) / len(scores) if scores else 0

    # 确保所有维度都有值
    for trait in big_five_traits.keys():
        if trait not in avg_scores:
            avg_scores[trait] = 0

    # 绘制雷达图
    categories = [big_five_traits[t] for t in big_five_traits.keys()]
    values = [avg_scores.get(t, 0) for t in big_five_traits.keys()]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='性格特征'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5]
            )),
        showlegend=False,
        title="Big Five 性格特征"
    )

    st.plotly_chart(fig, use_container_width=True)


def show_values_distribution():
    """显示价值观分布"""
    st.markdown("### ◈ 价值观分布")

    values_path = Path("memory/long_term/values.json")

    if not values_path.exists():
        st.info("暂无价值观数据")
        return

    with open(values_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    history = data.get("history", [])

    if not history:
        st.info("暂无历史记录")
        return

    # 统计价值观类型
    value_counts = {}
    for item in history:
        value_type = item.get("value_type", "unknown")
        value_counts[value_type] = value_counts.get(value_type, 0) + 1

    # 绘制条形图
    fig = px.bar(
        x=list(value_counts.keys()),
        y=list(value_counts.values()),
        labels={"x": "价值观类型", "y": "提及次数"},
        title="价值观分布"
    )

    st.plotly_chart(fig, use_container_width=True)


def show_learning_progress():
    """显示学习进度"""
    st.markdown("### ◈ 学习进度")

    if not st.session_state.agents_loaded:
        st.error("代理未加载")
        return

    try:
        agent = st.session_state.learning_agent
        stats = asyncio.run(agent.get_learning_stats())

        # 进度条
        completion = stats.get("completion_rate", 0)
        st.metric("完成度", f"{completion:.1f}%")
        st.progress(completion / 100)

        # 类别分布
        breakdown = stats.get("category_breakdown", {})

        if breakdown:
            categories = list(breakdown.keys())
            counts = [data.get("count", 0) for data in breakdown.values()]

            fig = px.bar(
                x=categories,
                y=counts,
                labels={"x": "类别", "y": "问题数量"},
                title="各类别问题分布"
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"加载失败: {e}")


def show_evolution_timeline():
    """显示时间演变趋势"""
    st.markdown("### ◈ 时间演变趋势")

    timeline_path = Path("memory/timeline/snapshots.json")

    if not timeline_path.exists():
        st.info("暂无时间轴数据")
        return

    with open(timeline_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    snapshots = data.get("snapshots", [])

    if not snapshots:
        st.info("暂无快照")
        return

    # 简单展示快照时间线
    timestamps = [s.get("timestamp", "") for s in snapshots]
    st.markdown(f"共有 {len(snapshots)} 个时间快照")

    for idx, snapshot in enumerate(sorted(snapshots, key=lambda x: x.get("timestamp", "")), 1):
        st.markdown(f"**{idx}. {snapshot.get('timestamp', '')[:10]}**")
        with st.expander("查看详情"):
            st.json(snapshot)
