---
id: REQ-031
title: The CLI is installed with uv from the distribution's git URL
status: active
statement: The system's CLI is installed with `uv`, from the distribution's git URL.
measure: The install the system prints, and the one its upgrade runs, is `uv tool install` with that URL and a release tag. A pinned release runs through `uvx` from the same URL. No registry and no other installer is supported.
applies-to: The CLI's install and update on every machine, and the router's run of a pinned release.
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - tests/test_install.py
        - tests/test_router.py
        - tests/test_upgrade.py
      record:
        - PRJ-004
---

# REQ-031 · Constraint · The CLI is installed with uv from the distribution's git URL

**Verified by:** Tests find that `pkit init` prints the `uv tool install` command tagged with its own [version](../../../glossary.md#term-version--version), as the CLI reference recommends, and never the untagged one. A test finds that the router runs a [version pin](../../../glossary.md#term-version-pin--version-pin) through `uvx` from the git URL, at that [release](../../../glossary.md#term-release--release)'s tag. Tests of the upgrade's step that updates the CLI find the `uv tool install --force` it runs.

**Imposed by:** PRJ-004, which distributes the CLI from a direct git URL on github.com, with no registry. It makes `uv tool install` the sole sanctioned installer. The router runs a [version pin](../../../glossary.md#term-version-pin--version-pin) through `uvx` (ADR-039), and the CLI's update runs or prints a `uv` command (ADR-063). The canonical `uv tool install` command names a [release](../../../glossary.md#term-release--release) tag, which ties the CLI's [version](../../../glossary.md#term-version--version) to one content (ADR-033).
