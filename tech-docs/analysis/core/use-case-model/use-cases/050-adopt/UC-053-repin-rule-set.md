---
id: UC-053
title: Re-pin an inherited rule set once I have reviewed its new major
status: active
actor: ACT-adopter
other-actors: []
requirements:
  - REQ-005
after:
  - [UC-038]
  - [UC-051, UC-054, UC-038]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/status.py
        - src/project_kit/rule_sets.py
        - src/project_kit/connections.py
        - src/project_kit/cli.py
      record:
        - COR-051#7
      artefact:
        - ACT-adopter
        - REQ-005
---

# UC-053 — Re-pin an inherited rule set once I have reviewed its new major

**Goal:** Re-pin an inherited rule set to its new major version once I have reviewed it.

**Other actors:** None.

**Preconditions:**

- **From UC-038:** A rule set of the project's own inherits another set, pinned to that set's major (COR-051 point 7).
- **From UC-051, UC-054 or UC-038:** The inherited set has moved to a new major. An upgrade, or a capability's upgrade, brought a method rule set's new major, or the project gave a set of its own one.

**Assumptions:** None.

**Trigger:** A new major of a set the project inherits arrives, and the project's rule set still pins the old one.

**Main path:**

1. The adopter runs `pkit status`.
2. Under `Rule sets`, the system shows each pin behind its inherited set's major, as `<set> pins <pin>; <inherited set> is at <version>`. Beside each, it names the fix: review what changed in the inherited set, then update the pin in `inherits`. It writes nothing (REQ-005).
3. The adopter runs `pkit validate`. Its `versions` member fails on the inheriting set, naming the new major and the same fix (COR-051 point 7).
4. The adopter reviews what the inherited set's new major changed, such as a rule added, withdrawn, superseded or tightened.
5. The adopter edits the pin in the set's `inherits` to the new major, such as `software-analysis:SAN@2`. No command writes it.
6. The adopter gives the set a new major version of its own. A pin moved to another major changes the rules the set passes on (COR-051 point 7).
7. The adopter runs `pkit validate` again, and its `versions` member passes the set.
8. The adopter runs `pkit rule-sets reach`. The system shows the inherited set's accepted rules binding again through the set, and writes nothing (UC-038 and REQ-005).

**Variants:**

- **2a.** No pin is behind its set. The system shows `<n> checked, all current`, and the use case ends.
- **4a.** The adopter finds a rule of the new major that the project will not follow. The adopter keeps the old pin, or stops inheriting the set, and proposes the change to the set's owner (COR-051 point 7). While the pin is behind, validation keeps failing, and the use case ends.
- **6a.** Another set of the project's own inherits this set. The other set's pin now falls behind in turn, and the path repeats for the other set from step 1.
- **7a.** Two routes to one artefact pin the set at different majors. Validation fails on the artefact, naming both routes, and the path rejoins at step 5 (COR-051 point 7).

**Postconditions:** The project's rule set pins the inherited set's current major, and validation passes it. The inherited set's accepted rules bind through it again, as the adopter reviewed them.

**Minimal guarantees:**

- While a pin is behind its set, no rule binds through that pin, and validation fails, so the gap is never silent (COR-051 point 7).
- `pkit status`, `pkit validate` and `pkit rule-sets reach` write nothing (REQ-005).
- The system moves no pin of its own accord. The adopter moves it, once the new major is reviewed (COR-051 point 7).
