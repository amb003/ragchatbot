from __future__ import annotations

import copy
import re
from typing import Any

_PAN_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{8,}\d")


def redact_ticket(ticket: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    redacted = copy.deepcopy(ticket)
    flags: list[str] = []

    for key in list(redacted.keys()):
        value = redacted[key]
        if not isinstance(value, str):
            continue
        if _PAN_RE.search(value):
            redacted[key] = _PAN_RE.sub("[REDACTED_PAN]", value)
            flags.append(f"redacted_pan:{key}")
        if _PHONE_RE.search(redacted[key]):
            redacted[key] = _PHONE_RE.sub("[REDACTED_PHONE]", redacted[key])
            flags.append(f"redacted_phone:{key}")

    if "pan" in redacted:
        redacted["pan"] = "[REDACTED_PAN]"
        if "redacted_pan:pan" not in flags:
            flags.append("redacted_pan:pan")

    return redacted, flags
