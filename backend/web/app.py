"""FastAPI 진입점."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile
from pydantic import BaseModel

load_dotenv()

from backend.agents.ci_triage.agent import CITriageAgent
from backend.agents.curator.agent import CuratorAgent
from backend.agents.qa_gen.agent import QAGenAgent
from backend.agents.rag.agent import RAGAgent
from backend.agents.research.agent import DeepResearchAgent
from backend.common.supervisor import Supervisor
from backend.ingest.db import ensure_schema
from backend.scheduler import start_scheduler, stop_scheduler

supervisor = Supervisor()
supervisor.register(CuratorAgent())
supervisor.register(RAGAgent())
supervisor.register(DeepResearchAgent())
supervisor.register(CITriageAgent())
supervisor.register(QAGenAgent())


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="agent-dev", version="0.1.0", lifespan=lifespan)

from backend.web.github_hook import router as github_router
app.include_router(github_router)


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
    agent = CuratorAgent()
    result = await agent.safe_run({"trigger": "manual"})
    return {
        "agent": result.agent,
        "articles_count": result.usage.get("articles_ranked", 0),
        "slack_sent": result.usage.get("slack_sent", False),
        "error": result.error,
    }


@app.post("/ingest")
async def ingest_file(file: UploadFile):
    """문서 업로드 → 청킹 → 임베딩 → pgvector 저장."""
    from backend.ingest.ingest import ingest_file as do_ingest

    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    chunks = do_ingest(tmp_path)
    return {"file": file.filename, "chunks": chunks}
