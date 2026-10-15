---
id: rb-escalation-tier2
title: Escalation to Tier-2 and Major Incident
version: 4.0
status: active
tags: [escalation, sla, process]
sla_tier: P1
---

# Escalation to Tier-2 and Major Incident

## When to escalate

- P1 POS outage > 30 minutes after standard recovery steps.
- Suspected **payment PCI** impact or data exposure (immediate security bridge).
- Multiple stores in one region with identical symptoms within 15 minutes.

## Required handoff fields

- `store_id`, `asset_tag`, telemetry snapshot time range
- Runbook steps attempted with timestamps
- Customer impact estimate (registers down, revenue at risk)

## Major incident

If ≥ 5 stores affected in one region, declare **major incident** and notify the regional command channel.
