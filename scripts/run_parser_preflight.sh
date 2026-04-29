#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

cd "$ROOT"

RA_CMD=(python -m research_assistant.cli)

echo "ra parser-preflight"
timeout "${TIMEOUT_SECONDS}s" "${RA_CMD[@]}" parser-preflight

echo "ra doctor --matrix"
timeout "${TIMEOUT_SECONDS}s" "${RA_CMD[@]}" doctor --matrix

echo "ra parser-tool-matrix"
timeout "${TIMEOUT_SECONDS}s" "${RA_CMD[@]}" parser-tool-matrix

echo "ra parser-benchmark-smoke"
timeout "${TIMEOUT_SECONDS}s" "${RA_CMD[@]}" parser-benchmark-smoke
