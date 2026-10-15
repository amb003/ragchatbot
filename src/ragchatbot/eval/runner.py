from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from ragchatbot.config import AppConfig, load_config
from ragchatbot.orchestrator.pipeline import run_ticket


class GoldenCase(BaseModel):
    case_id: str
    ticket_path: str
    expect_runbook_id: str
    expect_escalate: bool | None = None
    expect_regional_path: bool | None = None
    approve_action: bool = False


class GoldenSuite(BaseModel):
    cases: list[GoldenCase] = Field(default_factory=list)


class EvalCaseResult(BaseModel):
    case_id: str
    passed: bool
    details: list[str]


class EvalReport(BaseModel):
    passed: int
    failed: int
    results: list[EvalCaseResult]


def load_golden(path: Path) -> GoldenSuite:
    return GoldenSuite(**json.loads(path.read_text(encoding="utf-8")))


def run_eval(config: AppConfig | None = None) -> EvalReport:
    cfg = config or load_config()
    suite = load_golden(cfg.paths.eval_golden_path)
    results: list[EvalCaseResult] = []
    passed = 0
    failed = 0

    for case in suite.cases:
        ticket_path = cfg.root / case.ticket_path
        result = run_ticket(ticket_path, approve_action=case.approve_action, config=cfg)
        details: list[str] = []
        ok = True

        top_ids = [c.runbook_id for c in result.retrieval]
        if case.expect_runbook_id not in top_ids[:3]:
            ok = False
            details.append(f"expected runbook {case.expect_runbook_id} in top 3, got {top_ids[:3]}")

        if case.expect_escalate is not None and result.escalate != case.expect_escalate:
            ok = False
            details.append(f"expected escalate={case.expect_escalate}, got {result.escalate}")

        if case.expect_regional_path is not None and result.regional_path != case.expect_regional_path:
            ok = False
            details.append(f"expected regional_path={case.expect_regional_path}, got {result.regional_path}")

        if ok:
            passed += 1
            details.append("ok")
        else:
            failed += 1

        results.append(EvalCaseResult(case_id=case.case_id, passed=ok, details=details))

    return EvalReport(passed=passed, failed=failed, results=results)
