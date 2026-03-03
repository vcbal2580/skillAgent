# SkillAgent - Extensible AI Skill Assistant

[中文](README.md) | **English**

[![License: MIT + Commons Clause](https://img.shields.io/badge/license-MIT%20%2B%20Commons%20Clause-blue.svg)](LICENSE)

A lightweight, extensible AI skill assistant MVP powered by OpenAI Function Calling.
Supports web search, a personal knowledge base, custom skill plugins, plus
**image understanding, voice input, and document parsing** (multimodal).

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    main.py (CLI/Server)              │
├─────────────────────────────────────────────────────┤
│                   core/agent.py                      │
│              Agent Orchestrator                      │
│     (LLM ⇄ Tool Calling loop / multimodal routing)   │
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
│        FastAPI REST (text / image / audio / doc)     │
└─────────────────────────────────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **LLM abstraction** | OpenAI-compatible API — works with GPT, DeepSeek, Qwen, Ollama, etc. |
| **Skill system** | Register skills via class inheritance; auto-maps to Function Calling |
| **Entertainment skills** | Built-in divination, tarot career reading, daily luck, and almanac skills |
| **Knowledge base** | ChromaDB vector store for semantic retrieval of personal notes |
| **Web search** | DuckDuckGo search — free, no API key required |
| **Persistence** | SQLite conversation history |
| **API server** | FastAPI REST endpoints for GUI integration |
| **CLI** | Rich-powered interactive command-line interface |
| **Image understanding ★** | Send local images or URLs to a vision model for analysis |
| **Voice input ★** | Record mic or upload audio; STT transcribes to text then chats |
| **Document parsing ★** | Read PDF / Word / Excel; optionally save content to knowledge base |

## Quick Start

### Option A: One-command setup (recommended)

```bash
git clone <repo-url>
cd skillAgent
```

**Windows PowerShell:**
```powershell
.\scripts\setup.ps1
```

**macOS / Linux:**
```bash
bash scripts/setup.sh
```

The script handles everything: creates `.venv`, installs dependencies, registers the `hi` command, copies `config.example.yaml`, and reminds you to fill in your API key.

---

### Option B: Manual steps

```bash
git clone <repo-url>
cd skillAgent

python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Activate (Linux / macOS)
# source .venv/bin/activate

pip install -r requirements.txt
pip install -e .   # generates the hi command
```

> **How it works**: `pyproject.toml` defines `hi = "cli:main"` under `[project.scripts]`.
> `pip install -e .` generates `hi.exe` (Windows) or `hi` (Linux/macOS) inside `.venv/Scripts/`.
> Because it is an editable install, code changes take effect immediately — no reinstall needed.

### Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml and fill in your API key
```

Edit `config.yaml` to set your LLM provider:

```yaml
llm:
  provider: "openai"
  api_key: "sk-xxx"        # or set env var OPENAI_API_KEY
  model: "gpt-4o-mini"
```

**Using a local Ollama model:**
```yaml
llm:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "qwen2.5:7b"
```

**Using DeepSeek:**
```yaml
llm:
  base_url: "https://api.deepseek.com/v1"
  api_key: "sk-xxx"
  model: "deepseek-chat"
```

### 4. Run

**Interactive CLI (default):**
```bash
python main.py
```

**API server mode:**
```bash
python main.py server
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/reset` | Reset conversation history |
| `/skills` | List registered skills |
| `/quit` | Exit |
| `/image <path\|URL>` | Send an image to the vision model for analysis |
| `/voice [seconds]` | Record microphone (default 5 s), transcribe via STT, then chat |
| `/doc <path\|URL>` | Read a document (PDF/docx/xlsx), optionally save to knowledge base |

### `/image` example

```
You > /image C:\Users\you\Pictures\screenshot.png
Prompt (press Enter for default) > What errors can you see in this screenshot?
```

Public URLs also work:
```
You > /image https://example.com/chart.png
```

> Set a vision-capable model in `config.yaml`:
> ```yaml
> llm:
>   vision_model: "gpt-4o"   # or qwen-vl-plus, glm-4v, etc.
> ```

### `/voice` example

```
You > /voice 8
[STT] Recording 8s - speak now...
(Agent replies based on transcribed speech)
```

> Requires: `pip install sounddevice` and a configured STT engine (see Multimodal Config).

### `/doc` example

```
You > /doc C:\reports\Q4_report.pdf
Question (press Enter to summarize) > What are the key conclusions?
Save to knowledge base? (y/N) > y
Saved to knowledge base, ID: xxxx-xxxx
(Agent answers...)
```

- Supported formats: `.pdf`, `.docx`, `.xlsx`, `.txt`
- After saving with `y`, the document content can be semantically searched in future conversations

> Install format-specific deps:
> ```bash
> pip install pypdf          # PDF
> pip install python-docx   # Word
> pip install openpyxl      # Excel
> ```

## API Endpoints

Start the server with `python main.py server`, then:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a message `{"message": "..."}` |
| POST | `/chat/reset` | Reset conversation |
| POST | `/chat/image` | Vision chat `{"message": "...", "image_url": "<URL or base64>"}` |
| POST | `/chat/audio` | Upload audio file (multipart); STT then chat; returns `transcribed` + `reply` |
| POST | `/upload/document` | Upload document (multipart); optional `question` and `save_to_knowledge` params |
| GET | `/skills` | List registered skills |
| GET | `/knowledge` | List all knowledge entries |
| POST | `/knowledge` | Save knowledge `{"content": "...", "tags": [...]}` |
| DELETE | `/knowledge/{id}` | Delete a knowledge entry |
| GET | `/health` | Health check |

### `/chat/image` example

```bash
curl -X POST http://localhost:8000/chat/image \
  -H "Content-Type: application/json" \
  -d '{"message": "What is in this image?", "image_url": "https://example.com/pic.jpg"}'
```

### `/chat/audio` example

```bash
curl -X POST http://localhost:8000/chat/audio \
  -F "file=@recording.mp3" \
  -F "language=en"
# Returns: {"reply": "...", "transcribed": "recognised text"}
```

### `/upload/document` example

```bash
curl -X POST http://localhost:8000/upload/document \
  -F "file=@report.pdf" \
  -F "question=What are the key conclusions?" \
  -F "save_to_knowledge=true"
# Returns: {"text": "...", "reply": "...", "knowledge_id": "xxx"}
```

## Multimodal Configuration

Add these sections to `config.yaml`:

```yaml
llm:
  # Vision model for image understanding; falls back to llm.model if omitted
  vision_model: "gpt-4o"         # or qwen-vl-plus, glm-4v, etc.

stt:
  # STT engine: disabled | openai | dashscope
  engine: "openai"

  # OpenAI Whisper:
  openai_model: "whisper-1"      # default
  # api_key / base_url left blank to reuse llm.api_key / llm.base_url
  language: "en"                 # optional BCP-47 hint

  # Alibaba DashScope Paraformer:
  # engine: "dashscope"
  # api_key: "your-dashscope-api-key"
  # language: "zh"
```

### Optional multimodal dependencies

```bash
# Document parsing
pip install pypdf          # PDF
pip install python-docx   # Word .docx
pip install openpyxl      # Excel .xlsx

# Voice (mic recording + local audio file decode)
pip install sounddevice   # microphone recording
pip install soundfile     # local audio file decode (needed by dashscope local path)

# DashScope STT
pip install dashscope
```

## Adding a Custom Skill

Create a new skill in 3 steps:

### 1. Create `skills/my_skill.py`

```python
from skills.base import BaseSkill

class MySkill(BaseSkill):
    name = "my_skill"
    description = "Describe what this skill does — the LLM uses this to decide when to call it."
    parameters = {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of the parameter",
            },
        },
        "required": ["param1"],
    }

    def execute(self, param1: str) -> str:
        # Implement your logic here
        return f"Result: {param1}"
