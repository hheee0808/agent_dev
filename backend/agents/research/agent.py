"""Deep Research 에이전트 — planner → 다단계 검색 → 합성 → self-critique."""

from __future__ import annotations

import asyncio
import logging

from backend.agents.research.planner import decompose
from backend.agents.research.searcher import search_all
from backend.agents.research.synthesizer import critique, synthesize
from backend.common.agent_base import AgentBase, AgentResult
from backend.common.llm import generate

log = logging.getLogger(__name__)

MAX_CRITIQUE_ROUNDS = 2


class DeepResearchAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            name="research",
            description="복잡한 질문을 분해하여 다단계 웹/RAG 검색 후 인용 포함 리포트를 작성합니다.",
        )

    async def run(self, input_data: dict) -> AgentResult:
        question = input_data.get("message", "")
        if not question:
            return AgentResult(agent=self.name, output="리서치 주제를 입력해주세요.")

        sub_questions = decompose(question)
        log.info("sub-questions: %s", sub_questions)

        findings = []
        for sq in sub_questions:
            results = await search_all(sq)
            snippets = []
            sources = []
            for r in results:
                snippets.extend(r.snippets)
                sources.extend(r.sources)

            if snippets:
                summary, _ = generate(
                    f"Summarize these findings for the question: {sq}\n\n" + "\n".join(snippets),
                    system_instruction="Summarize concisely. Keep all factual details. Same language as question.",
                )
                findings.append({"query": sq, "content": summary, "sources": sources})
            else:
                findings.append({"query": sq, "content": "검색 결과 없음", "sources": []})

        report, usage = synthesize(question, findings)

        for i in range(MAX_CRITIQUE_ROUNDS):
            feedback = critique(report)
            if "PASS" in feedback.upper():
                log.info("critique passed at round %d", i + 1)
                break
            log.info("critique round %d: revising", i + 1)
            revised, rev_usage = generate(
                f"Revise this report based on feedback:\n\nFeedback:\n{feedback}\n\nReport:\n{report}",
                system_instruction="Revise the report to address the feedback. Keep citations. Same language.",
            )
            report = revised
            usage = rev_usage

        return AgentResult(
            agent=self.name,
            output=report,
            usage={
                **usage,
                "sub_questions": len(sub_questions),
                "findings": len(findings),
            },
        )
