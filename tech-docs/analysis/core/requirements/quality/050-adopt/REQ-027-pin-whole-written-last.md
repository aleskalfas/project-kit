---
id: REQ-027
title: The version pin holds the old one or the new one, never part, and an upgrade writes it last
status: active
statement: The version pin holds the old one or the new one, never part of either, and an upgrade writes it last.
measure: A write of `.pkit/version-pin` cut short at any point leaves the old version pin byte for byte, and no temporary file. An upgrade writes the version pin after the completion, so an upgrade that fails before the completion writes no version pin.
applies-to: "Every write of `.pkit/version-pin`: by `pkit pin`, `pkit unpin`, and `pkit upgrade` when it pins a project by default or raises its version pin."
actors:
  - ACT-operator
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - tests/test_router.py
        - tests/test_upgrade.py
        - tests/test_pin_cli.py
      record:
        - ADR-049#1
        - ADR-064#1
      artefact:
        - ACT-operator
---

# REQ-027 · Quality · The version pin holds the old one or the new one, never part, and an upgrade writes it last

**Verified by:** Tests of the [version pin](../../../glossary.md#term-version-pin--version-pin)'s one writer cut a write short, at the flush or at the rename. They find the old version pin, and no temporary file. Tests find that `pkit pin` and `pkit unpin` write through that one writer. Tests of `pkit upgrade` find that a failing [sync](../../../glossary.md#term-sync--sync) writes no version pin, and that a raise writes the version pin after the content.

**Rationale:** The router runs whatever [release](../../../glossary.md#term-release--release) the [version pin](../../../glossary.md#term-version-pin--version-pin) names, for every command in the [project](../../../glossary.md#term-project--project) (ADR-049). A torn version pin would send each command to no release, and a version pin written early would name content that never landed. So ADR-049 [point](../../../glossary.md#term-point--point) 1 writes the version pin last, after the content and the [migrations](../../../glossary.md#term-migration--migration). ADR-064 point 1 makes the write atomic, so the router never reads a torn version pin.
