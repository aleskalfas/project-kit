---
id: DEC-054
title: Use cases reach batch planning and body validation through a data point
status: accepted
date: 2026-10-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** this capability defines one data point, *the use cases settled on the default branch*, and lets whatever keeps a project's use cases fill it. When the point holds a set, batch planning walks the use cases before it slices the work and shows at its one approval gate which use cases the plan serves and what it misses. An issue body may also list the use cases it serves, and validation warns when one of them is not in the set. When nothing fills the point, none of this happens and nothing mentions use cases. When the point cannot be read — in a clone that has not fetched the default branch, say — validation says the citations were not checked, planning says the use cases could not be read, and neither reports a use case as unknown on that ground. The rule is a warning. It refuses nothing, and it checks only that a cited id exists.

## Context

A project may keep a written account of what its software must do, as use cases, each with a stable id. Another capability may keep them, or the project itself — the *keeper*. This capability has no part in writing them.

Batch planning slices fuzzy intent into filed issues ([project-management:DEC-029-project-manager-agent-shape]). Without the use cases, the only things it can check a slicing against are the intent and the reference material. A plan can then leave out a use case the work affects, or build behaviour no use case describes, and nobody notices before review.

Issue bodies can cite use cases as they cite decisions. An issue lives in the tracker, on no branch, so the use cases that every reader of it shares are those on the default branch. A use-case id is settled once its use case reaches the default branch, the project's settled state (COR-054). Before then, another line of work may take the same id, so citing it is a guess.

The capabilities stay independent. Whatever keeps the use cases works with no work tracker installed. This capability works without it, never reads its files or names it, and a project that keeps no use cases sees no change.

## Decision

**This capability accepts a data point for the use cases settled on the default branch and reads it through the backbone's resolution. What it does depends on how that resolution ended. When the point is off, nothing happens. When it cannot be read, the check says so and judges nothing. When it holds a set, batch planning walks it and body validation warns of a cited use case the set does not hold.**

1. **The point.** As the provider of the work-tracking role, this capability accepts `<methodology>::work-tracking:use-cases` (COR-053). It is a data point whose value is the use cases settled on the default branch (COR-052; COR-054).
   - **Its entries are `{id, title, status, path?}`**, the shape of a companion schema named after the point, at version 1 (COR-052 point 5).
     - `id` follows the point's own pattern: at version 1, `UC-` and three or more digits. Body validation derives its citation matcher from that pattern, so the two never disagree.
     - `status` is the point's two-value vocabulary, `active` and `withdrawn`. A filler maps its own lifecycle onto it. Planning reads it and walks active use cases only; body validation does not read it.
     - `path`, optional, is the repository-relative path of the document that describes the use case.
   - **Its combination is `single`.** One keeper answers, and a project filler replaces the answer whole.
   - **It has no default.** This capability holds no use cases of its own.
   - **Its inert policy is `fallback`**: its consumers only report, and a consumer that only reports may declare `fallback` (COR-052 point 6). The policy holds on three conditions, and they are part of this decision:
     - nothing refuses on the point, and nothing fails on it;
     - no finding is drawn from an id the point lacks unless the point resolved with no inert filler (point 3);
     - raising the rule of point 4 above a warning reopens the policy.

2. **The filler's contract.** The point's description states it, as what the point means and what one may rely on (COR-053 point 3), so any keeper can meet it without this capability knowing the keeper:
   - the value holds **every use case that ever settled**, withdrawn ones included;
   - **an id is never reused**: once settled, it names the same use case for good;
   - the answer is **complete or none**: a filler that cannot read a use case gives no answer, never a shorter list;
   - a capability's filler **declares that it reads settled state**, so no base named for a run reaches it, and the backbone does not start it where that branch cannot be read (COR-052 point 6).

   A project filler is the project's own statement of its use cases. It is held to the point's shape and taken as given.

   This record names no keeper, none of a keeper's files and nothing else a keeper keeps.

