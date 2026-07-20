#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export CUDA_VISIBLE_DEVICES="-1"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-900}"

cd "$ROOT"

RESULT_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/research-assistant-tests.XXXXXX")"
trap 'rm -rf "$RESULT_ROOT"' EXIT

mapfile -d '' INTEGRATION_REST < <(
  find tests/integration -maxdepth 1 -type f -name '*.py' ! -name 'test_cli_commands.py' -print0 | sort -z
)

run_partition() {
  local name="$1"
  shift
  setsid --wait timeout "${TIMEOUT_SECONDS}s" python -m pytest "$@" -q >"${RESULT_ROOT}/${name}.log" 2>&1
}

echo "CPU-only active test suite: CUDA_VISIBLE_DEVICES=-1"
echo "Four bounded partitions; timeout ${TIMEOUT_SECONDS}s per partition"

run_partition unit tests/unit &
unit_pid=$!
run_partition integration_cli tests/integration/test_cli_commands.py &
integration_cli_pid=$!
run_partition integration_rest "${INTEGRATION_REST[@]}" &
integration_rest_pid=$!
run_partition scripts tests/scripts &
scripts_pid=$!

status=0
for name in unit integration_cli integration_rest scripts; do
  pid_variable="${name}_pid"
  if wait "${!pid_variable}"; then
    echo "PASS ${name}"
  else
    partition_status=$?
    echo "FAIL ${name} (exit ${partition_status})" >&2
    status=1
  fi
  cat "${RESULT_ROOT}/${name}.log"
done
exit "$status"
