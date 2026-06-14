from backend.agents.state import MathClaim
from backend.tools.matching_tools import claim_aliases, extract_numbers


def test_claim_aliases_do_not_treat_parsing_as_sine():
    claim = MathClaim(
        "claim_1",
        "hyperparameter",
        "During constituency parsing inference, maximum output length is input length + 300.",
        None,
        "Unknown",
        0,
        "",
        0.9,
    )
    assert "sin" not in claim_aliases(claim)
    assert "timing_signal" not in claim_aliases(claim)


def test_extract_numbers_supports_paper_notation():
    assert extract_numbers("warmup_steps = 4000") == [4000.0]
    assert extract_numbers("epsilon = 10^{-9}") == [1e-09]
    assert extract_numbers("trained for 100K steps")[0] == 100000.0
