---
# A functional requirement (software-analysis DEC-002 points 1 to 6): behaviour
# that holds across use cases, such as a business rule of the domain.
# Behaviour that serves one actor's goal is a use case instead.
# Stamp it, never copy it. `pkit analysis new functional-requirement <slug>`:
# - numbers it, and fills its title
# - writes its actors (`--actor <ACT-id>`, each) and the requirements it
#   refines (`--refines <REQ-id>`, each), and anchors each of them
# - writes it to `requirements/functional/` under the analysis location, or to
#   a folder per functional area in it (`--area <area>`)
# It also anchors the files that verify it (`--path`), and the records it rests
# on or that answer it (`--record`). One with no anchor at all gives the reason
# instead (`--unanchored-because`).
# Its id is one numbering across the three kinds of requirement, so a move to
# another kind keeps it. Its heading is its id, its kind and its title. The
# statement, the measure and where it holds are fields a tool reads. Each holds
# its hint until you write in its place what it asks for, and so does each part
# of the body. The body is rendered from the kind's declared structure
# (`schemas/artefact-kinds.yaml`).
# Its own fields' shape is `schemas/functional-requirement.schema.json`, and the friction
# block is the core's.
id: REQ-000                       # stamped: the next free number across the three kinds, never reused
title: <Title>                    # --title. The heading below repeats it after the id and the kind.
status: active                    # or withdrawn: the file stays and its id is never reused
statement: "<!-- pkit:hint The behaviour that holds across use cases, in one sentence, such as a business rule of the domain. Behaviour that serves one actor's goal is a use case instead. Example: Every total in a report counts approved figures only. -->"
measure: "<!-- pkit:hint The value or the condition that shows the requirement is met. Write `None.` when there is none yet. Example: Each total equals the sum of the approved figures it covers. -->"
applies-to: "<!-- pkit:hint Where the requirement holds, in words, such as a class of commands or the whole system. Name no use case or journey here, since each one that must meet it lists it. Example: Every total the system shows or exports. -->"
actors: [ACT-actor]               # --actor: each actor whose need it meets
refines: []                       # --refines: each requirement it refines, of any kind
pkit:
  friction:
    anchors:
      path: ["<test that verifies it>"]       # --path: each file that verifies it, and the narrow code that holds it
      record: ["<record it rests on>"]        # --record: each record it rests on, or that answers it (DEC-001 point 11)
      artefact: [ACT-actor]                   # stamped from its actors and the requirements it refines, as the two fields list them
---

# REQ-000 · Functional · <Title>

**Verified by:** <!-- pkit:hint Each test, check or review that shows the requirement is met, named by what it does and never by its path. Anchor the file of each test or check. Write `None.` when nothing verifies it yet. Example: A test builds a report from approved and draft figures, and checks that each total leaves the drafts out. -->

**Rationale:** <!-- pkit:hint Why the system must meet the requirement, and whose need it serves. Write `None.` when a record it rests on gives the reason. Example: A draft figure may still change, so a total that counts it misleads the manager who reads it. -->
