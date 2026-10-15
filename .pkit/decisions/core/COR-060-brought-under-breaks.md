---
id: COR-060
title: A break in text a change brings under a rule is settled where the rule settles it, whatever brought the text there
status: accepted
date: 2026-10-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The rule-set reviewer judges a change against the accepted rules that bind on what the change alters or brings under a rule (COR-057). A change *brings an artefact under a rule* when the rule binds on the artefact at the head and did not bind on it at the base. For that rule, the change owns the whole of the artefact's content, whether it edits the artefact or not (COR-057 point 2). Each finding of the reviewer is a settled break, which withholds its approval, a passage for a person, which waits for a person's judgement, or a finding that informs (COR-057 point 3).

Many kinds of edit bring text under a rule. A change can accept the rule, change what a set inherits or its pin, or widen a set's scope. It can also declare, widen or type a place, or move an artefact to a path a set's scope selects.

COR-057 point 3 makes the kind of a break depend on which of them did it. Where the change makes a rule bind on an artefact it alters, through the rule's status, a scope or a pin, a finding under that rule is a passage for a person. Its premise is that whoever reviews that change of the rules judges the text the rule now reaches. A break in text brought under a rule by any other edit, such as what a set inherits, a place, a type or a move, takes its kind as any other. So the same break withholds approval when one edit brings the text under the rule, and nothing when another does. Under one widened scope, a break in a file the change edits even goes to a person, while the same break in a file it leaves alone is settled.

## Decision

**A break of a rule in text a change brings under that rule takes its kind as any other break the change owns. Where the rule's text settles it, it is a settled break, whatever brings the text under the rule. No change declares an exception for itself alone: the ways out of such a break are the ones a project already has. This overturns the paragraph "A rule the change itself moves" of COR-057 point 3, for a rule the change makes bind. For a rule the change stops from binding, that paragraph stands.**

### 1. One kind, whatever brings the text under the rule

A break of a rule in text the change brings under that rule is the change's (COR-057 point 2). It takes its kind as any other break the change owns (COR-057 point 3). Where the rule's text settles it, it is a settled break, and it withholds the reviewer's approval.

That holds whatever brings the text under the rule, such as the rule's status, what a set inherits or its pin, a set's scope, a place, a type or a move. It holds on an artefact the change adds, on one it changes, and on one it leaves as it was.

### 2. No exception of its own

No change declares an exception for itself alone. What a change, or what it says of itself, declares about a break leaves the break's kind as it is. A scope and a rule's wording are no such exception, since they sit in the rule sets and hold for every change.

Besides mending the text, or not bringing it under the rule, a change from which such a break withholds the reviewer's approval has these ways out:
- **The scope.** A change can widen a set's scope a step at a time, or leave a file out of it until the file is mended (COR-051 point 2). The scope's edit is part of the change, where its reviewers see it. A file a set's scope leaves out is out of each rule that binds on it only through that set, and so can be out of more than the rule it breaks.
- **The rule's own reach.** Some text must stay as it is, such as a quotation, legal wording, generated output or an exact message. The rule's own wording leaves it out, or the scopes of the sets the rule binds through there do. The wording is decided where the rule is written, and a scope is the project's. A rule a component ships is worded by its owner. A project that holds that wording wrong proposes a change to the owner, or does not inherit the set (COR-051 point 7).
- **A wrong judgement.** Where a gate requires the reviewer, its verdict holds the change only as that gate says, and the gate says whether and how a person overrides the reviewer. This record counts that as a way out only for a judgement held wrong. While no gate requires the reviewer, its verdict holds nothing (COR-057 point 5).

### What this overturns, and what stands

This record partially supersedes COR-057. Each overturned passage stays in COR-057 as it stood.
- **Overturned:**
  - in point 3's paragraph "A rule the change itself moves", the half where the change makes a rule *bind* on an artefact it alters, through the rule's status, a scope or a pin. A finding under that rule, on a passage the change owns, takes its kind as point 1 here says.
  - the same paragraph's last sentence, "Whoever reviews that change of the rules judges the text the rule now reaches"
  - in the Rationale's "Why a rule the change moves goes to a person":
    - the case of a change that accepts a rule and adds text beside it, and "In both, whether the rule should judge that text is the question the change itself puts", for that case
    - "Whoever reviews that change of the rules is placed to judge the text it reaches", as far as that text is text the change brings under the rule
