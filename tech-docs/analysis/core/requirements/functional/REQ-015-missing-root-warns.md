---
id: REQ-015
title: A declared documentation root that does not exist yet warns rather than fails
status: active
statement: A declared documentation root whose folder does not exist yet draws a warning from validation, never a failure.
measure: "With the root declared and its folder missing, validation reports `documentation root '<root>' does not exist yet; the default applies to readers until it is created (COR-049 point 7).` as a warning. Where nothing else fails, `pkit validate` exits 0."
applies-to: Validation of the documentation roots the backbone configuration declares, wherever validation runs, a CI pipeline included.
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_config_validate.py
      record:
        - COR-049#7
      artefact:
        - ACT-adopter
---

# REQ-015 · Functional · A declared documentation root that does not exist yet warns rather than fails

**Verified by:** A test declares a root whose folder is missing, and finds a warning and no error. Another pins the warning's words. A third finds that `pkit validate` exits 0 with the warning, and exits 1 once the configuration holds an error.

**Rationale:** The adopter may declare the roots before the [project](../../glossary.md#term-project--project) holds any document. COR-049 [point](../../glossary.md#term-point--point) 7 decides that such a root "produces a warning, not a failure, since a fresh project may have no documentation folder".
