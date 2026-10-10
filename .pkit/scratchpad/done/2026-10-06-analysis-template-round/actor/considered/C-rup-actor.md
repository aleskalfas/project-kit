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

**Brief description:** the person who builds: decisions, rules, notes, code and its documentation, one change at a time. They need the system to pass each change through the acceptance gate and the friction check, and to land it as COR-009 sets out.

**Characteristics:**

- **Environment:** a clone of the project's repository, on a machine whose operator they may be (`ACT-operator`). They direct agents there to make the change.
- **Number of users:** everyone who changes the project. One person working alone may commit straight to the default branch (COR-009 point 5).
- **Frequency of use:** for every change, and again when some work recurs often enough to deserve tooling of its own.
- **Domain knowledge:** the project's own code, decisions and rules.
- **Computer experience:** git, branches and pull requests, one logical unit per commit (COR-008 and COR-009).
- **Other applications:** git, the hosting service through `gh` (ADR-061), and the harness the agents run in.

**Relationships:**

- **Use cases:** the primary actor of those that build and land a change, such as `UC-xxx — Land a change on the default branch`.
- **Generalisation:** none.
