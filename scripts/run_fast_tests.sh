#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"

cd "$ROOT"
CMD=(python -m pytest tests/unit/test_schemas.py tests/unit/test_full_scale_plan_contracts.py tests/integration/test_industrial_platform_cli.py tests/integration/test_cli_commands.py::test_cli_help_includes_review_inbox_export_and_citation_commands -q)

echo "timeout ${TIMEOUT_SECONDS}s ${CMD[*]}"
timeout "${TIMEOUT_SECONDS}s" "${CMD[@]}"
