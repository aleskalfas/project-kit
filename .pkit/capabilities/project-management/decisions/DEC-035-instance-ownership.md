---
id: DEC-035
title: Instance ownership — distinguish concurrent clones of one identity
status: accepted
date: 2026-06-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **Partially superseded by [DEC-059](DEC-059-topology-of-seats.md).** In a project that declares a topology of seats in its committed configuration, a clone takes part by taking a seat, and its number is the seat's. Overturned for such a project: point 1's typed number as the sign that a clone takes part, point 2's pool of four numbers for each assignee, point 3's claim at creation by a clone in a planner's seat, and the Rationale's statement that no committed registry is needed. A project with no topology keeps this record whole. DEC-059's "What this overturns, and what stands" lists each passage.

When one person runs several clones of the same repository — each with its own
agent session driving the work-tracker — every issue shows the same human as
assignee, so no clone can tell which in-flight work belongs to which clone, and
the clones step on each other. This decision adds an **opt-in** mechanism so each
clone marks the issues it owns, sees whose-is-whose at a glance, can hand work
between clones, and is guarded (advisorily) against acting on another clone's
work. A clone that does not opt in behaves as if the facility were not there.

The mechanism is deliberately small: a per-clone identity the clone sets for
itself, a marker on the issue that records ownership, and ownership side-effects layered
onto the lifecycle commands the capability already owns. It is **not** a lock —
GitHub offers no atomic claim — so the guard *catches and resolves* clashes
rather than *preventing* them.

## Context

The capability binds to GitHub (per [project-management:DEC-003-github-bound-substrate]),
where an issue's only built-in "who" is its assignee — a real account. A single
person working from multiple clones is one account across all of them, so the
assignee cannot distinguish the clones. The lifecycle verbs
([project-management:DEC-026-work-ownership-lifecycle]) and the engine rebind
([project-management:DEC-033-rebind-issue-lifecycle-onto-process-substrate],
[project-management:DEC-034-cascade-slot-binding]) give the capability a set of
commands every mutation flows through — the natural seam to layer ownership onto.

The problem has two halves. **Visibility** — "which issues are this clone's?" —
is the motivating pain and is fully solvable. **Enforcement** — "stop two clones
clashing" — is only partially solvable: GitHub exposes no atomic test-and-set on
a label or assignee, so two clones can claim the same free issue in the same
instant before either's mark is visible. The design separates the two and is
honest about the limit of the second.

## Decision

Add an **opt-in instance-ownership** facility to the project-management
capability. The concept is named **instance ownership** (never "membership" —
that term already carries two meanings: team membership in
[project-management:DEC-021-team-membership-gate] and cascade membership in
[project-management:DEC-034-cascade-slot-binding]).

### 1. Activation is per-clone and opt-in

A clone sets its own identity with a
`set-instance <N>` command that writes a clone-local **instance id** to a
git-ignored runtime file (declared via the capability's `runtime_ignore:`
key per [pkit:ADR-009] rule 7, so it is never committed). A clone with
no instance id set behaves as if the facility were not there — no marking, no guard, no
signing. The presence of the id is the sole activation gate. The same runtime file
keeps a key the clone generates the first time it claims on a state issue (refinement
per [project-management:DEC-058-state-issues]).

A clone's identity may also carry a
human-readable **name**, such as `data` or `map`, on top of its number. An issue's
*expected* owner may then come from the instance that references its workstream, and
that expected owner feeds the pm-layer guard only. Where no instance or several reference the workstream,
the guard keeps the numeric behaviour described here (refinement per
[project-management:DEC-045-named-per-user-instances]).

### 2. Ownership is carried by a marker paired with the assignee

The label reuses the label substrate of
[project-management:DEC-012-classification-axes] but is **not** a
classification axis (it is optional, never inferred from issue content, and
carries no required/mutually-exclusive semantics — it gets its own schema
home, not a slot in the axes map). The owner is the **`(assignee, instance:N)`
pair**: the pool of instance numbers (default 4) is *per-assignee*, so one
assignee's `instance:2` is distinct from another's. Labels are created lazily
on first use, so default `bootstrap` is untouched.

The marker's substrate is selectable, "substrate-where-available". The `instance:N`
label described here is one binding, which an operator who knows the repository can
create labels opts into. By default a per-instance, append-only comment log carries the
marker as its source of truth, with a derived, regenerable owner mirror in the issue
description. Comment
creation is atomic per object, so the same-instant tie-break of point 6 holds on
either substrate (refinement per [project-management:DEC-043-ownership-substrate-selection]).

