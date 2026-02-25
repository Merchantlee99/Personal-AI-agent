#!/usr/bin/env bash
set -euo pipefail

LLM_PROXY_URL="${LLM_PROXY_URL:-http://localhost:8000}"
NEXT_URL="${NEXT_URL:-http://localhost:3000}"
START="${1:-$(date -u -v-1d '+%Y-%m-%dT00:00:00Z' 2>/dev/null || date -u -d '1 day ago' '+%Y-%m-%dT00:00:00Z')}"
END="${2:-$(date -u '+%Y-%m-%dT00:00:00Z')}"

echo "[1/2] Queue Hermes daily briefing"
curl -sS -X POST "${LLM_PROXY_URL}/api/hermes/daily-briefing" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\":\"Hermes Daily Trend Briefing\",
    \"source\":\"manual_test\",
    \"period_start\":\"${START}\",
    \"period_end\":\"${END}\",
    \"digest_text\":\"지난 24시간 테스트 digest: AI 에이전트, 여행테크, PM 트렌드 항목.\",
    \"articles\":[
      {
        \"source\":\"TechCrunch\",
        \"title\":\"Test AI Agent article\",
        \"url\":\"https://example.com/ai-agent\",
        \"published_at\":\"${END}\",
        \"summary\":\"테스트 요약\"
      }
    ]
  }" | sed 's/^/  /'
echo

echo "[2/2] Pull proactive updates from Next.js API (requires dev server on :3000)"
curl -sS "${NEXT_URL}/api/agent-updates" | sed 's/^/  /'
echo
