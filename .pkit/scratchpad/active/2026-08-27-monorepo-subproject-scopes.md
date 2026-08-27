---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-27
---

# Monorepo subproject scopes

## The question

May an independent pkit scope sit **below** a repository root — and if so, which claim wins when a command runs from inside such a subfolder: the enclosing repository, or the nearer project? Settling that (and reconciling the resolvers that currently answer it differently) is the substance of the deferred **monorepo-support decision**. This note maps the space; it produces a future ADR (which will *supersede* ADR-001's boundary premise), not a decision on its own.

Seeded from the ADR-001 rework under #787 (adoption effort) + an architect consult (2026-08-27). Relates to ADR-001 (project-root resolution — this supersedes two of its known-limitation bullets), ADR-039 (the entry-point router), COR-001 (no-shared-files), COR-012 (this note's carrier), COR-007 (build-on-recurrence — the gate for *when* to actually build this).

## Motivating use case (maintainer's, in their words)

A single git repository that deliberately houses **many projects in subfolders**, where **each subfolder-project is its own independent pkit scope with its own configuration** — e.g. generating a per-project "competitive analysis" for each, each project potentially configured differently (different capabilities, workstreams, decisions). Standing in a given subfolder and running `pkit` should operate against *that* subfolder-project.

## What already works today (so it is OUT of scope)

The architect consult established the door is **open, not foreclosed** — and more is already delivered than expected:

- **Git submodule sub-scopes work fully, today, with zero new code.** git scopes each submodule as its own worktree root, so *every* resolver (router and command) agrees on the submodule scope. If the subfolder-projects can be submodules, the use case is already met. The genuine gap is only **plain** subfolders (no nested `.git`).
- **Per-project config is native.** Each project root carries its own manifest, installed capabilities, workstreams, adapter settings, decisions namespace, agents overlay. The "each configured differently" requirement needs no new machinery — its no-inheritance semantic *is* the independence the use case wants.
- **Per-project version pins are native.** The router already honours a per-root pin, so heterogeneous pkit versions across sub-projects come for free.
- **The router is already nearest-marker-wins.** Its pre-dispatch walk stops at the nearest installed `.pkit/` (checking it before `.git`), so it *already* returns the nested subproject scope. It is the *command* resolver (git-first → repo-root-wins) that is the outlier.

**Still uncovered** (the actual work): the command resolver's precedence for plain subfolders; relaxing the init subfolder guard so an independent subfolder scope is first-class rather than refused; any cross-root "operate on all sub-projects" surface.

## Forces

- **git-first correctness vs nearest-marker flexibility.** git-first gets worktrees/submodules/symlinks right and is the reason ADR-001 defers to it; nearest-marker is what plain-subfolder scopes need. The two collide only in the nested-below-repo-root case.
- **Backward-compat vs ceremony.** A pure nearest-marker rule risks *silently shadowing* an enclosing repo for any existing adopter who happens to have a nested `.pkit/`; a repo-level opt-in avoids that at the cost of one declaration file.
- **Resolver divergence is real and named.** Router = nearest-marker (cheap, no subprocess, ADR-039 hot path); command resolver = git-first (validated). They already disagree in exactly the monorepo case. Reconciliation should align *precedence* (nearest wins) while keeping *rigor* different (router bare-existence, commands validated) — that split is healthy.
- **`--root` already reaches an un-serviceable state.** `pkit init --root <subfolder>` creates a nested `.pkit/` today (no subfolder guard on that path), but steady-state commands run from inside it resolve to the git root and report "not in a project." The decision closes that coherence gap; meanwhile `--root` arguably should *warn* when the target sits below a git root.
- **Fan-out surface.** N sub-projects means N independent `sync`/`upgrade`/pin operations. A workspace-level "operate on all sub-scopes" verb is a *new surface* — charter it or explicitly defer.
- **Discoverability.** Standing in the repo root (no `.pkit/`) with projects in subfolders yields "not in a project" — correct but confusing; a workspace-aware `status` that lists sub-scopes is a possible new surface.

## Candidate approaches (enumerate, don't choose)

- **(A) Nearest-validated-marker-wins, layered above git-first.** Walk up for the nearest install-marked `.pkit/` first (existing install-validation), fall back to git-first. Unifies all three resolvers onto the router's already-proven rule; backward-compatible for the standard layout (the nearest `.pkit/` *is* the repo root). Risk: a nested `.pkit/` now shadows the enclosing repo for existing adopters (rare). Architect's lean.
- **(B) A dedicated per-subfolder scope marker.** Collapses into (A) — the `.pkit/` install already *is* the marker; likely unnecessary.
- **(C) Repo-level "multi-project workspace" declaration.** A repo-root marker opts *into* nearest-marker below it; git-first stays the default everywhere else. Zero behaviour change for existing adopters, at the cost of one ceremony file. Safest backward-compat.

The genuine fork is **(A) pure nearest-marker vs (C) opt-in workspace**. Scope the decision to *plain subfolders* (submodules already work); state whether the two should look identical to the user.

## What the future ADR supersedes

ADR-001's premise — "git is the authority on which repository encloses a directory… that repository's root *is* the project root" — becomes "…unless a nearer project scope sits below it." This is a **foundational-decision change**: the monorepo-support ADR must carry the *explicit supersession gesture* (frontmatter `supersedes:` + leading supersession note per the decisions README), never a silent rewrite. It supersedes both of ADR-001's known-limitation bullets (the nested-invisible one and the router-vs-command precedence one).

## Sequencing / open questions

- **Build trigger.** No foreclosure ⇒ no urgency-by-foreclosure. Per COR-007, build when recurrence shows up (a real second consumer or explicit prioritisation), not on one use case. **If wanted sooner: use git submodules for the sub-projects today** (fully supported); let this note carry the plain-subfolder decision until there is build pressure.
- **Open:** (A) vs (C); whether submodule and plain-subfolder scopes should be indistinguishable to the user; whether a cross-root fan-out verb and a workspace-aware `status` are in scope or separate; the `--root`-below-git-root warning.

Retires by producing the monorepo-support ADR (+ any resolver-reconciliation decision), or is dropped.
