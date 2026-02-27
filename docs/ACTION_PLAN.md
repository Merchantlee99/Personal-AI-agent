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

### D. Security/Ops Follow-up
- [ ] Run internal secret rotation and smoke test
- [ ] Confirm n8n webhook auth headers and token gate behavior
- [ ] Audit `.env.local.example` completeness vs runtime requirements

## Evidence Log
- 2026-02-27: governance docs + lock board + PR template added.
- 2026-02-27: branch-protection script and setup guide added (`scripts/security/apply-branch-protection.sh`, `docs/BRANCH_PROTECTION_SETUP.md`).
