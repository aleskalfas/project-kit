---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-06
---

# The analysis template round

The maintainer picks each analysis kind's parts here, one kind at a time, from candidates filled with real pkit examples (#1362).

- **Why:** #1363 declares each kind's structure as data, so its parts are chosen first. The design's first cut is part 8 of the note for #1352, in PR #1353.
- **The order:** the use case, the journey, the actor, the glossary term and the revalidation record.
- **Where the candidates are:** in the folder `2026-10-06-analysis-template-round/` beside this note, one sub-folder per kind and one file per candidate. This note holds the comparison and the recommendation.
- **Why a folder:** the use case's filled candidates alone run to 2,600 words, so five kinds would bury the comparisons. In a file of its own, each candidate also reads exactly as an artefact would.
- **Retiring:** `pkit scratchpad done` moves this note only, so the folder moves beside it by hand. `pkit scratchpad list` and `pkit validate` ignore the folder.
- **Paths:** `SA/` is `.pkit/capabilities/software-analysis/`.
- **Citations:** records, rules and issues by permanent id, files by name, never by line number (RS-WRITE-014, proposed).
- **Reviewed:** by the critic, before the maintainer saw it. Its findings and the answers are in "Review", at the end of each kind.
- **Status:** the use case is fully decided. The other four kinds follow it.

## The use case

The maintainer chose nine parts: the design's five, two of them renamed, three of Cockburn's further parts, and *Assumptions*. The round had recommended the five alone, and its comparison and recommendation stay below as they were made.

### Decided: the use case

The maintainer chose the use case's parts and their labels on 6 October, in comments on PR #1374, and then answered its last two questions. Every question of the use case is now decided. F fills the parts with both examples (`use-case/F-chosen-template.md`).

- **Added, with the maintainer's reasons:**
  - *Other actors*, optional: the other actors who take part, each with what the use case must protect for them. It is Cockburn's stakeholders and interests, added for completeness.
  - *Preconditions*, required: what the system, or an earlier use case, has already made true before the use case starts. A journey's seams need them, since a seam is where one use case's end must meet the next one's start.
  - *Assumptions*, optional: what must also be true for the use case to work, but nothing in the system secures. Each names the record that admits it, and each is a candidate for a check. Question 5 gives the reasons.
  - *Minimal guarantees*, required: what the system still guarantees when the use case ends early or fails. pkit's safety guarantees need a part of their own. It is Cockburn's minimal guarantee, and the round's *Always holds*.
- **Renamed:** *Starts when* is now *Trigger*, and *Done when* is now *Postconditions*, the pair to *Preconditions*.
- **Every label a noun:** the maintainer chose the labels after the parts, in a later comment on the pull request. *Other actors* and *Minimal guarantees* were first *Also involved* and *If it fails*.
- **Otherwise, start small:** any other part is added once real use cases show it recurs.
- **Where each part ships:** with software-analysis, as the round recommended. The maintainer's comments leave that as it was.
- **The actor's voice ships too:** the goal is one sentence in the actor's own voice, as each of an actor's needs is (question 6). It is the mainstream user-story convention, not project-kit's alone. A project that prefers another voice replaces the hint in its own settings.
- **The append-only check:** a check keeps a use case's steps and variants append-only, filed as #1375 (question 4).

