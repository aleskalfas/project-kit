---
id: UC-006
title: Make my merges wait on the system's checks
status: active
actor: ACT-adopter
other-actors:
  - ACT-ci-pipeline
  - ACT-operator
requirements:
  - REQ-002
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-009
  - REQ-012
  - REQ-015
  - REQ-018
  - REQ-019
  - REQ-020
after:
  - [UC-014, UC-049]
shortfalls:
  - at: 8
    issue: "#1765"
    record: ADR-034#1
  - at: "1d"
    issue: "#1884"
    record: COR-004
  - at: "3d"
    issue: "#1867"
    record: COR-062#4
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/project_config.py
        - src/project_kit/cli.py
        - src/project_kit/friction_check.py
        - src/project_kit/validate.py
        - src/project_kit/validators.py
        - .github/workflows/checks.yml
      record:
        - COR-050#2
        - COR-050#6
        - COR-050#12
        - COR-054#3
        - COR-055#6
        - COR-062#4
        - COR-062#10
        - COR-004
        - ADR-019#2
        - ADR-034#1
        - ADR-055#5
        - ADR-068#6
      artefact:
        - ACT-adopter
        - ACT-ci-pipeline
        - ACT-operator
        - REQ-002
        - REQ-004
        - REQ-005
        - REQ-006
        - REQ-007
        - REQ-009
        - REQ-012
        - REQ-015
        - REQ-018
        - REQ-019
        - REQ-020
    revalidated:
      at: 2026-10-24T20:57:08Z
      outcome: updated
---

# UC-006 — Make my merges wait on the system's checks

