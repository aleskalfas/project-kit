---
id: REQ-018
title: A reading command of the friction group prints the same document for the same state
status: active
statement: A reading command of the friction group, run with `--json` twice over the same state of the repository, prints the same bytes.
measure: Each such command, run twice over one state, prints byte-identical documents, their keys sorted. A document holds no age and nothing else the time of the run gives.
applies-to: "The JSON document of each reading command of the friction group: `pkit friction check`, `check --all`, `debt`, `explain`, `artefacts` and `since`. A command that writes, such as `friction resolve`, is outside it."
actors:
  - ACT-ci-pipeline
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_friction_check.py
        - tests/test_friction_repository.py
        - tests/test_friction_report.py
        - tests/test_friction_artefacts.py
      artefact:
        - ACT-ci-pipeline
---

# REQ-018 · Quality · A reading command of the friction group prints the same document for the same state

**Verified by:** Tests run the change check, the whole-repository check, the debt listing, the explanation of an artefact and the listing of artefacts twice over one state. Each finds the two documents equal. No test runs `friction since` twice.

**Rationale:** No record decides it. The requirement is its own home, and merging the change that adds it approves it (software-analysis DEC-002 point 8).

The CLI reference gives each of these documents as stable, its keys sorted, and says that components read them, never the human view. A reader that compares two runs then sees only what changed in the repository.

REQ-007 asks the same of a command a component registers. These commands are the backbone's own, so it does not reach them.
