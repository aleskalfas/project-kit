The maintainer's chosen parts, filled with both examples. Each artefact is shown whole, as it would read on the default branch, inside its own fence. Every part is present in both, by the rule for every kind. The ordinary example has nothing for *Other actors*, *Preconditions* or *Assumptions*, so each reads `None.`.

## The landing

````markdown
---
id: UC-xxx
title: Land a change on the default branch
status: active
actor: ACT-developer
involves: [ACT-ci-pipeline, ACT-merge-authoriser, ACT-ai-agent, ACT-operator]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/pull_request_landing.py
        - src/project_kit/friction_check.py
        - src/project_kit/session_guard.py
      record: [COR-009, COR-039, COR-050, COR-054, COR-055, ADR-061]
      artefact: [ACT-developer, ACT-ci-pipeline, ACT-merge-authoriser, ACT-ai-agent, ACT-operator]
---

# UC-xxx — Land a change on the default branch

**Goal:** Land my change on the default branch as one squash commit with a conventional title.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs step 3's checks with no person to answer, against the one base it names for every check (COR-054 point 3).
- **Merge authoriser** (`ACT-merge-authoriser`): sees every answer the change wrote, word for word from the change check's own list, before authorising the merge. The authorisation covers only what was shown (COR-050 point 3).
- **AI agent** (`ACT-ai-agent`): where it acts for the developer, it may write the answers the change check asks before anyone accepts them (COR-050 point 3). A landing it runs never waits on a question nobody is there to answer (ADR-061 point 6).
- **Operator** (`ACT-operator`): is asked before the landing changes a repository other than the session's. Where nobody can be asked, the landing refuses (COR-039 point 1).

**Preconditions:** the change is committed in the project's repository.

**Assumptions:**

- `gh` reaches the repository the change was pushed to. The caller's environment and the working directory's remote decide where `gh` goes, and the guard compares directories only (ADR-061 point 4 and `session_guard.py`).
- Where a queue merges the pull request, its title is still conventional at the merge. The queue reads the title then, and the landing does not check the title (ADR-061 point 8).
- The service shows a change it accepted within the window the landing allows for settling a request (`pull_request_landing.py`). Otherwise a merge or an enqueue with no usable answer can end the landing `failed`, though the service may still apply it (ADR-061 point 7).

**Trigger:** the developer decides that the change is ready to land.

**Main path:**

1. The developer runs `pkit validate` and the change check, `pkit friction check`, on the change's branch, and both pass.
2. The developer pushes the branch and opens a pull request against the default branch, titled `<type>(<scope>): <description>`.
3. The CI pipeline runs the checks the project requires on the pull request, the change check among them, and they pass.
4. The merge authoriser is shown the change check's list of the answers the change wrote, word for word, and authorises the merge.
5. The developer runs `pkit pull-request land <n> --head <sha> --subject "<title>"`, where `<sha>` is the full commit id the checks passed on.
6. The system runs the cross-repository guard, reads the pull request, and checks that the base's merge queue squashes with the defaults `PR_TITLE` and `PR_BODY`.
7. The system hands the pull request to the queue, pinned to `<sha>`, and waits until the queue merges it.
8. The system ends the landing `merged`, naming the head it merged at and the merge commit.
9. The developer deletes the remote head branch with `pkit pull-request delete-branch <n> --expect <merged head>`, and then the local branch.

**Variants:**

- **1a.** Validation fails, or the change check fails in enforcing mode, for example on friction or a bump. The developer fixes the finding, or answers each flagged artefact with `pkit friction revalidate` or `pkit friction defer`. The path rejoins at step 1.
- **2a.** The developer works alone and commits straight to the default branch (COR-009 point 5). Where an agent commits for the developer, the developer is first shown the change check's list. The commits land as they were made, each with a conventional message, and the use case ends.
- **3a.** The change check reports an outdated base, which it never fails on. Unless a queue runs the checks again on the merge, the developer brings in the default branch, and the path rejoins at step 3.
- **3b.** The project requires no check on its pull requests. Nothing runs, and the path goes on at step 4.
- **4a.** An answer is written or reworded after the authorisation, so the authorisation does not cover it. That is a new commit, so the path rejoins at step 3, and step 4 shows the list again.
- **6a.** The working directory's repository is not the session's. The guard asks the operator at a terminal, and refuses without one unless `--allow-foreign-repo` confirms. A refusal sends nothing and ends the use case.
- **6b.** The base has no merge queue, so the system squash-merges the pull request with `<title>` as the subject, pinned to `<sha>`. The commit's body is the repository's default, not yet the pull request's body (ADR-061 point 8). Read merged once, the path rejoins at step 8. Otherwise the system waits as in step 7 with nothing handed to a queue, and ends `not-merged` if no merge comes.
- **6c.** The queue does not squash, or the defaults are not `PR_TITLE` and `PR_BODY`. The landing ends `refused` with nothing sent, and the use case ends.
- **6d.** The pull request's head is not `<sha>`, because a push came after the checks. The system takes the pull request out of the queue if it is there, and ends `head-moved`. The path rejoins at step 3.
- **6e.** The pull request, or the repository's squash defaults, cannot be read, as on a host other than GitHub. The landing ends `unreadable` with nothing sent, and the use case ends.
- **6f.** The pull request is closed, or merged at another head than `<sha>`. The landing ends `closed` or `merged-at-another-head` with nothing sent, and the use case ends.
- **6g.** The service refuses the direct merge of 6b, for example on a check that has not passed. The landing ends `failed`. Where auto-merge holds the pull request, the system warns that the service may merge it later, at whatever head it has then.
- **7a.** The queue drops the pull request, and the landing ends `dropped`. Where no new commit is needed, the developer repeats step 5 with `--allow-dropped-head`. Otherwise the path rejoins at step 3.
- **7b.** The wait runs out with the pull request still queued, and the landing ends `queued`. Repeating step 5 waits again.
- **7c.** A request got no usable answer, and no reading was taken since. The landing ends `unconfirmed`, since whether the request was made is not known. The developer reads the pull request with `pkit pull-request read <n>` and repeats step 5.
- **7d.** A push moves the head while the system waits. As in 6d, the system takes the pull request out of the queue, and the path rejoins at step 3. If the queue merged it at the new head first, the landing ends `merged-at-another-head` instead.
- **9a.** The branch's tip moved since the merge, another open pull request uses the branch, or the service refuses the deletion. The system keeps the branch and says why, and the change has landed all the same.
- **9b.** The branch is already gone, as where the repository deletes head branches on merge. Nothing is deleted, and nothing more is needed.
- **9c.** The head branch is in a fork, so a branch of that name here is not the pull request's. The system refuses, and deletes nothing.
- **9d.** The deletion got no usable answer, and the branch cannot be read since. The system ends `unconfirmed`, and repeating step 9 settles it.

