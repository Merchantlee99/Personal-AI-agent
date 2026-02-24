# Agent Comms Pipeline

이 문서는 에이전트 간 비동기 파일 메시지 버스 설계를 설명합니다.

## 폴더 구조

```text
shared_data/agent_comms/
├── inbox/
│   ├── ace/
│   ├── owl/
│   └── dolphin/
├── outbox/
│   ├── ace/
│   ├── owl/
│   └── dolphin/
├── archive/
├── deadletter/
└── router.log
```

## 메시지 파일명 규칙

```text
{from}_{to}_{YYYYMMDD}_{HHmmss}_{type}.json
```

예시:

```text
owl_ace_20260225_143022_report.json
```

## 메시지 포맷

```json
{
  "meta": {
    "id": "uuid-v4",
    "from": "owl",
    "to": "ace",
    "timestamp_kst": "2026-02-25T14:30:22+09:00",
    "type": "report",
    "priority": "high",
    "status": "pending"
  },
  "content": {
    "subject": "TripPixel 코드 리뷰 완료",
    "body": "본문 내용. 마크다운 허용.",
    "attachments": []
  },
  "routing": {
    "requires_response": true,
    "deadline": "2026-02-25T18:00:00+09:00",
    "callback_to": "owl"
  }
}
```

## 메시지 생명주기

```text
pending -> delivered -> processing -> done -> archived
```

에러 파일은 `deadletter/`로 이동됩니다.

## send.py

메시지 생성:

```bash
python agent/comms/send.py \
  --from clio \
  --to ace \
  --type report \
  --priority high \
  --subject "빌드 완료" \
  --body "TripPixel v1.0 빌드 성공. 배포 승인 요청."
```

별칭 매핑:

- `ace`, `에이스`, `morpheus`, `모르피어스` -> `ace`
- `owl`, `clio`, `클리오` -> `owl`
- `dolphin`, `hermes`, `헤르메스` -> `dolphin`

## router.py

단발 실행:

```bash
python agent/comms/router.py --once
```

감시 모드:

```bash
python agent/comms/router.py --watch --interval 10
```

기능:

- `outbox/*/*.json` -> 대상 `inbox/{to}` 전달
- 전달 시 상태를 `delivered`로 갱신
- `status=done` 메시지는 `archive/YYYYMMDD/`로 이동
- 예외 파일은 `deadletter/`로 이동
- 로그는 `router.log`에 기록

## 타입 가이드

- `report`: 결과 보고
- `request`: 작업 요청
- `handoff`: 작업 이관
- `alert`: 긴급 알림
