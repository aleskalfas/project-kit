---
id: JRN-009
title: Release a breaking change of my component with its migration
status: active
actor: ACT-component-author
steps:
  - UC-011
  - UC-009
relies-on:
  - UC-015
  - UC-019
  - UC-003
  - UC-034
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/migrations.py
        - src/project_kit/release.py
      record:
        - COR-010
        - PRJ-002#D3
      artefact:
        - ACT-component-author
        - UC-011
        - UC-009
        - UC-015
        - UC-019
        - UC-003
        - UC-034
---

# JRN-009 — Release a breaking change of my component with its migration

**Goal:** Release a breaking change of my component with the migration that carries the projects that installed it across.

**Steps:**

1. [UC-011](../use-cases/030-change/UC-011-migrate-component-change.md) — Carry the projects that installed my component across a breaking change of it
   - **Needs from [UC-015](../use-cases/010-develop/UC-015-package-capability.md) (outside this journey):** the [component](../../glossary.md#term-component--component), packaged as a [capability](../../glossary.md#term-capability--capability), whose [package metadata](../../glossary.md#term-package-metadata--package-metadata) gives its [version](../../glossary.md#term-version--version). The [migration](../../glossary.md#term-migration--migration)'s folder is the next minor past the version that the package metadata records on the [default branch](../../glossary.md#term-default-branch--default-branch).
   - **Needs from [UC-019](../use-cases/010-develop/UC-019-adapt-harness.md) (outside this journey):** the component written as an [adapter](../../glossary.md#term-adapter--adapter), whose package metadata gives its version as a capability's does. Either UC-015 or UC-019 is enough.
   - **Needs from [UC-003](../use-cases/030-change/UC-003-declare-changeset.md) (outside this journey):** the component's [changeset](../../glossary.md#term-changeset--changeset), committed with the migration. It declares `minor` or above, so the [release step](../../glossary.md#term-release-step--release-step) that moves the component raises its minor or major.
2. [UC-009](../use-cases/040-release/UC-009-release-component.md) — Release my component on its own version
   - **Needs from step 1 (UC-011):** the migration, in the folder of the next minor past the component's version, and its changeset. The release step computes the component's new version from the changesets alone. Where it writes another version than the folder names, `pkit release plan` warns and the release step goes on (UC-009 variant 2a). A new version below the folder's ships the [change](../../glossary.md#term-change--change), and an upgrade of the component to it runs none of the folder's migrations (`migrations.py`).
   - **Needs from [UC-034](../use-cases/030-change/UC-034-land-change.md) (outside this journey):** the change landed on the default branch, so its changeset waits under `.changes/unreleased/` beside the migration.

**Variants:**

- **1a.** The [change](../../glossary.md#term-change--change) renames or removes files only where the [migration](../../glossary.md#term-migration--migration) check finds no trigger, such as the [component](../../glossary.md#term-component--component)'s `project/` folder ([UC-011](../use-cases/030-change/UC-011-migrate-component-change.md) variant 5b). The path ends after step 1.

**Postconditions:** The [component](../../glossary.md#term-component--component)'s new [version](../../glossary.md#term-version--version) carries the breaking [change](../../glossary.md#term-change--change), with its [migration](../../glossary.md#term-migration--migration) in that version's folder. A [project](../../glossary.md#term-project--project)'s upgrade of the component across that version runs the migration. The changelog entry says what changed in the component, and what the component now requires.

**Minimal guarantees:**

- Wherever the path stops, the [migration](../../glossary.md#term-migration--migration) stays in a folder no [version](../../glossary.md#term-version--version) of the [component](../../glossary.md#term-component--component) has reached, since the migration check fails one already released. An upgrade of the component from below that folder's version to one at or past it runs the migration (`migrations.py`).
