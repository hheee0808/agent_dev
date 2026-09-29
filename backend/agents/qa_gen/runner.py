"""pytest 실행 + 자기 수정 루프."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from backend.common.llm import generate

log = logging.getLogger(__name__)

MAX_FIX_ROUNDS = 3

FIX_SYSTEM_PROMPT = """\
You are fixing a failing pytest test. Given the test code and error output,
fix the test so it passes. Return ONLY the corrected Python test code.
Do not explain the changes.
"""


def run_tests(test_code: str, project_dir: str = ".") -> tuple[bool, str]:
    """테스트 코드를 임시 파일에 쓰고 pytest 실행."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_test.py", dir=project_dir,
        delete=False, encoding="utf-8",
    ) as f:
        f.write(test_code)
        test_path = f.name

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
            capture_output=True, text=True, timeout=60, cwd=project_dir,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return passed, output[-3000:]
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out (60s)"
    except Exception as e:
        return False, str(e)
    finally:
        Path(test_path).unlink(missing_ok=True)


def run_with_fix(test_code: str, project_dir: str = ".") -> tuple[str, bool, int]:
    """테스트 실행 → 실패 시 자동 수정 → 최대 MAX_FIX_ROUNDS 반복.

    반환: (final_test_code, passed, fix_rounds)
    """
    current_code = test_code

    for i in range(MAX_FIX_ROUNDS + 1):
        passed, output = run_tests(current_code, project_dir)

        if passed:
            log.info("tests passed (round %d)", i)
            return current_code, True, i

        if i >= MAX_FIX_ROUNDS:
            log.warning("max fix rounds reached, tests still failing")
            return current_code, False, i

        log.info("fix round %d: attempting repair", i + 1)
        prompt = (
            f"Fix this failing test:\n\n"
            f"Test code:\n```python\n{current_code}\n```\n\n"
            f"Error output:\n```\n{output}\n```"
        )
        fixed, _ = generate(prompt, system_instruction=FIX_SYSTEM_PROMPT)

        if "```python" in fixed:
            fixed = fixed.split("```python")[1].split("```")[0]
        elif "```" in fixed:
            fixed = fixed.split("```")[1].split("```")[0]

        current_code = fixed.strip()

    return current_code, False, MAX_FIX_ROUNDS