3. **The states the rule distinguishes.** This capability reads the point through the backbone's document for one point (`pkit connections resolve --json`). It decides on the document's `outcome` and on its fillers' `state`. It never decides on the sentence in `why`, though it may show that sentence to people.
   - **Off**: `undefined` or `unfilled`. Nothing defines the point, or nothing fills it. There is no finding, and nothing mentions use cases.
   - **Could not check**: `no-answer`, `inert-fail`, `collision`, `selection-needed`, `selection-unmatched`, `definer-defect`, or a value this version does not know. There is no set to judge against. The same holds where the command returns no document, or one whose version this capability does not know.
     - One notice says the citations were not checked, and why. It is a notice about the check, not a finding against the body, and no citation is reported as unknown. It is reported at warning severity.
     - This point's own declaration cannot produce two of these values: `collision` under `single`, and `inert-fail` under `fallback`. They are read the same way all the same, so the consumer does not depend on the declaration staying as it is.
   - **Partly checked**: `resolved`, with a filler whose state is `inert`. The point answered without a filler that was meant to answer.
     - An id the point holds passes. The ids it lacks are named as not checked, never as unknown, in one notice that lists them, at warning severity.
     - Under `single` with no default, this state arises only where more than one filler is declared and one that was asked gives no answer while another answers.
   - **Empty** and **has entries**: `resolved`, with no inert filler. The value is the whole set, and the rule and the planning step apply to it.

4. **The rule.** Body validation reads citations from a `## Use cases` section only. The section is optional on Feature and Task bodies and lies outside the minimum structure ([project-management:DEC-010-issue-body-minimum-structure]). On EPIC, Umbrella and Milestone bodies the rule reads nothing; a `## Use cases` heading there is ordinary content, neither checked nor reported. A citation is an id in that section that matches the point's pattern.
   - **A cited id the resolved point does not hold is reported as a warning** ([project-management:DEC-014-validation-severity-model]).
     - The severity is the rule's token in the body-format schema; this record fixes it at `warning`, and no project setting changes it.
     - The warning is a report, never a refusal, wherever a body is validated: on reading, filing or editing an issue. No verb refuses or fails on it.
     - Unlike the body rules that refuse, it never stops a filing or an edit.
   - **The check is of existence only, and the rule says so wherever it is stated.** An id that exists but names a different use case from the one the author meant passes.
   - **A citation of a withdrawn use case passes silently.**
   - **The point is resolved only for a body that cites a use case.** A body with no citation starts no filler.
   - **The finding says what it was read against.** Where the answering filler read the default branch, the finding names the commit it read and suggests fetching the default branch. Where the project's own filler answered, the finding names that file.

5. **The planning step.** Batch planning reads the point before it proposes a slicing. The step is active only when the point is not off.
   - **With entries**, the agent walks the active use cases against the intent before it slices.
     - Each proposed Feature and Task names the use cases it satisfies in its `## Use cases` section. An issue that serves none, such as an internal refactor, has no such section.
     - The plan shown at the single approval gate ([project-management:DEC-029-project-manager-agent-shape]) surfaces both kinds of gap. One is a use case the plan leaves out: the intent touches it, but no planned issue names it. The other is behaviour the plan builds that no use case describes.
     - Where entries carry `path`, the agent may read those documents. Otherwise it maps the intent from titles alone, and the plan says so.
   - **Partly checked:** the agent walks the entries the point holds. The plan says that the set may be incomplete, and which filler did not answer.
     - Behaviour that no held use case describes is shown as a possible gap, since the missing filler may describe it.
     - An empty value read in this state does not lead to the prerequisite Task below.
   - **With an empty set**, the plan at the gate includes a prerequisite Task to author the use cases. It is there by default, and the user revises it away to plan without use cases.
     - The planned issues depend on the Task. They state the goals they serve as text and cite no use case, since none has settled.
     - One of the Task's acceptance criteria is that the dependent issues name their use cases.
     - No answer is saved to configuration. When the user revises the Task away, the plan's topmost new issue says so in prose — or, where the plan files only under an existing issue, each filed issue does. The next plan over an empty set includes the Task again.
   - **Could not check:** the plan says the use cases could not be read, and why, and proceeds without the step.
   - **The agent does not write use cases.** It plans their authoring as work. Describing what the software must do is not project management.

## Rationale

**Why a data point.** Components exchange knowledge through data points without depending on each other (COR-052; COR-053). Reading another capability's files would bind this capability to that capability's name, its layout and its rules for where documentation lives. The rule would also be wrong for any project whose use cases another keeper serves. Through the point, the keeper decides how its use cases are found, and any keeper, or the project itself, answers without a change here.

**Why `single`.** A project keeps one account of what its software must do. Merging two keepers' sets by id would merge two numbering schemes that never agreed to share one, and would make a collision a state every consumer has to handle. With one keeper answering, the project's own filler replaces the answer whole, which is the override a project needs when its keeper is wrong or missing. If two capabilities contribute, the project selects one (COR-052 point 4).

**Why `fallback`, and why it has conditions.** Failing closed exists so that a gate never passes on the entries that happened to survive (COR-052 point 6). Nothing passes, refuses or fails on this point. The rule only warns, and planning reads the point to advise.

