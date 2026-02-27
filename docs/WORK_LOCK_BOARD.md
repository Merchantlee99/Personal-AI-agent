# Work Lock Board

## 사용 목적
- 같은 파일을 동시에 수정해서 머지 충돌/스파게티가 생기는 것을 방지.
- 작업 시작 전에 락 선언, 종료 후 해제.

## 상태 값
- `LOCKED`: 작업 중 (다른 사람 수정 금지)
- `REVIEW`: 작업 완료, 리뷰 대기
- `FREE`: 누구나 작업 가능

## 현재 락 상태 (Active)
| Area | Main Files | Owner | Status | Started (KST) | ETA | PR |
|---|---|---|---|---|---|---|
| PROXY+SECURITY | `proxy/app/routers/*`, `proxy/app/middleware/*`, `proxy/app/utils/*`, `docker-compose.yml` | `thread-llm-proxy-security` | LOCKED | 2026-02-27 14:49 | 2026-02-27 EOD | - |
| API | `src/app/api/*`, `src/lib/server/*`, `src/lib/telegram-codes.ts` | `thread-feature-api` | LOCKED | 2026-02-27 14:49 | 2026-02-27 EOD | - |
| UI/UX | `src/components/*`, `src/app/globals.css` | `thread-ui-ux` | LOCKED | 2026-02-27 14:49 | 2026-02-27 EOD | - |
| WORKFLOW | `n8n/workflows/*`, `scripts/n8n/*` | `thread-n8n-workflow` | LOCKED | 2026-02-27 14:49 | 2026-02-27 EOD | - |
| RELEASE CAPTAIN | merge/order/approval only | `this-thread` | LOCKED | 2026-02-27 14:49 | ongoing | - |

## 머지 순서 (고정)
1. `PROXY+SECURITY`
2. `API`
3. `WORKFLOW`
4. `UI/UX`

사유:
- 보안/내부 계약을 먼저 고정해야 후속 충돌과 회귀가 줄어듭니다.

## 락 보드 템플릿 (재사용)
| Area | Main Files | Owner | Status | Started (KST) | ETA | PR |
|---|---|---|---|---|---|---|
| UI | `src/components/chat-dashboard.tsx` | - | FREE | - | - | - |
| UI | `src/components/chat-dashboard/*.tsx` | - | FREE | - | - | - |
| API | `src/app/api/chat/route.ts` | - | FREE | - | - | - |
| API | `src/app/api/agent-updates/route.ts` | - | FREE | - | - | - |
| PROXY | `proxy/app/routers/*.py` | - | FREE | - | - | - |
| PROXY | `proxy/app/utils/*.py` | - | FREE | - | - | - |
| AGENT | `agent/nanoclaw.py` | - | FREE | - | - | - |
| WORKFLOW | `n8n/workflows/*.json` | - | FREE | - | - | - |
| INFRA | `docker-compose.yml` | - | FREE | - | - | - |
| DOCS | `docs/*.md` | - | FREE | - | - | - |

## 운영 규칙
1. 작업 시작 전에 해당 파일/영역을 `LOCKED`로 변경.
2. 4시간 이상 점유 시 진행상황 코멘트 필수.
3. 작업 종료 후 `REVIEW`로 변경하고 PR 링크 추가.
4. 머지 완료 후 `FREE`로 복구.
5. 긴급 보안 이슈는 총책 승인 하에 락 우선권 부여.
6. 범위 외 파일 변경 시 PR에 사유와 영향도를 필수 기재.
