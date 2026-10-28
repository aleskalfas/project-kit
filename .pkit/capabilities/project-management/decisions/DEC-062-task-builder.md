---
id: DEC-062
title: A fresh builder agent builds each of a worker's Tasks, and the seat keeps every write
status: proposed
date: 2026-10-28
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** in a project with a topology of seats, a worker no longer builds a Task in its own session. It runs the capability's **build command**, which starts a **fresh builder agent** for that one Task. The builder runs in a new process, in a clone of its own, inside the operating system's sandbox. It sees only a brief that the command writes from the Task itself, so no Task inherits the context of the one before it. It may do what the project allows, except what is the seat's to do: it writes nothing to the work tracker, pushes nothing and starts no agent, and its sandbox keeps it out of the seat's clone. When it is stuck or needs a decision, it stops and asks, whoever may answer answers, and the build resumes. The seat then checks the work, pushes it and opens the pull request, and the merge gate checks the reviews as before. Commits that no build produced are refused, which catches a seat that skipped the command.

## Context

A worker takes ready work and builds it up to its merge ([project-management:DEC-059-topology-of-seats] point 2). Built in the seat's own session, each Task carries the context of the ones before it into its build, and the session grows from Task to Task. On 28 October the maintainer decided that each Task starts clean (#2259).

An instruction in the work loop to start a fresh helper agent does not make it so:
- nothing makes the seat start one;
- a harness may start a helper that inherits the whole conversation, such as a forked agent;
- the seat writes the helper's brief from its own context, so that context reaches the helper anyway;
- a harness with no helper of its own sends the seat back to building in its session.

The maintainer asked for a mechanism instead. The backbone already starts an agent in a fresh process, through the runner the project's adapter registers ([pkit:ADR-066] point 1). Probes on 28 October started the software-engineering capability's producer agent that way, in a clone of its own, sandboxed, with nothing that could ask. It built a probe Task with one signed commit. It stopped with a question on a Task it could not build as written, and finished once given the answer. The sandbox refused its writes outside its clone, a program's it ran among them, and its reads of the seat's clone.

## Decision

**In a project with a topology, a worker builds each Task through the build command. The command writes the builder's brief from the Task, and starts a fresh builder agent through the backbone's runner, in a sandboxed clone of its own, under rules that leave the seat's writes to the seat. The builder ends its run with a result or a question. Questions go to whoever may answer them, and the build resumes. The seat checks the work, pushes it and opens the pull request. A commit no build produced is refused.**

### 1. The build command is the only way a worker's Task is built

- **Every build of a worker's Task goes through it:** the first build, with the Task In Progress, and each fix round on a reviewer's verdict and each merge that resolves a conflict with the default branch, with the Task In Progress or in Review. A build moves the Task to no other state.
- **Each build is recorded on the Task:** its start and end commits, the builder, its brief (point 3) and how the build ended.
- **Provenance is checked** at each step a worker's work moves on: the commands that open its pull request, move its Task to Review, ask for the reviews and merge refuse a Task branch that carries a commit, outside the default branch's own, that no recorded build produced. So a fix round built around the command is caught before its verdicts and its merge, as the first build is. The seat writes the records under the account every clone shares, so like the guard of [project-management:DEC-035-instance-ownership], the check catches a skipped command and is no security boundary.
- **Where no builder can start,** because no builder is named (point 2), no runner is registered (ADR-066 point 1), or the platform cannot host the sandbox (point 4), the command says why, and the loop ends. A person may direct that one Task be built in the seat's session. The provenance check then takes the person's audited override, with its reason ([project-management:DEC-046-override-flag-convention]), and the seat's working tree goes back to the default branch before its next build (point 7, "Brought back as the Task's branch"). No build in the session happens silently.
- **Leads, and projects with no topology,** build as before. A project with no topology may run the build command by hand, and its provenance is not checked. A lead's builds through the command are named, not built.

### 2. A project names its builder through a connection point

- **The point.** As the provider of the work-tracking role, this capability defines `<methodology>::work-tracking:builder`, whose value names the agent that builds a Task ([pkit:COR-053]). Its combination is `single`, and its inert policy is `fail`, so a point that does not resolve starts no builder.
- **No default here.** Building is a discipline another capability owns ([pkit:COR-026]). A capability that ships a producer agent contributes it, as software-engineering contributes its producer. A project may fill the point itself, naming any deployed agent. Two capabilities that fill it are an error until the project selects one ([pkit:COR-052] point 3).
- **The point's version covers the build contract:** the brief the command writes and the result and question the builder ends with (points 3 and 5). A change that breaks a builder which conforms raises the version, as the fixers' point does ([project-management:DEC-056-drift-fixers] point 1).
- **The whole contract travels in the brief.** A builder needs nothing from this capability's files to follow it, so the capability that contributes a builder does not come to depend on this one.

