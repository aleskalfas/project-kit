---
rule-set: TECH
version: 1.1.0
inherits: [living-docs:LDOC@1, WRITE@0]
rules: {}
---

# The technical space's definition

The rules project-kit's technical space follows: the shared method, `living-docs:LDOC`, and project-kit's writing rules, [`WRITE`](../../rule-sets/writing.md). The space adds no rule of its own yet. The technical space is `tech-docs/`, plus `CONTRIBUTING.md` (its entry point until `tech-docs/README.md` exists) and the release guide ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); each place's assignment is in `.pkit/capabilities/living-docs/project/config.yaml`.
