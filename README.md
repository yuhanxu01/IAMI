# IAMI - I Am I

让 Claude Code 学习并模拟你的思维模式的项目。

## 🆕 GraphRAG 知识检索系统

现已集成 **GraphRAG** 知识图谱检索系统，提供强大的记忆检索和分析能力：

- 🔍 **智能检索**: 基于 LightRAG 的知识图谱查询
- 🤖 **Claude Code 集成**: 通过 MCP Server 无缝对接
- 📊 **可视化**: 人际关系网络和思想演变时间轴
- ⚡ **实时更新**: 自动监控文件变化并更新索引
- 💻 **本地运行**: 完全本地部署，使用 DeepSeek API

**快速开始**:
```bash
pip install -r graphrag/requirements.txt
cp .env.example .env  # 填入 DEEPSEEK_API_KEY
python graphrag/cli.py build
python graphrag/cli.py query "我的性格特征是什么？"
```

**详细文档**: [GraphRAG 快速指南](./graphrag/QUICKSTART.md) | [完整文档](./graphrag/README.md)

---

## 项目概述

IAMI 是一个让 AI 成为"数字自我"的系统。通过持续的对话和学习，Claude 会逐渐理解你的：

- 思维模式和决策方式
- 语言习惯和表达风格
- 价值观和信念体系
- 知识储备和兴趣领域
- 性格特点和情绪反应

## 快速开始

在 Claude Code 中打开此项目后：

### 进入学习模式
输入：`学习模式` 或 `learn mode`

Claude 会向你提问（选择题和问答题混合），分析你的回答，并更新记忆文件。

### 进入模拟模式
输入：`模拟模式` 或 `simulate mode`

Claude 会读取所有记忆，以你的思维方式和语言风格来回答问题。

## 项目结构

```
IAMI/
├── CLAUDE.md                    # Claude Code 主入口配置
├── README.md                    # 本文件
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

## 记忆系统

### 短期记忆
- 最近对话的上下文
- 待跟进的话题
- 近期观察到的变化

### 长期记忆
- **personality.json**: 性格特征（大五人格等）
- **values.json**: 价值观和信念
- **thinking_patterns.json**: 思维模式和决策风格
- **language_style.json**: 语言习惯和表达方式
- **knowledge.json**: 专业知识和兴趣领域

## 模拟模式命令

在模拟模式中可以使用：
- `退出模拟` - 回到正常 Claude 对话
- `元分析` - Claude 跳出角色分析模拟准确度
- `补充记忆` - 临时切换到学习模式

## GraphRAG 使用指南

### 命令行工具

```bash
# 构建索引
python graphrag/cli.py build

# 查询知识图谱
python graphrag/cli.py query "我的价值观是什么？"

# 生成可视化
python graphrag/cli.py visualize

# 查看统计
python graphrag/cli.py stats

# 实时监控（自动更新索引）
python graphrag/cli.py watch
```

### Claude Code 集成

1. 编辑 `.claude/mcp.json` 并填入你的 DeepSeek API Key
2. 启动 Claude Code
3. 在对话中直接问：
   - "查询我的性格特征"
   - "显示我的人际关系网络"
   - "查看我的思想演变时间轴"

### 更多文档

- [快速开始](./graphrag/QUICKSTART.md) - 5分钟快速部署
- [完整文档](./graphrag/README.md) - 详细功能说明
- [部署指南](./graphrag/DEPLOYMENT.md) - 部署步骤和配置
- [集成指南](./graphrag/INTEGRATION.md) - Claude Code 集成详解

---

## 隐私说明

所有记忆数据存储在本地文件中，你可以随时查看、编辑或删除。GraphRAG 索引也完全本地存储，只有查询文本会发送到 LLM API。
