#!/usr/bin/env bash
set -euo pipefail

QUERY="${1:-2026 한국 AI 트렌드}"
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL_HOST:-http://localhost:5678/webhook/hermes-trend}"
PROXY_SEARCH_URL="${PROXY_SEARCH_URL:-http://localhost:8000/api/search}"
INTERNAL_TOKEN="${LLM_PROXY_INTERNAL_TOKEN:-}"
if [[ -z "${TAVILY_API_KEY:-}" && -f ".env.local" ]]; then
  TAVILY_API_KEY="$(grep -E '^TAVILY_API_KEY=' .env.local | head -n 1 | cut -d'=' -f2- || true)"
fi
if [[ -z "${INTERNAL_TOKEN}" && -f ".env.local" ]]; then
  INTERNAL_TOKEN="$(grep -E '^LLM_PROXY_INTERNAL_TOKEN=' .env.local | head -n 1 | cut -d'=' -f2- | sed -e 's/^"//' -e 's/"$//' || true)"
fi

echo "[1/2] n8n webhook direct test"
echo "POST ${N8N_WEBHOOK_URL}"
curl -sS -X POST "${N8N_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"${QUERY}\",\"source\":\"nanoclaw\",\"agentId\":\"dolphin\",\"tavily_api_key\":\"${TAVILY_API_KEY:-}\"}" | sed 's/^/  /'
echo

echo "[2/2] llm-proxy /api/search test"
echo "POST ${PROXY_SEARCH_URL}"
curl -sS -X POST "${PROXY_SEARCH_URL}" \
  -H "Content-Type: application/json" \
  -H "x-internal-token: ${INTERNAL_TOKEN}" \
  -d "{\"query\":\"${QUERY}\"}" | sed 's/^/  /'
echo
