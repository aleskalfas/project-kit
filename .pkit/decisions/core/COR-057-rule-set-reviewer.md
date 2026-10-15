---
id: COR-057
title: One reviewer judges a change against the accepted rules that bind on what it alters or brings under a rule
status: accepted
date: 2026-10-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **Partially superseded by [COR-060](COR-060-brought-under-breaks.md).** A break in text a change brings under a rule takes its kind as any other break the change owns, whatever brings the text under the rule. Overturned: the half of point 3's paragraph "A rule the change itself moves" where the change makes a rule bind, with the paragraph's last sentence. Also overturned: the Rationale's case of a change that accepts a rule and adds text beside it, and the premise that whoever reviews that change of the rules is placed to judge the text it brings under the rule. Among what stands: the three kinds of finding, the half where the change makes a rule stop binding, and what a change owns. COR-060's "What this overturns, and what stands" lists each passage.

## Context

A project keeps its rules in rule sets (COR-051). The backbone gives one answer to which accepted rules bind on each artefact, and writers, checks and reviewers all read that answer (COR-051 point 7). A check enforces the part of a rule that the rule's owner declares as the check's (COR-051 point 2). The rest of the rule needs judgement.

No reviewer reads that answer. A reviewer judges against what its own instructions say. So an artefact's rules reach a reviewer only when someone copies them into its instructions. A copy has no id to cite, no status and no acceptance, and it drifts from the set it was taken from. A reviewer for each kind of document, each given fixed rules, would only multiply the copies. A change can then break an accepted rule and still pass every review.

The reviewers that check a project's work form a stack, each at its own stage and with its own scope (COR-024). None of them judges a change against the rule sets.

## Decision

**A core agent, the rule-set reviewer, judges a change against the accepted rules that bind on what the change alters or brings under a rule. It takes those rules only from the rule sets, through the backbone's one answer. It judges only what the change owns, which includes the whole of an artefact the change brings under a rule, for that rule. It judges only the parts of a rule that no check is declared to enforce. It is advisory unless a gate requires it, and this record requires no one to run it.**

### 1. What it judges

The agent is named `rule-set-reviewer`. It reviews one change at a time.
- **The artefacts.** It judges each artefact the change *alters*: one the change adds or removes, or one whose content it changes (COR-050). It also judges each artefact the change brings under a rule, even one whose content the change leaves as it was (point 2).
- **Moves.** An artefact moved within the declared places is the same artefact, since its history follows the move (COR-050 point 3). So a move that keeps the content alters nothing. But it can bring the artefact under a rule, where a set's scope selects its new path and not its old one. Moving an artefact out of the declared places removes it (COR-050 point 6).
- **The container.** The methodology's container is no part of the content. A change only inside it, to an answer or to the anchors, alters nothing, and the reviewer judges nothing there.
- **The rules.** Its remit is every accepted rule that binds on an altered artefact, or on an artefact the change brings under a rule, as the backbone answers (COR-051 point 7). The rules that bind at the change's head judge what the head holds. The rules that bound at the base judge an artefact the change removes.
- **Rules that bind nothing.** A proposed, superseded or withdrawn rule binds nothing, and the reviewer judges nothing under it. A rule reached only through a pin behind its set binds nothing either (COR-051 point 7). The reviewer may still report a break of it as a finding that informs.
- **A conflict in the answer.** Where the backbone's answer names a conflict for an artefact, the conflict is validation's finding, and validation fails on it (COR-051 point 7). The reviewer judges nothing that the conflict leaves unsettled. That alone does not keep it from approving.
- **Only what the change alters or brings under a rule.** It judges no other artefact, even where the change breaks a rule that binds there.
- **No rules of its own.** Its instructions say how to judge, never what to require. They hold no rule.
- **What it reads.** It reads the change, and each artefact it judges at the base and at the head. It also reads what each rule names as what it needs, such as the artefact's anchors or the artefacts it must agree with. A fact a rule needs but does not name, it does not guess (point 3).
- **A check's part.** A part of a rule that the rule's owner declares a check enforces is that check's while the check is there (COR-051 point 2). The reviewer does not judge that part, and runs no check. A part whose declared check is not there is the reviewer's. So is every other part, even one that a script could check.
- **Never an answer.** An answer on an artefact, such as a revalidation, a deferral or a reason for having no anchors, is written by the agent making the change, where its change owes it, or decided by a person, and the answers a change owes are checked by a reviewer the project chooses (COR-050 point 3). This reviewer writes none, and judges none.
- **Read-only.** It changes nothing it reviews.

