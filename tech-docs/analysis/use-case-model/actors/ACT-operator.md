---
id: ACT-operator
name: Operator
status: active
needs:
  - Let agents work on their own without a stream of confirmations, and know where their confinement does not hold.
  - Be asked before an agent changes a repository other than the session's own, so it never happens silently.
  - Find out why a command prompted me or was blocked, and what would stop it happening again.
  - Keep my per-machine choices (sandbox allowances, sockets, local settings) out of what the project commits.
  - Run each project at the version it pins, and be told plainly when the system falls back to my installed tool.
  - Get a fresh clone ready to work with one sync.
pkit:
  friction:
    anchors:
      record:
        - COR-028
        - COR-039
    revalidated:
      at: 2026-10-14T09:21:19Z
      outcome: updated
---

# ACT-operator — Operator

The person at the controls of a machine. The role is per machine and per clone.

- **Does:**
  - start agent sessions
  - choose how much the agents may do without asking
  - answer what the methodology gates
- **Comes:** every working day, in every clone.
- **Brings:** the machine, its credentials and sandbox, and the judgement the gates ask for.
- **Core:** the permission model, its sandbox and the cross-repository gate are this role's controls.
- **Note:** the role is not whoever holds the repository's settings, since making merges wait on the checks is the adopter's. CONTRIBUTING.md also calls whoever holds those settings the operator.
