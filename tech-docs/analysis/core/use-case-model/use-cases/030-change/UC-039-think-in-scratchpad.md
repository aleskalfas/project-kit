---
id: UC-039
title: Think a question through in a scratchpad note, and retire it
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
  - ACT-operator
requirements:
  - REQ-002
  - REQ-005
  - REQ-012
after:
  - [UC-014, UC-049]
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
  - at: 7
    issue: "#1765"
    record: ADR-034#1
  - at: "5b"
    issue: "#1765"
    record: ADR-034#1
  - at: "6a"
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scratchpads.py
        - src/project_kit/cli.py
        - .pkit/scratchpad/README.md
        - .pkit/skills/core/scratchpad-author.md
      record:
        - COR-012
        - COR-043#1
        - COR-043#2
        - COR-043#3
        - COR-043#4
        - COR-043#5
        - ADR-034#1
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - ACT-operator
        - REQ-002
        - REQ-005
        - REQ-012
    revalidated:
      at: 2026-10-24T03:45:02Z
      outcome: unchanged
      unchanged-because: The change rewords only the help of `pkit release merge` in cli.py, which this artefact does not describe.
---

# UC-039 — Think a question through in a scratchpad note, and retire it

**Goal:** Think a question too big for a decision through in a scratchpad note, and retire the note once it has produced something.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): starts the note through the `scratchpad-author` [skill](../../../glossary.md#term-skill--skill), which pairs with the [stamp](../../../glossary.md#term-stamp--stamp).
- **Operator** (`ACT-operator`): is asked before a command of this use case writes in another repository than the session's own. So no such write happens silently (REQ-012).

**Preconditions:** **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:**

- A note sent upstream as a [report](../../../glossary.md#term-report--report) is not edited afterwards, and further thinking goes in a new note. Nothing stops an edit, and a listing only warns of one (COR-043 [point](../../../glossary.md#term-point--point) 4).

**Trigger:** A question is too large for a [decision record](../../../glossary.md#term-decision-record--decision-record) yet, and its design space needs mapping first (COR-012).

**Main path:**

1. The developer runs `pkit new scratchpad <slug>`, or an AI agent runs it through the `scratchpad-author` [skill](../../../glossary.md#term-skill--skill).
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit new scratchpad` runs no such check, and writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the slug is kebab-case, and that no note in any state folder holds it. It stamps `.pkit/scratchpad/active/<YYYY-MM-DD>-<slug>.md`, dated today, and prints `Stamped: <path>`.
4. The note's front matter names its author, as git gives it, and the day it started. Its body opens with a title drawn from the slug. It has no status field, since the folder it lies in is its state (COR-012).
5. The developer writes the note's title, explores the question in its body, and commits the note.
6. Once the note's content lives in other [artefacts](../../../glossary.md#term-artefact--artefact), such as a [decision record](../../../glossary.md#term-decision-record--decision-record), the developer runs `pkit scratchpad done <slug> --produced <ref>`. Each `--produced` names one artefact the note fed.
7. At its entry, `pkit scratchpad done` checks the repository as step 2 does (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit scratchpad done` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

8. The system moves the note to `done/`, and adds `retired`, with today's date, and `produced`, with each reference, to its front matter. It prints `Moved: <from> -> <to>`.

**Variants:**

- **1a.** The developer passes `--dry-run`. The [system](../../../glossary.md#term-system--system) prints `Would stamp: <path>`, and writes nothing. `pkit scratchpad done` and `drop` take the flag too, and print `Would move: <from> -> <to>`.
- **3a.** The slug is not kebab-case, or a note in any state folder holds it. The system refuses and writes nothing, and the path rejoins at step 1.
- **3b.** `.pkit/scratchpad/active/` does not exist. The system refuses, naming `pkit init`, and writes nothing. The use case ends.
- **5a.** The note is sent upstream as a [report](../../../glossary.md#term-report--report). The report's command moves the note to `reported/` only on a successful post. It records the issue, the date and a hash of the file as sent (COR-043 points 2 and 3).
- **5b.** The developer posted the report outside the tooling, such as in a browser. The developer runs `pkit scratchpad reported <slug> <ref>`, which checks the repository as step 2 does. The system moves the note to `reported/` with the same record (COR-043 [point](../../../glossary.md#term-point--point) 3).

> [!WARNING]
> **Not built yet:** `pkit scratchpad reported` runs no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **5c.** The developer runs `pkit scratchpad list`. The system lists the notes by state, and writes nothing (REQ-005). For each reported note, it reads each issue's state live, and shows a state it cannot read as unknown (COR-043 point 5).
- **5d.** On the path of 5c, a reported note's file differs from the hash recorded when it was sent. The listing marks it `[modified since reported]`, and stops nothing (COR-043 point 4).
- **5e.** On the path of 5c, every issue of a reported note is closed. The listing names the `pkit scratchpad done` command that retires the note, and never retires it itself (COR-043 point 5).
- **5f.** On the path of 5b, the note lies in `reported/` already, and the run names an issue not yet recorded. The system adds that issue, and records the file's hash again. So the listing no longer marks an edit made before that run (`scratchpads.py`).
- **6a.** The line of thought did not pan out. The developer says why at the end of the note's body, and runs `pkit scratchpad drop <slug>`, which checks the repository as step 2 does. The system moves the note to `dropped/`, adding `retired` and no `produced`.

> [!WARNING]
> **Not built yet:** `pkit scratchpad drop` runs no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **6b.** The note lies in `reported/`, as 5a or 5b left it. The system retires it from there the same way, and removes `reported/` once it is empty (COR-043 points 1 and 2).
- **8a.** No active or reported note matches the slug, or a note of that name lies in the target folder already. The system refuses and writes nothing, and the path rejoins at step 6.

**Postconditions:** The note lies in `done/`, naming the [artefacts](../../../glossary.md#term-artefact--artefact) it produced, or in `dropped/`, saying why the line of thought stopped. It stays in the [project](../../../glossary.md#term-project--project) as the record of how the question was explored.

**Minimal guarantees:**

- [Sync](../../../glossary.md#term-sync--sync) never writes a [scratchpad note](../../../glossary.md#term-scratchpad-note--scratchpad-note), which is the [project](../../../glossary.md#term-project--project)'s own (`.pkit/scratchpad/README.md` and REQ-002).
- No tool retires a note on its own: a listing only names the command that retires it (COR-043 [point](../../../glossary.md#term-point--point) 5).
- A refused [stamp](../../../glossary.md#term-stamp--stamp) or move leaves every note as it was (`scratchpads.py`).
- `pkit scratchpad list` writes nothing, and never shows an issue it could not read as closed (COR-043 point 5 and REQ-005).
