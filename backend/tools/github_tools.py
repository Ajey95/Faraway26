from __future__ import annotations

import os
from urllib.parse import urlparse

from github import Github


def parse_repo_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError("GitHub repo URL must include owner and repository name")
    return f"{parts[0]}/{parts[1].removesuffix('.git')}"


def client() -> Github:
    return Github(os.getenv("GITHUB_TOKEN"))


def score_file_relevance(path: str) -> float:
    lowered = path.lower()
    score = 0.0
    if lowered == "tensor2tensor/models/transformer.py":
        score += 12.0
    if lowered == "tensor2tensor/layers/common_attention.py":
        score += 10.0
    if lowered == "tensor2tensor/layers/common_layers.py":
        score += 8.0
    if lowered == "tensor2tensor/utils/beam_search.py":
        score += 6.0
    for token in ("transformer", "attention", "hparam", "common", "beam", "model", "loss", "optim", "train", "activation", "bert", "config"):
        if token in lowered:
            score += 1.0
    if lowered.endswith(".py"):
        score += 0.5
    if lowered.endswith("_test.py") or "/test" in lowered:
        score -= 3.0
    if "/rl/" in lowered:
        score -= 4.0
    if "/research/" in lowered:
        score -= 1.0
    if "/models/research/" in lowered and "transformer" not in lowered:
        score -= 1.0
    return score


def fetch_relevant_python_files(repo_url: str, limit: int = 25) -> tuple[dict, list[str], dict[str, str]]:
    repo = client().get_repo(parse_repo_url(repo_url))
    tree = repo.get_git_tree(repo.default_branch, recursive=True).tree
    files = [item.path for item in tree if item.type == "blob" and item.path.endswith(".py")]
    ranked = sorted(files, key=score_file_relevance, reverse=True)[:limit]
    contents = {}
    for path in ranked:
        try:
            contents[path] = repo.get_contents(path).decoded_content.decode("utf-8", errors="replace")
        except Exception:
            contents[path] = ""
    structure = {path: {"type": "file", "relevance_score": score_file_relevance(path)} for path in files}
    return structure, ranked, contents
