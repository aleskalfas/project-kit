---
rule-set: PM
loaded: true
version: 1.0.0
rules:
  RS-PM-001:
    status: proposed
    origin: {decision: "project-management:DEC-013"}
    pkit:
      friction:
        anchors: {record: ["project-management:DEC-013", "COR-009#3"]}
  RS-PM-002:
    status: proposed
    origin: {decision: "project-management:DEC-013"}
    pkit:
      friction:
        anchors: {record: ["project-management:DEC-013", "COR-008"]}
  RS-PM-003:
    status: proposed
    origin: {decision: "project-management:DEC-012"}
    pkit:
      friction:
        anchors: {record: ["project-management:DEC-012"]}
---

## Operational rules of the project-management capability

*These are the project-management capability's operational rules, kept as its loaded rule set `PM` (COR-070). They bind on the work of every session in a project where project-management is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one cannot be kept with a rule of another capability's, stop the step and report the clash. The loaded file is generated from `.pkit/capabilities/project-management/rule-sets/pm.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync or install edits neither.*

### RS-PM-001 — A pull request opens with the issue it closes

**Open a pull request's body with `Closes #<issue>`, naming the issue it closes, as the pull-request template project-management ships does.** A pull request that closes more than one issue names each, as in `Closes #42, closes #43`, and those issues share one parent. `pkit pm open-pr` and `pkit pm edit-pr` check the body (project-management DEC-013).

### RS-PM-002 — Work starts from an issue, and its branch and pull request link to it

**Start a branch only for a Task the tracker holds, and link the branch and its pull request to that Task.** The branch's name carries the Task's number, by core's branch naming (COR-008), and its pull request closes the Task. Where the work has no issue yet, file one with `pkit pm create-issue` before you create the branch. A Task gets one branch, and an EPIC, a Feature, an Umbrella or a sub-task gets none (project-management DEC-013).

### RS-PM-003 — An issue carries one value on each classification axis

**Give each issue you file or edit one value on each classification axis the capability declares, `type`, `priority` and `workstream`, and never two values on one axis.** `type` is always a `type:*` label. The others are labels or board fields, as the project's substrate map binds them. `pkit pm create-issue` sets them and refuses an issue without them; its `type` also gives the Task's title prefix and its pull request's type (project-management DEC-012).
