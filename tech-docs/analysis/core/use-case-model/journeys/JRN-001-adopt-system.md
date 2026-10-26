---
id: JRN-001
title: Adopt the system
status: active
actor: ACT-adopter
steps:
  - UC-049
  - UC-021
  - UC-023
  - UC-006
relies-on:
  - UC-048
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/install.py
        - src/project_kit/visibility.py
        - src/project_kit/sync.py
        - src/project_kit/project_config.py
        - src/project_kit/declared_rule_sets.py
        - src/project_kit/friction_check.py
        - src/project_kit/provisioning.py
      record:
        - COR-001
        - COR-017
        - COR-050#1
        - COR-050#12
        - COR-050#14
        - COR-050#15
        - COR-051#6
        - COR-059#6
        - COR-059#9
        - PRJ-004
        - ADR-009#1
        - ADR-009#3
        - ADR-049#1
        - ADR-065#11
        - ADR-065#12
      artefact:
        - ACT-adopter
        - UC-049
        - UC-021
        - UC-023
        - UC-006
        - UC-048
---

# JRN-001 — Adopt the system

**Goal:** Install the system into my project with my backbone configuration and capabilities, and make my merges wait on the system's checks.

**Steps:**

1. [UC-049](../use-cases/050-adopt/UC-049-install-system.md) — Install the system into my project with one command
   - **Needs from [UC-048](../use-cases/050-adopt/UC-048-install-cli.md) (outside this journey):** the CLI on the adopter's machine, at a [release](../../glossary.md#term-release--release). A CLI installed from a branch or from main's latest commit names the last release as its [version](../../glossary.md#term-version--version), while its files may be newer. The [project](../../glossary.md#term-project--project) then records a version that vouches for no content ([PRJ-004](../../../../../.pkit/decisions/project/PRJ-004-distribution-channel.md) and [ADR-065 point 12](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#12-a-version-identifies-content-only-for-a-tagged-install)).
2. [UC-021](../use-cases/020-set-up/UC-021-declare-backbone-configuration.md) — Declare my project's backbone configuration once, and have it validated
   - **Needs from step 1 (UC-049):** the [system](../../glossary.md#term-system--system) installed in the project, with `.pkit/` to hold the [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration). Where the adopter keeps the system out of the shared repository (UC-049 variant 12a), `.pkit/` is excluded whole. The team's clones then never hold the backbone configuration the adopter declares ([ADR-009 point 3](../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#3-private--make-the-whole-footprint-git-invisible-via-gitinfoexclude)).
3. [UC-023](../use-cases/020-set-up/UC-023-add-or-remove-capability.md) — Add or remove a capability, and be told of a name collision
   - **Needs from step 1 (UC-049):** the version the project records, and the [adapters](../../glossary.md#term-adapter--adapter) that deploy the [capability](../../glossary.md#term-capability--capability)'s [skills](../../glossary.md#term-skill--skill) and [agent definitions](../../glossary.md#term-agent-definition--agent-definition). Under a CLI at another release than the project records, the capability's [install](../../glossary.md#term-install--install) stops before it reads anything ([COR-059 point 9](../../../../../.pkit/decisions/core/COR-059-version-transition.md#9-a-command-that-propagates-content-under-another-version-than-the-project-records-stops)).
   - **Needs from step 1 (UC-049):** the adopter's choice to commit the system for the team, or keep it out of the shared repository. A system kept out of the shared repository hides only its [components](../../glossary.md#term-component--component)' declared footprints, and none holds the [rule set](../../glossary.md#term-rule-set--rule-set) a capability's install creates. So git does not ignore that set, and a commit of the adopter's may carry it to the team ([ADR-009 point 1](../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#1-the-footprint-is-one-declared-list-per-component)).
   - **Needs from UC-048 (outside this journey):** the capability, shipped in the [distribution](../../glossary.md#term-distribution--distribution) of the CLI the operator installed. Outside the [methodology](../../glossary.md#term-methodology--methodology)'s [source repository](../../glossary.md#term-source-repository--source-repository), the capability's install copies it from there (UC-023 variant 6a). A capability that distribution does not ship is refused, unless the project authors it (UC-023 variant 3b).
   - **Needs from step 2 (UC-021):** the internal [documentation root](../../glossary.md#term-documentation-root--documentation-root), under which the capability's install may create a rule set of the project's own ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)). A root changed by hand afterwards leaves that set where no [place](../../glossary.md#term-place--place) finds it, and [validation](../../glossary.md#term-validation--validation) fails on that set ([COR-051 point 6](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#6-two-kinds-two-owners)).
4. [UC-006](../use-cases/030-change/UC-006-gate-merges.md) — Make my merges wait on the system's checks
   - **Needs from step 1 (UC-049):** the system committed for the team, so each checkout the CI pipeline makes holds it. A checkout holds nothing of a system kept out of the shared repository (ADR-009 point 3).
   - **Needs from step 1 (UC-049):** the version the project records. Under a CLI at another release than the project records, the CI job's `pkit sync` stops, and the CI job fails (COR-059 point 9). A [version pin](../../glossary.md#term-version-pin--version-pin), which the install does not write, keeps the CI job at the project's release ([ADR-049 point 1](../../../../architecture/decisions/ADR-049-per-project-version-pin.md#1-pin-source-a-dedicated-project-owned-directive-file)).
   - **Needs from step 2 (UC-021):** the places the backbone configuration declares, which the [change check](../../glossary.md#term-change-check--change-check) reads beside those an installed capability declares (COR-050 points [1](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#1-artefacts) and [14](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#14-project-settings)). Where no place is declared at all, or no [artefact](../../glossary.md#term-artefact--artefact) in one carries anchors, the change check is dormant and passes ([COR-050 point 15](../../../../../.pkit/decisions/core/COR-050-anchors-and-friction.md#15-dormant-until-used)). The merges then wait on validation and the project's other checks alone.
   - **Needs from step 3 (UC-023):** the capability, committed with the commands it registers. The rule set its install creates makes the method set's accepted rules bind on older artefacts, so the CI job may fail (COR-017).
   - **Needs from step 3 (UC-023):** what the capability's install provisioned. A checkout holds none of it, so the CI job runs `pkit sync` first ([ADR-065 point 11](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state)). Otherwise a validator the capability registers finds its environment not provisioned, and validation fails (UC-006 variant 3a).

**Variants:**

- **1a.** The adopter keeps the [system](../../glossary.md#term-system--system) out of the shared repository ([UC-049](../use-cases/050-adopt/UC-049-install-system.md) variant 12a). No checkout the CI pipeline makes holds the system, so the path ends after step 3 ([ADR-009 point 3](../../../../architecture/decisions/ADR-009-git-footprint-visibility.md#3-private--make-the-whole-footprint-git-invisible-via-gitinfoexclude)).
- **2a.** The adopter keeps the default of every key of the [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration). The path goes on at step 3, and the [change check](../../glossary.md#term-change-check--change-check) reads only the places the [capabilities](../../glossary.md#term-capability--capability) declare.
- **3a.** The [project](../../glossary.md#term-project--project) needs no capability yet. The path goes on at step 4, and the change check reads only the places the backbone configuration declares.

**Postconditions:** The [project](../../glossary.md#term-project--project) holds the [system](../../glossary.md#term-system--system) and the [capabilities](../../glossary.md#term-capability--capability) the adopter chose, committed for the team, and [validation](../../glossary.md#term-validation--validation) passes the project's [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration). No [pull request](../../glossary.md#term-pull-request--pull-request) merges into the [default branch](../../glossary.md#term-default-branch--default-branch) through the hosting service's protection while a check of the CI job fails on it.

**Minimal guarantees:**

- An [install](../../glossary.md#term-install--install) cut short reads as incomplete, and the next [version transition](../../glossary.md#term-version-transition--version-transition) finishes it ([COR-059 point 6](../../../../../.pkit/decisions/core/COR-059-version-transition.md#6-a-transition-of-the-backbone-records-its-target-first-and-its-completion-last)).
- Wherever the path stops, `pkit config set` has written no value that breaks the schema of the [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration) (`project_config.py`).
- No name collision of a [capability](../../glossary.md#term-capability--capability) is settled silently. The adopter chooses for each one, and with nobody to reply nothing is copied ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md)).
