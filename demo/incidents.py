"""Demo incident log fixtures for Runbook Responder."""

from __future__ import annotations

from datetime import datetime, timezone

from api.models import AlertPayload, LogEntry, Severity

NOW = datetime.now(timezone.utc)


def _ts(minutes_ago: int) -> datetime:
    return NOW.replace(microsecond=0) - __import__("datetime").timedelta(minutes=minutes_ago)


DEMO_INCIDENTS: dict[str, dict] = {
    "oom-order-service": {
        "alert": AlertPayload(
            alert_id="alert-oom-001",
            service="order-service",
            severity=Severity.CRITICAL,
            title="Critical: order-service OOMKilled",
            description="Pod order-service-7f8b9c restarted 3 times in 5 minutes",
            error_signature="OutOfMemoryError",
            metadata={"namespace": "production", "deploy_version": "v2.4.1"},
        ),
        "logs": [
            LogEntry(timestamp=_ts(8), level="INFO", message="Starting order-service v2.4.1", service="order-service"),
            LogEntry(timestamp=_ts(6), level="WARN", message="Heap usage at 85%", service="order-service"),
            LogEntry(timestamp=_ts(4), level="ERROR", message="java.lang.OutOfMemoryError: Java heap space", service="order-service"),
            LogEntry(timestamp=_ts(3), level="CRITICAL", message="Pod OOMKilled by kubelet", service="order-service"),
            LogEntry(timestamp=_ts(2), level="ERROR", message="Health check failed: connection refused", service="order-service"),
        ],
    },
    "auth-token-expired": {
        "alert": AlertPayload(
            alert_id="alert-auth-002",
            service="payment-api",
            severity=Severity.HIGH,
            title="High: 401 spike on payment-api",
            description="Authentication failure rate exceeded 40% over 3 minutes",
            error_signature="401 Unauthorized",
            metadata={"endpoint": "/v1/charges", "token_id": "svc-pay-prod-001"},
        ),
        "logs": [
            LogEntry(timestamp=_ts(10), level="INFO", message="Processing charge request batch", service="payment-api"),
            LogEntry(timestamp=_ts(7), level="WARN", message="JWT validation failed: token expired", service="payment-api"),
            LogEntry(timestamp=_ts(5), level="ERROR", message="401 Unauthorized - invalid service token", service="payment-api"),
            LogEntry(timestamp=_ts(4), level="ERROR", message="401 Unauthorized - invalid service token", service="payment-api"),
            LogEntry(timestamp=_ts(3), level="WARN", message="Error rate 42% on /v1/charges", service="payment-api"),
        ],
    },
    "upstream-timeout": {
        "alert": AlertPayload(
            alert_id="alert-upstream-003",
            service="checkout-service",
            severity=Severity.HIGH,
            title="High: checkout timeouts to payment-gateway",
            description="503 errors when calling upstream payment-gateway",
            error_signature="upstream timeout",
            metadata={"upstream": "payment-gateway", "latency_p99_ms": 12000},
        ),
        "logs": [
            LogEntry(timestamp=_ts(9), level="INFO", message="Checkout session started", service="checkout-service"),
            LogEntry(timestamp=_ts(6), level="WARN", message="payment-gateway health check degraded", service="payment-gateway"),
            LogEntry(timestamp=_ts(4), level="ERROR", message="Connection refused to payment-gateway:8443", service="checkout-service"),
            LogEntry(timestamp=_ts(3), level="ERROR", message="503 Service Unavailable - upstream timeout", service="checkout-service"),
            LogEntry(timestamp=_ts(2), level="CRITICAL", message="Circuit breaker OPEN for payment-gateway", service="checkout-service"),
        ],
    },
}
