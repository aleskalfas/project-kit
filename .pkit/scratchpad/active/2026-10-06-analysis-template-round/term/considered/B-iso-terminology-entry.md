---
TERM-revalidation:
  name: revalidation
  status: active
  definition: one review of some artefacts against one version of the system, which is a proposed design or the actual code
  replaces:
    - recheck
    - walkthrough
    - walk
  pkit:
    friction:
      anchors:
        record: [COR-050, "software-analysis:DEC-001"]
TERM-system:
  name: the system
  status: active
  definition: "software under discussion: pkit, as you install, run and extend it"
  pkit:
    friction:
      unanchored-because: "It names the whole of pkit, so an anchor on its code would match every change. No record defines it."
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-revalidation — revalidation

**Admitted terms:** None.

**Deprecated terms:** recheck, walkthrough, walk

**Example:** A change to COR-009 flags `ACT-developer`. The developer finds that the actor still holds, and records the revalidation with `pkit friction revalidate`.

**Notes to entry:**

- **Note 1 to entry:** A revalidation ends in one of four outcomes for each artefact (DEC-001 point 5). It holds, the analysis was stale, the code regressed, or a gap was found.
- **Note 2 to entry:** An artefact's `revalidated` block records its last revalidation (COR-050 point 3). DEC-001 point 4 calls that record the artefact's revalidation too.
- **Note 3 to entry:** A revalidation that is planned, or that finds a gap or a regression, leaves a revalidation record (DEC-001 point 6).
- **Note 4 to entry:** A revalidation reads the description, and testing runs the software (DEC-001 point 7).
- **Note 5 to entry:** *walkthrough* also names a part of each storyboard, its example dialogue (COR-016).

**Related terms:** `TERM-system`, which the definition uses.

**Source:** software-analysis DEC-001 point 5, modified. "A revalidation is" is dropped, and "which is" stands for the colon.

## TERM-system — the system

**Admitted terms:** None.

**Deprecated terms:** None.

**Example:** The system ends the landing `merged`, naming the head it merged at and the merge commit (UC-xxx, step 8).

**Notes to entry:**

- **Note 1 to entry:** The term is reserved. Other software is named for what it is, such as the hosting service or the harness, never a system (PR #1345, question 12).
- **Note 2 to entry:** *System under discussion* is Cockburn's name for the system a use case describes, *SuD*.
- **Note 3 to entry:** COR-009 calls the service a project's remote lives on a platform, which is not the platform the definition means.

**Related terms:** None.

**Source:** the maintainer's answer to question 12 on PR #1345, modified. The definition leaves out *system*, since a definition may not repeat its term.
