---
id: REQ-016
title: "The permission model's code needs only the system `python3` and its standard library"
status: active
statement: "The permission model's code under `.pkit/permissions/` needs only the system `python3` and its standard library."
measure: "Under the system `python3`, with no package outside its standard library importable, the code loads the permission model. It decides each call as it does where `ruamel.yaml` is importable."
applies-to: "The permission model's code under `.pkit/permissions/`, on every machine that runs it. The backbone's `pkit permissions` commands import it, and so does an adapter's permission hook."
actors:
  - ACT-operator
refines: []
pkit:
  friction:
    anchors:
      path:
        - tests/test_permission_decide.py
        - .pkit/permissions/*.py
      record:
        - ADR-014#1
      artefact:
        - ACT-operator
    revalidated:
      at: 2026-10-24T04:45:22Z
      outcome: unchanged
      unchanged-because: The new query and the hook ask import nothing beyond the standard library, and the hook tests run the ask under the system python3 too.
---

# REQ-016 · Constraint · The permission model's code needs only the system `python3` and its standard library

**Verified by:** Tests load the permission model and decide calls with `ruamel.yaml` made unimportable, and find the same results as with it. No test checks that the code imports nothing else outside the standard library.

**Imposed by:** ADR-014 point 1. An adapter's permission hook imports this code, and decides each call with the same loader and the same decision as the `pkit permissions` commands. So the code needs no more than the interpreter the hook runs under.

ADR-014 gives the example of `claude-code` on macOS. There `uv` cannot run inside the operating system's sandbox, while the system `python3` exists in every such sandbox. So the hook runs under the system `python3`, and the code reads YAML through a parser of its own where `ruamel.yaml` is missing.

#1765 may refine ADR-014 points 1 to 3, since the code turns the sandbox off on macOS entirely.
