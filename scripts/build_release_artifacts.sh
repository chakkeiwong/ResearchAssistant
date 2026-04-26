#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/chakwong/research-assistant}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
DIST_DIR="${DIST_DIR:-${ROOT}/dist}"

cd "$ROOT"
mkdir -p "$DIST_DIR"

echo "removing old artifacts from ${DIST_DIR}"
find "$DIST_DIR" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name 'release_artifacts_manifest.json' \) -delete

if python -c "import build" >/dev/null 2>&1; then
  CMD=(python -m build --outdir "$DIST_DIR")
else
  CMD=(python -m pip wheel --no-build-isolation . -w "$DIST_DIR")
fi

echo "timeout ${TIMEOUT_SECONDS}s ${CMD[*]}"
timeout "${TIMEOUT_SECONDS}s" "${CMD[@]}"

echo "timeout ${TIMEOUT_SECONDS}s python -m research_assistant.cli release-artifacts manifest --dist-dir ${DIST_DIR}"
timeout "${TIMEOUT_SECONDS}s" python -m research_assistant.cli release-artifacts manifest --dist-dir "$DIST_DIR"
