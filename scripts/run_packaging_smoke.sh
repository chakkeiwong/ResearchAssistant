#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/chakwong/research-assistant}"
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
