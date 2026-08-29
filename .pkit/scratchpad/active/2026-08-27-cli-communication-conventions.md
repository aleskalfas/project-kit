---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-27
---

# CLI presentation — deep brainstorm

**Question:** how should pkit's CLI present its output so it is genuinely readable for a human *and* stays clean for agents / pipes / CI — and what is the right architecture for that?

Approach: settle the **problem + requirements** first (below), *then* derive the architecture. Everything under §3–§5 is a working draft — reshape freely.

## 1. Consumers (who reads pkit's output)

- **Human** at an interactive terminal.
- **AI agent** invoking pkit (the agent-mediated usage model — a dominant consumer for pkit).
- **Script / pipe / CI** — non-interactive, parses the output.

**Weighting (decided):** model **(b)** — the structured/plain rendering is the **source of truth** (canonical, stable, versioned); the human view is a **renderer derived on top**; the **default renderer is picked by TTY** (pretty on a terminal, structured when piped). Agents/pipes are the dominant consumer; the human is secondary but genuinely served. Source-of-truth ≠ default format. (Grounded in §6 prior art; aligns with pkit's existing ADR-006 shape.)

## 2. Problem

- For **humans**, today's output (especially procedural commands — the `init` install dump, the post-init next-steps, `status`) is a dense, flat, largely-unstyled wall: no visual hierarchy, hard to scan, hard to find the one line that matters.
- For **agents / scripts**, output must stay stable, plain, and parseable — and must not be degraded by making it prettier for humans.
- Today neither is served well: output is uniformly plain (tolerable for machines, poor for humans), while the obvious "make it pretty" move (boxes / heavy formatting) risks breaking the machine path.

## 3. Requirements (draft — reshape freely)

### Human-facing
- **Scannable structure** — clear sections / zones + visual hierarchy.
- **Intentional emphasis** — semantic colour / emphasis, used sparingly (not everything coloured).
- **Correct wrapping** — wrap to the terminal width.
- **Clarifying symbols** — `✓ ⚠ →` where they help, not as clutter.
- **Guidance** — surface the line that matters; suggest what to do next.
- **Progress & responsiveness** — show progress for long-running ops; print something quickly so it never looks hung.

### Machine / agent-facing
- **Plain & stable** — non-TTY / pipe / CI output is plain, stable, greppable (no colour codes, animations, or width-reflow that breaks parsing).
- **Structured surface** — a JSON surface for programmatic use, stable across environments.
- **Same information everywhere** — nothing visible only in the pretty view.

### Cross-cutting
- **One house style** — consistent across all commands, not per-command ad-hoc.
- **No cost leak** — the human / pretty path imposes no startup or dependency cost on the machine path.
- **Context-adaptive + override** — auto-detect interactive vs not, plus an explicit override.
- **Quiet mode** — `--quiet` / `-q` suppresses non-essential output.
- **Streaming (long-running)** — stream output/events as work happens; a machine-parseable event stream for agents (cf. `terraform -json`).

### Agent-contract (from the 2024–26 agent-CLI prior art, §6)
- **Structured errors** — JSON on stderr `{code, message, remediation}`; strict stdout (data) / stderr (messages) separation.
- **Semantic exit codes** — not just 0/1: distinguish auth / validation / confirm-required / transient-vs-deterministic.
- **Help as contract** — `--help --json` (structured flag inventory); hard-fail on unknown commands/flags (no silent guessing).
- **Token efficiency** — `--fields` / `--compact` / `--raw`; prefer aggregate commands over many round-trips.
- **Mutation protocol** — non-interactive confirmation: exit-code + a JSON envelope of the proposed change + an exact re-run `--confirm` command, not a TTY prompt. (Connects to the `init` `--yes`/`--root`/confirm work.)
- **Versioned schema** — the machine schema is versioned + extensible (the `--porcelain=v2` lesson; agents tolerate added fields); graceful empty states (`(no matches)`, not an error code).

## 4. Constraints (must respect)

- **Evolve, don't ignore** — build on the accepted CLI architecture: ADR-006 (data ↔ presentation split), ADR-011 (TTY styling + the "structure reads with zero styling" invariant), ADR-024 (wrapping + byte-stable JSON).
- **No heavy-dep coupling** — don't tie output to a third-party lib's release cadence needlessly.
- **Land incrementally** — avoid a long half-migrated / inconsistent window.

## 5. Out of scope (confirm)

- Full-screen TUI / interactive full-screen programs.
- Localisation / i18n — likely defer for a dev-tool CLI (audience is developers + agents); confirm.
- _(others?)_

## 6. Prior art (research — how others solve one-CLI-two-audiences)

- **git porcelain vs plumbing** — the institutional proof that *human output is not an API*. Machines get a separate, **versioned** stable channel (`--porcelain=v2`: extensible, tolerate added fields), NUL-delimited for safe parsing.
- **One data model, N renderers, a selector flag** — kubectl `-o`, AWS `--output`, `gh --json`, docker `--format`. The human table is a *projection of the same structured object*. Winners **TTY-detect the default** (gh/docker downgrade when piped); AWS defaulting to JSON-at-a-human is the cautionary wart.
- **Colour/TTY standard** — precedence `NO_COLOR` (any non-empty → off) → `--color auto|always|never` → `FORCE_COLOR`/`CLICOLOR_FORCE` → isatty; also `TERM=dumb`. Never leak ANSI into a pipe.
- **Designing for AI agents (2024–26) — the sharpest, most relevant angle:**
  - TTY-flipped default: text on a TTY, **JSON when not** (agents are never a TTY → structured with zero flags).
  - JSON is *the contract* (reported agent success ~70–85% parsing text → 95–99% structured).
  - Errors = structured JSON on **stderr** `{code, message, remediation}`; stdout/stderr strictly separated; **semantic exit codes** (auth / validation / confirm-required / transient-vs-deterministic).
  - `--help` is a public contract → `--help --json`; **hard-fail unknown commands/flags**.
  - Token efficiency as a design axis: `--fields`/`--compact`/`--raw`; aggregate commands.
  - Mutation safety = a **confirmation protocol** (exit-code + JSON envelope + exact re-run `--confirm` command), not an interactive prompt.
  - Idempotent commands; **graceful empty states** (`(no matches)`, not an error).
  - CLI vs MCP: CLI ~10–32× cheaper on tokens, ~100% reliable vs MCP ~72%; emerging pattern is hybrid (CLI inner loop, MCP outer loop).
- **Rendering architecture** — build the data once, render many; **JSON is source of truth, the human view is a formatter over it**; independent code paths *drift* (fix architecturally). rich/Textual auto-strip ANSI when piped.

**Verdict for an agent-dominant tool (answers the §1 weighting):** the structured/plain rendering is the **source of truth** (canonical, stable, versioned); the human view is a **derived renderer on top**; the **default is picked by TTY** (pretty on a terminal, JSON when piped). NOT pretty-first-then-derive-plain — that's the legacy retrofit shape git/kubectl/aws had to migrate *away* from. Source-of-truth ≠ default format.

**Happy alignment:** pkit's accepted architecture is already this shape — ADR-006's semantic-data *parts* are the data model, `view()` is the human renderer, `--json` dumps the parts. We evolve in the validated direction, not rework it.

## 7. Output vocabulary (research — the components/use-cases to cover + extensibility)

**Convergent pattern across every library** (Rich `__rich_console__`, listr2 pluggable renderers, Bubble Tea `Model`+`View()`, ink, clig.dev `--json`/`--plain`): a **semantic data model** separated from a **swappable renderer** — none bakes ANSI/layout into the data. This *is* the architecture, and it is already pkit's ADR-006 shape.

### Common-core message types (~10 — the 80/20; ship as a closed, documented core)
- **Message + severity** — a styled status line; severity is an *attribute* (debug · info · success · warn · error), not its own type.
- **Key-value detail** — one record's fields. *(Gap: no library makes this first-class — everyone fakes it with a 2-col table; worth making first-class for agents.)*
- **List / Table** — N items, columns optional.
- **Tree / hierarchy** — nested data.
- **Progress** — determinate (bar + ETA) or indeterminate (spinner); one type with a flag.
- **Success / state-change** — a change happened.
- **Error + remediation** — failure with a fix hint + code. *(Also under-served by libraries; pkit's `init` refusals already do this well.)*
- **Next-steps / suggestions** — recommend the next command(s).
- **Prompt** — confirm · select · input · secret; non-interactive answer via flags/stdin.
- **Empty state** — a query legitimately returned nothing (not an error).
- **Summary / recap** — end-of-run rollup.
- _Near-core (fold in as needed):_ diff / change-preview · streaming log (JSONL) · multi-task progress · structured dump · pagination notice.

### Long tail (adopters add as needed)
syntax highlight · markdown · traceback · badge/label · banner · help/usage · sparkline · file/date picker · toast · live dashboard · hyperlink (OSC-8) · rate meter.

### Presentation components + pipe-safety (render side)
- **Pipe-safe (degrade gracefully):** styled status line (→ plain prefix), table (→ TSV), list, tree (→ ASCII indent), key-value block, panel (→ border stripped), structured dump.
- **TTY-only (down-convert or suppress off-TTY):** progress bar, spinner, live/auto-refresh, multi-task view, prompts (inert non-interactively). Progress down-converts to periodic `{type:progress,current,total}` events for agents — never an animation.

### Extensibility (the "future" surface)
- **Closed small core + open protocol.** The core set is the stable, documented types agents rely on; new use-cases implement a **one-method renderable protocol** (Rich's `__rich_console__` shape) + register a name — no fork.
- **Swappable renderers keyed on context** — agent/JSON (default), human-TTY, plain — auto-selected by TTY + `NO_COLOR`, flag-overridable.
- **Unknown-type fallback** — an unknown `type` dumps its payload as a structured object rather than erroring; a new type never breaks a consumer. Discriminated-union tagging (`type`) enables both machine dispatch *and* graceful degradation.
- Every event carries a `type` tag + a **pure-data payload** (no ANSI/layout); the renderer consumes severity/colour/hints — the data never holds them.

## 8. Packaging direction (decided): capability = destination, spec-first now

- **Capability is the destination.** The discipline (vocabulary + model↔renderer + agent-contract + a `cli-conventions-reviewer`) is reusable + opt-in (CLI-building adopters) — a legitimate capability, paralleling `software-engineering`.
- **Spec-first, now.** Author the **output vocabulary + renderer contract as a language-agnostic spec (a schema)** from day one; pkit's renderer is explicitly a **Python _binding_ of that spec.** Cheap, extraction-ready, and it is what Tier-1 implements against.
- **Struggle 1 — pkit's opinion wired in → parameters.** On extraction, the universal discipline moves to the capability (DEC records + schema + reviewer); pkit's records shrink to _"pkit adopts the `cli` capability with these parameters"_ (palette, renderers, commands, zones). Delicacy: ADR-006/011/024 blend universal + pkit-specific today → a careful **separation**, not a copy.
- **Struggle 2 — language-agnostic → spec + conformance as canon; per-language bindings pluggable.** The JSON-Schema / LSP / protobuf model: the capability ships the **spec + a conformance suite** (events + mode → required output); each language ships a **binding that passes conformance**. pkit ships the Python binding; a Go adopter writes their own against the same spec. The capability does NOT ship N implementations — bindings accrete per-language-adopter.
- **Methodology gap (surfaced):** COR-017 assumes capabilities ship _Python scripts run by the pkit CLI_; a capability whose deliverable is a _per-language adopter-imported library_ is a **new sub-shape** needing its own decision (a COR-017 extension) — landed at extraction, when it has a real consumer.
- **Timing — build-and-prove first, extract second (COR-007 + ADR-006's evolvability reasoning).** Extracting an unproven, unshipped discipline into a multi-language contract for one Python consumer is anticipation. So: (1) spec now + pkit binding; (2) Tier-1 proves the vocabulary on real commands; (3) extract `capabilities/cli/` on the stability trigger (conventions stop churning, or a 2nd consumer / language appears) + land the COR-017 extension then.
- **Reviewers:** run `critic` + `architect` on the concrete extraction plan (esp. the COR-017 extension) before committing.

## 9. Architecture (draft — building systematically)

### The shape: a 3-stage pipeline (the convergent pattern)
1. **Produce** — a command builds semantic **events** (tagged data from the vocabulary); it never formats strings.
2. **Select** — one renderer is chosen *at the command boundary* from context (TTY + `NO_COLOR`/`TERM` + flags).
3. **Render** — the selected renderer turns events → bytes (data → stdout; messages/progress/errors → stderr).

### The spec (language-agnostic canon)
- **Event model** — every output is `{type, …payload}`; `type` from the vocabulary (discriminated union); payload is **pure data** (no ANSI/layout); severity + render-hints are advisory attributes.
- **Vocabulary** — the closed core-10 `type`s (§7), each with a payload schema + a required rendering per mode. New `type`s ride the extension protocol.
- **Renderer contract** — a renderer maps `event → bytes`. Three obligations: **json** (canonical, byte-stable), **human** (styled TTY projection), **plain** (structure-only, ADR-011 zero-styling baseline).
- **Stream discipline** — data → stdout; messages/progress/logs/errors → stderr.
- **Extension protocol** — a new `type` implements the one-method renderable (human + plain; json auto from payload) + registers a name; **unknown `type` → structured-payload fallback**, never an error.

### The three renderers + selection
- **json** — the structured agent contract (byte-stable, versioned). · **human** — the styled TTY view. · **plain** — no-ANSI, pipe-safe baseline.
- **Selection (resolved once at the boundary):** explicit flag (`--json` / `--plain` / `--output …`) wins; else auto from `isatty(stdout)` + `NO_COLOR`/`TERM=dumb`.
- **Non-TTY default (decided): `plain`, with `json` opt-in via `--json`** — backward-compatible; keeps ADR-011's plain baseline as the default; agents pass `--json` (byte-stable, ADR-024). (json-by-default when a caller *signals* it's an agent is a possible future, on recurrence.)

### Flag surface (per the earlier architect guidance)
- `--json` → the json renderer (agent contract) · `--plain` → the plain renderer (clig.dev standard) · `--color auto|always|never` → colour within the human renderer (already exists).
- Don't overload `--color` with mode; **defer a tri-state `--output human|json|plain` enum** until the human view diverges structurally (it doesn't while the panels ban holds — architect's coupling: the mode enum and the panels ban stand or fall together).
- `--json`/`--plain` mutually exclusive; `--quiet`/`-q` suppresses non-essential events (info/success), never errors.

### pkit's binding (the Python realization)
- `cli_render.py` becomes pkit's **binding** of the spec: the event types + the human/plain renderers + the json serializer. ADR-006's parts ≈ the events; `view()` ≈ the human renderer; `--json` ≈ the json renderer.
- The excluded genres (install, next-steps, status) get expressed as **events** so they flow through the renderers — the architect's Tier-1, and the concrete first pain-fix.

### Requirement → architecture map
- **Human group** (scannable structure, intentional emphasis, wrapping, symbols, guidance, progress) → the **human renderer** (zones + colour roles + symbols + `wrap()`; `suggestions` / `progress` event types).
- **Machine group** (plain & stable, structured surface, same-info) → the **plain + json renderers** over the *same events*; same-info holds by construction; json byte-stable (ADR-024).
- **Cross-cutting** — one house style → the shared spec + renderers; no cost leak → human-only deps lazy-loaded on the human path; context-adaptive → the selection logic; quiet → `--quiet` filters events; streaming → incremental events (JSONL in json, append in human).
- **Agent-contract** — spans two layers:
  - _rendering:_ structured errors (`error` event → json on stderr), token efficiency (`--fields` / `--compact` on the json renderer), versioned schema (`schema_version` on json).
  - _command-layer (a **second** architecture layer):_ semantic exit codes, `--help --json` + hard-fail-unknown-flags, aggregate commands, the mutation protocol (`confirm-required` + envelope + `--confirm` — connects to `init`'s `--yes`/`--root`).
- **Takeaway:** the `cli` capability spans **two layers** — the **output vocabulary/renderers** *and* the **command-contract** (exit codes, help, unknown-flag, mutation). Both are part of the discipline.

### Sequencing (build-and-prove → extract)
1. **Stage 1 — the pain fix (now):** express install / next-steps (+ `status`) as events; build the human + plain renderers over them (extend `cli_render`). No json-default change, no new deps. Readability win; proves the vocabulary. _(= architect's Tier-1.)_
2. **Stage 2 — broaden:** migrate more commands to events; solidify the core-10 vocabulary + author the **spec as a schema**. The "conventions stopped churning" checkpoint.
3. **Stage 3 — agent-contract:** structured errors, semantic exit codes, `--help --json` + hard-fail-unknown-flags, token controls, mutation protocol, versioned schema.
4. **Stage 4 — extract the capability:** lift spec + reviewer + conformance into `capabilities/cli/`; pkit ADRs → parameters; land the COR-017 per-language-binding extension. On the stability / second-consumer trigger.

## 10. Decision: build the full discipline (maintainer) — critic corrections folded

Maintainer call (overriding critic's de-scope; critic is opposition, not veto): **build the full CLI-output discipline** — event model, vocabulary, renderers, toward the language-agnostic spec + `cli` capability — not just the minimal leaf-fix. The anticipation cost (one Python consumer, no second-language consumer yet) is accepted with eyes open; architect to structure it so **pkit's own binding is the proof and the per-language seam is *extensible, not pre-built*.**

**Critic's durable corrections — folded as build constraints (they hold regardless of scope):**
- **Retract the literal "structured when piped."** For pkit the dominant non-TTY consumer is the plain-text script/CI path; there is no general JSON surface to default to. Non-TTY default = **plain**; `--json` opt-in (decision A stands). (b) survives as *"the **event model** is the source of truth"*; the *default rendering* is plain, not JSON. Fix §1/§6 wording.
- **Two renderers, not three.** "Plain" is the *same* styled path with colour/width off (one gate, `strip_ansi(styled)==plain`), not a separate renderer. Renderers = the **styled path** (human↔plain via the colour/width gate) + a **`--json` serializer**. No second human/plain code path (drift).
- **The vocabulary is *evolving*, not "closed."** pkit's own genera break a closed core on contact (install = log/summary, `permissions diff` = change-preview → near-core; `status` pinned). Treat the core as a growing set (ADR-006's model-shaped-churn reality).
- **`status` is byte-parity-pinned** — exclude it, or migrate only behind its parity test. Not in the first slice.
- **ADR-006 deliberately excluded install/status/next-steps** as different genera — building the event model over them **amends ADR-006** (its exclusion + A′-vs-B/promotion-trigger reasoning). A conscious ADR change + maintainer sign-off, not a silent widening.
- **The command-contract (`--help --json`, semantic exit codes, mutation protocol) is a *second layer*** — kept in the discipline but sequenced separately, its own record(s).
- **Output-byte shifts need PRJ-002 changesets.**
- **§8 "spec-first now" reconciled:** author the spec *as we build and prove it in pkit* (pkit's binding is the reference); multi-language bindings + capability extraction still land on the stability trigger (Stage-4), not up front.
- **Sequencing correction:** prove the event model on a **settled** genre first (a stable read-view), *then* generalise to the churny install/next-steps genre.

**Next:** `architect` shapes the ADR reconciliation (amend ADR-006/011, reconcile ADR-024), the discipline's record structure, the sequencing, and the capability/spec/COR-017 shape — required now, because this modifies accepted foundational ADRs.
