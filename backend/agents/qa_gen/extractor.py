"""AST 기반 함수 시그니처 + 사용처 추출."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    name: str
    file: str
    lineno: int
    args: list[str] = field(default_factory=list)
    return_annotation: str = ""
    docstring: str = ""
    decorators: list[str] = field(default_factory=list)
    body_source: str = ""
    callers: list[str] = field(default_factory=list)


def extract_functions(file_path: str) -> list[FunctionInfo]:
    """파일에서 함수/메서드 시그니처 추출."""
    path = Path(file_path)
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        log.warning("syntax error in %s", file_path)
        return []

    functions = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        args = []
        for a in node.args.args:
            ann = ast.unparse(a.annotation) if a.annotation else ""
            args.append(f"{a.arg}: {ann}" if ann else a.arg)

        ret = ast.unparse(node.returns) if node.returns else ""
        doc = ast.get_docstring(node) or ""
        decos = [ast.unparse(d) for d in node.decorator_list]

        end_line = getattr(node, "end_lineno", node.lineno + 10)
        body = "\n".join(lines[node.lineno - 1:end_line])

        functions.append(FunctionInfo(
            name=node.name,
            file=str(path),
            lineno=node.lineno,
            args=args,
            return_annotation=ret,
            docstring=doc[:200],
            decorators=decos,
            body_source=body[:1500],
        ))

    return functions


def find_callers(target_name: str, project_dir: str) -> list[str]:
    """프로젝트에서 특정 함수를 호출하는 파일 목록."""
    callers = []
    for py in Path(project_dir).rglob("*.py"):
        try:
            source = py.read_text(encoding="utf-8", errors="replace")
            if target_name in source:
                callers.append(str(py))
        except Exception:
            continue
    return callers
