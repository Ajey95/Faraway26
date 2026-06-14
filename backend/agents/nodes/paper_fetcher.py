from __future__ import annotations

import re

import arxiv
import requests

from backend.agents.state import AuditState
from backend.tools.metadata_tools import check_retraction, get_semantic_scholar
from backend.tools.pdf_tools import extract_text, ocr_fallback

ARXIV_PATTERN = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def run(state: AuditState) -> AuditState:
    state["current_node"] = "fetch_paper"
    paper_url = state["paper_url"].strip()
    arxiv_id = paper_url[6:].strip() if paper_url.startswith("arxiv:") else paper_url if ARXIV_PATTERN.match(paper_url) else None
    metadata: dict = {"title": "Unknown", "authors": [], "year": None, "arxiv_id": arxiv_id, "abstract": ""}
    pdf_url = paper_url
    if arxiv_id:
        result = next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))
        pdf_url = result.pdf_url
        metadata.update({"title": result.title, "authors": [str(author) for author in result.authors], "year": result.published.year, "abstract": result.summary[:500]})
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        text = extract_text(response.content) or ocr_fallback(response.content)
    except Exception as exc:
        state["errors"].append(f"Paper fetch failed: {exc}")
        text = ""
    if arxiv_id:
        ss_data = get_semantic_scholar(arxiv_id)
        metadata["citation_count"] = ss_data.get("citationCount", 0)
        metadata["retracted"] = check_retraction(arxiv_id)
    state["paper_text"] = text
    state["paper_metadata"] = metadata
    state["sse_events"].append({"step": "paper_fetched", "title": metadata.get("title"), "chars": len(text), "retracted": metadata.get("retracted", False)})
    return state
