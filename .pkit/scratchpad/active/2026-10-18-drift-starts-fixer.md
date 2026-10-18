---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-18
---

# A drift finding starts its place's fixer

The design round of #1684. When drift is found, the fixer declared for that kind of artefact starts, and its proposal waits for the person. Nothing is applied without them.

- **Starts from:** the issue, the maintainer's choice 10 of 17 October and gaps G7, G11 and G12 (`2026-10-17-autonomous-feature-flow`), and the note `2026-07-02-agent-dispatch-privilege-model`.
- **Reviewed:** the architect recommended the design, and the critic reviewed it. Three red flags are fixed below. "Review" lists every finding and its answer.
- **Decides nothing.** The question for the maintainer is under "Who may start which agent". Records change only through the acceptance gate.

## In short

- **A command starts the fixers, not the `Agent` tool.** A project-management command reads the declared fixers, starts each granted one headless, as `review-pr` starts reviewers, and gathers the proposals. Code fixes the set of agents, so tests can check it.
- **The project grants, the capability declares.** A capability declares which of its agents fixes which of its types. Only the agents the project has granted in writing start. Until then the command starts nothing.
- **A fixer runs confined.** The command denies it every write but the workspace, and every network call. A fixer is a leaf: it starts no other agent.
- **The proposal waits as files,** in one durable run folder with an index. The project manager brings the proposals to the person in one batch. Once the person accepts, the project manager applies them through an ordinary pull request.
- **Built after #1682,** as choice 10 orders. The view then lists proposals as a third kind beside ready merges and acceptances.

## Who may start which agent

This is the issue's first criterion and the maintainer's to decide. Today only a person starts a fixer.

1. **Only you.** The command prints each fixer's start command, and you run it. Nothing new is granted, and nothing is automated.
2. **You start the command each time.** It starts every fixer the installed capabilities declare. Each run has your consent, and nothing runs after a merge on its own.
3. **Agents on a list you write.** You grant each fixer once, by name, with an opt-in command, as `enable-default-agent` works (DEC-030). The project manager may then run the command after each merge without asking. Only the agents on your list start. **Recommended.**
4. **Every fixer an installed capability declares.** Installing the capability is the grant, and the project manager runs the command after each merge. This is the architect's first recommendation.
5. **A privilege the permission hook enforces on the `Agent` tool.** This is the dispatch note's design. It cannot be built until a record accepts it, and it would not see a command that starts agents.

