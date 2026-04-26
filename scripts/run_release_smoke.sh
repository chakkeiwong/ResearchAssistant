#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/chakwong/research-assistant}"
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
timeout "${TIMEOUT_SECONDS}s" ra --root "${WORKSPACE}" demo setup

echo "timeout ${TIMEOUT_SECONDS}s ra --root ${WORKSPACE} demo run"
timeout "${TIMEOUT_SECONDS}s" ra --root "${WORKSPACE}" demo run

echo "timeout ${TIMEOUT_SECONDS}s ra --root ${WORKSPACE} release-report"
timeout "${TIMEOUT_SECONDS}s" ra --root "${WORKSPACE}" release-report
