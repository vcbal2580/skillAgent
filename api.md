# SkillAgent API Documentation

**Version:** 0.1.0

---

## Endpoints

### POST `/chat`

**Chat**

Send a message to the agent and get a response.

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✓ |  |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |
| 422 | Validation Error |

---

### POST `/chat/audio`

**Chat With Audio**

Upload an audio file (mp3/wav/m4a/ogg/webm). The server transcribes it
with STT and passes the text to the agent.

**Request Body** (`multipart/form-data`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | ✓ |  |
| `language` |  |  |  |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |
| 422 | Validation Error |

---

### POST `/chat/image`

**Chat With Image**

Send a text message plus an image (URL or base64 data URI) to the agent.

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✓ |  |
| `image_url` | string | ✓ |  |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |
| 422 | Validation Error |

---

### POST `/chat/reset`

**Reset Chat**

Reset conversation history.

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |

---

### GET `/health`

**Health**

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |

---

### GET `/knowledge`

**List Knowledge**

List all knowledge entries.

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |

---

### POST `/knowledge`

**Save Knowledge**

Save a new knowledge entry.

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | ✓ |  |
| `tags` | array |  |  |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |
| 422 | Validation Error |

---

### DELETE `/knowledge/{doc_id}`

**Delete Knowledge**

Delete a knowledge entry.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `doc_id` | path | string | ✓ |  |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |
| 422 | Validation Error |

---

### GET `/skills`

**List Skills**

List all registered skills.

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |

---

### POST `/upload/document`

**Upload Document**

Upload a document (PDF/docx/xlsx/xls/txt). Optionally ask a question about it
or save it to the knowledge base (Excel files are split per-sheet).

Returns:
    text: Extracted raw text preview (first 12 000 chars).
    reply: Agent answer if `question` was provided, else null.
    knowledge_ids: List of knowledge base IDs if saved, else null.
    chunks_saved: Number of chunks saved, if saved.

**Request Body** (`multipart/form-data`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | ✓ |  |
| `save_to_knowledge` | boolean |  |  |
| `question` |  |  |  |

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Successful Response |
| 422 | Validation Error |

---
