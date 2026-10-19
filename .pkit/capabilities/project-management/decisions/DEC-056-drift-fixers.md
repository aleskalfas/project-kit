---
id: DEC-056
title: Only granted fixers start on stale artefacts, and they only propose
status: accepted
date: 2026-10-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the default branch leaves an artefact out of date, the agent that fixes artefacts of its type starts and proposes an answer, and the person decides it. A capability declares which of its agents fixes which of its types. A fixer starts on its own only where the project granted it, and only the person grants. A command of this capability, the drift command, starts the granted fixers, each bounded and confined as far as the harness allows. The person is asked a plain question about each fixer nobody was asked about: by the drift command, and by install and upgrade once the core lifecycle can ask. Commands list, grant and revoke. A fixer only proposes. It takes one brief and ends with one line for each artefact, by one contract that this capability sets for every fixer. Its proposals wait as files, the landing command says how many wait, and the person accepts, rewords or refuses each before anything is written.

## Context

The whole-repository check finds the artefacts that merges left out of date on the default branch. That debt is derived from git (COR-050 point 9), and the checks are read-only (COR-050 point 12). A capability that owns artefacts may ship an agent that proposes their answers. Nothing starts such an agent. The debt waits until a person reads the check and starts the right agent by hand. Nothing gathers what they propose either, and each such answer is the person's decision (COR-050 point 3).

Starting them on their own raises who may start which agent.
- **A fixer is an agent with a shell** that runs with nobody watching. A reviewer a capability contributes applies on install ([project-management:DEC-032-conditional-reviewer-requirements]), but a reviewer gates a change a person is making.
- **Its input is not trusted.** Commit messages and pull requests reach it, so a contributor's words could steer it.
- **The harness confines a run only in part.** It can deny tools and commands, and an operating-system sandbox can bound what a shell writes. Network egress has no boundary there, a gap the harness reports rather than closes (COR-028 point 3).

What one agent may start through the harness's own dispatch tool is a separate question, about the permission model. This record leaves it to its own decision, and covers only the agents a command of this capability starts.

## Decision

**A capability declares its fixers in a data point this capability accepts. The person grants each fixer, by answering a question or by command, and nothing is granted by default. A command of this capability starts the granted fixers on the default branch's stale artefacts, each bounded, confined and limited to proposing. The proposals wait as files until the person decides each one, and this capability applies what the person accepts through an ordinary change.**

### 1. A capability declares its fixers

As the provider of the work-tracking role, this capability accepts `<methodology>::work-tracking:fixers` (COR-053). Its value says which agent fixes the artefacts of each type.
- **Its entries are `{id, agent, description}`,** the shape of a companion schema named after the point, at version 1 (COR-052 point 5).
  - The `id` is an artefact type (COR-056 point 1). A capability's entry names a type of its own. A project's entry may name any type, its own bare types included.
  - The `agent` is the agent that fixes artefacts of that type.
  - The `description` names in plain words what the agent keeps true, such as "your pages". The question of point 2 is built from it.
