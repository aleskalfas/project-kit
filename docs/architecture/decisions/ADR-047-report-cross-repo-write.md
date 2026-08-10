---
id: ADR-047
title: "`pkit report` — realizing the first deliberate fixed-foreign-repo write"
status: accepted
date: 2026-08-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** `pkit report` (per [pkit:PRJ-008]) files an issue to
project-kit's *own* repo — a repo the running session is almost never rooted in. Our
whole model is "a session mutates only its own repo; cross-repo mutation is an
operator-gated exception, never silent" ([COR-039](../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)).
`report` is the **first realization** of that reserved exception, so *how* it relates
to the boundary sets precedent. This ADR pins three realization choices that keep it
an *instance of the exception*, not an *erosion of the boundary*, so a future
maintainer doesn't misread it as either a licence for casual cross-repo writes or a
contradiction of COR-039.

## Context

COR-039 reserves cross-repo mutation as legitimate-but-operator-gated, "surfaced and
confirmed per change, never silent," realized by the self-guard interlock (ADR-034 —
the mechanism implemented as `session_guard`): before a mutation, compare the
mutation target against the session anchor;
a mismatch is the accidental-handoff shape and is refused/prompted.

`report` breaks that seam's assumption in two directions at once:

- For an ordinary adopter, the target (project-kit's repo) is **always** foreign — so
  a naive reuse of the interlock fires on *every* `report` and blocks it by
  construction, inviting the tempting "fix": route `report` through a general
  `--allow-foreign-repo`-style override.
- In self-host (a project-kit developer's session *is* rooted in project-kit's repo),
  target == anchor — so the interlock is a **silent no-op**, and a "report" on one's
  own repo would post with no confirm.

So the interlock cannot serve as `report`'s gate: it blocks the adopter and waves
through the maintainer — the opposite of what safety wants. And the reflexive
override-flag "fix" would normalize guard-bypass and hand every future author a
precedent ("`report` overrides the guard, so can I"). `report` needs its own
realization.

## Decision

**`report`'s reporter side is a *categorically-foreign, never-silent* write with a
fixed, distribution-set target. It sits outside the accidental-handoff interlock by
category — not by override — and its autonomy semantics degrade to a draft.**

1. **Outside the interlock by category, not by flag.** The `session_guard` interlock
   exists to catch a mutation that *could have been meant for this repo* landing
   elsewhere (accidental handoff of a governance artifact — an issue/decision/commit
   belonging to *this* project). A `report` is a *message addressed to the tool's
   makers*; it could **never** have been meant for the adopter's own tracker, and it
   lands **no** governance artifact in any project. So `report` is a *different
   category* of write and is scoped **outside** the interlock's domain — stated
   explicitly in code and here — rather than tripping it and overriding. No
   `--allow-foreign-repo` path is added or reused for `report`.

2. **Never-silent, realized as confirm-or-draft.** The per-change human gesture
   COR-039 requires cannot be "the agent ran `report`" (an autonomous agent could
   file to a public repo under the user's identity without the human seeing the
   body). So:
   - Interactive: a **target-naming confirmation of the exact body before send**
     ("posts a PUBLIC issue to `<owner/repo>` under your gh identity — confirm").
   - Autonomy / `--yes`: **degrade to producing the draft** (the prefilled-issue URL,
     or a file) — **do not post.** This is a deliberate **asymmetry**: everywhere
     else in the CLI `--yes` means "proceed"; for `report`'s foreign write it means
     "produce, don't send." It unifies with the no-`gh`-auth fallback (same "make the
     draft, don't post" path) and with the URL-first posture.

   > **Refinement ([COR-043](../../../.pkit/decisions/core/COR-043-scratchpad-reported-state.md) arc, #642, 2026-08-10) — the confirmed unit is the send payload, not only the body.** An attached scratchpad note that exceeds the issue-body budget is sent as an excerpted body **plus one overflow comment** carrying the full as-sent text — mechanically a second API call to the same foreign issue, but **one logical send**: the *entire payload* (body + overflow comment, with the truncation flagged) is shown and confirmed as **a single gesture before any post**. Partial failure fails closed and loud: if the issue posts but the overflow comment fails, nothing is stamped `reported` (the send did not complete as confirmed), the created issue is named to the operator with the remediation (retry the comment or edit the issue), and the error is surfaced verbatim. This does **not** relax the three bars: no new write category (same target, same issue, one confirm), no override flag, no configurable target. Reviewers should continue to reject any *independent* second write — this refinement covers only the overflow comment of an already-confirmed send. Additionally, the redaction lint over attached content runs at **compose time on every path** — drafts and URL-first included — since "redaction by construction" is a property of the composed payload, not of the channel that carries it.

3. **Fixed, distribution-set target — not configurable-per-adopter, not a
   `--repo`.** The target is one value set by the *distribution's* project config
   (project-kit → its repo; a fork → its own), never an adopter-facing argument. A
   configurable/`--repo` target would turn `report` into a general foreign-issue
   filer and dissolve the containment COR-039 exists to protect. A fork retargets by
   editing its config — an explicit, honest edit, not a runtime knob.

4. **The maintainer side is same-repo — no cross-repo machinery.** `report inbox` /
   `report link` operate on the *current* repo, which for a project-kit developer
   *is* the target. They are ordinary same-repo issue edits and are gated only by
   "current repo == report target" (which is also what scopes them to developers).

## Rationale

These three keep COR-039's boundary intact rather than eroded. Point 1 refuses the
guard-bypass precedent: `report` is not "allowed past" the interlock, it is *not in
its domain* — a distinction that matters because the interlock protects
project-governance artifacts from landing in the wrong project, and `report` moves no
such artifact. Point 2 satisfies COR-039's non-negotiable ("never silent") in a form
that survives autonomy — the failure mode of an agent silently filing is closed by
degrading to a draft. Point 3 preserves containment: a fixed single target is an
*instance* of the exception; a configurable target is the *general* cross-repo writer
the boundary forbids. Together they make `report` legible as "the one sanctioned,
contained foreign write," and give the next author who wants a foreign write a clear
bar to clear (categorical + never-silent + fixed-target) rather than a precedent to
cite loosely.

## Implications

- **`report`'s foreign write is explicitly scoped outside `session_guard`** in the
  implementation, with a comment pointing here; reviewers should reject any
  `--allow-foreign-repo`-style override introduced for `report`.
- **`--yes` carries a documented asymmetry** for `report` (produce-not-send); the CLI
  spec and `--help` state it so it doesn't read as a bug.
- **Redaction of the environment block** (strip `$HOME`/paths, kit-shipped
  capabilities only) is part of "never-silent done responsibly" — the confirmed body
  must be safe *before* the human rubber-stamps it, since a public repo + real
  identity is the exposure. (Detailed in PRJ-008.)
- **Precedent set:** a future deliberate foreign write must clear the same three bars
  or justify a new realization; this ADR is the reference. Sibling to ADR-034
  (the interlock it carves out of).
- Advisory at authoring: this records a *realization*, not a new principle — COR-039
  owns the principle. Promotion to `accepted` follows the same review as PRJ-008.
