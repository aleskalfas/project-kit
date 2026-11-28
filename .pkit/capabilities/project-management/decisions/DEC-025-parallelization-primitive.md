---
id: DEC-025
title: Parallelization primitive — lanes for code surface and dependencies for sequence, neither carried by workstreams
status: accepted
date: 2026-05-27
author: Ales Kalfas
---

**In plain terms:** two issues cannot be worked on at once for one of two reasons. They touch the same code, or one needs the other's outcome. This record keeps the two conflicts apart, gives each a mechanism of its own, and never makes a workstream carry either. Which work is ready in sequence is read from what each issue waits on, through the shared pool of [project-management:DEC-059-topology-of-seats] point 7 in a project with a topology, or through each seat's pools where the topology declares pools of workers ([project-management:DEC-061-pools-of-workers]). An issue records each wait as the tracker's own blocked-by link, or as a typed line where the project selects it, and one reader reads both. Until a project turns on the checks of DEC-085, readiness is read from each issue's `## Dependencies` section instead (refinement per [project-management:DEC-085-issue-waits]). Lanes, each a lock on one area of the code, are named here, and are built once lived evidence answers the open questions below.

## Context

Real adoption runs **multiple issues concurrently** across worktree branches. Without a methodology primitive, every adopter improvises the discipline and the answers drift. A parallel-execution model has to answer two questions:

