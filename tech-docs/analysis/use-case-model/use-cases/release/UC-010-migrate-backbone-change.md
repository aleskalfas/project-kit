---
id: UC-010
title: Never ship a backbone change that breaks installed projects without the migration that carries them across
status: active
actor: ACT-methodology-maintainer
other-actors:
  - ACT-ci-pipeline
  - ACT-ai-agent
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
      record:
        - COR-010
        - PRJ-002#D3
      artefact:
        - ACT-methodology-maintainer
        - ACT-ci-pipeline
        - ACT-ai-agent
    revalidated:
      at: 2026-10-19T06:13:45Z
      outcome: unchanged
      unchanged-because: cli.py changed only in the capability install, register and upgrade commands, which now end with the questions a data point declares. The release, migration and report commands this use case describes are untouched.
---

# UC-010 — Never ship a backbone change that breaks installed projects without the migration that carries them across

**Goal:** Never ship a backbone change that breaks installed projects without the migration that carries them across.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the migration check on every pull request, with no person to answer. The check fails while a rename or a removal it finds has no migration.
- **AI agent** (`ACT-ai-agent`): writes the migration for the maintainer through the `migration-author` skill, which pairs with the stamp of step 2.

**Preconditions:** None.

**Assumptions:**

- The maintainer judges what breaks installed projects. The check reads only renames and removals of files, in the trees it reads as the backbone's, an adapter's or a capability's (`migrations.py`). Another break, such as a flag whose meaning inverts, rests on that judgement (COR-010).
- Only the release step writes versions (PRJ-002 D3). The backbone's changeset for the change declares `minor` or above, so the release step that ships the change raises the backbone's minor or major. A patch release carries no migration (COR-010).

**Trigger:** The maintainer's change breaks what installed projects hold, such as renaming or removing a file in a tree the backbone ships.

**Main path:**

1. The maintainer runs `pkit new migration --tier backbone --name <slug>` without `--version`, or has an AI agent run the command through the `migration-author` skill.
2. The system takes the next minor past the backbone version that the default branch records in `.pkit/VERSION`. The system prints `Version: <X.Y.0>, the next minor past backbone <version>, which the default branch 'main' records.` and stamps `<NNN>-<slug>.sh` in `.pkit/migrations/backbone/<X.Y.0>/`.
3. The maintainer writes the script to carry installed projects across. The script is safe to run twice, and acts only on a positive sign that its change is needed (COR-010).
4. The maintainer runs `pkit migrations check-diff --include-working-tree` before committing.
5. The system lists each rename and removal the change makes in the trees the check reads, with each one's tier. It also lists each migration script the change adds, and ends with `Verdict: COVERED (every tier:component with triggers has a matching migration).`
6. The maintainer commits the change with its migration and its changeset (UC-003).
7. The CI pipeline runs `pkit migrations check-diff` on the pull request, and the check passes. The check reads the change from where the branch left its target, and the backbone's version at the target's tip.
8. For the release that ships the change, the release step computes the version the migration's folder names (UC-008).

**Variants:**

- **1a.** The change only adds, such as a new skill or a new schema, or it refines a document. It needs no migration (COR-010). The check reports `No migration-triggering changes in diff.`, and the use case ends.
- **1b.** The change renames or removes a decision record. The check finds no trigger in the decision record (`migrations.py`), and the use case ends.
- **1c.** The maintainer passes `--version <X.Y.0>`, as the `migration-author` skill asks where the release step will raise the major and no folder of that major waits. At step 2, the system stamps the script in that version's folder.
- **2a.** A folder of the next major already waits, in the working tree or on the default branch. The system takes that major instead, and prints `Version: <N.0.0>, the next major past backbone <version>, whose folder <N.0.0>/ already waits.` So the script runs after the migrations of the change that made the folder.
- **2b.** The default branch has commits but resolves to none in this clone, or the default branch's tree cannot be read. The system warns that `The migration's version is judged against the working tree alone, so it may name a version the default branch has released`, and takes the next minor past the working tree's `.pkit/VERSION`. The check of step 7 still reads the target's tip (7a).
- **2c.** On the path of 1c, the version given is at or below the backbone version that the default branch records. The system refuses with `--version <X.Y.0> is already released`, and names the version the system picks without `--version`. The path rejoins at step 1.
- **2d.** On the path of 1c, the version given is not of the form `X.Y.0`, such as `1.150.3`. The system refuses with `version '1.150.3' must be X.Y.0 (patch segment must be 0 per COR-010 — patches have no migrations).`, and the path rejoins at step 1.
- **3a.** The script adds a default that a project lacks. A later run over a project whose history is unknown may restore a default the project removed. The maintainer names that default in the changeset, so the release's notes carry the sentence (COR-010).
- **5a.** A rename or a removal has no migration of its tier and component. The system ends with `Verdict: UNCOVERED. Author migrations for the following tiers before merging:`, lists `backbone`, and exits 1. The path rejoins at step 1.
- **5b.** The change breaks installed projects in a way the check cannot see. Examples are a flag whose meaning inverts, and a rename in a tree the check does not read, such as `.pkit/permissions/`. The check finds no trigger and passes, whether or not the change holds a migration. The path goes on at step 6.
- **5c.** The change moves a file out of the backbone's trees, such as from `.pkit/skills/core/` to `.pkit/skills/project/`. The check reads a rename by its new path alone, so the check finds no trigger and passes. The path goes on at step 6.
- **7a.** After the branch was cut, a release landed on the target with the backbone at the version of the script's folder or above. The check lists the script with `targets <X.Y.0>, but <base> already records backbone <version>, so a project at <version> never runs it. Move it to <next>/ or a later folder.` The check ends with `Verdict: RELEASED. Move each script above to a version not yet released before merging.` and exits 1. The maintainer moves the script to the folder the check names, and the path rejoins at step 4.
- **8a.** The release step computes another version than the folder names. `pkit release plan` warns that the folder `does not match the computed backbone release`, and the release step goes on. The release pull request's body shows the warning for the maintainer to judge.

**Postconditions:** The release that ships the breaking change ships the change's migration, in the folder of the backbone version the release step computes for that release. A project's upgrade across that version runs the migration.

**Minimal guarantees:**

- The check fails a pull request that removes a file in the backbone's trees it reads, such as `.pkit/skills/core/`, or renames the file within them. Such a pull request passes only once it adds a backbone migration (COR-010 and `migrations.py`).
- The check fails a pull request that adds a backbone migration in a folder already released. A folder counts as released when its version is at or below the backbone's version at the target's tip (`migrations.py`).
