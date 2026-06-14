from backend.agents.nodes.verifier import verify_claim
from backend.agents.state import CodeEvidence, MathClaim
from backend.tools.math_tools import normalize_expression, sympy_equivalent


def claim(claim_type="hyperparameter", description="dropout is 0.1", raw_text="We use dropout 0.1", latex=None):
    return MathClaim("claim_1", claim_type, description, latex, "Section 1", 1, raw_text, 0.9)


def evidence(snippet="dropout = 0.1"):
    return CodeEvidence("claim_1", "model.py", 10, 10, snippet, "build_model", True, "ast_function")


def test_hyperparameter_match_passes_when_numeric_value_is_present():
    verdict = verify_claim(claim(), [evidence("self.dropout = 0.1")])
    assert verdict.status == "pass"
    assert verdict.confidence >= 0.8


def test_hyperparameter_mismatch_fails_when_related_code_has_different_value():
    verdict = verify_claim(claim(), [evidence("self.dropout = 0.3")])
    assert verdict.status == "fail"
    assert "Paper values" in verdict.discrepancy


def test_missing_evidence_returns_not_found():
    verdict = verify_claim(claim(), [])
    assert verdict.status == "not_found"


def test_simple_symbolic_equivalence_helper():
    assert normalize_expression(r"x^2 + 2*x + 1") == "x**2 + 2*x + 1"
    assert sympy_equivalent("x**2 + 2*x + 1", "(x + 1)**2")
