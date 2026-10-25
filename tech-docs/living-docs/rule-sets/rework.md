---
rule-set: REWORK
version: 1.0.0
inherits: [living-docs:LDOC@1, WRITE@2]
scope:
  paths: [.pkit/permissions/README.md, docs/permissions/README.md]
  types: [living-docs:page]
rules: {}
---

# The documentation rework's writing rules

This set brings project-kit's general writing rules, `WRITE`, to each page the documentation rework has rewritten (EPIC #1928). It adds no rule of its own.

- **What it binds:** the rules of `WRITE` and of the shared method, `living-docs:LDOC`, on each page its scope selects. The scope selects by path and by living-docs' page type, as the space definitions do.
- **Why it inherits `LDOC`:** a set that holds a project's documentation rules inherits `LDOC` (living-docs DEC-001 point 3). It pins major 1, as `USER` and `TECH` do. One page reached through two pins of a set at different majors fails validation (COR-051 point 7).
- **How it grows:** each slice of the rework adds the pages it rewrites to the scope's paths. A page several slices rewrite joins with the last of them.
- **When it goes:** once the spaces' definitions, `TECH` and `USER`, inherit `WRITE` (#1350). Every page then takes `WRITE` through its space, and this set is removed.
