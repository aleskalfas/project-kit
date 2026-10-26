---
id: REQ-024
title: Validation checks a part of an LDOC rule only where the rule binds
status: active
statement: "`pkit living-docs validate` checks a page's reader, its structure and its diagrams' `accTitle` and `accDescr` only where the rule each part belongs to binds on the page."
measure: "On a page where `RS-LDOC-003`, `RS-LDOC-004` or `RS-LDOC-008` does not bind, as `pkit rule-sets reach` gives it, validation reads no part of that rule. Its summary counts the page among those that check left out."
applies-to: "The capability's validator, `pkit living-docs validate`, wherever it runs: as the `living-docs:spaces` member of `pkit validate`, and inside each stamp of `pkit living-docs new`."
actors:
  - core:ACT-developer
  - core:ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/_lib/binding.py
        - tests/test_living_docs_spaces.py
      record:
        - living-docs:DEC-001#3
        - living-docs:DEC-001#6
        - COR-051#2
---

# REQ-024 · Functional · Validation checks a part of an LDOC rule only where the rule binds

**Verified by:** Tests find that a [page](../../glossary.md#term-page--page) `RS-LDOC-003` binds on is checked for its [reader](../../glossary.md#term-reader--reader), and that one it does not bind on has no reader read. Others find that a page reached only through a pin behind `LDOC`'s major is not checked. Another finds that a diagram fails only where `RS-LDOC-008` binds. One more finds that where the [backbone](../../../core/glossary.md#term-backbone--backbone)'s one <!-- pkit:not-the-term -->answer of where the rules bind cannot be read, that is one error, with nothing checked.

**Rationale:** Checks that enforced `LDOC`'s parts on every [page](../../glossary.md#term-page--page) of the spaces would enforce one requirement two ways. The [rule](../../../core/glossary.md#term-rule--rule)'s status and its scope would then no longer decide where its check applies ([living-docs DEC-001](../../../../../.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md), and [COR-051 point 2](../../../../../.pkit/decisions/core/COR-051-rule-sets.md#2-a-rule-set-is-a-collection-of-artefacts)).
