---
TERM-revalidation:
  name: revalidation
  status: active
  definition: "A revalidation is one review of some artefacts against one version of the system: a proposed design, or the actual code."
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
  definition: "The system under discussion: pkit, as the platform you install, run and extend."
  pkit:
    friction:
      unanchored-because: "It names the whole of pkit, so an anchor on its code would match every change. Its meaning is the maintainer's answer on PR #1345, which no record holds."
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-revalidation — revalidation

**Bounded context:** the analysis, where software-analysis names the act. The core records the same act, by the same name, in an artefact's friction block (DEC-001 point 4 and COR-050 point 3).

**Invariants:**

- It is written on the artefact it covers, on a person's decision, and never by the job that runs after merges (COR-050 point 3).
- Only a revalidation or a deferral recorded on the artefact clears friction (DEC-001 point 7).
- For each artefact it ends in one of four outcomes, recorded as `updated` or `unchanged` (DEC-001 point 5).
- It never rewrites the analysis to match broken code. Where stale versus regressed is unclear, a person decides before it is recorded (DEC-001 point 5).

**Examples:**

- A change to COR-009 flags `ACT-developer`. The developer finds that the actor still holds, and records the revalidation with `pkit friction revalidate`.
- Before a change's code is written, the developer revalidates the use cases its design touches. The revalidation is planned, so it leaves a record (DEC-001 point 6).

## TERM-system — the system

**Bounded context:** project-kit's analysis, where it means pkit. In the hints software-analysis ships, the same words mean each project's own software (`SA/templates/actors.md`).

**Invariants:**

- Every actor is a role that uses it (DEC-001 point 1).
- Every use case says how it fulfils one actor's goal (DEC-001 point 1).
- No other software is called a system. Each is named for what it is, such as the hosting service or the harness (PR #1345, question 12).

**Examples:**

- The system ends the landing `merged`, naming the head it merged at and the merge commit (UC-xxx, step 8).
