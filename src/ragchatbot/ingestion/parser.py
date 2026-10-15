from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RunbookMeta(BaseModel):
    id: str
    title: str
    version: str = "1.0"
    status: str = "active"
    tags: list[str] = Field(default_factory=list)
    sla_tier: str = "P3"
    deprecated_date: str | None = None
    superseded_by: str | None = None


class RunbookDocument(BaseModel):
    path: Path
    meta: RunbookMeta
    body: str
    content_hash: str


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_runbook(path: Path) -> RunbookDocument:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")
    meta_raw = yaml.safe_load(match.group(1)) or {}
    for key in ("version", "deprecated_date"):
        if key in meta_raw and meta_raw[key] is not None:
            meta_raw[key] = str(meta_raw[key])
    body = text[match.end() :].strip()
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    meta = RunbookMeta(**meta_raw)
    return RunbookDocument(path=path, meta=meta, body=body, content_hash=content_hash)
