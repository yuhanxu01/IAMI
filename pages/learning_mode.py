"""
学习模式页面 (Async Version)

功能：
1. 异步生成问题（预加载）
2. 后台分析回答（非阻塞）
3. 流畅的用户体验
"""

import asyncio
import streamlit as st
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List

# --- Helper Functions for Background Tasks ---

def run_background_analysis(agent, question: Dict[str, Any], answer: str):
    """
    后台运行分析和更新任务
    """
    try:
        # Create a new event loop for this thread if needed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 1. Analyze
        analysis = loop.run_until_complete(agent.analyze_answer(question, answer))
        
        # 2. Update Memory
        loop.run_until_complete(agent.update_memory(analysis, answer))
        
        loop.close()
        return analysis
    except Exception as e:
        print(f"Background analysis failed: {e}")
        return None

def run_background_generation(agent, category: Optional[str], context: Optional[str], question_type: str, excluded_questions: List[str]):
    """
    后台生成下一个问题
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        question = loop.run_until_complete(agent.generate_question(
            category=category,
            context=context,
            question_type=question_type,
            excluded_questions=excluded_questions
        ))
        
        loop.close()
        return question
    except Exception as e:
        print(f"Background generation failed: {e}")
        return None

@st.cache_resource
def get_executor():
    """全局线程池"""
    return ThreadPoolExecutor(max_workers=2)

def render():
    """渲染学习模式页面"""
    st.markdown("# ◇ 学习模式")
    st.markdown("通过对话了解您的思维模式、价值观和性格特征")
    st.markdown("---")

    # 检查代理
    if not st.session_state.agents_loaded:
        st.error("代理未加载")
        return

    agent = st.session_state.learning_agent
    executor = get_executor()

    # --- State Management ---
    
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
        
    if "next_question_future" not in st.session_state:
        st.session_state.next_question_future = None
        
    if "analysis_futures" not in st.session_state:
        st.session_state.analysis_futures = []
        
    if "question_type_choice" not in st.session_state:
        st.session_state.question_type_choice = "open"

    if "feedback_message" not in st.session_state:
        st.session_state.feedback_message = None

    # --- UI Components ---

    # 显示学习进度
    with st.expander("◈ 学习进度", expanded=False):
        try:
            stats = asyncio.run(agent.get_learning_stats())
            col1, col2 = st.columns(2)
            with col1:
                st.metric("已回答问题", stats.get("total_questions", 0))
                st.metric("完成度", f"{stats.get('completion_rate', 0):.1f}%")
            with col2:
                breakdown = stats.get("category_breakdown", {})
                st.markdown("**类别分布**")
                for cat, data in breakdown.items():
                    st.write(f"- {cat}: {data.get('count', 0)}")
        except Exception:
             st.write("加载中...")

    # 反馈消息 (Toast-like)
    if st.session_state.feedback_message:
        st.success(st.session_state.feedback_message)
        st.session_state.feedback_message = None # Show once

    st.markdown("---")

    # 自定义 CSS 用于本页
    st.markdown("""
