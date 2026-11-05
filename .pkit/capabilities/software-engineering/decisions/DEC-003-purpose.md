---
id: DEC-003
title: software-engineering exists so code that agents write follows a project's own conventions, and code is reviewed before it merges
status: accepted
date: 2026-10-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The capability's README tells an adopter when to install it: in any project where agents write code. It describes the capability as the discipline of authoring code under a project's own conventions, and of reviewing that code. So the code an agent produces meets the project's standards in every session, without the conventions being explained again each time. And code that reaches the merge gate is actually reviewed.

Two records decide how. One decides the agent that writes code ([software-engineering:DEC-001-producer-agent-and-conventions-seam]), and the other the agents that review it ([software-engineering:DEC-002-code-review-panel]). Neither states what the capability is for. So whatever describes the capability, such as an analysis of it, has no reviewed statement of its purpose to anchor. This record gives one.

## Decision

**software-engineering exists for two aims. Code that agents write for a project follows that project's own conventions, the same in every session, without anyone explaining them again. And code that reaches the merge gate is reviewed, with its documentation, before the gate lets it through.**

This record decides no new behaviour. It states what the capability is for, from what its README and its records already say. How each part works is decided elsewhere:
- An agent the capability ships reads the project's conventions before it writes code, and conforms to them. It checks its work for conformance, and leaves judgement of the design to the critic and the architect ([software-engineering:DEC-001-producer-agent-and-conventions-seam] points 3 and 4).
- The conventions are the project's own, kept where the project names them, so removing the capability never removes them ([software-engineering:DEC-001-producer-agent-and-conventions-seam] point 2).
- That agent carries no coding opinions of its own, so the project's conventions stay the one authority on its choices. Where the project has none yet, the agent says so and works by ordinary judgement ([software-engineering:DEC-001-producer-agent-and-conventions-seam] points 3 and 5).
- Reviewer agents judge a pull request's code, its security and its documentation, each where the condition it declares holds. Their verdicts fold through project-management's merge gate, with no aggregation of their own ([software-engineering:DEC-002-code-review-panel] points 1 and 6, [project-management:DEC-032-conditional-reviewer-requirements]).
- Each reviewer carries only knowledge that holds in any project, and reads the project's own rules from the same conventions ([software-engineering:DEC-002-code-review-panel] point 4).
- Each reviewer blocks only on an objective failure of the change in its own remit ([software-engineering:DEC-002-code-review-panel] point 3).
- Where the documentation reviewer reviews a change, it also checks the answers the change wrote, as a reviewer other than their writer. Which reviewer checks them is the project's choice ([software-engineering:DEC-002-code-review-panel] point 1).

## Rationale

**Why the project's conventions, not the agent's.** Opinions held in two places drift apart. Kept in the project alone, the conventions stay the one source the agent applies, and they outlive the capability ([software-engineering:DEC-001-producer-agent-and-conventions-seam]). An agent with no opinions of its own also lets a project see what its conventions add.

**Why review before the merge.** Without the reviewers, the merge gate checks a change's conventions, and nothing reviews its code. A change with real security defects can then pass approved ([software-engineering:DEC-002-code-review-panel]).

**Why the two aims share a capability.** That is a choice of packaging, which this record does not make. [software-engineering:DEC-002-code-review-panel] makes it, so that the agent that writes code and the reviewers of code can come to share one body of knowledge. It keeps the documentation reviewer with them as one panel, and records how review could move to a capability of its own.

**Why a record of the capability's own.** The statement concerns this capability alone, and it ships with it. So it belongs among the capability's records, not with any one project's.

## Implications

- **Whatever describes the capability's purpose,** such as an analysis of it, can anchor this record instead of stating a purpose of its own. A change to this record then flags each such description.
