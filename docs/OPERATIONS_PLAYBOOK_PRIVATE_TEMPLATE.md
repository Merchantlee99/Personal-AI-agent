# NanoClaw Operations Playbook (Private Template)

주의: 이 파일은 템플릿입니다.  
실제 운영본은 아래 경로로 복사해 작성하세요.

- 대상 파일: `/Users/isanginn/Workspace/Agent_Workspace/ops_private/OPERATIONS_PLAYBOOK_PRIVATE.md`

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
cp docs/OPERATIONS_PLAYBOOK_PRIVATE_TEMPLATE.md ops_private/OPERATIONS_PLAYBOOK_PRIVATE.md
```

---

## 0) 보안 규칙

- 실제 키/토큰/개인식별정보를 Git tracked 파일에 기록 금지
- 본문에는 값 대신 위치/책임자/만료일만 기록
- 스크린샷 공유 시 민감정보 마스킹

---

## 1) 비상 연락/책임 체계

- 운영 오너:
- Release Captain:
- 보안 담당:
- n8n 워크플로우 담당:
- UI/API 담당:

---

## 2) 민감 구성요소 인벤토리 (값은 쓰지 않음)

### 2.1 외부 키
- OpenAI: 발급 위치 / 만료 정책 / 마지막 교체일
- Anthropic:
- Gemini:
- Tavily:
- Telegram(ace):
- Telegram(owl):
- Telegram(dolphin):

### 2.2 OAuth
- Google Calendar client_id 관리 위치:
- refresh token 교체 이력:
- 테스트 사용자 목록:

### 2.3 내부 토큰
- `LLM_PROXY_INTERNAL_TOKEN` 교체 정책:
- `N8N_WEBHOOK_AUTH_TOKEN` 교체 정책:

---

## 3) 실제 운영 체크리스트 (로컬 환경)

### 3.1 Daily Start
- [ ] `docker compose ps` 정상
- [ ] `llm-proxy` health 정상
- [ ] Telegram smoke 정상
- [ ] Hermes briefing 테스트 정상

### 3.2 Daily End
- [ ] deadletter 적체 0 또는 원인 기록
- [ ] 실패 로그 triage 완료
- [ ] 다음날 처리 항목 `docs/ACTION_PLAN.md` 반영

---

## 4) P0/P1 비상 복구 절차 (실무 기록)

### 4.1 P0 템플릿
- 발생 시각:
- 영향 범위:
- 1차 차단 조치:
- 원인:
- 영구 조치:
- 재발 방지:

### 4.2 P1 템플릿
- 장애 유형:
- 임시 우회:
- 정상화 시각:
- 추적 이슈 링크:

---

## 5) 키 유출 의심 시 즉시 실행 절차

1) 노출 키 폐기  
2) 신규 발급  
3) `.env.local` 교체  
4) 내부 토큰 회전  
5) 재기동  
6) 호출 로그 검증  

운영 명령:

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
npm run security:rotate-internal
docker compose up -d --force-recreate llm-proxy nanoclaw-agent n8n
```

사후 점검:
- [ ] 비정상 호출 IP/패턴 없음
- [ ] Telegram/n8n/calendar 경로 정상

---

## 6) 워크플로우 드리프트 관리

- n8n webhook path 변경 시 반영 목록:
  - `.env.local` `N8N_WEBHOOK_URL_INTERNAL`
  - 관련 테스트 스크립트
  - 운영 문서 링크

- drift 점검 주기:
- 마지막 점검일:

---

## 7) Release Captain 운영 메모 (비공개)

- auto-merge 실패 패턴:
- 수동 머지 시 주의사항:
- branch protection 변경 이력:

---

## 8) 감사 로그 (비공개)

| 날짜 | 조치 | 범위 | 담당 | 결과 |
|---|---|---|---|---|
| YYYY-MM-DD | 예: 내부토큰 회전 | llm-proxy/n8n | owner | success |

