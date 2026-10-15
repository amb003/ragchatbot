from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel


class StoreRecord(BaseModel):
    store_id: str
    name: str
    region_id: str
    region_name: str
    metro: str
    circuit_id: str
    allow_offline_payments: bool


class AssetRecord(BaseModel):
    asset_tag: str
    store_id: str
    asset_type: str
    hostname: str
    pos_build: str
    payment_gateway: str


class TelemetrySnapshot(BaseModel):
    asset_tag: str
    store_id: str
    recorded_at: str
    heartbeat: str
    wan_link: str
    payment_gateway_latency_ms: int | None


class RegionalIncident(BaseModel):
    incident_id: str
    region_id: str
    status: str
    symptom: str
    started_at: str
    resolved_at: str | None
    root_cause: str | None
    eta_minutes: int | None


class EnrichmentBundle(BaseModel):
    store: StoreRecord | None
    asset: AssetRecord | None
    telemetry_latest: TelemetrySnapshot | None
    telemetry_recent_offline_minutes: int
    ticket_history: list[dict[str, Any]]
    sla: dict[str, Any] | None
    regional_incidents: list[RegionalIncident]


class DuckDBTools:
    def __init__(self, db_path: Path) -> None:
        if not db_path.exists():
            raise FileNotFoundError(f"DuckDB not found: {db_path}. Run ragchatbot generate-data")
        self.db_path = db_path

    def _query(self, sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
        con = duckdb.connect(str(self.db_path), read_only=True)
        try:
            return con.execute(sql, params or []).fetchall()
        finally:
            con.close()

    def enrich_ticket(self, store_id: str, asset_tag: str, ticket_id: str) -> EnrichmentBundle:
        store_row = self._query("SELECT * FROM stores WHERE store_id = ?", [store_id])
        asset_row = self._query("SELECT * FROM assets WHERE asset_tag = ?", [asset_tag])
        tel_rows = self._query(
            """
            SELECT asset_tag, store_id, recorded_at, heartbeat, wan_link, payment_gateway_latency_ms
            FROM telemetry
            WHERE asset_tag = ?
            ORDER BY recorded_at DESC
            LIMIT 24
            """,
            [asset_tag],
        )
        history = self._query(
            "SELECT ticket_id, event_at, event_type, detail FROM ticket_history WHERE ticket_id = ? ORDER BY event_at",
            [ticket_id],
        )
        priority_row = self._query("SELECT priority FROM tickets WHERE ticket_id = ?", [ticket_id])
        priority = priority_row[0][0] if priority_row else "P3"
        sla_row = self._query("SELECT priority, response_minutes, resolve_minutes FROM sla_policies WHERE priority = ?", [priority])

        region_id = store_row[0][2] if store_row else None
        incidents: list[tuple[Any, ...]] = []
        if region_id:
            incidents = self._query(
                "SELECT incident_id, region_id, status, symptom, started_at, resolved_at, root_cause, eta_minutes "
                "FROM regional_incidents WHERE region_id = ? ORDER BY started_at DESC",
                [region_id],
            )

        tel_latest = tel_rows[0] if tel_rows else None
        offline_minutes = 0
        for row in tel_rows:
            if row[3] == "offline":
                offline_minutes += 5
            else:
                break

        store = StoreRecord(
            store_id=store_row[0][0],
            name=store_row[0][1],
            region_id=store_row[0][2],
            region_name=store_row[0][3],
            metro=store_row[0][4],
            circuit_id=store_row[0][5],
            allow_offline_payments=bool(store_row[0][6]),
        ) if store_row else None

        asset = AssetRecord(
            asset_tag=asset_row[0][0],
            store_id=asset_row[0][1],
            asset_type=asset_row[0][2],
            hostname=asset_row[0][3],
            pos_build=asset_row[0][4],
            payment_gateway=asset_row[0][5],
        ) if asset_row else None

        telemetry = None
        if tel_latest:
            telemetry = TelemetrySnapshot(
                asset_tag=tel_latest[0],
                store_id=tel_latest[1],
                recorded_at=str(tel_latest[2]),
                heartbeat=tel_latest[3],
                wan_link=tel_latest[4],
                payment_gateway_latency_ms=tel_latest[5],
            )

        return EnrichmentBundle(
            store=store,
            asset=asset,
            telemetry_latest=telemetry,
            telemetry_recent_offline_minutes=offline_minutes,
            ticket_history=[
                {"ticket_id": r[0], "event_at": str(r[1]), "event_type": r[2], "detail": r[3]} for r in history
            ],
            sla={"priority": sla_row[0][0], "response_minutes": sla_row[0][1], "resolve_minutes": sla_row[0][2]}
            if sla_row
            else None,
            regional_incidents=[
                RegionalIncident(
                    incident_id=r[0],
                    region_id=r[1],
                    status=r[2],
                    symptom=r[3],
                    started_at=str(r[4]),
                    resolved_at=str(r[5]) if r[5] else None,
                    root_cause=r[6],
                    eta_minutes=r[7],
                )
                for r in incidents
            ],
        )
