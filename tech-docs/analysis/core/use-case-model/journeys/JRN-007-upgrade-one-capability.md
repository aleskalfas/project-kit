---
id: JRN-007
title: Upgrade one capability, and re-pin its rule set
status: active
actor: ACT-adopter
steps:
  - UC-054
  - UC-053
relies-on:
  - UC-048
  - UC-023
  - UC-038
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/capabilities.py
        - src/project_kit/upgrade.py
        - src/project_kit/rule_sets.py
        - src/project_kit/status.py
      record:
        - COR-059#3
        - COR-051#7
        - COR-017
        - ADR-065#4
        - ADR-065#7
        - ADR-065#12
      artefact:
        - ACT-adopter
        - UC-054
        - UC-053
        - UC-048
        - UC-023
        - UC-038
---

# JRN-007 — Upgrade one capability, and re-pin its rule set

**Goal:** Upgrade one capability on its own, and re-pin each rule set that inherits its method rule set once I have reviewed the new major.

**Steps:**

1. [UC-054](../use-cases/050-adopt/UC-054-upgrade-capability.md) — Upgrade one capability on its own
   - **Needs from [UC-023](../use-cases/020-set-up/UC-023-add-or-remove-capability.md) (outside this journey):** the [capability](../../glossary.md#term-capability--capability), recorded in the [manifest](../../glossary.md#term-manifest--manifest) at its [version](../../glossary.md#term-version--version). Its [install](../../glossary.md#term-install--install) may have created a [rule set](../../glossary.md#term-rule-set--rule-set) of the [project](../../glossary.md#term-project--project)'s own. That set inherits the capability's method rule set, and pins the major the method rule set had then ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
   - **Needs from [UC-048](../use-cases/050-adopt/UC-048-install-cli.md) (outside this journey):** a CLI that ships the capability newer than the manifest records, at the [backbone](../../glossary.md#term-backbone--backbone) version the project records. A CLI installed from a tag ships a newer version of a capability only with the backbone's next [release](../../glossary.md#term-release--release) ([ADR-065 point 12](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#12-a-version-identifies-content-only-for-a-tagged-install)). So under such a CLI, this step finishes an upgrade of the capability that stopped before its end.
2. [UC-053](../use-cases/050-adopt/UC-053-repin-rule-set.md) — Re-pin an inherited rule set once I have reviewed its new major
   - **Needs from step 1 (UC-054):** the method rule set's new major, copied in with the capability's new version. `pkit status` shows each rule set's pin that the new major leaves behind, and `pkit validate` fails on each set that holds one ([COR-051 point 7](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)). Where the project's merges wait on [validation](../../glossary.md#term-validation--validation), the capability's upgrade lands only once the re-pin rides in its [change](../../glossary.md#term-change--change).
   - **Needs from [UC-038](../use-cases/030-change/UC-038-author-rule-sets.md) (outside this journey):** a rule set the project authored that inherits the method rule set. Either such a set or the one UC-023 created is enough. No command moves a rule set's pin, so each pin moves only when the adopter edits it (COR-051 point 7).

**Variants:**

- **1a.** The [capability](../../glossary.md#term-capability--capability)'s new [version](../../glossary.md#term-version--version) brings no new major of a set the [project](../../glossary.md#term-project--project) inherits. `pkit status` shows every pin current, and the path ends after step 1 ([UC-053](../use-cases/050-adopt/UC-053-repin-rule-set.md) variant 2a).
- **1b.** The capability's upgrade stops before its end, such as on a failing [migration](../../glossary.md#term-migration--migration). The [manifest](../../glossary.md#term-manifest--manifest) keeps the capability's old version, and the next upgrade runs the migration again, so the path rejoins at step 1 ([UC-054](../use-cases/050-adopt/UC-054-upgrade-capability.md) variant 7a).
- **2a.** The adopter will not follow a [rule](../../glossary.md#term-rule--rule) of the new major, and keeps the old pin (UC-053 variant 4a). [Validation](../../glossary.md#term-validation--validation) keeps failing on the set, so where merges wait on validation the upgrade's [change](../../glossary.md#term-change--change) cannot land, and the path ends.

**Postconditions:** The [capability](../../glossary.md#term-capability--capability) holds the [version](../../glossary.md#term-version--version) the running CLI ships, with its [migrations](../../glossary.md#term-migration--migration) run, and the [backbone](../../glossary.md#term-backbone--backbone)'s [recorded versions](../../glossary.md#term-recorded-version--recorded-version) did not move. Each [rule set](../../glossary.md#term-rule-set--rule-set) of the [project](../../glossary.md#term-project--project)'s own pins the current major of each set it inherits, and [validation](../../glossary.md#term-validation--validation) passes it.

**Minimal guarantees:**

- The [capability](../../glossary.md#term-capability--capability)'s upgrade writes neither of the [backbone](../../glossary.md#term-backbone--backbone)'s [recorded versions](../../glossary.md#term-recorded-version--recorded-version), and moves no recorded version down (ADR-065 points [4](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#4-a-transition-runs-in-cor-010s-order-with-seed-paths-after-the-migrations) and [7](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#7-syncs-guard-stops-a-command-that-would-propagate-under-another-version)).
- While a [rule set](../../glossary.md#term-rule-set--rule-set)'s pin is behind the set it names, no [rule](../../glossary.md#term-rule--rule) binds through that pin. [Validation](../../glossary.md#term-validation--validation) fails meanwhile, so the gap is never silent ([COR-051 point 7](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)).
