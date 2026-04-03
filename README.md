<div align="center">

# 🤖 SkillAgent

### 可扩展的多模态 AI 技能助手

**English** | [Chinese](README.zh.md)

[![License: MIT + Commons Clause](https://img.shields.io/badge/license-MIT%20%2B%20Commons%20Clause-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-FF6B35)

> 用三行代码扩展一个新 AI 技能，让 LLM 自动在合适时机调用它。

</div>

---

## ✨ 为什么选择 SkillAgent？

- **零门槛接入任意 LLM** — OpenAI / DeepSeek / Ollama 一行配置切换，不锁定厂商
- **技能即插即用** — 继承 `BaseSkill`、写 `execute()`，注册一行，Agent 自动发现并调用
- **真正的本地知识库** — ChromaDB 嵌入式向量存储，[数据永不上云](docs/knowledge-offline.md)
- **多模态开箱即用** — 图片理解、语音输入、PDF / Word / Excel 文档解析，全部内置
- **轻量可部署** — CLI 直接用，FastAPI 服务一键启动，无需复杂基础设施

---

## 🚀 核心能力

| 能力 | 说明 |
|------|------|
| 🧠 **LLM 抽象** | OpenAI 兼容接口，GPT / DeepSeek / Ollama 等无缝切换 |
| 🔧 **技能系统** | 装饰器注册，自动映射 Function Calling，3 步扩展新技能 |
| 🌐 **联网搜索** | DuckDuckGo 免费实时搜索，无需任何 API Key |
| 📰 **新闻工作流** | 一句话创建本地新闻时间轴服务，定时自动刷新并生成 AI 总结 |
| 📊 **Git 提交总结** | 一键汇总日报/周报，可按作者和仓库过滤提交记录 |
| 🗄️ **个人知识库** | ChromaDB 向量语义检索，完全本地，数据不离机 |
| 🖼️ **图像理解** | 上传本地图片或 URL，多模态视觉模型分析 |
| 🎙️ **语音输入** | 麦克风录音 / 上传音频，STT 转文字后自动对话 |
| 📄 **文档解析** | PDF / Word / Excel / .eml 一键读取，可存入知识库 |
| 🔮 **命理娱乐** | 天干地支卜算、塔罗事业解读、今日好运、黄历宜忌 |
| 💬 **对话持久化** | SQLite 保存完整历史，重启不丢上下文 |
| 🌍 **多语言 i18n** | GNU gettext，零依赖，配置一行切换中英文 |

---

## ⚡ 快速开始

### 方式一：一键初始化（推荐）

```bash
git clone <repo-url>
cd skillAgent
```

<details open>
<summary><b>Windows PowerShell</b></summary>

```powershell
.\scripts\setup.ps1
```
</details>

<details>
<summary><b>macOS / Linux</b></summary>

```bash
bash scripts/setup.sh
```
</details>

脚本自动完成：`创建 .venv` → `安装依赖` → `注册 hi 命令` → `复制配置文件` → `提示填写 API Key`，一步到位。

---

### 方式二：手动安装

<details>
<summary><b>Windows PowerShell</b></summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# 若出现权限错误：Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pip install -r requirements.txt
pip install -e .
```
</details>

<details>
<summary><b>macOS / Linux</b></summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```
</details>

> `pip install -e .` 会在 `.venv/Scripts/` 生成 `hi` 命令，editable 模式修改代码后无需重新安装。

---

## ⚙️ 配置

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml` 选择你的 LLM：

<table>
<tr><th>场景</th><th>配置示例</th></tr>
<tr>
<td>OpenAI / 兼容接口</td>
<td>

```yaml
llm:
  api_key: "sk-xxx"
  model: "gpt-4o-mini"
```
</td>
</tr>
<tr>
<td>🦙 Ollama 本地模型</td>
<td>

```yaml
llm:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "qwen2.5:7b"
```
</td>
</tr>
<tr>
<td>DeepSeek</td>
<td>

```yaml
llm:
  base_url: "https://api.deepseek.com/v1"
  api_key: "sk-xxx"
  model: "deepseek-chat"
```
</td>
</tr>
</table>

### 启动

```bash
python main.py          # CLI 交互模式
python main.py server   # FastAPI 服务模式（端口 8000）
```

---

## 💻 CLI 命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/reset` | 重置对话历史 |
| `/skills` | 查看已注册的所有技能 |
| `/workflows` | 查看运行中的本地工作流服务（如新闻时间轴） |
| `/image <路径或URL>` | 📷 发送图片，视觉模型解析内容 |
| `/voice [秒数]` | 🎙️ 麦克风录音（默认 5 秒），语音转文字后对话 |
| `/doc <路径或URL>` | 📄 读取文档并可存入个人知识库 |
| `/quit` | 退出 |

**示例：图像理解**
```
You > /image C:\Users\你\Pictures\screenshot.png
Prompt > 这张截图里有什么错误信息？
```

**示例：语音输入**
```
You > /voice 8
[STT] Recording 8s - speak now...
```

**示例：文档问答 + 存库**
```
You > /doc F:\reports\Q4财务报告.pdf
Question > 核心结论是什么？
Save to knowledge base? (y/N) > y
✓ 已存入知识库，Excel 自动按 Sheet 切分为独立条目
```

> 支持格式：`.pdf` `.docx` `.xlsx` `.xls` `.eml` `.txt`

---

## 🌐 REST API

启动 `python main.py server` 后访问 `http://localhost:8000/docs` 查看交互式文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 文本对话 `{"message": "..."}` |
| POST | `/chat/image` | 图像对话，传入 URL 或 base64 |
| POST | `/chat/audio` | 上传音频文件，返回转写文本和回复 |
| POST | `/upload/document` | 上传文档，支持问答和存入知识库 |
| GET | `/skills` | 获取技能列表 |
| GET | `/workflows` | 获取运行中的工作流服务列表 |
| DELETE | `/workflows/{name}` | 停止指定工作流服务 |
| GET/POST/DELETE | `/knowledge` | 知识库 CRUD |
| POST | `/chat/reset` | 重置对话 |
| GET | `/health` | 健康检查 |

```bash
# 图像理解
curl -X POST http://localhost:8000/chat/image \
  -H "Content-Type: application/json" \
  -d '{"message": "这张图里有什么？", "image_url": "https://example.com/pic.jpg"}'

# 音频转写 + 对话
curl -X POST http://localhost:8000/chat/audio \
  -F "file=@recording.mp3" -F "language=zh"

# 文档问答
curl -X POST http://localhost:8000/upload/document \
  -F "file=@report.pdf" -F "question=核心结论？" -F "save_to_knowledge=true"

# 查看运行中的工作流
curl http://localhost:8000/workflows

# 停止指定工作流
curl -X DELETE http://localhost:8000/workflows/news_AI最新新闻
```

---

## 📰 新闻工作流（自动总结）

当你说「我想追踪 AI 最新新闻」时，Agent 会自动调用 `news_workflow` 技能：

1. 抓取最新新闻
2. 启动本地时间轴页面（`127.0.0.1`）
3. 按设定间隔自动刷新（例如每 60 分钟）
4. 每次刷新后自动生成「总览 + 要点 + 趋势」AI 总结

在页面中你会先看到 AI 总结卡片，再看到可点击原文链接的新闻时间轴。

---

## 🔧 多模态配置

在 `config.yaml` 中按需开启：

```yaml
llm:
  vision_model: "qwen-vl-plus"   # 视觉模型，留空则复用主模型

stt:
  engine: "openai"               # disabled | openai | dashscope
  openai_model: "whisper-1"
  language: "zh"
  # engine: "dashscope"          # 阿里云 Paraformer（高精度中文）
  # api_key: "your-dashscope-api-key"
```

**按需安装可选依赖：**

```bash
pip install pypdf python-docx openpyxl xlrd   # 文档解析
pip install sounddevice soundfile             # 语音录制 / 解码
pip install dashscope                         # 阿里云 STT
```

---

## 🧩 扩展技能：3 步接入

SkillAgent 的核心设计理念：**技能即模块，写完即生效**。

### 第一步：新建技能文件

```python
# skills/my_skill.py
from skills.base import BaseSkill

class MySkill(BaseSkill):
    name = "my_skill"
    description = "描述这个技能做什么 —— LLM 根据此决定何时调用它"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数说明"},
        },
        "required": ["param1"],
    }

    def execute(self, param1: str) -> str:
        return f"结果: {param1}"
```

### 第二步：注册到 Agent

```python
# core/agent.py → register_default_skills()
from skills.my_skill import MySkill
self.registry.register(MySkill())
```

### 第三步：完成 🎉

LLM 会自动识别新技能并在合适时机调用它，无需任何其他改动。

---

## 🗂️ 项目结构

```
skillAgent/
├── main.py                  # 入口（CLI + Server）
├── config.yaml              # 配置文件
├── core/
│   ├── agent.py             # Agent 编排器（LLM ⇄ Tool Calling 循环）
│   ├── llm.py               # LLM 客户端（文本 + 视觉）
│   ├── config.py            # 配置管理
│   ├── context.py           # 对话上下文
│   └── stt/                 # 语音识别引擎层
│       ├── engine_openai.py     # OpenAI Whisper
│       └── engine_dashscope.py  # 阿里云 Paraformer
├── skills/                  # 技能模块（可自由扩展）
│   ├── base.py / registry.py
│   ├── web_search.py        # 联网搜索
│   ├── document_skill.py    # 文档解析
│   ├── knowledge_skill.py   # 知识库管理
│   ├── divination_skill.py  # 八卦卜算
│   ├── tarot_career_skill.py
│   ├── lucky_today_skill.py
│   └── almanac_skill.py
├── knowledge/               # ChromaDB 向量存储
├── storage/                 # SQLite 对话历史
├── api/server.py            # FastAPI REST 服务
├── locales/                 # i18n 翻译文件
└── data/                    # 运行时数据（自动创建）
```

---

## 🌍 多语言支持（i18n）

基于 Python 内置 `gettext`，**零额外依赖**。

```yaml
# config.yaml
language: zh   # 中文
language: en   # English
```

**添加新语言（以日语为例）：**

1. 新建 `locales/ja/LC_MESSAGES/messages.po` 并翻译
2. 编译：`python scripts/compile_messages.py`
3. 设置 `language: ja`

**在代码中标记可翻译字符串：**
```python
from core.i18n import _
print(_("No search results found."))
```

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────┐
│              main.py  (CLI / API Server)             │
├──────────────────────────────────────────────────────┤
│                  core/agent.py                       │
│           Agent Orchestrator                         │
│     LLM ⇄ Tool Calling 循环 · 多模态调度             │
├─────────────┬──────────────┬────────────────────────┤
│   core/     │   skills/    │   knowledge/           │
│   llm.py    │  registry    │   ChromaDB             │
│   config    │  web_search  │   knowledge_manager    │
│   context   │  document    │                        │
│   stt/      │  datetime    │   storage/             │
│   tts/      │  divination  │   SQLite               │
├─────────────┴──────────────┴────────────────────────┤
│              api/server.py  (FastAPI REST)           │
│       文本 · 图像 · 音频 · 文档 · 知识库              │
└──────────────────────────────────────────────────────┘
```

---

## 📦 技术栈

| 组件 | 用途 |
|------|------|
| **Python 3.11+** | 运行环境 |
| **OpenAI SDK** | LLM 调用（兼容任何 OpenAI API 格式） |
| **ChromaDB** | 嵌入式向量数据库，本地语义检索 |
| **FastAPI + Uvicorn** | REST API 服务 |
| **DuckDuckGo Search** | 免费联网搜索，无需 API Key |
| **SQLite** | 对话历史持久化 |
| **Rich** | 终端美化输出 |
| **pypdf / python-docx / openpyxl** | 文档解析（可选） |
| **sounddevice / soundfile** | 麦克风录音 / 音频解码（可选） |
| **dashscope** | 阿里云 STT，高精度中文语音识别（可选） |

---

<div align="center">

Made with ❤️ · MIT + Commons Clause License

</div>
