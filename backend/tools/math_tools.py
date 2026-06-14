from __future__ import annotations

import re

import sympy as sp


def extract_latex_patterns(text: str) -> list[str]:
    patterns = [r"\$\$(.*?)\$\$", r"\$(.*?)\$", r"\\\[(.*?)\\\]", r"\\\((.*?)\\\)"]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(match.strip() for match in re.findall(pattern, text, flags=re.DOTALL))
    return matches


def sympy_equivalent(left: str, right: str) -> bool:
    try:
        return sp.simplify(sp.sympify(left) - sp.sympify(right)) == 0
    except Exception:
        return False
