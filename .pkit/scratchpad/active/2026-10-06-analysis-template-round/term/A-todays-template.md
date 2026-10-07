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

The words of the domain and what each means. A term's id is stable; its name may change, and the names it replaces are kept.

## TERM-revalidation — revalidation

A revalidation is planned before a change's code, or triggered by friction, by a landing that changes artefacts, or by onboarding (DEC-001 point 5). It ends, for each artefact, in one of four outcomes: it holds, the analysis was stale, the code regressed, or a gap was found. It is not testing, which runs the software rather than reading the description (DEC-001 point 7). Nor is it a storyboard's walkthrough (COR-016), though *walkthrough* was its earlier name.

For example, a change to COR-009 flags `ACT-developer`. The developer finds that the actor still holds, and records the revalidation with `pkit friction revalidate`.

## TERM-system — the system

In the analysis, the system is always pkit, as a whole. Every actor is a role that uses it (DEC-001 point 1). The word is reserved: other software is named for what it is, such as the hosting service or the harness (PR #1345, question 12). For example, the system ends the landing `merged` (UC-xxx, step 8).
