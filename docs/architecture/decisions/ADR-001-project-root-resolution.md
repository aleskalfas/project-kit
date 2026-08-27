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

A two-stage strategy — `git rev-parse` first, a *validated* directory-walk second — projected through two entry points that share one underlying walk (`find_target_root()` and `resolve_init_target()` in `src/project_kit/install.py`):

1. **Stage 1 — `git rev-parse --show-toplevel`.** Invoke git as a subprocess from cwd. If git returns 0, use the resolved-and-trimmed stdout.
2. **Stage 2 — validated directory-walk fallback.** If Stage 1 fails (git not installed, cwd not inside a git repo, git returns non-zero), walk up from the resolved cwd. A `.pkit/` directory qualifies an ancestor on sight — that path never depended on `.git`. A `.git` entry qualifies an ancestor **only when it is a real repository**: the walk *validates* each candidate rather than trusting a bare `.git` on existence alone (see *Why Stage 2 validates* below). A broken or vestigial `.git` does not qualify, and the walk continues upward.
3. **No resolution** — the general resolver returns `None`, and callers raise a context-appropriate "not in a project tree" error. `pkit init` is the exception: it never returns `None`, falling back to cwd because it runs *before* `.pkit/` exists and must be able to offer to init here (issue #780).

The two-stage shape originated in the bash dispatcher (where `git rev-parse` + a directory-walk is the idiomatic shape) and was preserved in the Python port; the bash dispatcher still carries a third mirror of the same order. The realisation may evolve; the contract above is the architectural commitment.

**Why Stage 2 validates, and how.** Trusting a bare `.git` on sight mis-resolves a real case: a non-git subfolder of a *workspace folder* whose `.git` is broken (git `rev-parse` fails there) and which carries no `.pkit/`. An unvalidated walk matches that `.git` and offers to install into the workspace folder — a folder that is not a coherent project root ([COR-001](../../../.pkit/decisions/core/COR-001-content-mechanisms.md) binds the manifest to one root; [COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md) makes init a one-shot bootstrap of that root). Validation closes this **without deleting the fallback** — deleting it would break the no-git project the fallback exists to serve, and a `.pkit/`-marked no-git project still resolves exactly as before:

- **Structural plausibility (subprocess-free, always available).** A `.git/` directory containing `objects/` + `refs/`, or a `.git` file that is a valid `gitdir:` worktree pointer, is plausible; a broken/vestigial `.git` is not. This is the shared correctness floor — it holds even when the `git` binary is absent, preserving the "does not require git" guarantee below.
- **Authoritative validation (when git is present).** Where the walk must distinguish a *broken* `.git` from a *valid repository git environmentally refused* (safe.directory / dubious-ownership — routine in Docker / CI / sudo trees), `git -C <candidate> rev-parse` is the authority, classified on exit status and repo structure, never on stderr prose.

**Two projections over one walk.** The shared git-first-plus-validated-walk mechanic is exposed at two altitudes. `find_target_root()` returns a *dumb* `Path | None` — the answer `sync` / `status` / `upgrade` / the authoring commands want; they must not carry init's consent policy. `pkit init` resolves through `resolve_init_target()`, which classifies the *same* validated walk into guided outcomes, because init is a one-shot consent act (COR-004):

- **INSTALL-HERE** — nothing found → install at cwd.
- **GIT_SUBFOLDER** — cwd is inside a *valid* repo below its root → target is the repo root; `--here` is refused as split-brain (a subfolder `.pkit/` is unreachable under git-toplevel resolution).
- **DUBIOUS-OWNERSHIP** — a valid repo git refused → **detect and guide** (surface the safe.directory remedy or an explicit target); never silently install a shadowed `.pkit/`.
- **PKIT-INSTALL ancestor** — an already-adopted project → **refuse and redirect to `pkit sync <ancestor>`**, consistent with init's one-shot / one-root meaning (COR-001 + COR-004). Nested-create is a *new capability*, deferred with the monorepo-subproject ADR, not a bugfix.

The shared correctness floor (reject a broken `.git`) lives low and benefits every command; the guided classification lives in init's projection only. The general resolver does not grow a "dubious-ownership" state that read-only commands would have to interpret.

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

- **The router resolves the boundary git-less and nearest-wins; commands resolve git-first and root-wins — they disagree in the nested case.** The pre-`click` entry-point router ([ADR-039](ADR-039-pkit-entry-point-router.md)) picks *which* pkit version/tree serves an invocation via `_enclosing_project` — a pure filesystem walk to the *nearest* `.git`/install-marked-`.pkit` boundary, deliberately git-less so the hot path spawns no subprocess. The two-stage command resolver above is git-*first*, so `git rev-parse` returns the *worktree root*. For every git-native topology these agree (a submodule or worktree has a `.git` entry, so the nearest-boundary walk stops exactly where `git rev-parse` does). They diverge only in the nested-`.pkit`-below-the-git-root case (the limitation above): the router selects the deeper subtree's version/pin while the command it dispatches then operates on the git root's `.pkit/` — a silent mis-target, not a crash. `pkit init`'s split-brain refusal (see below) actively defends against *creating* that topology, but pre-existing or cloned instances of it remain resolvable inconsistently. On a second axis — candidate *validation* — the router likewise stays on bare `.git`: `_enclosing_project` matches a `.git` entry structurally and does **not** run the command-side `git -C` validation, because by [ADR-039](ADR-039-pkit-entry-point-router.md) it is the stdlib-only, no-subprocess hot path and cannot adopt that check as-is. That divergence is benign by construction for the broken-`.git` case: a workspace folder the router matches carries no `.pkit/` version-pin and is not a source checkout, so routing washes through to "run self" — the same action as no match. Reconciling all three resolvers (`find_target_root`, `resolve_init_target`, `_enclosing_project`) onto one shared subprocess-free *structural* validator is recorded as a follow-up with the deferred monorepo-subproject ADR. Reconciling the two precedences (git-root-wins everywhere, or nearest-`.pkit`-wins everywhere) is the substance of that deferred support; the router's only *non-benign* divergence is the nearer-`.pkit`-wins split-brain that future ADR settles — not this broken-`.git` axis — and that ADR supersedes this bullet.

### Alternatives considered

- **`--root <path>` flag on every command, as default.** Rejected — adds a discoverable surface to every command's `--help`, increasing surface area for a need that's the exception, not the rule. Can be added later as an *optional* override (precedes the two-stage chain in resolution).

- **`PKIT_ROOT` environment variable.** Rejected — environment-variable-driven roots produce confusing behaviour when the variable is forgotten and stale across shells.

- **CWD-only: require cwd = root.** Rejected — breaks the common case of invoking pkit from a deeply-nested subdirectory.

- **`.pkit/`-walk only, no git involvement.** Rejected — doesn't handle pre-init (the `pkit init` command itself, which runs before `.pkit/` exists). A pure `.pkit/`-walk would force `pkit init` to take `--target` explicitly; the git-first path lets init resolve the surrounding git repo and bootstrap inside it.

- **`.git/`-walk only, no `git rev-parse` subprocess.** Rejected — worktrees have `.git` as a *file*, not a directory; a naive walk misses them. Reusing git is one subprocess; reimplementing git's resolution is many edge cases.

- **Delete the git walk-up entirely (Stage 1 `rev-parse` + a `.pkit/`-only walk).** Rejected — conflates a *broken* `.git` (the case validation fixes) with a *valid* `.git` git merely refused; the latter would fall through to install-here and drop a shadowed `.pkit/` inside a real repo, strictly worse than the bug being fixed. Validation, not deletion, is the right correction.

- **Put the guided outcome classification in the shared `find_target_root`.** Rejected — leaks init's consent policy (COR-004) into the many read-only call sites; either they discard init-only states or the resolver grows a mode flag. Policy at the wrong altitude. The classification lives in init's `resolve_init_target` projection instead.

- **Drive the broken-vs-refused branch on parsed git stderr text.** Rejected — locale- and version-fragile; the outcomes are distinguishable structurally (repo layout + exit status). stderr may enrich the guidance message, never discriminate the branch.

- **Run the `git -C` validation inside the router too.** Rejected — violates [ADR-039](ADR-039-pkit-entry-point-router.md)'s no-subprocess hot-path contract; the router stays on the structural predicate, and the three-resolver reconciliation onto one shared subprocess-free validator is deferred with the monorepo-subproject ADR (see *Known limitations*).

- **`pyproject.toml`-walk (like many Python tools).** Rejected — project-kit's adopters aren't necessarily Python projects. Tying root resolution to a Python-specific marker would prevent adoption by Go, Rust, or shell-only projects.

- **Project-root marker file (e.g., `.pkitroot`).** Rejected — adds a third marker file alongside `.git/` and `.pkit/` for the same purpose. The existing markers are sufficient.

## Implications

- **One contract, three code paths.** The resolution contract (git-first, then a *validated* walk-up) is single; its realisation runs three mirrors that must stay in step: `find_target_root()` (→ `Path | None`), `resolve_init_target()` (→ a classified reason, applying the *same* order and classifying it into the guided outcomes listed under *Current realisation*, never returning `None`), and the bash dispatcher. These are one contract with two Python projections plus a shell mirror, not one function — so the "single-point change" property holds only if a change to the resolution order is applied to all three. Factoring the shared git-first-plus-validated-walk mechanic into one private helper both Python entry points project from would restore that property; the third near-copy earns the extraction ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)), a refactor the codebase has earned but not yet fully taken.
- **init actively defends the one-`.pkit/`-per-tree invariant.** `pkit init` announces its resolved target on every run and confirms before installing anywhere other than cwd; refuses `--here` inside a git subfolder (a `.pkit/` there is unreachable — every command resolves to the git root); detects a dubious-ownership repo and **guides** rather than dropping a shadowed `.pkit/`; and refuses a second install that would straddle an existing one between cwd and the target (a split-brain), **redirecting** an already-adopted ancestor to `pkit sync`. This is the first place the codebase actively *defends* the invariant this ADR's resolution model assumes rather than merely relying on it (issue #780). The classified outcomes that drive these gates are the ones listed under *Current realisation*.
- **The general resolver returns `Path | None`; init resolves through the classified projection.** Read-only and post-init commands (`sync` / `status` / `upgrade` / the authoring commands) receive `Path | None` from `find_target_root()` and decide the error message themselves — `pkit status` phrases "not in a project tree." `pkit init` does **not** consume that return: it resolves through `resolve_init_target()`'s classified reason (above), so it can phrase "the project doesn't exist yet," offer to init here, and guide the subfolder / dubious / already-adopted cases. Keeping the classified reason out of the shared resolver gives read-only commands the flexibility their context needs without expanding that resolver's API or leaking init's consent policy into it.
- **A per-candidate failure-semantics surface.** Stage 2's validation runs per candidate: it preserves the no-git-on-PATH path (the structural predicate when the binary is absent) and treats a git subprocess failure as "not a valid candidate here," consistent with Stage 1's existing fall-through.
- **An override mechanism** — `--root` flag, `PKIT_ROOT` env var, or marker file — can be added later as a non-breaking extension: it would short-circuit ahead of the two-stage chain. The implicit-default-from-cwd contract stands as the floor.
- **Symlinked `.pkit/` trees resolve to the target directory.** Adopters who symlink a `.pkit/` tree from outside their repo get the symlink's *target* directory as their root, not the symlink's location, because `git rev-parse --show-toplevel` resolves symlinks. Acceptable; not encountered in practice.
- **The scenario matrix is the test suite.** The resolution model's behavioural coverage is the init-location scenario matrix — INSTALL-HERE, GIT_SUBFOLDER, DUBIOUS-OWNERSHIP, PKIT-INSTALL ancestor, a no-git `.pkit/`-marked project, and the broken/vestigial `.git` case Stage 2's validation rejects — exercised against both `find_target_root()` and `resolve_init_target()`.
