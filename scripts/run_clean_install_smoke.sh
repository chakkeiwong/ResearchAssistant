#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
TMP_PARENT="${TMP_PARENT:-/tmp}"
KEEP_TMP="${KEEP_TMP:-0}"

TMP_DIR="$(mktemp -d "${TMP_PARENT%/}/research-assistant-clean-install.XXXXXX")"
VENV_DIR="${TMP_DIR}/venv"
WORKSPACE="${TMP_DIR}/workspace"
DIST_DIR="${DIST_DIR:-${ROOT}/dist}"
WHEEL_PATH="${WHEEL_PATH:-}"

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

WHEEL=""
if [[ -n "${WHEEL_PATH}" ]]; then
  if [[ ! -f "${WHEEL_PATH}" ]]; then
    echo "WHEEL_PATH does not exist: ${WHEEL_PATH}" >&2
    exit 1
  fi
  WHEEL="${WHEEL_PATH}"
elif [[ -d "${DIST_DIR}" ]]; then
  WHEEL="$(find "${DIST_DIR}" -maxdepth 1 -type f -name 'research_assistant-*.whl' | sort | tail -n 1 || true)"
fi
if [[ -n "${WHEEL}" ]]; then
  INSTALL_TARGET="${WHEEL}"
  INSTALL_FLAGS=()
else
  INSTALL_TARGET="${ROOT}"
  INSTALL_FLAGS=(--no-build-isolation)
fi

echo "timeout ${TIMEOUT_SECONDS}s ${PYTHON} -m pip install ${INSTALL_FLAGS[*]} ${INSTALL_TARGET}"
PYTHONPATH="" timeout "${TIMEOUT_SECONDS}s" "${PYTHON}" -m pip install "${INSTALL_FLAGS[@]}" "${INSTALL_TARGET}"

cd "${TMP_DIR}"
unset PYTHONPATH

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
