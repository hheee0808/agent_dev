"""Framework-free supervisor — intent 분류 후 에이전트 디스패치.

Gemini function_calling으로 intent 분류 → 해당 에이전트 실행 → 결과 반환.
LangGraph/CrewAI 없이 60~150줄로 구현.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.common.agent_base import AgentBase, AgentResult
from backend.common.llm import generate, resolve_model
from backend.common.trace import trace_run

log = logging.getLogger(__name__)

CLASSIFY_SYSTEM_PROMPT = """\
You are an intent classifier for a multi-agent system.
Given a user message, decide which agent should handle it.
Call the `route` function with the agent name.
If no agent fits, use "none".
"""


class Supervisor:
    def __init__(self) -> None:
        self._agents: dict[str, AgentBase] = {}

    def register(self, agent: AgentBase) -> None:
        self._agents[agent.name] = agent

    @property
    def agent_names(self) -> list[str]:
        return list(self._agents.keys())

    def _build_route_declaration(self) -> dict:
        descriptions = "\n".join(
            f"- {a.name}: {a.description}" for a in self._agents.values()
        )
        return {
            "name": "route",
            "description": f"Route to one of the agents:\n{descriptions}",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": self.agent_names + ["none"],
                        "description": "The agent to handle this request.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this agent was chosen.",
                    },
                },
                "required": ["agent"],
            },
        }

    def classify(self, message: str) -> tuple[str, str]:
        """사용자 메시지 → (agent_name, reason). function_calling 기반."""
        from google.genai import types

        model = resolve_model()
        config = types.GenerateContentConfig(
            system_instruction=CLASSIFY_SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(**self._build_route_declaration()),
            ])],
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        from backend.common.llm import get_client
        resp = get_client().models.generate_content(
            model=model, contents=message, config=config,
        )

        for part in resp.candidates[0].content.parts:
            fc = getattr(part, "function_call", None)
            if fc and fc.name == "route":
                args = dict(fc.args) if fc.args else {}
                return args.get("agent", "none"), args.get("reason", "")

        return "none", "no function call returned"

    async def handle(self, message: str, *, trigger: str = "chat") -> AgentResult:
        agent_name, reason = self.classify(message)
        log.info("classify → agent=%s reason=%s", agent_name, reason)

        if agent_name == "none" or agent_name not in self._agents:
            text, usage = generate(
                message,
                system_instruction="You are a helpful AI assistant. Answer in the same language as the user.",
            )
            result = AgentResult(agent="direct", output=text, usage=usage)
            trace_run(
                agent_name="direct",
                trigger=trigger,
                input_payload={"message": message},
                output_payload={"text": text},
                **_usage_to_trace(usage),
            )
            return result

        agent = self._agents[agent_name]
        result = await agent.safe_run({"message": message})
        trace_run(
            agent_name=agent_name,
            trigger=trigger,
            input_payload={"message": message},
            output_payload={"output": str(result.output)[:2000]},
            elapsed_s=result.elapsed_s,
            error=result.error,
            **_usage_to_trace(result.usage),
        )
        return result


def _usage_to_trace(usage: dict) -> dict:
    if not usage:
        return {}
    return {
        "model": usage.get("model"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost_usd"),
    }
