---
consumers:
  - kind: agent
    name: project-manager
    namespace: project-management
---

# project-manager: batch-planning scripted scenarios

## Framing

This storyboard covers the **autonomous batch-planning flow** the `project-manager` agent runs when a user supplies fuzzy intent + reference material and wants the work sliced into issues filed correctly. The flow is one variation of the agent's PM-direction mode per [project-management:DEC-029-project-manager-agent-shape]; the user does not name it explicitly, the agent infers it from the request shape.

The flow operates on:

- **Input state**: the user's fuzzy intent expressed in natural language; reference artifacts the user points the agent at (scratchpad notes under `.pkit/scratchpad/`, handoff documents, related issues, decision records); the capability's eight schemas at runtime (issue-types, workflow, body-format, titles, classification, git-conventions, validation-severity, time-containers); the adopter's `project/config.yaml` and `project/workstreams.yaml`; and, while the use-case point is not off, the use cases settled on the default branch (`UC-NNN`), read through `pkit connections resolve pkit::work-tracking:use-cases --json`, per [project-management:DEC-054-use-case-validation]; over an empty set, the answer kept in this checkout when the Task to author them was declined, read through `pkit pm decline-use-case-task --show --json`.
- **Mutations**: GitHub issue creation via `create-issue.py`; body edits via `edit-issue.py`; milestone attachment via `gh issue edit`; optional state transitions via `move-issue.py`; audit comments per [project-management:DEC-014-validation-severity-model]; over an empty set, the kept answer to the use-case Task, via `decline-use-case-task`, on approval only.
- **The single approval gate**: the moment the agent shows the proposed slicing and waits for the user's approval / revision / refusal. No `gh` mutation happens before this gate.

User-facing entry points: invoking the `project-manager` agent with a fuzzy multi-issue ask. No CLI command; no flag; the agent infers batch-planning from the request shape during step 3 of its `How you work` procedure.

## Tone

Behavioural norms applied across every scenario:

- **One thought per turn.** Never dump the whole slicing in one message; stage it (intent restatement → proposed slicing → details on request).
- **Turns are 1–4 sentences.** Italics for behind-the-scenes narration to the user ("*reading the scratchpad…*", "*invoking critic against the slicing…*").
- **Confirmation prompts are short and direct.** "Approve, revise, or cancel?" — not paragraphs.
- **When the agent acts on a user request, it confirms what it did in one sentence and offers the next step.** "Filed #185 with parent ref to #182. Continuing with F4?"
- **Reviewer findings are surfaced verbatim, not paraphrased.** When `critic` or `architect` returns findings, the agent shows the findings (or a tight summary) and tags which finding(s) it incorporated into the revised slicing.

## Invocation pattern

Every "invoke `critic`" / "invoke `architect`" turn in the scenarios below assumes the `Agent` tool is available to you. It is when you are the **parent session** (booted via `claude --agent project-manager` or via the default-agent toggle the capability ships, per [DEC-030](../../decisions/DEC-030-capability-contributed-adapter-overlays.md)), and it usually is when you were spawned as a subagent too: the harness lets subagents nest up to a configured depth and withholds `Agent` only at that limit. If the tool is absent, replace each "invoke X" step with "recommend X to the outer parent session" and skip the dispatch turn. See DEC-029's "Invocation pattern" paragraph.

## Scenario 1: Happy path

### Trigger

User invokes `project-manager` with fuzzy intent + a pointer to a reference document (scratchpad, handoff, related issue, or decision record).

### Preconditions

- The reference document exists at the path the user names (or under a directory pattern the agent can resolve).
- The user has filing authority for the issue types implied by the slicing per [project-management:DEC-008-pm-and-implementer-roles].
- A milestone is either specified or default-resolvable from the capability's milestone config; if neither, the agent prompts before the approval gate.
- The use-case point is off: nothing defines it, or nothing fills it. The walk step does nothing and the dialogue never mentions use cases. Scenarios 5–11 cover every other state.

### Walkthrough

