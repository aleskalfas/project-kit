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
      path:
        - CONTRIBUTING.md
      record:
        - COR-028
        - COR-039
    revalidated:
      at: 2026-10-14T18:58:47Z
      outcome: unchanged
      unchanged-because: COR-028 and COR-039 now write their points as headings carrying the same numbers, word for word. COR-028's closing sentence, that the model is authoritative, and COR-039's paragraph on where its realization is recorded move into each record's opening, unchanged. The operator's needs, to know where confinement does not hold and to be asked before an agent changes another repository, rest on the same text, so the actor holds.
---

# ACT-operator — Operator

The person at the controls of a machine. The role is per machine and per clone.

- **Activities:**
  - start agent sessions
  - choose how much the agents may do without asking
  - answer what the methodology gates
- **Occasions:** every working day, in every clone.
- **Context:** the machine, its credentials and sandbox, and the judgement the gates ask for.
- **Core:** the permission model, its sandbox and the cross-repository gate are this role's controls.
- **Note:** the role is not whoever holds the repository's settings, since making merges wait on the checks is the adopter's. CONTRIBUTING.md also calls whoever holds those settings the operator.
