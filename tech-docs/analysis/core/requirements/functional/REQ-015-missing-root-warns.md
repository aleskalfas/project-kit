---
id: REQ-015
title: A declared documentation root that does not exist yet warns rather than fails
status: active
statement: A declared documentation root whose folder does not exist yet draws a warning from validation, never a failure.
measure: "With the documentation root declared and its folder missing, validation reports `documentation root '<root>' does not exist yet; the default applies to readers until it is created (COR-049 point 7).` as a warning. Where nothing else fails, `pkit validate` exits 0."
applies-to: Validation of the documentation roots the backbone configuration declares, wherever validation runs, a CI pipeline included.
obligation: v1:sha256:9bf9306740751a010926410133c283e17d8788d98242fe0466835f25be0ab918
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/config_validate.py
        - tests/test_config_validate.py
      record:
        - COR-049#7
      artefact:
        - ACT-adopter
---

# REQ-015 · Functional · A declared documentation root that does not exist yet warns rather than fails

**Verified by:** A test declares a documentation root whose folder is missing, and finds a warning and no error. Another pins the warning's words. A third finds that `pkit validate` exits 0 with the warning, and exits 1 once the [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration) holds an error.

**Rationale:** The adopter may declare the documentation roots before the [project](../../glossary.md#term-project--project) holds any document. [COR-049 point 7](../../../../../.pkit/decisions/core/COR-049-documentation-roots.md#7-visible-and-checked) decides that such a root "produces a warning, not a failure, since a fresh project may have no documentation folder".

The warning must say which root it means, that the folder is missing, and that the default applies to readers until the folder exists. So the adopter learns from the warning alone what a reader of the root gets meanwhile, and its citation says why this is no failure.
