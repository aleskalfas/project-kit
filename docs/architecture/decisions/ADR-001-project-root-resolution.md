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

- **The router resolves the boundary git-less and nearest-wins; commands resolve git-first and root-wins — they disagree in the nested case.** The pre-`click` entry-point router ([ADR-039](ADR-039-pkit-entry-point-router.md)) picks *which* pkit version/tree serves an invocation via `_enclosing_project` — a pure filesystem walk to the *nearest* `.git`/install-marked-`.pkit` boundary, deliberately git-less so the hot path spawns no subprocess. The two-stage command resolver above is git-*first*, so `git rev-parse` returns the *worktree root*. For every git-native topology these agree (a submodule or worktree has a `.git` entry, so the nearest-boundary walk stops exactly where `git rev-parse` does). They diverge only in the nested-`.pkit`-below-the-git-root case (the limitation above): the router selects the deeper subtree's version/pin while the command it dispatches then operates on the git root's `.pkit/` — a silent mis-target, not a crash. `pkit init`'s split-brain refusal (see below) now actively defends against *creating* that topology, but pre-existing or cloned instances of it remain resolvable inconsistently. Reconciling the two precedences (git-root-wins everywhere, or nearest-`.pkit`-wins everywhere) is the substance of the deferred monorepo-subproject support; that future ADR supersedes this bullet.

### Alternatives considered

- **`--root <path>` flag on every command, as default.** Rejected — adds a discoverable surface to every command's `--help`, increasing surface area for a need that's the exception, not the rule. Can be added later as an *optional* override (precedes the two-stage chain in resolution).

- **`PKIT_ROOT` environment variable.** Rejected — environment-variable-driven roots produce confusing behaviour when the variable is forgotten and stale across shells.

- **CWD-only: require cwd = root.** Rejected — breaks the common case of invoking pkit from a deeply-nested subdirectory.

- **`.pkit/`-walk only, no git involvement.** Rejected — doesn't handle pre-init (the `pkit init` command itself, which runs before `.pkit/` exists). A pure `.pkit/`-walk would force `pkit init` to take `--target` explicitly; the git-first path lets init resolve the surrounding git repo and bootstrap inside it.

- **`.git/`-walk only, no `git rev-parse` subprocess.** Rejected — worktrees have `.git` as a *file*, not a directory; a naive walk misses them. Reusing git is one subprocess; reimplementing git's resolution is many edge cases.

- **`pyproject.toml`-walk (like many Python tools).** Rejected — project-kit's adopters aren't necessarily Python projects. Tying root resolution to a Python-specific marker would prevent adoption by Go, Rust, or shell-only projects.

- **Project-root marker file (e.g., `.pkitroot`).** Rejected — adds a third marker file alongside `.git/` and `.pkit/` for the same purpose. The existing markers are sufficient.

## Implications

- The resolution *contract* (git-first, then walk-up) is single; its realisation now has three code paths that must stay in step. Post-init commands call `find_target_root()` and receive `Path | None`. `pkit init` calls a reason-returning sibling, `resolve_init_target()`, which applies the *same* two-stage order but (a) classifies the outcome (`GIT_ROOT` / `GIT_SUBFOLDER` / walk-up markers / `NONE`) so the consent gate can distinguish the happy path from an install at a resolved parent, and (b) never returns `None` — it falls back to CWD, because init runs *before* `.pkit/` exists and must be able to offer to init here (issue #780). The bash dispatcher carries a third mirror of the same order. These are one contract with two Python projections plus a shell mirror, not one function — so the "single-point change" property holds only if a change to the resolution order is applied to all three. Factoring the shared git-first-plus-walk-up mechanic into one helper that both Python entry points project from would restore the single-point property; it is a refactor the codebase has earned but not yet taken (COR-007).
- `pkit init` announces its resolved target on every run and confirms before installing anywhere other than CWD, refuses `--here` inside a git subfolder (a `.pkit/` there is unreachable — every command resolves to the git root), and refuses to create a second install that would straddle an existing one between CWD and the target (a split-brain). This is the first place the codebase actively *defends* the one-`.pkit/`-per-tree invariant this ADR's resolution model assumes rather than merely relying on it (issue #780).
- Commands receive `Path | None` from the resolver and decide the error message themselves: `pkit init` can phrase "the project doesn't exist yet"; `pkit status` phrases "not in a project tree". The contract gives commands the flexibility their context needs without expanding the resolver's API.
- An override mechanism — `--root` flag, `PKIT_ROOT` env var, or marker file — can be added later as a non-breaking extension: it would short-circuit ahead of the two-stage chain. The implicit-default-from-cwd contract stands as the floor.
- Adopters who symlink a `.pkit/` tree from outside their repo get the symlink's *target* directory as their root, not the symlink's location, because `git rev-parse --show-toplevel` resolves symlinks. Acceptable; not encountered in practice.

## Amendment 1 — the walk-up fallback is validated, not trusting; init resolves through a classified projection

*Status: accepted (2026-08-26). The body above remains accepted and in effect. This
amendment refines the *realisation* of the fallback and the return-contract *implication*
for one command (`pkit init`); it changes none of v1's standing decisions — implicit-from-cwd,
git-first-for-identity, and a fallback because project-kit does not require git all stand.*

**In one line:** the Stage-2 walk-up no longer trusts a bare `.git` on sight — it
*validates* each candidate is a real repository before accepting it, killing a live bug
where a workspace folder carrying a broken/vestigial `.git` was resolved as a project
root. `pkit init`, alone among commands, resolves through a projection that classifies
the walk into guided outcomes, because init carries a one-shot consent contract
(COR-004) the read-only commands do not.

**Why now — the live bug.** A user ran `pkit init` from a non-git subfolder of a
workspace folder whose `.git` is broken (git `rev-parse` fails there) and which has no
`.pkit/`. Stage 2 matched `(.git).exists()` and offered to install into the workspace
folder — a folder that is not a coherent project root (COR-001 binds the manifest to one
root; COR-004 makes init a one-shot bootstrap of that root). A workspace folder is not a
valid target, and a nested second install is deferred-monorepo territory.

### A1 — Stage 2 validates each candidate; it does not trust bare `.git`

v1's Stage 2 returned "the first ancestor with `.git/` or `.pkit/`." That trusted a
`.git` entry on existence alone. Amended: a candidate `.git` qualifies only when it is a
*real* repository.

- **Structural plausibility (subprocess-free, always available).** A `.git/` directory
  containing `objects/` + `refs/`, or a `.git` file that is a valid `gitdir:` worktree
  pointer, is plausible; a broken/vestigial `.git` is not and the walk continues upward.
  This is the shared correctness floor — it holds even when the `git` binary is absent,
  preserving v1's "does not require git" guarantee.
- **Authoritative validation (when git is present).** Where the walk must distinguish a
  *broken* `.git` from a *valid repository git environmentally refused* (safe.directory /
  dubious-ownership — routine in Docker/CI/sudo trees), `git -C <cand> rev-parse` is the
  authority, classified on exit status and structure, never on stderr prose.

This does **not** delete the fallback (that would break the no-git project v1 protects);
it validates it. A `.pkit/`-marked no-git project still resolves exactly as before — that
path never depended on `.git`.

### A2 — Two resolver altitudes; init projects a classified return

v1's Implications said "Commands receive `Path | None` from the resolver." That remains
true for the general resolver used by `sync` / `status` / `upgrade` / the authoring
commands: they want a *dumb* root-or-none answer and must not carry init's consent policy.

`pkit init` is different. It resolves through a projection that classifies the validated
walk into guided outcomes, because init is a one-shot consent act (COR-004):

- **INSTALL-HERE** — nothing found → install at cwd.
- **GIT_SUBFOLDER** — cwd is inside a *valid* repo below its root → target is the repo
  root; `--here` is refused as split-brain (a subfolder `.pkit/` is unreachable under
  git-toplevel resolution).
- **DUBIOUS-OWNERSHIP** — a valid repo git refused → **detect and guide** (surface the
  safe.directory remedy or an explicit target); never silently install a shadowed
  `.pkit/`.
- **PKIT-INSTALL ancestor** — an already-adopted project → **refuse and redirect to
  `pkit sync <ancestor>`**, consistent with init's one-shot / one-root meaning (COR-001 +
  COR-004). Nested-create is a *new capability*, deferred with the monorepo-subproject
  ADR, not a bugfix.

