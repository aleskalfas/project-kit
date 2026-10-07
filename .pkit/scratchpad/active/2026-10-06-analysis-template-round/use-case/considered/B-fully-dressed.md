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
      record: [COR-009, COR-039, COR-050, COR-055, ADR-061]
      artefact: [ACT-developer]
---

# UC-xxx — Land a change on the default branch

**Goal in context:** Land my change on the default branch as one squash commit with a conventional title. It happens once for every change, after the change's own checks pass.

**Scope:** pkit's backbone, and the hosting service it lands on, GitHub through `gh` (ADR-061 point 3).

**Level:** user goal.

**Stakeholders and interests:**

- **Developer:** wants the change on the default branch in one command, with no push made after the checks lost or merged unchecked.
- **Merge authoriser:** wants to authorise only the answers they were shown, word for word (COR-050 point 3).
- **Readers of the default branch:** want one commit per change with a conventional subject, so the history stays linear and each change reverts in one step (COR-009).
- **Operator:** wants no change made to a repository other than the session's without being asked (COR-039).

**Precondition:** pkit is installed in the project's repository, and the change is committed.

**Minimal guarantees:**

- No request the landing sends merges or queues a commit other than the checked head. A queued pull request whose head moved is taken out.
- A pull request that auto-merge already holds may still merge later, at another head. The landing warns of that and does not prevent it (ADR-061 point 5).
- A merge is reported only once a reading says merged. A request whose outcome is not known is reported as unconfirmed, never as not made.
- The remote head branch is deleted only after the merge, and only while its tip is the head that merged.

**Success guarantees:** the default branch holds the change as one squash commit whose subject is the pull request's title, and the pull request reads merged.

**Trigger:** the developer decides that a committed change is ready to land.

**Main success scenario:**

1. The developer runs `pkit validate` and the change check, `pkit friction check`, on the change's branch, and both pass.
2. The developer pushes the branch and opens a pull request against the default branch, titled `<type>(<scope>): <description>`.
3. The CI pipeline runs the checks the project requires on the pull request, the change check among them, and they pass.
4. The merge authoriser is shown the change check's list of the answers the change wrote, word for word, and authorises the merge.
5. The developer runs `pkit pull-request land <n> --head <sha> --subject "<title>"`, where `<sha>` is the full commit id the checks passed on.
6. The system runs the cross-repository guard, reads the pull request, and checks that the base's merge queue squashes with the defaults `PR_TITLE` and `PR_BODY`.
7. The system hands the pull request to the queue, pinned to `<sha>`, and waits until the queue merges it.
8. The system ends the landing `merged`, naming the head it merged at and the merge commit.
9. The developer deletes the remote head branch with `pkit pull-request delete-branch <n> --expect <merged head>`, and then the local branch.

**Extensions:**

- **1a.** Validation fails, or the change check fails in enforcing mode:
  - **1a1.** The developer fixes the finding, or answers each flagged artefact with `pkit friction revalidate` or `pkit friction defer`.
  - **1a2.** The developer repeats step 1.
- **2a.** The developer works alone and commits straight to the default branch (COR-009 point 5):
  - **2a1.** Where an agent commits for the developer, the developer is first shown the change check's list.
  - **2a2.** The commits land as they were made, each with a conventional message, and the use case ends.
- **3a.** The change check reports an outdated base, which it never fails on:
  - **3a1.** Unless a queue runs the checks again on the merge, the developer brings in the default branch.
  - **3a2.** The checks run again from step 3.
- **3b.** The project requires no check on its pull requests: nothing runs, and the use case goes on at step 4.
- **4a.** An answer is written or reworded after the authorisation, which does not cover it:
  - **4a1.** That is a new commit, so the checks run again from step 3.
  - **4a2.** Step 4 shows the merge authoriser the list again.
- **6a.** The working directory's repository is not the session's:
  - **6a1.** The guard asks at a terminal, and refuses without one unless `--allow-foreign-repo` confirms.
  - **6a2.** A refusal sends nothing, and the use case ends.
- **6b.** The base has no merge queue:
  - **6b1.** The system squash-merges the pull request with `<title>` as the subject, pinned to `<sha>`.
  - **6b2.** The commit's body is the repository's default, not yet the pull request's body (ADR-061 point 8).
  - **6b3.** The system reads the pull request once. Read merged, the use case goes on at step 8.
  - **6b4.** Otherwise the system waits as in step 7 with nothing handed to a queue, and ends `not-merged` if no merge comes.
- **6c.** The queue does not squash, or the defaults are not `PR_TITLE` and `PR_BODY`: the landing ends `refused` with nothing sent, and the use case ends.
- **6d.** The pull request's head is not `<sha>`, because a push came after the checks:
  - **6d1.** The system takes the pull request out of the queue if it is there, and ends `head-moved`.
  - **6d2.** The checks run again from step 3.
- **6e.** The pull request, or the repository's squash defaults, cannot be read, as on a host other than GitHub:
  - **6e1.** The landing ends `unreadable` with nothing sent, and the use case ends.
- **6f.** The pull request is closed, or merged at another head than `<sha>`:
  - **6f1.** The landing ends `closed` or `merged-at-another-head` with nothing sent, and the use case ends.
- **6g.** The service refuses the direct merge of 6b, for example on a check that has not passed:
  - **6g1.** The landing ends `failed`.
  - **6g2.** Where auto-merge holds the pull request, the system warns that the service may merge it later, at whatever head it has then.
- **7a.** The queue drops the pull request, and the landing ends `dropped`:
  - **7a1.** Where no new commit is needed, the developer repeats step 5 with `--allow-dropped-head`.
  - **7a2.** Otherwise the checks run again from step 3.
- **7b.** The wait runs out with the pull request still queued: the landing ends `queued`, and repeating step 5 waits again.
- **7c.** A request got no usable answer, and no reading was taken since:
  - **7c1.** The landing ends `unconfirmed`, since whether the request was made is not known.
  - **7c2.** The developer reads the pull request with `pkit pull-request read <n>` and repeats step 5.
- **7d.** A push moves the head while the system waits: as in 6d. If the queue merged it at the new head first, the landing ends `merged-at-another-head` instead.
- **9a.** The branch's tip moved since the merge, another open pull request uses the branch, or the service refuses the deletion:
  - **9a1.** The system keeps the branch and says why. The change has landed all the same.
- **9b.** The branch is already gone, as where the repository deletes head branches on merge: nothing is deleted, and nothing more is needed.
- **9c.** The head branch is in a fork, so a branch of that name here is not the pull request's: the system refuses, and deletes nothing.
- **9d.** The deletion got no usable answer, and the branch cannot be read since: the system ends `unconfirmed`, and repeating step 9 settles it.

**Technology and data variations:**

- **2.** The pull request is opened in the hosting service's web pages, or with `gh pr create`.
- **5.** The hosting service is GitHub, reached through `gh`. Another service would need its own realisation (ADR-061 point 3).
- **5.** With `--json`, the landing writes one JSON document a line, for a script that calls it.

**Related information:**

- **Frequency:** once for every change that lands through a pull request.
- **Open issues:** a direct merge does not yet carry the pull request's body (#1220). Whether the backbone may act on one hosting service waits for a core decision (#1222).
