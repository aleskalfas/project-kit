---
# A functional requirement (software-analysis DEC-002 points 1 to 6): behaviour
# that holds across use cases, such as a business rule of the domain.
# Behaviour that serves one actor's goal is a use case instead. It lives in
# `requirements/functional/` under the analysis location, in a folder per
# functional area where the project groups them. Its id is one numbering
# across the three kinds of requirement, so a move to another kind keeps it.
# Its heading is its id, its kind and its title. The statement, the measure and
# where it holds are fields a tool reads. Each holds its hint until you write
# in its place what it asks for, and so does each part of the body. The body is
# rendered from the kind's declared structure (`schemas/artefact-kinds.yaml`).
# It anchors each actor in `actors` and each requirement in `refines`, the
# files that verify it, and the records it rests on or that answer it. Its own
# fields' shape is `schemas/functional-requirement.schema.json`, and the
# friction block is the core's.
id: REQ-000                       # the next free number across the three kinds, never reused
title: <Title>                    # the heading below repeats it after the id and the kind
status: active                    # or withdrawn: the file stays and its id is never reused
statement: "<!-- pkit:hint The behaviour that holds across use cases, in one sentence, such as a business rule of the domain. Behaviour that serves one actor's goal is a use case instead. Example: Every total in a report counts approved figures only. -->"
measure: "<!-- pkit:hint The value or the condition that shows the requirement is met. Write `None.` when there is none yet. Example: Each total equals the sum of the approved figures it covers. -->"
applies-to: "<!-- pkit:hint Where the requirement holds, in words, such as a class of commands or the whole system. Name no use case or journey here, since each one that must meet it lists it. Example: Every total the system shows or exports. -->"
actors: [ACT-actor]               # each actor whose need it meets
refines: []                       # each requirement it refines, of any kind
pkit:
  friction:
    anchors:
      path: ["<test that verifies it>"]       # each file that verifies it, and the narrow code that holds it
      record: ["<record it rests on>"]        # each record it rests on, or that answers it (DEC-001 point 11)
      artefact: [ACT-actor]                   # its actors and the requirements it refines, as the two fields list them
---

# REQ-000 · Functional · <Title>

**Verified by:** <!-- pkit:hint Each test, check or review that shows the requirement is met, named by what it does and never by its path. Anchor the file of each. Write `None.` when nothing verifies it yet. Example: A test builds a report from approved and draft figures, and checks that each total leaves the drafts out. -->

**Rationale:** <!-- pkit:hint Why the system must meet the requirement, and whose need it serves. Write `None.` when a record it rests on gives the reason. Example: A draft figure may still change, so a total that counts it misleads the manager who reads it. -->
