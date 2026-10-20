---
id: UC-018
title: Know my capability is ready to share
status: active
actor: ACT-component-author
other-actors: []
after:
  - [UC-015]
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/release.py
        - src/project_kit/changesets.py
        - src/project_kit/cli.py
        - src/project_kit/manifest.py
      record:
        - COR-041
        - ADR-040#4
        - ADR-040#5
      artefact:
        - ACT-component-author
---

# UC-018 — Know my capability is ready to share

**Goal:** Know my capability is ready to share before other repositories pull it.

**Other actors:** None.

**Preconditions:**

- **From UC-015:** The project holds the capability's subtree, with its package metadata.

**Assumptions:**

- A project that pulls the capability takes it whole, at a ref of the repository where it is authored. That project gates it on the range it declares (COR-041 and ADR-040 point 4). The fetch that would pull it is not built yet (`manifest.py`), so this check is what the author has today.
- The author has run the capability on each backbone version its range admits. The check reads the range's form, never that claim, which the author owns (ADR-040 point 5).

**Trigger:** The author means to let other repositories pull the capability.

**Main path:**

1. The author runs `pkit release check-shareable <name>` in the project.
2. The system finds the capability's package metadata among the components under `.pkit/`.
3. The system checks that the package metadata holds a `component:` mapping with a `component.version`, since a project that pulls the capability pins it by version.
4. The system checks that `requires_backbone` is a range bounded on both sides, of the form `>=LOW,<HIGH`. The gate of a project that pulls the capability can evaluate such a range (ADR-040 point 4).
5. The system looks in the package metadata for a path that only the author's machine has, such as one under `/Users/`.
6. The system prints `shareability check: <name> is ready to be shared — ok.`, and exits 0.

**Variants:**

- **1a.** The author names the backbone. The system refuses with `'backbone' is the backbone tier, not a shareable component. Pass an adapter or capability name.`, and the use case ends.
- **2a.** No package metadata under `.pkit/` names the capability. The system refuses with `unknown component '<name>'.`, lists the components it knows, and the use case ends.
- **3a.** A check of step 3 or step 4 fails, such as for `requires_backbone: "*"`. The system prints `<name> is not ready to be consumed externally-sourced:` and one line for each gap. It ends with `Fix the gaps above, then re-run. See COR-041 / .pkit/release/README.md.`, and exits 1. The author mends each gap, and the path rejoins at step 1.
- **5a.** The package metadata names a path that only the author's machine has. The system warns `manifest references what looks like a local-only path ('<path>') — a consumer will not have it.`, and the path goes on at step 6.

**Postconditions:** The capability's package metadata declares a version, and a range on the backbone bounded on both sides. So a project that pulls the capability can pin it by version, and gate it against its own backbone.

**Minimal guarantees:**

- The check writes nothing (`release.py`).
- A capability whose range has no upper bound never passes the check (`release.py`).
