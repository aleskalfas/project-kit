---
id: COR-054
title: A project declares its default branch once, and every reader resolves it the same way
status: proposed
date: 2026-09-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Several parts of a project read what its default branch holds — its *settled state*. The friction change check compares a change with where it left its base (COR-050 point 6) — in practice the default branch. A component that numbers what it creates lets the first number to reach the default branch keep it, so it reads what the default branch holds. A work-tracking component cuts branches from the default branch and targets pull requests at it (COR-009).

Each of these used to find the default branch on its own. One read a name from its own settings and looked for the remote's copy of that branch first. Another assumed a fixed branch on the remote unless an environment variable named another. On a repository whose default branch has another name, or in a clone without the remote's copy, two components judging the same fact — has this reached the default branch? — read different commits, and neither says so.

## Decision

**A project declares its default branch once, in its backbone configuration. The backbone resolves it for every reader — the shared remote's copy, and the local branch only where there is no remote, saying so — and reports it when it resolves to nothing. A base named for one run of a comparison replaces it for that run only.**

1. **Declared once.** The backbone configuration (COR-048) gains a key owned by this record, `repository.default-branch`: the name of the branch the project's pull requests merge into (COR-009). The default is `main` (COR-008). It is written by the project's own edits, by the backbone's configuration commands under COR-048's consent rule, and by the upgrade migration of a component that kept a setting of its own for the branch, which carries a value other than the default over — running the upgrade is the consent (COR-048 point 5). No component keeps a setting of its own for it.

2. **Resolved one way.** A reader resolves the declared name to a commit in this order: the remote-tracking reference of the remote the project's shared work is pushed to — the branch's upstream, else in git's default layout `origin/<name>` — when it names a commit; else, only when the project has no such remote, the local branch of that name, and a reader that used the local branch says so, because a local branch can lag the shared one or carry work nobody pushed. Any branch named as a base resolves the same way. A reader that acts on the branch — cutting a branch from it, targeting a pull request at it — uses the name; a reader of what the branch holds uses the resolved commit.

3. **The override is a base, not a declaration.** A comparison against settled state — any check that compares a change with what the default branch holds — may be told to compare with another base for one run: on its command line, or through an environment variable a pipeline sets once for every such check (the checks' reference names it). The override replaces the default branch as *that run's base*, and nothing else. What the default branch is, for every other reader, is still the declaration: a pipeline pointing its checks at a pull request's target never moves where branches are cut from. A command that allocates from settled state rather than comparing with it — numbering a new artefact, say — reads the default branch, and any base named on its own command line, and allocates past both; the variable a pipeline sets for its checks never reaches it.

4. **Unresolved: report, never guess.** When the name resolves to no commit, the reader says so — the branch, the references it tried, and the fixes: fetch it, declare the right name, or name a base for the run. A comparison that needs the base fails rather than run without it; one with nothing to compare — nothing anchored, nothing numbered — needs no base and reports none. No reader falls back to another branch, to the checked-out branch or to a hosting service's answer.

5. **One computation, exposed.** The backbone computes the resolution in one place and exposes it through one reading command, in machine-readable form, as its other readings are (COR-050, Implications): the default branch, and a comparison's base with where the current branch left it. A component's own script reads it there, as it reads the declared places (COR-050 point 1). It never reads the declaration, the override or a remote's reference itself, and never computes where its branch left the base.

## Rationale

**Why declare it.** The default branch is a fact about the project, like its name (COR-048). Several components need it and none owns it; declared per component, it is described several times and drifts. Deriving it was considered instead. Git's record of the remote's default branch is written by a clone, but not in a repository created locally and pushed, and many pipeline checkouts leave it out; a hosting service answers only over the network, and differently per service. A declaration is the same in every clone, needs no network and is checked by validation.

**Why the remote's copy first.** The remote-tracking reference is the last known state of the shared branch — what everyone's work landed on. The branch's upstream names that remote whatever it is called; `origin` is the name git gives it by default. A local branch of the same name lags the shared one until someone updates it, or carries commits nobody pushed.

**Why the local branch only without a remote.** In a repository with no remote — one not yet published — the local branch is the only copy there is. Where a remote exists but its copy is missing — a clone that fetched one branch, a default branch renamed on the host — the local branch would be a stale or private stand-in that looks like the shared one, so the reader reports instead, and the fix is one fetch away.

**Why the override is only a base.** A pipeline points its comparisons at a pull request's target, which is not always the default branch — an integration branch, say. That is right for the comparison and wrong for everything else. If the override redefined the default branch, where a branch is cut from would depend on a variable set for a check. Allocation is the sharpest case: a number allocated past an integration branch but not past the default branch can collide where the work lands, so allocation always reads the default branch and adds only a base its own caller names.

**Why report rather than guess.** A comparison against the wrong base answers a different question and looks like an answer. Friction results already hold only against an up-to-date base (COR-050 point 6); a guessed base is worse than an outdated one, because nothing marks it.

**Why one computation.** Two resolutions drift: one that looks at the remote first and one that assumes a fixed name disagree exactly on the repositories where it matters. Components judging the same fact read the same commit only when they read the same answer.

### Alternatives considered

- **State that the check base is the default branch, and keep no key.** Rejected: a project whose default branch has another name would set the environment variable everywhere a check runs, and a component that needs the branch's *name* — to cut a branch from it — would still have nothing to read.
- **Derive the name from the remote or the hosting service.** Rejected; see Rationale.
- **The local branch first.** Rejected: a stale or unpushed local branch would silently become the settled state.
- **The local branch whenever the remote's copy is missing.** Rejected: where a remote exists, a missing copy is a clone to fetch, not a reason to read a branch that may lag it.
- **Declare the remote too.** Deferred until a project needs it: the branch's upstream already names a remote with another name, and `origin` covers git's default layout.
- **Let the environment variable redefine the default branch.** Rejected; see Rationale.
- **Fall back to another branch when nothing resolves.** Rejected: a guess, unmarked.
- **Keep each component's own setting.** Rejected: the drift this record removes.

## Implications

- **The backbone configuration's schema** gains the key; validation checks that its value is a branch name git accepts, and not a remote's or a full reference. An absent key means `main`, so a project on `main` changes nothing.
- **The change check's default base** is the resolved default branch: in a repository without a remote it compares with the local branch and says so, and in a project that declares another name, with that branch.
- **The backbone's reading command** exposes the resolution and the base, so a component's scripts — the commands a data point's filler runs included, which take no argument (COR-052) — read settled state without resolving anything.
- **A component that kept its own setting** retires it with an upgrade migration that carries a value other than the default over (point 1).
- **A remote not named `origin`** is found only through the branch's upstream: in a clone whose default branch tracks nothing and whose only remote has another name, the reader takes the local branch and says so.
- **COR-008's default branch** stays `main` as its recommendation and this key's default; a project whose default branch has another name declares it here instead of renaming it.
- **The reference** — the override's name and the reading command's fields — lives in the CLI reference.
