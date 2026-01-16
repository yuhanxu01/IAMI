# IAMI GraphRAG 快速开始指南

## 5 分钟快速部署

### 步骤 1: 安装依赖

```bash
cd /home/user/IAMI
pip install -r graphrag/requirements.txt
```

预计耗时: 2-3 分钟

### 步骤 2: 配置 API Key

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

在 `.env` 文件中设置：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

保存并退出（Ctrl+X, Y, Enter）

### 步骤 3: 构建索引

```bash
python graphrag/cli.py build
```

首次构建会索引所有记忆数据，预计 1-2 分钟。

### 步骤 4: 测试查询

```bash
python graphrag/cli.py query "用户的性格特征是什么？"
```

完成！现在你可以查询任何关于用户记忆的问题了。

---

## 与 Claude Code 集成

### 方法 1: MCP Server（推荐）

#### 1. 创建 MCP 配置

在项目根目录创建或编辑 `.claude/mcp.json`：

```bash
mkdir -p .claude
nano .claude/mcp.json
```

添加以下内容：

```json
{
  "mcpServers": {
    "iami-graphrag": {
      "command": "python",
      "args": ["/home/user/IAMI/graphrag/server/mcp_server.py"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

#### 2. 启动 Claude Code

```bash
claude-code
```

Claude Code 会自动加载 MCP Server。

#### 3. 使用

在 Claude Code 对话中直接问：

```
查询我的性格特征
```

Claude Code 会自动调用 `iami_query` 工具。

### 方法 2: 直接命令行

在 Claude Code 对话中，你也可以让 Claude 运行 CLI 命令：

```
请运行: python graphrag/cli.py query "我的价值观是什么？"
```

---

## 常用命令速查

```bash
# 构建/重建索引
python graphrag/cli.py build
python graphrag/cli.py build --force  # 强制重建

# 查询
python graphrag/cli.py query "问题"
python graphrag/cli.py query "问题" --mode hybrid --top-k 10

# 统计信息
python graphrag/cli.py stats

# 可视化
python graphrag/cli.py visualize

# 监控文件变化（实时更新）
python graphrag/cli.py watch
```

---

## MCP 工具说明

在 Claude Code 中可用的工具：

| 工具名称 | 用途 | 示例 |
|---------|------|------|
| `iami_query` | 查询知识图谱 | "查询我的性格特征" |
| `iami_rebuild_index` | 重建索引 | "重建知识图谱索引" |
| `iami_get_relationships` | 获取关系网络 | "显示我的人际关系网络" |
| `iami_get_timeline` | 获取时间轴 | "显示我的思想演变时间轴" |
| `iami_get_profile` | 获取人物画像 | "显示我的综合人物画像" |
| `iami_index_stats` | 索引统计 | "查看索引统计信息" |

---

## 查询模式选择

不同问题使用不同模式可获得最佳结果：

| 问题类型 | 推荐模式 | 示例 |
|---------|---------|------|
| 关系查询 | `local` | "我和张三的关系如何？" |
| 概览性问题 | `global` | "总结一下我的价值观" |
| 具体事实 | `naive` | "我的性格开放性得分是多少？" |
| 复杂问题 | `hybrid` | "我的思想如何随时间演变？" |

**默认使用 `hybrid` 模式，适合大多数情况。**

---

## 实时更新工作流

如果你在持续更新记忆数据：

### 终端 1: 运行文件监控
```bash
python graphrag/cli.py watch
```

### 终端 2: 使用 Claude Code
```bash
claude-code
```

现在，当你在 Claude Code 中更新记忆数据时，索引会自动更新！

---

## 可视化输出

运行可视化命令后：

```bash
python graphrag/cli.py visualize
```

输出文件位置：
- 关系网络: `graphrag/storage/visualizations/relationships.html`
- 时间轴: `graphrag/storage/visualizations/timeline.html`

在浏览器中打开这些文件查看交互式可视化。

---

## 故障排查速查

| 问题 | 解决方案 |
|------|---------|
| `DEEPSEEK_API_KEY not set` | 检查 `.env` 文件是否存在且配置正确 |
| `LightRAG not installed` | 运行 `pip install lightrag` |
| `MCP not available` | 运行 `pip install mcp` |
| 查询无结果 | 1. 运行 `python graphrag/cli.py stats` 检查索引<br>2. 尝试 `python graphrag/cli.py build --force` 重建 |
| 索引构建失败 | 检查 memory/ 目录下的 JSON 文件格式是否正确 |

---

## 下一步

- 📖 阅读完整文档: [README.md](./README.md)
- 🔧 自定义配置: [config.yaml](./config.yaml)
- 💻 查看 Python API: [README.md#python-api](./README.md#python-api)
- 🎨 了解可视化: [README.md#可视化](./README.md#可视化)

---

## 获取帮助

- 查看帮助: `python graphrag/cli.py --help`
- 查看命令帮助: `python graphrag/cli.py query --help`
- 查看日志: 检查控制台输出

享受你的 IAMI GraphRAG 知识检索系统！🚀
