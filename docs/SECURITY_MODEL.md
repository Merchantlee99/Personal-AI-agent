# Security Model

## 1. 보안 목표
본 프로젝트의 보안 목표는 다음 3가지를 동시에 달성하는 것입니다.

- 비밀정보(API 키/인증정보) 소스코드 유출 방지
- 에이전트 실행 환경의 최소 권한 운영
- 네트워크 경로 통제(직접 외부 호출 최소화)

## 2. 네트워크 보안 구조

- `airgap_net` (internal: true): 내부 통신 전용
- `external_net`: 외부 API 통신이 필요한 서비스만 연결
- `nanoclaw-agent`: 기본적으로 내부망 중심 동작, 최소 권한 컨테이너
- `llm-proxy`, `n8n`: 필요한 경우에만 외부 통신 브리지 역할

핵심 원칙:
- 클라이언트 브라우저는 외부 LLM/webhook을 직접 호출하지 않음
- 서버 라우터/프록시가 요청을 통제하고 로깅 가능하게 유지

## 2.1 사용자 설정 보안 체계 (현재 운영 방식)
아래는 실제 운영 시 적용한 보안 경계입니다.

1. OrbStack 컨테이너 경계
- `nanoclaw-agent`, `llm-proxy`, `n8n`을 로컬 macOS 위 OrbStack 기반 Docker 환경에서 실행
- 호스트 프로세스와 분리된 컨테이너 경계를 통해 실행 권한/네트워크 권한을 통제

2. API 라우팅 서버 분리
- 프론트엔드 요청은 Next.js API 라우터(`/api/chat`, `/api/proxy`)를 통해서만 처리
- 외부 LLM/웹훅 호출은 `llm-proxy`에서 수행하며 브라우저 직접 호출은 차단

3. n8n 웹훅 중계 전달
- 검색/외부 데이터 수집은 n8n webhook 경유로 수행
- n8n 결과는 지정 포맷(`final_text`, `filename`)으로 수신 후 저장/후처리
- nanoclaw는 직접 인터넷 접근보다 내부 파이프라인 결과 소비 중심으로 동작

4. 결과적 보안 효과
- 경계 분리: UI/라우터/프록시/에이전트 역할 분리
- 경로 통제: 외부 통신 지점을 `llm-proxy`/`n8n`으로 제한
- 권한 축소: nanoclaw 실행 권한과 파일시스템 권한 최소화

## 3. 컨테이너 최소 권한 정책

`nanoclaw-agent` 기준 적용 항목:
- non-root 사용자 실행
- `cap_drop: [ALL]`
- `no-new-privileges:true`
- 루트 파일시스템 read-only 운영(필요 경로는 볼륨으로 분리)
- 리소스 제한(memory/cpu)

## 3.1 n8n 데이터 영속성
- `n8n` 컨테이너는 아래 볼륨으로 상태를 유지:
  - `n8n_data:/home/node/.n8n`
- 보존되는 데이터:
  - owner 계정
  - 워크플로우
  - credential metadata
- 주의: 아래 명령 시 영속 데이터 삭제 가능
  - `docker compose down -v`
  - `docker volume rm agent_workspace_n8n_data`

## 4. 데이터 분리 정책

- 코드: Git 저장소
- 런타임 데이터: `shared_data/*`
- 비밀값: `.env.local` (Git 추적 금지)
- 샘플값: `.env.local.example` (Git 추적 허용)

추가 권장:
- `N8N_ENCRYPTION_KEY`를 고정 설정해 credential 암호화 키를 안정화할 것.

## 5. 푸시 전/후 유출 방지 장치

### 5.1 로컬 가드
- `scripts/prepush-guard.sh`
- 검사 항목:
  - 금지 파일 추적 여부 (`.env.local`, `shared_data/*`, `*.db` 등)
  - 주요 API 키 패턴 문자열 포함 여부

### 5.2 원격 가드 (GitHub Actions)
- `.github/workflows/public-repo-guard.yml`
- push / pull_request 시 동일 guard 실행

## 6. 체크리스트

퍼블릭 푸시 전 필수 점검:
1. `npm run git:guard`
2. `git status`에서 민감 파일 추적 여부 재확인
3. `.env.local` 미추적 상태 확인
4. 필요 시 키 로테이션(노출 이력 의심 시)

## 7. 권장 추가 보안

- Secret scanning 도구(gitleaks/trufflehog) CI 추가
- Docker 이미지 취약점 스캔(Trivy) 추가
- 역할 기반 토큰 분리(개발/운영 키 분리)
- 로그 마스킹 정책 도입

## 8. 로컬 n8n 운영 메모
- 로컬 owner 계정은 형식이 맞는 이메일이면 생성 가능(실수신 검증 강제 아님).
- 다만 퍼블릭 저장소에는 실제 운영용 계정/비밀번호를 커밋하지 않는 것을 권장.
- 본 저장소의 `docs/N8N_LOCAL_ACCOUNT.md`는 개발/로컬 테스트 목적이며 프로덕션 사용 금지.
