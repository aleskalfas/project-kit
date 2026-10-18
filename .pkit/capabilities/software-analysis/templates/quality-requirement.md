---
# A quality requirement (software-analysis DEC-002 points 1 to 6): how well
# the system must behave, such as how fast, how reliably or how safely. It
# lives in `requirements/quality/` under the analysis location, in a folder per
# functional area where the project groups them. Its id is one numbering
# across the three kinds of requirement, so a move to another kind keeps it.
# Its heading is its id, its kind and its title. The statement, the measure and
# where it holds are fields a tool reads. Each holds its hint until you write
# in its place what it asks for, and so does each part of the body. The body is
# rendered from the kind's declared structure (`schemas/artefact-kinds.yaml`).
# It anchors each actor in `actors` and each requirement in `refines`. It also
# anchors the files that verify it, and the records it rests on or that answer
# it. Its own fields' shape is `schemas/quality-requirement.schema.json`, and
# the friction block is the core's.
id: REQ-000                       # the next free number across the three kinds, never reused
title: <Title>                    # the heading below repeats it after the id and the kind
status: active                    # or withdrawn: the file stays and its id is never reused
statement: "<!-- pkit:hint How well the system must behave, in one sentence, such as how fast, how reliably or how safely. Say what the system achieves, never how it is built. Example: The system shows a report within two seconds of the analyst opening it. -->"
measure: "<!-- pkit:hint The value or the condition that shows the requirement is met. Write `None.` when there is none yet. Example: 95 of every 100 reports of a year's figures show within two seconds. -->"
applies-to: "<!-- pkit:hint Where the requirement holds, in words, such as a class of commands or the whole system. Name no use case or journey here, since each one that must meet it lists it. Example: Every report an analyst opens. -->"
actors: [ACT-actor]               # each actor whose need it meets
refines: []                       # each requirement it refines, of any kind
pkit:
  friction:
    anchors:
      path: ["<test that verifies it>"]       # each file that verifies it, and the narrow code that holds it
      record: ["<record it rests on>"]        # each record it rests on, or that answers it (DEC-001 point 11)
      artefact: [ACT-actor]                   # its actors and the requirements it refines, as the two fields list them
---

# REQ-000 · Quality · <Title>

**Verified by:** <!-- pkit:hint Each test, check or review that shows the requirement is met, named by what it does and never by its path. Anchor the file of each test or check. Write `None.` when nothing verifies it yet. Example: A timing test opens a report of a year's figures, and fails if it takes over two seconds to show. -->

**Rationale:** <!-- pkit:hint Why the system must meet the requirement, and whose need it serves. Write `None.` when a record it rests on gives the reason. Example: Analysts read reports during meetings, and a slow report holds the meeting up. -->
