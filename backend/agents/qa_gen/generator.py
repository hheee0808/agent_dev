"""pytest 테스트 코드 자동 생성."""

from __future__ import annotations

import logging

from backend.agents.qa_gen.extractor import FunctionInfo
from backend.common.llm import generate

log = logging.getLogger(__name__)

GEN_SYSTEM_PROMPT = """\
You are a Python test engineer. Given a function's signature, body, and context,
generate comprehensive pytest test code.

Rules:
- Use pytest style (not unittest)
- Include edge cases, error cases, and happy path
- Use descriptive test names: test_<function>_<scenario>
- Mock external dependencies (LLM calls, DB, HTTP)
- Add brief docstrings for complex tests
- Import the function being tested
- Return ONLY the Python test code, no explanation
"""


def generate_tests(func: FunctionInfo) -> str:
    """함수 정보 → pytest 코드 생성."""
    prompt = (
        f"Generate pytest tests for this function:\n\n"
        f"File: {func.file}\n"
        f"Function: {func.name}\n"
        f"Args: {', '.join(func.args)}\n"
        f"Return: {func.return_annotation}\n"
        f"Decorators: {func.decorators}\n"
        f"Docstring: {func.docstring}\n\n"
        f"Source:\n```python\n{func.body_source}\n```"
    )

    if func.callers:
        prompt += f"\n\nCalled from: {', '.join(func.callers[:5])}"

    test_code, _ = generate(prompt, system_instruction=GEN_SYSTEM_PROMPT)

    if "```python" in test_code:
        test_code = test_code.split("```python")[1].split("```")[0]
    elif "```" in test_code:
        test_code = test_code.split("```")[1].split("```")[0]

    return test_code.strip()
