#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"
GATE_ROOT="${GATE_ROOT:-/tmp/research-assistant-individual-git-gate}"

cd "$ROOT"

echo "timeout ${TIMEOUT_SECONDS}s scripts/run_fast_tests.sh"
timeout "${TIMEOUT_SECONDS}s" scripts/run_fast_tests.sh

echo "timeout ${TIMEOUT_SECONDS}s scripts/run_bounded_tests.sh"
timeout "${TIMEOUT_SECONDS}s" scripts/run_bounded_tests.sh

echo "timeout ${TIMEOUT_SECONDS}s python -m pytest tests/integration/test_individual_release_cli.py -q"
timeout "${TIMEOUT_SECONDS}s" python -m pytest tests/integration/test_individual_release_cli.py -q

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} init"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" init >/dev/null

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} individual-git-release validation-local"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" individual-git-release validation-local >/dev/null

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} individual-git-release fixture-rehearsal"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" individual-git-release fixture-rehearsal >/dev/null

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} individual-git-release performance --synthetic-count 100"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" individual-git-release performance --synthetic-count 100 >/dev/null

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} repository-hygiene check --strict"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" repository-hygiene check --strict

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} release-report"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" release-report

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} individual-git-release validation-report"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" individual-git-release validation-report

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli --root ${GATE_ROOT} individual-git-release gate-build"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli --root "$GATE_ROOT" individual-git-release gate-build
