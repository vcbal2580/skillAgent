# SkillAgent AI Reading Guide
<!-- AI-READABLE: Entry index for autonomous agents and RAG ingestion. -->

## Goal

This guide explains how another AI system should read this repository documentation efficiently and accurately.

## Recommended Read Order

1. docs/ARCHITECTURE.md
2. docs/SKILLS.md
3. docs/API_REFERENCE.md
4. docs/CONFIGURATION.md
5. persona.md
6. prompts/zh.yaml and prompts/en.yaml

## What Each Document Answers

- ARCHITECTURE.md
  - System boundaries, module responsibilities, execution flow.
  - Where context, tools, and LLM calls connect.

- SKILLS.md
  - Exact skill catalog and intended use.
  - Parameters and behavioral notes for tool selection.

- API_REFERENCE.md
  - Integration contract for backend usage.
  - Request/response shapes and endpoint semantics.

- CONFIGURATION.md
  - Runtime knobs and deployment-relevant settings.
  - Which config keys alter model behavior.

## Prompt Semantics

- Base behavior is controlled by persona.md (system prompt text source).
- Tool descriptions can be language-overridden via prompts/*.yaml.
- Actual LLM system message is composed at runtime in core/context.py:
  - real-time system clock prefix + configured system_prompt.

## Reliability Notes for AI Consumers

- Time-related reasoning:
  - Do not assume static year/date from pretrained priors.
  - Trust runtime timestamp injected by core/context.py.

- Tool usage:
  - Prefer dedicated skills over free-text speculation.
  - For real-time facts, use web_search or news_workflow.
  - For date/time, use get_datetime when precision matters.

- Knowledge behavior:
  - Personal memory is in ChromaDB, not in static markdown docs.
  - Use knowledge_manage actions to read/write user memory.

## Suggested RAG Chunking Strategy

- Chunk by heading level (H2/H3) for all docs/*.md.
- Keep each skill section in SKILLS.md as an independent chunk.
- Keep each endpoint section in API_REFERENCE.md as an independent chunk.
- Include file path metadata in every chunk for traceability.

## Versioning Note

These docs describe the current local codebase state. If code changes, update docs in the same commit batch (local or remote) to maintain consistency.
