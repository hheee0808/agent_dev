"""CI 트리아지 에이전트 — GitHub Actions 실패 분석 + PR 코멘트."""

from __future__ import annotations

import logging

from backend.agents.ci_triage.analyzer import analyze_log, format_pr_comment
from backend.agents.ci_triage.github import (
    find_pr_for_sha,
    get_failed_runs,
    get_run_log_text,
    post_pr_comment,
)
from backend.common.agent_base import AgentBase, AgentResult

log = logging.getLogger(__name__)


class CITriageAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            name="ci_triage",
            description="GitHub Actions CI 실패를 분석하고 원인·해결안을 PR에 코멘트합니다.",
        )

    async def run(self, input_data: dict) -> AgentResult:
        run_id = input_data.get("run_id")

        if run_id:
            return await self._analyze_run(int(run_id))

        runs = await get_failed_runs(limit=1)
        if not runs:
            return AgentResult(agent=self.name, output="최근 실패한 CI run이 없습니다.")

        latest = runs[0]
        return await self._analyze_run(latest["id"], run_data=latest)

    async def _analyze_run(self, run_id: int, run_data: dict | None = None) -> AgentResult:
        run_url = run_data.get("html_url", "") if run_data else ""
        head_sha = run_data.get("head_sha", "") if run_data else ""

        log_text = await get_run_log_text(run_id)
        analysis = analyze_log(log_text, run_url)
        comment_md = format_pr_comment(analysis, run_url)

        pr_commented = False
        if head_sha:
            pr_num = await find_pr_for_sha(head_sha)
            if pr_num:
                pr_commented = await post_pr_comment(pr_num, comment_md)

        usage = analysis.pop("usage", {})
        return AgentResult(
            agent=self.name,
            output=comment_md,
            usage={
                **usage,
                "run_id": run_id,
                "severity": analysis.get("severity"),
                "error_type": analysis.get("error_type"),
                "pr_commented": pr_commented,
            },
        )
