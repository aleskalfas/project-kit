---
rule-set: USER
version: 1.1.0
inherits: [living-docs:LDOC@1]
scope:
  paths: [docs/**, README.md, .pkit/**/README.md]
  exclude: [.pkit/release/README.md]
  types: [living-docs:page]
rules:
  RS-USER-001:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-13T20:06:25Z
          outcome: unchanged
          unchanged-because: "living-docs DEC-001's points are now headings, so the anchor names point 3, which states this rule: the user space adds that reader paths stay unbroken. Point 3's text is unchanged, so the rule holds."
---

# The user space's definition

The rules project-kit's user space follows: the shared method, `living-docs:LDOC`, and the rule below. The user space is `docs/`, the top-level `README.md` (its entry point) and the adopter-facing READMEs under `.pkit/` ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); the list and each place's assignment are in `.pkit/capabilities/living-docs/project/config.yaml`.

The set's scope selects the pages in those places by their type, living-docs' page type (living-docs DEC-001 point 4). It leaves out the release guide, a README under `.pkit/` that belongs to the technical space.

## RS-USER-001 — Reader paths stay unbroken

The paths the user space's readers take through its pages stay unbroken.
