---
id: REQ-028
title: The router never fails a command over a version pin it cannot resolve
status: active
statement: "The router never fails a command over a version pin it cannot resolve: it runs the command under the installed CLI, and warns."
measure: Where `uvx` cannot fetch the pinned release, the router warns once per command on standard error. The warning names the version pin and the CLI the router runs instead, and says when that CLI is older than the version pin. The router never ends a command over its version pin, and the command keeps its own checks.
applies-to: Every `pkit` command run in a project whose version pin names another release than the installed CLI's.
actors:
  - ACT-operator
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - tests/test_router.py
      record:
        - ADR-039#D2
      artefact:
        - ACT-operator
---

# REQ-028 · Quality · The router never fails a command over a version pin it cannot resolve

**Verified by:** Tests of the router find that an unresolvable version pin, or a missing `uvx`, leaves the command to the installed CLI, with a warning. They find the warning said once per command. They also find that it says when the installed CLI is older than the version pin, and never calls a newer one older.

**Rationale:** The operator runs each project at its version pin, and needs the command to run when the pinned release cannot be fetched, such as offline. ADR-039 D2 makes this mandatory: "a degraded-but-running command beats a broken one". The warning tells the operator plainly that the system fell back, since the output may not match the pinned methodology.

A command run this way keeps its own checks. So `pkit upgrade` refuses under the fallback, and sync stops where its guard finds another version than the project records (ADR-065 point 9).
