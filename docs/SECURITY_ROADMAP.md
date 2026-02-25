# Security Roadmap (Agent Workspace)

## Goal
- Keep current UX unchanged while strengthening backend and infra security.
- Support upcoming integrations (Telegram x3 agents, NotebookLM for Clio, agent-comms pipeline).

## Week 1 (In Progress) - Core Hardening
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

## Week 1.5 (Next Security Batch)
- remove `/api/hermes/daily-briefing` auth bypass and enforce `x-internal-token` from n8n HTTP node
- apply `read_only: true` + `tmpfs: /tmp` to `llm-proxy`
- apply `cap_drop: [ALL]`, `no-new-privileges:true` (and validate `read_only`) to `n8n`
- pin n8n image version (replace `latest`)
- set and persist `N8N_ENCRYPTION_KEY`

## Week 2 - Telegram Integration Hardening
- 3 bot tokens split by role:
  - Morpheus, Clio, Hermes
- allowlist-only chat IDs / user IDs
- command scope per bot (least privilege)
- inbound channel adapter with signed internal envelope:
  - `id, trace_id, from, to, type, ttl, payload_hash`

## Week 3 - Agent Comms Pipeline Security
- strict schema validation for all inter-agent messages
- HMAC signature verification
- idempotency key + replay protection
- message lifecycle enforcement:
  - `pending -> delivered -> processed -> archived`
  - invalid messages -> deadletter

## Week 4 - Clio NotebookLM Connector Security
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
