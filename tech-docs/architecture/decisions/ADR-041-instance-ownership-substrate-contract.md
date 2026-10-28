---
id: ADR-041
title: Fold the instance-ownership comment log through one read seam and regenerate the description mirror through one write point — comment-log authoritative, mirror derived, comment-wins over a lingering label
status: accepted
date: 2026-07-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** an issue's instance-owner can be recorded two ways — DEC-035's
`instance:N` label where the repo can create labels, and DEC-043's label-free
substrate where it cannot: an **append-only log of ownership events**
(claim / handoff / abandon / release) posted as issue comments, with a
plain-language **mirror of the *current* owner regenerated into the issue
description** so a human sees who owns an issue without reading the log. This
contract says: there is **one place** that reads that comment log and folds it to
"who owns this issue now" (every consumer asks it — the clash guard, the signed
listing, the mirror renderer — none re-scans comments itself), and **one place**
each that constructs an ownership-event comment write and regenerates the
description mirror. The comment log is **authoritative**; the description mirror
is a **derived** view the read seam regenerates by full overwrite, never a source
of truth. Where a repo carries both a lingering `instance:N` label and a
comment-log marker, the seam resolves **comment-log-wins**, once, for every
consumer. In a project with a topology of seats, the fold also takes from its caller
the time of reading, the limit, the Task's state and the seats' holders, and reads
no other seam (point 7). That is the whole decision; everything below is the rigor
behind it.

[project-management:DEC-043](../../../.pkit/capabilities/project-management/decisions/DEC-043-ownership-substrate-selection.md)
decided the *rule* — the instance-ownership marker binds to a **selectable
substrate** ("substrate-where-available"): the `instance:N` label
([project-management:DEC-035](../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md))
where labels are creatable, an append-only comment log (source of truth) plus a
derived, regenerable owner-mirror in the issue description where they are not; the
selector lives in instance-ownership's own schema home (not `substrate-map.yaml`),
default `comment`. This ADR records the *comment-substrate contract* DEC-043 named
as its ADR follow-up (DEC-043 point 5) — the **fourth sibling** to
[ADR-026](ADR-026-substrate-map-read-path-contract.md) (the label
read-path/sole-constructor seam),
[ADR-031](ADR-031-substrate-write-path-contract.md) (the field/milestone
write-path sole-constructor), and
[ADR-035](ADR-035-containment-resolution-contract.md) (the containment
read-seam + write-constructor): **how** ownership resolves on read and constructs
on write in `comment` mode, and the one invariant each side must never violate. It
pins the contract, not the selector schema, the comment-stamp format, or the
mirror-region UX, which DEC-043 and the audit-log facility's DEC-044 carry.

**The contract, in one breath:** instance ownership in `comment` mode has **one
read seam** — a single fold point answering "who owns this issue now, and via
which substrate," folding the per-instance append-only event log to current
ownership, with **comment-log-wins as a seam invariant** over a lingering label —
and **one write construction point per side** (the ownership-event comment write;
the description-mirror full-overwrite regenerator), each under the grep/AST
sole-constructor guard the sibling ADRs established. No consumer re-derives
ownership by scanning comments itself (ADR-026's one-reader discipline, applied to
the ownership axis); no script string-builds an ownership-event comment or a
mirror region inline (ADR-031/ADR-035's sole-constructor discipline, applied to a
fourth substrate).

**The load-bearing invariants — one read seam with comment-log-wins, one write
constructor per side, the mirror derived.** Three parts, structural only together:
(i) **every ownership consumer resolves the current owner only by asking the
seam** — the clash guard (DEC-035 point 6), the signed listing (DEC-035 point 7), and the
description-mirror renderer all route through the fold, and in a project with a
topology the pool a worker takes from, the check before writing and the seat's release do too;
none re-scans comments or reads the mirror directly, so there is one place ownership
is resolved and one place authenticity
(`author.login`) and comment-log-wins are enforced; (ii) **the seam folds the
append-only log to current ownership and, over a mixed repo, comment-log-wins** —
a claim followed by a handoff followed by an abandon folds to the last authentic
event's owner (or unclaimed), and where a lingering `instance:N` label coexists
with a comment-log marker the fold resolves to the comment-log owner, the label
treated as residual; this is DEC-035's lowest-wins tie-break preserved atop
per-object-atomic comment writes, lifted to a **mixed-mode reconciliation**
invariant (a repo forward-switched from label to comment may hold both; the seam
resolves it deterministically); and (iii) **each write is constructed in exactly
one point** — the ownership-event comment via one writer, the description mirror
via one full-overwrite regenerator (**never an append**) — under one grep/AST
guard, the same discipline ADR-031/ADR-035 hold for their substrates. The
description mirror is a **derived view** whose regeneration spine is the comment
log: a stray human edit or a racing write is regenerated by the seam, so no
ownership record is lost.

**In a project with a topology of seats**
([project-management:DEC-059](../../../.pkit/capabilities/project-management/decisions/DEC-059-topology-of-seats.md)),
the fold takes four inputs from its caller: the time of reading, which is GitHub's,
the limit after which a claim lapses, the Task's state in the lifecycle and the
seats' holders. So the ownership seam reads no other seam. A claim names its seat,
the seat's number and the clone's key, counts only while that clone holds that seat,
and on a Task In Progress lapses once its work has not renewed it within the limit.
A claim the seam cannot judge, for a log or a seat it could not read, is never
treated as free (point 7). The ownership-event comment is built by the audit-log
facility's builder, which also builds every event of a state issue (point 3).

## Context

DEC-043 settled the ownership substrate-selection rule and explicitly deferred the
formal contract to a sibling ADR: *"The write path is a sole-constructor pinned by
a sibling ADR … one read seam, one construction point, a grep/AST guard,
failure-posture-neutral. The ADR is authored by the architect once this record
settles."* (DEC-043 point 5, and its Implications naming "a fourth sibling ADR" that
pins the comment-log read seam, the description-mirror sole-constructor, the
grep/AST guard, and mixed-mode precedence). This record is that ADR.

