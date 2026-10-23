---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-agent-definition, name: agent definition}
      - {id: TERM-answer, name: answer}
      - {id: TERM-base, name: base}
      - {id: TERM-capability, name: capability}
      - {id: TERM-change, name: change}
      - {id: TERM-change-check, name: change check}
      - {id: TERM-component, name: component}
      - {id: TERM-consent, name: consent}
      - {id: TERM-data-point, name: data point}
      - {id: TERM-default-branch, name: default branch}
      - {id: TERM-distribution, name: distribution}
      - {id: TERM-finding, name: finding}
      - {id: TERM-head, name: head}
      - {id: TERM-methodology, name: methodology}
      - {id: TERM-process, name: process}
      - {id: TERM-project, name: project}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-report, name: report}
      - {id: TERM-reviewer, name: reviewer}
      - {id: TERM-role, name: role}
      - {id: TERM-rule, name: rule}
      - {id: TERM-skill, name: skill}
      - {id: TERM-validation, name: validation}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - File a Task under its parent, with its title and the sections its body needs checked as it is filed.
          - Move my issue through its lifecycle, with each move checked and the moves that need my authorisation never made without it.
          - Have the reviewer agents my change requires review my pull request, each verdict standing only while I change nothing its reviewer checks.
      - id: ACT-ai-agent
        name: AI agent
      - id: ACT-ci-pipeline
        name: CI pipeline
      - id: ACT-merge-authoriser
        name: Merge authoriser
      - id: ACT-operator
        name: Operator
TERM-authorisation:
  name: authorisation
  noun-forms: [authorisations]
  status: active
  definition: "person's go-ahead for one move the issue lifecycle leaves to a person, given for that one issue and never standing for a later move"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/workflow.yaml
        record:
          - project-management:DEC-006
          - project-management:DEC-014
          - project-management:DEC-055#3
TERM-cascade:
  name: cascade
  status: active
  definition: "effect of an issue's move on issues above it, each brought forward where it is behind, and offered for closing once no child is open"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/move-issue.py
          - .pkit/capabilities/project-management/scripts/close-issue.py
        record:
          - project-management:DEC-006
          - project-management:DEC-034
TERM-checkbox:
  name: checkbox
  noun-forms: [checkboxes]
  status: active
  definition: "box in an issue's body beside one claim, which is ticked once the claim is checked and must be ticked before the issue closes"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/body-format.yaml
          - .pkit/capabilities/project-management/scripts/_lib/checkbox_gate.py
        record:
          - project-management:DEC-007
          - project-management:DEC-038
TERM-classification-axis:
  name: classification axis
  noun-forms: [classification axes]
  status: active
  definition: "dimension along which every issue takes one value, from a fixed set or the project's own, carried as a label or a board field"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/classification.yaml
        record:
          - project-management:DEC-012
TERM-epic:
  name: EPIC
  noun-forms: [EPICs]
  status: active
  definition: "issue that states an outcome spanning several quarters, under which the work that delivers it is filed"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-004
TERM-feature:
  name: Feature
  status: active
  definition: "issue that claims one coherent piece of functionality, with checkboxes that verify it, under which the Tasks that deliver it are filed"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-004
TERM-batch-plan:
  name: batch plan
  noun-forms: [batch plans]
  status: active
  definition: "outline of issues the project-manager agent files for an intent once a person approves it, each with its parent and use-case entries"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/skills/pm/batch-plan.md
          - .pkit/capabilities/project-management/agents/project-manager/project-manager.md
        record:
          - project-management:DEC-029
          - project-management:DEC-054#3
TERM-issue:
  name: issue
  status: active
  definition: "item of work a GitHub repository tracks, with a title, a body and labels, of one of four types that nest under each other"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-003
          - project-management:DEC-004
TERM-issue-lifecycle:
  name: issue lifecycle
  status: active
  definition: "process that takes an item of tracked work from Todo through Backlog, In Progress and Review to Done, a person holding its start and end"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/workflow.yaml
          - .pkit/capabilities/project-management/scripts/move-issue.py
        record:
          - project-management:DEC-006
          - project-management:DEC-033
