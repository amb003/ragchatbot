# ragchatbot
Chatbot for IT support
ServeWell IT Support Agent Suite: End-to-End Design
1. Frame the problem first

Your solution should answer three questions for the panel:

What gets better? Time to first response, L2 load, and store downtime.
Why trust it? Every instruction is grounded, every action is gated, and everything is logged.
How does it scale? One accelerator that onboards new incident types by adding runbooks and config, not code.

Pilot scope: “POS offline at store” is the primary incident, and “receipt/kitchen printer not working” is the secondary one. These two share assets, network dependencies, and runbook structure, so the second one proves reusability.

Core insight to build around: “POS offline” is not one problem. It is one of four:

Device fault, which a runbook fixes.
Store network or ISP fault, which needs a different runbook or the carrier.
Regional or platform outage, where many stores report at once and no runbook helps.
Payment or PCI-sensitive fault, which must be escalated.

An agent that checks telemetry and nearby tickets before applying a runbook is much more credible than one that matches keywords to a runbook.

2. Architecture
Incoming ticket (ITSM webhook / CSV / API)
        │
        ▼
 ┌─────────────── Orchestrator (explicit state machine) ───────────────┐
 │ 1 Intake & Sanitize  → validate schema, redact PII/card data,       │
 │                         prompt-injection screen                      │
 │ 2 Triage & Enrich    → classify, extract store/asset, pull asset,   │
 │                         ticket history, SLA, telemetry, regional     │
 │                         incident check (tools, no LLM guessing)      │
 │ 3 Diagnose/Route     → decide path: runbook | known outage |        │
 │                         escalate (policy rules + LLM)                │
 │ 4 Retrieve           → hybrid RAG with metadata filters + threshold │
 │ 5 Plan & Guide       → LLM drafts steps, each citing chunk IDs      │
 │ 6 Verify             → grounding check, policy check, confidence    │
 │ 7 Act                → tiered actions, approval gate                │
 │ 8 Summarize          → requester message + ticket note + L2 handoff │
 └──────────────┬───────────────────────────────┬──────────────────────┘
                │                               │
   Tools / Data layer                  Audit + Trace store
   (SQL tables, vector index,          (append-only, per run_id)
    ITSM stub, automation stub)
