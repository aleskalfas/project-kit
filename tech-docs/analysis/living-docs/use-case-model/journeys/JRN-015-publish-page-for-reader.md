---
id: JRN-015
title: Write a page and have it read as its reader would read it
status: active
actor: core:ACT-developer
steps:
  - UC-044
  - UC-046
relies-on: []
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/schemas/page.schema.json
        - .pkit/capabilities/living-docs/scripts/_lib/readers.py
      record:
        - living-docs:DEC-001#3
        - living-docs:DEC-001#4
        - living-docs:DEC-001#5
        - living-docs:DEC-001#6
      artefact:
        - UC-044
        - UC-046
---

# JRN-015 — Write a page and have it read as its reader would read it

**Goal:** Write a page for the reader it names, and know before I publish it that it serves that reader.

**Steps:**

1. [UC-044](../use-cases/020-write/UC-044-write-page.md) — Write a page for the reader it names
2. [UC-046](../use-cases/020-write/UC-046-review-page-as-reader.md) — Have a page read as its declared reader would read it
   - **Needs from step 1 (UC-044):** the [page](../../glossary.md#term-page--page), whose front matter names its [reader](../../glossary.md#term-reader--reader) and its [page kind](../../glossary.md#term-page-kind--page-kind), with its anchors. The agent takes that reader's needs from the readers [data point](../../../core/glossary.md#term-data-point--data-point). Where `RS-LDOC-003` binds, a reader the data point does not hold leaves the page unread (UC-046 variant 3b). Nothing checked, as the page was written, that its anchors ground its statements, so the [reader-review](../../glossary.md#term-reader-review--reader-review) judges that grounding (living-docs DEC-001 points [3](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#3-what-the-shared-rules-require) and [6](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#6-reader-review)).

**Variants:**

- **1a.** The [page](../../glossary.md#term-page--page)'s [documentation space](../../glossary.md#term-documentation-space--documentation-space) has no [space definition](../../glossary.md#term-space-definition--space-definition) yet, so no [rule](../../../core/glossary.md#term-rule--rule) binds on the page ([UC-044](../use-cases/020-write/UC-044-write-page.md) variant 6c). The [reader-review](../../glossary.md#term-reader-review--reader-review) judges the page against no rule, and names what [validation](../../../core/glossary.md#term-validation--validation) reports of the page ([UC-046](../use-cases/020-write/UC-046-review-page-as-reader.md) variant 2a).
- **2a.** The reader-review finds what the [reader](../../glossary.md#term-reader--reader) misses or does not need. The developer mends the page as the review's [findings](../../../core/glossary.md#term-finding--finding) direct, and the path rejoins at step 2.
- **2b.** The agent finds nothing, says so in one line and writes no record. The path ends (UC-046 variant 7a).

**Postconditions:** The [page](../../glossary.md#term-page--page) lies in its [documentation space](../../glossary.md#term-documentation-space--documentation-space) and anchors what its statements rest on. It names its [reader](../../glossary.md#term-reader--reader) and its [page kind](../../glossary.md#term-page-kind--page-kind). A [reader-review](../../glossary.md#term-reader-review--reader-review) of the page as it stands found nothing the reader misses or does not need. So the developer knows that the page serves its reader.

**Minimal guarantees:**

- Stopping after step 1 leaves the [page](../../glossary.md#term-page--page) as the developer wrote it, naming its [reader](../../glossary.md#term-reader--reader) and its [page kind](../../glossary.md#term-page-kind--page-kind) ([living-docs DEC-001 point 4](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#4-pages-are-anchored-and-revalidated)).
- The [reader-review](../../glossary.md#term-reader-review--reader-review) changes no page. Each [finding](../../../core/glossary.md#term-finding--finding) gives a direction, never a rewritten page. Nothing the agent suggests is applied until the developer accepts it (living-docs DEC-001 points [5](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#5-fixes-are-proposed-never-applied-blind) and [6](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md#6-reader-review)).
