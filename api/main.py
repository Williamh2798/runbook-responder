"""Runbook Responder API — webhook + agent endpoints for UiPath Maestro integration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings

from agents.investigation_agent import investigate
from api.models import (
    AlertPayload,
    CaseRecord,
    CaseStage,
    InvestigationRequest,
    InvestigationResult,
    RemediationRequest,
    RemediationResult,
    Severity,
    TriageResult,
)
from demo.incidents import DEMO_INCIDENTS

app = FastAPI(
    title="Runbook Responder API",
    description="Agentic incident response backend for UiPath Maestro Case orchestration",
    version="1.0.0",
)

# In-memory store for demo (replace with UiPath Maestro Case in production)
_cases: dict[str, CaseRecord] = {}
_alerts: dict[str, AlertPayload] = {}


class Settings(BaseSettings):
    uipath_webhook_url: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append_timeline(case: CaseRecord, event: str, details: dict | None = None) -> None:
    case.timeline.append(
        {
            "timestamp": _now().isoformat(),
            "event": event,
            "details": details or {},
        }
    )
    case.updated_at = _now()


def triage_alert(alert: AlertPayload) -> TriageResult:
    """Classify severity and blast radius for Maestro Case opening."""
    severity_scores = {
        Severity.CRITICAL: 95,
        Severity.HIGH: 75,
        Severity.MEDIUM: 50,
        Severity.LOW: 25,
    }
    base = severity_scores.get(alert.severity, 50)

    blast_map = {
        "order-service": "Customer checkout and order placement affected",
        "payment-api": "Payment processing degraded; revenue impact likely",
        "checkout-service": "End-user checkout flow blocked",
        "payment-gateway": "All dependent payment services affected",
    }
    blast = blast_map.get(alert.service, f"Unknown blast radius for {alert.service}")

    return TriageResult(
        alert_id=alert.alert_id,
        severity=alert.severity,
        blast_radius=blast,
        priority_score=base,
        case_stage=CaseStage.TRIAGE,
        summary=f"{alert.severity.value.upper()} alert on {alert.service}: {alert.title}",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "runbook-responder", "cases_open": len(_cases)}


@app.get("/")
def root() -> dict:
    return {
        "name": "Runbook Responder",
        "docs": "/docs",
        "endpoints": {
            "ingest_alert": "POST /webhooks/alert",
            "triage": "POST /agents/triage",
            "investigate": "POST /agents/investigate",
            "remediate": "POST /remediation/execute",
            "case_status": "GET /cases/{case_id}",
            "demo_incidents": "GET /demo/incidents",
        },
    }


@app.get("/demo/incidents")
def list_demo_incidents() -> dict:
    """List pre-built demo scenarios for judges and video recording."""
    return {
        slug: {
            "alert_id": data["alert"].alert_id,
            "service": data["alert"].service,
            "title": data["alert"].title,
            "severity": data["alert"].severity.value,
        }
        for slug, data in DEMO_INCIDENTS.items()
    }


@app.post("/webhooks/alert")
async def ingest_alert(alert: AlertPayload) -> dict:
    """Receive monitoring alert and open a Maestro Case (UiPath calls this or vice versa)."""
    case_id = f"case-{uuid.uuid4().hex[:8]}"
    triage = triage_alert(alert)
    _alerts[alert.alert_id] = alert

    case = CaseRecord(
        case_id=case_id,
        alert_id=alert.alert_id,
        service=alert.service,
        stage=CaseStage.TRIAGE,
        severity=alert.severity,
        title=alert.title,
    )
    _append_timeline(case, "alert_received", alert.model_dump(mode="json"))
    _append_timeline(case, "triage_complete", triage.model_dump(mode="json"))
    case.stage = CaseStage.INVESTIGATE
    _cases[case_id] = case

    payload = {
        "case_id": case_id,
        "alert": alert.model_dump(mode="json"),
        "triage": triage.model_dump(mode="json"),
        "next_stage": CaseStage.INVESTIGATE.value,
    }

    if settings.uipath_webhook_url:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(settings.uipath_webhook_url, json=payload)

    return payload


@app.post("/agents/triage", response_model=TriageResult)
def agent_triage(alert: AlertPayload) -> TriageResult:
    """UiPath Agent Builder / API Workflow: triage an alert."""
    return triage_alert(alert)


@app.post("/agents/investigate", response_model=InvestigationResult)
def agent_investigate(request: InvestigationRequest) -> InvestigationResult:
    """UiPath API Workflow: coded investigation agent endpoint."""
    result = investigate(request)

    for case in _cases.values():
        if case.alert_id == request.alert_id:
            case.investigation = result
            case.stage = CaseStage.AWAIT_APPROVAL
            _append_timeline(case, "investigation_complete", result.model_dump(mode="json"))
            break

    return result


@app.post("/remediation/execute", response_model=RemediationResult)
def execute_remediation(request: RemediationRequest) -> RemediationResult:
    """Execute approved remediation (mocked for demo). Requires human approval in Maestro."""
    messages = {
        "restart_service": f"Restarted {request.service} pods; health checks passing",
        "rollback_deploy": f"Rolled back {request.service} to previous stable version",
        "revoke_token": f"Revoked and rotated service token for {request.service}",
        "scale_up": f"Scaled {request.service} replicas; CPU normalized",
        "no_action": "No automated action taken; escalated for manual review",
    }
    result = RemediationResult(
        alert_id=request.alert_id,
        action=request.action,
        status="success",
        message=messages.get(request.action.value, "Action completed"),
    )

    for case in _cases.values():
        if case.alert_id == request.alert_id:
            case.remediation = result
            case.stage = CaseStage.VERIFY
            _append_timeline(
                case,
                "remediation_executed",
                {"approved_by": request.approved_by, **result.model_dump(mode="json")},
            )
            case.stage = CaseStage.CLOSED
            _append_timeline(case, "case_closed", {"verified": True})
            break

    return result


@app.get("/cases/{case_id}", response_model=CaseRecord)
def get_case(case_id: str) -> CaseRecord:
    """Full case timeline for Maestro Case audit trail / demo."""
    if case_id not in _cases:
        raise HTTPException(status_code=404, detail="Case not found")
    return _cases[case_id]


@app.post("/demo/run/{slug}")
def run_demo_scenario(slug: str) -> dict:
    """Run a full demo scenario end-to-end (for video recording)."""
    if slug not in DEMO_INCIDENTS:
        raise HTTPException(status_code=404, detail=f"Unknown demo slug. Available: {list(DEMO_INCIDENTS)}")

    data = DEMO_INCIDENTS[slug]
    alert: AlertPayload = data["alert"]
    logs = data["logs"]

    triage = triage_alert(alert)
    investigation = investigate(
        InvestigationRequest(
            alert_id=alert.alert_id,
            service=alert.service,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            error_signature=alert.error_signature,
            logs=logs,
        )
    )

    return {
        "scenario": slug,
        "triage": triage.model_dump(mode="json"),
        "investigation": investigation.model_dump(mode="json"),
        "awaiting_human_approval": True,
        "recommended_action": investigation.recommended_action.value,
    }
