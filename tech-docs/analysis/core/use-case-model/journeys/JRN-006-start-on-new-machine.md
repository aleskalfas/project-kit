---
id: JRN-006
title: Start working on a project on a new machine
status: active
actor: ACT-operator
steps:
  - UC-048
  - UC-050
relies-on:
  - UC-008
  - UC-049
  - UC-052
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - src/project_kit/sync.py
        - src/project_kit/install.py
        - src/project_kit/upgrade.py
      record:
        - PRJ-004
        - COR-059#2
        - COR-059#5
        - ADR-065#7
        - ADR-065#8
        - ADR-065#11
        - ADR-065#12
        - ADR-039#2
        - ADR-039#D2
        - ADR-009#3
      artefact:
        - ACT-operator
        - UC-048
        - UC-050
        - UC-008
        - UC-049
        - UC-052
---

# JRN-006 — Start working on a project on a new machine

**Goal:** Get my clone of a project ready to work on a machine with no CLI yet, at the release the project records.

**Steps:**

1. [UC-048](../use-cases/050-adopt/UC-048-install-cli.md) — Put the system's CLI on my machine at a release
   - **Needs from [UC-008](../use-cases/040-release/UC-008-release-backbone.md) (outside this journey):** the [release](../../glossary.md#term-release--release)'s tag on the [distribution](../../glossary.md#term-distribution--distribution)'s repository, and the tag `latest` at the highest release's commit ([PRJ-004](../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). A CLI installed from a branch or from main's latest commit has a [version](../../glossary.md#term-version--version) that vouches for no content ([ADR-065 point 12](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#12-a-version-identifies-content-only-for-a-tagged-install)).
2. [UC-050](../use-cases/050-adopt/UC-050-ready-fresh-clone.md) — Get a fresh clone ready to work with one sync
   - **Needs from step 1 (UC-048):** the CLI, at the release the [project](../../glossary.md#term-project--project) records. Where the CLI is at another release, and the project pins none, [sync](../../glossary.md#term-sync--sync) stops and writes nothing. Its message names the remedy for the state it finds (ADR-065 points [7](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#7-syncs-guard-stops-a-command-that-would-propagate-under-another-version) and [8](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#8-each-stop-names-the-remedy-for-the-state-it-finds)). The documented command that puts the CLI on a machine names `latest`, so a project that records an older release meets this stop.
   - **Needs from [UC-049](../use-cases/050-adopt/UC-049-install-system.md) (outside this journey):** the [system](../../glossary.md#term-system--system), committed for the team. Where the adopter keeps the system out of the shared repository, a clone holds no `.pkit/`. Sync then refuses, and names `pkit init` ([ADR-009 point 3](../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#3-private--make-the-whole-footprint-git-invisible-via-gitinfoexclude)).
   - **Needs from [UC-052](../use-cases/050-adopt/UC-052-run-at-pin.md) (outside this journey):** the project's committed [version pin](../../glossary.md#term-version-pin--version-pin), where it has one. The router then runs sync at the pinned release through `uvx`, whatever release the CLI from step 1 runs ([ADR-039 point 2](../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#2-project-pins-a-version--me--re-exec-uvx-project-kitpin)). Where `uvx` cannot fetch that release, the system warns and runs the installed CLI, whose sync stops if its release differs (ADR-065 point 8).

**Variants:**

- **1a.** The machine has the CLI already, as for another [project](../../glossary.md#term-project--project). The path goes on at step 2.
- **2a.** The project records another [release](../../glossary.md#term-release--release) than the installed CLI's, and pins none, so [sync](../../glossary.md#term-sync--sync) stops at step 2. The path rejoins at step 1, where the operator installs the project's release by its tag ([UC-048](../use-cases/050-adopt/UC-048-install-cli.md) variant 1c).

**Postconditions:** The clone holds the [system](../../glossary.md#term-system--system) at the [release](../../glossary.md#term-release--release) the [project](../../glossary.md#term-project--project) records, and no [recorded version](../../glossary.md#term-recorded-version--recorded-version) moved. Its [skills](../../glossary.md#term-skill--skill) and [agent definitions](../../glossary.md#term-agent-definition--agent-definition) are deployed where the [harness](../../glossary.md#term-harness--harness) reads them. Its [agent workspace](../../glossary.md#term-agent-workspace--agent-workspace) exists, and each query command answers offline ([COR-059 point 2](../../../../../.pkit/decisions/core/COR-059-version-transition.md#2-reconciliation-runs-at-the-recorded-versions-and-moves-none) and [ADR-065 point 11](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)).

**Minimal guarantees:**

- Where the CLI is at another [release](../../glossary.md#term-release--release) than the [project](../../glossary.md#term-project--project) records, or where a [version transition](../../glossary.md#term-version-transition--version-transition) is incomplete, [sync](../../glossary.md#term-sync--sync) writes nothing ([ADR-065 point 7](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#7-syncs-guard-stops-a-command-that-would-propagate-under-another-version)).
- Installing or updating the CLI acts on no project ([COR-059 point 5](../../../../../.pkit/decisions/core/COR-059-version-transition.md#5-the-one-operation-rule-governs-operations-on-a-project)).
- A [version pin](../../glossary.md#term-version-pin--version-pin) that cannot be fetched never fails a command in the router, and the [system](../../glossary.md#term-system--system) says which CLI ran instead ([ADR-039 D2](../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#d2--graceful-degradation-is-mandatory)).
