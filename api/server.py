"""
FastAPI server - provides REST API for future GUI integration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


class KnowledgeRequest(BaseModel):
    content: str
    tags: list[str] = []


@app.on_event("startup")
async def startup():
    global agent
    agent = Agent()
    agent.register_default_skills()


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the agent and get a response."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        reply = agent.chat(req.message)
        return ChatResponse(reply=reply)
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
    return {"status": "healthy", "version": "0.1.0"}


def start_server():
    """Start the FastAPI server."""
    import uvicorn
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8000)
    uvicorn.run(app, host=host, port=port)
