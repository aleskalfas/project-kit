---
id: ACT-component-author
name: Component author
status: active
summary: "Someone who extends the system with a component (a capability or an adapter) rather than only using it."
needs:
  - Package a recurring discipline as a capability from the methodology's primitives, without forking the methodology.
  - Keep a capability I wrote in my own repository, where sync never overwrites it and uninstall never deletes it.
  - Give my capability roles, data points and processes that other components can connect to without naming it, and have the engine run and check them.
  - Release my component on its own version, and say which backbone versions it works with.
  - Carry the projects that installed my component across a surface change of it that breaks them.
  - Know my capability is ready to share before other repositories pull it.
  - Adapt the system to another harness, saying how far that harness meets each harness requirement and what of the permission model the harness cannot enforce.
pkit:
  friction:
    anchors:
      record:
        - COR-017
        - COR-031
        - COR-033
        - COR-041
        - COR-047
        - COR-053
        - ADR-040#5
        - COR-010
---

# ACT-component-author — Component author

Someone who extends the system with a component (a capability or an adapter) rather than only using it.

- **Role holders:**
  - an adopter growing a discipline in their own repository
  - an organisation that keeps private [methodology](../../glossary.md#term-methodology--methodology) in one repository for its others
  - whoever adapts the [system](../../glossary.md#term-system--system) to a new [harness](../../glossary.md#term-harness--harness)
- **Occasions:**
  - when a pattern recurs often enough to package
  - at each new [version](../../glossary.md#term-version--version) of their [component](../../glossary.md#term-component--component)
  - when a new [harness](../../glossary.md#term-harness--harness) arrives
- **Context:** the [component](../../glossary.md#term-component--component)'s decisions, schemas, [skills](../../glossary.md#term-skill--skill), [agent definitions](../../glossary.md#term-agent-definition--agent-definition) and [process](../../glossary.md#term-process--process) definitions. They own its [range](../../glossary.md#term-range--range).
- **Core:** the [capability](../../glossary.md#term-capability--capability) pattern, its [component origins](../../glossary.md#term-component-origin--component-origin), [connection points](../../glossary.md#term-connection-point--connection-point), the [process](../../glossary.md#term-process--process) engine and the [harness requirements](../../glossary.md#term-harness-requirement--harness-requirement) are where the component author extends the [system](../../glossary.md#term-system--system). They exist before any capability is installed.
- **Note:** in project-kit's [source repository](../../glossary.md#term-source-repository--source-repository) the methodology maintainer plays this part for the [capabilities](../../glossary.md#term-capability--capability) and the [adapter](../../glossary.md#term-adapter--adapter) project-kit ships.
