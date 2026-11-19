---
id: ADR-101
title: A capability may allow a privilege it defines to an agent it ships, reported as a widening
status: proposed
date: 2026-11-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** [ADR-016](ADR-016-capability-contributed-intent-grants.md) lets an installed capability ship grants that the permission model composes for it, and [ADR-021](ADR-021-capability-contributed-privilege-definitions.md) lets it define privileges of its own. Both rest on a capability's grant being a deny, which only narrows an agent's reach and so applies on install. This record lets a capability's grant also allow a privilege, on these terms:

- **Only its own privilege, only to its own agent.** The privilege is one the capability defines itself, and the agent is one the capability ships. The model's loader refuses a capability's allow of anything else.
- **Composed on install, binding once realized.** The allow is composed into the model on install, as a deny is. It widens the agent's reach, so it binds only once a person realizes the model, and a deny of the operator's still wins over it.
- **Reported as a widening.** The permissions overview reports it as a widening the capability contributes, so no agent's reach changes silently.

So a capability whose agent needs a call that a strict posture would deny carries the grant with it, and no project copies it by hand. This record overturns ADR-016 and ADR-021 in part, where they say that what a capability grants is a deny, and that the operator's choices decide every allow.

**Why an ADR.** What a capability's grant may carry, and how the model's loader composes, refuses and reports it, is a boundary of the backbone's permission model that binds every capability, an architecture record's question ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md), "Distinct from PRJ"). A capability that allows a privilege reads the rule here, not in the record of the capability that first did.

## Context

**What stands.**

- **A capability's grants.** An installed capability may ship a grants fragment, which the model's loader composes, found through the installed components, before the active profile and the project's own grants (ADR-016 points 1 and 2). The operator's profile choice and manual grants win on the allow side, and a capability's deny survives by deny-wins (ADR-016's Decision). A capability's deny narrows an agent's reach, so it applies on install under [ADR-008](ADR-008-confinement-allowances.md)'s narrowing class, and the overview reports which capability contributed it (ADR-016 point 7).
- **A capability's privileges.** A capability may define privileges of its own, each scoped to the capability, adding to the catalog and overwriting nothing. Its reach is over its own agents through its own deny grant, and the loader refuses a fragment past its bounds rather than strip it (ADR-021 points 2 to 4).
- **The posture.** The posture decides a call no grant covers: a strict posture denies it, and a lenient one leaves it to the harness's own rules, which may ask a person (the permissions README, "Grants and verdicts").
- **A widening waits for a person.** The permission hook allows no more than the model a person realized. A change in the checkout that widens the model binds only once a person realizes it, and realizing shows each widening before it writes ([ADR-095](ADR-095-hook-out-of-reach.md) point 3).

**The forcing case.** The project-management capability has its agent hold a harness's tools for messaging other sessions and listing them, under every posture ([project-management:DEC-081-delegation-between-seats] point 2). A capability's deny cannot grant them.

**Terms.**

- **A capability's allow** is a grant in a capability's grants fragment whose effect is allow.
- **An agent the capability ships** is an agent whose definition the capability ships among its own agents.
- *Realizing* and *a widening* are ADR-095's, and *the posture* is the permission model's.

## Decision

**A capability's grant may allow a privilege, but only one the capability defines itself, and only to an agent the capability ships. The allow is composed into the model on install, as a deny is, binds only once a person realizes the model, and is reported as a widening the capability contributes. The model's loader refuses a capability's allow of anything else.**

### 1. A capability allows only a privilege it defines, and only to an agent it ships

- **What it may allow.** A capability's grant may allow a privilege only where the capability defines the privilege itself (ADR-021), and only to an agent the capability ships.
- **Its reach.** So a capability shapes only its own agents' reach, through its own grant: a deny, or an allow of a privilege it defines itself.

### 2. The allow is composed on install, and binds once a person realizes the model

- **Composed as a deny is.** The allow is composed into the model on install, in the capability's fragment, as a deny is (ADR-016 points 1 and 2).
- **A widening.** The allow widens the agent's reach, so ADR-008's narrowing class, by which ADR-016 point 7 applies a deny on install, does not cover it. It binds only once a person realizes the model, which shows it as a widening (ADR-095 point 3). So a capability's denies apply on install, and its allows once a person realizes them.
- **What it decides.** Once realized, the allow decides a call that no grant of the operator's covers, which the posture would otherwise deny or leave to ask a person. A deny of the operator's still wins over it by deny-wins.

### 3. The read surface reports it as a widening the capability contributes

The model's read surface, the permissions overview among it, reports a capability's allow as a widening, with the capability that contributed it, as it reports a capability's deny (ADR-016 point 7).

### 4. The loader refuses a capability's allow of anything else

- **The refusal.** The model's loader refuses a capability's allow of anything but a privilege the capability defines itself, granted to an agent it ships, as it refuses a fragment past ADR-021's other bounds rather than strip it.
- **Where the check does not run.** An installed release older than the build that brings this check composes a capability's allow without it, and only realizing's report of the widening shows such an allow.

### What this overturns in ADR-016 and ADR-021, and what stands

Overturned, each a passage whose words this record makes untrue for a capability's allow, and the line each record gains points here (Implications):

