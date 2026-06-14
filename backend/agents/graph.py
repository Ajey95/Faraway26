from __future__ import annotations

from langgraph.graph import END, StateGraph

from backend.agents.state import AuditState
from backend.agents.nodes import ast_auditor, claim_extractor, paper_fetcher, repo_mapper, report_writer, verifier


def should_retry_extraction(state: AuditState) -> str:
    if state["claims"]:
        return "map_repo"
    if state["claim_extraction_attempts"] >= 2:
        return "map_repo"
    return "extract_claims"


def build_graph():
    graph = StateGraph(AuditState)
    graph.add_node("fetch_paper", paper_fetcher.run)
    graph.add_node("extract_claims", claim_extractor.run)
    graph.add_node("map_repo", repo_mapper.run)
    graph.add_node("audit_code", ast_auditor.run)
    graph.add_node("verify_claims", verifier.run)
    graph.add_node("write_report", report_writer.run)
    graph.set_entry_point("fetch_paper")
    graph.add_edge("fetch_paper", "extract_claims")
    graph.add_conditional_edges("extract_claims", should_retry_extraction, {"map_repo": "map_repo", "extract_claims": "extract_claims"})
    graph.add_edge("map_repo", "audit_code")
    graph.add_edge("audit_code", "verify_claims")
    graph.add_edge("verify_claims", "write_report")
    graph.add_edge("write_report", END)
    return graph.compile()
