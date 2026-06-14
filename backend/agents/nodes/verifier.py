from __future__ import annotations

from backend.agents.state import AuditState, Verdict


def run(state: AuditState) -> AuditState:
    state["current_node"] = "verify_claims"
    verdicts = []
    evidence_by_claim = {evidence.claim_id: evidence for evidence in state["code_evidence"]}
    for claim in state["claims"]:
        evidence = evidence_by_claim.get(claim.claim_id)
        if evidence:
            verdicts.append(Verdict(claim.claim_id, "partial", 0.55, f"Found likely implementation in {evidence.file_path}:{evidence.line_start}, but algebraic verification is not implemented yet.", "Requires symbolic mapping", False))
        else:
            verdicts.append(Verdict(claim.claim_id, "not_found", 0.8, "No matching implementation was found in the scanned relevant files.", None, False))
    state["verdicts"] = verdicts
    state["sse_events"].append({"step": "claims_verified", "verdicts": len(verdicts)})
    return state
