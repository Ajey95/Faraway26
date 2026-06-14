from __future__ import annotations

import json
import os
import re
import uuid

from openai import OpenAI

from backend.agents.state import AuditState, MathClaim
from backend.tools.math_tools import extract_latex_patterns

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
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return json.loads(re.sub(r",\s*([}\]])", r"\1", match.group()))


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
        state["claims"] = [MathClaim(f"claim_{uuid.uuid4().hex[:8]}", item["claim_type"], item["description"], item.get("latex"), item.get("section", "Unknown"), int(item.get("page_hint") or 0), item.get("verbatim_text", ""), float(item.get("confidence", 0))) for item in claims]
    state["sse_events"].append({"step": "claims_extracted", "count": len(state["claims"]), "attempt": state["claim_extraction_attempts"]})
    return state
