"""
模拟模式页面

功能：
1. 以用户思维模式回答问题
2. 显示使用的记忆上下文
3. 测试 AI 对用户的理解程度
"""

import asyncio
import streamlit as st
from datetime import datetime


def render():
    """渲染模拟模式页面"""
    st.markdown("# ◇ 模拟模式")
    st.markdown("AI 将以**您的思维模式**回答问题")
    st.markdown("---")

    # 检查代理
    if not st.session_state.agents_loaded:
        st.error("代理未加载")
        return

    agent = st.session_state.simulation_agent

    # 设置区域
    with st.sidebar:
        st.markdown("### ◇ 模拟设置")

        use_latest_only = st.checkbox(
            "只使用最新记忆",
            value=True,
            help="考虑思想演变，只使用最近的记忆快照"
        )

        st.markdown("---")
        st.markdown("### ◈ 使用提示")
        st.info("""
        - 问一些您可能被问到的问题
        - 测试 AI 是否理解您的立场
        - 看看 AI 能否用您的方式思考
        """)

    # 聊天区域
    st.markdown("### ◇ 对话")

    # 初始化聊天历史
    if "simulation_messages" not in st.session_state:
        st.session_state.simulation_messages = []

    # 显示聊天历史
    for message in st.session_state.simulation_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # 显示元数据
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("查看生成详情"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("使用的记忆", message["metadata"].get("memories_used", 0))
                    with col2:
                        st.metric("检索上下文", f"{message['metadata'].get('retrieval_context_length', 0)} 字符")

                    if "profile_summary" in message["metadata"]:
                        st.markdown("**人物画像摘要**")
                        st.markdown(message["metadata"]["profile_summary"])

    # 输入区域
    if prompt := st.chat_input("问我任何问题..."):
        # 添加用户消息
        st.session_state.simulation_messages.append({
            "role": "user",
            "content": prompt
        })

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成模拟回答
        with st.chat_message("assistant"):
            with st.spinner("正在以你的思维思考..."):
                try:
                    result = asyncio.run(agent.simulate_response(
                        query=prompt,
                        use_latest_only=use_latest_only
                    ))

                    response_text = result.get("simulated_response", "")

                    # 显示回答
                    st.markdown(response_text)

                    # 保存助手消息
                    st.session_state.simulation_messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "metadata": result
                    })

                    # 显示详情
                    with st.expander("查看生成详情"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("使用的记忆", result.get("memories_used", 0))
                        with col2:
                            st.metric("检索上下文", f"{result.get('retrieval_context_length', 0)} 字符")

                        if result.get("profile_summary"):
                            st.markdown("**人物画像摘要**")
                            st.markdown(result["profile_summary"])

                except Exception as e:
                    st.error(f"生成回答失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    # 控制按钮
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("清除对话", use_container_width=True):
            st.session_state.simulation_messages = []
            st.rerun()

    with col2:
        if st.button("导出对话", use_container_width=True):
            if st.session_state.simulation_messages:
                # 转换为文本
                export_text = "# IAMI 模拟对话\n\n"
                export_text += f"导出时间: {datetime.now().isoformat()}\n\n"
                export_text += "---\n\n"

                for msg in st.session_state.simulation_messages:
                    role = "◇ 用户" if msg["role"] == "user" else "◈ AI (模拟您)"
                    export_text += f"## {role}\n\n{msg['content']}\n\n"

                st.download_button(
                    label="下载对话",
                    data=export_text,
                    file_name=f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
            else:
                st.warning("没有对话可导出")

    with col3:
        if st.button("生成评估", use_container_width=True):
            if st.session_state.simulation_messages:
                st.info("此功能将在未来版本中提供：对模拟质量进行评估")
            else:
                st.warning("需要先进行对话")

    # 测试建议
    st.markdown("---")
    st.markdown("### ◈ 测试建议")

    test_questions = [
        "你对人工智能的看法是什么？",
        "如果必须在创新和稳定之间选择，你会选哪个？",
        "你通常如何做重要决定？",
        "你最重视的品质是什么？",
        "你对工作和生活平衡有什么看法？"
    ]

    st.markdown("尝试问这些问题：")
    cols = st.columns(2)
    for idx, question in enumerate(test_questions):
        col = cols[idx % 2]
        with col:
            if st.button(f"{question}", key=f"test_q_{idx}"):
                st.session_state.test_question = question
                # 触发问题输入
                st.rerun()