The shared correctness floor (reject broken `.git`) lives low and benefits every command;
the guided classification lives in init's projection only. The general resolver does not
grow a "dubious-ownership" state that read-only commands must interpret.

### A3 — Scope boundary: the router is intentionally left on bare `.git`, for now

`router.py::_enclosing_project` still matches bare `.git`. This amendment does **not**
change it. That divergence is benign by construction for the broken-`.git` case: a
workspace folder the router matches has no `.pkit/version-pin` and is not a source
checkout, so routing washes through to "run self" — the same action as no match. And the
router is, by ADR-039, the stdlib-only no-subprocess hot path; it cannot adopt the
command-side `git -C` validation as-is. Reconciling the three resolvers
(`find_target_root`, `resolve_init_target`, `_enclosing_project`) onto one shared
*subprocess-free structural* validator is recorded as a follow-up with the deferred
monorepo-subproject ADR — the router's real (non-benign) divergence is the
nearer-`.pkit`-wins split-brain that ADR settles, not this broken-`.git` axis.

### A4 — Alternatives considered (Amendment 1)

- **Delete the git walk-up entirely (only `rev-parse` + `.pkit/` walk).** Rejected —
  conflates a broken `.git` (the bug) with a valid `.git` git merely refused; the latter
  would fall through to install-here and drop a shadowed `.pkit/` inside a real repo,
  strictly worse than the bug being fixed.
- **Put the three-outcome classification in the shared `find_target_root`.** Rejected —
  leaks init's consent policy (COR-004) into the many read-only call sites; either they
  discard init-only states or the resolver grows a mode flag. Policy at the wrong
  altitude.
- **Drive the branch on parsed git stderr text.** Rejected — locale- and version-fragile;
  the outcomes are distinguishable structurally (repo layout + exit status). stderr may
  enrich the guidance message, never discriminate the branch.
- **Validate inside the router too, now.** Rejected for this change — violates ADR-039's
  no-subprocess hot-path contract; deferred to the 3-resolver reconciliation on a shared
  structural validator.

### A5 — Implications (Amendment 1)

- **One private git-first + walk-up + structural-validate helper; two projections.**
  `find_target_root` (→ `Path | None`) and `resolve_init_target` (→ classified reason)
  become thin projections over it (COR-007 — the third near-copy earns the extraction).
- **New failure-semantics surface.** Per-candidate validation is added; it preserves the
  no-git-on-PATH path (structural predicate when the binary is absent) and treats a git
  subprocess failure as "not a valid candidate here," consistent with Stage 1's existing
  fall-through.
- **Doc currency.** ADR-001's body "Commands receive `Path | None`" is scoped by this
  amendment to the general resolver; init's classified return is recorded here. The
  init-location scenario matrix (adoption scratchpad) becomes the resolution test suite.
- **Surface change → migration/version check.** Init's target-resolution behaviour
  changes observably; confirm `pkit migrations check-diff` coverage and declare the
  changeset with the implementation.
