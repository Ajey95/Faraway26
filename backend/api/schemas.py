from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class AuditRequest(BaseModel):
    paper_url: str = Field(..., examples=["arxiv:1706.03762"])
    repo_url: HttpUrl = Field(..., examples=["https://github.com/tensorflow/tensor2tensor"])
    audit_mode: Literal["quick", "deep", "full"] = "deep"


class ClaimSchema(BaseModel):
    claim_id: str
    claim_type: str
    description: str
    latex: str | None = None
    paper_section: str
    paper_page: int
    raw_text: str
    confidence: float


class VerdictSchema(BaseModel):
    claim_id: str
    status: str
    confidence: float
    reasoning: str
    discrepancy: str | None = None
    sympy_verified: bool


class AuditResult(BaseModel):
    audit_id: str
    status: str
    current_node: str
    reproducibility_score: float
    score_breakdown: dict[str, int]
    claims: list[ClaimSchema]
    verdicts: list[VerdictSchema]
    errors: list[str] = Field(default_factory=list)
    audit_mode: str = "deep"
