#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export CUDA_VISIBLE_DEVICES="-1"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/research-assistant-matplotlib}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"

cd "$ROOT"
mkdir -p "$MPLCONFIGDIR"

echo "CPU-only external parser benchmark: CUDA_VISIBLE_DEVICES=-1"
timeout "${TIMEOUT_SECONDS}s" python tests/scripts/run_parser_benchmark.py
