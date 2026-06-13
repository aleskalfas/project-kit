---
id: PRJ-003
title: Implementation language for the install/sync runtime is Python
status: accepted
date: 2026-05-08
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

The bash dispatcher at `.pkit/cli/pkit` (per PRJ-001) is the bootstrap. It exposes `init`, `status`, `version (bump)`, `new decision`, `deploy-skills`, `merge-settings`. Per the implementation-status note in `.pkit/cli/README.md`, the full CLI surface specified by COR-004 — `sync`, `merge`, `upgrade`, `bundle list/install/remove`, the rest of `new`, `validate` — lands when a proper runtime ships per the build roadmap.

Bash will not carry that surface. Reasons that compound:

- **Manifest schemas** (per COR-010): the backbone manifest, per-component manifests, `package.yaml`. Reading and writing structured YAML safely (preserving comments, ordered keys, bounded edits) is well past `sed | grep` territory.
- **Version-resolution** (per COR-010 + the lifecycle README): walking `requires_backbone` ranges across multiple components, computing compatibility before applying migrations. Needs real semver parsing.
- **Argparse** for the full surface: subcommands (`pkit new bundle <area> <name>`), flags (`--dry-run`, `--scope <scope>`), help text, error reporting. Bash `case` statements scale poorly past today's two-level dispatch.
- **Validation** (COR-004's `pkit validate`): walking the manifest, checking the no-shared-files invariant, link validity, schema rules per area. Needs structured data handling.
- **Migration orchestration** (per COR-010): running scripts in scope-and-version order, idempotency tracking, version-recording into the manifest. Needs transactional thinking that bash does not support cleanly.

The runtime's authoring language is a project-kit-internal choice (the kit's binary is opaque to adopters; they consume the surface, not the source) — hence PRJ. But it shapes everything downstream: distribution channel (PRJ for, gated on this), startup cost (affects adopter UX), authoring cost (affects how fast the kit evolves), and the ecosystem the kit lives next to.

## Decision

**Python**, distributed via `uv tool install` (with `pip install` as fallback). Specifics:

