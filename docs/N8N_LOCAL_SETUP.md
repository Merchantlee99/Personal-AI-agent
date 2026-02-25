# n8n Local Setup (Hermes Web Search Flow)

## 목적
- 로컬 OrbStack/Docker 환경에서 Hermes 웹검색 플로우를 n8n webhook으로 운영.
- 요청 경로를 `llm-proxy -> n8n -> llm-proxy 응답`으로 고정.

## 사전 준비
1. 컨테이너 기동 확인:
```bash
cd /Users/isanginn/Workspace/Agent_Workspace
docker compose ps
```
2. `.env.local`에 아래 값 확인:
```env
N8N_WEBHOOK_URL_INTERNAL=http://n8n:5678/webhook/hermes-trend
N8N_WEBHOOK_URL_HOST=http://localhost:5678/webhook/hermes-trend
N8N_WEBHOOK_URL=http://localhost:5678/webhook/hermes-trend
TAVILY_API_KEY=tvly-...
LLM_PROXY_INTERNAL_TOKEN=...
```

주의:
- 현재 구성은 `llm-proxy`가 `tavily_api_key`를 n8n webhook body에 포함해 전달합니다.
- n8n의 Code 노드에서 `$env` 접근이 차단된 경우에도 동작하도록 설계되었습니다.
- 보안 미들웨어가 적용된 환경에서는 n8n -> llm-proxy HTTP Request 노드에
  `x-internal-token: {{$env.LLM_PROXY_INTERNAL_TOKEN}}` 헤더를 추가해야 합니다.

## 방법 A: 템플릿 Import (권장)
1. n8n 접속: `http://localhost:5678`
2. `Import from File` 선택
3. 파일 선택:
   - `/Users/isanginn/Workspace/Agent_Workspace/n8n/workflows/hermes-trend-local.template.json`
4. 워크플로우 이름 확인: `Hermes Trend Local`
5. `Active` 토글 ON

이 템플릿은 아래 노드로 구성됩니다.
- `Webhook (POST /webhook/hermes-trend)`
- `Normalize Input (query/source/agentId/tavily_api_key 정규화)`
- `Search Tavily (Code node / fetch)`
- `Build Final Text (응답 가공, final_text/filename 반환)`

스케줄 기반 자동 브리핑 템플릿도 같이 제공됩니다.
- `/Users/isanginn/Workspace/Agent_Workspace/n8n/workflows/hermes-daily-briefing-schedule.template.json`
- 구성: `Cron(매일 09:00) -> RSS Read -> 24h Digest -> llm-proxy /api/hermes/daily-briefing`
- 목적: 사용자 입력 없이 Hermes 자동 브리핑 큐 적재
- 현재는 호환을 위해 `/api/hermes/daily-briefing`가 임시 bypass 경로로 열려 있을 수 있습니다.
  운영 보안 강화 시 bypass 제거 후 위 헤더 방식으로 고정하세요.

### Hermes Daily Briefing RSS 소스 설계 (현재 반영)
- KR IT/기술 블로그:
  - YozmIT: `https://yozm.wishket.com/magazine/feed/`
  - WoowahanTech: `https://techblog.woowahan.com/feed/`
  - KakaoTech: `https://tech.kakao.com/feed/`
  - TossTech: `https://toss.tech/rss.xml`
  - Naver D2: `https://d2.naver.com/d2.atom`
  - Danggeun(대체): `https://medium.com/feed/daangn`
  - Inflab Tech: `https://tech.inflab.com/rss.xml`
- Global AI/딥테크:
  - TLDR: `https://tldr.tech/rss`
  - OpenAI: `https://openai.com/news/rss.xml`
  - Google DeepMind: `https://deepmind.google/blog/rss.xml`
  - Hugging Face: `https://huggingface.co/blog/feed.xml`
- Global 개발 커뮤니티:
  - Dev.to: `https://dev.to/feed`
  - Lobsters: `https://lobste.rs/rss`

### 제외한 소스 (현재 템플릿 미반영)
- GeekNews(`https://news.hada.io/rss`): 403 케이스가 잦아 RSS Read 안정성이 낮음
- LINE Engineering RSS: 403 케이스 존재
- Anthropic 공식 블로그: 고정 RSS URL 미확정
- 데브윈영: 공식 RSS URL 미확정

해외 소스(locale=`global`)는 워크플로우가 `translation_required` 플래그를 붙이고, Hermes 브리핑 렌더러가 한국어 번역 요약을 강제합니다.

## 방법 B: 수동 생성
1. `Webhook` 노드 생성
   - Method: `POST`
   - Path: `hermes-trend`
   - Response Mode: `Last Node`
2. `Set` 노드 생성
   - `query = {{$json.body.query || $json.body.message || ""}}`
   - `source = {{$json.body.source || "nanoclaw"}}`
   - `agentId = {{$json.body.agentId || "dolphin"}}`
   - `tavily_api_key = {{$json.body.tavily_api_key || ""}}`
3. `Code` 노드에서 Tavily 호출 + 오류 폴백
4. `Code` 노드에서 `final_text`, `filename` 생성
5. `Active` 토글 ON

## 검증
자동 검증 스크립트:
```bash
/Users/isanginn/Workspace/Agent_Workspace/scripts/n8n/test-local-web-search.sh
```

Hermes 자동 브리핑 큐 테스트 스크립트:
```bash
/Users/isanginn/Workspace/Agent_Workspace/scripts/n8n/test-hermes-daily-briefing.sh
```

스케줄 워크플로우 수동 실행 검증:
```bash
docker exec nanoclaw-n8n n8n execute --id=hermes-daily-briefing-schedule
curl http://localhost:3000/api/agent-updates
```

개별 검증:
```bash
curl -X POST http://localhost:5678/webhook/hermes-trend \
  -H "Content-Type: application/json" \
  -d '{"query":"2026 한국 AI 트렌드","source":"nanoclaw","agentId":"dolphin","tavily_api_key":"tvly-..."}'
```

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"2026 한국 AI 트렌드"}'
```

## 자주 발생하는 오류
- `404 webhook not registered`
  - 원인: 워크플로우 비활성 또는 Path 오타
  - 조치: `Webhook Path=hermes-trend`, 워크플로우 `Active=ON` 확인

- `502 from llm-proxy`
  - 원인: 내부 URL(`http://n8n:5678/webhook/hermes-trend`) 호출 실패
  - 조치: n8n 직접 호출이 먼저 성공하는지 확인

- `401 Unauthorized from llm-proxy`
  - 원인: `x-internal-token` 헤더 누락 또는 값 불일치
  - 조치:
    1. `.env.local`의 `LLM_PROXY_INTERNAL_TOKEN` 확인
    2. n8n HTTP Request 노드 헤더 추가 (`x-internal-token`)
    3. `docker compose up -d --force-recreate llm-proxy n8n`

- Tavily 4xx/5xx
  - 원인: `TAVILY_API_KEY` 누락/만료 또는 할당량 초과
  - 조치: `.env.local` 키 확인 후 `docker compose up -d --force-recreate llm-proxy n8n`
