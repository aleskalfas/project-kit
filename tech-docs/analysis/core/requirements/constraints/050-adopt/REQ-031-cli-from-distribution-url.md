---
id: REQ-031
title: The CLI is installed with uv from the distribution's git URL
status: active
statement: The system's CLI is installed with `uv`, from the distribution's git URL.
measure: "`pkit init` prints, and the CLI reference gives, the recommended install: `uv tool install` with that URL and the tag `latest`, which points at the highest release. Every other install the system runs or prints names a release tag: its upgrade's, the one a stop names, and the install script's. A pinned release runs through `uvx` from the same URL, and none of these fetches waits at a terminal for a credential. That URL is the repository's public HTTPS URL, and no registry and no other installer is supported: the install script installs only through `uv tool install`."
applies-to: The CLI's install and update on every machine, a fresh clone's install by the install script, and the router's run of a pinned release.
obligation: v1:sha256:614c480d667bb571656e98270f4dbce9f01ec809b6fcf6e00843c9999efdd479
actors: []
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - src/project_kit/install.py
        - src/project_kit/upgrade.py
        - .pkit/cli/install-pkit.sh
        - scripts/latest_tag.py
        - tests/test_install.py
        - tests/test_install_script.py
        - tests/test_latest_tag.py
        - tests/test_router.py
        - tests/test_upgrade.py
      record:
        - PRJ-004
        - PRJ-015
        - ADR-033
        - ADR-039
        - ADR-063
        - ADR-090
---

# REQ-031 · Constraint · The CLI is installed with uv from the distribution's git URL

**Verified by:** Tests find that `pkit init` prints the `uv tool install` command tagged `latest`, as the CLI reference recommends, and never the untagged one. Tests of `scripts/latest_tag.py` find that it points `latest` at the commit of the highest [release tag](../../../glossary.md#term-release-tag--release-tag). A test finds that the [router](../../../glossary.md#term-router--router) runs a [version pin](../../../glossary.md#term-version-pin--version-pin) through `uvx` from the git URL, at the release tag of the pinned [release](../../../glossary.md#term-release--release). Tests of the upgrade's step that updates the CLI find the `uv tool install --force` it runs.

A test finds that the git URL is the repository's public HTTPS URL. Tests find the release lookup, the upgrade's update of the CLI and the probes of a pinned release run with git's terminal prompt off. Tests of the script `.pkit/cli/install-pkit.sh` find that it installs the [version](../../../glossary.md#term-version--version) the [project](../../../glossary.md#term-project--project) pins, or else the one it records. It installs from the git URL at that release tag, and never `latest`, and a test holds the script's URL equal to the router's.

**Imposed by:** [PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md), which distributes the CLI from a direct git URL on github.com, with no registry. It makes `uv tool install` the sole sanctioned installer. The [router](../../../glossary.md#term-router--router) runs a [version pin](../../../glossary.md#term-version-pin--version-pin) through `uvx` ([ADR-039](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md)), and the CLI's update runs or prints a `uv` command ([ADR-063](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md)). The canonical command names the tag `latest`, kept on the highest [release](../../../glossary.md#term-release--release)'s commit, so the CLI's [version](../../../glossary.md#term-version--version) names one content ([ADR-033](../../../../../architecture/decisions/ADR-033-official-install-bundles-content.md)).

[PRJ-015](../../../../../../.pkit/decisions/project/PRJ-015-https-install-form.md) makes that URL the repository's public HTTPS URL, which needs no credential. [ADR-090](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md) has every fetch the CLI makes of its own releases use it, and adds the script `.pkit/cli/install-pkit.sh`, which installs only through `uv tool install`.
