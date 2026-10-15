from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from ragchatbot.config import AppConfig, load_config

REGIONS = [
    ("R-NYC", "Northeast"),
    ("R-CHI", "Midwest"),
    ("R-DAL", "South"),
    ("R-LAX", "West"),
    ("R-ATL", "Southeast"),
]

ASSET_TYPES = ["pos_register", "payment_terminal", "store_router", "print_server", "back_office_pc"]
PRIORITIES = ["P1", "P2", "P3", "P4"]
SYMPTOMS = [
    "pos_offline",
    "payment_declines_all_cards",
    "printer_stuck",
    "wan_down",
    "operator_locked",
    "app_crash_loop",
    "cash_drawer_false_open",
]


class GeneratorStats(BaseModel):
    stores: int
    assets: int
    tickets: int
    telemetry_rows: int
    regional_incidents: int
    sla_policies: int
    duckdb_path: str
    manifest_path: str
    sample_ticket_path: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _build_stores(rng: random.Random, count: int) -> list[dict[str, Any]]:
    stores: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        region_id, region_name = REGIONS[(i - 1) % len(REGIONS)]
        stores.append(
            {
                "store_id": f"ST-{i:04d}",
                "name": f"Retail Store {i}",
                "region_id": region_id,
                "region_name": region_name,
                "metro": region_name,
                "circuit_id": f"CIRC-{region_id}-{i:04d}",
                "allow_offline_payments": rng.choice([True, False]),
                "manager_phone": f"+1-555-{rng.randint(100,999):03d}-{rng.randint(1000,9999):04d}",
            }
        )
    return stores


