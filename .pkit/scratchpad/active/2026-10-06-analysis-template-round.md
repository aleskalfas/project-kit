---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-06
---

# The analysis template round

The maintainer picks each analysis kind's parts here, one kind at a time, from candidates filled with one real pkit example (#1362).

- **Why:** #1363 declares each kind's structure as data, so its parts are chosen first. The design's first cut is part 8 of the note for #1352, in PR #1353.
- **The order:** the use case, the journey, the actor, the glossary term and the revalidation record.
- **Where the candidates are:** in the folder `2026-10-06-analysis-template-round/` beside this note, one sub-folder per kind and one file per candidate. This note holds the comparison and the recommendation.
- **Why a folder:** the use case's filled candidates alone run to 2,100 words, so five kinds would bury the comparisons. In a file of its own, each candidate also reads exactly as an artefact would.
- **Retiring:** `pkit scratchpad done` moves this note only, so the folder moves beside it by hand.
- **Paths:** `SA/` is `.pkit/capabilities/software-analysis/`.
- **Citations:** records, rules and issues by permanent id, files by name, never by line number (RS-WRITE-014, proposed).
- **Status:** the use case waits for the maintainer's picks. The other four kinds follow it.

## The use case

Today's five parts hold up, and filling the example showed two facts they have no place for. One is what must be true before the use case starts, and the other is what holds however it ends.

### The example

The example is a real core use case: the developer lands a change on the default branch.

- **The need it serves:** the developer's need to land a change as one squash commit with a conventional title (`ACT-developer`).
- **Why this one:** its main path crosses three actors, and its many variants test every part.
- **Derived from:**
  - COR-009, for the squash merge, the conventional title and direct work when alone
  - COR-050 points 3, 6 and 12, for the change check and the answers shown before the merge
  - ADR-061, for the landing command, and the CLI reference (`.pkit/cli/README.md`) for its outcomes
  - `src/project_kit/pull_request_landing.py`, for the sequence the landing runs
- **Core only:** no project-management verb appears. Step 2 names no command for opening the pull request, since the core has none.
- **The same in every candidate:** the front matter, the steps and the variants. Only the parts around them differ.

**What the example left unclear.** Each step is written as the records state it. These questions are about pkit, not the template, so the round does not decide them:

1. **A direct commit is no squash commit.** The developer's need names both paths. COR-009 point 5 allows direct work, and COR-008 makes each commit one logical unit. So variant 2a lands the commits as they were made.
2. **A direct merge does not carry the body.** COR-009 point 2 makes the pull request's body the commit's body. A direct merge passes only the subject until #1220 lands (ADR-061 point 8), and variant 6b says so.
3. **Is `pkit pull-request land` meant for a person?** The CLI reference describes it for callers: project-management's verbs and `release merge`. It also gives a human output, so step 5 has the developer run it.
4. **The landing's home is provisional.** The backbone lands on GitHub alone until a core decision (ADR-061 point 3, #1222). That decision would change the use case.

### The candidates

Each candidate is complete and filled, as the artefact would read on the default branch. Its id is `UC-xxx`, since the round stamps nothing into `tech-docs/analysis/`.

- **A, today's template** (`use-case/A-todays-template.md`): exactly the parts of `SA/templates/use-case.md`. They are *Goal*, *Starts when*, *Main path*, *Variants* and *Done when*. The template's instruction line under *Variants* stays, as in every artefact filled from it.
- **B, Cockburn's fully dressed form** (`use-case/B-fully-dressed.md`): his template's parts, in his order, adapted only where pkit requires.
  - *Primary actor* is the front matter's `actor`, so the body does not repeat it.
  - The front matter carries the id and the friction block.
  - *Extensions* keep his numbering, a letter after the step and then numbered sub-steps, such as `7a1`.
  - *Goal in context* opens with the one-sentence goal (DEC-001 point 1). Its second sentence is the context his template asks for.
  - *Related information* holds what this use case needs, its frequency and its open issues. His template leaves that part to each project.
- **C, Cockburn's casual form** (`use-case/C-casual.md`): the main path as a short story, then the variations in prose. His casual "Buy something" (Use Case 4) is the model.
- **D, the design's first cut:** equal to A in its parts, their order and their labels. It differs from A in three ways, and only the first shows in a filled artefact:
  - no instruction line under *Variants*, so a filled D is A without that line
  - each part stamped with a one-line hint, which the writer replaces
  - every part required and checked, with *Variants* allowed to read `None.`
- **Note:** the brief for this round named A's third part *Steps*. The template's label is *Main path*, and the candidates keep it.

**Sources.** Cockburn's forms and the RUP outline were read from these pages:

