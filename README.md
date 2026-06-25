# project-kit

> A reusable methodology + workflow framework for AI-assisted projects.

**Status:** active — implemented and self-hosting (project-kit adopts its own methodology). The installable methodology lives under [`.pkit/`](.pkit/README.md); the current version is recorded in [`.pkit/VERSION`](.pkit/VERSION).

**CLI binary:** `pkit` (per [PRJ-001](.pkit/decisions/project/PRJ-001-cli-binary-name.md))

---

## What this is

`project-kit` packages a working methodology — workflow rules, a decision-record system, an agent matrix, hard rules, schemas, scripts — into something that can be installed into any project and kept in sync as the methodology evolves.

The pattern: when an improvement is made in one project (a clearer hard rule, a sharper agent prompt, a better schema), it lands in `project-kit` and propagates outward to the projects that have adopted it.

## What this is *not*

- Not a library. No imports from `project-kit` into runtime code. Other projects do not depend on it as a runtime artifact.
- Not a packaged product. It installs via a direct git URL — no registry (per [PRJ-004](.pkit/decisions/project/PRJ-004-distribution-channel.md)).
- Not a substitute for thinking. The methodology is opinionated but not exhaustive — projects still make their own architectural decisions (and record them as PRJ / ADR records).

## What's in the box

The kit installs / synchronises a fixed set of files and conventions into a target project under `.pkit/`, plus the host-side glue an AI harness expects. The areas:

- **[`decisions/`](.pkit/decisions/README.md)** — the decision-record system. Two namespaces: `core/` (kit-shipped, `COR-` prefixed) and `project/` (yours, `PRJ-` prefixed). Home of the no-shared-files invariant.
- **[`capabilities/`](.pkit/capabilities/)** — opt-in installable disciplines (per COR-017). `project-management` (issue lifecycle, board state machine, label axes, PR conventions), `evidence`, `software-engineering`. Adopters install the ones they need.
- **[`rules/`](.pkit/rules/README.md)** — universal hard rules + tool hygiene, loaded into every adopter's `CLAUDE.md`.
- **[`agents/`](.pkit/agents/README.md)** — agent definitions (persistent roles AI harnesses delegate against), deployed by the adapter.
- **[`skills/`](.pkit/skills/README.md)** — installable, harness-agnostic agent skills.
- **[`schemas/`](.pkit/schemas/README.md)** — YAML schemas + JSON Schema companions; the structured source of truth capabilities read at runtime.
- **[`adapters/`](.pkit/adapters/README.md)** — translate kit content into the format/locations a specific harness expects (`claude-code` today).
- **[`lifecycle/`](.pkit/lifecycle/README.md)** — packaging, manifest schema, upgrade + migration framework.
- **[`cli/`](.pkit/cli/README.md)** — the `pkit` command-line surface.

[`.pkit/README.md`](.pkit/README.md) is the adopter-facing entry point that maps these areas.

## Installation model

Two operations on a target project:

1. **`pkit init`** — first-time install. Propagates kit-owned content, seeds project-side files, and merges adapter-owned config into a fresh repo.

2. **`pkit sync`** — refresh kit-owned content in a project that's already initialised, without clobbering project-owned files (the no-shared-files invariant guarantees the two never collide).

Upgrades across kit versions go through **`pkit upgrade`**, which runs any migrations the new version ships (per COR-010).

## CLI sketch

`pkit` is implemented in Python (per [PRJ-003](.pkit/decisions/project/PRJ-003-implementation-language.md)). The principal commands:

```
pkit init                 First install: propagate + seed + merge.
pkit sync                 Refresh kit-owned content from the source kit.
pkit merge                Re-run merge delivery on adapter-owned config files.
pkit upgrade              Move the project to a newer backbone version (runs migrations).
pkit status               Show how project-kit is wired in this project.
pkit validate             Check project state against the kit's invariants.
pkit version [bump ...]   Show or bump the version.
pkit new <kind> ...       Scaffold a decision, adapter, migration, area, agent, capability, ...
pkit capabilities ...     Manage capabilities: list, install (kit-shipped), register (in-repo/incubated), ...
```

`pkit --help` lists the full surface (including `agents`, `schemas`, `migrations`, `scratchpad`, `permissions`, and per-capability subcommand groups such as `pkit project-management ...`). See [`.pkit/cli/README.md`](.pkit/cli/README.md) for the per-command contract.

## Where to go next

- **Adopting or navigating the kit:** [`.pkit/README.md`](.pkit/README.md) — maps every area; start at [`.pkit/decisions/README.md`](.pkit/decisions/README.md) for the foundational pattern.
- **Working on project-kit itself:** [`CONTRIBUTING.md`](CONTRIBUTING.md) — kit-maintainer guidance (the axiom / project-neutrality / principles-not-inventory disciplines, the acceptance gate, running checks). First clone: run `mise trust` once to enable the task runner (or run the `uv run ...` commands directly — mise is optional).
- **Session instructions for AI agents:** [`CLAUDE.md`](CLAUDE.md).
