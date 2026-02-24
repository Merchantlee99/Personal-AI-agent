# n8n Local Owner Account (Dev Only)

이 문서는 로컬 n8n 초기 셋업용 계정 정보 메모입니다.
프로덕션 사용 금지.

## Owner Account

- Email: `nanoclaw.local.admin@example.com`
- Password: `O4lN2QJRv+u6ES95BMSP`

## API Key 필요 여부

- 현재 구성(로컬 webhook 호출: `llm-proxy -> n8n webhook`)에서는 **n8n API key 불필요**.
- API key는 아래 경우에만 필요:
  - n8n REST API를 직접 호출해서 워크플로우/실행을 제어할 때
  - n8n 외부 서비스 연동에서 토큰 인증이 필요한 경우

## 현재 운영 기준

- Hermes 트렌드 경로는 webhook 기반:
  - 내부: `http://n8n:5678/webhook/hermes-trend`
  - 호스트: `http://localhost:5678/webhook/hermes-trend`
