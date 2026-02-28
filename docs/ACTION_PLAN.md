# ACTION_PLAN

## Usage
- Check boxes as each step is completed.
- Keep this file aligned with actual implementation status.
- For each completed item, include evidence path (log/screenshot/PR).

## Current Track: Parallel Development Operations

### A. Governance Baseline
- [x] Add team role model document (`TEAM_PARALLEL_WORKFLOW.md`)
- [x] Add work lock board (`WORK_LOCK_BOARD.md`)
- [x] Add PR template and CODEOWNERS
- [x] Add branch-protection automation script + setup guide
- [ ] Apply branch protection rules in GitHub repository settings
- [x] Add thread handoff prompt pack (`THREAD_HANDOFF_PROMPTS.md`)
- [x] Add thread finish + release merge automation scripts
- [x] Add GitHub Actions full-auto path (auto PR + ordered auto merge)

### B. Development Protocolization
- [x] Add always-on repo instructions (`AGENTS.md`)
- [x] Add execution protocol (`PROTOCOL.md`)
- [x] Add memory archive (`MEMORY.md`)
- [x] Add reusable operation skill (`skills/project-ops/SKILL.md`)

### C. Near-Term Stabilization
- [ ] Finalize chat panel split cleanup (if pending)
- [ ] Verify no UI regression after right-panel widget integration
- [ ] Re-check `/api/chat` and `/api/agent-updates` end-to-end
- [ ] Re-check telegram bridge health in all three bots
- [x] Add UI/UX manual QA checklist and metric debug guide (`docs/UI_UX_QA_CHECKLIST.md`, `docs/UX_METRICS_DEBUG.md`)

### E. UI/UX Hardening Backlog (2026-02-27)
#### P0
- [x] Define chat panel transition map and explicit state ownership (open/close/resize/auto-expand).
- [x] Enforce panel interaction priority rules (`resizing > outside-dismiss > auto-expand`).
- [x] Preserve agent-switch continuity (per-agent draft + scroll context).
- [x] Improve error UX with immediate recovery actions (retry/copy/error context).

#### P1
- [x] Introduce slot-based layout wrappers for Left/Center/Right/Chat extension safety.
- [x] Unify motion behavior with tokens and `prefers-reduced-motion`.
- [x] Improve accessibility (roles, live region, keyboard flow and discoverability).
- [x] Add UX telemetry hooks (`send success ms`, `outside close count`, `switch re-input`).

### D. Security/Ops Follow-up
- [ ] Run internal secret rotation and smoke test
- [ ] Confirm n8n webhook auth headers and token gate behavior
- [ ] Audit `.env.local.example` completeness vs runtime requirements

### F. Agent Persona Voice UX (2026-02-28)
- [x] Add polite-speech voice contract to Morpheus/Clio/Hermes personas.
- [x] Differentiate opening sentence and closing action style by agent role.
- [x] Apply Hermes-specific "~어요/~요" ending rule to make channel voice distinct.

### G. API Usage Observability UX (2026-02-28)
- [x] Instrument proxy provider calls with token usage capture (success/error).
- [x] Persist daily usage events to SQLite and expose `/api/usage/summary`.
- [x] Replace right-panel API budget mock with live usage polling (`estimated` + `settled` split).

## Evidence Log
- 2026-02-27: governance docs + lock board + PR template added.
- 2026-02-27: branch-protection script and setup guide added (`scripts/security/apply-branch-protection.sh`, `docs/BRANCH_PROTECTION_SETUP.md`).
- 2026-02-27: active lock allocation + thread handoff prompt pack added for 4-thread parallel run.
- 2026-02-27: automation scripts added (`scripts/threads/finish-thread.sh`, `scripts/release-captain/merge-in-order.sh`).
- 2026-02-27: full-auto workflows added (`auto-pr-codex.yml`, `release-captain-auto-merge.yml`).
- 2026-02-27: started UI/UX hardening backlog P0→P1 implementation (`src/components/chat-dashboard*`, `src/app/globals.css`).
- 2026-02-27: completed UI/UX hardening backlog P0→P1 (`chat-panel-state.ts`, `dashboard-slot.tsx`, `ux-metrics.ts`, `chat-dashboard.tsx`, `globals.css`).
- 2026-02-28: added QA runbook + metrics debug docs for next verification cycle.
- 2026-02-28: updated agent persona voice contracts for Korean polite UX differentiation (`agent/personas/ace.md`, `agent/personas/owl.md`, `agent/personas/dolphin.md`).
- 2026-02-28: integrated live API usage summary pipeline (`proxy/app/utils/usage_store.py`, `proxy/app/routers/usage.py`, `src/app/api/usage/summary/route.ts`, `src/components/chat-dashboard/use-usage-summary.ts`).
