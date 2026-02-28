# SkillAgent - Extensible AI Skill Assistant

[中文](README.md) | **English**

A lightweight, extensible AI skill assistant MVP powered by OpenAI Function Calling.
Supports web search, a personal knowledge base, and custom skill plugins.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    main.py (CLI/Server)              │
├─────────────────────────────────────────────────────┤
│                   core/agent.py                      │
│              Agent Orchestrator                      │
│           (LLM ⇄ Tool Calling loop)                  │
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

## Features

| Feature | Description |
|---------|-------------|
| **LLM abstraction** | OpenAI-compatible API — works with GPT, DeepSeek, Qwen, Ollama, etc. |
| **Skill system** | Register skills via class inheritance; auto-maps to Function Calling |
| **Entertainment skills** | Built-in divination, tarot career reading, daily luck, and almanac skills |
| **Knowledge base** | ChromaDB vector store for semantic retrieval of personal notes |
| **Web search** | DuckDuckGo search — free, no API key required |
| **Persistence** | SQLite conversation history |
| **API server** | FastAPI REST endpoints for future GUI integration |
| **CLI** | Rich-powered interactive command-line interface |

## Quick Start

### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd skillAgent

# Create a virtual environment (recommended)
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Activate (Linux / macOS)
# source .venv/bin/activate
```

### 2. Install dependencies & register the `hi` command

```bash
# Install third-party dependencies
pip install -r requirements.txt

# Install the project in editable mode ← this generates hi.exe in .venv/Scripts/
pip install -e .
```

> **How it works**: `pyproject.toml` defines `hi = "cli:main"` under `[project.scripts]`.
> Running `pip install -e .` generates `hi.exe` (Windows) or `hi` (Linux/macOS) inside the
> active virtual environment. Because it is an editable install, `hi` always points to
> `cli.py` in the repository — no reinstall needed after code changes.

After installation, use the `hi` command anywhere (while the venv is active):

```bash
hi vcbal          # start interactive CLI mode
hi vcbal server   # start API server mode
```

### 3. Configure

Copy the template and fill in your API key:

```bash
cp config.example.yaml config.yaml
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

## API Endpoints

Start the server with `python main.py server`, then:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a message `{"message": "..."}` |
| POST | `/chat/reset` | Reset conversation |
| GET | `/skills` | List registered skills |
| GET | `/knowledge` | List all knowledge entries |
| POST | `/knowledge` | Save knowledge `{"content": "...", "tags": [...]}` |
| DELETE | `/knowledge/{id}` | Delete a knowledge entry |
| GET | `/health` | Health check |

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
│   ├── agent.py              # Agent orchestrator
│   ├── llm.py                # LLM client abstraction
│   ├── config.py             # Config loader
│   ├── context.py            # Conversation context manager
│   ├── i18n.py               # GNU gettext wrapper
│   └── prompt_loader.py      # Per-language YAML prompt overlay
├── knowledge/
│   ├── vector_store.py       # ChromaDB vector store
│   └── knowledge_manager.py  # Knowledge CRUD
├── skills/
│   ├── base.py               # BaseSkill abstract class
│   ├── registry.py           # Skill registry
│   ├── web_search.py         # Web search (DuckDuckGo)
│   ├── knowledge_skill.py    # Knowledge base management
│   ├── datetime_skill.py     # Date / time utility
│   ├── divination_skill.py   # Chinese stems/branches divination (entertainment)
│   ├── tarot_career_skill.py # Tarot career reading (entertainment)
│   ├── lucky_today_skill.py  # Daily luck generator (entertainment)
│   └── almanac_skill.py      # Chinese almanac / 黄历 (entertainment)
├── storage/
│   └── database.py           # SQLite conversation storage
├── api/
│   └── server.py             # FastAPI REST API
├── prompts/
│   ├── en.yaml               # English LLM-facing skill prompts
│   └── zh.yaml               # Chinese LLM-facing skill prompts (independently tunable)
├── locales/
│   └── zh/LC_MESSAGES/
│       ├── messages.po       # Chinese UI translations (editable source)
│       └── messages.mo       # Compiled binary (pre-built, committed)
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
