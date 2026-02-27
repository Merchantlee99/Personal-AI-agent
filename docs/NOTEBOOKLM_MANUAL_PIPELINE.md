# NotebookLM Manual Pipeline (Clio)

## 목적
- Clio가 만든 문서를 바로 외부 전송하지 않고, 수동 승인 후 업로드
- 초기 운영에서 데이터 유출/오전송 리스크 최소화

## 파이프라인
1. Stage: Clio 문서를 `pending` 큐에 저장
2. Review: 운영자가 `pending` 목록 확인
3. Approve:
   - 커넥터 비활성: `approved_local`로만 이동
   - 커넥터 활성: 업로드 성공 시 `uploaded`, 실패 시 `failed`
4. Reject: `rejected`로 이동

## 디렉터리
컨테이너 기준:
- `/app/shared_data/agent_comms/notebooklm/pending`
- `/app/shared_data/agent_comms/notebooklm/approved`
- `/app/shared_data/agent_comms/notebooklm/uploaded`
- `/app/shared_data/agent_comms/notebooklm/failed`
- `/app/shared_data/agent_comms/notebooklm/rejected`

호스트 기준:
- `shared_data/agent_comms/notebooklm/*`

## API
- `GET /api/notebooklm/health`
- `GET /api/notebooklm/pending?limit=20`
- `POST /api/notebooklm/stage`
- `POST /api/notebooklm/stage-from-vault`
- `POST /api/notebooklm/approve`

## 입력 제약
- `created_by`는 Clio(`owl`)만 허용
- `stage-from-vault`는 `/app/vault` 내부 파일만 허용

## 커넥터 설정
```bash
NOTEBOOKLM_CONNECTOR_ENABLED=false
NOTEBOOKLM_CONNECTOR_URL=""
NOTEBOOKLM_CONNECTOR_API_KEY=""
NOTEBOOKLM_CONNECTOR_TIMEOUT_SEC=30
```

## 예시
```bash
curl -sS -X POST http://localhost:8000/api/notebooklm/stage \
  -H "Content-Type: application/json" \
  -H "x-internal-token: ${LLM_PROXY_INTERNAL_TOKEN}" \
  -d '{
    "title":"TripPixel 경쟁사 분석",
    "content":"요약 본문 ...",
    "source":"clio_manual",
    "tags":["trip", "market"],
    "created_by":"owl"
  }'
```

```bash
curl -sS -X POST http://localhost:8000/api/notebooklm/approve \
  -H "Content-Type: application/json" \
  -H "x-internal-token: ${LLM_PROXY_INTERNAL_TOKEN}" \
  -d '{"id":"<pending-item-id>", "approve":true}'
```