### 2. What the change owns

The reviewer judges only a break the change owns.
- **Its own text.** The change owns what it adds, and a passage it moves or copies from elsewhere. It also owns a break that its edit introduces or widens. Moving a whole artefact moves none of its passages, so the change owns none of them by the move alone.
- **What it removes.** Removing an artefact can break a rule that bound on it at the base. Removing a passage can leave the artefact breaking a rule at the head. The change owns both breaks.
- **What it brings under a rule.** A change *brings an artefact under a rule* when the rule binds on the artefact at the head and did not bind on it at the base. Changes that can do so include:
  - a change to the rule sets, such as widening a set's scope, accepting the rule, or updating a pin
  - a change to the places, such as declaring or widening a place, or typing a place
  - moving the artefact to a path a set's scope selects

  For that rule, the change owns the whole of the artefact's content as the head holds it, whether it alters the artefact or not. A break of that rule there is the change's, though the text was there before. An artefact the change adds is brought under every rule that binds on it.
- **A break it says it fixes.** A break that was there before becomes the change's own when the change says it fixes it, and the break survives.
- **Everything else** that was there before is not the change's own, even where the change edits beside it.

### 3. Its findings, and what binds

A judgement under an accepted rule binds where the change owns the passage. Taste binds nothing. The reviewer has no rules of its own, so it makes no finding of taste. Each finding cites its rule by id (COR-051 point 3). It names the artefact, quotes the passage, and says what in the passage breaks the rule. A finding is one of three kinds:
- **A settled break.** The change owns the break, and the rule's text settles it with no reading left to choose. It withholds the reviewer's approval.
- **A passage for a person.** The rule binds and the change owns the passage. But judging it needs a reading the rule does not settle, or a fact the rule does not name. It withholds no approval, and waits for a person's judgement.
- **A finding that informs.** It is a break the change does not own, with the reason it is not the change's. It may also be a break of a rule that a pin behind its set holds back. It withholds nothing and holds nothing.

**A rule the change itself moves.** The change may make a rule bind or stop binding on an artefact it alters, through the rule's status, a scope or a pin. Whether that rule should then judge the passages the change owns there is a reading the rule's text does not settle. So a finding under that rule, on such a passage, is a passage for a person. Whoever reviews that change of the rules judges the text the rule now reaches.

**Its verdict.** The reviewer approves only when it judged the change and found no settled break. A reviewer that cannot judge the change does not approve, and says why. It cannot judge the change while a rule that binds on it cannot be judged. A fact the rule names that cannot be found is such a case.

**Its form comes from whoever invokes it.** Whoever invokes the reviewer, such as a gate, names the form of its verdict. The same invoker names the mark of each kind of finding. Where nobody names them, the reviewer states its verdict and each finding's kind in words. How a passage for a person reaches a person is the gate's to say.

### 4. Placement: core

It passes the test for a core agent (COR-026). A project that installs no capability still finds it useful, since rule sets are core and a project may keep its own. Its instructions name only what core defines: rule sets, the backbone's one answer, artefacts and their content. They name no capability, no gate's form and no rule.

### 5. Stage and posture

It reviews a diff, beside the convention-compliance reviewer in the reviewer stack (COR-024). The two judge the same diff on different questions.
- **Advisory.** A person or an agent may run it on any change by hand. A *gate* is a step a change must pass before it lands. The reviewer's verdict holds a change only where a gate requires it, and only as that gate says.
- **A contribution.** A component *contributes* the reviewer to a gate when the component makes that gate require it. A project may also add the reviewer to a gate of its own.
- **No review is required.** This record requires no one to run the reviewer, and no project needs a gate to use it.

