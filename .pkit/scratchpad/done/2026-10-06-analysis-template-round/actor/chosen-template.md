The maintainer's chosen parts, in two views. Each actor is shown whole, as its file would read on the default branch after #1346, inside its own fence.

- **The developer, as project-kit holds it:** the shipped parts, then project-kit's own labelled parts that the developer has something for, *Core* and *Note*. Its anchors gain ADR-061, which its *Core* cites.
- **The CI pipeline, in the shipped parts alone:** what an adopter's actor holds when the project adds nothing of its own. It is F, unchanged.

## The developer, as project-kit holds it

````markdown
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
        - ADR-061
---

# ACT-developer — Developer

The person who builds: decisions, rules, notes, code and its documentation, one change at a time.

- **Occasions:** for every change, and again when some work recurs often enough to deserve tooling of its own.
- **Context:** the change. They direct agents to make it.
- **Core:** whatever tracks the work, every change passes the acceptance gate and the friction check, and lands as COR-009 sets out. That the backbone itself lands pull requests is provisional (ADR-061 point 3, raised as #1222).
- **Note:** a work tracker's view of this role (project-management's "Implementer") comes with that capability.
````

## The CI pipeline, in the shipped parts alone

````markdown
---
id: ACT-ci-pipeline
name: CI pipeline
status: active
needs:
  - Run every check with no terminal and no person to answer, and gate the merge on its exit status.
  - Compare a change with its real base, the pull request's target or the queued merge's base, named once for all the checks.
  - Run the checks offline once the checkout is provisioned.
  - Get findings in a machine-readable form, to publish them where people look.
  - Be told when a shallow clone lacks history a check needs, rather than get a misleading result.
  - Have the whole-repository check report its findings without failing, so the check can run after merges and on a schedule.
  - Tag a release once it lands, from the version it declares, with no one there to confirm the push.
pkit:
  friction:
    anchors:
      record:
        - COR-054
        - COR-050
---

# ACT-ci-pipeline — CI pipeline

A project's continuous integration, acting on the system from outside. It is an actor because it starts work on its own trigger with no person in the session.

- **Occasions:** on every pull request, queued merge and push to the default branch, and on a schedule.
- **Context:** a clean checkout, a base to compare with, and no person to answer a prompt.
````
