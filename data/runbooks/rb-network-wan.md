---
id: rb-network-wan
title: Store Network WAN Outage
version: 2.0
status: active
tags: [network, wan, pos]
sla_tier: P1
---

# Store Network WAN Outage

Use when **all POS devices** at a store show offline telemetry or WAN link is `down`.

## Steps

1. Pull **WAN status** and **last carrier incident** for the store's circuit ID from telemetry.
2. Check **regional_incidents** for overlapping outages in the store's metro.
3. If a regional incident is `active`, link the ticket and communicate ETA from the incident record; do not dispatch field tech.
4. If no regional incident, open carrier ticket with circuit ID and attach ping loss metrics.
5. Enable **offline payment mode** only if corporate policy flag `allow_offline_payments` is true for the store (see SLA table).

## Escalation

Escalate to Carrier Relations if WAN remains down > 60 minutes without regional incident.
