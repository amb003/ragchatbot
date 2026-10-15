from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_audit(path: Path, record: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    record_id = record.get("record_id") or str(uuid.uuid4())
    record["record_id"] = record_id
    record["logged_at"] = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record_id