**The declaration #1363 takes, in this order:**

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# UC-NNN — <title>` | yes | heading | none, since the stamp writes it | `# UC-007 — Export the report as a file` |
| `goal` | Goal | yes | `sentence` | What the actor wants from this use case, in one sentence in their own voice: start with the verb, with *I* and *my* where they refer to themselves. | Export my report as a file. |
| `other-actors` | Other actors | no | none | Each other actor who takes part, and what this use case must protect for them. | **Auditor** (`ACT-auditor`): each export is logged with who made it. |
| `preconditions` | Preconditions | yes, and `None.` is allowed | none | What the system, or an earlier use case, has already made true before the use case starts. Each is a state, not an event, and no step checks it. Write `None.` when there is none. | The analyst is signed in. |
| `assumptions` | Assumptions | no | none | What must also be true for the use case to work, but nothing in the system secures. Name the record that admits each. | The disk keeps the file as the system wrote it (DEC-003). |
| `trigger` | Trigger | yes | none | The event that starts the use case, and who or what causes it. | The analyst asks to export the report on screen. |
| `main-path` | Main path | yes | `numbered-steps` | Numbered steps from the start to the goal, each saying who does what. | 1. The analyst chooses `Export`. 2. The system writes the report to a file. |
| `variants` | Variants | yes, and `None.` is allowed | `variants` | One for each condition, lettered after the step it branches from. Say what happens instead, and where the path rejoins or ends. Write `None.` when there is none. | 2a. The disk is full. The system says so and writes nothing, and the use case ends. |
| `postconditions` | Postconditions | yes | none | The state that shows the goal is met. | The file holds the whole report. |
| `minimal-guarantees` | Minimal guarantees | yes, and `None.` is allowed | none | What the system still guarantees when the use case ends early or fails. Name the record or code each rests on. Write `None.` when there is none. | A failed export leaves no partial file (DEC-003). |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it.
- **The examples:** one neutral use case runs through them all, the design's export. An auditor and a decision of the example's own complete it.
- **The actor's voice:** the goal's hint names it, and its example is in it (question 6). The voice is the method's now, so it is no project's style that the neutral floor of the design's part 5 keeps out.

**The front matter gains `involves`:**

