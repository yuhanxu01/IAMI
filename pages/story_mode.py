"""
故事模式页面

通过沉浸式的故事和角色扮演来分析用户的人格特征。
每次都是全新生成的故事，用户的选择会影响剧情走向。
"""

import asyncio
import streamlit as st
import json
import threading
import concurrent.futures
from datetime import datetime

# 后台线程池
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def _run_async_in_thread(coro):
    """在线程中运行异步协程"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def render():
    """渲染故事模式页面"""
    st.markdown("# ◇ 故事模式")
    st.markdown("在沉浸式的故事中展现真实的自我，通过选择揭示您的性格")
    st.markdown("---")

    # 检查代理
    if not st.session_state.agents_loaded:
        st.error("代理未加载")
        return

    # 初始化故事代理
    if "story_agent" not in st.session_state:
        from graphrag.agents import IAMIStoryAgent
        st.session_state.story_agent = IAMIStoryAgent(
            user_id=st.session_state.user_id, 
            indexer=st.session_state.indexer
        )

    agent = st.session_state.story_agent

    # 初始化状态
    if "current_story" not in st.session_state:
        st.session_state.current_story = None
    if "waiting_for_choice" not in st.session_state:
        st.session_state.waiting_for_choice = False
    if "current_scene_data" not in st.session_state:
        st.session_state.current_scene_data = None
    if "prefetched_scenes" not in st.session_state:
        st.session_state.prefetched_scenes = {}  # {choice_id: scene_data}
    if "prefetch_future" not in st.session_state:
        st.session_state.prefetch_future = None
    if "analysis_future" not in st.session_state:
        st.session_state.analysis_future = None

    # 侧边栏
    with st.sidebar:
        st.markdown("### ◇ 故事管理")

        # 如果没有进行中的故事
        if not st.session_state.current_story:
            st.info("◈ 在主界面选择或创建故事")
        else:
            # 显示当前故事信息
            story = st.session_state.current_story
            st.success(f"**{story.genre}** 故事进行中")

            st.metric("场景", f"{story.current_scene + 1}")
            st.metric("选择", len(story.choices_made))
            st.metric("紧张度", f"{story.world_state.get('tension_level', 5)}/10")

            st.markdown("---")

            # 操作按钮
            col1, col2 = st.columns(2)

            with col1:
                if st.button("保存", use_container_width=True):
                    success = asyncio.run(agent.save_story(story))
                    if success:
                        st.success("◈ 已保存")
                    else:
                        st.error("保存失败，请重试")

            with col2:
                if st.button("结束", use_container_width=True):
                    st.session_state.ending_story = True

    # 主内容区
    if not st.session_state.current_story:
        # 开始新故事
        show_story_start(agent)
    elif st.session_state.get("ending_story"):
        # 结束故事，显示分析
        show_story_ending(agent)
    else:
        # 进行中的故事
        show_ongoing_story(agent)


def show_story_start(agent):
    """显示故事开始界面"""
    st.markdown("## ◇ 开始新故事")
    
    # 显示已保存的故事（显眼位置）
    stories = asyncio.run(agent.list_stories())
    if stories:
        st.markdown("### 📚 继续你的故事")
        st.markdown("点击任意故事卡片继续你的冒险")
        
        # 使用列布局显示故事卡片
        cols_per_row = 3
        for i in range(0, len(stories), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, story in enumerate(stories[i:i+cols_per_row]):
                with cols[j]:
                    # 故事卡片
                    genre_emoji = {
                        "科幻": "🚀",
                        "奇幻": "🔮",
                        "悬疑": "🔍",
                        "现代": "🏙️",
                        "历史": "📜",
                        "生存": "⚔️",
                        "浪漫": "💕",
                        "惊悚": "👻",
                        "冒险": "🗺️"
                    }
                    emoji = genre_emoji.get(story['genre'], "📖")
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
                        border: 2px solid rgba(102, 126, 234, 0.3);
                        border-radius: 16px;
                        padding: 1.5rem;
                        margin-bottom: 1rem;
                        transition: all 0.3s ease;
                        cursor: pointer;
                        height: 100%;
                    ">
                        <div style="font-size: 2.5rem; text-align: center; margin-bottom: 0.5rem;">
                            {emoji}
                        </div>
                        <div style="font-size: 1.2rem; font-weight: 600; color: #a5b4fc; text-align: center; margin-bottom: 0.5rem;">
                            {story['genre']}
                        </div>
                        <div style="font-size: 0.9rem; color: #cbd5e1; text-align: center; margin-bottom: 1rem;">
                            {story['timestamp'][:10]}
                        </div>
                        <div style="display: flex; justify-content: space-around; margin-bottom: 1rem;">
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: #818cf8;">
                                    {story['scenes_count']}
                                </div>
                                <div style="font-size: 0.75rem; color: #94a3b8;">场景</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.5rem; font-weight: 700; color: #c084fc;">
                                    {story['choices_count']}
                                </div>
                                <div style="font-size: 0.75rem; color: #94a3b8;">选择</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"继续冒险", key=f"load_{story['story_id']}", use_container_width=True, type="primary"):
                        with st.spinner("正在加载故事..."):
                            state = asyncio.run(agent.load_story(story['story_id']))
                            if state:
                                st.session_state.current_story = state
                                st.rerun()
        
        st.markdown("---")

    st.info("""
    **故事模式说明**：
    - 每次都是全新生成的原创故事
    - 你的选择会真正影响剧情走向
    - 故事会通过你的选择来分析你的性格
    - 细致入微的场景描写，沉浸式体验
    """)

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### ◇ 选择故事类型")

        from graphrag.agents import StoryGenre

        genre_options = ["随机生成"] + StoryGenre.all_genres()

        selected_genre = st.selectbox(
            "故事类型",
            options=genre_options,
            help="选择你喜欢的故事类型，或让系统随机生成"
        )

        theme_input = st.text_input(
            "故事主题（可选）",
            placeholder="例如：友谊与背叛、生存与道德、权力与责任...",
            help="输入你想探索的主题"
        )

    with col2:
        st.markdown("### ◇ 类型说明")

        genre_descriptions = {
            "科幻": "太空、未来、科技",
            "奇幻": "魔法、异世界、冒险",
            "悬疑": "推理、解谜、真相",
            "现代": "都市、职场、生活",
            "历史": "古代、史实、文化",
            "生存": "末日、求生、困境",
            "浪漫": "情感、关系、成长",
            "惊悚": "恐怖、心理、悬念",
            "冒险": "探索、挑战、发现"
        }

        for genre, desc in genre_descriptions.items():
            st.markdown(f"**{genre}**: {desc}")

    st.markdown("---")
    
    st.markdown("### ◇ 探索公开故事")
    
    # 获取公开模版
    public_templates = asyncio.run(agent.get_public_templates())
    
    if public_templates:
        for t in public_templates:
            with st.expander(f"📖 {t['title']} ({t['genre']})"):
                st.write(t['description'])
                st.caption(f"作者: {t['author']} | 游玩次数: {t['play_count']}")
                if st.button("从此开始", key=f"tpl_{t['id']}"):
                    with st.spinner("正在进入故事世界..."):
                        try:
                            state = asyncio.run(agent.create_story_from_template(t['id']))
                            st.session_state.current_story = state
                            st.rerun()
                        except Exception as e:
                            st.error(f"加载故事失败: {e}")
    else:
        st.info("暂无公开故事模版")

    st.markdown("---")

    if st.button("开始故事", type="primary", use_container_width=True):
        with st.spinner("正在创造你的故事世界..."):
            try:
                # 生成故事设定
                genre = None if selected_genre == "随机生成" else selected_genre
                theme = theme_input if theme_input else None

                state = asyncio.run(agent.generate_story_setting(
                    genre=genre,
                    theme=theme
                ))

                st.session_state.current_story = state
                st.success("◈ 故事世界已创建")
                st.rerun()

            except Exception as e:
                st.error(f"创建故事失败: {e}")
                import traceback
                st.code(traceback.format_exc())



def show_ongoing_story(agent):
    """显示进行中的故事"""
    story = st.session_state.current_story

    # 显示故事标题
    if story.scenes:
        first_scene = story.scenes[0]
        st.markdown(f"# {first_scene.get('title', '未命名故事')}")
        st.markdown(f"*{story.genre} · 第 {story.current_scene + 1} 章*")

    st.markdown("---")

    # 1. 历史回顾 (折叠显示)
    if len(story.scenes) > 0:
        with st.expander("◈ 查看故事历程", expanded=False):
            for scene in story.scenes:
                st.markdown(f"### 第 {scene['scene_number']} 章: {scene['title']}")
                st.markdown(scene['description'])
                st.markdown("---")

    # 2. 上一个选择的后果 (作为衔接)
    if story.choices_made:
        last_choice = story.choices_made[-1]
        st.markdown("---")
        st.markdown("### ◇ 您的选择产生了影响")
        st.markdown(f'<div class="consequence-box">{last_choice["consequence"]}</div>', unsafe_allow_html=True)

    # 3. 当前正在进行的章节
    st.markdown("---")
    scene_data = st.session_state.current_scene_data
    if scene_data:
        st.markdown(f"## {scene_data.get('title', '新篇章')}")
        
        st.markdown('<div class="story-scene">', unsafe_allow_html=True)
        st.markdown(scene_data.get('description', '正在展开剧情...'))

        if scene_data.get('environment_details'):
            with st.expander("◈ 环境细节"):
                st.markdown(scene_data['environment_details'])

        if scene_data.get('character_emotions'):
            st.info(f"**氛围**: {scene_data['character_emotions']}")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 选项显示逻辑
    if not st.session_state.current_scene_data or st.session_state.current_scene_data.get("scene_number") != story.current_scene + 1:
        # 如果当前没有下一章节数据，自动触发生成（为了兼容性和初始状态）
        with st.spinner("故事继续展开..."):
            try:
                previous_choice = story.choices_made[-1] if story.choices_made else None
                scene_data = asyncio.run(agent.generate_next_scene(
                    state=story,
                    previous_choice=previous_choice
                ))
                st.session_state.current_scene_data = scene_data
                st.rerun()
            except Exception as e:
                st.error(f"生成场景失败: {e}")
    else:
        # 显示选项
        scene_data = st.session_state.current_scene_data

        st.markdown("### ◈ 您的选择")

        choices = scene_data.get('choices', [])
        
        # 检查是否需要启动预取
        if not st.session_state.prefetched_scenes and st.session_state.prefetch_future is None:
            # 启动后台预取
            def do_prefetch():
                return _run_async_in_thread(
                    agent.prefetch_scenes_for_choices(story, choices)
                )
            st.session_state.prefetch_future = _executor.submit(do_prefetch)
        
        # 检查预取是否完成
        if st.session_state.prefetch_future and st.session_state.prefetch_future.done():
            try:
                st.session_state.prefetched_scenes = st.session_state.prefetch_future.result()
            except Exception:
                st.session_state.prefetched_scenes = {}
            st.session_state.prefetch_future = None

        for choice in choices:
            st.markdown("---")

            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"**选项 {choice['id']}**")
                st.markdown(choice['text'])

                # 提示 - 放入折叠面板以减少干扰
                if choice.get('motivation') or choice.get('potential_consequence'):
                    with st.expander("◈ 查看选择解析与提示"):
                        if choice.get('motivation'):
                            st.caption(f"◇ 设定动机: {choice['motivation']}")
                        if choice.get('potential_consequence'):
                            st.caption(f"◈ 可能后果: {choice['potential_consequence']}")

            with col2:
                if st.button(
                    f"选择",
                    key=f"choice_{choice['id']}",
                    use_container_width=True,
                    type="primary"
                ):
                    # 处理选择
                    handle_choice(agent, story, choice, scene_data)
                    st.rerun()


def handle_choice(agent, story, choice, scene_data):
    """处理用户选择 - 并行优化版"""
    try:
        choice_id = choice.get('id')
        
        # 1. 添加当前场景到历史
        new_scene = {
            "scene_number": scene_data['scene_number'],
            "title": scene_data['title'],
            "description": scene_data['description'],
            "environment": scene_data.get('environment_details', ''),
            "mood": scene_data.get('character_emotions', ''),
            "timestamp": datetime.now().isoformat()
        }
        story.scenes.append(new_scene)
        story.current_scene = scene_data['scene_number']
        
        # 2. 获取下一场景数据（优先使用预加载）
        prefetched = st.session_state.prefetched_scenes.get(choice_id)
        
        if prefetched:
            next_scene_data = prefetched
        else:
            with st.spinner("正在生成后续剧情..."):
                next_scene_data = asyncio.run(agent.generate_next_scene(
                    state=story,
                    previous_choice={
                        "option_text": choice.get('text', ''),
                        "motivation": choice.get('motivation', '')
                    }
                ))
        
        # 3. 记录选择与后果
        choice_record = {
            "scene_number": story.current_scene,
            "choice": choice,
            "consequence": next_scene_data.get('immediate_consequence', '你的行动产生了意想不到的影响。'),
            "npc_reactions": next_scene_data.get('npc_reactions', {}),
            "analysis": {}, # 后台深度分析会填充此项
            "timestamp": datetime.now().isoformat()
        }
        story.choices_made.append(choice_record)
        
        # 4. 更新世界状态
        world_changes = next_scene_data.get('world_state_changes', {})
        if isinstance(world_changes, dict):
            story.world_state.update(world_changes)
        
        # 5. 更新 UI 状态
        st.session_state.current_scene_data = next_scene_data
        
        # 5. 后台深度分析与保存
        choice_index = len(story.choices_made) - 1
        def background_tasks():
            # 深度分析
            _run_async_in_thread(agent.process_choice_analysis_background(story, choice_index))
            # 自动保存
            _run_async_in_thread(agent.save_story(story))
            
        _executor.submit(background_tasks)
        
        # 6. 清除预取缓存
        st.session_state.prefetched_scenes = {}
        st.session_state.prefetch_future = None
        
        # 4. 保存故事
        success = asyncio.run(agent.save_story(story))
        if not success:
            st.warning("⚠️ 故事保存失败，进度可能丢失")

    except Exception as e:
        st.error(f"处理选择失败: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_story_ending(agent):
    """显示故事结束和分析"""
    story = st.session_state.current_story

    # 确保最终状态被保存
    success = asyncio.run(agent.save_story(story))
    if not success:
        st.error("⚠️ 无法保存最终进度")

    st.markdown("# ◇ 故事结束")
    st.markdown("感谢您的参与！让我们看看您在故事中展现的性格...")
    st.markdown("---")

    # 生成分析
    if "story_analysis" not in st.session_state:
        with st.spinner("正在分析你的选择..."):
            try:
                analysis = asyncio.run(agent.generate_story_analysis(story))
                st.session_state.story_analysis = analysis
            except Exception as e:
                st.error(f"分析失败: {e}")
                return

    analysis = st.session_state.story_analysis

    # 显示分析
    st.markdown("## ◈ 人格分析")

    # Big Five
    if "overall_personality" in analysis:
        st.markdown("### ◇ 性格特征")

        personality = analysis["overall_personality"]

        for trait, description in personality.items():
            with st.expander(f"**{trait.capitalize()}**"):
                st.markdown(description)

    # 核心价值观
    if "core_values" in analysis:
        st.markdown("### ◇ 核心价值观")

        values = analysis["core_values"]
        cols = st.columns(3)

        for idx, value in enumerate(values):
            col = cols[idx % 3]
            with col:
                st.info(value)

    # 道德基础
    if "moral_foundations" in analysis:
        st.markdown("### ◇ 道德基础")

        moral = analysis["moral_foundations"]

        col1, col2 = st.columns(2)

        with col1:
            for key in list(moral.keys())[:3]:
                st.metric(key.replace("_", " ").title(), moral[key])

        with col2:
            for key in list(moral.keys())[3:]:
                st.metric(key.replace("_", " ").title(), moral[key])

    # 决策模式
    if "decision_patterns" in analysis:
        st.markdown("### ◇ 决策模式")

        for pattern in analysis["decision_patterns"]:
            st.markdown(f"- {pattern}")

    # 关键时刻
    if "key_moments" in analysis:
        st.markdown("### ◇ 关键时刻")

        for moment in analysis["key_moments"]:
            with st.expander(f"场景 {moment['scene']}"):
                st.markdown(f"**选择**: {moment['choice']}")
                st.markdown(f"**意义**: {moment['significance']}")

    # 角色成长
    if "character_arc" in analysis:
        st.markdown("### ◇ 角色成长")
        st.info(analysis["character_arc"])

    # 建议
    if "recommendations" in analysis:
        st.markdown("### ◇ 建议")
        st.success(analysis["recommendations"])

    st.markdown("---")

    # 操作按钮
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("保存分析", use_container_width=True):
            # 保存分析到文件
            analysis_file = f"memory/stories/analysis_{story.story_id}.json"
            import json
            from pathlib import Path

            Path(analysis_file).parent.mkdir(parents=True, exist_ok=True)
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            st.success("◈ 分析已保存")

    with col2:
        if st.button("导出故事", use_container_width=True):
            # 导出完整故事
            export_text = f"# {story.scenes[0].get('title', '故事')}\n\n"
            export_text += f"**类型**: {story.genre}\n\n"
            export_text += "---\n\n"

            for scene in story.scenes:
                export_text += f"## 第 {scene['scene_number'] + 1} 章\n\n"
                export_text += f"{scene['description']}\n\n"

                # 找到这个场景的选择
                choices = [c for c in story.choices_made if c['scene_number'] == scene['scene_number']]
                if choices:
                    choice = choices[0]
                    export_text += f"**你的选择**: {choice['choice']['text']}\n\n"
                    export_text += f"**后果**: {choice['consequence']}\n\n"

                export_text += "---\n\n"

            st.download_button(
                label="下载故事",
                data=export_text,
                file_name=f"story_{story.story_id}.md",
                mime="text/markdown"
            )

    with col3:
        if st.button("新故事", use_container_width=True):
            # 清除状态，开始新故事
            st.session_state.current_story = None
            st.session_state.current_scene_data = None
            st.session_state.ending_story = False
            if "story_analysis" in st.session_state:
                del st.session_state.story_analysis
            st.rerun()


# CSS 样式
st.markdown("""
<style>
    .story-scene {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin: 1rem 0;
        line-height: 1.8;
        font-size: 1.1rem;
        box_shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    @media (max-width: 768px) {
        .story-scene {
            padding: 1.2rem;
            font-size: 1rem;
            line-height: 1.6;
        }
    }

    .consequence-box {
        background: rgba(255, 243, 205, 0.1);
        border-left: 4px solid #ffc107;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: #ffe082;
    }

    .choice-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        transition: all 0.3s;
    }

    .choice-card:hover {
        border-color: #667eea;
        background: rgba(102, 126, 234, 0.1);
        transform: translateX(5px);
    }
</style>
""", unsafe_allow_html=True)
