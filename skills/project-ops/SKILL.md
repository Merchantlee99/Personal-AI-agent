---
name: project-ops
description: Use this skill when working in this repository to enforce project-specific execution protocol (SPARC), living-document updates, mode-based behavior (prototype vs release-ready), and parallel team workflow hygiene.
---

# Project Ops Skill

## When to use
- Any non-trivial implementation or refactor in this repository.
- Any task that touches security, agent workflow, UI behavior, or multi-file changes.

## Mandatory workflow
1. Load and follow:
- `/Users/isanginn/Workspace/Agent_Workspace/AGENTS.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/PROTOCOL.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/ACTION_PLAN.md`
- `/Users/isanginn/Workspace/Agent_Workspace/docs/MEMORY.md`

2. Execute with SPARC
- Spec -> Pseudocode -> Architecture -> Refinement -> Completion.

3. Respect mode switch
- `프로토타입`: speed-first slice delivery.
- `배포 준비`: harden security/tests/edge-case coverage.

4. Update project memory
- If a reusable lesson appears, append one entry to `docs/MEMORY.md`.

5. Keep planning current
- Mark completed items in `docs/ACTION_PLAN.md`.

## Parallel workflow hygiene
- If file ownership/merge risk exists, use:
  - `/Users/isanginn/Workspace/Agent_Workspace/docs/TEAM_PARALLEL_WORKFLOW.md`
  - `/Users/isanginn/Workspace/Agent_Workspace/docs/WORK_LOCK_BOARD.md`

## Output checklist before final response
- Implementation completed or blocker clearly stated
- Validation steps/results included
- Action plan/memory updated when relevant
