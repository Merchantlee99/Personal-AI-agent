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

### [2026-02-27] Parallel commit+push can race when executed simultaneously
- Context: automation commit and push triggered in parallel calls.
- Symptom: push says "Everything up-to-date" while local branch remains ahead.
- Root cause: push ran before commit hash was created.
- Fix: run commit first, then push sequentially.
- Guardrail: avoid parallelizing dependent git operations (`commit -> push` must be ordered).

### [2026-02-27] Chat panel interactions need reducer + priority guard to avoid UX race conditions
- Context: conversation panel had overlapping triggers (outside click, resize, auto-expand, keyboard toggle).
- Symptom: panel could close/open unexpectedly when multiple interactions happened close together.
- Root cause: distributed boolean flags and direct setters without explicit transition/priority model.
- Fix: centralize panel phase in reducer (`closed/open/resizing`) and apply action priority guard (`resizing > close/open > toggle`).
- Guardrail: route panel state changes through reducer actions only; never directly mutate independent open/resize booleans.

### [2026-02-28] Multi-agent voice UX works best with shared politeness + role-specific sentence contracts
- Context: user wanted all agents to use honorific Korean while still feeling distinct.
- Symptom: when only role labels differ, responses sound similar and persona identity blurs.
- Root cause: prompts lacked explicit sentence-opening/ending constraints per agent.
- Fix: add `voice_contract` blocks to each persona with shared 존댓말 baseline and role-specific phrasing patterns.
- Guardrail: keep one shared speech baseline (존댓말) and differentiate by "opening line + structure + closing action", not by random style tokens.

### [2026-02-28] Usage panel credibility requires event-level logging, not static snapshot constants
- Context: right panel API budget needed to represent actual runtime behavior.
- Symptom: static constants looked operational but could not be validated against real traffic.
- Root cause: no persisted usage events and no summary API between proxy and dashboard.
- Fix: capture provider usage per call (success/error), persist to SQLite, and poll `/api/usage/summary` from dashboard.
- Guardrail: keep `estimated` and `settled` costs as separate fields; never present estimated numbers as settled billing.
