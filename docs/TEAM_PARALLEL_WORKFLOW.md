# Team Parallel Workflow

## 목적
- 여러 에이전트/작업자가 동시에 개발해도 충돌 없이 빠르게 머지하기 위한 운영 기준.
- 현재 프로젝트 특성(보안/인프라/UX 동시 변경)을 반영한 최소 역할 체계 정의.

## 권장 역할(최소 4, 권장 6)
1. 총책 승인(Release Captain)
- 최종 머지 승인 1인.
- 릴리스 기준/우선순위/충돌 조정 책임.

2. 기능 확장 담당(Feature Lead)
- API/에이전트 기능 추가, 라우팅, 워크플로우 확장 담당.
- 비즈니스 요구사항을 코드로 구체화.

3. UI/UX 담당(UI Lead)
- 대시보드/채팅 UX, 상태 시각화, 컴포넌트 일관성 담당.
- 접근성/사용성/시각 품질 책임.

4. 보안/인프라 담당(Security & Infra)
- Docker/네트워크/토큰/비밀값/권한 정책 담당.
- 배포 전 보안 체크리스트 통과 책임.

5. 데이터/워크플로우 담당(Workflow Lead, n8n)
- RSS/웹훅/스케줄/브리핑 파이프라인 담당.
- n8n 템플릿/운영 안정성/재실행 전략 책임.

6. 통합 검증 담당(QA Integrator)
- API 연동, 회귀 테스트, E2E 스모크 테스트, 장애 재현 담당.
- 머지 전 검증 로그/증적 취합.

참고:
- 인원이 부족하면 1인이 여러 역할을 겸임 가능.
- 단, 총책 승인 역할은 개발 역할과 분리하는 것이 가장 안전함.

## 브랜치/PR 운영 규칙
- 브랜치 네이밍: `codex/<area>-<short-topic>`
  - 예: `codex/ui-chat-panel`, `codex/security-token-gate`
- 한 PR은 한 주제만 포함:
  - `UI`, `API`, `INFRA`, `SECURITY`, `N8N`, `DOCS` 중 1~2개 범위.
- 강제 체크:
  - 관련 문서 업데이트(설계/보안/운영)
  - 로컬 검증 로그 첨부
  - 런타임 비밀값/데이터 미포함 확인

## 머지 게이트(총책 승인 기준)
1. 기능 정확성: 요구사항 충족 + 기존 플로우 회귀 없음
2. 보안 조건: 토큰/권한/헤더/네트워크 정책 훼손 없음
3. 운영 가능성: 장애 시 롤백/복구 방법 문서화
4. 증적: 실행 로그 또는 스크린샷 첨부

## 권장 작업 분배(현재 프로젝트 기준)
- Feature Lead: Morpheus/Clio/Hermes 기능 확장, Telegram command scope
- UI Lead: 중앙 비주얼 + 채팅 패널 + 상태 패널 일관성
- Security & Infra: llm-proxy gate, 내부 토큰, compose 보안 옵션
- Workflow Lead: Hermes daily briefing, n8n webhook/스케줄 안정화
- QA Integrator: `/api/chat`, `/api/agent-updates`, `/api/telegram/health` 회귀 검증
- Release Captain: PR 승인, 릴리스 노트/릴리즈 태깅

## 일일 운영 루틴(권장)
1. 오전 10분 스탠드업: 오늘 파일 락/작업 범위 선언
2. 점심 전 중간 통합: 충돌 가능 영역 조기 확인
3. 오후 EOD 통합: QA 체크 후 머지 후보 선정
4. 총책 최종 승인 후 main 반영

## 자동화 명령(권장)
각 작업 스레드 마감:

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
npm run thread:finish -- "feat(scope): short summary"
```

총책 순차 머지:

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
npm run release:merge-order -- \
  codex/proxy-security-xxx \
  codex/api-contract-xxx \
  codex/n8n-workflow-xxx \
  codex/ui-polish-xxx
```

주의:
- 머지 스크립트는 순서 고정이며 브랜치 4개를 명시적으로 받아서 오작동을 줄입니다.
- 충돌 발생 시 즉시 중단되며, 총책이 수동 조정 후 재실행해야 합니다.
