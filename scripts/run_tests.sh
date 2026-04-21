#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/chakwong/research-assistant"

cd "$ROOT"
python -m pytest tests/unit tests/integration -q
