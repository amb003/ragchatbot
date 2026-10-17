from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragchatbot.config import AppConfig, load_config
from ragchatbot.llm.client import LLMClient
from ragchatbot.orchestrator.audit import append_audit
from ragchatbot.orchestrator.grounding import grounding_score
from ragchatbot.orchestrator.models import (
    ActionStatus,
    Citation,
    LLMInsight,
    ProposedAction,
    TicketRunResult,
    TraceStep,
)
from ragchatbot.orchestrator.redaction import redact_ticket
from ragchatbot.retrieval.hybrid import RetrievedChunk, hybrid_search
from ragchatbot.tools.duckdb_tools import DuckDBTools


def _build_query(ticket: dict[str, Any]) -> str:
    return " ".join(
        [
            ticket.get("symptom", ""),
            ticket.get("subject", ""),
            ticket.get("description", ""),
            ticket.get("store_id", ""),
            ticket.get("asset_tag", ""),
        ]
    )


def _steps_from_chunks(chunks: list[RetrievedChunk], enrichment_wan_down: bool) -> list[str]:
    if enrichment_wan_down:
        preferred = [c for c in chunks if c.runbook_id == "rb-network-wan"]
        base = preferred or chunks
    else:
        preferred = [c for c in chunks if c.runbook_id == "rb-pos-offline"]
        base = preferred or chunks

    steps: list[str] = []
    for chunk in base[:2]:
        for line in chunk.text.splitlines():
            stripped = line.strip()
            if stripped.startswith(tuple(f"{n}." for n in range(1, 10))):
                steps.append(stripped)
    if not steps:
        steps = [
            "1. Check telemetry heartbeat and WAN status for the asset.",
            "2. Attempt graceful POS service restart via remote management.",
            "3. Run test authorization after heartbeat recovery.",
            "4. Escalate to Network Operations if offline persists.",
        ]
    return steps[:6]


def _citations_from_chunks(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(runbook_id=c.runbook_id, chunk_id=c.chunk_id, section=c.section)
        for c in chunks[:3]
    ]


def _regional_active(enrichment) -> bool:
    return any(i.status == "active" for i in enrichment.regional_incidents)


def run_ticket(
    ticket_path: Path,
    approve_action: bool = False,
    reject_action: bool = False,
    config: AppConfig | None = None,
) -> TicketRunResult:
    cfg = config or load_config()
    ticket: dict[str, Any] = json.loads(ticket_path.read_text(encoding="utf-8"))
    trace: list[TraceStep] = []

    redacted, redaction_flags = redact_ticket(ticket)
    trace.append(TraceStep(name="intake", detail="Ticket loaded and redacted", data={"flags": redaction_flags}))

    tools = DuckDBTools(cfg.paths.duckdb_path)
    enrichment = tools.enrich_ticket(
        store_id=ticket["store_id"],
        asset_tag=ticket["asset_tag"],
        ticket_id=ticket["ticket_id"],
    )
    trace.append(
        TraceStep(
            name="enrichment",
            detail="Loaded asset, telemetry, SLA, history, regional incidents",
            data={
                "telemetry_heartbeat": enrichment.telemetry_latest.heartbeat if enrichment.telemetry_latest else None,
                "offline_minutes": enrichment.telemetry_recent_offline_minutes,
                "active_regional": _regional_active(enrichment),
            },
        )
    )

    regional_path = _regional_active(enrichment) and ticket.get("symptom") in {"pos_offline", "wan_down"}
    query = _build_query(ticket)
    if regional_path:
        query += " regional outage incident playbook"

    retrieved = hybrid_search(query, config=cfg)
    if regional_path:
        retrieved = sorted(
            retrieved,
            key=lambda c: (c.runbook_id != "rb-regional-outage", -c.fused_score),
        )
    trace.append(
        TraceStep(
            name="retrieval",
            detail="Hybrid dense+sparse retrieval over runbook index",
            data={"top_runbook": retrieved[0].runbook_id if retrieved else None, "count": len(retrieved)},
        )
    )

    wan_down = enrichment.telemetry_latest is not None and enrichment.telemetry_latest.wan_link == "down"
    steps = _steps_from_chunks(retrieved, enrichment_wan_down=wan_down)
    citations = _citations_from_chunks(retrieved)
    score = grounding_score(steps, retrieved)
    passed = score >= cfg.retrieval.min_grounding_score
    trace.append(
        TraceStep(
            name="grounding",
            detail="Checked step overlap with retrieved chunks",
            data={"score": round(score, 3), "passed": passed, "threshold": cfg.retrieval.min_grounding_score},
        )
    )

    llm = LLMClient(cfg)
    insight = llm.complete_json(
        [
            {
                "role": "system",
                "content": "Return JSON only with keys summary, recommended_runbook_id, escalate, regional_incident.",
            },
            {
                "role": "user",
                "content": (
                    f"Structured analysis for ticket {ticket['ticket_id']} symptom {ticket.get('symptom')} "
                    f"with enrichment {enrichment.model_dump_json()}"
                ),
            },
        ],
        LLMInsight,
    )

    escalate = insight.escalate
    escalation_reason = None
    if ticket.get("priority") == "P1" and enrichment.telemetry_recent_offline_minutes >= 25:
        escalate = True
        escalation_reason = "P1 POS offline beyond 25 minutes of telemetry loss"
    if not passed:
        escalate = True
        escalation_reason = escalation_reason or "Grounding check below threshold"

    action = ProposedAction(
        action_id=f"ACT-{ticket['ticket_id']}",
        action_type="restart_pos_service",
        description="Simulated remote restart of POS service on the affected register",
        requires_approval=True,
    )
    if reject_action:
        action.status = ActionStatus.rejected
    elif approve_action:
        action.status = ActionStatus.simulated
    else:
        action.status = ActionStatus.pending_approval

    trace.append(
        TraceStep(
            name="action_gate",
            detail="Proposed remediation action (simulation only)",
            data={"action_type": action.action_type, "status": action.status.value},
        )
    )

    if escalate:
        trace.append(
            TraceStep(
                name="escalation",
                detail="Escalation path triggered",
                data={"reason": escalation_reason, "runbook": "rb-escalation-tier2"},
            )
        )

    audit_id = append_audit(
        cfg.orchestrator.audit_log_path,
        {
            "ticket_id": ticket["ticket_id"],
            "symptom": ticket.get("symptom"),
            "grounding_score": score,
            "grounding_passed": passed,
            "escalate": escalate,
            "action_status": action.status.value,
            "citations": [c.model_dump() for c in citations],
        },
    )

    return TicketRunResult(
        ticket_id=ticket["ticket_id"],
        symptom=ticket.get("symptom", ""),
        redacted_ticket=redacted,
        enrichment=enrichment,
        retrieval=retrieved,
        citations=citations,
        steps=steps,
        grounding_score=score,
        grounding_passed=passed,
        proposed_action=action,
        escalate=escalate,
        escalation_reason=escalation_reason,
        regional_path=regional_path,
        llm_insight=insight,
        trace=trace,
        audit_record_id=audit_id,
    )
