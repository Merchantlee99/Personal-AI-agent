# Air-Gapped Agent Dashboard Scaffold

## Documentation
- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [Security Model](docs/SECURITY_MODEL.md)
- [n8n Local Setup](docs/N8N_LOCAL_SETUP.md)
- [n8n Local Owner Account (Dev)](docs/N8N_LOCAL_ACCOUNT.md)
- [Agent Comms Pipeline](docs/AGENT_COMMS_PIPELINE.md)
- [UI Redesign v1](docs/UI_REDESIGN_V1.md)
- [Google Calendar Read-Only Setup](docs/GOOGLE_CALENDAR_READONLY_SETUP.md)
- [Security Roadmap](docs/SECURITY_ROADMAP.md)

## Stack
- Next.js (App Router)
- Tailwind CSS + shadcn/ui style components
- SQLite (local persistence through API router)
- Docker Compose (isolated multi-container runtime)

## Runtime Services (OrbStack / Docker Compose)
- `nanoclaw-agent`: file watcher + async comms processor
- `llm-proxy`: FastAPI proxy for agent chat/LLM/search
- `n8n`: local workflow engine for trend collection/search webhook

## Latest Updates (2026-02-25)
- Week 1 security hardening applied:
  - `llm-proxy` security middleware (`x-internal-token`, rate limit, body-size guard)
  - API error detail hardening (`llm/search/agent`)
  - server-to-server token forwarding in Next.js `/api/chat` and `agent/llm_client.py`
  - host-published ports restricted to localhost (`127.0.0.1:8000`, `127.0.0.1:5678`)
  - `nanoclaw-agent` token injection path aligned with `env_file: .env.local` (resolved intermittent internal 401)
- Local n8n routing standardized:
  - internal: `N8N_WEBHOOK_URL_INTERNAL=http://n8n:5678/webhook/hermes-trend`
  - host: `N8N_WEBHOOK_URL_HOST=http://localhost:5678/webhook/hermes-trend`
- Agent async comms bus under `shared_data/agent_comms`:
  - `inbox/`, `outbox/`, `archive/`, `deadletter/`
  - helper scripts: `agent/comms/send.py`, `agent/comms/router.py`
- Per-agent memory separation:
  - Morpheus: `MEMORY.md`
  - Clio: `MEMORY_CLIO.md`
  - Hermes: `MEMORY_HERMES.md`
- Agent alias normalization added across API/proxy/pipeline:
  - `ace|에이스|morpheus|모르피어스 -> ace`
  - `owl|clio|클리오 -> owl`
  - `dolphin|hermes|헤르메스 -> dolphin`
- Local n8n workflow template added:
  - `n8n/workflows/hermes-trend-local.template.json`
- Hermes proactive briefing pipeline added:
  - `n8n/workflows/hermes-daily-briefing-schedule.template.json`
  - `llm-proxy /api/hermes/daily-briefing` queues autonomous updates
  - frontend polls `/api/agent-updates` and appends Hermes auto messages
- UI interaction polish completed:
  - center hologram agent core + panel color synchronization by active agent
  - bottom chat panel opens by panel click, handle-only collapse/expand toggle
  - auto-growing composer (multiline) + in-field send button + key/click feedback
  - proactive unread indicators on agent list
- Morpheus calendar read-only integration added:
  - `llm-proxy /api/calendar/health` and `/api/calendar/events`
  - `ace` 일정 질의 시 Google Calendar read-only context 자동 주입
  - 이메일/URL/전화번호 마스킹 옵션 지원 (`GOOGLE_CALENDAR_MASK_SENSITIVE=true`)
  - OAuth test-user and refresh-token flow documented in `docs/GOOGLE_CALENDAR_READONLY_SETUP.md`

## Runtime Entry Points (Local)
- Frontend: `http://localhost:3000`
- Next API:
  - `POST /api/chat` (primary chat route)
  - `GET /api/chat` (agent list passthrough)
  - `POST /api/proxy` (legacy proxy/store-forward route)
  - `GET/POST /api/agent-updates` (Hermes autonomous updates)
- llm-proxy:
  - `GET /health`
  - `POST /api/agent`, `GET /api/agents`
  - `POST /api/llm`, `POST /api/search`
  - `GET /api/calendar/health`, `POST /api/calendar/events`
  - `POST /api/hermes/daily-briefing`
- n8n UI: `http://localhost:5678`

## UI Demo Video
https://github.com/user-attachments/assets/4318c31c-bd72-4c80-b956-c75428228906



## Quick Start
1. Copy env template:
   ```bash
   cp .env.local.example .env.local
   ```
2. Install deps:
   ```bash
   npm install
   ```
3. Run dev server:
   ```bash
   npm run dev
   ```

## Security Rules Implemented
- Client never calls external webhook directly.
- Chat input path is `Frontend -> /api/chat -> llm-proxy`; `/api/proxy` is legacy store/forward route.
- `llm-proxy` internal APIs require `x-internal-token` (except temporary bypass paths).
- `nanoclaw-agent` runs with `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges:true`, internal-only Docker network.
- `n8n` state persists via Docker volume: `n8n_data:/home/node/.n8n`.
- Local deployment is containerized with OrbStack + Docker Compose, with routing/server/proxy boundaries separated.

## Safe Public Push Guard
Before pushing to a public GitHub repository, enable the pre-push guard:

```bash
npm run git:hooks
```

Manual check:

```bash
npm run git:guard
```

The guard blocks pushes when tracked files include runtime/sensitive paths such as:
- `.env`, `.env.local`, `.env.*.local`
- `shared_data/*`
- `.next/*`, `node_modules/*`
- `*.db`, `*.sqlite*`

It also scans tracked files for obvious API key patterns.
