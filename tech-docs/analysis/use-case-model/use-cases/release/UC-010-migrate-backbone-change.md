---
id: UC-010
title: Never ship a backbone change that breaks installed projects without its migration
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ci-pipeline
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/migrations.py
        - src/project_kit/scaffolds.py
        - src/project_kit/release.py
        - src/project_kit/cli.py
        - scripts/check.sh
        - .github/workflows/checks.yml
        - .pkit/skills/core/migration-author.md
        - .pkit/rules/core.md
      record:
        - COR-010
        - PRJ-002#D3
      artefact:
        - ACT-methodology-maintainer
        - ACT-ci-pipeline
---

# UC-010 — Never ship a backbone change that breaks installed projects without its migration

**Goal:** Never ship a backbone change that breaks installed projects without the migration that carries them across.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the migration check on every pull request, with no person to answer. The check fails while a rename or a removal it finds has no migration.

**Preconditions:** None.

**Assumptions:**

- The maintainer judges what breaks installed projects. The check finds only renames and removals of files (`migrations.py`). Another break, such as a flag whose meaning inverts, rests on that judgement (COR-010).
- The backbone's changeset for the change declares `minor` or above, so the release computes the minor the migration names. A patch release carries no migration (COR-010).

**Trigger:** The maintainer's change breaks what installed projects hold, such as renaming or removing a file in a tree the backbone ships.

**Main path:**

1. The maintainer predicts the backbone's version in the release that will ship the change, with its patch `0`. Only the release writes versions, so the branch holds no such number (PRJ-002 D3).
2. The maintainer runs `pkit new migration --tier backbone --version <X.Y.0> --name <slug>`, through the `migration-author` skill. The system stamps `<NNN>-<slug>.sh` in `.pkit/migrations/backbone/<X.Y.0>/`.
3. The maintainer writes the script to carry installed projects across. The script is safe to run twice, and acts only on a positive sign that its change is needed (COR-010).
4. The maintainer runs `pkit migrations check-diff --include-working-tree` before committing, as core rule 7 asks.
5. The system lists each rename and removal the change makes in a tree a release ships, with its tier. It also lists each migration script the change adds, and ends with `Verdict: COVERED (every tier:component with triggers has a matching migration).`
6. The maintainer commits the change with its migration and its changeset (UC-003).
7. The CI pipeline runs `pkit migrations check-diff` on the pull request, from where the branch left its target, and the check passes.
8. The release that ships the change computes the version the migration's folder names (UC-008).

**Variants:**

- **1a.** The change only adds, such as a new skill or a new schema, or it refines a document. It needs no migration (COR-010). The check reports `No migration-triggering changes in diff.`, and the use case ends.
- **1b.** The change renames or removes a decision record. Sync refreshes the records whole, so the check asks no migration for it (`migrations.py`). The use case ends.
- **2a.** The maintainer leaves out `--version`. The system takes the backbone's current version, a minor already released, so a project already at that minor never runs the migration. No check reports it (`migrations.py` and `release.py`).
- **3a.** The script adds a default that a project lacks. A later run over a project whose history is unknown may restore a default the project removed. The maintainer says so in the changeset, naming the default, so the release's notes carry it (COR-010).
- **5a.** A rename or a removal has no migration of its tier and component. The system ends with `Verdict: UNCOVERED. Author migrations for the following tiers before merging:`, lists `backbone`, and exits 1. The path rejoins at step 2.
- **5b.** The change breaks installed projects in a way the check cannot see, such as a flag whose meaning inverts. The check finds no trigger and passes, whether or not the change holds a migration. The path goes on at step 6.
- **8a.** The release computes another version than the folder names. `pkit release plan` warns that the folder `does not match the computed backbone release`, and the release goes on. The release pull request's body shows the warning for the maintainer to judge.

**Postconditions:** The release that ships the breaking change ships its migration, in the folder of the backbone version that release computes. A project's upgrade across that version runs the migration.

**Minimal guarantees:**

- A pull request that renames or removes a file in a tree the check reads as the backbone's, such as `.pkit/skills/core/`, fails the check. The pull request passes only once it adds a backbone migration (COR-010 and `migrations.py`).
