# SkillAgent - 可扩展智能技能助手

**中文** | [English](README.en.md)

[![License: MIT + Commons Clause](https://img.shields.io/badge/license-MIT%20%2B%20Commons%20Clause-blue.svg)](LICENSE)

一个轻量级、可扩展的 AI 技能助手 MVP，基于 OpenAI Function Calling 驱动，支持联网搜索、个人知识库、自定义技能扩展，以及**图像理解、语音输入、文档解析**等多模态能力。

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    main.py (CLI/Server)              │
├─────────────────────────────────────────────────────┤
│                   core/agent.py                      │
│              Agent Orchestrator                      │
│    (LLM ⇄ Tool Calling 循环 / 多模态调度)            │
├──────────┬──────────────┬───────────────────────────┤
│ core/    │   skills/    │   knowledge/              │
│ llm.py   │  registry.py │   vector_store.py         │
│ context  │  base.py     │   knowledge_manager.py    │
│ config   │  web_search  │                           │
│ stt/     │  knowledge   │   storage/                │
│ tts/     │  datetime    │   database.py (SQLite)    │
│          │  document ★  │                           │
├──────────┴──────────────┴───────────────────────────┤
│                   api/server.py                      │
│     FastAPI REST（文本 / 图像 / 音频 / 文档）         │
└─────────────────────────────────────────────────────┘
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **LLM 抽象** | OpenAI 兼容接口，支持 GPT / DeepSeek / Ollama 等 |
| **技能系统** | 装饰器模式注册，自动映射 Function Calling |
| **命理娱乐技能** | 内置天干地支八卦卜算、塔罗事业解读、今日好运、黄历技能 |
| **知识库** | ChromaDB 向量存储，语义检索个人知识 |
| **联网搜索** | DuckDuckGo 免费搜索，无需 API Key |
| **持久化** | SQLite 保存对话历史 |
| **API 服务** | FastAPI REST 接口，为 GUI 预留 |
| **CLI** | Rich 美化的交互式命令行 |
| **图像理解 ★** | 上传本地图片或 URL，视觉模型分析内容 |
| **语音输入 ★** | 麦克风录音或上传音频文件，STT 转文字后对话 |
| **文档解析 ★** | 读取 PDF / Word / Excel，可存入知识库 |

## 快速开始

### 方式一：一键初始化（推荐）

```bash
git clone <repo-url>
cd skillAgent
```

**Windows PowerShell：**
```powershell
.\scripts\setup.ps1
```

**macOS / Linux：**
```bash
bash scripts/setup.sh
```

脚本会自动完成：创建 `.venv` → 安装依赖 → 注册 `hi` 命令 → 复制 `config.example.yaml` → 提示填写 API Key。

---

### 方式二：手动步骤

**Windows PowerShell：**
```powershell
git clone <repo-url>
cd skillAgent

python -m venv .venv

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1
# 如果提示"无法加载脚本"权限错误，先执行：
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

pip install -r requirements.txt
pip install -e .   # 生成 hi 命令
```

**macOS / Linux：**
```bash
git clone <repo-url>
cd skillAgent

python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .   # 生成 hi 命令
```

> **原理**：`pyproject.toml` 的 `[project.scripts]` 定义了 `hi = "cli:main"`，
> `pip install -e .` 在 `.venv/Scripts/` 生成 `hi.exe`（Windows）或 `hi`（Linux/macOS）。
> editable 模式下修改代码无需重新安装。

### 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入 API Key
```

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

### 4. 运行

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
| `/image <路径或URL>` | 发送图片，视觉模型理解并回复 |
| `/voice [秒数]` | 麦克风录音（默认 5 秒），STT 转文字后对话 |
| `/doc <路径或URL>` | 读取文档（PDF/docx/xlsx），可选存入知识库 |

### `/image` 使用示例

```
You > /image C:\Users\你\Pictures\screenshot.png
Prompt (press Enter for default) > 这张截图里有什么错误信息？
```

也支持公开 URL：
```
You > /image https://example.com/chart.png
```

> 需要在 `config.yaml` 中设置视觉模型：
> ```yaml
> llm:
>   vision_model: "qwen-vl-plus"   # 或 gpt-4o、glm-4v 等
> ```

### `/voice` 使用示例

```
You > /voice 8
[STT] Recording 8s - speak now...
（Agent 根据语音内容回复）
```

> 需要安装：`pip install sounddevice`，并在 `config.yaml` 配置 STT 引擎（见「多模态配置」）。

### `/doc` 使用示例

```
You > /doc F:\reports\Q4财务报告.pdf
Question (press Enter to summarize) > 核心结论是什么？
Save to knowledge base? (y/N) > y
已存入知识库，ID: xxxx-xxxx
（Agent 回答…）
```

- 支持格式：`.pdf`、`.docx`、`.xlsx`、`.txt`
- 输入 `y` 存入知识库后，后续对话可直接语义检索该文档内容

> 需要安装对应依赖：
> ```bash
> pip install pypdf          # PDF
> pip install python-docx   # Word
> pip install openpyxl      # Excel
> ```

## API 接口

启动 `python main.py server` 后：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 发送消息 `{"message": "..."}` |
| POST | `/chat/reset` | 重置对话 |
| POST | `/chat/image` | 图像对话 `{"message": "...", "image_url": "<URL或base64>"}` |
| POST | `/chat/audio` | 上传音频文件（multipart），STT 后对话，返回转写文本和回复 |
| POST | `/upload/document` | 上传文档（multipart），可附带 `question` 和 `save_to_knowledge` 参数 |
| GET | `/skills` | 获取技能列表 |
| GET | `/knowledge` | 获取所有知识 |
| POST | `/knowledge` | 保存知识 `{"content": "...", "tags": [...]}` |
| DELETE | `/knowledge/{id}` | 删除知识 |
| GET | `/health` | 健康检查 |

### `/chat/image` 示例

```bash
curl -X POST http://localhost:8000/chat/image \
  -H "Content-Type: application/json" \
  -d '{"message": "这张图里有什么？", "image_url": "https://example.com/pic.jpg"}'
```

### `/chat/audio` 示例

```bash
curl -X POST http://localhost:8000/chat/audio \
  -F "file=@recording.mp3" \
  -F "language=zh"
# 返回: {"reply": "...", "transcribed": "识别出的文字"}
```

### `/upload/document` 示例

```bash
curl -X POST http://localhost:8000/upload/document \
  -F "file=@report.pdf" \
  -F "question=核心结论是什么？" \
  -F "save_to_knowledge=true"
# 返回: {"text": "...", "reply": "...", "knowledge_id": "xxx"}
```

## 多模态配置

在 `config.yaml` 中添加以下配置：

```yaml
llm:
  # 视觉模型（图片理解），不设置默认复用 llm.model
  vision_model: "qwen-vl-plus"   # 或 gpt-4o、glm-4v 等

stt:
  # 语音识别引擎: disabled | openai | dashscope
  engine: "openai"

  # OpenAI Whisper：
  openai_model: "whisper-1"      # 默认
  # api_key / base_url 留空则复用 llm.api_key / llm.base_url
  language: "zh"                 # 可选 BCP-47 语言提示

  # 阿里云 DashScope Paraformer：
  # engine: "dashscope"
  # api_key: "your-dashscope-api-key"
  # language: "zh"
```

### 多模态可选依赖

```bash
# 文档解析
pip install pypdf          # PDF
pip install python-docx   # Word .docx
pip install openpyxl      # Excel .xlsx

# 语音（麦克风录音 + 本地音频文件解码）
pip install sounddevice   # 麦克风录音
pip install soundfile     # 本地音频文件解码（dashscope 本地文件转写需要）

# DashScope STT
pip install dashscope
```

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
│   ├── agent.py             # Agent 编排器（含多模态调度）
│   ├── llm.py               # LLM 客户端（文本 + 视觉）
│   ├── config.py            # 配置管理
│   ├── context.py           # 对话上下文管理
│   ├── stt/                 # 语音识别引擎层 ★
│   │   ├── __init__.py      # 工厂函数 get_stt_engine()
│   │   ├── engine_disabled.py
│   │   ├── engine_openai.py # OpenAI Whisper
│   │   └── engine_dashscope.py # 阿里云 Paraformer
│   └── tts/                 # 语音合成引擎层
├── knowledge/
│   ├── vector_store.py      # ChromaDB 向量存储
│   └── knowledge_manager.py # 知识 CRUD
├── skills/
│   ├── base.py              # 技能基类
│   ├── registry.py          # 技能注册中心
│   ├── web_search.py        # 联网搜索技能
│   ├── knowledge_skill.py   # 知识管理技能
│   ├── datetime_skill.py    # 日期时间技能
│   ├── document_skill.py    # 文档解析技能 ★
│   ├── divination_skill.py  # 天干地支/八卦卜算
│   ├── tarot_career_skill.py# 塔罗事业解读
│   ├── lucky_today_skill.py # 今日好运
│   └── almanac_skill.py     # 黄历宜忌
├── storage/
│   └── database.py          # SQLite 对话存储
├── api/
│   └── server.py            # FastAPI REST API（含多模态接口）★
└── data/                    # 运行时数据 (自动创建)
    ├── chromadb/             # 向量数据库
    └── agent.db              # SQLite 数据库
```

## 国际化 / Internationalization (i18n)

本项目使用 GNU gettext 标准方案实现多语言支持，**零额外依赖**（Python 内置 `gettext` 模块）。

### 切换语言

编辑 `config.yaml`：
```yaml
language: zh   # 中文（默认）
language: en   # English（回退到 msgid 英文原文）
```

### 目录结构

```
locales/
└── zh/
    └── LC_MESSAGES/
        ├── messages.po   # 可编辑翻译源文件
        └── messages.mo   # 编译后的二进制（已预编译提交）
```

### 添加新语言

1. 复制并新建语言目录，例如 `locales/ja/LC_MESSAGES/messages.po`
2. 翻译 `msgstr` 字段
3. 编译：
   ```bash
   python scripts/compile_messages.py
   ```
4. 在 `config.yaml` 中设置 `language: ja`

### 在代码中标记可翻译字符串

```python
from core.i18n import _
print(_("No search results found."))   # 自动对应当前语言
```

---

## 技术栈

- **Python 3.11+**
- **OpenAI SDK** - LLM 调用 (兼容任何 OpenAI API 格式)
- **ChromaDB** - 嵌入式向量数据库
- **DuckDuckGo Search** - 免费网页搜索
- **FastAPI + Uvicorn** - REST API 服务
- **SQLite** - 对话历史持久化
- **Rich** - 终端美化
- **pypdf / python-docx / openpyxl** - 文档解析（可选）
- **sounddevice / soundfile** - 麦克风录音 / 音频解码（可选）
- **dashscope** - 阿里云 STT（可选）
