---
id: ADR-001
title: Project root resolves implicitly from cwd; pkit is invocable from any subdirectory
status: accepted
date: 2026-05-27
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

Every `pkit` command operates against a *project root* — the directory that contains `.pkit/` and usually `.git/`. The CLI must resolve this root before doing anything else: install reads/writes inside it; sync rewrites kit-owned trees beneath it; status reports against it; the authoring commands (`pkit new <kind>`) all stamp relative to it.

Users invoke `pkit` from varied working directories — the repo root, deep subdirectories, freshly-cloned trees not yet initialised, and occasionally from outside any project tree. The resolution shapes the user experience of every command: whether the user must remember a flag, set an environment variable, `cd` to root, or can simply invoke `pkit` from wherever they are.

This ADR captures behaviour already in production (the bash dispatcher established it; the Python port preserves parity). The proposed status is the acceptance-gate gesture per [PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md); the behaviour itself isn't under redesign here.

## Decision

The CLI resolves the project root *implicitly from cwd* — no `--root` flag, no `PKIT_ROOT` environment variable, no per-user config, no requirement to `cd` to the project root before invoking. Every command starts by calling a single resolver and refuses cleanly when the resolution returns nothing.

The contract:

- **Inputs**: the user's current working directory.
- **Outputs**: a single directory (the project root) or none.
- **No side channels**: the resolver doesn't read environment variables, config files, or flags. The cwd is the only input.
- **Idempotent**: same (cwd, filesystem state) always produces the same answer.

### Current realisation

A two-stage strategy implemented as `find_target_root()` in `src/project_kit/install.py`:

1. **Stage 1 — `git rev-parse --show-toplevel`.** Invoke git as a subprocess from cwd. If git returns 0, use the resolved-and-trimmed stdout.
2. **Stage 2 — directory-walk fallback.** If stage 1 fails (git not installed, cwd not inside a git repo, git returns non-zero), walk up the resolved cwd; return the first ancestor with `.git/` (as a directory) or `.pkit/` (as a directory).
3. **No resolution** — return `None`. Callers raise a context-appropriate "not in a project tree" error.

The two-stage shape originated in the bash dispatcher (where `git rev-parse` + a directory-walk is the idiomatic shape) and was preserved in the Python port. The realisation may evolve; the contract above is the architectural commitment.

## Rationale

**Why implicit resolution.** Every alternative imposes friction on the common case (running `pkit` from a subdirectory of a known project). A `--root` flag adds an extra discoverable surface to every command's `--help`; an environment variable adds stale-state confusion when forgotten; requiring `cd` to root breaks the most common workflow (running pkit from inside a deeply-nested subdir). Implicit resolution is the lowest-friction default; explicit override mechanisms can be added later as non-breaking extensions if a real use case emerges.

**Why git first.** `git rev-parse --show-toplevel` is git's canonical answer to "where is the repo root for this cwd?" and handles three non-trivial cases reimplementations get wrong:

- **Symlinked directories** — git returns the resolved path consistently.
- **Worktrees** — `.git` is a file (not a directory) inside a worktree; `--show-toplevel` returns the worktree root, not the main repo or the parent.
- **Submodules** — from inside a submodule, git returns the submodule root, not the parent repo. This means submodules are treated as independent pkit scopes: each can have its own `.pkit/` (or not), and operating from inside a submodule operates against the submodule's scope. The semantic choice is inherited from git's repo-boundary model; pkit doesn't try to override it.

**Why a fallback at all.** project-kit doesn't *require* git. A project that uses pkit without version control (or hasn't initialised git yet) should still resolve correctly. The directory-walk lets `pkit status`, `pkit validate`, etc. work without git on PATH.

### Known limitations

- **Nested `.pkit/` is invisible to git.** If `.pkit/` lives at `/path/to/sub/.pkit/` inside a larger git repo at `/path/to/.git/`, Stage 1 returns the git root (`/path/to`) — not the directory containing `.pkit/`. The command then looks for `.pkit/` at `/path/to/` and fails with "not in a project tree" even though pkit *is* installed deeper. Workaround: install `.pkit/` at the git root (the standard layout) or invoke from inside the `.pkit/`-containing subtree without leaving it.

This limitation is a bug only if encountered; the standard layout (`.pkit/` at the repo root, no nested installs) avoids it. A future `--root` flag (per the rejected alternative below) handles it as an override.

### Alternatives considered

- **`--root <path>` flag on every command, as default.** Rejected — adds a discoverable surface to every command's `--help`, increasing surface area for a need that's the exception, not the rule. Can be added later as an *optional* override (precedes the two-stage chain in resolution).

- **`PKIT_ROOT` environment variable.** Rejected — environment-variable-driven roots produce confusing behaviour when the variable is forgotten and stale across shells.

- **CWD-only: require cwd = root.** Rejected — breaks the common case of invoking pkit from a deeply-nested subdirectory.

- **`.pkit/`-walk only, no git involvement.** Rejected — doesn't handle pre-init (the `pkit init` command itself, which runs before `.pkit/` exists). A pure `.pkit/`-walk would force `pkit init` to take `--target` explicitly; the git-first path lets init resolve the surrounding git repo and bootstrap inside it.

- **`.git/`-walk only, no `git rev-parse` subprocess.** Rejected — worktrees have `.git` as a *file*, not a directory; a naive walk misses them. Reusing git is one subprocess; reimplementing git's resolution is many edge cases.

- **`pyproject.toml`-walk (like many Python tools).** Rejected — project-kit's adopters aren't necessarily Python projects. Tying root resolution to a Python-specific marker would prevent adoption by Go, Rust, or shell-only projects.

- **Project-root marker file (e.g., `.pkitroot`).** Rejected — adds a third marker file alongside `.git/` and `.pkit/` for the same purpose. The existing markers are sufficient.

## Implications

- The resolver is a single canonical function; all commands trust its answer and don't reimplement project-root logic. Changing the resolution strategy is a single-point change.
- Commands receive `Path | None` from the resolver and decide the error message themselves: `pkit init` can phrase "the project doesn't exist yet"; `pkit status` phrases "not in a project tree". The contract gives commands the flexibility their context needs without expanding the resolver's API.
- An override mechanism — `--root` flag, `PKIT_ROOT` env var, or marker file — can be added later as a non-breaking extension: it would short-circuit ahead of the two-stage chain. The implicit-default-from-cwd contract stands as the floor.
- Adopters who symlink a `.pkit/` tree from outside their repo get the symlink's *target* directory as their root, not the symlink's location, because `git rev-parse --show-toplevel` resolves symlinks. Acceptable; not encountered in practice.
