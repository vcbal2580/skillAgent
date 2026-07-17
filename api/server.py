"""
FastAPI server - provides REST API for GUI / multimodal integration.
Supports text, image (vision), audio (STT), and document upload endpoints.
"""

import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from core.agent import Agent
from core.config import config

app = FastAPI(title="SkillAgent API", version="0.1.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: Agent = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    transcribed: Optional[str] = None  # filled for audio requests
    usage: Optional[dict] = None


class ImageChatRequest(BaseModel):
    message: str
    image_url: str  # public URL or base64 data URI


class KnowledgeRequest(BaseModel):
    content: str
    tags: list[str] = []


@app.on_event("startup")
async def startup():
    global agent
    # Initialise language-specific prompts (config already loaded by main.py)
    from core.i18n import setup as i18n_setup
    from core.prompt_loader import setup as prompt_setup
    lang = config.get("language", "en")
    i18n_setup(lang)
    prompt_setup(lang)
    agent = Agent()
    agent.register_default_skills()


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the agent and get a response."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        reply = agent.chat(req.message)
        return ChatResponse(reply=reply, usage=agent.last_usage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/reset")
async def reset_chat():
    """Reset conversation history."""
    agent.reset()
    return {"status": "ok", "message": "Conversation reset"}


@app.get("/skills")
async def list_skills():
    """List all registered skills."""
    return {"skills": agent.registry.list_skills()}


@app.get("/knowledge")
async def list_knowledge():
    """List all knowledge entries."""
    from knowledge.knowledge_manager import KnowledgeManager
    km = KnowledgeManager()
    items = km.list_all()
    return {"count": len(items), "items": items}


@app.post("/knowledge")
async def save_knowledge(req: KnowledgeRequest):
    """Save a new knowledge entry."""
    from knowledge.knowledge_manager import KnowledgeManager
    km = KnowledgeManager()
    doc_id = km.save(content=req.content, tags=req.tags)
    return {"id": doc_id, "status": "saved"}


@app.delete("/knowledge/{doc_id}")
async def delete_knowledge(doc_id: str):
    """Delete a knowledge entry."""
    from knowledge.knowledge_manager import KnowledgeManager
    km = KnowledgeManager()
    success = km.delete(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return {"status": "deleted"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.2.0"}


# ──────────────────────────────────────────────────────────
# Workflow management endpoints
# ──────────────────────────────────────────────────────────

@app.get("/workflows")
async def list_workflows():
    """List all running workflow services."""
    from skills.workflow_service import WorkflowManager
    manager = WorkflowManager()
    return {"workflows": manager.list_workflows()}


@app.delete("/workflows/{name}")
async def stop_workflow(name: str):
    """Stop a running workflow service."""
    from skills.workflow_service import WorkflowManager
    manager = WorkflowManager()
    if manager.stop_workflow(name):
        return {"status": "stopped", "name": name}
    raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")


# ──────────────────────────────────────────────────────────
# Multimodal endpoints
# ──────────────────────────────────────────────────────────

@app.post("/chat/image", response_model=ChatResponse)
async def chat_with_image(req: ImageChatRequest):
    """Send a text message plus an image (URL or base64 data URI) to the agent."""
    if not req.message.strip() and not req.image_url.strip():
        raise HTTPException(status_code=400, detail="message or image_url required")
    try:
        reply = agent.chat_with_image(
            user_input=req.message or "请描述这张图片",
            image_source=req.image_url,
        )
        return ChatResponse(reply=reply, usage=agent.last_usage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/audio", response_model=ChatResponse)
async def chat_with_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """Upload an audio file (mp3/wav/m4a/ogg/webm). The server transcribes it
    with STT and passes the text to the agent."""
    suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())
    try:
        reply = agent.chat_with_audio(tmp_path, language=language)
        # Recover transcribed text from context (last user message)
        msgs = agent.context.get_messages()
        transcribed = next(
            (m["content"] for m in reversed(msgs) if m["role"] == "user" and isinstance(m["content"], str)),
            None,
        )
        return ChatResponse(reply=reply, transcribed=transcribed, usage=agent.last_usage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@app.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    save_to_knowledge: bool = Form(False),
    question: Optional[str] = Form(None),
):
    """Upload a document (PDF/docx/xlsx/xls/txt). Optionally ask a question about it
    or save it to the knowledge base (Excel files are split per-sheet).

    Returns:
        text: Extracted raw text preview (first 12 000 chars).
        reply: Agent answer if `question` was provided, else null.
        knowledge_ids: List of knowledge base IDs if saved, else null.
        chunks_saved: Number of chunks saved, if saved.
    """
    from skills.document_skill import extract_document, extract_document_chunks

    suffix = os.path.splitext(file.filename or "doc.bin")[1] or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())
    try:
        text = extract_document(tmp_path)
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text could be extracted from the document.")

        max_chars = 12000
        preview = text[:max_chars]
        knowledge_ids = None
        chunks_saved = None

        if save_to_knowledge:
            from knowledge.knowledge_manager import KnowledgeManager
            km = KnowledgeManager()
            stem = os.path.splitext(file.filename or "document")[0]
            doc_chunks = extract_document_chunks(tmp_path)
            knowledge_ids = []
            for chunk in doc_chunks:
                tags = ["document", stem]
                if chunk["meta"].get("sheet"):
                    tags.append(chunk["meta"]["sheet"])
                doc_id = km.save(content=chunk["text"], tags=tags, source=file.filename or stem)
                knowledge_ids.append(doc_id)
            chunks_saved = len(knowledge_ids)

        reply = None
        if question:
            prompt = (
                f"以下是文档内容（可能已截断）：\n\n{preview}\n\n"
                f"请根据以上内容回答：{question}"
            )
            reply = agent.chat(prompt)

        return {"text": preview, "reply": reply, "knowledge_ids": knowledge_ids, "chunks_saved": chunks_saved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


def start_server():
    """Start the FastAPI server."""
    import uvicorn
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8000)
    uvicorn.run(app, host=host, port=port)
