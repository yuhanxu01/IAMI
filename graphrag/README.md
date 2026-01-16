# IAMI GraphRAG - 知识检索系统

基于 LightRAG 的本地知识图谱检索系统，专为 IAMI 思维模拟项目设计。

## 功能特性

- **知识图谱索引**: 自动索引 IAMI memory/ 下的所有记忆数据
- **智能检索**: 支持多种查询模式（naive, local, global, hybrid）
- **MCP Server**: 通过 Model Context Protocol 与 Claude Code 集成
- **可视化**: 人际关系网络和时间轴可视化
- **实时更新**: 监控文件变化自动更新索引
- **本地运行**: 完全本地部署，使用 DeepSeek API

## 系统架构

```
graphrag/
├── indexer/              # 数据索引器
│   ├── data_loader.py    # 加载 IAMI 记忆数据
│   └── graph_indexer.py  # LightRAG 图谱索引
├── server/               # MCP 服务器
│   └── mcp_server.py     # Claude Code 集成
├── visualizer/           # 可视化工具
│   └── graph_visualizer.py
├── storage/              # 存储目录
│   ├── index/            # 索引数据
│   ├── cache/            # 缓存
│   └── visualizations/   # 可视化输出
├── cli.py                # 命令行工具
├── watcher.py            # 文件监控器
├── config.yaml           # 配置文件
└── requirements.txt      # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
cd /home/user/IAMI
pip install -r graphrag/requirements.txt
```

### 2. 配置环境变量

复制示例配置并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置你的 DeepSeek API Key：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 3. 构建索引

```bash
python graphrag/cli.py build
```

### 4. 查询知识图谱

```bash
python graphrag/cli.py query "用户的性格特征是什么？"
```

## 使用方式

### 命令行工具 (CLI)

#### 构建索引
```bash
# 首次构建
python graphrag/cli.py build

# 强制重建
python graphrag/cli.py build --force
```

#### 查询
```bash
# 基本查询（使用 hybrid 模式）
python graphrag/cli.py query "用户的价值观是什么？"

# 指定查询模式
python graphrag/cli.py query "用户和张三的关系如何？" --mode local

# 返回更多结果
python graphrag/cli.py query "用户的思想如何演变？" --top-k 10
```

查询模式说明：
- `naive`: 简单向量搜索
- `local`: 局部图谱搜索（适合关系查询）
- `global`: 全局图谱搜索（适合概览性问题）
- `hybrid`: 混合模式（推荐，综合以上方法）

#### 查看统计
```bash
python graphrag/cli.py stats
```

#### 生成可视化
```bash
# 生成所有可视化
python graphrag/cli.py visualize

# 只生成关系网络
python graphrag/cli.py visualize --no-timeline

# 只生成时间轴
python graphrag/cli.py visualize --no-relationships
```

可视化文件保存在 `graphrag/storage/visualizations/`

#### 监控文件变化
```bash
# 启动文件监控（实时更新索引）
python graphrag/cli.py watch
```

### MCP Server (Claude Code 集成)

#### 1. 启动 MCP Server

```bash
python graphrag/server/mcp_server.py
```

#### 2. 配置 Claude Code

在 Claude Code 的 MCP 配置文件中添加（通常在 `~/.config/claude/mcp.json` 或项目的 `.claude/mcp.json`）：

```json
{
  "mcpServers": {
    "iami-graphrag": {
      "command": "python",
      "args": ["/home/user/IAMI/graphrag/server/mcp_server.py"],
      "env": {
        "DEEPSEEK_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### 3. 在 Claude Code 中使用

MCP Server 提供以下工具：

1. **iami_query**: 查询知识图谱
   ```
   查询用户的性格特征
   ```

2. **iami_rebuild_index**: 重建索引
   ```
   重建知识图谱索引
   ```

3. **iami_get_relationships**: 获取关系网络
   ```
   查看用户的人际关系网络
   ```

4. **iami_get_timeline**: 获取时间轴
   ```
   查看用户思想演变的时间轴
   ```

5. **iami_get_profile**: 获取人物画像
   ```
   查看用户的综合人物画像
   ```

6. **iami_index_stats**: 获取索引统计
   ```
   查看索引统计信息
   ```

Claude Code 会自动识别这些工具并在对话中使用。

## Python API

### 基本使用

```python
import os
from graphrag.indexer import IAMIDataLoader, IAMIGraphIndexer, IndexConfig

# 配置
config = IndexConfig(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    working_dir="./graphrag/storage/index"
)

