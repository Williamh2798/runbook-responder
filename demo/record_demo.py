#!/usr/bin/env python3
"""Slow, narrated demo for screen recording.

Usage:
    python demo/record_demo.py

Press ENTER between scenes (or let auto-pause run).
Set AUTO=1 to run without pauses: AUTO=1 python demo/record_demo.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
AUTO = os.getenv("AUTO") == "1"
PAUSE = 4 if AUTO else None  # seconds when AUTO=1


def say(text: str) -> None:
    print("\n" + "=" * 72)
    print("  NARRATOR")
    print("=" * 72)
    for line in text.strip().split("\n"):
        print(f"  {line}")
    print("=" * 72 + "\n")


def pause(label: str = "Press ENTER to continue...") -> None:
    if AUTO:
        if PAUSE:
            time.sleep(PAUSE)
        return
    input(f"\n  >>> {label} ")


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def highlight(title: str, payload: dict) -> None:
    print(f"\n--- {title} ---")
    print(json.dumps(payload, indent=2))


def main() -> None:
    say(
        """
        RUNBOOK RESPONDER — Demo Recording
        UiPath AgentHack 2026 · Track 1: Maestro Case

        What you're about to see:
          1. Three realistic production incidents
          2. AI triage + investigation for each
          3. Human approval required before any fix runs
        """
    )
    pause("Ready? Press ENTER to start Scene 1...")

    # Scene 1 — Problem
    say(
        """
        SCENE 1 — THE PROBLEM

        When production alerts fire, engineers jump between PagerDuty, logs,
        and Slack. There's no audit trail, and fixes often run without approval.

        Runbook Responder fixes that: every alert becomes a UiPath Maestro Case.
        """
    )
    pause()

    # Scene 2 — API overview
    say(
        """
        SCENE 2 — THE API

        This FastAPI backend exposes endpoints UiPath API Workflows call
        at each Maestro Case stage: triage, investigate, remediate.

        Open in browser: http://localhost:8000/docs
        """
    )
    try:
        root = api("GET", "/")
        highlight("API endpoints", root)
    except urllib.error.URLError:
        print("\n  ERROR: API not running.")
        print("  Start it first:  uvicorn api.main:app --reload\n")
        sys.exit(1)
    pause()

    # Scene 3 — List scenarios
    say(
        """
        SCENE 3 — DEMO SCENARIOS

        We built three realistic incidents for the demo video.
        Each one follows a different root cause and remediation path.
        """
    )
    incidents = api("GET", "/demo/incidents")
    highlight("Available scenarios", incidents)
    pause()

    scenarios = [
        (
            "oom-order-service",
            """
            SCENE 4 — INCIDENT 1: OOM Kill (2 AM deploy gone wrong)

            order-service was OOM-killed after deploy v2.4.1.
            Watch: triage → investigation → recommended rollback.
            Key point: awaiting_human_approval = true. AI suggests, human decides.
            """,
            ["triage.severity", "investigation.root_cause", "investigation.recommended_action", "awaiting_human_approval"],
        ),
        (
            "auth-token-expired",
            """
            SCENE 5 — INCIDENT 2: Expired auth token

            payment-api is returning 401 errors — 42% failure rate.
            Same case flow, different fix: revoke and rotate the token.
            This is why we use Maestro CASE, not a fixed BPMN diagram.
            """,
            ["investigation.root_cause", "investigation.recommended_action"],
        ),
        (
            "upstream-timeout",
            """
            SCENE 6 — INCIDENT 3: Upstream timeout

            checkout-service can't reach payment-gateway.
            Recommended action: restart the upstream service.
            Three incidents, three paths, one governed orchestration layer.
            """,
            ["investigation.root_cause", "investigation.recommended_action"],
        ),
    ]

    for slug, narration, _keys in scenarios:
        say(narration)
        pause(f"Press ENTER to run scenario: {slug}...")
        print(f"\n  $ python demo/trigger_alert.py {slug} --full\n")
        time.sleep(1 if AUTO else 0)
        result = api("POST", f"/demo/run/{slug}")
        highlight(f"Result: {slug}", result)

        triage = result.get("triage", {})
        inv = result.get("investigation", {})
        print("\n  KEY TAKEAWAYS:")
        print(f"    Severity     : {triage.get('severity', '—').upper()}")
        print(f"    Root cause   : {inv.get('root_cause', '—')}")
        print(f"    Confidence   : {inv.get('confidence', '—')}")
        print(f"    Action       : {inv.get('recommended_action', '—')}")
        print(f"    Human needed : {result.get('awaiting_human_approval', False)}")
        pause()

    # Scene 7 — Open case + remediate
    say(
        """
        SCENE 7 — OPEN A CASE + HUMAN APPROVAL FLOW

        Now we simulate what UiPath Maestro does:
          1. Alert ingested → Case opened
          2. Investigation complete → waiting for SRE
          3. Human approves → remediation executes
          4. Case closed with audit trail
        """
    )
    pause("Press ENTER to ingest alert and open a case...")

    from demo.incidents import DEMO_INCIDENTS

    alert = DEMO_INCIDENTS["oom-order-service"]["alert"]
    opened = api("POST", "/webhooks/alert", alert.model_dump(mode="json"))
    case_id = opened["case_id"]
    highlight("Case opened", opened)
    print(f"\n  Maestro Case ID: {case_id}")
    pause("Press ENTER to simulate SRE approval and run remediation...")

    inv = opened.get("triage")  # need investigation first
    run = api("POST", "/demo/run/oom-order-service")
    action = run["investigation"]["recommended_action"]
    remediated = api(
        "POST",
        "/remediation/execute",
        {
            "alert_id": alert.alert_id,
            "action": action,
            "approved_by": "sre-oncall@company.com",
            "service": alert.service,
        },
    )
    highlight("Remediation executed (after human approval)", remediated)

    case = api("GET", f"/cases/{case_id}")
    highlight("Final case timeline (audit trail)", case)
    pause()

    # Scene 8 — Close
    say(
        """
        SCENE 8 — WRAP UP

        Runbook Responder:
          · UiPath Maestro Case orchestrates every incident
          · Coded Python agent investigates (built with Cursor)
          · Humans approve before remediation runs
          · Full audit trail for compliance

        GitHub: github.com/Williamh2798/runbook-responder
        Track 1: UiPath Maestro Case · UiPath AgentHack 2026

        Thanks for watching.
        """
    )
    print("\n  Demo complete.\n")


if __name__ == "__main__":
    main()