> **User:** I want to plan the implementation work for the new project-manager agent — start from the scratchpad note tracking that design.
>
> **project-manager:** *Reading the scratchpad...* You're asking me to slice the COR-026 implementation arc into filed issues, picking up from where the scratchpad's crystallisation plan lands. The natural shape is one EPIC with five Features (F1–F5). I'll propose the slicing — give me a moment to invoke `critic` since this is a multi-issue arc.
>
> **project-manager:** *Invoking critic on the proposed slicing…* Plan: EPIC "Reclassify pm-coordinator agents per COR-026" with five child Features — capability DEC, storyboard, sub-procedure+body, retirements+migrations, doc audits. Workstream `agents`, Milestone 1, Medium priority on each. Critic flagged one concern: F3 and F4 are tightly coupled (intermediate state has a broken agent surface). I've noted that in the EPIC's Approach section — F3 and F4 may merge during implementation. Show me the full plan?
>
> **User:** Yes, show me.
>
> **project-manager:** *Renders the slicing table with parent-refs, titles, classifications, dependency chain.* Approve, revise, or cancel?
>
> **User:** Approve.
>
> **project-manager:** Filing E1 first (parent-ref target for the rest). *Calls create-issue.py for EPIC*. Filed #182. Filing F1–F5 in sequence... *Calls create-issue.py five times with --parent 182*. All filed: #183 (F1), #184 (F2), #185 (F3), #186 (F4), #187 (F5). Milestone attached on each. Anything else?

### Behind the scenes

