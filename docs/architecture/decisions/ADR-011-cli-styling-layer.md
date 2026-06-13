---
id: ADR-011
title: A TTY-aware semantic styling layer for CLI output — roles, one gate, plain baseline
status: accepted
date: 2026-06-09
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

[ADR-006](ADR-006-cli-read-view-renderer.md) built `cli_render` as an untyped semantic-data renderer (callers pass data parts; the renderer owns presentation bytes) and **explicitly reserved a styling seam**: "reserve a `render(style="plain"|"auto")` seam; build only `plain` now." The #299 CLI output convention (the "Command output conventions" section of `.pkit/cli/README.md`) crystallized the human-facing rules — three zones via header-case + whitespace, **never horizontal rules** — and likewise *reserved* the styling layer: "a stronger visible break, if ever wanted, is a *dim* header from a future TTY-aware styling layer (colour + TTY only), degrading to plain whitespace when piped / `NO_COLOR`."

The forcing case: the product owner found drawn `── … ──` rules more readable than plain header-case for *callout* blocks (`Next` / `Optional` in `setup autonomy`). Re-allowing drawn rules was rejected — they wrap on narrow terminals, are noise when piped, and break the field-standard scheme (#299). The agreed response is to **realize the reserved styling layer**, and to do it *systematically* (a semantic role vocabulary + one gate) rather than as ad-hoc `bold()` calls that would re-introduce the same drift #299 just fixed.

A `critic` + `architect` consult settled the shape and resolved two design questions. (1) **Where styling lives:** a leaf `style(role, text)` primitive that *both* `view()` (read-views, automatically) and the hand-built procedural step-logs (`setup` / `probe` / `sandbox status` / `confinement_list`) call — a layering, not a fork; `view()` calling `style()` internally *is* the realization of ADR-006's reserved `render(style=)` seam. (2) **The stream-visibility bug:** because several commands return `(report, str)` and the *caller* prints, sniffing `isatty()` at string-assembly time checks the wrong stream — so the colour decision must be resolved **once at the command boundary** and read by `style()`, never sniffed per-call. Proposed status is the acceptance-gate gesture per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md).

## Decision

**CLI human output gains a TTY-aware semantic styling layer: authors tag text with a closed set of *semantic roles*; a single gate maps roles to ANSI bytes or plain text based on a once-resolved colour decision; and styling is provably never load-bearing — the plain rendering always carries the full structure. v1 is monochrome (bold/dim); colour is a deferred map change behind the same roles.**

1. **Semantic roles, renderer owns the bytes (ADR-006's philosophy, applied to emphasis).** Authors never write presentation (`bold(...)`); they tag *meaning*. The closed enum: `title`, `heading` (zone/section headers — `Next`, `Legend`, `Commands`, `SECTION`), `strong` (the verdict / key live state — `Result:`, enforcement ON), `muted` (glosses, step continuations, asides), `command` (a copy-paste command), and the status trio `success` / `warn` / `danger` (the `✓` / `⚠` / `✗` sites). The role→style *map* is policy and lives in the renderer (per ADR-006's layering); the enum is fixed here so it can't drift. These roles name elements **already present** in the output (headers, the `Result` line, glosses, the existing `✓/⚠/✗`, backtick'd commands) — naming a real recurrence, not speculative inventory.

2. **One gate, resolved once.** A single `style(role, text) -> str` in `cli_render` is the only thing that emits SGR codes. The colour decision is resolved **once per process at the command boundary** (not sniffed ambiently per call, which would check the wrong stream) by the field-standard precedence: an **explicit `--color always|never` wins over everything** (including `NO_COLOR`); otherwise `--color auto` (the default) **defers to `NO_COLOR`** (its presence disables colour) and then to `isatty()` / `TERM=dumb`. `style()` reads the resolved decision. (`CLICOLOR_FORCE` and Windows-VT handling are optional later additions; v1 targets POSIX terminals.)

