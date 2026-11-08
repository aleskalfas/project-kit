---
id: DEC-067
title: A pull request's head starts programs only from the base's own repository, or on a person's word
status: accepted
date: 2026-11-05
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** some commands of this capability run the change check from a checkout of a pull request's head. That starts programs the head holds, under the account of whoever runs the command. These commands do so only for a head on the base's own repository that holds none of a sandboxed build's commits. A person at a terminal can also name a head for one run.

Any other head, such as a fork's, starts nothing, and no flag changes that. Where the check needs such a program, the command asks the person at its terminal. With nobody there, nothing merges through it.

So a person who lands a change trusts whatever can push to that repository: colleagues, the project's bots and its applications. A fork's words still reach the reviewers, whose runs this record does not confine. These commands also print text from outside them escaped, so a head cannot rewrite what a person reads.

## Context

The change check answers for an anchor of a registered kind by running its resolver ([COR-050](../../../decisions/core/COR-050-anchors-and-friction.md) point 2). The backbone runs that command in the working tree, so its script comes from the tree, and the kinds are the ones the head registers. So a head can replace a resolver, or register one of its own.

Away from a checkout at the head, the backbone refuses to run a resolver. The landing command and the move to review answer that refusal with a temporary checkout of the head, and run the check again there. The merge check ([project-management:DEC-055-pr-lists-answers] point 6) runs from a temporary checkout of the merge. Each run has the account and the environment of whoever started the command.

A security review reproduced the result: a head that changed a resolver ran its payload and read the host's token ([project-kit#2697](https://github.com/aleskalfas/project-kit/issues/2697)). The run also comes early. The move to review makes it before any reviewer has read the head, and the landing command before the person is told anything.

COR-050 point 2 calls a resolver's limits a declared and trusted contract, not a boundary, and leaves a boundary to the project. [project-management:DEC-065-answers-read-from-check] gave the view a limit: it never checks a head out (point 2). It left the landing command and the move to review to this record (point 6).

A head also reaches the person through words. A problem the change check states can hold control characters, as can a path or a name in the fixers' grant list. Some commands print them as they came. Such a character can move the cursor, erase a line or reorder what follows.

## Decision

**A command of this capability starts a head's programs only where the head lies on the base's repository and holds no build's commits. A person at a terminal can also name a head for one run. Any other head starts nothing, and no flag changes that. Its change check runs from git objects alone, and where that cannot answer, the person at a terminal is asked, and otherwise nothing merges. These commands print text from outside them escaped.**

### 1. A head on the base's repository may start programs

A *head's programs* are what a checkout of the head, or of its merge with the base, would run. That is each resolver and all it loads from that tree, and any hook the tree holds.

A command starts them only where two things hold. The host says the pull request's head lies in the base's own repository. And the head holds no commit of a *build*, which [project-management:DEC-063-task-builder] keeps in a sandbox until a person reviews it (point 7). Any other head is a head *from elsewhere*, a fork's above all.

- **What the test reads.** The host's own word, in the same reading that names the head, and the Task's build records. A head the host does not place, or records that cannot be read, fail it. So a reading that does not say is never a pass. A project with no seats has no builds, and a pull request with no Task has no build.
- **What the answer covers.** It holds for each commit a run reads there: the head, an earlier head an authorisation names, and the merge with the base.
- **Which pull request.** Two open pull requests that share a branch's name stop the run, naming both, since one may be a fork's.

### 2. Which commands take the test

- **The move to review, the landing command and its merge check** take it before they make any temporary checkout.
- **The review command** starts no program of the head, but a reviewer may need one. For a head from elsewhere it runs the change check from git objects too, as point 3 says. A person's word then reaches the reviewers it starts.
- **The view** starts nothing for any head, as DEC-065 point 2 has it. A person turns to it before trusting a change, so passing the test gives it no checkout.
- **The command that opens the pull request** takes no temporary checkout, for any head. It only warns, so a check it cannot run costs one warning line.
- **The other merge commands** run no change check, so they start nothing.

### 3. What a head from elsewhere gets

Unless a person names it (point 4), no temporary checkout of the head or of its merge is made. The change check reads each from git objects, run from the working directory, so nothing of the head starts.

