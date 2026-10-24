---
id: UC-011
title: Carry the projects that installed my component across a breaking change of it
status: active
actor: ACT-component-author
other-actors:
  - ACT-ci-pipeline
  - ACT-ai-agent
  - ACT-operator
requirements:
  - REQ-001
  - REQ-004
  - REQ-005
  - REQ-012
after:
  - [UC-015, UC-019]
shortfalls:
  - at: 9
    issue: "#1765"
    record: ADR-034#1
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
        - COR-054#4
        - PRJ-002#D3
        - ADR-034#1
      artefact:
        - ACT-component-author
        - ACT-ci-pipeline
        - ACT-ai-agent
        - ACT-operator
        - REQ-001
        - REQ-004
        - REQ-005
        - REQ-012
    revalidated:
      at: 2026-10-24T18:58:14Z
      outcome: unchanged
      unchanged-because: The aggregator gains a line that runs the pages' console fences. The migration check still runs in it, as the steps say.
---

# UC-011 — Carry the projects that installed my component across a breaking change of it

**Goal:** Carry the projects that installed my component across a breaking change of it.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the [migration](../../../glossary.md#term-migration--migration) check on every [pull request](../../../glossary.md#term-pull-request--pull-request), with no person to [answer](../../../glossary.md#term-answer--answer). It does so where the [component](../../../glossary.md#term-component--component)'s repository wires the check in, as project-kit's does (UC-006).
- **AI agent** (`ACT-ai-agent`): writes the migration for the author through the `migration-author` [skill](../../../glossary.md#term-skill--skill), which pairs with the [stamp](../../../glossary.md#term-stamp--stamp) of step 2.
- **Operator** (`ACT-operator`): is asked before the stamp writes in a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-015 or UC-019:** The author's [component](../../../glossary.md#term-component--component) exists as a [capability](../../../glossary.md#term-capability--capability) or an [adapter](../../../glossary.md#term-adapter--adapter), and its `package.yaml` holds its [version](../../../glossary.md#term-version--version).

**Assumptions:**

- The author judges what breaks the projects that installed the [component](../../../glossary.md#term-component--component). The check reads only renames and removals of files, in the trees it reads as the [backbone](../../../glossary.md#term-backbone--backbone)'s, an [adapter](../../../glossary.md#term-adapter--adapter)'s or a [capability](../../../glossary.md#term-capability--capability)'s (`migrations.py`). Another break, such as a key whose meaning changes, rests on that judgement (COR-010).
- Only the [release step](../../../glossary.md#term-release-step--release-step) writes [versions](../../../glossary.md#term-version--version) (PRJ-002 D3). The component's [changeset](../../../glossary.md#term-changeset--changeset) for the [change](../../../glossary.md#term-change--change) declares `minor` or above, so the release step that ships the change raises the component's minor or major. A new patch version of the component carries no [migration](../../../glossary.md#term-migration--migration) (COR-010).

**Trigger:** The author's [change](../../../glossary.md#term-change--change) breaks what the projects that installed the [component](../../../glossary.md#term-component--component) hold, such as renaming or removing one of the component's files.

**Main path:**

1. The author runs `pkit new migration --tier capability --component <name> --name <slug>` without `--version`, or has an AI agent run the command through the `migration-author` [skill](../../../glossary.md#term-skill--skill).
9. At its entry, before it writes, the [system](../../../glossary.md#term-system--system) checks that the repository it would [change](../../../glossary.md#term-change--change) is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit new migration` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

2. The system takes the next minor past the [version](../../../glossary.md#term-version--version) that the [component](../../../glossary.md#term-component--component)'s `package.yaml` records on the [default branch](../../../glossary.md#term-default-branch--default-branch). The system prints `Version: <X.Y.0>, the next minor past capability <name> <version>, which the default branch 'main' records.` and stamps `<NNN>-<slug>.sh` in the component's `migrations/<X.Y.0>/` folder.
3. The author writes the script to carry the projects across. The script is safe to run twice (COR-010 and REQ-001).
4. The author runs `pkit migrations check-diff --include-working-tree` before committing.
5. The system matches each rename and removal in the component's folder with a [migration](../../../glossary.md#term-migration--migration) of the same tier and component. It ends with `Verdict: COVERED (every tier:component with triggers has a matching migration).`
6. The author commits the change with its migration and the component's [changeset](../../../glossary.md#term-changeset--changeset) (UC-003).
7. The CI pipeline runs `pkit migrations check-diff` on the [pull request](../../../glossary.md#term-pull-request--pull-request), and the check passes.
8. The [release step](../../../glossary.md#term-release-step--release-step) that moves the component writes the version the migration's folder names (UC-009).

**Variants:**

- **1a.** The [component](../../../glossary.md#term-component--component) is an [adapter](../../../glossary.md#term-adapter--adapter). The author passes `--tier adapter`, and at step 2 the [system](../../../glossary.md#term-system--system) stamps the script in the adapter's `migrations/<X.Y.0>/` folder.
- **1b.** The author passes `--version <X.Y.0>`, as the `migration-author` [skill](../../../glossary.md#term-skill--skill) asks where the [release step](../../../glossary.md#term-release-step--release-step) will raise the major and no folder of that major waits. At step 2, the system stamps the script in that [version](../../../glossary.md#term-version--version)'s folder.
- **2a.** A folder of the component's next major already waits, in the working tree or on the [default branch](../../../glossary.md#term-default-branch--default-branch). The system takes that major instead, and prints `Version: <N.0.0>, the next major past capability <name> <version>, whose folder <N.0.0>/ already waits.` So the script runs after the [migrations](../../../glossary.md#term-migration--migration) of the [change](../../../glossary.md#term-change--change) that made the folder.
- **2b.** The default branch has commits but resolves to none in this clone, or the default branch's tree cannot be read. The system warns that `The migration's version is judged against the working tree alone, so it may name a version the default branch has released`, and takes the next minor past the version in the working tree's `package.yaml`. The check of step 7 still reads the target's tip (7a).
- **2c.** On the path of 1b, the version given is at or below the version that the component's `package.yaml` records on the default branch. The system refuses with `--version <X.Y.0> is already released`, and names the version the system picks without `--version`. The path rejoins at step 1.
- **2d.** On the path of 1b, the version given is not of the form `X.Y.0`, such as `0.55.3`. The system refuses with `version '0.55.3' must be X.Y.0 (patch segment must be 0 per COR-010 — patches have no migrations).`, and the path rejoins at step 1.
- **4a.** The [base](../../../glossary.md#term-base--base) resolves to no commit. The check refuses, naming the references it tried and the fixes, and never guesses a base (COR-054 [point](../../../glossary.md#term-point--point) 4 and REQ-004). The path rejoins at step 4.
- **5a.** A rename or a removal in the component's folder has no migration of that component. A migration of the [backbone](../../../glossary.md#term-backbone--backbone) or of another component does not cover it. The system ends with `Verdict: UNCOVERED. Author migrations for the following tiers before merging:`, lists the component by its tier and name, and exits 1. The path rejoins at step 1.
- **5b.** The change renames or removes files only in the component's `project/` folder, or only a [capability](../../../glossary.md#term-capability--capability)'s [decision records](../../../glossary.md#term-decision-record--decision-record). The check finds no trigger there (`migrations.py`), and the use case ends.
- **5c.** The change breaks the projects in a way the check cannot see, such as a key whose meaning changes. The check finds no trigger and passes, whether or not the change holds a migration. The path goes on at step 6.
- **5d.** The change moves a file out of the component's folder, or into another component's folder. The check reads a rename by its new path alone. So the check finds no trigger, or asks a migration of the component the file moved to. The path goes on at step 6.
- **5e.** The change adds a script whose number another script in its folder holds, perhaps one taken on the target since the branch left it. The system lists the script with the number to take, ends with `Verdict: NUMBER TAKEN. Renumber each script above before merging.` and exits 1. The author renumbers the script, and the path rejoins at step 4.
- **7a.** After the branch was cut, a [release](../../../glossary.md#term-release--release) [pull request](../../../glossary.md#term-pull-request--pull-request) landed on the target with the component at the version of the script's folder or above. The check reads the target's tip, and lists the script with `targets <X.Y.0>, but <base> already records capability <name> <version>, so a project at <version> never runs it. Move it to <next>/ or a later folder.` The check ends with `Verdict: RELEASED. Move each script above to a version not yet released before merging.` and exits 1. The author moves the script to the folder the check names, and the path rejoins at step 4.
- **8a.** The release step writes another version for the component than the folder names. `pkit release plan` warns that the folder `does not match the computed capability <name> release`, or for an adapter `the computed adapter <name> release`, and the release step goes on (`release.py`).

**Postconditions:** The [component](../../../glossary.md#term-component--component)'s [migration](../../../glossary.md#term-migration--migration) sits in the folder of the [version](../../../glossary.md#term-version--version) that the [release step](../../../glossary.md#term-release-step--release-step) writes for the component, and ships with that version. A [project](../../../glossary.md#term-project--project)'s upgrade of the component across that version runs the migration.

**Minimal guarantees:**

- The check fails a [pull request](../../../glossary.md#term-pull-request--pull-request) that removes a file of the [component](../../../glossary.md#term-component--component), or renames the file within the component's folder. Such a pull request passes only once it adds a [migration](../../../glossary.md#term-migration--migration) of that component. The check leaves out the component's `project/` folder and a [capability](../../../glossary.md#term-capability--capability)'s [decision records](../../../glossary.md#term-decision-record--decision-record) (COR-010 and `migrations.py`).
- The check fails a pull request that adds a migration of the component in a folder already released. A folder counts as released when its [version](../../../glossary.md#term-version--version) is at or below the component's version at the target's tip (`migrations.py`).
- The check fails a pull request that adds a migration of the component whose number another script in its folder holds (`migrations.py`). So a folder's scripts run in the order their numbers give.
