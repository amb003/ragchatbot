from pathlib import Path

import duckdb

from ragchatbot.config import load_config
from ragchatbot.synthetic.generator import generate_all


def test_generate_all_creates_duckdb_and_hero_ticket(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "config.yaml")
    cfg.paths.synthetic_dir = tmp_path / "synthetic"
    cfg.paths.duckdb_path = tmp_path / "synthetic" / "support.duckdb"
    cfg.paths.manifest_path = tmp_path / "synthetic" / "manifest.json"

    stats = generate_all(cfg)

    assert stats.stores == 50
    assert stats.tickets == 500
    assert cfg.paths.duckdb_path.exists()
    assert cfg.paths.manifest_path.exists()

    con = duckdb.connect(str(cfg.paths.duckdb_path))
    hero = con.execute(
        "SELECT ticket_id, symptom, store_id FROM tickets WHERE ticket_id = 'TKT-000001'"
    ).fetchone()
    con.close()
    assert hero == ("TKT-000001", "pos_offline", "ST-0001")
