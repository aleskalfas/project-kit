---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-29
---

# Minimal adoption path — lowering pkit's barrier for non-expert colleagues

> Working note, filled **step by step** as the discussion proceeds. Sections are
> stubs until we actually reach them; nothing here is a conclusion until marked so.

## The question

How do we make pkit (with the project-management capability) adoptable and usable by
colleagues who are **overwhelmed** by its surface — so there's a clear minimal fast-path
to install, understand, and use it day-to-day, without having to grok the machinery?

This is the **cognitive** sibling of EPIC #332's P0 principle ("implementation tech is
invisible to adopters"): that one is about install/runtime invisibility; this is about
*conceptual* invisibility — colleagues shouldn't need to learn schemas / migrations /
severity tokens to file an issue and move it across a board.

## Three kinds of overwhelm (decomposition — to confirm/prioritise)

1. **Visual** — the `.pkit/` tree is a wall of folders (schemas, migrations, permissions,
   lifecycle, adapters, …); intimidating when browsing the repo. *(The operator's initial
   idea — relocate non-user-facing trees under a subfolder — targets this.)*
2. **Conceptual** — too many ideas to learn (decisions vs schemas vs capabilities vs
   agents vs workflow vs …). Folder moves don't shrink this; curation / docs / a mental
   model do.
3. **Process** — "how do I adopt this, and what's the daily loop with the PM capability?"
   Needs a documented fast-path, not a folder move.

## Prior art / constraints noted (not yet decided)

- `pkit visibility` (ADR-009) already hides pkit's **git footprint** via
  `.git/info/exclude` — but that's git-tracking-hide, *different* from working-tree tidiness.
- Relocating `.pkit/` subtrees is a **large surface change**: migrations (COR-010), every
  path reference across decisions/docs/adapter/CLI, and the no-shared-files boundaries. So
  the "hide by relocation" lever has real cost and must clearly earn it.
- Area layout is governed by COR-011; the `.pkit/` structure isn't free-form.

## What we've settled (the walk)

- **A1 — roles in scope:** both Implementers and PMs exist — but see A2, the role split is
  *layer 2*, deferred.
