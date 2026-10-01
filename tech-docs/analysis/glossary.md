---
TERM-clone:
  name: Clone
  status: active
  definition: A working copy of the repository on one machine, in which one person runs agent sessions; one person may run several.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/instance_identity.py
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
      revalidated:
        at: 2026-09-30T23:02:14Z
        outcome: unchanged
        unchanged-because: "#840's lint and format pass reshapes the anchored code without changing what it does, so this page still describes it as it is"
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
      revalidated:
        at: 2026-10-01T15:12:48Z
        outcome: unchanged
        unchanged-because: DEC-013 gains that its merge mechanic is the backbone's, which every command that lands a PR calls; integration branches, which this term defines, are untouched
TERM-intent-note:
  name: Intent note
  status: active
  definition: A structured comment on an in-flight issue saying what is done and what comes next, from which any later session resumes the work.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/audit.py
          - .pkit/capabilities/project-management/scripts/start-work.py
        record:
          - project-management:DEC-044
      revalidated:
        at: 2026-10-01T20:49:54Z
        outcome: unchanged
        unchanged-because: "after #1242 was narrowed, start-work reads the issue's state from labels and milestone as before, through a function shared with review-work, and refuses nothing new; the first intent note start-work --next will write is untouched and still unbuilt, so the term holds"
TERM-new-front:
  name: New front
  status: active
  definition: Work whose nearest Feature or Umbrella ancestor has nothing in flight and nothing landed, so starting it opens a new line of work rather than continuing one.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/start-work.py
        record:
          - project-management:DEC-004
      revalidated:
        at: 2026-10-01T20:49:56Z
        outcome: unchanged
        unchanged-because: "#1242 now only shares start-work's early check, read from labels and milestone as before with no engine read and no new refusal, with review-work; it adds no start guard over fronts, which stays intended design, so the term holds"
TERM-release-scope:
  name: Release scope
  status: active
  definition: The work a release waits for — the release Milestone's children, and every open parent of work landed since the last release, each with its subtree, less what the operator deferred.
  pkit:
    friction:
      anchors:
        path:
          - .github/workflows/release-pr.yml
        record:
          - project-management:DEC-016
          - PRJ-002
      revalidated:
        at: 2026-09-30T05:35:15Z
        outcome: unchanged
        unchanged-because: PRJ-002 D4 now also lets a floor ride on a floor-only release of its component, holds an explicit floor to a release the tree records, and says no escape hatch waives the guard's tie; which work a release waits for is untouched by how version floors are declared and checked
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
  definition: The phase of a release Milestone in which work in flight continues, nothing new starts outside release scope, and the default branch receives only release scope.
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/start-work.py
          - .pkit/capabilities/project-management/scripts/done-work.py
          - .pkit/capabilities/project-management/scripts/merge-pr.py
        record:
          - project-management:DEC-016
          - project-management:DEC-014
          - ADR-019
      revalidated:
        at: 2026-10-01T22:17:09Z
        outcome: unchanged
        unchanged-because: every title rule the schema declares now runs, and DEC-011 states them; what this page says of titles and filing still holds
---

# Glossary

The words of the domain and what each means. A term's id is stable; its name may change, and the names it replaces are kept.

## TERM-clone — Clone

All of one person's clones share that person's tracker account, so the tracker's assignee cannot tell them apart; an instance id does (TERM-instance).