3. **Plain is the baseline; style only amplifies — a *tested* invariant.** The structure must read with zero styling (header-case + whitespace + indentation carry all meaning, exactly today's plain output). Styling is additive-only, enforced by a golden test: `strip_ansi(render(color=always)) == render(color=never)`. If that holds, style can never carry information the plain text doesn't — guaranteeing **scriptability** (pipes, CI), **accessibility** (screen-readers, colour-blindness), and a clean `--json`/human split. This is the load-bearing rule; it generalizes the convention's existing "no rules" / "no stacked subtitle" anti-patterns into one principle: *structure must read without styling.*

4. **`style()` is a leaf both consumers call.** `view()` calls `style()` internally for its titles/headers/glosses → the four read-views (`overview`/`explain`/`profile`/`catalog`) get styling with no call-site change (realizing ADR-006's `render(style=)` seam). The procedural step-logs call `style()` directly at their existing header / `✓⚠✗` sites. Everyone calls the one leaf; read-view authors *additionally* get `view()` on top.

5. **v1 is monochrome; colour deferred behind the same roles.** v1 maps roles to **bold/dim only** (theme-independent, accessible, and it makes rule 3 true *by construction* — no colour channel exists to smuggle meaning into). The **full enum ships from day one** so that adding colour later is a one-line *map* change, never a re-tagging of call sites; in v1 the colour-oriented roles (`success`/`warn`/`danger`/`command`) render conservatively (bold or plain), with the existing `✓/⚠/✗` symbols and backticks remaining the load-bearing signal they amplify.

## Rationale

**Why a role vocabulary is faithful to ADR-006's "dumb renderer," not a violation.** ADR-006's principle is *callers pass semantic data; the renderer owns presentation*. `style("heading", text)` is the same move applied to emphasis — semantic input, renderer-owned bytes — exactly like `title(noun, count, gloss)`. It would violate ADR-006 only if callers passed presentation (`style("bold_red", …)`); the closed *semantic* enum forbids that. The role→style map is presentation policy, which ADR-006 assigns to this layer. A user-configurable theming system *would* be over-abstraction — explicitly out of scope (one hardcoded map, closed enum).

**Why monochrome v1 with the full enum.** The two consult positions reconcile: the enum is the *semantic surface* (expensive to change — it touches every call site), while the role→style *map* is cheap (one place). So fix the full enum now (avoids a re-tagging migration when colour lands) but keep the v1 map monochrome (avoids colour's theme/accessibility/load-bearing risks, and makes the rule-3 invariant hold by construction). Naming the `✓/⚠/✗` and command sites as roles is not speculative inventory — those elements exist in today's output; the roles describe a recurrence already present across `probe`/`setup`/`sandbox status`.

**Why resolve colour once at the boundary.** Commands like `setup_autonomy`/`diff`/`probe` build a string and return it; the *caller* prints. So `isatty()` evaluated inside a string-builder (or in a helper far from the print site) inspects the wrong (or no) stream. Resolving the decision once where the command is invoked — where the output stream is known — and threading it to `style()` is the only correct factoring, and it also avoids recomputing the gate in tight loops (`probe` styles per-probe per-line).

**Why a child ADR, not an amendment to ADR-006.** ADR-006's decision is *untyped renderer (A′), typed Document deferred* — orthogonal to styling. This record **consumes the seam ADR-006 reserved**, it does not replace ADR-006's choice; amending ADR-006's body would muddy an accepted record over an unrelated axis. A child ADR records the role-enum + precedence + invariant as a unit and cites ADR-006 as the seam-provider. The #299 convention section is the *house-rule* home (it gets a one-line update pointing its reserved "future styling layer" at this ADR); the enum/precedence/invariant are pinned *here* as tested architecture so they don't drift the way the output convention did before #299.

### Alternatives considered

- **Re-allow drawn `── … ──` rules for callout blocks.** Rejected (#299, reaffirmed) — width-wraps, pipe-noise, off the field standard; and a rule can't rank `Next` over `Optional` the way bold-vs-dim can.
- **Ad-hoc `bold()` calls in command code.** Rejected — scatters presentation across call sites (the drift #299 fixed) and has no single gate for `NO_COLOR`/`isatty`.
- **Ship only 3 roles now (`heading`/`strong`/`muted`), add the rest later.** Rejected for the *enum* (re-tagging every `✓/⚠/✗`/command site later is the costly migration) but adopted for the *build* — v1 wires `heading`/`strong`/`muted` (Phase 1) while the enum is full.
- **Colour in v1.** Deferred — theme/accessibility risk, and monochrome makes the never-load-bearing invariant hold by construction. Colour becomes a one-line map change once demand + the invariant test exist.
- **Styling only inside `view()`.** Rejected — the procedural step-logs (proof-narratives / status, which ADR-006 excluded from read-views) would re-implement the gate or go unstyled; the shared leaf primitive is the COR-007-correct answer.
- **A user-configurable theming system.** Rejected — speculative generality; one hardcoded map.

## Implications

- **Child of ADR-006; no amendment, no supersession.** Realizes ADR-006's reserved `render(style=)` seam via a leaf `style()` that `view()` calls. ADR-006 stays intact and is cited as the seam-provider.
- **New global `--color {auto,always,never}` flag** (default `auto`) on the root command + `NO_COLOR`/`isatty`/`TERM=dumb` resolution at the command boundary. Additive with a safe default → a surface change (new flag + output bytes shift on a TTY) that bumps `.pkit/VERSION` per PRJ-002; **not** a COR-010 migration trigger (no rename/removal, no schema bump, no breaking signature). `cli_render` is tool-internal (NOT propagated), as is this layer.
- **The never-load-bearing invariant is pinned as a test** (`strip_ansi(styled) == plain`) that must precede the first styled render.
- **Doc currency:** the #299 convention section's "future TTY-aware styling layer" line is repointed at this *accepted* ADR (no longer a "future" layer once Phase 1 ships the gate), and a `--color` row joins "Standard flags." Both land in **Phase 1 step 1** (with the gate), not deferred across the phased build — otherwise the convention keeps advertising a layer that already exists, the exact drift this ADR prevents.
- **ADR-009 numbering gap is intentional:** 009 is reserved for the parked git-footprint-visibility ADR (unmerged branch); 010 is host-environment detection; this is 011. Noted so the gap isn't read as a dropped record.
- **Build sanction on acceptance — phased:**
  1. The `style()` gate + `--color` plumbing + the **never-load-bearing golden test** (the invariant's net, *before* any styled render).
  2. `view()` calls `style()` internally → the four read-views get styling for free.
  3. `setup autonomy` headers (`Next`/`Optional`/`Result`) + step-log migration (`probe`/`sandbox status`/`confinement_list`) onto roles, one command per commit.
  Phase 1 (steps 1–2 + the `setup` headers) is the immediate product-owner win; the rest sweeps incrementally.
