# UiPath Maestro Case Setup Guide

Step-by-step instructions to wire **Runbook Responder** into UiPath Automation Cloud.

## Architecture in UiPath

```
[Alert Source] ──POST──▶ [API Workflow: Ingest Alert]
                              │
                              ▼
                     [Maestro Case: Open]
                              │
                    Stage 1: TRIAGE
                              │
                              ▼
              [Agent Builder OR POST /agents/triage]
                              │
                    Stage 2: INVESTIGATE
                              │
                              ▼
              [API Workflow: POST /agents/investigate]
                              │
                    Stage 3: AWAIT APPROVAL
                              │
                              ▼
              [Maestro Human Task: Approve Remediation]
                              │
                    Stage 4: REMEDIATE
                              │
                              ▼
              [API Workflow: POST /remediation/execute]
                              │
                    Stage 5: VERIFY → CLOSED
```

## Step 1: Deploy the coded agent API

### Option A — Local (for development)

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Use a tunnel (ngrok, Cloudflare Tunnel) to expose `https://YOUR-TUNNEL.ngrok.io` to UiPath.

### Option B — Cloud (recommended for judges)

Deploy to Railway, Render, Fly.io, or Azure App Service. Set `OPENAI_API_KEY` optionally.

Note your public base URL: `https://your-api.example.com`

## Step 2: Create Maestro Case template

1. Open **UiPath Automation Cloud** → **Maestro** → **Cases**
2. Create case type: **Incident Response**
3. Define stages:

| Stage | Type | Description |
|---|---|---|
| Triage | Automatic | Classify severity, set priority |
| Investigate | Automatic | Call coded investigation agent |
| Await Approval | **Human task** | SRE reviews RCA and approves fix |
| Remediate | Automatic | Execute approved action |
| Verify | Automatic | Confirm alert cleared |
| Closed | Terminal | Audit trail complete |

4. Add case fields:

| Field | Type | Source |
|---|---|---|
| `alert_id` | Text | Webhook payload |
| `service` | Text | Webhook payload |
| `severity` | Text | Triage agent |
| `root_cause` | Text | Investigation agent |
| `recommended_action` | Text | Investigation agent |
| `confidence` | Number | Investigation agent |
| `approved_by` | Text | Human task output |

## Step 3: API Workflow — Ingest Alert

Create an **API Workflow** triggered by HTTP POST (or connect to your monitoring webhook):

**Request body** (matches `/webhooks/alert`):

```json
{
  "alert_id": "alert-001",
  "service": "order-service",
  "severity": "critical",
  "title": "Pod OOMKilled",
  "description": "Memory exhaustion after deploy",
  "error_signature": "OutOfMemoryError"
}
```

**Actions:**
1. Parse JSON body
2. Open Maestro Case (type: Incident Response)
3. Set case fields from payload
4. Move to **Triage** stage

## Step 4: API Workflow — Triage

**HTTP Request activity:**

- Method: `POST`
- URL: `{API_BASE}/agents/triage`
- Body: alert JSON from case

Map response to case fields: `severity`, `priority_score`, `blast_radius`.

Advance case to **Investigate** stage.

## Step 5: API Workflow — Investigate

**HTTP Request activity:**

- Method: `POST`
- URL: `{API_BASE}/agents/investigate`
- Body:

```json
{
  "alert_id": "{{case.alert_id}}",
  "service": "{{case.service}}",
  "severity": "{{case.severity}}",
  "title": "{{case.title}}",
  "description": "{{case.description}}",
  "error_signature": "{{case.error_signature}}",
  "logs": []
}
```

Map response to case fields: `root_cause`, `recommended_action`, `confidence`.

Advance case to **Await Approval** stage and create **Human Task**:

- **Title:** Review remediation for `{{case.service}}`
- **Description:** Root cause: `{{case.root_cause}}`. Recommended: `{{case.recommended_action}}`
- **Actions:** Approve / Reject
- **Assignee:** On-call SRE group

## Step 6: API Workflow — Remediate (after approval)

Only run when human task = **Approved**.

**HTTP Request activity:**

- Method: `POST`
- URL: `{API_BASE}/remediation/execute`
- Body:

```json
{
  "alert_id": "{{case.alert_id}}",
  "action": "{{case.recommended_action}}",
  "approved_by": "{{human_task.assignee}}",
  "service": "{{case.service}}"
}
```

Advance to **Verify** → **Closed**.

## Step 7: Test with demo data

From your machine:

```bash
python demo/trigger_alert.py oom-order-service
```

Or POST directly to your UiPath ingest webhook with the demo payload from `demo/incidents.py`.

## Step 8: Optional — Agent Builder triage agent

Instead of calling `/agents/triage`, you can build a low-code **Agent Builder** agent that:

1. Reads alert title + description
2. Classifies severity and blast radius
3. Outputs structured JSON to update case fields

This demonstrates **both coded and low-code agents** (bonus judging points).

## Troubleshooting

| Issue | Fix |
|---|---|
| UiPath can't reach localhost | Use ngrok or deploy API to cloud |
| Investigation returns low confidence | Use `--full` demo or set `OPENAI_API_KEY` |
| Human task not appearing | Check case stage transition after investigate workflow |
| CORS errors | Not applicable — UiPath calls server-side |

## Demo video tips

Record in this order:
1. Terminal: `python demo/trigger_alert.py oom-order-service --full`
2. UiPath Maestro: case appears, stages advance
3. Human task: click Approve
4. Case timeline: show closed case with full audit trail
5. Mention Cursor built `agents/investigation_agent.py`