### 6. What a contribution covers

A component may contribute the reviewer. It then contributes it for every artefact a change alters on which an accepted rule binds, at the base or at the head. It also contributes it for every artefact a change brings under an accepted rule. It does so for the artefacts of every owner, not only its own. So one contributor installed is enough for every such artefact to be judged at the gate.

### 7. Rule sets and a project's prose conventions

The reviewer reads rule sets only. A project may also keep conventions in prose, with no ids and no statuses. They guide the agents that produce its work, and the reviewers that read them. The rule-set reviewer cites none. A convention about an artefact that should bind through this reviewer moves into a rule set. There it gains an id, an origin and a status that only a reviewed change accepts (COR-051 point 4).

### 8. Evidence before a gate

The reviewer stack kept the critic and the architect advisory first (COR-024), and this reviewer starts the same way. A component contributes it to a gate only on evidence that it judges well when run by hand. This record names no bar for that evidence.

## Rationale

**Why one reviewer that reads the rules.** A rule copied into a reviewer's instructions loses what makes it a rule. It loses an id a finding can cite, a status, and the review that accepts it (COR-051). It also drifts from the set it came from. A reviewer that reads the backbone's one answer judges exactly the rules that bind, and nothing a copy kept after the set changed. One contract then serves every kind of artefact. What differs between kinds lives in the rule sets, where a project already keeps it. The reviewer stack rejected one reviewer for two roles at different stages (COR-024). This is one role, at one stage.

**Why its instructions hold no rule.** A rule written into the instructions would bind wherever the agent runs, with no status and no scope. It would also bind past the pins that hold back a shared set's new rules (COR-051 point 7).

**Why the base's rules judge only a removed artefact.** A removed artefact is not at the head, so no rule binds on it there. Yet removing it can break a rule that bound on it, and only the base's rules can say so. An artefact that remains is judged at the head, where a removed passage shows as what the artefact now lacks. Judging it under the base's rules too would draw two findings for one break.

**Why the container is left out.** It holds the answers, which are a person's (COR-050 point 3), and the anchors, whose change the friction checks already bring to a person. A change only there would otherwise draw a review of text nobody changed. The cost is that a rule about an artefact's anchors goes unjudged here on a change that touches only the anchors.

**Why only what the change alters or brings under a rule.** Every artefact a change could affect is, through anchors and rules, most of a project. Judging only what the change alters, and what it brings under a rule, keeps a review to the change. The cost is a break the change causes in an artefact it neither alters nor brings under a rule, such as a removed definition that another artefact still uses. Such a break is the business of a check, or of a rule that binds on the removed artefact too.

**Why it never judges a check's part.** A part judged twice draws two findings, and the two can disagree. The rule's owner says which part a check settles (COR-051 point 2), and the reviewer takes the rest. A part whose declared check is not there comes back to the reviewer. COR-051 point 2 hands it to whoever judges the rest of the rule.

**Why only what the change owns.** Otherwise a change that touches an old artefact would answer for every break the artefact already held. Each change would have to mend the past before it could land. A break the change says it fixes is its own, because a surviving break makes that claim false. Moving an artefact whole changes none of its text, so the change owns none of the text's breaks by the move alone. A move into a set's paths brings the text under that set's rules, as "Why a change owns the whole of what it brings under a rule" says. Following a move is a guess (COR-050 point 3). A move the backbone does not follow reads as a removal and an addition, and the change then owns the whole text. That errs toward too many findings, never too few.

**Why a change owns the whole of what it brings under a rule.** Text can come under a rule without being edited, in the ways point 2 names. A later change owns only what it edits. So if the change that brings the text under the rule did not own it, no change would, and its breaks would only inform. The rule would then claim to cover text that nobody checks. The change that brings the text under the rule is the one that makes that claim, so it answers for the text. It owns the text for that rule only. A rule that bound there at the base judges only what the change edits, so the change does not answer for the artefact's whole past. The costs:
- **A review of everything a rule newly reaches.** That can be much of a project, and a person judges each passage whose reading the rule does not settle.
- **A scope can widen a folder at a time.** A set that widens its scope so, or leaves files out of it (COR-051 point 2), keeps the review to what it brings in. A rule accepted, or a pin updated, reaches the set's whole scope at once.
- **A component's release can bring text under a rule.** A release that adds or types a place brings the project's text under the rules that select it, though the project made no choice to bring it there. The change that takes the release answers for that text.
- **Nothing comes under a rule that binds at both states.** A rule whose text a change tightens judges only what the change edits. So does a rule that a set's new major keeps, where one change takes the major and updates the pin to it. Taken in two changes, the pin's update brings every rule of the set under it. A successor rule is a rule of its own, so the change that accepts it brings its whole scope under it.

