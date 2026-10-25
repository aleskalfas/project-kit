---
id: UC-073
title: Revalidate the analysis after a change from an agent's proposed outcomes
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-050
  - REQ-052
after:
  - [UC-070]
shortfalls:
  - at: 13
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md
        - .pkit/capabilities/software-analysis/agents/analysis-resolver/storyboard.md
        - .pkit/capabilities/software-analysis/scripts/propose.py
        - .pkit/capabilities/software-analysis/scripts/_lib/resolve.py
        - .pkit/capabilities/software-analysis/scripts/_lib/answers.py
        - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        - .pkit/capabilities/software-analysis/package.yaml
      record:
        - software-analysis:DEC-001#1
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#6
        - software-analysis:DEC-001#8
        - project-management:DEC-056#3
        - project-management:DEC-056#6
        - ADR-034#1
        - COR-013
        - COR-017
        - COR-031
        - COR-050#3
        - COR-050#4
        - COR-050#5
        - COR-050#6
        - COR-050#13
      artefact:
        - REQ-050
        - REQ-052
---

# UC-073 — Revalidate the analysis after a change from an agent's proposed outcomes

**Goal:** Revalidate the analysis after a change, from an agent's proposed outcome for each flagged artefact, and never rewrite the analysis to match broken code.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `analysis-resolver` agent, which proposes each [revalidation outcome](../../glossary.md#term-revalidation-outcome--revalidation-outcome) with its evidence and runs no writer, so the developer decides each [answer](../../../core/glossary.md#term-answer--answer) (REQ-050).
- **Operator** (`core:ACT-operator`): is asked before `pkit analysis new` or `pkit analysis link` writes in a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:** **From UC-070:** The [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record)'s kind has its parts chosen.

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has software-analysis installed, or registered in place where software-analysis is developed, and the [adapter](../../../core/glossary.md#term-adapter--adapter) deploys its `analysis-resolver` [agent definition](../../../core/glossary.md#term-agent-definition--agent-definition) (COR-013, COR-017 and COR-031).
- A [change](../../../core/glossary.md#term-change--change) modified what an [analysis](../../glossary.md#term-analysis--analysis) [artefact](../../../core/glossary.md#term-artefact--artefact)'s anchors name, and the core's [friction](../../../core/glossary.md#term-friction--friction) checks flag the artefact. That is the [change check](../../../core/glossary.md#term-change-check--change-check), the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check) or its [debt](../../../core/glossary.md#term-debt--debt) listing (COR-050 point 5).
- The core's `pkit friction explain` gives each artefact's state, its anchors and the commits behind each changed one, at `schema_version` 1 (COR-050 point 13 and core:REQ-019).
- Each [answer](../../../core/glossary.md#term-answer--answer) is recorded with the core's writers, as `core:UC-002` describes, and the change check lists it for a [reviewer](../../../core/glossary.md#term-reviewer--reviewer) (COR-050 point 3).
- Where project-management is installed and the project granted the agent, project-management's drift command may start it with nobody watching (project-management DEC-056 points 3 and 6).
- Nothing at run time confines the agent to the [agent workspace](../../../core/glossary.md#term-agent-workspace--agent-workspace). Its definition grants no tool that edits a file in place and owns no path, but its Write and its Bash reach any file (COR-013).

**Trigger:** A [friction](../../../core/glossary.md#term-friction--friction) check flags [artefacts](../../../core/glossary.md#term-artefact--artefact) of the [analysis](../../glossary.md#term-analysis--analysis), and the developer wants their [revalidation outcomes](../../glossary.md#term-revalidation-outcome--revalidation-outcome).

**Main path:**

1. The developer asks the `analysis-resolver` agent to resolve the [friction](../../../core/glossary.md#term-friction--friction) that a [change check](../../../core/glossary.md#term-change-check--change-check), the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check) or its [debt](../../../core/glossary.md#term-debt--debt) listing names on the [analysis](../../glossary.md#term-analysis--analysis).
2. The agent loads its [storyboard](../../../core/glossary.md#term-storyboard--storyboard), and takes the flagged [artefacts](../../../core/glossary.md#term-artefact--artefact) of the analysis, upstream first.
3. For each, the agent reads `pkit friction explain <artefact> --json` and the commits behind each changed [anchor](../../../core/glossary.md#term-anchor--anchor), with `git show`. It reads the [change](../../../core/glossary.md#term-change--change)'s context too: the commit messages, the [pull request](../../../core/glossary.md#term-pull-request--pull-request) and the work item.
4. The agent runs `pkit analysis propose <artefact>`, passing what bears on intent as quotes, each with its source: `--intended`, `--unintended` or `--contradicted`.
5. The [system](../../../core/glossary.md#term-system--system) reads what the artefact quotes from its anchored code at its <!-- pkit:not-the-term -->revalidation point and at HEAD, and where lost code went. It checks each quote from a commit against that commit's message, applies its rules in order, and writes nothing (core:REQ-005).
6. The system proposes a [revalidation outcome](../../glossary.md#term-revalidation-outcome--revalidation-outcome), or gives a reading with the outcome it leans to, or finds the case ambiguous and asks its question. For an outcome, it gives what the person does first, and the writer commands word for word, with no `--yes`.
7. The agent checks what the system gave by reading the diff, and proposes each artefact's revalidation outcome (DEC-001 point 5).
8. The agent writes its [revalidation proposal](../../glossary.md#term-revalidation-proposal--revalidation-proposal) under `.agent-workspace/analysis-resolver/<change>/`: `proposal.md`, and a diff for each edit it proposes, checked with `git apply --check` (REQ-050).
9. The agent tells the developer where the proposal lies, what to do first, and the commands. It runs none (REQ-050).
10. The developer reviews each artefact's revalidation outcome against its evidence, and accepts it.
11. The developer applies each diff and does what comes first, such as reporting a defect. The developer records each [answer](../../../core/glossary.md#term-answer--answer) with the commands, as `core:UC-002` describes.
12. Where the [revalidation](../../glossary.md#term-revalidation--revalidation) has something to say, the developer runs the command the proposal drafts for its [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record), `pkit analysis new revalidation` (REQ-052). The command names the agent with `--by-agent analysis-resolver`, and it names the developer with `--confirmed-by` (DEC-001 point 6).
13. At its entry, before it writes, the system checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (core:REQ-012).

> [!WARNING]
> **Not built yet:** `pkit analysis new` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

14. The system writes the revalidation record whole, and the developer commits it in the same change as the answers.
15. The developer runs `pkit analysis validate`. The system reports each regression the revalidation record names as open until the artefact is revalidated on a later day, and never fails on it.

**Variants:**

- **1a.** project-management's drift command starts the agent, as the fixer of the [analysis](../../glossary.md#term-analysis--analysis)'s types the [project](../../../core/glossary.md#term-project--project) granted, with nobody to ask (DEC-001 points 5 and 8). The agent takes only the [artefacts](../../../core/glossary.md#term-artefact--artefact) its brief names, at the commit the brief pins. The path goes on at step 3, and variants 4b, 8a and 9a apply.
- **2a.** A flagged artefact is not the analysis's, such as a page or a [decision record](../../../core/glossary.md#term-decision-record--decision-record). The agent says that its owner revalidates it, and leaves it (COR-050 point 6).
- **4a.** `pkit analysis propose` refuses the artefact, and proposes nothing. It refuses an explanation of a `schema_version` other than 1 (core:REQ-019). It refuses an artefact the checks did not judge too, such as one beyond a shallow clone. The agent says why.
- **4b.** In a run a command starts, the run refuses `pkit analysis propose`, or it cannot start there. The agent judges no artefact by reading alone, and gives each the result `none`, `refused` (DEC-001 point 5).
- **6a.** Every changed [anchor](../../../core/glossary.md#term-anchor--anchor) moved: its code was renamed, or carried into another file. The [system](../../../core/glossary.md#term-system--system) proposes `holds`, the anchor re-pointed, recorded `unchanged`, since an edit to the anchors alone changes no content.
- **6b.** The artefact and the code disagree, and no quote says whether the [change](../../../core/glossary.md#term-change--change) was meant, so the system finds the case ambiguous. The agent holds the artefact and those downstream of it. It asks the developer what was meant, naming what disagrees, the commit and the two readings (DEC-001 point 5). The developer's reply is a quote, its source the developer, and the path rejoins at step 4.
- **7a.** The change was meant, so the analysis was stale. The agent drafts the artefact's edit as a diff, with the one sentence on what changed in it, and the [answer](../../../core/glossary.md#term-answer--answer) is `updated`. A revised [use case](../../glossary.md#term-use-case--use-case) keeps each step's number, which `pkit analysis check-numbers` holds (DEC-001 point 3). `pkit analysis link` runs before the answer, as `UC-071` describes in its variants 3b and 3d.
- **7b.** The code regressed, and no accepted decision record decides the regressed step. Where the use case anchors an accepted decision record, `pkit analysis propose` gives no command until the agent passes `--no-box`. The agent proposes no edit. The developer reports a defect, and records `unchanged` with its reason naming the defect, as `core:UC-002` describes in its variant 5b (DEC-001 point 5).
- **7c.** The code regressed a step that an accepted decision record decides. The agent names the step and the record to `pkit analysis propose`, which then gives the answer `updated`, since the box changes the use case. First the developer reports the defect, then adds the step's box and its `shortfalls` entry, which name the record and the defect's issue. The step keeps its words, since the box stands below it (DEC-001 points 1 and 5).
- **7d.** The agent finds a gap: behaviour nothing describes, or a description with no behaviour. `pkit analysis propose` never proposes one, so the agent finds it by reading. Where a new artefact closes the gap, the agent drafts it for the developer to write with the `analysis-author` [skill](../../../core/glossary.md#term-skill--skill). The answer is then `unchanged`, naming the gap and the artefact, but the answer is `updated` where the artefact itself changes.
- **7e.** On the path of 7d, the gap is a description with no behaviour. Where an accepted decision record decides it, the step keeps its words and takes its box. Otherwise the step says what the system does, under its own number (DEC-001 point 5).
- **7f.** The developer would rather put an artefact off, such as until a fix lands. The proposal gives a deferral, `pkit friction defer`, whose reason names an open follow-up, in place of the answer. It names each deferral the artefact carries, and whether to keep it with `--keep`.
- **8a.** In a run a command starts, the agent writes each artefact's answer as fields, with its diff and its evidence, in the brief's workspace. It writes no command (project-management DEC-056 point 6).
- **9a.** In a run a command starts, the agent ends with a line for each artefact: proposed, held with its question, or none with its reason. What becomes of each proposal is then project-management's, and the use case ends.
- **11a.** An `updated` answer changes an artefact's content, so the [change check](../../../core/glossary.md#term-change-check--change-check) may flag the artefacts downstream of it. The path rejoins at step 1 for them.
- **12a.** Every artefact holds, or was updated because the change was plainly meant, so nobody decided stale against regressed. No [revalidation record](../../glossary.md#term-revalidation-record--revalidation-record) is written, since each artefact's own answer is its record (REQ-052). The path goes on at step 15.
- **14a.** The [stamp](../../../core/glossary.md#term-stamp--stamp) refuses, such as for an agent named with no `--confirmed-by`, a regression or a gap no `--gap` names, or a placeholder left in. It writes nothing, and says why (`revalidation.py`). The path rejoins at step 12.

**Postconditions:** Each flagged [artefact](../../../core/glossary.md#term-artefact--artefact) of the [analysis](../../glossary.md#term-analysis--analysis) carries an [answer](../../../core/glossary.md#term-answer--answer) the developer decided: `unchanged` with why, `updated`, or a deferral. A regression names its defect, and a step an accepted [decision record](../../../core/glossary.md#term-decision-record--decision-record) decides keeps its words, with its box.

**Minimal guarantees:**

- The agent's definition grants no tool that edits a file in place, and the agent runs no writer (REQ-050).
- The agent proposes no edit that rewrites an [artefact](../../../core/glossary.md#term-artefact--artefact) to match code that regressed (DEC-001 point 5).
- Where stale and regressed cannot be told apart, the agent proposes no [answer](../../../core/glossary.md#term-answer--answer) until a person decides (DEC-001 point 5).
- `pkit analysis propose` writes nothing, and never reads an explanation of another version as version 1 (core:REQ-005 and core:REQ-019).
- A refused [stamp](../../../core/glossary.md#term-stamp--stamp) leaves every file as it was (`stamp.py`).