The comment-log substrate is a **fourth substrate**, distinct from the label axis
ADR-026 covers, the Projects-v2 field-value / milestone writes ADR-031 covers, and
the containment edge ADR-035 covers. It is a *different operation* again — reading
an issue's whole comment log and folding hidden-stamped event comments, writing
a new ownership-event comment, and full-overwriting a derived region of the issue
*body* — so it lives in its own module with its own sole-constructor guard, the
same discipline as the three prior seams, **not a widening of any of them.**
ADR-026's label invariant, ADR-031's field/milestone invariant, and ADR-035's
containment invariant all stay scoped to their own substrates and untouched.

[project-management:DEC-035](../../../.pkit/capabilities/project-management/decisions/DEC-035-instance-ownership.md)
is where the ownership semantics originate — the `(assignee, instance:N)` owner,
the clash guard that refuses an ordinary verb on another instance's work
(`[validation-severity:bypassable-with-audit]` per
[project-management:DEC-014](../../../.pkit/capabilities/project-management/decisions/DEC-014-validation-severity-model.md)),
and the same-instant lowest-wins tie-break both clones compute identically. DEC-043
refines DEC-035 to substrate-*where-available* and adds the comment substrate,
preserving those semantics atop per-object-atomic comment writes. This ADR pins how
that rule resolves at the seam in `comment` mode.

**The realization surface.** The ownership read seam and its two constructors are
realized in a module of their own. The fold resolves an issue's owner from the
comments and labels its caller passes, and the constructors build the event comment
and the mirror body. The seam offers the one reader of a whole comment log, paged to
its end, which the state-issue seam shares. The audit-log facility's builder builds
and parses each event, and a guard test keeps every ownership stamp inside the seam
and that builder.

The lifecycle commands resolve ownership through the fold. `create-issue` claims
what it files for its own account, except from a planner's seat, and `start-work`
claims an issue no instance owns. A claim re-reads the issue after it writes its
marker, and withdraws its claim where a lower instance claimed in the same
instant. `close-issue` releases the issue's owners as it closes the issue, and
`done-work` releases through the `close-issue --mode pr-merge` it runs.

The clash guard runs in `start-work`, `review-work`, `done-work`, `promote-issue`,
`edit-issue` and `move-issue`. It treats a claim that does not count as no claim,
and one the fold cannot judge as one that counts. In `comment` mode, a claim, a
back-off and a release regenerate the mirror from the fold, by full overwrite. The
mirror is written only where the body changes, and a failed write is a warning.

The pool a worker takes from is read by `next-task`: DEC-059's shared pool, or the
seat's pools where the topology declares pools of workers
([project-management:DEC-061](../../../.pkit/capabilities/project-management/decisions/DEC-061-pools-of-workers.md)).
`next-task` takes over a Task In Progress whose claim
does not count, and none whose claim the fold cannot judge. For the seat's release,
`seats` judges each Task in Review against the seats' holders, and names each Task a
released seat left. It reads each log whole through the shared reader, while the
other commands fold the comments a `gh issue view` read returns.

Of point 7's inputs, the fold takes the seats' holders, and no time of reading, limit
or state, so it judges no lapse. It returns the owners whose claims count, and each
claim that does not count, for no seat named or its seat released. It leaves
unjudged a claim whose seat is unread or missing from the holders. A failed read of
the issue is its caller's: the guard refuses, the claim and the release fail, and the
pool skips the Task.

Point 5's writers build an argv or a body and report no outcome. Their caller reads
success from `gh`'s exit and a lost race from the re-read fold, and no path reports
`CLOBBERED`. `handoff-issue` posts no ownership event, and no durability check or
reconcile report exists. The check before writing is the seat's confirmation and the
clash guard, and it parks no work.

The signed listing is not built. No function reads the mirror back, and every fold
reads comments. The contract binds each participant below, built or not:

1. **The ownership fold** (a single ownership-substrate `_lib` seam) — the one read
   point. Reads the mirror for a listing, at one call (DEC-043 Implications "read
   cost stays one call"), and the issue's whole comment log, paged to its end,
   whenever it folds one, so a fold never reads a log cut short. Keeps only comments carrying
   the hidden ownership stamp **authored by the expected assignee account**
   (`author.login` authenticity, DEC-043 point 3), folds the append-only claim / handoff
   / abandon / release sequence to current ownership, and — over a mixed repo —
   applies comment-log-wins against any lingering `instance:N` label. In a project
   with a topology, it takes the seats' holders, the time of reading, the limit and
   the Task's state from its caller, and reads the mirror where point 7 lets the
   mirror stand in. **The sole resolver — consumers route through it.**
2. **The clash guard** (DEC-035 point 6) — the ordinary-verb refusal and the same-instant
   lowest-wins back-off. **Resolves current ownership through the fold.**
3. **The signed listing** (DEC-035 point 7) — `mine` / `other instance` / `unclaimed`.
   **Resolves through the fold.**
4. **The description-mirror renderer** — folds the log and full-overwrites the
   derived owner-mirror region in the issue body. **Resolves through the fold; is
   itself the sole constructor of the mirror region (site 6).**
5. **The ownership-event comment writer** — the one point that posts a claim /
   handoff / abandon / release comment (hidden stamp + human text), which the
   audit-log facility's builder builds (point 3). Every
   ownership mutation (`create-issue` claim, `start-work` commons-claim,
   `handoff-issue` push/pull, terminal release) obtains its event write **only by
   asking this writer**. **The sole poster of the ownership-event comment.**
6. **The description-mirror regenerator** — the one construction point that writes
   the derived owner-mirror region by **full overwrite** from the folded log.
   **The sole constructor of the mirror region; never an append.**
7. **The pool, the check before writing and the seat's release** (DEC-059
   points 5, 7 and 9, DEC-061 point 5) — in a project with a topology, each judges a
   Task's claim through the fold, passing the seats' holders, the time of reading, the
   limit and the Task's state (point 7). The pool is the one a worker takes from:
   DEC-059's shared pool, or the seat's pools where the topology declares pools of
   workers. **Resolve through the fold.**

