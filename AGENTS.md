# Nichola Programme Governance

This repository uses isolated Git worktrees for all specialist work. These rules apply to every agent and human working in this repository.

## Authority and responsibilities

| Profile | Authority and responsibility |
| --- | --- |
| `atlas_operations` | Programme coordination, integration, conflict resolution, readiness decisions, and promotion authority. Atlas owns `integration/nichola` and is the only profile permitted to consolidate specialist commits there or recommend promotion toward `main`. |
| `vulcan_pycraft` | Backend, build-system, automation, and repository-local gate implementation. Vulcan works only on its assigned task branch/worktree and hands commits to Atlas. |
| `frontend_forge` | UI, client-side behaviour, accessibility, styling, and frontend assets. Frontend Forge works only on its assigned task branch/worktree and hands commits to Atlas. |
| `montessori_scholar` | Education requirements, pedagogical accuracy, safeguarding-sensitive content requirements, and content review. Montessori Scholar receives a dedicated worktree only when tracked-content editing is explicitly requested; review-only work must not modify Git state. |
| `minerva_qa` | Independent consolidated QA and release-readiness evidence. Minerva validates the integrated result from its separate validation branch/worktree and must not author implementation fixes there. Findings return to the responsible implementer through Atlas. |

## Designated Git isolation

All worktrees are outside the project container and derive from the approved `main` baseline.

| Profile | Worktree | Branch | Lifecycle |
| --- | --- | --- | --- |
| `atlas_operations` | `E:/2_nichola-worktrees/atlas_operations` | `integration/nichola` | Permanent integration worktree |
| `vulcan_pycraft` | `E:/2_nichola-worktrees/vulcan_pycraft` | `task/nichola-vulcan-gates` | Permanent specialist worktree |
| `frontend_forge` | `E:/2_nichola-worktrees/frontend_forge` | `task/nichola-frontend-ui` | Permanent specialist worktree |
| `minerva_qa` | `E:/2_nichola-worktrees/minerva_qa` | `validation/nichola-minerva` | Disposable validation worktree |
| `montessori_scholar` | Not allocated | Not allocated | Create only for an explicitly requested tracked-content task |

The original checkout at `E:/2_nichola/site` is the protected `main` checkout. Do not edit, commit, merge, reset, clean, stash, or switch branches there. Do not work outside the designated worktree for a profile. Before every change, verify the current path, branch, clean status, and expected baseline; stop on any mismatch.

## Integration and promotion

1. Specialist branches begin from the approved `main` SHA or an Atlas-approved integration SHA.
2. Specialists commit only their assigned scope and provide commit SHAs plus verification evidence to Atlas.
3. Atlas reviews and integrates explicit commits into `integration/nichola`; Atlas does not silently absorb unrelated working-tree changes.
4. Minerva independently validates the consolidated integration result. Validation findings do not grant Minerva implementation authority.
5. Only Atlas may recommend or perform a local promotion from the verified integration history. Promotion to `main`, remote pushes, deployments, and production changes require separate explicit user authorization.
6. Never force-push, rewrite shared history, or bypass a failed safeguard.

## Profile and state isolation

- Hermes project registrations, active-project selections, sessions, `SOUL.md`, instructions, and memories are profile-local protected state. Git worktree creation does not authorize changing any of them.
- Do not copy, merge, link, repoint, or hand-edit another profile's Hermes state. Use supported Hermes CLI operations only when a separately authorized registration change is required, and back up the affected configuration database first.
- Do not share one Hermes home between profiles. Exchange work through Git commits and explicit review evidence, not shared session or memory files.
- Repository files must not contain credentials, tokens, production data, or copied `.env` values. Local secrets remain outside Git and outside worktree-to-worktree transfers.

## Gate boundary

This document defines governance only. Repository-local automated gates are intentionally deferred to Vulcan on `task/nichola-vulcan-gates`, for later Atlas review and integration. No gate is implied merely by this policy file.
