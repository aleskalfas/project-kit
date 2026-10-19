---
id: ACT-developer
name: Developer
status: active
needs:
  - Record my decisions beside the methodology's, and build only on accepted ones.
  - Author and extend my project's rule sets without editing the ones that ship with the system.
  - Think a question too big for a decision through in a scratchpad note, and retire the note once it has produced something.
  - Say what each of my documents rests on, so a change there reaches me.
  - Answer what my change made stale, letting an agent write the answers my change owes and a reviewer other than that agent check them.
  - Know before I push that my change passes the checks my project gates its merges on.
  - Have a substantive draft challenged before I adopt it, and have my diff checked against the methodology's conventions before I commit it.
  - Land my change on the default branch as one squash commit with a conventional title, through a pull request or directly when I work alone.
  - Turn recurring work into my project's own skill or agent, designing its dialogue as a storyboard first.
  - Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.
  - Declare what my change means for the next release, in changesets naming what it moves, the backbone or a component, and the segment I judge.
  - Resolve what the default branch left out of date, knowing for each debt the change it came from.
  - File a Task under its parent, with its title and the sections its body needs checked as it is filed.
  - Move my issue through its lifecycle, with each move checked and the moves that need my authorisation never made without it.
  - Have the reviewer agents my change requires review my pull request, each verdict standing only while I change nothing its reviewer checks.
  - Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.
  - Revalidate the analysis after a change, from an agent's proposed outcome for each flagged artefact, and never rewrite the analysis to match broken code.
  - Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.
  - Free the ids of artefacts nothing cites, such as an abandoned pilot, so new artefacts may take those ids again.
  - Write a page for the reader it names, with anchors that ground each statement it makes.
  - Have the fix for a stale page proposed with its evidence, and review the fix before it is applied.
  - Have a page read as its declared reader would read it, each finding citing the rule the page breaks.
  - Ground each claim about an outside fact in a recorded excerpt of its source, with each citation checked against the evidence records.
  - Record a demo of my command line by running an executable storyboard, a document people read as it stands.
pkit:
  friction:
    anchors:
      record:
        - COR-009
        - ADR-061#3
        - software-engineering:DEC-001#1
        - software-engineering:DEC-001#2
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#3
        - COR-050#6
        - COR-050#9
        - project-management:DEC-010
        - project-management:DEC-011
        - project-management:DEC-006
        - project-management:DEC-026
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - project-management:DEC-032#D4
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#6
        - software-analysis:DEC-001#9
        - living-docs:DEC-001#3
        - living-docs:DEC-001#4
        - living-docs:DEC-001#5
        - living-docs:DEC-001#6
        - evidence:DEC-001
        - evidence:DEC-002
        - evidence:DEC-003
        - demo-recording:DEC-001
        - demo-recording:DEC-002#3
    revalidated:
      at: 2026-10-19T08:41:07Z
      outcome: unchanged
      unchanged-because: "software-analysis DEC-001 point 5 gains a paragraph: its agent is also the fixer of its types, which a command may start where the project granted it, and in such a run it judges only through the capability's own reading and leaves each answer as data for a person. The developer's need to revalidate from an agent's proposed outcome, never rewriting the analysis to match broken code, holds in a session and in such a run alike."
---

# ACT-developer — Developer

The person who builds: decisions, rules, notes, code and its documentation, one change at a time.

- **Occasions:** for every change, and again when some work recurs often enough to deserve tooling of its own.
- **Context:** the change. They direct agents to make it.
- **Core:** whatever tracks the work, every change passes the acceptance gate and the friction check, and lands as COR-009 sets out. That the backbone itself lands pull requests is provisional (ADR-061 point 3, raised as #1222).
- **Note:** a work tracker's view of this role (project-management's "Implementer") comes with that capability.