The architecturally-significant pins, each carrying an alternative DEC-043 already
rejected or this ADR holds against:

1. **One ownership read seam** (consumers ask the fold) vs. each consumer
   re-scanning comments itself — the re-derivation ADR-026's one-reader discipline
   forbids, applied to the ownership axis; it would give authenticity-filtering and
   the fold N places to drift.
2. **Comment-log-wins as a seam invariant** over a mixed repo (lingering label +
   comment marker) vs. a per-consumer tie-break that could disagree across the
   guard, the listing, and the mirror — analogous to ADR-035's native-wins lifted
   to mixed-mode reconciliation.
3. **One construction point per side** (event comment; mirror region) vs. inline
   comment/body construction at each ownership-mutation site — the scatter
   ADR-031/ADR-035 converge for their substrates.
4. **Mirror render is a derived full-overwrite** (comment log the spine) vs. an
   authoritative body region (DEC-043 rejected the latter as a whole-object
   read-modify-write with no CAS; recorded here as a write-construction invariant,
   not re-litigated).
5. **The fold takes its inputs from its caller** in a project with a topology —
   the seats' holders, the time of reading, the limit and the Task's state — vs. a
   fold that reads the seats' state issues, the topology or a clock itself, which
   would bind the ownership seam to other seams and judge one run's Tasks at
   several instants.

## Decision

**In plain terms:** ownership consumers never scan comments themselves, and ask
*one seam* "who owns this issue now?" The seam folds the append-only event
log — trusting only comments the expected account authored — to current ownership,
and over a repo that still carries an old `instance:N` label resolves
comment-log-wins. Every ownership *write* — the event comment, the description
mirror — is constructed in *one place*, the mirror always by full overwrite, never
appended. The mirror is a derived view; the comment log is the truth. In a project
with a topology, the caller passes in what decides whether a claim counts, and the
seam reads no other seam.

### 1. One ownership read seam — resolution lives in exactly one auditable place

"Who owns this issue now, and via which substrate?" is answered by a **single fold
seam**, not re-derived per consumer. The clash guard (DEC-035 point 6), the signed
listing (DEC-035 point 7), and the description-mirror renderer all resolve through it;
none re-scans comments directly. In a project with a topology, the pool a worker
takes from (DEC-059's shared pool, or the seat's pools where the topology declares
pools of workers, DEC-061), the check before writing and the seat's release resolve
through it too (point 7). A
listing reads each issue's mirror through the seam (point 4), so its cost stays one
call (DEC-043 Implications). Whenever the seam folds a log, it reads the whole log,
paged to its end. The fold itself is a function of that log, any lingering label
and, in a project with a topology, the inputs point 7 names. It returns the resolved
current owner, the substrate it came from, and the authenticated event history.

This is ADR-026's one-reader discipline applied to the ownership axis: the
indirection — comment scan, `author.login` authenticity filter (DEC-043 point 3),
append-only fold, comment-log-wins dedup — sits in one place where it can be
audited, tested, and reasoned about as a unit, and no second consumer re-derives
what one seam already resolves. A consumer re-scanning comments itself would (a)
duplicate the authenticity filter and the fold, and (b) give comment-log-wins and
the authenticity rule N places to drift instead of one to audit — exactly the
scatter the single seam exists to prevent. The seam owns the authenticity filter
too, so a consumer routing through it never trusts a forged marker.

### 2. Comment-log-wins as a seam invariant — and mixed-mode reconciliation

The seam folds the append-only log to current ownership, and over a mixed repo
resolves by a single rule: *a comment-log marker present for an issue is
authoritative; a coexisting lingering `instance:N` label is residual and does not
win.* This preserves DEC-035's ownership semantics under DEC-043's forward switch:

- **The fold is over an append-only sequence.** Claim, then handoff to another
  instance, then abandon, then a fresh claim — the seam folds to the *last
  authentic event's* owner (or unclaimed after an abandon/release), so history is
  preserved (DEC-043 point 3) while a single current owner resolves. The same-instant
  clash (DEC-035 point 6) holds unchanged: two clones each post their own event
  (per-object-atomic, no whole-object race), the re-read sees both, the
  higher-numbered instance backs off — lowest-wins computed identically by both
  clones from the folded log, exactly as it was from the labels.
- **Authenticity rides `author.login`.** A marker is trusted only if authored by the
  expected assignee account (DEC-043 point 3) — stronger than the label substrate, where
  a label carries no actor. The seam is the one place this filter runs.
