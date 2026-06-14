from __future__ import annotations

import json
import os
import re
import uuid

from openai import OpenAI

from backend.agents.state import AuditState, MathClaim
from backend.tools.math_tools import extract_latex_patterns

PAGE_NUMBER_PATTERN = re.compile(r"-?\d+")
VALID_CLAIM_TYPES = {"formula", "hyperparameter", "algorithm", "activation", "loss", "optimizer"}

EXTRACTION_SYSTEM_PROMPT = """You are a mathematical claim extractor for AI/ML research papers.
Your sole job is to identify every mathematical specification that could be verified by examining source code.
Output a JSON array of objects with keys: claim_type, description, latex, verbatim_text, section, page_hint, confidence.
Include only formula, hyperparameter, algorithm, activation, loss, or optimizer claims with confidence > 0.6."""
RETRY_SYSTEM_PROMPT = """The previous extraction returned no claims. Try again with confidence > 0.3 and look for hyperparameters, function names, and equations described in words. Output the same JSON array format."""


def chunk_text(text: str, max_chars: int = 24000) -> list[str]:
    sections = re.split(r"\n(?=\d+[\.\s]+[A-Z]|Abstract\b|Introduction\b|Conclusion\b|Methodology\b|Experiments?\b)", text)
    chunks, current = [], ""
    for section in sections:
        if len(current) + len(section) < max_chars:
            current += section
        else:
            if current:
                chunks.append(current)
            current = section
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def parse_model_response(response_text: str) -> list[dict]:
    clean = re.sub(r"```(?:json)?\n?", "", response_text).strip().rstrip("`")
    match = re.search(r"\[.*\]", clean, re.DOTALL)
    if not match:
        return []
    payload = match.group()
    repaired = re.sub(r",\s*([}\]])", r"\1", payload)
    repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", repaired)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return []


def parse_page_hint(value: object) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))

    match = PAGE_NUMBER_PATTERN.search(str(value))
    if not match:
        return 0
    return max(0, int(match.group()))


def normalize_claim_item(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None

    description = (
        item.get("description")
        or item.get("claim")
        or item.get("text")
        or item.get("verbatim_text")
        or item.get("raw_text")
    )
    if not description:
        return None

    claim_type = str(item.get("claim_type") or item.get("type") or "").strip().lower()
    if claim_type not in VALID_CLAIM_TYPES:
        claim_type = "formula" if item.get("latex") else "algorithm"

    try:
        confidence = float(item.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "claim_type": claim_type,
        "description": str(description),
        "latex": item.get("latex"),
        "section": item.get("section", "Unknown"),
        "page_hint": item.get("page_hint"),
        "verbatim_text": item.get("verbatim_text") or item.get("raw_text") or str(description),
        "confidence": confidence,
    }


def run(state: AuditState) -> AuditState:
    state["current_node"] = "extract_claims"
    state["claim_extraction_attempts"] += 1
    if not os.getenv("OPENAI_API_KEY"):
        latex_claims = extract_latex_patterns(state["paper_text"])[:10]
        state["claims"] = [MathClaim(f"claim_{i:03d}", "formula", "Formula extracted by offline regex fallback", latex, "Unknown", 0, latex, 0.35) for i, latex in enumerate(latex_claims, 1)]
    else:
        client = OpenAI()
        prompt = RETRY_SYSTEM_PROMPT if state["claim_extraction_attempts"] > 1 else EXTRACTION_SYSTEM_PROMPT
        claims = []
        for chunk in chunk_text(state["paper_text"][:120000]):
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
                instructions=prompt,
                input=chunk,
                max_output_tokens=4096,
            )
            claims.extend(parse_model_response(response.output_text))
        normalized_claims = [claim for claim in (normalize_claim_item(item) for item in claims) if claim]
        state["claims"] = [
            MathClaim(
                f"claim_{uuid.uuid4().hex[:8]}",
                item["claim_type"],
                item["description"],
                item.get("latex"),
                item.get("section", "Unknown"),
                parse_page_hint(item.get("page_hint")),
                item.get("verbatim_text", ""),
                float(item.get("confidence", 0)),
            )
            for item in normalized_claims
        ]
    state["sse_events"].append({"step": "claims_extracted", "count": len(state["claims"]), "attempt": state["claim_extraction_attempts"]})
    return state