- **Its version covers the run's contract too.** The contract is what the drift command passes a fixer and what the fixer hands back: the brief, the answer it writes for each artefact, its result lines and its `none` reasons (points 3 and 6). A contribution at a version says that each agent it names takes and returns that version's contract. A change that breaks a fixer which conforms raises the version. A contribution at the old version then leaves the point unresolved, so no fixer is read by a contract it does not follow (COR-052 point 5).
- **The contract is the point's, as its shape is.** A provider of the role that defines the point at a version takes that version's contract (COR-053 point 5). The point's fingerprint covers its companion schema alone, so no check compares two providers' contracts.
- **Keyed by type, not by place.** A place has no id, and a type has one. A project place that gives a component's type takes that type's fixer too. The point adds nothing to a place (COR-056 point 7).
- **Its combination is `union`.** Two capabilities that claim one type are an error naming both (COR-052 point 4). A project filler may replace an entry, naming any deployed agent.
- **It has no default.** A fixer belongs to the owner of the type it fixes, so this capability supplies none.
- **Its inert policy is `fail`.** The drift command (point 3) starts agents on the point's value. A point that does not resolve starts no fixer, and the command says why.
- **A capability contributes a static value,** not a command filler. The declaration then reads in the package metadata and in review, and resolving it runs nothing.
- **What a bad entry does:**
  - A capability's contribution that the point's schema refuses, or that targets another version, leaves the point unresolved, so no fixer starts. The command names the capability and the fixes: update it, pin it, or uninstall it, as the documentation slot does ([project-management:DEC-053-doc-check-slot] point 1).
  - A capability's entry may name a type not its own, or an agent it does not ship or has not deployed. Such an entry is reported and fails nothing, since the project cannot mend it (COR-055 point 1). No agent starts for it.
  - A capability's contribution through a command filler is a bad entry. This capability's validator reports it from the backbone's wiring, and the drift command starts no agent for its entries.
  - A project's entry that names an agent not deployed fails validation.
  - An agent whose own declaration claims paths, or grants a tool for changing existing files or starting agents, is reported, and the drift command does not start it. A tool that writes new files stays, for its workspace. This is a sanity check, not a limit: an agent with a shell is limited only by the confinement of point 5.

### 2. The person grants each fixer

A fixer starts on its own only where the project granted it.
- **The grant list** sits in this capability's project configuration. It holds each agent the person was asked about, the types the question named, and the answer. It is empty by default, so a project that never answers starts no fixer.
- **A grant is the person's act.** It is written only on the person's own answer, to the question or by running the grant command. An agent may record an answer only after it showed the person the question word for word and the person answered. It never answers for them.
- **The question.** One question for each agent, about the types nobody was asked about. Its words are this capability's, built from the declaration: the capability's name and the descriptions of the agent's entries. It says what the agent will do on its own after each merge, and that nothing is applied until the person approves it.
- **When it is asked.** Wherever a person can answer, before any fixer of those types starts, about each declared fixer type that has no recorded answer. The drift command asks it at a terminal. In a session with the person, the project manager relays it word for word and records only the person's answer. Install and upgrade ask it once a core record lets them ask for a point's definer (below).
- **Each answer is recorded,** a yes as a grant and a no as a refusal. It is written to the grant list in the checkout where it was given, as a change of the project's. The question asks only about a type with no answer there, so nothing asks again about those types. A yes starts a fixer from the first run after its change merges.
- **With nobody to ask,** nothing is granted or recorded, and the one command line that grants the fixer is printed. Running install, upgrade or the drift command is never the consent. Only the person's answer is, or the person running the grant command.
- **Commands for advanced use** list the declared fixers with their answers, grant one and revoke one. A revoke is recorded as a refusal. Every change to the list shows in the project's diff, as the activation of the default agent does ([project-management:DEC-030-capability-contributed-adapter-overlays]).
- **A grant counts once it is on the default branch.** The drift command reads the list at the commit its run is pinned to (point 3). So a grant counts only once its change merges, under the person's authorisation.
- **Shown at the merge.** The landing command lists a change to the grant list before it stops ready, asks or merges, as it lists a change to the friction settings ([project-management:DEC-055-pr-lists-answers] point 1). An authorisation given up front covers such a change only where the run found it when it started, as for a finding a person judges (DEC-055 point 3).
- **A grant names an agent and its types.** A type the point later gives a granted agent, by a capability's release or a project's entry, starts nothing until the person is asked about it.
- **A grant whose agent or type no entry names** starts nothing. Validation reports it with the command that revokes it.

