---
id: DEC-025
title: Parallelization primitive — lanes for code surface and dependencies for sequence, neither carried by workstreams
status: accepted
date: 2026-05-27
author: Ales Kalfas
---

**In plain terms:** two issues cannot be worked on at once for one of two reasons. They touch the same code, or one needs the other's outcome. This record keeps the two conflicts apart, gives each a mechanism of its own, and never makes a workstream carry either. Which work is ready in sequence is read from each issue's dependencies, through the shared pool of [project-management:DEC-059-topology-of-seats] point 7 in a project with a topology. Lanes, each a lock on one area of the code, are named here, and so is a typed line for each dependency. Both are built once lived evidence answers the open questions below.

## Context

Real adoption runs **multiple issues concurrently** across worktree branches. Without a methodology primitive, every adopter improvises the discipline and the answers drift. A parallel-execution model has to answer two questions:

1. **Can issues A and B be in flight at the same time?** A primitive for *code-surface conflicts* (overlapping files; merge collisions).
2. **Given the in-flight set, what is the unblocked frontier — what is safe to pick up next?** A primitive for *sequence conflicts* (B depends on A's outcome).

The two conflicts are unrelated — code-surface is static and geography-based; sequence is dynamic and outcome-based — and require different mechanisms.

The capability's other primitives each answer a part:

- [project-management:DEC-018-workstream-taxonomy-and-lifecycle] — workstreams are *long-lived domain areas* (categorisation, reporting). Overloading them as parallel-lane locks muddies the semantic; renames break the lock partition.
- [project-management:DEC-005-linking-and-containment] — dependencies between issues are **textual prose** in an optional `## Dependencies` body section, with no typed line a validator can parse. Native sub-issues handle parent↔child *containment* only.
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
- `Blocked by:` validation shape — `#N` only, `owner/repo#N`, both?

These need lived experience to settle. This record fixes the split and the terms, and the build of each mechanism waits for the evidence.

## Decision

**Parallel work meets two conflicts, of code surface and of sequence, and each has a mechanism of its own: lanes for code surface, and an issue's dependencies for sequence. Workstreams carry neither. Readiness in sequence is reckoned once, through the shared pool of [project-management:DEC-059-topology-of-seats] point 7 in a project with a topology. Lanes and the typed `Blocked by:` line are named here, and are built once lived evidence answers the open questions below ([COR-007]). The shapes this record gives them are the starting design, which the record that builds each settles.**

### Design at a glance

| Component | Substrate | Built |
|---|---|---|
| Code-surface conflict | `lane:<slug>` label series; one in-flight issue per lane | Named, not built |
| Sequence conflict | The `## Dependencies` body section ([DEC-005]), with a typed `Blocked by: #<N>` line | The section is built, and the typed line named, not built |
| Lane catalog | `project/lanes.yaml` — adopter-declared lane definitions | Named, not built |
| Readiness in sequence | The shared pool of DEC-059 point 7, in a project with a topology | Decided there |

### Lanes — additive to DEC-018, not a re-cut

The `workstream:<slug>` taxonomy from [project-management:DEC-018-workstream-taxonomy-and-lifecycle] stays exactly as written — long-lived domain areas; portfolio-scale; categorisation. **Lanes are a separate primitive** with a separate substrate (`lane:<slug>` label series) and separate semantic (ephemeral; code-area scope; operational lock, not categorisation).

The etymological re-cut (renaming workstreams to lanes) was rejected at the scratchpad stage because shared-board topologies (several repositories feeding one organisation-level planning board) carry the workstream field at the board level; renaming would require multi-team, multi-repo, multi-environment coordination for what is fundamentally a linguistic cleanup. The substrate vetoes the rename. See the scratchpad for the full analysis.

### `lane:<slug>` label series

A label series, parallel to but distinct from `workstream:<slug>`. Each label names an ephemeral lock domain (file area, deployment target, fixture set — adopter's call). **At most one in-flight issue per lane** is the lock rule. What counts as in flight is open question 1.

Until lanes are built, readiness takes no account of the code a Task touches, and the merge settles an overlap. Whether and how a lane's lock holds a ready Task back is for the record that builds lanes, which then refines DEC-059 point 7.

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

### Typed `Blocked by:` — a layer over DEC-005's prose

Dependencies are prose in an issue's optional `## Dependencies` body section ([project-management:DEC-005-linking-and-containment]), and the shared pool reads them ([DEC-059] point 7, [DEC-060]). The layer named for them is a **typed line** a validator can parse. The starting design:

```markdown
## Dependencies

Blocked by: #142
Blocked by: example-org/other-repo#27
```

Prose narrative may follow the typed lines. The validator extracts the typed lines into a parseable graph; the prose stays for human context. Which forms the line accepts is open question 4. DEC-059 names typed dependencies among what it does not build, and the record that builds them refines DEC-005.

### Readiness is reckoned once

In a project with a topology, which Tasks are ready in sequence is the shared pool's answer ([DEC-059] point 7), and the capability reckons readiness only through the pool. In a project with none, whoever hands out the work reads each issue's dependencies the same way, as the manual discipline does. Readiness on code surface waits for lanes.

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

The record that builds lanes and the typed line answers these from lived experience. Field notes accumulate in the source scratchpad (`.pkit/scratchpad/active/2026-05-26-parallelization-primitive.md`). In a project with a topology, the shared pool settles question 6 and part of question 8, and pools of workers settle question 7 where the topology declares them.

1. **In-flight state mechanism.** Computed from what? Candidates:
   - Issue state machine (`in_progress` from [project-management:DEC-006-state-machine-and-cascade])
   - In a project with a topology, an owner's claim that counts ([DEC-059] point 9)
   - Presence of a linked draft PR, or an open pull request through Review
   - Non-null assignee
   - Explicit `in-flight: true` label
   - Some combination
2. **Cardinality.** One lane per issue (mirrors workstream's mutual-exclusion), or multi-lane (an issue touching two code areas locks both)? Multi-lane gives accurate locking but explodes the "is anything ready?" query.
3. **Axis placement.** Does `lane` join [project-management:DEC-012-classification-axes]'s three axes as a fourth axis (type, priority, workstream, lane), or live outside the classification model as a lifecycle marker (similar in spirit to milestone — orthogonal to the axes)?
4. **`Blocked by:` validation shape.** Patterns the validator accepts: `#N` only, `owner/repo#N` for cross-repo, both? How does it interact with native sub-issues?
5. **Lane attribute model.** Stick with slug + description, or grow toward DEC-018's 5-attribute shape if lanes prove less ephemeral than expected?
6. **Ready-frontier command name + output.** In a project with a topology, readiness in sequence is the shared pool's ([DEC-059] point 7), so no command of this record reckons it. In a project with none, it is read by hand.
7. **Interaction with milestones / time-containers.** Does the active milestone gate the parallel frontier (issues outside the current milestone excluded from the ready set)? Where the topology declares pools of workers, it does, for each pool: a seat that builds takes only ready Tasks in an open milestone of a pool it serves ([project-management:DEC-061-pools-of-workers] point 5). Without pools, no milestone gates the ready set.
8. **Cross-repo dependencies (DEC-022 mesh).** The shared pool is the repository's own (DEC-059, Implications). Does the Blocked-by graph cross repo boundaries, and if so, how does readiness read another repository's state?
9. **Lane lifecycle scope.** Do `rename-lane` / `merge-lane` / `split-lane` / `edit-lane` ship with the first build of lanes, or stay deferred per COR-007?
10. **Build criterion.** How much lived parallel work counts as enough evidence to build lanes and the typed line? What signals close the question?
11. **In-flight detection in board mode.** Label-substrate adopters detect lane occupancy from `lane:*` labels on open issues. Board-substrate adopters might use a board-state field instead. Does the primitive support both, or require label substrate? (Working assumption: label-substrate-only since lanes are ephemeral — but evidence might force otherwise.)

## Rationale

The two-conflict shape — code-surface (static, geography) vs sequence (dynamic, outcome) — comes from how parallel work actually fails in practice: either two PRs touch the same files and merge-conflict, or one PR depends on another's outcome and starts too early. Adopters don't conflate these in conversation ("we can't run those at the same time because they touch the same surface" vs "B can't start until A lands"); the primitive shouldn't conflate them either.

The additive choice (separate `lane:*` series rather than re-cutting `workstream:*`) was forced by shared-board substrate. The full analysis lives in the source scratchpad. The decision here is: lanes are operationally distinct from workstreams; the methodology gives each its own substrate and lifecycle.

**Why readiness is reckoned once.** One reckoning of ready work keeps every seat reading the same answer. A reporter of its own would read dependencies apart from the owners and lapses that DEC-059 point 9 reads, and the two answers would drift.

**Why lanes and the typed line wait.** The open questions are evidence-shaped ([COR-007]). The pool, the owner and the foundation of DEC-060 already keep agents from colliding on one Task or on one shared choice. How often two Tasks still collide on code is the evidence lanes wait for.

The leaner lane lifecycle (4 verbs vs workstream's 8) reflects the ephemeral-by-intent design. Rename / merge / split are taxonomy operations; ephemeral lock domains don't typically need them. COR-007 promotes when recurrence forces.

The typed line, once built, preserves the existing prose substrate (no breaking change for adopters who use `## Dependencies` informally) and adds a parseable layer on top. Two adoption modes — informal-prose + typed-line — coexist until typed-line is ubiquitous.

### Alternatives considered

- **Overload `workstream:` as code-area lanes.** Rejected — breaks DEC-018's semantic; workstream renames break the lane partition; monorepos with cross-cutting libraries have nowhere to land.
- **Lanes only, with no dependencies read.** Rejected — covers code-surface but not sequence conflict.
- **Dependencies only, with no lanes ever.** Rejected as the destination — covers sequence but not code-surface conflict. It is what stands until lanes are built.
- **Build the full primitive now — lanes + typed Blocked-by + a ready-frontier reporter of its own.** Not taken. The open questions are evidence-shaped, and a reporter of its own would reckon readiness apart from the shared pool.
- **Manual discipline only — diligent prose convention + manual coordination, no methodology surface.** The bridge until lanes and the typed line are built. Adopters keep the discipline by hand, and its field notes are the evidence the build reads.

## Implications

- **No behaviour changes with this record.** It fixes the split and the terms. A record of their own builds lanes and the typed line once evidence answers the open questions, and adopters keep the manual discipline until then.
- **DEC-005 refinement** — the record that builds the typed line refines DEC-005 with a "Typed Blocked-by lines" subsection cross-referencing this record, and bumps the schema of the issue body format.
- **DEC-012 axis-model decision** — open question 3 either adds a fourth axis, which updates DEC-012, or places lanes outside the axis model, which leaves it as it stands.
- **New schema: `project/lanes.yaml`**, with the build of lanes. Optional file; absence equals no lanes; the capability's pre-check validates it when present.
- **New scripts**, with the build of lanes: `add-lane`, `remove-lane`, `list-lanes`, `show-lane`. Each lifecycle script reaches GitHub through the shared helper of [project-management:DEC-023-gh-host-and-owner].
- **No interaction with hooks at v1.** DEC-024's hook events do not include lane lifecycle events. If lane lifecycle hooks become useful, recurrence (COR-007) adds them later.
- **Mesh interaction.** Lanes are repo-local by design — ephemeral, code-area-bound. [project-management:DEC-022-methodology-mesh]'s `check-mesh.py` ignores `lanes.yaml`. The Blocked-by graph crossing repo boundaries is open question 8.
- **Versioning.** The build of lanes and of the typed line is a surface change of this capability, versioned per [pkit:PRJ-002]. This record changes no behaviour.

## Source scratchpad

`.pkit/scratchpad/active/2026-05-26-parallelization-primitive.md` — captures the etymological analysis (workstream vs lane), the field notes section, the substrate-veto argument against re-cutting DEC-018, and the manual-discipline → crystallised-primitive plan. The scratchpad stays open for the field notes, and retires per [COR-012] when the record that builds lanes and the typed line is accepted.