**Goal:** Make my merges wait on the system's checks, knowing they bind only once my CI requires them.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs every check with no terminal and no person to reply, and gates the merge on the exit status. It names the [base](../../../glossary.md#term-base--base) once, for every check (COR-054 [point](../../../glossary.md#term-point--point) 3).
- **Operator** (`ACT-operator`): is asked before `pkit config set` writes in a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- The [project](../../../glossary.md#term-project--project)'s continuous integration can run `pkit` on a checkout of each [pull request](../../../glossary.md#term-pull-request--pull-request). The hosting service holds a merge until a required status passes. The [backbone](../../../glossary.md#term-backbone--backbone) ships no workflow that runs these checks, so the adopter wires the job and its required status (ADR-019 [point](../../../glossary.md#term-point--point) 2).
- Branches are kept up to date with their [base](../../../glossary.md#term-base--base), or a merge queue runs the checks again on each merge (COR-050 point 6).

**Trigger:** The adopter decides that the [project](../../../glossary.md#term-project--project)'s merges should wait on the [system](../../../glossary.md#term-system--system)'s checks.

**Main path:**

1. The adopter runs `pkit config set friction.mode enforcing --yes`.
8. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit config set` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

2. The system validates the whole configuration file with the new value, and writes it. It prints `set friction.mode = enforcing  (.pkit/project/config.yaml)`.
3. The adopter adds a job to the [project](../../../glossary.md#term-project--project)'s CI that runs `pkit sync`, then `pkit validate`, `pkit friction check` and the project's other checks. The job sets `PKIT_CHECK_BASE` to the [pull request](../../../glossary.md#term-pull-request--pull-request)'s target, and sets `PKIT_CHECK_HEAD` to the pull request's [head](../../../glossary.md#term-head--head) (COR-062 point 4). In project-kit, that job is `.github/workflows/checks.yml`.
4. The adopter makes that job a required status of the [default branch](../../../glossary.md#term-default-branch--default-branch), on the hosting service.
5. On each pull request, the CI pipeline runs the job with no terminal, and no check asks anything.
6. Each check exits non-zero on what fails it. `pkit validate` fails on an `error` [finding](../../../glossary.md#term-finding--finding). The [change check](../../../glossary.md#term-change-check--change-check) fails on unanswered [friction](../../../glossary.md#term-friction--friction), a `bump`, a dead [anchor](../../../glossary.md#term-anchor--anchor), an unresolved kind and a resolver's missing result. It fails too on an [answer](../../../glossary.md#term-answer--answer) file written as COR-062 point 10 forbids.
7. The hosting service holds the merge until the job passes.

**Variants:**

- **1a.** The value is not a mode, such as `loud`. The [system](../../../glossary.md#term-system--system) refuses it with the schema's message, and writes nothing.
- **1b.** The adopter keeps the default, `warning` mode. The [change check](../../../glossary.md#term-change-check--change-check) reports what it finds and passes, so only [validation](../../../glossary.md#term-validation--validation)'s errors and the other checks fail the job.
- **1c.** The adopter writes `friction.mode` by hand, with a value that is no mode. The change check reads it as `warning`, with a warning line, and `pkit validate` fails on it (COR-050 [point](../../../glossary.md#term-point--point) 12).
- **1d.** The adopter passes `--dry-run`, to see first each edit the command would make. The system names each edit, and writes nothing (REQ-009).

> [!WARNING]
> **Not built yet:** `pkit config set` takes no `--dry-run`, and refuses the flag. COR-004 decides that it offers one, and #1884 tracks it.

- **3a.** The job does not run `pkit sync` first. A registered validator then says "environment not provisioned — run `pkit sync`", an `error` [finding](../../../glossary.md#term-finding--finding), so `pkit validate` fails.
- **3b.** The job's checkout lacks the [base](../../../glossary.md#term-base--base). Each check that compares refuses with its fixes, such as fetching the base or naming another.
- **3c.** The job's checkout is shallow. The change check names, in its header, each [artefact](../../../glossary.md#term-artefact--artefact) whose history the cut hides (UC-002).
- **3d.** The [project](../../../glossary.md#term-project--project)'s merges go through a merge queue, so the job runs on each merge the queue builds too. That merge holds the answers of the changes queued ahead. The change check judges what each [answer](../../../glossary.md#term-answer--answer) read against the [head](../../../glossary.md#term-head--head) of the answer's own [change](../../../glossary.md#term-change--change), never against the queue's merge (COR-062 point 4).

> [!WARNING]
> **Not built yet:** on a queue's merge, the change check reads the queue's merge as each change's own head. COR-062 point 4 decides that the check judges against the change's own head wherever it runs, and #1867 tracks it.

- **4a.** The adopter never makes the job required. The checks run and say what they find, and nothing holds the merge (COR-050 point 12). The use case ends.
- **6a.** The base moved on after the branch left it. The change check reports an `outdated-base` and never fails on it, since the fix is to update the branch.
- **6b.** No [place](../../../glossary.md#term-place--place) is declared yet, or nothing in the places carries the `pkit` container. The change check is dormant and passes.
- **6c.** A [documentation root](../../../glossary.md#term-documentation-root--documentation-root) the [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration) declares does not exist yet. Validation warns of it, and does not fail the job on it (REQ-015).
- **7a.** Someone with the right bypasses the required status, or commits straight to the [default branch](../../../glossary.md#term-default-branch--default-branch). The job does not hold that change.

**Postconditions:** No [pull request](../../../glossary.md#term-pull-request--pull-request) merges into the [default branch](../../../glossary.md#term-default-branch--default-branch) through the hosting service's protection while a check of the required job fails on it.

**Minimal guarantees:**

- An invalid [friction](../../../glossary.md#term-friction--friction) mode fails [validation](../../../glossary.md#term-validation--validation), so enforcement is never switched off silently (COR-050 [point](../../../glossary.md#term-point--point) 12).
- A validator that gives no result fails validation, and never passes it (COR-055 point 6).
- In enforcing mode, a resolver that gives no result fails the [change check](../../../glossary.md#term-change-check--change-check), which could not judge its [anchor](../../../glossary.md#term-anchor--anchor) (COR-050 points 2 and 12).
- An outdated [base](../../../glossary.md#term-base--base) is reported, and never fails the change check (COR-050 point 12).
