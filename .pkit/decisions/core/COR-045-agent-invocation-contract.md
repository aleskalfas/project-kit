---
id: COR-045
title: "Dispatching an agent: transports vary, but a gate is satisfied only by a durable artifact"
status: accepted
date: 2026-08-25
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

When one party dispatches an agent and needs what it produced, two different questions get confused. **How does the result travel back?** — that varies by harness, and should. **What is allowed to satisfy a gate?** — that must not vary at all.

Today only the first is handled, informally, and only where the **dispatching party** — whoever asked for the agent to run, whether a command, a script, or another agent — is code. Where the dispatcher is itself a model, and the harness runs the dispatched agent as an independent participant rather than as a call, the agent completes and its output reaches nobody. The dispatcher cannot distinguish that from an agent that had nothing to say.

This record separates the two questions and answers them differently.

**Transports are plural and configurable.** A harness may return a dispatched agent's output to its caller, or may not; a project may prefer a fresh invocation or one that continues from the dispatcher's context, for reasons of cost or continuity that only that project can weigh. The methodology owns the vocabulary for describing what a transport provides; each adapter realizes the ones its harness supports; each project configures which is used. Naming a transport obliges nobody to build it — the corpus's discipline of naming a distinction broadly while shipping only what a real case needs ([COR-016](COR-016-scripted-scenario-storyboards.md)).

**A gate is satisfied by a durable artifact the invocation produced — never by the dispatcher's report that it was produced.** This is not a preference between transports; it is what makes a gate a gate. The party that checks a gate is not the party that ran the agent, and usually runs later. If the check consults a durable artifact, then a dispatcher whose result was lost has simply not produced one, and the gate stays shut on its own — with no reliance on the dispatcher noticing, reporting honestly, or existing at all by then.

Together these mean an agent's result reaches the party that needs it, or that party is told it did not — while leaving every project free to choose how its agents are run.

## Context

[COR-013](COR-013-agent-architecture.md) established the agent as a role with declared authority. [COR-024](COR-024-critic-and-architect-agents.md) went further and made invoking certain agents a *discipline* — a review is expected before certain work proceeds. That expectation is only meaningful if the review's outcome actually arrives somewhere it can be acted on.

Harnesses differ on whether it does, and the difference is structural rather than incidental: it follows from whether a harness models a dispatched agent as a **call** (the dispatcher waits, the output comes back) or as an **independent participant** (it runs alongside, reports that it finished, and its output is reachable only through a channel the dispatcher may not have). Both are defensible designs, and a methodology that assumes either one is wrong somewhere.

Two properties vary across those designs and both matter to an adopting project:

- **Whether the output returns programmatically.** Where it does not, work is performed and lost.
- **What the agent starts from.** A fresh invocation begins with its own definition and the material it is pointed at; a continuing one begins from the dispatcher's accumulated context. That is a real trade — continuity aids some work and compromises other work — and its **cost** in either direction is not yet measured. No project should be forced onto one side of a trade nobody has quantified.

The failure is not hypothetical, and it is asymmetric in a way that points at the answer. Where the dispatching party is **code**, it can already detect and report a missing result: it waits, checks an exit status, and refuses to proceed on nothing. Where the dispatching party is a **model**, nothing compels it to notice, and an absent result looks exactly like a clean one.

The corpus already contains a mechanism that survives both cases, though it was built for a different reason. A merge gate is not satisfied by anyone's account of what a reviewer decided; it is satisfied by a **marked, durable comment** the reviewer path posted, which a *later, separate* process reads. That gate cannot be fooled by a dispatcher that never ran a reviewer, misreported one, or lost its output — not because the dispatcher is trusted, but because it is not consulted.

## Decision

**Separate the transport of an agent's result from the evidence a gate accepts. Let the first vary; fix the second.**

### 1. Transports are declared by property, realized by the adapter, configured by the project

A transport is described by **what it provides**, not by the mechanism a particular harness uses. The properties that matter:

- **Collectable** — the dispatching party receives the output programmatically, rather than being told only that the agent finished.
- **Context origin** — the agent begins from its own definition and the material it is given, or from the dispatching party's accumulated context.
- **Lifetime** — the agent answers once and ends, or remains addressable for further exchanges.
- **Authority** — what the dispatched agent may do while it runs: its own declared authority, or whatever the dispatching environment happens to permit. This is observable, differs between transports, and is the property a control over dispatching has to be able to read (Decision 6) — so a vocabulary that omitted it would leave that control nothing to attach to.

One further distinction is named but deliberately unspecified: whether a transport supports **concurrent** dispatch. It is observable and bears on the unmeasured cost question, so it is likely to matter — but no realization turns on it yet, and inventing its semantics before one does would be guesswork.

Naming properties rather than mechanisms is what lets a project ask for what it needs and an adapter answer honestly. The methodology owns this vocabulary; each **adapter declares which combinations its harness realizes**; each **adopting project configures** which is used, and may choose differently for different uses. Properties may be added as harnesses reveal distinctions that matter; a combination nobody realizes is simply unavailable.

**An unrealized request is refused, never silently substituted.** A party that asked for a fresh invocation and received a continuing one has been handed something it did not ask for, and cannot tell.

This is the opposite answer from the one [COR-028](COR-028-permission-model-realization.md) rule 3 gives for permission realization, where a realizer renders the closest achievable enforcement and *reports* the residual gap. The two are not in conflict; they are the same principle — **never leave the consumer misled about what actually happened** — applied to domains where different things un-mislead:

> **The test.** Can the consumer distinguish a partial realization from a complete one — and if not, is there a party who will receive the gap report and act on it? Where either holds, render what is achievable and report the shortfall. Where neither does, refuse.

Under COR-028 the report reaches an adopter who can close the gap elsewhere, and a partial boundary constrains in the meantime. Here the report's only recipient is the dispatching party, which in the failing case is the very thing that cannot be relied on to notice — so reporting does not un-mislead anyone, and only refusal does.

### 2. A gate is satisfied by a durable artifact, never by a dispatcher's report

Where an agent's outcome is used to **gate** work rather than merely inform it, the gate is satisfied only by a durable artifact the invocation produced — one the gate-checker can read independently, attribute to the path that produced it, and find later.

The reasoning is that a gate's checker is a *different party at a different time*. Making the artifact the sole evidence has three consequences worth stating plainly:

- **A lost result cannot masquerade as a clean one.** The artifact is absent, so the gate stays shut, whether the dispatcher was a model that lost the output, a script that crashed, or nobody at all.
- **Honesty is not required of the dispatcher**, because the dispatcher is not asked. This is what makes the guarantee hold for a model caller, which cannot be compelled to report accurately.
- **The transport becomes free to vary** without weakening the gate — which is what allows Decision 1 to be as permissive as it is.

**The transport realization writes the artifact, on the agent's behalf.** This is the point on which the record either closes the failure or merely contains it. Where a transport can collect the agent's output, the realization writes the artifact from what it collected. Where a transport *cannot* — the case that motivates this record — the realization supplies the artifact's location as part of the dispatch, and the agent writes there. Either way the artifact exists independently of whether anything returned to the dispatching party, so the work survives a transport that strands its output rather than merely failing safe.

This is consistent with Decision 4 rather than an exception to it: the *location* arrives at dispatch time from the transport, and the agent definition carries no knowledge of where output goes or how it travels. What the agent knows is the shape it must produce, which is its consumer's contract and always was.

An artifact should be **attributable** — a gate can tell one produced by its sanctioned path from one that merely looks similar. Attributability is an **honest interlock, not a security boundary**: anyone able to write where the artifact lives can imitate one, and the marker's job is to stop an accidental or incidental look-alike from counting, not to withstand a determined actor. A gate resting on it should say so rather than imply a proof it does not have.

### 3. The invariant: a result or a named failure, never silence

Independently of gates, an invocation ends in the agent's output or a **named** failure — the agent could not be started, exceeded its budget, produced nothing interpretable, or finished without its output being collectable. The kinds are distinguished because their remedies differ: a budget too small and an agent that was never available look identical from a distance and want opposite responses.