- **A2 — the reframe (priority order):** the **first layer** — the core value sold to the
  team and the thing they must understand quickly — is that **pkit secures the
  development-process conventions, centred on the GitHub issue workflow** (the issue
  lifecycle and the closing **cascade**). Delivery vehicle: **demonstrative demos** of how
  easy it is to *set up and use* — both **greenfield** (`pkit init` from scratch) and
  **brownfield** (adopting an existing repo; the operator drives the brownfield setup).
  The **Implementer-vs-PM split is layer 2** — important right after layer 1 lands, not now.

  Prior art for the demo vehicle: the **demo-recording** capability + **storyboard-author**
  skill (scripted CLI demos), and the `example-greenfield` / `example-brownfield` trees.
  Brownfield adoption ceremonies are already in flight (DEC-037; EPIC #217; back-fill #264).

- **A3 — the first-layer mental model** (what a colleague must understand; everything
  *around* the project-management capability, none of the under-the-hood tech). Three points:
  1. **You work through the `project-manager` agent**, which acts on *your* GitHub identity —
     you never touch issues manually; the agent does the filing/moving for you.
  2. **Every movement is gated by process** — the conventions are enforced, you can't skip
     steps. (They experience the gates; they don't read the gate definitions.)
  3. **The process is central and upgradable** — when the team changes a convention, we
     change it once in the pkit capability and `pkit upgrade` spreads it everywhere. This is
     the core sell: conventions secured centrally, not re-litigated per repo.

  **Out of layer 1 (under-the-hood, hidden):** schemas, permissions, migrations, lifecycle,
  adapters, cli internals, process definitions, agent *source* (they use the agent via
  Claude, not by browsing `.pkit/agents/`). This is the principled visible/hidden line that
  the operator's original "relocate non-user-facing folders" idea was reaching for.

- **A4 — park the physical folder relocation.** Moving `.pkit/` machinery under a subfolder
  attacks *visual* overwhelm (the repo first impression) only — it is **not required to sell
  or teach the conventions**, which is what layer 1 is. It's also a large surface change
  (path-rewrites, a migration, no-shared-files boundaries, adapter updates). So it's
  **deferred** as a separate structural item. The **visible/hidden line from A3 is kept** but
  delivered the *cheap* way for now — as **README curation** ("open `capabilities/` and
  `scratchpad/`; the rest is machinery you can ignore"), not a physical move. The `decisions/`
  visible-vs-hidden call (old Q4) only matters once/if we do the physical move, so it's parked
  with it.

- **A5 — the demo's target takeaways + the fast-path.** Two "aha"s the demo must land:
  1. **"Setup is trivial, new *or* existing project — pkit sets up everything in the repo
     itself."** (greenfield + brownfield ease.)
  2. **"It does the bookkeeping *for* me — I can't miss a label, leave a closed ticket open,
     forget to move a ticket between lanes, or forget to roll a milestone. It just does it."**
     (the gating + automation removes both the work and the *fear of error*.)

  **The fast-path (how a colleague learns to work with it, in 3 steps):**
  `pkit install`  →  `gh issues bootstrap`  →  *chat with the `project-manager` agent*.
  (Command names to reconcile precisely later: repo setup is `pkit init`; the PM capability
  install + tracker bootstrap is the `gh issues bootstrap` step; then all real work is
  conversational with the agent — no manual issue handling.)

  **Flagged to verify (candidate feature, not assumed):** does the workflow **auto-switch /
  roll milestones** when one closes (reassign still-open items to the next)? Operator unsure;
  "we can put it there" if missing. → confirm against the workflow schema; if absent, it's a
  candidate addition that would strengthen takeaway #2.

- **A6 — demo scenario catalog (collecting; priority TBD).** Each becomes a storyboard +
  recorded video later.

  *Setup (takeaway #1 — "trivial to start, new or existing"):*
  - **S1 Greenfield setup** — `pkit install` → `pkit init` → `gh issues bootstrap`; from zero
    to a conventioned repo.
  - **S2 Brownfield adopt + back-fill** — point pkit at a messy existing repo; **auditable
    propose-and-cite** back-fill of labels/classification; confirm → apply (the #264 work).

  *The work loop (takeaway #2 — "it does the bookkeeping, I can't mess it up"):*
  - **L1 Happy path** — file → start → PR → merge; labels + board move + closing-cascade
    happen by themselves.
  - **L2 The refusal** ⭐ — try to break the process (Done with no merged PR; mismatched PR
    type) → pkit blocks it with a plain reason. Sells "secured conventions" hardest.
  - **L3 Chat-to-file** — describe an issue in plain words → agent applies type/priority/
    workstream + title prefix + parent, no manual labelling.
  - **L4 Cascade roll-up** — close the last child → parent becomes closure-eligible (and/or
    forward-cascade: start child → parent → In Progress).
  - **L5 Scaffold the whole cascade** ⭐ (operator's "biggest asset") — from one conversation,
    the agent creates the full tree **Milestone → EPIC → Feature → Task → PR**. *(Verify how
    much of this the agent does today; gap → candidate to build.)*
  - **L6 Merge-gate** ⭐ — PR cannot merge until the reviewer agent's verdict passes
    (demonstrated live on #337 this session).

  *The long game (mental-model point 3 — the unique sell):*
  - **L7 Change once, propagate everywhere** — change a convention in the pkit capability →
    `pkit upgrade` → live in every adopter. Why this beats a hand-written CONTRIBUTING.md.

  **To verify (flagged, not assumed):** milestone auto-switch/roll on close (A5); how much of
  L5's full-tree scaffold the agent does today.

- **A7 — the process (operator's plan).** Collect scenarios (here, for now) → **sort by
  priority** → work each **one-by-one**: write a **storyboard** (storyboard-author) → record a
  **video** via the **demo-recording capability** (already shipped — but **likely needs
  extension**; think it through when specifying each storyboard). The scenario catalog likely
  crystallises into a docs-level catalog + per-scenario storyboards as we commit to building.

## Parked / deferred (revisit after layer 1)

- **Physical `.pkit/` folder relocation** (visual overwhelm / first impression). Big surface
  change; cheap docs-curation substitute used meanwhile. Includes the `decisions/`
  visible-vs-hidden question.
- **Implementer vs PM minimal daily loops** (layer 2). Until layer 1 lands.

- **A8 — priority order** (operator-endorsed; reshuffle freely). Narrative flows tangible →
  strategic; leads with both takeaways fast:
  1. **S1** greenfield setup (trivial to start)
  2. **L5** scaffold the whole cascade, Milestone→PR (the headline asset)
  3. **L1** happy-path loop (everyday automation)
  4. **L2** the refusal (can't mess it up)
  5. **L6** merge-gate (quality gate)
  6. **L3** chat-to-file (no manual labels)
  7. **L4** cascade roll-up
  8. **S2** brownfield adopt + back-fill (also the operator's real work-project path)
  9. **L7** change-once-propagate (the closer — why this beats a wiki)

  Build one-by-one per A7: storyboard → record. L5's build must first **verify** how much
  full-tree scaffold the agent does today (gap → implement). 

## What we've settled (the walk)

- **A9 — checkpoint + start S1.** This plan is committed as a checkpoint; building begins with
  **#1 (S1, greenfield setup)** — author its storyboard via the demo-recording capability on
  this branch. Building S1 first is also where we'll discover what the demo-recording
  capability needs **extended** (operator's A7 flag).

## Next steps

- Author the **S1 storyboard** (greenfield setup demo) — current.
- Then proceed down the A8 priority order, one scenario at a time (storyboard → record).

## Crystallises into (expected — placeholder)

- TBD as the walk narrows (likely: a fast-path adoption doc + possibly a `.pkit/` layout
  decision + project-hygiene conventions).