TERM-merge-gate:
  name: merge gate
  status: active
  definition: "set of conditions a pull request must meet before project-management lands it: each verdict it needs standing, its checks green, and its issues' checkboxes ticked"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/done-work.py
          - .pkit/capabilities/project-management/scripts/_lib/ci_checks.py
        record:
          - project-management:DEC-028
          - project-management:DEC-007
          - project-management:DEC-026
TERM-milestone:
  name: Milestone
  noun-forms: [Milestones]
  status: active
  definition: "container of issues, kept by GitHub apart from them, that closes at its due date, once its issues close, or at whichever comes first"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/time-containers.yaml
          - .pkit/capabilities/project-management/scripts/_lib/milestone.py
        record:
          - project-management:DEC-016
          - project-management:DEC-004
TERM-parent-reference:
  name: parent reference
  status: active
  definition: "first line of an issue's body that names the issue or Milestone it sits under, in the form its type declares"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
          - .pkit/capabilities/project-management/scripts/_lib/body_parent_ref.py
        record:
          - project-management:DEC-005
TERM-required-reviewer:
  name: required reviewer
  noun-forms: [required reviewers]
  status: active
  definition: "agent whose approving verdict a pull request needs to merge, named in the project's settings or contributed by a capability whose condition the change meets"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/required_reviewers.py
          - .pkit/capabilities/project-management/schemas/review-contributions.yaml
        record:
          - project-management:DEC-032#D1
          - project-management:DEC-032#D2
          - project-management:DEC-027
TERM-task:
  name: Task
  status: active
  definition: "issue for one unit of implementation work, which one pull request delivers"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-004
TERM-umbrella:
  name: Umbrella
  status: active
  definition: "issue that groups related Tasks by a theme they share, and claims no functionality of its own"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/issue-types.yaml
        record:
          - project-management:DEC-004
TERM-use-case-entry:
  name: use-case entry
  noun-forms: [use-case entries]
  status: active
  definition: "item a component fills into a data point of the work-tracking role, naming one goal the project's software serves, by its id, title and status"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/use-cases.schema.json
          - .pkit/capabilities/project-management/scripts/_lib/use_case_citations.py
        record:
          - project-management:DEC-054#1
TERM-verdict:
  name: verdict
  noun-forms: [verdicts]
  status: active
  definition: "comment a reviewer agent posts on a pull request, opening with a line that approves the change or requests changes to it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/scripts/_lib/agent_verdicts.py
          - .pkit/capabilities/project-management/scripts/_lib/verdict_freshness.py
        record:
          - project-management:DEC-028
TERM-workstream:
  name: workstream
  noun-forms: [workstreams]
  status: active
  definition: "long-lived area the project invests in over many outcomes, declared in a file of the project's own, and one value of a classification axis"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/project-management/schemas/workstreams.yaml
          - .pkit/capabilities/project-management/scripts/_lib/workstreams.py
        record:
          - project-management:DEC-018
          - project-management:DEC-012
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than project-management's floor, 1.144.0.
  - **Term:** [agent definition](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-definition--agent-definition)
  - **Term:** [answer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-answer--answer)
  - **Term:** [base](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-base--base)
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [change check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change-check--change-check)
  - **Term:** [component](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-component--component)
  - **Term:** [consent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-consent--consent)
  - **Term:** [data point](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-data-point--data-point)
  - **Term:** [default branch](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-default-branch--default-branch)
  - **Term:** [distribution](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-distribution--distribution)
  - **Term:** [finding](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-finding--finding)
  - **Term:** [head](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-head--head)
  - **Term:** [methodology](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-methodology--methodology)
  - **Term:** [process](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-process--process)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [report](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-report--report)
  - **Term:** [reviewer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-reviewer--reviewer)
  - **Term:** [role](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-role--role)
  - **Term:** [rule](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-rule--rule)
  - **Term:** [skill](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-skill--skill)
  - **Term:** [validation](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-validation--validation)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - File a Task under its parent, with its title and the sections its body needs checked as it is filed.
    - Move my issue through its lifecycle, with each move checked and the moves that need my authorisation never made without it.
    - Have the reviewer agents my change requires review my pull request, each verdict standing only while I change nothing its reviewer checks.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)
  - **Actor:** [CI pipeline](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ci-pipeline.md)
  - **Actor:** [Merge authoriser](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-merge-authoriser.md)
  - **Actor:** [Operator](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-operator.md)

