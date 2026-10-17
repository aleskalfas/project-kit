---
# A use case (software-analysis DEC-001 points 1, 3 and 4): one actor's goal
# and how the system fulfils it. Stamp it, never copy it: `pkit analysis new
# use-case <slug> --actor <ACT-id>` numbers it, fills its title, its actor, its
# other actors (`--other-actor <ACT-id>`, each) and an anchor to each actor,
# and writes it to `use-case-model/use-cases/` under the
# analysis location (`--area <area>` for a folder per functional area). Its
# heading is its id and title, as the front matter gives them. Its body is
# rendered from the use case's declared structure (`schemas/artefact-kinds.yaml`).
# Each part holds its hint until you write in its place what it asks for. Its
# own fields' shape is `schemas/use-case.schema.json`; the friction block is the
# core's.
id: UC-000                        # stamped: the next free number, never reused
title: <Title>                    # --title; the heading below repeats it after the id
status: active                    # or withdrawn: the file stays and its id is never reused
actor: ACT-actor                  # the actor whose goal this is
other-actors: []                  # --other-actor: each other actor who takes part
pkit:
  friction:
    anchors:
      path: ["<code it exercises>"]           # --path: a change there asks whether the use case still holds
      record: ["<record it rests on>"]        # --record: each record it rests on, or that answers it. A change to one asks the same (DEC-001 point 11)
      artefact: [ACT-actor]                   # its actor and other actors: a changed actor flags this use case
---

# UC-000 — <Title>

**Goal:** <!-- pkit:hint What the actor wants from this use case, in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. Example: Export my report as a file. -->

**Other actors:** <!-- pkit:hint Each other actor who takes part, and what this use case must protect for them. Write `None.` when there is none. Example: **Auditor** (`ACT-auditor`): each export is logged with who made it. -->

**Preconditions:** <!-- pkit:hint What the system, or an earlier use case, has already made true before the use case starts. Each is a state, not an event, and no step checks it. Write `None.` when there is none. Example: The analyst is signed in. -->

**Assumptions:** <!-- pkit:hint What must also be true for the use case to work, but nothing in the system secures. Name the record that admits each. Write `None.` when there is none. Example: The disk keeps the file as the system wrote it (DEC-003). -->

**Trigger:** <!-- pkit:hint The event that starts the use case, and who or what causes it. Example: The analyst asks to export the report on screen. -->

**Main path:** <!-- pkit:hint Numbered steps from the start to the goal, each saying who does what. Example: 1. The analyst chooses `Export`. 2. The system writes the report to a file. -->

**Variants:** <!-- pkit:hint One for each condition, lettered after the step it branches from. Say what happens instead, and where the path rejoins or ends. Write `None.` when there is none. Example: 2a. The disk is full. The system says so and writes nothing, and the use case ends. -->

**Postconditions:** <!-- pkit:hint The state that shows the goal is met. Example: The file holds the whole report. -->

**Minimal guarantees:** <!-- pkit:hint What the system still guarantees when the use case ends early or fails. Name the record or code each rests on. Write `None.` when there is none. Example: A failed export leaves no partial file (DEC-003). -->
