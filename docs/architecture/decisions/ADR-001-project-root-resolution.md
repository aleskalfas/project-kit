---
id: ADR-001
title: Project root resolves implicitly from cwd; pkit is invocable from any subdirectory
status: accepted
date: 2026-05-27
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

Every `pkit` command operates against a *project root* — the directory that holds the project's installed methodology (and usually its version-control repository). A command must resolve that root before doing anything else: install writes inside it, refresh rewrites kit-owned content beneath it, status reports against it, the authoring commands stamp relative to it.

Users invoke `pkit` from wherever they happen to be — the repository root, a deep subdirectory, a freshly-cloned tree not yet initialised, occasionally from outside any project. How the root is resolved shapes the experience of every command: whether the user must remember a flag, set a variable, change directory first, or can simply run `pkit` where they stand.

## Decision

The CLI resolves the project root **implicitly from the current working directory** — no flag, no environment variable, no per-user config, no requirement to change directory first. Every command resolves the root before acting and fails cleanly when there is none.

The contract:

- **Input** — the current working directory, and nothing else.
- **Output** — exactly one project root, or none.
- **No side channels** — no environment variables, config files, or flags feed the resolution. (`init`'s `--root` is not an exception: it *replaces* the resolution with an explicit target rather than feeding a signal into it.)
- **Deterministic** — the same directory and filesystem state always resolve the same way.

### How the root is found

Resolution proceeds in two steps:

1. **Ask version control first.** git is the authority on which repository encloses a directory, and it answers correctly for the cases a hand-rolled search gets wrong — symlinked paths, linked worktrees, and submodules (each submodule is its own scope). When git identifies an enclosing repository, that repository's root *is* the project root.

2. **Otherwise, search upward — but trust only a genuine marker.** When there is no version control to consult (it isn't installed, or the directory isn't inside a repository), walk toward the filesystem root looking for a project marker: an installed methodology, or a repository. A marker is accepted **only when it is real** — an empty or broken repository marker is not a project and is passed over. This is what stops a *workspace folder* — a directory that merely *holds* repositories, sometimes carrying a defunct marker — from being mistaken for a project root. The upward search deliberately needs no version-control tool present, because project-kit does not require one.

If neither step finds a root, the command reports that it is not inside a project — with one exception: **install** offers the current directory, because it necessarily runs before any project exists.

### Two readings of the situation, for two kinds of command

The same resolution is surfaced at two levels, and the difference is *consent*:

- **Steady-state commands** (refresh, status, upgrade, the authoring commands) receive a plain answer — *this root, or none* — carrying no policy about what to do with it.

- **Install** is the one command that *creates* a project, so it is the one that makes a consent decision, and it reads the situation more richly and guides the user:
  - nothing found → offer to install in the current directory;
  - the current directory is *inside* a repository → the repository root is the target, and installing in a subfolder is refused (a project placed below the root would be shadowed by it and never resolved);
  - the directory looks like a real repository that version control declines to vouch for (an ownership restriction, say) → **guide the user to resolve it** rather than silently installing in the wrong place;
  - the current directory is already inside an adopted project → **refuse, and point the user at refresh** — install is a one-time bootstrap of a single root ([COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md)); a second, nested install is out of scope and deferred to the monorepo-support decision.

Only install carries this richer reading. The steady-state answer stays policy-free, so no ordinary command inherits install's consent rules.

## Rationale

**Why implicit resolution.** Every alternative adds friction to the common case — running `pkit` from a subdirectory of a known project. A flag adds a surface to every command's help; a variable goes stale when forgotten; requiring the user to change directory first breaks the most common workflow. Implicit resolution is the lowest-friction default, and an explicit override can be added later without breaking it.

**Why defer to version control first.** git already answers "where is the enclosing repository root?" and gets three awkward cases right: symlinked directories (resolved consistently), linked worktrees (whose marker is a file, not a directory), and submodules (each treated as its own independent scope). pkit inherits git's repository-boundary model rather than trying to reimplement or override it.

**Why keep a fallback.** project-kit does not *require* version control. A project used without it — or before it is initialised — must still resolve. The upward search serves that case.

**Why the fallback validates.** Trusting any marker on sight mistakes a directory that merely *contains* projects for a project itself. Validating that a marker is genuine closes that gap **without removing the fallback** — removing it would break the no-version-control case the fallback exists to serve. The correction is to verify, not to drop the search.

**Why two levels.** Deciding *where to create a project* is a consent act that belongs only to the command making it. Pushing that classification onto every read-only command would leak install's policy into places that need nothing more than a plain root. Keeping the rich reading inside install keeps the shared answer simple.

### Known limitations

- **A project installed *below* the repository root is invisible.** If the methodology is installed in a subdirectory of a larger repository, version control resolves to the *repository* root; the command looks for the project there, not deeper, and reports "not in a project" even though one exists further down. The standard layout — methodology installed at the repository root, no nested installs — avoids this. The motivating case for lifting it is a single repository that deliberately houses several independent projects in subfolders — each its own methodology scope, with its own configuration, capabilities, and decisions. Supporting that is the substance of the deferred monorepo-support decision: it must settle whether a project's scope may sit *below* the repository boundary at all, and — if so — which claim wins when a command runs from inside such a subfolder: the enclosing repository, or the nearer project.

- **The pre-dispatch router and the commands can disagree in that nested case.** A separate, deliberately lightweight resolver decides *which* installed version serves an invocation before a command runs ([ADR-039](ADR-039-pkit-entry-point-router.md)); for speed it uses a cheaper "nearest marker" rule and skips the genuine-marker validation the commands apply. For every ordinary repository layout the two agree. They diverge only in the nested case above — and even then the disagreement is harmless for a defunct marker, resolving to "run the tool itself," the same as no match. Bringing the router and the commands onto one shared rule, and settling which precedence wins when a project sits below a repository root, is the substance of the deferred monorepo-support decision, which supersedes this limitation.

### Alternatives considered

- **A root flag on every command, as the default.** Rejected — adds a surface to every command's help for a need that is the exception, not the rule. Can be added later as an optional override ahead of the implicit default.
- **An environment variable.** Rejected — a variable-driven root produces confusing behaviour when it is forgotten or stale across shells.
- **Require the current directory to be the root.** Rejected — breaks the common case of running `pkit` from a nested subdirectory.
- **Search for the installed methodology only, never consulting version control.** Rejected — it can't handle install, which runs *before* the project exists; install would have to be told its target explicitly.
- **Reimplement the repository search instead of asking git.** Rejected — linked worktrees and submodules are edge cases git already resolves; reimplementing them invites bugs for no gain.
- **Drop the fallback once version control has been consulted.** Rejected — this conflates a *broken* marker (the case validation fixes) with a *real* repository that version control merely declined to vouch for; the latter would end up installed in the wrong place, worse than the problem being fixed. Validate, don't delete.
- **Put install's guided classification into the shared resolver.** Rejected — leaks install's consent policy into read-only commands. The classification belongs to install alone.
- **Decide the broken-versus-declined case from version control's error text.** Rejected — error text is fragile across locales and tool versions; the distinction is available more robustly from the repository's own shape and whether the tool succeeded.
- **Run the genuine-marker validation in the lightweight pre-dispatch router too.** Rejected — the router must stay fast and dependency-free; unifying the resolvers is deferred with the monorepo-support decision.
- **A language-specific marker (e.g. a Python project file).** Rejected — adopters are not all Python projects; a language-specific marker would exclude others.
- **A dedicated root-marker file.** Rejected — adds a third marker for a job the existing two already do.

## Implications

- **One resolution rule, realised in more than one place.** The two-step rule is expressed by the shared read-only resolver and install's guided resolver — which now draw on one underlying implementation ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)) — plus a lightweight pre-dispatch mirror that stays intentionally cheaper (see *Known limitations*). A change to the resolution *order* must be applied everywhere it is mirrored.
- **Install actively defends the one-project-per-tree assumption this model rests on.** It announces its resolved target, confirms before installing anywhere but the current directory, refuses a subfolder install that would be shadowed, guides rather than mis-installs when a repository can't be vouched for, and refuses a second install that would straddle an existing one — redirecting an already-adopted tree to refresh instead.
- **Read-only commands get a plain root; install gets the guided reading.** Steady-state commands receive a root-or-none and phrase their own "not in a project" message; install consumes the richer classification so it can offer to install here and guide the subfolder, un-vouchable, and already-adopted cases — without that policy leaking into the shared answer.
- **An override can be added later** — a flag, an environment variable, or a marker file — as a non-breaking extension ahead of the implicit default; `init` already carries such an override today (`--root <path>`, scoped to that one command). The implicit-from-cwd contract is the floor.
- **Symlinked project trees resolve to their target directory**, because version control resolves symlinks to their real location. Acceptable; not encountered in practice.
- **A scenario matrix is the test suite.** The behaviour is pinned by the set of situations it must handle — install-here, inside-a-subfolder, the un-vouchable repository, the already-adopted ancestor, a project with no version control, and the broken-marker case the validation rejects — exercised against both resolvers.
