---
id: ACT-component-author
name: Component author
status: active
needs:
  - Package a recurring discipline as a capability from the system's primitives, without forking the system.
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
      at: 2026-10-14T09:21:11Z
      outcome: updated
---

# ACT-component-author — Component author

Someone who extends the system with a component (a capability or an adapter) rather than only using it.

- **Can be:**
  - an adopter growing a discipline in their own repository
  - an organisation that keeps private methodology in one repository for its others
  - whoever adapts the system to a new harness
- **Comes:**
  - when a pattern recurs often enough to package
  - at each release of their component
  - when a new harness arrives
- **Brings:** the component's decisions, schemas, skills, agents and process definitions. They own its compatibility claim.
- **Core:** the capability pattern, its origins, connection points, the process engine and the harness requirements are the extension points this role uses. They exist before any capability is installed.
- **Note:** in project-kit's source repository the methodology maintainer plays this part for the capabilities and the adapter project-kit ships.
