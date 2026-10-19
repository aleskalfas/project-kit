---
id: UC-012
title: Report a problem with the system, and follow the report
status: active
actor: ACT-adopter
other-actors:
  - ACT-ai-agent
  - ACT-methodology-maintainer
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/report.py
        - src/project_kit/environment.py
        - src/project_kit/report_context.py
        - src/project_kit/cli.py
        - .pkit/skills/core/report-author.md
      record:
        - PRJ-008
        - ADR-047#2
        - ADR-047#3
        - ADR-050#1
        - ADR-050#2
        - COR-043#3
      artefact:
        - ACT-adopter
        - ACT-ai-agent
        - ACT-methodology-maintainer
    revalidated:
      at: 2026-10-19T08:30:02Z
      outcome: unchanged
      unchanged-because: This change adds the pkit agents run command to cli.py. The pkit report verbs, and how a report is staged and submitted, are untouched.
---

# UC-012 — Report a problem with the system, and follow the report

**Goal:** Report a problem with the system, and follow what happens to it.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): composes the report with the adopter through the `report-author` skill. Where the agent runs a report verb with `--yes`, the system stages the report and posts nothing. So the adopter sees every word before the report leaves (ADR-047 point 2).
- **Methodology maintainer** (`ACT-methodology-maintainer`): receives the report, and links each tracked fix to it (UC-013).

**Preconditions:** None.

**Assumptions:**

- The text the adopter writes holds nothing private. The system builds the environment block without paths, and checks only an attached note for home paths (ADR-047 point 2 and `report.py`).

**Trigger:** The adopter hits a problem with the system, or wants the system to change.

**Main path:**

1. The adopter runs `pkit report bug --title "<summary>" --body "<what happened>"` from the project's root.
2. The system composes the report from these parts:
   - a title that opens with `[Bug]`, and ends with the project's name where the system finds one
   - a context line naming the project, and its workstream where the project-management capability gives one (ADR-050)
   - the adopter's text
   - an environment block, which holds no path (PRJ-008):
     - the versions of pkit itself, the backbone, Python and each installed capability the system ships
     - the adapter's name and the operating system
   - a hidden marker of the report's kind
3. With `gh` signed in, the system shows the whole report and asks `Post as @<login> to <target>?`. The question names the adopter's `gh` identity, and the report target, project-kit's own repository (ADR-047 point 3).
4. The adopter confirms. The system posts the report there as an issue, and prints `[ok] filed: <url>`. The issue carries the label `report:bug` only where the adopter may set labels on the report target. The hidden marker names the kind either way (`report.py`).
5. Later, the adopter runs `pkit report`. The system lists each report the adopter filed, or another person filed for them (1d), with its number, kind, state and title.
6. The adopter runs `pkit report show <number>`. The system shows the report's state, and each tracked fix with that fix's state. It also shows how many comments the report has, and the latest one's first line.

**Variants:**

- **1a.** The adopter wants a change, or gives free feedback. The adopter runs `pkit report change-request` or `pkit report feedback`, whose titles open with `[CR]` or `[Feedback]`. A change request's text gets the headings `Motivation`, `Desired behaviour` and `Current workaround`, unless it has them.
- **1b.** An AI agent composes the report with the adopter, through the `report-author` skill. The agent runs the verb with `--yes`, and the system stages the report and prints `staged: pkit report submit <id>`. The adopter runs `pkit report submit <id>`, and the path goes on at step 3.
- **1c.** The adopter attaches a scratchpad note with `--scratchpad <slug>`. The system checks the note for home paths, and asks before posting where the system finds one. After a complete post, the system moves the note to `reported/` (COR-043 point 3).
- **1d.** The adopter files for another person with `--on-behalf-of @<login>`. The report says it was filed for that person, and that person's `pkit report` lists it, marked `(filed for you)`.
- **1e.** The adopter runs the verb outside a project. The system warns, and marks the project's half of the environment block `NOT COLLECTED`. The path goes on at step 3.
- **2a.** The project declares no name, on the path that posts through `gh`. The system asks for one, offering the remote repository's name, and offers to save the answer in the project's settings. Until the answer is saved, the system asks at each report (ADR-050 point 1). On any other path, the system takes the remote repository's name without asking.
- **2b.** The project has capabilities the system does not ship, such as the project's own. The environment block counts them, and leaves out their names unless `--include-private` asks for them.
- **3a.** `gh` is not signed in, or the adopter passes `--url`. The system prints a prefilled link to a new issue, and warns that the browser's signed-in account files it. With a note attached, the output ends with `pkit scratchpad reported <slug> <issue-ref>`, the command that moves the note once the report is filed (COR-043 point 3). The adopter files the report in the browser, and the path goes on at step 5.
- **3b.** On the path of 3a, the report is longer than a link can carry, 6000 characters. The system refuses the link, naming the ways that remain, and the use case ends.
- **4a.** The adopter declines. The system posts nothing, and prints the prefilled link where the report fits one. The use case ends.
- **4b.** `gh` fails to post the report. The system prints the prefilled link instead, or stages the report for `pkit report submit <id>` where the report is too long for a link. The use case ends.
- **4c.** The issue is posted, but the comment carrying the rest of a long attached note fails. The system moves no note, names the issue, and prints how to finish by hand. The use case ends.
- **5a.** The adopter passes `--tree`. The system lists, under each report, its tracked fixes with their states.
- **5b.** `gh` is not signed in. The system prints a link to the adopter's issues on the report target instead.

**Postconditions:** The report is an issue on project-kit's repository, with the adopter's versions attached. The adopter sees the report's state, and each tracked fix, from their own project.

**Minimal guarantees:**

- No report is posted until a person has seen it whole and confirmed it, with its target and the identity it posts as. Run with `--yes`, a report verb only stages the report, and `pkit report submit` refuses `--yes` (ADR-047 point 2).
- The environment block names no path. It leaves out the names of capabilities the system does not ship, unless `--include-private` asks for them (PRJ-008 and `environment.py`).
- A report command moves a scratchpad note to `reported/` only after a complete post. After a browser filing or a failed post, the note stays where it was until someone runs `pkit scratchpad reported` (COR-043 point 3).
