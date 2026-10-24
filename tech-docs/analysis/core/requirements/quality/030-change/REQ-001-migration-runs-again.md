---
id: REQ-001
title: A migration run again changes nothing
status: active
statement: A migration run again over the state it left changes nothing.
measure: A second run straight after the first leaves every file of the project, and the repository's git index, as the first run left them.
applies-to: Every migration of the backbone and of each component, whenever a version transition runs it.
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
        - tests/test_pm_workflow_migrations_after_the_copy.py
        - tests/test_migration_96_rules_area.py
        - tests/test_software_analysis_migration_rule_set.py
        - tests/test_software_analysis_templates.py
      record:
        - COR-010
        - COR-059#6
      artefact:
        - ACT-adopter
    revalidated:
      at: 2026-10-24T10:39:19Z
      outcome: unchanged
      unchanged-because: ACT-adopter's need says "Upgrade the system" for "Upgrade it", and "a version the whole project pins" for "a version pinned for the whole project". The need is the same, so this artefact holds.
---

# REQ-001 · Quality · A migration run again changes nothing

**Verified by:** A test replays every [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration) over a newly installed [project](../../../glossary.md#term-project--project), which already holds what each one leaves. It finds no file and no index entry changed. Tests run most of the [components](../../../glossary.md#term-component--component)' migrations a second time, or over a project they already carried across. Three have no such test, one of evidence's and two of project-management's.

**Rationale:** A [version transition](../../../glossary.md#term-version-transition--version-transition) records its completion only once every [migration](../../../glossary.md#term-migration--migration) has run. So when one stops, the next runs again each [backbone](../../../glossary.md#term-backbone--backbone) migration the stopped one ran (COR-059 [point](../../../glossary.md#term-point--point) 6).

COR-010 makes each migration idempotent, "so adopters can re-run safely". So an adopter whose version transition stopped runs it again, and each migration that already ran changes nothing the second time. A run after the [project](../../../glossary.md#term-project--project) changed that state may do more: a backbone migration may restore a default the project removed (COR-010).
