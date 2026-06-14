from backend.agents.nodes.claim_extractor import normalize_claim_item, parse_model_response, parse_page_hint


def test_parse_page_hint_accepts_model_text_labels():
    assert parse_page_hint("page 4") == 4
    assert parse_page_hint("p. 12") == 12
    assert parse_page_hint("4-5") == 4


def test_parse_page_hint_falls_back_for_empty_or_invalid_values():
    assert parse_page_hint(None) == 0
    assert parse_page_hint("") == 0
    assert parse_page_hint("unknown") == 0
    assert parse_page_hint(-2) == 0


def test_parse_model_response_repairs_latex_backslashes():
    response = r'''
[
  {
    "claim_type": "optimizer",
    "description": "Adam epsilon is 10^{-9}",
    "latex": "\epsilon = 10^{-9}",
    "verbatim_text": "epsilon",
    "section": "Training",
    "page_hint": "page 4",
    "confidence": 0.9,
  }
]
'''
    claims = parse_model_response(response)
    assert claims[0]["latex"] == r"\epsilon = 10^{-9}"
    assert claims[0]["page_hint"] == "page 4"


def test_normalize_claim_item_defaults_missing_claim_type():
    item = {"description": "The model uses dropout 0.1", "confidence": "0.8"}
    claim = normalize_claim_item(item)
    assert claim["claim_type"] == "algorithm"
    assert claim["description"] == "The model uses dropout 0.1"
    assert claim["confidence"] == 0.8


def test_normalize_claim_item_skips_unusable_items():
    assert normalize_claim_item("not a dict") is None
    assert normalize_claim_item({"claim_type": "formula"}) is None
