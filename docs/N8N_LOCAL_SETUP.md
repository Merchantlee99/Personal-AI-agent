# n8n Local Setup (Hermes Trend Route)

## 목적
- 로컬 OrbStack/Docker 환경에서 n8n webhook을 활성화하여
  Hermes 트렌드 질의를 내부 경로로 처리.

## 환경변수 규칙
- 내부(컨테이너 간): `N8N_WEBHOOK_URL_INTERNAL=http://n8n:5678/webhook/hermes-trend`
- 호스트(브라우저/로컬 서버): `N8N_WEBHOOK_URL_HOST=http://localhost:5678/webhook/hermes-trend`
- 하위 호환: `N8N_WEBHOOK_URL=http://localhost:5678/webhook/hermes-trend`

## 컨테이너 상태 확인
```bash
cd /Users/isanginn/Workspace/Agent_Workspace
docker compose ps
```

## n8n 워크플로우 생성 (최소 동작)
1. Workflow 생성: `Hermes Trend Webhook`
2. `Webhook` 노드
   - Method: `POST`
   - Path: `hermes-trend`
3. `Set` 노드(입력 정규화)
   - `query = {{$json.body.query || $json.body.message || ""}}`
   - `source = {{$json.body.source || "nanoclaw"}}`
   - `agentId = {{$json.body.agentId || "dolphin"}}`
4. (선택) 기존 RSS/필터/요약 체인 연결
5. `Respond to Webhook` 노드
   - JSON 응답 필드:
     - `final_text`
     - `filename`

예시 응답:
```json
{
  "final_text": "트렌드 요약 텍스트",
  "filename": "hermes_20260225_0230.txt"
}
```

6. 워크플로우 `Active` 토글 ON

## 검증
### 1) n8n 직접 호출
```bash
curl -X POST http://localhost:5678/webhook/hermes-trend \
  -H "Content-Type: application/json" \
  -d '{"query":"2026 한국 AI 트렌드","source":"nanoclaw","agentId":"dolphin"}'
```

### 2) llm-proxy 경유 호출
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"2026 한국 AI 트렌드"}'
```

## 자주 발생하는 오류
- `404 webhook not registered`
  - 원인: path 불일치 또는 워크플로우 비활성
  - 조치: `hermes-trend` path 확인 + Active ON

- `502 from llm-proxy`
  - 원인: 내부 n8n 경로 호출 실패/404
  - 조치: n8n webhook 응답부터 먼저 검증