## TERM-authorisation — authorisation

Explained in [VIEW-the-issue-lifecycle](domain-model/030-the-issue-lifecycle.md#authorisation).

**Example:** the developer authorises #1712's move from Todo to Backlog with `promote-issue 1712 --reason "scheduled this week"`. They authorise its landing by naming the [head](../core/glossary.md#term-head--head), in `land-work 1712 --yes --expect-head <sha>`.

**Distinctions:**

- **Consent:** the core's word for a person's agreement to a write. An authorisation decides that an [issue](#term-issue--issue) may make a move the team is bound by. Where a command carries one, the person's confirmation gives both (DEC-006).
- **Approval:** a [verdict](#term-verdict--verdict) that a [pull request](../core/glossary.md#term-pull-request--pull-request)'s [change](../core/glossary.md#term-change--change) may merge. It is no authorisation to merge, which stays the person's (DEC-055 point 3).
- **Bypass:** setting aside, with a reason, a [rule](../core/glossary.md#term-rule--rule) that refuses a move unless a person overrides it. The reason goes into an audit comment before the move. A bypass is how a person authorises such a move (DEC-014 and DEC-046 point 1).

## TERM-cascade — cascade

Explained in [VIEW-the-issue-lifecycle](domain-model/030-the-issue-lifecycle.md#cascade).

**Example:** `start-work 1712` moves #1712 to In Progress. The cascade brings the [EPIC](#term-epic--epic) #1643 from Backlog to In Progress too, and journals the step with the reason `forward cascade from #1712: backlog → in-progress`.

**Distinctions:**

- **A move asked for directly:** a move of the [issue](#term-issue--issue) named, which its [authorisation](#term-authorisation--authorisation) governs. A move of the cascade asks for none, since the person gave it on the issue below (DEC-006).
- **Downward cascade:** a parent's move changing its children. The [issue lifecycle](#term-issue-lifecycle--issue-lifecycle) never makes one (DEC-006).
- **Closing a parent:** the cascade never closes one. It makes the parent eligible to close, and a person authorises the close (DEC-006 and DEC-034).

## TERM-checkbox — checkbox

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#checkbox).

**Example:** #1712's acceptance criteria are eight checkboxes, such as one that `pkit analysis check-numbers` passes. A checkbox that names an [issue](#term-issue--issue), such as `- [ ] #99`, is ticked by GitHub when that issue closes.

**Distinctions:**

- **Sub-task:** a checkbox of a [Task](#term-task--task)'s body that names a piece of work. It holds up the close as any checkbox does (DEC-004 and DEC-007).
- **Acceptance criteria:** the section of a [Feature](#term-feature--feature)'s or a Task's body that holds its checkboxes. An [EPIC](#term-epic--epic) holds its own under *Success criteria* (DEC-010).

## TERM-classification-axis — classification axis

Explained in [VIEW-classification-of-issues](domain-model/020-classification-of-issues.md#classification-axis).

**Example:** #1712 takes one value on each of the three axes: `type:docs`, `priority:Medium` and `workstream:docs`.

**Distinctions:**

- **Type of an issue:** [EPIC](#term-epic--epic), [Feature](#term-feature--feature), [Umbrella](#term-umbrella--umbrella) or [Task](#term-task--task), which places the [issue](#term-issue--issue) in the hierarchy. The `type` axis gives its kind of work instead, such as `bug` or `docs` (DEC-004 and DEC-012).
- **Label:** GitHub's tag on an issue. It always carries the `type` axis, and carries the other two where no board field does (DEC-012).

## TERM-epic — EPIC

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#epic).

**Example:** #1643 is an EPIC, and #1890 is filed under it, since its body opens `EPIC: #1643`.

**Distinctions:**

- **Milestone:** a container of issues that GitHub keeps apart from them. An EPIC sits directly under one, and never deeper (DEC-004).
- **Feature:** an [issue](#term-issue--issue) that claims one coherent piece of functionality, with [checkboxes](#term-checkbox--checkbox) that verify it. It sits under an EPIC, or straight under a [Milestone](#term-milestone--milestone) where the [project](../core/glossary.md#term-project--project) skips the EPIC (DEC-004).
- **Umbrella:** an issue that groups related Tasks by a theme, and claims nothing (DEC-004).

## TERM-feature — Feature

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#feature).

**Example:** a Feature claims that a [project](../core/glossary.md#term-project--project) can rename a [workstream](#term-workstream--workstream). Three Tasks under it deliver the command, its tests and its documentation, and its [checkboxes](#term-checkbox--checkbox) say how the claim is verified.

**Distinctions:**

- **Umbrella:** an [issue](#term-issue--issue) that groups Tasks by a theme, and claims nothing. A Feature never holds another Feature or an [Umbrella](#term-umbrella--umbrella) (DEC-004 and DEC-005).
- **EPIC:** an issue that states an outcome spanning several quarters. A Feature sits under one, or straight under a [Milestone](#term-milestone--milestone) where the project skips the [EPIC](#term-epic--epic) (DEC-004).
- **Capability:** the core's word for a [component](../core/glossary.md#term-component--component) a project chooses to install. project-management's records say that a Feature claims "a [capability](../core/glossary.md#term-capability--capability)", meaning a piece of functionality in any component (DEC-004).

## TERM-batch-plan — batch plan

Explained in [VIEW-batch-planning](domain-model/050-batch-planning.md#batch-plan).

**Example:** for the intent "let a [project](../core/glossary.md#term-project--project) rename a [workstream](#term-workstream--workstream)", the batch plan holds a [Feature](#term-feature--feature) under an [EPIC](#term-epic--epic) and three Tasks under the Feature. Each row gives its type, title, parent, workstream, [Milestone](#term-milestone--milestone), priority and [use-case entries](#term-use-case-entry--use-case-entry).

**Distinctions:**

- **The `batch-plan` procedure:** the sub-procedure of the `pm` [skill](../core/glossary.md#term-skill--skill) that the agent follows to draft a batch plan, ask for its approval and file it (DEC-029).
- **Filing:** what the agent does once the person approves the batch plan. It files each [issue](#term-issue--issue) through the [capability](../core/glossary.md#term-capability--capability)'s own commands, which check it as they file it (DEC-029).

## TERM-issue — issue

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#issue).

**Example:** #1712 is an issue of the [Task](#term-task--task) type. Its title opens with `[Docs]`, and its labels are `type:docs`, `priority:Medium` and `workstream:docs`.

**Distinctions:**

- **Pull request:** a proposal to land one [change](../core/glossary.md#term-change--change), which closes the Task it names. It takes none of the four types (DEC-005).
- **Milestone:** a container that GitHub keeps apart from issues. It holds issues, and is none itself (DEC-004).
- **Report:** an issue an adopter files on the repository of the [distribution](../core/glossary.md#term-distribution--distribution) they use. A [project](../core/glossary.md#term-project--project) files its own Tasks to fix one (DEC-048).

## TERM-issue-lifecycle — issue lifecycle

Explained in [VIEW-the-issue-lifecycle](domain-model/030-the-issue-lifecycle.md#issue-lifecycle).

**Example:** #1712 is in Backlog. `start-work 1712` moves it to In Progress, `review-work 1712` moves it to Review, and the merge of its [pull request](../core/glossary.md#term-pull-request--pull-request) moves it to Done.

**Distinctions:**

- **Process:** the core's word for any declared course of a subject through states. The issue lifecycle is the [process](../core/glossary.md#term-process--process) project-management defines for issues, which the core's engine checks (DEC-033).
- **Review:** the state of a [Task](#term-task--task) whose pull request is open. A container never enters it, and goes from In Progress to Done by its own close (DEC-006).
- **A board's Status column:** a projection of the state, where a [project](../core/glossary.md#term-project--project) keeps a Projects v2 board. Where the two disagree, the state the [issue](#term-issue--issue) itself carries wins (DEC-006).

## TERM-merge-gate — merge gate

Explained in [VIEW-reviews-and-the-merge](domain-model/040-reviews-and-the-merge.md#merge-gate).

**Example:** `done-work 1712` reads each [required reviewer](#term-required-reviewer--required-reviewer)'s latest [verdict](#term-verdict--verdict) on #1712's [pull request](../core/glossary.md#term-pull-request--pull-request), its checks and #1712's [checkboxes](#term-checkbox--checkbox). It merges only once each holds, at the [head](../core/glossary.md#term-head--head) it judged.

**Distinctions:**

- **Branch protection:** GitHub's own [rule](../core/glossary.md#term-rule--rule) on a branch, which the hosting service holds. The merge gate is project-management's, and it runs before the merge is asked for (DEC-003 and DEC-028).
- **Authorisation to merge:** the person's go-ahead for the pull request at its head. A gate that passes gives no [authorisation](#term-authorisation--authorisation), and an authorisation passes no gate (DEC-055 point 3).
- **Change check:** the core's comparison of a head with its [base](../core/glossary.md#term-base--base). The landing command runs it to list the answers a [change](../core/glossary.md#term-change--change) wrote, and the merge gate judges none of them (DEC-055 point 3).

## TERM-milestone — Milestone

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#milestone).

**Example:** project-kit's Milestones of the category `housekeeping` close at their due date, and roll their open issues forward to the next. Those of the category `milestone` close once every [EPIC](#term-epic--epic) under them closes.

**Distinctions:**

- **EPIC:** an [issue](#term-issue--issue) that states one outcome. It sits directly under a Milestone, which may hold several (DEC-004 and DEC-016).
- **Workstream:** a long-lived area that classifies issues and never holds them. A theme that never closes is a [workstream](#term-workstream--workstream), never a Milestone (DEC-016).
- **Iteration:** an optional field of a Projects v2 board for a shorter window, which nothing requires (DEC-016).

## TERM-parent-reference — parent reference

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#parent-reference).

**Example:** #1712's body opens with `EPIC: #1643`, its parent reference. A [Task](#term-task--task) straight under a [Milestone](#term-milestone--milestone) opens with `Milestone: #<N>` instead.

**Distinctions:**

- **Sub-issue link:** GitHub's own field that holds an [issue](#term-issue--issue)'s parent. Where the two disagree, the sub-issue link wins, and the first line is rewritten to match it (DEC-005).
- **A reference in a section of the body,** such as "blocked by #12". It relates two issues in text, and makes neither the parent of the other (DEC-005).

## TERM-required-reviewer — required reviewer

Explained in [VIEW-reviews-and-the-merge](domain-model/040-reviews-and-the-merge.md#required-reviewer).

**Example:** software-engineering contributes `code-reviewer` under the condition `touches-code`. A [pull request](../core/glossary.md#term-pull-request--pull-request) that changes `x.py` needs its approving [verdict](#term-verdict--verdict), beside that of `pm-reviewer`, which project-kit's settings name.

**Distinctions:**

- **Reviewer:** the core's word for any agent or person who reports on a [change](../core/glossary.md#term-change--change). A required reviewer is one whose verdict project-management waits for (DEC-032 point D1).
- **An opted-out reviewer:** a contributed one that the [project](../core/glossary.md#term-project--project) declines in its settings, with its reason. It is not required (DEC-032 point D2).

## TERM-task — Task

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#task).

**Example:** #1712 is a Task under the [EPIC](#term-epic--epic) #1643, and one [pull request](../core/glossary.md#term-pull-request--pull-request) delivers it.

**Distinctions:**

- **Sub-task:** a [checkbox](#term-checkbox--checkbox) in a Task's body, and no [issue](#term-issue--issue). Once it needs its own pull request, it becomes a Task under the parent of the Task that held it (DEC-004 and DEC-010).
- **Feature:** an issue that claims a coherent piece of functionality, which several Tasks deliver (DEC-004).
- **Kind of work:** the value a Task takes on the `type` [classification axis](#term-classification-axis--classification-axis), such as `bug` or `docs`. It sets the prefix of the Task's title, and a Task of any kind is still a Task (DEC-012).

## TERM-umbrella — Umbrella

Explained in [VIEW-issues-and-their-hierarchy](domain-model/010-issues-and-their-hierarchy.md#umbrella).

**Example:** an Umbrella groups the Tasks that tidy the CLI's messages. Its body needs only a `## Purpose` section, which says what holds them together.

**Distinctions:**

- **Feature:** an [issue](#term-issue--issue) that claims functionality, with [checkboxes](#term-checkbox--checkbox) that verify it. An Umbrella may hold another Umbrella, and a [Feature](#term-feature--feature) holds none (DEC-004 and DEC-005).
- **Workstream:** a long-lived area that classifies issues across many outcomes, and holds none. An Umbrella holds its Tasks, and closes (DEC-004 and DEC-018).

## TERM-use-case-entry — use-case entry

Explained in [VIEW-batch-planning](domain-model/050-batch-planning.md#use-case-entry).

**Example:** in project-kit, software-analysis fills the [data point](../core/glossary.md#term-data-point--data-point). One of its entries is `UC-044`, titled "Write a page for the reader it names", `active`, with the path of its file.

**Distinctions:**

- **Use case:** another [component](../core/glossary.md#term-component--component)'s description of how the software fulfils one goal, with its steps. A use-case entry names one by its id and title, and holds none of its steps (DEC-054 point 1).
- **A citation in an issue's body:** a line of the body's `## Use cases` section, such as `- UC-044 — Write a page for the reader it names`. It names an entry by its id, and [validation](../core/glossary.md#term-validation--validation) warns where the data point holds no such id (DEC-054 point 4).

## TERM-verdict — verdict

Explained in [VIEW-reviews-and-the-merge](domain-model/040-reviews-and-the-merge.md#verdict).

**Example:** `pm-reviewer` posts a comment on #1712's [pull request](../core/glossary.md#term-pull-request--pull-request) that opens with `Reviewer agent (local, pm-reviewer): APPROVED`. Its marker names the [head](../core/glossary.md#term-head--head) and the [base](../core/glossary.md#term-base--base) it reviewed.

**Distinctions:**

- **Native review:** GitHub's own review state, which `review-pr` posts beside the verdict for branch protection to read. project-management reads the verdict, never the native review (DEC-028).
- **Finding:** a statement inside a verdict, tagged `[block]`, `[person]` or `[advisory]`. A `[block]` [finding](../core/glossary.md#term-finding--finding) makes the verdict request changes, and only the first line counts at the gate (DEC-028).
- **A free comment:** one posted with `comment-pr`. That command refuses a body whose first line would read as a verdict (DEC-047 point 5).
- **A person's approval:** in the `human` review mode, a person's approving review counts in a verdict's place (DEC-027).

## TERM-workstream — workstream

Explained in [VIEW-classification-of-issues](domain-model/020-classification-of-issues.md#workstream).

**Example:** project-kit declares the workstream `docs` in `.pkit/capabilities/project-management/project/workstreams.yaml`, and #1712 carries it as `workstream:docs`.

**Distinctions:**

- **EPIC:** an [issue](#term-issue--issue) that scopes one outcome inside a workstream. A workstream outlasts its [EPICs](#term-epic--epic), and never closes (DEC-018).
- **Milestone:** a container that closes. A theme that never ends takes a workstream to group its issues, and a rolling date-based [Milestone](#term-milestone--milestone) where it needs a parent that closes (DEC-016).
