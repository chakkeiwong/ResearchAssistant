#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
WORKSPACE="${WORKSPACE:-/tmp/research-assistant-release-smoke}"

cd "$ROOT"
CMD=(
  python -m pytest
  tests/integration/test_individual_release_cli.py
  -q
)

echo "timeout ${TIMEOUT_SECONDS}s ${CMD[*]}"
timeout "${TIMEOUT_SECONDS}s" "${CMD[@]}"

echo "timeout ${TIMEOUT_SECONDS}s ra --root ${WORKSPACE} demo setup"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "${WORKSPACE}" demo setup

echo "timeout ${TIMEOUT_SECONDS}s ra --root ${WORKSPACE} demo run"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "${WORKSPACE}" demo run

if [[ "${RELEASE_GATE_IN_PROGRESS:-0}" != "1" ]]; then
  echo "timeout ${TIMEOUT_SECONDS}s ra --root ${WORKSPACE} release-report"
  timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "${WORKSPACE}" release-report
else
  echo "release-report deferred until the candidate gate writes final evidence"
fi

echo "timeout ${TIMEOUT_SECONDS}s scripts/run_external_tool_tests.sh"
timeout "${TIMEOUT_SECONDS}s" scripts/run_external_tool_tests.sh
