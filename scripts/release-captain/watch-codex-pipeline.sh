#!/usr/bin/env bash
set -euo pipefail

# Release Captain watcher
# - Polls GitHub for codex PR queue and latest merged codex commit on main
# - Supports one-shot and continuous monitoring
#
# Usage:
#   bash scripts/release-captain/watch-codex-pipeline.sh --once
#   bash scripts/release-captain/watch-codex-pipeline.sh --interval 60
#   GITHUB_TOKEN=... bash scripts/release-captain/watch-codex-pipeline.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/shared_data/logs"
STATE_FILE="${LOG_DIR}/release-captain-watch-state.txt"
INTERVAL=60
ONCE=false
NOTIFY=false

REPO_OWNER="${REPO_OWNER:-Merchantlee99}"
REPO_NAME="${REPO_NAME:-Personal-AI-agent}"
REPO_API="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"

mkdir -p "${LOG_DIR}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval)
      INTERVAL="${2:-60}"
      shift 2
      ;;
    --once)
      ONCE=true
      shift
      ;;
    --notify)
      NOTIFY=true
      shift
      ;;
    *)
      echo "[error] unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "[error] curl is required." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "[error] jq is required." >&2
  exit 1
fi

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

    local from_keychain
    from_keychain="$(printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain get 2>/dev/null | awk -F= '/^password=/{print $2}')"
    if [[ -n "${from_keychain}" ]]; then
      printf "%s" "${from_keychain}"
      return 0
    fi
  fi

  return 1
}

curl_api() {
  local token="$1"
  local url="$2"

  curl -sS \
    -H "Authorization: Bearer ${token}" \
    -H "Accept: application/vnd.github+json" \
    "${url}"
}

notify_change() {
  local msg="$1"
  if [[ "${NOTIFY}" != "true" ]]; then
    return 0
  fi
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${msg}\" with title \"Release Captain Watch\" subtitle \"codex pipeline changed\"" >/dev/null 2>&1 || true
  fi
}

format_pr_lines() {
  jq -r '
    [.[] | select(.head.ref|startswith("codex/"))]
    | sort_by(.created_at)
    | .[]
    | [.number, .head.ref, .head.sha, (.title // ""), (.draft|tostring)]
    | @tsv
  '
}

build_snapshot() {
  local token="$1"

  local pulls_json
  pulls_json="$(curl_api "${token}" "${REPO_API}/pulls?state=open&base=main&per_page=100")"

  local pr_lines
  pr_lines="$(printf "%s" "${pulls_json}" | format_pr_lines)"

  local summary_lines=()
  local digest_parts=()

  if [[ -z "${pr_lines}" ]]; then
    summary_lines+=("open_codex_prs=0")
    digest_parts+=("no-open-pr")
  else
    local count
    count="$(printf "%s\n" "${pr_lines}" | wc -l | tr -d ' ')"
    summary_lines+=("open_codex_prs=${count}")

    while IFS=$'\t' read -r number ref sha title draft; do
      local state
      state="$(curl_api "${token}" "${REPO_API}/commits/${sha}/status" | jq -r '.state // "unknown"')"
      summary_lines+=("#${number} ${ref} | checks=${state} | draft=${draft} | ${title}")
      digest_parts+=("${number}:${sha}:${state}:${draft}")
    done <<< "${pr_lines}"
  fi

  local latest_merge
  latest_merge="$(curl_api "${token}" "${REPO_API}/commits?sha=main&per_page=30" | jq -r '
    map(select(.commit.message | test("^merge: codex/")))
    | if length == 0 then "none|none|none"
      else .[0] | [.sha, .commit.author.date, (.commit.message | split("\n")[0])] | join("|")
      end
  ')"
  summary_lines+=("latest_main_codex_merge=${latest_merge}")
  digest_parts+=("latest=${latest_merge}")

  local digest
  digest="$(printf "%s\n" "${digest_parts[@]}" | shasum -a 256 | awk '{print $1}')"

  {
    printf "digest=%s\n" "${digest}"
    printf "%s\n" "${summary_lines[@]}"
  }
}

print_cycle() {
  local now="$1"
  local snapshot="$2"

  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ${now}"
  printf "%s\n" "${snapshot}" | sed '1d'
  echo
}

main_loop() {
  local token
  if ! token="$(resolve_github_token)"; then
    echo "[error] GITHUB_TOKEN not found. Set env or configure macOS keychain token for github.com." >&2
    exit 1
  fi

  while true; do
    local now
    now="$(date +"%Y-%m-%d %H:%M:%S")"

    local snapshot
    if ! snapshot="$(build_snapshot "${token}")"; then
      echo "[${now}] watch_error=api_failure" | tee -a "${LOG_DIR}/release-captain-watch.log"
      if [[ "${ONCE}" == "true" ]]; then
        exit 1
      fi
      sleep "${INTERVAL}"
      continue
    fi

    local current_digest
    current_digest="$(printf "%s\n" "${snapshot}" | awk -F= '/^digest=/{print $2}')"
    local prev_digest=""
    if [[ -f "${STATE_FILE}" ]]; then
      prev_digest="$(cat "${STATE_FILE}" 2>/dev/null || true)"
    fi

    if [[ "${current_digest}" != "${prev_digest}" ]]; then
      print_cycle "${now}" "${snapshot}" | tee -a "${LOG_DIR}/release-captain-watch.log"
      printf "%s" "${current_digest}" > "${STATE_FILE}"
      notify_change "Queue changed at ${now}"
    else
      echo "[${now}] no_change" >> "${LOG_DIR}/release-captain-watch.log"
    fi

    if [[ "${ONCE}" == "true" ]]; then
      break
    fi
    sleep "${INTERVAL}"
  done
}

main_loop
