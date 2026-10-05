---
ACT-adopter:
  name: Adopter
  status: active
  needs:
    - Install the methodology with one command, committed for the team or kept out of the shared repository, and see its wiring into my project.
    - Upgrade it like a dependency, at a version pinned for the whole project, with its migrations run for me and my own files left alone.
    - Add or remove a capability, one shared from another of my repositories included, and be told of a name collision instead of being overwritten.
    - Choose which installed capability provides a role.
    - Declare my project's settings once (name, default branch, documentation roots, friction mode, anchored places, declared surface, excluded paths) and have them validated.
    - Add my own operational rules, settings, permission grants and agent paths beside the methodology's, never editing its files.
    - Make my merges wait on the system's checks, knowing they bind only once my CI requires them.
    - Re-pin an inherited rule set to its new major version once I have reviewed it.
    - Report a problem with the system, and follow what happens to it.
  pkit:
    friction:
      anchors:
        record:
          - COR-001
          - COR-010
ACT-ai-agent:
  name: AI agent
  status: active
  needs:
    - Start every session with the project's rules and conventions loaded.
    - Find my role definition deployed, with the project's own paths filled in and my own permission grants applied.
    - Create a methodology artefact through its paired skill and stamp, so its id, place and front matter come out right.
    - Keep my intermediate files in a workspace that no commit carries and no confirmation guards.
    - Get a delegated agent's result back whole, never cut short while still reading as complete.
  pkit:
    friction:
      anchors:
        record:
          - COR-013
ACT-ci-pipeline:
  name: CI pipeline
  status: active
  needs:
    - Run every check with no terminal and no person to answer, and gate the merge on its exit status.
    - Compare a change with its real base, the pull request's target or the queued merge's base, named once for all the checks.
    - Run the checks offline once the checkout is provisioned.
    - Get findings in a machine-readable form, to publish them where people look.
    - Be told when a shallow clone lacks history a check needs, rather than get a misleading result.
    - Have the whole-repository check report its findings without failing, so the check can run after merges and on a schedule.
    - Tag a release once it lands, from the version it declares, with no one there to confirm the push.
  pkit:
    friction:
      anchors:
        record:
          - COR-054
          - COR-050
ACT-component-author:
  name: Component author
  status: active
  needs:
    - Package a recurring discipline as a capability from the methodology's primitives, without forking the methodology.
    - Keep a capability I wrote in my own repository, where sync never overwrites it and uninstall never deletes it.
    - Give my capability roles, data points and processes that other components can connect to without naming it, and have the engine run and check them.
    - Release my component on its own version, and say which backbone versions it works with.
    - Carry the projects that installed my component across a breaking change of it.
    - Know my capability is ready to share before other repositories pull it.
    - Adapt the methodology to another harness, and say how far that harness meets each requirement and what of the permission model the harness cannot enforce.
  pkit:
    friction:
      anchors:
        record:
          - COR-031
          - COR-041
          - COR-047
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
    - Have a substantive draft challenged before I adopt it, and have my diff checked against the methodology's conventions before I commit it.
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
ACT-methodology-maintainer:
  name: Methodology maintainer
  status: active
  needs:
    - Develop the methodology in its source repository, where no sync copies over my work, and run what I ship there before any adopter does.
    - Keep each core record true for any project that adopts it.
    - Release the backbone so adopters can upgrade and pin to it, and know what each change since the last release means for them.
    - Never ship a backbone change that breaks installed projects without the migration that carries them across.
    - Receive adopters' reports with their versions attached, and link each one to the issue that fixes it.
  pkit:
    friction:
      anchors:
        record:
          - ADR-059
          - PRJ-002
ACT-operator:
  name: Operator
  status: active
  needs:
    - Let agents work on their own without a stream of confirmations, and know where their confinement does not hold.
    - Be asked before an agent changes a repository other than the session's own, so it never happens silently.
    - Find out why a command prompted me or was blocked, and what would stop it happening again.
    - Keep my per-machine choices (sandbox allowances, sockets, local settings) out of what the project commits.
    - Run each project at the version it pins, and be told plainly when pkit falls back to my installed tool.
    - Get a fresh clone ready to work with one sync.
  pkit:
    friction:
      anchors:
        record:
          - COR-028
          - COR-039
---

# Actors

Who uses the system, and what each needs from it. Each actor's id is stable. Its name may change.

## ACT-adopter — Adopter

The person who adopts the methodology for a project and keeps its setup.

- **The setup:**
  - what is installed, at which version
  - which of their own additions sit beside it
  - which checks the project's merges wait on
- **Comes:**
  - at setup
  - at each upgrade
  - when the project needs a discipline
