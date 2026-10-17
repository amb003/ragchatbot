from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ragchatbot.config import load_config
from ragchatbot.eval.runner import run_eval
from ragchatbot.ingestion.indexer import build_index
from ragchatbot.orchestrator.pipeline import run_ticket
from ragchatbot.synthetic.generator import generate_all

app = typer.Typer(help="IT support RAG ticket orchestrator (POC).")
console = Console()


def _print_trace(result) -> None:
    tree = Tree(f"[bold]Ticket {result.ticket_id}[/bold] ({result.symptom})")
    for step in result.trace:
        branch = tree.add(f"[cyan]{step.name}[/cyan]: {step.detail}")
        if step.data:
            for key, value in step.data.items():
                branch.add(f"{key}={value}")
    console.print(tree)

    table = Table(title="Retrieved runbooks")
    table.add_column("Runbook")
    table.add_column("Section")
    table.add_column("Score", justify="right")
    for chunk in result.retrieval:
        table.add_row(chunk.runbook_id, chunk.section, f"{chunk.fused_score:.3f}")
    console.print(table)

    console.print(Panel("\n".join(result.steps), title="Proposed steps (cited)"))
    cites = ", ".join(f"{c.runbook_id}#{c.section}" for c in result.citations)
    console.print(f"Citations: {cites}")
    console.print(
        f"Grounding: {result.grounding_score:.3f} ({'PASS' if result.grounding_passed else 'FAIL'}) | "
        f"Action: {result.proposed_action.status.value} | Escalate: {result.escalate}"
    )
    if result.escalation_reason:
        console.print(f"Escalation reason: {result.escalation_reason}")


@app.command("generate-data")
def generate_data() -> None:
    """Generate synthetic DuckDB tables, manifest, and sample tickets."""
    stats = generate_all()
    table = Table(title="Synthetic data generated")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for key, value in stats.model_dump().items():
        table.add_row(key, str(value))
    console.print(table)


@app.command("index-runbooks")
def index_runbooks() -> None:
    """Parse, chunk, embed, and index Markdown runbooks."""
    manifest = build_index()
    console.print(
        f"Indexed {manifest.runbook_count} runbooks into {manifest.chunk_count} chunks "
        f"at {load_config().paths.index_dir}"
    )


@app.command("run")
def run(
    ticket: Path = typer.Option(..., "--ticket", exists=True, readable=True, help="Ticket JSON path"),
    approve: bool = typer.Option(False, "--approve", help="Approve gated simulated action"),
    reject: bool = typer.Option(False, "--reject", help="Reject gated action"),
) -> None:
    """Process a single ticket end-to-end."""
    result = run_ticket(ticket, approve_action=approve, reject_action=reject)
    _print_trace(result)


@app.command("batch")
def batch(
    directory: Path = typer.Option(..., "--dir", exists=True, file_okay=False, help="Directory of ticket JSON files"),
    approve: bool = typer.Option(False, "--approve", help="Approve gated actions"),
) -> None:
    """Process all ticket JSON files in a directory."""
    files = sorted(directory.glob("*.json"))
    if not files:
        raise typer.BadParameter(f"No JSON tickets found in {directory}")
    for path in files:
        console.rule(path.name)
        result = run_ticket(path, approve_action=approve)
        _print_trace(result)


@app.command("eval")
def eval_cmd() -> None:
    """Run golden-set evaluation."""
    report = run_eval()
    table = Table(title="Eval report")
    table.add_column("Case")
    table.add_column("Passed")
    table.add_column("Details")
    for row in report.results:
        table.add_row(row.case_id, "yes" if row.passed else "no", "; ".join(row.details))
    console.print(table)
    console.print(f"Summary: {report.passed} passed, {report.failed} failed")
    if report.failed:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
