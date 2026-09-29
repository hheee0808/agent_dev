"""RAG 에이전트 — 문서 검색 → 인용 포함 답변 생성."""

from __future__ import annotations

import logging

from backend.agents.rag.retriever import Chunk, search
from backend.common.agent_base import AgentBase, AgentResult
from backend.common.llm import generate

log = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """\
You are a knowledgeable AI assistant specialized in AI agent development.
Answer the user's question using ONLY the provided context chunks.
If the context doesn't contain enough information, say so honestly.

Rules:
- Cite sources using [source:page] format
- Answer in the same language as the user's question
- Be concise but thorough
- If multiple sources agree, synthesize them
"""

NO_RESULTS_MSG = "관련 문서를 찾지 못했습니다. 문서를 먼저 업로드하거나, 질문을 다시 작성해 보세요."


def _format_context(chunks: list[Chunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] source={c.source} page={c.page_number} score={c.score:.2f}\n{c.content}")
    return "\n\n---\n\n".join(parts)


def _needs_requery(answer: str, chunks: list[Chunk]) -> bool:
    """답변 품질이 낮으면 재검색 판정."""
    low_score = all(c.score < 0.6 for c in chunks)
    hedging = any(phrase in answer for phrase in [
        "정보가 부족", "찾을 수 없", "문서에 없", "context doesn't contain",
        "not enough information", "cannot find",
    ])
    return low_score or hedging


class RAGAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            name="rag",
            description="AI 에이전트 관련 문서를 검색하고 인용과 함께 답변합니다.",
        )

    async def run(self, input_data: dict) -> AgentResult:
        query = input_data.get("message", "")
        if not query:
            return AgentResult(agent=self.name, output="질문을 입력해주세요.")

        chunks = search(query, top_k=5)
        if not chunks:
            return AgentResult(agent=self.name, output=NO_RESULTS_MSG)

        context = _format_context(chunks)
        prompt = f"Context:\n{context}\n\nQuestion: {query}"

        answer, usage = generate(prompt, system_instruction=RAG_SYSTEM_PROMPT)

        if _needs_requery(answer, chunks):
            log.info("requery triggered for: %s", query[:50])
            expanded_chunks = search(query, top_k=10)
            if len(expanded_chunks) > len(chunks):
                context = _format_context(expanded_chunks)
                prompt = f"Context:\n{context}\n\nQuestion: {query}"
                answer, usage = generate(prompt, system_instruction=RAG_SYSTEM_PROMPT)
                chunks = expanded_chunks

        sources = list({c.source for c in chunks})
        return AgentResult(
            agent=self.name,
            output=answer,
            usage={
                **usage,
                "chunks_used": len(chunks),
                "sources": sources,
            },
        )
