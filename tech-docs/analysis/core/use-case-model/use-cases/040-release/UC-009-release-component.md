---
id: UC-009
title: Release my component on its own version
status: active
actor: ACT-component-author
other-actors:
  - ACT-ci-pipeline
  - ACT-operator
after:
  - [UC-003]
  - [UC-034]
  - [UC-009, UC-015, UC-019]
requirements:
  - REQ-005
  - REQ-009
  - REQ-012
shortfalls:
  - at: 10
    issue: "#1765"
    record: ADR-034#1
  - at: "3h"
    issue: "#1884"
    record: COR-004
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/release.py
        - src/project_kit/versioning.py
        - src/project_kit/changesets.py
        - src/project_kit/cli.py
        - .github/workflows/release-pr.yml
      record:
        - PRJ-002#D1
        - PRJ-002#D3
        - PRJ-002#D4
        - PRJ-004
        - COR-010
        - COR-041
        - COR-004
        - ADR-034#1
      artefact:
        - ACT-component-author
        - ACT-ci-pipeline
        - ACT-operator
        - REQ-005
        - REQ-009
        - REQ-012
    revalidated:
      at: 2026-10-25T05:24:20Z
      outcome: unchanged
      unchanged-because: The change makes the help of pkit process graph say how its presets combine, as the command does it, and the command keeps the same edges. No step here filters that graph, so the use case holds.
---

# UC-009 — Release my component on its own version

