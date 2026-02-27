#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/release-captain/merge-in-order.sh \
#     codex/proxy-security-hardening \
#     codex/api-contract-normalize \
#     codex/n8n-briefing-stability \
#     codex/ui-chat-polish
#
# Order is fixed:
#   1) PROXY+SECURITY
#   2) API
#   3) WORKFLOW
#   4) UI/UX

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <proxy_branch> <api_branch> <workflow_branch> <ui_branch>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

PROXY_BRANCH="$1"
API_BRANCH="$2"
WORKFLOW_BRANCH="$3"
UI_BRANCH="$4"

BRANCHES=("${PROXY_BRANCH}" "${API_BRANCH}" "${WORKFLOW_BRANCH}" "${UI_BRANCH}")

for b in "${BRANCHES[@]}"; do
  if [[ "${b}" != codex/* ]]; then
    echo "[error] branch '${b}' must follow codex/* naming." >&2
    exit 1
  fi
done

if [[ -n "$(git status --porcelain)" ]]; then
  echo "[error] working tree is not clean. commit/stash first." >&2
  exit 1
fi

echo "[0/6] fetch"
git fetch origin --prune

echo "[1/6] checkout main"
git checkout main
git pull --ff-only origin main

merge_one() {
  local branch="$1"
  echo "[merge] ${branch}"
  git show-ref --verify --quiet "refs/remotes/origin/${branch}" || {
    echo "[error] origin/${branch} not found." >&2
    exit 1
  }
  git merge --no-ff "origin/${branch}" -m "merge: ${branch}"
  npm run lint
  npm run git:guard
}

echo "[2/6] merge proxy/security"
merge_one "${PROXY_BRANCH}"

echo "[3/6] merge api"
merge_one "${API_BRANCH}"

echo "[4/6] merge workflow"
merge_one "${WORKFLOW_BRANCH}"

echo "[5/6] merge ui/ux"
merge_one "${UI_BRANCH}"

echo "[6/6] push main"
git push origin main

echo "done."
