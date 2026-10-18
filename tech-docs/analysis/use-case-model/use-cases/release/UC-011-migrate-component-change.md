---
id: UC-011
title: Carry the projects that installed my component across a breaking change of it
status: active
actor: ACT-component-author
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
        - .pkit/skills/core/migration-author.md
      record:
        - COR-010
        - PRJ-002#D3
      artefact:
        - ACT-component-author
        - ACT-ci-pipeline
---

# UC-011 — Carry the projects that installed my component across a breaking change of it

**Goal:** Carry the projects that installed my component across a breaking change of it.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the migration check on every pull request, with no person to answer. It does so where the component's repository wires the check in, as project-kit's does (UC-006).

**Preconditions:** None.

**Assumptions:**

- The author judges what breaks the projects that installed the component. The check finds only renames and removals of files (`migrations.py`). Another break, such as a key whose meaning changes, rests on that judgement (COR-010).
- The component's changeset for the change declares `minor` or above, so the release writes the minor the migration names. A patch release carries no migration (COR-010).

**Trigger:** The author's change breaks what the projects that installed the component hold, such as renaming or removing one of the component's files.

**Main path:**

1. The author predicts the component's version in the release that will ship the change, with its patch `0`. Only the release writes versions, so the branch holds no such number (PRJ-002 D3).
2. The author runs `pkit new migration --tier capability --component <name> --version <X.Y.0> --name <slug>`, through the `migration-author` skill. The system stamps `<NNN>-<slug>.sh` in the component's `migrations/<X.Y.0>/` folder.
3. The author writes the script to carry the projects across. The script is safe to run twice (COR-010).
4. The author runs `pkit migrations check-diff --include-working-tree` before committing.
5. The system matches each rename and removal in the component's folder with a migration of the same tier and component. It ends with `Verdict: COVERED (every tier:component with triggers has a matching migration).`
6. The author commits the change with its migration and the component's changeset (UC-003).
7. The CI pipeline runs `pkit migrations check-diff` on the pull request, and the check passes.
8. The release that ships the change writes, for the component, the version the migration's folder names (UC-009).

**Variants:**

- **2a.** The component is an adapter. The author passes `--tier adapter`, and the system stamps the script in the adapter's `migrations/<X.Y.0>/` folder.
- **2b.** The author leaves out `--version`. The system takes the version in the component's `package.yaml`, a minor already released, so a project already at that minor never runs the migration. No check reports it (`migrations.py` and `release.py`).
- **5a.** A rename or a removal in the component's folder has no migration of that component. A migration of the backbone or of another component does not cover it. The system ends with `Verdict: UNCOVERED. Author migrations for the following tiers before merging:`, lists the component by its tier and name, and exits 1. The path rejoins at step 2.
- **5b.** The change renames or removes files only in the component's `project/` folder, or only its decision records. The check finds no trigger there (`migrations.py`), and the use case ends.
- **5c.** The change breaks the projects in a way the check cannot see, such as a key whose meaning changes. The check finds no trigger and passes, whether or not the change holds a migration. The path goes on at step 6.
- **8a.** The release writes another version for the component than the folder names. The release plan compares only the backbone's folders, so nothing reports it (`release.py`).

**Postconditions:** The release that moves the component ships its migration, in the folder of the version that release writes for the component. A project's upgrade of the component across that version runs the migration.

**Minimal guarantees:**

- A pull request that renames or removes a file of the component fails the check, unless the pull request adds a migration of that component. The check leaves out the component's `project/` folder and its decision records (COR-010 and `migrations.py`).
