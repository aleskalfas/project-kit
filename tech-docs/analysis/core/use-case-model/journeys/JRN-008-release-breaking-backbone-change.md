---
id: JRN-008
title: Release a breaking backbone change with its migration
status: active
actor: ACT-methodology-maintainer
steps:
  - UC-010
  - UC-008
relies-on:
  - UC-014
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
        - ACT-methodology-maintainer
        - UC-010
        - UC-008
        - UC-014
        - UC-003
        - UC-034
---

# JRN-008 — Release a breaking backbone change with its migration

**Goal:** Release a backbone change that breaks installed projects with the migration that carries them across.

**Steps:**

1. [UC-010](../use-cases/030-change/UC-010-migrate-backbone-change.md) — Never ship a backbone change that breaks installed projects without the migration that carries them across
   - **Needs from [UC-014](../use-cases/010-develop/UC-014-develop-methodology.md) (outside this journey):** the [backbone](../../glossary.md#term-backbone--backbone), developed in the [methodology](../../glossary.md#term-methodology--methodology)'s [source repository](../../glossary.md#term-source-repository--source-repository). There `pkit` runs the checkout's code as edited, so the [migration](../../glossary.md#term-migration--migration) check and the [release step](../../glossary.md#term-release-step--release-step) run the code the [release](../../glossary.md#term-release--release) ships. A command started with routing switched off runs the installed CLI's code instead, with no warning (UC-014 variant 3b).
   - **Needs from [UC-003](../use-cases/030-change/UC-003-declare-changeset.md) (outside this journey):** the backbone's [changeset](../../glossary.md#term-changeset--changeset), committed with the migration. It declares `minor` or above, so the release step that ships the [change](../../glossary.md#term-change--change) raises the backbone's minor or major.
2. [UC-008](../use-cases/040-release/UC-008-release-backbone.md) — Release the backbone so adopters can upgrade and pin to it
   - **Needs from step 1 (UC-010):** the migration, in the folder of the next minor past the backbone's [version](../../glossary.md#term-version--version), and its changeset. The release step computes the version from the changesets alone, and warns where the folder names another (UC-010 variant 8a, UC-008 variant 2e). The release goes on, and the release [pull request](../../glossary.md#term-pull-request--pull-request)'s body shows the warning for the maintainer to judge. A release below the folder's version ships the change, and an upgrade to it runs none of the folder's migrations (`migrations.py`).
   - **Needs from step 1 (UC-010):** where the migration adds a missing default, the changeset's sentence that names the default, for the changelog entry (UC-010 variant 3a). No command checks for that sentence, so the maintainer looks for it at UC-008 step 8.
   - **Needs from [UC-034](../use-cases/030-change/UC-034-land-change.md) (outside this journey):** the change landed on the [default branch](../../glossary.md#term-default-branch--default-branch), so its changeset waits under `.changes/unreleased/` beside the migration.

**Variants:**

- **1a.** The [change](../../glossary.md#term-change--change) needs no [migration](../../glossary.md#term-migration--migration), as when it only adds a [skill](../../glossary.md#term-skill--skill) or refines a document ([UC-010](../use-cases/030-change/UC-010-migrate-backbone-change.md) variant 1a). The path ends after step 1.

**Postconditions:** The [release](../../glossary.md#term-release--release) tagged `v<version>` carries the breaking [change](../../glossary.md#term-change--change), with its [migration](../../glossary.md#term-migration--migration) in that [version](../../glossary.md#term-version--version)'s folder. A [project](../../glossary.md#term-project--project)'s upgrade across that version runs the migration. The release's changelog entry says what the change means for adopters.

**Minimal guarantees:**

- Wherever the path stops, the [migration](../../glossary.md#term-migration--migration) stays in a folder no [release](../../glossary.md#term-release--release) has reached, since the migration check fails one already released. An upgrade from below that folder's [version](../../glossary.md#term-version--version) to a release at or past it runs the migration (`migrations.py`).
