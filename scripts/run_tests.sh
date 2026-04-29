#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"

cd "$ROOT"
echo "timeout ${TIMEOUT_SECONDS}s python -m pytest tests/unit tests/integration -q"
timeout "${TIMEOUT_SECONDS}s" python -m pytest tests/unit tests/integration -q
