"""
学习模式页面

功能：
1. 生成基于学术框架的问题
2. 记录用户回答
3. 分析并提取特征
4. 更新记忆文件
"""

import asyncio
import streamlit as st
from datetime import datetime


def render():
    """渲染学习模式页面"""
    st.markdown("# 📚 学习模式")
    st.markdown("通过对话了解你的思维模式、价值观和性格特征")
    st.markdown("---")

    # 检查代理
    if not st.session_state.agents_loaded:
        st.error("代理未加载")
        return

    agent = st.session_state.learning_agent

    # 显示学习进度
    with st.expander("📊 学习进度", expanded=False):
        try:
            stats = asyncio.run(agent.get_learning_stats())

            col1, col2 = st.columns(2)

            with col1:
                st.metric("已回答问题", stats.get("total_questions", 0))
                st.metric("完成度", f"{stats.get('completion_rate', 0):.1f}%")

            with col2:
                # 显示类别分布
                st.markdown("**类别分布**")
                breakdown = stats.get("category_breakdown", {})
                for category, data in breakdown.items():
                    st.write(f"- {category}: {data.get('count', 0)} 个问题")

        except Exception as e:
            st.warning(f"无法加载统计信息: {e}")

    st.markdown("---")

    # 主要内容区域
    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("### ⚙️ 设置")

        # 选择问题类别
        category_options = {
            "自动选择": None,
            "性格特征": "personality",
            "价值观": "values",
            "思维模式": "thinking_patterns",
            "道德基础": "moral_foundations",
            "人际关系": "relationships",
            "环境系统": "environment",
            "语言风格": "language_style"
        }

        selected_category = st.selectbox(
            "问题类别",
            options=list(category_options.keys()),
            help="选择要探索的维度，或让系统自动选择"
        )

        category = category_options[selected_category]

        # 添加上下文
        additional_context = st.text_area(
            "额外上下文（可选）",
            placeholder="例如：关注用户对技术的态度...",
            help="提供额外信息来指导问题生成"
        )

        # 生成问题按钮
        if st.button("🎲 生成新问题", type="primary", use_container_width=True):
            with st.spinner("正在生成问题..."):
                try:
                    question = asyncio.run(agent.generate_question(
                        category=category,
                        context=additional_context if additional_context else None
                    ))
                    st.session_state.current_question = question
                    st.success("问题已生成！")
                except Exception as e:
                    st.error(f"生成问题失败: {e}")

    with col1:
        st.markdown("### 💬 对话区域")

        # 显示当前问题
        if st.session_state.current_question:
            question = st.session_state.current_question

            st.markdown('<div class="question-card">', unsafe_allow_html=True)
            st.markdown(f"**问题** (类别: {question.get('category', 'unknown')})")
            st.markdown(f"### {question.get('question', '')}")

            if question.get("reasoning"):
                with st.expander("为什么问这个问题？"):
                    st.markdown(question.get("reasoning"))

            if question.get("follow_up_hints"):
                with st.expander("可能的追问方向"):
                    for hint in question.get("follow_up_hints", []):
                        st.markdown(f"- {hint}")

            st.markdown('</div>', unsafe_allow_html=True)

            # 回答区域
            st.markdown("---")
            st.markdown("**你的回答**")

            answer_text = st.text_area(
                "请尽可能详细地回答",
                height=200,
                placeholder="分享你的真实想法和经历...",
                key="answer_input"
            )

            col_a, col_b = st.columns([1, 1])

            with col_a:
                if st.button("📝 提交回答", type="primary", use_container_width=True, disabled=not answer_text):
                    if answer_text:
                        with st.spinner("正在分析你的回答..."):
                            try:
                                # 分析回答
                                analysis = asyncio.run(agent.analyze_answer(
                                    question=question,
                                    answer=answer_text
                                ))

                                # 显示分析结果
                                st.markdown("---")
                                st.markdown("### 📊 分析结果")

                                # 提取的特征
                                features = analysis.get("features", [])
                                if features:
                                    st.markdown("**提取的特征：**")
                                    for feature in features:
                                        confidence = "⭐" * feature.get("confidence", 0)
                                        st.markdown(f"- **{feature.get('trait')}**: {feature.get('value')}")
                                        st.markdown(f"  - 证据: {feature.get('evidence')}")
                                        st.markdown(f"  - 置信度: {confidence}")
                                else:
                                    st.warning("未能提取到明确特征")

                                # 是否需要追问
                                if analysis.get("follow_up_needed"):
                                    st.info(f"💡 建议追问: {analysis.get('suggested_follow_up')}")

                                # 更新记忆
                                with st.spinner("正在更新记忆..."):
                                    update_result = asyncio.run(agent.update_memory(
                                        analysis=analysis,
                                        answer=answer_text
                                    ))

                                    st.success("✓ 记忆已更新")

                                    with st.expander("查看更新详情"):
                                        st.json(update_result)

                                # 保存到历史
                                st.session_state.learning_history.append({
                                    "question": question,
                                    "answer": answer_text,
                                    "analysis": analysis,
                                    "timestamp": datetime.now().isoformat()
                                })

                                # 清除当前问题
                                st.session_state.current_question = None
                                st.rerun()

                            except Exception as e:
                                st.error(f"处理回答失败: {e}")

            with col_b:
                if st.button("⏭️ 跳过这个问题", use_container_width=True):
                    st.session_state.current_question = None
                    st.rerun()

        else:
            st.info("👈 点击左侧「生成新问题」开始学习")

    # 显示历史记录
    if st.session_state.learning_history:
        st.markdown("---")
        st.markdown("### 📜 本次会话历史")

        with st.expander(f"查看历史记录 ({len(st.session_state.learning_history)} 条)", expanded=False):
            for idx, item in enumerate(reversed(st.session_state.learning_history), 1):
                st.markdown(f"#### {idx}. {item['question'].get('category', 'unknown')}")
                st.markdown(f"**Q**: {item['question'].get('question', '')}")
                st.markdown(f"**A**: {item['answer'][:200]}...")

                features_count = len(item.get('analysis', {}).get('features', []))
                st.markdown(f"提取特征数: {features_count}")
                st.markdown("---")
