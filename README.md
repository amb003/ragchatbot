# ragchatbot

Ticket-oriented IT support orchestration for retail/POS: structured enrichment (DuckDB), hybrid RAG over runbooks, guardrails, gated actions, and eval.

## Stack

- Python 3.10+ (3.11+ recommended), plain orchestration — no LangChain/LlamaIndex
- Pydantic, DuckDB, Typer, Rich, pytest, httpx
- Open-weight LLMs via Groq → Cerebras → OpenRouter (OpenAI-compatible client, cache + throttle)
- Local embeddings: `BAAI/bge-small-en-v1.5` (`pip install -e ".[embeddings]"`); hash fallback if not installed

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,embeddings]"
copy .env.example .env   # add GROQ_API_KEY etc.
```

For offline demo without API keys:

```powershell
$env:RAGCHATBOT_MOCK_LLM = "1"
```

## Commands

| Command | Purpose |
|---------|---------|
| `ragchatbot generate-data` | Synthetic DuckDB + sample tickets |
| `ragchatbot index-runbooks` | Parse/chunk/embed runbooks under `data/runbooks/` |
| `ragchatbot run --ticket <file.json>` | End-to-end ticket flow with Rich trace |
| `ragchatbot run --ticket <file> --approve` | Approve gated simulated action |
| `ragchatbot batch --dir data/incoming/` | Batch ticket processing |
| `ragchatbot eval` | Golden-set regression runner |

One-shot demo:

```powershell
.\scripts\demo.ps1
```

Optional HITL UI:

```powershell
pip install -e ".[ui]"
streamlit run streamlit_app.py
```

## Pipeline (per ticket)

1. **Intake + redaction** — PAN/phone patterns removed from working copy  
2. **Enrichment** — DuckDB: store, asset, telemetry, history, SLA, regional incidents  
3. **Hybrid retrieval** — dense + BM25 over runbook chunks (deprecated runbooks down-ranked)  
4. **Cited steps** — extracted from top chunks; grounding overlap score vs threshold  
5. **LLM insight** — structured summary (live API or mock)  
6. **Gated action** — simulated `restart_pos_service` until `--approve`  
7. **Escalation** — P1 prolonged offline, failed grounding, or escalation runbook path  
8. **Audit log** — `data/logs/audit.jsonl`

## Config

- `config.yaml` — paths, models, retrieval thresholds  
- `.env` — API keys (see `.env.example`)

## Sample tickets

- `data/incoming/pos_offline_ST-0001.json` — POS offline happy path  
- `data/incoming/regional_pos_offline_CHI.json` — Midwest regional incident (ST-0002 / R-CHI)

## Production notes (POC scope)

- RBAC for runbooks and remediation actions  
- ITSM credentials and change management for live actions  
- Sample PAN data is synthetic for redaction testing only
