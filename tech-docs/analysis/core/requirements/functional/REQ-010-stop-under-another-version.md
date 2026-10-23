---
id: REQ-010
title: A command that propagates content under another version than the project records stops
status: active
statement: A command that propagates content stops before it writes, under a CLI at another version than the project records, or over an incomplete version transition.
measure: In each state that stops it, the command exits non-zero, with `--dry-run` too, and every file of the project holds what it held before. No flag lets it run, and its message names the remedy for the state it finds.
applies-to: "Every command that propagates content into a project at the backbone version it records: sync, a capability's install and a capability's upgrade. A version transition of the backbone propagates its target's content, so it stops only under a CLI older than the version the project records. A command that copies nothing, such as registering an incubated capability, is outside it, and so is the methodology's source repository (ADR-059)."
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_capabilities_version_guard.py
        - tests/test_sync.py
        - tests/test_upgrade.py
      record:
        - COR-059#9
        - ADR-065#7
        - ADR-059
      artefact:
        - ACT-adopter
---

# REQ-010 · Functional · A command that propagates content under another version than the project records stops

**Verified by:** Tests run sync under a CLI newer and older than the recorded version, and under a pin ahead of the running CLI. Others run it over an incomplete transition. Each finds that sync stops with nothing written, under `--dry-run` too, and that no flag overrides it.

Tests run a capability's install and upgrade in each state that stops sync. They find that each stops the same way, and names sync's remedies. Tests of the backbone's version transition find that it refuses content newer than the running CLI, and writes nothing.

**Rationale:** The adopter keeps a project at one recorded version, whose content and migrations belong together. Under another CLI, the command would copy another release's content without that release's migrations, in the words of its refusal. So COR-059 point 9 stops it before it writes, in a preview too, with no override.

Its message names the remedy for the state it finds. That may be a version transition to move the project on, or the project's own version of the CLI to stay (COR-059 point 9). ADR-065 point 7 has each such command run one guard before it writes anything.
