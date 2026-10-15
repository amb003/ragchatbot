from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from ragchatbot.config import AppConfig, load_config
from ragchatbot.ingestion.chunker import RunbookChunk
from ragchatbot.retrieval.embeddings import cosine_similarity, embed_texts


class RetrievedChunk(BaseModel):
    chunk_id: str
    runbook_id: str
    runbook_title: str
    status: str
    section: str
    text: str
    source_path: str
    dense_score: float
    sparse_score: float
    fused_score: float


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class _BM25:
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(corpus) if corpus else 0.0
        df: Counter[str] = Counter()
        for doc in corpus:
            df.update(set(doc))
        self.df = df
        self.n = len(corpus)

    def score(self, query: list[str], doc_idx: int) -> float:
        doc = self.corpus[doc_idx]
        if not doc:
            return 0.0
        tf = Counter(doc)
        score = 0.0
        dl = self.doc_len[doc_idx]
        for term in query:
            if term not in tf:
                continue
            idf = math.log(1 + (self.n - self.df[term] + 0.5) / (self.df[term] + 0.5))
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
            score += idf * (freq * (self.k1 + 1)) / (denom or 1.0)
        return score


def load_index(index_dir: Path) -> tuple[list[RunbookChunk], list[list[float]]]:
    chunks_raw = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
    vectors = json.loads((index_dir / "vectors.json").read_text(encoding="utf-8"))
    chunks = [RunbookChunk(**c) for c in chunks_raw]
    return chunks, vectors


def hybrid_search(
    query: str,
    config: AppConfig | None = None,
    include_deprecated: bool = False,
) -> list[RetrievedChunk]:
    cfg = config or load_config()
    index_dir = cfg.paths.index_dir
    if not (index_dir / "chunks.json").exists():
        raise FileNotFoundError(f"Runbook index missing at {index_dir}. Run: ragchatbot index-runbooks")

    chunks, vectors = load_index(index_dir)
    query_vec = embed_texts([query], model_name=cfg.embeddings.model_name, device=cfg.embeddings.device)[0]
    tokenized = [_tokenize(c.text) for c in chunks]
    bm25 = _BM25(tokenized)
    q_tokens = _tokenize(query)

    dense_scores: list[float] = [cosine_similarity(query_vec, v) for v in vectors]
    sparse_scores: list[float] = [bm25.score(q_tokens, i) for i in range(len(chunks))]

    def norm(values: list[float]) -> list[float]:
        if not values:
            return values
        lo, hi = min(values), max(values)
        if hi - lo < 1e-9:
            return [0.0 for _ in values]
        return [(v - lo) / (hi - lo) for v in values]

    dense_n = norm(dense_scores)
    sparse_n = norm(sparse_scores)

    ranked: list[RetrievedChunk] = []
    for i, chunk in enumerate(chunks):
        if chunk.status == "deprecated" and not include_deprecated:
            continue
        fused = 0.55 * dense_n[i] + 0.45 * sparse_n[i]
        if chunk.status == "deprecated":
            fused *= 0.35
        ranked.append(
            RetrievedChunk(
                **chunk.model_dump(),
                dense_score=dense_n[i],
                sparse_score=sparse_n[i],
                fused_score=fused,
            )
        )

    ranked.sort(key=lambda c: c.fused_score, reverse=True)
    return ranked[: cfg.retrieval.top_k_final]
