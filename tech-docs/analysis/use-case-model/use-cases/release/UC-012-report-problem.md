---
id: UC-012
title: Report a problem with the system, and follow it
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
---

# UC-012 — Report a problem with the system, and follow it

**Goal:** Report a problem with the system, and follow what happens to it.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): composes the report with the adopter through the `report-author` skill. Where the agent runs a report verb with `--yes`, the system stages the report and posts nothing. So the adopter sees every word before the report leaves (ADR-047 point 2).
- **Methodology maintainer** (`ACT-methodology-maintainer`): receives the report, and links each issue that fixes it (UC-013).

**Preconditions:** The adopter's `gh` is signed in to the hosting service.

**Assumptions:**

- The text the adopter writes holds nothing private. The system builds the environment block without paths, and checks only an attached note for home paths (ADR-047 point 2 and `report.py`).

**Trigger:** The adopter hits a problem with the system, or wants the system to change.

**Main path:**

1. The adopter runs `pkit report bug --title "<summary>" --body "<what happened>"` from the project's root.
2. The system composes the report from these parts:
   - a title that opens with `[Bug]` and ends with the project's name
   - a context line naming the project, and its workstream where the project-management capability gives one (ADR-050)
   - the adopter's text
   - an environment block of versions: the tool, the backbone, the adapter, Python, the operating system, and each capability the methodology ships (PRJ-008)
   - a hidden marker of the report's kind
3. The system shows the whole report, and asks `Post as @<login> to <target>?`. The question names the adopter's `gh` identity, and the report target, project-kit's own repository (ADR-047 point 3).
4. The adopter confirms. The system posts the report there as an issue labelled `report:bug`, and prints `[ok] filed: <url>`.
5. Later, the adopter runs `pkit report`. The system lists each report the adopter filed, or had filed for them, with its number, kind, state and title.
6. The adopter runs `pkit report show <number>`. The system shows the report's state, and each issue linked to fix it, with that issue's state. It also shows how many comments the report has, and the latest one's first line.

**Variants:**

- **1a.** The adopter wants a change, or gives free feedback. The adopter runs `pkit report change-request` or `pkit report feedback`, whose titles open with `[CR]` or `[Feedback]`. A change request's text gets the headings `Motivation`, `Desired behaviour` and `Current workaround`, unless it has them.
- **1b.** An AI agent composes the report with the adopter, through the `report-author` skill. The agent runs the verb with `--yes`, and the system stages the report and prints `staged: pkit report submit <id>`. The adopter runs `pkit report submit <id>`, and the path goes on at step 3.
- **1c.** The adopter attaches a scratchpad note with `--scratchpad <slug>`. The system checks the note for home paths, and asks before posting where it finds one. After a complete post, the system moves the note to `reported/` (COR-043 point 3).
- **1d.** The adopter files for another person with `--on-behalf-of @<login>`. The report says it was filed for that person, and that person's `pkit report` lists it, marked `(filed for you)`.
- **1e.** The adopter runs the verb outside a project. The system warns, and marks the project's versions in the environment block `NOT COLLECTED`. The path goes on at step 3.
- **2a.** The project declares no name. The system asks for one once, offering the remote repository's name, and offers to save the answer in the project's settings (ADR-050 point 1).
- **2b.** The project has capabilities of its own. The environment block counts them, and leaves out their names unless `--include-private` asks for them.
- **3a.** `gh` is not signed in, or the adopter passes `--url`. The system prints a prefilled link to a new issue, and warns that the browser's signed-in account files it. The adopter files the report in the browser, and the path goes on at step 5.
- **3b.** On the path of 3a, the report is longer than a link can carry, 6000 characters. The system refuses the link, naming the ways that remain, and the use case ends.
- **4a.** The adopter declines. The system posts nothing, and prints the prefilled link where the report fits one. The use case ends.
- **4b.** `gh` fails to post the report. The system prints the prefilled link instead, or stages the report for `pkit report submit <id>` where the report is too long for a link. The use case ends.
- **5a.** The adopter passes `--tree`. The system lists, under each report, the issues linked to fix it, with their states.
- **5b.** `gh` is not signed in. The system prints a link to the adopter's issues on the report target instead.

**Postconditions:** The report is an issue on project-kit's repository, with the adopter's versions attached. The adopter sees its state, and each issue linked to fix it, from their own project.

**Minimal guarantees:**

- No report is posted until a person has seen it whole and confirmed it, with its target and the identity it posts as. Run with `--yes`, a report verb only stages the report, and `pkit report submit` refuses `--yes` (ADR-047 point 2).
- The environment block names no path. It leaves out the names of the project's own capabilities unless `--include-private` asks for them (PRJ-008 and `environment.py`).
- A scratchpad note moves to `reported/` only after a complete post. So a browser filing or a failed post never marks the note sent (COR-043 point 3).