### 3. The brief is written from the Task, never from the seat's session

- **What it holds:** the contract, versioned with the point; the Task's title, body, acceptance criteria and documentation boxes, word for word; its parents, by reference; the records a foundation's Feature lists, where the Task rests on one ([project-management:DEC-060-foundation-before-slices]); its branch and the commit the build starts from.
- **What a later build adds:** for a fix round, the blocking findings of the verdicts, word for word; for a resumed build, the question and the answer (point 6).
- **The seat adds nothing of its own,** so nothing of the seat's context reaches the builder through the brief.
- **Kept on the Task,** with the build's record, so every reader of the Task, a worker that takes it over among them, sees exactly what a builder was told.

### 4. The builder runs in a sandboxed clone of its own, under rules that leave the seat's writes to the seat

- **A new process,** started through the backbone's runner (ADR-066 point 1), so it carries no conversation but its brief.
- **A clone of its own,** of the seat's clone at the Task branch's head.
- **Inside the operating system's sandbox,** which holds everything the builder runs, the programs it writes among them. Nothing of the builder's run touches the seat's clone, its files or its key, and it reaches only the network hosts the project lets a build reach, for its toolchain, never the project's remote or its work tracker, by the hosts the adapter declares for them (the architecture record). Where the platform cannot host the sandbox, no builder starts (point 1).
- **Nothing asks.** A call no rule allows is refused, not asked, and no flag or mode that approves a call in a person's place is passed (ADR-066 point 4).
- **The run's rules come from the default branch,** never from the Task's branch, so no build can widen the rules a later build runs under. They allow what the project's permission rules allow, since a build needs the project's own toolchain. Above those allows they deny what is the seat's work:
  - writing to the work tracker
  - pushing, and every other write to a remote
  - starting an agent
  - every command of this capability that writes

  This capability declares them, scoped to the build command's runs, beside the drift command's ([project-management:DEC-056-drift-fixers] point 5). In the permission model they are denies, which prevail over every allow ([pkit:COR-028] point 1). The adapter realises them for that run only, on a mechanism that fails closed, and the permission overview shows them.
- **The builder acts as no instance.** It writes nothing as the seat, and no command of this capability acts as an instance inside an *agent run*, a run the backbone's run command starts (ADR-066 point 8).
- **What stays open is stated** ([pkit:COR-028] point 3):
  - The builder reaches the network hosts its build is allowed. What it reads, it can send there, and the sandbox's list of hosts stops only a well-behaved request (ADR-066 point 11). Where the platform gives every process its credentials for such a host, a program the builder runs acts there as the account the clones share.
  - The project's instructions to the harness are read from the clone, earlier builds' changes among them. They shape the work, and grant no permission.
  - The person's own instructions to the harness reach the run, as they reach every run.
  - The rest of the machine stays readable to the builder, other seats' clones on the same machine among them.
  - The reviewers run unconfined in the seat's clone ([pkit:ADR-066] point 10). One that runs the change's code runs a build's commits outside a sandbox, until a record confines the reviewers' runs.

### 5. The builder ends its run with a result or a question

- **It never guesses** a decision that is not its own, and never works around a refused call.
- **A result** says whether the Task is built, and names its commits, the checks it ran and how each ended, the criteria it meets, a sentence on each document it revalidated as updated, any follow-up to file, and what it left undone.
- **A question** names its kind (point 6), asks one question, and says what the builder found, the options with what each means, the option it recommends, and its work so far.
- **The command says what the builder did not.** It reads each run's ending mechanically. A call the run's rules refused, a run past its limit, and a clone that does not bear the result out each become a question or a failure of their own, with no word of the builder's needed.

### 6. A question goes to whoever may answer it, and the build resumes

| Kind | What it asks | Who answers |
|---|---|---|
| decision | the Task's scope, documented behaviour, a record, a shared choice | the person only ([project-management:DEC-006-state-machine-and-cascade]) |
| permission | a call the project's rules refused that the build needs | the person only: once for that build, recorded, or by a lasting grant through a reviewed change. A call one of the build's own denies (point 4) refused is never granted, since it is the seat's work: it becomes a decision, about the Task's scope |
| advice | which of two ways to build fits | an advising agent the project names, which the command starts confined, on the brief and the question alone, whose answer the person accepts; else the person |
| environment | a missing tool, a broken checkout, a time limit | the person, or whoever runs the platform |

