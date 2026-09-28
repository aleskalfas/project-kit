---
id: ADR-058
title: One validator registry behind `pkit validate`; only errors fail
status: proposed
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** `pkit validate` becomes a registry. Each functionality registers one *validator* — a name, an order and a callable that reads the project and answers with summary lines and findings, each with a severity. The backbone registers twelve members; a capability registers its own by naming a command it already registers. One renderer, one summary, only an `error` fails. The focused commands stay; the check aggregator calls `pkit validate` once beside the checks that read a diff.

## Context

The core records name `pkit validate` as the check of project state against invariants ([COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md)); the living-documentation design note ([`.pkit/scratchpad/done/2026-09-26-software-analysis-living-docs-design.md`](../../../.pkit/scratchpad/done/2026-09-26-software-analysis-living-docs-design.md), its entry of 2026-09-28) decided that every functionality registers its validator there and the check gate calls it once, and [ADR-056](ADR-056-backbone-file-schemas-home.md) point 5 asked for its passes as members. Until now each Task added its pass by hand, five older validators had no place in the umbrella, and the reference-graph check — in it on `main` behind `--include-refs`, on by default — failed this repository on four false positives and twelve drift findings, so the aggregator (`scripts/check.sh`, the enforcement boundary of [ADR-019](ADR-019-enforcement-gate-mechanism-vs-boundary.md)) ran `schemas validate` and `decisions validate`, never `pkit validate` or `refs validate`.

## Decision

1. **One registry, one shape, in the binary.** `project_kit.validators` is the home. A `Validator` is a name, an order and a callable `Path → Outcome`; an `Outcome` is summary lines and `Finding`s, each a location relative to the project root (a path, `path:/json/pointer`, `path#entry`), a message, a severity and an optional label. It ships in the tool and propagates nothing ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1; [ADR-020](ADR-020-process-engine-code-home.md)).

