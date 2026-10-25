---
id: REQ-019
title: Each reading document of the friction group carries its version, and a reader refuses one it does not know
status: active
statement: Each JSON document a reading command of the friction group prints carries `schema_version`, and a reader of it refuses a version it does not know.
measure: "Every such document holds `schema_version` at its top level, raised only when a key a reader relies on changes its meaning or goes. A reader given a version it does not know reads nothing from the document, and names the version it found."
applies-to: "The JSON documents of `pkit friction check`, `check --all`, `debt`, `explain`, `artefacts` and `since`. A reader of them, a component or a project's own tooling, holds to it as the documents' contract, which the core does not check."
actors:
  - ACT-ci-pipeline
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_friction_check.py
        - tests/test_friction_repository.py
        - tests/test_friction_report.py
        - tests/test_friction_artefacts.py
        - tests/test_friction_since.py
        - tests/test_friction_report_body.py
      artefact:
        - ACT-ci-pipeline
---

# REQ-019 · Functional · Each reading document of the friction group carries its version, and a reader refuses one it does not know

**Verified by:** Tests of each reading command find `schema_version` in its document. A test gives project-kit's script that renders the [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check)'s [findings](../../../glossary.md#term-finding--finding) a document of schema version 2. It finds that the script refuses it, naming the schema version. Each [component](../../../glossary.md#term-component--component) tests its own readers.

**Rationale:** No record decides it. The requirement is its own home, and merging the [change](../../../glossary.md#term-change--change) that adds it approves it (software-analysis DEC-002 [point](../../../glossary.md#term-point--point) 8).

A [component](../../../glossary.md#term-component--component) reads these documents, never the human view, so a key whose meaning changed would be misread silently. A raised schema version tells such a reader to stop instead. A key added keeps the schema version, so a reader that knows the schema version still reads the document.

Four of these commands gained `schema_version` after they first shipped. So a document of theirs without it comes from an older [backbone](../../../glossary.md#term-backbone--backbone), and reads as schema version 1, as the CLI reference says.
