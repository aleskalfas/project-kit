---
rule-set: USER
version: 1.1.0
inherits: [living-docs:LDOC@1, WRITE@0]
rules:
  RS-USER-001:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-03T14:01:25Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 4 gains how a page anchors a source outside the repository — the source kind, each source captured as one file holding the version read; it says nothing of the links between pages, so the paths the user space's readers take through its pages stay unbroken
---

# The user space's definition

The rules project-kit's user space follows: the shared method, `living-docs:LDOC`, project-kit's writing rules, [`WRITE`](../../rule-sets/writing.md), and the rule below. The user space is `docs/`, the top-level `README.md` (its entry point) and the adopter-facing READMEs under `.pkit/` ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); the list and each place's assignment are in `.pkit/capabilities/living-docs/project/config.yaml`.

## RS-USER-001 — Reader paths stay unbroken

The paths the user space's readers take through its pages stay unbroken.