- Read the reference document (scratchpad / handoff / issue) via the Read tool.
- Read the use-case point (`pkit connections resolve pkit::work-tracking:use-cases --json`). Its `outcome` here is `undefined` or `unfilled`, so the step ends there: no Use cases column, no `## Use cases` sections, no mention of use cases. Any other outcome follows Scenarios 5–11.
- Parse out the implied work units. Apply [project-management:DEC-004-six-level-hierarchy]'s typing rules (Umbrella / EPIC / Feature / Task / Milestone) to choose ticket types.
- Apply [project-management:DEC-012-classification-axes]'s rules to assign workstream / priority / kind labels per ticket.
- Resolve parent-refs per [project-management:DEC-005-linking-and-containment].
- For multi-issue arcs (≥3 issues): invoke `critic` agent with the proposed slicing + the reference document. Capture findings. Revise the slicing or annotate the EPIC body with unresolved concerns.
- For cross-component work (≥3 components touched): additionally invoke `architect` agent. Capture and surface findings.
- Render the plan as a single message: slicing table + dependency chain + reviewer findings summary.
- **Pause for approval. No `gh` mutation before this point.**
- On approval: call `create-issue.py` for each ticket in dependency order. After each `[ok] created` response, parse the issue number for use in subsequent `--parent` references.
- After each issue creation, immediately call `edit-issue.py --body-file` with the real body content (the script's auto-generated template is a placeholder; the agent supplies the actual Outcome / What / Acceptance criteria content).
- Attach milestones via `gh issue edit` with the milestone title (the create-issue.py `--milestone NUM` path is broken pending #177 fix).
- Surface the final state: issue numbers, links, completion confirmation.

## Scenario 2: Ambiguous intent

### Trigger

User invokes `project-manager` with intent that's missing one or more pieces the agent needs before it can propose a slicing — typically: no reference material, scope unclear, or the named reference is too broad to imply a clear set of work units.

### Preconditions

- The user's request shape signals batch-planning intent (verbs like "plan", "scope", "slice"; multi-issue outcomes mentioned) but the inputs are incomplete.

### Walkthrough

> **User:** Can you plan out the work for the hooks engine?
>
> **project-manager:** Before I propose a slicing — two clarifying questions. (1) Which decision record motivates this work? I see DEC-024 covers a lifecycle-hooks engine; is that the one, or do you mean something else? (2) Are you scoping the v1 hooks engine (the four hook kinds DEC-024 names — set-board-field, post-comment, assign-milestone, custom-script) or just one of them?
>
> **User:** DEC-024, and just the four hook kinds for v1.
>
> **project-manager:** Got it. *Reading DEC-024…* Proposing a slicing in a moment.
>
> *(Continues with Scenario 1's happy-path flow from the slicing-proposal step.)*

### Behind the scenes

- Recognise the missing inputs before proposing any slicing.
- Ask **at most two** clarifying questions in one message — not a sequence of one-question-per-turn.
- If the user supplies the missing inputs, continue with Scenario 1's flow.
- If the user cannot supply the missing inputs ("I'm not sure"), offer to either (a) explore the codebase / decision corpus for context, or (b) defer the planning to a later session. Do not guess.
- No `gh` mutation in this scenario unless the clarification leads into Scenario 1's happy path.

## Scenario 3: Plan rejection

### Trigger

User reviews the proposed slicing at the single approval gate and rejects it — either as too coarse, too fine, or fundamentally mis-shaped for the work.

### Preconditions

- Scenario 1's flow has reached the approval gate.
- User responds with rejection feedback (not approval, not "cancel").

### Walkthrough

> **project-manager:** *Renders the slicing table.* Approve, revise, or cancel?
>
> **User:** F3 and F4 are too coupled — the broken intermediate state thing critic flagged. Merge them into one Feature.
>
> **project-manager:** Merging F3 and F4 into one Feature ("project-manager body rewrite + sub-procedure + retirements + migrations"). The merged Feature is one larger PR but lands a coherent change-set. Updated plan: E1 with four Features — F1 (DEC), F2 (storyboard), F3-merged, F5 (doc audits). Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Continues with Scenario 1's filing flow against the revised slicing.)*

### Behind the scenes

- Recognise rejection feedback as a signal to revise, not to abort.
- Parse the user's feedback for the specific change requested (merge tickets, split a ticket, change parent-refs, change classifications, drop a ticket, add a ticket).
- Apply the revision; re-render the slicing table.
- If the revision is non-trivial (changes the cross-component scope or introduces a new abstraction), re-invoke `critic` and/or `architect` against the revised slicing before showing it. Reviewers may have new findings.
- Present the revised plan with a brief summary of what changed.
- Loop: the user may revise multiple times before approving. Each revision pass is a fresh approval-gate cycle.
- If the user changes their mind and cancels: respond with "Cancelled. Nothing filed." and offer to re-engage when they're ready.
- No `gh` mutation in any revision cycle. Only the final approval triggers filing.

## Scenario 4: Mid-execution validation failure

### Trigger

After approval, during the filing pass, one of the planned issues' bodies fails methodology validation (the `edit-issue.py` script returns a hard-reject finding per [project-management:DEC-014-validation-severity-model]).

### Preconditions

- The approval gate has fired; the agent is in the filing loop.
- One of the planned bodies violates a validation rule (e.g., missing required section, forbidden file:line reference, parent-ref format error).

### Walkthrough

> **project-manager:** Filing F3 with parent-ref to #182. *Calls edit-issue.py with body…* Hard-reject: the body carries a `path:line` reference pattern in the Acceptance criteria section. [project-management:DEC-010-issue-body-minimum-structure] forbids that pattern (line numbers go stale). Want me to drop the line-number, leaving just the file path, and retry? Or refuse this Feature and continue with F4–F5 manually?
>
> **User:** Drop the line-number, retry.
>
> **project-manager:** *Retrying edit-issue.py with the corrected body…* Validation clean. Filed #185 body content. Continuing with F4.

### Behind the scenes

- Recognise the hard-reject response from `edit-issue.py` (exit code 1 with structured stderr).
- Surface the validation rule that fired verbatim — name the DEC and the schema entry — so the user understands what was rejected and why.
- Propose at least one specific corrective action (a body edit, a classification change, a parent-ref adjustment). Don't ask "what do you want?" without offering an option.
- If the user authorises the correction: apply it, re-invoke the script, continue the filing loop.
- If the user authorises a `--force` bypass (only valid for bypassable-with-audit severity, not hard-reject): refuse — hard-reject has no bypass form per [project-management:DEC-014-validation-severity-model].
- If the user chooses to skip the failing issue and continue: log the skip in the agent's surfaced result so the user remembers what wasn't filed.
- If multiple issues fail in sequence: aggregate the corrections where possible; surface the aggregate plan to the user before re-trying.
- After the filing loop terminates (success or partial-success), surface the final result: filed issues, skipped issues, total mutations.

## Scenario 5: Walking the use cases

### Trigger

Batch planning reads the use-case point and it holds entries, every filler that was meant to answer having answered.

### Preconditions

- The request has been recognised as batch planning, and the intent and reference material are clear (otherwise Scenario 2 comes first).
- `pkit connections resolve pkit::work-tracking:use-cases --json` gives `outcome: resolved`, no filler whose `state` is `inert`, and a `value` with entries.
- An active use case describes every behaviour the intent involves, and the plan leaves out none the intent touches (otherwise Scenario 6).

### Walkthrough

> **User:** Plan the export feature from the handoff note in the scratchpad.
>
> **project-manager:** *Reading the handoff note…* *Reading the use cases settled on the default branch…* Seven use cases, six of them active. The intent touches three: UC-003 "Export a report", UC-004 "Schedule an export" and UC-006 "Share an export". *Reading their documents…* I'll slice against those.
>
> **project-manager:** *Invoking critic on the proposed slicing…* Plan: one Feature, "Report export", with four Tasks. Three serve a use case each — UC-003, UC-004, UC-006. The fourth, a refactor of the report model, serves none. Every use case the intent touches is named by an issue, and nothing in the plan lacks a use case. Show me the full plan?
>
> **User:** Yes.
>
> **project-manager:** *Renders the slicing table, with its Use cases column.* Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Continues with Scenario 1's filing flow. Each Task that serves a use case carries a `## Use cases` section — `- UC-003 — Export a report`; the refactor has none.)*

### Behind the scenes

- Read the point: `pkit connections resolve pkit::work-tracking:use-cases --json`. Decide on the document's `outcome` and each filler's `state`, never on `why`.
- Walk the entries whose `status` is `active` against the intent, before any slicing. A withdrawn use case is history: no planned issue serves it.
- Where entries carry `path`, read those documents. Where they carry none, map the intent from titles alone and say so in the plan.
- In the slicing, name the use cases each Feature and Task serves, citing only ids the point holds: `none` for one that serves none, `—` for an EPIC, Umbrella or Milestone, whose bodies do not carry the section.
- At the approval gate, show the mapping and both kinds of gap. Here there is neither, and the plan says so in a sentence.
- On filing, each Feature and Task that serves a use case lists it under `## Use cases`, one per line. An issue that serves none has no such section.
- `edit-issue` reads each such section against the point and reports at warning severity, never refusing the edit. A use-case citation warning on a body the plan wrote is corrected before moving on — fix or drop the id — rather than left filed.

## Scenario 6: A gap between the plan and the use cases

### Trigger

The walk finds a gap of either kind: a use case the intent touches that no planned issue names, or behaviour the plan builds that no use case describes.

### Preconditions

- As Scenario 5: the point holds entries, and every filler that was meant to answer did.

### Walkthrough

> **project-manager:** *Reading the use cases settled on the default branch…* The intent touches UC-003 "Export a report" and UC-004 "Schedule an export". The handoff also asks for export to a shared folder, and no use case describes that.
>
> **project-manager:** Plan: one Feature, "Report export", with three Tasks. Two gaps for you to decide on. **Left out:** UC-004 "Schedule an export" — the intent touches it, and no planned issue names it. **Not described:** T3, export to a shared folder, builds behaviour no use case describes. Approve, revise, or cancel?
>
> **User:** Add a Task for scheduling. Keep T3 — I'll have its use case written.
>
> **project-manager:** Added T4 "Schedule an export", serving UC-004. T3 stays, with no `## Use cases` section; its body says what it builds in text. One gap is left, the one you kept: T3 has no use case. Approve, revise, or cancel?

### Behind the scenes

- Both kinds of gap are shown at the single approval gate, with the plan. Neither is raised earlier as a question of its own.
- **Left out:** the intent touches a use case, and no planned issue names it. Name the use case by id and title.
- **Not described:** the plan builds behaviour no use case describes. Name the issue and the behaviour.
- Neither blocks. The user approves the plan as it stands, revises it, or cancels.
- An issue that builds undescribed behaviour cites no use case, and no id is suggested for one that has not settled. The issue states what it builds as text.
- The project-manager does not write the missing use case. If the user wants its authoring planned, that is a Task like any other.
- A revision re-renders the plan with the gaps that remain (Scenario 3's loop).

## Scenario 7: A set that may be incomplete

### Trigger

The point resolved, and a filler that was meant to answer did not: the document's `outcome` is `resolved`, and one of its fillers has `state: inert`.

### Preconditions

- More than one filler is declared for the point — the project's own filler file beside a capability's, say — and one gave no answer while another answered.

### Walkthrough

> **project-manager:** *Reading the use cases settled on the default branch…* The point answered, but not in full: the project's filler file, `docs/pkit/fillers/pkit/work-tracking/use-cases.yaml`, gave no answer — one of its entries has a status the point does not know. I'll walk the five use cases the other filler gave. The set may be incomplete.
>
> **project-manager:** Plan: one Feature with three Tasks, serving UC-003 and UC-004. **Possible gap:** T3, export to a shared folder, matches none of the five use cases I could read; the filler that did not answer may describe it. Approve, revise, or cancel?

### Behind the scenes

- Walk the entries the point holds, as in Scenario 5.
- The plan says the set may be incomplete, and names the filler that did not answer, with its `reason`.
- Behaviour no held use case describes is a *possible* gap: what the missing filler would have supplied is unknown, not absent.
- An empty `value` in this state is not an empty set, and never leads to Scenario 9's prerequisite Task.
- On filing, `edit-issue` names a cited id the held set lacks as not checked, never as unknown. That notice is about the check, not against the body: pass it on to the user and go on.

## Scenario 8: The use cases could not be read

### Trigger

The point is defined and filled, and its resolution gave no set: an `outcome` other than `resolved`, `undefined` and `unfilled`, no document at all, or a document whose version the procedure does not know.

### Preconditions

- Typically a clone that has not fetched the default branch, so the filler that reads settled state is not started.

### Walkthrough

> **User:** Plan the export feature from the handoff note in the scratchpad.
>
> **project-manager:** *Reading the handoff note…* *Reading the use cases settled on the default branch…* The use cases could not be read: this clone has no copy of `origin/main`, so the filler that reads it was not started. `git fetch origin main` fixes that. I'll plan without the use-case step; fetch and ask again to have the plan checked against them.
>
> *(Continues with Scenario 1 from the slicing step, without the Use cases column. The approval gate says again that the use cases could not be read, and why.)*

### Behind the scenes

- Say that the use cases could not be read, and why: the document's `why`, and each inert filler's `reason`.
- Proceed without the step: no Use cases column, no `## Use cases` sections, no gaps reported.
- Never read this state as an empty set: no prerequisite Task, and no statement that the project has no use cases.
- The gate's message carries the same sentence, so the plan is approved knowing it was not checked.
- When the user fetches and asks again, read the point again from the start.

## Scenario 9: No use case has settled yet

### Trigger

The point resolved in full and holds nothing: `outcome: resolved`, no inert filler, an empty `value`.

### Preconditions

- Something fills the point — the project keeps use cases, or is set up to — and none has reached the default branch.
- The plan touches what users do: at least one planned Feature or Task serves a goal someone using the software reaches (otherwise Scenario 11).
- No answer from earlier today is kept in this checkout: `pkit pm decline-use-case-task --show --json` gives `none` or `expired` (otherwise Scenario 10).

### Walkthrough

> **User:** Plan the export feature from the handoff note in the scratchpad.
>
> **project-manager:** *Reading the handoff note…* *Reading the use cases settled on the default branch…* None has settled yet, so there is nothing to check the plan against. I'll slice first, then see which of the work touches what users do.
>
> **project-manager:** *Checking for an answer kept in this checkout…* Plan: one Feature, "Report export", with four Tasks. No use case has settled yet. T2 and T3 touch what users do, so T1 "Author the use cases for report export" comes first and they depend on it; T4, a refactor, does not. T2 and T3 state their goals in text — export a report, schedule an export — citing no use case, since none has settled. T1's last acceptance criterion: "T2 and T3 name the use cases they serve". Revise T1 away to plan without use cases; this checkout won't offer it again until tomorrow. Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Clears any kept answer, then continues with Scenario 1's filing flow, T1 first, so the `## Dependencies` sections of T2 and T3 name it by number. T4 does not depend on it.)*

The user may revise the Task away at the gate:

> **User:** Drop T1 — we're not writing use cases for this.
>
> **project-manager:** Dropped. The Feature's body will say the plan was made without use cases. This checkout won't offer it again until tomorrow. Updated plan: one Feature, three Tasks, no use case cited. Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Keeps the answer, then continues with Scenario 1's filing flow.)*

### Behind the scenes

- The prerequisite Task is in the plan by default. It is not offered as a question before slicing.
- After slicing, judge each Feature and Task: does it touch what users do — a goal someone using (not building) the software reaches, which a use case would describe? The build, tests, CI, refactors, tooling, and documentation of the method itself are internal. The table's Use cases column shows the judgement for every row: `T1` for T2 and T3, `none` for T4.
- Then read the kept answer: `pkit pm decline-use-case-task --show --json`. Here its `state` is `none` or `expired`, so the Task is in. An `unreadable` answer, or a command that fails, puts it in too, and the gate adds that an earlier answer could not be read, with its `why`.
- Only the issues that touch what users do depend on the Task: each names it in `## Dependencies`. They state the goals they serve as text and carry no `## Use cases` section. Internal work does not depend on it.
- One of the Task's acceptance criteria is that the dependent issues name their use cases. It closes the loop: the Task does not close until each dependent Feature and Task has gained its `## Use cases` section, which it can once the use cases have settled.
- The answer is kept on approval, never at the revision. On approval of a plan the user revised the Task out of, run `pkit pm decline-use-case-task` before filing. The plan's topmost new issue then says in prose that it was planned without use cases; where the plan files only under an existing issue, each filed issue says so.
- On approval of a plan that includes the Task, run `pkit pm decline-use-case-task --clear` before filing: an answer kept earlier is discarded.
- A cancelled plan keeps nothing. A revision returns to the slicing step, which judges again and reads the kept answer again; a Task the user revised away in this plan stays out.
- Removing the Task because an open issue already plans the authoring of the use cases is not a decline: the issues that touch what users do depend on that open issue, nothing is kept, and no issue says it was planned without use cases.
- The project-manager never writes a use case — it does not stamp, edit or commit one — and suggests no id for one: an id is settled once its use case reaches the default branch.
- No `gh` mutation happens before the approval gate.

## Scenario 10: A Task declined earlier the same day

### Trigger

Over an empty set, a plan that touches what users do, in a checkout where the Task to author the use cases was declined earlier the same day: `pkit pm decline-use-case-task --show --json` gives `state: declined`.

### Preconditions

- As Scenario 9: the point resolved in full and holds nothing, and the plan touches what users do.
- At 09:12 today, in this checkout, the user approved a plan they had revised the Task out of.

### Walkthrough

> **User:** Plan the dashboard filters from the issue I linked.
>
> **project-manager:** *Reading the issue…* *Reading the use cases settled on the default branch…* None has settled yet. I'll slice first.
>
> **project-manager:** *Checking for an answer kept in this checkout…* Plan: one Feature, "Dashboard filters", with two Tasks; both touch what users do and state their goals in text. No use case has settled yet. You declined the Task to author them at 09:12 today; it is offered again from tomorrow. Say if you want it in this plan. Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Continues with Scenario 1's filing flow. The Feature's body says the plan was made without use cases. Nothing is kept: the answer from 09:12 is not renewed.)*

The next morning, at 09:30, the Task is back:

> **User:** Plan the report sharing from the handoff note.
>
> **project-manager:** *Reading the handoff note…* *Reading the use cases settled on the default branch…* None has settled yet. I'll slice first.
>
> **project-manager:** *Checking for an answer kept in this checkout…* Plan: one Feature, "Report sharing", with three Tasks. No use case has settled yet. T2 and T3 touch what users do, so T1 "Author the use cases for report sharing" comes first and they depend on it. Revise T1 away to plan without use cases; this checkout won't offer it again until tomorrow. Approve, revise, or cancel?

The user may want the Task the same day after all:

> **project-manager:** … You declined the Task to author them at 09:12 today; it is offered again from tomorrow. Say if you want it in this plan. Approve, revise, or cancel?
>
> **User:** Add it — I'll write them this week.
>
> **project-manager:** Added T3 "Author the use cases for dashboard filters", to come first; T1 and T2 depend on it. Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Clears the answer from 09:12, then continues with Scenario 1's filing flow, T3 first.)*

### Behind the scenes

- Same day → no Task; next day → Task again. The answer counts as declined for the rest of the calendar day on which its plan was approved, in the machine's local time, and has expired from local midnight on. Quote the local times the command gives — `declined_at_local`, and `offered_again_at_local` — rather than work them out.
- Read the kept answer after the judgement, never before it: a plan of internal work reads nothing (Scenario 11).
- A plan that leaves the Task out on a kept answer keeps nothing: the answer is not renewed, so the Task comes back the next day whatever is planned today.
- The plan still says so on filing: its topmost new issue says in prose that it was planned without use cases — or each filed issue does, where the plan files only under an existing issue.
- When the user asks for the Task, it stays in the plan through every revision, and on approval `pkit pm decline-use-case-task --clear` discards the kept answer before the Task is filed.
- The answer is this checkout's. Another clone or worktree keeps its own, so a plan made there asks again, and a worktree removed after planning takes its answer with it.

## Scenario 11: Internal work over an empty set

### Trigger

Over an empty set, a plan none of whose Features and Tasks touches what users do.

### Preconditions

- As Scenario 9: the point resolved in full and holds nothing.
- Every planned issue is internal work: the build, tests, CI, refactors, tooling, or documentation of the method itself.

### Walkthrough

> **User:** Plan the CI clean-up from the scratchpad note.
>
> **project-manager:** *Reading the scratchpad note…* *Reading the use cases settled on the default branch…* None has settled yet. I'll slice first.
>
> **project-manager:** Plan: one Feature, "CI clean-up", with two Tasks — T1 splits the CI pipeline, T2 refactors the export module. No use case has settled yet, and this plan touches nothing users do — it splits the CI pipeline and refactors the export module — so it has no Task to author use cases. Say if it does. Approve, revise, or cancel?
>
> **User:** Approve.
>
> *(Continues with Scenario 1's filing flow. Nothing is kept, and no issue says it was planned without use cases.)*

The user may correct the judgement:

> **User:** T2 isn't only a refactor — it adds a way to retry a failed export.
>
> **project-manager:** Then T2 touches what users do. *Checking for an answer kept in this checkout…* T3 "Author the use cases for retrying an export" comes first, and T2 depends on it; T1, the CI split, does not. Revise T3 away to plan without use cases; this checkout won't offer it again until tomorrow. Approve, revise, or cancel?

### Behind the scenes

- Judge each Feature and Task after slicing. When none touches what users do, the plan has no prerequisite Task, and the table's Use cases column shows `none` on every Feature and Task.
- Read no kept answer and keep nothing: `decline-use-case-task` is not run, at the gate or on approval.
- The gate says why, naming what the work is, and invites a correction.
- No issue says it was planned without use cases: the plan builds nothing a use case would describe.
- A correction is not a decline. When the user says an issue touches what users do, the slicing step judges again, and Scenario 9's rule applies: read the kept answer, and include the Task unless it was declined earlier today (Scenario 10).
- When a correction leaves no issue that touches what users do, the plan is back here: no Task, and nothing kept.
