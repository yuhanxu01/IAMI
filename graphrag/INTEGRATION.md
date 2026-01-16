# IAMI GraphRAG - Claude Code 集成指南

## 集成架构

```
┌─────────────────┐
│  Claude Code    │
│   (用户界面)     │
└────────┬────────┘
         │
         │ MCP Protocol
         ▼
┌─────────────────┐
│  MCP Server     │
│  (工具提供者)    │
└────────┬────────┘
         │
         │ Python API
         ▼
┌─────────────────┐
│  GraphRAG Core  │
│  (LightRAG)     │
└────────┬────────┘
         │
         │ File System
         ▼
┌─────────────────┐
│  IAMI Memory    │
│  (JSON/MD)      │
└─────────────────┘
```

---

## 配置方式

### 方式 1: 项目级配置（推荐）

在项目根目录创建 `.claude/mcp.json`：

```json
{
  "mcpServers": {
    "iami-graphrag": {
      "command": "python",
      "args": ["/home/user/IAMI/graphrag/server/mcp_server.py"],
      "env": {
        "DEEPSEEK_API_KEY": "sk-your-api-key-here",
        "GRAPHRAG_INDEX_DIR": "/home/user/IAMI/graphrag/storage/index",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**优点**:
- 项目专用配置
- 不影响其他项目
- 易于版本控制（注意不要提交 API Key）

**使用**:
```bash
cd /home/user/IAMI
claude-code
```

---

### 方式 2: 全局配置

在用户目录创建 `~/.config/claude/mcp.json`：

```bash
mkdir -p ~/.config/claude
nano ~/.config/claude/mcp.json
```

内容同上。

**优点**:
- 所有 Claude Code 会话都可用
- 一次配置，处处使用

**缺点**:
- 可能与其他项目冲突

---

## MCP Server 详细说明

### 启动方式

MCP Server 由 Claude Code 自动启动，不需要手动运行。

当你启动 Claude Code 时：
1. Claude Code 读取 `mcp.json`
2. 自动运行 `python graphrag/server/mcp_server.py`
3. 建立 stdio 通信通道
4. 注册所有工具

### 工具列表

#### 1. iami_query

**功能**: 查询知识图谱

**参数**:
- `query` (必需): 问题文本
- `mode` (可选): 查询模式（naive/local/global/hybrid）
- `top_k` (可选): 返回结果数量

**示例**:
```
用户: "查询我的性格特征"
Claude: [自动调用 iami_query(query="我的性格特征", mode="hybrid")]
```

---

#### 2. iami_rebuild_index

**功能**: 重建知识图谱索引

**参数**:
- `force` (可选): 是否强制重建

**使用场景**:
- 大量更新记忆数据后
- 索引损坏时
- 切换不同数据版本时

**示例**:
```
用户: "重建索引"
Claude: [自动调用 iami_rebuild_index(force=True)]
```

---

#### 3. iami_get_relationships

**功能**: 获取人际关系网络

**参数**:
- `person_name` (可选): 特定人物名称

**示例**:
```
用户: "显示我和张三的关系"
Claude: [调用 iami_get_relationships(person_name="张三")]
```

---

#### 4. iami_get_timeline

**功能**: 获取思想演变时间轴

**参数**:
- `start_date` (可选): 起始日期
- `end_date` (可选): 结束日期

**示例**:
```
用户: "显示我在2024年的思想变化"
Claude: [调用 iami_get_timeline(start_date="2024-01-01", end_date="2024-12-31")]
```

---

#### 5. iami_get_profile

**功能**: 获取综合人物画像

**参数**: 无

**示例**:
```
用户: "显示我的完整人物画像"
Claude: [调用 iami_get_profile()]
```

---

#### 6. iami_index_stats

**功能**: 获取索引统计信息

**参数**: 无

**示例**:
```
用户: "查看索引状态"
Claude: [调用 iami_index_stats()]
```

---

## 使用模式

### 模式 1: 直接查询

**用户输入**:
```
我的性格开放性得分是多少？
```

**Claude 行为**:
1. 理解问题
2. 调用 `iami_query(query="性格开放性得分")`
3. 接收结果
4. 格式化并返回

---

### 模式 2: 复杂推理

**用户输入**:
```
基于我的性格和价值观，我适合从事什么职业？
```

**Claude 行为**:
1. 调用 `iami_query(query="性格特征")`
2. 调用 `iami_query(query="价值观")`
3. 综合分析
4. 给出职业建议

---

### 模式 3: 关系分析

**用户输入**:
```
分析一下我和家人的关系动态
```

**Claude 行为**:
1. 调用 `iami_get_relationships()`
2. 调用 `iami_query(query="家人关系", mode="local")`
3. 分析关系模式
4. 提供洞察

---

### 模式 4: 时间序列分析

**用户输入**:
```
我的价值观过去一年有什么变化？
```

**Claude 行为**:
1. 调用 `iami_get_timeline()`
2. 提取价值观相关的变化点
3. 分析趋势
4. 总结变化

---

## 高级技巧

### 技巧 1: 组合查询

```
用户: "基于我的性格、价值观和人际关系，帮我规划职业发展"

