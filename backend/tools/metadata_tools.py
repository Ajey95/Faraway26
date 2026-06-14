from __future__ import annotations

import requests


def get_semantic_scholar(arxiv_id: str) -> dict:
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}?fields=citationCount,isOpenAccess,openAccessPdf"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


def check_retraction(arxiv_id: str) -> bool:
    data = get_semantic_scholar(arxiv_id)
    return bool(data.get("isRetracted", False))
