---
id: UC-062
title: Have the reviewers my change requires review my pull request, and land it
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-merge-authoriser
  - core:ACT-ai-agent
  - core:ACT-ci-pipeline
  - core:ACT-operator
requirements:
  - REQ-040
  - REQ-041
  - REQ-042
after:
  - [UC-061]
shortfalls:
  - at: "1b"
    issue: "#1938"
    record: COR-004
  - at: 9
    issue: "#2122"
    record: COR-064#2
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/review-pr.py
        - .pkit/capabilities/project-management/scripts/land-work.py
        - .pkit/capabilities/project-management/scripts/done-work.py
        - .pkit/capabilities/project-management/scripts/_lib/pr_review.py
        - .pkit/capabilities/project-management/scripts/_lib/required_reviewers.py
        - .pkit/capabilities/project-management/scripts/_lib/review_contributions.py
        - .pkit/capabilities/project-management/scripts/_lib/review_opt_outs.py
        - .pkit/capabilities/project-management/scripts/_lib/verdict_freshness.py
        - .pkit/capabilities/project-management/scripts/_lib/author_delta.py
        - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
        - .pkit/capabilities/project-management/scripts/_lib/ci_checks.py
        - .pkit/capabilities/project-management/scripts/_lib/friction_answers.py
        - .pkit/capabilities/project-management/scripts/_lib/accepted_records.py
        - .pkit/capabilities/project-management/scripts/_lib/pr_merge.py
        - .pkit/capabilities/project-management/agents/pm-reviewer.md
        - .pkit/capabilities/project-management/schemas/review-contributions.yaml
      record:
        - COR-004
        - project-management:DEC-007
        - project-management:DEC-026
        - project-management:DEC-027
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - project-management:DEC-032#D2
        - project-management:DEC-032#D3
        - project-management:DEC-032#D4
        - project-management:DEC-032#D5
        - project-management:DEC-050
        - project-management:DEC-055#1
        - project-management:DEC-055#3
        - project-management:DEC-055#5
        - COR-013
        - COR-017
        - COR-021
        - COR-039
        - COR-050
        - COR-057
        - COR-062
        - COR-064#2
        - ADR-034#1
        - ADR-061
      artefact:
        - REQ-040
        - REQ-041
        - REQ-042
---

# UC-062 — Have the reviewers my change requires review my pull request, and land it

**Goal:** Have the reviewer agents my change requires review my pull request, each verdict standing only while I change nothing its reviewer checks.

**Other actors:**

