from pathlib import Path

from ragchatbot.config import AppConfig
from ragchatbot.orchestrator.pipeline import run_ticket


def test_pos_offline_orchestrator(prepared_env: AppConfig) -> None:
    ticket = prepared_env.root / "data" / "incoming" / "pos_offline_ST-0001.json"
    result = run_ticket(ticket, config=prepared_env)
    assert result.ticket_id == "TKT-000001"
    assert result.redacted_ticket["pan"] == "[REDACTED_PAN]"
    assert any(c.runbook_id == "rb-pos-offline" for c in result.retrieval)
    assert result.proposed_action.status.value == "pending_approval"


def test_approve_action(prepared_env: AppConfig) -> None:
    ticket = prepared_env.root / "data" / "incoming" / "pos_offline_ST-0001.json"
    result = run_ticket(ticket, approve_action=True, config=prepared_env)
    assert result.proposed_action.status.value == "simulated"
