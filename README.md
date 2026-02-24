# SkillAgent - 可扩展智能技能助手

一个轻量级、可扩展的 AI 技能助手 MVP，基于 OpenAI Function Calling 驱动，支持联网搜索、个人知识库、自定义技能扩展。

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    main.py (CLI/Server)              │
├─────────────────────────────────────────────────────┤
│                   core/agent.py                      │
│              Agent Orchestrator                      │
│         (LLM ⇄ Tool Calling 循环)                    │
├──────────┬──────────────┬───────────────────────────┤
│ core/    │   skills/    │   knowledge/              │
│ llm.py   │  registry.py │   vector_store.py         │
│ context  │  base.py     │   knowledge_manager.py    │
│ config   │  web_search  │                           │
│          │  knowledge   │   storage/                │
│          │  datetime    │   database.py (SQLite)    │
├──────────┴──────────────┴───────────────────────────┤
│                   api/server.py                      │
│               FastAPI REST (for GUI)                 │
└─────────────────────────────────────────────────────┘
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **LLM 抽象** | OpenAI 兼容接口，支持 GPT / DeepSeek / Ollama 等 |
| **技能系统** | 装饰器模式注册，自动映射 Function Calling |
| **知识库** | ChromaDB 向量存储，语义检索个人知识 |
| **联网搜索** | DuckDuckGo 免费搜索，无需 API Key |
| **持久化** | SQLite 保存对话历史 |
| **API 服务** | FastAPI REST 接口，为 GUI 预留 |
| **CLI** | Rich 美化的交互式命令行 |

## 快速开始

### 1. 安装依赖

```bash
cd f:\aiagent
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，设置 LLM API：

```yaml
llm:
  provider: "openai"
  api_key: "sk-xxx"        # 或设置环境变量 OPENAI_API_KEY
  base_url: ""              # 自定义API地址(Ollama等)
  model: "gpt-4o-mini"
```

**使用 Ollama 本地模型：**
```yaml
llm:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "qwen2.5:7b"
```

**使用 DeepSeek：**
```yaml
llm:
  base_url: "https://api.deepseek.com/v1"
  api_key: "sk-xxx"
  model: "deepseek-chat"
```

### 3. 运行

**CLI 交互模式（默认）：**
```bash
python main.py
```

**API 服务器模式：**
```bash
python main.py server
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/reset` | 重置对话历史 |
| `/skills` | 显示已注册技能 |
| `/quit` | 退出 |

## API 接口

启动 `python main.py server` 后：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 发送消息 `{"message": "..."}` |
| POST | `/chat/reset` | 重置对话 |
| GET | `/skills` | 获取技能列表 |
| GET | `/knowledge` | 获取所有知识 |
| POST | `/knowledge` | 保存知识 `{"content": "...", "tags": [...]}` |
| DELETE | `/knowledge/{id}` | 删除知识 |
| GET | `/health` | 健康检查 |

## 扩展技能

创建新技能只需 3 步：

### 1. 创建技能文件 `skills/my_skill.py`

```python
from skills.base import BaseSkill

class MySkill(BaseSkill):
    name = "my_skill"
    description = "描述这个技能做什么，LLM 会根据此决定何时调用"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "参数说明",
            },
        },
        "required": ["param1"],
    }

    def execute(self, param1: str) -> str:
        # 实现你的逻辑
        return f"结果: {param1}"
```

### 2. 注册技能

在 `core/agent.py` 的 `register_default_skills()` 中添加：

```python
from skills.my_skill import MySkill
self.registry.register(MySkill())
```

### 3. 完成！

LLM 会自动识别并在合适时机调用你的新技能。

## 项目结构

```
aiagent/
├── main.py                  # 入口 (CLI + Server)
├── config.yaml              # 配置文件
├── requirements.txt         # Python 依赖
├── core/
│   ├── agent.py             # Agent 编排器
│   ├── llm.py               # LLM 客户端抽象
│   ├── config.py            # 配置管理
│   └── context.py           # 对话上下文管理
├── knowledge/
│   ├── vector_store.py      # ChromaDB 向量存储
│   └── knowledge_manager.py # 知识 CRUD
├── skills/
│   ├── base.py              # 技能基类
│   ├── registry.py          # 技能注册中心
│   ├── web_search.py        # 联网搜索技能
│   ├── knowledge_skill.py   # 知识管理技能
│   └── datetime_skill.py    # 日期时间技能
├── storage/
│   └── database.py          # SQLite 对话存储
├── api/
│   └── server.py            # FastAPI REST API
└── data/                    # 运行时数据 (自动创建)
    ├── chromadb/             # 向量数据库
    └── agent.db              # SQLite 数据库
```

## 技术栈

- **Python 3.11+**
- **OpenAI SDK** - LLM 调用 (兼容任何 OpenAI API 格式)
- **ChromaDB** - 嵌入式向量数据库
- **DuckDuckGo Search** - 免费网页搜索
- **FastAPI + Uvicorn** - REST API 服务
- **SQLite** - 对话历史持久化
- **Rich** - 终端美化
