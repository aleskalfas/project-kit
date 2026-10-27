---
id: DEC-060
title: Slices are planned only once the choices they share are settled
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** vertical slices built at once go wrong when each slice must make the same choice alone, such as which library to use or how the code is laid out. So where the Tasks of new work would share a choice that nothing settles yet, planning goes in two stages. The first plans only the work's foundation: a record of each shared architectural choice, which the person accepts, and then a walking skeleton, a thin slice end to end whose code sets the patterns. Only once the foundation is done does the second stage plan the slices, against records and code that exist. Work whose shared choices are already settled skips the first stage.

## Context

[project-management:DEC-059-topology-of-seats] point 7 decides that workers take ready Tasks from one shared pool, and that the planner slices the work vertically, so that one agent can finish a Task across the software's layers. It does not say what must stand before the slices are planned.

On 26 October, planning a demonstration of several clones that build one new product, the maintainer raised what happens when vertical slices start before the product has a base. Each slice then chooses for itself the libraries, the layout of the code, the style of its interfaces and where its state lives. Each choice is reasonable alone, and the choices do not fit together. Merge conflicts and rework follow, and they grow with the number of agents working at once. The same holds in a product that stands, for a concern that crosses its slices, such as how errors reach the user. He asked for a record that settles it (#2150).

## Decision

**Where the Tasks of new work would share a choice that nothing settles yet, the work is planned in two stages. The first plans only the work's foundation: accepted records of its shared architectural choices, then a walking skeleton built on them, one Task at a time. The second plans the slices, once the foundation is done.**

Here the planner is whoever slices the work into Tasks: the planner seat, a lead for what it plans ([project-management:DEC-059-topology-of-seats] point 2), or any session that runs batch planning ([project-management:DEC-029-project-manager-agent-shape]).

### 1. A choice that Tasks would share, and nothing settles, calls for a foundation

Before it slices work, the planner names each choice that two or more Tasks would otherwise make each for itself. It counts the work's Tasks, the work the plan says will follow, and the open Tasks. Examples are the architecture, a library or framework, the layout of the code, the contract between layers, and the shape that each of a repeated kind takes. A choice is settled where an accepted record decides it, or where merged code shows a pattern the Tasks can follow. Where every choice is settled, the planner slices the work at once, as DEC-059 point 7 says. A choice that an open foundation settles is in hand: the new work plans no foundation of its own for it, and its slices are planned once that foundation is done, as point 3 says. Otherwise the work needs a foundation.

### 2. The foundation is one Feature, built one Task at a time

The foundation is one Feature whose body lists the choices it settles, so that any later filer finds them. Its Tasks form a chain, each naming the one before among its dependencies, so that one is ready at a time ([project-management:DEC-005-linking-and-containment]). They take High priority ([project-management:DEC-012-classification-axes]), since the work's slices wait for them.

- **The records first.** One Task holds a record of each architectural choice ([pkit:COR-025]). The architect agent authors the records where the project deploys it, and the builder otherwise. The person's acceptance of each record is one of that Task's acceptance criteria, so the Task cannot close on a draft ([project-management:DEC-007-checkbox-validation]).
- **Then the walking skeleton:** one thin slice that runs end to end through each layer the work touches, built on the accepted records. Choices of convention, such as the layout of the code and of its tests, are settled by its merged code.

Where one agent builds all the work in order, the person may fold the skeleton into the first slice, whose merged code then settles the choices of convention. The records still come first.

Where software-engineering is installed, and its conventions corpus offers a location the project owns for them, the choices of convention that the skeleton, or the first slice it is folded into, settles are also drafted into that corpus. A person accepts them before code builds on them (refinement per [software-engineering:DEC-004-skeleton-conventions-in-corpus], whose point 4 says when the corpus offers such a location).

### 3. The first plan files the foundation, and the second plans the slices

The first plan files an EPIC for the work ([project-management:DEC-004-six-level-hierarchy]), with the intent and an outline of the slices in its body. It files the foundation's Feature under that EPIC, and no slice. For each shared choice, the plan says whether it is settled and where, or whether the foundation settles it by a record or by the skeleton. So the person sees each judgement at the plan's single approval gate, and can overrule one. Closing the foundation's Feature, which the person authorises ([project-management:DEC-006-state-machine-and-cascade]), hands the work to the second plan. The second plan reads the EPIC's body, and slices the work against the accepted records and the skeleton's code.

### 4. Tasks that would make a choice the foundation settles wait for it

- **A Task outside the foundation, not yet started,** in Todo or Backlog, that would make one of the foundation's choices names the foundation's Feature among its dependencies, so the pool holds it back until the Feature closes (DEC-059 point 7). The first plan adds the Feature to each such Task already filed. A Task filed later names it where the Feature's body lists its choice.
- **A Task In Progress or in Review** that already makes one of those choices goes on. The foundation's first Task names it among its dependencies, and its records start from what that Task chose.

The pool holds these Tasks back in a project with a topology. In a project with none, whoever hands out the work follows the same order.

### 5. A foundation that proves wrong is changed, never worked around

A Task that finds a choice of the foundation does not hold makes no other choice in its place, and says so on its Task. The change goes through a Task of its own: a record's change through a record the person accepts, as point 2 says, and a convention's change through the skeleton's code, reviewed as code. Where software-engineering is installed and the convention has an entry in its conventions corpus, that Task also changes the entry, and a person accepts the changed entry before code builds on it (refinement per [software-engineering:DEC-004-skeleton-conventions-in-corpus]).

## Rationale

**Why settle shared choices first.** A choice that each Task makes alone is made once by each agent working at once, and their answers differ. Merging different answers costs more than deciding once. Agents in separate clones share no context, only what is committed, so a choice settled once on the default branch gives every Task the same base.

**Why the trigger is a shared choice, and not new work.** A new product is the common case, but not the only one. A concern that crosses the slices of a product that stands leaves a choice open that its Tasks would make alone. One library used by one Task is no shared choice, and needs no foundation.

**Why plan the slices only after the foundation.** A slice filed before its choices are made carries a body written against decisions not yet taken, and would have to be read again. Planned after the foundation, each slice rests on records and code that exist. The person approves twice, and the second plan shows what the foundation chose.

**Why records before the skeleton.** Code must not rest on a draft record (the acceptance gate of `.pkit/decisions/README.md`). Records accepted first let the skeleton build on settled choices. Where the skeleton then finds that two of them do not fit, the change goes through point 5, and is reviewed as a record.

**Why a skeleton beside the records.** Records leave open how a request flows through the layers and how tests are laid out. One slice built end to end answers those questions in code that later slices copy.

**Why one Task at a time.** The foundation's choices depend on each other: a framework constrains the conventions, and a transport constrains the format of a message. Decided by several agents at once, they would fail as the slices would, one level up.

**Why the person may fold the skeleton for one agent.** One agent that builds in order sets each convention once, and its merged code settles the convention for the Tasks after it. The records still come first, since an architectural choice is reviewed before code rests on it, and a pattern in code with no record is drift ([pkit:COR-025]).

**The cost.** Workers wait while the foundation is built, and on a platform each waiting sandbox costs money. For a new product, nearly all the work waits, which is close to a phase of the project. In a product that stands, only the work that shares the open choice waits, and the rest of the pool goes on.

### Alternatives considered

- **Slice vertically from the first day.** Rejected: each Task makes the shared choices alone, as the Context says.
- **File the slices with the foundation, each naming it among its dependencies.** Rejected, as "Why plan the slices only after the foundation" says.
- **Partition by layer from the start, a seat for each layer.** Rejected, for DEC-059's reasons ("Why one shared pool, and vertical slices"). Layers built apart need their contract settled first in any case.
- **A Task for each decision, taken from the pool at once.** Rejected, as "Why one Task at a time" says.
- **The skeleton's layers built at once by several agents, once their contract is decided.** Not taken now: the layers share the repository's root files, and the skeleton's patterns would be several agents'. A later record may allow it, with the contract written as code.
- **Records drafted beside the skeleton, in one pull request.** Rejected: the skeleton would rest on drafts, as "Why records before the skeleton" says.
- **Leave the foundation to the first slice.** Rejected where agents work at once: slices started beside it make the same choices before it merges. For one agent, the skeleton may be folded into the first slice, as point 2 allows.

## Implications

- **Batch planning** gains the first stage: naming the shared choices, the EPIC with its outline, the foundation's Feature, and the judgement for each choice at the gate. Each role's procedure that slices work follows it (#2143), as does filing a Task during work, which names an open foundation's Feature where point 4 says.
- **No command changes.** The rule rests on the readiness that DEC-059 point 7 decides, on dependencies, which stay prose (DEC-005), and on the checkbox gate at close.
- **Named, and not decided here:** how a Task In Progress waits for a change to the foundation, since a dependency holds back only a Task in Backlog; a shared choice found during work, which no foundation named; which of two leads plans a foundation for a choice their scopes share; and a warning for a Task filed without an open foundation among its dependencies.
- **The analysis of parallel work** (#2096) gains the two stages in its use case of planning across scopes.
- **DEC-029 and DEC-059 point 7 are refined in place,** each with a pointer to this record, at DEC-029's batch-planning steps and at DEC-059's line on vertical slicing.
