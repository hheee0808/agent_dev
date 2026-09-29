"""에이전트 공통 인터페이스."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.common.tool import ToolRegistry

log = logging.getLogger(__name__)


@dataclass
class AgentResult:
    agent: str
    output: Any
    usage: dict = field(default_factory=dict)
    elapsed_s: float = 0.0
    error: str | None = None


class AgentBase(ABC):
    name: str
    description: str
    tools: ToolRegistry

    def __init__(self, name: str, description: str, tools: ToolRegistry | None = None) -> None:
        self.name = name
        self.description = description
        self.tools = tools or ToolRegistry()

    @abstractmethod
    async def run(self, input_data: dict) -> AgentResult:
        ...

    async def safe_run(self, input_data: dict) -> AgentResult:
        t0 = time.time()
        try:
            result = await self.run(input_data)
            result.elapsed_s = time.time() - t0
            return result
        except Exception as e:
            log.exception("agent %s failed", self.name)
            return AgentResult(
                agent=self.name,
                output=None,
                elapsed_s=time.time() - t0,
                error=str(e),
            )
