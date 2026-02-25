#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
RESTART_CONTAINERS=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --no-restart)
      RESTART_CONTAINERS=false
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--env-file <path>] [--no-restart]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required to rotate secrets." >&2
  exit 1
fi

backup_file="${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
cp "${ENV_FILE}" "${backup_file}"
chmod 600 "${backup_file}" || true

upsert_quoted() {
  local key="$1"
  local value="$2"
  local tmp_file
  tmp_file="$(mktemp)"
  awk -v k="${key}" -v v="${value}" '
    BEGIN { done = 0 }
    $0 ~ ("^" k "=") { print k "=\"" v "\""; done = 1; next }
    { print }
    END { if (!done) print k "=\"" v "\"" }
  ' "${ENV_FILE}" >"${tmp_file}"
  mv "${tmp_file}" "${ENV_FILE}"
}

read_key_value() {
  local key="$1"
  awk -F= -v k="${key}" '$1 == k { print $2; found=1 } END { if (!found) print "" }' "${ENV_FILE}" \
    | sed -e 's/^"//' -e 's/"$//'
}

generate_token() {
  openssl rand -hex 32
}

generate_password() {
  openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-' | cut -c1-40
}

llm_proxy_token="$(generate_token)"
n8n_webhook_token="$(generate_token)"
n8n_basic_password="$(generate_password)"

upsert_quoted "LLM_PROXY_INTERNAL_TOKEN" "${llm_proxy_token}"
upsert_quoted "N8N_WEBHOOK_AUTH_TOKEN" "${n8n_webhook_token}"
upsert_quoted "N8N_BASIC_AUTH_PASSWORD" "${n8n_basic_password}"

# One-time bootstrap for n8n credential encryption.
existing_n8n_key="$(read_key_value "N8N_ENCRYPTION_KEY")"
if [[ -z "${existing_n8n_key}" ]]; then
  upsert_quoted "N8N_ENCRYPTION_KEY" "$(generate_token)"
fi

chmod 600 "${ENV_FILE}" || true
mkdir -p "${ROOT_DIR}/shared_data/logs"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) rotated internal secrets (LLM_PROXY_INTERNAL_TOKEN, N8N_WEBHOOK_AUTH_TOKEN, N8N_BASIC_AUTH_PASSWORD)" \
  >> "${ROOT_DIR}/shared_data/logs/security-rotation.log"

if [[ "${RESTART_CONTAINERS}" == true ]]; then
  cd "${ROOT_DIR}"
  docker compose up -d --force-recreate llm-proxy nanoclaw-agent n8n
fi

echo "Rotation completed."
echo "- env: ${ENV_FILE}"
echo "- backup: ${backup_file}"
echo "- restarted: ${RESTART_CONTAINERS}"
echo "- note: secret values are intentionally not printed."
