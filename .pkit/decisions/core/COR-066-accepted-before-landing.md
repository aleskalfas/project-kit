---
id: COR-066
title: A decision reaches the default branch only accepted
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a decision record or a rule is a proposal only inside the change that proposes it. A person accepts it there, before work rests on it, and it reaches the default branch accepted. A check of its own refuses a merge, or a direct commit, that would land a proposal, and the person who authorises a change to land sees first every record and rule it makes accepted. A project turns the refusal on when it chooses.

## Context

The decision-record specification and [COR-025](COR-025-adr-decision-space.md) let a record land on the default branch as `proposed`, and be accepted later in a separate step. [COR-051](COR-051-rule-sets.md) point 4 gives rules the same statuses. A proposed record or rule binds nothing, and accepting one stays a person's ([COR-064](COR-064-answer-delegate.md) point 6), so no agent decides alone. A proposal that lands, though, stays on the default branch with nothing to end it: it reads like a decision beside the accepted ones, and later work may build on it or decide its question without citing it.

## Decision

**A decision record or a rule reaches the default branch only accepted, by a person, within the change that proposes it. A check of its own refuses to land a proposal, and what a change makes accepted is shown to the person before they authorise it.**

### 1. A proposal lives only in its change

A decision record or a rule is proposed only within the change that proposes it. A person accepts it in that change, before work in the change rests on it, and an agent writes `accepted` only once a person has; until then it reads `proposed` on its branch. Work in a change built on that one may rest on it once it is accepted, and reaches the default branch no earlier than that change does. A proposal that is refused is the change closed, so it never lands. A refused proposal whose reasoning is worth keeping becomes a scratchpad note, abandoned with the reason it was refused ([COR-012](COR-012-scratchpad-notes.md)).

This overturns COR-025's "ADRs land as `proposed`", and the specification's practice of landing records proposed. A person's acceptance stays a separate act, made within the change. The statuses stand: a proposed record or rule binds nothing, and it exists only on the branch of the change that proposes it.

### 2. A check of its own refuses to land a proposal

A check of its own, apart from a change's other checks, reports each record or rule proposed at the change's head and not proposed at its base: an added proposal, or an accepted one set back to proposed. A record or rule moved to another path is not added. The check fails while it reports one.

- **Through a merge.** A component that carries out merges on a person's authority runs it before it merges, after the reviewers have judged the change, proposal included, and refuses to merge while it fails. A project without such a component has its host require the check for a merge, reported on a line of its own, so its failure while a proposal is discussed blocks no push and hides no other check.
- **By a direct commit** to the default branch. The person accepts the record before the commit, and the check runs on the commit before it is pushed.
- **Nowhere else.** A check run before a push, and the decisions check a project runs on each change, leave it out.

A record or rule a project receives from elsewhere is judged where it is kept: the check skips it. A proposed record or rule already on the default branch blocks no change; point 4 says how it is settled.

### 3. The person sees what the change makes accepted

The same check lists each record and rule the change makes accepted, added accepted or set to accepted. For each, it shows the commit that set it to accepted, the change's commits before that one that touch anything else, and the record's edits since. The person who authorises the change to reach the default branch sees that list first, shown by the component that carries out merges or, without one, by the change's author, and reads there the text that lands. An edit made to a record after its acceptance in the change is accepted only through this list. The check cannot tell who wrote a status: where no component shows the list, only the author's word says the person saw it.

### 4. A project turns the refusal on

Point 1 binds every project. A project turns on point 2's refusal with a key in its backbone configuration that this record owns ([COR-048](COR-048-backbone-configuration.md) point 2). With the key absent, the refusal is off. Point 3's list is shown either way. The key counts as the default branch holds it when the check runs, so a change that turns it on or off counts only once it has landed, and the person who authorises that change sees it. Its writers are an install and a change a person authorises, each with consent as COR-048 point 5 asks. An upgrade does not write it.

