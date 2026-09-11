---
id: COR-045
title: A record names the role, not the thing currently playing it
status: accepted
date: 2026-09-10
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> **In one sentence:** a record refers to a thing the way it means it — by the role it plays where the role is the point, by name where the name is the point.
>
> One question separates them: **if this name changed tomorrow with no decision changing, would the record become wrong?** If yes, a role was meant and a name was written.
>
> This protects the property that makes a record worth trusting: it stays true without being edited.

## Context

A record is written once, accepted, and then relied upon. That is what distinguishes it from documentation, which is expected to be maintained alongside the thing it describes. Applying documentation habits to records is what produces records that quietly rot.

A record about a boundary, a contract, or a mechanism reaches naturally for the concrete thing embodying it — a path, a module, a function, a constant. It makes the record feel precise and checkable, and at the moment of writing it *is* both. But those names are the fastest-moving part of any project. A rename or a move makes the record false while the decision it records has not changed at all. Nobody notices, because nobody re-reads accepted records looking for drift. The record is discovered to be wrong much later, by a reader who then cannot tell which of its other claims are still reliable — and a record whose reliability is uncertain has lost the only thing it was for.

The habit is not confined to one namespace: it appears across the architectural, capability, and project id-spaces, which is what marks it as a property of records as an artifact kind rather than of any one corpus.

This record governs only *how a record refers to things*. The neighbouring question — whether a record may narrate its own revisions — is already settled by the record-system specification, which rules that a refinement is edited in place because version control is the change log and the record does not duplicate it internally. That rule keeps its existing owner; this record does not restate it.

## Decision

**Refer to a thing the way you mean it.** Where a record means *whatever plays this part* — what answers a question, what owns a boundary, what a caller may rely on — it names the part, not whichever component is playing it today. Where a record means a *particular name* — because that name is what the record decides, or because it belongs to something outside the project and is being recorded as a fact — it names it plainly.

1. **Prefer the role when the role is what you mean.** A record reaching for a path, a module or a function to identify *the thing that does X* is naming an understudy for the part. The name will change; the part will not.

   The counterfactual tells you which you meant: **would this sentence become false if the name changed, and no decision changed?** If yes, you meant the role and wrote a name. If no — because changing the name would itself be changing the decision, or because the name is not yours to change — then the name *is* what you meant, and it belongs there.

2. **Precision is required either way.** Naming a role is not licence for vagueness. A record must stay falsifiable — a reader has to be able to tell whether the system conforms. That comes from describing the part sharply enough that only one thing could be playing it. Where a concrete anchor genuinely helps a reader, its home is the work implementing the decision, which is expected to age, rather than the record, which is not.

## Rationale

**Why a role is usually more precise than a name.** A name feels concrete but conveys only location; the reader still has to go and look to learn what the thing does. A role states the obligation directly, which is the part that has to hold. A record naming which component owns a boundary stays checkable across any refactor. A record citing where that component currently sits stops being checkable the moment it moves — and, worse, still *looks* checkable while being wrong.

**Why a record rather than the authoring guidance.** The disciplines that govern record authoring live in the maintainer guide, which is explicitly not delivered to adopting projects. An adopter authoring architectural, project, or capability records therefore receives no authoring discipline today beyond the schema — and those are precisely the namespaces where this habit concentrates. So the diagnosis is not "the guidance existed and was ignored"; for an adopter the guidance was never delivered at all. A rule that adopters must follow has to reach them.

**Why a counterfactual rather than a prohibition.** A flat ban would be wrong wherever the name is the point, and an author facing a wrong rule works around it rather than applying it. The counterfactual asks the author what they meant, which is the actual question — and because it needs no catalogue of permitted cases, a legitimate use nobody anticipated passes on its merits rather than by being on a list. It doubles as the review test, so author and reviewer apply one instrument.

### Alternatives considered

- **Ban implementation identifiers outright, with a list of exceptions.** Rejected twice over. An exception list is an inventory, which a record is the wrong carrier for — the next legitimate case is absent from it and gets flagged. And needing the list at all was the signal that the rule was mis-stated: the cases are not exceptions to *avoid names*, they are instances of *meaning a name*.
- **Permit identifiers wherever they aid precision.** Rejected as stated: precision is exactly why authors reach for them, so the permission consumes the rule. The legitimate need behind it is met by the counterfactual, which distinguishes a name that carries meaning from a name standing in for a role.
- **Restrict the rule to architectural records.** Rejected on the evidence: the habit spans three id-spaces. There is one real asymmetry — architectural records have a custodian charged with auditing them against running reality, while the other id-spaces have no such owner — but that argues for extending the audit, not for narrowing the rule.
- **Convert the existing corpus in one pass.** Rejected — turning a name into a role requires knowing which role the author meant, and that judgment is most reliable when someone is already working in the area. A bulk rewrite risks flattening meaning that cannot be recovered afterwards.
- **Leave it to reviewer judgment without a stated rule.** Rejected — the habit accretes because each instance looks like diligence. A reviewer needs a test they can point at, not an instinct.

## Implications

- **A reviewer has one concrete question to ask**, answerable without deep subject-matter knowledge in the ordinary case: would this sentence become false if a name changed, with no decision changing? The reviewer that audits authored records against the methodology's disciplines owns this check, alongside the disciplines it already applies.
- **Existing records convert on contact**, not in a sweep — when someone working in the area can tell which role a name was standing in for.
- **Records get shorter.** A role usually needs fewer words than a name plus the explanation of why that name matters.
- **The record system's own specification keeps the neighbouring rule** about editing in place rather than narrating revisions. One owner per rule; each is reachable from the other.
- **Authoring guidance delivered to adopters gains a rule it did not carry**, which is the gap this record exists to close. Guidance that reaches only the methodology's own maintainers cannot govern adopter-authored records.
