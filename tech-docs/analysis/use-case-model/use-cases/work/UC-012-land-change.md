---
id: UC-012
title: Land my change on the default branch
status: active
actor: ACT-developer
other-actors:
  - ACT-merge-authoriser
  - ACT-ai-agent
  - ACT-ci-pipeline
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/open-pr.py
        - .pkit/capabilities/project-management/scripts/review-work.py
        - .pkit/capabilities/project-management/scripts/land-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - .pkit/capabilities/project-management/scripts/review-pr.py
        - .pkit/capabilities/project-management/scripts/_lib/friction_answers.py
        - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
        - .pkit/capabilities/project-management/scripts/_lib/pr_merge.py
        - .pkit/capabilities/project-management/skills/pm/transition-state.md
        - src/project_kit/pull_request_landing.py
        - .pkit/rules/core.md
      record:
        - COR-009#1
        - COR-009#2
        - COR-009#5
        - COR-050#3
        - project-management:DEC-006
        - project-management:DEC-026
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - project-management:DEC-050
        - project-management:DEC-055#1
        - project-management:DEC-055#3
        - project-management:DEC-055#5
        - ADR-061#5
      artefact:
        - ACT-developer
        - ACT-merge-authoriser
        - ACT-ai-agent
        - ACT-ci-pipeline
---

# UC-012 — Land my change on the default branch

**Goal:** Land my change on the default branch as one squash commit with a conventional title, through a pull request or directly when I work alone.

**Other actors:**

- **Merge authoriser** (`ACT-merge-authoriser`): authorises the merge of one head. Before that, the merge authoriser is told what changed in each updated document, and which documents wait for which follow-up. The merge authoriser also sees each finding a reviewer left for a person (COR-050 point 3 and project-management DEC-055 point 3).
- **AI agent** (`ACT-ai-agent`): the `project-manager` agent may land the change for the developer, and runs the merging command only on the merge authoriser's authorisation. The reviewer agents the merge gate requires judge the head (project-management DEC-028 and DEC-032).
- **CI pipeline** (`ACT-ci-pipeline`): runs the project's checks on the pull request's head, which the landing waits for. In project-kit, they include the changeset guard (UC-003).

**Preconditions:** The change is committed on its branch, and the branch is pushed. The project tracks its work through project-management, with an issue for the change.

**Assumptions:**

- The authorisation to merge is the person's, given for one head, per issue and in the session (project-management DEC-006 and DEC-055 point 3). Nothing tells an agent's `--yes` from the person's, since the agent runs under the person's account. So the agent runs the merging command only on the person's word (the `pm` skill's landing step).
- The developer passes the `--expect-head` the `ready:` line names. `--yes` alone merges whichever head the run pins (`land-work.py`).
- Whoever lands the change shows the merge authoriser each finding for a person, whole, before asking. The landing command cannot tell that a person read it (project-management DEC-055 point 5).
- A reviewer other than the writer of the answers checks them, where the project chose one (COR-050 point 3 and UC-002).
- The pull request's title stays conventional. `open-pr` composes it, and nothing checks it again before the merge (`open-pr.py` and `land-work.py`).

**Trigger:** The developer's change is ready to land, its answers written and its changesets declared.

**Main path:**

1. The developer opens the pull request with `pkit pm open-pr <N>`. The system composes its title as `<type>(<scope>): <summary>`. It writes the change check's list of answers into the description, under `## Documentation this change affects` (project-management DEC-055 points 1 and 2).
2. The developer runs `pkit pm review-work <N>`, which moves the issue to Review and marks the pull request ready (project-management DEC-026).
3. The developer, or the `project-manager` agent for the developer, runs `pkit pm land-work <N>`. The system pins the pull request's head, and waits until every check on that head passes.
4. The system has the reviewers the merge gate requires review that head, in parallel. The system keeps each verdict that still stands for the head, and runs the rest again (project-management DEC-028 and DEC-032 D1).
5. The system prints each finding a reviewer left for a person, whole. The system derives the list of answers at the pinned head, prints the list, and writes it into the description.
6. The system stops ready, naming the head and the command that merges it: `ready: <sha> — CI passed, … merge with: pkit pm land-work <N> --yes --expect-head <full sha>`.
7. The developer shows the merge authoriser the verdicts and each finding for a person, whole. The developer also tells the merge authoriser what the lines above `ready:` say. They say what changed in each updated document, and which documents wait for which follow-up.
8. The merge authoriser authorises the merge of that head.
9. The developer runs the `ready:` line's command. The system squash-merges the pinned head, the pull request's title as the commit's subject, and prints `merge: merged as <commit>`.
10. The system moves the issue to Done, closes it, and deletes the head branch at the merged head.

