#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
WORKSPACE="${WORKSPACE:-/tmp/research-assistant-industrial-release-gate}"

cd "$ROOT"

echo "timeout ${TIMEOUT_SECONDS}s scripts/run_fast_tests.sh"
timeout "${TIMEOUT_SECONDS}s" scripts/run_fast_tests.sh

echo "timeout ${TIMEOUT_SECONDS}s scripts/run_bounded_tests.sh"
timeout "${TIMEOUT_SECONDS}s" scripts/run_bounded_tests.sh

echo "timeout ${TIMEOUT_SECONDS}s python -m pytest tests/integration/test_industrial_platform_cli.py -q"
timeout "${TIMEOUT_SECONDS}s" python -m pytest tests/integration/test_industrial_platform_cli.py -q

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${WORKSPACE} industrial-release gate-build"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "${WORKSPACE}" industrial-release gate-build