- **What it holds:** the actors of *Other actors*, by id, as a list, such as `involves: [ACT-merge-authoriser, ACT-ci-pipeline]`. It is absent where the part is.
- **Why data:** a tool takes data only from the front matter (the design's Decided 2). So a check can resolve each id to an actor.
- **An anchor too:** each actor in it is an artefact anchor, as the primary actor is (DEC-001 point 4). A change to one flags the use case.

**Left out, one reason each** (the maintainer's):

- **Scope:** it is always "the system", and the layer shows in the area folder.
- **Level:** the kind implies it.
- **Constraints:** preconditions and postconditions hold them until they recur.
- **Technology and data variations:** variants carry them.
- **Open questions:** they go on the pull request.
- **Frequency and priority:** they are project management's.

**The round's questions:**

1. **Question 1, DEC-001 point 1's parts only:** no. Three parts ship beyond them, and any other waits until real use cases show it recurs. Each later kind is weighed in its turn.
2. **Question 2, *Always holds*:** it comes now, as *Minimal guarantees*, required with `None.` allowed.
3. **Question 3, *Variants* required:** yes, with `None.` allowed, as recommended.
4. **Question 4, the append-only check:** option (a). A check keeps a use case's steps and variants append-only, filed as #1375. It depends on #1364.
5. **Question 5, a fact the use case relies on that the system does not secure:** option (c). It goes in *Assumptions*, a part of its own, and *Preconditions* stay strict.
6. **Question 6, the actor's voice in the goal hint:** option (b). The first-person voice ships with software-analysis for every project, for an actor's needs and a use case's goal.

**What filling F showed:**

- **The landing's precondition:** it sat in A's *Starts when*. A's trigger read "a committed change", which is a state. F moves the state to *Preconditions*, and *Trigger* keeps the event.
- **E's precondition:** none, so the part reads `None.`. Neither example lists "pkit is installed". Every use case would share it, as "the system is running" would.
- **Facts outside the system:** the landing relies on three that no step checks and nothing in the system secures. F lists them under *Assumptions*, each with the record that admits it.
  - **Where `gh` goes:** the maintainer's example. The caller's environment and the working directory's remote decide the target (ADR-061 point 4), and the guard compares directories only (`session_guard.py`).
  - **The title at a queue's merge:** the queue reads the title at the merge, and the landing makes no rule of a title changed since (ADR-061 point 8).
  - **How soon the service shows a change:** the code names it an assumption (`pull_request_landing.py`). ADR-061 point 7 admits that the service may still apply a change two readings did not see.
- **The four questions, applied:** the committed change is a precondition. GitHub as the host is checked, so it stays variant 6e. The three facts above are assumptions.
- **E's assumptions:** none, so E leaves the part out, as it leaves out *Other actors*.
- **The goals, in the voice of question 6:** both already read so, and F keeps them as they are.
  - The landing's starts with *Land*, and says *my change*.
  - E's starts with *Think*. The developer never refers to itself in it, so it needs no *my*.
  - E's repeats one of the developer's needs word for word, and the landing's is the first part of another (`ACT-developer`).
- **Who is involved:** the landing involves four actors, and E involves none, so E shows the part left out.
  - The CI pipeline and the merge authoriser take part in steps 3 and 4.
  - The AI agent takes part where it acts for the developer, as in 2a.
  - The operator answers the guard in 6a, which now names them.
- **An interest with no guarantee:** the merge authoriser's interest rests on a person showing the list, which no check verifies (COR-050 point 3). So *Other actors* states it, and *Minimal guarantees* cannot.
- **Interests that repeat needs:** the CI pipeline's, the merge authoriser's and the operator's restate needs their actors already carry. The round raised this against stakeholders, and the maintainer kept the part for completeness.
- **Minimal guarantees, held to what the records give:** each item cites its record or code, checked against ADR-061, COR-039 and the landing's code.
  - Every merge and enqueue is pinned to the checked head. That does not mean that no unchecked commit merges.
  - Auto-merge is not the landing's request, and a queue may merge a moved head before the next reading. F's items say both.
- **Anchors:** every record and file F cites is among its anchors, so a change to one flags the use case (RS-WRITE-014). The landing gains COR-054, for the CI pipeline's base, and its four involved actors.
- **What F changes from A:** the front matter's `involves` and anchors, the precondition taken out of A's *Starts when*, and 6a naming the operator. *Variants* drops A's instruction line, as D does. The steps and the other variants are A's.
- **Length:** the landing runs to 1,443 words, against A's 960 and B's 1,282. E runs to 333, against 259 in the recommended parts.

**For the build:**

- **The parts (#1363):** the table above, in its order, with each part's hint and example.
- **`involves`, a schema change (#1363 and #1364):** the use case's schema gains it as an optional list of actor ids (`SA/schemas/use-case.schema.json`). The check resolves each id to an actor, and requires each one's artefact anchor as it does for `actor` today (`SA/scripts/_lib/check.py`).
- **The stamp (#1366):** it writes `involves` and each actor's anchor, as it writes the primary actor and its anchor today (`SA/scripts/_lib/stamp.py`).
- **DEC-001 first (#1358):** its point 1 names a use case's parts, and its point 4 names a use case's anchors. The four new parts and `involves` go beyond both, so #1358's refinement says so before any build cites it (core rule 2).
- **A possible form (#1365):** a form could hold the items of *Other actors* to `involves`, as `steps-match-front-matter` holds a journey's steps. The round does not decide it.
- **The append-only check (#1375):** filed on question 4's answer. It compares a use case's steps and variants with the default branch's, and reports one renumbered or removed. It depends on #1364, whose check reads the steps and variants.
- **The actor's voice moves to software-analysis** (question 6). It was project-kit's own rule, RS-ANALYSIS-001, planned in #1368.
  - **The format rule (#1360):** it carries the voice for an actor's needs and a use case's goal.
  - **The declaration (#1363):** the goal's hint and example above. The hint for an actor's `needs` names the same voice, in the actor's round.
  - **The templates (#1366):** rendered from those hints, so every stamped goal and need shows the voice.
  - **#1368 keeps only project-kit's own additions:** the rule on labels, the actors' labels as data, and its edits to `WRITE`. Its rule on the voice goes.
  - **The design note changes with it:** its parts 5 and 9 still give the voice to project-kit's rule set (`2026-10-05-analysis-kind-structure.md`).

### The example

The main example is a real core use case: the developer lands a change on the default branch.

- **The need it serves:** the developer's need to land a change as one squash commit with a conventional title (`ACT-developer`).
- **Why this one:** it crosses three actors and has twenty variants, so it tests every part. It is also heavy on mechanism, so a second, ordinary example checks the recommendation (`use-case/E-second-example.md`).
- **Derived from:**
  - COR-009, for the squash merge, the conventional title and direct work when alone
  - COR-050 points 3, 6 and 12, for the change check and the answers shown before the merge
  - ADR-061 and the CLI reference (`.pkit/cli/README.md`), for the landing command and its ends
  - `src/project_kit/pull_request_landing.py`, for the sequence the landing runs
- **Core only:** no project-management verb appears. Step 2 names no command for opening the pull request, since the core has none.
- **The same in every candidate:** the front matter, the steps and the variants. Only the parts around them differ. F, which came later, also adds to the front matter and names the operator in 6a.

**What the example left unclear.** Each step is written as the records and the CLI reference state it, except step 5 (item 3). The round decides none of these, but item 3 bears on steps 5 to 9, which much of the comparison draws on.

1. **A direct commit is no squash commit.** The developer's need names both paths. COR-009 point 5 allows direct work, and COR-008 makes each commit one logical unit. So variant 2a lands the commits as they were made.
2. **A direct merge does not carry the body.** COR-009 point 2 makes the pull request's body the commit's body. A direct merge passes only the subject until #1220 lands (ADR-061 point 8), and variant 6b says so.
3. **No record has a person run `pkit pull-request land`.** ADR-061 has capability scripts call the command and the release import its module. Only `release merge` lands through `land` today. The command also gives a human output, so step 5 has the developer run it.
4. **The landing's home is provisional.** ADR-061 point 3 is revisited on a core decision about the placement (#1222), and again when a second hosting service is supported. Either would change steps 5 to 9.

### The candidates

Each candidate is complete and filled, as the artefact would read on the default branch. Its id is `UC-xxx`, since the round stamps nothing into `tech-docs/analysis/`.

- **A, today's template** (`use-case/A-todays-template.md`): exactly the parts of `SA/templates/use-case.md`. They are *Goal*, *Starts when*, *Main path*, *Variants* and *Done when*. The template's instruction line under *Variants* stays, as in every artefact filled from it.
- **B, Cockburn's fully dressed form** (`use-case/B-fully-dressed.md`): his template's parts, in his order, adapted only where pkit requires.
  - *Primary actor* is the front matter's `actor`, so the body does not repeat it.
  - The front matter carries the id and the friction block.
  - *Extensions* keep his numbering, a letter after the step and then numbered sub-steps, such as `7a1`.
  - *Goal in context* opens with the one-sentence goal (DEC-001 point 1). Its second sentence is the context his template asks for.
  - *Related information* holds two items, the frequency and the open issues. His template leaves that part to each project.
- **C, Cockburn's casual form** (`use-case/C-casual.md`): the main path as a short story, then the variations in prose. His casual "Buy something" (Use Case 4) is the model.
- **D, the design's first cut:** equal to A in its parts, their order and their labels. It differs from A in three ways, and only the first shows in a filled artefact:
  - no instruction line under *Variants*, so a filled D is A without that line
  - each part stamped with a one-line hint, which the writer replaces
  - every part required and checked, with *Variants* allowed to read `None.`
- **E, a second example in the recommended parts** (`use-case/E-second-example.md`): the developer thinks a question through in a scratchpad note. It is an ordinary use case, with six steps and three variants.
- **F, the chosen template** (`use-case/F-chosen-template.md`): the maintainer's nine parts, filled with both examples, the landing and E. It came after the recommendation, and "Decided: the use case" says what filling it showed.
- **Note:** the brief for this round named A's third part *Steps*. The template's label is *Main path*, and the candidates keep it.

**Sources.** Cockburn's forms and the RUP outline were read from these pages:

- **Fully dressed and casual:** *Writing Effective Use Cases*, pre-publication draft 3 of 21 February 2000 ([extract](https://www.ifi.uzh.ch/dam/jcr:00000000-25a0-3d08-0000-00000ce96422/weuc_extract.pdf)). Its fully dressed template is Use Case 7, and its casual example is Use Case 4.
- **The older template:** Cockburn's "Basic Use Case Template", TR.96.03a, version 2 of 1998 ([page](https://www.cs.otago.ac.nz/coursework/cosc461/uctempla.htm)). It adds priority, performance, frequency, channels, schedule and a failed end condition.
- **RUP:** the use-case specification template ([page](https://www.cin.ufpe.br/~if682/RUP/webtmpl/templates/req/rup_ucspec.htm)). Its parts are a brief description, a basic flow and alternative flows, special requirements, preconditions, postconditions and extension points.
- **Not verified:** the published edition of 2001, whose wording may differ from the draft's. The draft itself names the goal part *Context of use* in its template, and *Goal in Context* in its examples. B takes the second.

### At a glance

B says the most and costs the most, and C cannot be cited. Words are counted in the body, labels included, with the heading and front matter left out.

| Candidate | Parts | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 5: *Goal*, *Starts when*, *Main path*, *Variants*, *Done when* | None marked. Today's check catches a placeholder left in, not a part deleted. | 960 | Over C, steps that can be cited and a stated end | The instruction line under *Variants*, in every artefact |
| B | 12: *Goal in context*, *Scope*, *Level*, *Stakeholders and interests*, *Precondition*, *Minimal guarantees*, *Success guarantees*, *Trigger*, *Main success scenario*, *Extensions*, *Technology and data variations*, *Related information* | None marked. *Related information* holds whatever a project needs. | 1,282 | The scope (GitHub through `gh`), ADR-061 point 5's obligations in one place, four stakeholders' interests, technology variations, open issues | *Goal in context* repeats the goal, and its second sentence repeats the frequency. *Success guarantees* repeat *Done when*. *Level* reads "user goal" in every use case. Two interests repeat actors' needs, and *Open issues* repeat the tracker. |
| C | 2, unlabelled: the story and the variations | None | 351 | Nothing. It reads fastest, as one story. | Nothing, but it drops the step numbers, the outcomes and the end as a part of its own |
| D | 5, as A | All five, *Variants* allowed to read `None.` | 943 | As A, with hints and checks | Nothing |
| F | 9: *Goal*, *Other actors*, *Preconditions*, *Assumptions*, *Trigger*, *Main path*, *Variants*, *Postconditions*, *Minimal guarantees* | All but *Other actors* and *Assumptions*. *Preconditions*, *Variants* and *Minimal guarantees* may read `None.`. | 1,443 | The other actors as data and anchors, the precondition apart from the trigger, three assumptions, and seven guarantees, each with its record or code | Three interests restate actors' needs. *Minimal guarantees* restates ADR-061 point 5's obligations, and *Assumptions* restate what its points 4, 7 and 8 admit. |

**Note:** F came after the recommendation, and its row is added here to compare.

### Fit with pkit

Only A, B and D keep the step numbers that journeys and evidence cite. Most of B's further parts are stable, restate a record, or are watched by no anchor.

- **Steps and variants cited** (DEC-001 point 3):
  - A and D number the steps and letter the variants, as journeys and evidence cite them.
  - B does too, and adds sub-steps such as `7a1`. Evidence cites the extension, `7a`, since a use case's `steps` take a number and letters only (`SA/schemas/revalidation-evidence.schema.json`). That costs B nothing against A.
  - C has no numbers, so neither a journey's seam nor a test run can name a step. As the main form it would break DEC-001 point 3.
- **Anchors:** friction flags the whole use case, never one part, and no artefact records which anchor bears on which part. The table is a reviewer's own mapping, which a reviewer would rebuild each time:

  | Part | The anchor that would flag it |
  |---|---|
  | *Goal*, *Starts when*, B's *Trigger* | `ACT-developer`, whose need the goal serves |
  | *Main path* steps 1 to 4, and their variants | `friction_check.py`, COR-009, COR-050 and COR-055 |
  | *Main path* steps 5 to 9, and their variants | `pull_request_landing.py`, `session_guard.py`, COR-039 and ADR-061 |
  | *Done when*, B's *Success guarantees* | COR-009 |
  | B's *Scope*, *Technology and data variations* | ADR-061, for its point 3 |
  | B's *Minimal guarantees* | ADR-061, for its point 5, and `pull_request_landing.py` |
  | B's *Stakeholders and interests* | ADR-061, COR-050, COR-009 and COR-039, one for each interest. The other actors are not anchored, which DEC-001 point 4 neither asks nor forbids. |
  | B's *Related information* | None. No anchor kind watches an issue. |
  | C's story | Every anchor, on the whole text |
  | F's *Other actors* | Each actor in `involves`, as an artefact anchor |
  | F's *Assumptions* | ADR-061, `session_guard.py` and `pull_request_landing.py` |
  | F's *Minimal guarantees* | ADR-061, COR-039, `pull_request_landing.py` and `session_guard.py` |

- **Quoting code:** A, B and D quote commands, flags and outcomes in backticks, as the analysis-author skill asks. C quotes its commands, but names no outcome, such as `merged` or `dropped`.
- **The one-sentence goal** (DEC-001 point 1):
  - A's and D's *Goal* is one sentence, and D checks it.
  - B's goal part is "a longer statement of the goal, if needed", in the words of Cockburn's 2000 template. A `sentence` form would refuse it unless the goal and the context were split.
  - C has no goal part, and only its title carries the goal, as a phrase.
- **Revalidation:** the steps go stale with the code, and most other parts stay true. Take #1220, which would make a direct merge carry the body:
  - **A and D:** variant 6b goes stale. A reviewer rereads steps 5 to 9 and their variants to find it.
  - **B:** extension 6b2 goes stale, and so do *Open issues*. *Open issues* also go stale whenever an issue closes, and nothing flags that.
  - **C:** one sentence of the third paragraph goes stale, and a reviewer rereads the whole story to find it.
  - **Guarantees:** B's *Minimal guarantees* go stale when ADR-061 point 5 or the landing's code changes. A guarantee over every end also goes stale whenever an end is added.
- **What a script can check:**
  - **A and D:** the heading against the id and title, as today. Then each part present, in order and not empty, and the goal one sentence. Then the steps numbered once each, and each variant after a step of the main path.
  - **B:** the same for its parts. Then *Level* from a closed list, each technology variation after a step, and each sub-step under its extension.
  - **C:** only that text is there.
  - **None of them:** whether "rejoins at step 3" names a step that exists. A later form could check it.
- **The writing rules:**
  - A's instruction line holds a semicolon in every artefact, which RS-WRITE-008 forbids. D drops it.
  - C's paragraphs run to four sentences, the most RS-WRITE-007 allows, and its series stay in sentences where RS-WRITE-003 asks for lists.
  - B's sub-steps keep each sentence short, at the cost of 34 percent more words than A.

### Recommendation

Ship D's five parts, all required, and ship no further part for now.

**Decided otherwise.** The maintainer added three parts and renamed one, as "Decided: the use case" says. This recommendation stays as it was made, and each point the decision turned is marked below.

- **Why the five:** they are DEC-001 point 1's account of a use case, and both examples filled each one without strain. The design's part 8 chose the same.
- **Why no further part ships now:** software-analysis is installed in project-kit alone (the design's Decided 1). An optional part added later fails no artefact, since an optional element is checked only when present (the design's part 1). So a part ships once real use cases show it recurs (COR-007).
- **What was weighed and left out:**
  - **A precondition, *Assumes*:** the main example's one fact, GitHub through `gh`, is checked by the landing, so it is variant 6e. It is also false for variant 2a. E's precondition would be "pkit is installed", true of every use case.
    - **Decided otherwise:** *Preconditions* comes, required, since a journey's seams need it. The landing's committed change, which no step checks, is its one precondition. *Assumptions* comes too, optional, for what no step checks and nothing in the system secures (question 5).
  - **A guarantee over every end, *Always holds*:** the strongest candidate. Question 2 asks about it.
    - **Decided otherwise:** it comes now as *Minimal guarantees*, required, since pkit's safety guarantees need a part of their own.
  - **Scope:** real in pkit, since a use case belongs to the core or to a capability. An area can carry it (`--area`, DEC-001 point 2), and so can the goal's wording.
  - **Level:** DEC-001 names no levels, and a journey already covers a path across use cases. A level would need a rule that DEC-001 lacks.
  - **Stakeholders and interests:** two of the main example's four interests repeat actors' needs, and the steps name the other actors.
    - **Decided otherwise:** they come as *Other actors*, optional and limited to actors, for completeness. The actors are also listed as data in the front matter.
  - **Success guarantees and Trigger:** they are *Done when* and *Starts when*.
  - **Technology and data variations:** a variant holds them, as 6e holds the host.
  - **Related information:** open issues belong to the tracker, which no anchor watches.
  - **The casual form:** journeys and evidence cannot cite a step in it (DEC-001 point 3).
- **Labels:** today's. A project may relabel any part (the design's part 4).
  - **Decided otherwise:** every label a noun. *Starts when* is now *Trigger*, and *Done when* is now *Postconditions*.
- **Ships with:** every part ships with software-analysis. project-kit adds no part of its own for the use case.
- **Note:** project-kit's style still reaches these parts through its rule sets, not as parts. Examples are `WRITE`, and RS-ANALYSIS-001's actor's voice for the goal once it is accepted.
  - **Decided otherwise:** the actor's voice ships with software-analysis, in the goal's hint (question 6).

The declaration #1363 would have taken, in this order, before the table in "Decided: the use case" superseded it:

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# UC-NNN — <title>` | yes | heading | none, since the stamp writes it | `# UC-007 — Export the report as a file` |
| `goal` | Goal | yes | `sentence` | What the actor wants from this use case, in one sentence. | Export the report as a file. |
| `starts-when` | Starts when | yes | none | The event that starts the use case, and who or what causes it. | The analyst asks to export the report on screen. |
| `main-path` | Main path | yes | `numbered-steps` | Numbered steps from the start to the goal, each saying who does what. | 1. The analyst chooses `Export`. 2. The system writes the report to a file. |
| `variants` | Variants | yes, and `None.` is allowed | `variants` | One for each condition, lettered after the step it branches from. Say what happens instead, and where the path rejoins or ends. Write `None.` when there is none. | 2a. The disk is full. The system says so and writes nothing, and the use case ends. |
| `done-when` | Done when | yes | none | The state that shows the goal is met. | The file holds the whole report. |

- **The hints:** each is one line, with short sentences, no semicolon and no project's voice, as the design's part 5 asks. They say what goes in a part, never how to format it (the design's part 2).
- **The examples:** one neutral use case runs through them all, the design's own.
- **What the hints leave out:** two rules today's text carries move elsewhere. The template's instruction line holds the append-only rule, and the skill's *Fill it* list holds the backtick rule. Question 4 asks where the first goes. The backtick rule is a format, so it stays in the skill's walkthrough.

### Questions for the maintainer

Each question is one decision, with a recommendation. The maintainer settled all six on 6 October. Questions 5 and 6 came from filling F.

1. **Does software-analysis ship only DEC-001 point 1's parts, with any further part shipped once real artefacts show it recurs?**
   - **Recommendation:** yes. It settles the use case's further parts now, and the same choice returns for the other four kinds. It reverses nothing, since the design's part 8 left the same parts out.
   - **Else:** each kind weighs each further part on its own, and the use case's open question is *Always holds*.
   - **Decided:** no. The use case ships three parts beyond DEC-001 point 1, and any other waits until real use cases show it recurs.
2. **Does *Always holds* wait, or come now?**
   - **Recommendation:** wait, and revisit once project-kit has real use cases. It recurred in each case traced: the landing, E, where a note is moved and never deleted, and two the critic traced. But its first worked example overclaimed what ADR-061 point 5 gives, and it restates the record it rests on.
   - **Else:** ship it as an optional part, or add it in project-kit's own `structures.yaml`. A project's addition needs a project rule naming it, and binds only at that rule's status (the design's part 4).
   - **Decided:** it comes now, as *Minimal guarantees*, required with `None.` allowed.
3. **Is *Variants* required, with `None.` allowed?**
   - **Recommendation:** yes, for the design's reason: a required part makes the writer consider variants. It differs from *Always holds*, since DEC-001 point 1 names variants.
   - **Else:** *Variants* is optional, and a use case without it passes.
   - **Decided:** yes, as recommended.
4. **Does a check keep steps and variants append-only, in place of the template's instruction line?**
   - **Recommendation:** yes, filed as an issue of its own. The check compares a use case's steps and variants with the base, and reports one renumbered or removed. It reaches the later editor, which is who the rule is for. A hint does not, since the writer deletes it at the first fill.
   - **Else:** the instruction line stays in every artefact, without its semicolon, or the rule lives in DEC-001 point 3 and the skill's *Later* alone.
   - **Decided:** option (a), as recommended. The check is filed as #1375, and depends on #1364.
5. **Does *Preconditions* also hold a fact the use case relies on that the system does not guarantee?**
   - **The case:** the landing relies on `gh` reaching the repository the change was pushed to, as the caller's environment sets it up (ADR-061 point 4). No step checks it, and the chosen hint leaves it out.
   - **Recommendation:** yes. The hint would read "What already holds before the use case starts", and the landing would state the fact. A reader then learns what the use case trusts unchecked.
   - **Else:** the hint stays as chosen, and such a fact goes unstated until a step checks it and a variant can name it.
   - **Decided:** option (c), a part of its own. *Preconditions* stay strict, and such a fact goes in *Assumptions*, optional, right after them.
     - **Why:** the methodologies agree on keeping what is guaranteed apart from what is assumed. Cockburn keeps preconditions to what is guaranteed. Requirements standards list assumptions apart (IEEE 830, ISO/IEC/IEEE 29148 and Volere), and safety cases make assumptions explicit. A part in each use case puts the risk where it is.
     - **The test:** four questions place a fact the use case needs.
       - Does pkit make it true in this use case? Then it is a requirement.
       - Was it made true before the use case starts? Then it is a precondition.
       - Is it checked and reacted to? Then it is a variant.
       - Is it outside the system, and unchecked? Then it is an assumption.
6. **Does the shipped goal hint name the actor's voice?**
   - **The case:** the decision as recorded for this round gives the goal "in the actor's voice". The design keeps the voice as project-kit's own rule, since a voice is a project's style (its part 9, and COR-014).
   - **Recommendation:** no. The shipped hint asks for one sentence, and project-kit's goals keep the voice through RS-ANALYSIS-001.
   - **Else:** the shipped hint names the voice, and the design's parts 5 and 9 change with it.
   - **Decided:** option (b), the shipped hint names the voice. It ships with software-analysis for every project, for an actor's needs and a use case's goal.
     - **Why:** it is the mainstream user-story convention, not project-kit's alone.
     - **Another voice:** a project that prefers one replaces the hint in its own settings.
     - **The build:** the voice moves from #1368 to software-analysis, as "For the build" says.

### Review

The critic reviewed the first draft. Each finding below changed the draft, or is answered here.

| Finding | Answer |
|---|---|
| Red flag: variant 6b sent a direct merge to a queue the base does not have | The code waits by reading, with no hand-off. 6b says so, with its `not-merged` end. |
| Red flag: variant 4a re-authorised without running the checks again | An edited answer is a new commit, so 4a rejoins at step 3. |
| Red flag: B's guarantee "no commit that nobody checked merges" is false for a pull request auto-merge holds | B now says what the landing sends, and states the auto-merge exception (ADR-061 point 5). Question 2 weighs it. |
| Red flag: the only fact for *Assumes* is checked by the landing, false for 2a, and provisional | *Assumes* is dropped. The fact is variant 6e. |
| Red flag: a hint cannot carry the append-only rule to a later editor, and hints carry no format | Question 4 now asks for a check, and the backtick rule stays in the skill. |
| The recommendation reversed the design's part 8 without saying so | The recommendation now confirms part 8, and Question 1 says so. |
| Optional parts cost every stamp two hints to delete | No optional part is recommended. |
| One atypical example | E, an ordinary use case, fills the recommended parts. |
| Step 5 is no record's, and unclear items 3 and 4 misread ADR-061 | Corrected, and the lead says which item bears on the comparison. |
| The example contradicted itself: *Starts when*, 2a's showing, B's branch guarantee | *Starts when* names no branch. 2a shows the list where an agent commits, and B's success guarantee drops the branch. |
| Missing ends | Added: 6e to 6g, 9b to 9d, `not-merged`, `merged-at-another-head`, and 7c's request in place of the merge. 3a no longer forces a rebase. |
| C names no outcome | Said in "Fit with pkit" and "At a glance". |
| B was not anchored to COR-039 | Every candidate now anchors COR-039, since every one describes the guard. |
| The hints added a rule and broke their own examples | The main path's hint says who does what. `None.` is quoted, and *Done when*'s example no longer names a choice that no step makes. |
| Three clauses lacked their verbs (RS-WRITE-009) | Each has its verb. |
| Scope and Level were rejected for reasons that do not hold in pkit | Restated: an area can carry scope, and DEC-001 names no levels. |
| Counter-alternative: one policy for the whole round | Adopted as Question 1. |
| Counter-alternative: a check of step numbers against the base | Adopted as Question 4. |
