#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export CUDA_VISIBLE_DEVICES="-1"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-1800}"

cd "$ROOT"

if ! python -m coverage --version >/dev/null 2>&1; then
  echo "coverage is not installed; install the dev extra first" >&2
  exit 1
fi

timeout "${TIMEOUT_SECONDS}s" python -m coverage run -m pytest \
  tests/unit tests/integration tests/scripts -q
python -m coverage report
