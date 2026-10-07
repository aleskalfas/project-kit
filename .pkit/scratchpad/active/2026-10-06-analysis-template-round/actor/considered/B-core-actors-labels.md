---
id: ACT-developer
name: Developer
status: active
needs:
  - Record my decisions beside the methodology's, and build only on accepted ones.
  - Author and extend my project's rule sets without editing the ones that ship with the methodology.
  - Think a question too big for a decision through in a scratchpad note, and retire the note once it has produced something.
  - Say what each of my documents rests on, so a change there reaches me.
  - Answer what my change made stale, judging an agent's proposed answer word for word, or running its commands myself when it cannot ask me.
  - Know before I push that my change passes the checks my project gates its merges on.
  - Have a substantive draft challenged before I adopt it, and have my diff checked against the methodology's conventions before I commit it.
  - Land my change on the default branch as one squash commit with a conventional title, through a pull request or directly when I work alone.
  - Turn recurring work into my project's own skill or agent, designing its dialogue as a storyboard first.
pkit:
  friction:
    anchors:
      record:
        - COR-009
---

# ACT-developer — Developer

The person who builds: decisions, rules, notes, code and its documentation, one change at a time.

- **Comes:** for every change, and again when some work recurs often enough to deserve tooling of its own.
- **Brings:** the change. They direct agents to make it.
- **Core:** whatever tracks the work, every change passes the acceptance gate and the friction check, and lands as COR-009 sets out. That the backbone itself lands pull requests is provisional (ADR-061 point 3, raised as #1222).
- **Note:** a work tracker's view of this role (project-management's "Implementer") comes with that capability.
