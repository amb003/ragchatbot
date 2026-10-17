import os
from pathlib import Path

import pytest

from ragchatbot.config import load_config
from ragchatbot.ingestion.indexer import build_index
from ragchatbot.synthetic.generator import generate_all


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def prepared_env(project_root: Path, tmp_path_factory):
    os.environ["RAGCHATBOT_MOCK_LLM"] = "1"
    cfg = load_config(project_root / "config.yaml")
    work = tmp_path_factory.mktemp("ragchatbot")
    cfg.paths.synthetic_dir = work / "synthetic"
    cfg.paths.duckdb_path = work / "synthetic" / "support.duckdb"
    cfg.paths.manifest_path = work / "synthetic" / "manifest.json"
    cfg.paths.index_dir = work / "index"
    cfg.orchestrator.audit_log_path = work / "logs" / "audit.jsonl"
    cfg.llm.cache_path = work / "cache" / "llm.jsonl"
    cfg.root = project_root
    cfg.paths.runbooks_dir = project_root / "data" / "runbooks"
    cfg.paths.eval_golden_path = project_root / "data" / "eval" / "golden.json"
    generate_all(cfg)
    build_index(cfg)
    return cfg
