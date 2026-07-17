# SkillAgent — Architecture Overview
<!-- AI-READABLE: This document describes the complete system architecture.
     Read this first to understand how all modules connect. -->

## Project Identity

| Field        | Value                                      |
|-------------|---------------------------------------------|
| Package name | `vcbal-agent`                              |
| CLI command  | `hi` (entry point → `main:main`)           |
| Version      | 0.1.0                                      |
| Python       | ≥ 3.10                                     |
| License      | MIT + Commons Clause                       |

---

## Request Lifecycle

```
User Input (text / image / audio / document)
        │
        ▼
  main.py / api/server.py          ← entry points
        │
        ▼
  core/agent.py  Agent.chat()      ← orchestrator
        │
        ├─ core/context.py         ← builds message list
        │     └─ injects current system time into every system message
        │         format: "【当前系统时间：YYYY年MM月DD日 HH:MM 星期X】"
        │
        ├─ core/llm.py  LLMClient  ← calls OpenAI-compatible API
        │
        └─ skills/registry.py      ← dispatches tool calls
              └─ skills/<skill>.py ← executes skill, returns string
```

Loop runs until: no more tool calls **or** `max_tool_calls` (default 5) reached.

---

## Module Map

### `core/`

| File             | Role                                                                 |
|-----------------|----------------------------------------------------------------------|
| `agent.py`      | Orchestrator. Multi-turn tool-call loop. Handles text/image/audio/doc input. |
| `config.py`     | Singleton YAML config loader. Supports env var overrides. Auto-creates data dirs. |
| `context.py`    | Conversation history (max 20 turns). **Prepends real-time timestamp to system prompt on every call.** |
| `llm.py`        | OpenAI-compatible client. Supports chat, vision, function-calling.   |
| `prompt_loader.py` | Loads `prompts/<lang>.yaml` overlays onto skill tool definitions. |
| `i18n.py`       | GNU gettext i18n. Locales at `locales/<lang>/LC_MESSAGES/messages.mo`. |

### `core/stt/`

| Engine               | Trigger              | Notes                                     |
|---------------------|----------------------|-------------------------------------------|
| `engine_disabled.py` | `stt.engine: disabled` | No-op, always returns empty string       |
| `engine_openai.py`   | `stt.engine: openai`   | Whisper API. mic record + file transcribe |
| `engine_dashscope.py`| `stt.engine: dashscope`| Paraformer. async batch + real-time stream|

### `skills/`

| File                  | Skill name(s)           |
|-----------------------|-------------------------|
| `base.py`             | Abstract `BaseSkill`    |
| `registry.py`         | `SkillRegistry` – registers skills, builds OpenAI function-call schema |
| `web_search.py`       | `web_search`            |
| `knowledge_skill.py`  | `knowledge_manage`      |
| `datetime_skill.py`   | `get_datetime`          |
| `weather_skill.py`    | `get_weather`           |
| `divination_skill.py` | `fortune_divination`    |
| `tarot_career_skill.py`| `tarot_career_reading` |
| `lucky_today_skill.py`| `today_luck`            |
| `almanac_skill.py`    | `huangli_today`         |
| `document_skill.py`   | (internal helper)       |
| `wecom_notify_skill.py`| `wecom_notify`         |
| `git_summary_skill.py`| `git_daily_summary`    |
| `news_workflow_skill.py`| `news_workflow`       |
| `workflow_service.py` | `WorkflowManager` singleton – background HTTP services |

### `knowledge/`

| File                   | Role                                            |
|-----------------------|-------------------------------------------------|
| `knowledge_manager.py` | CRUD API: save / search / delete / list / count |
| `vector_store.py`      | ChromaDB backend. Persistent at `./data/chromadb`. Cosine similarity. |

### `storage/`

| File          | Role                                                         |
|--------------|--------------------------------------------------------------|
| `database.py` | SQLite conversation history. Tables: `conversations`, `sessions`. Path: `./data/agent.db`. |

### `api/`

| File        | Role                                      |
|------------|-------------------------------------------|
| `server.py` | FastAPI app. All REST endpoints. CORS open. Port 8000. |

---

## Data Directories

```
data/
├── chromadb/          ← ChromaDB vector store
│   └── chroma.sqlite3
├── git_cache/         ← Cloned remote git repos for git_daily_summary
└── agent.db           ← SQLite conversation history
```

---

## Prompt Override System

1. Python skill class defines base `description` and `parameters`.
2. `prompts/zh.yaml` or `prompts/en.yaml` can override any field.
3. `prompt_loader.overlay(skill_name, tool_def)` merges at startup.
4. Active language set by `config.language` (default `zh`).

---

## Key Design Decisions

- **System time injection** — Every LLM call includes the live system clock in the system message, preventing date hallucination.
- **News freshness** — `news_workflow` uses `timelimit='d'/'w'/'m'` in ddgs calls and tags each item `today/3days/week/older`.
- **No hardcoded secrets** — All API keys via `config.yaml` (git-ignored) or environment variables.
- **OpenAI-compatible** — Works with any provider exposing the OpenAI chat-completions API.
