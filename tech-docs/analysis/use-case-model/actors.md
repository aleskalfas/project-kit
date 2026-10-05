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
ACT-developer:
  name: Developer
  status: active
  needs:
    - Record my decisions beside the methodology's, and build only on accepted ones.
    - Author and extend my project's rule sets without editing the ones that ship with the methodology.
    - Think a question too big for a decision through in a scratchpad note, and retire the note once it has produced something.
    - Say what each of my documents rests on, so a change there reaches me.
    - Answer what my change made stale, judging an agent's proposed answer word for word, or running its commands myself when it cannot ask me.
    - Know before I push that my change passes the checks my project gates its merges on.
    - Have a substantive draft challenged before I adopt it, and my diff checked against the methodology's conventions before I commit it.
    - Land my change on the default branch as one squash commit with a conventional title, through a pull request or directly when I work alone.
    - Turn recurring work into my project's own skill or agent, designing its dialogue as a storyboard first.
  pkit:
    friction:
      anchors:
        record:
          - COR-009
ACT-merge-authoriser:
  name: Merge authoriser
  status: active
  needs:
    - See every answer the change wrote on its artefacts, word for word from the check's own list, before I authorise its merge.
    - Have my authorisation cover only what I was shown, and be asked again for anything written or reworded after.
    - Be shown the same list before an agent commits straight to the default branch for me.
    - Have a decision record or rule an agent drafted become binding only through my own review of it.
  pkit:
    friction:
      anchors:
        record:
          - COR-050
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

## ACT-developer — Developer

The person who builds: decisions, rules, notes, code and its documentation, one change at a time. They come for every unit of work, and again when some work recurs often enough to deserve tooling of its own. They bring the change and direct agents to make it. Core: every change passes the acceptance gate and the friction check, whatever tracks the work, and lands as COR-009 sets out. That the backbone itself lands pull requests is provisional (ADR-061 point 3, raised as #1222). A work tracker's view of this role (project-management's "Implementer") comes with that capability.

## ACT-merge-authoriser — Merge authoriser

The person who authorises a change's merge into the default branch. Where work is committed there directly, it is the person the agent works for, before the commit. Always a person: the authorisation turns the answers an agent wrote into a person's decision, and the same person's review turns a record or rule an agent drafted into a binding one. They come at the end of each piece of work, and whenever a drafted record or rule waits for acceptance. They bring the authority to land the change. The name is not "approver", because project-management uses that word for a reviewer agent (DEC-028). Core: COR-050 point 3 defines this role, for a merge and a direct commit alike, and the acceptance gate gives it acceptance, so it exists with no work tracker installed.

## ACT-operator — Operator

The person at the controls of a machine. They start agent sessions, choose how much the agents may do without asking, and answer what the methodology gates. They come every working day, in every clone, bringing the machine, its credentials and sandbox, and the judgement the gates ask for. The role is per machine and per clone; it is not whoever holds the repository's settings, whom CONTRIBUTING.md also calls the operator (:65, :67), since making merges wait on the checks is the adopter's. Core: the permission model, its sandbox and the cross-repository gate are this role's controls.
