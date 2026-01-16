# IAMI - I Am My Intelligence (我即是我)

这是一个让 Claude 学习并模拟用户思维模式的项目。

**核心理念**: 人的思想是动态的，会随时间变化。本系统不只记录"你是谁"，更追踪"你如何变化"。

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
│   ├── long_term/               # 长期记忆 (JSON) - 带历史追踪
│   │   ├── personality.json     # 性格特征 (Big Five)
│   │   ├── values.json          # 价值观 (Schwartz + Moral Foundations)
│   │   ├── thinking_patterns.json # 思维模式
│   │   ├── language_style.json  # 语言风格
│   │   └── knowledge.json       # 知识储备
│   └── timeline/                # 思想演变时间轴
│       ├── snapshots.json       # 思想快照
│       └── evolution.md         # 演变记录
├── analysis/
│   ├── profile.json             # 综合人物画像
│   └── insights.md              # 分析洞察
└── questions/
    ├── categories.md            # 问题库（基于学术框架）
    └── asked_history.json       # 已问过的问题记录
```

## 学术框架

问题设计和分析基于以下学术研究：
- **Big Five Inventory (BFI-2)** - 性格五因素模型
- **Schwartz Value Survey** - 10种基本人类价值观
- **Moral Foundations Theory** - Haidt的道德基础理论
- **Situational Judgment Tests** - 情境判断测试方法
- **Political Compass** - 双轴政治倾向模型

## 如何使用

当用户在对话开始时输入以下关键词，进入对应模式：

### 进入学习模式
用户输入: `学习模式` 或 `learn mode`
- 读取 `modes/learn.md` 并按照其指令执行
- 使用具体情境问题（非空洞的抽象问题）
- 追溯真实经历，挖掘推理过程
- 所有记录带时间戳，追踪变化

### 进入模拟模式
用户输入: `模拟模式` 或 `simulate mode`
- 读取 `modes/simulate.md` 并按照其指令执行
- 读取所有记忆文件和时间轴
- 以用户**当前**的思维模式回答（考虑演变历史）

## 核心原则

1. **时间维度**: 所有记录带时间戳，追踪思想演变
2. **具体化**: 用情境判断题，不问空洞问题
3. **真实性**: 优先追溯真实经历，而非假设性回答
4. **学术基础**: 基于心理学研究框架，不是随意设计

## 模式识别规则

当你看到用户的第一条消息时：
1. 如果包含"学习模式"或"learn mode" → 读取 `modes/learn.md`
2. 如果包含"模拟模式"或"simulate mode" → 读取 `modes/simulate.md`
3. 如果都不包含 → 提示用户选择模式

## 参考资料

- [Big Five Inventory](https://www.colby.edu/academics/departments-and-programs/psychology/research-opportunities/personality-lab/the-bfi-2/)
- [Moral Foundations Theory](https://moralfoundations.org/)
- [Schwartz Value Survey](https://www.mededportal.org/doi/10.15766/mep_2374-8265.10002)
- [Political Compass](https://www.politicalcompass.org/)
