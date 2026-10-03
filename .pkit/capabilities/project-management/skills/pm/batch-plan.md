# pm batch-plan — take fuzzy intent + reference material and file a sliced plan behind a single approval gate

Sub-procedure of the pm composite skill (`pm.md` in this folder). The `project-manager` agent dispatches here when the user supplies fuzzy multi-issue intent + a reference document (scratchpad, handoff, related issue, decision record) and wants the work sliced into filed issues without a per-issue back-and-forth. The user-facing dialogue and scripted scenarios are authored in the storyboard sibling to the agent (`.pkit/capabilities/project-management/agents/project-manager/storyboard.md`) per [COR-016](../../../../decisions/core/COR-016-scripted-scenario-storyboards.md).

## When to use this operation

- The user provides intent + at least one reference artifact and asks the agent to plan / scope / slice the work.
- The agent infers batch-planning from request shape per step 3 of `project-manager.md`'s `How you work` — the user does not name "batch-plan mode" explicitly.

When the request is **single-issue** ("file this one bug", "create the EPIC for X"), use [create-issue](create-issue.md) directly instead.

## What this sub-procedure carries

Six sequential steps. The agent narrates each step's start to the user per the storyboard's tone rules; the procedural detail is here. Step 2 acts only while the use-case point is not off ([project-management:DEC-054-use-case-validation]); while it is off the flow goes from step 1 straight to step 3, and nothing in it mentions use cases.

### 1. Read intent and reference material

- Read the user's fuzzy intent verbatim from the conversation.
- Read every reference artifact the user points at, using the `Read` tool. Common shapes: a scratchpad note under `.pkit/scratchpad/`, a handoff document, a related GitHub issue (fetch via `gh issue view`), a decision record, or a verbal description from earlier in the session.
- If any reference cannot be resolved (path not found, issue not accessible), surface the gap before proposing a slicing — do not guess content.
- If the user's intent has missing inputs that prevent slicing (no reference at all; scope too vague), ask at most two clarifying questions per the storyboard's Scenario 2 — not a sequence of single-question turns.

### 2. Walk the use cases (while the use-case point is not off)

Per [project-management:DEC-054-use-case-validation], a slicing is checked against what the software must do before it is proposed. The use cases come from one place: the `pkit::work-tracking:use-cases` data point, the use cases settled on the default branch — each an `id`, a `title`, a `status` (`active` or `withdrawn`) and, where given, the `path` of the document that describes it. Whatever keeps the project's use cases fills the point; this step reads the point and nothing else.

**Read the point**: `pkit connections resolve pkit::work-tracking:use-cases --json`. The command exits 1 on an unresolved point and still prints its document, so the document decides, never the exit code. Decide on the document's `outcome` and on its fillers' `state`. Its `why` is a sentence to show the user, never one to decide on. The storyboard scripts each state in which the step acts: a walk (Scenario 5), a gap (6), a partly checked set (7), use cases that could not be read (8), and an empty set — under work that touches what users do (9), under a Task declined earlier the same day (10) and under internal work (11).

| The document | State | What the step does |
|---|---|---|
| `outcome` is `undefined` or `unfilled` | off | Nothing. No Use cases column in step 3, no `## Use cases` section in step 6, and nothing said about use cases. |
| `outcome` is `resolved`, no filler's `state` is `inert`, `value` has entries | has entries | Walks them. |
| `outcome` is `resolved`, no filler's `state` is `inert`, `value` is empty | empty | Plans the prerequisite Task ahead of work that touches what users do, unless a declined answer is kept (step 3). |
| `outcome` is `resolved`, and a filler's `state` is `inert` | partly checked | Walks what the point holds, and says the set may be incomplete. |
| any other `outcome`, including one this table does not list; no document; a `schema_version` other than 1 | could not check | Says the use cases could not be read, and why, and goes on without the step. |

