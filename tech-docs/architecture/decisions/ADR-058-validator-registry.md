---
id: ADR-058
title: One validator registry behind `pkit validate` — a name, an order and a callable answering findings with a severity; only errors fail
status: proposed
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** `pkit validate` stops being a list of hand-wired passes in the command and becomes a registry. Each functionality registers one *validator* — a name, an order, and a callable that reads the project at a root and answers with summary lines and findings, each finding carrying a severity. The backbone registers its twelve members in one module; a capability registers its own in its package metadata, as it registers commands. One renderer prints every member under its own heading, one summary closes the report, and only an `error` fails the command. The focused commands — `schemas validate`, `decisions validate`, `refs validate`, `data validate <path>`, `process validate <address>` — stay as they are; the umbrella runs the same computations. The check aggregator calls `pkit validate` once; the checks that read a diff stay their own lines.

## Context

The core records name `pkit validate` as the check of project state against invariants ([COR-004](../../../.pkit/decisions/core/COR-004-cli-surface.md)), and the living-documentation design note decided that every functionality registers its validator there and that the check gate calls it once. The backbone file schemas record asked that its passes be registered members of that umbrella ([ADR-056](ADR-056-backbone-file-schemas-home.md) point 5). Each Task of the validation Feature then added its pass to the command by hand — configuration, packages, friction, the wiring resolver under two headings, rule sets — each printing its own section, with the errors of every pass funnelled into one issue list printed *before* the sections. Five older validators had their own commands and no place in the umbrella. The check aggregator (`scripts/check.sh`, the enforcement boundary of [ADR-019](ADR-019-enforcement-gate-mechanism-boundary.md)) ran two of them and not `pkit validate` at all, because the reference-graph check failed on this repository: four false positives of a form mismatch, and twelve findings of drift between front matter and body.

## Decision

1. **One registry, one shape, in the binary.** `project_kit.validators` is the home. A `Validator` is a name, an order and a callable `Path → Outcome`; an `Outcome` is a tuple of summary lines and a tuple of `Finding`s, each a location relative to the project root (a path, `path:/json/pointer`, or `path#entry`), a message, a severity and an optional label. The registry, like every engine of this milestone, ships in the tool and propagates nothing ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1; [ADR-020](ADR-020-process-engine-code-home.md)).

2. **Severity is the whole contract between a member and the umbrella.** `error` fails `pkit validate`. `warning`, `info` and `report` print and never fail: a warning asks for attention (an unknown key with the nearest known one, a drifted declaration), an info states a fact (a default in use), a report is what an owning record says is *reported rather than judged* (an inert point block, an orphaned fill — [COR-053](../../../.pkit/decisions/core/COR-053-connection-points.md) point 10, [COR-051](../../../.pkit/decisions/core/COR-051-rule-sets.md)). Each member maps its own severities onto these four; which finding takes which severity stays with the record that owns the check.

3. **The backbone's members, in dependence order:** `manifests`, `schemas`, `configuration`, `packages`, `connections`, `versions`, `friction`, `rule-sets`, `decisions`, `refs`, `process`, `data` — what a later member reads, an earlier one checked. The umbrella never changes what a member computes; it only renders the outcome. Two members have a *repository* scope their focused surfaces lack: `data` walks the repository outside `.pkit/` and the dot-directories and checks every file a `pkit_schema:` field or a `binds_to:` glob claims, skipping what nothing claims; `process` checks that every declared definition resolves to one file, and does not run a subject's invariants — those need a subject and its predicates, and stay `pkit process validate <address>`'s.

4. **A capability registers its validators in package metadata**, under `validators:` — a name, a `script`, a `help` line and an optional `order` — as it registers commands under `commands:`. Registering a script there *is* its declaration of the query contract ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 3): the block admits nothing but validators, which only `pkit validate` — a reading command — ever runs, so no separate literal is asked of the entry. The umbrella addresses it `<capability>:<name>`, sorts it after the backbone's members unless its order says otherwise, and runs the script as a *query command* in the sense of ADR-057 point 3: from the project root, with no arguments, bounded by the predicate runner's thirty seconds, reading one JSON document from its standard output — `{"summary": [...], "findings": [{"severity", "location", "message"}]}`. **No answer is an error finding, never a clean pass**: an abnormal exit, a timeout, an answer that is not that document. The package schema types the block permissively, the packages member checks that each script exists, and the registry reads the block defensively — a malformed entry is the packages member's finding, not a crash.

