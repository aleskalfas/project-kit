---
id: UC-048
title: Put the system's CLI on my machine at a release
status: active
actor: ACT-operator
other-actors:
  - ACT-ci-pipeline
  - ACT-ai-agent
requirements:
  - REQ-003
  - REQ-009
  - REQ-031
after:
  - [UC-008]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/upgrade.py
        - src/project_kit/router.py
        - src/project_kit/cli.py
        - .pkit/cli/install-pkit.sh
      record:
        - PRJ-003
        - PRJ-004
        - PRJ-015
        - ADR-033
        - ADR-063
        - ADR-065#12
        - ADR-090
        - COR-059#5
      artefact:
        - ACT-operator
        - ACT-ci-pipeline
        - ACT-ai-agent
        - REQ-003
        - REQ-009
        - REQ-031
---

# UC-048 — Put the system's CLI on my machine at a release

**Goal:** Put the system's CLI on my machine at a release, and update it.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): runs the script `.pkit/cli/install-pkit.sh` in variant 1d, with no person to reply. A setup command that readies a container or a hosted agent's machine runs the script the same way. This use case counts it as the pipeline's case ([ADR-090 point 3](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#3-an-install-script-in-the-cli-area-installs-a-fresh-clones-pkit)).
- **AI agent** (`ACT-ai-agent`): runs the same script in variant 1d, as it runs any other command ([ADR-090 point 3](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#3-an-install-script-in-the-cli-area-installs-a-fresh-clones-pkit)).

**Preconditions:** **From [UC-008](../040-release/UC-008-release-backbone.md):** The [release](../../../glossary.md#term-release--release) carries its tag, `v<version>`, on the [distribution](../../../glossary.md#term-distribution--distribution)'s repository. The tag `latest` points at the highest release's commit ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)).

**Assumptions:**

- `uv` is on the machine, and gives the CLI a Python of 3.11 or later apart from the projects' own ([PRJ-003](../../../../../../.pkit/decisions/project/PRJ-003-implementation-language.md) and [REQ-003](../../../requirements/constraints/REQ-003-python-floor.md)).
- The operator can reach the [distribution](../../../glossary.md#term-distribution--distribution)'s repository on github.com over HTTPS, with no credential, while the repository is public ([PRJ-015 point 3](../../../../../../.pkit/decisions/project/PRJ-015-https-install-form.md#3-the-documented-install-needs-no-credential)).

**Trigger:** The operator starts using the [system](../../../glossary.md#term-system--system) on a machine, or wants the [release](../../../glossary.md#term-release--release) that machine's CLI runs to move on.

**Main path:**

1. The operator runs `uv tool install git+https://github.com/aleskalfas/project-kit.git@latest`, naming the tag `latest`, which points at the highest [release](../../../glossary.md#term-release--release) ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md), [PRJ-015 point 1](../../../../../../.pkit/decisions/project/PRJ-015-https-install-form.md#1-the-install-the-project-gives-names-the-https-url) and [REQ-031](../../../requirements/constraints/050-adopt/REQ-031-cli-from-distribution-url.md)).
2. `uv` installs the [system](../../../glossary.md#term-system--system)'s CLI, `pkit`, at that release. The CLI carries the [methodology](../../../glossary.md#term-methodology--methodology)'s content of the same release, so its [version](../../../glossary.md#term-version--version) names one content ([ADR-033](../../../../../architecture/decisions/ADR-033-official-install-bundles-content.md) and [ADR-065 point 12](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#12-a-version-identifies-content-only-for-a-tagged-install)).
3. The operator runs `pkit version`, and the system prints `pkit <version>`.
4. Later, the operator runs `pkit upgrade` outside any [project](../../../glossary.md#term-project--project), where no git repository and no `.pkit/` lie above the working directory ([ADR-063 point 5](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#5-where-the-step-runs)).
5. The system asks the [distribution](../../../glossary.md#term-distribution--distribution)'s repository for its latest release, with `git ls-remote --tags` against the URL compiled into the CLI. It waits at most five seconds ([ADR-063 point 1](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#1-detect-best-effort)).
6. The system finds the CLI behind that release. Run by the CLI `uv` installed, at a terminal, it runs `uv tool install --force` with that URL and the latest release's tag ([ADR-063 point 2](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#2-install-when-the-tool-is-behind)).
7. The system replaces itself with the same command under the new CLI, which finds itself current and prints `pkit tool is current (v<version>).`.

**Variants:**

- **1a.** The operator installs from a fork kept in a private repository, whose fetch asks for a credential. A token in git's credential store serves that fetch, or an SSH key the machine holds ([PRJ-015 point 3](../../../../../../.pkit/decisions/project/PRJ-015-https-install-form.md#3-the-documented-install-needs-no-credential)).
- **1b.** The operator installs a branch, a commit or main's latest commit, naming neither `latest` nor a [release](../../../glossary.md#term-release--release)'s tag. The CLI's [version](../../../glossary.md#term-version--version) then names the last release, while its files may be newer. So no version vouches for its content ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md) and [ADR-065 point 12](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#12-a-version-identifies-content-only-for-a-tagged-install)).
- **1c.** The operator wants a release other than the latest. The operator runs step 1 again with `--force` and that release's tag.
- **1d.** On a machine with nobody at the keyboard, the CI pipeline or the AI agent runs `sh .pkit/cli/install-pkit.sh` in a [project](../../../glossary.md#term-project--project)'s fresh clone ([ADR-090 point 3](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#3-an-install-script-in-the-cli-area-installs-a-fresh-clones-pkit)). The script installs the CLI at the project's [version pin](../../../glossary.md#term-version-pin--version-pin), or else at its [recorded version](../../../glossary.md#term-recorded-version--recorded-version), and never at `latest` ([ADR-090 point 4](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#4-it-installs-the-projects-version-never-latest)). It installs nothing where it finds a CLI installed, and succeeds only where the project's commands then run that version ([ADR-090 point 5](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#5-it-never-replaces-a-pkit-it-finds-installed-and-checks-the-pkit-the-commands-run)).
- **4a.** The operator passes `--dry-run`. The [system](../../../glossary.md#term-system--system) says which `uv` command it would run, and installs nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).
- **4b.** The operator runs `pkit upgrade` in a project that pins no version. The system runs steps 5 to 7 first, then upgrades the project under the CLI they leave ([UC-051](UC-051-upgrade-system.md)). In a pinned project the system never runs them ([ADR-063 point 5](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#5-where-the-step-runs)).
- **5a.** The lookup fails, offline, without credentials, without `git`, or past its limit. The system warns `could not check for a newer pkit tool`, and ends without failing the command ([ADR-063 point 1](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#1-detect-best-effort)).
- **6a.** The CLI is the latest release, or newer. The system prints `pkit tool is current (v<version>).`, and the use case ends.
- **6b.** Standard input or standard output is no terminal, or the operator passed `--no-self-update`. The system prints `A newer pkit tool is available: v<latest> (you are running v<version>).` and the command that updates the CLI, and installs nothing ([ADR-063 point 3](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#3-print-the-command-where-it-cannot-or-may-not-install-and-stop-where-the-hand-over-fails)).
- **6c.** The running CLI is not the one `uv` installed, such as one run through `uv run`. The system says so, prints the command that updates the CLI, and installs nothing ([ADR-063 point 3](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#3-print-the-command-where-it-cannot-or-may-not-install-and-stop-where-the-hand-over-fails)).
- **6d.** The update exits non-zero, or cannot start. The system prints the command that updates the CLI, and the command ends without failing.
- **7a.** `pkit` cannot be started, or the `PATH` finds another `pkit` still behind. The system stops with an error, says it stopped before it synced or pinned anything, and names the command to run again ([ADR-063 point 3](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#3-print-the-command-where-it-cannot-or-may-not-install-and-stop-where-the-hand-over-fails)).

**Postconditions:** The machine's CLI runs a [release](../../../glossary.md#term-release--release), with that release's content. Where the update ran, it runs the latest release.

**Minimal guarantees:**

- A failed lookup or a failed update of the CLI never fails `pkit upgrade` ([ADR-063 point 1](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#1-detect-best-effort)).
- The [system](../../../glossary.md#term-system--system) replaces an installed CLI only under the CLI `uv` installed, at a terminal, and never where automation runs it ([ADR-063 point 3](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#3-print-the-command-where-it-cannot-or-may-not-install-and-stop-where-the-hand-over-fails)).
- The script `.pkit/cli/install-pkit.sh` installs the CLI only where it finds none installed, and replaces none ([ADR-090 point 5](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#5-it-never-replaces-a-pkit-it-finds-installed-and-checks-the-pkit-the-commands-run)).
- Where the script refuses a [version pin](../../../glossary.md#term-version-pin--version-pin) or a [recorded version](../../../glossary.md#term-recorded-version--recorded-version), it installs nothing and says why ([ADR-090 point 4](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#4-it-installs-the-projects-version-never-latest)).
- Updating the CLI acts on no [project](../../../glossary.md#term-project--project) ([COR-059 point 5](../../../../../../.pkit/decisions/core/COR-059-version-transition.md#5-the-one-operation-rule-governs-operations-on-a-project)). Outside any project, `pkit upgrade` touches no project's files.
- The system installs the CLI from the [distribution](../../../glossary.md#term-distribution--distribution)'s URL compiled into it, and from no other source ([ADR-063 point 7](../../../../../architecture/decisions/ADR-063-upgrade-updates-the-tool.md#7-the-tool-from-its-compiled-url) and [REQ-031](../../../requirements/constraints/050-adopt/REQ-031-cli-from-distribution-url.md)). The script installs from its own copy of that URL, which a test holds equal to it ([ADR-090 point 7](../../../../../architecture/decisions/ADR-090-self-fetch-over-https.md#7-its-install-is-the-sanctioned-one)).
