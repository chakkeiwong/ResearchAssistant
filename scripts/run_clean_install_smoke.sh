#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/chakwong/research-assistant}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
TMP_PARENT="${TMP_PARENT:-/tmp}"
KEEP_TMP="${KEEP_TMP:-0}"

TMP_DIR="$(mktemp -d "${TMP_PARENT%/}/research-assistant-clean-install.XXXXXX")"
VENV_DIR="${TMP_DIR}/venv"
WORKSPACE="${TMP_DIR}/workspace"

cleanup() {
  if [[ "${KEEP_TMP}" != "1" ]]; then
    rm -rf "${TMP_DIR}"
  else
    echo "KEEP_TMP=1, preserved ${TMP_DIR}"
  fi
}
trap cleanup EXIT

echo "temporary directory: ${TMP_DIR}"
echo "timeout ${TIMEOUT_SECONDS}s python -m venv ${VENV_DIR}"
timeout "${TIMEOUT_SECONDS}s" python -m venv "${VENV_DIR}"

PYTHON="${VENV_DIR}/bin/python"
RA="${VENV_DIR}/bin/ra"

echo "timeout ${TIMEOUT_SECONDS}s ${PYTHON} -m pip install --no-build-isolation ${ROOT}"
timeout "${TIMEOUT_SECONDS}s" "${PYTHON}" -m pip install --no-build-isolation "${ROOT}"

echo "timeout ${TIMEOUT_SECONDS}s ${RA} --help"
timeout "${TIMEOUT_SECONDS}s" "${RA}" --help >/dev/null

echo "timeout ${TIMEOUT_SECONDS}s ${RA} version"
timeout "${TIMEOUT_SECONDS}s" "${RA}" version

echo "timeout ${TIMEOUT_SECONDS}s ${RA} --root ${WORKSPACE} init"
timeout "${TIMEOUT_SECONDS}s" "${RA}" --root "${WORKSPACE}" init

echo "timeout ${TIMEOUT_SECONDS}s ${RA} --root ${WORKSPACE} doctor"
timeout "${TIMEOUT_SECONDS}s" "${RA}" --root "${WORKSPACE}" doctor

echo "timeout ${TIMEOUT_SECONDS}s ${RA} --root ${WORKSPACE} demo setup"
timeout "${TIMEOUT_SECONDS}s" "${RA}" --root "${WORKSPACE}" demo setup

echo "timeout ${TIMEOUT_SECONDS}s ${RA} --root ${WORKSPACE} demo run"
timeout "${TIMEOUT_SECONDS}s" "${RA}" --root "${WORKSPACE}" demo run

echo "timeout ${TIMEOUT_SECONDS}s ${RA} --root ${WORKSPACE} release-report"
timeout "${TIMEOUT_SECONDS}s" "${RA}" --root "${WORKSPACE}" release-report
