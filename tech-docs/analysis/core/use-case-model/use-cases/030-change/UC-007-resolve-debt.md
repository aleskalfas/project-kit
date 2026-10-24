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
  - at: 7
    issue: "#1873"
    record: COR-062#1
  - at: "3b"
    issue: "#1765"
    record: ADR-034#1
  - at: "4c"
    issue: "#1873"
    record: COR-062#5
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
    revalidated:
      at: 2026-10-24T04:58:26Z
      outcome: unchanged
      unchanged-because: A renamed placed file whose derived links alone moved is no longer listed behind a deferral. How a person resolves debt is unchanged.
---

# UC-007 — Resolve what the default branch left out of date

**Goal:** Resolve what the default branch left out of date, knowing for each debt the change it came from.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the whole-repository check after each push to the default branch and on a schedule. The check reports its findings and never fails on them (COR-050 point 12).
- **AI agent** (`ACT-ai-agent`): an agent an installed capability ships for an artefact's type proposes each answer. It gives its evidence and the commands that write it. It runs none of those commands, since each answer is a person's decision (COR-050 point 3).
- **Operator** (`ACT-operator`): is asked before a command that writes an answer changes a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-034:** The default branch holds debt: a change that landed there left an artefact stale, or deferred its answer.

**Assumptions:**

- The project's continuous integration runs the whole-repository check on the default branch, as project-kit's `friction-report.yml` does (ADR-055 point 5).
- An answer that no change of the writer's own owes is a person's decision, shown to the person word for word before it is written. Nothing at run time stops an agent writing one (COR-050 point 3 and core rule 20).

**Trigger:** The whole-repository check reports debt on the default branch.

**Main path:**

1. The CI pipeline runs `pkit friction check --all --json` on the default branch, and publishes its findings where people look. In project-kit, that is one tracking issue, kept by `.github/workflows/friction-report.yml` (ADR-055 point 5).
2. The developer lists the debt with `pkit friction debt`: each stale, deferred and answered-apart finding, oldest first. Each comes with its origin's commit, author, date and change (COR-050 point 9 and COR-062 point 7).
3. The developer runs `pkit friction explain <artefact>` on a debt. It shows these:
   - what changed under each anchor since the revalidation point
   - the commits behind each finding
   - the command that clears each finding
4. The developer judges each debt, and answers it in one of three ways:
   - updating the artefact and revalidating it `updated`
   - revalidating it `unchanged`, with why it still holds
   - deferring it to an open follow-up issue
7. At its entry, each command that writes an answer checks that the repository it would change is the session's own. Where it is another, the command asks the operator (REQ-012). It writes the answer to an answer file of the change's own, as UC-002 does (COR-062 point 1).

> [!WARNING]
> **Not built yet:** `pkit friction revalidate` and `pkit friction defer` run no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

> [!WARNING]
> **Not built yet:** each answer is written in the artefact's own `friction` block. COR-062 point 1 decides that a change writes its answers in answer files of its own, and #1873 tracks it.

5. The developer lands the answers in a change of their own. Its change check flags each answer the change was not asked for as `not asked for by this change`.
6. The next whole-repository check finds each answered artefact `current`, or `deferred` where the developer deferred it.

**Variants:**

- **1a.** The clone is shallow, and an artefact's revalidation point lies beyond the cut. The check reports the artefact `unreachable`, and does not judge it until `git fetch --unshallow` brings the history. The path goes on at step 2 for the other debts.
- **1b.** An anchor's resolver gives no answer, or the anchor names a kind that nothing installed resolves. The artefact is `unresolved`, and the check never reports it `current`. The path goes on at step 2 for the other debts.
- **1c.** An anchor resolves to nothing at the latest commit, such as a path whose files were removed. The check reports it as a `dead-anchor`, an error it reports and never fails on, and judges the artefact on its other anchors (REQ-020). The path goes on at step 2.
- **3a.** An installed capability ships an agent for the artefact's type. The developer dispatches that agent, which proposes the outcome with its evidence and the commands to run, and runs none (COR-050 point 3). The path goes on at step 4.
- **3b.** An agent that an installed capability ships for the artefact's type proposed the answer before the developer reached the debt. The agent ran with nobody watching, through the backbone's run command, `pkit agents run`:
  - The command starts the runner the adapter registers, confined to a clone at a pinned commit (ADR-066 point 1).
  - At its entry, the command checks that the repository it would change is the session's own. With nobody to ask, the command refuses another (REQ-012).

  The developer reads the agent's proposal, a file the run handed back, and the path goes on at step 4.

> [!WARNING]
> **Not built yet:** `pkit agents run` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **4a.** The artefact still describes what is wanted, and a change broke what it describes. A defect is reported, and the artefact is revalidated `unchanged`, its reason naming the defect.
- **4b.** An anchor is dead, such as a path whose files were removed. The developer corrects the anchor in the block, and revalidates the artefact, since its anchor list changed. The change check asks for that revalidation, so it is not flagged at step 5.
- **4c.** The debt is an artefact answered apart: two live revalidations of it, neither of which read the other. The developer revalidates it once, judging their combined state. The revalidation reads both, and replaces them (COR-062 points 5 and 7).

> [!WARNING]
> **Not built yet:** the writers write no answer file, so no revalidation reads another and replaces it. COR-062 point 5 decides that a revalidation replaces the revalidations it read, and #1873 tracks it.

- **5a.** An answer the developer gives is `updated`, so the artefact's content changed. Each artefact anchored to it owes an answer in the same change (COR-050 point 6), and the path rejoins at step 4 for each one.

**Postconditions:** Each artefact whose debt the developer resolved carries a new answer on the default branch. The whole-repository check reports it `current`, or `deferred` with its follow-up.

**Minimal guarantees:**

- The whole-repository check reports what it finds, and never fails on it, in either mode (COR-050 point 12).
- Debt is derived from git at each run, never kept in a ledger, so it never drifts from the history (COR-050 point 9).
- An artefact the check could not judge is never reported `current` (COR-050 point 2).
