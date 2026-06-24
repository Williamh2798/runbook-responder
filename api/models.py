"""Shared Pydantic models for Runbook Responder."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseStage(str, Enum):
    TRIAGE = "triage"
    INVESTIGATE = "investigate"
    AWAIT_APPROVAL = "await_approval"
    REMEDIATE = "remediate"
    VERIFY = "verify"
    CLOSED = "closed"


class RemediationAction(str, Enum):
    RESTART_SERVICE = "restart_service"
    ROLLBACK_DEPLOY = "rollback_deploy"
    REVOKE_TOKEN = "revoke_token"
    SCALE_UP = "scale_up"
    NO_ACTION = "no_action"


class AlertPayload(BaseModel):
    """Incoming alert from monitoring (PagerDuty, Datadog, Sentry, etc.)."""

    alert_id: str = Field(..., description="Unique alert identifier")
    service: str = Field(..., description="Affected service name")
    severity: Severity
    title: str
    description: str = ""
    error_signature: str = Field("", description="Error class or signature for matching")
    source: str = "demo"
    metadata: dict[str, Any] = Field(default_factory=dict)


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    service: str


class InvestigationRequest(BaseModel):
    alert_id: str
    service: str
    severity: Severity
    title: str
    description: str = ""
    error_signature: str = ""
    logs: list[LogEntry] = Field(default_factory=list)


class InvestigationResult(BaseModel):
    alert_id: str
    root_cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_action: RemediationAction
    remediation_details: str
    evidence: list[str] = Field(default_factory=list)
    agent_type: str = "coded"


class TriageResult(BaseModel):
    alert_id: str
    severity: Severity
    blast_radius: str
    priority_score: int = Field(..., ge=1, le=100)
    case_stage: CaseStage = CaseStage.TRIAGE
    summary: str


class RemediationRequest(BaseModel):
    alert_id: str
    action: RemediationAction
    approved_by: str
    service: str


class RemediationResult(BaseModel):
    alert_id: str
    action: RemediationAction
    status: str
    message: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CaseRecord(BaseModel):
    case_id: str
    alert_id: str
    service: str
    stage: CaseStage
    severity: Severity
    title: str
    investigation: InvestigationResult | None = None
    remediation: RemediationResult | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timeline: list[dict[str, Any]] = Field(default_factory=list)
