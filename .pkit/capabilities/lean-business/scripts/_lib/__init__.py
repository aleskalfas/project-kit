"""The lean-business capability's data layer: an idea's files read, worked out and checked.

Imported by the capability's scripts. Each fact two readers share is worked out in one
module, so the check, the process's detections, the commands and the status never disagree
(lean-business DEC-002 points 12 to 14):

- `location` and `layout`: the folder that holds the ideas, and the place of each file in
  an idea's folder (points 1 and 2);
- `ids`: the ids, and the references between the files (point 7);
- `fingerprint`: the canonical form and the fingerprints taken over it (point 13);
- `timeline`: where a cycle's window and an experiment's time box fall once the cycle's
  suspensions are counted (point 12);
- `suspensions`: the rules a suspension keeps (point 12);
- `readings`: the facts worked out from the files, such as an experiment's pass or fail
  (points 2 and 10);
- `checks`: the capability's check, a member of validation (point 14).
"""