Where this record names the label, it means the marker on whichever substrate carries
it: each stamp, strip, transfer and re-read below acts on that marker.

### 3. A clone claims at creation, for the whole tree

`create-issue` stamps the
creating clone's instance label; the clone owns the entire filed arc
(containers + leaves) from birth. `start-work` claims an issue that has no
owner yet (legacy / human-filed / pre-feature — the *commons*).

### 4. Ownership releases on terminal transitions and transfers on reclaim

The
label is stripped when the issue closes (PR-merge or won't-do). For a
container that closes via the cascade fold
([project-management:DEC-034-cascade-slot-binding]), the **pm closure wrapper
that observes the fold strips the label** — the engine fold itself stays
realm-blind. Work is redistributed with `handoff-issue` extended by
`--to-instance <N>` (push), `--to-instance self` (pull/claim), and
`--recursive` (subtree). Reclaim between one person's own clones changes only
the label, not the assignee. In a project with a topology, an owner also releases
a Task once it stops work on it, and its work renews the claim as it goes on. A
claim on a Task In Progress that its work has not renewed within a generous limit
lapses, and a claim counts only while its clone holds the claim's seat (refinement
per [project-management:DEC-059-topology-of-seats]).

### 5. Changing the assignee strips the label

Because the owner is the
`(assignee, instance:N)` pair, assigning an issue to a *different person*
removes the instance label; the new assignee re-claims with their own clone
(or leaves it, if they run none). Filing for another
(`create-issue --assignee <other>`) is the same case: the creating clone's
label does not stick to an issue assigned to someone else.

### 6. The clash guard catches and resolves; it does not lock

An *ordinary*
lifecycle verb (`start-work`, `done-work`, `edit-issue`, `move-issue`) acting
on an issue already owned by another instance is refused with
`[validation-severity:bypassable-with-audit]` — overridable with a reason
that posts an audit comment; reclaim is the clean alternative. This catches
the everyday clash. For the *same-instant* clash (two clones claim the same
commons issue before either label is visible — unpreventable, as GitHub has
no atomic claim), the claiming verb **re-reads after stamping**; if two
instance labels are present it has detected a collision and the
**higher-numbered instance auto-backs-off** (removes its label, abandons the
claim, notifies). The **lowest instance number wins** — a tie-break both
clones compute identically from the labels alone, with no coordination. In a
project with a topology, a claim that no longer counts is no claim, so the guard
does not refuse on it. Every command that writes as the owner reads the claim
first, and a session whose claim no longer counts parks its work (refinement per
[project-management:DEC-059-topology-of-seats]).

### 7. Listings show every issue, signed by owner

**Listings show every issue, signed by owner** (`mine` / `other instance` /
`unclaimed`), with a flag to narrow to this instance's own.

### 8. The instance marker is a pm-domain side-effect, never engine state

Claim, release, transfer, and the guard all live in the capability's command
wrappers (the same seam branch-creation rides per DEC-033). The process
engine and its cascade predicates
([project-management:DEC-034-cascade-slot-binding],
[pkit:COR-037-process-cascade]) stay **realm-blind**: instance ownership is
never an input to a gate, a transition, or the cascade fold. This keeps the
shared substrate content-free.

### How this record extends DEC-026

This DEC **extends the `handoff-issue` contract** of
[project-management:DEC-026-work-ownership-lifecycle] with the `--to-instance`
modes, `--recursive`, and a transfer between one person's clones that keeps the
assignee. DEC-026's handoff between people stands, and its "The seven commands"
points here.

## Rationale

**Why opt-in by clone-local id, no committed config.** The single-clone case is
the overwhelming common one and must stay zero-ceremony; gating on the presence
of a clone-local id means a non-participating clone is byte-for-byte unchanged.
Clones coordinate through the ownership markers on GitHub (the shared substrate per
DEC-003), so no committed registry is needed — the feature's entire persistent state
is the per-clone id plus the markers.

**Why a label paired with the assignee, not the assignee alone or a synthetic
handle.** GitHub assignees must be real accounts, so a `user@instance` assignee
is impossible. The instance number alone is ambiguous across people; pairing it
with the assignee makes "Alice's clone 2" precise and keeps the pool per-person.
Reusing the label substrate (not a new mechanism) is cheap; refusing to make it
a classification axis avoids distorting [project-management:DEC-012-classification-axes]
(every axis there is required + inferred + mutually-exclusive; ownership is none
of those).

