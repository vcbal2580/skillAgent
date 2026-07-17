# SkillAgent API Reference
<!-- AI-READABLE: Backend endpoint contract for integration and tooling. -->

Base server: FastAPI app in api/server.py
Default host/port from config: api.host, api.port (example: 0.0.0.0:8000)

## Endpoints

### POST /chat

- Description: Send a plain text message to the agent.
- Request JSON:
  - message: string (required)
- Response JSON:
  - reply: string
  - transcribed: string|null
- Errors:
  - 400 when message empty
  - 500 internal runtime errors

### POST /chat/reset

- Description: Reset conversation history.
- Response JSON:
  - status: "ok"
  - message: "Conversation reset"

### GET /skills

- Description: List all currently registered skill names.
- Response JSON:
  - skills: string[]

### GET /knowledge

- Description: List all saved knowledge entries.
- Response JSON:
  - count: integer
  - items: object[]

### POST /knowledge

- Description: Save one knowledge entry.
- Request JSON:
  - content: string
  - tags: string[] (optional)
- Response JSON:
  - id: string
  - status: "saved"

### DELETE /knowledge/{doc_id}

- Description: Delete a knowledge entry by id.
- Response JSON:
  - status: "deleted"
- Errors:
  - 404 when id does not exist

### GET /health

- Description: Health check endpoint.
- Response JSON:
  - status: "healthy"
  - version: "0.2.0"

### GET /workflows

- Description: List running workflow services.
- Response JSON:
  - workflows: object[]

### DELETE /workflows/{name}

- Description: Stop a running workflow service by name.
- Response JSON:
  - status: "stopped"
  - name: string
- Errors:
  - 404 when workflow not found

### POST /chat/image

- Description: Send text + image to multimodal agent route.
- Request JSON:
  - message: string
  - image_url: string (public URL or data URI)
- Response JSON:
  - reply: string
  - transcribed: null

### POST /chat/audio

- Description: Upload audio file for STT then chat.
- Request: multipart/form-data
  - file: binary (required)
  - language: string (optional)
- Response JSON:
  - reply: string
  - transcribed: string|null

### POST /upload/document

- Description: Upload document for extraction, optional KB save, optional question answering.
- Request: multipart/form-data
  - file: binary (required)
  - save_to_knowledge: boolean (optional, default false)
  - question: string (optional)
- Response JSON:
  - text: string (preview, truncated to 12000 chars)
  - reply: string|null
  - knowledge_ids: string[]|null
  - chunks_saved: integer|null
- Errors:
  - 422 when no text extracted
  - 500 runtime errors

---

## Data Models (Simplified)

- ChatRequest: { message: string }
- ChatResponse: { reply: string, transcribed?: string|null }
- ImageChatRequest: { message: string, image_url: string }
- KnowledgeRequest: { content: string, tags: string[] }

---

## Operational Notes

- CORS is open to all origins in current implementation.
- A global singleton Agent instance is initialized at startup.
- Language setup runs at startup using config.language and initializes i18n + prompt overlays.
