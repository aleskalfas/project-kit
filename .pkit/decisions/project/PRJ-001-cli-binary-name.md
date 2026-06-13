---
id: PRJ-001
title: CLI binary name is `pkit`
status: accepted
date: 2026-05-06
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

COR-004 ("CLI command surface") settles the design rules for project-kit's CLI but explicitly defers the binary's name to a PRJ-side decision in the implementing project. That implementing project is project-kit itself, so this record makes the choice.

The CLI is the surface adopters use to install, sync, merge, validate, and otherwise operate on a project-kit-adopting project. Every interaction with the methodology runs through this binary. Picking the name now lets dispatcher scripts, documentation, and adopter-facing material reference it concretely.

## Decision

The CLI binary's name is **`pkit`**.

## Rationale

Considered alternatives:

- **`pk`** — shortest. Rejected: too generic; collides with multiple existing tools (FreeBSD's `pk` package manager; various development utilities).
- **`pkit`** — short, mnemonic for "project-kit," lowercase consistent with most CLI binaries. No notable collisions with common tools. **Chosen.**
- **`projk`** / **`prkit`** — slightly longer, less mnemonic, no advantage over `pkit`.
- **`kit`** — clearest mnemonic but extremely generic; high likelihood of collision with other tooling and ambiguous in conversation ("kit" alone could mean anything).
- **`project-kit`** — exact methodology name. Rejected: too long for routine CLI use; hyphens are slightly awkward to type repeatedly.

`pkit` strikes the right balance: short enough for routine use, mnemonic for the methodology, distinctive enough to avoid collisions, lowercase per CLI convention.

## Implications

- The CLI dispatcher at `.pkit/cli/pkit` (and its eventual full-runtime equivalent) is named `pkit`.
- Adopter-facing documentation throughout the kit refers to the CLI as `pkit`.
- Future PRJs in project-kit's project namespace will cover related concerns: implementation language for the runtime, distribution channel (pip / Homebrew / curl-pipe-bash / GitHub releases / etc.), and version-management scheme.