- **Never the seat from its own context.** That would carry the seat's context into the build, which this record keeps out.
- **The question waits on the Task.** The command posts it on the Task, so the seat never writes the builder's question. The seat tells the person, and ends the loop. A later session's first step finds the open question before it takes any other work.
- **A waiting build holds the claim.** While a build waits on a question, or on its hand-back (point 7), the Task stays in its state, In Progress or, for a fix round, Review, and claimed. Like a Task in Review, it waits on others, not on its owner, so its claim does not lapse while it waits. A Task in Review keeps its claim anyway, so this adds a rule only for a Task In Progress (refinement of DEC-059 point 9). A build that ended unfinished with no question, or was not borne out, a lost one among them once its ending is posted, does not wait, and its Task's claim lapses as any other's. A release of the seat, by its clone or by force, still frees it (DEC-059 point 5).
- **The build resumes** in the builder's own session where the harness keeps it, so the builder goes on with its own context of the Task. Where it does not, a fresh builder starts with the brief, the question and the answer. The question and its answer stay recorded together.
- **Bounds.** A run that reached its limit is never started again on its own. A Task stops for the person once it has asked as many questions as the command allows.
- **Only the person's answer counts.** Where every clone works under one account, an answer's author on the Task does not prove who wrote it. Like the guard of DEC-035, this catches mistakes and is no security boundary.

### 7. A build's commits run only in a sandbox until a person reviews them, and only the seat pushes them

- **Checked in the sandbox.** Once the builder's run ends, the command runs the project's checks itself, in the builder's clone and its sandbox, and reads how each ended. So no criterion rests on the builder's word alone, and the checks run the build's code nowhere else.
- **Brought back as the Task's branch, never into the seat's working tree.** Once the run's clone and the checks bear out its result (point 5), and the seat still holds the Task's claim, the command brings back only commits, signed by the command where the project signs, so the builder never holds the key. The seat's working tree stays on the default branch, so the seat's own tools, settings, hooks and instructions are always code a person reviewed. A build whose commits cannot be signed yet waits on its hand-back, its work kept.
- **Then the seat.** It ticks the criteria the checks bear out, files the follow-ups for the person to schedule, checks its seat before the push (DEC-059 point 9), and pushes the Task's branch. Its push runs no hook that would run the build's commits, and the project's continuous integration runs the checks again. The seat's push is the only push to the project's remote. It then opens the pull request as before.
- **The claim while a build runs.** The build command's work is the seat's work, so once a Task's claim is renewed by its work (DEC-059 point 9), the command renews it while the build runs, and stops when the run ends.

### 8. The seat asks for the reviews, and the merge gate checks them

- **The builder starts no reviewer** (point 4).
- **The seat asks for the verdicts** once the checks on its pushed head pass. A verdict that asks for changes starts a fix round through the build command (point 1).
- **The merge gate** keeps its check of the reviews, and gains the provenance check (point 1). It refuses the merge until every required reviewer has a verdict that stands for the head, or the person overrides that reviewer with an audited reason ([project-management:DEC-028-agent-as-approver-paths], [project-management:DEC-050-per-reviewer-override]). The person authorises the merge.

### What this changes, and what stands

- **DEC-059, refined in place:** point 2, a worker builds each Task through the build command; point 6, a builder acts as no instance, and no command of this capability acts as one inside an agent run; point 9, a Task whose build waits on a question or on its hand-back keeps its claim; its Implications, which name the worker's loop. The rest of DEC-059 stands.
- **DEC-029, refined in place:** the worker's loop in the pm skill builds through the build command and acts on its endings. The project-manager agent stays a thin dispatcher.
- **Stands:** the merge gate's check of the reviews, to which the merge adds the provenance check (point 8), and the person's authorisation of each merge; a lead's helpers, which act as the lead's instance (DEC-059 point 6); DEC-056's fixers and their confinement.

## Rationale

**Why a mechanism, not an instruction.** An instruction leaves the clean start to the agent that would lose it. A seat that skips the helper, a forked helper, and a brief written from the seat's memory each defeat it, and none of them shows. A new process with a brief written from the Task cannot carry the seat's conversation, and the provenance check shows a build that went around the command.

**Why through the runner.** The backbone already has one way for a command to start an agent, and its adapter holds the tie to the harness ([pkit:ADR-066] point 1). The build command takes the same way, so it works on every harness whose adapter registers a runner, and calls no harness itself.

**Why a clone of its own, in the sandbox.** A builder in the seat's clone could read the seat's workspace, which holds the seat's notes. It could write a hook or a configuration that the seat's next push runs as the seat. A clone of its own keeps its own files apart, and the sandbox keeps it, and every program it runs, out of the seat's. Rules that see only commands cannot do that: a probe's program wrote outside the clone until the sandbox was on.

