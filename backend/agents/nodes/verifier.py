from __future__ import annotations

import re
from collections import defaultdict

from backend.agents.state import AuditState, CodeEvidence, MathClaim, Verdict
from backend.tools.math_tools import normalize_expression, sympy_equivalent
from backend.tools.matching_tools import claim_aliases, claim_text, evidence_relevance, extract_numbers, matched_numbers

IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _numbers(text: str) -> list[float]:
    return extract_numbers(text)


def _token_overlap(claim: MathClaim, evidence: CodeEvidence) -> float:
    claim_tokens = {token.lower() for token in IDENTIFIER_PATTERN.findall(f"{claim.description} {claim.raw_text}") if len(token) > 3}
    code_tokens = {token.lower() for token in IDENTIFIER_PATTERN.findall(f"{evidence.function_name} {evidence.code_snippet}") if len(token) > 3}
    if not claim_tokens or not code_tokens:
        return 0.0
    return len(claim_tokens & code_tokens) / len(claim_tokens | code_tokens)


def _ranked_evidence(claim: MathClaim, evidence_items: list[CodeEvidence]) -> list[CodeEvidence]:
    return sorted(
        evidence_items,
        key=lambda item: evidence_relevance(claim, item.file_path, item.function_name, item.code_snippet),
        reverse=True,
    )


def _implementation_pattern(claim: MathClaim, evidence: CodeEvidence) -> str | None:
    text = claim_text(claim)
    code = f"{evidence.function_name}\n{evidence.code_snippet}".lower()

    if "attention" in text and "dot_product_attention" in code and "softmax" in code and "matmul" in code:
        return "scaled dot-product attention"
    if ("multi-head" in text or "multihead" in text) and ("multihead_attention" in code or "split_heads" in code):
        return "multi-head attention"
    if ("feed-forward" in text or "ffn" in text) and ("dense_relu_dense" in code or "ffn_layer" in code or "relu" in code):
        return "position-wise feed-forward network"
    if "positional" in text and ("timing_signal" in code or ("sin" in code and "cos" in code)):
        return "sinusoidal positional encoding"
    if ("learning rate" in text or "lrate" in text or "warmup" in text) and ("noam" in code or "learning_rate_warmup_steps" in code):
        return "Transformer learning-rate schedule"
    if ("layernorm" in text or "layer norm" in text or "sublayer" in text) and ("layer_preprocess" in code or "layer_postprocess" in code or "norm_type" in code):
        return "residual layer normalization"
    if "beam" in text and ("beam_search" in code or "beam_size" in code or "alpha" in code):
        return "beam-search decoding"
    return None


def _formula_verdict(claim: MathClaim, evidence_items: list[CodeEvidence]) -> Verdict | None:
    if not claim.latex:
        return None

    for evidence in _ranked_evidence(claim, evidence_items):
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

        pattern = _implementation_pattern(claim, evidence)
        if pattern:
            return Verdict(
                claim.claim_id,
                "pass",
                0.84,
                f"Matched the {pattern} implementation in {evidence.file_path}:{evidence.line_start}-{evidence.line_end}.",
                None,
                False,
            )
    return None


def _hyperparameter_verdict(claim: MathClaim, evidence_items: list[CodeEvidence]) -> Verdict | None:
    if claim.claim_type not in {"hyperparameter", "optimizer"}:
        return None
    paper_numbers = _numbers(f"{claim.description} {claim.raw_text} {claim.latex or ''}")
    if not paper_numbers:
        return None

    best_partial: Verdict | None = None
    aliases = claim_aliases(claim)
    for evidence in _ranked_evidence(claim, evidence_items):
        relevance = evidence_relevance(claim, evidence.file_path, evidence.function_name, evidence.code_snippet)
        code_numbers = _numbers(evidence.code_snippet)
        matches = matched_numbers(paper_numbers, code_numbers)
        ratio = len(matches) / max(len(paper_numbers), 1)

        if matches and (len(paper_numbers) == 1 or ratio >= 0.45 or len(matches) >= 2):
            return Verdict(
                claim.claim_id,
                "pass",
                min(0.94, 0.78 + 0.04 * len(matches)),
                f"Matched claimed numeric setting(s) {matches} in {evidence.file_path}:{evidence.line_start}-{evidence.line_end}.",
                None,
                False,
            )

        if matches:
            best_partial = Verdict(
                claim.claim_id,
                "partial",
                0.68,
                f"Matched some claimed numeric setting(s) {matches} in {evidence.file_path}:{evidence.line_start}-{evidence.line_end}, but not enough values for a full pass.",
                f"Paper values {paper_numbers}; matched values {matches}.",
                False,
            )
            continue

        has_alias = any(alias.lower() in evidence.code_snippet.lower() or alias.lower() in evidence.function_name.lower() for alias in aliases)
        if has_alias and code_numbers and relevance >= 1.5:
            best_partial = best_partial or Verdict(
                claim.claim_id,
                "fail",
                0.7,
                f"Found the relevant implementation setting in {evidence.file_path}:{evidence.line_start}, but numeric values differ.",
                f"Paper values {paper_numbers}; code values {code_numbers[:10]}.",
                False,
            )

    return best_partial


def _semantic_verdict(claim: MathClaim, evidence: CodeEvidence) -> Verdict:
    pattern = _implementation_pattern(claim, evidence)
    if pattern:
        return Verdict(
            claim.claim_id,
            "pass",
            0.82,
            f"Matched the {pattern} implementation in {evidence.file_path}:{evidence.line_start}-{evidence.line_end}.",
            None,
            False,
        )

    overlap = _token_overlap(claim, evidence)
    relevance = evidence_relevance(claim, evidence.file_path, evidence.function_name, evidence.code_snippet)
    if claim.claim_type in {"activation", "loss", "algorithm", "formula"} and (overlap >= 0.08 or relevance >= 4.0):
        return Verdict(
            claim.claim_id,
            "partial",
            min(0.8, 0.52 + overlap + min(relevance, 5.0) / 20),
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

    best_evidence = max(evidence_items, key=lambda item: evidence_relevance(claim, item.file_path, item.function_name, item.code_snippet))
    return (
        _formula_verdict(claim, evidence_items)
        or _hyperparameter_verdict(claim, evidence_items)
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
