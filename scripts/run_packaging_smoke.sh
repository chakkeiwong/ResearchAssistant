#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"

cd "$ROOT"
CMD=(
  python -m pytest
  tests/integration/test_individual_release_cli.py::test_project_metadata_exposes_ra_entrypoint
  -q
)

echo "timeout ${TIMEOUT_SECONDS}s ${CMD[*]}"
timeout "${TIMEOUT_SECONDS}s" "${CMD[@]}"

echo "timeout ${TIMEOUT_SECONDS}s python -m pip install --dry-run --no-build-isolation ."
timeout "${TIMEOUT_SECONDS}s" python -m pip install --dry-run --no-build-isolation .