- **Brings:** their project, its existing `CLAUDE.md` and settings, its repository settings, and the rules and grants they add.
- **Core:** the split between methodology-owned and project-owned files, and the install and upgrade lifecycle, exist for this role. Installing a capability is itself a core act.

## ACT-ai-agent — AI agent

An AI agent working under the methodology, acting on the system from outside.

- **Can be:** the main session acting for a person, or an agent that session dispatches for one role (in the core: critic, architect, methodology-reviewer, convention-compliance-reviewer, process-author).
- **Comes:** whenever work is done. It keeps no memory between sessions beyond what the repository holds.
- **In the model:** when it does a role's work, it appears as a step in that role's use cases.
- **Core:** the agent architecture, the rules loaded into every session and the adapter's deployment make this actor exist. The core's reviewer agents advise, and no core gate counts their verdict.

## ACT-ci-pipeline — CI pipeline

A project's continuous integration, acting on the system from outside. It is an actor because it starts work on its own trigger with no person in the session.

- **Comes:** on every pull request, queued merge and push to the default branch, and on a schedule.
- **Brings:** a clean checkout, a base to compare with, and no person to answer a prompt.
- **In the model:** its needs are what the system must give an unattended runner. The goals its runs serve belong to people:
  - The change check serves the developer and the merge authoriser.
  - The whole-repository report serves the developer (a change to what a document rests on reaches them).
  - A release tag serves the methodology maintainer.
- **Core:** the backbone ships no workflow. It ships only checks made to run unattended, and one base a pipeline names for all of them (COR-054 point 3). The checks bind once the project makes them a required status (COR-050 point 12).
- **Note:** project-kit's workflows are one wiring of these. Two of their steps are project-kit's alone: the changeset guard and the release tag (PRJ-002 and release README:22-29).

## ACT-component-author — Component author

Someone who extends the methodology with a component (a capability or an adapter) rather than only using it.

- **Can be:**
  - an adopter growing a discipline in their own repository
  - an organisation that keeps private methodology in one repository for its others
  - whoever adapts the methodology to a new harness
- **Comes:**
  - when a pattern recurs often enough to package
  - at each release of their component
  - when a new harness arrives
- **Brings:** the component's decisions, schemas, skills, agents and process definitions. They own its compatibility claim.
- **Core:** the capability pattern, its origins, connection points, the process engine and the harness requirements are the extension points this role uses. They exist before any capability is installed.
- **Note:** in project-kit's source repository the methodology maintainer plays this part for the capabilities and the adapter project-kit ships.

## ACT-developer — Developer

The person who builds: decisions, rules, notes, code and its documentation, one change at a time.

- **Comes:** for every change, and again when some work recurs often enough to deserve tooling of its own.
- **Brings:** the change. They direct agents to make it.
- **Core:** whatever tracks the work, every change passes the acceptance gate and the friction check, and lands as COR-009 sets out. That the backbone itself lands pull requests is provisional (ADR-061 point 3, raised as #1222).
- **Note:** a work tracker's view of this role (project-management's "Implementer") comes with that capability.

## ACT-merge-authoriser — Merge authoriser

The person who authorises a change's merge into the default branch. Where work is committed there directly, it is the person the agent works for, before the commit.

- **Always a person:** the authorisation turns the answers an agent wrote into a person's decision. The same person's review turns a record or rule an agent drafted into a binding one.
- **Comes:** at the end of each change, and whenever a drafted record or rule waits for acceptance.
- **Brings:** the authority to land the change.
- **Core:** two core rules make this role, and neither needs a work tracker. COR-050 point 3 covers seeing a change's answers before a merge or direct commit, and the acceptance gate covers accepting a record or rule.
- **Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028).

## ACT-methodology-maintainer — Methodology maintainer

Whoever maintains a distribution of the methodology.

- **Can be:** project-kit's maintainers, or a fork's.
- **Does:** work in the distribution's source repository, on the core records, the backbone and the releases adopters upgrade to.
- **Comes:** for every change to the methodology and every backbone release.
- **Brings:** the methodology's disciplines (CONTRIBUTING.md). They are the first adopter of what they ship.
- **Core:** the source repository, its release policy and its report inbox exist for this role.

## ACT-operator — Operator

The person at the controls of a machine. The role is per machine and per clone.

- **Does:**
  - start agent sessions
  - choose how much the agents may do without asking
  - answer what the methodology gates
- **Comes:** every working day, in every clone.
- **Brings:** the machine, its credentials and sandbox, and the judgement the gates ask for.
- **Core:** the permission model, its sandbox and the cross-repository gate are this role's controls.
- **Note:** the role is not whoever holds the repository's settings, since making merges wait on the checks is the adopter's. CONTRIBUTING.md also calls whoever holds those settings the operator (:65, :67).