- **With entries, walk the active use cases against the intent.** A withdrawn use case is history: no new work serves it. Where an entry carries `path`, read that document for what the use case says; where the entries carry none, map the intent from titles alone and say so in the plan. Note three things for the gate: the use cases each planned Feature and Task serves; each use case the intent touches that no planned issue names; and the behaviour the plan builds that no use case describes.
- **Partly checked: walk the entries the point holds**, as above. The plan says the set may be incomplete and names the filler that gave no answer, with its `reason`. Behaviour that no held use case describes is shown as a *possible* gap, since the missing filler may describe it. An empty `value` in this state is not the empty set: it does not lead to the prerequisite Task.
- **With an empty set, there is nothing to walk.** No use case has settled, so no planned issue cites one. Whether the plan opens with a prerequisite Task to author them depends on what the planned work does, so step 3 decides it after slicing ("Over an empty set: the prerequisite Task").
- **Could not check: say so, and why** — the document's `why`, and each inert filler's `reason` — then go on to step 3 without the step. An unread point is never read as an empty set: no prerequisite Task, and no claim that the project has no use cases.
- **Do not write use cases.** Their authoring is planned as work. Suggest no id for a use case that has not settled: an id is settled once its use case reaches the default branch.

### 3. Propose the slicing

Apply the methodology's typing rules to the work units implied by intent + references:

