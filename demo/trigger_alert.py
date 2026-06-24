#!/usr/bin/env python3
"""Fire a demo alert at the Runbook Responder API.

Usage:
    python demo/trigger_alert.py oom-order-service
    python demo/trigger_alert.py auth-token-expired
    python demo/trigger_alert.py upstream-timeout
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from demo.incidents import DEMO_INCIDENTS

DEFAULT_BASE = "http://localhost:8000"


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger a Runbook Responder demo alert")
    parser.add_argument(
        "scenario",
        choices=list(DEMO_INCIDENTS.keys()),
        help="Demo incident scenario slug",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="API base URL")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full end-to-end demo (triage + investigate) via /demo/run/{slug}",
    )
    args = parser.parse_args()

    path = f"/demo/run/{args.scenario}" if args.full else "/webhooks/alert"
    url = f"{args.base_url.rstrip('/')}{path}"

    if args.full:
        req = urllib.request.Request(url, method="POST")
    else:
        alert = DEMO_INCIDENTS[args.scenario]["alert"]
        body = json.dumps(alert.model_dump(mode="json")).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(json.dumps(json.loads(resp.read().decode()), indent=2))
    except urllib.error.URLError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Is the API running? Start with: uvicorn api.main:app --reload", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
