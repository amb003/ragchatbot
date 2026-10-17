from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ragchatbot.config import AppConfig, load_config
from ragchatbot.ingestion.chunker import RunbookChunk, chunk_runbook
from ragchatbot.ingestion.parser import parse_runbook
from pydantic import BaseModel

from ragchatbot.retrieval.embeddings import embed_texts


class IndexManifest(BaseModel):
    indexed_at: str
    runbook_count: int
    chunk_count: int
    files: list[dict[str, str]]


def build_index(config: AppConfig | None = None) -> IndexManifest:
    cfg = config or load_config()
    runbooks_dir = cfg.paths.runbooks_dir
    index_dir = cfg.paths.index_dir
    index_dir.mkdir(parents=True, exist_ok=True)

    all_chunks: list[RunbookChunk] = []
    file_entries: list[dict[str, str]] = []
    for path in sorted(runbooks_dir.glob("*.md")):
        doc = parse_runbook(path)
        chunks = chunk_runbook(doc)
        all_chunks.extend(chunks)
        file_entries.append(
            {
                "path": str(path.relative_to(cfg.root)).replace("\\", "/"),
                "runbook_id": doc.meta.id,
                "content_hash": doc.content_hash,
            }
        )

    texts = [c.text for c in all_chunks]
    vectors = embed_texts(texts, model_name=cfg.embeddings.model_name, device=cfg.embeddings.device)

    chunks_path = index_dir / "chunks.json"
    vectors_path = index_dir / "vectors.json"
    manifest_path = index_dir / "index_manifest.json"

    chunks_path.write_text(
        json.dumps([c.model_dump() for c in all_chunks], indent=2),
        encoding="utf-8",
    )
    vectors_path.write_text(json.dumps(vectors), encoding="utf-8")

    manifest = IndexManifest(
        indexed_at=datetime.now(timezone.utc).isoformat(),
        runbook_count=len(file_entries),
        chunk_count=len(all_chunks),
        files=file_entries,
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest
