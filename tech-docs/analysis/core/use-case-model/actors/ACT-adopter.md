---
id: ACT-adopter
name: Adopter
status: active
summary: "The person who adopts the methodology for a project and keeps its setup."
needs:
  - Install the system with one command, committed for the team or kept out of the shared repository, and see its wiring into my project.
  - Upgrade the system like a dependency, at a version the whole project pins, with its migrations run for me and my own files left alone.
  - Add or remove a capability, one shared from another of my repositories included, and be told of a name collision instead of being overwritten.
  - Choose which installed capability provides a role.
  - Declare my project's backbone configuration once (name, default branch, documentation roots, friction mode, anchored places, declared surface, excluded paths) and have it validated.
  - Add my own operational rules, the harness's settings, permission grants and agent paths beside the methodology's, never editing its files.
  - Make my merges wait on the system's checks, knowing they bind only once my CI requires them.
  - Re-pin an inherited rule set to its new major version once I have reviewed it.
  - Report a problem with the system, and follow what happens to it.
  - See, before I install a capability, what it would connect to in my project and which conflicts I would have to resolve.
  - Upgrade one capability on its own to the version my project's release ships, without moving the backbone.
pkit:
  friction:
    anchors:
      record:
        - COR-001
        - COR-010
        - COR-053#8
        - COR-059#3
---

# ACT-adopter — Adopter

The person who adopts the methodology for a project and keeps its setup.

- **Setup:**
  - what is installed, at which [version](../../glossary.md#term-version--version)
  - which of their own additions sit beside it
  - which checks the [project](../../glossary.md#term-project--project)'s merges wait on
- **Occasions:**
  - at setup
  - at each upgrade
  - when the [project](../../glossary.md#term-project--project) needs a discipline
- **Context:** their [project](../../glossary.md#term-project--project), its existing `CLAUDE.md` and settings, its repository settings, and the rules and grants they add.
- **Core:** the split between methodology-owned and project-owned files, and the [install](../../glossary.md#term-install--install) and upgrade lifecycle, exist for the adopter. Installing a [capability](../../glossary.md#term-capability--capability) is itself a core act.