- **Where no anchor needs a resolver,** that is the whole check. The command goes on as for any head, but for the brief point 5 gives its reviewers.
- **Where one does,** the backbone refuses, and no answers come, in either friction mode. At a terminal the command asks (point 4). With nobody there:
  - **The move to review** stops. `--force` moves on with its warning that the sentences went unchecked (DEC-065 point 3), and starts nothing.
  - **The landing command** merges nothing (DEC-065 point 5). Its line says why, that a second run changes nothing, and that a person at a terminal can go on. It exits with a code of its own, which asks a person to act.
  - **The review command** starts its reviewers under point 5's brief.
- **The landing command finds this out first.** For a head from elsewhere it runs the check before it waits for checks or starts a reviewer. A merge can still need a resolver its head did not, and the merge check then asks or stops the same way.
- **No flag starts a program.** `--force` goes without the check and never takes a checkout. A run authorised up front stops here, even at a terminal.

### 4. A person at a terminal can name a head for one run

At a terminal, the command shows the head's commit and the repository it comes from. It says the head's programs would start under the person's account, and that reading the head's diff needs no checkout. The person answers by typing the commit's short id.

- **What the word covers.** That one run of that command: the commit named, its merge with the base, and the reviewers the run starts. Another run, or a later head, asks again.
- **What gives it.** Only that answer. No flag, no run authorised up front and no run off a terminal gives it.
- **What it leaves.** A comment on the pull request names the commit, the command and who named it. It is posted before anything starts, and with no comment posted nothing starts.
- **What it leaves standing.** Every other stop, each reviewer's verdict and the authorisation to merge.
- **What holds it.** An agent runs with no terminal, so the question stops it, and a person directing one runs that command themselves. A program that fakes a terminal could still answer. So this guards a routine run, and it is no boundary.

### 5. A reviewer of such a head is told to start nothing

A local reviewer runs unconfined in the person's checkout ([pkit:ADR-066] point 10). The backbone's refusal tells it to run from a checkout at the head. So a reviewer of a head from elsewhere could start what this record withholds.

- **The brief says what the head may do.** For a head from elsewhere that nobody named, it tells the reviewer to start nothing of the head and to check it out nowhere. That holds whatever the refusal advises. It outranks the agents README and a reviewer's definition, which allow a reproduction.
- **A check it cannot run stays what its own rule makes it.** The reviewer of the answers blocks, since they would go unchecked.
- **This is an instruction, not a boundary.** The reviewer is an agent reading words the head wrote (point 8).

### 6. In a working tree of the head, the person has already chosen

A command cannot keep to this record from a working tree that holds the head's files, an older commit of its branch included. A capability's commands are read from the project's own tree, so there the command is the head's own. It has started before any test is taken, and the change check runs resolvers there with no refusal. Making such a tree can itself start the head's programs, where a clone takes its hooks from a tracked folder.

So this record protects a working directory that holds none of the head's files, as DEC-065 does for the view. A person reads a head from elsewhere through its diff. They land it from a tree of their own, since the landing command would otherwise be the head's.

### 7. These commands print text from outside them escaped

Each command this record names, and the documentation check, escapes text it did not write itself before that text joins a line it prints. It escapes as the change check's human-readable report does: each control character, bidirectional override and zero-width character is written as its escape. It does so line by line, so a finding printed whole keeps its lines.

- **What counts.** Anything from the head, the host or a program. Examples are a problem the change check states, a program's error output, a path, a title, a check's name and a grant's words.
- **What does not.** Machine-readable output keeps its bytes, since no terminal reads it as text.

### 8. What a person trusts when they land a change

Whoever runs these commands trusts each of the following, and the capability's README says so.

- **Whatever can push to the base's repository.** That is each person, bot and application the project granted. Their programs run under the account of whoever runs the command, which may reach far more than that repository. They run at the move to review, before any reviewer has read them, and at the landing, before the person is told anything.
- **A head they named,** for that run.
- **The host,** for saying where a head lies.
- **The reviewers' runs.** A head from elsewhere starts no program, but its words still reach an agent that runs unconfined. A steered reviewer can do what the person's account can. ADR-066 point 10 leaves that to the record that confines those runs.
- **What lands.** Once merged, the change's programs run wherever the project is checked. An authorisation to merge gives that, and this record does not narrow it.

A project with writers it does not trust this far confines the run where it runs it, as COR-050 point 2 says. A container holding a token for that one repository is such a place.

