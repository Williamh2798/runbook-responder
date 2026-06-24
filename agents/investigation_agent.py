"""Coded investigation agent for Runbook Responder.

Built with Cursor as part of UiPath AgentHack. Uses LangChain + OpenAI when
OPENAI_API_KEY is set; falls back to deterministic rule-based RCA for demos.
"""

from __future__ import annotations

import os
import re
from typing import Iterable

from api.models import (
    InvestigationRequest,
    InvestigationResult,
    LogEntry,
    RemediationAction,
)

# Rule patterns: error_signature or log message substring -> (root_cause, action, details)
INCIDENT_RULES: list[tuple[str, str, RemediationAction, str]] = [
    (
        r"OOM|OutOfMemory|heap",
        "JVM heap exhaustion caused by memory leak after recent deploy v2.4.1",
        RemediationAction.ROLLBACK_DEPLOY,
        "Rollback deployment to v2.4.0 and increase heap limit temporarily",
    ),
    (
        r"401|403|Unauthorized|token.*expired|JWT",
        "Expired service account token causing authentication failures",
        RemediationAction.REVOKE_TOKEN,
        "Revoke compromised token and rotate service account credentials",
    ),
    (
        r"Connection refused|timeout|503|upstream",
        "Upstream payment-gateway unreachable; cascading failures in order-service",
        RemediationAction.RESTART_SERVICE,
        "Restart payment-gateway pods and verify health checks pass",
    ),
    (
        r"CPU|throttl|rate.?limit",
        "Traffic spike exceeded autoscaling threshold; CPU saturation on api-gateway",
        RemediationAction.SCALE_UP,
        "Scale api-gateway replicas from 3 to 6 and enable rate limiting",
    ),
]


def _match_rule(text: str) -> tuple[str, RemediationAction, str] | None:
    for pattern, root_cause, action, details in INCIDENT_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return root_cause, action, details
    return None


def _collect_evidence(logs: Iterable[LogEntry], limit: int = 5) -> list[str]:
    evidence: list[str] = []
    for entry in logs:
        if entry.level.upper() in {"ERROR", "CRITICAL", "WARN"}:
            evidence.append(f"[{entry.level}] {entry.message}")
        if len(evidence) >= limit:
            break
    return evidence or ["No error-level log lines found; triage from alert metadata only"]


def investigate_rule_based(request: InvestigationRequest) -> InvestigationResult:
    """Deterministic RCA for demo scenarios without an LLM API key."""
    haystack = " ".join(
        [
            request.error_signature,
            request.title,
            request.description,
            *(log.message for log in request.logs),
        ]
    )
    match = _match_rule(haystack)
    evidence = _collect_evidence(request.logs)

    if match:
        root_cause, action, details = match
        confidence = 0.88
    else:
        root_cause = (
            f"Unable to determine definitive root cause for {request.service}. "
            "Recommend manual investigation of recent deploys and dependency health."
        )
        action = RemediationAction.NO_ACTION
        details = "Escalate to on-call SRE for manual runbook review"
        confidence = 0.45

    return InvestigationResult(
        alert_id=request.alert_id,
        root_cause=root_cause,
        confidence=confidence,
        recommended_action=action,
        remediation_details=details,
        evidence=evidence,
        agent_type="coded-rule-based",
    )


def investigate_with_llm(request: InvestigationRequest) -> InvestigationResult:
    """LangChain-powered investigation when OPENAI_API_KEY is configured."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    log_blob = "\n".join(
        f"{e.timestamp.isoformat()} [{e.level}] {e.message}" for e in request.logs[-20:]
    )
    system = (
        "You are an SRE investigation agent. Analyze alerts and logs. "
        "Respond in this exact format:\n"
        "ROOT_CAUSE: <one sentence>\n"
        "ACTION: <one of restart_service|rollback_deploy|revoke_token|scale_up|no_action>\n"
        "DETAILS: <one sentence remediation plan>\n"
        "CONFIDENCE: <0.0-1.0>"
    )
    human = (
        f"Alert: {request.title}\n"
        f"Service: {request.service}\n"
        f"Severity: {request.severity.value}\n"
        f"Description: {request.description}\n"
        f"Error signature: {request.error_signature}\n\n"
        f"Logs:\n{log_blob or '(no logs)'}"
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    text = response.content if isinstance(response.content, str) else str(response.content)

    def extract(label: str, default: str = "") -> str:
        m = re.search(rf"{label}:\s*(.+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    action_raw = extract("ACTION", "no_action").lower()
    action_map = {a.value: a for a in RemediationAction}
    action = action_map.get(action_raw, RemediationAction.NO_ACTION)

    try:
        confidence = float(extract("CONFIDENCE", "0.75"))
    except ValueError:
        confidence = 0.75

    return InvestigationResult(
        alert_id=request.alert_id,
        root_cause=extract("ROOT_CAUSE", "Analysis incomplete"),
        confidence=min(max(confidence, 0.0), 1.0),
        recommended_action=action,
        remediation_details=extract("DETAILS", "Review manually"),
        evidence=_collect_evidence(request.logs),
        agent_type="coded-langchain",
    )


def investigate(request: InvestigationRequest) -> InvestigationResult:
    """Run investigation using LLM if available, otherwise rule-based fallback."""
    if os.getenv("OPENAI_API_KEY"):
        try:
            return investigate_with_llm(request)
        except Exception:
            pass
    return investigate_rule_based(request)