2. **Severity is the whole contract between a member and the umbrella.** `error` fails `pkit validate`; `warning`, `info` and `report` print and never fail. A warning asks for attention (a drifted declaration; an unknown key in package metadata, with the nearest known one — in the configuration file an unknown key is an *error*, [COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 4); an info states a fact; a report is what an owning record says is *reported rather than judged* ([COR-053](../../../.pkit/decisions/core/COR-053-connection-points.md) point 10, [COR-051](../../../.pkit/decisions/core/COR-051-rule-sets.md)). Which finding takes which severity stays with the record that owns the check.

3. **The backbone's members, in dependence order:** `manifests`, `schemas`, `configuration`, `packages`, `connections`, `versions`, `friction`, `rule-sets`, `decisions`, `refs`, `process`, `data` — what a later member reads, an earlier one checked, with one soft exception: `configuration` reads raw package declarations before `packages` validates them. The umbrella never changes what a member computes; the CLI reference's `validate` table says what each checks and which focused surface it keeps. `process` and `data` walk the repository, which their focused surfaces do not: `data` checks every claimed file in the repository and in the project-owned `project/` folders under `.pkit/`, skipping what nothing claims — a third file source beside the two of ADR-057 point 2, joining #1034's consolidation.

4. **A capability registers its validators in package metadata**, under `validators:`, by naming a command it registers under `commands:`. An entry is `command` — a path through the tree, checked like every other command reference — and an optional `order`; the leaf's `help` is the validator's, and the same script is a focused surface (`pkit <capability> <command>`). Because the entry names a `commands:` leaf, ADR-057 point 3 applies unchanged: the leaf declares the query contract on its own entry — the literal is **`query-contract: true`** — package validation reports a validator leaf without it, and the runner refuses it. The umbrella addresses the validator `<capability>:<name>`, sorts it after the backbone's members unless its order says otherwise, and runs the script as a query: from the project root with the one argument `--json`, the offline marker set, in its own process group, bounded by the predicate runner's thirty seconds and killed as a group on timeout, reading one JSON findings document and nothing else from standard output, diagnostics on standard error. **No answer is an error finding, never a clean pass**: a leaf without the declaration, an abnormal exit, a timeout, an answer that is not exactly that document. This runner is the third start-bound-capture-parse beside the dispatcher's and the predicate runner's — recorded debt for #1035 (ADR-057 point 5; COR-053 point 11) — and the predicate runner still lacks the process-group kill.

5. **One renderer, one summary; the umbrella's exit rule.** Every member prints under its heading through one renderer, one summary closes the report, and the exit code is 1 on errors only. The rule is the umbrella's: a focused surface keeps its own exit — `refs validate` fails on any finding, drift included. `--only NAME` and `--skip NAME` address members; `--no-refs` is kept as `--skip refs`.

6. **The refs member's split.** Drift between an artifact's front matter and its body is a **warning**: the artifact deploys and resolves regardless, and the body parser is a heuristic. Everything that does not resolve is an **error**. The change is narrow: `pkit validate`'s own exit no longer fails on drift, while the gate gets stronger — the aggregator now runs the check, which it never did.

7. **Diff-scoped checks are not validators.** `pkit friction check`, `pkit migrations check-diff` and `pkit release lint` read a base ref and answer about a *change*; a validator answers about the *tree*, and mixed in, `pkit validate` would answer differently on the same tree. The whole-repository friction check reads history, not the tree, so it is not a member either. They stay their own lines of the aggregator, which calls `pkit validate` once and drops the lines it subsumes.

## Rationale

**Why a registry.** Five hand-wired passes had diverged in where errors printed, how a finding was located and how an unknown key was phrased, and the sixth would have diverged again. A registry makes the order visible in one place, lets the aggregator call one command so nothing registered can be forgotten there, and gives a capability a way in that does not touch the command.

**Why severity on the finding, not on the surface.** The same finding must mean the same thing wherever it prints; the exit rule in one place and the classification with the check that raised it keep every member honest.

**Why a validator names a command.** A capability already registers what it can run in one place; a second registry of scripts would be a second walker of the same tree and a second place for the query-contract declaration. Naming the leaf makes the validator a focused surface for free, lets package validation check the reference as it checks every other, and puts the declaration where ADR-057 asked for it.

**Why drift warns.** A gate that fails on a heuristic parser's reading of prose fails for the wrong reasons — that is why `--no-refs` existed. Drift is real and worth fixing at the source; it is not breakage, and the twelve instances on this repository are now visible in every run instead of hidden behind a flag.

**Why the callable takes only the root.** Every existing pass had that signature, and a capability's command has nothing else to receive; the wiring resolved twice, for `connections` and `versions`, is the one resolver run twice, not two computations (ADR-057 point 2).

**Why an ADR.** The core records decide that the umbrella exists; its registry, order, query contract and exit rule are project-kit's realisation ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)), at the altitude of ADR-056.

### Alternatives considered

- **Keep adding passes to the command.** Rejected: the divergence above, and no way in for a capability.
- **Register by import side effect.** Rejected: the order would live in import order, invisible and fragile.
- **A validator as its own script under `validators:`.** Rejected: a second registry, a second walker, and no place for the declaration ADR-057 puts on a `commands:` entry.
- **A run context shared across members** (the wiring resolved once). Rejected for now: one more type for a few milliseconds; the trigger to revisit is recorded.
- **Make `refs validate` fail on errors only.** Rejected: the focused surface's charter is the strict lint an author runs; changing its exit is a separate decision.

## Implications

- `project_kit.validators` holds the shape, the backbone's members, the package-metadata reader, the query runner and the renderer; `pkit validate` runs the registry.
- Validators are the first query commands to run, so the declaration's literal (`query-contract: true` on a `commands:` leaf), the offline marker (`PKIT_OFFLINE=1`, with `UV_OFFLINE=1` beside it so a `uv run --script` shebang resolves from uv's cache and never fetches) and provisioning (run the focused surface once, online) are specified here and in the package-metadata reference — the lifecycle README's package table and literals section; ADR-057 point 3 points here. The package schema gains the block and the declaration; the packages member and the register pre-flight check them. No shipped capability registers one yet.
- `scripts/check.sh` calls `pkit validate` once and drops `schemas validate` and `decisions validate`: `schemas` is the identical computation (`validate_all(root, resolve=True)`), `decisions` the focused command's id-space check plus front matter. The diff-scoped lines stay. Keep `--skip` out of `check.sh`: an override belongs in an audit-trailed channel, not a bare flag (ADR-019 point 6).
- The query runner joins the shared start-bound-capture-parse primitive when #1035 extracts it; the `data` walk joins #1034's consolidation.
- **Raised for a core decision (#1045).** Whether capability-registered validators and the four severities become a COR-021 refinement, or stay this record's realisation.
- **Recorded trigger to revisit.** A member that needs what another computed — beyond the wiring — reopens the run-context alternative.
- Accepted by the maintainer before the trunk builds on it ([PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)).
