---
id: rb-pos-offline
title: POS Terminal Offline Recovery
version: 3.2
status: active
tags: [pos, network, store-operations]
sla_tier: P1
---

# POS Terminal Offline Recovery

Use when a store reports **POS offline**, **cannot process sales**, or **register shows disconnected**.

## Preconditions

- Confirm the issue affects one register vs entire store.
- Verify you have `store_id` and `asset_tag` from the ticket.

## Steps

1. **Check telemetry** for the asset: last heartbeat, WAN link status, and payment gateway reachability.
2. If heartbeat stopped within the last 15 minutes, attempt **graceful POS service restart** via remote management (do not power-cycle yet).
3. Verify **store router** status in telemetry; if WAN is down, follow *Store Network WAN Outage* (rb-network-wan.md) instead of POS-only steps.
4. After restart, confirm heartbeat resumes and run a **test authorization** (penny sale or gateway ping).
5. If offline persists after two restart attempts within 30 minutes, **escalate to Network Operations** with asset telemetry snapshot.

## Citations for auditors

Document: heartbeat timestamps, restart actions, test auth result, and escalation ticket ID if created.

## Do not

- Reimage the terminal without Tier-2 approval.
- Clear local transaction queue unless directed by Payment Operations.
