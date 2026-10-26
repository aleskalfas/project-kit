---
id: REQ-009
title: A command whose effect reaches past what the person named offers `--dry-run`
status: active
statement: A command that changes or removes content that already exists, beyond what the person named, offers a preview of those edits through `--dry-run`.
measure: Each such command accepts `--dry-run`. Run with it, the command names each edit it would make. Every file of the project then holds the bytes and the mode it held before, those under `.git` included.
applies-to: Every command of the backbone and of the components, judged by the widest effect it can have. Sync, merge delivery, install, uninstall and a version transition are such commands. A command that only creates new files, or only writes the one value or entry named, is outside it.
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_sync.py
        - tests/test_upgrade.py
        - tests/test_install.py
        - tests/test_merge.py
        - tests/test_capabilities.py
        - tests/test_capabilities_in_source.py
        - tests/test_settings_consolidate.py
        - tests/test_refs.py
        - tests/test_friction_resolve.py
        - tests/test_visibility.py
      record:
        - COR-004
      artefact:
        - ACT-adopter
---

# REQ-009 · Quality · A command whose effect reaches past what the person named offers `--dry-run`

**Verified by:** Tests run `pkit sync`, `pkit init` and `pkit upgrade` with `--dry-run`, and find nothing written. So do tests of `pkit refs rename`, `pkit settings consolidate`, `pkit friction resolve` and each mode of `pkit visibility`. Tests of a [capability](../../glossary.md#term-capability--capability)'s [install](../../glossary.md#term-install--install), registration, upgrade, refresh and uninstall find the same. A test of `pkit merge --dry-run` finds that it prints what it would run, and runs none of it.

No test or check finds a command of the class that lacks the flag. Sixteen of the [backbone](../../glossary.md#term-backbone--backbone)'s commands in the class lack it, among them `pkit config set`, `pkit release apply` and `pkit version bump`. Nobody has sorted the [components](../../glossary.md#term-component--component)' commands.

**Rationale:** [COR-004](../../../../../.pkit/decisions/core/COR-004-cli-surface.md) asks for a preview of each command whose effect a [project](../../glossary.md#term-project--project) would want to see before it happens. It names the class by effect: a command that changes or removes content that already exists, beyond what the person named. The CLI undoes no run, so such an edit costs far more to undo than to read first. An adopter who installs, upgrades or removes a [component](../../glossary.md#term-component--component) sees what it would do to the project's files before it lands.
