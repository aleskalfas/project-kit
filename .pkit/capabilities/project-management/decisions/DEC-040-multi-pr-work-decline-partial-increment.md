---
id: DEC-040
title: No partial-increment path; multi-PR work decomposes among three existing mechanisms
status: accepted
date: 2026-06-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A Task is the unit of implementation work, closed by exactly one PR that carries a `Closes #N` keyword; the auto-close on merge is what fires the closure cascade up the hierarchy (per [project-management:DEC-006-state-machine-and-cascade]). A recurring question is what to do when a piece of work feels too large for a single PR — whether the methodology should grow a *partial-increment* path that lets one Task absorb several PRs, each merging an interim slice while the Task stays open until the last slice lands.

The pull toward such a path is real: large work naturally wants to land in reviewable steps. But the three surfaces that would have to bend to accommodate it — the mandatory `Closes #N` keyword, the one-PR-per-Task shape, and squash-merge — are deliberately chosen invariants, not incidental defaults. This record settles whether to add the fourth mechanism or to direct the want into the three that already exist.

## Decision

The methodology does **not** add a partial-increment / multi-PR-per-Task path. A Task remains one PR-sized unit of implementation work, closed by exactly one PR via `Closes #N`.

When work feels too big for one PR, choose among the three mechanisms the methodology already ships:

1. **Sub-task checkboxes inside one Task** — when the increments are small steps of a single PR-sized unit that share one acceptance criterion. The Task still lands in one PR; the checkboxes track the steps within it. (Per [project-management:DEC-011-title-formats]' `sub_task_promotion` guidance and `body-format`'s sub-task block.)

2. **Decompose into a Feature whose child Tasks each close their own PR** — when the work is genuinely several PR-sized units. This is the primary answer to "this needs multiple PRs": promote the would-be sub-tasks to sibling Tasks under an owning container (Feature / Umbrella / EPIC), and each Task closes its own PR via `Closes #N`.

3. **Integration branch** — when several Tasks must assemble off-`main` before promotion. The opt-in `integration_branches` construct (per [project-management:DEC-013-branch-and-pr-conventions]) roots a shared branch at one owning issue; each marked Task still gets exactly one PR that closes it into the integration branch, and a final PR promotes the assembled branch to `main`.

The discriminator is the size and coupling of the increments: small steps of one unit → path 1; several real units → path 2; several units that must land together off-`main` → path 3.

## Rationale

A multi-PR-per-Task path would cut against three load-bearing invariants at once:

- **Mandatory `Closes #N`.** [project-management:DEC-013-branch-and-pr-conventions] already records the rejection of an optional-`Closes` policy, precisely because auto-close on merge is the primary closure path and the cascade trigger. A partial-increment path needs interim PRs that merge *without* closing their Task — i.e. exactly the optional-`Closes` behaviour already declined.
- **One PR per Task.** The branch / PR conventions derive a single branch and a single closing PR from each Task. Multiple closing PRs per Task would break branch-to-issue derivation and the close-gate that runs once per Task.
- **Squash-merge.** One PR maps to one commit on the base branch. Interim slices that accumulate under one open Task reintroduce the multi-commit-per-unit history that squash-merge exists to avoid.

The closure cascade ([project-management:DEC-006-state-machine-and-cascade]) compounds the cost: it fires off the `Closes #N`-on-merge trigger, so a Task that merges interim PRs without closing has no defined point at which its ancestors learn the work advanced.

Per [COR-007](../../../decisions/core/COR-007-pattern-extraction.md)'s recurrence-and-overlap test, a fourth mechanism is not warranted: the need is already served three ways, each tuned to a different increment shape. Adding a fourth would be inventory ahead of an unmet need, not extraction of an un-served pattern.

### Alternatives considered

- **Add an explicit partial-increment / multi-PR-per-Task path.** Rejected — it requires interim PRs that merge without `Closes #N` (the optional-`Closes` policy already declined in [project-management:DEC-013-branch-and-pr-conventions]), breaks one-PR-per-Task branch derivation, and undoes the squash-merge invariant. The want it serves is already covered by decomposition or an integration branch.
- **Relax the `Closes #N` hard-reject on interim PRs.** Rejected — the hard-reject is the signal that the work has outgrown one Task and should decompose; removing it hides the decision rather than resolving it.

## Implications

- The `Closes #N` hard-reject on a PR that does not close its Task is **working as intended**. It is the prompt to pick one of the three paths above — most often path 2, decompose — not friction to be engineered away.
- No schema, command, or template changes follow from this record. It pins existing behaviour and documents the decision tree authors apply when a Task feels too large.
- Authors and the project-manager route "too big for one PR" to the decision tree: small steps of one unit stay as sub-task checkboxes; several real units become sibling Tasks under a container; several units that must assemble off-`main` use an integration branch.
- If a genuinely un-served increment shape recurs in the future, the COR-007 test reopens — but the bar is an observed shape that none of the three paths covers, not a preference for fewer issues.
