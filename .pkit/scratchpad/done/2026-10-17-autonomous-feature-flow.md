---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-17
retired: 2026-10-18
produced:
  - https://github.com/aleskalfas/project-kit/issues/1673
  - https://github.com/aleskalfas/project-kit/issues/1667
  - https://github.com/aleskalfas/project-kit/issues/1674
  - https://github.com/aleskalfas/project-kit/issues/1675
  - https://github.com/aleskalfas/project-kit/issues/1676
  - https://github.com/aleskalfas/project-kit/issues/1677
  - https://github.com/aleskalfas/project-kit/issues/1678
  - https://github.com/aleskalfas/project-kit/issues/1679
  - https://github.com/aleskalfas/project-kit/issues/1680
  - https://github.com/aleskalfas/project-kit/issues/1681
  - https://github.com/aleskalfas/project-kit/issues/1682
  - https://github.com/aleskalfas/project-kit/issues/1683
  - https://github.com/aleskalfas/project-kit/issues/1684
  - https://github.com/aleskalfas/project-kit/issues/1685
---

# A big feature through project-kit, ready for autonomous agents

The design round of #1648. A big feature should move through project-kit from its assignment to its release, with every artefact kept in step. Agents should do most of the work. This note sets out that flow, compares it with established processes, and writes the version an autonomous agent can follow.

- **Read from main at `65b7604e`:** the records, the guides and the code cited below. `9bff1a6e` landed during the reviews, and step 2 reads it.
- **Starts from:** the project manager's sketch of 17 October, and this session's practice. Every claim of the sketch was checked. "What the sketch gets right, and what it gets wrong" lists the corrections.
- **Governed by:** the anchors and friction record (COR-050), software-analysis DEC-001, living-docs DEC-001, and project-management's records on planning, the gate and landing (DEC-006, DEC-026, DEC-028, DEC-032, DEC-054, DEC-055).
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Decided:** the maintainer answered each choice on 17 October. His answers are in "For the maintainer", with the issues filed from them. No record changes here.

## The question

How does a big feature move from an assigned intent to a release and then stay true, each artefact resting on those before it? Which parts of that may an agent do alone, and which must stop for a person? And how does a person hand authority to an agent and take it back?

## In short

**Write what the system must do first, then decide how, then build and verify, then explain.** Each description anchors what makes it true, so a change flags every description resting on it. Each pull request answers those flags before it merges.

**Agents do the work, and the person makes the decisions.** A person hands an agent the work of a plan, never a decision. Each decision stays for one pull request or one record, but an agent can bring the person several together. A chain of tasks can merge into the plan's integration branch, so the person decides once, on the merge into main.

- **The flow:** eight steps, from planning to drift. Most of the machinery exists. The gaps are in the analysis, in the trace from a requirement to its test, and in who may decide what.
- **The comparison:** every established process put people in its roles, and the authority came with the role. Each kept its trace apart from the code. Each left independence and attention to people.
- **The autonomous version:** a producer never judges its own work. A gate reads evidence, never the producer's account. An agent stops at every decision on a closed list, at a judgement no rule settles, and before anything on the never-alone list.
- **The largest gap:** this session merged pull requests and accepted records on standing delegations that no record holds. DEC-006, the pm skill and the project manager's own instructions all ask for the person's authorisation of each merge. And today nothing can tell an act of the person from an agent's. Attribution and acceptance are one core question (G2).
- **Light where it can be:** each step runs only when its trigger holds. A fix, a record or a page change skips most of them.

## 1. The reference flow

### The principle, corrected

The sketch says each later artefact anchors what it rests on, from use cases to requirements, decisions, code and docs. The anchors run another way.

- **Only an artefact carries anchors.** An artefact is a document, or a collection entry, in a place declared to hold them (COR-050 point 1).
- **An artefact anchors what makes it true:** what it describes, and what it applies. A use case anchors the code it exercises and the records it relies on (software-analysis DEC-001 point 4). A page anchors code, records, analysis artefacts and the home of each fact it summarises (living-docs DEC-001 point 4). A rule that fills another anchors the rule it fills (COR-051).
- **Code and tests are not artefacts, so they anchor nothing.** A decision record may anchor what it governs (COR-050, "Why it is core"). None does yet, as the architect found on #1393 (PR #1646, "Beyond this issue").
- **So a change flags only the artefacts anchored to it.** Changed code flags the use cases and pages anchored to it. A changed decision flags whatever anchors it. A changed use case flags the journeys and pages anchored to it, and no code and no test.
- **Friction lands only where an answer can be held.** The answer lives in the artefact, never in a pull request's description (COR-050). A test can hold none.
- **The order of writing is not the order of anchors.** The analysis is written first, and anchors the code written after it. Friction carries a change from the code back to every description. Nothing carries a revised use case forward to the code: the plan that revised it does, by filing the tasks that build it. Planning reads the use cases only when an intent is planned (DEC-054).

### What keeps the steps in step

| Link | What carries it | When it fires |
|---|---|---|
| An issue and the use cases it serves | its `## Use cases` section (DEC-054 point 4) | on reading, filing and editing, as a warning, on existence only |
| A use case and its actors, code and records | anchors (DEC-001 point 4, COR-050) | the change check, on every pull request |
| A journey and its use cases | anchors the stamp writes from its steps | the same |
| A page and what it describes | anchors (living-docs DEC-001 point 4) | the same |
| A pull request and every description it made stale | the change check's answers, listed in the pull request (COR-050 point 6, DEC-055) | before the merge |
| Code and the descriptions it still lacks | uncovered surface, where a project declares its surface (COR-050 point 8) | reported, never failed |
| The default branch and the debt nobody answered | the whole-repository check (COR-050 point 6) | on each push to main, and daily |
| A change and its release | a changeset (PRJ-002) | at the release |
| A record and what builds on it | citations, and the acceptance gate | `pkit refs validate`, and every author |

### The steps

Each step says what happens, what exists today and what is missing.

**1. Plan.** The person states the intent. The project manager agent walks the use cases first, and slices the intent into an EPIC and its tasks. It shows the plan at one approval gate (DEC-029, DEC-054). The critic reviews a plan of three issues or more, and the architect one that crosses three components or adds an abstraction.
- *Exists:* the walk, the citations, and both kinds of gap at the gate. A prerequisite task writes the use cases first, when none exists and the work touches what users do.
- *In project-kit today:* software-analysis fills the data point that carries the use cases to planning, and it holds none. So every plan that touches what users do offers the prerequisite task. The maintainer declined it, so those issues say they were planned without use cases (DEC-054 point 5).
- *Missing:* nothing in the machinery. The use cases themselves are EPIC #1643's.

**2. Say what the system must do.** Use cases, journeys and terms, and later quality requirements and constraints, written with the `analysis-author` skill and `pkit analysis new`. A planned revalidation record names the design it was reviewed against (DEC-001 point 6).
- *Exists:* the four kinds, the stamp, the number check, and the planned record with `reviewed-against`. The format check binds now: `SAN`'s format rule is accepted (`fceb363f`), and project-kit's rule set for its analysis, `ANA`, inherits it.
- *Missing:*
  - quality requirements and constraints, designed in PR #1646 for #1393 and waiting for the maintainer
  - a way for a reader to tell a use case of planned behaviour from one of built behaviour (G4)
  - the planned revalidation as a lifecycle, which DEC-001 point 11 leaves for later
  - a review of the analysis's content at the gate. The rule-set reviewer joins with #1420. Its judgement rules for the analysis landed with #1577 (`9bff1a6e`), proposed. They judge a use case's actor and goal, and whether anchors name what statements rest on. No gate asks the person to review an analysis change, though EPIC #1643 plans that he does.

