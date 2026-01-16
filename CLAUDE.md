# IAMI - I Am My Intelligence (我即是我)

这是一个让 Claude 学习并模拟用户思维模式的项目。

## 项目结构

```
IAMI/
├── CLAUDE.md                    # 本文件 - 主入口
├── modes/
│   ├── learn.md                 # 学习模式指令
│   └── simulate.md              # 模拟模式指令
├── memory/
│   ├── conversations/           # 对话记录 (Markdown)
│   ├── short_term/              # 短期记忆 (JSON)
│   │   └── recent.json
│   └── long_term/               # 长期记忆 (JSON)
│       ├── personality.json     # 性格特征
│       ├── knowledge.json       # 知识储备
│       ├── values.json          # 价值观
│       ├── thinking_patterns.json # 思维模式
│       └── language_style.json  # 语言风格
├── analysis/
│   ├── profile.json             # 综合人物画像
│   └── insights.md              # 分析洞察
└── questions/
    ├── categories.md            # 问题分类库
    └── asked_history.json       # 已问过的问题记录
```

## 如何使用

当用户在对话开始时输入以下关键词，进入对应模式：

### 进入学习模式
用户输入: `学习模式` 或 `learn mode`
- 读取 `modes/learn.md` 并按照其指令执行
- Claude 会向用户提问（选择题和问答题混合）
- 分析对话并更新记忆文件

### 进入模拟模式
用户输入: `模拟模式` 或 `simulate mode`
- 读取 `modes/simulate.md` 并按照其指令执行
- Claude 会读取所有记忆文件
- 以用户的思维模式和语言风格回答问题

## 核心原则

1. **记忆优先**: 始终先读取记忆文件了解用户
2. **持续学习**: 每次对话后更新记忆
3. **准确模拟**: 模拟模式下要完全代入用户视角
4. **中文为主**: 主要使用中文进行对话和记录

## 模式识别规则

当你看到用户的第一条消息时：
1. 如果包含"学习模式"或"learn mode" → 读取 `modes/learn.md`
2. 如果包含"模拟模式"或"simulate mode" → 读取 `modes/simulate.md`
3. 如果都不包含 → 提示用户选择模式
