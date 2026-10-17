---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-17
---

# A big feature through project-kit, ready for autonomous agents

The design round of #1648. A big feature should move through project-kit from its assignment to its release, with every artefact kept in step. Agents should do most of the work. This note sets out that flow, compares it with established processes, and writes the version an autonomous agent can follow.

- **Read from main at `65b7604e`:** the records, the guides and the code cited below.
- **Starts from:** the project manager's sketch of 17 October, and this session's practice. Every claim of the sketch was checked. "What the sketch gets right, and what it gets wrong" lists the corrections.
- **Governed by:** the anchors and friction record (COR-050), software-analysis DEC-001, living-docs DEC-001, and project-management's records on planning, the gate and landing (DEC-006, DEC-026, DEC-028, DEC-032, DEC-054, DEC-055).
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Decided:** nothing yet. No record changes here. The choices are in "For the maintainer".

## The question

How does a big feature move from an assigned intent to a release and then stay true, each artefact resting on those before it? Which parts of that may an agent do alone, and which must stop for a person? And how does a person hand authority to an agent and take it back?

## In short

**Write what the system must do first, then decide how, then build and verify, then explain.** Each description anchors what makes it true, so a change flags every description resting on it. Each pull request answers those flags before it merges.

**Agents do the work, and the person makes the decisions.** A person hands an agent the work of a plan, never a decision. The decisions stay one at a time, each for one pull request or one record, but an agent can bring the person several together.

- **The flow:** eight steps, from planning to drift. Most of the machinery exists. The gaps are in the analysis, in the trace from a requirement to its test, and in who may decide what.
- **The comparison:** every established process put people in its roles, and the authority came with the role. Each kept its trace apart from the code. Each left independence and attention to people.
- **The autonomous version:** a producer never judges its own work. A gate reads evidence, never the producer's account. An agent stops at every decision, at a judgement no rule settles, and before anything on the never-alone list.
- **The largest gap:** this session merged pull requests and accepted records on standing delegations that no record holds. DEC-006, the pm skill and the project manager's own instructions all ask for the person's authorisation of each merge. And today nothing can tell an act of the person from an agent's.
- **Light where it can be:** each step runs only when its trigger holds. A fix, a record or a page change skips most of them.

## 1. The reference flow

### The principle, corrected

The sketch says each later artefact anchors what it rests on, from use cases to requirements, decisions, code and docs. The anchors run another way.

