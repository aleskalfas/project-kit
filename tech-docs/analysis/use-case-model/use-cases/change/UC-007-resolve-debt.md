---
id: UC-007
title: Resolve what the default branch left out of date
status: active
actor: ACT-developer
other-actors:
  - ACT-ci-pipeline
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/friction_repository.py
        - src/project_kit/friction_report.py
        - .github/workflows/friction-report.yml
        - .pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/rules/core.md
      record:
        - COR-050#2
        - COR-050#3
        - COR-050#9
        - COR-050#12
        - ADR-055#5
        - software-analysis:DEC-001#5
        - living-docs:DEC-001#5
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
        - ACT-ai-agent
---

# UC-007 — Resolve what the default branch left out of date

**Goal:** Resolve what the default branch left out of date, knowing for each debt the change it came from.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the whole-repository check after each push to the default branch and on a schedule. The check reports its findings and never fails on them (COR-050 point 12).
- **AI agent** (`ACT-ai-agent`): the `analysis-resolver` and the `living-docs` agent propose each answer with its evidence and the commands that write it. Neither writes an answer itself (software-analysis DEC-001 point 5 and living-docs DEC-001 point 5).

**Preconditions:** None.

**Assumptions:**

- An answer that no change of the writer's own owes is a person's decision, shown to the person word for word before it is written. Nothing at run time stops an agent writing one (COR-050 point 3 and core rule 20).

**Trigger:** The whole-repository check reports debt on the default branch.

**Main path:**

1. The CI pipeline runs `pkit friction check --all --json` on the default branch, and publishes its findings where people look. In project-kit, that is one tracking issue, kept by `.github/workflows/friction-report.yml` (ADR-055 point 5).
2. The developer lists the debt with `pkit friction debt`: each stale and deferred finding, oldest first, with its origin's commit, author, date and change.
3. The developer runs `pkit friction explain <artefact>` on a debt. It shows what changed under each anchor since the revalidation point, the commits behind it, and the command that clears each finding.
4. The developer judges each debt. They update the artefact and revalidate it `updated`, revalidate it `unchanged` with why, or defer it to an open follow-up issue.
5. The developer lands the answers in a change of their own, whose change check flags each one `not asked for by this change`.
6. The next whole-repository check finds each answered artefact `current`.

**Variants:**

- **1a.** The clone is shallow, and an artefact's revalidation point lies beyond the cut. The check reports the artefact `unreachable` and does not judge it, until `git fetch --unshallow` brings the history.
- **1b.** An anchor's resolver gives no answer, or names a kind that nothing installed resolves. The artefact is `unresolved`, so the check does not judge it, and never reports it `current`.
- **3a.** The artefact is an analysis artefact or a page. The developer dispatches the `analysis-resolver` or the `living-docs` agent, which proposes the outcome with its evidence and the commands to run. The path goes on at step 4.
- **3b.** The agent cannot ask the person, such as when another agent dispatched it. It returns the commands and runs none, and the person runs those they accept (core rule 20).
- **4a.** The analysis artefact still describes what is wanted, and the code regressed. A defect is reported, and the artefact is revalidated `unchanged`, its reason naming the defect. Where stale versus regressed is unclear, a person decides first (software-analysis DEC-001 point 5).
- **4b.** An anchor is dead, such as a path whose files were removed. The developer corrects the anchor in the block, and revalidates the artefact, since its anchor list changed.

**Postconditions:** Each debt the developer resolved carries a new answer on the default branch, and the whole-repository check no longer reports it.

**Minimal guarantees:**

- The whole-repository check reports what it finds, and never fails on it, in either mode (COR-050 point 12).
- Debt is derived from git at each run, never kept in a ledger, so it never drifts from the history (COR-050 point 9).
- An artefact the check could not judge is never reported `current` (COR-050 point 2).
