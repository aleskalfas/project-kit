---
id: REQ-017
title: A backbone migration is safe over any state
status: active
statement: A backbone migration acts only on a positive sign that its change is needed, and never deletes by a path's name or position alone.
measure: Run over any state a project may hold, its migration history unknown included, the migration changes only what such a sign shows is needed. The migration leaves a project's own file as it was, where only a path the migration names marks the file for change.
applies-to: Every backbone migration, whenever a version transition runs it, over a project whose migration history may be unknown.
actors:
  - ACT-adopter
refines:
  - REQ-001
pkit:
  friction:
    anchors:
      path:
        - tests/test_backbone_migration_replay.py
        - .pkit/rules/core.md
      record:
        - COR-010
        - COR-059#6
      artefact:
        - ACT-adopter
        - REQ-001
---

# REQ-017 · Quality · A backbone migration is safe over any state

**Verified by:** A test replays every [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration) over a newly installed [project](../../../glossary.md#term-project--project), and over projects that each hold one state a replay risks. It finds that each leaves a project's own files alone, such as a hand-written [agent definition](../../../glossary.md#term-agent-definition--agent-definition) at a path a migration once removed. It also finds which defaults a replay may restore, the cost the [release](../../../glossary.md#term-release--release)'s notes state.

**Rationale:** A [version transition](../../../glossary.md#term-version-transition--version-transition) may run every [backbone](../../../glossary.md#term-backbone--backbone) [migration](../../../glossary.md#term-migration--migration) again over a [project](../../../glossary.md#term-project--project) whose migration history is unknown ([COR-059 point 6](../../../../../../.pkit/decisions/core/COR-059-version-transition.md#6-a-transition-of-the-backbone-records-its-target-first-and-its-completion-last)). So a migration that acted on a path alone could delete a file the project wrote there since. [COR-010](../../../../../../.pkit/decisions/core/COR-010-resource-lifecycle.md) makes each backbone migration safe over any state for that reason, and core rule 5 binds every author of one to it.

A missing default the migration adds counts as a positive sign. So running it again may restore a default the project removed after it first ran, and the [release](../../../glossary.md#term-release--release)'s notes say so (COR-010).