```

### 2. Register the skill

In `core/agent.py`, inside `register_default_skills()`:

```python
from skills.my_skill import MySkill
self.registry.register(MySkill())
```

### 3. Done!

The LLM will automatically recognise and invoke your new skill at the right moment.

## Project Structure

```
skillAgent/
├── main.py                   # Entry point (CLI + Server)
├── config.example.yaml       # Config template (commit this)
├── config.yaml               # Your local config (git-ignored)
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Package metadata & console script
├── core/
│   ├── agent.py              # Agent orchestrator (multimodal routing)
│   ├── llm.py                # LLM client (text + vision)
│   ├── config.py             # Config loader
│   ├── context.py            # Conversation context manager
│   ├── i18n.py               # GNU gettext wrapper
│   ├── prompt_loader.py      # Per-language YAML prompt overlay
│   ├── stt/                  # Speech-To-Text engine layer ★
│   │   ├── __init__.py       # Factory: get_stt_engine()
│   │   ├── engine_disabled.py
│   │   ├── engine_openai.py  # OpenAI Whisper
│   │   └── engine_dashscope.py # Alibaba Paraformer
│   └── tts/                  # Text-To-Speech engine layer
├── knowledge/
│   ├── vector_store.py       # ChromaDB vector store
│   └── knowledge_manager.py  # Knowledge CRUD
├── skills/
│   ├── base.py               # BaseSkill abstract class
│   ├── registry.py           # Skill registry
│   ├── web_search.py         # Web search (DuckDuckGo)
│   ├── knowledge_skill.py    # Knowledge base management
│   ├── datetime_skill.py     # Date / time utility
│   ├── document_skill.py     # Document parsing (PDF/docx/xlsx) ★
│   ├── divination_skill.py   # Chinese stems/branches divination
│   ├── tarot_career_skill.py # Tarot career reading
│   ├── lucky_today_skill.py  # Daily luck generator
│   └── almanac_skill.py      # Chinese almanac / 黄历
├── storage/
│   └── database.py           # SQLite conversation storage
├── api/
│   └── server.py             # FastAPI REST API (incl. multimodal endpoints) ★
├── prompts/
│   ├── en.yaml               # English LLM-facing skill prompts
│   └── zh.yaml               # Chinese LLM-facing skill prompts
├── locales/
│   └── zh/LC_MESSAGES/
│       ├── messages.po       # Chinese UI translations
│       └── messages.mo       # Compiled binary
├── scripts/
│   └── compile_messages.py   # Pure-Python .po → .mo compiler
└── data/                     # Runtime data (auto-created, git-ignored)
    ├── chromadb/             # Vector database
    └── agent.db              # SQLite database
