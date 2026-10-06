---
id: UC-xxx
title: Land a change on the default branch
status: active
actor: ACT-developer
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/pull_request_landing.py
        - src/project_kit/friction_check.py
        - src/project_kit/session_guard.py
      record: [COR-009, COR-050, COR-055, ADR-061]
      artefact: [ACT-developer]
---

# UC-xxx — Land a change on the default branch

**Goal:** Land my change on the default branch as one squash commit with a conventional title.

**Starts when:** the developer's change is committed on its own branch, and they decide it is ready to land.

**Main path:**

1. The developer runs `pkit validate` and the change check, `pkit friction check`, on the branch, and both pass.
2. The developer pushes the branch and opens a pull request against the default branch, titled `<type>(<scope>): <description>`.
3. The CI pipeline runs the checks the project requires on the pull request, the change check among them, and they pass.
4. The merge authoriser is shown the change check's list of the answers the change wrote, word for word, and authorises the merge.
5. The developer runs `pkit pull-request land <n> --head <sha> --subject "<title>"`, where `<sha>` is the full commit id the checks passed on.
6. The system runs the cross-repository guard, reads the pull request, and checks that the base's merge queue squashes with the defaults `PR_TITLE` and `PR_BODY`.
7. The system hands the pull request to the queue, pinned to `<sha>`, and waits until the queue merges it.
8. The system ends the landing `merged`, naming the head it merged at and the merge commit.
9. The developer deletes the remote head branch with `pkit pull-request delete-branch <n> --expect <merged head>`, and then the local branch.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** Validation fails, or the change check fails in enforcing mode, for example on friction or a bump. The developer fixes the finding, or answers each flagged artefact with `pkit friction revalidate` or `pkit friction defer`. The path rejoins at step 1.
- **2a.** The developer works alone and commits straight to the default branch (COR-009 point 5). Where an agent wrote answers, the developer is shown the change check's list before the commit. The developer commits with a conventional message and pushes, and the use case ends.
- **3a.** The change check reports an outdated base. The developer merges or rebases the default branch into the branch, and the path rejoins at step 3.
- **3b.** The project requires no check on its pull requests. Nothing runs, and the path goes on at step 4.
- **4a.** An answer is written or reworded after the authorisation, so the authorisation does not cover it. The path rejoins at step 4, and the list is shown again.
- **6a.** The working directory's repository is not the session's. The guard asks at a terminal, and refuses without one unless `--allow-foreign-repo` confirms. A refusal sends nothing and ends the use case.
- **6b.** The base has no merge queue. The system squash-merges the pull request with `<title>` as the subject, pinned to `<sha>`, and reads it once. The commit's body is the repository's default, not yet the pull request's body (ADR-061 point 8). Read merged, the path rejoins at step 8, and otherwise at step 7.
- **6c.** The queue does not squash, or the defaults are not `PR_TITLE` and `PR_BODY`. The landing ends `refused` with nothing sent, and the use case ends.
- **6d.** The pull request's head is not `<sha>`, because a push came after the checks. The system takes the pull request out of the queue if it is there, and ends `head-moved`. The path rejoins at step 3.
- **7a.** The queue drops the pull request, and the landing ends `dropped`. Where no new commit is needed, the developer repeats step 5 with `--allow-dropped-head`. Otherwise the path rejoins at step 3.
- **7b.** The wait runs out with the pull request still queued, and the landing ends `queued`. Repeating step 5 waits again.
- **7c.** A request got no usable answer, and no reading was taken since. The landing ends `unconfirmed`, since whether the pull request merged is not known. The developer reads it with `pkit pull-request read <n>` and repeats step 5.
- **7d.** A push moves the head while the system waits. As in 6d, the system takes the pull request out of the queue, and the path rejoins at step 3.
- **9a.** The branch's tip moved since the merge, or another open pull request uses the branch. The system keeps the branch and says why. The change has landed all the same.

**Done when:** the default branch holds the change as one squash commit whose subject is the pull request's title, and the pull request reads merged.
