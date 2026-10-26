---
id: UC-007
title: Resolve what the default branch left out of date
status: active
actor: ACT-developer
other-actors:
  - ACT-ci-pipeline
  - ACT-ai-agent
  - ACT-operator
requirements:
  - REQ-002
  - REQ-004
  - REQ-005
  - REQ-006
  - REQ-007
  - REQ-009
  - REQ-012
  - REQ-018
  - REQ-019
  - REQ-020
after:
  - [UC-034]
shortfalls:
  - at: 7
    issue: "#1765"
    record: ADR-034#1
  - at: "3b"
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/friction_repository.py
        - src/project_kit/friction_report.py
        - src/project_kit/friction_check.py
        - src/project_kit/agent_runs.py
        - .github/workflows/friction-report.yml
        - .pkit/rules/core.md
      record:
        - COR-050#2
        - COR-050#3
        - COR-050#6
        - COR-050#9
        - COR-050#12
        - COR-062#1
        - COR-062#5
        - COR-062#7
        - COR-064#1
        - COR-064#3
        - COR-064#4
        - COR-064#5
        - ADR-034#1
        - ADR-055#5
        - ADR-066#1
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
        - ACT-ai-agent
        - ACT-operator
        - REQ-002
        - REQ-004
        - REQ-005
        - REQ-006
        - REQ-007
        - REQ-009
        - REQ-012
        - REQ-018
        - REQ-019
        - REQ-020
---

# UC-007 — Resolve what the default branch left out of date

