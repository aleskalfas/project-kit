---
id: REQ-025
title: Nothing in living-docs fetches the text a captured source names
status: active
statement: No command and no agent of living-docs fetches the text a captured source names, or compares it with the version the project recorded.
measure: "The resolver of a `source` anchor and validation reach no network. For a page stale on a `source` anchor, the agent asks a person what changed in the text, and reads no part of it."
applies-to: "Every command living-docs registers, and the living-docs agent in each of its intents, wherever a captured source is read or a page rests on one."
actors:
  - core:ACT-developer
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/resolve-source.py
        - .pkit/capabilities/living-docs/scripts/_lib/source_layout.py
        - .pkit/capabilities/living-docs/agents/living-docs/living-docs.md
        - tests/test_living_docs_sources.py
      record:
        - living-docs:DEC-001#4
        - COR-050#2
    revalidated:
      at: 2026-10-25T05:30:36Z
      outcome: unchanged
      unchanged-because: The agent's reader-review now reads the reading-evidence point through the backbone. Nothing in living-docs fetches a captured source's text, as before.
---

# REQ-025 · Constraint · Nothing in living-docs fetches the text a captured source names

**Verified by:** A test runs the resolver offline, from an empty cache and apart from the [project](../../../core/glossary.md#term-project--project), and finds its result. Nothing checks the agent, whose definition grants it a shell: its text alone says it fetches no source.

**Imposed by:** The [friction](../../../core/glossary.md#term-friction--friction) checks read the repository alone and reach no network (COR-050 point 2). A check that gives the same result wherever it runs cannot ask a source whether it changed. A fetched copy of the text also changes with every timestamp on it (living-docs DEC-001).
