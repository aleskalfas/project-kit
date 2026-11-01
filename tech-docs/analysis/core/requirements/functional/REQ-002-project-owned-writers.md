---
id: REQ-002
title: Project-owned content is written only by the writers records name
status: active
statement: The system writes project-owned content only through a writer that a decision record names.
measure: Sync leaves each file of project-owned content as it was, save the entries merge delivery adds or restores. Every other write to project-owned content comes from a writer that a decision record names.
applies-to: Every command of the backbone and of the components that writes into a project.
obligation: v1:sha256:f2906ce2f7e7aff6532fdc3d80926d953d6733be54857b3350404d58c5d304c4
actors:
  - ACT-adopter
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/treecopy.py
        - tests/test_sync.py
        - tests/test_treecopy.py
        - tests/test_merge_settings_sh.py
        - tests/test_merge_claude_md_sh.py
      record:
        - COR-001
        - COR-002
        - COR-048#5
        - ADR-065#11
      artefact:
        - ACT-adopter
---

# REQ-002 · Functional · Project-owned content is written only by the writers records name

**Verified by:** Tests run [sync](../../glossary.md#term-sync--sync) over [project-owned content](../../glossary.md#term-project-owned-content--project-owned-content), `.claude/settings.json` and the [project](../../glossary.md#term-project--project)'s [operational rules](../../glossary.md#term-operational-rule--operational-rule) among it, and find each file as it was. Tests run [merge delivery](../../glossary.md#term-merge-delivery--merge-delivery) over a project's `.claude/settings.json` and its `CLAUDE.md`, and find every entry the project wrote still there. Tests of [propagation](../../glossary.md#term-propagation--propagation) find that it neither writes over nor removes a file of project-owned content. No test covers every writer at once.

**Rationale:** The adopter keeps their own files beside the [methodology](../../glossary.md#term-methodology--methodology)'s, and the [system](../../glossary.md#term-system--system) must never break anything they wrote. [COR-001](../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md) decides that "the core layer writes project-owned paths only through the writers that records name, and [sync](../../glossary.md#term-sync--sync) writes them only through [merge delivery](../../glossary.md#term-merge-delivery--merge-delivery)". Merge delivery adds the methodology's entries, and never removes an entry the [project](../../glossary.md#term-project--project) wrote ([COR-002](../../../../../.pkit/decisions/core/COR-002-merge-delivery.md)).

[ADR-065 point 11](../../../../architecture/decisions/ADR-065-upgrade-runs-the-transition.md#11-each-writer-of-a-project-owned-path-is-named-and-each-owner-of-derivable-state) names the writers of first [install](../../glossary.md#term-install--install), sync and the [version transition](../../glossary.md#term-version-transition--version-transition). Other writers are named by their own records, such as [COR-048 point 5](../../../../../.pkit/decisions/core/COR-048-backbone-configuration.md#5-written-only-with-consent) for the keys of the [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration).
