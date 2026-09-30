---
rule-set: USER
version: 1.0.0
inherits: [living-docs:LDOC@1]
rules:
  RS-USER-001:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-09-30T03:25:07Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 1 now says a place or a folder of held documents another component declares is that component's, a review log say; the user space's pages, and the paths readers take through them, are unchanged
---

# The user space's definition

The rules project-kit's user space follows: the shared method, `living-docs:LDOC`, and the rule below. The user space is `docs/`, the top-level `README.md` (its entry point) and the adopter-facing READMEs under `.pkit/` ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); the list and each place's assignment are in `.pkit/capabilities/living-docs/project/config.yaml`.

## RS-USER-001 — Reader paths stay unbroken

The paths the user space's readers take through its pages stay unbroken.
