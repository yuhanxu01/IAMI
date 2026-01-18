"""
索引管理页面

功能：
1. 查看索引统计
2. 重建索引
3. 测试查询
4. 管理向量库
"""

import asyncio
import streamlit as st


def render():
    """渲染索引管理页面"""
    st.markdown("# ◇ 索引管理")
    st.markdown("管理 RAG 检索系统")
    st.markdown("---")

    if not st.session_state.agents_loaded or not st.session_state.indexer:
        st.error("索引器未加载")
        return

    indexer = st.session_state.indexer

    # 选择功能
    tab1, tab2, tab3 = st.tabs(["◈ 统计信息", "◈ 索引管理", "◈ 查询测试"])

    with tab1:
        show_index_stats(indexer)

    with tab2:
        manage_index(indexer)

    with tab3:
        test_query(indexer)


def show_index_stats(indexer):
    """显示索引统计信息"""
    st.markdown("### ◈ 索引统计概览")

    try:
        stats = indexer.get_stats()
        
        # 顶部总览卡片
        lightrag_stats = stats.get("lightrag", {})
        chroma_stats = stats.get("chromadb", {})
        
        # 使用自定义 CSS 卡片展示核心数据
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            file_count = len(lightrag_stats.get("files", []))
            st.markdown(f'''
                <div class="stats-card">
                    <div class="stats-number">{file_count}</div>
                    <div class="stats-label">源文件数量</div>
                </div>
            ''', unsafe_allow_html=True)
            
        with col2:
            doc_count = chroma_stats.get("document_count", 0)
            st.markdown(f'''
                <div class="stats-card">
                    <div class="stats-number">{doc_count}</div>
                    <div class="stats-label">向量文档数</div>
                </div>
            ''', unsafe_allow_html=True)

        with col3:
            # 模拟一个实体数量统计 (如果 graph 存在)
            element_count = lightrag_stats.get("element_count", "N/A")
            st.markdown(f'''
                <div class="stats-card">
                    <div class="stats-number">{element_count}</div>
                    <div class="stats-label">图谱实体数</div>
                </div>
            ''', unsafe_allow_html=True)
            
        with col4:
            st.markdown(f'''
                <div class="stats-card">
                    <div class="stats-number">已连接</div>
                    <div class="stats-label">系统状态</div>
                </div>
            ''', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 详细信息分栏
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.markdown("""
                <div style='background: rgba(102, 126, 234, 0.1); padding: 20px; border-radius: 15px; border-left: 5px solid #667eea;'>
                    <h4 style='margin-top:0'>◈ LightRAG 知识图谱详情</h4>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("##### 存储路径")
            st.code(lightrag_stats.get("working_dir", "N/A"), language="bash")
            
            if lightrag_stats.get("files"):
                with st.expander("📁 查看源文件列表", expanded=False):
                    for f in lightrag_stats["files"]:
                        st.text(f"• {f}")
                        
        with detail_col2:
            st.markdown("""
                <div style='background: rgba(121, 85, 72, 0.1); padding: 20px; border-radius: 15px; border-left: 5px solid #795548;'>
                    <h4 style='margin-top:0'>◈ ChromaDB 向量库详情</h4>
                </div>
            """, unsafe_allow_html=True)
            
            st.info(f"**集合名称**: `{chroma_stats.get('collection_name', 'N/A')}`")
            
            st.markdown("##### 持久化目录")
            st.code(chroma_stats.get("persist_directory", "N/A"), language="bash")

    except Exception as e:
        st.error(f"获取统计信息失败: {e}")


def manage_index(indexer):
    """管理索引"""
    st.markdown("### ◇ 索引管理")

    # 重建索引
    st.markdown("#### 重建索引")
    st.warning("重建索引将重新处理所有记忆文件，这可能需要一些时间。")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("重建知识图谱索引", type="primary", use_container_width=True):
            with st.spinner("正在重建 LightRAG 索引..."):
                try:
                    from graphrag.indexer.data_loader import IAMIDataLoader

                    loader = IAMIDataLoader()
                    documents = loader.load_all_data()

                    st.info(f"找到 {len(documents)} 个文档")

                    # 使用 LightRAG 索引器
                    results = asyncio.run(
                        st.session_state.indexer.lightrag_indexer.index_documents(documents)
                    )

                    st.success("◈ 知识图谱索引重建完成")
                    st.json(results)

                except Exception as e:
                    st.error(f"重建失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    with col2:
        if st.button("重建对话记忆索引", use_container_width=True):
            with st.spinner("正在重建 ChromaDB 索引..."):
                try:
                    # 清空现有集合
                    await_result = asyncio.run(
                        st.session_state.indexer.chroma_indexer.reset_collection()
                    )

                    if await_result:
                        st.success("◈ 对话记忆集合已重置")
                    else:
                        st.error("◇ 重置失败")

                except Exception as e:
                    st.error(f"重置失败: {e}")

    # 索引单个文档
    st.markdown("---")
    st.markdown("#### 索引单个文档")

    doc_type = st.selectbox(
        "文档类型",
        options=[
            "conversation",
            "personality",
            "values",
            "thinking_patterns",
            "language_style",
            "knowledge",
            "relationship"
        ]
    )

    doc_content = st.text_area("文档内容", height=150)

    if st.button("提交文档", use_container_width=True, disabled=not doc_content):
        if doc_content:
            with st.spinner("正在索引..."):
                try:
                    from datetime import datetime

                    doc = {
                        "id": f"{doc_type}_{datetime.now().timestamp()}",
                        "type": doc_type,
                        "content": doc_content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {}
                    }

                    result = asyncio.run(indexer.index_document(doc))

                    st.success("◈ 文档已提交")
                    st.json(result)

                except Exception as e:
                    st.error(f"索引失败: {e}")


def test_query(indexer):
    """测试查询"""
    st.markdown("### ◇ 查询测试")

    # 查询输入
    query = st.text_input("输入查询", placeholder="例如：您的性格特征是什么？")

    col1, col2 = st.columns(2)

    with col1:
        use_lightrag = st.checkbox("使用 LightRAG", value=True)
        if use_lightrag:
            lightrag_mode = st.selectbox(
                "LightRAG 模式",
                options=["naive", "local", "global", "hybrid"],
                index=3
            )

    with col2:
        use_chromadb = st.checkbox("使用 ChromaDB", value=True)
        if use_chromadb:
            chromadb_k = st.slider("检索数量", 1, 20, 5)

    if st.button("执行查询", type="primary", disabled=not query):
        if query:
            with st.spinner("正在查询..."):
                try:
                    result = asyncio.run(indexer.query(
                        query=query,
                        use_lightrag=use_lightrag,
                        use_chromadb=use_chromadb,
                        lightrag_mode=lightrag_mode if use_lightrag else "hybrid",
                        chromadb_k=chromadb_k if use_chromadb else 5
                    ))

                    # 显示结果
                    if use_lightrag and result.get("lightrag_result"):
                        st.markdown("#### LightRAG 结果")
                        lightrag_res = result["lightrag_result"]

                        if lightrag_res.get("success"):
                            st.success("◈ 知识图谱查询成功")
                            st.markdown(lightrag_res.get("result", ""))
                        else:
                            st.error("◇ 知识图谱查询失败")

                    if use_chromadb and result.get("chromadb_results"):
                        st.markdown("---")
                        st.markdown("#### 对话记忆结果")
                        chromadb_res = result["chromadb_results"]

                        st.success(f"◈ 找到 {len(chromadb_res)} 个相关文档")

                        for idx, doc in enumerate(chromadb_res, 1):
                            with st.expander(f"文档 {idx} (相似度: {doc.get('similarity_score', 0):.4f})"):
                                st.markdown(doc.get("content", ""))
                                st.json(doc.get("metadata", {}))

                except Exception as e:
                    st.error(f"查询失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
