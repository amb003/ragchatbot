---
id: rb-printer-kitchen
title: Kitchen Printer Queue Stuck
version: 1.1
status: active
tags: [printer, store-operations]
sla_tier: P3
---

# Kitchen Printer Queue Stuck

Use when **receipt/kitchen tickets not printing** but POS is online.

## Steps

1. Clear stuck print spooler job on the print server VM (store back-office).
2. Restart print service; verify test page.
3. If hardware error LED is on, schedule hardware swap (P3).

Not applicable for POS-wide offline scenarios.
