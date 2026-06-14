from __future__ import annotations

import ast
from dataclasses import asdict, dataclass


@dataclass
class FunctionInfo:
    name: str
    line_start: int
    line_end: int
    source: str


@dataclass
class ConstantInfo:
    name: str
    value: object
    line: int


def extract_functions(source: str) -> list[dict]:
    lines = source.splitlines()
    tree = ast.parse(source)
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            functions.append(asdict(FunctionInfo(node.name, node.lineno, end, "\n".join(lines[node.lineno - 1:end]))))
    return functions


def extract_constants(source: str) -> list[dict]:
    tree = ast.parse(source)
    constants = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants.append(asdict(ConstantInfo(target.id, node.value.value, node.lineno)))
    return constants