**Why a passage for a person withholds no approval.** A judgement call that withheld approval would hold the change until someone overrode the reviewer, and overriding would become a habit. A judgement call that only informed would reach nobody. So it waits for a person, and withholds nothing. The rule binds, so the judgement is owed. The cost is that a gate which reads only the verdict brings it to nobody, so the gate decides how it reaches a person.

**Why a rule the change moves goes to a person.** Take a change that accepts a rule and adds text beside it. It would otherwise be held by a rule that was not yet accepted when the text was written. A change that retires a rule and removes an artefact it bound on would be held by the rule it retires. In both, whether the rule should judge that text is the question the change itself puts. Accepting a rule is a reviewed change, a person's review where a person takes part (COR-051 point 4). A change that retires a rule, or moves a scope or a pin, changes the rule sets too. Whoever reviews that change of the rules is placed to judge the text it reaches.

**Why it makes no finding of taste.** It has no rules of its own, and taste binds nothing, since no review accepted it as a rule. A finding of taste would also cite no rule, where every other finding cites one.

**Why a reviewer that cannot judge does not approve.** An approval says the change was judged. A reviewer that could not read the rules, or the change, has judged nothing, and an approval would claim it had. A rule it cannot judge leaves the change judged only in part, and an approval would claim the whole. A fact a rule names but nobody can find is such a case. The rule's owner said where the fact is, so its absence is a fault to mend, not a reading to choose.

**Why the form comes from whoever invokes it.** A gate belongs to whoever runs it, and so does the form of the verdicts it reads. A core agent that fixed that form would tie core to one gate. Taking the form from its invoker keeps the reviewer one agent wherever it runs, by hand or at a gate.

**Why core.** Rule sets are core, and so is the one answer the reviewer reads. A project with rule sets of its own and no capability installed can still run it. A capability that shipped the reviewer would make judging against rules need that capability installed. Yet the rules reach beyond any one capability's discipline (COR-026).

**Why advisory, and why no review is required.** The critic and the architect started advisory (COR-024), and so does this reviewer. Requiring it everywhere would make every project pay for a gate before anyone knew whether its findings were right. Whoever runs a gate is placed to decide when to add it.

**Why a contribution covers every ruled artefact.** The reviewer's question is the rules', not the contributor's. The rules bind across components, through the sets a project keeps. A contributor that covered only its own artefacts would leave the rest unjudged wherever it is the only contributor installed. A component usually contributes reviewers of its own discipline, over its own work. This reviewer's discipline is core's, so it serves every artefact the rules reach.

**Why prose conventions stay apart.** Binding criteria kept in two places drift apart. Prose conventions carry no id, no status and no acceptance, so a finding could not cite one precisely. Keeping the reviewer to rule sets gives every finding that binds a rule that a review accepted.

**Why evidence before a gate, and no bar here.** The reviewer stack kept the critic and the architect advisory until experience showed more was needed. It made a gate a decision of its own (COR-024). This reviewer's gate is a component's contribution, and what it must show first is that it judges well. A gate that blocks wrongly costs every change it judges. Runs by hand show how often the reviewer is wrong, at no cost to anyone's change. A component's contribution changes the gate of every project that installs it, so it waits for that evidence. A project that adds the reviewer to its own gate decides for itself. What the evidence must show depends on what the gate holds, and what a wrong block costs there, so this record names no bar. The cost is that the evidence comes from the rules the reviewer was tried on. A project whose rules differ meets it at the gate untried on them.

