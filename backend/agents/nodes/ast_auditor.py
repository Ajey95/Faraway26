from __future__ import annotations

from backend.agents.state import AuditState, CodeEvidence
from backend.tools.ast_tools import extract_constants, extract_functions


def run(state: AuditState) -> AuditState:
    state["current_node"] = "audit_code"
    functions, constants, evidence = {}, {}, []
    claim_terms = [(claim.claim_id, claim.description.lower()) for claim in state["claims"]]
    for path, source in state["file_contents"].items():
        try:
            functions[path] = extract_functions(source)
            constants[path] = extract_constants(source)
            for function in functions[path]:
                haystack = f"{function['name']}\n{function['source']}".lower()
                for claim_id, description in claim_terms:
                    if any(term and term in haystack for term in description.split() if len(term) > 4):
                        evidence.append(CodeEvidence(claim_id, path, function["line_start"], function["line_end"], function["source"], function["name"], True, "ast_function"))
                        break
        except Exception as exc:
            state["errors"].append(f"AST parse failed for {path}: {exc}")
    state["ast_functions"] = functions
    state["ast_constants"] = constants
    state["code_evidence"] = evidence
    state["sse_events"].append({"step": "code_audited", "functions": sum(len(v) for v in functions.values()), "evidence": len(evidence)})
    return state
