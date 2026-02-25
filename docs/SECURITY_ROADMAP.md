# Security Roadmap (Agent Workspace)

## Goal
- Keep current UX unchanged while strengthening backend and infra security.
- Support upcoming integrations (Telegram x3 agents, NotebookLM for Clio, agent-comms pipeline).

## Week 1 (Completed) - Core Hardening
- Scope
  - localhost-only published ports
  - internal API token for llm-proxy
  - basic request hardening (rate limit + body size limit)
  - remove internal exception leakage from API responses
- Status
  - Completed:
    - `llm-proxy` security middleware added (`x-internal-token`, rate limit, max body bytes)
    - Next.js `/api/chat` now forwards internal token server-side only
    - `agent/llm_client.py` now forwards internal token for container-to-proxy calls
    - `docker-compose.yml` host port bindings changed to loopback only:
      - `127.0.0.1:8000:8000`
      - `127.0.0.1:5678:5678`
    - `nanoclaw-agent` token injection path aligned to `.env.local` (`env_file`) and internal 401 mismatch removed
    - generic error responses applied to llm/search/agent routers
  - Deferred (manual):
    - key rotation (Google/OAI/Gemini/Anthropic/Tavily)
    - periodic key rotation policy + automation

## Week 1.5 (Completed) - Container Hardening Batch
- `/api/hermes/daily-briefing` auth bypass removed; n8n HTTP node injects `x-internal-token`
- `llm-proxy` hardened with `read_only: true` + `tmpfs: /tmp`
- `n8n` hardened with `cap_drop: [ALL]`, `no-new-privileges:true`, `read_only: true`, `tmpfs` runtime paths
- n8n image pinned from `latest` to `n8nio/n8n:2.9.2`
- `N8N_ENCRYPTION_KEY` persisted for credential at-rest stability
- internal secret rotation script added: `npm run security:rotate-internal`

## Week 2 (Current) - Operational Security Automation
- add scheduled internal secret rotation runbook (weekly cadence)
- automate post-rotation smoke tests:
  - `docker compose ps`
  - `/api/agents` unauthorized/authorized checks
  - n8n -> llm-proxy internal call check
- improve secret backup hygiene:
  - `.env.local.bak.*` ignored by git (applied)
  - optional retention cleanup script (pending)

## Week 3 - Telegram Integration Hardening
- 3 bot tokens split by role:
  - Morpheus, Clio, Hermes
- allowlist-only chat IDs / user IDs
- command scope per bot (least privilege)
- inbound channel adapter with signed internal envelope:
  - `id, trace_id, from, to, type, ttl, payload_hash`

## Week 4 - Agent Comms Pipeline Security
- strict schema validation for all inter-agent messages
- HMAC signature verification
- idempotency key + replay protection
- message lifecycle enforcement:
  - `pending -> delivered -> processed -> archived`
  - invalid messages -> deadletter

## Week 5 - Clio NotebookLM Connector Security
- export-only path for NotebookLM (`/exports/notebooklm`)
- PII masking / content sanitizer before sync
- source tagging + audit trail
- retry queue and failure quarantine

## Runtime Security Checklist (Always)
- never commit `.env.local`
- rotate leaked keys immediately
- keep Google Calendar scope at `calendar.readonly` only
- avoid passing 3rd-party keys in webhook body when credential store is available
- validate all externally sourced content before memory/file writes
- keep internal token identical across Next.js, nanoclaw-agent, llm-proxy (`LLM_PROXY_INTERNAL_TOKEN`)
- use `npm run security:rotate-internal` after suspected exposure or at planned intervals
