---
id: UC-048
title: Put the system's CLI on my machine at a release
status: active
actor: ACT-operator
other-actors: []
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
      record:
        - PRJ-003
        - PRJ-004
        - ADR-033
        - ADR-063
        - ADR-065#12
        - COR-059#5
      artefact:
        - ACT-operator
        - REQ-003
        - REQ-009
        - REQ-031
    revalidated:
      at: 2026-10-24T03:45:10Z
      outcome: unchanged
      unchanged-because: The change rewords only the help of `pkit release merge` in cli.py, which this artefact does not describe.
---

# UC-048 — Put the system's CLI on my machine at a release

**Goal:** Put the system's CLI on my machine at a release, and update it.

**Other actors:** None.

**Preconditions:** **From UC-008:** The [release](../../../glossary.md#term-release--release) carries its tag, `v<version>`, on the [distribution](../../../glossary.md#term-distribution--distribution)'s repository (PRJ-004).

**Assumptions:**

- `uv` is on the machine, and gives the CLI a Python of 3.11 or later apart from the projects' own (PRJ-003 and REQ-003).
- The operator can reach the [distribution](../../../glossary.md#term-distribution--distribution)'s repository on github.com, over SSH, or over HTTPS with a token (PRJ-004).

**Trigger:** The operator starts using the [system](../../../glossary.md#term-system--system) on a machine, or wants the [release](../../../glossary.md#term-release--release) that machine's CLI runs to move on.

**Main path:**

1. The operator runs `uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@v<version>`, naming a [release](../../../glossary.md#term-release--release)'s tag (PRJ-004 and REQ-031).
2. `uv` installs the [system](../../../glossary.md#term-system--system)'s CLI, `pkit`, at that release. The CLI carries the [methodology](../../../glossary.md#term-methodology--methodology)'s content of the same release, so its [version](../../../glossary.md#term-version--version) names one content (ADR-033 and ADR-065 [point](../../../glossary.md#term-point--point) 12).
3. The operator runs `pkit version`, and the system prints `pkit <version>`.
4. Later, the operator runs `pkit upgrade` outside any [project](../../../glossary.md#term-project--project), where no git repository and no `.pkit/` lie above the working directory (ADR-063 point 5).
5. The system asks the [distribution](../../../glossary.md#term-distribution--distribution)'s repository for its latest release, with `git ls-remote --tags` against the URL compiled into the CLI. It waits at most five seconds (ADR-063 point 1).
6. The system finds the CLI behind that release. Run by the CLI `uv` installed, at a terminal, it runs `uv tool install --force` with that URL and the latest release's tag (ADR-063 point 2).
7. The system hands over to the same command under the new CLI, which finds itself current and prints `pkit tool is current (v<version>).`.

**Variants:**

- **1a.** The operator authenticates to GitHub with a token, not SSH keys. The operator installs from the HTTPS form, `git+https://github.com/aleskalfas/project-kit.git@v<version>` (PRJ-004).
- **1b.** The operator installs a branch, a commit or main's latest commit, naming no [release](../../../glossary.md#term-release--release) tag. The CLI's [version](../../../glossary.md#term-version--version) then names the last release, while its files may be newer. So no version vouches for its content (PRJ-004 and ADR-065 [point](../../../glossary.md#term-point--point) 12).
- **1c.** The operator wants a release other than the latest. The operator runs step 1 again with `--force` and that release's tag.
- **4a.** The operator passes `--dry-run`. The [system](../../../glossary.md#term-system--system) says which `uv` command it would run, and installs nothing (REQ-009).
- **4b.** The operator runs `pkit upgrade` in a [project](../../../glossary.md#term-project--project) that pins no version. The system runs steps 5 to 7 first, then upgrades the project under the CLI they leave (UC-051). In a pinned project the system never runs them (ADR-063 point 5).
- **5a.** The lookup fails, offline, without credentials, without `git`, or past its limit. The system warns `could not check for a newer pkit tool`, and ends without failing the command (ADR-063 point 1).
- **6a.** The CLI is the latest release, or newer. The system prints `pkit tool is current (v<version>).`, and the use case ends.
- **6b.** Standard input or standard output is no terminal, or the operator passed `--no-self-update`. The system prints `A newer pkit tool is available: v<latest> (you are running v<version>).` and the command that updates the CLI, and installs nothing (ADR-063 point 3).
- **6c.** The running CLI is not the one `uv` installed, such as one run through `uv run`. The system says so, prints the command that updates the CLI, and installs nothing (ADR-063 point 3).
- **6d.** The update exits non-zero, or cannot start. The system prints the command that updates the CLI, and the command ends without failing.
- **7a.** `pkit` cannot be started, or the `PATH` finds another `pkit` still behind. The system stops with an error, says it stopped before it synced or pinned anything, and names the command to run again (ADR-063 point 3).

**Postconditions:** The machine's CLI runs a [release](../../../glossary.md#term-release--release), with that release's content. Where the update ran, it runs the latest release.

**Minimal guarantees:**

- A failed lookup or a failed update of the CLI never fails `pkit upgrade` (ADR-063 [point](../../../glossary.md#term-point--point) 1).
- The [system](../../../glossary.md#term-system--system) installs the CLI only under the CLI `uv` installed, at a terminal, and never where automation runs it (ADR-063 point 3).
- Updating the CLI acts on no [project](../../../glossary.md#term-project--project) (COR-059 point 5). Outside any project, `pkit upgrade` touches no project's files.
- The system installs the CLI from the [distribution](../../../glossary.md#term-distribution--distribution)'s URL compiled into it, and from no other source (ADR-063 point 7 and REQ-031).
