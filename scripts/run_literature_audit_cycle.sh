#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT"

$PYTHON_BIN -m pytest -q tests/unit/test_latex_source_processing.py tests/unit/test_discovery.py tests/integration/test_cli_commands.py
./scripts/run_tests.sh
