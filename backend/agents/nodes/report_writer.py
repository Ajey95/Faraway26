from __future__ import annotations

from collections import Counter

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.agents.state import AuditState


def run(state: AuditState) -> AuditState:
    state["current_node"] = "write_report"
    counts = Counter(verdict.status for verdict in state["verdicts"])
    state["score_breakdown"] = {key: counts.get(key, 0) for key in ["pass", "fail", "partial", "not_found"]}
    total = max(len(state["verdicts"]), 1)
    state["reproducibility_score"] = (counts.get("pass", 0) + 0.5 * counts.get("partial", 0)) / total
    state["report_markdown"] = f"# Reproducibility Audit\n\nScore: {state['reproducibility_score']:.0%}\n"
    env = Environment(loader=FileSystemLoader("backend/templates"), autoescape=select_autoescape())
    state["report_html"] = env.get_template("report.html.j2").render(state=state)
    state["sse_events"].append({"step": "report_written", "score": state["reproducibility_score"]})
    return state
