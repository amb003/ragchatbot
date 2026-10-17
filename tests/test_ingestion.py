from pathlib import Path

from ragchatbot.ingestion.chunker import chunk_runbook
from ragchatbot.ingestion.parser import parse_runbook


def test_parse_and_chunk_runbook(project_root: Path) -> None:
    path = project_root / "data" / "runbooks" / "rb-pos-offline.md"
    doc = parse_runbook(path)
    chunks = chunk_runbook(doc)
    assert doc.meta.id == "rb-pos-offline"
    assert doc.meta.status == "active"
    assert len(chunks) >= 3
