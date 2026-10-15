---
id: rb-payment-terminal
title: Payment Terminal Reset and Re-pairing
version: 1.8
status: active
tags: [payments, pos, hardware]
sla_tier: P2
---

# Payment Terminal Reset and Re-pairing

Use for **card reader errors**, **pairing lost**, or **declines on all cards** when POS network is healthy.

## Steps

1. Confirm POS heartbeat is `ok` and payment gateway latency is under 500ms.
2. Initiate **soft reset** on the payment terminal from device management.
3. Re-pair terminal to the register using the in-store pairing code (never share codes in external chat).
4. Run **test transaction**; capture auth code in ticket notes.

## When to escalate

Escalate to Payment Operations if gateway errors persist after re-pair or if error code indicates key injection failure.