- **A description anchors what makes it true.** A use case anchors the code it exercises and the records it relies on (software-analysis DEC-001 point 4). A page anchors code, records, analysis artefacts and the home of each fact it summarises (living-docs DEC-001 point 4).
- **What is described anchors nothing.** Code and tests carry no anchors. No decision record carries a friction block today, as the architect found on #1393 (PR #1646, "Beyond this issue").
- **So a change flags descriptions only.** Changed code flags the use cases and pages anchored to it. A changed decision flags whatever anchors it. A changed use case flags the journeys and pages anchored to it, and no code and no test.
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
  - a review of the analysis's content at the gate. The rule-set reviewer joins with #1420, and its judgement rules for the analysis come with #1577. No gate asks the person to review an analysis change, though EPIC #1643 plans that he does.

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
- *Missing:* the rule-set reviewer at the gate (#1420). A trace of who authorised: an agent passes `--yes`, and the gate cannot tell on whose word (G12).

**7. Release.** Changesets become versions and a changelog, and declared floors rise (PRJ-002). A weekly workflow opens the release pull request, and a person merges it.
- *Exists:* all of it, the capability floor raised at `65b7604e` included.
- *Missing:* #1645, which keeps the self-host manifests in step. And PRJ-002's wording of who reads the segment (G8).

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

- **Who judges a trigger:** the orchestrator proposes each issue's steps at the plan's gate, and the person corrects them there. DEC-054 point 5 already works so for "touches what users do".
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
| Each later artefact anchors what it rests on | Each description anchors what makes it true. Code, tests and, today, records anchor nothing, so a changed use case flags no code |
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

Each rule names in brackets the record that holds it. A rule no record holds yet is marked *candidate*, with the gap that would make it one.

1. **A producer never judges its own work.** A gate passes on a check, or on the act of an authority other than the actor it gates (COR-033 P4). A reviewer other than the agent checks the answers its change wrote (COR-050 point 3). The merge gate enforces this only on its remote path, where a reviewer has an account of its own. On the local path, the one project-kit runs, author exclusion is relaxed and the developer attests the verdict, an honour system (DEC-028). So here the rule is discipline, and the check of it is a *candidate* (G12).
2. **A gate reads evidence, never the producer's account.** The answers' reviewer works from the change check's own list (COR-050 point 3). The capability writes that list into the pull request, with no word an agent composed (DEC-055 point 1). A verdict counts only with its marker, for the head its reviewer reviewed (DEC-028). A delegated agent's result reaches its dispatcher whole (COR-047, `delegated-result-complete`).
3. **A judgement no rule settles goes to a person, and one a rule settles does not.** A reviewer's passage for a person withholds no approval, and waits for the person (COR-057 point 3, the `[person]` tag of DEC-028). A design fork the conventions do not settle is surfaced, never buried (the `software-engineer` agent). Stale versus regressed, when unclear, is a person's call (DEC-001 point 5).
4. **An agent that cannot tell stops, and never reads silence as a pass.** A resolver that gives no answer leaves its artefact unjudged (COR-050 point 2). A reviewer that cannot judge does not approve (COR-057 point 3). Output with no verdict line posts no verdict (DEC-028). Use cases that cannot be read are reported as not checked, never as unknown (DEC-054 point 3). A step that fails again after one retry stops, as signing did (*candidate*, G3).
5. **The person is asked one decision at a time, in plain words** (core rules 17 and 18). A recommendation with each question is practice only (*candidate*, G3).
6. **A person hands over the work, never a decision, and the decisions can come together.** An agent may do all the work of a plan, up to each decision. Each decision stays the person's, shown with what the person must be told:
   - a merge, authorised for one head. The person is first told what changed and what is left out of date (DEC-006, DEC-055 point 3, COR-050 point 3).
   - an acceptance: a person's review accepts a rule an agent drafted (COR-051 point 4), and the same for a record is a *candidate* (G2)
   - a finding for a person, and stale versus regressed when unclear (DEC-028, DEC-001 point 5)

   Several decisions may be put to the person in one message, each still for one head or one record. That batch is a *candidate* (G1).
7. **Build on what has landed, or on the integration branch the plan names.** Work depends only on accepted records (the acceptance gate). A builder never builds on another builder's unmerged branch, as this session's chains did (*candidate*, G3). An integration branch is the plan's, reviewed as it is assembled (DEC-013).

### Step by step

For each step: who acts, what each decides alone, what makes it stop and ask, and what the hand-off carries and who checks it. A last line says what part of the step a person may hand over.

**1. Plan**
- **Acts:** the person states the intent. The orchestrator plans. The critic, and for a wide plan the architect, review the slicing (DEC-029).
- **Decides alone:** the orchestrator decides the slicing, the order, the dependencies, each issue's classification and the use cases it serves. It starts work and asks for review (DEC-006). The reviewers decide their findings, which the gate shows (DEC-029).
- **Stops and asks:** at the one approval gate, before it files (DEC-029). On the prerequisite task when no use case exists and the work touches what users do (DEC-054 point 5). Scheduling an issue is the person's commitment (DEC-006).
- **Hands on:** the plan, with its use-case mapping, both kinds of gap and each issue's steps, checked by the person. Each body is validated as it is filed (DEC-010).
- **May be handed over:** the work of the approved plan, issue by issue. The plan is the grant.

**2. Say what the system must do**
- **Acts:** an author agent with the `analysis-author` skill, the checks, the rule-set reviewer once it is at the gate (#1420), and the person.
- **Decides alone:** the author decides the wording, the parts within the format rule, the anchors, the numbers, and the outcomes it proposes in a planned record. A reviewer decides its findings under the rules that bind (COR-057).
- **Stops and asks:** on a goal, a guarantee or a requirement that no person's statement, record or existing behaviour gives (*candidate*, G13). On candidates drawn from a brownfield project, which a person confirms (DEC-001 point 9). On freeing an id, which the project declares and no tool infers (DEC-001 point 3).
- **Hands on:** the analysis change and its planned record, naming the design it was reviewed against (DEC-001 point 6). Checked by `pkit analysis validate`, `check-numbers` and `check-pointers`, the reviewers and the person.
- **May be handed over:** the drafting. What the system must do is the person's decision.

**3. Decide how**
- **Acts:** an author agent with the `scratchpad-author` or `decision-author` skill. The critic, then the architect, then the methodology-reviewer (COR-024). The person.
- **Decides alone:** the author decides the drafting, the alternatives and the recommendation, and starts a note, which decides nothing (COR-012). The reviewers decide their findings, advisory (COR-024).
- **Stops and asks:** on every choice the accepted records do not settle. On acceptance, which is the person's (point 6 above). On a round that outgrows its issue, after the architect's first recommendation (*candidate*, G3).
- **Hands on:** the note or the record, with each reviewer's finding answered in it. Checked by the reviewers, `pkit decisions validate` and the person.
- **May be handed over:** the drafting and the reviews. Never the acceptance.

**4. Build and verify**
- **Acts:** a builder in an isolated worktree, CI, the reviewers the gate requires (DEC-032), and the answers' reviewer.
- **Decides alone:** the builder decides the code within the conventions and the records, and the tests. It writes the answers its own change owes, each deferral naming an open follow-up (COR-050 point 3). It declares the changeset and its segment (G8). Each reviewer decides its verdict within its remit (DEC-028).
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
- **Stops and asks:** before every merge, which is authorised for one head (DEC-006, `--yes --expect-head`, the pm skill's landing step). An authorisation given before the findings for a person were shown does not cover them (the pm skill). The landing command holds a run whose findings it did not find when it started (DEC-055 point 3). Each firm stop of DEC-055 point 3. Any bypass of a gate, whose reason is the person's (DEC-026, DEC-050).
- **Hands on:** the `ready:` line with the head, CI, the verdicts, the answers and the findings to judge. Checked by the person.
- **May be handed over:** everything up to the `ready:` line. The authorisation stays the person's, though several can be given at once (G1).

**7. Release**
- **Acts:** the release workflow and `pkit release`, then the person.
- **Decides alone:** nothing new. The release is computed from the changesets, whose segments the builders declared in step 4 (PRJ-002).
- **Stops and asks:** always. The workflow never merges the release pull request.
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
- The approval signal comes from a human other than the agent (DEC-008).
- The authorisation to merge is the person's, not the review approval an agent may give (DEC-055 point 3).
- The landing step runs `--yes` only on the user's authorisation, for that head (the pm skill). The project manager's own instructions refuse standing authorisations across sessions.
- A person's review accepts a rule an agent drafted (COR-051 point 4).

**What this session did.** The delegations under "This session as evidence" were given in conversation, carried into briefs, and used across sessions for a week. Merges ran under them, against all four of the first statements. So did refinements of accepted rules: `28f7314b` (#1596) and `17c3e0f4` (#1634) refined `LDOC`'s rules under the delegation, which sits against COR-051 point 4. Two whole sets went to the maintainer instead. He accepted `SAN`'s rules himself (`fceb363f`), and items of the `WRITE` draft (`43981938`).

**What can be handed over, recommended** (*candidate*, G1):
- **The work, granted in writing.** The approved plan is the grant (DEC-029's gate). It names the issues, so it scopes the work.
- **Passed down by issue.** A builder the orchestrator dispatches holds the work of its own issue, and nothing of the person's decisions.
- **Ended in writing, where it was granted.** A stop point in the plan, or the person's word written on the EPIC, so the next session reads it. A word said only in conversation is lost with the session.
- **Decisions, batched, never delegated.** The orchestrator brings the ready heads together, each with its findings for a person, its answers and its sentences. The person authorises them in one message, one head each. That meets DEC-006, DEC-055 and COR-050 point 3 as they stand, and needs no new record. It also removes most of the cost that led to the standing delegation.
- **An acceptance travels with what the person sees.** It has a pull request of its own. Or the landing command lists each status the change flips, beside the answers, as it lists friction's settings (DEC-055 point 1).

**The alternative: a delegation of decisions, recorded** (*candidate*, G1). If the maintainer wants merges without him, the record must change, and the gate must check the grant.
- It partly supersedes DEC-006's sentence on standing authorisations, as COR-060 partly superseded COR-057.
- The grant is an artefact the gate reads, so an authorisation leaves a trace of an authority other than the agent's (COR-033 P4).
- Under a grant the landing command stops on every finding for a person and every bypass. It stops on every change to the analysis, a record's status or a gate. Those stay the person's.
- The person is still told what each merge changed and left out of date. A digest after the merge, written where the grant is, would replace the telling before it, and that weakens COR-050 point 3.
- The journal cannot hold the log: project-kit keeps it per clone and uncommitted (`.pkit/project/config.yaml`), and it records moves, not acceptances. The commit bodies hold the acceptances already.

### What an agent never does alone

- **Accept a decision record or a rule.** COR-051 point 4 holds it for a rule, and it is a *candidate* for a record (G2).
- **Merge without the person's authorisation for that head** (DEC-006, DEC-055 point 3, the pm skill).
- **Bypass a gate,** with `--bypass` or `--bypass-reviewer`, on a reason of its own (DEC-026, DEC-050 record the reason, and its owner is a *candidate*, G1).
- **Write an answer its change was not asked for,** or a reason for having no anchors (COR-050 points 1 and 3, core rule 20).
- **Invent what the system must do.** A goal, a guarantee or a requirement comes from a person, a record or existing behaviour (*candidate*, G13).
- **Rewrite the analysis or a test to match broken code** (DEC-001 point 5 for the analysis, and a *candidate* for a test, G9).
- **Apply a documentation fix nobody reviewed** (living-docs DEC-001 point 5).
- **Run a destructive operation, or rewrite history** (core rule 8). The permission baseline denies destructive file operations, rewrites of history and escalation of privilege (the privilege catalog, ADR-002). This session's builders never rewrote a branch at all, which is stricter than the force-push policy (DEC-013).
- **Change another repository** (COR-039, core rule 19).
- **Go around the permission model** (core rules 14 and 15), or switch off signing, which is practice only (*candidate*, G3).
- **Change the instructions or settings that bind it** inside its own change. Those are its body, its brief and its permission grants (*candidate*, G3).
- **Change a gate to pass its own work.** Changes to friction's settings are shown to the person (DEC-055 point 1). Yet a change may leave a file out of a rule's scope to pass, in view of its reviewers (COR-060 point 2). The rest of a gate's settings is a *candidate* (G10).

## 4. The gaps, each a candidate issue

Each names what is missing, where it would go, and what it adds to the person's load. They are ordered by what it costs to leave them.

- **G1. Decisions ran on standing delegations no record holds.** Recommended: the plan grants the work, and the orchestrator batches the decisions for the person, one head or one record each. That needs no record, only the batch in the pm skill and perhaps a verb. The alternative is a recorded, gate-checked delegation, which partly supersedes DEC-006. (project-management. Load: less than today's per-pull-request asks.)
- **G2. Who accepts a decision record is unwritten.** The decision-record README asks that "everyone look at the record and agree". A rule has it: a person's review accepts it (COR-051 point 4). project-kit's own analysis already asks for it, in the merge authoriser's fourth need. Refine the acceptance gate: acceptance is the person's, and reaches the person as its own pull request or listed at the landing. (core, project-management. Load: one line per acceptance.)
- **G3. Some stop rules live only in uncommitted briefs.** The chains, the retry-once rule, the stop when a round outgrows its issue, signing, a recommendation with each question, and never editing one's own instructions. Over two hundred briefs repeat them, which meets the recurrence test (COR-007). Move them into the `project-manager` and `software-engineer` agents' bodies, or into a builder's skill. (project-management, software-engineering. Load: none.)
- **G4. Nothing tells a reader which use cases are not built yet.** A use case ahead of its code anchors its actor and its records, with no error. It says what is wanted, so its missing code is a gap. A planned record names that gap, and the task that fills it (DEC-001 points 5 and 6). Two things are missing. A reader of the use case cannot see that it is planned. And nothing makes the building change add the code anchor, beyond uncovered surface where a surface is declared. A `planned` status would have to map onto the use-case point's `active` and `withdrawn` (DEC-054 point 1). (software-analysis. Load: none.)
- **G5. A tightened requirement signals no test.** In #1393's proposal a requirement anchors the test that verifies it. So an edit of the test already flags the requirement. A change to the requirement flags the use cases that list it, never that test. The change check could also name the tests a changed requirement anchors. That is a new signal against the anchors' direction, not friction, and it is the core check's to give. (core, with #1393's build. Load: none, the change's author answers it.)
- **G6. Test results reach no revalidation.** The evidence point is defined, and nothing fills it in project-kit. A filler from CI's test results. (project-kit, or a later testing capability. Load: none.)
- **G7. Nothing dispatches the drift agents.** The tracking issue waits for a person. A routine that dispatches the `analysis-resolver` and the `living-docs` agent on each finding, and brings the person their proposals in one batch. (project-management. Load: the same answers, gathered.)
- **G8. PRJ-002 D2 calls the segment a person's read.** Its reason is against inferring the segment from the commit type, and an agent's judged read meets that. So it may be a wording fix: a judged read, by the change's author, checked by a reviewer. (project-kit. Load: none.)
- **G9. A test's expectation can change unseen, where no requirement names the test.** A test a requirement anchors is covered by G5's anchors. For the rest, a change that alters what a test expects says so, and a reviewer checks it against the analysis. (software-engineering's code review. Load: none, a reviewer checks it.)
- **G10. Only friction's settings are shown as a change to the gate.** Show every change to what gates a merge, as friction's settings are shown (DEC-055 point 1). That covers the workflows, the required reviewers, the rule scopes and the permission profiles. A scope that leaves a file out (COR-060 point 2) is one such change. (project-management. Load: a line, on the rare change that alters a gate.)
- **G11. What waits on the person is scattered.** A plan at its gate, a head ready to merge, a finding to judge, a proposal, a record to accept. One view of them, each with its question and a recommendation. It is a project-management view, outside the process engine, which never lists its subjects (COR-032). (project-management. Load: less, one place instead of several.)
- **G12. Nothing tells an act of the person from an agent's.** Commits are signed with the person's key. Local verdicts post under the person's account (DEC-028). An agent passes `--yes`. So a gate cannot confirm an authorisation came from another authority than the actor (COR-033 P4), and code owners would not help. Agents acting under an account of their own, as DEC-028's remote path has, would leave the person's account to the person's acts. (project-management, the adapter. Load: none.)
- **G13. Analysis first lets an agent invent what the system must do.** It is the riskiest act in the flow, since everything after builds on it. Each new or changed goal, guarantee and requirement names its source, a person's statement, a record or existing behaviour. The planned record's `reviewed-against` already names the design. (software-analysis's skill, and perhaps a rule in `SAN`. Load: the person reviews the analysis change, as EPIC #1643 plans.)
- **G14. Reviewers share the builder's model, and were measured once.** The rule-set reviewer's trial is the one measure: the maintainer judged 23 of 27 blocks right, then 15 of 16 (COR-057 point 8). A periodic sample of each gating reviewer's blocks, judged by the person, would show a drift in their accuracy. (core. Load: a sample, now and then.)

Already filed, and part of the flow:
- #1393, requirements, and #1447, the analysis and the architecture
- #1420, the rule-set reviewer at the gate, and #1577, its judgement rules for the analysis
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
- **The never-alone list becomes assumptions, and a few guarantees.** Most items are discipline: nothing at run time stops an agent from breaking them (the agents README, "Friction writers"). So each is an assumption of a use case, naming the record that admits it (DEC-001 point 1). The few the system secures are minimal guarantees. "Land a change" guarantees that no head merges but the one authorised (`--expect-head`), and no list of answers but the merged head's (DEC-055 point 3).
- **Some requirements rest on no record.** "The person is asked one decision at a time" rests on a core rule, and "a chain waits for each merge" on practice alone. As the maintainer said on 17 October, such a requirement arises beside the records. It is its own home until a record decides it (#1393's proposal, point 5).

The journey waits for #1393, as the maintainer ordered on 17 October: the capability first, then project-kit's analysis. Its actors, use cases and steps could be drafted with today's kinds, and only its requirements wait. That would reverse his order, so it is not recommended.

## For the maintainer

One choice per line, the recommendation first, in the order they depend on each other.

1. **Delegation (G1):** the plan grants the work, and decisions come to you batched — or a recorded, gate-checked delegation of decisions, partly superseding DEC-006.
2. **Acceptance (G2):** a person accepts a record too, each acceptance shown at the landing — or a pull request per acceptance — or left unwritten.
3. **Who acted (G12):** agents act under an account of their own — or under yours, as now.
4. **The stop rules (G3):** into the `project-manager` and `software-engineer` agents' bodies — or into a builder's skill — or left in briefs.
5. **Where a big feature's analysis lands (G4):** first, on main, its planned record naming each gap's task — or with the code, losing the plan's citations — or on an integration branch.
6. **Sources of what the system must do (G13):** each goal, guarantee and requirement names its source, in the skill — or also as a rule in `SAN`.
7. **From requirement to test (G5, G6):** with #1393's build, the core change check names the tests a changed requirement anchors, and CI fills the evidence point — or later.
8. **Drift (G7):** the project manager dispatches the drift agents and brings you their proposals in one batch — or by hand, as now.
9. **What waits on you (G11):** one project-management view of every wait — or not yet.
10. **The segment (G8):** PRJ-002 D2 reworded to a judged read, checked by a reviewer — or unchanged.
11. **The first journey:** "deliver a feature" under EPIC #1643, after #1393 — or drafted now without its requirements.

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
- **G5's place:** the core check's, and a new signal, not friction.
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