<style>
    @media (max-width: 768px) {
        .question-card {
            padding: 1.2rem !important;
            margin: 1rem 0 !important;
        }
        .question-card h3 {
            font-size: 1.2rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    # 在手机端，我们可能希望设置在下面或者在折叠面板里
    with col2:
        with st.expander("⚙️ 设置", expanded=st.session_state.get("mobile_settings_expanded", False)):
            st.markdown("### ◇ 问题设置")
            
            # 类别选择
            category_options = {
                "自动选择": None,
                "性格特征": "personality",
                "价值观": "values",
                "思维模式": "thinking_patterns",
                "道德基础": "moral_foundations",
                "人际关系": "relationships",
                "环境系统": "environment",
                "语言风格": "language_style",
                "社会热点": "social_hotspots"
            }
            selected_cat_name = st.selectbox("问题类别", list(category_options.keys()))
            selected_category = category_options[selected_cat_name]

            # 问题类型选择
            st.markdown("### 问题类型")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("问答题", type="primary" if st.session_state.question_type_choice == "open" else "secondary", use_container_width=True):
                    st.session_state.question_type_choice = "open"
                    
            with c2:
                if st.button("选择题", type="primary" if st.session_state.question_type_choice == "mcq" else "secondary", use_container_width=True):
                    st.session_state.question_type_choice = "mcq"

            # 额外上下文
            context = st.text_area("额外上下文", placeholder="指导问题生成...", height=68)

            # 强制生成按钮
            if st.button("生成新问题", use_container_width=True):
                st.session_state.next_question_future = None # Cancel pending
                st.session_state.current_question = None     # Clear current
                st.rerun() # Will trigger generation below

    with col1:
        st.markdown("### ◇ 对话区域")

        # --- Logic Flow ---

        # 1. Check if we need to fetch a question
        if st.session_state.current_question is None:
            if st.session_state.next_question_future is None:
                # Start generating Q1
                with st.spinner("正在生成第一个问题..."):
                    # We run this synchronously for the VERY first question to avoid blank screen
                    q = asyncio.run(agent.generate_question(
                        category=selected_category,
                        context=context,
                        question_type=st.session_state.question_type_choice
                    ))
                    st.session_state.current_question = q
                    st.rerun()
            else:
                # We have a future, check if it's done
                if st.session_state.next_question_future.done():
                    st.session_state.current_question = st.session_state.next_question_future.result()
                    st.session_state.next_question_future = None # Consumed
                    st.rerun()
                else:
                    with st.spinner("正在准备下一个问题..."):
                        # Wait for it
                        st.session_state.current_question = st.session_state.next_question_future.result()
                        st.session_state.next_question_future = None
                        st.rerun()
        
        # 2. Display Question
        if st.session_state.current_question:
            q_data = st.session_state.current_question
            
            # --- Pre-fetch Trigger ---
            # If we have a current question, but no NEXT question is being generated, start generating it NOW.
            if st.session_state.next_question_future is None:
                # 排除当前问题以及本次会话中所有已回答/正在回答的问题，避免并发导致重复
                excluded = [q_data.get("question", "")]
                if "learning_history" in st.session_state:
                    for item in st.session_state.learning_history:
                        q_text = item.get("question", {}).get("question")
                        if q_text and q_text not in excluded:
                            excluded.append(q_text)
                            
                st.session_state.next_question_future = executor.submit(
                    run_background_generation,
                    agent, 
                    selected_category, # Use current settings for next Q
                    context,
                    st.session_state.question_type_choice,
                    excluded
                )
            
            # Render Card
            card_html = f"""
            <div class="question-card">
                <div style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 0.5rem;">
                    <strong>问题</strong> (类别: {q_data.get('category', 'unknown')})
                </div>
                <h3 style="margin: 0; line_height: 1.4;">{q_data.get('question', '')}</h3>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

            if q_data.get("reasoning"):
                with st.expander("AI 的思考"):
                    st.write(q_data.get("reasoning"))

            # Input Area
            is_mcq = q_data.get("type") == "mcq"
            final_answer = ""
            submit_ready = False

            if is_mcq:
                opts = q_data.get("options", [])
                sel = st.radio("选择回答:", opts, index=None, key=f"radio_{q_data.get('id')}")
                extra = st.text_area("补充说明 (可选):", key=f"text_{q_data.get('id')}")
                if sel:
                    final_answer = f"用户选择了：{sel}。补充说明：{extra}"
                    submit_ready = True
            else:
                final_answer = st.text_area("你的回答:", height=200, key=f"text_{q_data.get('id')}")
                submit_ready = bool(final_answer.strip())

            # Action Buttons
            c_sub, c_skip = st.columns([1, 1])
            
            with c_sub:
                if st.button("提交回答", type="primary", use_container_width=True, disabled=not submit_ready):
                    # 1. Add to history first to get index
                    history_item = {
                        "question": q_data,
                        "answer": final_answer,
                        "timestamp": datetime.now().isoformat(),
                        "status": "running",
                        "analysis": None
                    }
                    st.session_state.learning_history.append(history_item)
                    idx = len(st.session_state.learning_history) - 1
                    
                    # 2. Submit task with index reference
                    future = executor.submit(run_background_analysis, agent, q_data, final_answer)
                    st.session_state.analysis_futures.append((future, idx))
                    
                    # 3. Move to next question immediately
                    st.session_state.current_question = None 
                    st.session_state.feedback_message = "回答已提交，正在后台分析..."
                    st.rerun()

            with c_skip:
                if st.button("跳过", use_container_width=True):
                    st.session_state.current_question = None
                    st.rerun()

    # --- Analysis Status & History Update ---
    
    # Check for completed analyses
    # We use a list to store indices to remove
    indices_to_remove = []
    
    for i, (future, hist_idx) in enumerate(st.session_state.analysis_futures):
        if future.done():
            indices_to_remove.append(i)
            try:
                result = future.result()
                # Update the specific history item
                # Safety check: ensure index still valid (though list only appends)
                if 0 <= hist_idx < len(st.session_state.learning_history):
                    st.session_state.learning_history[hist_idx]["analysis"] = result
                    st.session_state.learning_history[hist_idx]["status"] = "completed"
                    
                    # Optional: Toast notification
                    # st.toast(f"问题 '{st.session_state.learning_history[hist_idx]['question']['question'][:10]}...' 分析完成")
            except Exception as e:
                print(f"Error retrieving analysis result: {e}")

    # Remove processed futures (reverse order)
    for i in reversed(indices_to_remove):
        st.session_state.analysis_futures.pop(i)

    # --- Global History Display ---
    st.markdown("---")
    with st.expander("⌛ 历史记录 (查看所有已回复问题)", expanded=False):
        try:
            full_history = asyncio.run(agent.get_full_history())
            if not full_history:
                st.info("暂无历史记录")
            else:
                # 按时间倒序
                for item in reversed(full_history):
                    # 兼容性处理：尝试新字段名，回退到旧字段名
                    q_text = item.get("question_text") or item.get("question", "未知问题")
                    ans_text = item.get("answer", "未记录回答")
                    timestamp = item.get("timestamp", "")[:16].replace("T", " ")
                    cat = item.get("category", "unknown")
                    
                    with st.expander(f"📅 {timestamp} | {q_text[:30]}...", expanded=False):
                        st.markdown(f"**问题**: {q_text}")
                        st.markdown(f"**类别**: {cat}")
                        st.markdown(f"**回答**: {ans_text}")
                        
                        # 优先展示详细分析结果，如果没有则尝试展示 summary
                        analysis_results = item.get('analysis_results', [])
                        if analysis_results:
                            st.markdown("#### 分析结果")
                            for f in analysis_results:
                                st.write(f"- **{f.get('trait')}**: {f.get('value')} (置信度: {f.get('confidence')}/5)")
                        elif item.get('analysis_summary'):
                            summary = item['analysis_summary']
                            st.markdown("#### 分析摘要")
                            st.write(f"- 特征数量: {summary.get('features_count', 0)}")
                            st.write(f"- 平均置信度: {summary.get('confidence_avg', 0):.1f}/5")
                        else:
                            st.info("该条记录暂无详细分析结果")
                        
                        # 删除按钮
                        if st.button("🗑️ 删除该条记录", key=f"del_{item.get('timestamp')}", use_container_width=True):
                            if asyncio.run(agent.delete_history_item(item.get('timestamp'))):
                                st.toast("记录已成功删除")
                                st.rerun()
                            else:
                                st.error("删除记录失败")
        except Exception as e:
            st.error(f"加载历史记录失败: {e}")

    # --- History Display (Current Session) ---
    if st.session_state.learning_history:
        st.markdown("---")
        st.markdown("### ◇ 本次会话历史")
        
        # Reverse to show newest first
        for item in reversed(st.session_state.learning_history):
            q_text = item['question'].get('question', '')
            status = item.get('status', 'completed')
            
            with st.expander(f"{'🔄' if status == 'running' else '✅'} {q_text}", expanded=False):
                st.write(f"**您的回答**: {item.get('answer')}")
                
                if status == 'running':
                    st.info("正在后台分析中...")
                elif item.get('analysis'):
                    analysis = item['analysis']
                    st.markdown("#### 分析结果")
                    features = analysis.get("features", [])
                    if features:
                        for f in features:
                            st.write(f"- **{f.get('trait')}**: {f.get('value')} (置信度: {f.get('confidence')}/5)")
                    else:
                        st.write("未提取到显著特征")
                else:
                    st.warning("分析未能完成")

