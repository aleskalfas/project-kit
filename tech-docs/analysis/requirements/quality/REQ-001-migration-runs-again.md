---
id: REQ-001
title: A migration run again changes nothing
status: active
statement: A migration that runs again over a project it already carried across changes nothing.
measure: A second run leaves every file of the project, and the repository's index, as the first run left them.
applies-to: Every migration of the backbone, of each adapter and of each capability, whenever a version transition runs it.
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_backbone_migration_replay.py
        - tests/test_pm_migration_*.py
        - tests/test_pm_workflow_v*_migration.py
        - tests/test_migration_96_rules_area.py
        - tests/test_software_analysis_migration_rule_set.py
      record:
        - COR-010
        - COR-059#6
      artefact:
        - ACT-adopter
---

# REQ-001 · Quality · A migration run again changes nothing

**Verified by:** A test replays every backbone migration over a newly installed project, and finds no file and no index entry changed. Tests run most of the components' migrations a second time, or over a project they already carried across. Three have no such test, one of evidence's and two of project-management's.

**Rationale:** After a version transition stops, the next one runs again each migration the stopped transition ran (COR-059 point 6). COR-010 makes each migration safe to run again, "so adopters can re-run safely". So an adopter whose `pkit upgrade` stopped runs it again, and the transition finishes with nothing harmed.