- ADR-016's Decision headline, "so the operator's profile choice and manual grants still win on the allow side while a capability *deny* survives via deny-wins", since a capability's allow decides, once realized, a call they leave uncovered (point 2);
- ADR-016's Summary, "Install the capability → its grants apply", since a capability's allow binds only once a person realizes the model (point 2);
- ADR-016's Summary property "**Your settings win on what's *allowed***", which states the headline's guarantee to the operator, for the same call (point 2);
- ADR-016's Summary property "**The privilege definition stays central** for now — only the *policy* (deny it to this agent) moves into the capability", since an allow of a privilege the capability defines itself moves into it too (point 1);
- ADR-016 point 7, "Narrowing-but-reported honesty", whose footing is that what a capability grants is a deny, which narrows an agent's reach and so is "safe to auto-apply on capability install per ADR-008's narrowing class", since a capability's allow widens it and binds only once realized (point 2);
- ADR-021's Summary bullet "Never a guardrail", where a capability "shapes only its own agents' reach, through its own deny grant (ADR-016's channel, unchanged)", since it shapes it through its allow too (point 1);
- ADR-021 point 3, "A capability's reach is over its own agents via its own deny grant", for the same reach (point 1);
- ADR-021 point 4's honest bound, "a capability can deny recognised commands **to the subjects its own grants name**", since it can also allow a privilege it defines itself to an agent it ships (point 1);
- ADR-021's Rationale, "so the worst a capability can do is fence its own agents", since it can also widen their reach by a privilege of its own, reported as a widening (points 1 and 3).

Refined in place, each completed with a case this record adds, its words left true: ADR-016's Summary property "It's visible", and ADR-021's Implications bullet on the narrowing footing, each as the Implications word it.

Standing: the rest of each record, among it ADR-016's composition, its discovery through the installed components and what it says of a capability's deny, and ADR-021's merge of a capability's privileges, its bounds on them and its attribution of them.

## Rationale

**Why a capability may allow at all.** An agent's reach is its capability's policy, and travels with the capability, as a deny of its own does (ADR-016). Left to each project, a strict posture would deny the call with no word, and every project that installs the capability would copy the same grant by hand, the hand-copy ADR-016 removed for a deny.

**Why only its own privilege, and only to its own agent.** A grant bounded so widens nothing else: no privilege of the backbone or of another capability, and no agent the capability does not ship. So the worst a capability can do is fence its own agents, or widen their reach by a privilege of its own, reported as a widening.

**Why reported as a widening, and binding once realized.** Reported with the capability that contributed it, the allow changes no agent's reach silently, as the report of a deny keeps a narrowing in view (ADR-016 point 7). A widening binds only once a person realizes the model, and realizing shows it first (ADR-095 point 3), so a person sees the allow before it binds.

### Alternatives considered

- **Leave every allow to the project, and have a capability ship only the privilege's definition.** Not taken, as "Why a capability may allow at all" says.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md) point 5):
  - **Overturned in part.** ADR-016 and ADR-021 each gain a line at the top of the body, before the Summary, and their words stay as they stood under it. ADR-016 gains:

    > **Partially superseded by [ADR-101](ADR-101-capability-contributed-allows.md).** A capability's grant may also allow a privilege, but only one the capability defines itself, and only to an agent the capability ships. The allow is composed into the model on install, as a deny is, binds only once a person realizes the model, and is reported as a widening the capability contributes, and the loader refuses a capability's allow of anything else. Overturned, each for a capability's allow: the Decision's headline, where the operator's choices still win on the allow side, the Summary's "Install the capability → its grants apply", its properties "Your settings win on what's *allowed*" and "The privilege definition stays central", and point 7's footing, that what a capability grants is a deny, each quoted in ADR-101's "What this overturns in ADR-016 and ADR-021, and what stands". Refined in place where ADR-101 says: the Summary's "It's visible". The rest stands.

    ADR-021 gains:

    > **Partially superseded by [ADR-101](ADR-101-capability-contributed-allows.md).** A capability's grant may also allow a privilege the capability defines itself, but only to an agent the capability ships, reported as a widening. Overturned, each for that allow: the Summary's "Never a guardrail", where a capability shapes its agents' reach through its own deny grant, point 3's reach "via its own deny grant", point 4's honest bound, and the Rationale's "the worst a capability can do is fence its own agents", each quoted in ADR-101's "What this overturns in ADR-016 and ADR-021, and what stands". Refined in place where ADR-101 says: the Implications' bullet on the narrowing footing. The rest stands.

  - **Refined in place,** each completed with a forward refinement pointer to this record, its words left true:
    - ADR-016's Summary property "It's visible", whose "shows which capability contributed a deny" gains "or an allow, and marks an allow as a widening" (point 3)
    - ADR-021's Implications bullet on the narrowing footing, completed by a sentence: a capability's allow of a privilege it defines itself, to an agent it ships, is a widening, reported as one (points 2 and 3)
  - **An edit that changes no decision:** none.
- **The build.** The loader's refusal (point 4) and the overview's report (point 3) come with the build of the first capability that allows a privilege, project-management's ([project-management:DEC-081-delegation-between-seats]'s Implications).
- **Acceptance.** This record overturns the accepted ADR-016 and ADR-021 in part, so accepting it needs the person's sign-off. It rests on no proposed record. [project-management:DEC-081-delegation-between-seats] rests on it, and the two are accepted in one change, with ADR-100 and [project-management:DEC-082-pace-of-subagents] (DEC-081's Implications).
- **Changesets.** This record moves nothing, so it needs none of its own. The build declares its components' changes (PRJ-002).
- **No migration.** Nothing it changes is built yet.
