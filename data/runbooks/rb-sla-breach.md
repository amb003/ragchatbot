---
id: rb-sla-breach
title: SLA Breach Notification
version: 1.2
status: active
tags: [sla, process]
sla_tier: P2
---

# SLA Breach Notification

When **elapsed time** exceeds SLA target for the ticket priority (see `sla_policies` table):

1. Notify store manager and account team using template by priority.
2. Document breach reason code: `vendor_delay`, `access_denied`, `customer_defer`, `complexity`.
3. If P1 breach imminent at 80% of window, pre-alert duty manager.

Cross-reference `store_id` SLA tier before sending customer comms.
