---
id: ADR-024
title: Prose fields wrap through a shared cli_render leaf — hanging-indent always, width-wrap TTY-only, --json byte-stable
status: accepted
date: 2026-06-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

When a command renders an *author-supplied prose field* — a process state's
`meaning`, a transition's `why`, a journal `reason`, a blocked `prompt`,
an invariant's `reason` — that text can carry author newlines or run long.
Today nothing in the CLI knows how to lay prose out: [ADR-006](ADR-006-cli-read-view-renderer.md)'s
`cli_render` computes *table* widths but has no prose facility, and the one
place that needed multi-line prose (`render_status_narrative` in
`src/project_kit/process.py`) hand-rolls ~43 `lines.append` calls and grew an
ad-hoc `_prompt_lines` wrapper. The result is the wrap-bug class an adopter hit:
continuation lines dumped flush at column 0, fixed one field at a time
(the `prompt` in #216, then `Where:`, with `why`/`reason` still latent).

This ADR adds **one shared prose primitive to `cli_render`** and one rule for
how it behaves, so the class is fixed at the layer that owns presentation rather
than patched field by field. In one breath: a leaf
`wrap(text, *, indent, hang, width) -> list[str]` is the only place prose
breaks; **hanging-indent of author-newline'd text is unconditional**
(structural — even when piped, a multi-line field must not dump flush at
column 0), while **hard-wrapping a long single line to terminal width is
TTY-gated** and resolved **once at the command boundary** the same way colour
already is in [ADR-011](ADR-011-cli-styling-layer.md).

The load-bearing invariant is *not* a claim about the human narrative's bytes.
The human narrative is a **porcelain** surface; its **machine sibling is
`render_status_json`**, the `--json` envelope a script keys on. Per the
`2026-06-01-cli-design-conventions` note, free-form prose is **never** offered as
a parsed / `--json` surface — so nothing should parse the human narrative, and on
that surface **neither hanging-indent nor width-wrap is a consumer contract**.
What scriptability actually depends on is therefore pinned precisely: **the
`--json` machine surface (`render_status_json`) is byte-identical regardless of
TTY / `COLUMNS` / piped** — it never calls `wrap()`, so no presentation decision
can reach it. That is the golden-test invariant (the analogue of ADR-011's
`strip_ansi(styled) == plain`). On the human surface we keep a *weaker*
presentation regression net — *the piped narrative gains no width-driven line
breaks* — but state it plainly: piping still applies structural hanging-indent
to author newlines, so the piped narrative is **not** byte-identical to the raw
field text. The narrative net guards against an accidental width-wrap regression;
it is not the invariant scriptability rests on.

This is the **same shape as ADR-011**: it *consumes the renderer-owns-presentation
principle ADR-006 established* on a new axis (line-breaking), it does not revisit
ADR-006's A′-vs-typed-`Document` choice — so it is a sibling ADR, not an
amendment to ADR-006's body. And it follows ADR-011's *both-layered* shape:
`wrap()` ships as a **leaf the procedural narratives call directly now, and that
`view()` calls internally on the second-consumer trigger** (when a read-view
first needs a prose block) — exactly as `style()` is both a leaf and a thing
`view()` calls. The leaf is the entry point; the `view()`-internal path is a
later layering, not an exclusion.

## Context

The forcing case: an adopter binding the `ux-ui-design` capability ran
`pkit process status` and saw author-supplied prose render with continuation
lines flush at column 0 — first a multi-line gate `prompt` (fixed narrowly in
#216 via an ad-hoc `_prompt_lines` helper inside `process.py`), then the
`Where: <state> — <meaning>` line, with every other author-supplied field
(`why`, journal `reason`, invariant `reason`, blocked `resume_reason`) carrying
the same latent flaw.

The root cause is architectural, not a single bug:
`render_status_narrative` **bypasses ADR-006 entirely** — it hand-builds all
layout with ~43 `lines.append`/`extend` calls and manual indentation, calling
`cli_render.view()` zero times. Because presentation is scattered across the
function, each prose field re-derives its own indentation and none wraps; the
bugs therefore scatter field by field. The ad-hoc `_prompt_lines` is the second
hand-rolled prose layout to escape the renderer — the recurrence
[COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md) names as
the trigger to extract a shared primitive rather than keep re-patching.

`cli_render` today has **no prose facility at all**: `view()`/`section()`
compute *table* column widths and own the read-view zone rhythm, but there is no
text-wrapping or hanging-indent helper anywhere — not in the shared layer, not
in the procedural narratives that ADR-006 deliberately scoped *out* of
read-views. ADR-011 already established the precedent this ADR follows: a leaf
primitive in `cli_render` that both `view()` and the hand-built procedural
step-logs call, with its environment decision (colour) resolved **once at the
command boundary** (`cli.py`'s `resolve_color`) because the `(report, str)`
return pattern means a string-builder cannot see the stream it will be printed
to. Width is the second such environment dimension and takes the same factoring.

This decision was shaped by an `architect` consult on a maintainer proposal. As
project-kit's own architecture record, concrete paths and the src placement are
in scope here (per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)).

## Decision

**Add a shared prose primitive to `cli_render`, with a width policy that mirrors
ADR-011's colour policy and a never-load-bearing invariant that mirrors
ADR-011's.**

1. **A leaf `wrap()` now, `view()`-internal on the second-consumer trigger.**
   Prose layout lives in a standalone
   `cli_render.wrap(text, *, indent, hang, width=None) -> list[str]` — the one
   place prose breaks into lines. Two distinct judgements land it here, and they
   should not be conflated. (a) *Whether to extract a shared primitive at all* is
   the [COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)
   recurrence test: two hand-rolled prose layouts (`_prompt_lines` plus the
   scattered `lines.append` indentation) is the trigger to extract rather than
   re-patch. (b) *Whether the carrier is a leaf or a `view()` extension* is
   ADR-006's read-view scope: the procedural narratives this serves
   (`render_status_narrative`, `probe`, `setup`, journal dumps) sit **outside**
   read-views, so the carrier must be callable without `view()`. The leaf is
   therefore the entry point both consumers reach — exactly as `style()` is
   (ADR-011 rule 4): the narratives call `wrap()` *directly* today, and `view()`
   / `section()` call it *internally later* when a read-view first needs a prose
   block (ADR-006's promotion-on-second-consumer discipline governs that
   layering). It takes one logical prose field plus its indent context and owns
   the line-breaking bytes — the same move `title(noun, count, gloss)` and
   `style(role, text)` make, applied to prose.

2. **Hanging-indent is unconditional; width-wrap is TTY-gated.** Author newlines
   (`\n` in the field) always produce continuation lines indented under the
   field — even when piped — because the human narrative is a *presentation*
   surface where readability is the goal and a multi-line field dumped flush at
   column 0 is simply wrong on it. Only the *hard-wrap of an over-long single
   line to terminal width* is gated on a TTY. Both transformations mutate the
   piped narrative's bytes relative to the raw field text — hanging-indent
   injects leading whitespace, width-wrap injects breaks; **neither is required
   to be byte-stable**, because (per rule 4) nothing parses the human narrative.
   The split between them is a *presentation* judgement (structural indentation is
   always wanted; width reflow is only wanted on a TTY), not a load-bearing-bytes
   judgement.

3. **Width resolved once at the command boundary.** A `resolve_width(...)` /
   `_wrap_width` pair sits beside ADR-011's `resolve_color` / `_color_enabled`.
   `wrap()` reads the resolved value; it never sniffs `isatty()` itself (the same
   wrong-stream factoring ADR-011 §2 fixed for colour — the `(report, str)`
   return pattern means the builder can't see the print stream). Resolution:

   - **Piped is always no-wrap, regardless of `COLUMNS`.** When the stream is not
     a TTY, resolve to the no-hard-wrap sentinel *unconditionally*. This is where
     the colour parallel **deliberately diverges** from ADR-011's precedence: for
     colour, an explicit override (`--color always`, `COLUMNS`-style env) beats
     the environment, so a forced setting survives a pipe. Applying that rule
     here would let `COLUMNS` inject width-driven breaks into piped output — the
     exact corruption the presentation/contract split avoids — so width does the
     opposite: piped wins over `COLUMNS`. `COLUMNS` (and a future `--width`) sets
     the width used **only when on a TTY** (or when an explicit `--width` is given
     for a TTY render); it never *forces* wrapping onto a pipe.
   - **On a TTY:** width is `COLUMNS` if set and valid, else
     `shutil.get_terminal_size((80, …)).columns`. **Guard a zero / nonsensical
     reading:** if `get_terminal_size` returns `columns == 0` (or any value below
     the floor), treat it as indeterminate and resolve to no-wrap rather than
     producing one-char-per-line output.
   - **Minimum-width floor.** A resolved width below `indent + hang + a small
     content minimum` is treated as no-wrap (there is no sane reflow into a column
     narrower than the indentation plus a few characters). This makes degenerate
     narrow widths degrade to the readable piped form instead of pathological
     output.
   - **`break_long_words=False`.** A single token longer than the available width
     (a long path, URL, or `command`-role string) **overflows the column rather
     than being hard-broken mid-token.** ADR-011 keeps `command` strings
     copy-pasteable / load-bearing; a mid-token break would corrupt a path the
     reader is meant to copy. Overflow-don't-break preserves the token, accepting
     one over-long line as the lesser harm.

4. **The load-bearing invariant is `--json` byte-stability — a tested
   invariant.** Scriptability rests on the *machine* surface, not the human one.
   The pinned, golden-tested invariant is: **`render_status_json` produces
   byte-identical output regardless of TTY / `COLUMNS` / piped**, because it never
   calls `wrap()` (no presentation decision can reach the `--json` envelope a
   consumer parses). This is the prose analogue of ADR-011's
   `strip_ansi(styled) == plain` — the thing a script depends on, pinned so it
   cannot drift. The golden test stabilizes `render_status_json` across TTY,
   `COLUMNS`, and piped invocations.

   A **second, weaker net** guards the human narrative against a width-wrap
   *regression*: when width resolves to no-wrap (piped / indeterminable), the
   narrative contains **no width-driven hard breaks**. Note precisely what this
   does and does not claim — it does **not** assert the piped narrative is
   byte-identical to the raw field text (hanging-indent still injects whitespace
   per rule 2); it asserts only that *width* introduces no breaks when piped. It
   is a presentation regression net, explicitly the weaker check, **not** the
   invariant scriptability rests on. Width measurement is against **visible**
   width, so prose is wrapped *before* styling (never measure already-SGR'd text),
   keeping the two leaves composable.

5. **`_prompt_lines` becomes a thin caller.** The #216 ad-hoc wrapper is rewired
   onto `wrap()` (its `❓ ` marker is a first-line prefix; marker-prefix +
   hanging-indent is exactly the general shape `wrap`'s `hang` parameter
   exposes), retiring the second hand-rolled prose layout into the shared leaf.

## Rationale

**Why the carrier is a leaf the narratives call, not a `view()`-only facility.**
ADR-006 scoped the procedural/diagnostic narratives (`status`, `probe`, `setup`)
*out* of read-views precisely because they aren't title+table+Legend documents.
If wrapping lived *only* inside `view()`, every one of those narratives would
re-implement it — which is exactly how `_prompt_lines` got hand-rolled. So the
leaf must be reachable without `view()`. This is *not* "leaf instead of `view()`"
— it is ADR-011's both-layered shape: `wrap()` is a leaf the narratives call
directly, **and** the thing `view()` calls internally once a read-view needs a
prose block (ADR-011's `style()` is exactly this — a leaf that `view()` also
calls). What is deferred is only the `view()`-internal *path*, on ADR-006's
second-consumer trigger; building it now, with no read-view consumer, would be
the speculative-generality trap. ADR-011's "styling only inside `view()`"
alternative was rejected for the same reason: the procedural step-logs need the
leaf directly.

**Why a sibling ADR, not an ADR-006 amendment.** This is ADR-011's own reasoning
applied verbatim. ADR-006's *decision* is "untyped renderer A′, typed `Document`
deferred" — orthogonal to line-breaking. This record **consumes the
renderer-owns-presentation principle** ADR-006 established on a new axis; it does
not replace ADR-006's choice. Amending ADR-006's body over an unrelated axis
would muddy an accepted record, the exact reason ADR-011 chose a child record.
ADR-006 stays intact and is cited as the principle-provider.

**Why width follows colour's boundary-resolution.** Width is the second
environment dimension `cli_render` reads (after colour), and it has the *same*
factoring hazard: commands build a string and return it for the caller to print,
so `isatty()` evaluated in the string-builder inspects the wrong stream
(ADR-011's load-bearing finding). Resolving width once where the stream is known
and threading it to `wrap()` is the only correct factoring and is consistent
with the established pattern rather than a new one.

**Why the hanging-indent / width-wrap split — and why neither is a contract.**
A tempting but *false* justification is "hanging-indent is structural, so it's
safe even piped." It is not safe in the byte-identity sense: injected indentation
mutates the piped bytes exactly as width-wrap does. The split is not "one is
byte-safe and one isn't" — **both** mutate the piped narrative. The split is a
*presentation* judgement on the human surface: a multi-line field flush at column
0 is unreadable whether or not you have a wide terminal, so indent it always;
reflowing a long line to terminal width only helps on a TTY, so gate it there.

What makes this safe at all is the porcelain/plumbing split, demonstrated rather
than asserted: the human narrative is a **porcelain** surface, and per the
`2026-06-01-cli-design-conventions` note free-form prose is **never** offered as a
parsed / `--json` surface ("never offer it for one-line mutation confirmations or
free-form prose"). A consumer that needs structured status reads the **machine
sibling**, `render_status_json`. So no consumer contract sits on the human
narrative's bytes — indent and width are both free to vary. Scriptability is
guaranteed *not* by the narrative being byte-stable (it isn't) but by the `--json`
surface being byte-stable, which it is by construction (`render_status_json` never
calls `wrap()`). That is the construction that makes scriptability hold; the
hanging-indent/width split is a readability choice layered on top of it.

### Alternatives considered

- **Extend `view()`/`section()` to own prose blocks *now* (instead of shipping
  the leaf first).** Rejected *for now*, not forever — the offending narratives
  are outside read-views (ADR-006), so they need the leaf directly regardless;
  and `view()` would have to represent nested sub-lines (journal entries, per-move
  prechecks) its table model doesn't carry, distorting the narrative or forcing a
  premature `view()` rework. The `view()`-internal path is bought on the
  second-consumer trigger, layered over the same leaf.
- **Patch each prose field in `render_status_narrative` locally** (the cheap
  fix). Rejected — it leaves the next field latent (the #216 pattern repeating)
  and keeps presentation scattered, the root cause.
- **Amend ADR-006's body to add prose-wrapping to the renderer's remit.**
  Rejected — muddies an accepted record over an axis orthogonal to A′-vs-B;
  ADR-011's sibling-ADR precedent is the cleaner home.
- **Wrap on a TTY by sniffing `isatty()` inside `wrap()`.** Rejected — the
  wrong-stream bug ADR-011 already diagnosed; resolve once at the boundary.
- **Hard-wrap unconditionally (even when piped).** Rejected — injects
  width-driven breaks into the piped narrative for no reader benefit (a pipe has
  no terminal width to reflow toward), making the output sensitive to `COLUMNS`
  where it should be inert. The narrative regression net (rule 4) forbids it.
- **Let `COLUMNS` force-wrap even when piped (the strict ADR-011 precedence
  parallel).** Rejected — ADR-011 has an explicit override beat the environment,
  which for width would mean `COLUMNS` injects breaks into piped output. Width
  deliberately diverges: piped is always no-wrap, `COLUMNS` only sets the TTY
  width. This keeps the piped narrative inert to a stray `COLUMNS` in the
  environment, which is the safer default for the porcelain surface.
- **Hard-break long tokens to fit the width (`break_long_words=True`).**
  Rejected — would split a long path / URL / `command`-role string mid-token,
  corrupting a string ADR-011 keeps copy-pasteable. Overflow the column instead.

## Implications

- **Child of ADR-006; no amendment, no supersession.** Realizes a prose facility
  in the layer ADR-006 owns; ADR-006 is cited as the principle-provider and
  stays intact. Sibling to ADR-011 (same boundary-resolution + never-load-bearing
  pattern, different environment axis).
- **Scope of the immediate change — own-line fields only (the recommended cut):**
  add `wrap()` + `resolve_width`/`_wrap_width` to `cli_render`; rewire
  `_prompt_lines` and the author-supplied prose sites that **start their own
  line** — the blocked `prompt`, `resume_reason`, journal `reason`, invariant
  `reason`, and `check.outcome.reason` — onto `wrap()`; pin the `--json`
  byte-stability golden test plus the weaker no-width-break narrative net. This
  closes the own-line wrap-bug **class** without migrating the narrative onto
  `view()`.
- **`meaning` and `why` are deferred to a follow-up — scoped out of the first
  cut.** These two are not own-line fields: they render as **inline suffixes** of
  composed lines — `Where: <state> — <meaning>` and
  `<marker> <to> [<trigger>] — <why>` (and the invariant
  `<marker> <id> — <why>`). A `wrap(text, *, indent, hang, width)` leaf cleanly
  lays out a field that *starts* its own line, but it cannot wrap a prose tail
  sitting after a **variable-width styled prefix** (the prefix width is
  `len(style(...))` of a runtime state-id / move-id, which `wrap` does not see).
  Handling them needs *either* a `first_line_prefix_width` parameter on `wrap()`
  *or* a layout change lifting the suffix onto its own continuation line — both
  are follow-up work. Lifting them onto their own line now is **rejected for the
  first cut** specifically because it would shift **plain (piped) output bytes**,
  not just TTY bytes (it restructures the narrative for every consumer, not just
  reflow on a TTY) — a larger, separately-reviewed change. The first cut
  therefore covers the own-line fields and explicitly leaves `meaning` / `why`
  for the prefix-aware follow-up.
- **Full `view()` migration of `render_status_narrative` is explicitly NOT in
  scope** — tracked separately. ADR-006's promotion trigger (a read-view needing
  the shape) is not met for this diagnostic genre; forcing it would over-reach.
- **Versioning:** a TTY-only output-bytes shift plus a new internal facility →
  a small surface change that bumps `.pkit/VERSION` per
  [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md). It
  is **not** a [COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)
  migration trigger (no rename/removal, no `schema_version` bump, no CLI
  signature break — only TTY output bytes change). `cli_render` is tool-internal
  (NOT propagated), as is this facility.
- **Doc currency — this ADR is the architectural pin; the house rule lands with
  the implementation.** This ADR pins the *architecture*: the leaf's placement in
  `cli_render`, boundary-resolution of width, and the load-bearing invariant
  (`render_status_json` is byte-stable across TTY / `COLUMNS` / piped). The
  *authoring house-rule* — the convention text below — is **not** mine to land
  (`.pkit/` is owned by the methodology surface and the convention note is an
  active scratchpad draft). It must be landed by the maintainer/engineer **as
  part of the implementation change-set**, in two places: the
  `.pkit/cli/README.md` "Command output conventions" section (alongside ADR-011's
  sibling rules) **and** the `2026-06-01-cli-design-conventions` note (resolving
  its open "Colour / NO_COLOR / non-TTY rendering" question for the width axis).
  Leaving the rule only in an active scratchpad draft is drift — the convention
  must reach the README when the code does. The exact convention text to land:

  > **Author-supplied prose fields wrap through `cli_render.wrap()`.**
  > Hanging-indent of author newlines is unconditional; hard-wrap to terminal
  > width is TTY-only and resolved once at the command boundary (piped is always
  > no-wrap, regardless of `COLUMNS`); long tokens overflow rather than breaking
  > mid-token. The human narrative is porcelain and is **never** a parsed
  > surface — a script reads the `--json` sibling, which never wraps and is
  > byte-stable across TTY / `COLUMNS` / piped.
- **Acceptance gate:** this record is `proposed`; building `wrap()` against it
  waits on acceptance (PRJ-005).