### 9. What this gives up

- **The reproduced run stays open to a writer.** Someone who can push to the base's repository can still replace a resolver and read the token. This record moves the line from anyone to the project's own writers.
- **A project with seats, whose anchors need a program,** stops at each build's move to review and landing until a person comes to a terminal. A sandboxed run of the check would lift that (Alternatives, "Confining the run").
- **A fork's change, where anchors need a program,** lands through the landing command only with a person at a terminal, for each head. No agent lands it, and no run authorised up front does.
- **The stop can send a person to the other merge commands.** A merge through them runs no change check and tells no answer, as DEC-065 point 6 says. The stop's line says so, so that it does not read as a neutral choice.
- **A project whose members work from forks** pays this on every head, their own included.

## Rationale

**Why the base's repository.** The project granted each person, bot and application that may push there, and anyone can open a pull request from a fork. The host states it in one word, beside the head, and the head cannot change it. A pull request whose fork was deleted still reads as from elsewhere, as all 29 did among 600 closed pull requests of `cli/cli`. Hosts draw the same line for their own checks, keeping a project's secrets from a fork's run.

**Why writers are trusted this far.** A writer's branch already runs on a colleague's machine when they test it, and a writer can often change what the project's own checks run. What this adds is a run nobody chose. On a project whose anchors need a program, any narrower test would stop nearly every landing, and a person would come to pass it unread. Point 8 states the cost.

**Why a build's commits count as from elsewhere.** The test asks where a head lies, but here the project knows who wrote it. DEC-063 keeps the seat from running a build's commits, a check among them, until a person reviews them. Were a seat's check to run them, the push DEC-063 denies the builder would be one commit away. A person's word at a terminal is that review's place in these commands.

**Why a question at a terminal.** The word has to come from a person, and a terminal is the one place this capability can tell a person is likely there. The landing command already asks there before it merges. It costs one account and one run, and it keeps the pull request, its author and their fix rounds where they are.

**Why the stop holds in either friction mode.** COR-050 point 12 lets an anchor with no answer pass in warning mode. The refusal gives no document at all, so nothing can be told, and what guards the answers guards what merges (DEC-065 point 5). So the stop is this record's choice, and firmer than warning mode.

**Why the merge check reads git objects too.** A merge can need a resolver its head did not. The base may have added an anchor of a kind whose script the head replaced. A head whose own check started nothing would then start its program at the merge, since a checkout runs resolvers with no refusal.

**Why escaping sits in this record.** It is the same boundary at a different door. A head reaches the account through programs, and the person through words. One such character can rewrite what the person is told just above the merge prompt.

### Alternatives considered

- **Trusting a head by its author.** Rejected. The host names who opened the pull request, not who can push to its branch. A member's fork takes pushes from whoever that member lets in, and a commit's author is whatever its writer typed. The test would read one person's standing, and the programs would come from someone else.
- **Trusting a head a reviewer approved.** Rejected. The move to review comes before any reviewer. A verdict judges a diff, not whether it is safe to run, and the head's own words reach an agent reviewer. One reading would stand between a stranger and the person's account.
- **Comparing the head's programs with the base's.** Rejected, as DEC-065 rejected it for the view: a resolver loads more than its own file.
- **Running the check from the base's resolvers.** Not taken. It would need no trust in a head, and forks could land with no person at a terminal.
  - It rests on a promise no resolver makes. COR-050 point 2 asks a resolver for no network and no writes, not that it reads the tree only as data. One that loads what the tree holds runs the head's code by another route.
  - A head that changes a resolver would be judged by the old one, so the check here and the check after the merge could part.
  - A later record could let a resolver declare that it reads the tree only as data, and run such a resolver from the base's copy. That changes what the core check decides, so it waits for forks to become routine.
- **Confining the run.** Not taken. An operating-system sandbox can run a project's check with no harness ([pkit:ADR-073] point 5).
  - A resolver that starts through `uv` cannot run in that sandbox on one platform, and some platforms have no sandbox (ADR-073 point 3).
  - The sandbox leaves most of the machine readable. Whether it holds data in with no hosts and no harness is not shown, and a probe would have to show it.
  - A later record could run a build's check there, which would lift point 9's stop where the platform allows.