- **Hierarchy choice** — [project-management:DEC-004-six-level-hierarchy] gives the Umbrella / EPIC / Feature / Task / Milestone taxonomy. Choose the smallest type that contains the work; do not over-nest. A multi-deliverable arc → EPIC with Feature children; a single deliverable → standalone Feature (no EPIC wrapper) per the small-adopter shortcut.
- **Classification per ticket** — [project-management:DEC-012-classification-axes] specifies workstream / priority / kind labels. Read the adopter's `project/workstreams.yaml` for allowed workstream values; the kind axis maps to `type:*` labels per the script's enforcement. Default priority is Medium unless intent signals otherwise.
- **Parent-refs** — [project-management:DEC-005-linking-and-containment] specifies the `Milestone: #N` / `EPIC: #N` / `Feature: #N` / `Task: #N` body-first-line format. The slicing must produce a consistent reference graph (no cycles; each child has the correct parent type per `issue-types.yaml`'s containment graph).
- **Dependency chain** — express ordering between issues either implicitly (via parent-refs) or explicitly (as Dependencies sections in the body). Flag tight coupling in the body's Approach / Notes section.
- **Same-module Tasks are built one at a time** — two Tasks are in the same module when the source files their bodies' implementation notes name overlap. The later one names the earlier in its `## Dependencies` section (one of the recommended sections in [project-management:DEC-010-issue-body-minimum-structure]; the relation is textual, per [project-management:DEC-005-linking-and-containment]), whether the earlier is in this plan or already open, and is dispatched once the earlier has merged — a scheduling constraint, because the two change the same files, not a dependency of one outcome on the other. Tasks in different modules run in parallel. Each landing in a shared module sends every other open PR there through another review round, which is why parallel work inside one module costs more than it saves.
- **Milestone resolution** — if the adopter's config or the intent names a milestone, attach it. If neither, prompt before the approval gate. A follow-up a reviewer produced takes the scope decision in [create-issue](create-issue.md)'s intent recognition instead, which can leave it without a Milestone.
- **Use cases per ticket** (only when step 2 walked a set) — name the use cases each Feature and Task serves, citing only ids the point holds. A Feature or Task that serves none — an internal refactor, a chore — shows `none`. Only Feature and Task bodies carry the section, so every other type shows `—`.
- **Over an empty set: the prerequisite Task** (only when step 2 read an empty set). Decide it once the slicing stands, and again on every revision, since step 5 returns here:
  1. **Judge each planned Feature and Task: does it touch what users do?** Work touches what users do when it serves a goal someone using (not building) the software reaches, which a use case would describe. Internal work serves none: the build, tests, CI, refactors, tooling, and documentation of how the software is built and worked on. For a library or a command-line program, using it is calling or running it to reach the user's goal; building, testing or releasing it is internal. It is the judgement the walk over a set with entries makes for the second kind of gap: whether the plan builds behaviour a use case would describe.
  2. **No planned issue touches what users do:** the plan has no prerequisite Task. Read no kept answer and keep nothing; the gate says why (step 5).
  3. **Otherwise, an answer the user gave in this plan holds:** a Task they revised away stays out, and a Task they asked for stays in, whatever is kept.
  4. **Otherwise, read the kept answer:** `pkit pm decline-use-case-task --show --json`, and decide on its `state`:
     - `declined` — the Task was declined in this checkout earlier today: leave it out, and quote `declined_at_local` at the gate.
     - `none` or `expired` — include the Task.
     - `unreadable`, or the command fails or prints no document — include the Task, and say at the gate that an earlier answer could not be read, with its `why`.
  5. **When the Task is in the plan, it comes first.** Only the issues that touch what users do depend on it, each naming it in its `## Dependencies` section; internal work does not. The dependent issues state the goals they serve as text and cite no use case, since none has settled. One of the Task's acceptance criteria is that the dependent issues name their use cases: once the use cases have settled, each dependent Feature and Task gains its `## Use cases` section.
  6. **The Use cases column shows the judgement** for every Feature and Task, as the walk over a set with entries shows `none`: the Task's number (`T1`) where the issue depends on it, `declined` where the issue touches what users do and the Task is left out on the user's answer, and `none` for internal work. Every other type shows `—`.

Render the slicing as a single table the user can scan at a glance (the Use cases column only when step 2 read a set, empty or not):

| # | Type | Title | Parent | Workstream | Milestone | Priority | Use cases | Notes |
|---|---|---|---|---|---|---|---|---|

### 4. Adversarial review (when threshold applies)

Per [project-management:DEC-029-project-manager-agent-shape]'s reviewer-invocation discipline:

- **Multi-issue arcs (≥3 issues to file)** invoke the `critic` agent against the proposed slicing. Pass the slicing table + the source reference document.
- **Cross-component work (≥3 components touched, or any work introducing a new abstraction)** additionally invoke the `architect` agent.
- **Narrow single-issue work** skips the reviewer pass.

Capture each reviewer's findings. Decide per finding whether to (a) revise the slicing to incorporate the concern, (b) annotate the EPIC body's Approach / Notes section to record the unresolved concern, or (c) note the disagreement and let the user resolve at the approval gate.

### 5. Single approval gate

Present the slicing to the user as a single message:

- The slicing table.
- The dependency chain (explicit ordering).
- Reviewer findings summary (which were incorporated, which are noted, which need user resolution).
- When step 2 walked a set: the use-case mapping (the table's column) and both kinds of gap — each use case the intent touches that no planned issue names, and the behaviour the plan builds that no use case describes. Over a partly checked set: that the set may be incomplete, which filler did not answer, and the second kind as possible gaps. Where the walk went by titles alone, that too.
- Over an empty set, the table's Use cases column and one of these lines:
  - **The Task is in the plan:** "No use case has settled yet. T2 and T3 touch what users do, so T1 'Author the use cases for report export' comes first and they depend on it; T4, a refactor, does not. Revise T1 away to plan without use cases; this checkout won't offer it again until tomorrow."
  - **Internal work only:** "No use case has settled yet, and this plan touches nothing users do — it splits the CI pipeline and refactors test helpers — so it has no Task to author use cases. Say if it does."
  - **Declined earlier today:** "No use case has settled yet. You declined the Task to author them at 09:12 today; it is offered again from tomorrow. Say if you want it in this plan."
  - **An earlier answer could not be read:** the first line, and "An earlier answer to this could not be read (<why>), so the Task is offered."
- When the use cases could not be read: that, and why.
- Bodies are not shown at the gate — they are filled per ticket after approval. The slicing's classifications, parent-refs and use cases are the contract the user approves.

End the message with: "Approve, revise, or cancel?"

**No `gh` mutation happens before this gate fires positively.** On revision, return to step 3 and re-render; over an empty set, step 3 judges each issue again and reads the kept answer again. On cancel, end the operation; surface "Cancelled. Nothing filed." — and over an empty set nothing is kept. On approve, proceed to step 6.

Over an empty set, tell a decline from a correction:

- **The user removes the Task itself:** a decline. The plan is made without use cases, and the answer is kept when the plan is approved (step 6).
- **The user says an issue does, or does not, touch what users do:** a correction of the judgement, not a decline. Step 3 judges again; where no issue that touches what users do remains, the plan has no Task, as for internal work, and nothing is kept.
- **The user removes the Task because an open issue already plans the authoring of the use cases:** not a decline either. The issues that touch what users do depend on that open issue instead, and nothing is kept.

### 6. File via primitives

In dependency order (parents before children so parent-ref values are available):

- For each ticket: call `scripts/create-issue.py` with `--type`, `--title`, `--kind`, `--workstream`, `--priority`, `--parent` (if any), `--yes` — and, when the plan originated from a feedback/change-request report #N, `--from-report N` so each filed issue is auto-linked into #N's `## Tracked by` (per [project-management:DEC-048-from-report-auto-link]; a link failure exits 4 with a remediation command and never rolls the issue back).
- Parse the script's `[ok] created: <URL>` line for the new issue number.
- Immediately call `scripts/edit-issue.py --body-file <tmp> --yes` to overwrite the auto-generated template body with the planned body content (the create-issue.py script produces a placeholder body; the real content is what was approved at the gate). When a Feature or Task names use cases, its body lists them in a `## Use cases` section, one per line (`- UC-003 — <the use case's title>`); an issue that serves none has no such section, and neither has a body of another type.
- `edit-issue` reports on that section at warning severity and never refuses the edit over it. A use-case citation warning on a body the plan wrote means it cites a use case the point does not hold — a mistyped id, or one that has not settled. Correct the body (fix or drop the id) and re-run `edit-issue` rather than leave the guess filed. The other thing it may say is that citations were not checked — the point could not be read, or it answered without a filler that was meant to answer. That is a notice about the check, not a finding against the body: pass it on to the user and go on.
- Over an empty set, before and while filing:
  - **The plan includes the Task:** run `pkit pm decline-use-case-task --clear`, then file the Task ahead of the issues that depend on it, so their `## Dependencies` sections name it by number.
  - **The user revised the Task away at this gate:** run `pkit pm decline-use-case-task` before filing, so plans from this checkout leave the Task out for the rest of the day.
  - **The Task was left out on a kept answer:** keep nothing; the kept answer is not renewed.
  - **Whenever the Task is left out on the user's answer**, given at this gate or kept, the plan's topmost new issue says in prose that it was planned without use cases — or, where the plan files only under an existing issue, each filed issue does.
  - **Internal work only, or the Task removed because an open issue already plans the authoring:** keep nothing and write no such line. In the second case, the dependent issues name that open issue in their `## Dependencies` sections.
- Attach milestone via `gh issue edit <number> -R <repo> --milestone "<title>"` per the workaround for issue #177 (the create-issue.py `--milestone NUM` path is broken pending that issue's fix).
- Handle each script's failure modes per [validate-body](validate-body.md)'s severity model: warnings emit and continue; hard-rejects pause and follow the storyboard's Scenario 4 walkthrough.

After the filing loop completes:

- Surface the final state to the user: filed issue numbers + URLs, skipped issues (if any), total mutations.
- If state transitions were part of the plan (move issue from Triage to Backlog, etc.), invoke the [transition-state](transition-state.md) sub-procedure for each transition. Cascades fire per the workflow schema.

## Handling failures during filing

Per the storyboard's Scenario 4: on hard-reject, surface the specific rule that fired (DEC + schema entry), propose at least one corrective action, wait for the user's authorisation. Do not bypass hard-rejects. Aggregate consecutive failures where possible so the user is not asked one-by-one for related fixes.

## What this sub-procedure does NOT do

- It does not architect *what* to build. Architectural and product decisions go to the user, the `architect` agent, or a human. Batch-planning takes the user's stated outcomes and slices them into tickets; it does not invent the outcomes.
- It does not write use cases. Over an empty set it plans their authoring as work — the prerequisite Task, ahead of the work that touches what users do — and a later plan walks them once they have settled.
- It does not authorise itself to bypass the membership gate ([project-management:DEC-021-team-membership-gate]) or any hard-reject severity. The user authorises bypassable-with-audit overrides; hard-rejects are never bypassable.
- It does not skip the single approval gate even when "the slicing seems obvious". The gate is the contract; the agent waits.
- It does not file before the cited prerequisites (parent EPIC, dependent decisions). If a slicing depends on an unfiled prerequisite, file the prerequisite first and then file the dependents in the same approval-gated session.
