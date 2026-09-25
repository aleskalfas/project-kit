---
id: ADR-035
title: Resolve containment through one read seam and construct it through one write point — native-where-present, native-wins, textual the universal spine
status: accepted
date: 2026-06-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a parent's children can live under two substrates — GitHub's
native sub-issue links where the tracker supports them, and a textual first-line
parent-ref on each child where it does not. This contract says: there is **one
place** that answers "what are this parent's children, and via which substrate"
(every consumer asks it, none re-derives by parsing bodies itself), and **one
place** that constructs a containment write (the native link, and the
render-on-demand textual children view where there is no native panel). The read
seam unions the two substrates with **native-wins** dedup so a repo holding
children created under
either substrate resolves correctly, and it says whether the set it returns is the
*complete* one — a gate that closes a container cannot act on a child set that might
be short. That is the whole decision; everything below is the rigor behind it.

[project-management:DEC-039](../../../.pkit/capabilities/project-management/decisions/DEC-039-containment-substrate-selection.md)
decided the *rule* — containment is a **selectable substrate** (native sub-issues
where the tracker supports them, a textual representation where it does not); the
native ideal stays, project-kit's adaptation layer carries the fallback; the
child-side textual parent-ref is the universal spine written in both modes; the
textual parent-side view is render-on-demand (a generated do-not-edit comment the
read path overwrites), not a stored body block. This ADR records the
*containment-resolution contract* DEC-039 named as its ADR follow-up — the **third
sibling** to [ADR-026](ADR-026-substrate-map-read-path-contract.md) (the label
read-path/sole-constructor seam) and
[ADR-031](ADR-031-substrate-write-path-contract.md) (the non-label write-path
sole-constructor): **how** containment resolves on read and constructs on write,
and the invariants each side must never violate. It is the on-call/maintainer
reference for the seam realized by the merged #344 (native write) + #345
(`resolve_children` read seam) + #865 (seam-owned corpus acquisition and the
completeness verdict) + #869 (the *unsupported* verdict attributed by probe, one
definition for both paths) + #863 (both non-gate consumers on seam acquisition, and
the read-vs-write postures on a partial answer), ahead of the Track-2 textual-view
build (EPIC #343); it
pins the contract, not the selector schema or the render-on-demand UX (those land
with the Feature, citing DEC-039).

**The contract, in one breath:** containment has **one read seam** — a single
resolution point (`resolve_children` in `_lib/containment.py`) answering "what are
this parent's children, via which substrate, and is that answer complete,"
native-where-present / textual-otherwise, with **native-wins** and **an honest
completeness verdict** as seam invariants — and **one write construction point** per
containment substrate (the native sub-issue link; the render-on-demand textual
children-comment), each under the grep/AST sole-constructor guard ADR-031
established. No consumer re-derives containment by parsing body parent-refs itself
(ADR-026's one-reader discipline, applied to the containment axis); no script
string-builds a containment write inline (ADR-031's sole-constructor discipline,
applied to a third substrate).

**The load-bearing invariants — one read seam with native-wins and honest
determinacy, one write constructor per substrate.** Four parts, structural only
together: (i) **every containment consumer resolves children only by asking the
seam** — `show-tree`, the [project-management:DEC-034](../../../.pkit/capabilities/project-management/decisions/DEC-034-cascade-slot-binding.md)
closure-fold child-walk, and `close-issue`'s open-children walk all route through
`resolve_children`; none re-parses body parent-refs directly, so there is one
place containment is resolved and one place native-wins is enforced; (ii) **the
seam unions the two substrates with native-wins dedup** — a child present under
both substrates resolves to NATIVE, a child present only textually resolves to
TEXTUAL, and a native child the textual scan missed is still NATIVE; this is
DEC-005's native-wins rule lifted from a single-substrate tie-break to a
**mixed-mode reconciliation** invariant (a repo may hold children created under
either substrate after a forward switch, and the seam unions them deterministically);
(iii) **the seam reports whether its answer is complete, and an incomplete answer is
an indeterminacy rather than a child set** — the native read distinguishes
*unsupported* (no native substrate, so textual is the whole answer) from *unreadable*
(a native child set may exist and was not seen) — a distinction it *establishes* by
asking the API, never infers from a failed call's status — the textual scan reports
*complete* vs *truncated*, and either indeterminacy makes the whole resolution
incomplete; a
gate consumer maps an incomplete resolution to indeterminate, never to a child set
and never to "no children", while a non-gate consumer may *render* an incomplete
answer only if it marks the output partial and must *refuse* to write one anywhere
durable; and (iv) **every containment write is constructed in
exactly one point per substrate** — the native link via `add_sub_issue_args` /
`link_sub_issue`, the textual view via the single render-on-demand writer
(`refresh_children_comment`) — never string-built inline, under the same grep/AST
guard ADR-031 holds for field-value and milestone writes. The textual parent-side view is a **full-overwrite of a generated
do-not-edit comment** (single source, render-on-demand), **never an append** —
DEC-039 D4's storage decision, recorded here as a write-construction invariant.

## Context

DEC-039 settled the containment substrate-selection rule and explicitly deferred
the formal contract to a sibling ADR: *"The formal read-seam + sole-constructor
contract (the consistency invariants) is pinned in a sibling architect-owned ADR
(the third sibling to ADR-026 read-path / ADR-031 write-path); this record decides
the rule, the ADR the contract."* DEC-039 is now `accepted`; this is that ADR.

Containment is a **third non-label substrate**, distinct from the two ADR-031
covers (Projects-v2 field-value and milestone assignment) and from the label axis
ADR-026 covers. It establishes the native parent ↔ child edge that surfaces a
child in the parent's sub-issues panel and feeds the Projects-v2 "Sub-issues
progress" field. Because it is a different operation (`gh api …/sub_issues` rather
than `gh project item-edit` / `gh issue …--milestone` / a `<axis>:<value>` label),
it lives in its own module (`_lib/containment.py`) with its own sole-constructor
guard — the same discipline as ADR-031's substrate-write seam, **not a widening of
that seam's covered set**. ADR-026's label invariant and ADR-031's field/milestone
invariant both stay scoped to their own substrates and untouched.

[project-management:DEC-005](../../../.pkit/capabilities/project-management/decisions/DEC-005-linking-and-containment.md)
is where native-wins originates — its "native sub-issues canonical, textual
first-line projection in parallel, native wins on disagreement" rule. DEC-039
refined DEC-005 to native-*where-available* and made the textual child-side ref
the universal spine written in both modes. This ADR pins how that refined rule
resolves at the seam.

**The realization surface — the seam fetches, resolves, and vouches.** As ADR-026
enumerated its ~26 inline label sites and ADR-031 its four (then six) non-label
sites, this Context names the containment realization as-built. Unlike those two,
containment landed seam-first: #344 supplied the native write through one
construction point (`add_sub_issue_args` / `link_sub_issue`), #345 supplied the
one read seam (`resolve_children`), converging the three pre-existing
body-parent-ref walkers onto it, #865 moved corpus acquisition and the
completeness verdict behind that same seam, #869 made the *unsupported* verdict
an attribution the seam establishes rather than a reading of the failed call's text,
with the write path routed through the same classification, and #863 converged the
last two consumers — the tree renderer and the children-view refresh — onto seam
acquisition. The seam fetches the corpus itself (`fetch_issue_corpus`, whose
`limit` defaults to `CORPUS_CEILING`), reads the native panel three-valued
(`read_native_children` → `READ` / `UNSUPPORTED` / `UNREADABLE`, the two non-`READ`
verdicts decided in one classification point that *attributes* a failed call rather
than reading its error text), and returns `complete` + `incomplete_reason` alongside
the child set; every gate consumer holds on an incomplete answer rather than acting
on it. **Every consumer acquires through the seam**, and the two that are not gates
answer an incomplete corpus differently according to what each emits: the tree render
labels itself partial and continues, the children-view refresh refuses to write. The
sites below name where each one stands against that contract.

As project-kit's own capability-architecture record, concrete site names
are in scope (per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md));
the selector schema (`substrate-map.yaml`'s `containment: native | textual` axis)
and the render-on-demand textual-view UX are not — they land with the Track-2
Feature (EPIC #343), citing DEC-039. The sites:

1. **`resolve_children`** (`_lib/containment.py`) — the one read seam, and the one
   corpus fetcher. Native side: one `GET …/sub_issues` per parent
   (`read_native_children`), three-valued — `READ`, a determinate `UNSUPPORTED`,
   or an indeterminate `UNREADABLE`. A non-zero exit is classified in one place
   (`_classify_native_failure`): a conclusive status (410/422) is `UNSUPPORTED`
   outright; an ambiguous 404 is `UNSUPPORTED` only when a probe of the parent
   issue itself succeeds, attributing the 404 to the sub-resource rather than to
   the repository; everything else — a probe that fails or cannot run, a missing
   `gh`, an unparseable payload — is `UNREADABLE`. Textual side: every issue in the corpus whose body
   first-line parent-ref names the parent, where the corpus is either fetched by the
   seam (`fetch_issue_corpus`, *truncated* when the **requested** `limit` is struck —
   `CORPUS_CEILING` is that parameter's default and the value a gate takes, while a
   renderer may deliberately ask for less and is then judged against its own ask) or
   supplied by the caller *with* a completeness claim — a corpus handed over without
   one is not vouched for. Union with native-wins dedup, returned with `complete` /
   `incomplete_reason`. **The sole resolver — consumers route through it.**
2. **`show-tree`** — the parent → children tree renderer. **Converged — resolves
   *and* acquires through the seam;** it asks `fetch_issue_corpus` at the operator's
   `--limit` (default 500) and `--state` — the view controls the seam admits for a
   renderer — and the verdict on *that ask* is one of the two containment facts the
   render reports: a tree built from a struck limit is marked `[partial]` in text (on
   stdout *and* stderr, so a redirected render keeps the caveat), as a
   `> **Partial view**` note in markdown, and as `"complete": false` with an
   `incomplete_reason` beside it in JSON, while a complete render carries no mark
   at all — which is what makes the mark informative. A renderer rather than a gate,
   so point 5 licenses it to use an incomplete answer *labelled*; its own write
   trigger does not inherit that licence (site 6). The second fact is each parent's
   own `ChildResolution`: `_link_parents` forwards the corpus's completeness claim
   into the seam and returns the parents it could not vouch for, so an *unreadable*
   native panel marks the render partial even when the corpus was whole. The note
   names whichever of the two it established — truncation first when both hold,
   since a bounded corpus reaches the seam as an unvouched one and every parent then
   reports incomplete as a *consequence*, so naming the consequence would tell the
   operator the corpus had been read in full — and asserts nothing when neither is
   established. A third cause sits outside containment: a PR list that strikes the
   same `--limit` also marks the render partial, its reason appended to either
   containment reason with "; " rather than ranked against it, because the PR list
   is independent of the tree.
3. **The DEC-034 closure-fold child-walk** (`_lib/lifecycle_predicates.py`) — the
   cascade membership read. **Converged — resolves *and* acquires through the seam;**
   `cascade_members` asks `resolve_children` with no corpus of its own and maps an
   incomplete resolution to indeterminate. Its sibling `parent_has_active_descendant`
   takes the corpus from `fetch_issue_corpus` and holds on an incomplete one; it
   filters by the textual ref itself because it needs each row's state, labels and
   milestone to infer position — which the child set does not carry.
4. **`close-issue`** — the open-children walk behind the refused-cascade hint
   (`_find_open_children`). **Converged — resolves *and* acquires through the seam;**
   it takes the corpus from `fetch_issue_corpus` (it needs each row's state to filter
   the resolved children to the still-open ones), hands it to `resolve_children`
   *with* its completeness claim, and refuses rather than reporting a child set when
   the resolution is incomplete.
5. **`link_sub_issue` / `add_sub_issue_args`** (`_lib/containment.py`) — the one
   native containment write construction point; `create-issue` calls it on
   `--parent`, any future parent-link mutation reuses it. **The sole constructor of
   the native containment write.** Its `UNSUPPORTED` verdict comes from the read
   side's classification point, not from a predicate of its own, so the two paths
   cannot hold different notions of "unsupported" — a write that fails on a
   credential fault reports `FAILED` to the operator rather than quietly
   degrading to the textual spine.
6. **`refresh_children_comment`** (`_lib/containment.py`) and its two triggers — the
   one construction point for the textual parent-side children view, and the only
   containment write rendered *from* a resolved child set. `create-issue --parent`
   refreshes it once the child-side textual ref is written; `show-tree
   --refresh-children-views` refreshes every parent explicitly. **Both triggers
   refuse on an incomplete corpus** — `create-issue` skips the publish and leaves the
   previous render standing, `show-tree` exits non-zero without writing — and the
   same refusal covers a corpus that could not be read at all, which would otherwise
   render an *empty* children list indistinguishable from a parent that genuinely has
   none. Each refusal reports the fact the seam established and prescribes no
   remedy that presumes another — the message is the operator's only route to
   unblocking the write, so a misattributed cause there costs more than on a render
   (point 5's non-gate bullet). The refusal sits at each trigger rather than inside
   the writer, which renders from whatever corpus it is handed; a third trigger must
   carry the check itself (point 5's write posture).

The architecturally-significant pins, each carrying an alternative DEC-039 already
rejected or this ADR holds against:

1. **One containment read seam** (the consumers ask `resolve_children`) vs. each
   consumer re-deriving children by parsing body parent-refs itself — the exact
   re-derivation ADR-026's one-reader discipline forbids, applied here to
   containment.
2. **Native-wins as a seam invariant** spanning mixed-substrate repos vs. a
   per-consumer tie-break that could disagree across consumers; and the
   mixed-mode reconciliation it entails (a forward-switched repo holds children
   under either substrate; the seam unions them).
3. **One write construction point per containment substrate** (the native link, the
   render-on-demand textual view) vs. inline `gh api …/sub_issues`
   construction at each parent-link site — the scatter ADR-031 converges for
   field/milestone writes.
4. **Render-on-demand full-overwrite of a generated comment** for the textual
   parent-side view vs. a stored body block appended on every child-create
   (DEC-039 D4 rejected the latter; recorded here as a write-construction
   invariant, not re-litigated).
5. **The seam answers with a determinacy** (complete vs incomplete, with the native
   read three-valued and acquisition behind the seam) vs. answering with rows alone
   and leaving each consumer to fetch its own corpus under its own ceiling — the
   shape that lets a truncated scan or an unreadable native panel reach a close gate
   as a confident, silently short child set.
6. **The `UNSUPPORTED` verdict is attributed by asking the API** (a conclusive
   status, or a 404 the parent-issue probe pins on the sub-resource) vs. inferred
   from the failed call's status or error text — which cannot separate an absent
   endpoint from a repository the caller may not see, and so grants determinacy on
   no evidence.

## Decision

**In plain terms:** containment consumers stop parsing body parent-refs themselves
and start asking *one seam* "what are this parent's children?" The seam answers
with the union of the two substrates, native-wins on conflict, degrading to
textual-only where native is unsupported — and it says whether that answer is the
whole story, because a child set that might be short is not an answer a close gate
can act on. And every containment *write* — the native link, the textual children
view — is constructed in *one place* per substrate, never string-built inline. What
a consumer may then *do* with an incomplete answer depends on what it emits: a render
may show it labelled, a write may not publish it at all.

### 1. One containment read seam — resolution lives in exactly one auditable place

"What are this parent's children, and via which substrate?" is answered by a
**single read seam** (`resolve_children`), not re-derived per consumer. `show-tree`,
the DEC-034 closure-fold child-walk, and `close-issue`'s open-children walk all
resolve through it; none re-parses body parent-refs directly. The seam takes a
parent number, and either acquires the corpus itself or accepts one the caller
supplies *with* its completeness claim (point 5); it returns the resolved child set,
the substrate each child came from, and how determinate that answer is.

This is ADR-026's one-reader discipline applied to the containment axis: the
indirection (corpus acquisition + native panel read + textual body-ref scan +
native-wins dedup + the completeness verdict) sits in one place where it can be
audited, tested, and reasoned about as a unit, and no second consumer re-derives
what one seam already resolves. A consumer re-parsing
body parent-refs itself would (a) duplicate the native-panel read and the dedup
logic, and (b) give native-wins N places to drift instead of one to audit —
exactly the scatter the single seam exists to prevent. The seam owns the textual
projection too (`_body_names_parent`), so a consumer routing through it never
re-parses a body itself.

### 2. Native-wins as a seam invariant — and mixed-mode reconciliation

The seam unions the two substrates with **native-wins dedup**, governed by a
single rule: *a child present under both substrates resolves to NATIVE; a child
present only textually resolves to TEXTUAL; a native child the textual scan missed
is still NATIVE.* Native-wins is DEC-005's original tie-break — but DEC-039 lifts
it from a single-substrate disagreement rule to a **mixed-mode reconciliation
invariant**:

- **A repo may hold children under either substrate.** DEC-039's selector is a
  *forward* switch — an operator who moves from textual to native (or runs on an
  instance that gains sub-issue support) leaves a corpus with some children linked
  natively and some carrying only the textual ref. The seam must resolve such a
  repo correctly, not assume one substrate.
- **The seam unions them with native-wins dedup.** The resolved child set is the
  *union* of the native panel and the textual body-ref scan, deduped by issue
  number, with NATIVE winning any child present both ways. A native child absent
  from the corpus scan is still NATIVE (the native panel is authoritative even for
  a child the textual scan missed); a textual-only child is TEXTUAL.
- **Native support is a property of the read, not of the repo.** When the native
  `GET …/sub_issues` establishes the substrate **unsupported** — a conclusive status
  (410 gone, 422 unprocessable: an older GHES, the feature off), or a 404 the seam
  has *attributed to the endpoint* rather than to the repository — the seam degrades
  to **textual-only**: the read mirror of the write side's UNSUPPORTED no-op, and a
  *determinate* answer, because there is no native substrate for a child to hide in
  and textual is the whole story. A merely **unreadable** panel (auth, a token
  missing issue scope, a repository the caller may not see, network, a transient 5xx,
  a missing `gh`) is a different fact and does not license that degradation: a native
  child set may exist and was not seen, so the resolution is incomplete (point 5). An
  *empty* native read is distinct again — a successful read of a parent with no
  native children, which does **not** trigger textual fallback.
- **Attribution, not inference — the seam asks the API which fact obtains.** The two
  facts above are not separable from the failed response: GitHub answers **404** both
  for an endpoint that does not exist here and for a repository the caller may not
  know exists, with the same status and the same message. So the seam does not read a
  verdict off the status or the error text. It settles the ambiguous case by making a
  second, narrower request — the parent issue itself, the call child-id resolution
  already makes. **Probe succeeds** ⇒ repository, credentials and parent are all
  visible, so the 404 belongs to the sub-resource ⇒ `UNSUPPORTED`. **Probe fails, or
  cannot run at all** ⇒ a repository, credential or visibility fault ⇒ `UNREADABLE`,
  the fail-closed default. Only a conclusive status short-circuits the probe: an
  invisible repository never produces a 410 or a 422. One extra call, on the failure
  path only, once per parent resolved — paid only when something is already wrong.

State the invariant precisely: **native-wins is enforced once, at the seam, over
the union of both substrates — so a mixed-substrate repo resolves deterministically
regardless of which consumer asks.** This is what makes the forward switch safe: no
consumer sees a different child set depending on whether it happened to read the
native panel or the textual refs.

### 3. One write construction point per containment substrate — sole-constructor

Each containment substrate has **exactly one construction point**, and every write
of that substrate routes through it — ADR-031's sole-constructor discipline applied
to a third (containment) substrate:

- **The native sub-issue link** is constructed in one place (`add_sub_issue_args`
  builds the `gh api …/sub_issues` POST argv; `link_sub_issue` composes the
  id-resolve / idempotency-read / add). A mutating script obtains the containment
  write **only by asking this module**; it never string-builds the `gh api
  …/sub_issues` argv inline. `create-issue` calls it on `--parent` today; any
  future parent-link mutation (re-parent, promote, a batch set-field that moves a
  parent) reuses the same construction point.
- **The render-on-demand textual children view** (`refresh_children_comment`) is
  likewise a single construction point: one writer renders the parent-side children
  comment and the read path refreshes it. There is no second place a
  children-comment is written. Because that write replaces the parent's view
  wholesale, every trigger of it refuses on an incomplete resolution rather than
  publishing a labelled one — the write half of point 5's posture rule.

This is ADR-031's instinct at a new substrate boundary: a single auditable
construction point makes "no script string-builds a containment write inline" a
*structural* property (there is no other way to build the write) rather than a
*remembered* one (do not mis-spell the `gh api …/sub_issues` call at each site).
The containment write is a different operation from ADR-031's two (`gh api
…/sub_issues`, not `gh project item-edit` / `gh issue …--milestone`), so it gets
its **own** construction point and its **own** grep/AST guard
(`tests/test_pm_containment_write_seam.py`) — **not a widening of ADR-031's covered
set.** ADR-031's invariant stays field/milestone-scoped; ADR-026's stays
label-scoped; both untouched.

The construction point is **failure-posture-neutral** in the same spirit as
ADR-031 point 6: `link_sub_issue` records the outcome (`LINKED` / `ALREADY` /
`UNSUPPORTED` / `FAILED`) in a neutral `LinkResult`; the caller decides what the
outcome means. `create-issue` treats every outcome as non-fatal — the textual ref
is the spine — and reports a one-line note keyed on the outcome. An UNSUPPORTED
instance degrades the native write to a no-op (the textual ref carries the
relationship); a native write never fails the create.

**"Unsupported" is defined once, for both directions.** The write path does not
carry its own notion of feature-absence: when the add fails, it asks the *read*
side's classification point (point 2's attribution) what the failure was, and only
its `UNSUPPORTED` answer degrades the write to a no-op. This matters because the
two paths have opposite postures on the same fact — the read degrades to
textual-only, the write degrades to silence — so a second definition would let
them disagree about the same instance, and the cheap wrong one loses the operator
signal outright: a broken credential announced as "native sub-issues unsupported
on this instance" is a no-op the operator has no reason to investigate, where
`FAILED` names the fault. One definition, two postures.

### 4. The textual parent-side view is render-on-demand full-overwrite, never append

Where there is no native panel, the parent-side children view is a **generated
do-not-edit comment the read path refreshes by full overwrite** — a single source —
**not** a body block appended on every child-create. This is DEC-039 D4's storage
decision, recorded here as the write-construction invariant it implies: the textual
view's one construction point (point 3) writes by **overwrite**, never by append.

The reason is the read-seam's own existence (point 1): the seam already *derives*
the parent's children from the child-side refs + native panel on demand, so a
stored parent-side block would be a **second source of truth** that can drift from
what the seam derives, bought at the cost of parent-body write-amplification on
every child-create (a read-modify-write of the *parent* body, with its concurrency
race and partial-failure drift). Render-on-demand overwrite delivers the same
in-UI visibility with none of those failure modes — the visibility goal and the
storage decision are separable, and only visibility is wanted (DEC-039 Rationale).
The child-side textual ref remains the **universal spine** written in both modes;
the parent-side comment is a derived, regenerable view, never the source.

### 5. The seam reports determinacy — an incomplete answer is never a child set

**In plain terms:** "I found three children" and "I found three children and I know
there are no others" are different answers, and a close gate needs the second. The
seam has to say which one it is handing back.

Points 1 and 2 settle *how* the two substrates reconcile; completeness is a separate
property, and rows alone cannot carry it. A scan that stopped at a pagination
ceiling returns a child set indistinguishable from an exhaustive one — a **silently
short** answer feeding a gate whose whole job is to refuse on doubt, and the one
failure mode such a gate cannot detect for itself. The native side carries the same
hazard in a different form: *unsupported* (the instance has no native substrate, so
textual genuinely is the whole answer) and *unreadable* (auth, a token without issue
scope, network, a transient 5xx, a missing `gh` — a native child set may exist and
was not seen) are different facts about the world. Degrading an unsupported read to
textual-only is sound; degrading an unreadable one discards children and presents the
remainder as though it were everything.

**And the failed response does not say which fact obtains.** Both native calls are
REST, so a non-2xx carries a status — but the statuses do not partition cleanly:
GitHub returns **404** for an absent endpoint *and* for a repository the caller may
not see, identically. The read that matters most is the one a scope-poor credential
produces, because it is silent: a fine-grained token without issue read on a private
repository answers 404 rather than 401, so taking the status at face value hands a
close gate a *determinate* textual-only answer precisely when the native panel is
invisible — and public-repo work keeps succeeding, so nothing surfaces the fault
(#869). No predicate over the status or the error text can separate the two causes,
because there is nothing in the response to separate them by. Determinacy here is
therefore something the seam must **establish**, not something it may infer: a
conclusive status (410/422, which an invisible repository never produces) settles it
directly, and an ambiguous 404 is settled by the parent-issue probe of point 2 —
`UNSUPPORTED` only when that probe proves the repository, the credentials and the
parent are all visible. A failure the seam cannot attribute is `UNREADABLE`. This
is the load-bearing direction of the bias, and the reason the check is an API call
rather than a string match: the cheaper text predicate is exactly the one that
resolves an unknown into a confident answer, and simplifying to it reopens the gate
fail-open without changing a single visible behaviour on a well-credentialed repo.

The contract therefore carries a determinacy channel:

- **Each half reports its own outcome, not just its rows.** The native read is
  three-valued — a successful read (possibly empty), a determinate *unsupported*,
  or an indeterminate *unreadable*. The textual scan is two-valued — *complete* (the
  corpus was enumerated to exhaustion) or *truncated* (a ceiling was struck, or the
  caller supplied a corpus it does not claim is exhaustive).
- **The resolution is complete only when neither half is indeterminate.** A
  successful-or-unsupported native read plus a complete textual scan is complete.
  An unreadable native panel, or a truncated textual scan, makes the resolution
  **incomplete** whatever the other half returned. A non-empty native panel does not
  rescue a truncated textual scan: the rows never fetched are exactly where a
  textual-only child would be.
- ***Unsupported* is the only failed native read that still counts as complete —
  so it must be earned, not assumed.** It is the one verdict that converts a call
  that did not answer into a whole answer, which makes it the seam's single
  fail-open surface. It is reached two ways and no other: a conclusive status, or a
  404 the parent-issue probe attributes to the sub-resource. Every failure the seam
  cannot attribute — including one it could not probe — falls to *unreadable*. The
  default direction of the ambiguity is indeterminate.
- **An incomplete resolution is an indeterminate answer for any gate consumer.** It
  is never reported as a confident child set and never as "no children" — the
  fail-closed posture the process substrate requires (COR-033), which the cascade
  slot states explicitly for membership: indeterminate membership overrides the
  `on_empty` policy (COR-037).
- **For a non-gate consumer the posture turns on what it emits: a read may label,
  a write must refuse.** One verdict, two admissible answers, and the discriminator
  is not the consumer's rank but whether its output outlives the command. A consumer
  that only *renders* — a tree view, a diagnostic listing — **may** use an
  incomplete resolution provided it **marks the output partial in every format it
  emits**, and
  provided a complete answer carries no such mark, so the mark carries information
  rather than becoming a permanent disclaimer nobody reads. A consumer that *writes*
  the child set somewhere durable **refuses**: it declines the write and leaves
  whatever stood there. The asymmetry is in the blast radius of being wrong. A short
  render is discarded with the terminal by the one operator who chose the limit and
  can see the caveat; a short *written* view is read later by someone who did not run
  the command, and where it is the only parent-side view of children — the no-native
  case the textual substrate exists for — it carries no hedge of its own, so it reads
  as the parent's children, full stop. Stale beats confidently wrong. The refusal
  covers a corpus that could not be read at all for the same reason: rendering that
  as an empty children list is indistinguishable from a parent that genuinely has
  none, which is the silently-short failure in its purest form.
  **Whichever of the two answers a consumer gives, the account it prints is bounded
  by what the seam established.** A partial mark, or a refusal's stated reason, may
  say *less* than the seam knows — "the view may be short; the reason was not
  established" is an honest signal — but it must never assert a cause the seam did
  not establish. A prescribed remedy is that assertion in working clothes: *re-run
  with a higher limit* says the corpus was bounded, so printing it when the corpus
  was read in full and a native panel was merely unreadable sends the operator to
  raise the limit, meet the same signal again, and learn nothing, while the access
  fault that actually hid the children goes unnamed. Distinguishing causes at all
  sits *below* this contract — a consumer with one possible cause has nothing to
  distinguish, and nothing here obliges one to name a cause. The contract binds only
  the other direction: whatever a signal does name must be what the seam
  established. The prohibition binds the refusing consumer hardest: a
  blocked write's message is the operator's only route to unblocking it. This is
  the *unsupported* verdict's shape one layer out — the cheap wrong answer converts
  an indeterminacy into a confident diagnosis, and is wrong in exactly the case the
  signal exists for while reading correctly on every well-credentialed repo, which
  is why it is pinned here rather than left to each site's wording.
- **The seam owns acquisition, not only resolution.** Completeness is a property of
  *how the corpus was fetched*, so the fetch belongs behind the seam: the seam
  supplies the corpus read (paginate to exhaustion, under a *default* ceiling set far
  above any plausible corpus, and report *truncated* whenever the limit actually
  **requested** is struck — a gate takes that default because it wants every row or
  an honest refusal, a renderer may ask for less and is then judged against its own
  ask), and a caller holding a corpus already passes it in *together with* its
  completeness claim. One fetcher, one place the ceiling semantics live. Leaving
  acquisition to each consumer puts a separately chosen ceiling at every call site
  behind a seam that cannot tell one from another, and both failure modes then show
  up at once:
  a tracker that crossed 507 issues struck the closure fold's own 500-row ceiling
  and refused every container close, while `close-issue`'s hint fetched the same
  500 rows with no truncation check and would have served a short child set as a
  whole one (#846). That is why this half of the contract is not optional.

**The write-mode selector never selects the read strategy.** The seam consults
*both* substrates on every resolution, regardless of the `containment: native |
textual` axis
[DEC-039](../../../.pkit/capabilities/project-management/decisions/DEC-039-containment-substrate-selection.md)
D2 introduces. That axis declares how this capability **writes**; it makes no claim
about what a pre-existing corpus **contains** — a brownfield import, a hand-filed
issue, an issue predating native linking, or a native write that degraded (DEC-005:
a native-link failure never fails the create) all leave children the declared mode
does not describe. Reading native-only because the mode says `native` would miss
every such child and answer "no children" to a close gate. This is point 2's
mixed-mode reconciliation restated as a prohibition: the seam does not assume one
substrate, and the selector is not an input to it.

**What this forecloses.** Resolving the textual half through the tracker's *search*
index (matching the parent-ref text) is rejected as a gate mechanism. Search
indexing is asynchronous — stale in exactly the window after child activity when a
close gate runs; the query cannot express the first-line-position constraint the
textual ref actually carries, so its matches need post-filtering and its misses are
invisible; and the index offers no completeness guarantee at all. It would convert a
loud indeterminate into a quiet false negative, the precise failure this section
exists to prevent. Full enumeration with an honest truncation signal is the only
textual mechanism that can answer a gate.

### Boundaries — what this contract is NOT

- **Not the selector schema.** How `substrate-map.yaml` spells the
  `containment: native | textual` axis (DEC-039 D2) lands with the Track-2 Feature
  (DEC-039 Implications), not here. This ADR pins the resolution + construction
  contract, not the schema field.
- **Not the render-on-demand UX.** How the generated children comment is formatted,
  when the read path refreshes it, and the `do-not-edit` marker convention are
  Track-2 Feature work (EPIC #343). This ADR pins only that the write is a
  single-source full-overwrite, never an append.
- **Not auto-detection of sub-issue support.** DEC-039 deferred auto-detection (and
  its per-machine sidecar cache, [ADR-032](ADR-032-per-machine-activation-routing-axis.md)
  routing) explicitly; the selector is a manual operator declaration. The seam
  degrades on the *read* (unsupported native call → textual-only) regardless; the
  manual selector is the operator's deliberate choice, orthogonal to the read-time
  degradation. The parent-issue probe (point 2) is **not** auto-detection either: it
  runs only after a call has already failed, it attributes *that* failure, it is
  never cached, and its answer feeds the resolution in hand — never the selector.
- **Not a reconciliation back-fill.** Switching existing issues from textual to
  native (a [project-management:DEC-037](../../../.pkit/capabilities/project-management/decisions/DEC-037-adoption-ceremony.md)
  `migrate`-family op) is deferred by DEC-039, not pinned here. This ADR pins that
  the seam *reads* a mixed-substrate repo correctly (point 2); back-filling one
  substrate from the other is a separate operation.
- **Not a DEC-005 supersession.** DEC-005's native ideal and the upstream MET-004
  ideal stand; DEC-039 *refined* DEC-005 to native-*where-available* and this ADR
  pins how that refined rule resolves. Native-wins is DEC-005's rule, lifted to a
  mixed-mode invariant, not replaced.

## Rationale

**Why one read seam, not per-consumer re-derivation.** Resolving a parent's
children is a cross-cutting concern — three consumers need it
(`show-tree`, the DEC-034 closure-fold, `close-issue`), and the *same* resolution
logic (native panel read + textual body-ref scan + native-wins dedup) must behave
identically across all of them. A concern that must be uniform across many
consumers belongs at one boundary, not copied into each. Three consumers all
parsing body parent-refs themselves would give native-wins three places to drift
and triplicate the native-panel read — the exact scatter ADR-026's one-reader
discipline exists to prevent, here on the containment axis. One seam is the COR-007
"extract the shared shape" move applied to containment resolution; the third
consumer arriving (the closure-fold, after `show-tree` and `close-issue`) is what
earns the extraction under COR-007's recurrence test rather than speculative
generality.

**Why native-wins as a seam invariant, and why mixed-mode reconciliation matters.**
DEC-039's selector is a forward switch, so a real repo can hold children under both
substrates at once — the migration is not atomic, and an instance can gain
sub-issue support mid-life. If native-wins were a per-consumer tie-break,
`show-tree` and the closure-fold could disagree about a parent's child set during
the mixed window, and the cascade fold could read a different membership than the
tree renders. Enforcing native-wins **once at the seam over the union** makes the
mixed-substrate repo resolve deterministically for every consumer — the property
that makes the forward switch safe. The union (not native-only, not textual-only)
is required because either substrate alone misses children the other holds during
the switch.

**Why one write construction point per substrate.** "Construct the containment
write in exactly one place" is the same architectural property ADR-031 made
load-bearing for field/milestone writes and ADR-026 for labels: a single auditable
point makes the invariant *structural* (there is no other way to build the write)
rather than *remembered* (do not string-build the wrong `gh api …/sub_issues` argv
at each parent-link site). With `create-issue` calling it today and re-parent /
promote / batch-set-field reusing it tomorrow, the un-converged world would have a
parent-link write buildable at every mutation site — N places for the guard to fail
to cover, N for a future author to mis-spell the API call. One constructor and one
guard collapse that. Giving containment its *own* construction point and guard
(rather than widening ADR-031's) keeps each substrate's invariant precise: a
containment write is `gh api …/sub_issues`, not the field/milestone verbs ADR-031
covers, and folding it into ADR-031's seam would overload that seam with an
operation its drivers never invoke and force its guard to allow a third API shape.

**Why render-on-demand over a stored block.** The only thing a stored parent-side
children block adds beyond the child-side ref + the read seam is *in-UI visibility
on a no-native instance*. A stored, auto-maintained block buys that at the cost of
parent-body write-amplification on every child-create (a read-modify-write of the
parent with its concurrency race) and a second source of truth that can drift from
what the seam already derives. Rendering the view on demand (overwrite a generated
comment) delivers the same visibility with none of those failure modes — the
visibility goal and the storage decision are separable, and only visibility is
wanted. This is DEC-039 D4's Rationale; recorded here because it is a
write-construction invariant (overwrite, never append) the single construction
point must honour.

**Why determinacy belongs to the seam, not to each consumer.** Whether an answer is
complete depends on how the corpus was acquired and on what the native panel did —
both of which the seam either performs or is handed. A consumer downstream of it
sees only rows, so it cannot reconstruct the difference between "these are the
children" and "these are the children I managed to see"; asking each consumer to
track its own completeness re-creates exactly the per-site divergence the one-reader
discipline removes, one level up. The asymmetry of the failure decides the posture:
an over-cautious indeterminate costs a retry or a manual override, while a
confidently short child set closes a container over open work and is invisible at
the moment it matters. A gate can only be as honest as the seam it asks, so the seam
carries the verdict.

**Why the unsupported verdict costs an extra call.** Every other outcome the seam
reports is free — it falls out of a response it already has. This one does not,
because the response is genuinely ambiguous: 404 names an absent endpoint and an
unseeable repository with the same status and the same words, and the second is what
a scope-poor credential produces. A seam that must vouch for its own answer cannot
build the one verdict that *grants* completeness out of evidence that does not
distinguish the two cases; the alternative is not a cheaper check but a confident
guess. So the seam pays for the distinction — one narrow request, on the failure path
only, once per parent — and the cost lands exactly where it is affordable, since the
call only happens when something is already wrong. Placing that classification behind
the seam rather than at the read and write call sites is the same one-reader move as
points 1 and 5: "unsupported" is one fact about the instance, and two definitions of
it would let the two paths disagree about the same repository while each looked
locally correct. The architectural shape to protect is that **the fail-open verdict
is the expensive one**. A future author optimising the probe away is left with a
predicate that is right on every well-credentialed repository and wrong in precisely
the case the gate exists for — a regression with no visible symptom, which is why the
mechanism is pinned here and not left as an implementation detail.

### Alternatives considered

- **Each consumer re-derives children by parsing body parent-refs itself** (no read
  seam). Rejected — triplicates the native-panel read and the native-wins dedup,
  gives native-wins three places to drift, and lets consumers disagree about a
  parent's child set in a mixed-substrate repo. The one-reader discipline (ADR-026)
  on the containment axis is the fix.
- **Native-wins as a per-consumer tie-break** rather than a seam invariant.
  Rejected — `show-tree` and the closure-fold could resolve different child sets
  during the forward-switch mixed window; the cascade fold would read a membership
  the tree disagrees with. Enforcing native-wins once at the seam over the union
  makes the repo resolve deterministically for every consumer.
- **Resolve native-only (ignore textual once native is supported)** or
  **textual-only (ignore the native panel).** Both rejected — either substrate alone
  misses children the other holds during a forward switch; the union with
  native-wins dedup is what reconciles the mixed-mode repo.
- **Inline `gh api …/sub_issues` construction at each parent-link site** (no
  sole-constructor). Rejected — re-grows the scatter ADR-031 converges for
  field/milestone writes; gives the invariant N places to drift and the guard N
  shapes to chase. One construction point behind one guard is the structural
  property.
- **Widen ADR-031's substrate-write seam to cover containment** (one seam for all
  non-label writes). Rejected — a containment write is a distinct operation (`gh api
  …/sub_issues`, not `item-edit` / `--milestone`); folding it in overloads that
  seam with an operation its drivers never invoke and forces its guard to allow a
  third API shape. Containment gets its own construction point and guard; ADR-031's
  invariant stays field/milestone-scoped.
- **A stored, auto-appended parent-side `## Children` block as the textual
  fallback.** Rejected (DEC-039 D4) — parent-body write-amplification on every
  child-create plus a second source of truth that drifts from the read seam.
  Render-on-demand full-overwrite of a generated comment delivers the same
  visibility with none of those failure modes.
- **Treat an unreadable native panel as an unsupported one** (any failed native read
  degrades to textual-only). Rejected — the two are different facts: an unsupported
  instance has no native children to miss, while an unreadable panel may be hiding
  a child set that was simply not fetched. Collapsing them turns a transient auth or
  network failure into a confident, short child set at a close gate.
- **Classify the failure from its status or error text** (treat a 404 on
  `…/sub_issues` as unsupported). Rejected — it is the previous alternative wearing
  a status code: GitHub returns 404 both for an absent endpoint and for a repository
  the caller may not see, so the predicate silently collapses *unreadable* into
  *unsupported* for every scope-poor credential, and a fine-grained token missing
  issue read on a private repository lands there rather than on a 401 (#869). No
  richer text matching rescues it; the distinction is not in the response. The seam
  attributes the ambiguous case by probing the parent issue instead, and treats an
  unattributable failure as unreadable.
- **Probe unconditionally, on every failed native read** rather than only on the
  ambiguous status. Rejected as needless — an invisible repository never yields a 410
  or a 422, so those statuses already name feature-absence on their own; probing them
  buys nothing and puts a second request on a path that is already answered.
- **Let the write path keep its own unsupported predicate** (the read probes, the
  write reads the status). Rejected — one fact about the instance with two
  definitions drifts, and the write's posture makes the wrong answer quiet: a
  credential fault reported as "unsupported" degrades to a silent no-op the operator
  has no reason to investigate, where `FAILED` names the fault. Both paths route
  through the one classification point and keep their own postures.
- **Resolve the textual half through the tracker's search index** rather than a full
  corpus enumeration. Rejected — the index is asynchronous and therefore stale in
  exactly the window after child activity when a close gate runs, the query cannot
  express the first-line-position constraint the parent-ref carries, and it offers no
  completeness guarantee at all. It converts a loud indeterminate into a quiet false
  negative.
- **One posture for every non-gate consumer — label the children-view write partial
  rather than refusing it.** Rejected — a render's caveat is read by the operator who
  chose the limit, in the same breath as the output it qualifies, and is discarded
  with the terminal. A comment's caveat is read, if at all, by someone arriving at the
  parent later with no idea a limit was involved, and the view it hedges is the only
  parent-side child list a no-native adopter has. Same verdict, different blast radius:
  leaving the previous render standing is stale, overwriting it with a short list under
  a heading that claims to be the parent's children is confidently wrong.

## Implications

- **One containment read seam** (`resolve_children` in `_lib/containment.py`) that
  `show-tree`, the DEC-034 closure-fold child-walk, and `close-issue` resolve
  through; no consumer re-parses body parent-refs directly. The *resolution* half is
  realized by the merged **#345**, the *acquisition + determinacy* half by **#865**,
  the *attributed unsupported verdict* by **#869**, and the last two consumers'
  convergence onto seam acquisition by **#863** (Context).
- **Native-wins is a seam invariant over the union of both substrates** — a child
  present both ways is NATIVE, a textual-only child is TEXTUAL, a native child the
  corpus scan missed is still NATIVE; native support is a property of the *read* (an
  *unsupported* substrate degrades to textual-only, an *unreadable* panel does not,
  and an empty native read is not a fallback trigger). This makes a
  **mixed-substrate (forward-switched) repo** resolve deterministically for every
  consumer.
- **The seam reports determinacy, and an incomplete resolution is indeterminate** —
  the native read distinguishes *unsupported* (determinate; textual is the whole
  answer) from *unreadable* (indeterminate), the textual scan reports *complete* vs
  *truncated*, and either indeterminacy makes the whole resolution incomplete. A gate
  consumer maps an incomplete resolution to indeterminate, never to a child set and
  never to "no children". The seam owns corpus acquisition so the ceiling semantics
  live in one place: `CORPUS_CEILING` is the default `limit` and the value a gate
  takes, a renderer may ask for less, and *truncated* is measured against whatever
  was requested.
- **A non-gate consumer's posture on that verdict turns on what it emits** — a
  consumer that only renders may proceed provided it marks the output partial in
  every format (and leaves a complete render unmarked, so the mark means something);
  a consumer that writes the child set somewhere durable refuses and leaves the
  previous state standing. Either way the wording is bounded by what the seam
  established: it may name no cause, but never one the seam did not establish, and
  a prescribed remedy (*raise the limit*) asserts one. `show-tree` labels
  (`[partial]` on stdout and stderr, a `> **Partial view**` note in markdown,
  `"complete": false` with an `incomplete_reason` beside it in JSON, so a machine
  consumer is not sent back to inferring the cause either); the textual
  children-view refresh refuses at both of its triggers, including on a corpus that
  could not be read at all — rendering that as an empty children list is
  indistinguishable from a parent with none.
- **The *unsupported* verdict is attributed, never inferred from a failed call** —
  reached by a conclusive status (410/422, which an invisible repository cannot
  produce) or by a 404 that a probe of the parent issue pins on the sub-resource
  rather than on the repository; every failure the seam cannot attribute, including
  one it could not probe, is *unreadable*. This is the seam's one fail-open surface
  (an unsupported read still counts as complete), so it costs one extra request on
  the failure path rather than a status match. **Both the read and the write path
  route through that single classification point** — one definition of "unsupported",
  two postures on it: the read degrades to textual-only, the write degrades to a
  no-op, and a write that failed on credentials reports `FAILED` instead.
- **Both substrates are consulted on every resolution** — the
  `containment: native | textual` selector governs *writes* only and is not an input
  to the read seam, because the declared write mode makes no claim about what a
  pre-existing corpus contains.
- **One write construction point per containment substrate** — the native sub-issue
  link via `add_sub_issue_args` / `link_sub_issue` (realized by the merged
  **#344**), the render-on-demand textual children view via a single writer
  (`refresh_children_comment`). Each under its own grep/AST sole-constructor guard
  (`tests/test_pm_containment_write_seam.py` covers both), the same
  discipline as ADR-031 — **not a widening of ADR-031's covered set**. The
  containment write is `gh api …/sub_issues`; ADR-026's label invariant and
  ADR-031's field/milestone invariant stay scoped to their own substrates.
- **The construction point is failure-posture-neutral** (ADR-031 point 6 spirit):
  `link_sub_issue` records the outcome in a neutral `LinkResult`; the caller decides
  what it means. `create-issue` treats every outcome as non-fatal (the textual ref
  is the spine), degrading an UNSUPPORTED instance's native write to a no-op. A
  native write never fails the create.
- **The textual parent-side view is a single-source full-overwrite, never an
  append** (DEC-039 D4) — render-on-demand of a generated do-not-edit comment the
  read path refreshes, because the seam already derives the children and a stored
  block would be a drift-prone second source of truth. The child-side textual ref
  remains the universal spine in both modes. This ADR pins the overwrite-not-append
  invariant and the refuse-on-incomplete posture, not the comment-format UX.
- **The selector schema and render-on-demand UX are Track-2 Feature work** (EPIC
  #343), citing DEC-039 — the `substrate-map.yaml` `containment: native | textual`
  axis (DEC-039 D2) and the generated-comment format/marker convention. This ADR
  pins the resolution + construction contract, not the schema field or the UX.
- **Relationship to records — no DEC-005 or DEC-039 amendment needed.** Records the
  containment-resolution contract DEC-039 named as its ADR follow-up (the third
  sibling to ADR-026 read-path / ADR-031 write-path). **DEC-005 is not superseded** —
  its native ideal stands; DEC-039 refined it to native-*where-available* and this
  ADR pins how that refined rule resolves; native-wins is DEC-005's rule lifted to a
  mixed-mode reconciliation invariant. Inherits ADR-026's one-reader discipline at a
  new boundary (the containment read seam) and ADR-031's sole-constructor + grep/AST
  guard discipline at a new substrate (the containment write), with both prior
  invariants staying scoped to their own substrates. Composes with DEC-034 (the
  closure-fold reads its membership through the seam). Does not restate DEC-039;
  cites it as the decision.
- **Acceptance.** `accepted` — the maintainer sign-off on DEC-039 (refine DEC-005 +
  extend DEC-036) covers the direction, and this ADR is the architect-owned contract
  pinning how that accepted rule resolves (PRJ-005). It introduces no abstraction
  beyond the seam #344/#345 already established — the determinacy channel is a
  property that seam must carry, not a new boundary — and supersedes nothing.
