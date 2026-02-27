# Thread Handoff Prompts

아래 블록을 각 스레드 첫 메시지로 그대로 붙여서 시작하세요.

## 1) llm-proxy/보안 스레드
```text
역할: llm-proxy/보안 담당
범위:
- /proxy/app/routers/**
- /proxy/app/middleware/**
- /proxy/app/utils/**
- /docker-compose.yml
- /docs/SECURITY_ROADMAP.md

금지:
- /src/components/**
- /src/app/api/**

목표(P0):
1) webhook HMAC 실패 원인별 코드/로그 분리
2) memory_update quarantine 승인 경로 점검
3) Telegram inbound replay 방지(ttl+idempotency) 최소 구현

검증:
- docker compose build llm-proxy && docker compose up -d --force-recreate llm-proxy
- /health 200
- 서명 누락 요청 401
- 내부 토큰 정상 요청 200

제출 형식:
- 변경 파일
- 리스크 2개
- 검증 로그
- 롤백 1줄
```

## 2) 기능/API 스레드
```text
역할: 기능/API 담당
범위:
- /src/app/api/**
- /src/lib/server/**
- /src/lib/telegram-codes.ts

금지:
- /proxy/**
- /n8n/workflows/**
- /src/components/** 대규모 변경

목표(P0):
1) /api/chat, /api/agent-updates, /api/telegram/health 응답 포맷 일관화
2) malformed payload 처리 공통 헬퍼화
3) 사용자 에러/내부 에러 분리

검증:
- npm run lint
- GET /api/telegram/health 200
- POST /api/chat 정상+에러 케이스
- malformed 입력 처리 확인

제출 형식:
- 계약 변경 여부(있으면 breaking 여부)
- 검증 로그
- 롤백 1줄
```

## 3) UI/UX 스레드
```text
역할: UI/UX 담당
범위:
- /src/components/**
- /src/app/globals.css

금지:
- API 계약 변경
- /proxy/**
- /n8n/**

목표(P0):
1) 우측 패널 위젯 추가 시 레이아웃 붕괴 재발 방지
2) 채팅 입력창 자동확장/토글 UX 안정화
3) 에이전트 전환 시 컬러/상태 전환 깜빡임 제거

검증:
- npm run lint
- 수동 시나리오: 에이전트 전환/전송/줄바꿈/패널 토글

제출 형식:
- 변경 전후 캡처
- UX 리스크 1~2개
- 롤백 1줄
```

## 4) n8n 워크플로우 스레드
```text
역할: n8n 워크플로우 담당
범위:
- /n8n/workflows/**
- /scripts/n8n/**
- /docs/N8N_LOCAL_SETUP.md

금지:
- /src/**
- /proxy/**

목표(P0):
1) RSS 0건이면 skipped + 큐 미생성 보장
2) Sign Payload(HMAC) 헤더 주입 표준화
3) 소스 장애 시 부분 성공/fallback 문서화

검증:
- n8n execute 2회 (기사 있음/없음)
- webhook auth 누락/정상 각각 확인

제출 형식:
- 워크플로우 JSON 변경 요약
- 실패 케이스 처리 표
- 롤백 1줄
```

## 공통 규칙
- 브랜치: `codex/<area>-<topic>`
- 시작 전 `/docs/WORK_LOCK_BOARD.md` 상태 확인
- 완료 후 `REVIEW` 전환 + PR 링크 기재
- 총책 승인 게이트: `CI / lint`, `Public Repo Guard / guard`, 범위 외 파일 변경 사유
- 작업 마감 자동화:
  - `npm run thread:finish -- "feat(scope): summary"`
