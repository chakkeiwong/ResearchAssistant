#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
PAPER_ID="${2:-}"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT"

$PYTHON_BIN -m pytest -q tests/unit/test_latex_source_processing.py tests/unit/test_discovery.py tests/integration/test_cli_commands.py

if [[ -n "$PAPER_ID" ]]; then
  $PYTHON_BIN -m research_assistant.cli show --paper-id "$PAPER_ID" >/tmp/research_assistant_show.json
  $PYTHON_BIN -m research_assistant.cli literature-audit-propose --paper-id "$PAPER_ID" >/tmp/research_assistant_literature_audit.json
fi

./scripts/run_tests.sh
