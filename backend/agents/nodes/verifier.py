from __future__ import annotations

import math
import re
from collections import defaultdict

from backend.agents.state import AuditState, CodeEvidence, MathClaim, Verdict
from backend.tools.math_tools import normalize_expression, sympy_equivalent

NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", re.IGNORECASE)
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _numbers(text: str) -> list[float]:
    values: list[float] = []
    for match in NUMBER_PATTERN.findall(text or ""):
        try:
            values.append(float(match))
        except ValueError:
            continue
    return values


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-9)


def _token_overlap(claim: MathClaim, evidence: CodeEvidence) -> float:
    claim_tokens = {token.lower() for token in IDENTIFIER_PATTERN.findall(f"{claim.description} {claim.raw_text}") if len(token) > 3}
    code_tokens = {token.lower() for token in IDENTIFIER_PATTERN.findall(f"{evidence.function_name} {evidence.code_snippet}") if len(token) > 3}
    if not claim_tokens or not code_tokens:
        return 0.0
    return len(claim_tokens & code_tokens) / len(claim_tokens | code_tokens)


def _formula_verdict(claim: MathClaim, evidence: CodeEvidence) -> Verdict | None:
    if not claim.latex:
        return None
    paper_expr = normalize_expression(claim.latex)
    code_expr = normalize_expression(evidence.code_snippet)
    if paper_expr and code_expr and sympy_equivalent(paper_expr, code_expr):
        return Verdict(
            claim.claim_id,
            "pass",
            0.92,
            f"Symbolic equivalence matched between the paper formula and {evidence.file_path}:{evidence.line_start}.",
            None,
            True,
        )
    return None


def _hyperparameter_verdict(claim: MathClaim, evidence: CodeEvidence) -> Verdict | None:
    if claim.claim_type not in {"hyperparameter", "optimizer"}:
        return None
    paper_numbers = _numbers(f"{claim.description} {claim.raw_text} {claim.latex or ''}")
    code_numbers = _numbers(evidence.code_snippet)
    if not paper_numbers:
        return None
    if any(_close(paper, code) for paper in paper_numbers for code in code_numbers):
        return Verdict(
            claim.claim_id,
            "pass",
            0.88,
            f"Matched claimed numeric setting in {evidence.file_path}:{evidence.line_start}.",
            None,
            False,
        )
    if code_numbers:
        return Verdict(
            claim.claim_id,
            "fail",
            0.72,
            f"Found related code in {evidence.file_path}:{evidence.line_start}, but numeric values differ.",
            f"Paper values {paper_numbers}; code values {code_numbers[:8]}",
            False,
        )
    return None


def _semantic_verdict(claim: MathClaim, evidence: CodeEvidence) -> Verdict:
    overlap = _token_overlap(claim, evidence)
    if claim.claim_type in {"activation", "loss", "algorithm", "formula"} and overlap >= 0.08:
        return Verdict(
            claim.claim_id,
            "partial",
            min(0.8, 0.52 + overlap),
            f"Found semantically related implementation evidence in {evidence.file_path}:{evidence.line_start}-{evidence.line_end}; manual review is still required for exact scientific equivalence.",
            "Semantic match found, but no deterministic equivalence proof was available.",
            False,
        )
    return Verdict(
        claim.claim_id,
        "partial",
        0.48,
        f"Found candidate implementation evidence in {evidence.file_path}:{evidence.line_start}-{evidence.line_end}, but the match is weak and needs review.",
        "Weak evidence match.",
        False,
    )


def verify_claim(claim: MathClaim, evidence_items: list[CodeEvidence]) -> Verdict:
    if not evidence_items:
        return Verdict(
            claim.claim_id,
            "not_found",
            0.84,
            "No matching implementation was found in the scanned relevant files.",
            "No code evidence linked to this claim.",
            False,
        )

    best_evidence = max(evidence_items, key=lambda item: _token_overlap(claim, item))
    return (
        _formula_verdict(claim, best_evidence)
        or _hyperparameter_verdict(claim, best_evidence)
        or _semantic_verdict(claim, best_evidence)
    )


def run(state: AuditState) -> AuditState:
    state["current_node"] = "verify_claims"
    evidence_by_claim: dict[str, list[CodeEvidence]] = defaultdict(list)
    for evidence in state["code_evidence"]:
        evidence_by_claim[evidence.claim_id].append(evidence)

    state["verdicts"] = [verify_claim(claim, evidence_by_claim.get(claim.claim_id, [])) for claim in state["claims"]]
    state["sse_events"].append({"step": "claims_verified", "verdicts": len(state["verdicts"])})
    return state
