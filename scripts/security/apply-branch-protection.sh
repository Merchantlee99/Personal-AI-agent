#!/usr/bin/env bash
set -euo pipefail

# Apply GitHub branch protection for this repository.
# Required env:
#   GITHUB_TOKEN  (repo admin permissions)
# Optional env:
#   REPO_OWNER    (default: Merchantlee99)
#   REPO_NAME     (default: Personal-AI-agent)
#   TARGET_BRANCH (default: main)
#   PROTECTION_PROFILE (default: strict)
#     - strict: requires 1 review + codeowner review
#     - auto: no review requirement (for full automation)

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
PROTECTION_PROFILE="${PROTECTION_PROFILE:-strict}"

if [[ "${PROTECTION_PROFILE}" != "strict" && "${PROTECTION_PROFILE}" != "auto" ]]; then
  echo "[error] PROTECTION_PROFILE must be strict|auto" >&2
  exit 1
fi

if [[ "${PROTECTION_PROFILE}" == "auto" ]]; then
  REQUIRED_REVIEWS='null'
else
  REQUIRED_REVIEWS='{
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": true
  }'
fi

API_BASE="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}"

echo "[1/3] applying protection on ${REPO_OWNER}/${REPO_NAME}:${TARGET_BRANCH} (profile=${PROTECTION_PROFILE})"
curl -fsS -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "${API_BASE}/branches/${TARGET_BRANCH}/protection" \
  -d "{
    \"required_status_checks\": {
      \"strict\": true,
      \"checks\": [
        {\"context\": \"CI / lint\"},
        {\"context\": \"Public Repo Guard / guard\"}
      ]
    },
    \"enforce_admins\": true,
    \"required_pull_request_reviews\": ${REQUIRED_REVIEWS},
    \"restrictions\": null,
    \"allow_force_pushes\": false,
    \"allow_deletions\": false,
    \"required_conversation_resolution\": true,
    \"lock_branch\": false,
    \"allow_fork_syncing\": true
  }" >/dev/null

echo "[2/3] enforcing linear history"
LINEAR_CODE="$(curl -sS -o /tmp/branch_protect_linear.json -w "%{http_code}" -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "${API_BASE}/branches/${TARGET_BRANCH}/protection/required_linear_history" || true)"
if [[ "${LINEAR_CODE}" != "200" && "${LINEAR_CODE}" != "201" && "${LINEAR_CODE}" != "204" ]]; then
  echo "[warn] required_linear_history endpoint returned ${LINEAR_CODE}; continuing." >&2
fi

echo "[3/3] readback summary"
curl -fsS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  "${API_BASE}/branches/${TARGET_BRANCH}/protection" | sed -n '1,120p'

echo "branch protection applied successfully."
