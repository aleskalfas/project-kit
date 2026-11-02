---
id: REQ-031
title: The CLI is installed with uv from the distribution's git URL
status: active
statement: The system's CLI is installed with `uv`, from the distribution's git URL.
measure: The install the system prints is `uv tool install` with that URL and the tag `latest`, which points at the highest release. The one its upgrade runs names a release's own tag. A pinned release runs through `uvx` from the same URL. No registry and no other installer is supported.
applies-to: The CLI's install and update on every machine, and the router's run of a pinned release.
obligation: v1:sha256:a6a5f3f5e28af210178924885fa617894b1ca8e33ba49ec4fd59271ac60c7caa
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - tests/test_install.py
        - tests/test_latest_tag.py
        - tests/test_router.py
        - tests/test_upgrade.py
      record:
        - PRJ-004
---

# REQ-031 · Constraint · The CLI is installed with uv from the distribution's git URL

**Verified by:** Tests find that `pkit init` prints the `uv tool install` command tagged `latest`, as the CLI reference recommends, and never the untagged one. Tests of `scripts/latest_tag.py` find that it points `latest` at the commit of the highest [release](../../../glossary.md#term-release--release) tag. A test finds that the router runs a [version pin](../../../glossary.md#term-version-pin--version-pin) through `uvx` from the git URL, at the pinned release's tag. Tests of the upgrade's step that updates the CLI find the `uv tool install --force` it runs.

**Imposed by:** [PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md), which distributes the CLI from a direct git URL on github.com, with no registry. It makes `uv tool install` the sole sanctioned installer. The router runs a [version pin](../../../glossary.md#term-version-pin--version-pin) through `uvx` ([ADR-039](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md)), and the CLI's update runs or prints a `uv` command ([ADR-063](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md)). The canonical command names the tag `latest`, kept on the highest [release](../../../glossary.md#term-release--release)'s commit, so the CLI's [version](../../../glossary.md#term-version--version) names one content ([ADR-033](../../../../../architecture/decisions/ADR-033-official-install-bundles-content.md)).