**Variants:**

- **1a.** The developer works alone, and commits straight to the default branch, as COR-009 point 5 allows. Where the project chose a reviewer of the answers, that reviewer checks the answers before the commit. Where an agent commits for the developer, the developer is told each sentence and each deferral first (COR-050 point 3 and core rule 20). No command carries this path, and the use case ends.
- **3a.** A check fails on the head. The system stops with `ci: failed on <sha> — <check> … Review and merge not started`. The developer fixes the change and pushes, and the path rejoins at step 3.
- **3b.** The checks still run when the wait ends. The system stops with `ci: still running on <sha> …`, and the path rejoins at step 3.
- **3c.** The pull request conflicts with its base. The system stops, and names the fix: merge the base into the branch, resolve the conflicts and push. The developer then answers what the combined state made stale (UC-002), and the path rejoins at step 3.
- **3d.** The head moves while the run waits. The system stops, saying the head moved, and the path rejoins at step 3.
- **4a.** A reviewer requests changes. The system stops with `review: changes requested by <reviewers> — the blocking findings are above; merge not started`. The developer fixes each `[block]` finding and pushes, and the path rejoins at step 3.
- **5a.** The list cannot be written as it must be. The system merges nothing and writes nothing, a firm stop with no override (project-management DEC-055 point 3). The cases are these:
  - the list cannot be derived, or a file the change touches cannot be read for answers
  - a word of the list reads as a closing reference, or holds an HTML comment's delimiter
  - the description cannot hold the list
  - the base's commits since the head left it changed a file that carries a listed answer

  The developer mends the cause, and the path rejoins at step 3.
- **8a.** The merge authoriser asks for a change, such as on a finding for a person. The developer makes it and pushes, and the path rejoins at step 3 (the `pm` skill's landing step).
- **9a.** The head moved after the authorisation, with changes outside the `revalidated` blocks. The system stops with `head: stopped — PR #<P>'s head is <sha>, not <sha>, the head the merge was authorised for …`. The new head needs its checks, its review and its own authorisation, and the path rejoins at step 3.
- **9b.** The head moved after the authorisation, and every change since lies inside `revalidated` blocks, a clean merge of the base counting as none. The authorisation covers the later head, and the system merges it, saying which head and why (project-management DEC-055 point 3). The path goes on at step 10.
- **9c.** At that later head, the run finds a finding for a person, or a reason for having no anchors. Or it finds an answer the list flags as `not asked for by this change`. The system stops ready, naming the later head, and the path rejoins at step 7.
- **9d.** A verdict that carries a finding for a person was posted after the run started, or does not stand for the head. The system stops ready instead of merging, and the path rejoins at step 7 (project-management DEC-055 point 3).
- **9e.** The base merges through a queue. The system enqueues the pull request for the pinned head alone, and prints `merge: queued — …`. The developer runs the same command again once the queue merges it.
- **9f.** The merge authoriser decides to bypass a gate, such as one reviewer's approval. The developer runs `done-work` with `--bypass-reviewer <reviewer> --bypass-reviewer-reason "<reason>"`, or `--bypass "<reason>"`. The system posts the audit comment before the merge (project-management DEC-026 and DEC-050).

**Postconditions:** The change is one squash commit on the default branch, its subject the pull request's conventional title. It merged at the head the merge authoriser authorised, or at a later head that authorisation covers, and its issue is Done.

**Minimal guarantees:**

- Only the head the run pinned merges, since the merge names that head to the hosting service (`land-work.py` and `pull_request_landing.py`).
- A run with no terminal and no `--yes` merges nothing, and stops at `ready:` (`land-work.py`).
- Given `--expect-head`, no head merges but the authorised one, or a later head whose every change since lies inside `revalidated` blocks (project-management DEC-055 point 3).
- The list of answers in the description is the list for the head that merges (project-management DEC-055 point 3).
- A missing or unreadable verdict never satisfies the merge gate (project-management DEC-028).
- A run authorised up front merges only where it found each verdict that carries a finding for a person at its start. Each such verdict stands for the head it merges (project-management DEC-055 point 3).
