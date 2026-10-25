---
id: REQ-002
title: Project-owned content is written only by the writers records name
status: active
statement: The system writes project-owned content only through a writer that a decision record names.
measure: Sync leaves each file of project-owned content as it was, save the entries merge delivery adds or restores. Every other write to project-owned content comes from a writer that a decision record names.
applies-to: Every command of the backbone and of the components that writes into a project.
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
    revalidated:
      at: 2026-10-24T20:50:45Z
      outcome: unchanged
      unchanged-because: ACT-adopter's core item says the adopter where it said this role. Its needs are the same, so this requirement holds.
---

# REQ-002 · Functional · Project-owned content is written only by the writers records name

**Verified by:** Tests run [sync](../../glossary.md#term-sync--sync) over [project-owned content](../../glossary.md#term-project-owned-content--project-owned-content), `.claude/settings.json` and the [project](../../glossary.md#term-project--project)'s [operational rules](../../glossary.md#term-operational-rule--operational-rule) among it, and find each file as it was. Tests run [merge delivery](../../glossary.md#term-merge-delivery--merge-delivery) over a project's `.claude/settings.json` and its `CLAUDE.md`, and find every entry the project wrote still there. Tests of [propagation](../../glossary.md#term-propagation--propagation) find that it neither writes over nor removes a file of project-owned content. No test covers every writer at once.

**Rationale:** The adopter keeps their own files beside the [methodology](../../glossary.md#term-methodology--methodology)'s, and the [system](../../glossary.md#term-system--system) must never break anything they wrote. COR-001 decides that "the core layer writes project-owned paths only through the writers that records name, and [sync](../../glossary.md#term-sync--sync) writes them only through [merge delivery](../../glossary.md#term-merge-delivery--merge-delivery)". Merge delivery adds the methodology's entries, and never removes an entry the [project](../../glossary.md#term-project--project) wrote (COR-002).

ADR-065 [point](../../glossary.md#term-point--point) 11 names the writers of first [install](../../glossary.md#term-install--install), sync and the [version transition](../../glossary.md#term-version-transition--version-transition). Other writers are named by their own records, such as COR-048 point 5 for the keys of the [backbone configuration](../../glossary.md#term-backbone-configuration--backbone-configuration).