- **Language**: Python 3.11+ (matches the floor that mainstream distributions and `uv` tools assume today; gives us `tomllib`, structural pattern matching, exception groups).
- **Packaging**: standard `pyproject.toml` with PEP 621 metadata; entry point `pkit = "project_kit.cli:main"`.
- **Dependencies**: kept minimal. Likely `ruamel.yaml` (round-trip YAML for manifest editing), `click` (or `typer` — a `click` wrapper) for the CLI, and `packaging` for semver / version-spec parsing.
- **Distribution channel**: deferred to a separate PRJ record (tracked as issue #6); this record fixes language only.

## Rationale

**Why Python.** The CLI's work is structured-data manipulation (YAML manifests, JSON settings, git invocations, subprocess control, filesystem walks). Python's standard library covers all of it directly — `pathlib`, `subprocess`, `json`, `argparse`, `tomllib` — with `ruamel.yaml` as the only essential third-party piece for round-trip-safe YAML editing. Authoring velocity for that kind of work is materially higher in Python than in Go or Rust.

**Why this matters for project-kit specifically.** The kit's near-term adopters (`example-brownfield`, `example-greenfield`) are Python projects. Cohesion with the adopter ecosystem is real value: contributors moving between adopter and kit code work in one language; debugging tools, type-checking conventions, and packaging patterns transfer.

**Why startup cost is acceptable.** Python cold-start is ~100–200 ms with `uv`'s lightweight launcher, ~50–100 ms warm. The CLI is invoked from terminals during deliberate development moments — not in tight loops, hooks, or pre-receive paths — so the cost is below the threshold a developer perceives as slow. (If profiling later shows a hot-path command crossing 500 ms cold, that command is a candidate for a Go or Rust subcommand, not a justification to retrofit the whole runtime.)

**Why `uv` for distribution.** `uv tool install project-kit` is the modern equivalent of `pipx install project-kit`: an isolated environment per tool, automatic Python-interpreter management, fast resolution. It avoids the global-pip foot-gun and the "which Python?" footwork. `pip install` and source-checkout symlink (today's bootstrap pattern) remain as fallbacks; `uv` is the recommended path.

**Why minimal third-party dependencies.** Each dependency is a future migration cost — every kit upgrade that crosses a dep's major version forces an adopter migration. A kit whose runtime depends on a small fixed set (round-trip YAML, semver, argparse-equivalent) keeps that surface narrow. The kit prefers stdlib where it suffices.

### Alternatives considered

- **Go** — Rejected. Single-static-binary distribution and ~5 ms startup are real wins, but: (a) authoring velocity is lower for the structured-data work the CLI mostly does; (b) ecosystem cohesion with Python adopters is lost; (c) cross-compilation and release-channel work (which we'd want to make distribution easy) is a real cost not yet justified; (d) the manifest layer's design (per COR-010) leans on round-trip-safe YAML, which is more mature in Python (`ruamel.yaml`) than in Go (`yaml.v3` is good but lossier on round-trips). The startup-cost advantage doesn't pay for the authoring-velocity loss at this stage.
- **Rust** — Rejected. Same single-binary advantages as Go, plus a richer type system. But authoring overhead (longer compile times, lifetime-management surface, dependency-tree weight) makes it the wrong choice for a project where the runtime is a means, not the end. Reconsider if a future hot path emerges.
- **TypeScript / Node** — Rejected. Node ubiquity is real; npm distribution for CLI tools is mature (`npx`, global installs). But: Node startup (~100–200 ms) without `uv`-equivalent isolation; the kit's adopters are not all Node projects; YAML round-tripping in JS is meh; the ecosystem is in a phase of churn (esm migrations, package-manager fragmentation) that adds adoption friction.
- **Stay with shell** — Rejected for the reasons in Context. Bash bootstrap is what we have today; it's appropriate for `init` + a handful of primitives. The full CLI surface needs structured data, argparse, semver, and orchestration — bash can technically do all of these and it would be a maintenance liability.
- **Multi-language (e.g., Go core + Python plugins)** — Rejected. Ergonomically tempting (binary core + scripted bundles) but the complexity of a stable IPC / plugin protocol exceeds the value at this scale. Adopters who want to author bundles or adapters write in Python alongside the kit; one language end-to-end is simpler.
- **Lean on `uv run script` style with no packaging** — Rejected. Lightweight but defeats the goal of `pkit` being installable as a regular CLI tool. `uv tool install` gives both lightweight install and a proper executable.

## Implications

- **The full COR-004 surface** (`sync`, `merge`, `upgrade`, `bundle …`, the rest of `new`, `validate`) is implemented in Python alongside or replacing the bash dispatcher. The bash dispatcher's commands graduate into the Python surface or are replaced; nothing is silently dropped.
- **`pyproject.toml`** lives at the project-kit repo root. Entry point: `pkit = "project_kit.cli:main"`. Source under `src/project_kit/` with conventional Python layout.
- **Adapter scripts (`deploy-skills.sh`, `merge-settings.sh`)** stay shell. They're harness-translation primitives invoked from the CLI; rewriting them in Python adds no value and removes useful POSIX-shell ubiquity.
- **Migrations** (per COR-010 and `.pkit/lifecycle/README.md`) stay shell. They're authored per-version, idempotency-checked locally, and live next to the contract they migrate. Python migrations would force a Python interpreter at upgrade time even for trivial mechanical changes.
- **Distribution channel** is a separate decision (a future PRJ record — see issue #6). Likely candidates: PyPI (public), a private artifact registry, Homebrew tap, or a `curl … | bash` installer. The language choice narrows the candidates but does not select one.
- **Adopter Python version requirements**: `pkit` ships with `requires-python = ">=3.11"`. Adopters whose projects target older Pythons are unaffected — `uv tool install` provisions an isolated Python for `pkit` regardless of the project's interpreter.
- **Authoring conventions**: per CLAUDE.md's existing references, the Python implementation follows conventional commits (COR-008), the principles-not-inventory rule, and the bump policy in PRJ-002. The Python layer doesn't change those.
- **Testing**: pytest, with the migration-script idempotency check as a first-class test pattern.
- **Type checking**: pyright or mypy in strict mode. Worth committing to a typed codebase from the first commit since the surface (manifests, version specs) is genuinely typed.