- **Stripping the environment of tokens.** Not taken. It closes one route and reads as a boundary. The same account reaches the host's credential through its own tools.
- **Reading the answers from the project's own checks.** Rejected. For a fork's head, those checks run the head's copy of their definition, so their report is the head's word. Not every project runs them either (DEC-065 point 6).
- **Pushing the head to the base's repository as the way on.** Not taken. It needs no new question, and a person may still do it.
  - It gives the head the base's own checks and their secrets, and then each colleague's account at every later run. Nothing afterwards marks the commit as a fork's.
  - It starts a new pull request the fork's author cannot push to, so each fix round is another read and push.
- **Letting a build's head pass, as the repository's.** Not taken. It would spare a project with seats the stop. But it would overturn DEC-063 point 7, and one commit to a resolver would run with the seat's access, before any reviewer.
- **A flag naming the commit.** Not taken. An agent types a flag as easily as a person, and a stop line naming one invites it. The question gives the same word, and no routine run can give it.
- **Refusing with no way on.** Not taken. The stop would leave only the other merge commands, which run no change check.
- **Stripping control characters rather than escaping them.** Not taken. An escape shows the person that a head wrote one, and stripping hides it.
- **Leaving anchors of registered kinds unjudged.** Rejected. It would start nothing, as the view does. But whether an answer was asked for needs the file list a resolver gives (DEC-065), and a merge needs the check whole.
- **Starting no local reviewer on a head from elsewhere.** Not taken. It would close the words' route for that head. But it decides what ADR-066 point 10 leaves to the record that confines those runs, and it leaves such a head with no review.
- **A project setting that widens or narrows the test.** Not taken. No project has asked for one. A project that works from forks, or confines its runs (COR-050 point 2), may come to. A record can then weigh it.

## Implications

- **DEC-065.** These are refinements per this record.
  - Point 6's last item says the landing command and the move to review run only a head that passes this test or a person named.
  - Point 2's "That run" adds that at such a checkout the command is the head's own.
  - Point 3 says the command that opens the pull request takes no temporary checkout, so a refusal there costs a warning line.
- **DEC-063 and ADR-073** stand. This record brings these commands into line with DEC-063 point 7, and the reviewers' runs stay the open item each names.
- **ADR-068.** These are refinements per this record of [pkit:ADR-068] point 6, whose first item makes `<rev>` the change's own head.
  - A flag may name the change's own head beside `--head`, under the rule `PKIT_CHECK_HEAD` keeps: the commit checked, or a parent of it.
  - A run away from the commit named starts nothing that commit holds, as a promise, and its refusal has a machine-readable form.
  - `--head` alone still reads no variable.
- **The backbone** builds those two. Without the flag, a merge read from git objects could not be judged against the head (DEC-055 point 6). The capability's changeset declares the backbone it needs.
- **The commands.**
  - The review command gains a run of the change check, from git objects, for a head from elsewhere.
  - The merge check reads git objects first for every head, as the head's own check does, and takes a checkout only on the refusal.
  - The view's message on a checkout at the head says the command there is the head's own.
- **The other commands' output** waits for a sweep, which a follow-up issue carries once this record is accepted. The rule reaches past this capability, so a record on the command-line surface is its lasting home.
- **The review brief** carries point 5, and says what it outranks. The contract stays in the brief, as a builder's does (DEC-063 point 2), so no reviewer's definition changes.
- **The pm skill** says an agent stops at such a head, at the move to review and at the landing. It then asks its person to run the command at a terminal.
- **The tests** take a head from elsewhere that replaced a resolver, through a real backbone. In the move to review, the landing command and the merge check, they show no program of it started. They cover a reading that does not place the head, `--force`, an earlier head, and a merge needing a resolver its head did not. A named head starts its programs for that run alone, and a head that passes keeps its checkout where an anchor needs one.
- **The documentation.** The capability README says what a person trusts (point 8), where it says how the answers are derived and how a pull request lands. It says how to make the landing command's local branch with no checkout, and its table of overrides says this stop has no flag. The CLI README says what the backbone gains.
- **No core record changes.** COR-050 point 2 already leaves a boundary to the project.
- **No migration.** No file of an adopter's moves.
- **A surface change.** The capability and the backbone change what these commands start, what the landing command stops on, and how a head is named. The build's changesets declare it.
