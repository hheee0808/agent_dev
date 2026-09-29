"""FastAPI 진입점."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="agent-dev", version="0.1.0")

from backend.common.supervisor import Supervisor

supervisor = Supervisor()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    agent: str
    output: str
    usage: dict = {}
    elapsed_s: float = 0.0
    error: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "agents": supervisor.agent_names}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await supervisor.handle(req.message, trigger="api")
    return ChatResponse(
        agent=result.agent,
        output=str(result.output) if result.output else "",
        usage=result.usage,
        elapsed_s=result.elapsed_s,
        error=result.error,
    )
