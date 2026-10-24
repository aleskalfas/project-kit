---
id: REQ-026
title: An interrupted version transition never reads as finished, and the next one completes it
status: active
statement: A version transition that stops before its end never reads as finished, and the next transition completes it.
measure: A transition of the backbone that stops at any step leaves `completed_version` missing, or unequal to `backbone_version`, and status shows the transition incomplete. A transition of one capability that stops leaves the capability's manifest at the version it held. The next transition runs each migration from the recorded completion or version. Where no completion is recorded, it runs every backbone migration once.
applies-to: "Every version transition: of the backbone, by `pkit upgrade` and by `pkit pin` to a newer release, and of one capability, by `pkit capabilities upgrade`. First install records the backbone's two states in the same order (COR-059 point 6)."
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/manifest.py
        - tests/test_upgrade.py
        - tests/test_install.py
        - tests/test_status.py
        - tests/test_capabilities.py
        - tests/test_backbone_migration_replay.py
      record:
        - COR-059#6
        - ADR-065#3
        - ADR-065#4
      artefact:
        - ACT-adopter
---

# REQ-026 · Quality · An interrupted version transition never reads as finished, and the next one completes it

**Verified by:** A test stops an upgrade on a failing migration, and finds the completion behind and no version pin written. It then finds that the next upgrade runs the migrations again and records the completion last. Tests find that an upgrade records the target before its copy, and records the completion before the version pin. A test finds that first install records the target first, and records the completion last.

Tests find that a missing completion runs every backbone migration once, and that a completion ahead of the target reads as incomplete. A test of status finds that it shows an incomplete transition beside the backbone's line. Tests of `pkit capabilities upgrade` find that a failing migration stops it, and that the capability's manifest moves before the copy.

**Rationale:** The adopter upgrades the system like a dependency, with its migrations run. A transition cut short in its migrations would otherwise read as done, so the next upgrade would find nothing to do. Those migrations would then never run (COR-059's context).

So COR-059 point 6 records the target before anything else, and records the completion last. A project is at a version only when both name it. The next transition finishes an incomplete one, and runs every backbone migration once where no completion is recorded.
