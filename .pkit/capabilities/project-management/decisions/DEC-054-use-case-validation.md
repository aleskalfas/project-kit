---
id: DEC-054
title: Batch planning and issue bodies are checked against the use cases settled on the default branch
status: proposed
date: 2026-10-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project may keep a written account of what its software must do, as use cases numbered `UC-NNN` within the project. Another capability keeps them. This capability has no part in writing them.

Batch planning slices fuzzy intent into filed issues ([project-management:DEC-029-project-manager-agent-shape]). Without the use cases, it has only the intent and the reference material to check a slicing against. A plan can then leave out a use case the work affects, or build behaviour that no use case describes, and nobody notices before review.

Issue bodies can cite use cases as they cite decisions. A use-case number is settled only when its use case reaches the default branch: when two lines of work pick the same number, the one that lands later renumbers. A number cited before then is a guess.

The two capabilities stay independent. The one that keeps the use cases works with no work tracker installed. This capability works without it, never reads its files or names it, and a project that keeps no use cases sees no change.

## Decision

**This capability accepts a data point through which the use cases settled on the default branch reach it. While the point has a contributor, batch planning walks the use cases before it slices, each planned issue names the use cases it satisfies, and body validation reports a cited use case that the point does not hold. Without a contributor, none of this happens.**

1. **The point.** As the provider of the work-tracking role, this capability accepts `<methodology>::work-tracking:use-cases` (refinement per COR-053):
   - **its value is the use cases settled on the default branch**, the branch as the backbone resolves it (COR-054) — never the working tree, and never a base named for one run;
   - **its entries are `{id, title, status}`**: the use case's `UC-NNN` id, its title, and whether it is active or withdrawn. The shape is a companion schema named after the point, at version 1 (COR-052 point 5);
   - **its policy is `union`**, so the use cases of every contributor merge by id;
   - **no default takes part**, since this capability holds no use cases of its own;
   - **its inert policy is `fallback`**: a contributor that cannot answer, because this clone has not fetched the default branch for example, leaves the point unresolved with a warning.

   A capability that keeps use cases contributes to the point by addressing the role. This capability reads the point only through the backbone's resolution of it.

2. **Three states.** How the point resolves decides what follows:
   - **No contributor.** Nothing fills the point. The planning step and the citation rule are inert, and nothing mentions use cases.
   - **A contributor, and the point resolves.** Its value is the use cases. An empty value means the project has no use cases yet.
   - **A contributor, and the point does not resolve.** A filler meant to answer could not. This capability says the use cases could not be read, with the backbone's reason, and never treats them as none.

3. **The rule.** Body validation finds every `UC-NNN` a body cites. It reports each one the resolved point does not hold, at the severity the body-format schema names for the rule, which is a warning. The finding is a report, not a refusal: filing and editing go ahead.
   - **A withdrawn use case is held.** Its id is never reused, so citing it is not a guess.
   - **What cannot be checked is said so.** When the point does not resolve, validation says the citations could not be checked and reports none of them as unknown. When the point resolves while one of its fillers was inert, an id the point does not hold may be that filler's, so it is reported as not checked rather than unknown.
   - **Every body is checked where it is validated:** by `validate-issue`, by `edit-issue` on a body edit, and by `create-issue` on the body it files.

   The body rules also forbid predicting a decision id ([project-management:DEC-010-issue-body-minimum-structure]). That rule is stated and not checked by any script, so this rule claims no parity with it. It stands on its own.

4. **The planning step.** While the point has a contributor, batch planning reads it before proposing a slicing and maps the intent onto the use cases. Each planned issue names the use cases it satisfies, and its filed body lists them in a `## Use cases` section. The section is optional, outside the minimum structure. An issue that serves no use case, such as an internal refactor, has no such section.
   - **An empty set.** The agent offers to file the authoring of the use cases as a prerequisite Task. The planned issues depend on that Task and state the goals they serve as text, since no id exists yet to cite. The user may instead plan without use cases.
   - **That choice is recorded once.** The answer is written to this capability's project configuration, as `batch_plan.no_use_cases`. A later plan reads it and does not ask again while the set stays empty. Removing the setting makes the agent ask again.
   - **A gap.** When the set is not empty but the intent involves behaviour no use case describes, the agent raises it on that plan with the same offer. The approval gate names the behaviour nothing describes.
   - **An unresolved point** is reported with the reason and its fix, and the plan may go ahead without use cases.
   - **The project-manager does not write use cases.** Describing what the software must do is analysis, not project management.

## Rationale

**Why a data point.** Components exchange knowledge through slots without depending on each other (COR-052). Reading another capability's files would bind this capability to that capability's name, its layout and its rules for where documentation lives. Through the point, the keeper of the use cases decides how they are found, and any capability that keeps use cases can contribute with no change here.

**Why the default branch.** A use-case number is settled there: the first use case to land keeps it. The working tree, or a base named for one run, would accept a number that another line of work may still take.

**Why `fallback`.** COR-052 asks a slot that enforces to fail closed. This point enforces nothing: its consumer reports and never refuses. Under `fail`, every clone that has not fetched the default branch would see an error from validation for a check that only advises. The consumer keeps the guarantee that failing closed exists for: it never reads an unresolved point as an empty set, and while a filler is inert it reports an id the point does not hold as not checked, never as unknown.

**Why a report, not a refusal.** The finding names a likely guess. A clone's view of the default branch can lag behind the remote, and a use case may land minutes later. Blocking a filing on that would weigh more than the rule warrants. The planning step keeps guessed numbers out of the plans the agent writes, and the report catches the rest.

**Why record the empty-set choice.** A project with no use cases would otherwise be asked on every plan. In the project configuration the answer is a reviewed, visible setting that holds across sessions and clones, and removing it undoes it.

**Why offer authoring instead of doing it.** Use cases describe the product and outlive the plan, and writing them has its own discipline for keeping them true. This capability's part is to notice the gap and route the work.

### Alternatives considered

- **Read the use cases from the files of the capability that keeps them.** Rejected. It couples this capability to another's name and layout.
- **Activate the rule when a named capability is installed.** Rejected for the same reason. Whether the point has a contributor needs no name.
- **Inert policy `fail`.** Rejected. A clone that has not fetched the default branch would fail validation for an advisory check.
- **Require a `## Use cases` section on every issue while the point has a contributor.** Rejected. Chores and refactors serve no use case, and a mandatory "none" line would be ceremony.
- **Refuse an unknown citation.** Rejected. It would block filings on a view of the default branch that may be stale.

## Implications

- **This capability's package** accepts the point and ships its companion schema. `pkit capabilities show` names what fills it.
- **The body-format schema** carries the citation rule and lists `## Use cases` among the optional sections. `validate-issue`, `edit-issue` and `create-issue` check citations.
- **The project configuration** gains `batch_plan.no_use_cases`, the recorded answer for a project with no use cases yet.
- **The batch-plan sub-procedure** gains the use-case step ahead of slicing, and the project-manager's storyboard covers a project with no use cases yet.
- **[project-management:DEC-010-issue-body-minimum-structure]** and **[project-management:DEC-029-project-manager-agent-shape]** point at this record where they are refined.
- **Journeys, actors and glossary terms** are not cited or checked. Checking them needs its own decision when a need arrives.
