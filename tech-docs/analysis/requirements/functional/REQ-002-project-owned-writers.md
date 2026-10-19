---
id: REQ-002
title: Project-owned content is written only by the writers records name
status: active
statement: The system writes project-owned content only through a writer that a decision record names.
measure: Sync leaves each project-owned file as it was, save the entries merge delivery adds. Every other write to project-owned content comes from a writer a decision record names.
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
        - ADR-065#11
      artefact:
        - ACT-adopter
---

# REQ-002 · Functional · Project-owned content is written only by the writers records name

**Verified by:** Tests run sync over a project's own files, its `.claude/settings.json` and its operational rules among them, and find each as it was. Tests run merge delivery over a project's `.claude/settings.json` and its `CLAUDE.md`, and find every entry the project wrote still there. Tests of the routine that copies the methodology's trees find that it neither writes over nor removes a file the project owns. No test covers every writer at once.

**Rationale:** The adopter keeps their own files beside the methodology's, and the system must never break anything they wrote. COR-001 decides that "the core layer writes project-owned paths only through the writers that records name, and sync writes them only through merge delivery". Merge delivery adds the methodology's entries, and never removes an entry the project wrote (COR-002).
