<div align="center">

# 🤖 SkillAgent

### Extensible Multimodal AI Skill Assistant

[中文](README.md) | **English**

[![License: MIT + Commons Clause](https://img.shields.io/badge/license-MIT%20%2B%20Commons%20Clause-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-FF6B35)

> Extend the agent with a new AI skill in three lines of code — the LLM calls it automatically.

</div>

---

## ✨ Why SkillAgent?

- **No vendor lock-in** — Switch between OpenAI / DeepSeek / Ollama with a single config line
- **Skills are plug-and-play** — Inherit `BaseSkill`, implement `execute()`, register in one line — done
- **Truly local knowledge base** — ChromaDB embedded vector store; [your data never leaves your machine](docs/knowledge-offline.md)
- **Multimodal out of the box** — Image understanding, voice input, PDF / Word / Excel parsing, all built in
- **Lightweight & deployable** — Use it as a CLI today, expose a FastAPI service tomorrow

---

## 🚀 Core Capabilities

| Capability | Description |
|-----------|-------------|
| 🧠 **LLM Abstraction** | OpenAI-compatible — GPT / DeepSeek / Ollama / Qwen seamlessly switchable |
| 🔧 **Skill System** | Class-based registration, auto-maps to Function Calling, 3-step extensibility |
| 🌐 **Web Search** | DuckDuckGo real-time search — free, no API key needed |
| 📰 **News Workflow** | Create a local live news timeline in one request, auto-refresh with AI summaries |
| 📊 **Git Summary** | Generate daily/weekly git commit summaries with repo/author filters |
| 🗄️ **Personal Knowledge Base** | ChromaDB semantic retrieval, fully local, data stays on device |
| 🖼️ **Image Understanding** | Upload local images or URLs, vision model analyzes content |
| 🎙️ **Voice Input** | Mic recording or audio upload — STT transcription then conversation |
| 📄 **Document Parsing** | PDF / Word / Excel / .eml one-click read, saveable to knowledge base |
| 🔮 **Entertainment Skills** | Chinese divination, tarot career reading, daily luck, almanac |
| 💬 **Conversation Persistence** | SQLite saves full history — context survives restarts |
| 🌍 **i18n** | GNU gettext, zero extra deps, switch language with one config line |

---

## ⚡ Quick Start

### Option A: One-command setup (recommended)

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

The script handles everything: `create .venv` → `install deps` → `register hi command` → `copy config` → `prompt for API key`.

---

### Option B: Manual install

<details>
<summary><b>Windows PowerShell</b></summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If you get a permissions error: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
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

> `pip install -e .` generates a `hi` command in `.venv/Scripts/`. Editable installs mean code changes take effect immediately — no reinstall needed.

---

## ⚙️ Configuration

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and pick your LLM:

<table>
<tr><th>Scenario</th><th>Config</th></tr>
<tr>
<td>OpenAI / compatible</td>
<td>

```yaml
llm:
  api_key: "sk-xxx"
  model: "gpt-4o-mini"
```
</td>
</tr>
<tr>
<td>🦙 Local Ollama</td>
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

### Run

```bash
python main.py          # Interactive CLI
python main.py server   # FastAPI server (port 8000)
```

---

## 💻 CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/reset` | Reset conversation history |
| `/skills` | List all registered skills |
| `/workflows` | List running local workflow services (e.g., news timelines) |
| `/image <path\|URL>` | 📷 Send image to vision model |
| `/voice [seconds]` | 🎙️ Record mic (default 5 s), transcribe via STT, then chat |
| `/doc <path\|URL>` | 📄 Read a document, optionally save to knowledge base |
| `/quit` | Exit |

**Image understanding**
```
You > /image C:\Users\you\Pictures\screenshot.png
Prompt > What errors can you see in this screenshot?
```

**Voice input**
```
You > /voice 8
[STT] Recording 8s - speak now...
```

**Document Q&A + save to KB**
```
You > /doc C:\reports\Q4_report.pdf
Question > What are the key conclusions?
Save to knowledge base? (y/N) > y
✓ Saved — Excel files are auto-split per sheet for accurate retrieval
```

> Supported formats: `.pdf` `.docx` `.xlsx` `.xls` `.eml` `.txt`

---

## 🌐 REST API

Start the server with `python main.py server`, then open `http://localhost:8000/docs` for the interactive Swagger UI.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Text conversation `{"message": "..."}` |
| POST | `/chat/image` | Vision chat — URL or base64 image |
| POST | `/chat/audio` | Upload audio file, returns transcription + reply |
| POST | `/upload/document` | Upload document, supports Q&A and saving to KB |
| GET | `/skills` | List registered skills |
| GET | `/workflows` | List running workflow services |
| DELETE | `/workflows/{name}` | Stop a specific workflow service |
| GET/POST/DELETE | `/knowledge` | Knowledge base CRUD |
| POST | `/chat/reset` | Reset conversation |
| GET | `/health` | Health check |

```bash
# Image understanding
curl -X POST http://localhost:8000/chat/image \
  -H "Content-Type: application/json" \
  -d '{"message": "What is in this image?", "image_url": "https://example.com/pic.jpg"}'

# Audio transcription + chat
curl -X POST http://localhost:8000/chat/audio \
  -F "file=@recording.mp3" -F "language=en"

# Document Q&A
curl -X POST http://localhost:8000/upload/document \
  -F "file=@report.pdf" -F "question=Key conclusions?" -F "save_to_knowledge=true"

# List running workflows
curl http://localhost:8000/workflows

# Stop a workflow
curl -X DELETE http://localhost:8000/workflows/news_AI_latest_news
```

---

## 📰 News Workflow (Auto Summary)

When you ask something like "Track the latest AI news", the agent can call `news_workflow` automatically to:

1. Fetch latest news items
2. Start a local timeline page on `127.0.0.1`
3. Refresh data on a configurable interval (for example every 60 minutes)
4. Generate an AI summary on each refresh (overview + key points + trend)

The page shows an AI summary card first, followed by a clickable news timeline.

---

## 🔧 Multimodal Configuration

Enable in `config.yaml` as needed:

```yaml
llm:
  vision_model: "gpt-4o"         # Vision model; falls back to llm.model if omitted

stt:
  engine: "openai"               # disabled | openai | dashscope
  openai_model: "whisper-1"
  language: "en"
  # engine: "dashscope"          # Alibaba Paraformer (high accuracy Chinese)
  # api_key: "your-dashscope-api-key"
```

**Install optional dependencies:**

```bash
pip install pypdf python-docx openpyxl xlrd   # Document parsing
pip install sounddevice soundfile             # Mic recording / audio decode
pip install dashscope                         # Alibaba Cloud STT
```

---

## 🧩 Extend with a Custom Skill: 3 Steps

The core design philosophy: **a skill is a module — write it and it works**.

### Step 1: Create the skill file

```python
# skills/my_skill.py
from skills.base import BaseSkill

class MySkill(BaseSkill):
    name = "my_skill"
    description = "Describe what this skill does — the LLM uses this to decide when to call it."
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"},
        },
        "required": ["param1"],
    }

    def execute(self, param1: str) -> str:
        return f"Result: {param1}"
```

### Step 2: Register the skill

```python
# core/agent.py → register_default_skills()
from skills.my_skill import MySkill
self.registry.register(MySkill())
```

### Step 3: Done 🎉

The LLM automatically discovers and invokes your skill at the right moment — no other changes needed.

---

## 🗂️ Project Structure

```
skillAgent/
├── main.py                  # Entry point (CLI + Server)
├── config.yaml              # Your config (git-ignored)
├── core/
│   ├── agent.py             # Agent orchestrator (LLM ⇄ Tool Calling loop)
│   ├── llm.py               # LLM client (text + vision)
│   ├── config.py            # Config loader
│   ├── context.py           # Conversation context
│   └── stt/                 # STT engine layer
│       ├── engine_openai.py     # OpenAI Whisper
│       └── engine_dashscope.py  # Alibaba Paraformer
├── skills/                  # Skill modules (freely extensible)
│   ├── base.py / registry.py
│   ├── web_search.py        # Web search
│   ├── document_skill.py    # Document parsing
│   ├── knowledge_skill.py   # Knowledge base management
│   ├── divination_skill.py  # Chinese divination
│   ├── tarot_career_skill.py
│   ├── lucky_today_skill.py
│   └── almanac_skill.py
├── knowledge/               # ChromaDB vector store
├── storage/                 # SQLite conversation history
├── api/server.py            # FastAPI REST service
├── locales/                 # i18n translation files
└── data/                    # Runtime data (auto-created)
```

---

## 🌍 Internationalization (i18n)

Built on Python's built-in `gettext` — **zero extra dependencies**.

```yaml
# config.yaml
language: en   # English
language: zh   # Chinese
```

**Add a new language (e.g. Japanese):**

1. Create `locales/ja/LC_MESSAGES/messages.po` and translate
2. Compile: `python scripts/compile_messages.py`
3. Set `language: ja`

**Mark strings as translatable in code:**
```python
from core.i18n import _
print(_("No search results found."))
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│              main.py  (CLI / API Server)             │
├──────────────────────────────────────────────────────┤
│                  core/agent.py                       │
│           Agent Orchestrator                         │
│      LLM ⇄ Tool Calling loop · multimodal routing    │
├─────────────┬──────────────┬────────────────────────┤
│   core/     │   skills/    │   knowledge/           │
│   llm.py    │  registry    │   ChromaDB             │
│   config    │  web_search  │   knowledge_manager    │
│   context   │  document    │                        │
│   stt/      │  datetime    │   storage/             │
│   tts/      │  divination  │   SQLite               │
├─────────────┴──────────────┴────────────────────────┤
│              api/server.py  (FastAPI REST)           │
│         text · image · audio · document · KB         │
└──────────────────────────────────────────────────────┘
```

---

## 📦 Tech Stack

| Component | Purpose |
|-----------|---------|
| **Python 3.11+** | Runtime |
| **OpenAI SDK** | LLM communication (compatible with any OpenAI-format API) |
| **ChromaDB** | Embedded vector database for local semantic search |
| **FastAPI + Uvicorn** | REST API server |
| **DuckDuckGo Search** | Free web search, no API key required |
| **SQLite** | Conversation history persistence |
| **Rich** | Beautiful terminal output |
| **pypdf / python-docx / openpyxl** | Document parsing (optional) |
| **sounddevice / soundfile** | Mic recording / audio decode (optional) |
| **dashscope** | Alibaba Cloud STT — high-accuracy Chinese ASR (optional) |

---

<div align="center">

Made with ❤️ · MIT + Commons Clause License

</div>
