---
id: rb-pos-password-reset
title: POS Operator Password Reset
version: 1.0
status: active
tags: [identity, pos]
sla_tier: P4
---

# POS Operator Password Reset

Use for **locked operator accounts** on POS (not for payment keys).

## Steps

1. Verify requester identity via store manager callback list.
2. Reset operator PIN in identity tool; force re-login on register.
3. Log action in audit trail with approver name.

Does not resolve connectivity or offline POS issues.
