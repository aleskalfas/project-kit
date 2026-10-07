---
TERM-revalidation:
  name: revalidation
  status: active
  definition: "A revalidation is one review of some artefacts against one version of the system: a proposed design, or the actual code."
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
  definition: "The system under discussion: pkit, as the platform you install, run and extend."
  pkit:
    friction:
      unanchored-because: "It names the whole of pkit, so an anchor on its code would match every change. No record defines it."
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-revalidation — revalidation

**Example:** a change to COR-009 flags `ACT-developer`. The developer finds that the actor still holds, and records the revalidation with `pkit friction revalidate`.

**Distinctions:**

- **The `revalidated` block:** where an artefact records its last revalidation, with its `at`, its outcome and its deferrals (COR-050 point 3). DEC-001 point 4 calls that record the artefact's revalidation too.
- **A revalidation record:** the document a revalidation leaves when it is planned, or finds a gap or a regression (DEC-001 point 6). A routine revalidation leaves none.
- **Testing:** it asks whether the software still does what a description says, and fixes the software. A revalidation asks whether the description is still true, and usually fixes the description (DEC-001 point 7).
- **A storyboard's walkthrough:** the example dialogue of one scenario in a storyboard (COR-016). *Walkthrough* was the act's working name in the design behind DEC-001.

## TERM-system — the system

**Example:** the system ends the landing `merged`, naming the head it merged at and the merge commit (UC-xxx, step 8).

**Distinctions:**

- **A system:** other software, such as the hosting service or the harness. The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the service a project's remote lives on. The definition calls pkit a platform in another sense, as what you install, run and extend.
