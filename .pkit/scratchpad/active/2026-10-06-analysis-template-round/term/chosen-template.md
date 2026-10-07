The maintainer's chosen shape, filled with both terms. The glossary is one collection file, so both terms sit in it. The file is shown whole inside one fence, as it would read on the default branch.

- **Revalidation:** its `replaces` reads `[recheck]` (question 3). *Walkthrough*, a working name that means something else, is a distinction.
- **System:** its name has no article (question 4). Its definition is B's, in ISO's form, to be approved by the maintainer when stamped (question 2).
- **Both definitions:** each starts with its broader kind, with no article and no full stop, and never repeats its term. Revalidation's is B's without its first word, *one*, which the note explains.

````markdown
---
TERM-revalidation:
  name: revalidation
  status: active
  definition: review of some artefacts against one version of the system, which is a proposed design or the actual code
  replaces:
    - recheck
  pkit:
    friction:
      anchors:
        record: [COR-050, "software-analysis:DEC-001"]
TERM-system:
  name: system
  status: active
  definition: "software under discussion: pkit, as you install, run and extend it"
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
- **A walkthrough:** the example dialogue of one scenario in a storyboard (COR-016). DEC-001 point 7 names a scripted walk-through among the checks that are run, whose results are evidence. *Walkthrough* was the act's working name in the design behind DEC-001.

## TERM-system — system

**Example:** the system ends the landing `merged`, naming the head it merged at and the merge commit (UC-xxx, step 8).

**Distinctions:**

- **A system:** other software, such as the hosting service or the harness. The analysis names it for what it is, never a system (PR #1345, question 12).
- **A platform:** in COR-009, the hosting service a project's remote lives on. It is other software, never the system.
````