**What this capability needs from the core lifecycle.** The question belongs at install and upgrade too. Installing a capability that declares a fixer should ask, and so should the upgrade that first brings one, where a person can answer. Install and upgrade are the backbone's operations, and no capability acts inside another's install. A migration of the capability that declares a fixer could run this capability's command only by naming this capability, which connection points exist to avoid (COR-053). So asking there needs a core record, which decides whether and how. This capability asks of it the trigger above: a declared fixer type with no recorded answer. That trigger also covers installing this capability after a capability that declares a fixer, and an upgrade after an install that had nobody to answer. The record sits with three accepted ones:
- COR-017, which rejects install asking whether to create a declared project rule set, since a run with nobody to answer would take that choice silently
- COR-059 point 4, whose list of the choices that keep their own consent within a transition it would extend
- COR-053 point 9, which declines a consent model for events

Merge delivery's prompt-once tier (COR-002) is a precedent only in its rule: it asks where a person can answer, and writes nothing where nobody can. Until that record ships, the drift command and the project manager ask.

### 3. A command starts the granted fixers

A command of this capability, the drift command, starts the fixers. The harness's dispatch tool does not.
- **Who runs it.** The person, or the project manager in the session that landed a merge into the default branch. Whoever runs it, it starts only granted fixers. A person may still start any agent by hand, in a session of their own.
- **What it reads, and where.** It pins one commit of the default branch, as the backbone resolves it (COR-054 point 2). It reads at that commit the whole-repository check's machine-readable findings, the backbone's one answer for each artefact's type (COR-056 point 6), the point and the grant list. It reads no tracking issue, and no rendered prose for any choice of its own. The pull requests it puts in a brief are data for the fixer (below).
- **Where each fixer runs.** In a separate working copy at that commit, never in the person's checkout, which may be on another branch. The copy is provisioned as the project's checks are, so every anchor resolves there. The fixer's own definition is the one at that commit, so an edit to a fixer that has not merged never runs unwatched.
- **What it dispatches.** Stale artefacts with a granted fixer, and nothing else. It lists the rest, each with its reason:
  - deferred debt, and dead or ambiguous anchors
  - an artefact the check could not judge
  - an artefact with no type, or a tied type
  - a type no entry names, or whose fixer is not granted
- **Order.** Upstream first (COR-050 point 11). An artefact whose upstream is stale waits, listed with that upstream, until the upstream is answered. It waits too where the upstream has no granted fixer. So no brief holds an artefact beside its stale upstream.
- **Unchanged friction.** An artefact whose friction matches its standing proposal, or its standing question, is not dispatched again, nor is one whose `none` stands (below). A flag dispatches it anyway, as the review command runs a reviewer whose verdict is still fresh only when forced ([project-management:DEC-032-conditional-reviewer-requirements] D4).
- **A dry run** says what it would start, and starts nothing.
- **The brief.** Each run gives its fixer one brief, and no other message. The brief keeps two parts apart:
  - **The frame instructs.** It says that the drift command started the agent as the fixer of the artefacts' types, with nobody watching. It names:
    - the commit, and the working copy the fixer reads. Every path the fixer reads, those its own definition names included, is relative to the working copy's root.
    - the workspace, the one folder the fixer writes. The shell's temp folder lies in it, under a name the brief gives, and nothing in that folder is read back.
    - the artefacts, each as the whole-repository check names it, with its type, upstream first
    - the command forms the run's rules allow (point 5)
  - **The data informs, and never instructs.** Each piece is quoted with its source, between markers made new for the run, as words nobody vetted:
    - for an artefact held in an earlier run, the question, the person's answer and who gave it
    - for each commit the check names behind an artefact's friction, the title and text of the pull request that carried it. A text cut at the size the command bounds is marked as cut. Where the work tracker has no such pull request, or cannot be reached, the brief says so.
