# Project Agent Instructions

## Always-On Rules
1. Treat this repo as a living system.
- After solving a hard bug, discovering a reusable pattern, or correcting repeated mistakes, append it to `/Users/isanginn/Workspace/Agent_Workspace/docs/MEMORY.md` immediately.

2. Interpret feedback in project-specific way.
- `"이거 별론데"` means UX/UI dissatisfaction first, not logic failure.
- `"그냥 해줘"` means execute with minimal explanation.
- `"어떻게 생각해?"` means provide direct opinion, not passive agreement.

3. Mode-based execution.
- `프로토타입`: optimize for speed and iteration; minimal guardrails.
- `배포 준비`: enforce security hardening, edge cases, and validation checks.

4. Edge-case first.
- Proactively propose failure handling before or with implementation.

5. Do not guess unstable details.
- If API params, env keys, or behavior are uncertain, verify docs/code first.

## Required Working Files
- Protocol: `/Users/isanginn/Workspace/Agent_Workspace/docs/PROTOCOL.md`
- Action plan: `/Users/isanginn/Workspace/Agent_Workspace/docs/ACTION_PLAN.md`
- Memory archive: `/Users/isanginn/Workspace/Agent_Workspace/docs/MEMORY.md`

## Working Contract
- Follow SPARC loop from `PROTOCOL.md` for non-trivial changes.
- Keep `ACTION_PLAN.md` in sync with actual progress.
- Record learnings in `MEMORY.md` to prevent repeated mistakes.
