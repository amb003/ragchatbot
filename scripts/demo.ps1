# End-to-end demo for ragchatbot POC
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]" | Out-Null

$env:RAGCHATBOT_MOCK_LLM = "1"
ragchatbot generate-data
ragchatbot index-runbooks
ragchatbot run --ticket data/incoming/pos_offline_ST-0001.json
ragchatbot run --ticket data/incoming/pos_offline_ST-0001.json --approve
ragchatbot eval
