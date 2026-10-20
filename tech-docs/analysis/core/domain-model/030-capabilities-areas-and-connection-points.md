---
id: VIEW-capabilities-areas-and-connection-points
title: Capabilities, areas and connection points
status: active
explains:
  - TERM-capability
  - TERM-range
  - TERM-area
  - TERM-connection-point
  - TERM-role
  - TERM-data-point
pkit:
  friction:
    anchors:
      record:
        - COR-003
        - COR-011
        - COR-017
        - COR-026
        - COR-027
        - COR-030
        - COR-031#D3
        - COR-052
        - COR-053
        - COR-061#1
        - COR-061#5
        - PRJ-002#D4
      artefact:
        - TERM-capability
        - TERM-range
        - TERM-area
        - TERM-connection-point
        - TERM-role
        - TERM-data-point
---

# VIEW-capabilities-areas-and-connection-points — Capabilities, areas and connection points

Some disciplines suit only some projects, yet forcing them on every [project](../glossary.md#term-project--project) is wrong, and copying them into each loses their reuse (COR-017). A part can also fail without a word when what it builds on changes incompatibly (COR-030). Other parts must help each other without either depending on the other (COR-052, COR-053). Every project also needs fixed homes, with declared layouts, for its kinds of content (COR-011).

A [capability](../glossary.md#term-capability--capability) packages one discipline, which each project chooses to [install](../glossary.md#term-install--install) beside the [backbone](../glossary.md#term-backbone--backbone) and its [adapters](../glossary.md#term-adapter--adapter). A [component](../glossary.md#term-component--component)'s ranges say which [versions](../glossary.md#term-version--version) of what it builds on it works with. [Areas](../glossary.md#term-area--area) are the homes every project holds, with no install. Capabilities work together through [roles](../glossary.md#term-role--role) and [connection points](../glossary.md#term-connection-point--connection-point) without naming each other, and a [data point](../glossary.md#term-data-point--data-point) is the kind that takes data in.

```mermaid
classDiagram
  accTitle: Capabilities, areas and connection points
  accDescr: A capability is a component a project chooses to install. A component declares a range on the backbone, and a capability may declare a range on another capability. An area is a slice of a project's .pkit tree that needs no install. A capability provides roles, and under a role it defines connection points, which other components fill, depend on or subscribe to. A data point is the kind of connection point that takes data in.
  class Component["Component"]
  class Backbone["Backbone"]
  class Project["Project"]
  class Capability["Capability"]
  class Range["Range"]
  Range : floor
  Range : upper bound
  class Area["Area"]
  Area : README
  class ConnectionPoint["Connection point"]
  ConnectionPoint : address
  ConnectionPoint : kind
  ConnectionPoint : version
  class Role["Role"]
  Role : qualified name
  class DataPoint["Data point"]
  DataPoint : combination policy
  Capability --|> Component
  Project o-- Capability : installs
  Project *-- Area : holds
  Component --> Range : declares on the backbone
  Capability --> Range : declares on another capability
  Range ..> Backbone : admits versions of
  Capability "1" --> "*" Role : provides
  Capability "1" --> "*" ConnectionPoint : defines
  Role "1" o-- "*" ConnectionPoint : names
  DataPoint --|> ConnectionPoint
```

## Capability

Defined in [TERM-capability](../glossary.md#term-capability--capability).

**Why:** A discipline that suits only some projects must be one each [project](../glossary.md#term-project--project) can choose (COR-017). Otherwise it is forced on every project, or scattered through each project's own files, where it cannot be reused (COR-017).

A capability is a [component](../glossary.md#term-component--component) that packages one discipline: its [decision records](../glossary.md#term-decision-record--decision-record), [skills](../glossary.md#term-skill--skill), [agent definitions](../glossary.md#term-agent-definition--agent-definition), scripts and schemas. Each project chooses whether to [install](../glossary.md#term-install--install) it. `software-analysis` is one.

**Attributes:**

- its own subtree, `.pkit/capabilities/<name>/`, with its `package.yaml`, its decision records and its skills (COR-017)
- its own namespace of decision records, DEC, cited with its name, as in `software-analysis:DEC-001` (COR-017)
- the [roles](../glossary.md#term-role--role) it provides (COR-053 [point](../glossary.md#term-point--point) 1)

**Relations:**

- It is a kind of component. The [adapter](../glossary.md#term-adapter--adapter) is the other kind, which carries what one [harness](../glossary.md#term-harness--harness) needs and no discipline (COR-027).
- A project installs it, or registers it where the project authors the capability itself (COR-031 point D3).
- It may depend on other capabilities, each through a [range](../glossary.md#term-range--range) (COR-030).
- It ships the agent definitions its discipline needs (COR-026).

**States:** None.

**Always true:**

- It owns its subtree, and puts nothing into the [backbone](../glossary.md#term-backbone--backbone)'s own folders (COR-017).
- Registering a capability the project authors copies nothing (COR-031 point D3).

## Range

Defined in [TERM-range](../glossary.md#term-range--range).

**Why:** A part whose dependency changed in a way that breaks it fails without a word when it runs (COR-030). A range turns that into a refusal when a part is installed, upgraded or removed (COR-030).

A range is the set of [versions](../glossary.md#term-version--version) a [component](../glossary.md#term-component--component) declares it works with: of the [backbone](../glossary.md#term-backbone--backbone), or of another [capability](../glossary.md#term-capability--capability). It runs from a floor to any upper bound, as in `>=1.149.0,<2.0.0`.

**Attributes:**

- a floor, the lowest version it admits
- an upper bound, the version it stops below, where it has one

**Relations:**

- Each component declares one on the backbone, its `requires_backbone` (COR-017).
- A capability declares one for each capability it depends on (COR-030).
- [Install](../glossary.md#term-install--install) checks the ranges before it writes anything (COR-030).

**States:** None.

**Always true:**

- A capability installs only where what it depends on falls within its ranges. Install never proceeds silently past one, and never installs a dependency by itself (COR-030).
- A floor rises only where a declaration asks for it, never by itself (PRJ-002 D4).

## Area

Defined in [TERM-area](../glossary.md#term-area--area).

**Why:** Each domain of content needs a fixed home, with a layout tools can rely on (COR-011). Without one, each new home invents its own shape, and tools have nothing to work from (COR-011).

An area is a top-level slice of a [project](../glossary.md#term-project--project)'s `.pkit/` tree, such as `.pkit/decisions/`. Its README declares its layout. Every project holds each area the [methodology](../glossary.md#term-methodology--methodology) ships, with no [install](../glossary.md#term-install--install), and may add areas of its own.

**Attributes:**

- its name, the folder `.pkit/<name>/` (COR-011)
- a README that declares its variant and its layout (COR-011)

**Relations:**

- It sits beside the [capabilities](../glossary.md#term-capability--capability) in `.pkit/`, and is no capability (COR-011).
- The methodology's areas ship with the [backbone](../glossary.md#term-backbone--backbone).
- Where it holds both the methodology's content and the project's, a `core/` folder and a `project/` folder keep them apart (COR-003).

**States:** None.

**Always true:**

- Every project has every area the methodology ships (COR-011).
- An area a project adds is the project's own, and cannot take the name of an area the methodology ships (COR-011).
- Tools read an area's layout from its README, never from the files they find in it (COR-011).

## Connection point

Defined in [TERM-connection-point](../glossary.md#term-connection-point--connection-point).

**Why:** [Capabilities](../glossary.md#term-capability--capability) need each other's knowledge, and need to react to each other, without depending on each other (COR-053). A connection point's address names a [role](../glossary.md#term-role--role), never a capability, so replacing one capability with another touches nothing connected to it (COR-053).

A connection point is a declared interface that one installed capability defines. Other [components](../glossary.md#term-component--component) fill it, depend on it or subscribe to it, without naming that capability. Its address names its role, as in `pkit::analysis:revalidation-evidence`.

**Attributes:**

- an address, `<publisher>::<role>:<point>` (COR-053 [point](../glossary.md#term-point--point) 2)
- a kind (COR-053 point 2):
  - a [data point](../glossary.md#term-data-point--data-point), which takes data in
  - a process, offered for others to depend on
  - an event, which signals that a writing command finished
- a [version](../glossary.md#term-version--version), an integer that rises only where it breaks what connects to it (COR-053 point 5)
- a description, in prose (COR-053 point 3)

**Relations:**

- The capability that provides its role defines it (COR-053 point 2).
- Other components connect to it at a version equal to its own (COR-053 point 5).
- The [backbone](../glossary.md#term-backbone--backbone) resolves and checks every connection to it (COR-053 point 7).

**States:** None.

**Always true:**

- It is optional by default. A connection to it is mandatory only with a reason (COR-053 point 6).
- Two of its versions are compatible only when they are equal (COR-053 point 5).
- The component that offers an event never names those that subscribe to it (COR-053 point 2).

## Role

Defined in [TERM-role](../glossary.md#term-role--role).

**Why:** A connection that names the [capability](../glossary.md#term-capability--capability) at its other end breaks when that capability is replaced (COR-053). A role names the job instead, and its publisher qualifies it, so no name is reserved for everyone (COR-053).

A role is a name under which one installed capability provides [connection points](../glossary.md#term-connection-point--connection-point), so that others use them without naming that capability. The publisher that coined the name qualifies it, as in `pkit::documentation`.

**Attributes:**

- its qualified name, `<publisher>::<role>` (COR-053 [point](../glossary.md#term-point--point) 1)
- no [version](../glossary.md#term-version--version): a role redefined in a way that breaks takes a new name (COR-053 point 5)

**Relations:**

- A capability declares the roles it provides (COR-053 point 1).
- The capability providing a role defines its connection points (COR-053 point 2).
- Another capability may provide the same role, and stand in for the one that coined it (COR-053 point 1).

**States:** None.

**Always true:**

- One installed capability at most provides each role: two are an error until the [project](../glossary.md#term-project--project) selects one (COR-053 points 1 and 7).
- An installed capability the project did not select connects nothing under that role, while its own commands still run (COR-053 point 1).

## Data point

Defined in [TERM-data-point](../glossary.md#term-data-point--data-point).

**Why:** A [component](../glossary.md#term-component--component) often needs knowledge that another component, or the [project](../glossary.md#term-project--project), is better able to give (COR-052). The consumer must still work without that other component, and one set of rules must settle precedence, collisions and failure (COR-052).

A data point is a declared interface through which the [capability](../glossary.md#term-capability--capability) providing a [role](../glossary.md#term-role--role) accepts input. A project file, installed capabilities and that capability's own default fill it, and the [backbone](../glossary.md#term-backbone--backbone) resolves what it holds. It is the kind of [connection point](../glossary.md#term-connection-point--connection-point) that takes data in.

**Attributes:**

- its address, its [version](../glossary.md#term-version--version) and the schema of its data (COR-052 points 1 and 5)
- a combination policy, one of these (COR-052 [point](../glossary.md#term-point--point) 3):
  - one filler alone fills it
  - entries merge by id
  - entries merge and any collision fails
- optionally a question, which asks a person about the point and records the reply (COR-061 point 1)

**Relations:**

- It is the kind of connection point that takes data in (COR-053 point 2).
- Where fillers overlap, a project file wins over a capability, and a capability wins over the default (COR-052 point 4).

**States:** None.

**Always true:**

- A filler that fails gives no result, which is never read as an empty one (COR-052 point 6).
- A capability's filler counts only where its version matches the point's (COR-052 point 5).
- A question asks only what has no recorded reply. Where nobody can reply, it records nothing (COR-061 points 1 and 5).
