---
id: ADR-006
title: Read-view CLI output renders through a tool-internal helper layer, untyped now (Option A′)
status: accepted
date: 2026-06-02
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

The conventions for `pkit`'s human-readable output — a title with an inline gloss,
an optional status line, CAPS-headed sections of computed-width table rows, a
`Legend` block, a `Commands` block, the Header/Body/Reference zones, inline
parenthetical glosses, constant-column suppression, and no horizontal rules — are
recorded in two scratchpad notes (`2026-05-31-cli-output-conventions.md`,
`2026-06-01-cli-design-conventions.md`). They are currently *hand-implemented and
copy-pasted* across four `permissions` views (`overview`, `explain`, `profile
list`, `profile show`) in `src/project_kit/permissions.py`. The same align-and-join
column builder and the same constant-column-suppression logic are reimplemented in
each. That is the recurrence [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)
names as the trigger to invest in shared tooling; the output note pre-registered
exactly this extraction.

A survey of all ~56 leaf commands (authoritatively recorded in the scratchpad)
established that this shape is **not** universal: only *read-for-understanding
views* are documents the reader studies. The other genera — `key:value` trees
(e.g. `status`, which is also parity-pinned), progress/imperative output (e.g.
`install`), diagnostic lists (e.g. `validate`, and `permissions diff`, a
reconciliation report), and one-line confirmations (the mutations) — are a
different kind of output and out of scope. The addressable surface is the four
`permissions` read-views today, with the `schemas list`/`show`/`resolve` trio as
candidates that have the table bones but lack the title/Legend/Commands blocks.

This decision was shaped by a `critic` pass (which corrected an over-scoped "every
command" framing and a rigged design comparison) and an `architect` pass (which
confirmed placement and flagged two cheap-now constraints). The full design space
is in `.pkit/scratchpad/active/2026-06-02-cli-render.md`. As project-kit's own
architecture record, concrete paths and the src-vs-propagated split are in scope
here (per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)).

## Decision

Extract a **tool-internal read-view renderer** at `src/project_kit/cli_render.py`,
scoped strictly to read-for-understanding views.

1. **Shape — Option A′.** String/tuple helpers carrying **semantic data** feed a
   single `view(...)` assembler that owns *all* layout/convention decisions (zone
   order, blank-line rhythm, header casing, status-as-footer, no-rules). A
   `table()` primitive owns computed-width alignment + constant-column suppression;
   `legend()`/`commands()` format the reference blocks. The parts a command passes
   are data (a title is `(label, count, gloss)`, a table is `(rows, columns)`), not
   pre-aligned strings — presentation lives only in `view()`.

2. **Defer the typed `Document` model (Option B).** A typed block hierarchy that
   makes illegal output unrepresentable is deferred, not adopted, behind a pinned
   trigger: **promote when a second independent command family adopts the read-view
   shape *and* the conventions have stopped churning, *or* when a correctness
   regression ships that a type would have caught.**

3. **Layering.** Three layers, each with one owner:
   [COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md) owns *which*
   commands exist; the convention notes own the *house rules*; this renderer owns
   the *mechanical half of how a read-view renders*.

4. **Placement — tool-internal, not propagated.** The module lives in
   `src/project_kit/` because its only consumer is the global `pkit` CLI. This is
   the **inverse** of [ADR-003](ADR-003-permission-core-code-home.md)'s constraint
   (the decision core is propagated *because* an in-tree hook must import it without
   the global runtime); the renderer has no such consumer, so it is **not** a second
   member of ADR-003's "neutral propagated shared code" category.

## Rationale

- **Why extract now:** COR-007 — four views copy-pasting the same mechanical code
  clears the recurrence bar for extracting the read-view shape.
- **Why scope to read-views:** the command survey shows the other genera
  (key:value tree, progress, diagnostic list, confirmation, plain list) genuinely
  differ; forcing them onto this model would distort them, and `status` cannot
  change output at all without breaking its parity test.
- **Why A′ over B (the load-bearing choice):** the dominant force is evolvability —
  "we are not done defining the conventions; we must be able to change anything
  quickly." A single `view()` makes *structural* convention changes one-place
  (A′'s win, which the first draft wrongly attributed only to B). B's sole real
  advantage is correct-by-construction (no API to draw a rule), but B makes
  *model-shaped* changes ripple three places (type + render branch + every call
  site), and early-stage convention churn is at least as often model-shaped as
  layout-shaped. So during the churn phase A′ serves the dominant force better, at
  less cost; correct-by-construction is bought later if it earns its keep.
- **Why semantic-data parts:** if parts were pre-formatted strings the view would
  be the only materialisation of the data, and the deferred `--json` surface (which
  dumps the same data) would force a retrofit of every call site. Data-carrying
  parts keep that seam open and make the A′→B promotion a mechanical wrap.
- **Why `src/` placement:** a deliberate application of ADR-003's code-home
  reasoning, not an oversight — the consumer set decides the tier.

### Alternatives considered

- **Option A (helpers each command assembles itself):** rejected — structural
  changes touch every command. A′ is A with one shared assembler, capturing the
  evolvability A lacks.
- **Option B (typed `Document` now):** deferred — its guarantee is real but its
  cost lands on the most likely class of near-term change; promote on the pinned
  trigger.
- **Option C (Rich / a third-party table lib):** rejected — it would not suppress
  constant columns or honour the no-rules zone scheme, and couples output to its
  release cadence. ~150 in-house lines encode exactly our conventions.
- **Null (keep copy-pasting):** rejected on the four-view recurrence.

## Implications

- **Build & migration:** add `cli_render.py` + semantic golden tests, migrate the
  four `permissions` views, and **deliberately re-baseline** their exact bytes
  (normalising incidental accidents, e.g. the `show_profile` row `rstrip` that
  `overview` lacks). The safety net is semantic goldens + a reviewed re-baseline,
  **not** byte-identical output (which would bake accidents into the API contract).
- **Versioning:** the re-baseline is a small surface change (output bytes shift) →
  bumps `.pkit/VERSION` per [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md).
  It is **not** a [COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)
  migration trigger: no file rename/removal, no `schema_version` bump, no CLI
  signature break — only output bytes change.
- **Relation to [ADR-005](ADR-005-permission-profile-surface.md):** `profile
  list`/`show` are its surface; the migration re-baselines their *output bytes*, not
  ADR-005's decision (verbs/contents). No supersession.
- **`--json` seam:** parts-carry-data keeps the human/machine split viable (build
  the data once; `view()` renders it, a future `--json` dumps it). Confirm
  concretely when `diff --json` lands — `diff` is itself out of this renderer's
  scope.
- **Styling layer:** reserve a `render(style="plain"|"auto")` seam; build only
  `plain` now. The deferred dim-when-TTY layer (the `NO_COLOR`/non-TTY open
  question) slots in behind it without views changing.
- **Scope boundary:** do not migrate `status`/`install`/`schemas validate`/
  mutations (different genera). The `schemas list`/`show`/`resolve` trio are
  candidates — adopting them is a deliberate enhancement (add the missing blocks),
  and would be the event that arms the A′→B promotion trigger.
- **Acceptance gate:** this record is `proposed`; building `cli_render` against it
  waits on acceptance.
