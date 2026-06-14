from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, is_dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from backend.agents.graph import build_graph
from backend.agents.state import AuditState, initial_state
from backend.api.schemas import AuditRequest, AuditResult

router = APIRouter()
AUDITS: dict[str, AuditState] = {}
TASKS: dict[str, asyncio.Task] = {}


def _json_default(value):
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _result(state: AuditState) -> AuditResult:
    payload = json.loads(json.dumps(state, default=_json_default))
    status = "completed" if payload["current_node"] == "write_report" else "running"
    if payload["current_node"] == "failed":
        status = "failed"
    return AuditResult(
        audit_id=payload["audit_id"],
        status=status,
        current_node=payload["current_node"],
        audit_mode=payload.get("audit_mode", "deep"),
        reproducibility_score=payload["reproducibility_score"],
        score_breakdown=payload["score_breakdown"],
        claims=payload["claims"],
        verdicts=payload["verdicts"],
        errors=payload["errors"],
    )


async def _run_audit(audit_id: str) -> None:
    graph = build_graph()
    try:
        AUDITS[audit_id] = await asyncio.to_thread(graph.invoke, AUDITS[audit_id])
    except Exception as exc:  # keep API inspectable for early implementation failures
        AUDITS[audit_id]["errors"].append(str(exc))
        AUDITS[audit_id]["current_node"] = "failed"
        AUDITS[audit_id]["sse_events"].append({"step": "failed", "error": str(exc)})


@router.post("/audit", response_model=AuditResult, status_code=202)
async def create_audit(request: AuditRequest) -> AuditResult:
    audit_id = str(uuid.uuid4())
    AUDITS[audit_id] = initial_state(request.paper_url, str(request.repo_url), audit_id, request.audit_mode)
    TASKS[audit_id] = asyncio.create_task(_run_audit(audit_id))
    return _result(AUDITS[audit_id])


@router.get("/audit/{audit_id}", response_model=AuditResult)
async def get_audit(audit_id: str) -> AuditResult:
    if audit_id not in AUDITS:
        raise HTTPException(status_code=404, detail="Audit not found")
    return _result(AUDITS[audit_id])


@router.get("/audit/{audit_id}/stream")
async def stream_audit(audit_id: str):
    if audit_id not in AUDITS:
        raise HTTPException(status_code=404, detail="Audit not found")

    async def event_generator():
        cursor = 0
        while True:
            events = AUDITS[audit_id]["sse_events"]
            for event in events[cursor:]:
                yield {"event": event.get("step", "message"), "data": json.dumps(event)}
            cursor = len(events)
            if AUDITS[audit_id]["current_node"] in {"write_report", "failed"}:
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get("/audit/{audit_id}/report", response_class=HTMLResponse)
async def get_report(audit_id: str) -> HTMLResponse:
    if audit_id not in AUDITS:
        raise HTTPException(status_code=404, detail="Audit not found")
    return HTMLResponse(AUDITS[audit_id]["report_html"] or "<p>Report is not ready yet.</p>")


@router.get("/audits", response_model=list[AuditResult])
async def list_audits() -> list[AuditResult]:
    return [_result(state) for state in AUDITS.values()]
