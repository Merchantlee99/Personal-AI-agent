#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/shared_data/logs"
PID_FILE="${LOG_DIR}/release-captain-watch.pid"
OUT_LOG="${LOG_DIR}/release-captain-watch.log"
WATCH_SCRIPT="${ROOT_DIR}/scripts/release-captain/watch-codex-pipeline.sh"
INTERVAL="${WATCH_INTERVAL:-60}"

mkdir -p "${LOG_DIR}"

is_running() {
  [[ -f "${PID_FILE}" ]] || return 1
  local pid
  pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  [[ -n "${pid}" ]] || return 1
  kill -0 "${pid}" >/dev/null 2>&1
}

resolve_github_token() {
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    printf "%s" "${GITHUB_TOKEN}"
    return 0
  fi

  if command -v git >/dev/null 2>&1; then
    local from_git_credential
    from_git_credential="$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | awk -F= '/^password=/{print $2}')"
    if [[ -n "${from_git_credential}" ]]; then
      printf "%s" "${from_git_credential}"
      return 0
    fi
  fi

  return 1
}

start() {
  if is_running; then
    echo "already_running pid=$(cat "${PID_FILE}")"
    return 0
  fi

  local token
  if ! token="$(resolve_github_token)"; then
    echo "failed_to_start: missing GITHUB_TOKEN (env or git credential helper)" >&2
    exit 1
  fi

  nohup env GITHUB_TOKEN="${token}" bash "${WATCH_SCRIPT}" --interval "${INTERVAL}" >> "${OUT_LOG}" 2>&1 &
  local pid=$!
  echo "${pid}" > "${PID_FILE}"
  sleep 1

  if is_running; then
    echo "started pid=${pid} interval=${INTERVAL}s log=${OUT_LOG}"
  else
    echo "failed_to_start" >&2
    exit 1
  fi
}

stop() {
  if ! is_running; then
    echo "not_running"
    rm -f "${PID_FILE}"
    return 0
  fi

  local pid
  pid="$(cat "${PID_FILE}")"
  kill "${pid}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
  rm -f "${PID_FILE}"
  echo "stopped pid=${pid}"
}

status() {
  if is_running; then
    echo "running pid=$(cat "${PID_FILE}") interval=${INTERVAL}s log=${OUT_LOG}"
  else
    echo "stopped"
  fi
}

logs() {
  tail -n 80 "${OUT_LOG}" 2>/dev/null || echo "no_logs"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) logs ;;
  *)
    echo "usage: $0 {start|stop|restart|status|logs}" >&2
    exit 1
    ;;
esac
