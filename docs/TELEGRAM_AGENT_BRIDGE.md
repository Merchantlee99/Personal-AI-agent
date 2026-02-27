# Telegram Agent Bridge

## 목적
- 텔레그램에서 Morpheus/Clio/Hermes를 호출할 수 있는 보안형 브리지 제공
- agent별 토큰, chat_id allowlist, 명령 권한 분리

## 동작 방식
1. `llm-proxy`가 백그라운드 폴링으로 각 bot `getUpdates` 호출
2. 허용된 `chat_id`만 처리
3. 허용된 명령만 agent 실행 엔진으로 전달
4. 응답을 텔레그램 `sendMessage`로 반환
5. (선택) Morpheus는 웹 채널과 공통 히스토리 DB를 공유 가능

## 지원 명령
- `/read <text>`: 읽기/핵심 정리 (결론 1줄 + 근거 2줄 + 다음 액션 1줄)
- `/summary <text>`: 일반 요약 (핵심 3줄 + 포인트 목록)
- `/trend <text>`: Hermes 전용 트렌드 정리 템플릿
- `/chat <text>`: 자유 질의/일반 대화 (프롬프트 가공 없이 전달)

## 보안 제약
- allowlist 미설정 시 해당 agent 폴링 차단
- `/api/*`는 `x-internal-token` 필수
- 텔레그램 명령은 agent별 허용 명령만 처리

## 환경 변수
```bash
TELEGRAM_BRIDGE_ENABLED=false
TELEGRAM_ENABLED_AGENTS="ace"
TELEGRAM_POLL_INTERVAL_SEC=6
TELEGRAM_MAX_UPDATES_PER_POLL=20
TELEGRAM_HTTP_TIMEOUT_SEC=30

AGENT_SHARED_HISTORY_ENABLED=true
AGENT_SHARED_HISTORY_TARGETS="ace"
AGENT_HISTORY_DB_PATH="/app/shared_data/agent_comms/history/agent_history.sqlite3"
AGENT_HISTORY_MAX_CONTEXT_MESSAGES=20
AGENT_HISTORY_MAX_STORED_MESSAGES=300
AGENT_HISTORY_MAX_MESSAGE_CHARS=4000
ACE_SHARED_USER_ID="owner"

TELEGRAM_BOT_TOKEN_ACE=""
TELEGRAM_ALLOWED_CHAT_IDS_ACE=""
TELEGRAM_ALLOWED_COMMANDS_ACE="read,summary,chat"
TELEGRAM_SHARED_USER_ID_ACE="owner"

TELEGRAM_BOT_TOKEN_OWL=""
TELEGRAM_ALLOWED_CHAT_IDS_OWL=""
TELEGRAM_ALLOWED_COMMANDS_OWL="read,summary,chat"
TELEGRAM_SHARED_USER_ID_OWL=""

TELEGRAM_BOT_TOKEN_DOLPHIN=""
TELEGRAM_ALLOWED_CHAT_IDS_DOLPHIN=""
TELEGRAM_ALLOWED_COMMANDS_DOLPHIN="read,summary,trend,chat"
TELEGRAM_SHARED_USER_ID_DOLPHIN=""
```

## 단계별 활성화

### Stage 1 (Morpheus 파일럿)
```bash
TELEGRAM_BRIDGE_ENABLED=true
TELEGRAM_ENABLED_AGENTS="ace"
TELEGRAM_BOT_TOKEN_ACE="<bot token>"
TELEGRAM_ALLOWED_CHAT_IDS_ACE="<your_chat_id>"
TELEGRAM_SHARED_USER_ID_ACE="owner"
ACE_SHARED_USER_ID="owner"
```