- **A repo may hold both substrates.** DEC-043's selector defaults to `comment`; a
  repo forward-switched from `label` (DEC-035's original mechanism) leaves lingering
  `instance:N` labels alongside new comment-log markers. **The seam resolves
  comment-log-wins** — the folded comment-log owner is authoritative, the lingering
  label is residual (to be stripped on the next ownership mutation, the same way
  DEC-035 point 4 strips on terminal transitions). This is ADR-035's native-wins
  instinct at a new substrate boundary: the newer/authoritative substrate wins over
  the residual one, enforced **once, at the seam, over the union** — so the guard,
  the listing, and the mirror never disagree about a mixed repo.

State the invariant precisely: **comment-log-wins is enforced once, at the seam,
over the union of the comment log and any lingering label — so a mixed-substrate
repo resolves deterministically regardless of which consumer asks.** (The symmetric
case — selector `label` with a stray comment marker — resolves to the label per the
selector; that is not the motivating forward switch and the label mechanism stands
untouched per DEC-035. The seam reads per the selector; comment-log-wins is the
tie-break *within* the `comment`-mode union that the forward switch actually
produces.)

In a project with a topology, point 7 says when a claim counts, and the fold resolves
among the claims that count.

### 7. In a project with a topology, the fold takes its inputs from its caller

In a project with a topology of seats, every event that makes an owner names the
owner's seat, the seat's number and the clone's key (DEC-059 point 9). The fold then
takes four more inputs from its caller, and reads no other seam:

- **The seats' holders:** for each seat, the clone that holds it, by its account and
  key, or free, or unread. The caller reads them from each seat's state issue
  ([project-management:DEC-058](../../../.pkit/capabilities/project-management/decisions/DEC-058-state-issues.md),
  DEC-059 point 3). A command on one Task reads the seats its claims name, which the
  seam gives from the Task's log, and the pool reads every seat.
- **The time of reading:** GitHub's time, taken from GitHub's answer to the run's
  first read, never a clock of the clone's. A run that cannot get it leaves each
  claim on a Task In Progress unjudged.
- **The limit** after which a claim lapses, which the topology sets (DEC-059 point
  2).
- **The issue's state in the lifecycle,** which the caller's read of the issue
  already holds.

A run is one invocation of one command, from its start to its exit. It reads its own
seat, the holders it needs and the time of reading at its start, and reads them
again after it waits on something outside it, such as a check or a person's answer.
A command on one Task reads the seats that Task's claims name right after it reads
the Task's log. So one run judges every claim against one state of the seats, at
one instant.

When a claim counts:

- **Its seat.** A claim counts only while the clone it names holds the seat it
  names, by the holders the caller passed. A claim that names no seat, made under a
  typed number before the topology, does not count (DEC-059 point 9).
- **A handoff to a seat** names the target seat, its number and the key of its
  holder in the holders the caller passed. It counts for the target as a claim
  does.
- **Its lapse.** A claim on a Task In Progress counts until the limit has passed
  since the owner's last claim, handoff or renewal, judged at the time of reading.
  Only a renewal that names the claim's seat and key renews it. A claim on an issue
  in any state other than In Progress does not lapse. Nor does the claim on a Task
  whose build waits, on a question or on its hand-back, which the caller passes as
  it passes the Task's state, read from the build command's events on the Task:
  its ending, its resume and its hand-back (refinement per
  [ADR-073](ADR-073-builder-runs.md) points 5, 8 and 9).
- **A Task moved back to In Progress** by a command of the capability gets a
  renewal from that command (DEC-059 point 9), so the limit runs from the move. A
  move made outside the capability, such as by a board's automation, renews
  nothing, and the claim may lapse at once.
- **Time and order.** The fold orders the events by comment id, and reads each
  event's time from GitHub's record of the comment's creation, never from a time its
  stamp holds. So the clocks of the sandboxes decide nothing (DEC-059 point 9).

What it returns:

- **The owners whose claims count,** as point 2 resolves them. A claim that does not
  count is no claim, so the tie-break by the lower number runs among the claims that
  count (DEC-035 point 6).
- **Each claim that does not count,** with its reason: lapsed, its seat released,
  or no seat named.
- **Each claim it cannot judge,** with its reason: a log it could not read whole, a
  seat it names that is unread or missing from the holders, a state it could not
  read, or no time of reading. No consumer treats an unjudged claim as free (point
  5).

What it reads:

- **A Task In Progress,** whose claim alone lapses: the seam folds its whole log
  (point 1).
- **Any other issue:** the seam may read the issue's mirror in place of its log
  (point 4). It judges the mirror's seat and key against the holders itself, and
  gives the result a fold gives, with the mirror named as its source.
- **What a mirror read allows:** a consumer may pass over an issue whose claim the
  mirror shows counting, and a listing may show a person what the mirror reads. Before
  a consumer offers an issue as free, treats it as free or acts on it as its owner,
  the seam folds the whole log. A missing or garbled mirror never makes an issue free
  without that fold.
- **The claim path's re-read** folds the whole log, whatever the Task's state
  (DEC-035 point 6).

### 3. One write construction point per side — sole-constructor

Each ownership write has **exactly one construction point**, and every write routes
through it — ADR-031/ADR-035's sole-constructor discipline applied to a fourth
substrate:

- **The ownership-event comment** (claim / handoff / abandon / release, and in a
  project with a topology the renewal of DEC-059 point 9; hidden stamp + human text)
  is built by one builder, the audit-log facility's
  ([project-management:DEC-044](../../../.pkit/capabilities/project-management/decisions/DEC-044-audit-log-facility.md)),
  and posted by one writer, this seam's. The same builder builds every event of a
  state issue (DEC-058 point 4), and parses a comment back into its event, so the
  stamp's grammar and its version have one owner. Each seam names its own event
  types and payload, and neither builds an event's stamp itself. A mutating script obtains an
  ownership event **only by asking the writer** — `create-issue`'s claim-at-birth (DEC-035
  point 3), `start-work`'s commons-claim, `handoff-issue`'s push/pull/recursive modes
  (DEC-035 point 4), and the terminal release all reuse the same construction point;
  none string-builds the stamped comment inline. The event log aligns with, and
  does not duplicate, the handoff audit comment
  [project-management:DEC-026](../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)
  already posts (DEC-043 point 3).
- **The description-mirror region** is constructed in one regenerator that writes
  the region by **full overwrite** from the folded log — never a second writer, and
  **never an append** (point 4).

This is ADR-031/ADR-035's instinct at a new substrate boundary: a single auditable
construction point makes "no script string-builds an ownership write inline" a
*structural* property (there is no other way to build the write) rather than a
*remembered* one. The ownership writes are distinct operations from the three prior
seams' (a stamped `gh issue comment` and a body-region overwrite, not a label, a
`gh project item-edit` / `--milestone`, or a `gh api …/sub_issues`), so they get
**their own** construction points and **their own** grep/AST guard — **not a
widening of ADR-026/ADR-031/ADR-035's covered sets.** All three prior invariants
stay scoped to their own substrates.

