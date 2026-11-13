---
id: UC-052
title: Run each project at the version it pins
status: active
actor: ACT-operator
other-actors: []
requirements:
  - REQ-002
  - REQ-009
  - REQ-012
  - REQ-026
  - REQ-027
  - REQ-028
  - REQ-029
  - REQ-030
  - REQ-031
after:
  - [UC-049]
  - [UC-008]
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
  - at: "1d"
    issue: "#1884"
    record: COR-004
  - at: 10
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/router.py
        - src/project_kit/cli.py
        - src/project_kit/upgrade.py
        - src/project_kit/sync.py
        - src/project_kit/candidates.py
      record:
        - PRJ-004
        - ADR-039
        - ADR-049
        - ADR-064
        - ADR-065#8
        - ADR-065#9
        - ADR-065#11
        - ADR-059
        - COR-004
        - ADR-034#1
        - ADR-089#6
        - ADR-089#7
        - ADR-092#7
        - ADR-092#4
      artefact:
        - ACT-operator
        - REQ-002
        - REQ-009
        - REQ-012
        - REQ-026
        - REQ-027
        - REQ-028
        - REQ-029
        - REQ-030
        - REQ-031
---

# UC-052 — Run each project at the version it pins

**Goal:** Run each project at the version it pins, and be told plainly when the system falls back to my installed CLI.

**Other actors:** None.

**Preconditions:**

