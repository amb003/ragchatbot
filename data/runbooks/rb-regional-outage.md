---
id: rb-regional-outage
title: Regional Service Outage Playbook
version: 2.3
status: active
tags: [regional, incident, pos, network]
sla_tier: P1
---

# Regional Service Outage Playbook

Use when **regional_incidents** shows an `active` outage affecting POS or WAN in a metro.

## Steps

1. Correlate open tickets by `region_id` and symptom (POS offline vs WAN only).
2. Attach all tickets to the **parent incident** record.
3. Publish store-facing comms using the incident template (ETA, workaround).
4. Suspend per-store truck rolls unless incident status is `investigating` with no carrier ETA > 4h.
5. After incident `resolved`, run post-incident checklist: verify sample stores' telemetry green for 30 minutes.

## Grounding note

Do not claim root cause until incident `root_cause` field is populated by Engineering.
