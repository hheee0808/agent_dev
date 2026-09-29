"""Tool 정의 — 에이전트가 사용하는 도구의 공통 인터페이스."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable

    def to_gemini_declaration(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def execute(self, **kwargs) -> Any:
        log.info("tool.execute: %s(%s)", self.name, list(kwargs.keys()))
        if inspect.iscoroutinefunction(self.fn):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(self.fn(**kwargs))
        return self.fn(**kwargs)

    async def aexecute(self, **kwargs) -> Any:
        log.info("tool.aexecute: %s(%s)", self.name, list(kwargs.keys()))
        if inspect.iscoroutinefunction(self.fn):
            return await self.fn(**kwargs)
        import functools, asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(self.fn, **kwargs),
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def gemini_declarations(self) -> list[dict]:
        return [t.to_gemini_declaration() for t in self._tools.values()]