### 4. The description mirror is derived full-overwrite, never append, never authoritative

The description mirror is a **derived view the read seam regenerates by full
overwrite** from the folded log — the comment log is its regeneration spine
(DEC-043 point 4). It is therefore safe to full-overwrite: if a human edits or deletes
the region, or a write races, the seam regenerates it from the log and **no
ownership record is lost**, because the mirror was never the truth. The one
construction point (point 3) writes by **overwrite**, never by append — a
per-instance append to a shared body region would be the whole-object
read-modify-write with no compare-and-set that DEC-043 rejected for an
authoritative body substrate (concurrent claims clobber; lowest-wins degrades to
last-writer-wins).

This is the [project-management:DEC-039](../../../.pkit/capabilities/project-management/decisions/DEC-039-containment-substrate-selection.md)
D4 / ADR-035 point 4 pattern — a generated, regenerable view whose truth lives
elsewhere — with the roles swapped from ADR-035: there the *comments* are the
render-on-demand view and the native panel / child-side ref is the spine; here the
*comments* are authoritative and the *body region* is the view. The direction
differs; the invariant (derived view, single-source full-overwrite, spine
elsewhere) is the same.

The seam reads the mirror back through one function of its own, and no consumer
parses it. In a project with a topology, the mirror shows the owner as of its last
rewrite, with the claim's seat, the seat's number and the clone's key. It cannot
stand for the fold of a Task In Progress, whose claim lapses by the time of reading,
so the guard and the pool ask the seam to fold that Task's log (point 7). A
seat's release writes nothing to the issues its clone claimed (DEC-059 point 5), so
the seam judges the mirror's seat and key against the seats' holders before the
mirror stands in for any other issue. The mirror carries no author, so it only ever
lets a consumer pass over an issue, never treat one as free.

### 5. Failure-posture neutrality — the constructors report, the caller decides

Both construction points and the fold are **failure-posture-neutral**, in the same
spirit as ADR-031 point 6 and ADR-035 point 3. They construct/execute/fold and
report a neutral outcome; **each caller imposes its own posture**:

- **The ownership-event comment writer** reports `WROTE` / `FAILED`. The
  **claim path** re-reads after writing (DEC-035 point 6) and, on seeing a
  lower-numbered instance's event, reads `RACED-LOST` from the fold and **backs
  off** (posts an abandon event, notifies); a **handoff** treats `WROTE` as success
  and moves on; a **durability-check** path treats `FAILED` as a retryable
  substrate error. The writer takes no view on which — the posture is the caller's.
- **The description-mirror regenerator** reports `WROTE` / `CLOBBERED` (the region
  had drifted — a human edit, a deletion, or a racing write — and was regenerated
  by full overwrite) / `FAILED`. The **routine render** treats `CLOBBERED` as
  *expected and benign* (the mirror is derived; regeneration is its whole job) and
  does not alarm; a **reconcile/durability report** may surface the `CLOBBERED`
  count as drift observed-and-healed. Same construction, different posture per
  caller.
- **The fold, in a project with a topology,** reports each claim that does not
  count, and each claim it cannot judge, with its reason (point 7). On a claim that
  does not count, the **check before writing** parks its session's work (DEC-059
  point 9), the **pool** offers the Task to a worker, and the **clash guard**
  does not refuse (DEC-035 point 6). No consumer treats an unjudged claim as free:
  the pool takes no such Task over, the check before writing does not write, and
  the guard refuses as on a claim that counts. The fold takes no view on which.

This is what lets the claim / back-off / handoff / reconcile callers coexist behind
one set of constructors without any inheriting another's posture — construction and
fold are one concern (the seam's), failure-handling is another (the caller's), and
they live at different layers. If a constructor baked in a posture, the back-off
path would inherit the claim path's, or the reconcile report would inherit the
routine render's — the exact miscoupling neutrality prevents.

### 6. Realm-blindness — the seam feeds only the pm-layer guard, never the fold

