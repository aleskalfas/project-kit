---
id: UC-006
title: Resolve a decision number two clones took
status: active
actor: ACT-clone-session
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/decisions.py
        - src/project_kit/decisions_validate.py
      record:
        - software-analysis:DEC-001
      artefact:
        - ACT-clone-session
        - .pkit/decisions/README.md
---

# UC-006 — Resolve a decision number two clones took

**Goal:** When two clones mint the same decision number in parallel, the second learns it before merging, and renumbers with one command.

**Starts when:** A clone session authors a new decision record on its branch while another clone may be doing the same.

**Main path:**

1. The session mints the record's number (`pkit new decision`) from the fetched default branch as well as the working tree: one past the highest either holds.
2. Another clone, minting from the same default branch before either merged, takes the same number for a different record.
3. The other clone's pull request reaches the default branch first, and keeps the number.
4. On this branch, the check against the default branch (`decisions validate --against <ref>`, run in CI) fails: another record holds the number there.
5. The session renumbers its record (`decisions renumber <old> <new>`): the file name, the record's id, and the typed references and Markdown links in the files the branch changed.
6. The command reports what it cannot rewrite — bare mentions of the id, and mentions outside the tree such as commits, issues and changesets — for the session to fix by hand.
7. The check passes, and the record merges under its new number.

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** The default branch cannot be fetched (offline). The number comes from the working tree alone, with a warning.
- **5a.** The record being renumbered has already landed on the default branch under this branch's slug. The command refuses: renumbering a landed record would break the default branch.
- **5b.** The new number is already held on the default branch. The command refuses and names the next free one.

**Done when:** Both records are on the default branch under distinct numbers, and nothing is left to renumber after the merge.

**Design:** Situation S6 of the coordination design walk. Built today: minting from the working tree alone (`src/project_kit/decisions.py`), and the check that no two records in one tree share an id (`decisions_validate.py`). Intended, not built yet — EPIC #943: minting from the default branch, `validate --against`, `renumber`, and a core record for provisional numbering. A number is never reserved remotely, since an abandoned branch would strand it. The analysis capability already numbers use cases and journeys the same way, first to the default branch keeping the number (`pkit analysis check-numbers`).
