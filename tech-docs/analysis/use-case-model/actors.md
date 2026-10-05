---
ACT-adopter:
  name: Adopter
  status: active
  needs:
    - Install the methodology into my project with one command, committed for the team or kept out of the shared repository, and see how it is wired.
    - Upgrade it like a dependency, at a version pinned for the whole project, with its migrations run for me and my own files left alone.
    - Add or remove a capability, one shared from another of my repositories included, and be told of a name collision instead of being overwritten.
    - Choose which installed capability provides a role.
    - Declare my project's settings once (name, default branch, documentation roots, friction mode, anchored places, declared surface, excluded paths) and have them validated.
    - Add my own operational rules, settings, permission grants and agent paths beside the methodology's, never editing its files.
    - Make my merges wait on pkit's checks, knowing they bind only once my CI requires them.
    - Re-pin an inherited rule set to its new major version once I have reviewed it.
    - Report a problem with pkit, and follow what happens to it.
  pkit:
    friction:
      anchors:
        record:
          - COR-001
          - COR-010
ACT-operator:
  name: Operator
  status: active
  needs:
    - Let agents work on their own without a stream of confirmations, and know where their confinement does not hold.
    - Be asked before an agent changes a repository other than the session's own, so it never happens silently.
    - Find out why a command prompted me or was blocked, and what would stop it happening again.
    - Keep my per-machine choices (sandbox allowances, sockets, local settings) out of what the project commits.
    - Run each project at the version it pins, and be told plainly when it falls back to my installed tool.
    - Get a fresh clone ready to work with one sync.
  pkit:
    friction:
      anchors:
        record:
          - COR-028
          - COR-039
---

# Actors

Who uses the system, and what each needs from it. Each actor's id is stable; its name may change.

## ACT-adopter — Adopter

The person who adopts the methodology for a project and keeps its setup: what is installed, at which version, which of their own additions sit beside it, and which checks the project's merges wait on. They come at setup, at each upgrade, and when the project needs a discipline. They bring their project, its existing `CLAUDE.md` and settings, its repository settings, and the rules and grants they add. Core: the split between methodology-owned and project-owned files, and the install and upgrade lifecycle, exist for this role. Installing a capability is itself a core act.

## ACT-operator — Operator

The person at the controls of a machine. They start agent sessions, choose how much the agents may do without asking, and answer what the methodology gates. They come every working day, in every clone, bringing the machine, its credentials and sandbox, and the judgement the gates ask for. The role is per machine and per clone; it is not whoever holds the repository's settings, whom CONTRIBUTING.md also calls the operator (:65, :67), since making merges wait on the checks is the adopter's. Core: the permission model, its sandbox and the cross-repository gate are this role's controls.
