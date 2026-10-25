---
id: ACT-director
name: Director
status: active
summary: "The person who directs a project's AI agents while several of them work on it at once."
needs:
  - Set up the topology my project runs, so that every agent of it reads the same one.
  - See which agent works on which issue, without visiting each agent.
  - Measure one topology against another on comparable work, by figures the tracker holds.
pkit:
  friction:
    anchors:
      record:
        - project-management:DEC-008
        - project-management:DEC-045
---

# ACT-director — Director

The person who directs a project's AI agents while several of them work on it at once. They choose which agents run and on what, and they decide what the agents bring to them.

**Setup:** the [project](../../../core/glossary.md#term-project--project)'s [topology](../../glossary.md#term-topology--topology), which names each agent, its [scope](../../glossary.md#term-scope--scope), and whether it plans, builds or does both.

**Human role:** only a person supplies the intent the agents act on, and decides what they bring (DEC-008).

**Occasions:**

- when a [project](../../../core/glossary.md#term-project--project) starts to run several agents at once
- whenever the shape of the work changes, such as a new [workstream](../../glossary.md#term-workstream--workstream)
- each time the agents bring decisions to them

**Context:** the [project](../../../core/glossary.md#term-project--project)'s [workstreams](../../glossary.md#term-workstream--workstream), and the authority to decide what the agents bring.

**Note:** one person may be the director, the planner and the merge authoriser at once. The director acts for a [project](../../../core/glossary.md#term-project--project), while the core's operator is at the controls of one machine. On a platform, each agent's sandbox is a machine of its own.
