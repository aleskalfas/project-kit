---
rule-set: TECH
version: 1.1.0
inherits: [living-docs:LDOC@1]
scope:
  paths: [tech-docs/**, CONTRIBUTING.md, .pkit/release/README.md]
  types: [living-docs:page]
rules: {}
---

# The technical space's definition

The rules project-kit's technical space follows: the shared method, `living-docs:LDOC`. The space adds no rule of its own yet. The technical space is `tech-docs/`, plus `CONTRIBUTING.md` (its entry point until `tech-docs/README.md` exists) and the release guide ([ADR-055](../../architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md) point 3); each place's assignment is in `.pkit/capabilities/living-docs/project/config.yaml`.

The set's scope selects the pages in those places by their type, living-docs' page type (living-docs DEC-001 point 4). So the decision records, the rules and the analysis under `tech-docs/` stay outside it.