- **Fully dressed and casual:** *Writing Effective Use Cases*, pre-publication draft 3 of 21 February 2000 ([extract](https://www.ifi.uzh.ch/dam/jcr:00000000-25a0-3d08-0000-00000ce96422/weuc_extract.pdf)). Its fully dressed template is Use Case 7, and its casual example is Use Case 4.
- **The older template:** Cockburn's "Basic Use Case Template", TR.96.03a, version 2 of 1998 ([page](https://www.cs.otago.ac.nz/coursework/cosc461/uctempla.htm)). It adds priority, performance, frequency, channels and schedule.
- **RUP:** the use-case specification template ([page](https://www.cin.ufpe.br/~if682/RUP/webtmpl/templates/req/rup_ucspec.htm)). Its parts are a brief description, a basic flow and alternative flows, special requirements, preconditions, postconditions and extension points.
- **Not verified:** the published edition of 2001, whose wording may differ from the draft's. The draft itself names the goal part *Context of use* in its template, and *Goal in Context* in its examples.

### At a glance

B says the most and costs the most, and C cannot be cited. Words are counted in the body, labels included, with the heading and front matter left out.

| Candidate | Parts | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 5: *Goal*, *Starts when*, *Main path*, *Variants*, *Done when* | None marked. Today's check catches a placeholder left in, not a part deleted. | 732 | Over C, steps that can be cited and a stated end | The instruction line under *Variants*, in every artefact |
| B | 12: *Goal in context*, *Scope*, *Level*, *Stakeholders and interests*, *Precondition*, *Minimal guarantees*, *Success guarantees*, *Trigger*, *Main success scenario*, *Extensions*, *Technology and data variations*, *Related information* | None marked. *Related information* holds whatever a project needs. | 1,019 | The precondition (GitHub through `gh`), ADR-061 point 5's obligations in one place, other actors' interests, technology variations, open issues | *Goal in context* repeats the goal, and its second sentence the frequency. *Success guarantees* repeat *Done when*. *Scope* and *Precondition* both say GitHub. *Level* reads "user goal" in every use case. The interests repeat the actors' needs, and *Open issues* the tracker. |
| C | 2, unlabelled: the story and the variations | None | 341 | Nothing. It reads fastest, as one story. | Nothing, but it drops the step numbers and the end as a part of its own |
| D | 5, as A | All five, *Variants* allowed to read `None.` | 715 | As A, with hints and checks | Nothing |

### Fit with pkit

Only A, B and D keep the step numbers that journeys and evidence cite. Most of B's extra parts are stable, or watched by no anchor.

- **Steps and variants cited** (DEC-001 point 3):
  - A and D number the steps and letter the variants, as journeys and evidence cite them.
  - B does too, and adds sub-steps such as `7a1`. Evidence cannot cite a sub-step, since a use case's `steps` take a number and letters only (`SA/schemas/revalidation-evidence.schema.json`).
  - C has no numbers, so neither a journey's seam nor a test run can name a step. As the main form it would break DEC-001 point 3.
- **Anchors:** friction flags the whole use case, never one part. Which anchor would flag each part tells a reviewer where to look first:

  | Part | The anchor that would flag it |
  |---|---|
  | *Goal*, *Starts when*, B's *Trigger* | `ACT-developer`, whose need the goal serves |
  | *Main path* steps 1 to 4, and their variants | `friction_check.py`, COR-009, COR-050 and COR-055 |
  | *Main path* steps 5 to 9, and their variants | `pull_request_landing.py`, `session_guard.py` and ADR-061 |
  | *Done when*, B's *Success guarantees* | COR-009 |
  | B's *Scope*, *Precondition*, *Technology and data variations* | ADR-061, for its point 3 |
  | B's *Minimal guarantees* | ADR-061, for its point 5, and `pull_request_landing.py` |
  | B's *Stakeholders and interests* | In part. COR-009 and COR-050 would flag two interests, but the use case anchors neither the other actors nor COR-039 (DEC-001 point 4). |
  | B's *Related information* | None. No anchor kind watches an issue. |
  | C's story | Every anchor, on the whole text |

- **Quoting code:** every candidate quotes commands, flags and outcomes in backticks, as the analysis-author skill asks. In C they sit inside long sentences, where a reviewer finds them more slowly.
- **The one-sentence goal** (DEC-001 point 1):
  - A's and D's *Goal* is one sentence, and D checks it.
  - B's *Goal in context* is "a longer statement of the goal, if needed", in Cockburn's words. A `sentence` form would refuse it unless the goal and the context were split.
  - C has no goal part, and only its title carries the goal, as a phrase.
- **Revalidation:** the steps go stale with the code, and most other parts stay true. Take #1220, which would make a direct merge carry the body:
  - **A and D:** variant 6b goes stale. A reviewer rereads steps 5 to 9 and their variants to find it.
  - **B:** extension 6b2 goes stale, and so does *Open issues*. *Open issues* also goes stale whenever an issue closes, and nothing flags that.
  - **C:** one sentence of the third paragraph goes stale, and a reviewer rereads the whole story to find it.
  - **Guarantees:** B's *Minimal guarantees* go stale only when ADR-061 point 5 changes, and its record anchor flags that.
- **What a script can check:**
  - **A and D:** the heading against the id and title, as today. Then each part present, in order and not empty, and the goal one sentence. Then the steps numbered once each, and each variant after a step of the main path.
  - **B:** the same for its parts. Then *Level* from a closed list, each technology variation after a step, and each sub-step under its extension.
  - **C:** only that text is there.
  - **None of them:** whether "rejoins at step 3" names a step that exists. A later form could check it.
- **The writing rules:**
  - A's instruction line holds a semicolon in every artefact, which RS-WRITE-008 forbids. D drops it.
  - C's paragraphs run to four sentences, the most RS-WRITE-007 allows, and its series stay in sentences where RS-WRITE-003 asks for lists.
  - B's sub-steps keep each sentence short, at the cost of 39 percent more words than A.

### Recommendation

Keep D's five parts as they are, and add two optional parts from Cockburn's form, *Assumes* and *Always holds*.

- **Why the five stay required:** they are DEC-001 point 1's account of a use case, and the example filled each one.
- **Why *Assumes*:** A says nowhere that the landing needs GitHub and `gh`. B's *Precondition* said it, and the RUP outline has preconditions too.
- **Why *Always holds*:** B's *Minimal guarantees* gathered ADR-061 point 5's obligations, which A spreads over steps 6 to 9 and four variants. Many use cases have none, so it is optional.
- **Why not the rest of B:**
  - *Scope:* the system is the project's software in every use case. Where a use case reaches less, *Assumes* says so.
  - *Level:* every use case is at the user-goal level, and a journey plays the summary level's part.
  - *Stakeholders and interests:* the actors' needs hold the interests, and the steps name the other actors.
  - *Success guarantees* and *Trigger:* they are *Done when* and *Starts when*.
  - *Technology and data variations:* a variant or *Assumes* holds them.
  - *Related information:* open issues belong to the tracker, which no anchor watches.
- **Why not C:** journeys and evidence cannot cite a step in it (DEC-001 point 3).
- **Labels:** today's, so no artefact is relabelled. A project may relabel any part (the design's part 4).
- **Ships with:** every part ships with software-analysis, since each is general use-case practice. project-kit adds no part of its own.
- **Note:** project-kit's style still reaches these parts through its rule sets, not as parts. Examples are `WRITE`, and RS-ANALYSIS-001's actor's voice for the goal once it is accepted.

The declaration #1363 would take, in this order:

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# UC-NNN — <title>` | yes | heading | none, since the stamp writes it | `# UC-007 — Export the report as a file` |
| `goal` | Goal | yes | `sentence` | What the actor wants from this use case, in one sentence. | Export the report as a file. |
| `assumes` | Assumes | no | none | What must already be true when the use case starts. The use case does not check it. | The report has finished generating. |
| `starts-when` | Starts when | yes | none | The event that starts the use case, and who or what causes it. | The analyst asks to export the report on screen. |
| `main-path` | Main path | yes | `numbered-steps` | Numbered steps from the start to the goal, each one action by an actor or the system. Quote commands and messages in backticks. Add steps and variants, never renumber them. | 1. The analyst chooses `Export`. 2. The system writes the report to a file. |
| `variants` | Variants | yes, and `None.` is allowed | `variants` | One per condition, lettered after the step it branches from. Say what happens instead, and where the path rejoins or ends. Write None. when there is none. | 2a. The disk is full. The system says so and writes nothing, and the use case ends. |
| `done-when` | Done when | yes | none | The state that shows the goal is met. | The file is saved where the analyst chose. |
| `always-holds` | Always holds | no | none | What stays true however the use case ends, on the main path or a variant. | No half-written file is left behind. |

- **The hints:** each is one line, short sentences, no semicolon and no project's voice, as the design's part 5 asks. The examples follow one neutral use case, the design's own.
- **Where today's guidance goes:** the instruction line's append-only rule and the skill's backtick rule move into the *Main path* hint. Question 4 asks about that.

### Questions for the maintainer

Each question is one decision, with a recommendation.

1. **Does *Assumes* ship with software-analysis, as an optional part?**
   - **Recommendation:** yes. Cockburn's and RUP's forms both have preconditions, and the example's GitHub-only limit had no other home in A.
   - **Else:** project-kit adds it in its own `structures.yaml`, and other projects go without it.
2. **Does *Always holds* ship with software-analysis, as an optional part?**
   - **Recommendation:** yes. Only Cockburn's form has it, but it gathered the landing's safety obligations in three lines.
   - **Else:** project-kit adds it in its own `structures.yaml`, or the obligations stay spread over the steps.
3. **Is *Variants* required, with `None.` allowed?**
   - **Recommendation:** yes, as the design's first cut has it. The example's fourteen variants held most of what ADR-061 decides, and an optional part invites leaving them out.
   - **Else:** *Variants* is optional, and a use case without it passes.
4. **Does the *Main path* hint carry the append-only rule and the backtick rule?**
   - **Recommendation:** yes. Today the template's instruction line carries the first, and the skill's *Fill it* list the second. The design removes both, and the hint is the one place every writer reads.
   - **Else:** the append-only rule stays in DEC-001 and the skill's *Later* alone, and the backtick rule has no home.
