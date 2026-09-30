---
id: COR-054
title: A project declares its default branch once, and every reader resolves it the same way
status: proposed
date: 2026-09-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Several parts of a project read what its default branch holds — its *settled state*. The friction change check compares a change with the point where it left the default branch (COR-050 point 6). A component that numbers what it creates lets the first number to reach the default branch keep it, so it reads what the default branch holds. A work-tracking component cuts branches from the default branch and targets pull requests at it (COR-009).

Each of these used to find the default branch on its own. One read a name from its own settings and looked for the remote's copy of that branch first. Another assumed a fixed branch on the remote unless an environment variable named another. On a repository whose default branch has another name, or in a clone without the remote's copy, two components judging the same fact — has this reached the default branch? — read different commits, and neither says so.

## Decision

**A project declares its default branch once, in its backbone configuration. The backbone resolves it for every reader — the remote's copy first, then the local branch — and says so when neither exists. A base named for one run of a comparison replaces it for that run only.**

1. **Declared once.** The backbone configuration (COR-048) gains a key owned by this record, `repository.default-branch`: the name of the branch the project's settled work lands on. The default is `main`. It is written by the project's own edits, or by the backbone's configuration commands under COR-048's consent rule. No component keeps a setting of its own for it. A component that kept one before this record reads the backbone's instead, and may keep its own only as a deprecated alias: the alias never overrides a declared value, and it warns wherever it is still read.

2. **Resolved one way.** A reader resolves the declared name to a commit in this order: the remote-tracking reference of the repository's conventional remote (in git, `origin/<name>`), when it names a commit; else the local branch of that name. A reader that acts on the branch — cutting a branch from it, targeting a pull request at it — uses the name; a reader of what the branch holds uses the resolved commit.

3. **The override is a base, not a declaration.** A comparison against settled state — a change check, or a check that compares numbers — may be told to compare with another base for one run: on its command line, or through an environment variable a pipeline sets once for every such check (the checks' reference names it). The override replaces the default branch as *that run's base*, and nothing else. What the default branch is, for every other reader, is still the declaration: a pipeline pointing its checks at a pull request's target never moves where branches are cut from.

4. **Neither resolves: report, never guess.** When neither reference names a commit, the reader says so — the branch, both references it tried, and the fixes: fetch it, declare the right name, or name a base for the run. A comparison that needs the base does not run without it, as the change check does not run on a base that does not resolve; one with nothing to compare leaves the base out. No reader falls back to another branch, to the checked-out branch or to a hosting service's answer.

5. **One computation, exposed.** The backbone computes the resolution in one place and exposes it through its reading commands: the declared name and whether it was declared or defaulted, the reference and commit it resolves to, and, for a comparison, the base in effect, where it came from (the run, the environment or the declaration), its commit and the point where the current branch left it. A component's own script reads it there, as it reads the declared places (COR-050 point 1). It never reads the declaration, the override or the remote's reference itself, and never computes where its branch left the base.

## Rationale

**Why declare it.** The default branch is a fact about the project, like its name (COR-048). Several components need it and none owns it; declared per component, it is described several times and drifts. Deriving it was considered instead. Git's record of the remote's default branch is written by a clone, but not in a repository created locally and pushed, and many pipeline checkouts leave it out; a hosting service answers only over the network, and differently per service. A declaration is the same in every clone, needs no network and is checked by validation.

**Why the remote's copy first.** The remote-tracking reference is the last known state of the shared branch — what everyone's work landed on. A local branch of the same name lags it until someone updates it, or carries commits nobody pushed. The local branch is the fallback for a clone with no remote, such as a repository not yet published.

**Why the override is only a base.** A pipeline points its comparisons at a pull request's target, which is not always the default branch — an integration branch, say. That is right for the comparison and wrong for everything else. If the override redefined the default branch, where a branch is cut from would depend on a variable set for a check.

**Why report rather than guess.** A comparison against the wrong base answers a different question and looks like an answer. Friction results already hold only against an up-to-date base (COR-050 point 6); a guessed base is worse than an outdated one, because nothing marks it.

**Why one computation.** Two resolutions drift: one that looks at the remote first and one that assumes a fixed name disagree exactly on the repositories where it matters. Components judging the same fact read the same commit only when they read the same answer.

### Alternatives considered

- **State that the check base is the default branch, and keep no key.** Rejected: a project whose default branch has another name would set the environment variable everywhere a check runs, and a component that needs the branch's *name* — to cut a branch from it — would still have nothing to read.
- **Derive the name from the remote or the hosting service.** Rejected; see Rationale.
- **The local branch first.** Rejected: a stale or unpushed local branch would silently become the settled state.
- **Let the environment variable redefine the default branch.** Rejected; see Rationale.
- **Fall back to another branch when neither resolves.** Rejected: a guess, unmarked.
- **Keep each component's own setting.** Rejected: the drift this record removes.

## Implications

- **The backbone configuration's schema** gains the key; validation checks that its value is a branch name. An absent key means `main`, so a project on `main` changes nothing.
- **The change check's default base** becomes the resolved default branch. It used to be a fixed branch on the remote: in a clone without the remote's copy the check now compares with the local branch rather than refusing, and in a project that declares another name it compares with that branch.
- **The backbone's reading commands** expose the resolution and the base, so a component's scripts — the commands a data point's filler runs included, which take no argument (COR-052) — read settled state without resolving anything.
- **A component that kept its own setting** aliases it with a deprecation warning, or retires it with a migration where retiring it would change what an installed project reads.
- **The reference** — the key in the configuration section, the override's name, the reading command's fields — lives in the CLI reference, not here.
