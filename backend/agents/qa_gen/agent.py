"""QA 테스트 생성 에이전트 — AST 추출 → 테스트 생성 → 실행 → 자기 수정."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.agents.qa_gen.extractor import extract_functions, find_callers
from backend.agents.qa_gen.generator import generate_tests
from backend.agents.qa_gen.runner import run_with_fix
from backend.common.agent_base import AgentBase, AgentResult

log = logging.getLogger(__name__)


class QAGenAgent(AgentBase):
    def __init__(self) -> None:
        super().__init__(
            name="qa_gen",
            description="Python 함수의 pytest 테스트를 자동 생성하고, 실패 시 자기 수정합니다.",
        )

    async def run(self, input_data: dict) -> AgentResult:
        file_path = input_data.get("file_path", "")
        function_name = input_data.get("function_name")
        project_dir = input_data.get("project_dir", ".")

        if not file_path or not Path(file_path).exists():
            return AgentResult(agent=self.name, output="유효한 파일 경로를 지정해주세요.")

        functions = extract_functions(file_path)
        if not functions:
            return AgentResult(agent=self.name, output=f"함수를 찾을 수 없습니다: {file_path}")

        if function_name:
            functions = [f for f in functions if f.name == function_name]
            if not functions:
                return AgentResult(agent=self.name, output=f"함수 '{function_name}'을 찾을 수 없습니다.")

        results = []
        total_passed = 0
        total_rounds = 0

        for func in functions:
            if func.name.startswith("_") and not function_name:
                continue

            func.callers = find_callers(func.name, project_dir)
            test_code = generate_tests(func)
            final_code, passed, rounds = run_with_fix(test_code, project_dir)

            results.append({
                "function": func.name,
                "passed": passed,
                "fix_rounds": rounds,
                "test_code": final_code,
            })
            if passed:
                total_passed += 1
            total_rounds += rounds

        output_parts = []
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            output_parts.append(
                f"### {r['function']} [{status}] (fix rounds: {r['fix_rounds']})\n"
                f"```python\n{r['test_code']}\n```"
            )

        return AgentResult(
            agent=self.name,
            output="\n\n".join(output_parts),
            usage={
                "functions_tested": len(results),
                "passed": total_passed,
                "failed": len(results) - total_passed,
                "total_fix_rounds": total_rounds,
            },
        )
