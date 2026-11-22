"""The lean-business capability's library: an idea's files read, worked out, checked and
written.

Imported by the capability's scripts. Each fact two readers share is worked out in one
module, so the check, the process's detections, the commands and the status never disagree
(lean-business DEC-002 points 12 to 14):

- `root`: the project a command runs in, and the capability's own paths in it;
- `location` and `layout`: the folder that holds the ideas, the place of each file in an
  idea's folder, and the file of a subject's id (points 1 and 2);
- `listing`: the files git sees, which the backbone's data validation reads too;
- `reading`: a file read as YAML 1.2, a day as the text it is written as;
- `ids`: the ids, and the references between the files (point 7);
- `model`: an idea's subjects, and the lookups between them, each with a typed result that
  tells a subject found from a reference that names nothing, one into a kind of which the
  location holds no file, and another idea's subject (points 2 and 7);
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
- `readings`: the facts worked out from the files, such as whether a canvas is priced, an
  experiment's pass or fail, an assumption's outcome and an idea dropped (points 2 and 10;
  DEC-003 point 8);
- `checks` and `findings`: the capability's check, a member of validation, and the findings
  it gives, each with its severity and its label (point 14);
- `positions`: where each subject of the capability's processes stands, read from its files
  whenever a process predicate asks, and what the predicates answer the engine (DEC-003
  points 1 to 4 and 7).

What the commands write and read through (DEC-001 point 3; DEC-003 point 5):

- `acting`: the context a command runs in, with the day its entry read and the engine it
  asks; its consent forms; content, an act, a move and an act the script's move follows;
  and what a command prints after its write;
- `writes`: a write built, held to the check and the data validation as the files would
  stand, then written, or undone where a move after it is refused; the location's record;
- `editing`: a file edited round trip, its comments, quoting and order kept;
- `naming`: the ids a write gives, from `--id` or the text, and those taken or named; and
  the id that a person's name of an assumption or a cycle reads as;
- `staling`: each verdict and shortlisting a write leaves stale;
- `engine` and `backbone`: the process engine's status, can-move and move, reached through
  `pkit`;
- `canvases`: a variant's canvas and its boxes, as the desk commands read and change them;
- `assumptions`, `experiments` and `cycles`: a variant's assumptions, an experiment and the
  cycle it names, and a cycle's plan, its suspensions and its review, as the experiment
  path's commands read and change them;
- `estimates`: the viability estimate, worked out from the goal and the inputs (DEC-002
  point 4);
- `grid`: a canvas drawn as the book's grid, with its credit line (DEC-001 point 6);
- `briefing`: the status, with the briefing that brings a person back to an idea, each
  position the engine's, and its structured form (DEC-001 point 10; DEC-002 point 15).

None reads the clock: a gate, and a reading that depends on a day, takes the day from its
caller (DEC-003 point 1; COR-055 point 2).
"""
