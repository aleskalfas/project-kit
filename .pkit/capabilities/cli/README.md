# cli capability

Formalises a **CLI output discipline**: a command emits `type`-tagged, pure-data **events** from an evolving vocabulary, and a renderer selected at the command boundary turns them into bytes — a styled **human** view (porcelain, free to change) and a stable, parseable **machine** surface. The load-bearing guarantee: *the machine surface is the stable contract; the human surface is porcelain.* It's for any project that wants CLI output that is genuinely readable for humans **and** dependable for agents, pipes, and CI at the same time.

> **Status: under development.** This capability is being built and proven inside project-kit first — `src/project_kit/cli_render.py` is the reference **binding**, and this subtree carries the universal spec. It is **not yet installable**; it assembles on the `integration/cli-capability` branch and graduates to a released, installable capability when the discipline stabilises (see [ADR-054](../../../docs/architecture/decisions/ADR-054-cli-output-discipline.md) → *Scope and deferrals*). The full design lives in the scratchpad note `.pkit/scratchpad/active/2026-08-27-cli-communication-conventions.md`.

## What this capability ships

The **universal** half of the discipline (the pkit-specific palette / zone rhythm / command-wiring stays the binding, in `src/`):

- **[`output-discipline.md`](output-discipline.md)** — the spec: the event model, the vocabulary, the renderer contract, selection, and the invariants. Governed by [ADR-054](../../../docs/architecture/decisions/ADR-054-cli-output-discipline.md).
- `schemas/` — _(planned)_ the vocabulary + payload schemas as structured data + a conformance description.
- `decisions/` — _(planned)_ capability-internal decisions as the discipline's universal contract crystallises out of the pkit ADRs.
- `agents/` — _(planned)_ a `cli-conventions-reviewer` that checks a CLI against the discipline.

## Adopter setup

_Not yet installable — under development._ When it graduates, an adopter will `pkit capabilities install cli` and either write a binding in their language against the spec + conformance suite, or adopt an existing reference binding.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[cli:DEC-001-<slug>]`. Other capabilities and adopter content use the same form.

## Dependencies

None beyond the backbone. A language binding is per-adopter; the capability ships the spec + (planned) conformance suite, not N implementations.
