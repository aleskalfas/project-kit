# CLI output discipline — spec

The precise description of how pkit's CLI produces output: the event model, the vocabulary, the renderer contract, selection, and the invariants. This is the **evolving reference** ("what-is") governed by the architectural decision in [ADR-053](architecture/decisions/ADR-053-cli-output-discipline.md) ("what + why"). The design rationale and prior-art survey live in the scratchpad note `.pkit/scratchpad/active/2026-08-27-cli-communication-conventions.md`.

**Status: evolving.** This spec grows as the discipline is built and proven slice by slice (see ADR-053 → Implications → Sequencing). Sections marked _(planned)_ describe decided-but-not-yet-built behaviour; sections describing shipped behaviour cite the code that realizes them. When the discipline is extracted into a reusable `cli` capability, this doc becomes that capability's spec; today it describes pkit's reference **binding** (`src/project_kit/cli_render.py`).

## The model in one picture

```
command  ──emits──▶  events (type-tagged, pure data)  ──renderer(selected)──▶  bytes
```

A command produces **data**, never formatted strings. A **renderer**, selected once at the command boundary from the runtime context, turns the events into bytes. Two output **surfaces** exist with different contracts: the **machine surface** is stable and parseable; the **human surface** is porcelain.

## Events (the data model)

An event is a `type`-tagged, pure-data object: `{type, …payload}`.

- **`type`** — a discriminated-union tag naming the message kind (from the vocabulary below).
- **payload** — pure data only: no ANSI, no layout, no pre-formatted strings.
- **attributes** (advisory) — severity and render hints the renderer *may* consume; never data the payload depends on.

Today's semantic-data parts (`cli_render.title()` / `status()` / `section()`) are the first events; the discipline adds the `type` discriminator and a per-type payload schema. _(Migration planned — ADR-053 sequencing.)_

## Vocabulary (evolving)

The set of `type`s is a **growing** core, not a closed list. Each entry defines its payload and its required rendering per surface. The common-core candidates (from the prior-art survey):

| `type` | Payload (sketch) | Human render | Machine shape |
|---|---|---|---|
| `message` | `{level, text}` | styled status line + severity symbol | `{type, level, text}` |
| `detail` | `{fields}` | aligned key-value block | `{type, fields}` |
| `list` / `table` | `{items}` / `{columns, rows}` | list / aligned table | same, structured |
| `tree` | `{root}` | indented tree | nested object |
| `progress` | `{current, total?, label}` | bar / spinner (TTY only) | periodic status object |
| `result` | `{ok, subject, change?}` | ✓ line | `{type, ok, …}` |
| `error` | `{code, message, remediation?}` | ✗ line + hint (stderr) | `{type, code, …}` |
| `suggestions` | `{items:[{cmd, why}]}` | "Next:" list | structured |
| `empty` | `{subject, hint?}` | dim "no results" | `{type, empty:true}` |
| `summary` | `{counts, ok}` | recap line | structured |

_This table is illustrative and will be pinned precisely as each type is built and proven. Two types are worth making first-class (under-served by every library): **`detail`** (key-value) and **`error`** (with remediation)._

## Renderers and selection

Two renderers over one event stream:

- **Styled path** — the human view. Realized by the shipped leaves `style()` (colour gate, [ADR-011](architecture/decisions/ADR-011-cli-styling-layer.md)) and `wrap()` (width gate, [ADR-024](architecture/decisions/ADR-024-cli-prose-wrapping.md)). The **plain** rendering is *this same path with both gates off* — not a separate renderer — which is why `strip_ansi(styled) == plain` holds.
- **Machine serializer** — the stable surface (`--json`), carrying the full structure, byte-stable across TTY / `COLUMNS` / piped.

**Selection** is resolved once at the command boundary, exactly as colour and width already are:

- explicit flags win — `--json` (machine surface), `--plain` (styled path, gates off), `--color auto|always|never`;
- otherwise auto from `isatty(stdout)` + `NO_COLOR` / `TERM=dumb`.
- **Non-TTY default is plain**, with `--json` opt-in (ADR-053 Decision 5).
- Stream discipline: data → stdout; messages / progress / errors → stderr.

## Extension protocol

- A new `type` is added by implementing a **one-method renderable** (its human rendering; the machine shape is its payload) and registering the name.
- An **unknown `type`** degrades to a structured-payload dump (machine) / a plain structured representation (human) — **never an error**. A new type can never break a consumer.

## Invariants (the nets)

- **`strip_ansi(styled) == plain`** — styling is additive; structure reads with zero styling. (ADR-011; pinned test.)
- **Machine surface is byte-stable** across TTY / `COLUMNS` / piped, and carries the full structure. (Generalizes ADR-024's `render_status_json`; ADR-053 Decision 2.)
- **Same information in every rendering** — held by construction, because all renderers consume the same events.

## Binding ↔ spec seam

- **Universal (the future `cli` capability owns):** the event model, the vocabulary + payload schemas, the renderer contract, the selection rules, the invariants, and a conformance suite.
- **pkit-specific (stays the binding):** the role→colour palette, the zone rhythm, and the per-command wiring in `src/project_kit/`.

Extraction into `capabilities/cli/` — and the per-language-binding capability sub-shape it needs — is deferred to the stability trigger (ADR-053 Decision 6).
