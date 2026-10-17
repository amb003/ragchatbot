---
id: rb-software-rollback
title: POS Application Rollback
version: 1.5
status: active
tags: [pos, software, release]
sla_tier: P2
---

# POS Application Rollback

Use after a **bad POS app release** causes crashes but network is healthy.

## Steps

1. Confirm crash signature matches known bad build in release notes.
2. Pin register to **N-1** build via deployment channel.
3. Monitor heartbeat and error rate for 20 minutes.

If registers are offline due to WAN, do not rollback until connectivity is restored.
