#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
RUN_N8N_WEBHOOK_TEST=true
RUN_PROXY_SEARCH_TEST=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --skip-n8n-webhook)
      RUN_N8N_WEBHOOK_TEST=false
      shift
      ;;
    --skip-proxy-search)
      RUN_PROXY_SEARCH_TEST=false
      shift
      ;;
    *)
      echo "[error] Unknown option: $1" >&2
      echo "Usage: $0 [--env-file <path>] [--skip-n8n-webhook] [--skip-proxy-search]" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[error] Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

read_key_value() {
  local key="$1"
  awk -F= -v k="${key}" '$1 == k { print $2; found=1 } END { if (!found) print "" }' "${ENV_FILE}" \
    | sed -e 's/^"//' -e 's/"$//'
}

INTERNAL_TOKEN="$(read_key_value "LLM_PROXY_INTERNAL_TOKEN")"
N8N_WEBHOOK_URL_HOST="$(read_key_value "N8N_WEBHOOK_URL_HOST")"
if [[ -z "${N8N_WEBHOOK_URL_HOST}" ]]; then
  N8N_WEBHOOK_URL_HOST="http://localhost:5678/webhook/hermes-trend"
fi

if [[ -z "${INTERNAL_TOKEN}" ]]; then
  echo "[FAIL] LLM_PROXY_INTERNAL_TOKEN is empty in ${ENV_FILE}" >&2
  exit 1
fi

FAIL_COUNT=0

pass() {
  echo "[OK] $1"
}

fail() {
  echo "[FAIL] $1" >&2
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

http_code() {
  curl -sS -o /tmp/critical_check_resp.json -w "%{http_code}" "$@"
}

echo "[check] containers running"
for name in llm-proxy nanoclaw-agent nanoclaw-n8n; do
  if docker inspect "${name}" >/dev/null 2>&1; then
    running="$(docker inspect -f '{{.State.Running}}' "${name}" 2>/dev/null || true)"
    if [[ "${running}" == "true" ]]; then
      pass "${name} running"
    else
      fail "${name} not running"
    fi
  else
    fail "${name} not found"
  fi
done

echo "[check] llm-proxy health"
code="$(http_code http://localhost:8000/health || true)"
if [[ "${code}" == "200" ]]; then
  pass "GET /health = 200"
else
  fail "GET /health expected 200, got ${code}"
fi

echo "[check] internal token gate"
code="$(http_code http://localhost:8000/api/telegram/health || true)"
if [[ "${code}" == "401" ]]; then
  pass "GET /api/telegram/health without token = 401"
else
  fail "GET /api/telegram/health without token expected 401, got ${code}"
fi

code="$(http_code -H "x-internal-token: ${INTERNAL_TOKEN}" http://localhost:8000/api/telegram/health || true)"
if [[ "${code}" == "200" ]]; then
  pass "GET /api/telegram/health with token = 200"
else
  fail "GET /api/telegram/health with token expected 200, got ${code}"
fi

echo "[check] hermes webhook double-gate"
code="$(http_code -X POST -H "Content-Type: application/json" \
  -d '{"title":"check","digest_text":"check","articles":[]}' \
  http://localhost:8000/api/hermes/daily-briefing || true)"
if [[ "${code}" == "401" ]]; then
  pass "POST /api/hermes/daily-briefing without token = 401"
else
  fail "POST /api/hermes/daily-briefing without token expected 401, got ${code}"
fi

code="$(http_code -X POST \
  -H "Content-Type: application/json" \
  -H "x-internal-token: ${INTERNAL_TOKEN}" \
  -H "x-webhook-timestamp: 0" \
  -H "x-webhook-signature: sha256=invalid" \
  -d '{"title":"check","digest_text":"check","articles":[]}' \
  http://localhost:8000/api/hermes/daily-briefing || true)"
if [[ "${code}" == "401" ]]; then
  pass "POST /api/hermes/daily-briefing with invalid webhook signature = 401"
else
  fail "POST /api/hermes/daily-briefing with invalid webhook signature expected 401, got ${code}"
fi

if [[ "${RUN_N8N_WEBHOOK_TEST}" == "true" ]]; then
  echo "[check] n8n webhook path"
  code="$(http_code -X POST \
    -H "Content-Type: application/json" \
    -d '{"query":"healthcheck","source":"critical_check","agentId":"dolphin"}' \
    "${N8N_WEBHOOK_URL_HOST}" || true)"
  if [[ "${code}" == "404" ]]; then
    fail "N8N webhook path not registered or workflow inactive (POST ${N8N_WEBHOOK_URL_HOST})"
  elif [[ "${code}" =~ ^2[0-9][0-9]$ ]]; then
    pass "N8N webhook reachable (${code})"
  else
    fail "N8N webhook unexpected status ${code} (POST ${N8N_WEBHOOK_URL_HOST})"
  fi
fi

if [[ "${RUN_PROXY_SEARCH_TEST}" == "true" ]]; then
  echo "[check] llm-proxy search route"
  code="$(http_code -X POST \
    -H "Content-Type: application/json" \
    -H "x-internal-token: ${INTERNAL_TOKEN}" \
    -d '{"query":"healthcheck","agentId":"dolphin","source":"critical_check"}' \
    http://localhost:8000/api/search || true)"
  if [[ "${code}" =~ ^2[0-9][0-9]$ ]]; then
    pass "POST /api/search reachable (${code})"
  else
    fail "POST /api/search expected 2xx, got ${code}"
    if [[ -f /tmp/critical_check_resp.json ]]; then
      echo "  detail: $(cat /tmp/critical_check_resp.json | tr '\n' ' ' | cut -c1-240)" >&2
    fi
  fi
fi

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
  echo "[result] FAIL (${FAIL_COUNT} checks failed)" >&2
  exit 1
fi

echo "[result] OK (all critical checks passed)"
