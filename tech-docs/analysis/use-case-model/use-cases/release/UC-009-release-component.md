---
id: UC-009
title: Release my component on its own version
status: active
actor: ACT-component-author
other-actors:
  - ACT-ci-pipeline
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
      artefact:
        - ACT-component-author
        - ACT-ci-pipeline
---

# UC-009 — Release my component on its own version

**Goal:** Release my component on its own version, and say which backbone versions it works with.

**Other actors:**

- **CI pipeline** (`ACT-ci-pipeline`): in project-kit, opens the release pull request that carries the component's release beside any other (UC-008).

**Preconditions:** The component's repository declares its releases in changesets under `.changes/unreleased/`, as project-kit does (PRJ-002 D1). Changesets naming the component wait there (UC-003), and its `package.yaml` gives its `version` and a `requires_backbone` range.

**Assumptions:**

- The author has run the component on the backbone the repository carries. The release claims that the component works with that backbone, and the author owns that claim (COR-041).

**Trigger:** The component author decides to release what the component's changesets declare.

**Main path:**

1. The component author runs `pkit release plan`.
2. The system groups the pending changesets by component, and takes the highest segment of each. It prints the component's move as `<component>: <old> -> <new> (<segment>)`, with each floor and bound it will raise or widen.
3. The author runs `pkit release apply` on a release branch, and confirms `Write these versions and consume the changesets?`.
4. The system writes the component's new version in the `version:` line of its `package.yaml`.
5. The system widens the upper bound of the component's `requires_backbone` to cover the backbone the repository carries, the one the author releases under. It never narrows a bound, and never moves a floor on its own.
6. The system raises each floor a changeset declares for the component, on the backbone or on another capability. It also widens each upper bound on a capability that a changeset says the component runs on (PRJ-002 D4).
7. The system adds an entry at the top of `CHANGELOG.md`, headed by the date, since the backbone does not move. It tags each of the component's notes `**<component> <version>**`, and states each raised floor, such as `Requires backbone >=1.149.0.`
8. The system deletes the changesets it consumed.
9. The author commits the release and merges it. The release cuts no tag, since a tag names a version of the backbone only (PRJ-004).

**Variants:**

- **1a.** In project-kit, the weekly release workflow plans and applies the release, with the backbone's where it moves (UC-008). A release that moves no backbone takes the branch `release/<run id>`, and the path goes on at step 9.
- **3a.** The author runs `pkit release apply --no-broaden`, to keep the upper bound as written, such as for a patch known not to work on the newest backbone. Step 5 is skipped, and each declared floor and bound is still written.
- **3b.** A changeset declares `requires_backbone: release`, and the release moves no backbone. The floor rises to the current backbone, and the plan adds `backbone does not move this release`, asking the author to confirm that the needed surface shipped there.
- **3c.** That current backbone is a pre-release, such as `1.150.0rc1`. The system refuses the release before writing anything, since no floor rises to a pre-release (PRJ-002 D4). The use case ends.
- **3d.** A declared floor would leave a range that admits no backbone, such as where `--no-broaden` keeps an upper bound at or below the floor. The system refuses the release before writing anything, and the use case ends.
- **3e.** The release would leave another capability whose range excludes the component's new version. The system refuses before writing anything, naming the dependent, its range and the version (PRJ-002 D4). The use case ends.
- **3f.** The release moves the backbone too. Step 5 instead widens every component's upper bound to cover the new backbone's minor, and the backbone is released as UC-008 says.
- **6a.** A floor already stands at or above the version a changeset declares. The floor stays as it is, and the plan says `requires_backbone floor stays`.

**Postconditions:** The component's `package.yaml` carries its new version. Its `requires_backbone` range admits the backbone it was released under, unless the author kept the upper bound. The changelog entry says what changed in the component, and what the component now requires.

**Minimal guarantees:**

- No floor rises unless a changeset declares it, so a release never claims a need its author did not state (PRJ-002 D4).
- The release only widens an upper bound, and never narrows one (PRJ-002 D4).
- A release the system refuses writes nothing (`release.py`).
