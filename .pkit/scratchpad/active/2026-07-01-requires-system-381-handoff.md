---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-07-01
---

# Handoff — requires_system (#381) + the adoption/OBS issue arc

> Session-continuity note (resume-here). Retire it when #381 lands. Drive
> everything through the `project-manager` agent — that's what filed/started
> this work.

## TL;DR — where we are

- A 25-issue arc (pkit adoption demos + OBS recording-surface upgrade) was
  **batch-planned behind one approval gate and filed**.
- Active thread is **Task #381** (In Progress) — the `requires_system`
  declaration substrate. Its decision (**COR-039**) is authored + accepted; its
  code substrate is implemented, tested, committed.
- All #381 work lives on branch **`feat/381-add-requires-system-schema-field`**,
  freshly **rebased onto `origin/main`** (VERSION **1.132.0**). Nothing pushed,
  no PR yet.

## The filed issue tree

```
EPIC #372  Capabilities-framework hardening (standalone; the requires_system home)
  Feature #373  requires_system mechanism
    Task #381  parse/define requires_system substrate     <-- ACTIVE, In Progress
    Task #382  enforce: warn-at-install / hard-gate-at-use / doctor  (next in spine)

EPIC #359  Lower pkit's adoption barrier / sell PM value via demos  (In Progress via cascade)
  Feature #364  OBS multi-surface recording upgrade
    #377 author surface DECs (surface model + DEC-004 supersession + DEC-001 corollary)
    #378 OBS capture+swap   #379 Marp-PDF presentation   #380 Playwright browser
  Feature #374  demo-recording engine primitives
    #383 input-injection   #384 before_record/teardown   #385 agent-boot + assert
  Feature #376  Demo scenario catalog
    #386 verify agent Milestone->PR scaffold depth (V1)
    #390 S1 greenfield ... #398 S9 change-once-propagate  (9 scenario Tasks, priority order)
  #387 verify workflow milestone auto-roll-on-close (V2)
  #389 write adoption fast-path doc (DOC)
```
(#375 was a duplicate of #373, closed won't-do.)

## #381 status + EXACT next steps

Branch commits (3, on top of main):
- `d3d808e` add COR-039 (proposed)
- `0dd3bd2` accept COR-039
- `990996c` parse requires_system substrate — `capabilities.py` `SystemDependency`
  dataclass + `requires_system` field + parser + 5 tests, **plus** the VERSION
  bump 1.131.1→1.132.0 + adapter ceiling broaden folded in.

COR-039 = **"Capabilities declare dependencies on external system tools"**
(accepted): declare external tools in `package.yaml`; **warn at install**,
capability **hard-gates at use**, fail-closed on indeterminate probe, preflight
check; kit never installs the tool. Reviewed by critic + methodology-reviewer +
convention-compliance.

Tests pass (117/117 capabilities); `pkit migrations check-diff --base main` = no
trigger (pure additive field).

**#381 acceptance criteria:** #2 (DEC authored+accepted) is **ticked**. #1 and #3
are satisfied but **not ticked, and their wording is wrong** — fix next (local PM
ops, no push):
1. **Correct criterion 1 wording**: drop "with its JSON Schema companion
   updated" — there is NO JSON Schema for `package.yaml`; it's the Python
   manifest model in `src/project_kit/capabilities.py`. Reword to "…defined in
   the capability manifest model."
2. **Correct criterion 3 wording**: an additive optional field is a pure addition
   → **no schema_version bump, no migration**. Reword to "pure additive field: no
   migration required; the surface-change VERSION bump rides with this
   change-set." (COR-039's Implications section is slightly over-specified here —
   optional one-line amendment.)
3. Tick criteria 1 & 3 via `check-criterion` (needs the FULL criterion text as
   the guard, not a substring).
4. Then all 3 ticked → move #381 to **Review** and **open the PR** (held for
   explicit user word — do not push without it). Consider a quick re-rebase first
   (branch was ~1 behind main at handoff time).

## Gotchas / environment (important)

- **`pkit` routing bug in non-interactive shells:** bare `pkit` hits the
  **pinned adopter binary** (`~/.local/bin/pkit`), NOT this checkout, because
  mise's PATH isn't active — so `pkit version bump` silently ran against the
  wrong tree. **Use the CWD-router shim `~/.pkit/shim/pkit …`** for any mutating
  pkit command against this repo (that's how the 1.132.0 bump and this scratchpad
  stamp were done). Read-only capability scripts under
  `.pkit/capabilities/project-management/scripts/*.py` run fine directly.
- **Reset the pinned binary:** the misroute bumped it to a bogus 1.133.0 → run
  `mise run pkit:pinned-install` to restore it. Harmless to this repo/main.
- **Issue reads:** the project-manager agent is denied raw `gh issue view` — use
  `.../scripts/show-issue.py <N>` (or `pkit project-management show-issue`).
  `gh issue list` is allowed.
- **Task parent-ref quirk:** `create-issue.py` stamps `Feature: #<N>` for ALL
  tasks (even under an EPIC); `edit-issue.py` accepts any `<Label>: #<N>`.
  #387/#389 were corrected to `EPIC: #359`.

## Dependency spine (what unblocks what)

`#381 → #382`. COR-039 being accepted **unblocks #377** (the surface DECs
depended on the requires_system DEC). Engine primitives (#383/#384/#385) and #364
backends depend on #377 (the surface-model DEC). S1 (#390) can start early
(depends on #384 at most, not the whole OBS upgrade). S2 (#391) needs V1 (#386).

## Reviewer / discipline reminders

For the #381 PR: `convention-compliance-reviewer` on the diff at PR time. The
requires_system code adds a cross-cutting external-dependency concern →
`architect` review is warranted before/at PR (critic already covered the design
via COR-039). software-engineer left one open judgment call: 15 pyright
`reportUnknown*` findings symmetric with the sibling `requires_capabilities`
parser (ungated in CI) — decide cast-to-silence vs keep-symmetric at review.

## Retire when

#381 merges (or is abandoned). At that point drop this note
(`pkit scratchpad drop requires-system-381-handoff`) or fold any durable
learnings into the relevant issue/decision.
