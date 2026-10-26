---
id: UC-034
title: Land my change on the default branch
status: active
actor: ACT-developer
other-actors:
  - ACT-merge-authoriser
  - ACT-operator
after:
  - [UC-014, UC-049]
requirements:
  - REQ-012
shortfalls:
  - at: 5
    issue: "#1257"
    record: ADR-061#8
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/pull_request_landing.py
        - src/project_kit/cli.py
        - src/project_kit/session_guard.py
        - .pkit/rules/core.md
      record:
        - COR-009#1
        - COR-009#2
        - COR-009#4
        - COR-009#5
        - COR-008
        - COR-050#3
        - COR-039
        - ADR-061#3
        - ADR-061#4
        - ADR-061#5
        - ADR-061#6
        - ADR-061#8
      artefact:
        - ACT-developer
        - ACT-merge-authoriser
        - ACT-operator
        - REQ-012
---

# UC-034 — Land my change on the default branch

**Goal:** Land my change on the default branch as one squash commit with a conventional title, through a pull request or directly when I work alone.

**Other actors:**

- **Merge authoriser** (`ACT-merge-authoriser`): authorises the merge of one [head](../../../glossary.md#term-head--head). They read what the [change](../../../glossary.md#term-change--change) updated in the [pull request](../../../glossary.md#term-pull-request--pull-request)'s sentences, and what it leaves out of date in the [change check](../../../glossary.md#term-change-check--change-check)'s list. Where an agent commits straight to the [default branch](../../../glossary.md#term-default-branch--default-branch), the person it works for is the merge authoriser. They are told the same before the commit ([COR-050 point 3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
- **Operator** (`ACT-operator`): is asked before the landing changes the hosting service for a repository other than the session's own. So no such change happens silently ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- The repository is hosted on GitHub, which `gh` reaches from the developer's working directory and environment (ADR-061 points [3](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#3-github-only-through-gh-labelled-provisionally) and [4](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#4-no-hosting-service-settings-in-the-backbone)).
- The command's home in the [backbone](../../../glossary.md#term-backbone--backbone) is provisional. [COR-009](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md) puts a platform's pull-request conventions in [capabilities](../../../glossary.md#term-capability--capability), and #1222 raises the conflict for a core decision (ADR-061 point 3).
- The developer lands only once the [project](../../../glossary.md#term-project--project)'s checks pass at the [head](../../../glossary.md#term-head--head), and the merge authoriser has authorised that head. The command keeps none of these gates, which are its caller's ([ADR-061 point 5](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)).
- The [pull request](../../../glossary.md#term-pull-request--pull-request)'s title follows conventional commits, as [COR-009 point 2](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md#2-pr-title-follows-conventional-commits) asks. No step of the [system](../../../glossary.md#term-system--system) checks it before the merge.
- Before an agent commits straight to the [default branch](../../../glossary.md#term-default-branch--default-branch), the [reviewer](../../../glossary.md#term-reviewer--reviewer) the project chose checks the [change](../../../glossary.md#term-change--change)'s answers. The person the agent works for is told each sentence and each deferral first. Nothing at run time stops the commit ([COR-050 point 3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation) and core rule 20).

**Trigger:** The developer's [change](../../../glossary.md#term-change--change) is ready to land, its checks run at the [pull request](../../../glossary.md#term-pull-request--pull-request)'s [head](../../../glossary.md#term-head--head).

**Main path:**

1. The merge authoriser reads the [pull request](../../../glossary.md#term-pull-request--pull-request)'s sentence on each updated [artefact](../../../glossary.md#term-artefact--artefact), and the [change check](../../../glossary.md#term-change-check--change-check)'s list of answers ([UC-002](UC-002-answer-stale.md)). They authorise the merge of the pull request at its [head](../../../glossary.md#term-head--head) ([COR-050 point 3](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#3-the-revalidation)).
2. The developer runs `pkit pull-request land <n> --head <sha> --subject "<title>"`, with the head that was authorised and the pull request's title.
3. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md) and [ADR-061 point 6](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#6-the-command-guards-the-changes-it-makes)).
4. The system reads the pull request once, for these:
   - its state
   - its head
   - whether its [base](../../../glossary.md#term-base--base) merges through a merge queue
5. On a base without a queue, the system squash-merges the pull request, pinned to `<sha>`. The commit's subject is `<title>`, and its body is the pull request's body (COR-009 points [1](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md#1-squash-merge-as-the-default-merge-style) and [2](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md#2-pr-title-follows-conventional-commits), and [ADR-061 point 8](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#8-cor-009s-landing-realised)).

> [!WARNING]
> **Not built yet:** a direct merge passes the subject alone, so the commit's body is whatever the repository's default composes. ADR-061 point 8 decides that a direct merge carries the pull request's body, read just before the request, and #1257 tracks it.

6. The system reads the pull request again, and ends `merged` once a reading says it merged at `<sha>`, naming the merge commit.
7. The developer deletes the head branch with `pkit pull-request delete-branch <n> --expect <sha>`. The system deletes it only while its tip is the head that merged ([COR-009 point 4](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md#4-feature-branches-are-short-lived-and-deleted-after-merge) and [ADR-061 point 5](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)).

**Variants:**

- **1a.** The developer works alone, and commits the [change](../../../glossary.md#term-change--change) straight to the [default branch](../../../glossary.md#term-default-branch--default-branch), as [COR-009 point 5](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md#5-prs-are-recommended-not-enforced) allows. It is one commit, its subject a conventional title ([COR-008](../../../../../../.pkit/decisions/core/COR-008-git-conventions.md)). Where an agent commits, it first tells the merge authoriser what the change updated, and what the change leaves out of date (core rule 20). No command of the [system](../../../glossary.md#term-system--system) carries this way, and the use case ends.
- **2a.** The developer passes `--dry-run`. The system checks the repository as step 3 does, but asks no one, so in another repository it refuses unless `--allow-foreign-repo` is passed. Otherwise it takes its one reading, says what the landing would do, and sends nothing. The use case ends.
- **2b.** `<sha>` is no full commit id, such as an abbreviated one. The system refuses it as a usage error, reads nothing, and exits `2`, since an abbreviated [head](../../../glossary.md#term-head--head) would read as another head.
- **3a.** The repository is another, and the operator declines. Or nobody can reply, and the developer passed no `--allow-foreign-repo`. The system refuses, sends nothing, and the use case ends.
- **4a.** The [pull request](../../../glossary.md#term-pull-request--pull-request) merged already at `<sha>`. The system ends `merged`, sends nothing, and the path goes on at step 7.
- **4b.** The reading shows another head than `<sha>`. Where the pull request is queued, the system takes it out of the queue, so no commit nobody checked merges. The system ends `head-moved`, and the path rejoins at step 1 for the new head.
- **4c.** The pull request is closed unmerged, or the reading cannot be taken. The system ends `closed` or `unreadable`, sends nothing, and the use case ends.
- **5a.** The [base](../../../glossary.md#term-base--base) merges through a merge queue. The system checks that the queue squashes, and that the repository's squash-commit defaults are `PR_TITLE` and `PR_BODY`, and refuses otherwise ([ADR-061 point 8](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#8-cor-009s-landing-realised)). It enqueues the pull request pinned to `<sha>`, and waits for the queue to merge it. The path goes on at step 6.
- **5b.** The developer passed `--admin` on a base that merges through a queue. The system refuses, since no administrator merge passes a queue, and sends nothing ([ADR-061 point 5](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)).
- **5c.** The request gets no usable response. The system reads the pull request to settle whether the request was made, and never says the request was not made ([ADR-061 point 5](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)):
  - Where a reading sees the request made, the system goes on.
  - Where two readings do not see the request made, the system ends `failed`.
  - Where no reading can be taken, the system ends `unconfirmed`.

  The developer reads the pull request with `pkit pull-request read <n>`, and the path rejoins at step 2.
- **6a.** The wait runs out with the pull request still queued. The system ends `queued`, and the developer runs the same command again later, which waits for it. The path rejoins at step 2.
- **6b.** The queue drops the pull request. The system ends `dropped`. The developer mends what dropped it, or runs the command again with `--allow-dropped-head` to enqueue it again, and the path rejoins at step 2.
- **7a.** The branch's tip moved after the merge, or another open pull request uses the branch as its head or its base. The system keeps the branch, and says why ([ADR-061 point 5](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides)).

**Postconditions:**

- The [change](../../../glossary.md#term-change--change) is on the [default branch](../../../glossary.md#term-default-branch--default-branch), with every [answer](../../../glossary.md#term-answer--answer) it wrote, its deferrals included.
- Through a [pull request](../../../glossary.md#term-pull-request--pull-request), the change is one squash commit, whose subject is the pull request's title and whose body is the pull request's body. The pull request's head branch is gone.
- Worked alone, the change is one commit made straight on the default branch.
- What the change left without an answer or deferred stays on the default branch as [debt](../../../glossary.md#term-debt--debt) ([COR-050 point 9](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#9-debt-is-derived-from-git-never-kept-in-a-ledger)). So does an [artefact](../../../glossary.md#term-artefact--artefact) the change revalidated apart from another change ([COR-062 point 7](../../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md#7-answers-made-apart-are-debt-not-a-conflict)).

**Minimal guarantees:**

- The landing merges nothing but `<sha>`. Each request is pinned to it, and a [pull request](../../../glossary.md#term-pull-request--pull-request) queued at another [head](../../../glossary.md#term-head--head) is taken out of the queue ([ADR-061 point 5](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#5-the-command-makes-requests-and-reports-facts-the-caller-decides) and `pull_request_landing.py`).
- A merge is stated only once a reading says merged. A request with no usable response is never reported as not made (ADR-061 point 5).
- In a repository other than the session's own, nothing is sent to the hosting service without the operator's yes or `--allow-foreign-repo` ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md) and `session_guard.py`).
- No request reaches a queue that would not make the squash commit [COR-009](../../../../../../.pkit/decisions/core/COR-009-pr-workflow.md) asks for ([ADR-061 point 8](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md#8-cor-009s-landing-realised)).
- The landing deletes no branch. `pkit pull-request delete-branch` deletes one only while its tip is the head that merged (ADR-061 point 5).
