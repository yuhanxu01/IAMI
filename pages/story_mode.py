"""
故事模式页面

通过沉浸式的故事和角色扮演来分析用户的人格特征。
每次都是全新生成的故事，用户的选择会影响剧情走向。
"""

import asyncio
import streamlit as st
import json
from datetime import datetime


def render():
    """渲染故事模式页面"""
    st.markdown("# 📖 故事模式")
    st.markdown("在沉浸式的故事中展现真实的自我，通过选择揭示你的性格")
    st.markdown("---")

    # 检查代理
    if not st.session_state.agents_loaded:
        st.error("代理未加载")
        return

    # 初始化故事代理
    if "story_agent" not in st.session_state:
        from graphrag.agents import IAMIStoryAgent
        st.session_state.story_agent = IAMIStoryAgent(st.session_state.indexer)

    agent = st.session_state.story_agent

    # 初始化状态
    if "current_story" not in st.session_state:
        st.session_state.current_story = None
    if "waiting_for_choice" not in st.session_state:
        st.session_state.waiting_for_choice = False
    if "current_scene_data" not in st.session_state:
        st.session_state.current_scene_data = None

    # 侧边栏
    with st.sidebar:
        st.markdown("### 📚 故事管理")

        # 如果没有进行中的故事
        if not st.session_state.current_story:
            st.info("✨ 开始一个全新的故事")

            # 故事列表
            stories = agent.list_stories()
            if stories:
                st.markdown("---")
                st.markdown("### 💾 已保存的故事")

                for story in stories[:5]:
                    with st.expander(f"{story['genre']} - {story['timestamp'][:10]}"):
                        st.write(f"场景数: {story['scenes_count']}")
                        st.write(f"选择数: {story['choices_count']}")

                        if st.button(f"继续", key=f"load_{story['story_id']}"):
                            state = agent.load_story(story['story_id'])
                            if state:
                                st.session_state.current_story = state
                                st.rerun()
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
                if st.button("💾 保存", use_container_width=True):
                    agent.save_story(story)
                    st.success("✓ 已保存")

            with col2:
                if st.button("🔚 结束", use_container_width=True):
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
    st.markdown("## ✨ 开始新故事")

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
        st.markdown("### 🎭 选择故事类型")

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
        st.markdown("### 📚 类型说明")

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

    if st.button("🎬 开始故事", type="primary", use_container_width=True):
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
                st.success("✓ 故事世界已创建")
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

    # 显示最新场景
    if story.scenes:
        latest_scene = story.scenes[-1]

        st.markdown(f"## 第 {latest_scene['scene_number'] + 1} 章")

        # 场景描写
        st.markdown('<div class="story-scene">', unsafe_allow_html=True)
        st.markdown(latest_scene.get('description', ''))

        if latest_scene.get('environment'):
            with st.expander("🌍 环境细节"):
                st.markdown(latest_scene['environment'])

        if latest_scene.get('mood'):
            st.info(f"**氛围**: {latest_scene['mood']}")

        st.markdown('</div>', unsafe_allow_html=True)

        # 显示最近的选择后果
        if story.choices_made and story.current_scene == latest_scene['scene_number']:
            last_choice = story.choices_made[-1]
            if last_choice.get('consequence'):
                st.markdown("---")
                st.markdown("### ⚡ 你的选择的影响")
                st.markdown('<div class="consequence-box">', unsafe_allow_html=True)
                st.markdown(last_choice['consequence'])
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 生成或显示选项
    if not st.session_state.current_scene_data or st.session_state.current_scene_data.get("scene_number") != story.current_scene + 1:
        # 需要生成新场景
        if st.button("📖 继续故事", type="primary", use_container_width=True):
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

        st.markdown("### 🎯 你的选择")

        choices = scene_data.get('choices', [])

        for choice in choices:
            st.markdown("---")

            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"**选项 {choice['id']}**")
                st.markdown(choice['text'])

                # 提示
                if choice.get('motivation'):
                    st.caption(f"💭 动机: {choice['motivation']}")

                if choice.get('potential_consequence'):
                    st.caption(f"⚠️ 可能: {choice['potential_consequence']}")

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
    """处理用户选择"""
    with st.spinner("处理你的选择..."):
        try:
            # 处理选择
            result = asyncio.run(agent.process_choice(story, choice))

            # 添加场景
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

            # 清除当前场景数据
            st.session_state.current_scene_data = None

            # 保存
            agent.save_story(story)

        except Exception as e:
            st.error(f"处理选择失败: {e}")


def show_story_ending(agent):
    """显示故事结束和分析"""
    story = st.session_state.current_story

    st.markdown("# 🎬 故事结束")
    st.markdown("感谢你的参与！让我们看看你在故事中展现的性格...")
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
    st.markdown("## 📊 人格分析")

    # Big Five
    if "overall_personality" in analysis:
        st.markdown("### 🎭 性格特征 (Big Five)")

        personality = analysis["overall_personality"]

        for trait, description in personality.items():
            with st.expander(f"**{trait.capitalize()}**"):
                st.markdown(description)

    # 核心价值观
    if "core_values" in analysis:
        st.markdown("### 💎 核心价值观")

        values = analysis["core_values"]
        cols = st.columns(3)

        for idx, value in enumerate(values):
            col = cols[idx % 3]
            with col:
                st.info(value)

    # 道德基础
    if "moral_foundations" in analysis:
        st.markdown("### ⚖️ 道德基础")

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
        st.markdown("### 🧠 决策模式")

        for pattern in analysis["decision_patterns"]:
            st.markdown(f"- {pattern}")

    # 关键时刻
    if "key_moments" in analysis:
        st.markdown("### ⭐ 关键时刻")

        for moment in analysis["key_moments"]:
            with st.expander(f"场景 {moment['scene']}"):
                st.markdown(f"**选择**: {moment['choice']}")
                st.markdown(f"**意义**: {moment['significance']}")

    # 角色成长
    if "character_arc" in analysis:
        st.markdown("### 🌱 角色成长")
        st.info(analysis["character_arc"])

    # 建议
    if "recommendations" in analysis:
        st.markdown("### 💡 建议")
        st.success(analysis["recommendations"])

    st.markdown("---")

    # 操作按钮
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 保存分析", use_container_width=True):
            # 保存分析到文件
            analysis_file = f"memory/stories/analysis_{story.story_id}.json"
            import json
            from pathlib import Path

            Path(analysis_file).parent.mkdir(parents=True, exist_ok=True)
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            st.success("✓ 分析已保存")

    with col2:
        if st.button("📥 导出故事", use_container_width=True):
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
        if st.button("🆕 新故事", use_container_width=True):
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
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        line-height: 1.8;
        font-size: 1.1rem;
    }

    .consequence-box {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    .choice-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s;
    }

    .choice-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }
</style>
""", unsafe_allow_html=True)
