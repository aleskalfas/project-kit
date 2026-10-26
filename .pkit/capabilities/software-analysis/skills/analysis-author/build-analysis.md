# Building an analysis

An analysis is built from its concepts up, in four steps ([software-analysis:DEC-001-software-analysis-discipline] point 12). Follow them for a new analysis, for an area you add later, and for the candidates of a brownfield project.

- **Each artefact uses only what the order puts before it:** what an earlier step wrote, or what its own step wrote first. So a definition uses terms already defined, and an area uses the areas it builds on. Each artefact names a concept by the one term that defines it, in every area.
- **Areas and journeys are part of the build, never extras afterwards** ([software-analysis:DEC-005-finding-functionality]). Step 3 plans the functional areas before the first use case, and step 4 writes a journey for each path the use cases make. Plan both from what the use cases do, never from how many there are.
- **Go back when something is missing.** Where an artefact needs something the order puts before it, and finds it missing, go back and write it there first. Then go on. It may be a concept, an actor, a requirement, or a use case of an area this one builds on.
- **Choose a kind's parts before its first artefact,** as the dispatcher says (`choose-templates.md`).
- **On a brownfield project,** start from the declared surface, and end once it is covered (the sections before step 1 and after step 4). Derive each step's candidates from the code, the existing documents and the project's decisions. A person confirms the candidates (DEC-001 point 9). Confirming a step's candidates before the next step builds on them saves rework, but the order does not ask it.

Each step below says what to write, and when it is done. "Names each concept by its term" means what the shared framing's "Use the glossary's terms" says.

## Before step 1, on a brownfield project: the declared surface

Before you derive any candidate, find the surface the analysis ought to cover (DEC-001 point 9). The project declares it as `surface` in the `friction` key of `.pkit/project/config.yaml`. An installed capability may declare some of it too.

1. **Run `pkit friction check --all`,** and read its `Uncovered surface` line.
2. **Where the line reads `no surface declared`,** the declared surface holds no file. Ask the person which paths the analysis ought to cover, such as `src/**`. Write the paths they name under `surface` by hand, since `pkit config set` writes no list, and run `pkit validate`. Derive no candidate until the check counts the paths of the declared surface.
3. **Where the line counts those paths,** go on with step 1. The paths listed under it are those no artefact anchors yet, and show where to start.

## 1. The concepts, then the actors

**Write:**

1. **List the concepts** the system works with, as its decisions, its code and its people use them. A word used as a dictionary has it needs no term (`term.md`, step 1).
2. **Give each concept one name.** Where two words name one thing, choose one, and use only it from here on. Where one word names two things, give each its own term.
3. **Stamp and define each term** (`term.md`). A definition gives the term's broader kind and what sets it apart. So define a broader concept before the concepts that name it as their kind. Name each concept a definition relates to by its term. A definition holds no word of its own term's name, so where a related term's name is such a word, name that concept in other words.
4. **Then the domain-model views,** where the project keeps a domain model (`view.md`). Group related concepts, and stamp one view for each group, in the order of their numbers. Each view explains its concepts and draws how they relate, and uses only the views numbered before it. Drawing the concepts finds those the definitions missed: go back and define each first.
5. **Then stamp the actors** (`actor.md`): each role that uses the system, with its needs.

**Done when:**

- each concept you listed is a term in force, defined, and anchored to what embodies it, or stamped with its reason for having no anchor
- each definition names each concept it relates to by its term
- no two terms define one concept, and no term names two
- where the project keeps a domain model, each group of related concepts is a view, each term in it is explained by one view, and each view names only the concepts of the views numbered before it
- each role that uses the system is an actor, its needs naming each concept by its term
- `pkit analysis validate --preview` reports nothing on the glossary, the views or the actors. Where a set of yours inherits `SAN`, its summary counts none of them among the artefacts no rule of `SAN` binds on.

You may not know every concept yet. A concept a later step finds is added then, by going back.

## 2. The requirements that bind the whole system

**Write** each obligation that holds across the whole system: how well the system must behave, a rule that holds across use cases, or a limit on the solution (`requirement.md`). Name the actors whose needs it meets, from step 1. Each requirement names its source, as the shared framing's "Name the source of what the system must do" says. A requirement that binds one area, or some areas, waits for step 3.

**Done when:**

- each obligation of the whole system that a record, a person or the code gives is a requirement, with its source
- each requirement's `applies-to` says where it holds
- each names each concept by its term
- `pkit analysis validate --preview` reports nothing on the requirements. Where a set of yours inherits `SAN`, its summary counts none of them among the artefacts no rule of `SAN` binds on.

## 3. The use cases, area by area

**Plan the areas first, from what the use cases will do** (DEC-005 point 1). Every use case lies in a functional area, so every analysis plans its areas, a small one included.