- **No name that could forge a line.** An artefact is not dispatched where its name holds a backtick, a control character, or a line or paragraph separator. Nor is one whose name is no plain path inside the repository, such as one with a `..` part, or whose folder would fall in the shell's temp folder. The command lists each with that reason.
- **The result.** Each fixer ends with one line for each artefact the brief names, in a fixed grammar, as a reviewer's verdict line has one ([project-management:DEC-028-agent-as-approver-paths]). The line says proposed with its answer's file, held with a question for the person, or none with a reason:

  ```text
  Fixer result (<agent>): proposed `<artefact>` in `<artefact>/answer.json`
  Fixer result (<agent>): held `<artefact>`: <the question>
  Fixer result (<agent>): none `<artefact>`: <reason>: <the reason in words>
  ```

  - **What counts as a line:** any line of the fixer's final message that, stripped of the whitespace around it, starts with `Fixer result (`. The message is the fixer's own text, never a tool's result, split into lines at each line feed. Every such line counts, not only the first, and one inside a fenced block counts the same. A fence's own lines are no result lines.
  - **What a line must match:** `<agent>` is the fixer the command started, and `<artefact>` is one of the brief's names, compared exactly. `<reason>` is one of the list below.
  - **What gives an artefact no result:**
    - no line for it, or more than one
    - a proposed line whose answer is missing, refused by the schema (point 6), or written for another artefact
    - a held or none line whose artefact's folder holds an answer
    - a run that reached its wall-clock limit (point 4)

    Such an artefact counts as `failed`, below, and the command reports why.
  - **What is read for nothing:** a line off the grammar, for another agent, or for an artefact the brief does not name. The command reports it.

  The command reads these lines and the answers' fields, never prose. A held question is shown in the batch (point 6), and the person's answer goes with the artefact's next dispatch.
- **The `none` reasons** are a fixed list. Each says what clears it, so the command tells a `none` that stands from one that passes.
  - **Cleared by the artefact:** `not-mine`, an artefact the fixer does not fix, and `not-stale`, one not stale at the commit or not judged by the checks. Each stands for that fixer until the artefact's friction changes.
  - **Cleared by the setup:** `refused`, a call the fixer needs that the run's rules or its sandbox stopped, and `out-of-step`, another component's answer in a version the fixer does not read. Each stands for that fixer until the setup changes, and the command reports it at every run as a fault of the setup. The setup is anything the run is made from but the artefact, such as:
    - the fixer's definition, and the overlay that resolves it
    - the run's rules, with the denies they carry
    - the run's bounds
    - a component's version

    The command records the setup with the `none`.
  - **Cleared by the next run:** `upstream`, an artefact that waits for its upstream, which the words name, and `failed`, a call or a reading that failed for any other cause. The artefact is dispatched again at the next run. One that fails at two runs in a row then stands as the setup's faults do, under `failed`.

  Each `none` that stands is listed at every run, with its reason.

### 4. The run is bounded

- **A cap per fixer,** counting only artefacts with no standing proposal, so each run moves on.
- **A limit on fixers at once,** set as the review command's limit on reviewers is.
- **A wall-clock limit per fixer.** A fixer that reaches it is marked failed, and is not retried in that run. Each of its artefacts counts as `failed` (point 3).
- **One run at a time per repository,** held by a lock.
- **An artefact an open pull request already changes** is listed, not dispatched.
- **A failure outside the fixer's work,** such as an agent that could not start, is retried once (core rule 21). The command first checks that the failed start wrote nothing. If it fails again, the command starts no further fixer and reports what failed.

### 5. Each run is confined

A run nobody watches cannot ask, so a tool call no rule allows is refused, and the rules are the whole grant. A project's allow rules may let through far more than a fixer needs: pushing, merging, changing a record's status, or running a writer. So each run is given what proposing needs, as far as the harness can hold it.
- **Allowed for each run,** and nothing else: reading files, writing its own workspace, reading version control, the backbone's reading commands, and each command another component declares a query. A writer added later is refused without anyone listing it.
- **The brief names the forms the rules allow.** Reading version control covers git's reading commands, pointed at the working copy. Making a diff between a file there and one in the workspace, and checking that a diff applies, are forms allowed in their own right, since a fixer proposes a diff. The brief's list of forms is built from the run's rules, so it names no form they refuse. What a form's options could add, such as writing a file or running a program, the sandbox holds, not the rule.
- **Denied for each run,** above any allow rule, as the floor where the harness can only take away:
  - writing with the file tools anywhere but the run's own workspace
  - version control beyond reading
  - the work tracker, and the toolchain that installs or runs packages
  - every writer of the methodology, and every command of this capability
- **The rules are the permission model's** (COR-028 point 1). This capability declares them, scoped to a fixer's run, and the adapter realises them for that run. In the model they are denies, and a deny prevails over every allow, the shared baseline's included. So the run is held to the list above, whatever the baseline allows. The command keeps no rule list of its own.
- **Held where they fail closed.** The adapter realises the run's rules on a mechanism that fails closed, as a deny that must hold is (COR-028 point 2).
- **The operating-system sandbox** wraps the fixer's shell. The run's workspace is the only folder it writes, and no network domain is allowed.
- **No bypass.** The command never passes a flag that bypasses the permission rules.
- **Where the harness cannot confine,** the command starts no fixer and says why. That is where the adapter cannot hold the run's rules on a mechanism that fails closed, or cannot wrap the run's shell in the sandbox.
- **A leaf.** A fixer starts no other agent, and the command refuses to start inside a fixer's run.
- **Checked after each fixer:** nothing changed outside the run's workspace, no reference moved, and no ignored file appeared. A breach sets that fixer's proposals aside, and the command reports it.
- **What stays open is stated,** as intent the harness cannot enforce is (COR-028 point 3):
  - Network egress is no boundary. A sandbox's list of domains stops only a well-behaved request.
  - A command the platform runs outside the sandbox is held by the run's rules alone.
  - Where the adapter can only take away, the project's allow rules outside the denied categories reach the run.
  - The permission layer sees the command, not each agent it starts.
  - A proposal's words can carry a contributor's steering, so the person reads every word of each answer before accepting it.
  - A pull request's text can change after its merge, so the words a brief quotes may be newer than the commit.

### 6. The proposals wait for the person

- **Files, not pull requests.** A fixer writes its proposal into its workspace, in a folder named for the artefact as the brief names it. The folder holds `evidence.md`, which the person reads before deciding, the diff where the fixer proposes an edit, and `answer.json`. A held artefact's folder holds its evidence and no answer. A pull request would need a branch, a commit, a push and an issue, each made under the person's account by a run nobody watched.
- **A proposal is data.** It is a diff and its answer. The diff is confined to the file of the artefact it was dispatched for, or to its entry in a collection file. A proposal whose diff reaches anything else is set aside, as a breach is (point 5).
- **An answer is fields,** which a schema of this capability holds:
  - the artefact, as the brief names it, and the outcome, `unchanged` or `updated`
  - for `unchanged`, the justification, the fixer's draft that the person confirms or rewrites
  - for `updated`, the one sentence on what changed in the artefact
  - the deferrals the fixer proposes keeping
  - its diff's file, in the artefact's folder
  - what the person does before the answer is recorded, in words

  An answer the schema refuses gives its artefact no result (point 3). This capability builds each writer's command from the fields, and never runs a string a fixer wrote.
- **Gathered in the main working tree.** The command gathers every run into the agent workspace of the repository's main working tree, in a folder of this capability's. So removing a worktree removes no proposal. A repository with no main working tree gathers nothing, and the command says why. An index lists each artefact, its type, its fixer, its state, its proposal and the commit it was judged at.
- **Reached through this capability's commands.** The project manager reads, shows and applies the queue only through them, never with file tools.
- **A queue in the workspace.** The agent workspace holds intermediate files (core rule 16). Here it also holds a queue. A run's folder is kept until each of its proposals is accepted or refused, and then removed. A queue removed by other hands loses only work that can be done again, and the refusals kept in it.
- **The queue is the clone's.** Git holds the debt, and the whole-repository check recomputes it anywhere (COR-050 point 9). A proposal is work that can be done again. In a clone that holds none, a stale artefact has no standing proposal, so the next run there dispatches it.
- **Checked again before it is shown, and before it is applied.** A proposal whose artefact is no longer stale, or whose friction at the current default branch differs from what it was judged against, is set aside and dispatched again. It is never shown or applied, since a revalidation would answer friction nobody judged. A proposal judged under another version of the contract is set aside and dispatched again too. The index records the version each run's proposals follow.
- **Visible.** The landing command prints a one-line count of the proposals waiting. A view of what waits on the person, once this capability builds one, lists them beside the rest.
- **One batch.** The project manager brings the proposals to the person together, each with its evidence, its diff and its commands word for word. The person accepts, rewords or refuses each.
- **A refusal is remembered** in the queue, against the artefact's friction, so the artefact is not dispatched again until its friction changes. It goes with the queue. Its lasting form is a deferral, which the person may give instead as their own answer.
- **After yes.** The person first does what each accepted answer lists for them to do, such as reporting a defect and writing its reference into the reason. The project manager files an issue, branches, applies the accepted diffs in upstream order and runs the writers the person accepted. A diff that no longer applies is set aside and dispatched again. The project manager runs a writer only under the conditions the agents README sets for an agent whose task is the answer itself ("Friction writers"). The change then passes the ordinary gate, and the person authorises its merge.
- **A fixer runs no writer.** It has no way to ask the person, and point 5 denies it every writer.

## Rationale

**Why the person grants each fixer.** A capability's reviewer gates a change a person is making, so installing the capability is the opt-in (DEC-032). A fixer is different. It widens what runs in the project: an agent with a shell, unwatched, on input a contributor wrote. So the person grants it, once for each agent and its types, and the default grants nothing.

**Why the grant list is no second permission model.** The grant is the person's consent to this capability's automation, as the toggle for the default agent is (DEC-030). What a run may do is the permission model's (point 5). The list says which agents the drift command may start, and never what they may do.

**Why install should ask.** Install is the moment a project takes up a capability's discipline. A separate step is one the project must first learn of, which is COR-017's reason for creating a declared project rule set at install. COR-017 rejects asking there, because a run with nobody to answer would take the choice silently. Here a run with nobody to answer takes nothing, so asking takes nothing silently. Running install is not the consent, since a fixer widens what runs. The answer to a plain question is.

**Why a consent, where events need none.** COR-053 point 9 asks no third consent for a capability's event subscribers, for two reasons. The project installed the capability and the user ran the writing command, and a subscriber needs no network and acts the same on the same inputs. Neither holds for a fixer. After a merge the project manager runs the drift command, not the person. A fixer's network egress has no hard boundary, and an agent does not act the same on the same inputs.

**Why the trigger is state, not a release.** Asking only on "the upgrade that first brings a fixer" misses three cases:
- this capability installed after the capability that declares the fixer
- an install with nobody to answer
- every install before the core record ships

Asking wherever a type has no recorded answer covers them all, and still asks once.

**Why a grant counts once it merges.** A grant the drift command read from the working tree could be written a minute earlier, by anyone, the project manager included. Read at the default branch, it counts only after the person authorised its merge. The landing command shows it there, so an authorisation does not carry a grant nobody saw.

**Why a grant names types.** A grant of an agent alone would widen with no question when the agent comes to fix a new type. Naming the types keeps every widening a question.

**Why a command, not the harness's dispatch tool.** Code fixes the set of agents it starts, so tests check it, and the grant is read in one place. The review command already starts agents this way.

**Why keyed by type.** A type is declared by the owner of what it names (COR-056), so the capability that owns a type declares its fixer. A project place that gives the type takes the fixer with it.

**Why `fail`.** A project filler that breaks answers nothing. Under `fallback`, the rest would still resolve, and a capability's agent would start again for a type the project gave to another agent. Starting nothing, and saying why, is the safe reading.

**Why the command confines each run.** Which agent may start which through the harness's dispatch tool is not decided. A fixer started now would otherwise run under whatever allow rules the project has. So each run is given what proposing needs, through the permission model, and what the harness cannot hold is stated.
- **An allow list, with denies as its floor.** A list of denies only takes away. Every other allow rule of the project would still reach the run, and a writer added later would too. An allow list refuses what nobody listed.
- **Fail closed.** A permission layer that fails open lets a call through when it breaks. A harness that cannot hold a run's rules starts no fixer, since a run that is unconfined while it appears confined is worse than none.

**Why a proposal is data.** The run is bounded, but what a proposal does lands later, applied by an agent under the project's whole allow list. A fixer a contributor steered could propose a diff beyond its artefact, or a writer's command with something added. Confining the diff to its artefact, and building each command from fields, leaves only the answers' words for the person to read. No word of a command is a fixer's, as no word of the list of answers is an agent's (DEC-055 point 1).

**Why one contract, under the point's version.** Each capability that ships a fixer would otherwise state its own side of the run, and two sides drift apart. The command reads every fixer one way, so the contract has one home. The point already carries a version that its contributions target (COR-052 point 5). A contribution names an agent, so a break of the contract breaks the contribution, whatever its entries' shape. Its inert policy is `fail`, so such a break stops every fixer until each contribution catches up, as any break of the point does. No fixer is read by a contract it does not follow.

**Why the brief keeps its frame apart from its data.** Commit messages, pull requests and the person's answers are words a fixer must read and must not obey. Quoting each with its source, apart from the frame, tells the fixer which words instruct it. That is no boundary. A steered fixer can still propose a steered answer, which is why the person reads every word (point 5).

**Why the brief carries the pull request.** Where an artefact and what it rests on disagree, a fixer judges whether the change was meant, and the pull request is the main evidence of that. The run reaches no network, so the command reads it outside the run and passes it in. Its words are a contributor's, as a commit message's are, so it is quoted as data.

**Why exact names, and none that could break a line.** A line names its artefact between backticks, and the name is a folder too. A name holding a backtick or a line break could end the name early or open a forged line. Compared exactly against the brief, a line can answer only for an artefact the fixer was given.

**Why every line counts, unlike a verdict line.** A verdict line is the first that matches, and text in a fenced block carries no finding's tag (DEC-028). Here a quoted line could then come before the real one and stand in for it, and a fixer may write its lines in a fence. So every line counts, and two lines for one artefact give it no result. A forged or doubled line costs its artefact a result, never a wrong reading.

**Why a fixed list of `none` reasons, sorted by what clears them.** A `none` that will come back the same takes a place under the fixer's cap at each run if it is dispatched again, so the run never moves on (point 4). A `none` that waits on something is never tried again if it is remembered. What clears a `none` decides which it is. The artefact's friction clears an artefact's reason. A setup's fault is cleared only by a change to the setup, so it stands until one comes, and the person is told of it at every run. The command reads no prose, so a code on the line tells them apart.

**Why files, checked again, and one batch.** A proposal costs nothing to keep and can be made again. It needs no account and no branch. Proposals wait for days, so each is checked against the current default branch before the person sees it. A batch asks the person once for each run, not once for each artefact.

**Why a count in the landing command.** It is the command the person runs for each merge, so the proposals waiting show where the work is.

### Alternatives considered

