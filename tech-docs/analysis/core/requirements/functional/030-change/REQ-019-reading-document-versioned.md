---
id: REQ-019
title: Each reading document of `pkit friction` carries its version, and a reader refuses one it does not know
status: active
statement: Each JSON document a reading command of `pkit friction` prints carries `schema_version`, and a reader of it refuses a version it does not know.
measure: "Every such document holds `schema_version` at its top level. The schema version is raised when, and only when, one of the document's own keys, or a value of one of its sets, goes. No key or value comes to mean anything else. A reader given a version it does not know reads nothing from the document, and names the version it found."
applies-to: "The JSON documents of `pkit friction check`, `check --all`, `debt`, `explain`, `artefacts` and `since`. A reader of them, a component or a project's own tooling, holds to it as the documents' contract, which the core does not check."
obligation: v1:sha256:2de4b8087cd48a5a797c1cdc07686e60323d195708a816620de6371d06ca43ae
actors:
  - ACT-ci-pipeline
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/friction_check.py
        - src/project_kit/friction_repository.py
        - src/project_kit/friction_report.py
        - src/project_kit/friction_discovery.py
        - src/project_kit/friction_since.py
        - scripts/friction_report_body.py
        - tests/test_friction_check.py
        - tests/test_friction_repository.py
        - tests/test_friction_report.py
        - tests/test_friction_artefacts.py
        - tests/test_friction_since.py
        - tests/test_friction_report_body.py
      record:
        - software-analysis:DEC-002#8
        - ADR-097
      artefact:
        - ACT-ci-pipeline
---

# REQ-019 · Functional · Each reading document of `pkit friction` carries its version, and a reader refuses one it does not know

**Verified by:** Tests of each reading command find `schema_version` in its document. A test gives project-kit's script that renders the [whole-repository check](../../../glossary.md#term-whole-repository-check--whole-repository-check)'s [findings](../../../glossary.md#term-finding--finding) a document of schema version 2. It finds that the script refuses it, naming the schema version. Each [component](../../../glossary.md#term-component--component) tests its own readers.

**Rationale:** [ADR-097](../../../../../architecture/decisions/ADR-097-machine-output-contract.md) decides how a command's machine-readable output stays stable, and this requirement applies that decision to these documents. Where the two disagree, the record wins ([software-analysis DEC-002 point 8](../../../../../../.pkit/capabilities/software-analysis/decisions/DEC-002-analysis-requirements.md#8-what-approves-a-requirement-and-the-record-it-rests-on)).

A [component](../../../glossary.md#term-component--component) reads these documents, never the human view. A key added keeps the schema version, so a reader that knows the schema version still reads the document. A key or a value never comes to mean anything else, since a reader would misread it silently ([ADR-097 point 5](../../../../../architecture/decisions/ADR-097-machine-output-contract.md#5-a-key-or-a-value-means-one-thing-for-good)).

A key or a value that goes raises the schema version, in the same [change](../../../glossary.md#term-change--change) ([ADR-097 point 4](../../../../../architecture/decisions/ADR-097-machine-output-contract.md#4-what-is-a-breaking-change-and-what-is-not)). A reader that reads as ADR-097 asks finds such a key missing, and says that it could not tell. A reader that would read a key gone as a default, such as zero, is stopped by the raised schema version instead.

Four of these commands gained `schema_version` after they first shipped. So a document of theirs without it comes from an older [backbone](../../../glossary.md#term-backbone--backbone), and reads as schema version 1, as the CLI reference says.
