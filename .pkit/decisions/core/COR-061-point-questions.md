---
id: COR-061
title: A data point may declare a question, asked after an install or a transition
status: accepted
date: 2026-10-18
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a capability that needs the person's own answer about a data point it defines may name, on the point, a command of its own that asks and records the answer. The backbone runs that command after a capability's install or upgrade, and after a version transition, where a person can answer at a terminal. With nobody there it asks nothing, and prints the command to run later. The routine sync never asks. Only the person's answer is the consent, and until they answer, the capability takes no choice in their place.

## Context

A capability may need a choice only the person can make, about a data point it defines (COR-053 point 2). The point's definer keeps the answer in its own state. Other capabilities contribute to the point, so a new entry can arrive with any capability's install or upgrade. The moment the person takes up a discipline is that install, and the person is often at a terminal then.

No capability can ask inside another's install:
- **Install and a transition are operations of the core layer** (COR-017, COR-059 point 3). The backbone runs a capability's command only in the roles a record gives it, such as a filler, a validator or a subscriber, and none of those asks a person.
- **A migration of the contributing capability** could run the definer's command only by naming the definer, which connection points exist to avoid (COR-053). It also runs inside the transition, whose one consent is the choice of its target (COR-059 point 4).
- **An event subscriber** runs bounded, after a writing command, with no consent of its own (COR-053 point 9). A question needs a person, and the answer is a consent.

So asking at install and at a transition needs the backbone to run the question. Two accepted records bound how:
- COR-017 rejects install asking whether to create a declared project rule set, since a run with nobody to answer would take that choice silently.
- COR-059 point 4 lists the choices that keep their own consent within a transition, and point 2 keeps the merge tier that prompts out of reconciliation.

## Decision

**A data point's definer may declare a question on the point: a command of its own that asks the person and records each answer they give. The backbone runs it after a capability's install or upgrade and after a transition of the backbone, only where a person can answer. With nobody to answer it runs nothing, and prints the command to run later. Reconciliation never asks. Only the person's answer is the consent, so the question keeps its own consent, and until the person answers, the definer takes no choice in their place.**

### 1. A data point may declare a question

- **On the point the definer accepts.** A data point may name a question: a command of its definer's own. A contribution and an offered point name none. The question is optional.
- **What it is for.** A choice that installing the definer does not already make: one about the entries other components bring to the point, or an authority only the person can give. A choice that installing the definer makes is install's own, as COR-017 sets for the declared project rule set.
- **What the command does.** It asks the person what it needs about the point, records each answer they give in the definer's own state, and ends. It writes nothing but those answers, and runs no operation of the core layer. The backbone runs it with no argument. It reads what it needs itself, such as the point's value and the answers already recorded.
- **It asks only what has no recorded answer.** The trigger is state, not an event. So the command decides what to ask, and asking nothing is a normal outcome.
- **An answer covers what the question named.** An entry it did not name has no answer, even where a provider or a contributor was replaced for another that is the same to the wiring (COR-053).
- **The words and the record are the definer's.** The backbone sees neither.
- **The person may run the command at any time,** as any command of the definer's.

### 2. It runs after an install and after a transition

- **Three operations run it:**
  - a capability's install, its registration included (COR-031)
  - a capability's upgrade, whatever its origin
  - a transition of the backbone
- **Which questions:**
  - for a capability's install or upgrade, the question of each point the capability defines, and of each point its contributions reach
  - for a transition of the backbone, every question. Every shipped capability moves (COR-059 point 7), and each command asks only what waits.
  - only a point an active provider defines (COR-053 point 1), each point's question once in a run
- **After the operation, and no part of it.** A question runs once the operation is complete and has made every write of its own. A transition of the backbone has recorded its completion (COR-059 point 6). The question is the definer's command, which the command that ran the operation starts afterwards. It is no operation of the core layer, so that command still runs exactly one (COR-059 point 5).
- **A preview** runs no question, and names each one the operation would run.
- **No other operation runs a question.** Reconciliation never does (point 4).

### 3. Only where a person can answer

- **Where a person can answer,** the backbone runs each question in turn and hands it the terminal. It sets no time bound, since a person answers.
- **With nobody to answer,** it runs none, and nothing is recorded. For each question it would have run, it prints the command, for the person to run later. It cannot tell whether anything waits, so that command may have nothing to ask.
- **A question that fails** is reported with its command, and the next question still runs.
- **A person who stops the questions** leaves the rest unasked, and each is printed with its command.
- **Neither undoes the operation,** nor changes its outcome. The operation was complete before the first question ran.

### 4. Reconciliation never asks

Reconciliation runs no question, whether or not a person can answer. A question left unanswered waits for the next install, upgrade or transition, or for the person to run the command.

### 5. Only the person's answer is the consent