**Postconditions:** the default branch holds the change as one squash commit whose subject is the pull request's title, and the pull request reads merged.

**Minimal guarantees:**

- A landing that ends `refused` or `unreadable` has sent no request, and leaves the pull request as it was (ADR-061 point 5 and `pull_request_landing.py`).
- Each merge or enqueue the landing sends is pinned to `<sha>`. A push after the checks fails it, rather than landing commits nobody checked (ADR-061 point 5).
- While the landing runs, a reading at another head than `<sha>` makes the system ask to take a queued pull request out of the queue. If the queue merged it first, the landing ends `merged-at-another-head` (ADR-061 point 5 and `pull_request_landing.py`).
- Auto-merge is not the landing's request. Where it holds the pull request, a direct merge the service refuses leaves auto-merge armed. The service may then merge the pull request at whatever head it has, and the landing only warns (ADR-061 point 5).
- The system reports a merge only once a reading says merged and names the head. Where a request got no usable answer and no reading follows, the landing ends `unconfirmed`, claiming neither a merge nor its absence (ADR-061 point 5).
- The remote head branch is deleted only once the pull request reads merged, and only while its tip is the head that merged. So a push made after the merge is not lost (ADR-061 point 5).
- Where the harness gives the session's anchor, the guard stops a request from another repository's directory unless the operator confirms (ADR-061 point 6). Where git cannot be asked, the guard warns and lets the request go (`session_guard.py`). The guard is an interlock, not a boundary (COR-039 point 3).
````

## The ordinary example

````markdown
---
id: UC-xxx
title: Think a question through in a scratchpad note
status: active
actor: ACT-developer
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scratchpads.py
      record: [COR-012, COR-043]
      artefact: [ACT-developer]
---

# UC-xxx — Think a question through in a scratchpad note

**Goal:** Think a question too big for a decision through in a scratchpad note, and retire the note once it has produced something.

**Other actors:** None.

**Preconditions:** None.

**Assumptions:** None.

**Trigger:** the developer meets a question too large to settle in one decision record.

**Main path:**

1. The developer picks a slug of two to four words that names the question.
2. The developer runs `pkit new scratchpad <slug>`.
3. The system writes `.pkit/scratchpad/active/<date>-<slug>.md`, with the authors from git, today's date as `started`, and a heading from the slug.
4. The developer maps the question in the note: its forces, what is known, the alternatives and the open questions.
5. Once the note has produced records or documents, the developer runs `pkit scratchpad done <slug> --produced <ref>`.
6. The system moves the note to `done/`, and adds `retired` and `produced` to its front matter.

**Variants:**

- **2a.** A note in any state already uses the slug. The system refuses and writes nothing, and the path rejoins at step 1.
- **4a.** The developer sends the note as a report with `pkit report`. Once the post succeeds, the system moves the note to `reported/` and records the issue it became (COR-043). The note is then frozen, and later thinking goes in a new note. The path rejoins at step 5.
- **5a.** The line of thought does not pan out. The developer adds why to the note and runs `pkit scratchpad drop <slug>`. The system moves the note to `dropped/` and adds `retired`, and the use case ends.

**Postconditions:** the note sits in `done/`, naming what it produced.

**Minimal guarantees:**

- The stamp makes every check before it writes, so a refused stamp writes nothing (`scratchpads.py`).
- Retiring a note moves it, and never deletes it. A dropped note is kept as a record of what was explored (COR-012).
- The report stamps the note only once its post succeeds, so a failed post leaves the note active (COR-043 point 3).
- Notes are the project's own and never synced, so no sync overwrites one (COR-012).
````