# 加载数据
loader = IAMIDataLoader()
documents = loader.load_all_data()

# 创建索引
indexer = IAMIGraphIndexer(config)
results = await indexer.index_documents(documents)

# 查询
result = await indexer.query(
    "用户的性格特征是什么？",
    mode="hybrid",
    top_k=5
)
print(result['result'])
```

### 同步 API

```python
from graphrag.indexer import IAMIGraphIndexerSync

# 使用同步版本
indexer = IAMIGraphIndexerSync(config)
results = indexer.index_documents(documents)
result = indexer.query("用户的性格特征是什么？")
```

### 可视化

```python
from graphrag.visualizer import IAMIGraphVisualizer

viz = IAMIGraphVisualizer()

# 生成关系网络可视化
viz.visualize_relationships()

# 生成时间轴可视化
viz.visualize_timeline()
```

## 配置说明

### config.yaml

主要配置项：

```yaml
# LLM Configuration
llm:
  provider: "deepseek"
  model: "deepseek-chat"
  temperature: 0.7
  max_tokens: 4000

# Storage
storage:
  index_dir: "./graphrag/storage/index"
  cache_dir: "./graphrag/storage/cache"

# Indexing
indexing:
  chunk_size: 512
  chunk_overlap: 50
  enable_entity_extraction: true
  enable_relationship_extraction: true

# Query
query:
  top_k: 5
  similarity_threshold: 0.7
```

### 环境变量

- `DEEPSEEK_API_KEY`: DeepSeek API 密钥（必需）
- `GRAPHRAG_INDEX_DIR`: 索引目录（可选）
- `DEEPSEEK_MODEL`: 模型名称（可选，默认 deepseek-chat）
- `LOG_LEVEL`: 日志级别（可选，默认 INFO）

## 数据源

系统自动索引以下数据：

- `memory/long_term/`: 长期记忆（性格、价值观、思维模式等）
- `memory/short_term/`: 短期记忆
- `memory/relationships/`: 人际关系网络
- `memory/environment/`: 生态环境系统
- `memory/timeline/`: 思想演变时间轴
- `memory/conversations/`: 对话历史

每个文档都会被：
1. 解析并提取元数据
2. 分块处理
3. 提取实体和关系
4. 构建知识图谱
5. 创建向量索引

## 故障排查

### 问题：API Key 错误
```
Error: DEEPSEEK_API_KEY not set
```
**解决**: 在 `.env` 文件中设置正确的 API Key

### 问题：索引失败
```
Error indexing document: ...
```
**解决**:
1. 检查 JSON 文件格式是否正确
2. 查看详细错误日志
3. 尝试使用 `--force` 强制重建

### 问题：查询无结果
**解决**:
1. 确认索引已构建：`python graphrag/cli.py stats`
2. 尝试不同的查询模式
3. 检查索引目录是否有数据

### 问题：MCP Server 无法连接
**解决**:
1. 确认 MCP Server 正在运行
2. 检查 Claude Code 的 MCP 配置
3. 查看服务器日志

## 性能优化

### 索引优化
- 调整 `chunk_size` 和 `chunk_overlap`
- 使用更快的 embedding 模型
- 启用缓存

### 查询优化
- 使用适当的查询模式（local vs global）
- 调整 `top_k` 值
- 启用 reranking

### 存储优化
- 定期清理缓存：`rm -rf graphrag/storage/cache/*`
- 压缩索引文件
- 使用 SSD 存储

## 高级功能

### 自定义数据源

编辑 `config.yaml` 添加新的数据源：

```yaml
data_sources:
  - path: "./custom/data/*.json"
    type: "json"
    weight: 1.0
```

### 自定义 LLM

修改 `graph_indexer.py` 中的 LLM 函数以使用其他模型。

### 导出数据

```python
# 导出图谱数据
import json
stats = indexer.get_stats()
with open('export.json', 'w') as f:
    json.dump(stats, f)
```

## 开发

### 运行测试

```bash
# 测试数据加载
python graphrag/indexer/data_loader.py

# 测试索引
python graphrag/indexer/graph_indexer.py

# 测试可视化
python graphrag/visualizer/graph_visualizer.py
```

### 贡献

欢迎贡献！请：
1. Fork 项目
2. 创建特性分支
3. 提交 Pull Request

## 许可证

MIT License

## 相关资源

- [LightRAG](https://github.com/HKUDS/LightRAG)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [DeepSeek API](https://platform.deepseek.com/)
- [IAMI 项目](../README.md)
