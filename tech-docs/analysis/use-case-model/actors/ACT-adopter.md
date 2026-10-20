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
  - Add my own operational rules, settings, permission grants and agent paths beside the methodology's, never editing its files.
  - Make my merges wait on the system's checks, knowing they bind only once my CI requires them.
  - Re-pin an inherited rule set to its new major version once I have reviewed it.
  - Report a problem with the system, and follow what happens to it.
  - Choose the parts of each kind of analysis artefact as I adopt software analysis, keeping, relabelling or adding to the shipped ones.
  - Set up a documentation space for one audience, with its own location and a definition whose scope selects its pages.
  - Bring my existing documents into documentation spaces, anchored and fit for their readers, through a proposed plan that I review before anything moves.
  - See, before I install a capability, what it would connect to in my project and which conflicts I would have to resolve.
  - Upgrade one capability on its own to the version my project's release ships, without moving the backbone.
pkit:
  friction:
    anchors:
      record:
        - COR-001
        - COR-010
        - software-analysis:DEC-001#1
        - living-docs:DEC-001#1
        - living-docs:DEC-001#2
        - living-docs:DEC-001#8
        - COR-053#8
        - COR-059#3
    revalidated:
      at: 2026-10-19T19:00:00Z
      outcome: unchanged
      unchanged-because: DEC-001 point 1 gains the domain-model view, a kind that explains the glossary's concepts, and says nothing new of an actor or its needs. The adopter's needs hold as written.
---

# ACT-adopter — Adopter

The person who adopts the methodology for a project and keeps its setup.

- **Setup:**
  - what is installed, at which version
  - which of their own additions sit beside it
  - which checks the project's merges wait on
- **Occasions:**
  - at setup
  - at each upgrade
  - when the project needs a discipline
- **Context:** their project, its existing `CLAUDE.md` and settings, its repository settings, and the rules and grants they add.
- **Core:** the split between methodology-owned and project-owned files, and the install and upgrade lifecycle, exist for this role. Installing a capability is itself a core act.
