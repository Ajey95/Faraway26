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


def test_transformer_hparams_pass_when_core_settings_are_present():
    paper_claim = claim(
        "hyperparameter",
        "The base Transformer uses N=6 layers, d_model=512, d_ff=2048, h=8, dropout=0.1, and label smoothing=0.1",
        "base 6 512 2048 8 0.1 0.1",
        "N=6, d_model=512, d_ff=2048, h=8, dropout=0.1, label_smoothing=0.1",
    )
    code = """
def transformer_base_v1():
    hparams.hidden_size = 512
    hparams.num_hidden_layers = 6
    hparams.add_hparam("filter_size", 2048)
    hparams.add_hparam("num_heads", 8)
    hparams.layer_prepostprocess_dropout = 0.1
    hparams.label_smoothing = 0.1
"""
    verdict = verify_claim(paper_claim, [evidence(code)])
    assert verdict.status == "pass"


def test_attention_formula_passes_on_implementation_pattern():
    paper_claim = claim(
        "formula",
        "Scaled dot-product attention computes softmax(QK^T / sqrt(d_k)) V",
        "Attention(Q,K,V)=softmax(QK^T/sqrt(d_k))V",
        r"Attention(Q,K,V)=softmax(QK^T/sqrt(d_k))V",
    )
    code = """
def dot_product_attention(q, k, v, bias):
    logits = tf.matmul(q, k, transpose_b=True)
    weights = tf.nn.softmax(logits + bias)
    return tf.matmul(weights, v)
"""
    verdict = verify_claim(paper_claim, [evidence(code)])
    assert verdict.status == "pass"