**Goal:** Release my component on its own version, and say which backbone versions it works with.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): in project-kit, opens the [release](../../../glossary.md#term-release--release) [pull request](../../../glossary.md#term-pull-request--pull-request) that carries the [component](../../../glossary.md#term-component--component)'s new [version](../../../glossary.md#term-version--version). That pull request carries the new versions of the [backbone](../../../glossary.md#term-backbone--backbone) and of other components too (UC-008).
- **Operator** (`ACT-operator`): is asked before `pkit release apply` changes a repository other than the session's own. So no such write happens silently (REQ-012).

**Preconditions:**

- **From UC-003:** Changes to the [component](../../../glossary.md#term-component--component) declare, in [changesets](../../../glossary.md#term-changeset--changeset) naming it, what each means for the component's next [version](../../../glossary.md#term-version--version).
- **From UC-034:** The component's changes landed on the [default branch](../../../glossary.md#term-default-branch--default-branch), so their changesets wait under `.changes/unreleased/`.
- **From UC-009, UC-015 or UC-019:** The component's `package.yaml` gives its `version` and a `requires_backbone` [range](../../../glossary.md#term-range--range). The component's last [release step](../../../glossary.md#term-release-step--release-step) wrote them, or its author did when packaging it as a [capability](../../../glossary.md#term-capability--capability) or writing it as an [adapter](../../../glossary.md#term-adapter--adapter).

**Assumptions:**

- The [component](../../../glossary.md#term-component--component)'s repository declares, in [changesets](../../../glossary.md#term-changeset--changeset) under `.changes/unreleased/`, what each [change](../../../glossary.md#term-change--change) means for its [release step](../../../glossary.md#term-release-step--release-step), as project-kit does (PRJ-002 D1).
- The author has run the component on the [backbone](../../../glossary.md#term-backbone--backbone) the repository carries. The new [version](../../../glossary.md#term-version--version) claims that the component works with that backbone, and the author owns that claim (COR-041).

**Trigger:** The component author decides to ship, as a new [version](../../../glossary.md#term-version--version), what the [component](../../../glossary.md#term-component--component)'s [changesets](../../../glossary.md#term-changeset--changeset) declare.

**Main path:**

1. The component author runs `pkit release plan`.
2. The [system](../../../glossary.md#term-system--system) groups the pending [changesets](../../../glossary.md#term-changeset--changeset) by what each names, and takes the highest segment for each. It prints the [component](../../../glossary.md#term-component--component)'s move as `<component>: <old> -> <new> (<segment>)`, with each floor and upper bound a changeset declares for the component.
3. The author runs `pkit release apply` on a [release](../../../glossary.md#term-release--release) branch, and confirms `Write these versions and consume the changesets?`.
10. At its entry, before it prints its plan, `pkit release apply` checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit release apply` runs the check only when `--tag --push` asks it to push a tag. Without them, it writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

4. The system writes the component's new [version](../../../glossary.md#term-version--version) in the `version:` line of its `package.yaml`.
5. The system widens the upper bound of the component's `requires_backbone` to cover the [backbone](../../../glossary.md#term-backbone--backbone) the repository carries, the one the author releases under. The system never narrows an upper bound, and moves no floor unless a changeset declares that floor (`versioning.py`).
6. The system raises each floor a changeset declares for the component, on the backbone or on another [capability](../../../glossary.md#term-capability--capability). It also widens each upper bound on a capability that a changeset says the component runs on (PRJ-002 D4).
7. The system adds an entry at the top of `CHANGELOG.md`, headed by the date, since the backbone does not move. The system heads each of the component's notes with `**<component> <version>**`, and states each raised floor, such as `Requires backbone >=1.149.0.`
8. The system deletes the changesets it consumed.
9. The author commits the [release step](../../../glossary.md#term-release-step--release-step)'s writes, and merges them into the [default branch](../../../glossary.md#term-default-branch--default-branch). They get no tag, since a tag names a backbone version, read from `.pkit/VERSION` (PRJ-004 and `versioning.py`).

**Variants:**

- **1a.** In project-kit, `release-pr.yml` runs the [release step](../../../glossary.md#term-release-step--release-step) for the [component](../../../glossary.md#term-component--component), with the [backbone](../../../glossary.md#term-backbone--backbone) where the backbone moves (UC-008). A release step that moves no backbone takes the branch `release/<run id>`. The maintainer merges the [release](../../../glossary.md#term-release--release) [pull request](../../../glossary.md#term-pull-request--pull-request) as UC-008 says, and the use case ends with no tag cut.
- **3a.** The author runs `pkit release apply --no-broaden`, to keep the upper bound as written, such as for a patch known not to work on the newest backbone. Step 5 is skipped, and each declared floor and upper bound is still written.
- **3b.** A [changeset](../../../glossary.md#term-changeset--changeset) declares `requires_backbone: release`, and the release step moves no backbone. The floor rises to the current backbone. The plan adds `backbone does not move this release`, asking the author to confirm that the needed surface shipped there.
- **3c.** On the path of 3b, the current backbone is a pre-release, such as `1.150.0rc1`. The [system](../../../glossary.md#term-system--system) refuses the release step before writing anything, since no floor rises to a pre-release (PRJ-002 D4). The use case ends.
- **3d.** A changeset declares a floor or an upper bound the release step cannot write. Examples are an explicit floor above the backbone the tree carries, and a `release` floor on a [capability](../../../glossary.md#term-capability--capability) the release step does not move. The system refuses before writing anything, and the use case ends (PRJ-002 D4).
- **3e.** A declared floor would leave a [range](../../../glossary.md#term-range--range) that admits no backbone, such as where `--no-broaden` keeps an upper bound at or below the floor. The system refuses the release step before writing anything, and the use case ends.
- **3f.** The release step would leave another capability whose range excludes the component's new [version](../../../glossary.md#term-version--version). The system refuses before writing anything, naming that capability, its range and the version (PRJ-002 D4). The use case ends.
- **3g.** The release step moves the backbone too. Step 5 instead widens every component's upper bound to cover the new backbone's minor, and the backbone is released as UC-008 says.
- **3h.** The author first passes `--dry-run` to `pkit release apply`, to see each edit it would make. The system names each edit, and writes nothing (REQ-009).

> [!WARNING]
> **Not built yet:** `pkit release apply` takes no `--dry-run`, and refuses the flag. COR-004 decides that it offers one, and #1884 tracks it.

- **6a.** A floor already stands at or above the version a changeset declares. The floor stays as it is, and the plan says `requires_backbone floor stays`.

**Postconditions:**

- The [component](../../../glossary.md#term-component--component)'s `package.yaml` carries its new [version](../../../glossary.md#term-version--version). The component's `requires_backbone` [range](../../../glossary.md#term-range--range) admits the [backbone](../../../glossary.md#term-backbone--backbone) it was released under, unless the author kept the upper bound.
- The changelog entry says what changed in the component, and what the component now requires.
- A repository that pulls the component whole receives the new version through a transition of the component. The transition moves the component to a ref holding that version (COR-041 and COR-059 [point](../../../glossary.md#term-point--point) 3). In project-kit, a [release step](../../../glossary.md#term-release-step--release-step) that moves only components reaches a CLI taken from a tag with the next [release](../../../glossary.md#term-release--release) (PRJ-004).

**Minimal guarantees:**

- No floor rises unless a [changeset](../../../glossary.md#term-changeset--changeset) declares it, so a [release step](../../../glossary.md#term-release-step--release-step) never claims a need no changeset declared (`release.py` and PRJ-002 D4).
- The release step only widens an upper bound, and never narrows one (`versioning.py` and PRJ-002 D4).
- A release step the [system](../../../glossary.md#term-system--system) refuses for a changeset's declaration, or for a [range](../../../glossary.md#term-range--range), writes nothing. Each of those refusals comes before the first write (`release.py`).
