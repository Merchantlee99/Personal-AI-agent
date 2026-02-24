# Air-Gapped Agent Dashboard Scaffold

## Documentation
- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [Security Model](docs/SECURITY_MODEL.md)
- [n8n Local Setup](docs/N8N_LOCAL_SETUP.md)
- [n8n Local Owner Account (Dev)](docs/N8N_LOCAL_ACCOUNT.md)

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
- Local n8n routing standardized:
  - internal: `N8N_WEBHOOK_URL_INTERNAL=http://n8n:5678/webhook/hermes-trend`
  - host: `N8N_WEBHOOK_URL_HOST=http://localhost:5678/webhook/hermes-trend`
- Agent async comms bus added under `shared_data/agent_comms`:
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
- All user input must pass through `/api/proxy`.
- API route writes payloads into SQLite and can optionally forward to n8n.
- `nanoclaw-agent` runs with `read_only: true`, `cap_drop: [ALL]`, internal-only Docker network.
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
