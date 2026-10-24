---
id: JRN-002
title: Upgrade the system
status: active
actor: ACT-adopter
steps:
  - UC-051
  - UC-053
relies-on:
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
        - COR-059
        - COR-059#6
        - COR-051#7
        - COR-017
        - PRJ-004
        - ADR-064#1
      artefact:
        - ACT-adopter
        - UC-051
        - UC-053
        - UC-049
        - UC-008
        - UC-023
        - UC-038
---

# JRN-002 — Upgrade the system

**Goal:** Upgrade my project to a newer release, and re-pin each inherited rule set once I have reviewed its new major.

**Steps:**

1. UC-051 — Upgrade the system like a dependency
   - **Needs from UC-049 (outside this journey):** the system installed in the project, its manifest recording the versions the project holds. An install cut short reads as incomplete, and this upgrade finishes it first (COR-059 point 6).
   - **Needs from UC-008 (outside this journey):** the release to move to, tagged on the distribution's repository. A release step that moves only components makes no release, so their new versions reach the project only with the backbone's next release (PRJ-004).
2. UC-053 — Re-pin an inherited rule set once I have reviewed its new major
   - **Needs from step 1 (UC-051):** a method rule set's new major, copied in with the component that ships it. The upgrade names no pin it leaves behind, so the adopter finds each with `pkit status`, or as a `pkit validate` failure (COR-051 point 7). Where the project's merges wait on validation, the upgrade's own change fails there until the re-pin rides in that change.
   - **Needs from UC-023 (outside this journey):** the rule set of the project's own that a capability's install created, pinned to the major the capability's method set had then (COR-017). That pin falls behind once an upgrade brings the method set's new major.
   - **Needs from UC-038 (outside this journey):** a rule set the project authored that inherits another set. Either such a set or the one UC-023 created is enough. No command writes a pin, so each pin moves only when the adopter edits it (COR-051 point 7).

**Variants:**

- **1a.** No set that a rule set of the project's own inherits moved to a new major. `pkit status` shows every pin current, and the path ends after step 1 (UC-053 variant 2a).
- **1b.** The upgrade stops before it completes, such as on a failing migration. It writes no version pin, and the next upgrade runs that migration again, so the path rejoins at step 1 (COR-059 point 6).
- **2a.** The adopter will not follow a rule of the new major, and keeps the old pin. Validation keeps failing on the set, and the path ends (UC-053 variant 4a).

**Postconditions:** The project holds the target release's content, with every migration up to it run. Its version pin names that release, unless the adopter declined one. Validation passes each rule set of the project's own, which pins the current major of each set it inherits.

**Minimal guarantees:**

- An upgrade cut short reads as incomplete, and the next one finishes it (COR-059 point 6).
- A failed upgrade writes no version pin, and the router never reads a torn one (ADR-064 point 1).
- While a pin is behind its set, no rule binds through that pin, and validation fails, so the gap is never silent (COR-051 point 7).