**Why claim-at-creation for the whole tree.** A clone picks work off the backlog,
so it must be able to tell, *while an item sits in the backlog*, which arc is
another clone's. Claiming only at start-work would leave the backlog ambiguous —
the exact pain. Owning the filed tree from birth makes a batch-planned arc cohere
as one clone's territory; per-issue reclaim (point 4) keeps it redistributable,
and a partially-reclaimed tree is reported faithfully by the signed listing
rather than being a contradiction.

**Why catch-and-resolve, not a lock — stated honestly.** GitHub has no atomic
claim, so no command, however gated, can guarantee mutual exclusion. The everyday
clash (acting on already-owned work) *is* preventable and is blocked. The rare
same-instant clash is detected-and-auto-resolved (lowest number wins) rather than
silently producing double-work. Presenting the guard as anything stronger would
be false confidence; this record names the limit explicitly.

**Why capability-local, not a core principle.** "One identity, many concurrent
working instances" has exactly one consumer today (this capability). Per
[pkit:COR-007] the extraction trigger is a second independent binding; until then
a kit-level principle would be speculative generality. If it recurs, its natural
home is the process substrate's peer-subject awareness
([pkit:COR-037-process-cascade] gestures at peer concerns), not a standalone
principle — noted so a future maintainer does not re-derive it as a COR.

### Alternatives considered

- **Visibility only (drop the guard and reclaim).** Ship signed listings and
  labelling, no enforcement. Tempting because the guard cannot lock — but the
  everyday clash *is* preventable, and catch-and-resolve adds real value over
  silent double-work. Kept the guard, framed honestly.
- **Leaf-only claim (containers stay unclaimed).** Dissolves the
  container-close label-strip question automatically. Rejected in favour of
  whole-tree ownership (the closure wrapper strips the container label cleanly,
  point 4), because backlog-level "whose arc is this" visibility is the stated
  need and leaf-only does not provide it.
- **Decouple ownership from assignee** (instance label stands alone). Simpler,
  but loses the per-person pool that lets two people each run clones without
  colliding number-spaces. Kept the pair; handle reassignment by stripping
  (point 5).
- **Earliest-claim-wins tie-break.** More intuitively fair, but needs event-
  history reads and ties on the same second. Lowest-number-wins needs only the
  labels and never ties — and which of one person's clones wins is immaterial.

## Implications

- **New command `set-instance <N>`** writes the clone-local id; the capability's
  `package.yaml` declares that runtime file under `runtime_ignore:` so it is
  never committed (reuses the [pkit:ADR-009] rule 7 renderer; pure additive,
  trips no migration).
- **`create-issue`, `start-work`, `done-work`, `close-issue`, `edit-issue`,
  `move-issue` gain ownership side-effects** (stamp / claim-commons / strip /
  guard) as wrapper-level behaviour — additive, the same class as branch-
  creation; the engine is untouched.
- **`handoff-issue` gains `--to-instance <N>`, `--to-instance self`,
  `--recursive`** and a same-assignee, marker-only transfer mode — a contract
  extension on [project-management:DEC-026-work-ownership-lifecycle], which
  points here.
- **A new schema home for the ownership marker** (its own section/file, not a
  slot in `classification.yaml`), referencing the
  [project-management:DEC-014-validation-severity-model] tokens for the guard.
- **The cascade predicates stay realm-blind** ([project-management:DEC-034-cascade-slot-binding]);
  if a future "close only my realm's children" notion is wanted, it must not
  feed instance ownership into the engine fold — that would cross the
  content-free boundary [pkit:COR-037-process-cascade] holds and require its own
  authorisation.
- **Listings sign by owner** only when the feature is active; otherwise
  unchanged.
- **Deferred (per [pkit:COR-007], named not built):** the Projects-v2 board-field
  equivalent of the label; configurable pool size (ship the constant 4); the
  cross-*human* same-instant tie-break (the single-user case is fully covered).
- **Pattern lineage:** the brownfield-adoption and this note are distinct design
  inputs; this DEC retires the `multi-clone-issue-ownership` scratchpad
  (`pkit scratchpad done multi-clone-issue-ownership --produced DEC-035`).
