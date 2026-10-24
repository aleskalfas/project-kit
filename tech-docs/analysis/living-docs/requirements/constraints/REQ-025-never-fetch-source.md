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
      at: 2026-10-24T03:53:17Z
      outcome: unchanged
      unchanged-because: The agent changed only how reader-review falls back to a space's audience, read from a file of the repository. It still never fetches a source.
---

# REQ-025 · Constraint · Nothing in living-docs fetches the text a captured source names

**Verified by:** A test runs the resolver offline, from an empty cache and apart from the project, and finds its answer. Nothing checks the agent, whose definition grants it a shell: its text alone says it fetches no source.

**Imposed by:** The friction checks read the repository alone and reach no network (COR-050 point 2). A check that gives the same answer wherever it runs cannot ask a source whether it changed. A fetched copy of the text also changes with every timestamp on it (living-docs DEC-001).
