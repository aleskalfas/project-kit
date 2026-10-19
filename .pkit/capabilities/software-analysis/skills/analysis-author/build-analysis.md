# Building an analysis

An analysis is built from its concepts up, in four steps ([software-analysis:DEC-001-software-analysis-discipline] point 12). Follow them for a new analysis, for an area you add later, and for the candidates of a brownfield project.

- **Each artefact uses only what the order puts before it:** what an earlier step wrote, or what its own step wrote first. So a definition uses terms already defined, and an area uses the areas it builds on. Each artefact names a concept by the one term that defines it, in every area.
- **Go back when something is missing.** Where an artefact needs something the order puts before it, and finds it missing, go back and write it there first. Then go on. It may be a concept, an actor, a requirement, or a use case of an area this one builds on.
- **Choose a kind's parts before its first artefact,** as the dispatcher says (`choose-templates.md`).
- **On a brownfield project,** derive each step's candidates from the code, the existing documents and the project's decisions. A person confirms the candidates (DEC-001 point 9). Confirming a step's candidates before the next step builds on them saves rework, but the order does not ask it.

Each step below says what to write, and when it is done. "Names each concept by its term" means what the shared framing's "Use the glossary's terms" says.

## 1. The concepts, then the actors

**Write:**

1. **List the concepts** the system works with, as its decisions, its code and its people use them. A word used as a dictionary has it needs no term (`term.md`, step 1).
2. **Give each concept one name.** Where two words name one thing, choose one, and use only it from here on. Where one word names two things, give each its own term.
3. **Stamp and define each term** (`term.md`). A definition gives the term's broader kind and what sets it apart. So define a broader concept before the concepts that name it as their kind. Name each concept a definition relates to by its term. A definition holds no word of its own term's name, so where a related term's name is such a word, name that concept in other words.
4. **Then stamp the actors** (`actor.md`): each role that uses the system, with its needs.

**Done when:**

- each concept you listed is a term in force, defined, and anchored to what embodies it, or stamped with its reason for having no anchor
- each definition names each concept it relates to by its term
- no two terms define one concept, and no term names two
- each role that uses the system is an actor, its needs naming each concept by its term
- `pkit analysis validate --preview` reports nothing on the glossary or the actors. Where a set of yours inherits `SAN`, its summary counts none of them among the artefacts no rule of `SAN` binds on.

You may not know every concept yet. A concept a later step finds is added then, by going back.

## 2. The requirements that bind the whole system

**Write** each obligation that holds across the whole system: how well the system must behave, a rule that holds across use cases, or a limit on the solution (`requirement.md`). Name the actors whose needs it meets, from step 1. Each requirement names its source, as the shared framing's "Name the source of what the system must do" says. A requirement that binds one area, or some areas, waits for step 3.

**Done when:**

- each obligation of the whole system that a record, a person or the code gives is a requirement, with its source
- each requirement's `applies-to` says where it holds
- each names each concept by its term
- `pkit analysis validate --preview` reports nothing on the requirements. Where a set of yours inherits `SAN`, its summary counts none of them among the artefacts no rule of `SAN` binds on.

## 3. The use cases, area by area

**Order the areas first.** List the areas of the product. For each, name the areas it builds on: those whose use cases make true what its use cases rely on, such as a precondition. Write an area only after the areas it builds on.

- **Two areas that build on each other** are written together, or the line between them is drawn again.
- **A project that groups no use cases** writes them all as one area.

**For each area, in that order:**

1. **Its requirements:** those that bind this area alone, and those that bind some areas, this one the first of them (`requirement.md`, with `--area` for one that binds this area alone).
2. **Its use cases** (`use-case.md`, with `--area`). Write one for each need of an actor that the area serves. Each lists the requirements it must meet.
3. **Anything the area lacks:** go back to its step, write it there, and then use it. It may be a concept, an actor, a requirement, or a use case of an area this one builds on.

**An area is done when:**

- each need of an actor that the area serves is the goal of one of its use cases
- each obligation that binds the area alone, or binds it first among some areas, is a requirement
- each of its use cases and requirements names each concept by its term
- `pkit analysis validate --preview` reports nothing on the area, and `pkit analysis check-numbers` passes

**The step is done** when every area is.

## 4. The journeys, last

**Write** a journey where an actor's goal spans several use cases and what passes from one to the next can break (`journey.md`, step 1). Its use cases are written by now, in step 3.

**Done when:**

- each such goal of an actor is a journey, across the areas it passes through
- each journey names each concept by its term
- `pkit analysis validate --preview` reports nothing on the journeys, and `pkit analysis check-numbers` passes

## What a reviewer checks

A reviewer judges what the order leaves in the analysis under `SAN`'s `RS-SAN-008`, as the shared framing's "Use the glossary's terms" gives it. While the rule is proposed, it binds nothing, and this procedure asks the same of you. The order you write in, and which area builds on which, are yours to keep, and no rule holds them.
