from __future__ import annotations

from backend.agents.state import AuditState
from backend.tools.github_tools import fetch_relevant_python_files


def run(state: AuditState) -> AuditState:
    state["current_node"] = "map_repo"
    try:
        structure, relevant, contents = fetch_relevant_python_files(state["repo_url"])
        state["repo_structure"] = structure
        state["relevant_files"] = relevant
        state["file_contents"] = contents
    except Exception as exc:
        state["errors"].append(f"Repository mapping failed: {exc}")
    state["sse_events"].append({"step": "repo_mapped", "files": len(state["file_contents"])})
    return state