**Why the seat never runs a build's commits.** A build's code that the seat ran, in a check, a push's hook, or its own tools from a working tree that holds the build, would run with the seat's access and credentials, outside the sandbox that holds the builder. In a project that builds its own tooling, the seat's next command would run the build. Kept in the sandbox and in continuous integration until a person reviews them, a build's commits reach nothing the sandbox keeps from the builder.

**Why the default branch's rules.** Earlier builds' commits sit on the Task's branch, and nobody has reviewed them yet. Rules read from there would let one build widen the next one's. Read from the default branch, they are the rules a person reviewed and merged, as no unmerged change shapes a run nobody watches (ADR-066 point 3).

**Why the project's allows, with the seat's writes denied.** A build needs the project's toolchain, which differs from project to project, so a closed list like the drift command's would refuse what a build needs. What only the seat may do, writing to the tracker, pushing and starting agents, is denied above every allow. Everything else the project allows stays, so a refusal mostly marks a step the project's rules do not yet cover, which an interactive session would have asked about.

**Why stop and resume, not ask during the run.** Nobody watches the run. A tool that answers the harness's prompts would answer in a person's place, which ADR-066 point 4 rules out, and it stalls where nobody is there. Ending the run with a question keeps the builder's work, and resuming keeps its context of the Task. A probe showed both.

**Why the person answers decisions and permissions.** A role never stands in for a person's authorisation (DEC-059 point 8), and a permission the run's rules refused is one. Advice changes no rule, so an advising agent may give it, on the brief and the question alone. The seat may not, since its answer would carry its context into the build.

**Why a waiting build holds the claim.** The work so far sits in the builder's clone and session, which another clone cannot take over. A claim that lapsed would hand the Task to a worker that starts again, and lose both.

**Why a connection point.** The side that needs a builder declares the point ([pkit:COR-053]). Installing a capability that ships a producer agent then makes the build command work with no configuration, and the point's version keeps a builder on the contract it follows.

**Why no build in the session by default.** A build in the seat's session gives up the clean start. Where it happens with nobody choosing it, the loss does not show. A person's audited direction makes it show.

### Alternatives considered

- **An instruction in the work loop to start a fresh helper.** Rejected, for the reasons in the Context.
- **A fresh session of the seat for each Task.** Not taken. The new session reads the Task itself, so it needs no brief, but a session is started by the platform, not by a command. It may be combined with this record later.
- **The builder in the seat's clone, as the reviewers run.** Rejected: it reads the seat's workspace, and can write what the seat's push runs.
- **A clone of its own with no sandbox.** Rejected: a probe's program wrote outside the clone.
- **ADR-066's confined form.** Not available for a build: it allows no edit and no network.
- **A tool that relays the harness's prompts to a person.** Rejected: it answers in a person's place (ADR-066 point 4), and stalls where nobody is there.
- **A configuration key, or a builder named by each seat.** Not taken now. A key carries no versioned contract. A seat's own builder, such as a test agent for a seat scoped to tests, may refine point 2 later.
- **The seat answering advice.** Rejected: its answer carries its context into the build.

## Implications

- **An architecture record** decides how the build command realises points 1 to 8: the builder's clone, its sandbox and its hand-back, the run's settings and its mode, the endings and their exits, the detached run the seat waits on, the resume, the records of builds and the provenance check. It refines ADR-066.
- **A seat's working tree stays on the default branch:** in a project with a topology, the commands that start a worker's Task cut its branch without checking it out.
- **Renewal ships no later than lapse,** so no build's claim lapses while it runs (DEC-059 point 9).
- **This capability gains** the build command; the checks a project names for a build, in its configuration; the point and its companion schema; the run's rules; the provenance check in the commands that open a pull request, move a Task to Review, ask for the reviews and merge; the refusal to act as an instance inside an agent run; the worker's loop in the pm skill; its README's sections on seats and their loops.
- **software-engineering** contributes its producer agent to the point.
- **The backbone's run command and the adapter's runner** gain what the architecture record needs, each declared by its own changeset (PRJ-002).
- **A harness requirement** joins the requirement set for the run the architecture record decides ([pkit:COR-047]).
- **The analysis** gains the worker's build, its question and its answer, in the use cases of parallel work.
- **Acceptance:** this record refines the accepted DEC-059 and DEC-029 in place, so accepting it needs the maintainer's sign-off. It, the refinements and the architecture record land in one change, accepted together.
- **Named, not built:** a lead's builds through the command; a seat's own builder; a seat taking other work while a question waits.