This taxonomy governs **invocation** and reaches no further: other boundaries in a system have their own failure vocabularies, authored for their own reasons, and nothing here supersedes them.

The invariant binds **every dispatching party that is code**, and is a discipline for one that is a model — carried wherever that project states its working practices, since a model has no other place to receive it. That asymmetry is honest rather than convenient: a model cannot be *made* to notice silence, which is exactly why Decision 2 places a gate's guarantee somewhere a model's diligence is not required.

### 4. Delivery is not an agent's concern

An agent definition states its role, its authority, and what it produces — never how its output travels. Transport depends on the harness and the configured properties, neither of which a definition knows, and mechanics written into agent bodies become the same knowledge copied everywhere and drifting ([COR-007](COR-007-pattern-extraction.md)).

The boundary: **transport** leaves the agent definition; the **form of what the agent produces** stays with whatever decision consumes it. An agent may still be told to emit a particular shape, because that shape is the consumer's contract — it is only the question of how the emission reaches anyone that ceases to be the agent's business.

### 5. A budget may not systematically starve an expected agent

A time budget is legitimate and necessary. What is not legitimate is one set so low that an agent the gate *expects* can never finish inside it: the gate then cannot be satisfied by doing the work, only by overriding it, and an override meant for exceptional cases silently becomes the ordinary path. That is worse than no budget, because it looks like diligence while training the reflex it should prevent.

The rule is therefore about the relationship between the budget and the work, not about where the number lives. Whether one value serves every use or several are needed is a project's judgment, made where the budget is configured.

### 6. A control over dispatching must be expressed over transports, not over one mechanism

Nothing here grants authority to dispatch. But the requirement runs in the direction that can actually be satisfied: **where a project governs which agents may dispatch which others, that control must be expressed over transports** — because a control that recognises only one harness mechanism cannot see a transport realized by another, and would be routed around by the mere act of choosing a different one.

The consequence is a precondition on realization rather than advice to transport authors: **a transport the governing control cannot observe is not an available transport.** A realization that the control cannot see is not "unpoliced" — it is unavailable until the control can see it.

This too is an honest interlock rather than a boundary: a party able to issue arbitrary commands can dispatch an agent without asking anyone. The control's purpose is to make dispatching visible and deliberate, not to make it impossible.

## Rationale

**Why separate the two questions.** Conflating them is what makes the problem look intractable. If a gate depends on the result *returning*, then a harness without a return channel cannot host a gate, and the methodology must either mandate a harness or weaken the gate. Separating them dissolves that: the gate depends on an artifact, which any agent that can write one can produce, so the transport is free to be whatever the harness and the project prefer.

**Why the artifact rather than the report.** A gate exists to be checked by someone who was not there. Its evidence must outlive the moment and be readable by a party with no memory of it — which a report by the dispatching party is not, however honest that dispatcher intends to be. This also removes an entire class of question that would otherwise need answering: whether a dispatcher is trustworthy, whether it noticed a failure, whether it was even the same party that started the work.

**Why transports are described by property.** Naming mechanisms would freeze one harness's implementation into the methodology and leave any other adapter unable to say what it offers. Properties are what a caller actually cares about, and they let an adapter declare a combination the vocabulary's authors never anticipated.

**Why refuse rather than degrade.** Not because degrading is wrong in general — the corpus is right to prefer it for permissions — but because the thing that makes degrading safe there is absent here. A gap report works when someone will receive and act on it; the recipient here is the dispatching party, which in the case this record exists for is a model that cannot be relied on to notice. A report nobody acts on is silence with extra steps.

**Why name properties broadly and realize narrowly.** The vocabulary is cheap; realizations are not. Naming lets a definition, a configuration and a conversation refer to the same distinctions today, while each realization waits for a project that needs it — name the distinction broadly, build narrowly ([COR-016](COR-016-scripted-scenario-storyboards.md)).

### Alternatives considered

