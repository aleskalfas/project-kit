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
---

# REQ-002 · Functional · Project-owned content is written only by the writers records name

**Verified by:** Tests run sync over project-owned content, `.claude/settings.json` and the project's operational rules among it, and find each file as it was. Tests run merge delivery over a project's `.claude/settings.json` and its `CLAUDE.md`, and find every entry the project wrote still there. Tests of propagation find that it neither writes over nor removes a file of project-owned content. No test covers every writer at once.

**Rationale:** The adopter keeps their own files beside the methodology's, and the system must never break anything they wrote. COR-001 decides that "the core layer writes project-owned paths only through the writers that records name, and sync writes them only through merge delivery". Merge delivery adds the methodology's entries, and never removes an entry the project wrote (COR-002). ADR-065 point 11 names the writers of first install, sync and the version transition. Other writers are named by their own records, such as COR-048 point 5 for the keys of the backbone configuration.