- **Running the operation is never the consent.** Choosing a transition's target consents to its parts (COR-059 point 4). It gives no answer to a question.
- **The command records only an answer the person gave.** With nobody to answer, nothing is recorded.
- **Until the person answers, the definer takes no choice in their place.** It treats an entry with no answer as one the person has not consented to. As for a value a capability offers to record (COR-048 point 5), with nobody to ask nothing is written and the default applies. Here the default is no consent.
- **This record names the question's command as the writer of its answers,** with the person's answer as the consent (COR-001's rule on writers). The backbone itself writes no answer.
- **So a question keeps its own consent,** among the choices COR-059 point 4 lists, and no choice is taken silently.

### 6. What waits between operations

Entries can reach a point without an install or a transition, such as through a project filler or a change of provider (COR-052, COR-053 point 7). Such an entry waits for the next operation that asks. Meanwhile the definer may report what waits for an answer, naming the command, through its validator, at a severity that does not fail (COR-055 points 3 and 5).

## Rationale

**Why the definer asks.** The definer gives the point its meaning, and keeps the answers in its own state. A contributor never names the definer (COR-053), so it cannot ask the definer's question. The backbone knows only which commands to run and when, so it holds no discipline's words.

**Why the backbone runs it.** No capability can ask inside another's install. The backbone already runs the install, the upgrade and every transition, and knows which capability moves. A migration cannot serve: it would name the definer, and it runs inside the transition, under the target's consent.

**Why the command decides what to ask.** Whether anything waits for an answer depends on the point's value and the answers recorded. Only the definer can read the answers. So the backbone runs the command, and the command may ask nothing. That covers the cases a trigger tied to one release misses:
- installing the definer after a contributor
- a contribution a later release adds
- an upgrade after an install that had nobody to answer

**Why after the operation, and outside it.** By then the operation's writes are done, and a transition's completion is recorded. A question that is stopped or fails then leaves no operation half done. The point's value it reads is the one the operation leaves. Outside the operation, the question is no part of the transition's one consent, and the core layer's operation stays one (COR-004). An event's subscribers already run this way: after the command that emits the event, and a failing one never undoes that command (COR-053 point 9).

**Why only at a terminal.** A question asked with nobody to answer would hang, or be answered by a default. A default answer takes the choice silently, which COR-017 rejects for install. With nobody to answer, nothing is recorded, and the printed command lets the person answer later.

**Why, with nobody to answer, the backbone prints the command and runs nothing.** The question is a writing command. Running it with nobody watching, trusting it to ask and write nothing, would give it a second contract that the backbone cannot check. The printed command is the backbone's own, so it is safe whatever the definer's command would do. The cost is noise: with nobody at a terminal, the command is printed even where nothing waits. A definer that reports what waits (point 6) gives the person the signal the printed command cannot.

**Why reconciliation never asks.** It is the routine refresh, which never asks (COR-004). It moves no version and installs no capability (COR-059 point 2). A question it skips waits for the next operation that asks.

**How this differs from COR-017's rejection.** COR-017 rejects install asking whether to create the declared project rule set. There, installing the capability already makes the choice, and a run with nobody to answer would make it silently. A question is only for a choice installing the definer does not make (point 1). With nobody to answer, nothing is recorded and the definer takes no choice in the person's place (point 5). So asking takes nothing silently.

**What it cannot ensure.**
- **A terminal is not proof of a person.** A program holding the terminal can answer. The same limit holds for the other choices COR-059 point 4 lists, which ask where a person can answer.
- **An entry that arrives without an operation that asks** waits, as point 6 says. So does an entry an externally-sourced capability brings, whose content reaches the project by reconciliation after its pin moves (COR-041, COR-059 point 3).
- **No flag skips the questions at a terminal.** A person who stops them gets the rest printed (point 3), and a run with no terminal is never asked.

### Alternatives considered

- **A migration of the contributing capability runs the definer's command.** Rejected: it names the definer, runs once for each version, and runs inside the transition under the target's consent.
- **The backbone words the question and records the answer itself, from the point's declaration.** Rejected: the backbone would hold a discipline's words, and write a state the definer owns.
- **A question on each contribution, asked by its contributor.** Rejected: the answer is the definer's state, and one point's contributors would each ask their own way.
- **The question as a part of the transition.** Rejected: its consent is the person's answer, not the target, and a part runs before the completion is recorded, so a question stopped there would leave the transition incomplete. A capability's install, which also asks, is no transition, so the operations would place the question two ways.
- **Externally-sourced definers left out of the run.** Rejected: the backbone already runs such a capability's fillers, validators and subscribers. COR-059 point 3 keeps its migrations out of a transition, and a question runs after the operation, under the person's answer, as no migration does.
- **A question on the capability, for its own install, not tied to a point.** Not taken now: the need is a choice about the entries other components bring, and only the point ties those entries to their definer. A value a capability offers to record on its own install (COR-048 point 5) is for a record of its own, when one needs it.
- **Sync asks too.** Rejected: a routine refresh never asks.
- **The command runs with nobody to answer, and prints only what waits.** Rejected: see "Why, with nobody to answer, the backbone prints the command and runs nothing".
- **A second command for each question, a query that says what waits.** Not taken now: it would let the backbone print only where something waits, at the cost of a second command for each question. Point 6 lets a definer report what waits without it.
- **A default answer where nobody answers.** Rejected: it takes the choice silently.
- **Ask only in the release that first brings a point's question.** Rejected: it misses an install with nobody to answer, and a contributor installed later.

## Implications

- **COR-059** is refined in place:
  - point 4's list of the choices that keep their own consent names a point's question, and with nobody to give it, a question records nothing
  - point 5 says that a point's question, run after the operation, is no second operation
- **COR-004's** anchoring paragraph says the same, beside the update of the CLI.
- **The package-metadata reference** names the key that declares a question on an accepted data point. It also names the check that the command is one of the definer's commands, and that it is not declared a query command (COR-052 point 6), since a question writes.
- **The lifecycle and command references** say how the backbone runs a question, which questions each operation runs, and what it prints with nobody to answer.
- **A capability that declares a question** says in its own records what it asks, where it records each answer, that it asks only what has no answer, and what it does with an entry that has none.
- **The realisation** is the implementing project's: how a terminal is told apart, the order the questions run in, and the wording of what is printed. Its decision of the version transition says where the questions run after it.
