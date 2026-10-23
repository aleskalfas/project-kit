---
change: '#1890'
trigger: planned
reviewed-against:
  - title: "#1890's body"
    url: https://github.com/aleskalfas/project-kit/issues/1890
    version: '2026-10-22T23:27:48Z'
  - title: the core's code and records
    version: a5573cd00bbd251a10fe83a884ee3f1766c0b1b7
date: '2026-10-23'
by: 'builder agent for #1890'
confirmed-by: Aleš Kalfas
outcomes:
  ACT-developer: analysis-stale
  ACT-adopter: analysis-stale
  ACT-ai-agent: gap-found
  ACT-operator: gap-found
  ACT-merge-authoriser: analysis-stale
  TERM-migration: analysis-stale
  TERM-agent-definition: holds
  TERM-operational-rule: holds
  TERM-skill: holds
  UC-020: analysis-stale
  VIEW-the-system-and-its-methodology: gap-found
---

# 2026-10-23 — The concepts of agents and permissions, and the needs only a capability meets

## Outcomes

- **ACT-developer — analysis-stale.** Its 12 needs that only a capability meets moved to that capability's glossary head, with the 20 anchors on capability records behind them (DEC-001 point 2).
- **ACT-adopter — analysis-stale.** Its 3 needs that only software-analysis or living-docs meets moved to their heads, with 4 anchors. Two needs now say backbone configuration and the harness's settings.
- **ACT-ai-agent — gap-found.** Its needs used a grant and a workspace that no term defined, and called its agent definition a role definition. Terms now define both, and the need says agent definition.
- **ACT-operator — gap-found.** Its needs used the sandbox, which no term defined, and none stated putting the system's tool on the machine. TERM-sandbox defines it, and a need of its own states the install.
- **ACT-merge-authoriser — analysis-stale.** It anchored project-management DEC-028 for a note on another component's word. Both left, since the core's analysis describes the core alone.
- **TERM-migration — analysis-stale.** Its example and one anchor named project-management's migration. Both now name a backbone migration.
- **TERM-agent-definition — holds.** It anchored the Claude Code adapter's deploy script, and now anchors the core's contract with adapters. Its definition holds.
- **TERM-operational-rule — holds.** It anchored the Claude Code adapter's merge script, and now anchors the core's rules and its contract with adapters. Its definition holds.
- **TERM-skill — holds.** It anchored the Claude Code adapter's deploy script, and now anchors the skills area and the core's contract with adapters. Its definition holds.
- **UC-020 — analysis-stale.** Step 9, variants 1a and 9a and a guarantee quoted the Claude Code adapter's scripts. They now say what every adapter does, Claude Code only an example.
- **VIEW-the-system-and-its-methodology — gap-found.** No term defined scratchpad note, which the developer's needs use. The view now explains TERM-scratchpad-note.

## Gaps

- **ACT-ai-agent, ACT-operator:** their needs used a grant, the sandbox and the agent workspace, which no term defined. **Resolution:** nine terms define them, and VIEW-agents-and-permissions explains them.
- **ACT-operator:** no need stated putting the system's tool on the machine at a release. **Resolution:** the operator's need states it, and 050-adopt writes its use case.
- **VIEW-the-system-and-its-methodology:** scratchpad note, which the developer's needs use, had no term. **Resolution:** TERM-scratchpad-note defines it, and the view explains it.
