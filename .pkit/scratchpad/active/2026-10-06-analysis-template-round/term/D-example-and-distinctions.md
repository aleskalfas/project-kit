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

**Example:** a change to COR-009 flags `ACT-developer`. The developer finds that the actor still holds, and records the revalidation with `pkit friction revalidate`.

**Distinctions:**

- **Testing:** it asks whether the software still does what a description says, and fixes the software. A revalidation asks whether the description is still true, and usually fixes the description (DEC-001 point 7).
- **A storyboard's walkthrough:** the example dialogue of one scenario in a storyboard (COR-016). *Walkthrough* was an earlier name of this term.

## TERM-system — the system

**Example:** the system ends the landing `merged`, naming the head it merged at and the merge commit (UC-xxx, step 8).

**Distinctions:**

- **An actor:** a role that uses the system, such as the CI pipeline or an AI agent (DEC-001 point 1).
- **Other software:** never called a system. It is named for what it is, such as the hosting service or the harness (PR #1345, question 12).
