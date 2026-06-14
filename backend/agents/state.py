from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, TypedDict


ClaimType = Literal["formula", "hyperparameter", "algorithm", "activation", "loss", "optimizer"]
VerdictStatus = Literal["pass", "fail", "partial", "not_found"]


@dataclass
class MathClaim:
    claim_id: str
    claim_type: ClaimType
    description: str
    latex: Optional[str]
    paper_section: str
    paper_page: int
    raw_text: str
    confidence: float


@dataclass
class CodeEvidence:
    claim_id: str
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    function_name: str
    ast_extracted: bool
    extraction_method: str


@dataclass
class Verdict:
    claim_id: str
    status: VerdictStatus
    confidence: float
    reasoning: str
    discrepancy: Optional[str] = None
    sympy_verified: bool = False


class AuditState(TypedDict):
    paper_url: str
    repo_url: str
    audit_id: str
    audit_mode: str
    paper_text: str
    paper_metadata: dict
    claims: list[MathClaim]
    claim_extraction_attempts: int
    repo_structure: dict
    relevant_files: list[str]
    file_contents: dict[str, str]
    ast_functions: dict
    ast_constants: dict
    code_evidence: list[CodeEvidence]
    verdicts: list[Verdict]
    report_markdown: str
    report_html: str
    reproducibility_score: float
    score_breakdown: dict[str, int]
    current_node: str
    errors: list[str]
    sse_events: list[dict]


def initial_state(paper_url: str, repo_url: str, audit_id: str, audit_mode: str = "deep") -> AuditState:
    return {
        "paper_url": paper_url,
        "repo_url": repo_url,
        "audit_id": audit_id,
        "audit_mode": audit_mode,
        "paper_text": "",
        "paper_metadata": {},
        "claims": [],
        "claim_extraction_attempts": 0,
        "repo_structure": {},
        "relevant_files": [],
        "file_contents": {},
        "ast_functions": {},
        "ast_constants": {},
        "code_evidence": [],
        "verdicts": [],
        "report_markdown": "",
        "report_html": "",
        "reproducibility_score": 0.0,
        "score_breakdown": {"pass": 0, "fail": 0, "partial": 0, "not_found": 0},
        "current_node": "queued",
        "errors": [],
        "sse_events": [],
    }
