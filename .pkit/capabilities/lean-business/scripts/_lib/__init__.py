"""The lean-business capability's data layer: an idea's files read, worked out and checked.

Imported by the capability's scripts. Each fact two readers share is worked out in one
module, so the check, the process's detections, the commands and the status never disagree
(lean-business DEC-002 points 12 to 14):

- `location` and `layout`: the folder that holds the ideas, the place of each file in an
  idea's folder, and the file of a subject's id (points 1 and 2);
- `listing`: the files git sees, which the backbone's data validation reads too;
- `ids`: the ids, and the references between the files (point 7);
- `model`: an idea's subjects, and the lookups between them, each with a typed result
  (points 2 and 7);
- `gates`: the gates of the moves and the acts, each asked with the day of its act
  (DEC-003 points 2 to 4);
- `acts`: the acts recorded in an idea's files, each with the gate that judges it, asked
  with the cycles as their suspensions stood (DEC-002 points 12 and 14);
- `fingerprint`: the canonical form, the fingerprints taken over it, and whether a kept
  one still matches (point 13);
- `timeline`: where a cycle's window and an experiment's time box fall once the cycle's
  suspensions are counted, as they stand or as they stood on a day (point 12);
- `suspensions`: the rules a suspension keeps, contradicting no act already recorded among
  them (point 12);
- `schemas`: where each kind of file writes a day, read from its schema (DEC-003 point 1);
- `readings`: the facts worked out from the files, such as an experiment's pass or fail
  and an assumption's outcome (points 2 and 10; DEC-003 point 8);
- `checks`: the capability's check, a member of validation (point 14);
- `positions`: where each subject of the capability's processes stands, read from its files
  whenever a process predicate asks, and what the predicates answer the engine (DEC-003
  points 1 to 4 and 7).

None reads the clock: a gate, and a reading that depends on a day, takes the day from its
caller (DEC-003 point 1; COR-055 point 2).
"""