def _build_assets(rng: random.Random, stores: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    store_ids = [s["store_id"] for s in stores]
    # Guarantee each store has at least one POS register for enrichment demos.
    for idx, store_id in enumerate(store_ids, start=1):
        assets.append(
            {
                "asset_tag": f"AST-{idx:05d}",
                "store_id": store_id,
                "asset_type": "pos_register",
                "hostname": f"pos-register-{idx:05d}",
                "pos_build": rng.choice(["4.12.1", "4.12.0", "4.11.8", "4.12.2"]),
                "payment_gateway": "paygate-primary",
            }
        )
    next_id = len(store_ids) + 1
    while len(assets) < count:
        store_id = rng.choice(store_ids)
        asset_type = rng.choices(
            ASSET_TYPES,
            weights=[40, 25, 10, 10, 15],
            k=1,
        )[0]
        assets.append(
            {
                "asset_tag": f"AST-{next_id:05d}",
                "store_id": store_id,
                "asset_type": asset_type,
                "hostname": f"{asset_type.replace('_', '-')}-{next_id:05d}",
                "pos_build": rng.choice(["4.12.1", "4.12.0", "4.11.8", "4.12.2"]),
                "payment_gateway": "paygate-primary",
            }
        )
        next_id += 1
    return assets


def _pick_pos_asset(assets: list[dict[str, Any]], store_id: str) -> dict[str, Any]:
    candidates = [a for a in assets if a["store_id"] == store_id and a["asset_type"] == "pos_register"]
    if candidates:
        return candidates[0]
    return next(a for a in assets if a["store_id"] == store_id)


def _build_telemetry(
    rng: random.Random,
    assets: list[dict[str, Any]],
    hero_asset_tag: str,
    hero_offline: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    now = _utc_now()
    for asset in assets:
        is_hero = asset["asset_tag"] == hero_asset_tag
        for minutes_ago in range(0, 120, 5):
            ts = now - timedelta(minutes=minutes_ago)
            if is_hero and hero_offline and minutes_ago < 25:
                heartbeat = "offline"
                wan = "up"
                gateway_ms = None
            elif is_hero and hero_offline:
                heartbeat = "ok"
                wan = "up"
                gateway_ms = rng.randint(80, 200)
            else:
                heartbeat = rng.choices(["ok", "offline"], weights=[92, 8], k=1)[0]
                wan = "down" if heartbeat == "offline" and rng.random() < 0.3 else "up"
                gateway_ms = rng.randint(60, 400) if heartbeat == "ok" else None
            rows.append(
                {
                    "asset_tag": asset["asset_tag"],
                    "store_id": asset["store_id"],
                    "recorded_at": _iso(ts),
                    "heartbeat": heartbeat,
                    "wan_link": wan,
                    "payment_gateway_latency_ms": gateway_ms,
                    "cpu_pct": rng.randint(5, 85) if heartbeat == "ok" else None,
                }
            )
    return rows


def _build_sla_policies() -> list[dict[str, Any]]:
    return [
        {"priority": "P1", "response_minutes": 15, "resolve_minutes": 60},
        {"priority": "P2", "response_minutes": 30, "resolve_minutes": 240},
        {"priority": "P3", "response_minutes": 120, "resolve_minutes": 1440},
        {"priority": "P4", "response_minutes": 480, "resolve_minutes": 4320},
    ]


def _build_regional_incidents(rng: random.Random, stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = _utc_now()
    incidents: list[dict[str, Any]] = []
    # One resolved historical incident per region
    for region_id, _ in REGIONS:
        incidents.append(
            {
                "incident_id": f"INC-{region_id}-001",
                "region_id": region_id,
                "status": "resolved",
                "symptom": "wan_degradation",
                "started_at": _iso(now - timedelta(days=rng.randint(10, 40))),
                "resolved_at": _iso(now - timedelta(days=rng.randint(5, 9))),
                "root_cause": "carrier_fiber_cut",
                "eta_minutes": None,
            }
        )
    # Active incident in Midwest (not hero store region) for distractor testing
    incidents.append(
        {
            "incident_id": "INC-R-CHI-ACTIVE",
            "region_id": "R-CHI",
            "status": "active",
            "symptom": "pos_offline",
            "started_at": _iso(now - timedelta(minutes=45)),
            "resolved_at": None,
            "root_cause": None,
            "eta_minutes": 90,
        }
    )
    return incidents


def _build_tickets(
    rng: random.Random,
    stores: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    count: int,
    hero_ticket: dict[str, Any],
) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = [hero_ticket]
    for i in range(2, count + 1):
        store = rng.choice(stores)
        asset = _pick_pos_asset(assets, store["store_id"])
        symptom = rng.choice(SYMPTOMS)
        tickets.append(
            {
                "ticket_id": f"TKT-{i:06d}",
                "store_id": store["store_id"],
                "asset_tag": asset["asset_tag"],
                "priority": rng.choice(PRIORITIES),
                "symptom": symptom,
                "status": rng.choice(["open", "in_progress", "resolved"]),
                "created_at": _iso(_utc_now() - timedelta(hours=rng.randint(1, 720))),
                "subject": f"{symptom.replace('_', ' ').title()} at {store['store_id']}",
                "description": f"Store reports {symptom}. Asset {asset['asset_tag']}.",
                "requester_email": f"store{store['store_id'].split('-')[1]}@example.com",
            }
        )
    return tickets


def _build_ticket_history(rng: random.Random, tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticket in tickets[:80]:
        base = datetime.fromisoformat(ticket["created_at"].replace("Z", "+00:00"))
        rows.append(
            {
                "ticket_id": ticket["ticket_id"],
                "event_at": ticket["created_at"],
                "event_type": "created",
                "detail": "Ticket created via portal",
            }
        )
        if rng.random() < 0.4:
            rows.append(
                {
                    "ticket_id": ticket["ticket_id"],
                    "event_at": _iso(base + timedelta(minutes=rng.randint(5, 60))),
                    "event_type": "note",
                    "detail": rng.choice(
                        [
                            "Restarted POS service remotely",
                            "Waiting on store manager callback",
                            "Linked to known release issue 4.12.2",
                        ]
                    ),
                }
            )
    return rows


def _hero_pos_offline_ticket(store: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticket_id": "TKT-000001",
        "store_id": store["store_id"],
        "asset_tag": asset["asset_tag"],
        "priority": "P1",
        "symptom": "pos_offline",
        "status": "open",
        "created_at": _iso(_utc_now() - timedelta(minutes=12)),
        "subject": "POS offline cannot ring sales",
        "description": (
            "Register 1 shows offline since opening. Cannot process cards or cash sales. "
            "Other registers at this store appear fine. Manager: Maria Lopez."
        ),
        "requester_email": "manager@example.com",
        "contact_phone": "+1-555-010-4821",
        "pan": "4111-1111-1111-1111",  # intentional PCI-like pattern for redaction tests
    }


def _write_duckdb(path: Path, tables: dict[str, list[dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    staging = path.parent / "_duckdb_staging"
    staging.mkdir(parents=True, exist_ok=True)
    try:
        for name, rows in tables.items():
            if not rows:
                continue
            json_path = staging / f"{name}.json"
            json_path.write_text(json.dumps(rows), encoding="utf-8")
            escaped = str(json_path).replace("'", "''")
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_json_auto('{escaped}')")
    finally:
        con.close()


def _write_manifest(path: Path, runbooks_dir: Path, stats: dict[str, Any]) -> None:
    repo_root = runbooks_dir.resolve().parents[1]
    runbook_files = sorted(runbooks_dir.glob("*.md"))
    manifest = {
        "generated_at": _iso(_utc_now()),
        "runbooks": [
            {"path": str(p.relative_to(repo_root)).replace("\\", "/"), "filename": p.name}
            for p in runbook_files
        ],
        "stats": stats,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def generate_all(config: AppConfig | None = None) -> GeneratorStats:
    cfg = config or load_config()
    rng = random.Random(cfg.synthetic.seed)

    stores = _build_stores(rng, cfg.synthetic.store_count)
    assets = _build_assets(rng, stores, cfg.synthetic.asset_count)

    hero_store = stores[0]  # ST-0001, Northeast
    hero_asset = next(a for a in assets if a["store_id"] == hero_store["store_id"] and a["asset_type"] == "pos_register")
    hero_ticket = _hero_pos_offline_ticket(hero_store, hero_asset)

    telemetry = _build_telemetry(rng, assets, hero_asset["asset_tag"], hero_offline=True)
    sla = _build_sla_policies()
    incidents = _build_regional_incidents(rng, stores)
    tickets = _build_tickets(rng, stores, assets, cfg.synthetic.ticket_count, hero_ticket)
    history = _build_ticket_history(rng, tickets)

    cfg.paths.synthetic_dir.mkdir(parents=True, exist_ok=True)
    incoming = cfg.paths.synthetic_dir.parent / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    sample_ticket_path = incoming / "pos_offline_ST-0001.json"
    sample_ticket_path.write_text(json.dumps(hero_ticket, indent=2), encoding="utf-8")

    tables = {
        "stores": stores,
        "assets": assets,
        "tickets": tickets,
        "ticket_history": history,
        "telemetry": telemetry,
        "sla_policies": sla,
        "regional_incidents": incidents,
    }
    _write_duckdb(cfg.paths.duckdb_path, tables)

    stats = {
        "stores": len(stores),
        "assets": len(assets),
        "tickets": len(tickets),
        "telemetry_rows": len(telemetry),
        "regional_incidents": len(incidents),
        "sla_policies": len(sla),
    }
    _write_manifest(cfg.paths.manifest_path, cfg.paths.runbooks_dir, stats)

    return GeneratorStats(
        **stats,
        duckdb_path=str(cfg.paths.duckdb_path),
        manifest_path=str(cfg.paths.manifest_path),
        sample_ticket_path=str(sample_ticket_path),
    )
