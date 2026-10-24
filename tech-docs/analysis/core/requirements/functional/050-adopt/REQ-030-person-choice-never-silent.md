---
id: REQ-030
title: A choice in a version transition that needs a person is never taken silently
status: active
statement: "A choice in a version transition that needs a person is never taken silently: with nobody to answer, nothing the choice decides is written."
measure: A transition of the backbone asks about a new name collision only at a terminal, and elsewhere refuses before its first write. `pkit capabilities upgrade` asks only under `--interactive`, and otherwise refuses before its first write. A dependency gate's warning refuses unless the call passes `--force`. With nobody to answer, a data point's question records nothing, and the command prints the line that runs the question later.
applies-to: "Each choice in a version transition that COR-059 point 4 leaves to a person. Those are a new name collision, a dependency gate's override and a data point's question. Merge delivery's tier that prompts is left out, since none is built (ADR-065 point 4). The requirement holds for `pkit upgrade`, `pkit pin` to a newer release and `pkit capabilities upgrade`."
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_upgrade.py
        - tests/test_capabilities.py
        - tests/test_point_questions.py
      record:
        - COR-059#4
        - ADR-065#6
      artefact:
        - ACT-adopter
    revalidated:
      at: 2026-10-24T19:00:34Z
      outcome: unchanged
      unchanged-because: "As #2003 asks, tests now find that a collision answer piped in off a terminal is refused before any write. The measure holds as written."
---

# REQ-030 · Functional · A choice in a version transition that needs a person is never taken silently

**Verified by:** A test runs `pkit upgrade` with no terminal over a new name collision, with `--force` passed, and finds every file as it was. Tests of the dependency gates find that a warning refuses without `--force`. A test finds that `pkit capabilities upgrade` refuses a new name collision without `--interactive`. Tests of the questions find that with nobody to reply none runs, and each one's line is printed.

**Rationale:** The adopter's own files sit beside the [methodology](../../../glossary.md#term-methodology--methodology)'s, and a transition must never choose for the adopter which of two colliding [artefacts](../../../glossary.md#term-artefact--artefact) stays. COR-059 [point](../../../glossary.md#term-point--point) 4 lets one [consent](../../../glossary.md#term-consent--consent), choosing the target, cover a transition's parts. Some choices keep the consent their own records set, and each is given by a person's reply or an explicit override. None is ever taken silently.
