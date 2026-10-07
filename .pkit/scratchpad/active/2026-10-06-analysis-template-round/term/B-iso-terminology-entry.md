---
TERM-revalidation:
  name: revalidation
  status: active
  definition: review of some artefacts against one version of the system, a proposed design or the actual code
  replaces:
    - walkthrough
    - walk
  pkit:
    friction:
      anchors:
        record: [COR-016, COR-050, "software-analysis:DEC-001"]
TERM-system:
  name: the system
  status: active
  definition: platform under discussion, pkit, as you install, run and extend it
  pkit:
    friction:
      unanchored-because: "It names the whole of pkit, so an anchor on its code would match every change. Its meaning is the maintainer's answer on PR #1345, which no record holds."
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-revalidation — revalidation

**Admitted terms:** None.

**Deprecated terms:** walkthrough, walk

**Example:** A change to COR-009 flags `ACT-developer`. The developer finds that the actor still holds, and records the revalidation with `pkit friction revalidate`.

**Notes to entry:**

- **Note 1 to entry:** A revalidation ends in one of four outcomes for each artefact (DEC-001 point 5). It holds, the analysis was stale, the code regressed, or a gap was found.
- **Note 2 to entry:** A revalidation reads the description, and testing runs the software (DEC-001 point 7).
- **Note 3 to entry:** *walkthrough* also names a part of each storyboard, its example dialogue (COR-016).

**Related terms:** `TERM-system`, which the definition uses.

**Source:** software-analysis DEC-001 point 5, modified. The article and the colon are dropped.

## TERM-system — the system

**Admitted terms:** None.

**Deprecated terms:** None.

**Example:** The system ends the landing `merged`, naming the head it merged at and the merge commit (UC-xxx, step 8).

**Notes to entry:**

- **Note 1 to entry:** The term is reserved. Other software is named for what it is, such as the hosting service or the harness, never a system (PR #1345, question 12).
- **Note 2 to entry:** Every actor is a role that uses the system (DEC-001 point 1).

**Related terms:** None.

**Source:** the maintainer's answer to question 12 on PR #1345, modified. The definition leaves out *system*, since a definition may not repeat its term.
