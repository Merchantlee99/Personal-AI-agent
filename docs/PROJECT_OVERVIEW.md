# Personal AI Agent Platform - Project Overview

## 1. 프로젝트 목표
이 프로젝트의 목표는 개인용 AI 에이전트 시스템을 로컬 우선(Local-First) 구조로 운영하면서,
보안 격리를 유지한 채 다음 기능을 제공하는 것입니다.

- 멀티 에이전트 대화 인터페이스 제공 (Morpheus / Clio / Hermes)
- 모든 사용자 입력을 서버 라우터를 통해 통제
- 검색/LLM 호출/문서화를 분리한 파이프라인 운영
- 추후 데스크톱 앱(Tauri 등) 확장을 고려한 아키텍처 유지

## 2. 아키텍처 개요
핵심 구성 요소는 아래 3개 계층으로 나뉩니다.

- UI 계층: Next.js App Router 기반 대시보드 및 채팅 화면
- 오케스트레이션 계층: Next.js API 라우터 + llm-proxy(FastAPI)
- 실행 계층: nanoclaw-agent(파일 감시/처리), n8n(웹검색), shared_data 저장소

## 2.1 실제 운영 배치(로컬)
- 컨테이너 런타임: OrbStack(Docker Compose)
- 에이전트 실행: `nanoclaw-agent` 컨테이너
- API 게이트웨이: Next.js API 라우터 + `llm-proxy`
- 워크플로우 엔진: `n8n` 컨테이너
- 외부 검색 경로: `n8n webhook` 경유 후 내부 파이프라인으로 전달

요청 경로 요약:
`Frontend -> Next.js API -> llm-proxy / n8n -> shared_data -> nanoclaw`

## 2.2 에이전트 ID/별칭 정책
- 내부 canonical ID(고정):
  - `ace`, `owl`, `dolphin`
- 사용자/프롬프트 별칭(정규화):
  - `ace | 에이스 | morpheus | 모르피어스 -> ace`
  - `owl | clio | 클리오 -> owl`
  - `dolphin | hermes | 헤르메스 -> dolphin`

이 정책은 Next API, llm-proxy, nanoclaw, comms scripts에 공통 적용됩니다.

## 3. 구축 과정 요약
현재 저장소는 아래 순서로 스캐폴딩/확장되었습니다.

1. Next.js 대시보드 초기 스캐폴딩 및 멀티 에이전트 UI 구성
2. `/api/proxy` 경유 정책 적용 (클라이언트 직접 외부 호출 금지)
3. SQLite 기반 입력 로그 저장 구조 추가
4. Docker Compose 기반 격리 네트워크 구성
5. nanoclaw-agent 파일 감시 파이프라인(수신함 -> vault 변환) 구현
6. llm-proxy에 LLM/검색/에이전트 라우트 추가
7. MEMORY.md 자동 업데이트 파서 연결
8. 캐릭터 기반 에이전트명(Morpheus/Clio/Hermes) 및 보고 스타일 반영
9. 퍼블릭 저장소 공개를 위한 민감정보 Push Guard 도입

## 4. 현재 동작 플로우

### 4.1 채팅 플로우
1. 사용자가 프론트엔드에서 메시지 입력
2. Next.js `/api/chat`이 요청 수신
3. `/api/chat` -> `llm-proxy /api/agent` 전달
4. llm-proxy가 페르소나 + 모델 설정으로 LLM 호출
5. 응답이 UI로 반환되고 에이전트별 히스토리에 저장

### 4.2 검색 플로우
1. 요청이 llm-proxy `/api/search`로 전달
2. llm-proxy가 내부 URL(`N8N_WEBHOOK_URL_INTERNAL`)로 n8n webhook 호출
3. n8n 응답(`final_text`, `filename`)을 수신
4. 필요 시 shared_data 경로에 파일 저장/후속 처리

### 4.3 에이전트 간 비동기 통신 플로우
1. 에이전트가 `outbox/{agent}`에 JSON 메시지 생성
2. `agent/comms/router.py`가 대상 `inbox/{agent}`로 전달 (`pending -> delivered`)
3. `nanoclaw`가 `inbox/ace`를 처리 (`processing -> done`)
4. 처리 완료 메시지는 `archive/YYYYMMDD`로 이동
5. 실패 메시지는 `deadletter`로 이동

경로: `shared_data/agent_comms/{inbox,outbox,archive,deadletter}`

### 4.4 에이전트 메모리 분리
- Morpheus: `shared_data/obsidian_vault/MEMORY.md`
- Clio: `shared_data/obsidian_vault/MEMORY_CLIO.md`
- Hermes: `shared_data/obsidian_vault/MEMORY_HERMES.md`

목적: 최소권한 컨텍스트 공유와 역할별 응답 품질 안정화.

### 4.5 텔레그램 브리지(외부 채널)
- llm-proxy가 에이전트별 봇 토큰/allowlist를 기준으로 폴링 처리
- 명령 스코프를 에이전트별로 분리해 최소권한 운영
- 운영 엔드포인트:
  - `GET /api/telegram/health`
  - `POST /api/telegram/poll-once`
  - `POST /api/telegram/send`

### 4.6 NotebookLM 수동 승인 파이프라인(Clio)
- Clio(owl)만 stage 가능
- 큐 수명주기: `pending -> approved_local/uploaded/failed/rejected`
- API:
  - `POST /api/notebooklm/stage`
  - `POST /api/notebooklm/stage-from-vault`
  - `GET /api/notebooklm/pending`
  - `POST /api/notebooklm/approve`

## 5. 운영 원칙

- Agent ID는 고정(`ace`, `owl`, `dolphin`), 표시명은 프로필로 관리
- 사용자 입력은 항상 서버 라우터를 경유
- 런타임 데이터(shared_data)와 코드 저장소를 분리
- 페르소나 변경은 코드 분기보다 프로필 교체 방식으로 처리
- 병렬 개발 시 `docs/WORK_LOCK_BOARD.md`로 파일 락 선언 후 작업 시작
- 구현/리팩터링은 `docs/PROTOCOL.md`의 SPARC 루프를 기본 절차로 사용

## 6. 공개 저장소 운영 방침
퍼블릭 저장소에는 실행 코드/템플릿만 포함하고,
아래 데이터는 업로드 금지합니다.

- 실제 API 키 및 `.env.local`
- `shared_data/*` 런타임 산출물
- SQLite DB 및 캐시/빌드 산출물

자세한 보안 통제 항목은 `docs/SECURITY_MODEL.md`를 참고하세요.

## 7. 운영 문서 맵
- 프로토콜: `docs/PROTOCOL.md`
- 액션 플랜: `docs/ACTION_PLAN.md`
- 러닝 아카이브: `docs/MEMORY.md`
- 병렬 운영 규칙: `docs/TEAM_PARALLEL_WORKFLOW.md`
- 파일 락 보드: `docs/WORK_LOCK_BOARD.md`
