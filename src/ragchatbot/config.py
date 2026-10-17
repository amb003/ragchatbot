from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    runbooks_dir: Path
    synthetic_dir: Path
    duckdb_path: Path
    manifest_path: Path
    index_dir: Path
    eval_golden_path: Path


class LLMConfig(BaseModel):
    primary_provider: str = "groq"
    fallback_providers: list[str] = Field(default_factory=lambda: ["cerebras", "openrouter"])
    default_model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.2
    max_tokens: int = 2048
    cache_path: Path = Path("data/cache/llm_responses.jsonl")
    requests_per_minute: int = 30


class EmbeddingsConfig(BaseModel):
    model_name: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"


class RetrievalConfig(BaseModel):
    top_k_dense: int = 8
    top_k_sparse: int = 8
    top_k_final: int = 5
    min_grounding_score: float = 0.65


class OrchestratorConfig(BaseModel):
    audit_log_path: Path = Path("data/logs/audit.jsonl")


class SyntheticConfig(BaseModel):
    seed: int = 42
    store_count: int = 50
    asset_count: int = 300
    ticket_count: int = 500


class AppConfig(BaseModel):
    root: Path
    paths: PathsConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    synthetic: SyntheticConfig = Field(default_factory=SyntheticConfig)


def load_config(path: Path | None = None) -> AppConfig:
    root = Path(__file__).resolve().parents[2]
    config_path = path or (root / "config.yaml")
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    paths_raw = raw.get("paths", {})
    llm_raw = raw.get("llm", {})
    emb_raw = raw.get("embeddings", {})
    ret_raw = raw.get("retrieval", {})
    orch_raw = raw.get("orchestrator", {})
    synthetic_raw = raw.get("synthetic", {})

    cache_path = root / llm_raw.get("cache_path", "data/cache/llm_responses.jsonl")
    audit_path = root / orch_raw.get("audit_log_path", "data/logs/audit.jsonl")

    return AppConfig(
        root=root,
        paths=PathsConfig(
            runbooks_dir=root / paths_raw["runbooks_dir"],
            synthetic_dir=root / paths_raw["synthetic_dir"],
            duckdb_path=root / paths_raw["duckdb_path"],
            manifest_path=root / paths_raw["manifest_path"],
            index_dir=root / paths_raw.get("index_dir", "data/index"),
            eval_golden_path=root / paths_raw.get("eval_golden_path", "data/eval/golden.json"),
        ),
        llm=LLMConfig(
            primary_provider=llm_raw.get("primary_provider", "groq"),
            fallback_providers=llm_raw.get("fallback_providers", ["cerebras", "openrouter"]),
            default_model=llm_raw.get("default_model", "llama-3.3-70b-versatile"),
            temperature=float(llm_raw.get("temperature", 0.2)),
            max_tokens=int(llm_raw.get("max_tokens", 2048)),
            cache_path=cache_path,
            requests_per_minute=int(llm_raw.get("requests_per_minute", 30)),
        ),
        embeddings=EmbeddingsConfig(**emb_raw) if emb_raw else EmbeddingsConfig(),
        retrieval=RetrievalConfig(**ret_raw) if ret_raw else RetrievalConfig(),
        orchestrator=OrchestratorConfig(audit_log_path=audit_path),
        synthetic=SyntheticConfig(**synthetic_raw) if synthetic_raw else SyntheticConfig(),
    )
