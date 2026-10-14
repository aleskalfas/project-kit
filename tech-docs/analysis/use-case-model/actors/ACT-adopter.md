---
id: ACT-adopter
name: Adopter
status: active
needs:
  - Install the system with one command, committed for the team or kept out of the shared repository, and see its wiring into my project.
  - Upgrade it like a dependency, at a version pinned for the whole project, with its migrations run for me and my own files left alone.
  - Add or remove a capability, one shared from another of my repositories included, and be told of a name collision instead of being overwritten.
  - Choose which installed capability provides a role.
  - Declare my project's settings once (name, default branch, documentation roots, friction mode, anchored places, declared surface, excluded paths) and have them validated.
  - Add my own operational rules, settings, permission grants and agent paths beside the system's, never editing its files.
  - Make my merges wait on the system's checks, knowing they bind only once my CI requires them.
  - Re-pin an inherited rule set to its new major version once I have reviewed it.
  - Report a problem with the system, and follow what happens to it.
pkit:
  friction:
    anchors:
      record:
        - COR-001
        - COR-010
    revalidated:
      at: 2026-10-14T09:21:09Z
      outcome: updated
---

# ACT-adopter — Adopter

The person who adopts the methodology for a project and keeps its setup.

- **The setup:**
  - what is installed, at which version
  - which of their own additions sit beside it
  - which checks the project's merges wait on
- **Comes:**
  - at setup
  - at each upgrade
  - when the project needs a discipline
- **Brings:** their project, its existing `CLAUDE.md` and settings, its repository settings, and the rules and grants they add.
- **Core:** the split between the files the system owns and those the project owns, and the install and upgrade lifecycle, exist for this role. Installing a capability is itself a core act.
