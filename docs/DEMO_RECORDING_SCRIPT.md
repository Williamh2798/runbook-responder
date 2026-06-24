# Runbook Responder — Demo Recording Script

**Total time:** ~4 minutes · **Pace:** Slow and deliberate · **Track:** UiPath Maestro Case

Read each **SAY** block aloud. Run each **DO** block on screen. Pause 2–3 seconds between steps.

---

## BEFORE YOU HIT RECORD

- [ ] Terminal open, font size 16+
- [ ] Browser ready at http://localhost:8000/docs
- [ ] Close notifications / Slack
- [ ] Optional: split screen — Terminal left, Browser right
- [ ] Start API: `uvicorn api.main:app --reload`

---

## SCENE 1 — The Problem (0:00 – 0:30)

**SAY:**
> "When a production alert fires — like a service crashing or payments failing — engineers jump between PagerDuty, logs, Slack, and runbooks. There's no single system of record, and remediation often happens without approval or audit trails.
>
> We built **Runbook Responder** to fix that. Every alert becomes a **UiPath Maestro Case** — with AI agents investigating, and humans approving before anything destructive runs."

**DO:** Show GitHub repo homepage briefly (optional tab):
> https://github.com/Williamh2798/runbook-responder

---

## SCENE 2 — Architecture (0:30 – 1:00)

**SAY:**
> "Here's how it works. An alert comes in from monitoring. **UiPath Maestro Case** orchestrates the lifecycle: Triage, Investigate, Human Approval, Remediate, and Verify.
>
> A **coded Python agent** — built with **Cursor** — analyzes logs and finds root cause. UiPath stays the governance layer. Nothing runs until an SRE approves."

**DO:** Open `docs/architecture.md` in GitHub or show architecture diagram from README.

---

## SCENE 3 — Start the API (1:00 – 1:20)

**SAY:**
> "Let me start our investigation backend. This FastAPI server exposes webhooks that UiPath API Workflows call during each case stage."

**DO:** Type slowly in terminal:

```bash
cd runbook-responder
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**SAY:**
> "Server is up. Let's open the API documentation."

**DO:** Browser → http://localhost:8000/docs

**SAY:**
> "These endpoints map directly to Maestro Case stages — ingest alert, triage, investigate, and execute remediation after approval."

---

## SCENE 4 — Demo Scenario 1: OOM Kill (1:20 – 2:30)

**SAY:**
> "Imagine it's 2 AM. **order-service** just got OOM-killed after a bad deploy. Let's fire that alert."

**DO:** New terminal tab. Type slowly:

```bash
python demo/trigger_alert.py oom-order-service --full
```

**SAY (while output appears):**
> "First — **Triage**. Severity is CRITICAL. Priority score 95. Blast radius: customer checkout is affected.
>
> Next — the **Investigation Agent** runs. It reads the logs… heap at 85 percent… OutOfMemoryError… pod killed by kubelet.
>
> Root cause: **JVM heap exhaustion after deploy v2.4.1**. Confidence: 88 percent.
>
> Recommended action: **rollback the deploy**.
>
> Notice it says **awaiting human approval**. The agent suggests — but does NOT execute. That's the human-in-the-loop gate in Maestro Case."

**DO:** Scroll through JSON output slowly, pointing at:
- `triage.severity`
- `investigation.root_cause`
- `investigation.recommended_action`
- `awaiting_human_approval: true`

---

## SCENE 5 — UiPath Maestro Case (2:30 – 3:15)

**SAY:**
> "In UiPath, this alert opens a **Maestro Case**. Stage one: Triage. Stage two: Investigate — our API Workflow calls the coded agent. Stage three: **Human Task** — the on-call SRE sees the root cause and clicks Approve or Reject.
>
> Only after approval does stage four run: Remediation — rollback the deploy. Stage five: Verify the alert cleared. Case closed — with a full audit timeline."

**DO:** Show `uipath/SETUP.md` stage table OR UiPath Maestro screen if you have Labs access.

**SAY:**
> "Every transition is logged. Judges — and real compliance teams — can see exactly who approved what and when."

---

## SCENE 6 — Scenario 2: Auth Token (3:15 – 3:45)

**SAY:**
> "Different incident, different path. Payment API — 401 spike from an expired service token."

**DO:**

```bash
python demo/trigger_alert.py auth-token-expired --full
```

**SAY:**
> "This time the agent recommends **revoke and rotate the token** — not a rollback. Same case flow, different remediation. That's why we use **Maestro Case**, not a fixed BPMN diagram."

---

## SCENE 7 — Scenario 3: Upstream Timeout (3:45 – 4:05)

**SAY:**
> "One more — checkout service timing out because payment-gateway is down."

**DO:**

```bash
python demo/trigger_alert.py upstream-timeout --full
```

**SAY:**
> "Recommended action: **restart the upstream service**. Three scenarios, three different root causes, one governed orchestration layer."

---

## SCENE 8 — Built with Cursor (4:05 – 4:30)

**SAY:**
> "The investigation agent lives in `agents/investigation_agent.py` — built with **Cursor** as part of UiPath for Coding Agents. It uses LangChain when an OpenAI key is set, or rule-based analysis for demos.
>
> UiPath orchestrates. Coded agents investigate. Humans approve. That's **Runbook Responder**."

**DO:** Briefly show `agents/investigation_agent.py` in editor (scroll, don't read code line by line).

---

## SCENE 9 — Close (4:30 – 5:00)

**SAY:**
> "Runbook Responder — agentic incident response on UiPath Maestro Case. Public repo, MIT license, setup guide included. Thanks for watching."

**DO:** End on GitHub repo or README.

---

## SWAGGER LIVE DEMO (optional insert at Scene 4)

If you want to show the browser instead of CLI:

1. Go to **POST /demo/run/{slug}** in Swagger
2. Click **Try it out**
3. Type slug: `oom-order-service`
4. Click **Execute**
5. Narrate the response body slowly

Same for **POST /webhooks/alert** with this body:

```json
{
  "alert_id": "alert-oom-001",
  "service": "order-service",
  "severity": "critical",
  "title": "Critical: order-service OOMKilled",
  "description": "Pod restarted 3 times in 5 minutes",
  "error_signature": "OutOfMemoryError"
}
```

---

## ON-SCREEN TEXT OVERLAYS (optional)

| Timestamp | Text overlay |
|---|---|
| 0:05 | Runbook Responder · UiPath AgentHack 2026 |
| 0:35 | UiPath Maestro Case = orchestration + governance |
| 1:45 | Step 1: Triage → Step 2: Investigate → Step 3: Human Approve |
| 2:15 | AI suggests · Human approves · Then it runs |
| 4:10 | Built with Cursor · Track 1: Maestro Case |

---

## TROUBLESHOOTING DURING RECORDING

| Issue | Fix |
|---|---|
| Connection refused | Start uvicorn first |
| Empty output | Run from project root with venv active |
| Swagger won't load | Check port 8000 not in use |
