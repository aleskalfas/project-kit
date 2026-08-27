---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-27
---

# CLI communication conventions

## The question

How should pkit's CLI *communicate* — its output, help, errors, colour, symbols, prompts — and where should that standard live: a **project convention** (PRJ + house-style doc) or an **installable capability**? Settled direction (maintainer, 2026-08-27): **convention first, capability when it recurs.** This note captures the design space, the clig.dev principles we're adopting, and the two-layer split, and seeds the PRJ.

Emerged from the adoption effort (EPIC #775): after the #780/#787 init work the maintainer flagged that pkit's CLI output "doesn't look good" versus a reference (mockingbird's `rich-click` help), and that the presentation standard should be defined *before* rewriting individual messages (e.g. the post-init next-steps message) so they conform.

Relates to: [COR-004](../../decisions/core/COR-004-cli-surface.md) (CLI surface principles), [COR-007](../../decisions/core/COR-007-pattern-extraction.md) (extract-on-recurrence — the convention-vs-capability discriminator), [COR-017](../../decisions/core/COR-017-capability-pattern.md) (capability pattern), the `software-engineering` capability (the self-adopted-reviewer-panel precedent), PRJ-001/003 (binary name / implementation language), ADR-039 (the router hot path — the startup-cost constraint).

## Source: clig.dev (Command Line Interface Guidelines)

Read in full (https://clig.dev/llms.txt). ~40 principles. The ones most relevant to pkit:

- **Human-first, but composable.** Data → `stdout`; messages/logs/errors → `stderr`. `--json` for machine output; `--plain` when human formatting would break `grep`/`awk`.
- **Say just enough.** Brief success output; don't dump developer-only detail by default; offer `-q`/`--quiet`.
- **If you change state, tell the user** + **suggest the next command(s)** + **make current state easy to see.**
- **Errors as documentation** — catch and rewrite for humans, name the remedy; put the most important line last; red used sparingly.
- **Colour with intention; disable it** when not a TTY, when `NO_COLOR` is set, when `TERM=dumb`, or on `--no-color`. No animations when not a TTY.
- **Symbols where they clarify** (`✓ ⚠ ✗ →`) — not clutter.
- **Help:** concise by default (description + 1–2 examples + pointer to `--help`); full on `-h`/`--help`; lead with examples; bold headings/formatting (this is the `rich-click` win); most-common commands/flags first.
- **Args/flags:** prefer flags to args; full-length version of every flag; standard names (`--dry-run`, `--force`, `--json`, `--quiet`, `-h/--help`); confirm-before-dangerous (prompt on TTY, require `--force`/explicit target otherwise); never *require* a prompt.
- **Robustness:** responsive < 100 ms (print before slow work); progress for long ops; validate input early.
- **Future-proofing:** additive changes; warn before a breaking change.

**pkit already honours much of this** — state-change messaging (init/sync/upgrade), error-as-documentation with a remedy (the #787 init refusals are textbook), confirm-before-dangerous, `--dry-run`, correct exit codes, additive changesets. **Gaps** are mostly presentation (colour, symbols, panels, help formatting) + a few conventions: `--json`/`--plain`, `--quiet`, `NO_COLOR`/TTY-aware colour, a shared render layer instead of ad-hoc `click.echo` (274 in cli.py alone).

## The two layers (the crux of convention-vs-capability)

- **Layer A — universal CLI-design principles** (clig.dev-derived: human-first, say-just-enough, TTY-aware colour, error-as-doc, suggest-next-command, `--json`/`--plain`, exit codes). Reusable by *any* CLI-building project. **Capability-shaped** — a future `cli-design` capability could ship these as DEC records + a `cli-conventions-reviewer` agent, paralleling how `software-engineering` ships its review panel.
- **Layer B — pkit's house style + code** (`rich`/`rich-click`, the specific palette/symbols/panels, the shared render module growing out of `cli_render.py`). pkit-specific → **PRJ + code**, regardless of the capability question.

## Decision: convention first, capability on recurrence

- **Now:** a **PRJ** record ("pkit adopts clig.dev-aligned CLI conventions + `rich`/`rich-click` as the presentation layer") + a **house-style doc** (the visual language) + the **shared render module**. Serves the one consumer that needs it today (pkit), and Layer B is inherently project-specific.
- **Deferred (COR-007):** extract a `cli-design` capability when a **second** project wants Layer A. One consumer today = building the capability now is anticipation, not recurrence. Record the intent so the seed isn't lost.
- **Honest counter (named, not dismissed):** pkit's *purpose* is packaging reusable disciplines and self-adoption is how `software-engineering` began — so a deliberate choice to ship CLI-design as a discipline from day one is defensible. Maintainer chose convention-first because the immediate need is concrete and single-consumer.

## Tools

- **`rich-click`** — near-drop-in for click's `--help`/usage/error screens → the mockingbird look (panels, coloured columns, styled metavars) for almost free.
- **`rich`** — the toolkit for command *runtime* output (panels, styled status lines, symbols, summaries, progress). Manual; drives the house style. One dependency (`rich-click` brings `rich`).
- **Tradeoff to weigh (critic/architect):** `rich` is a non-trivial import (~tens of ms). It does NOT touch the ADR-039 router hot path (that runs before the CLI loads), but adds latency to every command that reaches the CLI. Snappiness vs polish. Mitigations to consider: lazy import, import only on the render path.

## Open questions / candidate scope

- Palette + symbol set (semantic colours: success/warn/error/dim; `✓ ⚠ ✗ →`), and the panel/section grammar.
- The render-module API: what primitives (status line, section/panel, summary block, warning/error, next-steps, table, progress) all commands emit through.
- `--json`/`--plain`/`--quiet` + `NO_COLOR`/TTY detection — adopt globally or per-command?
- Adoption strategy: big-bang vs incremental (start with `--help` via `rich-click`, then the install/next-steps output, then the rest).
- Does any of this touch COR-004's principles, or is it purely a realisation/house-style layer beneath them? (Likely the latter — COR-004 governs *which* verbs/consent; this governs *how they speak*.)

## Path

scratchpad (this) → `critic`/`architect` on the convention-vs-capability fork + the `rich` startup-cost tradeoff → PRJ record + house-style doc → shared render layer + `rich-click` → conform per-command, starting with the post-init next-steps message. Retires by producing the PRJ + house-style doc + render module (and the recorded `cli-design`-capability earmark), or is dropped.
