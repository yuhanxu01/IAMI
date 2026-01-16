# IAMI GraphRAG 部署指南

## 系统状态

✅ **已完成**:
- GraphRAG 核心系统（基于 LightRAG）
- 数据索引器（支持所有 IAMI 记忆数据）
- MCP Server（Claude Code 集成）
- 关系图谱可视化
- 时间轴追踪
- 实时文件监控和索引更新
- CLI 命令行工具
- Python 依赖安装

⚠️ **待配置**:
- DeepSeek API Key

---

## 立即部署（3 步完成）

### 步骤 1: 设置 DeepSeek API Key

1. **获取 API Key**
   - 访问 [DeepSeek 平台](https://platform.deepseek.com/)
   - 注册/登录账号
   - 在 API Keys 页面创建新的 API Key

2. **配置环境变量**

创建 `.env` 文件：

```bash
cd /home/user/IAMI
cp .env.example .env
nano .env
```

在 `.env` 文件中填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

保存并退出（Ctrl+X, Y, Enter）

### 步骤 2: 验证系统

运行测试脚本：

```bash
python graphrag/test_system.py
```

你应该看到：
```
✓ PASS: Imports
✓ PASS: Configuration
✓ PASS: Data Loader
✓ PASS: Visualizer

🎉 All tests passed! System is ready to use.
```

### 步骤 3: 构建知识图谱索引

```bash
python graphrag/cli.py build
```

预计耗时 1-3 分钟（取决于数据量）。

---

## 使用方式

### 方式 1: 命令行工具（CLI）

#### 查询知识图谱

```bash
# 基本查询
python graphrag/cli.py query "用户的性格特征是什么？"

# 高级查询
python graphrag/cli.py query "用户和家人的关系如何？" --mode local --top-k 10
```

#### 查看统计信息

```bash
python graphrag/cli.py stats
```

#### 生成可视化

```bash
python graphrag/cli.py visualize
```

可视化文件保存在 `graphrag/storage/visualizations/`

#### 实时监控（后台运行）

```bash
# 在新终端中运行
python graphrag/cli.py watch
```

当你更新记忆文件时，索引会自动更新。

---

### 方式 2: Claude Code MCP Server（推荐）

#### A. 配置 MCP Server

MCP 配置文件已创建：`.claude/mcp.json`

**重要**: 编辑此文件，填入你的 API Key：

```bash
nano .claude/mcp.json
```

找到这一行：
```json
"DEEPSEEK_API_KEY": "",
```

改为：
```json
"DEEPSEEK_API_KEY": "sk-your-actual-api-key-here",
```

#### B. 启动 Claude Code

Claude Code 会自动加载 MCP Server。

#### C. 在对话中使用

直接在 Claude Code 对话中问：

```
查询我的性格特征
```

```
显示我的人际关系网络
```

```
查看我的思想演变时间轴
```

Claude Code 会自动调用相应的 MCP 工具。

---

### 方式 3: Python API

```python
import os
from graphrag.indexer import IAMIGraphIndexerSync, IndexConfig

# 配置
config = IndexConfig(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    working_dir="./graphrag/storage/index"
)

# 创建索引器
indexer = IAMIGraphIndexerSync(config)

# 查询
result = indexer.query("用户的性格特征是什么？")
print(result['result'])
```

---

## 可用的 MCP 工具

在 Claude Code 中自动可用：

| 工具名称 | 功能 | 示例问题 |
|---------|------|---------|
| `iami_query` | 查询知识图谱 | "我的价值观是什么？" |
| `iami_rebuild_index` | 重建索引 | "重建知识图谱索引" |
| `iami_get_relationships` | 获取关系网络 | "显示我的人际关系" |
| `iami_get_timeline` | 获取时间轴 | "显示我的思想演变" |
| `iami_get_profile` | 获取人物画像 | "显示我的综合画像" |
| `iami_index_stats` | 查看统计 | "查看索引状态" |

---

## 查询模式说明

GraphRAG 支持 4 种查询模式：

- **naive**: 简单向量搜索，速度最快
- **local**: 局部图谱搜索，适合关系查询（如"我和张三的关系"）
- **global**: 全局图谱搜索，适合概览性问题（如"总结我的价值观"）
- **hybrid**: 混合模式（默认），综合以上方法，推荐使用

示例：
```bash
# 关系查询用 local
python graphrag/cli.py query "我和家人的关系" --mode local

# 概览用 global
python graphrag/cli.py query "总结我的性格" --mode global

# 通用查询用 hybrid
python graphrag/cli.py query "我的思想如何演变" --mode hybrid
```

---

## 工作流推荐

### 日常使用

1. **启动文件监控**（可选，推荐）
   ```bash
   python graphrag/cli.py watch
   ```

2. **使用 Claude Code 进行对话**
   - Claude Code 会自动调用 GraphRAG 工具
   - 你的问题会被智能路由到知识图谱

3. **定期查看可视化**
   ```bash
   python graphrag/cli.py visualize
   ```

### 更新记忆后

如果你大量更新了记忆数据：

```bash
# 重建索引
python graphrag/cli.py build --force

# 或者在 Claude Code 中说
"重建知识图谱索引"
```

---

## 性能建议

### 索引性能

- **首次索引**: 1-3 分钟（取决于数据量）
- **增量更新**: 10-30 秒（文件监控模式）
- **查询速度**: 1-5 秒（取决于查询模式）

### 优化建议

1. **使用文件监控**: 避免频繁手动重建索引
2. **选择合适的查询模式**: 简单问题用 naive，复杂问题用 hybrid
3. **定期清理缓存**: `rm -rf graphrag/storage/cache/*`

---

## 故障排查

### 问题 1: API Key 错误

```
Error: DEEPSEEK_API_KEY not set
```

**解决**:
1. 确认 `.env` 文件存在
2. 确认 API Key 正确填写
3. 重新运行命令

### 问题 2: 导入错误

```
ImportError: No module named 'lightrag'
```

**解决**:
```bash
pip install -r graphrag/requirements.txt
```

### 问题 3: 索引失败

**解决**:
1. 检查 JSON 文件格式
2. 查看详细错误日志
3. 尝试强制重建：
   ```bash
   python graphrag/cli.py build --force
   ```

### 问题 4: MCP Server 无响应

**解决**:
1. 确认 `.claude/mcp.json` 配置正确
2. 检查 API Key 是否填写
3. 重启 Claude Code

### 问题 5: 查询无结果

**解决**:
1. 确认索引已构建：`python graphrag/cli.py stats`
2. 尝试不同查询模式
3. 检查数据是否存在于 `memory/` 目录

---

## 维护

### 定期任务

**每周**:
- 重建索引（如果有大量更新）
  ```bash
  python graphrag/cli.py build --force
  ```

**每月**:
- 清理缓存
  ```bash
  rm -rf graphrag/storage/cache/*
  ```
- 更新依赖
  ```bash
  pip install -r graphrag/requirements.txt --upgrade
  ```

### 备份

重要文件需要备份：
- `graphrag/storage/index/` - 索引数据
- `.env` - 配置文件
- `.claude/mcp.json` - MCP 配置

```bash
# 创建备份
tar -czf graphrag-backup-$(date +%Y%m%d).tar.gz graphrag/storage .env .claude/mcp.json
```

---

## 进阶使用

### 自定义查询

```python
from graphrag.indexer import IAMIGraphIndexerSync, IndexConfig

indexer = IAMIGraphIndexerSync(config)

# 批量查询
questions = [
    "用户的性格特征",
    "用户的价值观",
    "用户的人际关系"
]

for q in questions:
    result = indexer.query(q)
    print(f"\n{q}:\n{result['result']}\n")
```

### 导出数据

```python
import json

stats = indexer.get_stats()

with open('graphrag_export.json', 'w') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
```

---

## 技术栈

- **GraphRAG**: LightRAG (HKU)
- **Vector DB**: HNSW + nano-vectordb
- **LLM**: DeepSeek API
- **Integration**: Model Context Protocol (MCP)
- **Visualization**: Plotly + Pyvis
- **CLI**: Click + Rich

---

## 支持

### 文档

- [README.md](./README.md) - 完整文档
- [QUICKSTART.md](./QUICKSTART.md) - 快速开始
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 本文档

### 命令帮助

```bash
python graphrag/cli.py --help
python graphrag/cli.py query --help
```

### 日志

所有操作都会输出详细日志，查看控制台输出即可。

---

## 下一步

系统已经完全部署好了！你只需要：

1. ✅ 设置 DeepSeek API Key
2. ✅ 运行测试验证
3. ✅ 构建索引
4. ✅ 开始使用！

**推荐的第一个查询**:
```bash
python graphrag/cli.py query "帮我总结一下我的个人特征"
```

或者在 Claude Code 中：
```
帮我总结一下我的个人特征
```

享受你的 IAMI GraphRAG 知识检索系统！🚀
