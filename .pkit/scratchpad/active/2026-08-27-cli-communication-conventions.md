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

## 2. Problem

- For **humans**, today's output (especially procedural commands — the `init` install dump, the post-init next-steps, `status`) is a dense, flat, largely-unstyled wall: no visual hierarchy, hard to scan, hard to find the one line that matters.
- For **agents / scripts**, output must stay stable, plain, and parseable — and must not be degraded by making it prettier for humans.
- Today neither is served well: output is uniformly plain (tolerable for machines, poor for humans), while the obvious "make it pretty" move (boxes / heavy formatting) risks breaking the machine path.

## 3. Requirements (draft — reshape freely)

### Human-facing
- **H1** — scannable structure: clear sections / zones + visual hierarchy.
- **H2** — semantic emphasis / colour, used with intention (not everything coloured).
- **H3** — correct wrapping to terminal width.
- **H4** — symbols where they clarify (`✓ ⚠ →`).
- **H5** — guidance: surface the important line; suggest what to do next.

### Machine / agent-facing
- **M1** — non-TTY / pipe / CI output is plain, stable, greppable (no colour codes, animations, or width-reflow that breaks parsing).
- **M2** — a structured surface (JSON) for programmatic use, stable across environments.
- **M3** — **same information in every rendering** — nothing visible only in the pretty view.

### Cross-cutting
- **X1** — one consistent house style across all commands (not per-command ad-hoc).
- **X2** — the human / pretty path must not impose cost (startup latency, heavy deps) on the machine path.
- **X3** — adapt to context automatically (interactive vs not) + an explicit override.

## 4. Constraints (must respect)

- **K1** — evolve the accepted CLI architecture, don't ignore it: ADR-006 (data ↔ presentation split), ADR-011 (TTY styling + the "structure reads with zero styling" invariant), ADR-024 (wrapping + byte-stable JSON).
- **K2** — don't needlessly couple output to a heavy third-party lib's release cadence.
- **K3** — land incrementally; avoid a long half-migrated / inconsistent window.

## 5. Out of scope (confirm)

- Full-screen TUI / interactive full-screen programs.
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