When a project turns the refusal on, the check lists each proposed record or rule on its own default branch, and a person settles each: a record is accepted or deleted, since a record has no state for a refused proposal, and a rule is accepted or withdrawn, which keeps it in place binding nothing (COR-051 point 4).

## Rationale

**Why nothing proposed lands.** Accepting a decision stays a person's so that no agent decides alone. A proposal that lands keeps that promise, since it binds nothing, but it stays: it sits beside accepted records, where readers and agents meet it, and work builds on it or around it. Kept inside its change, a proposal is either accepted or closed, and the default branch holds only what a person decided. The change is the place to discuss and refine a proposal, so nothing is lost.

**Why acceptance comes first, and is shown again at landing.** A person accepts a record before work rests on it, as the specification's acceptance gate asks. The check sees only a change's commits, not who wrote them, so refusing only the word `proposed` would push an agent to write `accepted` itself. The list at landing shows the person who authorises the merge each acceptance, the commit that made it, the work that came before it and every edit since. An acceptance no person gave, or text changed after it, is then seen before it lands. Without a component that shows it, this rests on the author's word, as an answer's evidence does ([COR-050](COR-050-anchors-and-friction.md) point 3).

**Why the refusal is a check of its own.** A proposal is pushed, reviewed and revised in its change before a person accepts it. A failure among the change's other checks would block the push where a hook runs them, stop the reviewers where the merge waits for every check to pass, and hide the other failures. A check of its own, run where the merge is decided, refuses only the merge.

**Why rules too.** A proposed rule is a draft awaiting the same acceptance. What it would report can be shown on the branch that proposes it, before it binds. A rule set that never holds a proposed rule on its default branch never delivers one to a project that receives it. There are two costs. A rule is accepted in the change that adds it, so a rule set gathers its new rules into one change where it wants them in one version. And a proposed rule is tried only on the changes its proposing branch has the reviewer judge, where one on the default branch was reported, to inform, on every change ([COR-057](COR-057-rule-set-reviewer.md)).

**Why the refusal waits for its key.** A project that adopts this may have changes open that hold a proposal, and proposals already on its default branch. An upgrade that refused proposals at once would stop those changes. So a project turns the refusal on when it chooses, and a new one at its install. The list of what a change makes accepted costs nothing backwards, so it is shown either way. Held by the default branch, the key cannot be moved by the change it would check.

### Alternatives considered

- **Keep landing records proposed.** Rejected: a landed proposal reads like a decision, and nothing ends its life.
- **The refusal fails among a change's other checks.** Rejected: it would block a proposal's push where a hook runs those checks, stop the reviewers where the merge waits for every check to pass, and hide other failures.
- **The refusal fails only in the run that lands the change.** Rejected: where no component carries out merges, that run cannot be told apart from the others.

## Implications

- **COR-025** gains a first line saying it is partially superseded by this record, for landing records proposed.
- **The decision-record specification** says a record reaches the default branch accepted, after a person accepts it in its change. Its acceptance gate counts a record a person accepted in the change, or in a change it is built on. Its check of a change on records gains point 3's list, and point 2's refusal stands beside it as a check of its own; both read rules where their rule sets keep them.
- **A component that carries out merges on a person's authority** runs the reviewers on a change that holds a proposal, shows the person one list of what the change decides (the records and rules it makes accepted, beside the edits to accepted records it already lists), and runs point 2's check before it merges. A status set to accepted after the reviewers judged a change is a new head they judge again, unless that component's own rules say otherwise.
- **A project's checks run before a push**, and its decisions check on each change, leave point 2's check out; where no component carries out merges, the host requires it for a merge on a line of its own.
- **The core operational rules, the authoring skill for records and the agent that authors architecture records** have a person accept a record in its change before work rests on it, and no longer land a record proposed.
- **An architecture record realizes this record**: point 2's check and how it reads rules, point 3's list, and the key.
