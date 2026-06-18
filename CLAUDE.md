# Agency — AI 代运营 Agent

RAG 知识库 + 双重记忆 + Skill 插件的 AI Agent 框架。

## 项目结构

```
agent/
├── chat.py              # CLI 对话入口 (多 Session + 流式输出)
├── config.py            # 全局配置 (从 env/.env.develop 加载)
├── llm.py               # DeepSeek LLM 工厂 (LangChain)
├── graph.py             # LangGraph 编排 (3步运营 Agent + 工具循环)
├── rag.py               # RAG 引擎: 文本分割 → Embedding → pgvector 存储/检索
├── memory.py            # MemoryManager: 短期记忆(deque) + 长期记忆(pgvector)
├── session.py           # SessionManager: 多会话 CRUD + 消息持久化 + 语义搜索
├── test_rag.py          # RAG 管道测试 (7项)
├── skills_demo.py       # Skill 调用演示脚本
├── sample.txt           # 测试用文本
├── skills/
│   ├── __init__.py      # SkillRegistry 自动扫描注册中心
│   ├── base.py          # BaseSkill 抽象基类
│   └── demo/skill.py    # TextToolsSkill 示例技能
env/
└── .env.develop         # 环境变量 (API keys, PG 连接)
```

## 技术栈

| 能力 | 方案 |
|------|------|
| LLM | DeepSeek (`deepseek-v4-pro`), OpenAI 兼容 SDK |
| Embedding | 阿里云百炼 DashScope (`text-embedding-v4`, 1024d) |
| 向量存储 | PostgreSQL + pgvector (远端 47.120.17.107) |
| 文本分割 | LangChain `RecursiveCharacterTextSplitter` (chunk=256, overlap=50) |
| Agent 编排 | LangGraph (`StateGraph` + 条件路由) |
| 技能系统 | 自研 SkillRegistry + OpenAI Function Calling |

## 核心模块

### 1. RAG 引擎 (`rag.py`)

```python
from rag import RAG
rag = RAG(table_name="document_chunks", embedding_dim=1024)
rag.ingest_text(text, source_path="/path/to/file", dedup=True)
results = rag.search("查询", top_k=10)
```

- `embed()` 自动按每批 10 条分批调用百炼 API
- `ingest_text(dedup=True)` 默认先删除同 source_path 旧数据再写入
- `search()` 用 pgvector `<=>` 余弦相似度检索
- 预留 `ingest_image()` / `ingest_video()` 接口

### 2. 双重记忆 (`memory.py`)

```
短期: collections.deque (max 10轮, 20条消息)
  → 满时弹出最旧 2 轮
  → LLM 压缩为摘要 → 插回队列头部
  → LLM 提取结构化经验 → 重要性过滤(≥3) → 写入长期记忆

长期: pgvector agent_memories 表
  → 每条记忆包含 importance (1-10) + memory_type (preference/fact/decision/goal)
  → 检索时按余弦相似度 + 重要性展示
```

### 3. 会话管理 (`session.py`)

```
chat_sessions 表: id, title, created_at, updated_at
chat_messages 表: id, session_id, role, content, embedding(1024d), created_at

CLI 命令:
  /sessions   /new   /switch <id>   /delete <id>
  /history    /search <关键词>
```

每条消息自动向量化存入 `embedding` 列，`/search` 跨 session 语义检索。

### 4. Skill 系统 (`skills/`)

创建新技能 3 步:

```python
from skills.base import BaseSkill

class MySkill(BaseSkill):
    name = "my_skill"
    description = "一句话描述"

    def tool_spec(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": { ... }
            }
        }

    def execute(self, **kwargs) -> str:
        return "结果"

MY_SKILL = MySkill()  # 模块级实例, 注册中心自动发现
```

把 `.py` 文件放入 `skills/` 目录, `SkillRegistry.load_all()` 自动扫描加载。

### 5. Agent 工作流 (`graph.py`)

LangGraph 三步管道: `START → 意图分析 → 工具调度 ⇄ 工具执行 → 结果整合 → END`

- 最多 2 轮工具调用, 防死循环
- 工具: generate_content, analyze_data, brainstorm_ideas (依赖外部 tools.ops_agent)

## 数据库表 (PostgreSQL 47.120.17.107:5432/agency)

| 表名 | 用途 | 向量维度 |
|------|------|----------|
| `document_chunks` | RAG 知识库文档块 | 1024 |
| `test_chunks_16d` | 测试用 (截断到16维) | 16 |
| `agent_memories` | 长期记忆 | 1024 |
| `chat_sessions` | 会话列表 | - |
| `chat_messages` | 消息历史 + 向量 | 1024 |

## 运行

```bash
cd agent

# 对话(主入口)
python chat.py

# RAG 管道测试
python test_rag.py

# Skill 调用演示
python skills_demo.py

# 单次提问
python chat.py 什么是深度学习
```
