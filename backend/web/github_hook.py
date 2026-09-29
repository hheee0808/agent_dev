"""GitHub Actions webhook — CI 실패 시 자동 트리아지."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from backend.agents.ci_triage.agent import CITriageAgent

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/github")
async def github_webhook(request: Request):
    payload = await request.json()
    action = payload.get("action")

    if action == "completed":
        run = payload.get("workflow_run", {})
        if run.get("conclusion") == "failure":
            agent = CITriageAgent()
            result = await agent.safe_run({
                "run_id": run.get("id"),
                "run_data": run,
            })
            return {"handled": True, "agent": result.agent, "error": result.error}

    return {"handled": False, "reason": "not a failure event"}