**Why a record of its own.** The rule-set record stays about rules and their machinery. The reviewer stack introduced its agents in a record of their own (COR-024), and this reviewer follows it. The stack's own statement is refined in place to admit it.

**Why the name.** It is `rule-set-reviewer`, not `rules-reviewer`. The methodology's operational rules for agents share the word, and they are not rule sets (COR-051 point 1).

### Alternatives considered

- **A reviewer for each kind of document, each given fixed rules.** Rejected. Each copy of a rule loses its id, its status and its acceptance, and drifts from its set.
- **The convention-compliance reviewer also reads the rule sets.** Rejected. One agent would judge a diff on two questions, from two sources of binding criteria.
- **The review in the rule-set record.** Rejected. That record would carry a reviewer's discipline beside the rules' machinery.
- **A capability ships the reviewer.** Rejected. Judging against rules would need that capability installed, though rule sets are core.
- **The component that runs a gate requires the reviewer in every project.** Rejected. That component would add a reviewer of a discipline it does not own to every project's gate, whether the project keeps rules or not.
- **A gate from the start.** Rejected. Nobody yet knows how often it blocks wrongly.
- **Core requires the review.** Rejected. Core runs no gate, and a project that keeps rules with no gate still runs the reviewer by hand.
- **A contribution that covers only the contributor's own artefacts.** Rejected. Where one contributor is installed, every other ruled artefact would go unjudged at the gate.
- **Each project gathers its own evidence before a contribution applies.** Not taken. Every project would repeat the same trial, and the evidence a contribution needs would no longer be the contributor's.
- **The reviewer also reads a project's prose conventions.** Rejected. Binding criteria in two places drift, and a prose convention carries no id, status or acceptance.
- **The reviewer fixes the form of its own verdict.** Rejected. It would fix the form of a gate that core does not run.
- **It judges the parts a check enforces too.** Rejected. One part judged twice draws two findings that can disagree.
- **A judgement call withholds approval.** Rejected. It holds the change until someone overrides the reviewer, which trains the habit of overriding.
- **Every break in an altered artefact is the change's.** Rejected. A change that touches an old artefact would answer for its whole past.
- **Text a change brings under a rule stays unowned until a change edits it.** Rejected. The rule would claim to cover text that nobody checks, and no later change would answer for it.
- **A change to an artefact's anchors alters it, for this reviewer.** Not taken. The friction checks already bring an anchor's change to a person, and the content they rest on is unchanged.
- **A shared principle of what any change owns, for every reviewer.** Not taken here. This record states what a change owns for its own reviewer. Lifting it would bind reviewers this record does not govern.

## Implications

- **The agent ships among the core agents,** under the agent contract (COR-013), and is deployed like any other core agent. Its instructions name no rule.
- **The backbone gives the reviewer what it reads,** before the agent ships:
  - its one answer at a change's base and at its head
  - each artefact followed across the change, by the same pairing the friction checks use (COR-050)
  - for each part a check is declared to enforce, whether that check is there
  - the rules a pin behind its set holds back, beside the rules that bind
  - the rules the change brings each artefact under, and each artefact it brings under a rule without altering it
- **A change to the agent's instructions** changes every gate that requires the reviewer. So it is a surface change of the backbone (COR-010).
- **The reviewer stack is refined in place,** atomically with this record's acceptance. Its statement of the stack admits the rule-set reviewer, on the diff, beside the convention-compliance reviewer (COR-024).
- **Components** whose artefacts a project's rules may reach may contribute the reviewer to a gate, once they hold the evidence of point 8. A contribution covers every ruled artefact (point 6). Core runs no gate, so nothing in core checks a contribution. Points 6 and 8 bind the contributor as its own discipline.
- **Projects** run the reviewer by hand on any change, and may add it to a gate of their own.
- **Rule owners** take a part of a rule off the reviewer by declaring a check for it (COR-051 point 2). A rule that needs a fact names where to find it. Otherwise its judgement goes to a person.
- **No project's state changes.** The agent is an addition, so no migration is due (COR-010).
- **The agents reference** lists the reviewer once it ships.
