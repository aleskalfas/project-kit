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

**Persona:** Dana Novak, 34, a backend developer in a team of five.

**Tagline:** lands small changes often, and wants nothing left stale behind them.

**Bio:** Dana joined the team two years ago. The team adopted the methodology this spring, and its checks now gate every merge.

**Experience:** fluent in git and pull requests. New to decision records and the friction check.

**Context:** her job requires it, since the project gates its merges on the methodology's checks. She uses it for every change, several times a day, from a terminal and an agent session on her laptop.

**Behaviors:** she directs an agent to make most edits, and reads its diff before each commit. She runs the checks locally only after a push has failed in CI.

**Goals and concerns:**

- **Speed:** land a small change on the day she starts it.
- **Accuracy:** never merge a document that her change made stale.
- **Thoroughness:** have a substantive draft challenged before she adopts it.

**Frustrations:**

- One changed file flags every document anchored to it, and each needs an answer in the same pull request (COR-050 point 6).
- A proposed record cannot be built on until someone accepts it (the acceptance gate).
- A check fails in CI after she pushed, where she could have run it before.

**Quote:** "Tell me before I push, not after."