- **Mandate one transport.** Rejected: settles the cost-versus-continuity trade before anyone has measured it, and binds the methodology to one harness's model.
- **Make the returned result the gate's evidence.** Rejected: it is exactly what fails today, it requires the dispatcher to be honest and attentive, and it makes a gate impossible on a harness with no return channel.
- **Require every agent definition to carry a fallback delivery mechanism.** Rejected: copies transport mechanics into every agent, has each author solve it differently, and surfaces the differences only when something is lost.
- **Require the dispatching party to be able to retrieve a message from a running agent.** Rejected: makes the contract depend on a harness feature that may not exist; where it does not, the failure is untouched.
- **Report the substitution and proceed** — render the nearest available transport and note the shortfall. Rejected by the test above: the note's only recipient is the dispatching party, and where that party is a model there is no one the report reliably reaches. It is the right answer where a human or a later process will read it, which is why the permission domain takes it.
- **Leave invocation to each caller.** Rejected: two dispatching paths already exist on two different mechanisms, and the one that broke is the one that had no shared contract to inherit. Each additional caller would re-derive both transport and failure semantics, and the failure semantics are where silent divergence does the most damage.
- **Scope the record to gates alone.** Rejected: gates are where a lost result is unrecoverable, but a lost result is waste everywhere. The gate rule is the part that must not vary; the invariant covers the rest.

## Implications

- **The gate rule is largely already met** wherever a gate consults a marked, durable artifact rather than a report; those gates need confirming against Decision 2, not rebuilding. What is new is that the rule becomes general, so a future gate cannot be built on a dispatcher's word.
- **A shared invocation seam is introduced**, and each dispatching party that is *code* becomes a consumer of it rather than an owner of its own. For a dispatching party that is a **model**, the seam is reachable only as discipline — it can be told to use it and cannot be made to. That is why the guarantee for gates rests on Decision 2 rather than on the seam: a record that promised the seam would *reach* the model dispatcher would be promising something no seam can deliver.
- **Whether the seam is realized as a new mechanism or as an instance of the existing hook contract** — declared name, adapter-supplied implementation, defined precedence, output and failure through a fixed channel — is left to the realization, but the question must be answered rather than assumed: the existing mechanism already carries most of this contract's shape, and re-deriving it would be the duplication this record's own reasoning objects to.
- **Adapters gain a declaration obligation**: which property combinations they realize. An unrealized request is a refusal.
- **Agent definitions lose transport language.** Several carry it today and are corrected under Decision 4; the shape they are asked to emit is unaffected.
- **[COR-024](COR-024-critic-and-architect-agents.md)'s invocation discipline is read through this record** — the expectation to run a reviewer means little until the reviewer's outcome reliably arrives or is reported missing. A caveat in a capability decision that restricts an agent to one dispatching arrangement **stays as written until that decision is amended in its own right**: such a caveat may have been authored around a platform constraint a different transport does not share, but narrowing it is that record's business, not this one's — and doing it here would loosen an accepted restriction on the strength of a transport that has no realization and no authorisation coverage yet.
- **The configuration surface is project-owned**: which properties each use requires, and its budget.
- **The agents-area specification carries Decision 4's consequence** — what an agent definition may and may not state about its output — and any declaration that moves with removed transport language moves on both sides at once, since definitions are checked for agreement between what they declare and what they say.
- **The permission-realization record gains a pointer to the test in Decision 1**, so a reader landing on its degrade-and-report rule can see where the opposite answer applies and why.
- **Where an existing invocation records a deliberate single knob** rather than a table, this record does not overturn it; a budget varying by transport is a coarser axis than one varying per agent, and the finer table stays unwanted until evidence asks for it.
- **The adapter tier acquires a responsibility it did not have: acting inside the request path at run time**, rather than only at deployment or on demand. That is universal — it holds for every adopter and every harness — and is recorded here rather than left to each project to rediscover.
- **Which transports a particular harness realizes, and how**, is specific to that adopter and belongs in their own architectural record.
- **Adding a property to the vocabulary later under-specifies every declaration already written against it**, so the vocabulary's growth is a compatibility question and not a free extension.