```

## Internationalization (i18n)

The project uses GNU gettext for UI strings with **zero extra dependencies** (Python's built-in `gettext` module), plus per-language YAML files for LLM-facing prompts that can be tuned independently per language.

### Switch language

Edit `config.yaml`:
```yaml
language: zh   # Chinese (default)
language: en   # English (falls back to msgid originals)
```

### Two-layer i18n design

| Layer | Mechanism | Files | Purpose |
|-------|-----------|-------|---------|
| UI strings | GNU gettext | `locales/<lang>/LC_MESSAGES/messages.po/.mo` | CLI output, error messages, labels |
| LLM prompts | YAML overlay | `prompts/<lang>.yaml` | Skill descriptions sent to the LLM — tunable per language |

### Add a new language (e.g. Japanese)

1. Create `locales/ja/LC_MESSAGES/messages.po` — translate the `msgstr` fields
2. Create `prompts/ja.yaml` — tune the LLM-facing skill descriptions
3. Compile:
   ```bash
   python scripts/compile_messages.py
   ```
4. Set `language: ja` in `config.yaml`

### Mark translatable strings in code

```python
from core.i18n import _
print(_("No search results found."))   # automatically uses active language
```

## Tech Stack

- **Python 3.11+**
- **OpenAI Python SDK** — LLM communication
- **ChromaDB** — local vector database
- **FastAPI + Uvicorn** — REST API server
- **Rich** — CLI formatting
- **DuckDuckGo Search (`ddgs`)** — free web search
- **PyYAML** — prompt YAML loading
- **SQLite** (stdlib) — conversation history
- **gettext** (stdlib) — internationalisation
- **pypdf / python-docx / openpyxl** — document parsing (optional)
- **sounddevice / soundfile** — mic recording / audio decode (optional)
- **dashscope** — Alibaba Cloud STT (optional)
