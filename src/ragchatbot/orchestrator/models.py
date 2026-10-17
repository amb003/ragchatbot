from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ragchatbot.retrieval.hybrid import RetrievedChunk
from ragchatbot.tools.duckdb_tools import EnrichmentBundle


class ActionStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    simulated = "simulated"


class ProposedAction(BaseModel):
    action_id: str
    action_type: str
    description: str
    status: ActionStatus = ActionStatus.pending_approval
    requires_approval: bool = True


class Citation(BaseModel):
    runbook_id: str
    chunk_id: str
    section: str


class TraceStep(BaseModel):
    name: str
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)


class LLMInsight(BaseModel):
    summary: str
    recommended_runbook_id: str
    escalate: bool = False
    regional_incident: bool = False


class TicketRunResult(BaseModel):
    ticket_id: str
    symptom: str
    redacted_ticket: dict[str, Any]
    enrichment: EnrichmentBundle
    retrieval: list[RetrievedChunk]
    citations: list[Citation]
    steps: list[str]
    grounding_score: float
    grounding_passed: bool
    proposed_action: ProposedAction
    escalate: bool
    escalation_reason: str | None = None
    regional_path: bool
    llm_insight: LLMInsight | None = None
    trace: list[TraceStep]
    audit_record_id: str
