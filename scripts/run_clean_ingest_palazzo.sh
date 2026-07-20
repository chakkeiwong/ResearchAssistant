#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-180}"

TEST_ID="tests/integration/test_cli_library_commands.py::test_cli_ingest_palazzo_uses_parser_consensus"

cd "$ROOT"
echo "Running deterministic parser-consensus regression: ${TEST_ID}"
echo "This wrapper does not require a private Palazzo PDF; pytest builds a sanitized temporary fixture."
timeout "${TIMEOUT_SECONDS}s" python -m pytest "$TEST_ID" -q
