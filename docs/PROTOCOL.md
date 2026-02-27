# PROTOCOL

## Purpose
- Single source for execution protocol, quality bar, and project-specific behavior.
- Use this as the first reference before implementing non-trivial changes.

## Stack
- Frontend: Next.js (App Router), Tailwind CSS
- Backend proxy: FastAPI (`llm-proxy`)
- Workflow: n8n
- Agent runtime: `nanoclaw-agent` (Docker)
- Data plane: `shared_data/*` and SQLite utilities

## Core Execution Protocol (SPARC)
1. Spec
- Clarify exact scope, non-goals, and acceptance criteria.

2. Pseudocode
- Define input/output and core branching before coding.

3. Architecture
- Decide component boundaries, ownership, and data flow.

4. Refinement
- Check edge cases, failure modes, security and rollback path.

5. Completion
- Implement, verify, and update docs/memory.

## Human Rules
- `"이거 별론데"`: prioritize UX/UI revision.
- `"그냥 해줘"`: deliver execution quickly with minimal narrative.
- `"어떻게 생각해?"`: provide direct technical stance and trade-offs.

## Mode Switch
- Prototype mode (`프로토타입`)
  - Prioritize speed and functional slice.
  - Keep safeguards lightweight.
- Release-ready mode (`배포 준비`)
  - Prioritize security, tests, validation, and rollback safety.

## Verification Rules
- No assumption for unstable facts (env key names, API params, endpoint behavior).
- Validate with code/docs/runtime checks before finalizing.
- For high-impact logic, include explicit manual verification steps.

## Structured Prompting Convention
When describing complex tasks, prefer tag-based sections:

```xml
<spec>...</spec>
<constraints>...</constraints>
<acceptance>...</acceptance>
<risks>...</risks>
<next_action>...</next_action>
```

## Required Post-Work Updates
- Update `/Users/isanginn/Workspace/Agent_Workspace/docs/ACTION_PLAN.md` status.
- Append new lesson to `/Users/isanginn/Workspace/Agent_Workspace/docs/MEMORY.md` when a reusable insight appears.
