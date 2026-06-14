from __future__ import annotations

import math
import re

from backend.agents.state import MathClaim

TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])-?\d+(?:,\d{3})*(?:\.\d+)?(?:e[-+]?\d+)?\s*[Kk]?")
POWER_OF_TEN_PATTERN = re.compile(r"10\s*(?:\^|\*\*)\s*\{?\s*(-?\d+)\s*\}?")

STOP_WORDS = {
    "about",
    "against",
    "also",
    "and",
    "are",
    "base",
    "been",
    "being",
    "code",
    "computed",
    "during",
    "each",
    "from",
    "function",
    "implemented",
    "into",
    "layer",
    "layers",
    "model",
    "paper",
    "position",
    "setting",
    "that",
    "their",
    "these",
    "this",
    "used",
    "uses",
    "where",
    "with",
}


def claim_text(claim: MathClaim) -> str:
    return f"{claim.claim_type} {claim.description} {claim.raw_text} {claim.latex or ''}".lower()


def claim_tokens(claim: MathClaim) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(claim_text(claim))
        if len(token) > 2 and token.lower() not in STOP_WORDS
    }


def claim_aliases(claim: MathClaim) -> set[str]:
    text = claim_text(claim)
    aliases: set[str] = set()

    def has(*needles: str) -> bool:
        return any(needle in text for needle in needles)

    tokens = set(TOKEN_PATTERN.findall(text))

    if has("scaled dot", "dot-product", "dot product", "qk", "attention("):
        aliases.update({"dot_product_attention", "scaled_dot_product", "softmax", "matmul", "attention"})
    if has("multi-head", "multihead", "head_i", "heads"):
        aliases.update({"multihead_attention", "split_heads", "combine_heads", "num_heads", "attention"})
    if has("d_model", "model dimension", "dimensionality", "embedding"):
        aliases.update({"hidden_size", "d_model", "embedding"})
    if has("d_ff", "feed-forward", "feed forward", "ffn"):
        aliases.update({"filter_size", "ffn_layer", "dense_relu_dense", "relu", "conv_hidden_relu"})
    if has("d_k", "d_v", "key", "value"):
        aliases.update({"attention_key_channels", "attention_value_channels", "total_key_depth", "total_value_depth"})
    if has("encoder", "decoder", "identical layers", "n=6", "n = 6", "4 layers"):
        aliases.update({"num_hidden_layers", "num_encoder_layers", "num_decoder_layers"})
    if has("dropout", "p_drop"):
        aliases.update({"dropout", "layer_prepostprocess_dropout", "attention_dropout", "relu_dropout"})
    if has("label smoothing", "epsilon_ls"):
        aliases.update({"label_smoothing"})
    if has("adam", "optimizer", "beta_1", "beta1", "beta_2", "beta2", "epsilon"):
        aliases.update({"optimizer_adam_beta1", "optimizer_adam_beta2", "optimizer_adam_epsilon", "adam"})
    if has("warmup", "learning rate", "lrate", "noam"):
        aliases.update({"learning_rate_warmup_steps", "learning_rate_decay_scheme", "learning_rate_schedule", "noam"})
    if has("positional", "position-wise", "sine", "cosine") or "sin" in tokens or "cos" in tokens:
        aliases.update({"timing_signal", "add_timing_signal", "pos", "sin", "cos"})
    if has("layernorm", "layer norm", "normalization", "sublayer"):
        aliases.update({"layer_preprocess", "layer_postprocess", "layer_norm", "norm_type"})
    if has("beam", "length penalty", "alpha"):
        aliases.update({"beam_search", "beam_size", "alpha", "length_penalty"})
    if has("transformer"):
        aliases.update({"transformer", "transformer_base", "transformer_big"})

    return aliases


def extract_numbers(text: str) -> list[float]:
    if not text:
        return []

    values: list[float] = []
    for exponent in POWER_OF_TEN_PATTERN.findall(text):
        try:
            values.append(10 ** int(exponent))
        except ValueError:
            continue

    without_powers = POWER_OF_TEN_PATTERN.sub(" ", text)
    for raw in NUMBER_PATTERN.findall(without_powers):
        item = raw.strip().replace(",", "")
        multiplier = 1000 if item.lower().endswith("k") else 1
        item = item[:-1] if item.lower().endswith("k") else item
        try:
            values.append(float(item) * multiplier)
        except ValueError:
            continue

    deduped: list[float] = []
    for value in values:
        if not any(numbers_close(value, existing) for existing in deduped):
            deduped.append(value)
    return deduped


def numbers_close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-9)


def matched_numbers(paper_numbers: list[float], code_numbers: list[float]) -> list[float]:
    return [paper for paper in paper_numbers if any(numbers_close(paper, code) for code in code_numbers)]


def evidence_relevance(claim: MathClaim, file_path: str, function_name: str, code_snippet: str) -> float:
    text = f"{file_path}\n{function_name}\n{code_snippet}".lower()
    tokens = claim_tokens(claim)
    aliases = claim_aliases(claim)
    paper_numbers = extract_numbers(f"{claim.description} {claim.raw_text} {claim.latex or ''}")
    code_numbers = extract_numbers(code_snippet)

    score = 0.0
    score += 1.6 * sum(1 for alias in aliases if alias.lower() in text)
    score += 0.35 * sum(1 for token in tokens if token in text)
    score += 0.8 * len(matched_numbers(paper_numbers, code_numbers))

    lowered_path = file_path.lower()
    lowered_function = function_name.lower()
    if "tensor2tensor/models/transformer.py" in lowered_path:
        score += 3.5
    if "tensor2tensor/layers/common_attention.py" in lowered_path:
        score += 2.5
    if "tensor2tensor/layers/common_layers.py" in lowered_path:
        score += 1.5
    if "transformer" in lowered_path or "transformer" in lowered_function:
        score += 1.2
    if "hparams" in text and claim.claim_type in {"hyperparameter", "optimizer"}:
        score += 1.5
    if "/test" in lowered_path or lowered_path.endswith("_test.py"):
        score -= 2.0
    if "/rl/" in lowered_path and "reinforcement" not in claim_text(claim):
        score -= 3.0
    if "/research/" in lowered_path and "research" not in claim_text(claim):
        score -= 0.75

    return score
