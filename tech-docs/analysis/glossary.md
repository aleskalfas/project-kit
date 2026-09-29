---
TERM-clone:
  name: Clone
  status: active
  definition: A working copy of the repository on one machine, in which one person runs agent sessions; one person may run several.
  pkit:
    friction:
      anchors:
        record:
          - project-management:DEC-035
TERM-instance:
  name: Instance
  status: active
  definition: A clone that has set its instance id, so it can mark the work it owns and be told apart from the same person's other clones.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
          - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
        record:
          - project-management:DEC-035
          - project-management:DEC-043
          - ADR-041
TERM-integration-branch:
  name: Integration branch
  status: active
  definition: A long-running shared branch rooted at one owning issue, where that issue's Tasks land before the whole arc reaches the default branch in one pull request.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/git-conventions.yaml
        record:
          - project-management:DEC-013
TERM-intent-note:
  name: Intent note
  status: active
  definition: A structured comment on an in-flight issue saying what is done and what comes next, from which any later session resumes the work.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/audit.py
        record:
          - project-management:DEC-044
TERM-new-front:
  name: New front
  status: active
  definition: Work whose nearest Feature or Umbrella ancestor has nothing in flight and nothing landed, so starting it opens a new line of work rather than continuing one.
  pkit:
    friction:
      anchors:
        record:
          - project-management:DEC-004
TERM-release-scope:
  name: Release scope
  status: active
  definition: The work a release waits for — the release Milestone's children, and every open parent of work landed since the last release, each with its subtree, less what the operator deferred.
  pkit:
    friction:
      anchors:
        record:
          - project-management:DEC-016
          - PRJ-002
TERM-session:
  name: Session
  status: active
  definition: One running agent conversation in a clone, from its start until it ends or is killed; what it holds only in its context is lost when it dies.
  pkit:
    friction:
      anchors:
        record:
          - COR-039
TERM-stabilisation:
  name: Stabilisation
  status: active
  definition: The phase of a release Milestone in which work in flight continues, nothing new starts, and the default branch receives only release scope.
  pkit:
    friction:
      anchors:
        record:
          - project-management:DEC-016
          - project-management:DEC-014
          - ADR-019
---

# Glossary

The words of the domain and what each means. A term's id is stable; its name may change, and the names it replaces are kept.

## TERM-clone — Clone

All of one person's clones share that person's tracker account, so the tracker's assignee cannot tell them apart; an instance id does (TERM-instance). A git worktree made inside a clone for a helper session is part of that clone, not a clone of its own.

## TERM-instance — Instance

The id is a number the clone sets once for itself (`set-instance`) and keeps in a git-ignored file, so it outlives every session; a name may go with it (project-management DEC-045). An issue's owner is the pair of its assignee and an instance number, so one person's instance 2 is not another person's (DEC-035). Ownership is carried on the tracker — by an append-only comment log, the default, or by an `instance:N` label (DEC-043). A clone that sets no id takes no part.

## TERM-integration-branch — Integration branch

Opt-in: the owner designates it with an `Integration: integration/<slug>` line at the top of the owning issue's body, and every descendant inherits the line. A marked Task's pull request targets the integration branch, and the final pull request into the default branch closes the owning issue (project-management DEC-013). Like the default branch, it is never force-pushed.

## TERM-intent-note — Intent note

Intended design, not built yet (EPIC #943). `start-work --next` writes the first note when work starts, so the work has a direction from its first moment, and `pause-issue <N> --done … --next …` writes one whenever a session stops. Each note is stamped with its time and instance and is never merged with another; the latest one is the issue's direction.

A note records direction. It is not a handoff — the clone keeps the issue (DEC-026) — and not a block, since the work still has moves (COR-034). Its stamp follows the shared audit record shape (DEC-044).

## TERM-new-front — New front

A Task with no Feature or Umbrella ancestor is its own front; the hierarchy is DEC-004's. "Landed" is read on the branch the work lands on: the default branch, or the integration branch for work under an integration marker. Starting a new front is what a stabilisation holds back.

## TERM-release-scope — Release scope

Intended design, not built yet (EPIC #943). What has landed is derived from the default branch's history since the last release — its commits, their pull requests, the issues those close and the open parents of those issues — never from Milestone tagging, since an issue holds one Milestone. A release is ready when nothing in release scope is open. A parent the operator defers, with the reason stamped on it, leaves release scope for the release gate and the stabilisation guards alike.

## TERM-session — Session

A session is rooted in one repository (COR-039). Killing sessions is ordinary — the operator stops one, a crash takes them all — so nothing a clone needs in order to resume may live only in a session.

## TERM-stabilisation — Stabilisation

A feature freeze, not a code freeze. Intended design, not built yet (EPIC #943): `stabilize-milestone <N> --reason …` writes a `Stabilizing:` line into the Milestone's description, and `--lift`, or closing the Milestone, removes it. While it is on, starting a new front or landing out-of-scope work on the default branch is refused unless bypassed with an audited reason (project-management DEC-014), and a required CI status holds the same line, so an out-of-date clone or a raw merge cannot cross it (ADR-019). The command keeps the American spelling, `stabilize-milestone`.