- **Stands:**
  - the three kinds of finding, and what each withholds
  - the half where the change makes a rule *stop* binding, through the rule's status, a scope or a pin: a finding under that rule, on a passage the change owns, is a passage for a person
  - in the Rationale's "Why a rule the change moves goes to a person":
    - the case of a change that retires a rule and removes an artefact it bound on, and "In both, whether the rule should judge that text is the question the change itself puts", for that case
    - "Whoever reviews that change of the rules is placed to judge the text it reaches", for the text of an artefact the change removes
  - what a change owns, the whole of an artefact it brings under a rule included (COR-057 point 2)

## Rationale

**Why one kind, whatever brings the text under the rule.** The break is the change's, since the change owns the text it brings under the rule. In text a rule binds on at the head, a break the change owns takes its kind from the rule's text: settled where the text settles it, a passage for a person where it does not. How the text came under the rule changes nothing the rule's text settles. If it decided the kind, an author could choose the edit whose breaks withhold nothing, or edit a file to soften its breaks. A break the rule settles would then reach a person as a judgement call, among every passage the rule comes to reach. A change that tightens a rule's text brings nothing under the rule, so this record does not reach it. That cost stays COR-057's.

**Why a review of the rules does not judge the text.** Accepting a rule is a reviewed change (COR-051 point 4), and so is updating a pin (COR-051 point 7). Widening a scope changes the rule sets too. But the text such a change brings under a rule is not in its diff. Whoever reviews the change judges the rule, and does not see each passage the rule comes to reach. So the rule-set reviewer judges that text as it judges any other text the change owns.

**Why a rule the change stops from binding is not decided here.** That case arises only on an artefact the change removes, since only the base's rules judge a removed artefact (COR-057 point 1). A removed artefact is not at the head, so the rule claims no text there. The reason a change owns the text it brings under a rule, that the rule would otherwise claim text nobody checks (COR-057, "Why a change owns the whole of what it brings under a rule"), does not reach it. Whether the rule should judge that text is the question the change itself puts, about the rule rather than a passage. A change can stop a rule binding to soften a break. On an artefact it removes, the break then reaches a person, and the edit of the rule sets is in view of its reviewers. On one it keeps, the rule judges nothing at the head, and the edit of the rule sets is what its reviewers see.

**Why no exception of its own.** A scope and a rule's wording keep text out of a rule in the open, for every change. An exception a change declares for itself alone would let the rule claim text that nobody checks. What a gate lets a person override is the gate's to say. This record counts it as a way out only for a judgement held wrong, which leaves the rule as it is. Leaving a file out of a scope costs a line in the change, in view of its reviewers, so overriding the reviewer need not be the cheaper way to land a rule.

**The costs.** COR-057 names what a change takes on when it owns the text it brings under a rule ("Why a change owns the whole of what it brings under a rule"). Under this record, each settled break in that text withholds approval, however the text came under the rule.
- **Settled breaks across a set's whole reach.** A change that accepts a rule, updates a pin, or takes a component's release that adds or types a place can meet them at once, though it edits none of that text. Updating a pin in a change of its own meets settled breaks of every rule of the set (COR-057, "Nothing comes under a rule that binds at both states").
- **Leaving a file out is coarse.** Until the file comes back in, it is out of the rules it does not break too (point 2). A scope leaves out whole files, so a passage that must stay as it is, inside a file a rule should judge, needs the rule's own wording. A project's own new rule can come in through a set of the project's whose scope widens a step at a time.

### Alternatives considered

- **How text comes under a rule decides the kind of a break in it.** Rejected. A wider scope, an accepted rule or an updated pin would send a break to a person, and a place, a type or a move would settle it. An author could then choose the edit whose breaks withhold nothing.
- **Every break in text brought under a rule goes to a person, however it came there.** Rejected. A break the rule settles would withhold nothing, and a person would judge one by one every passage the rule comes to reach.
- **An exception a change declares for itself alone.** Rejected. A scope and a rule's wording keep text out of a rule in the open, for every change. A gate's override, where a gate has one, counts here only for a judgement held wrong. An exception of the change's own would let the rule claim text that nobody checks.
- **The same kind for a rule the change stops from binding.** Not taken here. The rule claims no text at the head there, so it claims none that nobody checks. A change can stop a rule to soften a removal's break, and that edit of the rule sets is in view of its reviewers.

## Implications

- **The rule-set reviewer** gives a break in text the change brings under a rule its kind as any other. On an artefact the change does not add, each such finding names the edit that brought the artefact under the rule, and a settled break points to point 2's ways out. An exception the change declares changes no finding's kind.
- **COR-057's top line** says it is partially superseded by this record.
- **No project's state changes,** so no migration is due (COR-010).
