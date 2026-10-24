---
id: ACT-operator
name: Operator
status: active
summary: "The person at the controls of a machine."
needs:
  - Let agents work on their own without a stream of confirmations, and know where their confinement does not hold.
  - Be asked before an agent changes a repository other than the session's own, so it never happens silently.
  - Find out why a command prompted me or was blocked, and what would stop it happening again.
  - Keep my per-machine choices (sandbox allowances, sockets, local settings) out of what the project commits.
  - Put the system's tool on my machine at a release, and update it.
  - Run each project at the version it pins, and be told plainly when the system falls back to my installed tool.
  - Get a fresh clone ready to work with one sync.
pkit:
  friction:
    anchors:
      record:
        - COR-028
        - COR-039
        - PRJ-004
        - ADR-063
      artefact:
        - CONTRIBUTING.md#running-checks
    revalidated:
      at: 2026-10-24T20:08:24Z
      outcome: unchanged
      unchanged-because: Running checks now says what the console-fence run leaves out of its write check, what it shows as placeholders and when its update writes. The section still calls whoever holds the repository's settings the operator, as the note says.
---

# ACT-operator — Operator

The person at the controls of a machine. The [role](../../glossary.md#term-role--role) is per machine and per clone.

- **Activities:**
  - start agent sessions
  - choose how much the agents may do without asking
  - [answer](../../glossary.md#term-answer--answer) what the [methodology](../../glossary.md#term-methodology--methodology) gates
- **Occasions:** every working day, in every clone.
- **Context:** the machine, its credentials and [sandbox](../../glossary.md#term-sandbox--sandbox), and the judgement the gates ask for.
- **Core:** the permission model, its [sandbox](../../glossary.md#term-sandbox--sandbox) and the cross-repository gate are this [role](../../glossary.md#term-role--role)'s controls.
- **Note:** the [role](../../glossary.md#term-role--role) is not whoever holds the repository's settings, since making merges wait on the checks is the adopter's. CONTRIBUTING.md also calls whoever holds those settings the operator.
