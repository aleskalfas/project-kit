---
# A constraint (software-analysis DEC-002 points 1 to 6): a limit on the
# solution, which the design takes as given. It says who or what imposes it,
# where a requirement of the other two kinds says why it is needed.
# Stamp it, never copy it: `pkit analysis new constraint <slug>`
# numbers it, fills its title, its actors (`--actor <ACT-id>`, each) and the
# requirements it refines (`--refines <REQ-id>`, each), anchors each of them,
# and writes it to `requirements/constraints/` under the analysis location
# (`--area <area>` for a folder per functional area).
# Its id is one numbering across the three kinds of requirement, so a move to
# another kind keeps it. Its heading is its id, its kind and its title. The
# statement, the measure and where it holds are fields a tool reads. Each holds
# its hint until you write in its place what it asks for, and so does each part
# of the body. The body is rendered from the kind's declared structure
# (`schemas/artefact-kinds.yaml`).
# It also anchors the files that verify it (`--path`), and the records it rests
# on or that answer it (`--record`). One with no anchor at all gives the reason
# instead (`--unanchored-because`). Its own fields' shape is
# `schemas/constraint.schema.json`, and the friction block is the core's.
id: REQ-000                       # stamped: the next free number across the three kinds, never reused
title: <Title>                    # --title. The heading below repeats it after the id and the kind.
status: active                    # or withdrawn: the file stays and its id is never reused
statement: "<!-- pkit:hint The limit on the solution, in one sentence, which the design takes as given. Example: The system stores every figure inside the client's own country. -->"
measure: "<!-- pkit:hint The value or the condition that shows the constraint is kept. Write `None.` when there is none yet. Example: Every store of figures, backups included, lies in a data centre in that country. -->"
applies-to: "<!-- pkit:hint Where the constraint holds, in words, such as a class of commands or the whole system. Name no use case or journey here, since each one that must meet it lists it. Example: The whole system, its backups included. -->"
actors: [ACT-actor]               # --actor: each actor whose need it meets
refines: []                       # --refines: each requirement it refines, of any kind
pkit:
  friction:
    anchors:
      path: ["<test that verifies it>"]       # --path: each file that verifies it, and the narrow code that holds it
      record: ["<record it rests on>"]        # --record: each record it rests on, or that answers it (DEC-001 point 11)
      artefact: [ACT-actor]                   # stamped from its actors and the requirements it refines, as the two fields list them
---

# REQ-000 · Constraint · <Title>

**Verified by:** <!-- pkit:hint Each test, check or review that shows the constraint is kept, named by what it does and never by its path. Anchor the file of each test or check. Write `None.` when nothing verifies it yet. Example: A review before each release checks where every store of figures lies. -->

**Imposed by:** <!-- pkit:hint Who or what imposes the constraint, and why the design cannot choose otherwise. Write `None.` when a record it rests on says so. Example: The client's contract forbids storing its figures abroad, and no design can change the contract. -->
