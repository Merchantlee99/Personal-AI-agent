#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/threads/finish-thread.sh "feat(api): normalize error envelope"
#
# Behavior:
# - refuse on main branch
# - run lint + guard
# - commit staged/unstaged changes
# - push current branch to origin

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${BRANCH}" == "main" ]]; then
  echo "[error] refusing to auto-finish on main branch." >&2
  echo "checkout your thread branch first (e.g. codex/ui-...)." >&2
  exit 1
fi

if [[ "${BRANCH}" != codex/* ]]; then
  echo "[warn] branch '${BRANCH}' does not follow 'codex/*' naming."
fi

COMMIT_MSG="${1:-chore(${BRANCH#codex/}): thread updates}"

echo "[1/5] lint"
npm run lint

echo "[2/5] guard"
npm run git:guard

HAS_CHANGES="0"
if [[ -n "$(git status --porcelain)" ]]; then
  HAS_CHANGES="1"
fi

if [[ "${HAS_CHANGES}" == "1" ]]; then
  echo "[3/5] commit"
  git add -A
  git commit -m "${COMMIT_MSG}"
else
  echo "[3/5] no local changes to commit"
fi

echo "[4/5] push"
git push -u origin "${BRANCH}"

echo "[5/5] done"
echo "branch=${BRANCH}"
