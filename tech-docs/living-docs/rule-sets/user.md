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
          at: 2026-10-01T23:31:25Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check, so two providers' results for one page at one commit stand side by side; that is the evidence point's key, and the paths the user space's readers take through its pages are untouched by it
---

# The user space's definition

The rules project-kit's user space follows: the shared method, `living-docs:LDOC`, and the rule below. The user space is `docs/`, the top-level `README.md` (its entry point) and the adopter-facing READMEs under `.pkit/` ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); the list and each place's assignment are in `.pkit/capabilities/living-docs/project/config.yaml`.

## RS-USER-001 — Reader paths stay unbroken

The paths the user space's readers take through its pages stay unbroken.
