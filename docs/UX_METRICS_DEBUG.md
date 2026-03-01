# UX Metrics Debug Guide

## 목적
- `dashboard:ux-metric` 이벤트를 로컬에서 빠르게 확인하고 QA 기록에 활용한다.

## 현재 발행 지표
- `chat_send_success_ms`: 전송 요청부터 성공 응답까지 소요 시간(ms)
- `chat_panel_outside_close`: 패널 바깥 클릭으로 닫힌 횟수
- `agent_switch_reinput`: 에이전트 전환 후 입력 재개까지 걸린 시간(ms)

## 콘솔 확인 방법
`NODE_ENV !== production`에서는 자동으로 콘솔에 출력된다.

예시 로그:
```text
[ux-metric] { metric: "chat_send_success_ms", agentId: "ace", value: 842, ts: "..." }
```

## 수동 리스너 (선택)
브라우저 콘솔에서 아래를 실행하면 이벤트를 별도로 수집할 수 있다.

```js
window.__uxMetrics = [];
window.addEventListener("dashboard:ux-metric", (event) => {
  window.__uxMetrics.push(event.detail);
  console.table(window.__uxMetrics.slice(-10));
});
```

## QA 리포트 템플릿
- 테스트 일시:
- 브랜치/커밋:
- 시나리오:
- 수집 지표:
  - `chat_send_success_ms` p50/p95:
  - `chat_panel_outside_close` 총 횟수:
  - `agent_switch_reinput` 평균:
- 이슈/관찰:
