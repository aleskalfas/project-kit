---
id: DEC-056
title: Only granted fixers start on stale artefacts, and they only propose
status: accepted
date: 2026-10-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** when the default branch leaves an artefact out of date, the agent that fixes artefacts of its type starts and proposes an answer, and the person decides it. A capability declares which of its agents fixes which of its types. A fixer starts on its own only where the project granted it, and only the person grants. A command of this capability, the drift command, starts the granted fixers, each bounded and confined as far as the harness allows. The person is asked a plain question about each fixer nobody was asked about: by the drift command, and by install and upgrade once the core lifecycle can ask. Commands list, grant and revoke. A fixer only proposes. Its proposals wait as files, the landing command says how many wait, and the person accepts, rewords or refuses each before anything is written.

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
- **What it reads, and where.** It pins one commit of the default branch, as the backbone resolves it (COR-054 point 2). It reads at that commit the whole-repository check's machine-readable findings, the backbone's one answer for each artefact's type (COR-056 point 6), the point and the grant list. It reads no tracking issue and no rendered prose.
- **Where each fixer runs.** In a separate working copy at that commit, never in the person's checkout, which may be on another branch. The copy is provisioned as the project's checks are, so every anchor resolves there. The fixer's own definition is the one at that commit, so an edit to a fixer that has not merged never runs unwatched.
- **What it dispatches.** Stale artefacts with a granted fixer, and nothing else. It lists the rest, each with its reason:
  - deferred debt, and dead or ambiguous anchors
  - an artefact the check could not judge
  - an artefact with no type, or a tied type
  - a type no entry names, or whose fixer is not granted
- **Order.** Upstream first (COR-050 point 11). An artefact whose upstream is stale waits, listed with that upstream, until the upstream is answered. It waits too where the upstream has no granted fixer.
- **Unchanged friction.** An artefact whose friction matches its standing proposal is not dispatched again. A flag dispatches it anyway, as the review command runs a reviewer whose verdict is still fresh only when forced ([project-management:DEC-032-conditional-reviewer-requirements] D4).
- **A dry run** says what it would start, and starts nothing.
- **The result.** Each fixer ends with one line per artefact, in a fixed form, as a reviewer's verdict line is ([project-management:DEC-028-agent-as-approver-paths]). The line says proposed, held with a question for the person, or none with a reason. The command reads that line, never prose. A held question is shown in the batch (point 6), and the person's answer goes with the artefact's next dispatch.

### 4. The run is bounded

- **A cap per fixer,** counting only artefacts with no standing proposal, so each run moves on.
- **A limit on fixers at once,** set as the review command's limit on reviewers is.
- **A wall-clock limit per fixer.** A fixer that reaches it is marked failed, and is not retried.
- **One run at a time per repository,** held by a lock.
- **An artefact an open pull request already changes** is listed, not dispatched.
- **A failure outside the fixer's work,** such as an agent that could not start, is retried once (core rule 21). The command first checks that the failed start wrote nothing. If it fails again, the command starts no further fixer and reports what failed.

### 5. Each run is confined

A run nobody watches cannot ask, so a tool call no rule allows is refused, and the rules are the whole grant. A project's allow rules may let through far more than a fixer needs: pushing, merging, changing a record's status, or running a writer. So each run is given what proposing needs, as far as the harness can hold it.
- **Allowed for each run,** and nothing else: reading files, writing its own workspace, reading version control, the backbone's reading commands, and each command another component declares a query. A writer added later is refused without anyone listing it.
- **Denied for each run,** above any allow rule, as the floor where the harness can only take away:
  - writing with the file tools anywhere but the run's own workspace
  - version control beyond reading
  - the work tracker, and the toolchain that installs or runs packages
  - every writer of the methodology, and every command of this capability
- **The rules are the permission model's** (COR-028 point 1). This capability declares them, scoped to a fixer's run, and the adapter realises them for that run. In the model they are denies, and a deny prevails over every allow, the shared baseline's included. So the run is held to the list above, whatever the baseline allows. The command keeps no rule list of its own.
- **Held where they fail closed.** The adapter realises the run's rules on a mechanism that fails closed, as a deny that must hold is (COR-028 point 2).
- **The operating-system sandbox** wraps the fixer's shell. The run's working copy is the only folder it writes, and no network domain is allowed.
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

### 6. The proposals wait for the person

- **Files, not pull requests.** A fixer writes its proposal into its run's workspace. A pull request would need a branch, a commit, a push and an issue, each made under the person's account by a run nobody watched.
- **A proposal is data.** It is a diff and its answers. The diff is confined to the file of the artefact it was dispatched for, or to its entry in a collection file. Each answer is fields: the artefact, the outcome, and the justification or reason. A proposal whose diff reaches anything else is set aside, as a breach is (point 5). This capability builds each writer's command from the fields, and never runs a string a fixer wrote.
- **Gathered in the main working tree.** The command gathers every run into the agent workspace of the repository's main working tree, in a folder of this capability's. So removing a worktree removes no proposal. A repository with no main working tree gathers nothing, and the command says why. An index lists each artefact, its type, its fixer, its state, its proposal and the commit it was judged at.
- **Reached through this capability's commands.** The project manager reads, shows and applies the queue only through them, never with file tools.
- **A queue in the workspace.** The agent workspace holds intermediate files (core rule 16). Here it also holds a queue. A run's folder is kept until each of its proposals is accepted or refused, and then removed. A queue removed by other hands loses only work that can be done again, and the refusals kept in it.
- **The queue is the clone's.** Git holds the debt, and the whole-repository check recomputes it anywhere (COR-050 point 9). A proposal is work that can be done again. In a clone that holds none, a stale artefact has no standing proposal, so the next run there dispatches it.
- **Checked again before it is shown, and before it is applied.** A proposal whose artefact is no longer stale, or whose friction at the current default branch differs from what it was judged against, is set aside and dispatched again. It is never shown or applied, since a revalidation would answer friction nobody judged.
- **Visible.** The landing command prints a one-line count of the proposals waiting. A view of what waits on the person, once this capability builds one, lists them beside the rest.
- **One batch.** The project manager brings the proposals to the person together, each with its commands word for word. The person accepts, rewords or refuses each.
- **A refusal is remembered** in the queue, against the artefact's friction, so the artefact is not dispatched again until its friction changes. It goes with the queue. Its lasting form is a deferral, which the person may give instead as their own answer.
- **After yes.** The project manager files an issue, branches, applies the accepted diffs in upstream order and runs the writers the person accepted. A diff that no longer applies is set aside and dispatched again. The project manager runs a writer only under the conditions the agents README sets for an agent whose task is the answer itself ("Friction writers"). The change then passes the ordinary gate, and the person authorises its merge.
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
- **A fixer field on each place.** Rejected. A place has no id, and a third concept on places would move them into a functionality of their own (COR-056 point 7).
- **A fixer field on a type's registry entry.** Rejected. It changes a core schema, takes away the project's way of giving one type another agent, and puts who keeps a type into the declaration of what it is.
- **The whole-repository check dispatches.** Rejected. The checks are read-only (COR-050 point 12).
- **Waiting for a view of what waits on the person.** Rejected. Files and a count line serve until one is built.

## Implications

- **This capability** declares the point and its companion schema, and adds the grant list to its configuration schema. It ships the commands that list, grant and revoke, the drift command, and the commands that show and apply the queue. The landing command gains the count line and lists a change to the grant list. This capability's skill and the project manager's body say when to run the command and how to relay the question. They also say how to bring the batch, and how to apply what the person accepts.
- **A capability that ships a fixer** contributes its entries. Its agent's brief takes the drift command's request and ends in the result line, and its storyboard covers the run.
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
