# NanoClaw Operations Playbook (Public)

기준 경로: `/Users/isanginn/Workspace/Agent_Workspace`  
범위: 공개 저장소에 포함 가능한 운영 표준

## 1) 운영 대상

- Next.js: `http://localhost:3000`
- llm-proxy: `http://127.0.0.1:8000`
- n8n: `http://127.0.0.1:5678`
- nanoclaw-agent: 파일 감시/비동기 처리

## 2) 일일 운영 루틴

### 시작 점검

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
docker compose ps
docker compose logs --tail=80 llm-proxy
docker compose logs --tail=80 nanoclaw-agent
docker compose logs --tail=80 nanoclaw-n8n
curl -sS http://localhost:8000/health
```

### 기능 점검

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
bash scripts/security/telegram_api_smoke.sh
bash scripts/n8n/test-hermes-daily-briefing.sh
```

### 종료 점검

- `shared_data/agent_comms/deadletter` 적체 여부 확인
- 자동 브리핑 누락 여부 확인
- 실패 로그를 `docs/ACTION_PLAN.md`로 이관

## 3) 배포/재기동

### 전체

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
npm run security:ensure-volumes
docker compose build
docker compose up -d --force-recreate
docker compose ps
```

### 특정 서비스

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
docker compose build llm-proxy
docker compose up -d --force-recreate llm-proxy
docker compose logs --tail=120 llm-proxy
```

## 4) 보안 운영 표준

### 내부 비밀값 로테이션

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
npm run security:rotate-internal
```

후속 검증:

```bash
docker compose ps
curl -sS http://localhost:8000/health
bash scripts/security/telegram_api_smoke.sh
npm run security:check-critical
```

### 외부 키 운영 원칙

- 외부 API 키는 수동 로테이션
- 키 변경 후 즉시 재기동
- 키 값은 문서/커밋/이슈/스크린샷에 기록 금지

## 5) 장애 등급 (운영/유지보수 기준)

### P0
- 전 채널 응답 불가
- 인증 우회/비밀값 유출 의심
- 주요 데이터 손상

SLA: 15분 이내 완화 시작

### P1
- Telegram 또는 n8n 단일 채널 중단
- Hermes 데일리 브리핑 누락
- auto-merge 파이프라인 정지

SLA: 2시간 이내 원인 확인 + 임시 완화

### P2
- UI 표시 오류
- 비핵심 자동화 실패
- 문서/운영 도구 경고성 이슈

SLA: 다음 배포 주기 내 해결

## 6) 대표 장애 런북

### 6.1 nanoclaw -> llm-proxy 401

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
docker compose up -d --force-recreate llm-proxy nanoclaw-agent
docker compose logs --tail=120 llm-proxy
docker compose logs --tail=120 nanoclaw-agent
```

### 6.2 Telegram 무응답

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
bash scripts/security/telegram_api_smoke.sh
```

### 6.3 n8n webhook 404

- workflow active 상태 확인
- webhook 경로 drift 확인

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
bash scripts/n8n/test-local-web-search.sh "2026 한국 AI 트렌드"
```

### 6.4 Calendar OAuth 실패

- 테스트 사용자/redirect URI/refresh token 재확인
- `llm-proxy` 재기동 후 health 재검증

## 7) 변경관리

- 병렬 개발 시 `/Users/isanginn/Workspace/Agent_Workspace/docs/WORK_LOCK_BOARD.md` 선점 필수
- PR/머지 게이트:
  - `lint`
  - `Public Repo Guard / guard`
- 머지 순서:
  1. PROXY+SECURITY
  2. API
  3. WORKFLOW
  4. UI/UX

## 8) 관측/감시

### Release Captain Watch

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
npm run watch:codex:start
npm run watch:codex:status
npm run watch:codex:logs
```

중지:

```bash
npm run watch:codex:stop
```

## 9) 금지사항

- `.env.local` 커밋 금지
- 운영 중 `docker volume rm agent_workspace_n8n_data` 금지
- `latest` 이미지 태그 임의 사용 금지

## 10) 연계 문서

- `/Users/isanginn/Workspace/Agent_Workspace/docs/SECURITY_MODEL.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/SECURITY_ROADMAP.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/N8N_LOCAL_SETUP.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/TELEGRAM_AGENT_BRIDGE.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/GOOGLE_CALENDAR_READONLY_SETUP.md`
