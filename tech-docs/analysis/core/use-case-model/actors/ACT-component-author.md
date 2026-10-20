---
id: ACT-component-author
name: Component author
status: active
needs:
  - Package a recurring discipline as a capability from the methodology's primitives, without forking the methodology.
  - Keep a capability I wrote in my own repository, where sync never overwrites it and uninstall never deletes it.
  - Give my capability roles, data points and processes that other components can connect to without naming it, and have the engine run and check them.
  - Release my component on its own version, and say which backbone versions it works with.
  - Carry the projects that installed my component across a breaking change of it.
  - Know my capability is ready to share before other repositories pull it.
  - Adapt the system to another harness, and say how far that harness meets each requirement and what of the permission model the harness cannot enforce.
pkit:
  friction:
    anchors:
      record:
        - COR-031
        - COR-041
        - COR-047
    revalidated:
      at: 2026-10-20T01:36:54Z
      outcome: unchanged
      unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/use-case-model/actors/, with no word changed, so the role and its needs still hold.
---

# ACT-component-author — Component author

Someone who extends the system with a component (a capability or an adapter) rather than only using it.

- **Role holders:**
  - an adopter growing a discipline in their own repository
  - an organisation that keeps private methodology in one repository for its others
  - whoever adapts the system to a new harness
- **Occasions:**
  - when a pattern recurs often enough to package
  - at each release of their component
  - when a new harness arrives
- **Context:** the component's decisions, schemas, skills, agents and process definitions. They own its compatibility claim.
- **Core:** the capability pattern, its origins, connection points, the process engine and the harness requirements are the extension points this role uses. They exist before any capability is installed.
- **Note:** in project-kit's source repository the methodology maintainer plays this part for the capabilities and the adapter project-kit ships.