- **Merge authoriser** (`core:ACT-merge-authoriser`): authorises the merge of one [head](../../../../core/glossary.md#term-head--head), after reading each `[person]` [finding](../../../../core/glossary.md#term-finding--finding) and the answers the [change](../../../../core/glossary.md#term-change--change) wrote. No [verdict](../../../glossary.md#term-verdict--verdict) stands in for that [authorisation](../../../glossary.md#term-authorisation--authorisation) ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
- **AI agent** (`core:ACT-ai-agent`): each [required reviewer](../../../glossary.md#term-required-reviewer--required-reviewer), which posts its verdict and changes nothing it reviews ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)). An agent may also land the change for the developer, through the `pm` [skill](../../../../core/glossary.md#term-skill--skill).
- **CI pipeline** (`core:ACT-ci-pipeline`): runs the checks the merge waits for, at the [pull request](../../../../core/glossary.md#term-pull-request--pull-request)'s head.
- **Operator** (`core:ACT-operator`): is asked before a command changes a repository other than the session's own, so no such write happens silently ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-061](../020-file-and-move/UC-061-move-issue.md):** The [Task](../../../glossary.md#term-task--task) is in Review, and its [pull request](../../../../core/glossary.md#term-pull-request--pull-request) is open ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md)).

**Assumptions:**

- The [project](../../../../core/glossary.md#term-project--project) has project-management installed, the CLI registers `pkit pm`, and the adapter deploys each [reviewer](../../../../core/glossary.md#term-reviewer--reviewer) agent ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md), [COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md) and [COR-021](../../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md)).
- The backbone runs each reviewer agent the system names, and returns its output (COR-013).
- The backbone answers which artefacts a [change](../../../../core/glossary.md#term-change--change) alters, or brings under a [rule](../../../../core/glossary.md#term-rule--rule), that an accepted rule binds on ([COR-057](../../../../../../.pkit/decisions/core/COR-057-rule-set-reviewer.md)).
- The backbone's [change check](../../../../core/glossary.md#term-change-check--change-check) lists the answers the change wrote, from the [answer](../../../../core/glossary.md#term-answer--answer) files the change adds ([COR-050](../../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) and [COR-062](../../../../../../.pkit/decisions/core/COR-062-answers-in-own-files.md)).
- The backbone merges the [pull request](../../../../core/glossary.md#term-pull-request--pull-request) pinned to a [head](../../../../core/glossary.md#term-head--head), and deletes its branch, as `core:UC-034` describes ([ADR-061](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md)).

**Trigger:** The developer's [change](../../../../core/glossary.md#term-change--change) is ready, and its [Task](../../../glossary.md#term-task--task) is in Review.

**Main path:**

1. The developer runs `pkit pm land-work <N>`, with the [Task](../../../glossary.md#term-task--task)'s number.
2. At its entry, the system checks the [project](../../../../core/glossary.md#term-project--project)'s prerequisites, and the developer's membership where the team keeps a list ([REQ-041](../../../requirements/functional/REQ-041-gates-before-writing.md)). It then checks that the repository it would write in is the session's own, and asks the operator where it is another ([core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)).
3. The system reads the [pull request](../../../../core/glossary.md#term-pull-request--pull-request)'s [head](../../../../core/glossary.md#term-head--head), prints it, and holds it as the head this run judges.
4. The system waits for the checks at that head, and goes on once each has passed. A head with no check reported never counts as passed (`ci_checks.py`).
5. The system works out the [required reviewers](../../../glossary.md#term-required-reviewer--required-reviewer): those the project's settings name, and each a [capability](../../../../core/glossary.md#term-capability--capability) contributes whose condition the [change](../../../../core/glossary.md#term-change--change) meets ([DEC-032 point D1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d1--the-required-local-reviewer-set-resolves-from-the-prs-closing-issues)). It prints them, with each contributed [reviewer](../../../../core/glossary.md#term-reviewer--reviewer) the project declined and its reason ([DEC-032 point D2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d2--capabilities-contribute-reviewer-requirements-pm-collects-them-by-walking-the-manifest)).
6. For each required reviewer whose latest [verdict](../../../glossary.md#term-verdict--verdict) still stands for the head, the system keeps the verdict. It runs the others at once, through `review-pr`, each on the change at that head ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md) and [DEC-032 point D4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d4--review-pr-invokes-the-resolved-set)).
7. Each reviewer posts its verdict, whose first line approves the change or requests changes, and whose marker names the head and the [base](../../../../core/glossary.md#term-base--base) it reviewed. Its [findings](../../../../core/glossary.md#term-finding--finding) follow, each tagged `[block]`, `[person]` or `[advisory]` (DEC-028).
8. The system prints each `[person]` finding whole, and marks one whose verdict no longer stands for the head ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)). Beside them, it prints each accepted decision record the change alters, with the points it edits, for the merge authoriser to judge (`accepted_records.py`).
9. The system lists the answers the change wrote, from the [change check](../../../../core/glossary.md#term-change-check--change-check), and writes the list into the pull request's description ([DEC-055 point 1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#1-the-list)). It prints, beside the list, each revalidation of a document on the base's tip that the change's [answer](../../../../core/glossary.md#term-answer--answer) did not read (DEC-055 point 3).

> [!WARNING]
> **Not built yet:** `land-work` does not show what the change does to the delegate's name. [COR-064 point 2](../../../../../../.pkit/decisions/core/COR-064-answer-delegate.md#2-named-in-committed-configuration-by-the-person-alone) decides that the merge authoriser is shown it, and #2122 tracks it.

10. With no [authorisation](../../../glossary.md#term-authorisation--authorisation) yet, the system stops ready and exits `8`. It names the command that merges: `pkit pm land-work <N> --yes --expect-head <sha>`.
11. The merge authoriser reads the findings and the list, and authorises the merge of the pull request at that head (DEC-055 point 3).
12. The developer runs `pkit pm land-work <N> --yes --expect-head <sha>`, and the system runs steps 2 to 9 again at that head.
13. The system holds the pull request to the [merge gate](../../../glossary.md#term-merge-gate--merge-gate). Each required reviewer's latest verdict must be a standing approval, and each [checkbox](../../../glossary.md#term-checkbox--checkbox) of each [issue](../../../glossary.md#term-issue--issue) the pull request closes must be ticked. The pull request's checks must have passed ([DEC-007](../../../../../../.pkit/capabilities/project-management/decisions/DEC-007-checkbox-validation.md), DEC-028 and `done-work.py`).
14. The system has the backbone merge the pull request, pinned to the head the gate judged. The system then moves to Done, and closes, each issue the pull request closes, and has the branch deleted. It prints `[ok] merged + closed #<N>` ([DEC-026](../../../../../../.pkit/capabilities/project-management/decisions/DEC-026-work-ownership-lifecycle.md) and DEC-028).

**Variants:**

- **1a.** The developer runs `pkit pm review-pr <N>` alone, to have the [change](../../../../core/glossary.md#term-change--change) reviewed before landing it. The system runs steps 2 and 5 to 7, and the use case ends.
- **1b.** The developer passes `--dry-run`. The system makes its checks, says what it would run and merge, and writes nothing ([COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md)). The use case ends.

> [!WARNING]
> **Not built yet:** the dry run names no move of the [cascade](../../../glossary.md#term-cascade--cascade) that the merge would bring about. COR-004 decides that a dry run names each edit a run would make, and #1938 tracks it.

- **2a.** The [project](../../../../core/glossary.md#term-project--project) does not meet the prerequisites, the developer is no member, or the operator declines a write in another repository. The system refuses and writes nothing ([REQ-041](../../../requirements/functional/REQ-041-gates-before-writing.md) and [core:REQ-012](../../../../core/requirements/functional/REQ-012-ask-before-another-repository.md)). The use case ends.
- **4a.** A check fails at the [head](../../../../core/glossary.md#term-head--head). The system names it, and starts no review and no merge. The use case ends.
- **4b.** The checks still run when the wait ends. The system says so and exits `5`, and the developer runs the command again later. The path rejoins at step 1.
- **4c.** The head moves while the system waits. The system stops, names both heads, and exits `3`. The path rejoins at step 1.
- **5a.** The [required reviewers](../../../glossary.md#term-required-reviewer--required-reviewer) cannot be worked out, such as where a contributed [reviewer](../../../../core/glossary.md#term-reviewer--reviewer)'s agent is not deployed. The system refuses, names the cause, and runs no reviewer ([DEC-032 point D5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d5--activation-is-install-driven-the-resolved-set-is-recomputed-at-gate-time)). The use case ends.
- **5b.** The project registers no local reviewer of its own. The system runs each reviewer a [capability](../../../../core/glossary.md#term-capability--capability) contributes that the change requires, as any other ([DEC-032 point D4](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d4--review-pr-invokes-the-resolved-set)). Where the change requires no local reviewer at all, the system says so and runs none.
- **6a.** The developer changed something a reviewer checks since its [verdict](../../../glossary.md#term-verdict--verdict)'s head, or the [pull request](../../../../core/glossary.md#term-pull-request--pull-request) no longer stands on the verdict's [base](../../../../core/glossary.md#term-base--base). The verdict is stale, and the system runs that reviewer again ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).
- **6b.** The developer's only edits since an approving verdict are [answer](../../../../core/glossary.md#term-answer--answer) files the change adds. The verdict of a reviewer that only the condition `touches-code` requires stands, since an answer file is no code ([DEC-032 point D1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d1--the-required-local-reviewer-set-resolves-from-the-prs-closing-issues)).
- **6c.** A reviewer's output holds no line that reads as a verdict. The system counts no verdict for it, prints the reviewer's whole output, and stops, exiting `6` ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)). The use case ends.
- **7a.** A verdict requests changes. The system prints the first line of each `[block]` [finding](../../../../core/glossary.md#term-finding--finding), and starts no merge ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)). The developer changes the work, and the path rejoins at step 1.
- **8a.** A `[person]` finding's verdict was posted while the run went on, or does not stand for the head. A run authorised up front stops ready, and merges nothing until the merge authoriser has seen the finding ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
- **12a.** The head is not the one the [authorisation](../../../glossary.md#term-authorisation--authorisation) named. The system stops before it checks anything, unless each edit since that head lies in answer files the change adds. Then the authorisation covers the later head ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation)).
- **13a.** A required reviewer's latest verdict is missing or stale. The system refuses the merge, and lists each reviewer it still needs. It names `pkit pm review-pr <N>`, with the [Task](../../../glossary.md#term-task--task)'s number, to run them again ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).

- **13b.** A [checkbox](../../../glossary.md#term-checkbox--checkbox) of an [issue](../../../glossary.md#term-issue--issue) the pull request closes is unticked. The system refuses the merge, listing each one ([DEC-007](../../../../../../.pkit/capabilities/project-management/decisions/DEC-007-checkbox-validation.md)). The use case ends.
- **13c.** The developer bypasses one required reviewer: `pkit pm done-work <N> --yes --bypass-reviewer <name> --bypass-reviewer-reason "<R>"`. The system posts the reason in an [audit comment](../../../glossary.md#term-audit-comment--audit-comment) before the merge, and counts that reviewer as satisfied ([DEC-050](../../../../../../.pkit/capabilities/project-management/decisions/DEC-050-per-reviewer-override.md)).
- **13d.** The project's settings set `review.mode` to `human`. A person's approving review counts in place of the verdicts, and `land-work` runs no reviewer ([DEC-027](../../../../../../.pkit/capabilities/project-management/decisions/DEC-027-review-modes.md)).
- **14a.** The base merges through a merge queue. The backbone queues the pull request pinned to the head, and the system exits `4` while it waits in the queue ([ADR-061](../../../../../architecture/decisions/ADR-061-hosting-service-acts-in-the-backbone.md)).

**Postconditions:** The [pull request](../../../../core/glossary.md#term-pull-request--pull-request) merged at the [head](../../../../core/glossary.md#term-head--head) the gate judged, with a standing approval from each [required reviewer](../../../glossary.md#term-required-reviewer--required-reviewer). Each [issue](../../../glossary.md#term-issue--issue) it closed is in Done.

**Minimal guarantees:**

- A [verdict](../../../glossary.md#term-verdict--verdict) that is missing or cannot be read never satisfies the [merge gate](../../../glossary.md#term-merge-gate--merge-gate) ([DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).
- Only a comment that carries the verdict's marker counts as a verdict (DEC-028).
- An approval stands only while the developer changes nothing its [reviewer](../../../../core/glossary.md#term-reviewer--reviewer) checks. A commit the system cannot read makes it stale (DEC-028).
- Where the [required reviewers](../../../glossary.md#term-required-reviewer--required-reviewer) cannot be worked out, nothing merges on part of them ([DEC-032 point D5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d5--activation-is-install-driven-the-resolved-set-is-recomputed-at-gate-time)).
- The merge is pinned to the [head](../../../../core/glossary.md#term-head--head) the gate judged, so a push after the gate fails it (DEC-028).
- Nothing merges through `land-work` without an [authorisation](../../../glossary.md#term-authorisation--authorisation) for that head, given at a terminal or by `--yes` with `--expect-head` ([DEC-055 point 3](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#3-the-review-and-the-authorisation) and [REQ-042](../../../requirements/functional/REQ-042-held-moves-authorised.md)).
- `done-work`, as in variant 13c, pins its merge to the head its gate read (DEC-028 and [DEC-055 point 5](../../../../../../.pkit/capabilities/project-management/decisions/DEC-055-pr-lists-answers.md#5-what-this-does-not-verify)).
