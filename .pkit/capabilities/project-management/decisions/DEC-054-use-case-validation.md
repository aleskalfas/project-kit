---
id: DEC-054
title: Batch planning is checked against the project's use cases
status: accepted
date: 2026-09-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The software-analysis capability keeps an account of what a project's software must do. Part of it is a set of use cases, each numbered `UC-NNN` within the project and kept under the internal documentation root ([software-analysis:DEC-001-software-analysis-discipline]).

Batch planning slices fuzzy intent into filed issues ([project-management:DEC-029-project-manager-agent-shape]). Until now it had nothing to check a slicing against but the intent and the reference material. A plan could leave out a use case the work affects, or build behaviour that no use case describes, and nobody would notice before review.

Issue bodies can cite use cases as they cite decisions, and the same failure applies. A decision id cited before the decision exists is a guess, and the body rules already forbid predicting one ([project-management:DEC-010-issue-body-minimum-structure]). A use-case number is a guess for the same reason. It is settled only when the use case reaches the default branch: when two lines of work pick the same number, the later one renumbers.

The two capabilities must stay independent. Software-analysis works with no work tracker installed, and a project that uses this capability without software-analysis must see no change.

## Decision

**When the software-analysis capability is installed, batch planning reads the project's use cases before it slices the work, and each planned issue names the use cases it satisfies. Body validation reports any cited use case that does not exist on the default branch, as it reports a predicted decision id.**

1. **Active only when installed.** The planning step and the validation rule apply only when software-analysis is registered as installed in the project. That is the same test this capability applies to any other capability that contributes to it. Without software-analysis, planning runs as before, and validation does not look for use-case citations.

2. **The use cases come before the slicing.** After reading the intent and the reference material, batch planning reads the use cases the intent affects.
   - **A gap is raised before slicing.** If the project has no use cases yet, or the intent involves behaviour no use case describes, the agent says so and offers to have the missing use cases authored first, through software-analysis's own authoring, before it proposes a slicing.
   - **The user may decline.** Planning then goes ahead, and the plan says which issues cite no use case.
   - **The project-manager does not write use cases.** Describing what the software must do is analysis, not project management.

3. **Each planned issue names the use cases it satisfies.** The slicing shows them for each issue. The filed body lists them in a `## Use cases` section, one use case per line. An issue that serves no use case, such as an internal refactor, says so in the plan and has no such section. The section is optional, so the minimum body structure does not change.

4. **Cited use cases must exist on the default branch.** Body validation finds every use-case id the body cites, in the `UC-NNN` form, anywhere in the body. It reports each one that is not a use case on the default branch, at the severity of a predicted decision id: a warning.
   - **A withdrawn use case still exists.** Its id is never reused, so citing it is not a guess.
   - **An unreadable default branch is said so.** When validation cannot read the default branch, it says the citations were not checked. It does not report them as unknown, and it does not pass them silently.

5. **The default branch is the reference, not the working tree.** A use case written on a branch that has not landed may still be renumbered, so its number cannot be cited yet. Where use cases live, and how a file is recognised as one, follow software-analysis's layout, read as it stands on the default branch.

## Rationale

**Why before slicing.** A slicing is cheapest to correct before anything is filed. Reading the use cases first shows the gaps while the plan is still being shaped: behaviour that nothing describes, and a use case the plan misses.

**Why offer authoring instead of doing it.** Use cases describe the product and outlive the plan. Writing them is software-analysis's work, and it has its own discipline for keeping them true. The project-manager's part is to notice the gap and send it to the right place.

**Why a warning, as for a predicted decision id.** Both citations name something that is not yet settled, so one severity serves both and keeps the body rules consistent. A script's view of the default branch can lag behind the remote, and a use case may land in parallel minutes later. Blocking a filing on that would weigh more than the rule warrants. The planning step keeps guessed numbers out of the plans the agent writes, and the warning catches the rest.

**Why the default branch.** Software-analysis settles a number on the default branch, where the first use case to land keeps it. Any other number is a prediction.

### Alternatives considered

- **Require a `## Use cases` section on every issue when software-analysis is installed.** Rejected. Many chores and refactors serve no use case, and a mandatory "none" line would be ceremony. The citation rule already catches the harmful case.
- **Refuse an unknown citation outright.** Rejected. It would part from the decision-id rule, and it would block filings on a view of the default branch that may be stale.
- **Check citations against the working tree.** Rejected. It would accept a number that a parallel change may still take.
- **Make software-analysis a dependency of this capability.** Rejected. Each capability must work alone.

## Implications

- **The batch-plan sub-procedure** gains the use-case step ahead of slicing, and the project-manager's storyboard covers a project with no use cases yet.
- **The body-format schema** gains the citation rule next to the predicted-decision-id rule, and the validate and edit commands check it.
- **[project-management:DEC-010-issue-body-minimum-structure]** and **[project-management:DEC-029-project-manager-agent-shape]** point at this record where they are refined.
- **The capability README** describes the step, the rule, and how use cases are read from the default branch.
- **Journeys, actors and glossary terms** are not cited or checked. Checking them needs its own decision when a real need arrives.
