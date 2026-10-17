from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

_EMBED_DIM = 384


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _hash_embed(text: str, dim: int = _EMBED_DIM) -> list[float]:
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(0, min(len(digest), dim)):
            vec[i % dim] += (digest[i] / 255.0) - 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@lru_cache(maxsize=1)
def _load_sentence_transformer(model_name: str, device: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device=device)


def embed_texts(texts: list[str], model_name: str, device: str = "cpu") -> list[list[float]]:
    if not texts:
        return []
    try:
        model = _load_sentence_transformer(model_name, device)
        encoded = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [row.tolist() for row in encoded]
    except Exception:
        return [_hash_embed(t) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