**Why 3.** A started fixer can do more than a reviewer. A contributed reviewer adds a gate and narrows what merges (DEC-032). A contributed fixer runs an agent with a shell, unwatched. project-kit lets a narrowing apply on install and keeps a widening explicit (ADR-008, and ADR-016 point 7 for a capability's deny). So the person grants each agent. Option 3 is also the shape the dispatch note gives its allowlist, a list a person writes for each agent (its D3). The two can then meet later. Option 4 would have to be undone.

**What every option keeps.**
- A fixer only proposes. It runs no friction writer, as "Friction writers" in the agents README requires of an agent nobody watches.
- Accepting a proposal, and merging the change that applies it, stay the person's (choices 1 and 2).

## The design

### The declaration

- **A data point project-management accepts,** `pkit::work-tracking:fixers`, beside `doc-check` and `use-cases` (DEC-053, DEC-054).
  - **Entries:** `{id, agent, description}`. The `id` is a qualified type, such as `software-analysis:use-case` (COR-056).
  - **Combination `union`:** two capabilities that claim one type collide, and the project settles it by an override (COR-052 point 4).
  - **No default.** A filler that goes inert reads "fixers unknown for its types", never "no fixer" (COR-052 point 6, `fallback`).
- **Keyed by type, not by place.** A place has no id, and a type has. A project place typed `living-docs:page` gets the fixer too. It is no field on COR-050's place. A third concept on places would move places into a functionality of their own (COR-056 point 7).
- **A static `value`, not a command filler.** The declaration reads in package metadata and in review, and resolving it runs no code (`src/project_kit/data_points.py`).
- **Contributions:**
  - software-analysis: its actor, term, use-case and journey types, each naming `analysis-resolver`
  - living-docs: `living-docs:page`, naming the `living-docs` agent in its friction-fix intent
- **Checked at validation and on every run:** the type is the contributor's own, and the agent is shipped by the same capability and deployed. A frontmatter test, `owns: []` and no `Edit` or `Agent` tool, is a sanity check only. With a shell and `Write`, frontmatter limits nothing at run time. The confinement below does.

### The grant

- A list in project-management's project configuration: each granted agent, and the types it may fix. It is empty by default.
- One opt-in command writes it, with the person's consent (COR-048), and another removes an entry. Both are shown in the diff.
- The command starts a declared fixer only when the list grants it.

### The run

- **The command,** such as `pkit pm fix-drift`, with `--dry-run`. The person runs it, or the project manager does, in the session that landed a merge into the default branch. Either way it starts only granted agents.
- **Reading friction:** `pkit friction check --all --json`, and the types from `pkit friction artefacts --json` (COR-056 point 6). Not the tracking issue: its workflow is project-kit's own, and its body is rendered prose.
- **Where it runs:** a detached worktree at the default branch's commit, from a full clone. It is provisioned with `uv sync` and `pkit sync`, as the workflow is, so every anchor resolves.
- **What is dispatched:** stale artefacts only. Deferred debt, dead or ambiguous anchors, artefacts the check could not judge and type ties are listed, not dispatched.
- **Order:** upstream first (COR-050 point 11). An artefact whose upstream is stale under another fixer waits, listed as such, until the upstream is answered.
- **Unchanged friction:** an artefact whose friction matches its standing proposal is not dispatched again. `--force` dispatches it anyway (DEC-046).
- **Bounds:**
  - a cap per fixer, counting only artefacts with no standing proposal, so each run moves on
  - two fixers at once by default, as in `review-pr`
  - a wall-clock limit per fixer
  - one run at a time per repository, held by a lock
  - an artefact an open pull request already changes is listed, not dispatched
- **A fixer that fails:** retried once for a cause outside its work, such as a timeout (core rule 21). If it fails again, its artefacts are marked failed and the rest go on.
- **The result:** each fixer ends with one fixed line per artefact, as DEC-028's verdict line does: proposed, held with a question, or none with a reason. The command reads that line, never prose.

### Confinement

A headless run cannot prompt. So a tool call no rule allows is refused, and the allow list is the whole grant. project-kit's allow list approves `git`, `gh`, `pkit`, `uv`, `rm`, `Write` and `Edit`.

- **What an unwatched fixer could do under it:** push, merge through `land-work --yes`, flip a record's status, or run a writer. Text from commit messages and pull requests reaches the analysis-resolver, so a contributor's words could steer it.
- **What the command sets for each run:**
  - deny rules, which win over any allow: every write but the run worktree's own workspace, `git` beyond reading, `gh`, every `pkit` writer and `pkit pm`
  - the OS sandbox around its shell, with no network (ADR-004). The fixers read only local state.
  - the recursion marker: the command refuses to start inside a fixer's run
- **What the ADR must state, not leave to the trial:** the command never passes a flag that bypasses permissions. The sandbox wraps the fixer's shell and leaves the CLI's own connection to its model alone.
- **Checked after each fixer:** nothing changed outside the workspace, no ref moved, and no ignored file appeared. A breach sets that fixer's proposals aside and is reported.
- **What stays:** the permission hook sees only `pkit`. It may also judge a headless agent as the session's default agent (`decide.py`), so no per-agent grant counts until a test shows which agent it judges. A proposal can carry an injected command, so the person reads every command before running it. These stay in the ADR, and the dispatch note covers the command route when it becomes a record.

### The hand-off

- **Files, not a draft pull request.** The fixers already write their proposals into the workspace. A draft pull request needs a branch, a commit, a push and an issue, all under the person's account by a run nobody watched (G12).
- **Kept in the main checkout:** the command gathers every run into the main checkout's workspace, `.agent-workspace/project-manager/drift/`. It keeps an index of each artefact, its type, its fixer, its state and its proposal, and the commit it was judged at. Proposals do not depend on a worktree that is later removed.
- **Why one checkout is enough.** Dispatch is local, as the issue decides. The debt is not kept there: git holds it, and the whole-repository check recomputes it anywhere (COR-050 point 9). A proposal is work that can be done again. In a checkout that holds none, a stale artefact has no standing proposal, so the next run there dispatches it again. A view on another machine shows the debt, and marks each artefact with no proposal there.
- **Visible:** `land-work` prints a one-line count of proposals waiting, until #1682 lists them.
- **One batch:** the project manager brings the proposals together, each with its commands word for word (choice 1, and "Friction writers" condition 3). The person accepts, rewords or refuses each.
- **After yes:** the project manager files an issue, branches, applies the diffs and runs the writers the person accepted. It runs a writer only under the four conditions of "Friction writers", so its body names them. The change then passes the ordinary gate, and the person authorises its merge.

### What #1682 adds later

One place lists the proposals beside ready merges and acceptances. #1682's first scope names only those two, so proposals are a third kind it must add.

## Order of work

Choice 10 builds the loop after #1682 and after project-kit has its analysis and pages. project-kit's analysis holds eight actors and a glossary today, with no use case, so a loop built now has little to run on. The tasks below keep that order. Three go ahead, since none adds the loop: the decision the first criterion needs, its ADR, and moving the runner, which changes no behaviour.

## Records that change

- **New, project-management:** a decision holding the point, the grant, the command and its bounds, the confinement, the hand-off and the batch. It answers the first criterion.
- **New, ADR:** agents a command starts. Where the runner lives, its tie to the `claude` CLI, what the permission hook sees, the per-run confinement and the check after the run. It is accepted before the command is built.
- **Refined in place:**
  - project-management DEC-029, "Invocation pattern": an agent a project-management command starts is no `Agent`-tool dispatch, and its set is the grant the command reads
  - software-analysis DEC-001 and living-docs DEC-001: each names its agent as the fixer of its types
  - the agents README, "Friction writers" condition 2: "an agent another agent or a command started"
  - both fixers' bodies and storyboards: the brief they take, the result line, and "a command started you"
  - the pm skill and the project manager's body: when to run the command, the batch, and applying accepted proposals
  - the dispatch note: the command route
- **Untouched:** COR-050, COR-052, COR-053, COR-056, COR-028 and the privilege catalog. No migration: every change adds.
- **Changesets:** a minor each for project-management, software-analysis and living-docs.
- **Later:** a harness requirement (COR-047) that an agent can be started confined from a command and its files read.

## Build tasks

1. **The project-management decision.** The critic, the architect and the methodology-reviewer, then the maintainer's acceptance. Delivers the first criterion. It can start now.
2. **The ADR,** after task 1. Delivers the runner's architecture, accepted before task 5.
3. **The runner out of `review-pr`,** into project-management's `_lib`, after task 2. Behaviour stays the same, so it needs no changeset.
4. **The point and the grant,** after #1682. The schema, the package entry, the checks on each entry, the grant list and its commands, with tests on fixtures. Delivers the declaration and the grant.
5. **The command,** after tasks 3 and 4. The worktree, reading, order, bounds, lock, confinement, the check after the run, the index, the count line and `--dry-run`, tested with a stub runner. Delivers a run that proposes.
6. **software-analysis,** after task 4. The contribution, the agent's brief and result line, its storyboard, the README and the DEC-001 refinement. Delivers its fixer, declared.
7. **living-docs,** the same, in parallel with task 6.
8. **The pm skill and the project manager's body,** after task 5. Running the command after merges, the batch, and applying what the person accepts. Delivers the closed loop.
9. **A live trial,** after tasks 6 to 8. One headless run of each fixer on a seeded stale artefact, its result line read and its confinement tested, the hook's judged agent included. Delivers the evidence a stub cannot give.

## Review

### The architect

The architect recommended the design above, with four exceptions the critic changed: the grant was the declaration itself, confinement waited for the dispatch note, proposals went one at a time, and the build could start before #1682. Its escalation flags:
- **Who may start which agent.** Kept, as the question above.
- **Not waiting for the dispatch note.** Kept. The note governs the `Agent` tool, and the command route needs no record from it.
- **Unattended agents under a permissive allow list.** Answered by confinement the command sets now.
- **A second way to start agents the permission model cannot see.** Kept, for the ADR and the note.

It also found what the issue gets wrong:
- the fixer is keyed by type, under `connections`
- the checks are read-only, so the project manager dispatches, not the check
- the living-docs agent's brief must name its friction-fix intent
- the Doc impact leaves out DEC-029, the agents README and the note

### The critic

Three red flags. R2 and R3 were fixed at once. R1 was partly fixed, and a confirmation round's remainder is answered.

- **R1. The build reversed choice 10's order without saying so.** Fixed. The build follows #1682, and only the decision, its ADR and the runner's move go ahead. The run folder sits in the main checkout, and a count line shows what waits. The confirmation round found the folder still one checkout's. Answered under "Why one checkout is enough": git holds the debt, and a proposal is work that can be done again.
- **R2. The unattended risk was understated, and controls that exist now were deferred.** Fixed. The residual names merging and status changes, and prompt injection. The command sets deny rules and a sandbox without network for each run. The check after the run covers ignored files, and the hook's judged agent is tested in the trial.
- **R3. "The declaration is the grant" misread its precedents.** Fixed. A contributed fixer widens what runs, so the person grants it (ADR-008, ADR-016 point 7). The recommendation is now option 3, a list the person writes.

The confirmation round found no new red flag. Its gaps are answered:
- what goes ahead of #1682 is the decision, its ADR and the runner's move
- the ADR states that no flag bypasses permissions, and that the sandbox wraps only the shell
- the command starts only granted agents, and the project manager runs it in the session that landed the merge
- a fixer writes only into the run worktree's own workspace

The first round's gaps, each answered:
- the frontmatter test is a sanity check, not a limit
- an artefact whose upstream is stale under another fixer waits
- the cap counts only artefacts with no standing proposal
- the worktree is provisioned as the workflow is
- a lock keeps one run at a time, and an open pull request's artefacts are listed
- after the person's yes, the project manager applies through an ordinary pull request
- both fixers' storyboards and bodies change
- a live trial joins the build
- a failed fixer is retried once (core rule 21)

Its weaker points, all taken:
- proposals come in one batch, not one at a time
- the missing `Agent` prompt is no benefit. The hook's blindness to the route is a cost.
- the ADR comes before the command
- DEC-029 keeps the dispatch note for the `Agent` tool, and the new decision covers only what a command starts
- the writers' refusal without `--yes` off a terminal is the code's (`src/project_kit/friction_write.py`), not COR-050 point 13's

Its counter-alternatives:
- **A command the person starts, with no trigger after merges:** option 2.
- **A list the person writes, by an opt-in command:** taken, option 3.
- **A durable hand-off with a count:** taken.
