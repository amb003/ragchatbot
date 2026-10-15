from __future__ import annotations

import re

from ragchatbot.retrieval.hybrid import RetrievedChunk


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", text.lower()))


def grounding_score(steps: list[str], chunks: list[RetrievedChunk]) -> float:
    if not steps or not chunks:
        return 0.0
    step_tokens = _tokenize(" ".join(steps))
    if not step_tokens:
        return 0.0
    chunk_tokens = _tokenize(" ".join(c.text for c in chunks))
    if not chunk_tokens:
        return 0.0
    overlap = len(step_tokens & chunk_tokens)
    return overlap / max(len(step_tokens), 1)