Claude会:
1. 查询性格特征
2. 查询价值观
3. 查询人际关系
4. 综合分析
5. 给出职业规划建议
```

### 技巧 2: 指定查询模式

```
用户: "用局部图谱模式查询我和导师的关系"

Claude会:
- 使用 mode="local" 进行查询
- 关注关系细节
```

### 技巧 3: 时间过滤

```
用户: "查看我2024年的思想快照"

Claude会:
- 调用 iami_get_timeline
- 过滤2024年的数据
```

### 技巧 4: 多轮对话

```
用户: "查询我的性格特征"
Claude: [返回性格特征]

用户: "基于这个，推荐一些适合我的活动"
Claude: [基于之前的查询结果继续推理]
```

---

## 调试和日志

### 查看 MCP Server 日志

如果 MCP Server 在后台运行，可以通过以下方式查看日志：

1. **Claude Code 内置日志**:
   - Claude Code 通常会显示工具调用日志

2. **手动运行测试**:
   ```bash
   python graphrag/server/mcp_server.py
   ```

   这会启动 MCP Server 并显示所有日志。

3. **设置日志级别**:
   在 `mcp.json` 中：
   ```json
   "env": {
     "LOG_LEVEL": "DEBUG"  // INFO, DEBUG, ERROR
   }
   ```

---

## 故障排查

### 问题 1: Claude Code 找不到 MCP Server

**症状**:
```
Claude没有调用任何 IAMI 工具
```

**解决**:
1. 检查 `.claude/mcp.json` 是否存在
2. 检查路径是否正确
3. 重启 Claude Code

---

### 问题 2: MCP Server 启动失败

**症状**:
```
Error: MCP server failed to start
```

**解决**:
1. 手动测试启动:
   ```bash
   python graphrag/server/mcp_server.py
   ```
2. 检查 Python 依赖是否完整
3. 检查 API Key 是否设置

---

### 问题 3: 工具调用失败

**症状**:
```
Tool execution failed: ...
```

**解决**:
1. 检查索引是否已构建:
   ```bash
   python graphrag/cli.py stats
   ```
2. 重建索引:
   ```bash
   python graphrag/cli.py build --force
   ```

---

### 问题 4: 查询结果为空

**症状**:
```
Query returned no results
```

**解决**:
1. 确认数据存在于 `memory/` 目录
2. 尝试不同的查询模式
3. 降低相似度阈值（在代码中调整）

---

## 性能优化

### 1. 预加载索引

在 MCP Server 启动时预加载索引，减少首次查询延迟。

（已在当前实现中完成）

### 2. 缓存查询结果

对于重复查询，使用缓存避免重复计算。

### 3. 异步处理

使用异步 API 提高并发性能。

（已在当前实现中使用）

---

## 安全建议

### 1. API Key 管理

**不要**:
- ❌ 将 API Key 提交到 Git
- ❌ 在代码中硬编码 API Key
- ❌ 在公开场合分享配置文件

**应该**:
- ✅ 使用环境变量或 `.env` 文件
- ✅ 将 `.env` 添加到 `.gitignore`
- ✅ 使用不同的 API Key 用于开发和生产

### 2. 数据隐私

- 所有数据本地存储
- 只有查询文本发送到 DeepSeek API
- 可以选择使用本地 LLM（需要配置）

---

## 与 IAMI 其他模式集成

### 学习模式集成

在学习模式中，当用户回答问题后：

```python
# 自动触发索引更新
subprocess.run(["python", "graphrag/cli.py", "build"])
```

### 模拟模式集成

在模拟模式中，Claude 可以：

```python
# 查询所有相关记忆
result = iami_query("用户的完整思维模式")

# 基于查询结果进行模拟
simulate_response_based_on(result)
```

---

## 示例工作流

### 完整会话示例

```
用户: 启动 Claude Code
Claude: [MCP Server 自动启动并加载]

用户: "帮我分析一下我的性格"
Claude: [调用 iami_query("性格特征")]
Claude: "根据你的记忆，你的性格特征是..."

用户: "这和我的价值观有什么关联？"
Claude: [调用 iami_query("价值观")]
Claude: "你的价值观主要体现在..."
Claude: "你的性格开放性和你对创新的重视相辅相成..."

用户: "查看我的人际关系"
Claude: [调用 iami_get_relationships()]
Claude: "你的主要人际关系包括..."

用户: "我的思想过去一年有什么变化？"
Claude: [调用 iami_get_timeline()]
Claude: "过去一年，你的思想主要在以下方面发生了变化..."
```

---

## 总结

IAMI GraphRAG 通过 MCP 与 Claude Code 无缝集成，提供：

✅ **自动化**: Claude 自动识别并调用相关工具
✅ **智能化**: 基于上下文选择最佳查询策略
✅ **便捷化**: 用户只需自然对话，无需学习命令
✅ **本地化**: 数据和索引完全本地存储
✅ **实时化**: 支持实时索引更新

开始使用：
1. 配置 `.claude/mcp.json`
2. 启动 Claude Code
3. 开始对话！

更多信息请参考：
- [README.md](./README.md) - 完整文档
- [QUICKSTART.md](./QUICKSTART.md) - 快速开始
- [DEPLOYMENT.md](./DEPLOYMENT.md) - 部署指南
