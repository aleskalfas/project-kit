---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-anchor, name: anchor}
      - {id: TERM-decision-record, name: decision record}
      - {id: TERM-finding, name: finding}
      - {id: TERM-rule, name: rule}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Write a page for the reader it names, with anchors that ground each statement it makes.
          - Have the fix for a stale page proposed with its evidence, and review the fix before it is applied.
          - Have a page read as its declared reader would read it, each finding citing the rule the page breaks.
      - id: ACT-adopter
        name: Adopter
        needs:
          - Set up a documentation space for one audience, with its own location and a definition whose scope selects its pages.
          - Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.
TERM-page:
  name: page
  status: active
  definition: "document of a documentation space, written for the reader it declares and anchored to what makes it true"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/living-docs/schemas/page.schema.json
        record:
          - living-docs:DEC-001#1
          - living-docs:DEC-001#4
      revalidated:
        at: 2026-10-23T20:56:32Z
        outcome: unchanged
        unchanged-because: DEC-001 point 1 changes only where a new page may go, under its space's root or into a place assigned to that space. What a page is, which this term defines, does not change.
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than living-docs's floor, 1.149.0.
  - **Term:** [anchor](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-anchor--anchor)
  - **Term:** [decision record](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-decision-record--decision-record)
  - **Term:** [finding](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-finding--finding)
  - **Term:** [rule](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-rule--rule)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Write a page for the reader it names, with anchors that ground each statement it makes.
    - Have the fix for a stale page proposed with its evidence, and review the fix before it is applied.
    - Have a page read as its declared reader would read it, each finding citing the rule the page breaks.
  - **Actor:** [Adopter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-adopter.md)
    - Set up a documentation space for one audience, with its own location and a definition whose scope selects its pages.
    - Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.

## TERM-page — page

**Example:** `.pkit/permissions/README.md` declares the kind `reference` and the reader `user`, and anchors `.pkit/permissions/decide.py`, so a change to that code asks it whether it still holds.

**Distinctions:**

- **Unclassified document:** a document in a space's places that declares no page kind. It is no page, and onboarding classifies it (DEC-001 point 4).
- **Decision record:** a document a page anchors. It is never a page, whatever place it lies in (DEC-001 point 4).
- **Page kind:** what a page declares in `kind`, such as `reference`. Declaring it is what makes a document a page (DEC-001 point 4).