- **Only the person starts a fixer, by hand.** Rejected. The debt waits until someone remembers to read the check.
- **The person runs the command each time, and it starts every declared fixer.** Rejected. Nothing would run after a merge on its own, which is what the loop is for.
- **Installing the capability is the grant.** Rejected. A fixer widens what runs, so the grant stays explicit.
- **A grant by command only, with no question.** Rejected. A step the project must first learn of is one it rarely takes, as COR-017 reasons for the declared project rule set.
- **A grant of an agent for every type.** Rejected. It widens with no question.
- **A privilege the permission layer enforces on the dispatch tool.** Not taken. It is the question this record leaves to its own decision, and that layer would not see a command that starts agents.
- **A draft pull request for each proposal.** Rejected. A run nobody watched would act under the person's account.
- **Each capability states its fixer's side of the run.** Rejected. The sides drift, and the command reads one contract.
- **The run reads the pull request itself.** Rejected. The run reaches no network (point 5).
- **A `none` reason in words alone.** Rejected. The command reads no prose.
- **A contract version on each entry, or each fixer's own.** Not taken. The command would read several contracts at once, or refuse entry by entry. The point's version keeps one contract, at the cost that a break stops every fixer until each contribution catches up (point 1).
- **Lines that name an artefact by its place in the brief.** Not taken. A person reads the line, and a name says which artefact it answers for. A name a fixer cannot repeat exactly costs only that artefact's result, and the command reports it.
- **A fixer that proposes a deferral.** Rejected. A deferral is the person's to give, and its reason names an open follow-up, which a run cannot open.
- **A fixer field on each place.** Rejected. A place has no id, and a third concept on places would move them into a functionality of their own (COR-056 point 7).
- **A fixer field on a type's registry entry.** Rejected. It changes a core schema, takes away the project's way of giving one type another agent, and puts who keeps a type into the declaration of what it is.
- **The whole-repository check dispatches.** Rejected. The checks are read-only (COR-050 point 12).
- **Waiting for a view of what waits on the person.** Rejected. Files and a count line serve until one is built.

## Implications

- **This capability** declares the point and its companion schema, ships the schema of a fixer's answer, and adds the grant list to its configuration schema. It ships the commands that list, grant and revoke, the drift command, and the commands that show and apply the queue. The landing command gains the count line and lists a change to the grant list. This capability's skill and the project manager's body say when to run the command and how to relay the question. They also say how to bring the batch, and how to apply what the person accepts.
- **A capability that ships a fixer** contributes its entries. Its agent takes the brief, writes each answer the schema holds, and ends with the result lines, a reason from the list on each `none`. Its body restates the contract in plain words, and its storyboard covers the run. An agent references rather than embeds (COR-006), but the body is the agent's own instruction, which it follows before it reads anything. The point's version keeps the restatement true, since a change that breaks it raises the version (point 1).
- **A break of the contract** raises the point's version, so it reaches each project's own filler file too, which names the version it targets (COR-052 point 2). The migration COR-010 asks of such a change rewrites no project's filler file, since it cannot vouch for an agent the project names. The file then fails validation, naming the version, until the project re-targets it. The release says what a project's own fixer must change.
- **The command reads the contract from data.** The `none` reasons, their classes and the line's grammar are what the drift command reads. The change that ships the command holds them as data of this capability, and tests this record and the README against it (COR-018).
- **A core record** decides whether and how install and upgrade ask the question (point 2). Until it ships, the drift command and the project manager ask.
- **A harness requirement** (COR-047): an agent can be started from a command, confined for one run, and its files read after it ends.
- **Architecture decisions of the methodology** settle how this is realised:
  - where the runner lives
  - how the adapter realises each part of point 5, and the shape the permission model gives a rule scoped to a run
  - what the permission layer sees, and the check after each run
- **A record on which agent may start which** is expected to cover this route too, once one is accepted. It would adopt or absorb the grant list, so that a project keeps one such list.
- **[project-management:DEC-029-project-manager-agent-shape]**, "Invocation pattern", covers the agents the project manager dispatches through the harness's tool. An agent the drift command starts is no such dispatch. DEC-029 is refined to say so in the change that ships the drift command.
- **"Friction writers" in the agents README** needs no change. Its condition that an agent can ask the person already lets a fixer run no writer, and point 5 denies it every writer.
- **The agent workspace** is described as holding intermediate files, by core rule 16 and by the permission capability's account of it. This capability's queue is a further use. Those accounts are asked to name such a use, so that an agent removing what it no longer needs leaves a queue alone.
- **No migration.** Every change adds.
