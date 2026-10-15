from __future__ import annotations

import re
from pydantic import BaseModel

from ragchatbot.ingestion.parser import RunbookDocument


class RunbookChunk(BaseModel):
    chunk_id: str
    runbook_id: str
    runbook_title: str
    status: str
    section: str
    text: str
    source_path: str


_SECTION_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


def chunk_runbook(doc: RunbookDocument) -> list[RunbookChunk]:
    body = doc.body
    matches = list(_SECTION_RE.finditer(body))
    chunks: list[RunbookChunk] = []
    if not matches:
        chunks.append(_make_chunk(doc, "body", body.strip()))
        return chunks

    preamble = body[: matches[0].start()].strip()
    if preamble:
        chunks.append(_make_chunk(doc, "introduction", preamble))

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        section_title = match.group(2).strip()
        section_body = body[start:end].strip()
        if section_body:
            chunks.append(_make_chunk(doc, section_title, section_body))
    return chunks


def _make_chunk(doc: RunbookDocument, section: str, text: str) -> RunbookChunk:
    slug = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")[:40] or "section"
    chunk_id = f"{doc.meta.id}::{slug}"
    return RunbookChunk(
        chunk_id=chunk_id,
        runbook_id=doc.meta.id,
        runbook_title=doc.meta.title,
        status=doc.meta.status,
        section=section,
        text=text,
        source_path=str(doc.path),
    )