5. **One renderer, one summary, one exit rule.** Every member prints as its heading, its summary lines, then each finding as `<severity>  <location>` over `→ <message>`. Every unknown-key message in every member comes from `backbone_schemas.render_unknown_key` ([ADR-056](ADR-056-backbone-file-schemas-home.md) point 4), which `expand_schema_error` now routes a JSON Schema validator's `additionalProperties` violation through — so the schemas and data members phrase an unknown key as the configuration and package members do. The report closes with the count per severity and `All checks passed.` or `N error(s) found.`; the exit code is 1 on errors only. `--only NAME` and `--skip NAME` address members; `--no-refs` is kept as `--skip refs`.

6. **The refs member's split.** Drift between an artifact's front matter and its body — a declared reference the body never cites, a body citation the front matter does not declare — is a **warning**: the artifact deploys and resolves regardless, and the body parser is a heuristic (a dotted configuration key reads as a hook). Every other finding — a path owned twice or by nobody, a hook no provider answers, colliding providers, a missing storyboard, a citation that does not resolve, a sub-procedure that does not exist — is an **error**. `pkit refs validate`, the focused surface, keeps its stricter exit and fails on any finding. The pattern check reads a `reads.patterns` entry bare or bracketed, as the deploy does ([ADR-052](ADR-052-optional-read-category-empty-tolerance.md)).

7. **Diff-scoped checks are not validators.** `pkit friction check`, `pkit migrations check-diff` and `pkit release lint` read a base ref and answer about a *change*; a validator answers about the *tree*. They stay their own lines of the aggregator, which calls `pkit validate` once and drops the lines it subsumes.

## Rationale

**Why a registry.** Five hand-wired passes had already diverged in three ways — where errors printed, how a finding was located, how an unknown key was phrased — and the sixth would have diverged again. A registry makes the order visible in one place, lets the aggregator call one command so nothing registered can be forgotten there, and gives a capability a way in that does not touch the command.

**Why severity on the finding, not on the surface.** The same finding must mean the same thing wherever it prints. Putting the exit rule in one place (only errors fail) and the classification with the check that raised it keeps every member honest: a member that wants to fail the gate says `error`, and a reader of one section knows what each line does without reading the command.

**Why drift warns.** A gate that fails on a heuristic parser's reading of prose fails for the wrong reasons — that is why `--no-refs` existed. Drift is real and worth fixing at the source; it is not breakage, and the twelve instances on this repository are now visible in every run instead of hidden behind a flag.

**Why the callable takes only the root.** Every existing pass already had that signature, and a capability's script has nothing else to receive. The price is that the wiring is resolved twice — once for `connections`, once for `versions` — through the one resolver, which is cheap; the one-home rule of ADR-057 point 2 holds, since nothing is computed twice by different code.

**Why state and change stay apart.** A validator's answer depends only on the tree; a diff check's answer depends on a base ref the aggregator chooses. Mixing them would make `pkit validate` answer differently on the same tree.

**Why an ADR.** The core records decide that the umbrella exists; the shape of its registry, the order of the members, the query contract of a capability's script and what fails the gate are project-kit's realisation ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)), at the altitude of ADR-056.

### Alternatives considered

- **Keep adding passes to the command.** Rejected: the divergence above, and no way for a capability in.
- **Register by import side effect** (a decorator on each pass). Rejected: the order would live in import order, invisible and fragile; the explicit tuple is the order.
- **A capability's validator as a plain command the umbrella calls by name** (`pkit <cap> validate`). Rejected: the umbrella would parse human output; a declared script with a declared answer makes the contract checkable and fails closed.
- **A run context shared across members** (the wiring resolved once). Rejected for now: one more type in the shape for a few milliseconds; recorded as the trigger to revisit.
- **Fix the twelve drift findings at the source instead of classifying drift.** Not an alternative but a complement: the classification is right regardless, and the fixes follow in the artifacts' own change-sets.
- **Make `refs validate` fail on errors only, like the umbrella.** Rejected: the focused surface's charter is the strict lint an author runs; changing its exit is a separate decision.

## Implications

- `project_kit.validators` holds the shape, the backbone's members, the package-metadata reader, the script runner and the renderer; each member's module exposes its outcome; `pkit validate` runs the registry.
- The package schema gains the `validators` block; the packages member and the register pre-flight check its scripts exist; the lifecycle README's package-metadata reference documents it. No shipped capability registers one yet.
- `scripts/check.sh` calls `pkit validate` once and drops `schemas validate` and `decisions validate`; the diff-scoped lines stay.
- The script runner joins the shared start-bound-capture-parse primitive when #1035 extracts it.
- **Recorded trigger to revisit.** A member that needs what another computed — beyond the wiring — reopens the run-context alternative.
- Accepted by the maintainer before the trunk builds on it ([PRJ-005](../../../.pkit/decisions/project/PRJ-005-adopt-adrs.md)).