- **From [UC-049](UC-049-install-system.md):** The [system](../../../glossary.md#term-system--system) is installed in the [project](../../../glossary.md#term-project--project), and its [manifest](../../../glossary.md#term-manifest--manifest) records the [version](../../../glossary.md#term-version--version) of the content the project holds.
- **From [UC-008](../040-release/UC-008-release-backbone.md):** Each [release](../../../glossary.md#term-release--release) a [version pin](../../../glossary.md#term-version-pin--version-pin) names carries its [release tag](../../../glossary.md#term-release-tag--release-tag) on the [distribution](../../../glossary.md#term-distribution--distribution)'s repository, so `uvx` can fetch that release ([ADR-039 D3](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#d3--pin-correspondence-assumes-disciplined-tagging)).

**Assumptions:**

- `uvx`, which `uv` brings, is on the machine ([PRJ-004](../../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)).

**Trigger:** The operator wants a [project](../../../glossary.md#term-project--project) to stay at its [release](../../../glossary.md#term-release--release) while the installed CLI moves, or runs a command in a project pinned that way.

**Main path:**

1. The operator runs `pkit pin` in the [project](../../../glossary.md#term-project--project).
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit pin` runs no such check, and writes in whatever repository holds its working directory. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system reads the [backbone](../../../glossary.md#term-backbone--backbone) [version](../../../glossary.md#term-version--version) the project records, `backbone_version` in `.pkit/manifest.yaml`. It writes `.pkit/version-pin` at that version, whole, and prints `Pinned project-kit to <version> (.pkit/version-pin).` ([ADR-049 point 3](../../../../../architecture/decisions/ADR-049-per-project-version-pin.md#3-three-separate-gestures-manage-the-pin--freeze-raise-remove--because-they-are-three-different-intents) and [REQ-027](../../../requirements/quality/050-adopt/REQ-027-pin-whole-written-last.md)).
4. The operator commits the [version pin](../../../glossary.md#term-version-pin--version-pin), so every clone of the project runs at it.
5. Later, the operator runs a `pkit` command in the project, where the installed CLI is at another [release](../../../glossary.md#term-release--release).
6. Before it loads the rest of the CLI, the system finds the project's version pin, naming another release than the running CLI's ([ADR-039 point 2](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#2-project-pins-a-version--me--re-exec-uvx-project-kitpin)).
7. The system checks that `uvx` can fetch the pinned release, from the [distribution](../../../glossary.md#term-distribution--distribution)'s git URL at its [release tag](../../../glossary.md#term-release-tag--release-tag) ([ADR-039 D2](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#d2--graceful-degradation-is-mandatory) and [REQ-031](../../../requirements/constraints/050-adopt/REQ-031-cli-from-distribution-url.md)).
8. The system runs the command under `uvx` at the pinned release, which brings that release's code and content together. It exits with the command's status ([ADR-039 D1](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#d1--version-lock-soundness-rests-on-adr-033)).
9. Later, the operator runs `pkit unpin`.
10. At its entry, `pkit unpin` checks the repository as step 2 does (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit unpin` runs no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

11. The system removes `.pkit/version-pin`, and prints `Removed pin (.pkit/version-pin); project now floats on the installed tool.` (ADR-049 point 3).

**Variants:**

- **1a.** `pkit upgrade` pinned the [project](../../../glossary.md#term-project--project) already, as it does by default ([UC-051](UC-051-upgrade-system.md)). The path goes on at step 4.
- **1b.** The operator names the [release](../../../glossary.md#term-release--release) the content is at, `pkit pin <version>`. The [system](../../../glossary.md#term-system--system) writes the [version pin](../../../glossary.md#term-version-pin--version-pin) at it, as step 3 does.
- **1c.** The operator names a newer release. The system runs that release's own `pkit upgrade` through `uvx`, with routing bypassed, which brings the content to that release ([REQ-026](../../../requirements/quality/050-adopt/REQ-026-interrupted-transition-completes.md), [REQ-029](../../../requirements/functional/050-adopt/REQ-029-compatibility-before-write.md) and [REQ-030](../../../requirements/functional/050-adopt/REQ-030-person-choice-never-silent.md)). Only then does `pkit pin` write the version pin, last ([ADR-049 point 5](../../../../../architecture/decisions/ADR-049-per-project-version-pin.md#5-bootstrap-the-raise-via-the-existing-pkit_no_route-bypass-self-invoked-in-the-gesture) and [REQ-027](../../../requirements/quality/050-adopt/REQ-027-pin-whole-written-last.md)).
- **1d.** On the path of 1c, the operator first passes `--dry-run` to `pkit pin`, to see each edit the raise would make. The system names each edit, and writes nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).

> [!WARNING]
> **Not built yet:** `pkit pin` takes no `--dry-run`, and refuses the flag. [COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md) decides that it offers one, and #1884 tracks it.

- **1e.** On the path of 1c, the newer release's upgrade fails. The system says so, and leaves the version pin where it was ([ADR-049 point 1](../../../../../architecture/decisions/ADR-049-per-project-version-pin.md#1-pin-source-a-dedicated-project-owned-directive-file)). The use case ends.
- **1f.** The operator names an older release. The system refuses with `refusing to pin <version>: it is OLDER than this project's current content`, and writes nothing. It names reverting the commit of each upgrade since that release, `git revert <commit>`, to roll the project back ([ADR-049 point 3](../../../../../architecture/decisions/ADR-049-per-project-version-pin.md#3-three-separate-gestures-manage-the-pin--freeze-raise-remove--because-they-are-three-different-intents)).
- **1g.** The operator names a branch, a commit, or a pre-release other than a [release candidate](../../../glossary.md#term-release-candidate--release-candidate) in PEP 440's normal form. The system refuses with `pkit pin takes a version like 1.145.0`, and writes nothing.
- **1h.** The project has no [manifest](../../../glossary.md#term-manifest--manifest). The system refuses, naming `pkit upgrade`, which writes the manifest ([ADR-065 point 8](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#8-each-stop-names-the-remedy-for-the-state-it-finds)).
- **1i.** The project is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository). The system refuses, since there the [router](../../../glossary.md#term-router--router) runs the checkout's own code before it reads any version pin ([ADR-059](../../../../../architecture/decisions/ADR-059-methodology-source-repository.md)).
- **1j.** The operator names a release candidate in PEP 440's normal form, such as `pkit pin 3.0.0rc1`, at a final release. The system orders it by PEP 440, so a candidate sorts below its final release. A version pin that names a candidate asks for it, so the system raises the project to it as 1c does ([ADR-089 point 6](../../../../../architecture/decisions/ADR-089-release-candidates.md#6-a-pin-may-name-a-candidate-and-a-pin-that-names-one-asks-for-candidates)).
- **1k.** The operator names a release candidate spelt another way, such as `2.0.0-rc.1`. The system refuses, names the normal form, `2.0.0rc1`, and writes nothing ([ADR-089 point 6](../../../../../architecture/decisions/ADR-089-release-candidates.md#6-a-pin-may-name-a-candidate-and-a-pin-that-names-one-asks-for-candidates)).
- **1l.** The project's manifest records a release candidate, and the operator names a release or release candidate newer than its content. The system refuses and writes nothing, since a project on a release candidate moves to no other release ([ADR-092 point 7](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#7-a-project-on-a-candidate-moves-to-no-other-release)). Its message names the ways off, as UC-051's 1f does, and `pkit upgrade --pre` where the move onto the candidate was cut short. The use case ends.
- **1m.** The operator names a release candidate whose withdrawal tag, `withdrawn/v<candidate>`, the [distribution](../../../glossary.md#term-distribution--distribution)'s repository holds. The system warns that the candidate is withdrawn, and pins it as 1b or 1j does, since the operator asked for it ([ADR-092 point 4](../../../../../architecture/decisions/ADR-092-final-release-from-head.md#4-a-withdrawal-is-a-tag-which-pkit-upgrade---pre-passes-by-and-pkit-pin-warns-of)). Where it cannot ask that repository, it warns that it could not check.
- **6a.** The project pins no [version](../../../glossary.md#term-version--version), or its version pin names the running CLI's release. The system runs the command itself ([ADR-039 point 3](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#3-match-or-no-pin--run-self)).
- **6b.** The working directory lies in the methodology's source repository. The system runs that checkout's own code, and reads no version pin ([ADR-039 point 1](../../../../../architecture/decisions/ADR-039-pkit-entry-point-router.md#1-source-checkout--exec-the-in-tree-dispatcher)).
- **6c.** `PKIT_NO_ROUTE` is set. The system runs the command under the running CLI, and reads no version pin.
- **6d.** The version pin names a release candidate. The system runs the command under `uvx` at that candidate, fetched from the candidate's own tag, as it runs a release ([ADR-089 point 6](../../../../../architecture/decisions/ADR-089-release-candidates.md#6-a-pin-may-name-a-candidate-and-a-pin-that-names-one-asks-for-candidates)).
- **7a.** `uvx` cannot fetch the pinned release, as offline, or `uvx` is missing. The system warns once on standard error that it runs the installed CLI instead, and runs the command there ([REQ-028](../../../requirements/quality/050-adopt/REQ-028-unresolved-pin-runs-installed.md)).
- **7b.** On the path of 7a, the installed CLI is older than the version pin. The warning says so, and says that `pkit sync` and `pkit upgrade` refuse rather than write older content over the project's.
- **7c.** On the path of 7a, the operator ran `pkit upgrade`. The system refuses, and names reconnecting, the version pin run through `uvx`, or `pkit unpin` then `pkit upgrade` ([ADR-065 point 9](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#9-a-pinned-projects-upgrade-runs-under-the-code-of-its-pin-or-of-a-newer-release)).
- **11a.** The project holds no version pin. The system prints `No pin to remove; project already floats on the installed tool.`.
- **11b.** The project's manifest records a release candidate. The system refuses and writes nothing, since a project on a release candidate stays pinned ([ADR-089 point 7](../../../../../architecture/decisions/ADR-089-release-candidates.md#7-an-upgrade-or-an-init-refuses-a-candidate-nobody-asked-for-and-a-move-to-a-candidate-always-pins)). Its message names the ways off, as UC-051's 1f does. The use case ends.

**Postconditions:** Each command in the [project](../../../glossary.md#term-project--project) runs at the [release](../../../glossary.md#term-release--release) its [version pin](../../../glossary.md#term-version-pin--version-pin) names, whatever CLI the machine has installed, while that release can be fetched. Where it cannot, the operator is told which CLI ran instead.

**Minimal guarantees:**

- The [version pin](../../../glossary.md#term-version-pin--version-pin) holds the old one or the new one, never part of either ([REQ-027](../../../requirements/quality/050-adopt/REQ-027-pin-whole-written-last.md)).
- A raise writes the version pin only once the content reached the new [release](../../../glossary.md#term-release--release). A failed raise leaves the old version pin ([ADR-049 point 1](../../../../../architecture/decisions/ADR-049-per-project-version-pin.md#1-pin-source-a-dedicated-project-owned-directive-file)).
- A version pin that cannot be fetched never fails a command in the [router](../../../glossary.md#term-router--router) ([REQ-028](../../../requirements/quality/050-adopt/REQ-028-unresolved-pin-runs-installed.md)).
- `pkit pin` never moves a [project](../../../glossary.md#term-project--project) to an older release ([ADR-049 point 3](../../../../../architecture/decisions/ADR-049-per-project-version-pin.md#3-three-separate-gestures-manage-the-pin--freeze-raise-remove--because-they-are-three-different-intents)).
- `pkit pin`, `pkit unpin` and `pkit upgrade` write the version pin, and so does a `pkit init` run by a [release candidate](../../../glossary.md#term-release-candidate--release-candidate) ([ADR-064 point 3](../../../../../architecture/decisions/ADR-064-upgrade-pins-by-default.md#3-what-the-default-does-not-reach)). No other command writes it ([ADR-065 point 11](../../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state) and [REQ-002](../../../requirements/functional/REQ-002-project-owned-writers.md)).
