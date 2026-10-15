---
id: rb-pos-offline-deprecated
title: POS Offline — Hard Reboot Only (DEPRECATED)
version: 0.9
status: deprecated
deprecated_date: 2023-06-01
superseded_by: rb-pos-offline
tags: [pos, deprecated]
sla_tier: P1
---

# POS Offline — Hard Reboot Only (DEPRECATED)

> **DEPRECATED** — Superseded by *POS Terminal Offline Recovery* (rb-pos-offline). Do not use.

## Old steps (invalid)

1. Power-cycle register immediately without checking telemetry.
2. Delete local transaction database.
3. Reimage terminal on first failure.

These steps cause data loss and violate current payment compliance policy.