**Goal:** Resolve what the default branch left out of date, knowing for each debt the change it came from.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check) after each push to the [default branch](../../../glossary.md#term-default-branch--default-branch) and on a schedule. The check reports its [findings](../../../glossary.md#term-finding--finding) and never fails on them ([COR-050 point 12](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).
- **AI agent** (`ACT-ai-agent`): an agent an installed [capability](../../../glossary.md#term-capability--capability) ships for an [artefact](../../../glossary.md#term-artefact--artefact)'s type proposes each [answer](../../../glossary.md#term-answer--answer). It gives its evidence and the commands that write it. It runs none of those commands, since each answer is a person's decision, or the delegate's ([COR-050 point 3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) and [COR-064 point 1](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#1-the-answers-a-delegate-decides)).
- **Operator** (`ACT-operator`): is asked before a command that writes an answer changes a repository other than the session's own. So no such write happens silently ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-034](UC-034-land-change.md):** The [default branch](../../../glossary.md#term-default-branch--default-branch) holds [debt](../../../glossary.md#term-debt--debt): a [change](../../../glossary.md#term-change--change) that landed there left an [artefact](../../../glossary.md#term-artefact--artefact) stale, or deferred its [answer](../../../glossary.md#term-answer--answer).

**Assumptions:**

- The [project](../../../glossary.md#term-project--project)'s continuous integration runs the [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check) on the [default branch](../../../glossary.md#term-default-branch--default-branch), as project-kit's `friction-report.yml` does ([ADR-055 point 5](../../../../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md#5-friction-check-enforcing-from-the-day-it-exists)).
- An [answer](../../../glossary.md#term-answer--answer) that no [change](../../../glossary.md#term-change--change) of the writer's own owes is a person's decision, shown to the person word for word before it is written. Where a person named a delegate, the delegate may decide it instead ([COR-064 point 1](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#1-the-answers-a-delegate-decides)). Nothing at run time stops an agent writing one ([COR-050 point 3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) and core rule 20).

**Trigger:** The [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check) reports [debt](../../../glossary.md#term-debt--debt) on the [default branch](../../../glossary.md#term-default-branch--default-branch).

**Main path:**

1. The CI pipeline runs `pkit friction check --all --json` on the [default branch](../../../glossary.md#term-default-branch--default-branch), and publishes its [findings](../../../glossary.md#term-finding--finding) where people look. In project-kit, that is one tracking issue, kept by `.github/workflows/friction-report.yml` ([ADR-055 point 5](../../../../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md#5-friction-check-enforcing-from-the-day-it-exists)).
2. The developer lists the [debt](../../../glossary.md#term-debt--debt) with `pkit friction debt`: each stale, deferred and answered-apart finding, oldest first. Each comes with its origin's commit, author, date and [change](../../../glossary.md#term-change--change) ([COR-050 point 9](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger) and [COR-062 point 7](../../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)).
3. The developer runs `pkit friction explain <artefact>` on a debt. It shows these:
   - what changed under each [anchor](../../../glossary.md#term-anchor--anchor) since the revalidation point
   - the commits behind each finding
   - the command that clears each finding
4. The developer judges each debt, and answers it in one of three ways:
   - updating the [artefact](../../../glossary.md#term-artefact--artefact) and revalidating it `updated`
   - revalidating it `unchanged`, with why it still holds
   - deferring it to an open follow-up issue
7. At its entry, each command that writes an [answer](../../../glossary.md#term-answer--answer) checks that the repository it would write in is the session's own. Where it is another, the command asks the operator ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)). It writes the answer to an answer file of the change's own, as [UC-002](UC-002-answer-stale.md) does ([COR-062 point 1](../../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#1-answers-live-in-answer-files)).

> [!WARNING]
> **Not built yet:** `pkit friction revalidate` and `pkit friction defer` run no such check. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

5. The developer lands the answers in a change of their own. Its [change check](../../../glossary.md#term-change-check--change-check) flags each answer the change was not asked for as `not asked for by this change`. A [reviewer](../../../glossary.md#term-reviewer--reviewer) checks each such answer, whoever decided it ([COR-064 point 4](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#4-a-reviewer-checks-every-answer-no-change-owes)).
6. The next [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check) finds each answered artefact `current`, or `deferred` where the developer deferred it.

**Variants:**

- **1a.** The clone is shallow, and an [artefact](../../../glossary.md#term-artefact--artefact)'s revalidation point lies beyond the cut. The check reports the artefact `unreachable`, and does not judge it until `git fetch --unshallow` brings the history. The path goes on at step 2 for the other debts.
- **1b.** An [anchor](../../../glossary.md#term-anchor--anchor)'s resolver gives no result, or the anchor names a kind that nothing installed resolves. The artefact is `unresolved`, and the check never reports it `current`. The path goes on at step 2 for the other debts.
- **1c.** An anchor resolves to nothing at the latest commit, such as a path whose files were removed. The check reports it as a `dead-anchor`, an error it reports and never fails on, and judges the artefact on its other anchors ([REQ-020](../../../requirements/functional/030-change/REQ-020-dead-anchor-error.md)). The path goes on at step 2.
- **3a.** An installed [capability](../../../glossary.md#term-capability--capability) ships an agent for the artefact's type. The developer dispatches that agent, which proposes the outcome with its evidence and the commands to run, and runs none ([COR-050 point 3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)). The path goes on at step 4.
- **3b.** An agent that an installed capability ships for the artefact's type proposed the [answer](../../../glossary.md#term-answer--answer) before the developer reached the [debt](../../../glossary.md#term-debt--debt). The agent ran with nobody watching, through the [backbone](../../../glossary.md#term-backbone--backbone)'s run command, `pkit agents run`:
  - The command starts the runner the [adapter](../../../glossary.md#term-adapter--adapter) registers, confined to a clone at a pinned commit ([ADR-066 point 1](../../../../../architecture/decisions/ADR-066-unattended-agent-runner.md#1-the-runner-is-a-command-the-adapter-registers-and-the-backbone-runs-it)).
  - At its entry, the command checks that the repository it would write in is the session's own. With nobody to ask, the command refuses another ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

  The developer reads the agent's proposal, a file the run handed back, and the path goes on at step 4.

> [!WARNING]
> **Not built yet:** `pkit agents run` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **4a.** The artefact still describes what is wanted, and a [change](../../../glossary.md#term-change--change) broke what it describes. A defect is reported, and the artefact is revalidated `unchanged`, its reason naming the defect.
- **4b.** An anchor is dead, such as a path whose files were removed. The developer corrects the anchor in the block, and revalidates the artefact, since its anchor list changed. The [change check](../../../glossary.md#term-change-check--change-check) asks for that revalidation, so it is not flagged at step 5.
- **4c.** The debt is an artefact answered apart: two live revalidations of it, neither of which read the other. The developer revalidates it once, judging their combined state. `pkit friction revalidate` names the files of both in the new revalidation's `read`, so the new revalidation replaces the two (COR-062 points [5](../../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#5-what-an-answer-replaces) and [7](../../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)).
- **4d.** A person named a delegate, and an agent other than the delegate drafted the answer. The delegate decides it on the developer's behalf, from what the files hold (COR-064 points [1](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#1-the-answers-a-delegate-decides) and [3](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#3-never-on-an-answer-it-drafted-and-from-what-the-files-hold)). It refers to the developer an answer only an account could settle, such as whether a change was meant. The developer is told afterwards what it decided ([COR-064 point 5](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#5-the-person-is-told-not-asked)).

- **5a.** An answer the developer gives is `updated`, so the artefact's content changed. Each artefact anchored to it owes an answer in the same change ([COR-050 point 6](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#6-friction-in-two-checks)), and the path rejoins at step 4 for each one.

**Postconditions:** Each [artefact](../../../glossary.md#term-artefact--artefact) whose [debt](../../../glossary.md#term-debt--debt) the developer resolved carries a new [answer](../../../glossary.md#term-answer--answer) on the [default branch](../../../glossary.md#term-default-branch--default-branch). The [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check) reports it `current`, or `deferred` with its follow-up.

**Minimal guarantees:**

- The [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check) reports what it finds, and never fails on it, in either mode ([COR-050 point 12](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#12-warning-or-enforcing-and-who-owns-which-finding)).
- [Debt](../../../glossary.md#term-debt--debt) is derived from git at each run, never kept in a ledger, so it never drifts from the history ([COR-050 point 9](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger)).
- An [artefact](../../../glossary.md#term-artefact--artefact) the check could not judge is never reported `current` ([COR-050 point 2](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#2-anchors)).
