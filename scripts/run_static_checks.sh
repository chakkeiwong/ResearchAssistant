#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"

cd "$ROOT"

python -m compileall -q src scripts
bash -n scripts/*.sh

if python -m ruff --version >/dev/null 2>&1; then
  timeout "${TIMEOUT_SECONDS}s" python -m ruff check src tests scripts
else
  echo "ruff not installed; install the dev extra to run lint checks"
fi

if python -m mypy --version >/dev/null 2>&1; then
  timeout "${TIMEOUT_SECONDS}s" python -m mypy \
    src/research_assistant/ingest/parser_command.py \
    src/research_assistant/ingest/parser_base.py \
    src/research_assistant/cli_registration \
    src/research_assistant/cli_actions \
    src/research_assistant/survey/next_action.py
else
  echo "mypy not installed; install the dev extra to run type checks"
fi

git diff --check
