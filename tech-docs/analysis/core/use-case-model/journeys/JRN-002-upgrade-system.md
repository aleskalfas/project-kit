---
id: JRN-002
title: Upgrade the system
status: active
actor: ACT-adopter
steps:
  - UC-051
  - UC-053
relies-on:
  - UC-048
  - UC-049
  - UC-008
  - UC-023
  - UC-038
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/upgrade.py
        - src/project_kit/connections.py
        - src/project_kit/status.py
        - src/project_kit/declared_rule_sets.py
      record:
        - COR-059#3
        - COR-059#6
        - COR-051#7
        - COR-017
        - PRJ-004
        - ADR-064#1
        - ADR-065#12
      artefact:
        - ACT-adopter
        - UC-051
        - UC-053
        - UC-048
        - UC-049
        - UC-008
        - UC-023
        - UC-038
    revalidated:
      at: 2026-10-24T03:45:15Z
      outcome: unchanged
      unchanged-because: UC-008 changed only in variant 9a, the refusal of a pull request that is no release pull request. This journey needs from UC-008 only the tagged release.
---

# JRN-002 — Upgrade the system

**Goal:** Upgrade my project to a newer release, and re-pin each inherited rule set once I have reviewed its new major.

**Steps:**

1. UC-051 — Upgrade the system like a dependency
   - **Needs from UC-048 (outside this journey):** the CLI the operator installed from a release's tag, whose content the upgrade copies. A CLI installed from a branch or from main's head has a version that vouches for no content (ADR-065 point 12). The upgrade's target then names none.
   - **Needs from UC-049 (outside this journey):** the system installed in the project, its manifest recording the versions the project holds. An install cut short leaves the project incomplete, so this upgrade finishes that install before it moves on (COR-059 point 6).
   - **Needs from UC-008 (outside this journey):** the release to move to, tagged on the distribution's repository. A release step that moves only components makes no release (PRJ-004). Those components' new versions reach a CLI installed from a tag only with the backbone's next release.
2. UC-053 — Re-pin an inherited rule set once I have reviewed its new major
   - **Needs from step 1 (UC-051):** a method rule set's new major, copied in with the component that ships it. The upgrade names no rule set's pin it leaves behind (`upgrade.py`). The adopter finds each with `pkit status`, or as a `pkit validate` failure (COR-051 point 7). Where the project's merges wait on validation, the upgrade's own change fails there until the re-pin rides in that change.
   - **Needs from UC-023 (outside this journey):** the rule set of the project's own that a capability's install created, pinned to the major the capability's method set had then (COR-017). That pin falls behind once an upgrade brings the method set's new major.
   - **Needs from UC-038 (outside this journey):** a rule set the project authored that inherits another set. Either such a set or the one UC-023 created is enough. No command moves a rule set's pin, so each such pin moves only when the adopter edits it (COR-051 point 7).

**Variants:**

- **1a.** No set that a rule set of the project's own inherits moved to a new major. `pkit status` shows every pin current, and the path ends after step 1 (UC-053 variant 2a).
- **1b.** The upgrade stops before it completes, such as on a failing migration. It writes no version pin, and the next upgrade runs that migration again, so the path rejoins at step 1 (COR-059 point 6).
- **2a.** The adopter will not follow a rule of the new major, and keeps the old pin (UC-053 variant 4a). Validation keeps failing on the set, so where merges wait on validation the upgrade's change cannot land, and the path ends.
- **2b.** The adopter stops inheriting the set instead (UC-053 variant 4a). No pin is then behind, and the path ends.

**Postconditions:** The project holds the target release's content, with every migration up to it run. Its version pin names that release, unless the adopter declined one. Validation passes each rule set of the project's own, which pins the current major of each set it inherits.

**Minimal guarantees:**

- An upgrade cut short reads as incomplete, and the next one finishes it (COR-059 point 6).
- A failed upgrade writes no version pin, and the router never reads a torn one (ADR-064 point 1).
- While a rule set's pin is behind the set it names, no rule binds through that pin (COR-051 point 7). Validation fails meanwhile, so the gap is never silent.
