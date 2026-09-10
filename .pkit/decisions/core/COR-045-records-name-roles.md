---
id: COR-045
title: A record names the role, not the thing currently playing it
status: proposed
date: 2026-09-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **In one sentence:** a record refers to a component by the role it plays — what answers a question, what owns a boundary, what a caller may rely on — rather than by the identifier that implements that role today.
>
> The test is a counterfactual: **if this name changed tomorrow with no decision changing, would the record become wrong?** If yes, the record is naming an implementation where it should name a role.
>
> This protects the property that makes a record worth trusting: it stays true without being edited.

## Context

A record is written once, accepted, and then relied upon. That is what distinguishes it from documentation, which is expected to be maintained alongside the thing it describes. Applying documentation habits to records is what produces records that quietly rot.

A record about a boundary, a contract, or a mechanism reaches naturally for the concrete thing embodying it — a path, a module, a function, a constant. It makes the record feel precise and checkable, and at the moment of writing it *is* both. But those names are the fastest-moving part of any project. A rename or a move makes the record false while the decision it records has not changed at all. Nobody notices, because nobody re-reads accepted records looking for drift. The record is discovered to be wrong much later, by a reader who then cannot tell which of its other claims are still reliable — and a record whose reliability is uncertain has lost the only thing it was for.

The habit is not confined to one namespace: it appears across the architectural, capability, and project id-spaces, which is what marks it as a property of records as an artifact kind rather than of any one corpus.

This record governs only *how a record refers to things*. The neighbouring question — whether a record may narrate its own revisions — is already settled by the record-system specification, which rules that a refinement is edited in place because version control is the change log and the record does not duplicate it internally. That rule keeps its existing owner; this record does not restate it.

## Decision

**D1 — Refer to a role, not to the name of the thing playing it.** Name what a component is obliged to do, not where it currently lives or what it is currently called. Apply the counterfactual test above during authoring and during review.

**D2 — Precision is required; it comes from the role, not the name.** This is not licence for vagueness. A record must stay falsifiable — a reader has to be able to tell whether the system conforms. That precision comes from describing the role sharply enough that only one thing could be playing it. Where a concrete anchor genuinely helps, its home is the work that implements the decision, which is expected to age, rather than the record, which is not.

**D3 — When the identifier is what the record decides, name it.** A record whose subject *is* a name — a canonical filename, a frontmatter key, a marker token, a schema field — is naming the decided thing, not an incidental anchor. The counterfactual settles it: if that name changed, the decision would have changed, so the test does not fire. The rule targets names a record mentions in passing, never the token it rules on.

**D4 — Externally-owned names are pinned facts.** A third party's expected layout, a tool's flag, an upstream format's field: these are facts about something outside the project's control, not implementations of a project role. A record may pin them, and must, to stay checkable. The axiom discipline already permits naming external tools and specifications explicitly; this is the same allowance applied to their identifiers.

## Rationale

**Why roles are more precise than names, not less.** A name feels concrete but conveys only location; the reader still has to go and look to learn what the thing does. A role states the obligation directly, which is the part that has to hold. A record naming which component owns a boundary stays checkable across any refactor. A record citing where that component currently sits stops being checkable the moment it moves — and, worse, still *looks* checkable while being wrong.

**Why a record rather than the authoring guidance.** The disciplines that govern record authoring live in the maintainer guide, which is explicitly not delivered to adopting projects. An adopter authoring architectural, project, or capability records therefore receives no authoring discipline today beyond the schema — and those are precisely the namespaces where this habit concentrates. So the diagnosis is not "the guidance existed and was ignored"; for an adopter the guidance was never delivered at all. A rule that adopters must follow has to reach them.

**Why a counterfactual rather than a prohibition.** A flat ban on identifiers would be wrong in the cases D3 and D4 describe, and an author facing a wrong rule works around it rather than applying it. The counterfactual is a single question, answerable at the point of writing, that produces the right answer in all four cases — and it doubles as the review test, so author and reviewer apply the same instrument.

### Alternatives considered

- **Ban implementation identifiers outright.** Rejected — false for records whose decided subject is a name, and for externally-owned facts. A rule with unstated exceptions gets discretionary application, which is no rule.
- **Permit identifiers wherever they aid precision.** Rejected as stated: precision is exactly why authors reach for them, so the exception consumes the rule. The legitimate need behind it is met by D2 and D3 instead.
- **Restrict the rule to architectural records.** Rejected on the evidence: the habit spans three id-spaces. There is one real asymmetry — architectural records have a custodian charged with auditing them against running reality, while the other id-spaces have no such owner — but that argues for extending the audit, not for narrowing the rule.
- **Convert the existing corpus in one pass.** Rejected — turning a name into a role requires knowing which role the author meant, and that judgment is most reliable when someone is already working in the area. A bulk rewrite risks flattening meaning that cannot be recovered afterwards.
- **Leave it to reviewer judgment without a stated rule.** Rejected — the habit accretes because each instance looks like diligence. A reviewer needs a test they can point at, not an instinct.

## Implications

- **A reviewer has one concrete question to ask**, answerable without deep subject-matter knowledge in the ordinary case: would this sentence become false if a name changed, with no decision changing? The reviewer that audits authored records against the methodology's disciplines owns this check, alongside the disciplines it already applies.
- **Existing records convert on contact**, not in a sweep — when someone working in the area can tell which role a name was standing in for.
- **Records get shorter.** A role usually needs fewer words than a name plus the explanation of why that name matters.
- **The record system's own specification keeps the neighbouring rule** about editing in place rather than narrating revisions. One owner per rule; each is reachable from the other.
- **Authoring guidance delivered to adopters gains a rule it did not carry**, which is the gap this record exists to close. Guidance that reaches only the methodology's own maintainers cannot govern adopter-authored records.