### Stage 2 (Clio/Hermes 확장)
```bash
TELEGRAM_ENABLED_AGENTS="ace,owl,dolphin"
TELEGRAM_BOT_TOKEN_OWL="<bot token>"
TELEGRAM_ALLOWED_CHAT_IDS_OWL="<clio chat_id>"
TELEGRAM_BOT_TOKEN_DOLPHIN="<bot token>"
TELEGRAM_ALLOWED_CHAT_IDS_DOLPHIN="<hermes chat_id>"
```

## 운영용 API
- `GET /api/telegram/health`
- `POST /api/telegram/poll`
- `POST /api/telegram/send`
- `POST /api/telegram/poller/start`

### `GET /api/telegram/health` 응답 규약
```json
{
  "status": "ok",
  "code": "TELEGRAM_HEALTH_OK | TELEGRAM_BRIDGE_DISABLED | TELEGRAM_NOT_CONFIGURED | TELEGRAM_POLLER_STOPPED",
  "message": "ready | disabled | no_enabled_agents | poller_not_running",
  "retryable": false,
  "telegram": {}
}
```

### `POST /api/telegram/send` 응답 규약
- 성공
```json
{
  "status": "ok",
  "code": "TELEGRAM_SENT",
  "message": "sent",
  "retryable": false,
  "agent_id": "ace",
  "chat_id": "123456789"
}
```
- 실패 (`HTTP 4xx/5xx`, `detail` 내부 공통 필드)
```json
{
  "detail": {
    "status": "error",
    "code": "TELEGRAM_BAD_REQUEST | TELEGRAM_FORBIDDEN | TELEGRAM_RATE_LIMITED | TELEGRAM_UNAUTHORIZED | TELEGRAM_NETWORK_ERROR | TELEGRAM_NOT_CONFIGURED | TELEGRAM_UNKNOWN_ERROR",
    "message": "error detail",
    "retryable": false,
    "telegram_status": 400,
    "method": "sendMessage"
  }
}
```

### `POST /api/telegram/poll` 응답 규약
- 성공
```json
{
  "status": "ok",
  "code": "TELEGRAM_POLL_OK | TELEGRAM_POLL_PARTIAL",
  "message": "polled | partial",
  "retryable": false,
  "results": [
    {
      "agent_id": "ace",
      "scanned_updates": 0,
      "processed_commands": 0,
      "sent_replies": 0,
      "skipped_untrusted": 0,
      "last_update_id": null,
      "error_code": null,
      "error_message": null,
      "retryable": false
    }
  ]
}
```
- 실패 (`HTTP 4xx/5xx`, `detail` 내부 공통 필드)
```json
{
  "detail": {
    "status": "error",
    "code": "TELEGRAM_INVALID_AGENT | TELEGRAM_NOT_CONFIGURED",
    "message": "unknown_agent:... | no_enabled_agents",
    "retryable": false
  }
}
```

### `POST /api/telegram/poller/start` 응답 규약
- 성공
```json
{
  "status": "ok",
  "code": "TELEGRAM_POLLER_STARTED",
  "message": "started",
  "retryable": false,
  "started": true,
  "telegram": {}
}
```
- 실패 (`HTTP 503`)
```json
{
  "detail": {
    "status": "error",
    "code": "TELEGRAM_NOT_CONFIGURED",
    "message": "no_enabled_agents",
    "retryable": false
  }
}
```

모든 `/api/*` 호출은 내부 토큰 헤더 필요:
```http
x-internal-token: <LLM_PROXY_INTERNAL_TOKEN>
```

## 스모크 검증 스크립트
응답 스키마(`code/message/retryable`)가 깨지지 않았는지 빠르게 점검:

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
bash scripts/security/telegram_api_smoke.sh
```

직접 실행(동일 동작):
```bash
python3 /Users/isanginn/Workspace/Agent_Workspace/scripts/security/telegram_api_smoke.py
```

- 기본 대상: `http://localhost:8000`
- 다른 주소 검증:
```bash
BASE_URL=http://127.0.0.1:8000 bash scripts/security/telegram_api_smoke.sh
```
