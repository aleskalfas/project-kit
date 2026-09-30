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
      artefact:
        - ACT-clone-session
        - .pkit/decisions/README.md
    revalidated:
      at: 2026-09-30T22:51:12Z
      outcome: unchanged
      unchanged-because: decisions validate gains a warning of revision narration inside a record, and the decisions README the steps for refining one in place; minting a number and the check that no two records share an id, which this use case describes, are unchanged
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
- **5a.** The record being renumbered has already landed on the default branch. The command refuses: renumbering a landed record would break the default branch.
- **5b.** The new number is already held on the default branch. The command refuses and names the next free one.

**Done when:** Both records are on the default branch under distinct numbers, and nothing is left to renumber after the merge.

**Design:** Situation S6 of the coordination design walk. Built today: minting from the working tree alone (`src/project_kit/decisions.py`), and the check that no two records in one tree share an id (`decisions_validate.py`). Intended, not built yet — EPIC #943 (F3): minting from the default branch, `validate --against` and `renumber`, which land in the code anchored here, and a core record for provisional numbering, which F3 adds as this use case's record anchor when it is accepted, revalidating the use case. Until then no accepted record decides how decision numbers are minted: the decisions README says how records are numbered today, and is the artefact anchor. A number is never reserved remotely, since an abandoned branch would strand it. The analysis capability numbers use cases and journeys the same way, first to the default branch keeping the number (`pkit analysis check-numbers`); the core record would generalise that rule to decision records.

**Gaps** (revalidation `2026-09-29-multi-clone-coordination`):

- **H, at 5a.** The design walked had `renumber` refuse "if `<old>` is on the default branch under another slug" — exactly the collision it exists to resolve. Proposed fix (pending authorisation; carried by F3 T3.2 of EPIC #943): refuse when the record being renumbered has already landed on the default branch, or when `<new>` is held there. Open: how "already landed" is recognised — by this branch's slug on the default branch, or by the record having existed at the merge-base, which a changed or coinciding slug cannot mislead.