1. **Can issues A and B be in flight at the same time?** A primitive for *code-surface conflicts* (overlapping files; merge collisions).
2. **Given the in-flight set, what is the unblocked frontier — what is safe to pick up next?** A primitive for *sequence conflicts* (B depends on A's outcome).

The two conflicts are unrelated — code-surface is static and geography-based; sequence is dynamic and outcome-based — and require different mechanisms.

The capability's other primitives each answer a part:

- [project-management:DEC-018-workstream-taxonomy-and-lifecycle] — workstreams are *long-lived domain areas* (categorisation, reporting). Overloading them as parallel-lane locks muddies the semantic; renames break the lock partition.
- [project-management:DEC-005-linking-and-containment] — native sub-issues handle parent↔child *containment* only. What an issue waits on is the tracker's own blocked-by link, or a typed line in an optional `## Dependencies` body section, whose prose explains (refinement per [project-management:DEC-085-issue-waits]).
- [project-management:DEC-035-instance-ownership] — an issue's owner keeps two clones off that one issue.
- [project-management:DEC-059-topology-of-seats] point 7 — in a project with a topology, workers take ready Tasks from one shared pool. It answers the second question from the owners and the dependencies.
- [project-management:DEC-060-foundation-before-slices] — the choices that slices would share are settled before the slices are planned, so no two slices each make one alone.

Nothing answers the first question for two Tasks that touch the same code. Agent-driven workflows make the gap acute: an orchestrator computing "what is safe to start now" needs both conflicts in a form it can read.

### Why the mechanisms wait for evidence

The scratchpad's own recommended path is **manual discipline first → crystallise the primitive later**: adopters run an informal convention, capturing the discipline that works in practice and watching where the prose substrate breaks, and the primitive is built from that lived evidence.

That follows [COR-007]'s pattern-extraction discipline: invest in tooling when recurrence forces it, not before. Several open questions below are **evidence-shaped** — they cannot be settled from first principles alone:

- In-flight state mechanism — what occupies a lane?
- Cardinality — one lane per issue, or multi-lane?
- Axis placement — lane joins the classification axes from [project-management:DEC-012-classification-axes] as a fourth axis, or lives outside as a lifecycle marker?

These need lived experience to settle. This record fixes the split and the terms, and the build of lanes waits for the evidence. Waits had their evidence first, and DEC-085 decides them (refinement per DEC-085).

## Decision

**Parallel work meets two conflicts, of code surface and of sequence, and each has a mechanism of its own: lanes for code surface, and an issue's dependencies for sequence. Workstreams carry neither. Readiness in sequence is reckoned once, through the shared pool of [project-management:DEC-059-topology-of-seats] point 7 in a project with a topology, or through each seat's pools where the topology declares pools of workers ([project-management:DEC-061-pools-of-workers]). What an issue waits on is recorded and read as [project-management:DEC-085-issue-waits] decides. Lanes are named here, and are built once lived evidence answers the open questions below ([COR-007]). The shape this record gives them is the starting design, which the record that builds them settles.**

### Design at a glance

| Component | Substrate | Built |
|---|---|---|
| Code-surface conflict | `lane:<slug>` label series; one in-flight issue per lane | Named, not built |
| Sequence conflict | The tracker's own blocked-by links, or a typed `Blocked by: #<N>` line where the project selects it ([DEC-085]) | Decided there |
| Lane catalog | `project/lanes.yaml` — adopter-declared lane definitions | Named, not built |
| Readiness in sequence | The shared pool of DEC-059 point 7, in a project with a topology, or each seat's pools where the topology declares them (DEC-061) | Decided there |

### Lanes — additive to DEC-018, not a re-cut

The `workstream:<slug>` taxonomy from [project-management:DEC-018-workstream-taxonomy-and-lifecycle] stays exactly as written — long-lived domain areas; portfolio-scale; categorisation. **Lanes are a separate primitive** with a separate substrate (`lane:<slug>` label series) and separate semantic (ephemeral; code-area scope; operational lock, not categorisation).

The etymological re-cut (renaming workstreams to lanes) was rejected at the scratchpad stage because shared-board topologies (several repositories feeding one organisation-level planning board) carry the workstream field at the board level; renaming would require multi-team, multi-repo, multi-environment coordination for what is fundamentally a linguistic cleanup. The substrate vetoes the rename. See the scratchpad for the full analysis.

### `lane:<slug>` label series

A label series, parallel to but distinct from `workstream:<slug>`. Each label names an ephemeral lock domain (file area, deployment target, fixture set — adopter's call). **At most one in-flight issue per lane** is the lock rule. What counts as in flight is open question 1.

Until lanes are built, readiness reckons nothing from the code a Task touches. The planner orders Tasks that share a file through their dependencies, and the merge settles any other overlap (refinement per [project-management:DEC-066-fold-tasks-that-share-a-file]). Whether and how a lane's lock holds a ready Task back is for the record that builds lanes, which then refines DEC-059 point 7.

### `project/lanes.yaml` — lane catalog

The starting design: an adopter declares lane definitions in a separate file, paralleling `project/workstreams.yaml`:

```yaml
schema_version: 1

lanes:
  - slug: workbench
    description: Sandbox harness code (workbench/, harness libs).
  - slug: gateway
    description: Gateway routing + auth code.
  - slug: recorder
    description: Session recording subsystem.
```

The lane attribute model starts **lighter** than the workstream's 5-attribute shape: slug + description only. Lanes are ephemeral by intent; the workstream attribute model (`status`, `deprecated_reason`) doesn't earn its keep for short-lived lock domains. Open question 5 settles it.

### Waits — the tracker's links, or a typed line (refinement per [project-management:DEC-085-issue-waits])

What an issue waits on is recorded in one of two forms: the tracker's own blocked-by links, by default, or a typed `Blocked by: #N` line in the issue's `## Dependencies` section, where the project selects it. One reader reads both forms for every command that reckons readiness, the shared pool among them ([DEC-059] point 7, [DEC-060]). A Task waits on what its Feature, Umbrella or EPIC waits on too, which holds back its start but not its merge. The rest of the section is prose that explains, and no command reads it as a wait. Until a project turns on DEC-085's checks, readiness is reckoned from the section instead, each open issue it names holding a Task back. A Task declares its waits, or that it waits for nothing, with the line `Blocked by: nothing` in that section. DEC-085 decides too what a wait may name, how a project turns on the checks that refuse or hold a Task, and how a project's existing sections are converted.

### Readiness is reckoned once

In a project with a topology, which Tasks are ready in sequence is the shared pool's answer ([DEC-059] point 7), and the capability reckons readiness only through the pool. Where the topology declares pools of workers, that answer routes through each seat's pools ([project-management:DEC-061-pools-of-workers]). In a project with no topology, whoever hands out the work reads each issue's dependencies the same way, as the manual discipline does. Readiness on code surface waits for lanes.

### Lane lifecycle — leaner than DEC-018

Workstreams ship eight lifecycle scripts (add / rename / merge / split / edit / remove / show / list). The starting design gives lanes a leaner set:

| Verb | Purpose |
|---|---|
| `add-lane` | Add a lane to `lanes.yaml` + create the `lane:<slug>` label |
| `remove-lane` | Remove a lane; refuse if any issue still uses the label unless `--force` |
| `list-lanes` | List declared lanes; surface occupancy from open-issue scan |
| `show-lane` | Read-only view of one lane entry |

`rename-lane`, `merge-lane`, `split-lane`, `edit-lane` start deferred — lanes are ephemeral by intent; the rename/merge/split operations on a workstream taxonomy don't translate. Open question 9 settles it, and recurrence (COR-007) promotes the deferred verbs if needed.

## Open questions — evidence sought

The record that builds lanes answers these from lived experience. [project-management:DEC-085-issue-waits] answers question 4, and question 10 for waits, and narrows question 8. Field notes accumulate in the source scratchpad (`.pkit/scratchpad/active/2026-05-26-parallelization-primitive.md`). In a project with a topology, the shared pool settles question 6 and part of question 8. The topology settles question 7 too, whether it declares pools of workers or not: where it does, the open milestones of a seat's pools gate that seat's ready set, and where it does not, no milestone gates the ready set.

1. **In-flight state mechanism.** Computed from what? Candidates:
   - Issue state machine (`in_progress` from [project-management:DEC-006-state-machine-and-cascade])
   - In a project with a topology, an owner's claim that counts ([DEC-059] point 9)
   - Presence of a linked draft PR, or an open pull request through Review
   - Non-null assignee
   - Explicit `in-flight: true` label
   - Some combination
2. **Cardinality.** One lane per issue (mirrors workstream's mutual-exclusion), or multi-lane (an issue touching two code areas locks both)? Multi-lane gives accurate locking but explodes the "is anything ready?" query.
3. **Axis placement.** Does `lane` join [project-management:DEC-012-classification-axes]'s three axes as a fourth axis (type, priority, workstream, lane), or live outside the classification model as a lifecycle marker (similar in spirit to milestone — orthogonal to the axes)?
4. **`Blocked by:` validation shape** (refinement per DEC-085). A typed line names one issue of the waiting issue's own repository, as `#N`, and a line of the same shape with `nothing` in place of the number declares that a Task waits for nothing. A wait is apart from containment: a child does not wait on its parent, a wait on the waiting issue's ancestor is refused, since it would hold work back for good, and a container's wait holds back the start of the Tasks under it (DEC-085 points 1, 4 and 12).
5. **Lane attribute model.** Stick with slug + description, or grow toward DEC-018's 5-attribute shape if lanes prove less ephemeral than expected?
6. **Ready-frontier command name + output.** In a project with a topology, readiness in sequence is the shared pool's ([DEC-059] point 7), so no command of this record reckons it. In a project with none, it is read by hand.
7. **Interaction with milestones / time-containers.** Does the active milestone gate the parallel frontier (issues outside the current milestone excluded from the ready set)? Where the topology declares pools of workers, every open milestone of the seat's pools gates it, for each seat that builds: the seat chooses its work only from ready Tasks in those milestones ([project-management:DEC-061-pools-of-workers] point 5). Where the topology declares no pool, no milestone gates the ready set.
8. **Cross-repo dependencies (DEC-022 mesh).** The shared pool is the repository's own (DEC-059, Implications). Does the Blocked-by graph cross repo boundaries, and if so, how does readiness read another repository's state? Until a record answers it, a wait on another repository's issue is refused when written, and leaves its waiting issue's readiness unknown when found (refinement per DEC-085).
9. **Lane lifecycle scope.** Do `rename-lane` / `merge-lane` / `split-lane` / `edit-lane` ship with the first build of lanes, or stay deferred per COR-007?
10. **Build criterion.** How much lived parallel work counts as enough evidence to build lanes? What signals close the question? For waits, prose read as waits held Tasks back for good, and a view of the work needed waits it can read: that evidence is enough to build them (refinement per DEC-085).
11. **In-flight detection in board mode.** Label-substrate adopters detect lane occupancy from `lane:*` labels on open issues. Board-substrate adopters might use a board-state field instead. Does the primitive support both, or require label substrate? (Working assumption: label-substrate-only since lanes are ephemeral — but evidence might force otherwise.)

## Rationale

The two-conflict shape — code-surface (static, geography) vs sequence (dynamic, outcome) — comes from how parallel work actually fails in practice: either two PRs touch the same files and merge-conflict, or one PR depends on another's outcome and starts too early. Adopters don't conflate these in conversation ("we can't run those at the same time because they touch the same surface" vs "B can't start until A lands"); the primitive shouldn't conflate them either.

The additive choice (separate `lane:*` series rather than re-cutting `workstream:*`) was forced by shared-board substrate. The full analysis lives in the source scratchpad. The decision here is: lanes are operationally distinct from workstreams; the methodology gives each its own substrate and lifecycle.

**Why readiness is reckoned once.** One reckoning of ready work keeps every seat reading the same answer. A reporter of its own would read dependencies apart from the owners and lapses that DEC-059 point 9 reads, and the two answers would drift.

**Why lanes wait.** The open questions are evidence-shaped ([COR-007]). The pool, the owner and the foundation of DEC-060 already keep agents from colliding on one Task or on one shared choice. How often two Tasks still collide on code is the evidence lanes wait for. Waits had their evidence first: prose read as waits held Tasks back for good, so DEC-085 decides them.

The leaner lane lifecycle (4 verbs vs workstream's 8) reflects the ephemeral-by-intent design. Rename / merge / split are taxonomy operations; ephemeral lock domains don't typically need them. COR-007 promotes when recurrence forces.

The prose of a `## Dependencies` section stays, as explanation. Until a project turns on the checks of DEC-085 point 11, readiness is reckoned from that section, each open issue it names holding a Task back, and nothing DEC-085 adds holds or refuses a Task. So a project that writes its dependencies as prose meets no breaking change until then. A project's existing sections are converted to waits through a proposal a person reviews (DEC-085 point 10), and once the checks are on, the prose holds nothing back.

### Alternatives considered

- **Overload `workstream:` as code-area lanes.** Rejected — breaks DEC-018's semantic; workstream renames break the lane partition; monorepos with cross-cutting libraries have nowhere to land.
- **Lanes only, with no dependencies read.** Rejected — covers code-surface but not sequence conflict.
- **Dependencies only, with no lanes ever.** Rejected as the destination — covers sequence but not code-surface conflict. It is what stands until lanes are built.
- **Build the full primitive now — lanes, waits and a ready-frontier reporter of its own.** Not taken. Lanes' open questions are evidence-shaped, and a reporter of its own would reckon readiness apart from the shared pool. DEC-085 decides waits, once their evidence came.
- **Manual discipline only — diligent prose convention + manual coordination, no methodology surface.** The bridge until lanes are built. Adopters keep the discipline by hand, and its field notes are the evidence the build reads.

## Implications

- **No behaviour changes with this record.** It fixes the split and the terms. A record of their own builds lanes once evidence answers the open questions, and adopters keep the manual discipline until then. DEC-085 decides waits.
- **DEC-005, overturned in part** — DEC-085 overturns DEC-005's table in part, so that "blocked by" is the tracker's own link, or a typed line where the project selects it.
- **DEC-012 axis-model decision** — open question 3 either adds a fourth axis, which updates DEC-012, or places lanes outside the axis model, which leaves it as it stands.
- **New schema: `project/lanes.yaml`**, with the build of lanes. Optional file; absence equals no lanes; the capability's pre-check validates it when present.
- **New scripts**, with the build of lanes: `add-lane`, `remove-lane`, `list-lanes`, `show-lane`. Each lifecycle script reaches GitHub through the shared helper of [project-management:DEC-023-gh-host-and-owner].
- **No interaction with hooks at v1.** DEC-024's hook events do not include lane lifecycle events. If lane lifecycle hooks become useful, recurrence (COR-007) adds them later.
- **Mesh interaction.** Lanes are repo-local by design — ephemeral, code-area-bound. [project-management:DEC-022-methodology-mesh]'s `check-mesh.py` ignores `lanes.yaml`. The Blocked-by graph crossing repo boundaries is open question 8.
- **Versioning.** The build of lanes, and that of waits, is a surface change of this capability, versioned per [pkit:PRJ-002]. This record changes no behaviour.

## Source scratchpad

`.pkit/scratchpad/active/2026-05-26-parallelization-primitive.md` — captures the etymological analysis (workstream vs lane), the field notes section, the substrate-veto argument against re-cutting DEC-018, and the manual-discipline → crystallised-primitive plan. The scratchpad stays open for the field notes, and retires per [COR-012] when the record that builds lanes is accepted.
