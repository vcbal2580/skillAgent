# SkillAgent Configuration Guide
<!-- AI-READABLE: Exact configuration surface and runtime effects. -->

Primary file: config.yaml (copy from config.example.yaml)

## Top-Level Keys

- language
- llm
- knowledge
- storage
- agent
- api
- git_summary
- wecom
- stt
- feishu (optional, commented in example)

---

## language

- Type: string
- Values: zh | en
- Effect:
  - Controls i18n message locale.
  - Controls prompt overlay source file: prompts/zh.yaml or prompts/en.yaml.

---

## llm

- provider: openai | deepseek | zhipu | qwen | ollama
- api_key: provider API key (or env-based)
- base_url: OpenAI-compatible base URL
- model: default chat model
- temperature: float
- max_tokens: int
- vision_model: optional model used for image chat route

Notes:
- Any provider exposing OpenAI-compatible chat-completions can be used.
- Some fields can be overridden by environment variables depending on provider.

---

## knowledge

- persist_directory: path (default ./data/chromadb)
- collection_name: string (default personal_knowledge)
- top_k: int (semantic search result count)

---

## storage

- db_path: path to sqlite file (default ./data/agent.db)

---

## agent

- system_prompt:
  - inline multi-line text, or
  - file reference with prefix: file:persona.md
- max_tool_calls: int (default 5)
- max_history: int (default 20 conversation turns)

Important runtime behavior:
- The system prompt is dynamically prefixed by real system time on every LLM call in core/context.py.
- Prefix format: 【当前系统时间：YYYY年MM月DD日 HH:MM 星期X】

---

## api

- host: bind host
- port: bind port

---

## git_summary

- author: optional global author filter
- repos: list of repositories
  - path: local absolute path or remote URL
  - name: display name
  - author: optional per-repo override

---

## wecom

Fields used by WeCom integration:
- webhook_url
- corp_id
- token
- encoding_aes_key
- agent_id
- corp_secret
- callback_path

---

## stt

- engine: disabled | openai | dashscope
- openai_model: whisper model name for OpenAI mode
- api_key: optional override, otherwise can reuse llm credentials
- base_url: optional override for openai mode
- language: optional language hint

---

## Minimal Working Example

language: zh

llm:
  provider: qwen
  api_key: your-dashscope-api-key
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  model: qwen-plus
  temperature: 0.7
  max_tokens: 2048

knowledge:
  persist_directory: ./data/chromadb
  collection_name: personal_knowledge
  top_k: 5

storage:
  db_path: ./data/agent.db

agent:
  system_prompt: file:persona.md
  max_tool_calls: 5
  max_history: 20

api:
  host: 0.0.0.0
  port: 8000

stt:
  engine: disabled
