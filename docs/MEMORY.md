# MEMORY

> Living archive for recurring issues, fixes, and guardrails.
> Append new entries immediately after meaningful discoveries.

## Entry Template
- Date:
- Context:
- Symptom:
- Root cause:
- Fix:
- Guardrail:

---

## Lessons

### [2026-02-26] Internal token mismatch can create intermittent 401 between services
- Context: `nanoclaw-agent -> llm-proxy` internal calls.
- Symptom: occasional `401 Unauthorized`, fallback triggered.
- Root cause: `LLM_PROXY_INTERNAL_TOKEN` not aligned across containers.
- Fix: unify env injection path with `.env.local` and recreate impacted containers.
- Guardrail: keep a single token source and verify with `/api/telegram/health` and internal smoke calls after rotate/redeploy.

### [2026-02-26] Unknown agent fallback caused misrouting noise
- Context: autonomous queue ingestion.
- Symptom: unknown agent payload could be treated as default agent path.
- Root cause: permissive fallback behavior in updates route.
- Fix: remove fallback and deadletter unknown payloads.
- Guardrail: strict canonical ID map only (`ace/owl/dolphin`) with explicit alias normalization.

### [2026-02-26] n8n production webhook returns 404 when workflow is inactive
- Context: local n8n and webhook-based trend routes.
- Symptom: `POST /webhook/...` returns 404.
- Root cause: workflow inactive or wrong production URL path.
- Fix: publish/activate workflow and verify webhook endpoint.
- Guardrail: add startup checklist to verify `docker compose ps` and webhook health before integration tests.

### [2026-02-27] User feedback phrase "별론데" maps to UI direction issue
- Context: dashboard redesign iterations.
- Symptom: logic rework attempted when visual/interaction quality was the issue.
- Root cause: feedback semantics not encoded as project rule.
- Fix: encode phrase semantics in protocol/agent instructions.
- Guardrail: first classify complaint as logic vs UX before coding changes.
