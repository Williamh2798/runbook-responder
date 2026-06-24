# Runbook Responder

**Agentic IT incident response orchestrated by UiPath Maestro Case.**

When production alerts fire, AI agents triage and investigate root cause. UiPath Maestro Case manages each incident through governed stages—with humans approving every remediation action before it runs.

Built for [UiPath AgentHack 2026](https://uipath-agenthack.devpost.com/) · **Track 1: UiPath Maestro Case**

---

## Business problem

Production incidents are chaotic: alerts flood in, engineers context-switch between tools, and remediation often happens without audit trails or approval gates. Runbook Responder turns every alert into a **governed Maestro Case** with AI-assisted investigation and mandatory human approval before any destructive action.

## Solution overview

```
Alert (PagerDuty/Datadog/demo)
        │
        ▼
┌───────────────────────────────────────────────────┐
│           UiPath Maestro Case                      │
│  Triage → Investigate → Approve → Remediate → Verify │
└─────────┬─────────────────────┬─────────────────────┘
          │                     │
          ▼                     ▼
   Agent Builder            Coded Agent
   (triage/classify)    (Python + LangChain, built with Cursor)
          │                     │
          └──────────┬──────────┘
                     ▼
              Human approval task
              (SRE approve/reject fix)
```

## Agent type

| Component | Type |
|---|---|
| Triage / classification | **Low-code** — UiPath Agent Builder or API Workflows |
| Root-cause investigation | **Coded agent** — Python + LangChain (built with **Cursor**) |
| Case orchestration | **Low-code** — UiPath Maestro Case |
| Human approval gate | **Low-code** — Maestro human task |
| Remediation execution | **Low-code** — UiPath API Workflows + RPA (mocked in demo) |

**This solution uses both Coded Agents and Low-code Agents.**

## UiPath components used

- **UiPath Maestro Case** — incident case lifecycle and audit timeline
- **UiPath Agent Builder** — alert triage and classification
- **UiPath API Workflows** — HTTP calls to coded investigation agent
- **UiPath Automation Cloud** — orchestration and governance layer
- **UiPath for Coding Agents (Cursor)** — built the Python investigation agent and API

## Prerequisites

- Python 3.11+
- UiPath Automation Cloud with Maestro Case access (UiPath Labs sandbox)
- Optional: `OPENAI_API_KEY` for LLM-powered investigation (rule-based fallback works without it)

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/Williamh2798/runbook-responder.git
cd runbook-responder
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Start the API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for interactive API documentation.

### 3. Run a demo scenario

```bash
# Open a case from an OOM alert
python demo/trigger_alert.py oom-order-service

# Full triage + investigation (no UiPath required for local demo)
python demo/trigger_alert.py oom-order-service --full
```

**Demo scenarios:**

| Slug | Scenario | Expected action |
|---|---|---|
| `oom-order-service` | JVM heap exhaustion after deploy | `rollback_deploy` |
| `auth-token-expired` | 401 spike from expired service token | `revoke_token` |
| `upstream-timeout` | Payment gateway unreachable | `restart_service` |

### 4. Connect to UiPath Maestro Case

Follow the step-by-step guide: **[uipath/SETUP.md](uipath/SETUP.md)**

## API endpoints (for UiPath API Workflows)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/webhooks/alert` | Ingest alert, open case |
| `POST` | `/agents/triage` | Triage agent |
| `POST` | `/agents/investigate` | Coded investigation agent |
| `POST` | `/remediation/execute` | Execute approved remediation |
| `GET` | `/cases/{case_id}` | Case timeline / audit trail |
| `POST` | `/demo/run/{slug}` | End-to-end demo scenario |

## Project structure

```
runbook-responder/
├── agents/
│   └── investigation_agent.py   # Coded RCA agent (Cursor-built)
├── api/
│   ├── main.py                  # FastAPI webhook + agent endpoints
│   └── models.py                # Shared schemas
├── demo/
│   ├── incidents.py             # Realistic demo scenarios
│   └── trigger_alert.py         # CLI to fire demo alerts
├── uipath/
│   └── SETUP.md                 # Maestro Case wiring guide
├── docs/
│   └── architecture.md          # Architecture deep-dive
├── requirements.txt
└── LICENSE                      # MIT
```

## Demo video checklist

Your ≤5 min video should show:

1. Alert fires (use `demo/trigger_alert.py`)
2. Maestro Case opens and moves to **Investigate** stage
3. Coded agent returns root cause + recommended fix
4. Human approval task appears — SRE approves
5. Remediation executes; case closes with audit trail
6. Mention **Cursor** was used to build the coded agent (bonus points)

## License

MIT License — see [LICENSE](LICENSE). Applies to original solution code only; UiPath platform components remain under UiPath license terms.

## Author

William Henry · UiPath AgentHack 2026
