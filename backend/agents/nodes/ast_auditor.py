from __future__ import annotations

from backend.agents.state import AuditState, CodeEvidence
from backend.tools.ast_tools import extract_constants, extract_functions
from backend.tools.matching_tools import evidence_relevance

MAX_EVIDENCE_PER_CLAIM = 6
MIN_EVIDENCE_SCORE = 2.0


def run(state: AuditState) -> AuditState:
    state["current_node"] = "audit_code"
    functions, constants, evidence = {}, {}, []
    function_entries = []
    for path, source in state["file_contents"].items():
        try:
            functions[path] = extract_functions(source)
            constants[path] = extract_constants(source)
            for function in functions[path]:
                function_entries.append((path, function))
        except Exception as exc:
            state["errors"].append(f"AST parse failed for {path}: {exc}")

    for claim in state["claims"]:
        ranked = sorted(
            (
                (evidence_relevance(claim, path, function["name"], function["source"]), path, function)
                for path, function in function_entries
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        for score, path, function in ranked[:MAX_EVIDENCE_PER_CLAIM]:
            if score < MIN_EVIDENCE_SCORE:
                continue
            evidence.append(
                CodeEvidence(
                    claim.claim_id,
                    path,
                    function["line_start"],
                    function["line_end"],
                    function["source"],
                    function["name"],
                    True,
                    "ranked_ast_function",
                )
            )

    state["ast_functions"] = functions
    state["ast_constants"] = constants
    state["code_evidence"] = evidence
    state["sse_events"].append({"step": "code_audited", "functions": sum(len(v) for v in functions.values()), "evidence": len(evidence)})
    return state
