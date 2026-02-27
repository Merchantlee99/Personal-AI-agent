#!/usr/bin/env bash
set -euo pipefail

# Apply GitHub branch protection for this repository.
# Required env:
#   GITHUB_TOKEN  (repo admin permissions)
# Optional env:
#   REPO_OWNER    (default: Merchantlee99)
#   REPO_NAME     (default: Personal-AI-agent)
#   TARGET_BRANCH (default: main)

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

require_cmd curl

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"

REPO_OWNER="${REPO_OWNER:-Merchantlee99}"
REPO_NAME="${REPO_NAME:-Personal-AI-agent}"
TARGET_BRANCH="${TARGET_BRANCH:-main}"

API_BASE="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"

echo "[1/3] applying protection on ${REPO_OWNER}/${REPO_NAME}:${TARGET_BRANCH}"
curl -fsS -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "${API_BASE}/branches/${TARGET_BRANCH}/protection" \
  -d '{
    "required_status_checks": {
      "strict": true,
      "checks": [
        {"context": "CI / lint"},
        {"context": "Public Repo Guard / guard"}
      ]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": true,
      "require_last_push_approval": true
    },
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false,
    "required_conversation_resolution": true,
    "lock_branch": false,
    "allow_fork_syncing": true
  }' >/dev/null

echo "[2/3] enforcing linear history"
curl -fsS -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "${API_BASE}/branches/${TARGET_BRANCH}/protection/required_linear_history" >/dev/null

echo "[3/3] readback summary"
curl -fsS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "${API_BASE}/branches/${TARGET_BRANCH}/protection" | sed -n '1,120p'

echo "branch protection applied successfully."