**3. Decide how.** A question too big for one decision goes to a scratchpad note (COR-012). A choice becomes a decision record, reviewed by the critic, the architect and the methodology-reviewer (COR-024), then accepted. A use case anchors the architecture records it rests on. A view, where one exists, anchors the use cases it realises (the maintainer's decision of 10 October, #1447).
- *Exists:* notes, records, the acceptance gate, the reviewer stack, and a use case's anchor on a record.
- *Missing:* #1447's refinement of DEC-001, and any architecture view in project-kit. Nothing says who accepts a decision record (G2).

**4. Build and verify.** One task per pull request, built in an isolated worktree, with tests for what changes. The change check flags every description anchored to what changed. The change's author answers each one: updated, still true, or out of date until a named follow-up. A reviewer other than the author checks the answers (COR-050 point 3).
- *Exists:* all of it. In project-kit `docs-reviewer` checks the answers, and it is required on every classified pull request.
- *Missing:*
  - a requirement's *Verified by*, which is #1393's proposal and not yet decided
  - a signal from a tightened requirement to the test that verifies it (G5)
  - test results reaching a revalidation. The evidence point is defined, and nothing fills it in project-kit (DEC-001 point 7, G6).

**5. Explain.** Pages written with the `docs-author` skill, anchored to the code, the records and the analysis they rest on. They change in the same pull request as the code they describe (project-management DEC-015). Each fact has one home, and a summary elsewhere links and anchors to it (living-docs DEC-001 point 3).
- *Exists:* the spaces and their definitions, the stamp and the checks. `LDOC`, living-docs' shared rules for pages, binds through each space's definition. project-kit's pages are already anchored to code and records, and friction is enforcing.
- *Missing:* pages anchored to the analysis, since there is no analysis yet to anchor, and the rebuild of project-kit's documentation on it (EPIC #234).

**6. Merge.** `land-work` waits for CI, and has the required reviewers review the head in parallel (DEC-032). It prints the answers and each finding for a person, and stops ready (DEC-055). The person authorises one head. The merge goes through the queue where the base has one (DEC-026).
- *Exists:* all of it. project-kit requires `pm-reviewer` on every pull request, the code, security and docs reviewers on code, and `docs-reviewer` on every classified pull request.
- *Missing:* the rule-set reviewer at the gate (#1420). A trace of who authorised. The merge gate is a cross-authority gate (DEC-033 D2), and the engine checks that whoever merged is not the actor (COR-033 P4). But an agent passes `--yes` under the person's account, so the gate cannot tell on whose word (G12).

**7. Release.** Changesets become versions and a changelog, and declared floors rise (PRJ-002). A weekly workflow opens the release pull request, and a person merges it.
- *Exists:* all of it, the capability floor raised at `65b7604e` included.
- *Missing:* #1645, which keeps the self-host manifests in step. And where the person reads the segment, which PRJ-002 D2 makes a person's read (G8).

**8. Drift.** The whole-repository check runs on each push to main and daily, and keeps one tracking issue (`friction-report`). The `analysis-resolver` and the `living-docs` agent propose fixes, with the commands a person runs.
- *Exists:* the check, the tracking issue and both agents.
- *Missing:* anything that dispatches the agents on the report. A person or the project manager does it by hand (G7).

### Light where it can be

The maintainer asked on 17 October that the process not be bureaucratic where it need not be. Each step runs only when its trigger holds.

| Step | Its trigger |
|---|---|
| 1. Plan | an intent of more than one issue. A single issue is filed directly, with no reviewer (DEC-029) |
| 2. Say what the system must do | the change alters what someone using the software reaches (DEC-054 point 5's test). Internal work skips it |
| 3. Decide how | a choice no accepted record settles. A note only for a question too large for one record (COR-012) |
| 4. Build and verify | code changes |
| 5. Explain | a page's anchor changes, or new surface no page describes (COR-050 point 8) |
| 6. Merge | every change |
| 7. Release | a surface change, declared by a changeset (PRJ-002) |
| 8. Drift | every push to main, and daily |

- **Who judges a trigger:** the orchestrator proposes each issue's steps at the plan's gate, and the person corrects them there. DEC-054 point 5 already works so for "touches what users do". Showing the steps at the gate refines what DEC-029's gate holds (G15).
- **A fix** that restores described behaviour takes steps 4 and 6. Each use case it flags still holds, so its answer is `unchanged`, with no record (DEC-001 points 5 and 6).
- **A change inside one use case** revises the use case in the code's pull request. That is a stale analysis updated, with no record (DEC-001 points 5 and 6). This drops "analysis first" on purpose: one use case is reviewed best beside its code.
- **A record alone** takes steps 3 and 6. **A page alone** takes steps 5 and 6.
- **A wide, shallow change,** such as renaming a command, takes steps 4, 5 and 6. It answers every use case and page it flags, and needs no note unless the rename is itself a question.
- **What the records already spare:** a routine revalidation writes no record (DEC-001 point 6). The critic skips questions and single-file edits (COR-024). Friction is dormant until used (COR-050 point 15). `LDOC` creates nothing ahead of its need.
- **Requirements without records:** the maintainer said on 17 October that a requirement need not rest on a decision record. #1393's proposal matches: a requirement rests on the record that decides it, else on the page that states it, else it is its own home.

### What the sketch gets right, and what it gets wrong

The sketch's eight steps, its known gaps and its account of the session hold, with these corrections.

| The sketch says | What the records and the code say |
|---|---|
| Each later artefact anchors what it rests on | Each artefact anchors what makes it true. Code and tests are no artefacts and anchor nothing, so a changed use case flags no code |
| Planning walks the use cases, and exists | It does, over an empty set: every plan touching users so far was planned without use cases |
| The format check holds the analysis's structure | True since `SAN`'s format rule was accepted (`fceb363f`), through `ANA` |
| The maintainer reviews the analysis change | No gate asks for it. It is EPIC #1643's plan |
| Quality requirements and constraints, with `pkit analysis new` | Not yet: #1393 is designed, not decided |
| A planned record says the analysis was revised ahead of the code | The record exists. Its lifecycle does not, and nothing tells a reader which use cases are not built yet |
| Views anchor the requirements they satisfy, and requirements anchor the decisions behind them | #1393's proposal. Decided so far: a view anchors the use cases it realises, and a use case anchors the records it rests on (#1447) |
| A test is what a requirement's *Verified by* names | #1393's proposal, not decided |
| The analysis-resolver proposes the outcome | Only when someone dispatches it. A builder answers its own change's flags, and asks a person when stale versus regressed is unclear |
| project-kit's pages are not built this way yet | They are anchored and checked already. They are not built on an analysis |
| The maintainer authorises the merge | The records say so: DEC-006, DEC-055 point 3, and the pm skill's landing step. This session merged on a standing delegation instead |
| Merged on the maintainer's standing delegations | The project manager's own instructions refuse standing authorisations across sessions, and the delegation of 11 October was used for a week |
| Drift exists | The check and its issue exist. Dispatching the agents is by hand |

## 2. Compared with established processes

Each process below was defined before capable AI agents. Each block says what the flow keeps from it, what it lacks and who it assumed decides. It ends with what the process leaves implicit once an agent does the work.

### RUP and the Unified Process

- **Keeps:** use cases drive the work, and each traces into the design that realises it, its use-case realisation. Non-functional requirements sit beside the use-case model, in a supplementary specification. The flow keeps all three: use cases first, views that anchor them (#1447), and the requirement kinds (#1393).
- **Lacks:** a trace kept with the code. Requirement tools of the time marked a link suspect when either end changed, but the links lived in a separate tool. Code sat outside them, and clearing a suspect link was nobody's duty in the change that caused it. RUP also prescribed many artefacts whatever their use, and teams cut them.
- **Who decided:** people in roles: the system analyst, the architect, and a change control board for a baselined requirement.
- **Left implicit:** whose word changes a baselined requirement once an agent drafts both the change and its impact. A role says who does the work, not who answers for it.

### The V-model

- **Keeps:** each level of specification is paired with the test that verifies it, planned when the specification is written. A requirement's *Verified by*, in #1393's proposal, is that pairing.
- **Lacks:** a signal to the test when its requirement changes, within the change. A tool could mark the link suspect, but the test's author learnt of it later, if at all. The flow has the same hole today (G5). The V also assumes stable specifications, built in sequence.
- **Who decided:** different people on each side of the V, with verification independent of construction, and a sign-off at each level.
- **Left implicit:** independence. An agent that writes both the code and the test that verifies it folds both sides of the V into one author.

### Scrum and Kanban

- **Keeps:** one person orders the work, Scrum's product owner. A definition of done holds every increment. Policies are explicit, and work in progress is limited (Kanban). The flow keeps the person who decides what is built, each issue's criteria as its definition of done, and a limit on parallel builders.
- **Lacks:** any account of artefacts beyond the backlog and the increment. Documentation and traceability are left to the team.
- **Who decided:** the product owner decides what is built, and the developers decide how (Scrum Guide 2020). In Kanban the members of the system agree its policies together.
- **Left implicit:** how much of the how an agent may decide. Some choices of how bind later work, such as a new abstraction or a dependency, and Scrum never needed to set them apart. Kanban's limit on work in progress becomes the person's capacity to decide, not the builders' capacity to build.

### Shape Up

- **Keeps:** a problem is shaped before anyone builds it, with its appetite, its rough solution, its rabbit holes and its no-gos. A betting table decides. The team then has full autonomy inside the shape, and a circuit breaker stops work that overruns its cycle. The flow keeps the design note before the build, the person's decision, autonomy inside a scope, and the stop when a round outgrows its issue.
- **Lacks:** any artefact that outlives the cycle. The pitch is dropped once built, and nothing is kept true.
- **Who decided:** senior people at the betting table decide what is built. The team decides how, inside the shape.
- **Left implicit:** where the shape's edge lies. A team judges it in conversation. An agent needs it written, and needs to stop at it.

### TDD and BDD

- **Keeps:** the test before the code, and scenarios in the domain's words that run as tests, which BDD calls living documentation. The flow keeps the test in the change, and names executable use cases for later (DEC-001 point 11). A result can inform a revalidation through the evidence point (DEC-001 point 7).
- **Lacks:** the why. A test says what must hold, never why. A scenario that stops running drifts like any page.
- **Who decided:** the developer who writes the test. In BDD the business, development and testing agree each scenario together.
- **Left implicit:** what a red test means: the code is wrong, or the test is. An agent can make a test pass by changing what it expects. That is the twin of rewriting the analysis to match broken code, which DEC-001 point 5 forbids.

### DevOps and continuous delivery

- **Keeps:** every change through one automated pipeline, in small batches, with everything in version control. A release is a decision. The flow keeps CI as a required status, the merge queue, one task per pull request, and a release pull request a person merges.
- **Lacks:** a check on the descriptions. The pipeline checks the code. Friction extends it to what describes the code.
- **Who decided:** the pipeline decides what may be released. A person decides to release under continuous delivery, and nobody does under continuous deployment. Owners of the pipeline's files, named by the repository, approve changes to it.
- **Left implicit:** who acts when the owner's account is the agent's too. Code owners and branch protection check an account, and in this session the agents acted under the person's account (G12).

### Docs-as-code, with arc42 and C4

- **Keeps:** documentation in the repository, reviewed in the same pull requests as the code. arc42's quality requirements, glossary and decisions, and its context view naming who uses the system. C4's levels of view. The flow keeps the spaces, the glossary, the requirement kinds, the records, and a context view naming actors by id (#1447).
- **Lacks:** anything that finds a page made false. Docs-as-code puts the page next to the code, but readers still find the drift. arc42 is a template, not a way to keep one true.
- **Who decided:** the architect writes, and the pull request's reviewers approve.
- **Left implicit:** whose job it is to ask whether a page still holds after a change. Nobody's in particular. Friction makes it the change's author's, checked by a reviewer.

### The ADR practice

- **Keeps:** each decision recorded with its context and consequences, a status, and a successor in place of a silent edit (Nygard, 2011). The flow keeps records, statuses, supersession and the acceptance gate. It refines a record in place where Nygard would supersede it, through points whose ids never change (COR-058).
- **Lacks:** a link from a decision to what builds on it, so a superseded decision leaves its dependants unaware. Anchors give descriptions that link, but not code.
- **Who decided:** the team, or its architects. Nygard's status says accepted, never by whom. MADR adds the deciders.
- **Left implicit:** who accepts, when an agent writes the record. In project-kit an agent drafts records, and the architect agent keeps the ADRs (COR-025). An `accepted` an agent wrote looks the same as one the person decided.

### Three lessons

1. **Authority came with the role. With an agent in the role, it must be granted.** Every process named roles and assumed a person in each. An agent can do a role's work, but it cannot answer for it. So each authority an agent holds is written down, scoped and revocable. The nearest models sit outside software processes: a delegation-of-authority matrix, separation of duties, the four-eyes rule, and scoped, revocable tokens.
2. **The trace becomes part of the change.** The old tools marked a link suspect, in a store apart from the code, and left it for someone to clear. The flow checks the trace in the repository, in the same pull request. It holds the merge until each flag is answered, and keeps the answer in the artefact. It covers pages and the analysis as well as requirements. The trace still stops at the code and the tests (G5).
3. **Independence and the person's attention become the constraint.** Independent verification assumed different people. With agents it is designed: another agent, another remit, and evidence instead of the producer's account. Agents on one model can still share a blind spot, so the person's judgement samples them (G14). Building gets cheap, and the person's decisions become the bottleneck. On 30 September a pull request drew eight to twelve reviewer runs (`2026-09-30-review-load-and-friction-prs`). So the flow spends the person's attention only where no rule decides.

## 3. The autonomous version

### Who acts

- **A person** decides what is built, makes every judgement that no rule settles, accepts records and rules, and authorises merges and releases. In project-kit the maintainer is that person.
- **The orchestrator,** the project manager agent, plans, files, dispatches the builders and lands their work (DEC-029). In this session it built nothing, though DEC-008 lets it do an implementer's work.
- **Producing agents** make the work. A builder works in an isolated worktree: the `software-engineer` agent, or a session given a brief. An author works through a paired skill: `analysis-author`, `docs-author`, `decision-author` or `scratchpad-author`. The architect writes the ADRs (COR-025).
- **Proposing agents** never apply what they propose. The `analysis-resolver` and the `living-docs` agent return answers with the commands a person runs (DEC-001 point 5, living-docs DEC-001 point 5).
- **Reviewing agents** judge, and write nothing on what they judge. The critic, the architect, the methodology-reviewer and the convention-compliance reviewer form the stack (COR-024), with the rule-set reviewer beside the last (COR-057). The reviewers the merge gate requires hold the merge (DEC-028, DEC-032).

### This session as evidence

This session ran the flow with agents, and its practice is the first evidence for the rules below.

- **Standing delegations.** The maintainer let the project manager run an agreed build order without asking, accept a record that only restates his decision, and merge through `land-work`. Each acceptance names the delegation in its commit: 33 commits on main since 12 October read "Accepted under the maintainer's delegation of 11 October". The grant itself, its scope and its end are written nowhere.
- **Stop rules.** A builder stopped and reported when a review round outgrew its issue, after the architect's first recommendation. It stopped on a choice no record or decision settled, on signing that failed twice, and before a destructive operation (core rule 8).
- **Reviewer stacks.** Each builder ran the critic, the architect and the methodology, code, convention, rule-set and docs reviewers as each fitted. A fix round carried the blocking findings only (the pm skill's review step).
- **Chains of tasks.** A builder given dependent tasks built the next only once the last had merged.
- **Signed commits.** Each commit was signed with the maintainer's key, and its trailers named the agent's session.
- **One decision at a time.** The maintainer was asked one question per turn, in plain words (core rule 17), with a recommendation.

Some of this practice lives only in the project manager's briefs. That is the chains, the retry-once rule, the stop when a round outgrows its issue, signing, and the recommendation. They are over two hundred files in the agent workspace, which no commit carries and nobody reviews (G3).

### The rules for every step

Each rule names in brackets what holds it, in one of three ways.
- **A record:** an id, such as (DEC-006). It changes only through the acceptance gate.
- **A shipped skill or agent:** its name, such as (the pm skill). It holds the rule, but changes without passing the acceptance gate.
- **Nothing yet:** marked *candidate*, with the gap that would make it one.

1. **A producer never judges its own work.** A gate passes on a check, or on an act of an authority other than the actor it gates (COR-033 P4). The merge gate is such a gate: the engine checks that whoever merged is not the actor (DEC-033 D2). A reviewer other than the agent checks the answers its change wrote (COR-050 point 3). The verdicts enforce this only on the remote path, where a reviewer has an account of its own. On the local path, the one project-kit runs, author exclusion is relaxed and the developer attests the verdict, an honour system (DEC-028). Under one shared account the rule is discipline, and its check is a *candidate* (G12).
2. **A gate reads evidence, never the producer's account.** The answers' reviewer works from the change check's own list (COR-050 point 3). The capability writes that list into the pull request, every word the check's but the author's sentence on each updated document (DEC-055 point 1). A verdict counts only with its marker, while it stands for the head (DEC-028). A delegated agent's result reaches its dispatcher whole (COR-047, `delegated-result-complete`).
3. **A judgement no rule settles goes to a person, and one a rule settles does not.** A reviewer's passage for a person withholds no approval, and waits for the person (COR-057 point 3, the `[person]` tag of DEC-028). Stale versus regressed, when unclear, is a person's call (DEC-001 point 5). A design fork the conventions do not settle is surfaced, never buried (the `software-engineer` agent).
4. **An agent that cannot tell stops, and never reads silence as a pass.** A resolver that gives no answer leaves its artefact unjudged (COR-050 point 2). A reviewer that cannot judge does not approve (COR-057 point 3). Output with no verdict line posts no verdict (DEC-028). Use cases that cannot be read are reported as not checked, never as unknown (DEC-054 point 3). A step that fails again after one retry stops, as signing did (*candidate*, G3).
5. **The person is asked one decision at a time, in plain words** (core rules 17 and 18). A recommendation with each question is practice only (*candidate*, G3).
6. **A person hands over the work, never a decision, and the decisions can come together.** An agent may do all the work of a plan, up to each decision. Each decision is the person's, shown with what the person must be told. The list is closed, and the steps and the never-alone list below use the same one:
   1. scheduling an issue, closing one as won't-do, and closing a parent (DEC-006)
   2. what the system must do: a new or changed goal, guarantee or requirement (*candidate*, G13)
   3. accepting a record or a rule. COR-051 point 4 holds it for a rule an agent drafted, where the path involves a person. For a record, and for a refinement of an accepted rule, it is a *candidate* (G2).
   4. merging into the default branch, authorised for one head (DEC-006, DEC-055 point 3). The person is first told what changed and what is left out of date (COR-050 point 3). Merging the release pull request.
   5. a finding for a person, and stale versus regressed when unclear (DEC-028, DEC-001 point 5)
   6. an answer a change was not asked for, and a reason for having no anchors (COR-050 points 1 and 3)
   7. freeing an id, and confirming candidates drawn from a brownfield project (software-analysis DEC-001 points 3 and 9)
   8. bypassing a gate, with the reason on record (DEC-026, DEC-050). Whose reason it may be is a *candidate* (G1).
   9. a destructive operation, and a change to another repository (core rules 8 and 19, COR-039)

   Several decisions may be put to the person in one message, each still for one head or one record. That batch is a *candidate* (G1).
7. **Build on what has landed, or on the integration branch the plan names.** Work depends only on accepted records (the acceptance gate). A builder never builds on another builder's unmerged branch, as this session's chains did (*candidate*, G3). An integration branch is the plan's, reviewed as it is assembled (DEC-013).
8. **An agent leaves its own bindings alone.** Within its own change, it never changes what binds it. That is its body, its brief, its permission grants, and the settings of a gate it must pass (*candidate*, G3 and G10).

### Step by step

For each step: who acts, what each decides alone, what makes it stop and ask, and what the hand-off carries and who checks it. A last line says what part of the step a person may hand over.

**1. Plan**
- **Acts:** the person states the intent. The orchestrator plans. The critic, and for a wide plan the architect, review the slicing (DEC-029).
- **Decides alone:** the orchestrator decides the slicing, the order, the dependencies, each issue's classification and the use cases it serves. It starts work and asks for review (DEC-006). The reviewers decide their findings, which the gate shows (DEC-029).
- **Stops and asks:** at the one approval gate, before it files (DEC-029). On the prerequisite task when no use case exists and the work touches what users do (DEC-054 point 5). Scheduling an issue is the person's commitment, given per issue and in the session (DEC-006).
- **Hands on:** the plan, with its use-case mapping, both kinds of gap and each issue's steps, checked by the person. Each body is validated as it is filed (DEC-010).
- **May be handed over:** the work of the approved plan, issue by issue. The plan is the grant. The orchestrator schedules every planned issue at the gate, in the session, with the approval as its audited reason (`promote-issue --reason`, DEC-026). Scheduling one later "under the plan" would be the standing authorisation DEC-006 forbids.

**2. Say what the system must do**
- **Acts:** an author agent with the `analysis-author` skill, the checks, the rule-set reviewer once it is at the gate (#1420), and the person.
- **Decides alone:** the author decides the wording, the parts within the format rule, the anchors, the numbers, and the outcomes it proposes in a planned record. A reviewer decides its findings under the rules that bind (COR-057).
- **Stops and asks:** on a goal, a guarantee or a requirement that no person's statement, record or existing behaviour gives (*candidate*, G13). On candidates drawn from a brownfield project, which a person confirms (DEC-001 point 9). On freeing an id, which the project declares and no tool infers (DEC-001 point 3).
- **Hands on:** the analysis change and its planned record, naming the design it was reviewed against (DEC-001 point 6). Checked by `pkit analysis validate`, `check-numbers` and `check-pointers`, the reviewers and the person.
- **May be handed over:** the drafting. What the system must do is the person's decision. Today it has no gesture of its own. The person decides it by authorising the analysis change's merge, which the batch marks as such (G1, G13).

**3. Decide how**
- **Acts:** an author agent with the `scratchpad-author` or `decision-author` skill. The critic, then the architect, then the methodology-reviewer (COR-024). The person.
- **Decides alone:** the author decides the drafting, the alternatives and the recommendation, and starts a note, which decides nothing (COR-012). The reviewers decide their findings, advisory (COR-024).
- **Stops and asks:** on every choice the accepted records do not settle. On acceptance, which is the person's (rule 6, item 3). On a round that outgrows its issue, after the architect's first recommendation (*candidate*, G3).
- **Hands on:** the note or the record, with each reviewer's finding answered in it. Checked by the reviewers, `pkit decisions validate` and the person.
- **May be handed over:** the drafting and the reviews. Never the acceptance.

**4. Build and verify**
- **Acts:** a builder in an isolated worktree, CI, the reviewers the gate requires (DEC-032), and the answers' reviewer.
- **Decides alone:** the builder decides the code within the conventions and the records, and the tests. It writes the answers its own change owes, each deferral naming an open follow-up (COR-050 point 3). It proposes the changeset's segment, which the person reads at the release (G8). Each reviewer decides its verdict within its remit (DEC-028).
- **Stops and asks:** on a design fork nothing settles (the `software-engineer` agent). On stale versus regressed, when unclear (DEC-001 point 5). On an answer its change was not asked for (COR-050 point 3). On a test whose expectation the change must weaken (*candidate*, G9). Before a destructive operation (core rule 8).
- **Hands on:** a draft pull request with signed commits, the changeset and the tests. The check's list of answers, with a sentence for each updated document. Each finding, fixed or left with why. Checked by CI, the required reviewers and the answers' reviewer (DEC-055 point 3).
- **May be handed over:** all of it.

**5. Explain**
- **Acts:** an author agent with the `docs-author` skill. `docs-reviewer`, for what a change left undocumented (DEC-015). The rule-set reviewer on pages (#1420). The `living-docs` agent, for a reader-review.
- **Decides alone:** the author decides the page within `LDOC` and its space's rules, its anchors, and the answers its change owes. A statement its anchors do not ground it anchors or cuts (living-docs DEC-001 point 5). The reviewers decide their findings.
- **Stops and asks:** on an ungrounded statement it can neither anchor nor cut, which it raises with a person (living-docs DEC-001 point 5). On where an existing document belongs during onboarding, which a person reviews (living-docs DEC-001 point 8).
- **Hands on:** the page change and the `## Doc impact` section, in the code's pull request. Checked by validation, `docs-reviewer` and the rule-set reviewer.
- **May be handed over:** all of it.

**6. Merge**
- **Acts:** the orchestrator runs `land-work`, and the person authorises.
- **Decides alone:** waiting, re-running a reviewer whose verdict went stale, and a signed merge of main into the branch. The revalidation of a combined state after a conflict (COR-050 point 3).
- **Stops and asks:** before every merge, which is authorised for one head (DEC-006, `--yes --expect-head`, the pm skill's landing step). An authorisation given before the findings for a person were shown does not cover them (the pm skill). The landing command holds a run whose findings it did not find when it started (DEC-055 point 3). Each firm stop of DEC-055 point 3. Any bypass of a gate (rule 6, item 8).
- **Hands on:** the `ready:` line with the head, CI, the verdicts, the answers and the findings to judge. Checked by the person.
- **May be handed over:** everything up to the `ready:` line. The authorisation stays the person's, though several can be given at once (G1). For a chain, the merge of each link into the plan's integration branch could be handed over too. The final merge into main stays the person's (G1).

**7. Release**
- **Acts:** the release workflow and `pkit release`, then the person.
- **Decides alone:** nothing new. The release is computed from the changesets, whose segments the builders proposed in step 4 (PRJ-002).
- **Stops and asks:** always. The workflow never merges the release pull request. The person reads each segment there, which keeps it a person's read (PRJ-002 D2, G8).
- **Hands on:** the release pull request, with its versions and its changelog. Checked by `pkit release check` and the person.
- **May be handed over:** opening it. Never merging it.

**8. Drift**
- **Acts:** the whole-repository check, the `analysis-resolver`, the `living-docs` agent and the person.
- **Decides alone:** the proposals.
- **Stops and asks:** always. An answer that no change of the agent's own owes is the person's. It is shown word for word before it is written (COR-050 point 3, the agents README's "Friction writers").
- **Hands on:** the tracking issue, then each proposal with its evidence and its commands. Checked by the person.
- **May be handed over:** finding and proposing. Never the answer.

### Delegation: how a person hands authority over and takes it back

**What the records say.**
- The person holds both ends of the issue lifecycle: scheduling the work, and merging it. Authorisations are given per issue and in the session, and "no standing 'go ahead with everything' applies in a later turn" (DEC-006).
- The authorisation to merge is the person's, not the review approval an agent may give (DEC-055 point 3). DEC-008 says the approval signal itself comes from a human other than the agent. That predates the agent approver of DEC-028, and is out of step with it.
- The landing step runs `--yes` only on the user's authorisation, for that head (the pm skill). The project manager's own instructions refuse standing authorisations across sessions.
- A person's review accepts a rule an agent drafted (COR-051 point 4).

**What this session did.** The delegations under "This session as evidence" were given in conversation, carried into briefs, and used across sessions for a week. Merges ran under them, against all four statements above on merging. So did refinements of accepted rules: `28f7314b` (#1596) and `17c3e0f4` (#1634) refined `LDOC`'s rules under the delegation. Whether refining an accepted rule counts as accepting it, COR-051 point 4 does not settle (G2). Two whole sets went to the maintainer instead. He accepted `SAN`'s rules himself (`fceb363f`), and items of the `WRITE` draft (`43981938`).

**What can be handed over, recommended** (*candidate*, G1):
- **The work, granted in writing.** The approved plan is the grant (DEC-029's gate). It names the issues, so it scopes the work. Each planned issue is scheduled at the gate, in the session (step 1).
- **Passed down by issue.** A builder the orchestrator dispatches holds the work of its own issue, and nothing of the person's decisions.
- **Ended in writing, where it was granted.** A stop point in the plan, or the person's word written on the EPIC, so the next session reads it. A word said only in conversation is lost with the session.
- **Decisions, batched, never delegated.** The orchestrator brings the ready heads together, each with its findings for a person, its answers and its sentences. It marks each head that carries a decision of substance: an analysis change, a record's status, a change to a gate. The person authorises them in one message, one head each. That meets DEC-006, DEC-055 and COR-050 point 3 as they stand.
- **What a batch cannot do.** A head that moves, or meets a firm stop of DEC-055 point 3, drops out and returns in the next batch. And a chain still waits for each link's merge before the next link starts (rule 7).
- **A chain through the plan's integration branch.** Agents merge each link of a chain into the integration branch the plan names (DEC-013). The person authorises the final merge into main, told every answer of the whole branch. COR-050 point 3 asks the telling only before a merge into the default branch, so this weakens nothing core holds. It refines project-management. DEC-006 gives a merge into an integration branch the same path to Done as one into main, the person's authorisation included. DEC-055 point 3 makes every merge authorisation the person's.
- **An acceptance before the work that depends on it.** The acceptance gate asks that a record is accepted before work depends on it (the decision-record README). So an acceptance cannot be given by authorising the merge of a change that already builds on it. Two shapes fit:
  - a pull request for each acceptance, which the person authorises
  - acceptances the person gives in conversation, batched before the dependent work starts. The status change's commit names on whose word it was made.

  The landing command can then list each status a change flips, as it lists friction's settings (DEC-055 point 1). That listing checks the acceptance was given. It is not the acceptance.

**The alternative: a delegation of decisions, recorded** (*candidate*, G1). If the maintainer wants merges into main without him, records change in two namespaces, and the gate must check the grant.
- **In project-management,** it overturns three passages. They are DEC-006's row for Review to Done, its sentence on per-issue authorisations in the session, and DEC-055 point 3's "the authorisation is the person's". A record that does so partly supersedes them, in COR-060's form: a section saying what it overturns and what stands. DEC-008's paragraph on the approval signal is refined first, and DEC-006's amendment blocks are folded into its text, as the refinement rules ask.
- **In core,** a digest after the merge in place of the telling before it changes COR-050 point 3. A project-management record cannot supersede a core one, so that takes a core decision.
- **The grant is an artefact the gate reads,** so an authorisation leaves a trace of an authority other than the agent's (COR-033 P4). That needs G12 first. Under one shared account, the engine's check that the merger is not the actor tells nothing (DEC-033 D2).
- **Under a grant the landing command still stops** on every finding for a person and every bypass. It stops on every change to the analysis, a record's status or a gate. Those stay the person's.
- **The log is not the journal.** project-kit keeps its journal per clone and uncommitted (`.pkit/project/config.yaml`), and it records moves, not acceptances. The commit bodies hold the acceptances already.

### What an agent never does alone

- **Take any decision on rule 6's list,** each with what holds it there. Among them are accepting a record or a rule, and merging into main without the person's authorisation for that head. So are bypassing a gate on a reason of its own, and inventing what the system must do.
- **Rewrite the analysis or a test to match broken code** (DEC-001 point 5 for the analysis, and a *candidate* for a test, G9).
- **Apply a documentation fix nobody reviewed** (living-docs DEC-001 point 5).
- **Rewrite history** (core rule 8). The permission baseline denies destructive file operations, rewrites of history and escalation of privilege (the privilege catalog, ADR-002). This session's builders never rewrote a branch at all, which is stricter than the force-push policy (DEC-013).
- **Go around the permission model** (core rules 14 and 15), or switch off signing, which is practice only (*candidate*, G3).
- **Change what binds it, within its own change** (rule 8). A change may still leave a file out of a rule's scope to pass, in view of its reviewers (COR-060 point 2). Changes to friction's settings are shown to the person (DEC-055 point 1), and the rest of a gate's settings is a *candidate* (G10).

## 4. The gaps, each a candidate issue

Each names what is missing, where it would go, and what it adds to the person's load. They are ordered by what it costs to leave them.

- **G1. Decisions ran on standing delegations no record holds.** Recommended: the plan grants the work, scheduled at the gate in the session. The orchestrator batches the decisions for the person, one head or one record each, marking the decisions of substance. A chain merges into the plan's integration branch, and the person authorises the merge into main. A bypass's reason is the person's. The batch needs the pm skill, and perhaps a verb. The integration-branch path refines DEC-006 and DEC-055 point 3. The alternative is a recorded, gate-checked delegation of decisions. It partly supersedes DEC-006 and DEC-055 point 3, needs a core decision on COR-050 point 3, and needs G2 first. (project-management. Load: less than today's per-pull-request asks.)
- **G2. Attribution and acceptance are one core question.** G12 is its mechanism.
  - **Acceptance:** who accepts a decision record is unwritten. The decision-record README asks that "everyone look at the record and agree". A rule has it: a person's review accepts it, where the path involves a person (COR-051 point 4). project-kit's own analysis asks it for records too, in the merge authoriser's fourth need. Nothing says whether refining an accepted rule or record counts as accepting it.
  - **Attribution:** a gate cannot tell who acted (G12).
  - **One core record could hold both.** Every act is attributed to the authority that took it. An acceptance needs an authority other than the author: where the path involves a person, that person's review. That carries COR-033 P4 from process transitions to the acceptance gates, and refines COR-051 point 4 without superseding it. DEC-028 already names decision-record acceptance as the second instance that would move its pattern to core.
  - **Its realisations:** project-management's gate reads the identity and lists the acceptances. The adapter and the permission capability give agents credentials of their own. A project record names project-kit's person, the maintainer.

  (core, then project-management, the adapter and the permission capability. Load: one decision per acceptance, which the person makes today in name.)
- **G3. Some stop rules live only in uncommitted briefs.** Over two hundred briefs repeat them, which meets the recurrence test (COR-007). Each has a home of its own, by what kind of thing it is (COR-006):
  - never editing one's own instructions or settings, and never switching off signing: deny rules in the permission profiles (COR-028). These then become guarantees, not discipline.
  - retrying once then stopping, and a recommendation with each question: conduct for any agent, in the core rules
  - building only on merged work, and stopping when a round outgrows its issue: procedures in the pm skill, beside batch planning and landing
  - signing itself: a project-kit policy, in a PRJ record or the project rules

  (core, project-management, the permission capability, project-kit. Load: none.)
- **G4. Nothing tells a reader which use cases are not built yet.** This note takes the option with no new state. A use case ahead of its code anchors its actor and its records, with no error. It says what is wanted, so its missing code is a gap. A planned record names that gap, and the task that fills it (DEC-001 points 5 and 6). Two things stay missing. A reader of the use case cannot see that it is planned. And nothing makes the building change add the code anchor, beyond uncovered surface where a surface is declared. A `planned` state would be the lifecycle DEC-001 point 11 leaves to a decision of its own. It would also have to map onto the use-case point's `active` and `withdrawn` (DEC-054 point 1). (software-analysis. Load: none.)
- **G5. A tightened requirement signals no test.** In #1393's proposal a requirement anchors the test that verifies it. So an edit of the test already flags the requirement. A change to the requirement flags the use cases that list it, never that test. A test can hold no answer, so this is no friction (the principle above). Recommended: a rule of `SAN` on requirements, shipped with #1393. A change to a requirement's statement revisits each test its *Verified by* names, or says why the test still verifies it. The rule-set reviewer judges it, reading the requirement's anchors (COR-057 point 1). A check can be declared as the rule's checkable part, listing the anchored tests (COR-051 point 2). Core moves only when a second kind needs a forward obligation (COR-007). (software-analysis, with #1393's build. Load: none, the change's author answers it.)
- **G6. Test results reach no revalidation.** The evidence point is defined, and nothing fills it in project-kit. A filler from CI's test results. (project-kit, or a later testing capability. Load: none.)
- **G7. Nothing dispatches the drift agents.** The tracking issue waits for a person. The resolver for a place could be declared beside that place (COR-050 point 1), so a dispatcher finds it without naming any capability. The note `2026-07-02-agent-dispatch-privilege-model` governs which agent may start it. Its proposals go to the person through G11's view. (core and project-management. Load: the same answers, gathered.)
- **G8. The segment is a person's read, and the agents proposed it.** PRJ-002 D2 decides who reads it, so rewording it would supersede D2. Kept instead: the change's author proposes the segment, and the person reads it on merging the release pull request (step 7). That is a refinement of PRJ-002. (project-kit. Load: a read of the changelog the person merges anyway.)
- **G9. A test's expectation can change unseen, where no requirement names the test.** A test a requirement anchors flags the requirement when it changes (G5). For the rest, a change that alters what a test expects says so. A reviewer checks it against the analysis, read through a data point. (software-engineering's code review. Load: none, a reviewer checks it.)
- **G10. Only friction's settings are shown as a change to the gate.** Each component could declare which of its settings bear on a gate. Project-management then shows a change to any of them, as it shows friction's settings (DEC-055 point 1). That covers the workflows, the required reviewers, the rule scopes and the permission profiles. A scope that leaves a file out (COR-060 point 2) is one such change. (project-management, with each owner's declaration. Load: a line, on the rare change that alters a gate.)
- **G11. What waits on the person is scattered.** A plan at its gate, a head ready to merge, a finding to judge, a proposal, a record to accept. One view of them, each with its question and a recommendation. Other components fill a data point of what waits on a person, and project-management reads it, as it reads the use cases (DEC-054). It stays outside the process engine, which never lists its subjects (COR-032). It is the first real case of the view across processes that the substrate leaves for later. Decide it after G1 and G2, which say what waits on the person, and before G7. (project-management. Load: less, one place instead of several.)
- **G12. Nothing tells an act of the person from an agent's.** Commits are signed with the person's key. Local verdicts post under the person's account (DEC-028). An agent passes `--yes`. So the merge gate's cross-authority check cannot tell the person from the agent (DEC-033 D2, COR-033 P4), and code owners would not help. Agents acting under an account of their own, as DEC-028's remote path has, would leave the person's account to the person's acts. It stays optional: where agents have no identity, DEC-028's honour system holds. It is the mechanism of G2. (project-management, the adapter, the permission capability. Load: none.)
- **G13. Analysis first lets an agent invent what the system must do.** It is the riskiest act in the flow, since everything after builds on it. Each new or changed goal, guarantee and requirement names its source, as a rule's origin does (COR-051 point 5). The source is when it was decided, by whom and why, in the decider's words. Or it is a cited record, or existing behaviour. The planned record's `reviewed-against` already names the design. The person's decision on it has no gesture of its own: it is the authorisation of the analysis change's merge, which G1's batch marks. (software-analysis's skill, and perhaps a rule in `SAN`. Load: the person reviews the analysis change, as EPIC #1643 plans.)
- **G14. Reviewers share the builder's model, and were measured once.** COR-057 point 8 asks for evidence before a reviewer gates, and names no bar. The rule-set reviewer's trial is the one measure so far: the maintainer judged 23 of 27 blocks right, then 15 of 16 (`2026-10-15-rule-set-reviewer-trial`). A periodic sample of each gating reviewer's blocks, judged by the person, would show a drift in their accuracy. Which reviewers gate is project-management's choice (DEC-032), so the sample starts there or in a PRJ record. (project-management or project-kit. Load: a sample, now and then.)
- **G15. The plan's gate shows no steps per issue.** "Light where it can be" has the orchestrator propose each issue's steps at the gate, and the person correct them. That adds to what DEC-029's gate holds. (project-management. Load: one column in a plan the person reads anyway.)

Already filed, and part of the flow:
- #1393, requirements, and #1447, the analysis and the architecture
- #1420, the rule-set reviewer at the gate. #1577 gave it judgement rules for the analysis, proposed, which the maintainer accepts or not.
- #1645, the release's manifests
- EPIC #1643, project-kit's analysis, and EPIC #234, its documentation

The note `2026-07-02-agent-dispatch-privilege-model` holds which agent may start which.

## 5. The first journey: deliver a feature

EPIC #1643 writes project-kit's own analysis. This flow becomes its first journey once the areas are settled and #1393's kinds exist.

- **Actor:** the developer, who directs agents to make each change (ACT-developer). The merge authoriser and the AI agent take part.
- **Goal:** deliver a feature from intent to release, with every description still true.
- **Steps:** one per step of the flow, each a use case of the area that owns it. These are candidates, settled with the areas:
  1. plan an intent into issues against the use cases (project management)
  2. revise the analysis ahead of a change (analysis)
  3. think a question through, and record the decision (decisions and notes)
  4. build a change, and answer what it made stale (friction)
  5. write a page anchored to what makes it true (documentation)
  6. land a change on one authorised head (landing)
  7. release the components from their changesets (release)
  8. resolve drift the whole-repository check found (friction)
- **Seams:** the hand-offs of part 3, where the path can break. A use case is cited before it settled. A use case describes unbuilt behaviour. The list of answers is for another head than the merged one. A changeset is missing.
- **Variant:** the autonomous path. An agent takes each step, and the journey stops at the person exactly where part 3 says.

Two things follow for the analysis.
- **The never-alone list becomes assumptions, and a few guarantees.** Most items are discipline: nothing at run time stops an agent from breaking them (the agents README, "Friction writers"). So each is an assumption of a use case, naming the record that admits it (DEC-001 point 1). The few the system secures are minimal guarantees. "Land a change" guarantees that no head merges but the one authorised (`--expect-head`), and no list of answers but the merged head's (DEC-055 point 3). The permission baseline's denies are guarantees too. G3 would move more items there, and G12 would make the merge gate's check of who acted one.
- **Some requirements rest on no record.** "The person is asked one decision at a time" rests on a core rule, and "a chain waits for each merge" on practice alone. As the maintainer said on 17 October, such a requirement arises beside the records. It is its own home until a record decides it (#1393's proposal, point 5).

The journey waits for #1393, as the maintainer ordered on 17 October: the capability first, then project-kit's analysis. Its actors, use cases and steps could be drafted with today's kinds, and only its requirements wait. That would reverse his order, so it is not recommended.

## For the maintainer

One choice per line, the recommendation first, in the order they depend on each other. They went to the maintainer one at a time. His answer of 17 October is under each.

1. **Attribution and acceptance (G2, G12):** one core record, each act attributed to its taker, an acceptance needing someone other than its author — or both left unwritten.
   - **Answered:** accepting a record or a rule is always the person's act. Agents prepare it, the project manager brings edits in batches, and the commit records whose word it was and when. The identity part, G12, waits.
2. **Delegation (G1):** the plan grants the work, decisions come batched, chains merge into the plan's integration branch — or a gate-checked delegation of decisions, needing choice 1.
   - **Answered:** merges into main are his, in batches, each for the exact head he saw. A chain's links merge into the plan's integration branch without him, and the final merge into main is his. A written delegation the gate checks is looked at again once agents have identities of their own.
3. **How an acceptance reaches you (G2):** given in conversation before the work that depends on it, then listed at the landing as a check — or a pull request for each.
   - **Answered:** settled by choice 1. Acceptances come in batches, in conversation, before the work that depends on them.
4. **The stop rules (G3):** each to its home among the permission profiles, the core rules, the pm skill and a PRJ record — or two agents' bodies — or briefs.
   - **Answered:** each moves to its home. Never editing one's own instructions or settings, and never switching off signing, become deny rules in the permission profiles. Retrying once then stopping, and a recommendation with each question, go into the core rules. Building only on merged work, and stopping when a round outgrows its issue, go into the pm skill. Signing every commit goes into project-kit's project rules or a PRJ record.
5. **Where a big feature's analysis lands (G4):** first on main, with a planned record naming each gap's task — or with the code, losing the plan's citations — or on an integration branch.
   - **Answered:** first on main, with a planned record naming each gap's task. A marker a reader can see on a planned use case comes later.
6. **Sources of what the system must do (G13):** each names its source as a rule's origin does, in the skill — or also as a rule in `SAN`.
   - **Answered:** a judgement rule of `SAN`. Every new or changed goal, guarantee or requirement names its source, in any form: an anchored record, a *Rationale* or *Imposed by*, existing behaviour anchored to code, or a quoted decision with who made it and when. It is proposed beside RS-SAN-003 to 005 and a rule that a requirement contradicting the record it rests on breaks. All are accepted together, in the major of `SAN` that ships them. The `analysis-author` skill says the same.
7. **From requirement to test (G5):** a rule of `SAN` with a declared check, shipped with #1393 — or a new signal in the core change check.
   - **Answered:** settled in the requirements discussion below. #1659 rides on the general mechanism of #1667.
8. **Test evidence (G6):** CI's test results fill the evidence point in project-kit — or later.
   - **Answered:** later, as a task under EPIC #1643, once the first requirements carry *Verified by*.
9. **What waits on you (G11):** a data point other components fill, read by one project-management view — or not yet.
   - **Answered:** one project-management view, starting with ready merges and records awaiting acceptance. Other kinds come later.
10. **Drift (G7):** each place's resolver declared beside it and dispatched, its proposals in choice 9's view — or by hand, as now.
    - **Answered:** each kind of place declares its fixer, and the drift check dispatches it. Its proposals land in choice 9's view. It is built after the view, and after project-kit has its analysis and pages.
11. **The segment (G8):** the author proposes, and you read it at the release, refining PRJ-002 — or D2 superseded.
    - **Answered:** the agent proposes the segment with a one-line reason. The merge batch shows it, and he may change it there. The release changelog is the last read. This refines PRJ-002 D2.
12. **The first journey:** "deliver a feature" under EPIC #1643, after #1393 — or drafted now without its requirements.
    - **Answered:** settled. "Deliver a feature" is written under EPIC #1643 after #1393, as the worked example.

G9, G10, G14 and G15 need no choice of direction. Each is filed as a task if the maintainer agrees. They wait for his word, and none is filed yet.

**Also decided in the requirements discussion of 17 October (#1393):**
- **The direction of links is fixed.** The analysis points at the solution, never the reverse. This replaces the drivers on records: no record or view anchors an analysis artefact (#1447).
- **A general core mechanism, #1667,** lets a kind of link declare that a change to its source revisits the targets it names.
- **G5 rides on it,** through #1659.

**Filed from it:** EPIC #1673, with #1674 to #1680, #1682 and #1684 under it. #1681 under #1547. #1683 and #1685 under #1643. And #1667 and #1659.

## Review

### The critic

Four red flags, all fixed.

- **R1. Rule 1 cited DEC-028 for an author exclusion its local path relaxes.** Fixed. Rule 1 now says the gate enforces the exclusion only on the remote path. The local path, project-kit's, is an honour system, and its check is G12.
- **R2. The never-alone list let an agent accept a restatement, against COR-051 point 4 and the merge authoriser's need.** Fixed. An agent never accepts a record or a rule. The delegation section names the two rule refinements accepted under the delegation, and the two sets the maintainer accepted himself.
- **R3. "Delegate an act whose judgement is made" hid a judgement in both its examples, and misread DEC-055 point 3.** Fixed. Rule 6 is now "hand over the work, never a decision", with the decisions batched. A standing delegation of decisions is the alternative, with what it would need. DEC-055 point 3 and the pm skill are each cited for what each says.
- **R4. Lesson 2 said no earlier process flagged a changed link, but requirement tools marked links suspect.** Fixed. The RUP and V-model blocks name suspect links, and lesson 2 says what differs.

The gaps it found, each answered:
- **More evidence on the standing merge, and supersession:** the project manager's instructions and DEC-008 are cited. The alternative says it partly supersedes DEC-006.
- **The delegation's edge cases:** an end is written where the grant is. Work passes down by issue. Bypassing a gate and editing one's own instructions join the never-alone list. Inventing what the system must do is G13.
- **Who acted cannot be checked:** G12. The journal is no longer offered as the log, since it is kept per clone and holds moves only.
- **The three weights fitted only chosen cases:** replaced by each step's trigger, judged at the plan's gate. A fix's flagged use cases still hold, with no record.
- **G4 overstated:** rewritten. A use case ahead of its code anchors its actor and records with no error. Uncovered surface joins the table.
- **G11 against the engine:** G11 is a project-management view, outside the engine.
- **G5's place:** a new signal, not friction. The architect then moved it from core to software-analysis (A4).
- **The overlap with #1393:** G5 and G9 say a test a requirement anchors already flags the requirement.
- **The brief's sub-points per step:** each step gives the reviewers' decisions and what may be handed over. Step 7 names the segment.
- **One model for all agents:** lesson 3 and G14.
- **The person's attention:** each gap names what it adds to the person's load.
- **Integration branches:** rule 7 names the plan's integration branch.

Its weaker points, all taken:
- what lives only in briefs is narrowed, and the acceptances are shown in the commit bodies
- the guardrails cite the privilege catalog and ADR-002, not COR-028
- COR-060 point 2 is a case G10 must face, not a defence
- rule 4 drops COR-047, and the stack cites COR-024, the queue DEC-026, the orchestrator's building DEC-008
- living-docs DEC-001 point 5's stop is narrowed to raising a question
- what DEC-054 carries, and when its prerequisite task is offered, are stated
- the review-load figure is dated, and #1393's proposal is labelled each time
- G8 is a wording fix
- part 5's never-alone items are assumptions, with a few guarantees
- the comparison gives MADR's deciders, code owners and Kanban's members

Its counter-alternatives:
- **Batched authorisation:** taken as the recommendation.
- **A delegation the gate checks:** the alternative.
- **Acceptance in a pull request of its own:** an option of choice 2.
- **Prior art for lesson 1:** added.
- **G4 with no new state:** taken.
- **The journey now, with today's kinds:** offered and not recommended, since the maintainer ordered the capability first.

One point answered without a change. The critic saw a tension between analysis first and `LDOC`'s "nothing ahead of its need". A use case written before its code serves a feature already planned, so its need has come. The rule is about pages, too.

Readability: `LDOC` and the use-case point are explained, dense paragraphs split, and the choices ordered by what depends on what. They go to the maintainer one at a time.

A confirmation round found all four red flags fixed, with no new one.

### The architect

The architect edited nothing. It found four concerns that need the maintainer's authorisation, four of fit, three of drift, and agreed with the rest. Each is answered in the note.

Concerns for the maintainer:
- **A1. Batching does not help a chain.** Each link of a chain waits for the person's authorisation before the next starts. A head that moves, or meets a firm stop, drops out of a batch. Answered: the delegation section says what a batch cannot do. It adds the third path the architect proposed: a chain merges into the plan's integration branch, and the person authorises the merge into main. COR-050 point 3 asks the telling only there, so only project-management records change.
- **A2. Showing an acceptance at the landing conflicts with the acceptance gate.** Work that depends on a record is written after its acceptance, so a merge cannot be the acceptance of a record the change builds on. Answered: two shapes fit, a pull request per acceptance, or acceptances given in conversation before the dependent work. A listing at the landing only checks them. Choice 3.
- **A3. The alternative to G1 reaches into core.** A digest after the merge changes COR-050 point 3, which a project-management record cannot supersede. In project-management it overturns more than one sentence of DEC-006, and needs COR-060's form. A grant the gate checks needs G12 first. Answered in the alternative, in G1 and in choice 2.
- **A4. G5 belongs in software-analysis.** A test can hold no answer, so a signal to it is no friction. A rule of `SAN` on requirements, judged by the rule-set reviewer with a declared check, needs no change to core. Answered: G5 and choice 7. The principle now says friction lands only where an answer can be held.

Fit:
- **A5. G1, G2 and G12 are one concern.** DEC-028 already names decision-record acceptance as the second instance that would move its pattern to core. Answered: G2 is now attribution and acceptance, one core question, with G12 its mechanism. It keeps COR-051 point 4's condition, where the path involves a person. It asks whether refining an accepted rule or record counts as accepting it. Choices 1 and 3.
- **A6. G3's rules have several homes, not two agent bodies.** Answered: G3 sorts each rule by what kind of thing it is (COR-006). Rule 8 and part 5 note that permission denies make guarantees of what is discipline now.
- **A7. G7, G10 and G11 would have project-management read other components' state.** Answered: G11 reads a data point others fill, G7 finds resolvers declared beside their places, and G10 reads each owner's declaration. G11 comes before G7.
- **A8. G14 belongs in project-management or a PRJ record, and cited the wrong source.** Answered in G14.

Drift:
- **A9. "The principle, corrected" named the wrong property.** Any artefact may carry anchors, records and rules included. Answered: the principle now says only artefacts carry anchors, and code and tests are not artefacts.
- **A10. Several citations.** Answered:
  - rule 1 cites DEC-033 D2
  - rule 2 says the author writes a sentence per updated document, and that a verdict counts while it stands for the head
  - rules held by a shipped skill or agent are marked apart from those a record holds
  - rule 6's list of decisions is closed, and the steps and the never-alone list use it
  - deciding what the system must do has its gesture named in G13
  - the plan's grant schedules each issue at the gate, in the session, as DEC-006 asks
  - showing each issue's steps at the gate is G15
  - the bypass's owner is in G1
- **A11. DEC-008's paragraph and DEC-006's amendment blocks are out of step.** Answered: the delegation section names both, for any record that builds on them.

Its placement table changed G5, G7, G8, G11, G12 and G14 as above. G8 is no wording fix: PRJ-002 D2 stays, and the person reads the segment at the release. Its escalation flags are the alternative to G1, G2 with G12, G5 if kept in core, and G8 if D2 were changed. Each is a choice above.
