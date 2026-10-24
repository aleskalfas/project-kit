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
    revalidated:
      at: 2026-10-24T10:39:31Z
      outcome: unchanged
      unchanged-because: ACT-adopter's need says "Upgrade the system" for "Upgrade it", and "a version the whole project pins" for "a version pinned for the whole project". The need is the same, so this artefact holds.
---

# REQ-010 · Functional · A command that propagates content under another version than the project records stops

**Verified by:** Tests run [sync](../../glossary.md#term-sync--sync) under a CLI newer and older than the [recorded version](../../glossary.md#term-recorded-version--recorded-version), and under a pin ahead of the running CLI. Others run it over an incomplete transition. Each finds that sync stops with nothing written, under `--dry-run` too, and that no flag overrides it.

Tests run a [capability](../../glossary.md#term-capability--capability)'s [install](../../glossary.md#term-install--install) and upgrade in each state that stops sync. They find that each stops the same way, and names sync's remedies. Tests of the [backbone](../../glossary.md#term-backbone--backbone)'s [version transition](../../glossary.md#term-version-transition--version-transition) find that it refuses content newer than the running CLI, and writes nothing.

**Rationale:** The adopter keeps a [project](../../glossary.md#term-project--project) at one [recorded version](../../glossary.md#term-recorded-version--recorded-version), whose content and [migrations](../../glossary.md#term-migration--migration) belong together. Under another CLI, the command would copy another [release](../../glossary.md#term-release--release)'s content without that release's migrations, in the words of its refusal. So COR-059 [point](../../glossary.md#term-point--point) 9 stops it before it writes, in a preview too, with no override.

Its message names the remedy for the state it finds. That may be a [version transition](../../glossary.md#term-version-transition--version-transition) to move the project on, or the project's own [version](../../glossary.md#term-version--version) of the CLI to stay (COR-059 point 9). ADR-065 point 7 has each such command run one guard before it writes anything.
