# UI/UX QA Checklist (Chat Dashboard)

## 목적
- `P0/P1 UI·UX 개선`이 실제 동작에서 회귀 없이 유지되는지 빠르게 검증한다.
- 특히 `chat panel 상태 전이`, `outside click dismiss`, `agent 전환 연속성`, `오류 복구 UX`를 집중 확인한다.

## 사전 조건
- `npm ci` 완료
- `npm run dev -- --port 3010` 실행
- 브라우저: 최신 Chrome 권장

## P0 시나리오

### 1) 상태 전이/우선순위
- 대화창 닫힘 상태에서 중앙 하단 패널 클릭 → 열림
- 열림 상태에서 핸들 클릭 → 닫힘
- 열림 상태에서 `Esc` → 닫힘
- 열림 상태에서 리사이즈 시작 후 드래그 중 outside 영역 클릭 → 리사이즈 우선, 패널 유지
- 리사이즈 종료 직후 자동확장 점프가 즉시 과도하게 발생하지 않는지 확인

### 2) outside click dismiss
- 열림 상태에서 `좌/우 패널` 클릭 → 유지
- 열림 상태에서 `채팅 패널 내부` 클릭 → 유지
- 열림 상태에서 `그 외 바깥 영역` 클릭 → 닫힘

### 3) 에이전트 전환 연속성
- `ace` 입력 draft 작성 후 `owl`로 전환, 다른 draft 작성
- 다시 `ace`로 전환 시 기존 draft 복원 확인
- 각 에이전트 스크롤을 다른 위치로 둔 뒤 전환 시 위치가 유지되는지 확인

### 4) 오류 복구 UX
- `/api/chat` 실패를 유도(임시 500 등)해 system 메시지 표시 확인
- 최신 오류 메시지 하단 `재시도`, `요청 복사` 버튼 노출 확인
- `재시도` 클릭으로 동일 요청 재실행되는지 확인

## P1 시나리오

### 5) 슬롯 기반 확장 안전성
- DOM에서 `data-dashboard-slot` 값(`left/center/right/chat`) 존재 확인
- 새 위젯을 추가할 때 해당 슬롯 안쪽만 수정하면 레이아웃 충돌이 없는지 확인

### 6) 모션/접근성
- OS `prefers-reduced-motion: reduce` 활성 시 과도한 애니메이션 중단 확인
- 패널 핸들 `aria-expanded` 값이 열림/닫힘에 맞게 변하는지 확인
- 채팅 로그가 `role="log"` + `aria-live="polite"`로 노출되는지 확인

### 7) 키보드 흐름
- `Ctrl+/` 패널 토글 동작 확인
- `Enter` 전송 / `Shift+Enter` 줄바꿈 확인
- `Ctrl+1/2/3` 에이전트 전환 확인

### 8) 지표 이벤트
- DevTools Console에서 `[ux-metric]` 로그 확인
- 확인 대상:
  - `chat_send_success_ms`
  - `chat_panel_outside_close`
  - `agent_switch_reinput`

## 회귀 방지 체크
- 우측 패널 표시/비표시 전환 시 중앙 및 채팅 패널 inset이 자연스럽게 재배치되는지 확인
- 에이전트 전환 시 컬러/글로우 변화가 순간 깜빡임 없이 transition 되는지 확인
- 채팅 열림 상태에서 빠른 연속 입력/수신 시 패널 높이 흔들림이 없는지 확인
