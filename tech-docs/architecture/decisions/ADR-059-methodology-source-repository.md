---
id: ADR-059
title: The methodology's source repository is the one a sync would copy from
status: proposed
date: 2026-09-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** several parts of the backbone ask whether the repository being worked on is the methodology's own source, and until now they answered in two ways without saying which one was the definition. This record fixes it: **the methodology's source repository is the repository whose `.pkit/` is the source tree the running code copies from**, so a sync has nothing to copy into it. That is sync's self-host condition. Two consumers cannot evaluate it: the entry-point router runs before any code is chosen, and the lifecycle's ownership predicate is propagated code that cannot import the tool. They recognise the repository by two marker files instead: the package source and the in-tree dispatcher. The markers stand in for the definition, and they agree with it for one reason: the router's first route runs a checkout's own code whenever the markers are present. The package-source marker is a name specific to this distribution, so it is listed with the methodology's other literals in the lifecycle README.

## Context

Six places ask the question. Sync's self-host path, upgrade's self-host branch and init's refusal to install into the source compare the target root with the folder the source tree is found in: the running package's own checkout first, the bundled tree otherwise ([ADR-033](ADR-033-official-install-bundles-content.md)). The router's first route ([ADR-039](ADR-039-pkit-entry-point-router.md)), upgrade's refusal to replace the tool inside a checkout ([ADR-044](ADR-044-upgrade-self-update-detect-instruct.md) D3) and the ownership predicate `is_methodology_source` (#1007) look for two files at the root instead. The predicate feeds `is_synced_copy`, which living-docs uses to refuse a synced copy as a documentation place ([living-docs:DEC-001-living-docs-discipline] point 1). ADR-055 point 3 rests on that answer when it declares `.pkit/` to be source here.

Nothing recorded which answer is the definition, or why the two agree. They agree only because of route 1. With routing bypassed, sync can copy into a checkout that the predicate still calls source. The predicate also carries this distribution's package name inside code every adopter receives. That is a literal, and universal applicability says literals belong in the distribution's reference, not in shared code ([COR-014](../../../.pkit/decisions/core/COR-014-universal-applicability.md)).

## Decision

1. **The definition.** A repository is the methodology's source when its root is the parent of the source tree the running code resolves: the tree a sync would copy from. A bundled tree never has a project as its parent, so under an installed distribution no repository is the source. One function holds the test, `project_kit.install.is_self_host`. Its consumers are sync's self-host path (deploy primitives only, no propagation), upgrade's self-host branch (which delegates to sync) and init's refusal.
2. **The stand-in.** Where the definition cannot be evaluated, the source repository is recognised by two files at its root, both required: the package source and the in-tree dispatcher. An adopter has the dispatcher but never the package source. There are three consumers:
   - **The router's route 1** (`project_kit.router.is_source_checkout`). It runs before any code is chosen, because choosing the code is its job.
   - **Upgrade's self-update skip.** It calls the router's function and is reached only after the definition has said no.
   - **The ownership predicate** (`is_methodology_source` in `.pkit/lifecycle/ownership.py`). It is loaded where the tool's package cannot be imported, for the reason [ADR-003](ADR-003-permission-core-code-home.md) gives.

   The router's function and the predicate are two copies of one test, and a test holds them equal.
3. **Route 1 keeps the two tests equal.** When the markers are present, the router execs that checkout's dispatcher, which runs that checkout's package. The source tree the running code resolves is therefore that checkout's `.pkit/`, and the definition holds. The resolver also requires that `.pkit/` to carry its decisions, which every source tree does. In the other direction, where the definition holds, the running code is that repository's package source, and the dispatcher is tracked source beside it. A test holds the predicate to sync's own decision in a source-shaped tree and an adopter-shaped tree, under the condition route 1 establishes.
4. **The literal.** The two marker paths are this distribution's names: its package and its dispatcher ([PRJ-001](../../../.pkit/decisions/project/PRJ-001-cli-binary-name.md)). They are listed in the lifecycle README's table of the methodology's literals ("The methodology's literals"), and both copies of the marker test cite that table.

## Rationale

**Why sync's condition is the definition.** Every consumer is asking whether this is the tree a sync copies from. The markers say what a source checkout looks like. Sync's condition says what makes a repository the source. The markers give the same answer for a checkout whichever code operates on it, but whether a sync copies into that checkout depends on exactly which code that is.

**Why not one function for all six.** The tool and the propagated tree are the boundary. The ownership predicate cannot import the tool. The router could load the tree-side predicate from its own bundled copy, but it would first have to find that copy. That means a second locator for the source tree on the router's stdlib-only hot path, to save a check of two files. Nor can the definition move into either of them, because it has to know which code is running. The router decides that, and the predicate never learns it. So each test has one function, and the marker test exists in two copies held equal by a test.

**Why the gap is named here and not closed.** With routing bypassed (`PKIT_NO_ROUTE=1`), or when a checkout is operated on by another checkout's code or by the installed tool, the markers say source while the definition says adopter. Sync then propagates the foreign source over the checkout. Keying sync on the markers would not fix this. Sync would skip propagation, but it would also run foreign code as though it were the checkout's own. The honest answer in that case is a refusal. What the refusal says, and whether the bypass may override it, is a design of its own, and reaching the gap takes a deliberate bypass or an unusual invocation.

### Alternatives considered

- **Markers as the definition, with sync keyed on them.** Rejected. Sync's self-host path skips propagation because the running source *is* the target's state, and markers cannot establish that.
- **One shared function across the tool/tree boundary.** Rejected for the reasons above.
- **Leave both tests unrecorded, joined only by the router-versus-predicate test.** Rejected. That test pins the markers, not what they stand in for, so sync's condition could change and nothing would notice.

## Implications

- `install.is_self_host` replaces three copies of the comparison in sync, upgrade and init. Each consumer of either test cites this record, and the marker copies cite the literals table.
- `tests/test_lifecycle_ownership.py` holds the predicate equal to the router's markers and to sync's own decision.
- **Revisit** when a consumer must stay correct without route 1. That covers several cases: sync or upgrade refusing a target the markers call source when the running code is not its own; route 1 changing or being retired; the package source moving or being renamed; and a second distribution of the methodology with its own package. Each breaks the argument in point 3.
