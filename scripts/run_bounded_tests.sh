#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/chakwong/research-assistant}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"

cd "$ROOT"
CMD=(
  python -m pytest
  tests/unit/test_schemas.py
  tests/unit/test_full_scale_plan_contracts.py
  tests/unit/test_workspace_exports.py
  tests/unit/test_review.py
  tests/unit/test_discovery.py
  tests/unit/test_downloads.py
  tests/integration/test_citation_cli.py
  tests/integration/test_industrial_platform_cli.py
  -q
)

echo "timeout ${TIMEOUT_SECONDS}s ${CMD[*]}"
timeout "${TIMEOUT_SECONDS}s" "${CMD[@]}"
