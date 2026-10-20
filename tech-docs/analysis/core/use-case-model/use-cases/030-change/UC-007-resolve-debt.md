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
        - src/project_kit/friction_check.py
        - .github/workflows/friction-report.yml
        - .pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - .pkit/rules/core.md
      record:
        - COR-050#2
        - COR-050#3
        - COR-050#6
        - COR-050#9
        - COR-050#12
        - ADR-055#5
        - software-analysis:DEC-001#5
        - living-docs:DEC-001#5
      artefact:
        - ACT-developer
        - ACT-ci-pipeline
        - ACT-ai-agent
    revalidated:
      at: 2026-10-20T02:03:37Z
      outcome: unchanged
      unchanged-because: Both agents now end a fixer run in the run contract's line forms, a none carrying one of its reasons, and the resolver takes a run's quoted pull-request text as intent. In a session each still proposes the answers with evidence and commands and runs none, so how a developer resolves debt is untouched.
---

# UC-007 — Resolve what the default branch left out of date

**Goal:** Resolve what the default branch left out of date, knowing for each debt the change it came from.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the whole-repository check after each push to the default branch and on a schedule. The check reports its findings and never fails on them (COR-050 point 12).
- **AI agent** (`ACT-ai-agent`): the `analysis-resolver` and the `living-docs` agent propose each answer with its evidence and the commands that write it. Neither runs those commands itself (living-docs DEC-001 point 5 and `analysis-resolver.md`).

**Preconditions:** The default branch holds debt: a change that landed there left an artefact stale, or deferred its answer.

**Assumptions:**

- The project's continuous integration runs the whole-repository check on the default branch, as project-kit's `friction-report.yml` does (ADR-055 point 5).
- An answer that no change of the writer's own owes is a person's decision, shown to the person word for word before it is written. Nothing at run time stops an agent writing one (COR-050 point 3 and core rule 20).

**Trigger:** The whole-repository check reports debt on the default branch.

**Main path:**

1. The CI pipeline runs `pkit friction check --all --json` on the default branch, and publishes its findings where people look. In project-kit, that is one tracking issue, kept by `.github/workflows/friction-report.yml` (ADR-055 point 5).
2. The developer lists the debt with `pkit friction debt`: each stale and deferred finding, oldest first, with its origin's commit, author, date and change.
3. The developer runs `pkit friction explain <artefact>` on a debt. It shows these:
   - what changed under each anchor since the revalidation point
   - the commits behind each finding
   - the command that clears each finding
4. The developer judges each debt, and answers it in one of three ways:
   - updating the artefact and revalidating it `updated`
   - revalidating it `unchanged`, with why it still holds
   - deferring it to an open follow-up issue
5. The developer lands the answers in a change of their own. Its change check flags each answer the change was not asked for as `not asked for by this change`.
6. The next whole-repository check finds each answered artefact `current`, or `deferred` where the developer deferred it.

**Variants:**

- **1a.** The clone is shallow, and an artefact's revalidation point lies beyond the cut. The check reports the artefact `unreachable`, and does not judge it until `git fetch --unshallow` brings the history. The path goes on at step 2 for the other debts.
- **1b.** An anchor's resolver gives no answer, or the anchor names a kind that nothing installed resolves. The artefact is `unresolved`, and the check never reports it `current`. The path goes on at step 2 for the other debts.
- **3a.** The artefact is an analysis artefact or a page. The developer dispatches the `analysis-resolver` or the `living-docs` agent. It proposes the outcome with its evidence and the commands to run, and runs none. The path goes on at step 4.
- **4a.** The analysis artefact still describes what is wanted, and the code regressed. A defect is reported, and the artefact is revalidated `unchanged`, its reason naming the defect. Where stale versus regressed is unclear, a person decides first (software-analysis DEC-001 point 5).
- **4b.** An anchor is dead, such as a path whose files were removed. The developer corrects the anchor in the block, and revalidates the artefact, since its anchor list changed. The change check asks for that revalidation, so it is not flagged at step 5.
- **5a.** An answer the developer gives is `updated`, so the artefact's content changed. Each artefact anchored to it owes an answer in the same change (COR-050 point 6), and the path rejoins at step 4 for each one.

**Postconditions:** Each artefact whose debt the developer resolved carries a new answer on the default branch. The whole-repository check reports it `current`, or `deferred` with its follow-up.

**Minimal guarantees:**

- The whole-repository check reports what it finds, and never fails on it, in either mode (COR-050 point 12).
- Debt is derived from git at each run, never kept in a ledger, so it never drifts from the history (COR-050 point 9).
- An artefact the check could not judge is never reported `current` (COR-050 point 2).
