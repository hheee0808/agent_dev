"""웹 큐레이션 에이전트 — 소스 수집 → 필터/랭킹 → Slack 발송."""

from __future__ import annotations

import logging

from backend.agents.curator.formatter import format_digest
from backend.agents.curator.ranker import rank_articles
from backend.agents.curator.slack import send_digest
from backend.agents.curator.sources import fetch_all
from backend.common.agent_base import AgentBase, AgentResult

log = logging.getLogger(__name__)


class CuratorAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            name="curator",
            description="AI 에이전트 관련 뉴스를 수집·큐레이션하여 Slack 다이제스트를 발송합니다.",
        )

    async def run(self, input_data: dict) -> AgentResult:
        articles = await fetch_all()
        if not articles:
            return AgentResult(agent=self.name, output="수집된 기사가 없습니다.")

        ranked = await rank_articles(articles)
        if not ranked:
            return AgentResult(agent=self.name, output="관련 기사가 없습니다.")

        digest = format_digest(ranked)
        sent = send_digest(digest)

        return AgentResult(
            agent=self.name,
            output=digest,
            usage={"articles_collected": len(articles), "articles_ranked": len(ranked), "slack_sent": sent},
        )
