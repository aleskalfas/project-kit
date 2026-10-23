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
    revalidated:
      at: 2026-10-23T14:50:24Z
      outcome: unchanged
      unchanged-because: Core rules 14, 16 and 19 stop calling the permission model's code a capability, and change nothing else they say. What this requirement rests on in the rules holds.
---

# REQ-017 · Quality · A backbone migration is safe over any state

**Verified by:** A test replays every backbone migration over a newly installed project, and over projects that each hold one state a replay risks. It finds that each leaves a project's own files alone, such as a hand-written agent definition at a path a migration once removed. It also finds which defaults a replay may restore, the cost the release's notes state.

**Rationale:** A version transition may run every backbone migration again over a project whose migration history is unknown (COR-059 point 6). So a migration that acted on a path alone could delete a file the project wrote there since. COR-010 makes each backbone migration safe over any state for that reason, and core rule 5 binds every author of one to it.

A missing default the migration adds counts as a positive sign. So running it again may restore a default the project removed after it first ran, and the release's notes say so (COR-010).
