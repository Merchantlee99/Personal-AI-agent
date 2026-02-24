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

## 3. 컨테이너 최소 권한 정책

`nanoclaw-agent` 기준 적용 항목:
- non-root 사용자 실행
- `cap_drop: [ALL]`
- `no-new-privileges:true`
- 루트 파일시스템 read-only 운영(필요 경로는 볼륨으로 분리)
- 리소스 제한(memory/cpu)

## 4. 데이터 분리 정책

- 코드: Git 저장소
- 런타임 데이터: `shared_data/*`
- 비밀값: `.env.local` (Git 추적 금지)
- 샘플값: `.env.local.example` (Git 추적 허용)

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
