"""FastAPI 진입점."""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

from backend.agents.curator.agent import CuratorAgent
from backend.common.supervisor import Supervisor
from backend.scheduler import start_scheduler, stop_scheduler

supervisor = Supervisor()
supervisor.register(CuratorAgent())


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="agent-dev", version="0.1.0", lifespan=lifespan)


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


@app.post("/curator/run")
async def run_curator():
    """수동 큐레이션 트리거."""
    agent = CuratorAgent()
    result = await agent.safe_run({"trigger": "manual"})
    return {
        "agent": result.agent,
        "articles_count": result.usage.get("articles_ranked", 0),
        "slack_sent": result.usage.get("slack_sent", False),
        "error": result.error,
    }