1. **List the functions.** Each need of an actor, from step 1, is the goal of a use case to come. Group the needs by the function each serves: what the component does, as a reader would say it. Each function is one area.
2. **Cut by what they do.** Never split an area because it holds many use cases, or merge two because each holds few. Never cut by actor, by a concept or by the code's modules, unless that is also what the use cases do together.
3. **One function, one area.** An analysis whose use cases all serve one function keeps them in one area.
4. **Order the areas.** For each, name the areas it builds on: those whose use cases make true what its use cases rely on, such as a precondition. Write an area only after the areas it builds on.

- **Two areas that build on each other** keep the cut by function: leave both without numbers and write them together. Make them one area only where they serve one function.
- **Give each area its goal** in the capability's settings file, beside the area's folder name, before the area's first use case ([software-analysis:DEC-003-analysis-diagrams] point 8). The overview shows it under the area.
  - **Its form:** one phrase that starts with its verb, as the shipped hints ask of a use case's goal. So it reads after "The goal is to …". It may end with "so" and its reason. An example is `010-ordering: Place an order and pay for it`.
  - **One level above the use cases:** the area's use cases are the steps toward its goal.
  - **No actor's voice:** no *I* or *my*, since an area has several actors.
  - **No rule of `SAN` judges it,** since it is a setting. So check its form yourself.

**For each area, in that order:**

1. **Its requirements:** those that bind this area alone, and those that bind some areas, this one the first of them (`requirement.md`, with `--area` for one that binds this area alone).
2. **Its use cases** (`use-case.md`, with `--area` always). Write one for each need of an actor that the area serves. Each lists the requirements it must meet. A use case whose function no area holds sends you back to the plan, for a new area or a goal drawn again.
3. **The paths you meet:** where a use case takes up what an earlier use case of the same actor left, toward one goal of that actor, note the path for step 4.
4. **Anything the area lacks:** go back to its step, write it there, and then use it. It may be a concept, an actor, a requirement, or a use case of an area this one builds on.

**An area is done when:**

- each need of an actor that the area serves is the goal of one of its use cases
- each of its use cases is a step toward the area's goal, and none serves another area's function
- each obligation that binds the area alone, or binds it first among some areas, is a requirement
- each of its use cases and requirements names each concept by its term
- `pkit analysis validate --preview` reports nothing on the area, and `pkit analysis check-numbers` passes

**The step is done** when every area is, and no use case in force lies outside an area.

## 4. The journeys, last

**Write a journey for each path the use cases make** (DEC-005 point 2, `journey.md`). A path is a goal one actor reaches only through several of its own use cases, taken in turn, each taking up what an earlier one left. Its use cases are written by now, in step 3.

1. **Find the paths.** Start from those you noted in step 3. Then read each actor's use cases for a precondition that another use case of the same actor makes true. `pkit analysis diagram chain` draws those links. Each is a sign of a path, never proof: ask whether the actor takes the two in turn toward one goal of its own.
2. **Judge from content, never by count.** An actor with many use cases may take no path, and one with two may take one. Never write a journey for an actor or an area only so that it has one.
3. **One journey for each whole path.** A stretch of a path needs no journey of its own, and a shorter path the actor sometimes takes is a variant of the journey. A path's steps may lie in several areas, and its journey is one.

**Done when:**

- each path the use cases make is a journey, across the areas it passes through
- each journey's steps make a path
- each journey names each concept by its term
- `pkit analysis validate --preview` reports nothing on the journeys, and `pkit analysis check-numbers` passes

## After step 4, on a brownfield project: the surface covered

Each step's list says when that step is done. Onboarding ends only once the declared surface is covered (DEC-001 point 9). So run `pkit friction check --all` once more, and read its two measures. The check never fails, so read the measures, not its exit status.

- **`Uncovered surface`** counts none uncovered, as in `0 of 40 paths in the declared surface`. A path it lists is one no artefact anchors yet. Go back to the step whose artefact describes what the path does, and anchor that artefact to the path, or write one there.
- **`Unanchored artefacts`** lists none of the analysis's artefacts. An artefact it lists has neither anchors nor a reason a person accepted. Anchor it, or show the person its reason for having none, word for word, and write the reason only once they accept it. The shared framing's "An actor, a term or a requirement nothing embodies" says how.

Until both hold, onboarding is not done, whatever each step's list says. An artefact accepted with its reason is listed apart, and never counted (COR-050 point 8).

## What a reviewer checks

A reviewer judges what the order leaves in the analysis under `SAN`'s `RS-SAN-008`, as the shared framing's "Use the glossary's terms" gives it. Under `RS-SAN-011`, a reviewer judges that each domain-model view names only the concepts of the views numbered before it. Under `RS-SAN-009`, a reviewer also judges which area builds on which: the producers each precondition names, and the areas' numbers. Under `RS-SAN-014`, a reviewer judges that each use case lies in its function's area, and that a journey tells each path. While these rules are proposed, they bind nothing, and this procedure asks the same of you. The order you write the steps in is yours to keep, and no rule holds it.