The ownership fold is a **pm-domain read** with **pm-domain consumers only** — the
clash guard, the signed listing, the mirror renderer, and in a project with a
topology the pool, the check before writing and the seat's release. Instance
ownership remains, per DEC-035 point 8 and DEC-043 point 6, **never an input to a gate, a
transition, or the cascade fold**
([project-management:DEC-034](../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md),
COR-037's process-cascade). This is the deliberate *inverse* of ADR-035, where the
DEC-034 closure-fold child-walk is one of the containment seam's consumers: there,
membership is engine-relevant and the fold reads it through the seam; here,
ownership is **not** engine-relevant and the cascade fold must **not** read it. The
ownership seam's consumer set is closed to the pm layer; wiring it into the engine
fold would cross the content-free boundary COR-037 holds and require its own
authorisation (DEC-035 Implications). The engine and its cascade predicates stay
realm-blind.

### Boundaries — what this contract is NOT

- **Not the selector schema.** The `label | comment` selector (default `comment`)
  belongs to instance-ownership's own schema home, explicitly **not** a slot in
  `substrate-map.yaml` (DEC-043 point 2). So an ownership-only opt-in does not trip
  DEC-036's emergent activation. This ADR pins the resolution + construction
  contract, not the selector field.
- **Not the comment-stamp or mirror-region format.** The hidden-stamp syntax and
  the mirror region's rendered shape are carried by the shared audit-log facility's
  own DEC ([project-management:DEC-044-audit-log-facility], with DEC-043 Implications:
  "the ownership event log is that facility specialised"). This ADR pins only that
  the event write and the mirror render each have one constructor and that the
  mirror is overwrite-not-append.
- **Not DEC-009's rule for derived regions.** The description-mirror region is
  capability-owned, do-not-edit, **derived** body content, the third class
  [project-management:DEC-009](../../../.pkit/capabilities/project-management/decisions/DEC-009-living-documents.md)
  models. DEC-009's wording and scope rules govern body content a person or the PM
  authors, and neither applies to a derived region. A human edit to the region is
  not a gated scope edit, and the next render overwrites it safely. This ADR cites
  that class, and DEC-009 owns validate-body's rule for it.
- **Not a DEC-035 supersession.** DEC-035's label mechanism, the
  `(assignee, instance:N)` owner, and the clash-guard semantics all stand. DEC-043
  refines DEC-035 to substrate-*where-available*, and DEC-035 point 2 carries the
  refinement pointer to DEC-043. This ADR pins how the comment substrate resolves.
  Comment-log-wins is DEC-035's lowest-wins tie-break preserved atop per-object
  atomic writes and lifted to a mixed-mode invariant, not a replacement.
- **Not auto-selection.** The selector is a manual operator declaration defaulting
  to `comment` (DEC-043 point 2); this ADR pins no auto-detection of label-creatability.
  The seam resolves comment-log-wins over the mixed union the forward switch
  produces regardless.
- **Not a label / field / containment contract change.** ADR-026's label invariant,
  ADR-031's field/milestone invariant, and ADR-035's containment invariant stay
  scoped to their own substrates. This is a fourth substrate with its own seam,
  its own two constructors, and its own guard.
- **Not the state issues' seam.** A state issue's reads, fold and writes are a seam
  of their own (DEC-058 Implications), which shares the event builder with this one
  (point 3). This seam never reads a state issue, the topology or a clock. Its
  caller reads them and passes what point 7 names.

## Rationale

**Why one read seam, not per-consumer comment scans.** Resolving the current owner
is a cross-cutting concern — in a project with no topology, three consumers need it
(clash guard, signed listing, mirror renderer), and a topology adds three more — and
the *same* logic (authenticity filter + append-only fold +
comment-log-wins dedup) must behave identically across all of them. A concern that
must be uniform across many consumers belongs at one boundary, not copied into
each. Three consumers each scanning comments would give the `author.login`
authenticity rule and comment-log-wins three places to drift and triplicate the
fold — the exact scatter ADR-026's one-reader discipline exists to prevent, here on
the ownership axis. One seam is the COR-007 "extract the shared shape" move applied
to ownership resolution; the third consumer arriving (the mirror renderer, after
the guard and the listing) earns the extraction under COR-007's recurrence test
rather than speculative generality.

**Why comment-log-wins as a seam invariant, and why mixed-mode matters.** DEC-043's
selector is a forward switch, so a real repo can carry both a lingering `instance:N`
label and a comment-log marker at once — the switch is not atomic, and a
label-mode repo that adopts the comment default leaves its old labels in place.
If the tie-break were per-consumer, the clash guard could refuse on the stale label
while the signed listing reads the comment-log owner and the mirror renders a third
answer, during the mixed window. Enforcing comment-log-wins **once at the seam over
the union** makes the mixed repo resolve deterministically for every consumer — the
property that makes the forward switch safe. Comment-log-wins (not label-wins) is
the right direction because the comment log is the authenticity-bearing,
per-object-atomic, history-preserving substrate DEC-043 chose as source of truth;
the label is the residual DEC-035 artifact the switch is leaving behind.

**Why the fold takes its inputs from its caller.** A fold that read the seats' state
issues itself would make the ownership seam call another seam, and each Task's fold
would read every seat again. The caller reads the holders once in a run and passes
them to every fold. A fold that read a clock would judge each Task of one run at a
different instant, and its tests would need a fake clock. With the four inputs
passed in, the fold is a function of what it is given, testable with no GitHub and
no configuration, while the seam's read of the log stays the one part that needs
GitHub — the one-seam discipline of point 1, kept for every input.

**Why the time of reading is GitHub's.** A lapse compares the time of reading with
the time GitHub records for the owner's last renewal. A clone's clock that runs fast
would see live claims lapse, and the pool would take live Tasks over. Taking
both times from GitHub keeps DEC-059 point 9's rule that the sandboxes' clocks
decide nothing, at no extra call.

**Why an unread seat leaves a claim unjudged.** Reading an unread seat as free would
turn every claim naming it into a released one, so one failed read would hand a
live clone's Tasks to the pool. An unjudged claim costs a retry, never a takeover.

**Why the mirror only lets a consumer pass over an issue.** DEC-043 keeps a
listing's cost at one call by reading the mirror, and DEC-059 makes the mirror unfit
to stand for a fold that lapses. A mirror that names a counting claim can only make
a consumer leave an owned issue alone, which is safe whatever made it stale. Acting
on an issue, or treating it as free, rests on the folded log alone.

**Why one event builder for two seams.** An ownership event and a state issue's
event are the same shape of comment, a hidden stamp and a line a person reads.
DEC-044 makes one builder for every such comment, so the stamp's grammar and its
version have one owner while each seam keeps a fold of its own.

**Why one construction point per side.** "Construct the ownership write in exactly
one place" is the same architectural property ADR-031 made load-bearing for
field/milestone writes and ADR-035 for containment: a single auditable point makes
the invariant *structural* rather than *remembered*. With `create-issue`,
`start-work`, `handoff-issue`'s three modes, and terminal release all writing
ownership events, and every read regenerating the mirror, the un-converged world
would have an event comment buildable at every mutation site and a mirror writable
at every render — N places for the guard to fail to cover, N for a future author to
mis-stamp the comment or mis-overwrite the region. One constructor per side and one
guard collapse that. Giving ownership its *own* construction points and guard
(rather than widening a prior seam) keeps each substrate's invariant precise: an
ownership write is a stamped comment / a body-region overwrite, not any of the
three prior substrates' operations, and folding it into a prior seam would overload
that seam with an operation its drivers never invoke.

**Why the mirror is derived full-overwrite, not an authoritative or appended body
region.** DEC-043 pressure-tested and rejected an authoritative body region: a
whole-object read-modify-write with no compare-and-set, so concurrent claims
clobber and lowest-wins degrades to last-writer-wins — the silent double-work the
guard exists to prevent. A per-instance *append* to a shared region has the same
whole-object race. The only thing the body region should add beyond the comment log
is at-a-glance visibility of the current owner (DEC-043 Rationale) — and rendering
it on demand by full overwrite from the log delivers exactly that with none of the
concurrency failure modes, precisely *because* it is not the source of truth. This
is DEC-039 D4 / ADR-035 point 4's separation of the visibility goal from the
storage decision; only visibility is wanted.

**Why failure-posture neutrality.** The callers have genuinely different correct
postures — the claim path must back off on `RACED-LOST` (DEC-035 point 6), the handoff
path must not, the routine render must treat a `CLOBBERED` mirror as benign, and a
reconcile report may surface it as healed drift. Baking any one posture into a
constructor would force another caller to wear a posture its path rejects — a
claim writer that swallowed the race would break lowest-wins; a mirror renderer
that alarmed on every regeneration would make the derived region look broken.
Neutrality keeps construction/fold (the seam's job) orthogonal to failure-handling
(the caller's job), the same separation ADR-031 and ADR-035 draw for their
substrates.

**Why realm-blindness, stated as a non-consumer.** ADR-035's containment seam feeds
the cascade fold because membership *is* engine state; ownership is deliberately
*not* (DEC-035 point 8, COR-037's content-free substrate). Naming the engine fold as an
explicit **non-consumer** of the ownership seam is what keeps the boundary from
eroding the way a convenient "close only my realm's children" feature would erode
it — that would feed ownership into the fold and cross the content-free boundary,
requiring its own authorisation. The pm-layer-only consumer set is the boundary,
enforced by the seam having no engine-side caller.

### Alternatives considered

- **Each consumer re-scans comments itself** (no read seam). Rejected — triplicates
  the `author.login` authenticity filter and the append-only fold, gives
  comment-log-wins three places to drift, and lets the guard, listing, and mirror
  disagree about a mixed repo. The one-reader discipline (ADR-026) on the ownership
  axis is the fix.
- **Comment-log-wins as a per-consumer tie-break** rather than a seam invariant.
  Rejected — during the forward-switch mixed window the guard could refuse on the
  stale label while the listing and mirror read the comment-log owner. Enforcing it
  once at the seam over the union resolves the repo deterministically for every
  consumer.
- **Label-wins over the comment log** in mixed mode. Rejected — the label is the
  residual substrate the forward switch is leaving; the comment log is the
  authenticity-bearing, per-object-atomic, history-preserving source of truth
  DEC-043 chose. Comment-log-wins is the only direction consistent with the switch.
- **Authoritative body region as the source of truth** (no comment log). Rejected
  by DEC-043 — whole-object read-modify-write with no CAS; concurrent claims clobber
  and lowest-wins degrades to last-writer-wins. Kept only as a *derived* mirror
  (point 4).
- **Per-instance append to the mirror region** instead of full overwrite. Rejected
  — the same whole-object race as the authoritative region, on every claim.
  Full-overwrite of a derived region regenerated from the log carries no such race.
- **Inline event-comment / mirror construction at each ownership-mutation site** (no
  sole-constructor). Rejected — re-grows the scatter ADR-031/ADR-035 converge for
  their substrates; gives the invariant N places to drift and the guard N shapes to
  chase.
- **Widen a prior seam** (ADR-031's write seam or ADR-035's containment seam) to
  cover ownership. Rejected — an ownership write is a distinct operation (stamped
  comment / body-region overwrite); folding it in overloads that seam with an
  operation its drivers never invoke and forces its guard to allow a fourth shape.
  Ownership gets its own constructors and guard; the prior invariants stay scoped.
- **Feed the ownership fold into the cascade closure fold** (a "close only my
  realm's children" convenience). Rejected — crosses the content-free engine
  boundary COR-037 holds (DEC-035 point 8); if ever wanted it needs its own
  authorisation, not a quiet widening of this seam's consumer set.
- **The fold reads the seats' state issues itself.** Rejected — it binds the
  ownership seam to another seam, and reads every seat once for each Task.
- **The fold reads a clock.** Rejected — one run would judge its Tasks at different
  instants, and every test would need a fake clock.
- **The time of reading from the clone's clock.** Rejected — a clock that runs fast
  would lapse live claims, against DEC-059 point 9.
- **An unread seat passed as free.** Rejected — one failed read would release every
  claim naming the seat.
- **Each consumer judges the mirror against the holders.** Rejected — a second
  resolver in every consumer, the scatter point 1 forbids.
- **The mirror stands for the fold of a Task In Progress.** Rejected — the claim
  lapses by the time of reading, which the mirror's last rewrite cannot know.
- **The stamp's time orders the fold in a project with a topology.** Rejected — a
  clone writes that time, and the clocks of the sandboxes would decide a lapse
  (DEC-059 point 9).

## Implications

- **One ownership read seam** (an ownership-substrate `_lib` fold) that the clash
  guard (DEC-035 point 6), the signed listing (DEC-035 point 7), and the description-mirror
  renderer resolve through, and in a project with a topology the pool, the
  check before writing and the seat's release; no consumer re-scans comments or
  parses the mirror directly. Reads the mirror for a listing, and the issue's whole
  comment log, paged to its end, whenever it folds one (DEC-043 Implications),
  filters by `author.login` authenticity (DEC-043 point 3), and folds the append-only
  claim/handoff/abandon/release sequence to current ownership. The lifecycle commands
  resolve through it, as do the pool in `next-task` and, for the seat's
  release, `seats`. The signed listing is not built, no function reads the mirror back, and
  only `seats` reads a log through the shared reader.
- **Comment-log-wins is a seam invariant over the union of both substrates** — a
  comment-log marker is authoritative; a coexisting lingering `instance:N` label is
  residual and does not win, and is stripped on the next ownership mutation (DEC-035
  point 4). This makes a **forward-switched (label→comment) repo** resolve
  deterministically for every consumer. It is DEC-035's lowest-wins tie-break
  preserved atop per-object-atomic comment writes and lifted to a mixed-mode
  reconciliation invariant.
- **One write construction point per side, under one grep/AST guard** — the
  ownership-event comment writer (claim/handoff/abandon/release, hidden stamp +
  human text, the only one `create-issue`, `start-work`, `handoff-issue` and the
  terminal release may use) and the description-mirror regenerator (full overwrite
  from the folded log). The guard is the two-half shape ADR-031/ADR-035 hold: (a) a **construction
  test** — the writers construct/execute the covered writes and the ownership
  mutation sites obtain their write *from* them; **and** (b) a **grep/AST scan-all**
  — no script string-builds a stamped ownership-event comment or a mirror-region
  overwrite inline except the two constructors. Its own module and its own guard —
  **not a widening of ADR-026 / ADR-031 / ADR-035's covered sets.**
- **The description mirror is a derived, single-source full-overwrite, never an
  append, never authoritative** (DEC-043 point 4) — the comment log is its regeneration
  spine, so a stray human edit, deletion, or racing write is regenerated with no
  ownership record lost. This is DEC-039 D4 / ADR-035 point 4 with the comment/body
  roles swapped.
- **The constructors and fold are failure-posture-neutral** (ADR-031 point 6 /
  ADR-035 point 3 spirit): the event writer reports `WROTE` / `FAILED` (the claim
  path reads `RACED-LOST` from the re-read fold and backs off, DEC-035 point 6; handoff
  and durability-check paths impose their own posture); the mirror regenerator
  reports `WROTE` / `CLOBBERED` / `FAILED` (routine render treats
  `CLOBBERED` as benign; a reconcile report may surface it as healed drift).
  Construction/fold and failure-handling live at different layers. The writers build
  an argv or a body and report no outcome, so each caller reads success from `gh`'s
  exit. No path reports `CLOBBERED`, `handoff-issue` posts no ownership event, and no
  durability check or reconcile report exists.
- **Realm-blindness — the seam has pm-layer consumers only.** The clash guard, the
  signed listing, and the mirror renderer consume the fold, and in a project with a
  topology the pool, the check before writing and the seat's release; the engine and its
  cascade predicates (DEC-034, COR-037) explicitly **do not** — the inverse of
  ADR-035, where the closure fold *is* a containment-seam consumer. Wiring
  ownership into the engine fold would cross the content-free boundary and require
  its own authorisation (DEC-035 point 8 / DEC-035 Implications).
- **In a project with a topology,** the fold must take four inputs from its caller
  and fold each Task In Progress's whole log (point 7). The pool, the check
  before writing and the seat's release must resolve through it (DEC-059
  Implications), the pool being DEC-059's shared pool, or the seat's pools where the
  topology declares pools of workers (DEC-061). The ownership stamp has a version carrying the seat, the seat's
  number and the clone's key, and readers accept the earlier version (DEC-044 point
  2). Point 7 says how the fold judges renewal and lapse, and point 5 leaves parking
  to the check before writing (DEC-059 point 9).
- **One event builder for two seams.** The audit-log facility's builder builds and
  parses the ownership events and every event of a state issue (point 3). The
  ownership seam's writer asks that builder for each event's body, and composes no
  stamp of its own.
- **DEC-009 models the region.** The description-mirror region is capability-owned,
  do-not-edit, **derived** body content. DEC-009 places it in a third class of body
  content, which neither its wording rule nor its scope rule governs, and points
  here. A human edit to the region is not gated, and the next render overwrites it.
  This ADR cites that class, and DEC-009 owns validate-body's rule for it.
- **The selector schema, comment-stamp format, and mirror-region UX lie outside
  this contract.** The `label | comment` selector lives in instance-ownership's own
  schema home (default `comment`), **not** in `substrate-map.yaml` (DEC-043 point 2).
  The shared audit-log facility's DEC carries the hidden-stamp syntax and the mirror
  region's rendered shape. This ADR pins the resolution + construction contract, not
  the schema or the UX.
- **Relationship to records — no DEC-035 or DEC-043 amendment needed.** Records the
  comment-substrate contract DEC-043 named as its ADR follow-up (the fourth sibling
  to ADR-026 read-path / ADR-031 write-path / ADR-035 containment). **DEC-035 is not
  superseded** — its label mechanism and clash-guard semantics stand; DEC-043
  refines it to substrate-*where-available* and this ADR pins how the comment
  substrate resolves; comment-log-wins is DEC-035's lowest-wins tie-break lifted to
  a mixed-mode invariant. Inherits ADR-026's one-reader discipline at a new boundary
  (the ownership fold), ADR-031/ADR-035's sole-constructor + grep/AST guard
  discipline at a fourth substrate (the event comment and the mirror region), and
  DEC-039 D4 / ADR-035 point 4's derived-view pattern (roles swapped) — with all
  three prior seam invariants staying scoped to their own substrates. Composes with
  DEC-014 (the guard's severity token) and DEC-026 (the event log aligns with the
  handoff audit comment). Does not restate DEC-043; cites it as the decision.
- **Acceptance.** This ADR pins the contract for the comment substrate, by which
  DEC-043 refines the **foundational DEC-035**. So accepting it needs the
  maintainer's sign-off, not the architect's alone. The seam, its two constructors
  and its guard cite this ADR for the invariant. Point 7, and the event builder that
  point 3 shares with state issues, rest on the maintainer's sign-off on DEC-059,
  which DEC-058 and DEC-059 record.