Under `fail`, the backbone's validation would report an error in every clone or pipeline job that has not fetched the default branch. It would do the same before the default branch is first pushed. All of that would be for a check that only warns.

The consumer keeps, by itself, the guarantee that failing closed exists for. It never reads an unresolved point as an empty set. It draws no finding from an id the point lacks unless every filler meant to answer did.

The sibling point under this role, the documentation obligations, feeds the merge gate and declares `fail` for that reason ([project-management:DEC-053-doc-check-slot]). This point would need the same as soon as its rule refused anything, which is why raising the severity reopens the policy.

**Why existence only.** The value carries ids, titles and a status. Whether a body's prose fits the use case it cites is a judgment no matcher makes well, and a rule that guessed would warn wrongly on every paraphrase. Existence catches the failure that matters: an id guessed before its use case settled. Saying that the check stops there keeps a pass from being read as more than it is.

**Why a withdrawn use case passes.** Ids are never reused, so a citation of a withdrawn use case is a true reference, not a guess. Validation runs again on old issues. Warning on every issue that served a use case later withdrawn would turn the rule into noise. Planning maps onto active use cases only.

**Why a report, not a refusal.** The finding names a likely guess, read against this clone's view of the default branch, which may lag the remote. A use case may land minutes later. Blocking a filing on that weighs more than the rule warrants. The planning step keeps guessed ids out of the plans the agent writes, and the report catches the rest.

**Why no saved answer.** A setting that silenced the offer would outlive its reason: once use cases exist, the setting is stale, and while it stands it hides the prerequisite from every later plan. A default the user revises away at the gate costs one edit per plan. It keeps the choice with the plan it concerns, and leaves a trace where the work is, in the plan's own issues, instead of in configuration nobody reviews with the plan.

**Why settled state is the reference for issue bodies.** An issue is on no branch, so the default branch is the only state every reader of it shares, on any branch or none. A citation checked against a working tree or a feature branch would pass for an id that another line of work may take before it lands.

The cost falls on use cases authored on a branch. Until they settle, the issues that depend on them cite none, and the prerequisite Task's acceptance criterion carries the citations forward to when the use cases land.

### Alternatives considered

- **Read the use cases from the files of whatever keeps them.** Rejected: it couples this capability to another's name and layout.
- **Activate the rule when a named capability is installed.** Rejected for the same reason: whether the point is off needs no name.
- **Combination `union`.** Rejected; see "Why `single`".
- **Inert policy `fail`.** Rejected: every clone that has not fetched the default branch would get an error for a check that only warns.
- **Refuse an unknown citation.** Rejected: it would block filings on a view of the default branch that may be stale.
- **Find use-case ids anywhere in a body.** Rejected: ids in prose, quotations and history would be checked as if they were citations. A section states what the issue serves.
- **Check that a citation's meaning fits.** Rejected; see "Why existence only".
- **Save the empty-set answer in configuration.** Rejected; see "Why no saved answer".
- **Require a `## Use cases` section on every issue while the point holds a set.** Rejected: chores and refactors serve no use case, and a mandatory "none" line is ceremony.
- **Check against the use cases on the branch at hand.** Rejected: an issue is on no branch; see "Why settled state is the reference for issue bodies".

## Implications

- **This capability's package metadata** accepts the point, with the filler's contract as its description, and ships the companion schema named after it. The status report shows what fills the point.
- **The body-format schema** lists `## Use cases` as an optional section of Feature and Task bodies, and carries the rule at warning severity. Templates do not carry it.
- **The pm skill** carries the rule in its body-validation procedure and the planning step in its batch-planning procedure.
- **The project-manager's storyboard** gains scenes for each state of point 3 in which planning acts: a walk over a non-empty set, a gap, a partly checked set, a point that could not be read, and an empty set.
- **No configuration key is added.**
- **A keeper that contributes records, in its own decision,** its contribution and the obligations of point 2 it takes on. Among them, its filler reads settled state and gives no answer when a reading it relies on fails.
- **[project-management:DEC-010-issue-body-minimum-structure]** carries two refinement notes, both pointing here. Among the universal body rules, the note says that a use case cited in a `## Use cases` section and not held by the use-case point is reported as a warning: a report that checks existence only. Among the optional sections, it says that Feature and Task bodies may carry `## Use cases`, outside the floor.
- **[project-management:DEC-029-project-manager-agent-shape]** carries the refinement at two steps: the walk and the approval gate. The batch-planning sub-procedure walks the use cases between reading the intent and proposing a slicing, while the use-case point is not off. The single approval gate shows the mapping, both kinds of gap, and the prerequisite Task over an empty set.
