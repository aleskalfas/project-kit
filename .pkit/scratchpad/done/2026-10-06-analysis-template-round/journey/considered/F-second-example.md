---
id: JRN-xxx
title: Upgrade the methodology and re-pin a rule set
status: active
actor: ACT-adopter
steps: [UC-yy1, UC-yy2]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/upgrade.py
        - src/project_kit/rule_sets.py
        - src/project_kit/status.py
      record: [COR-051]
      artefact: [UC-yy1, UC-yy2, ACT-adopter]
---

# JRN-xxx — Upgrade the methodology and re-pin a rule set

**Goal:** Upgrade the methodology in my project, and re-pin each of my rule sets whose inherited set moved to a new major.

**Steps:**

1. UC-yy1 — The adopter upgrades the methodology with `pkit upgrade`, which runs the migrations and syncs the new content.
2. UC-yy2 — The adopter reviews each inherited set that moved to a new major, and re-pins the set that inherits it.

**Seams:**

- **UC-yy2:** relies on the rule sets UC-yy1 synced. An inherited set that gained an accepted rule, or withdrew, superseded or tightened one, is now at a new major (COR-051 point 7). A project set still pinning the old major fails `pkit validate` under `versions`, and `pkit status` names the edit that re-pins it (`rule_sets.py`). That failure starts UC-yy2, so the upgrade passes no pipeline until the re-pin lands with it.

**Postconditions:** the project runs the new version of the methodology, and each of its rule sets pins the major its inherited set is at.