Intended design, not built yet — pending gap J (#1140, under EPIC #508): a git worktree made inside a clone for a helper session is part of that clone, not a clone of its own. Today a worktree does not see its clone's instance id, which is read from a git-ignored file under the working tree's own root (`_lib/instance_identity.py`), so a session there acts as a clone that never set one.

## TERM-instance — Instance

The id is a number the clone sets once for itself (`set-instance`) and keeps in a git-ignored file, so it outlives every session; a name may go with it (project-management DEC-045). An issue's owner is the pair of its assignee and an instance number, so one person's instance 2 is not another person's (DEC-035). Ownership is carried on the tracker — by an append-only comment log, the default, or by an `instance:N` label (DEC-043). A clone that sets no id takes no part.

## TERM-integration-branch — Integration branch

Opt-in: the owner designates it with an `Integration: integration/<slug>` line at the top of the owning issue's body, and every descendant inherits the line. A marked Task's pull request targets the integration branch, and the final pull request into the default branch closes the owning issue (project-management DEC-013). Like the default branch, it is never force-pushed.

## TERM-intent-note — Intent note

Intended design, not built yet (EPIC #943). `start-work --next` writes the first note when work starts, so the work has a direction from its first moment, and `pause-issue <N> --done … --next …` writes one whenever a session stops. Each note is stamped with its time and instance and is never merged with another; the latest one is the issue's direction. Never merging refines how DEC-044 point 2 dedups a re-posted stamp, and waits for authorisation. `start-work.py` is anchored because the first note will be written there; F1 of EPIC #943 adds `pause-issue`'s path as an anchor when it lands.

A note records direction. It is not a handoff — the clone keeps the issue (DEC-026) — and not a block, since the work still has moves (COR-034). Its stamp follows the shared audit record shape (DEC-044).

## TERM-new-front — New front

Intended design, not built yet (EPIC #943) — pending gaps I and K1. No record defines a front yet. The anchor on project-management DEC-004 stands for the hierarchy the definition reads, and nothing more. `start-work.py` is anchored because the start guard will read fronts there. F2 of EPIC #943 adds the record that defines a front as an anchor, and revalidates this term.

A Task with no Feature or Umbrella ancestor is its own front. What a stabilisation holds back is a new front outside release scope: an untouched Feature under the release Milestone, or a Task filed directly under it, is release-scope work, and starting it is allowed (gap K1's proposed fix; the design walked refused every new front). Where "landed" is read for work under an integration marker is open (gap I): on the integration branch, or such work is left out of the start guard altogether.

## TERM-release-scope — Release scope

Intended design, not built yet (EPIC #943). What has landed is derived from the default branch's history since the last release — its commits, their pull requests, the issues those close and the open parents of those issues — never from Milestone tagging, since an issue holds one Milestone. A release is ready when nothing in release scope is open. A parent the operator defers, with the reason stamped on it, leaves release scope for the release gate and the stabilisation guards alike (gap G's proposed fix). Open: whether "open parent" means the nearest parent or every ancestor, and what a Milestone parent or a catch-all Umbrella does to it (K4); and whether a pull request that closes no issue, such as the release pull request, is in scope (gap K3). `release-pr.yml` is anchored because the release gate will read release scope there; F2 of EPIC #943 adds the computation's path as an anchor.

## TERM-session — Session

A session is rooted in one repository and carries that repository's governance (COR-039): that is the part of this term its anchor stands for. That a session's context dies with it is how agent harnesses behave, which no record decides. Killing sessions is ordinary — the operator stops one, a crash takes them all — so nothing a clone needs in order to resume may live only in a session.

## TERM-stabilisation — Stabilisation

A feature freeze, not a code freeze. Intended design, not built yet (EPIC #943): `stabilize-milestone <N> --reason …` writes a `Stabilizing:` line into the Milestone's description, and `--lift`, or closing the Milestone, removes it. While it is on, starting a new front outside release scope (gap K1) or landing out-of-scope work on the default branch is refused unless bypassed with an audited reason (project-management DEC-014), and a required CI status holds the same line, so an out-of-date clone or a raw merge cannot cross it (ADR-019) — pending gap K2: a status computed per commit does not see a stabilisation, or a deferral, that came after a pull request's last commit. The guards' scripts are anchored; F2 of EPIC #943 adds `stabilize-milestone` and the check the required status runs as anchors. The command keeps the American spelling, `stabilize-milestone`.
