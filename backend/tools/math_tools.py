from __future__ import annotations

import math
import re

try:
    import sympy as sp
except Exception:  # pragma: no cover - exercised in minimal environments without sympy
    sp = None


def extract_latex_patterns(text: str) -> list[str]:
    patterns = [r"\$\$(.*?)\$\$", r"\$(.*?)\$", r"\\\[(.*?)\\\]", r"\\\((.*?)\\\)"]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(match.strip() for match in re.findall(pattern, text, flags=re.DOTALL))
    return matches


def normalize_expression(text: str) -> str:
    """Best-effort conversion of simple LaTeX/Python math snippets into sympy/eval text."""
    if not text:
        return ""
    expr = text.strip()
    expr = re.sub(r"```.*?```", "", expr, flags=re.DOTALL)
    expr = re.sub(r"return\s+", "", expr)
    expr = expr.replace("\\cdot", "*").replace("\\times", "*")
    expr = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", expr)
    expr = expr.replace("^", "**")
    expr = expr.replace("math.", "").replace("np.", "").replace("torch.", "")
    expr = re.sub(r"[^A-Za-z0-9_+\-*/().,\s]", " ", expr)
    candidates = [line.strip() for line in expr.splitlines() if line.strip()]
    if not candidates:
        return ""
    return max(candidates, key=len)


def _numeric_equivalent(left: str, right: str) -> bool:
    names = sorted(set(re.findall(r"\b[a-zA-Z_]\w*\b", f"{left} {right}")) - set(dir(math)))
    safe_math = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
    samples = [-2.0, -0.5, 0.25, 1.5, 3.0]
    for value in samples:
        env = {**safe_math, **{name: value for name in names}}
        try:
            if not math.isclose(float(eval(left, {"__builtins__": {}}, env)), float(eval(right, {"__builtins__": {}}, env)), rel_tol=1e-6, abs_tol=1e-8):
                return False
        except Exception:
            return False
    return True


def sympy_equivalent(left: str, right: str) -> bool:
    if sp is not None:
        try:
            return sp.simplify(sp.sympify(left) - sp.sympify(right)) == 0
        except Exception:
            pass
    return _numeric_equivalent(left, right)
