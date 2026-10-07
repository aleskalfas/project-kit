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
- **Status:** the use case and the journey are fully decided, and the actor waits for the maintainer's answers. The glossary term and the revalidation record follow.

## The use case

The maintainer chose nine parts: the design's five, two of them renamed, three of Cockburn's further parts, and *Assumptions*. The round had recommended the five alone, and its comparison and recommendation stay below as they were made.

### Decided: the use case

The maintainer chose the use case's parts and their labels on 6 October, in comments on PR #1374, and then answered its last two questions. Every question of the use case is now decided. F fills the parts with both examples (`use-case/F-chosen-template.md`).

- **Added, with the maintainer's reasons:**
  - *Other actors*, optional: the other actors who take part, each with what the use case must protect for them. It is Cockburn's stakeholders and interests, added for completeness.
  - *Preconditions*, required: what the system, or an earlier use case, has already made true before the use case starts. A journey's seams need them, since a seam is where one use case's end must meet the next one's start.
    - **The reason changed** with the journey's question 2. Journeys carry their own hand-overs, and the part records the rare state an earlier use case set up that nothing checks again.
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
| `goal` | Goal | yes | `sentence` | What the actor wants from this use case, in one sentence in their own voice. Start with the verb, with *I* and *my* where they refer to themselves. | Export my report as a file. |
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
- **The goal's hint, split:** as one sentence it ran to 28 words, over RS-WRITE-005's limit. It is two sentences now, and asks the same. The journey's round found it.

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

## The journey

The maintainer chose five parts for the journey: *Goal*, *Steps*, *Variants*, *Postconditions* and *Minimal guarantees*. Each step carries what it needs from the path, so the round's *Seams* part goes. The comparison and the recommendation stay below as they were made.

### Decided: the journey

The maintainer decided the journey on 7 October, in comments on PR #1374. The journey is fully decided, and G fills its parts with the adopter's first day (`journey/G-chosen-template.md`).

- **The name stays *journey*:** a summary-level path an actor takes across several use cases, with the seams between them.
  - It is explicitly not a UX journey map.
  - The engineering usage matches ours, such as critical user journeys in reliability engineering and end-to-end testing.
  - The hint and the README say so.
- **The parts, in order:**
  - *Goal*, required: one sentence in the actor's own voice, as a use case's goal is.
  - *Steps*, required: one line for each step, the use case's id and its title exactly as the use case states it, such as `2. UC-002 — See how pkit is wired into my project`. Under a step, one line for each hand-over it relies on.
  - *Variants*, optional: the journey's own branches.
  - *Postconditions*, required: the state that shows the whole path succeeded.
  - *Minimal guarantees*, optional: what still holds when the path stops before its end.
- **A hand-over sits under the step that needs it:**
  - **From an earlier step:** `**Needs from step 1 (UC-001):** <what it receives>. <How that can break.>` The named step is an earlier step of this journey, with the right number and id.
  - **From a use case outside the journey,** typically another actor's: `**Needs from UC-006 (outside this journey):** <what it receives>. <How that can break.>` The journey's front matter lists that use case in `relies-on`.
  - **From nothing:** a step that needs nothing from the path has no such line.
- **The seams, weighed:** the maintainer chose B.
  - **A, a separate *Seams* part:** one item for each step that relies on another, as the round recommended. It gives an overview of every hand-over, and survives an inserted step. But it splits each step from what it needs.
  - **B, each hand-over nested under its step:** a journey is read as a path, so the context wins.
- **The round's questions:**
  1. **Question 1, the seam's key:** settled by B. A hand-over names the step it relies on, by number and id, under the step that relies on it. No line names a pair.
  2. **Question 2, strict *Preconditions*:** option (a). The use case keeps them strict, as decided, and the reason changes. Journeys carry their own hand-overs, and the part records the rare state an earlier use case set up that nothing checks again. It is Cockburn's counterpart to *Postconditions*.
  3. **Question 3, the use cases a journey relies on beyond its steps:** option (b), as `relies-on`. Each listed use case is an anchor, so a change to it flags the journey.
  4. **Question 4, `init`'s next steps:** it is no template decision, so it is filed as #1376.
- **As recommended:** each step's use case has the journey's actor, and the journey anchors its actor. Every part ships with software-analysis, and project-kit adds none of its own.

**The declaration #1363 takes, in this order:**

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# JRN-NNN — <title>` | yes | heading | none, since the stamp writes it | `# JRN-003 — Build and export the first report` |
| `goal` | Goal | yes | `sentence` | What the actor wants from the whole path, in one sentence in their own voice. Start with the verb, with *I* and *my* where they refer to themselves. | Build my first report and export it as a file. |
| `steps` | Steps | yes | `steps-match-front-matter` | One line for each use case in `steps`, in order: its id and its title as the use case states it. Under a step, add one line for each hand-over it needs from an earlier step or from a use case outside the journey. Say what it receives and how that can break. | `3. UC-007 — Export the report as a file`, and under it `**Needs from step 2 (UC-005):** the report the analyst saved. A report left unsaved is not offered for export.` |
| `variants` | Variants | no | `variants`, read against *Steps* | One for each branch of the whole path, lettered after the step it leaves. Say where the path rejoins or ends. | 3a. The analyst wants a second report, and the path rejoins at step 2. |
| `postconditions` | Postconditions | yes | none | The state that shows the whole path succeeded. | The analyst holds a file with their first report. |
| `minimal-guarantees` | Minimal guarantees | no | none | What still holds when the path stops before its end. Name the record or code each rests on. | Stopping after any step leaves every saved report as it was (DEC-003). |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it. The stamp writes each hand-over's label, so the hint for *Steps* names none.
- **The examples:** one neutral journey runs through them all, the analyst's first report. Its last step is the use case's own example, the export. *Minimal guarantees*' example now names its record, as its hint asks.
- **An outside need, in the example's terms:** `**Needs from UC-009 (outside this journey):** the template an administrator published. Without it, the analyst has nothing to build a report from.` The journey then lists `relies-on: [UC-009]`.

**The front matter gains `relies-on`:**

- **What it holds:** the use cases outside the journey that a step needs something from, by id, as a list, such as `relies-on: [UC-006]`. It is absent where no step needs one.
- **Why data:** a tool takes data only from the front matter (the design's Decided 2). So a check can resolve each id to a use case, and hold the list to the nested lines.
- **An anchor too:** each use case in it is an artefact anchor, as each step's is. A change to one flags the journey.

**The forms #1365 builds**, as the maintainer decided:

- **The step lines:** *Steps* holds one numbered item for each entry of `steps`, in the same order, numbered from 1. Item n opens with its number, the n-th id of `steps`, ` — ` and that use case's `title`, exactly. A repeated use case repeats its line.
- **A need from a step:** `**Needs from step N (UC-xxx):**` sits under a later step, and step N of this journey has the id UC-xxx.
- **A need from outside:** `**Needs from UC-xxx (outside this journey):**` names a use case in `relies-on`, and each use case in `relies-on` has at least one such line.
  - **The round's reading, for #1365 to confirm:** a use case outside the journey is no step of it, so no id is in both `steps` and `relies-on`.
- **The anchors:** the journey's use-case anchors equal its steps plus `relies-on`.
- **One actor:** each step's use case has the journey's actor as its `actor`. The stamp refuses the same, so the check accepts nothing the stamp would refuse.
- **A renamed use case:** each journey through it fails its title check until the step line follows. Friction flags that journey anyway, since the use case changed.
- **What no form checks:** whether the words are true. Friction flags the journey when a step's use case, a use case in `relies-on` or an anchored file changes. A reviewer then rereads the hand-overs (DEC-001 point 4).
- **Withdrawn use cases:** a journey in force may name no withdrawn step (`check.py`). A withdrawn journey is history, so no form fails it (the design's part 1).
  - **The round's reading, for #1365 to confirm:** the same holds for `relies-on`.

**Left out, one reason each:**

- **Seams, as a part of its own:** each hand-over sits under its step (B).
- **Preconditions and Trigger:** the first step's use case holds them.
- **Assumptions:** each step's use case holds its own.
- **Other actors:** the steps' use cases name each with what they must protect. Another actor's use case that a step needs is in `relies-on`.
- **A journey map's parts:** a journey is not a UX journey map, so touchpoints, thinking, feeling and opportunities stay out.
- **Level and scope:** the kind implies the level, and the area folder shows the scope.

**What filling G showed:**

- **Each hand-over has its source:** the six facts of A's seam UC-xx4 → UC-xx5 now sit in four lines under step 6. They come from steps 1, 3 and 5, and from the developer's landing.
- **A repeated use case:** step 5 needs what step 4 showed, the second pass through UC-xx2. The number tells the two passes apart, where the id cannot.
- **Step 1 needs nothing,** so it has no line. Every later step needs something from an earlier one.
- **The journey's own branches:** two of D's extensions cross use cases, 1b and 4a, so G keeps them as variants 1a and 4a. D's other extensions each belong to one step's use case, or are a hand-over that G states under its step.
- **The step lines lose the commands:** A's lines named them, such as `pkit init`. Each title is its use case's now, and the commands are in the use cases.
- **The front matter:** `relies-on` lists the landing, and the anchors gain it. E's `involves` goes.
- **Length:** G runs to 595 words, against A's 705 and E's 731.

**For the build:**

- **The parts (#1363):** the table above, in its order, with each part's hint and example.
- **`relies-on`, a schema change (#1363 and #1365):** the journey's schema gains it as an optional list of use-case ids. It refuses an unknown field today (`SA/schemas/journey.schema.json`). The check resolves each id to a use case in the analysis, and requires the use-case anchors to equal `steps` with it (`SA/scripts/_lib/check.py`).
- **The forms (#1365):** as defined above. `seams-match-steps` goes, and `steps-match-front-matter` reads the titles and the nested needs.
- **One actor, checked (#1365):** the check compares each step's `actor` with the journey's (`check.py`), and the stamp refuses the same (`SA/scripts/_lib/stamp.py`).
- **The stamp and the templates (#1366):** rendered from the table, so *Starts*, *Seams to watch* and *Done when* go, and the instruction line with them.
  - **The step lines:** the stamp writes each one with its use case's title, which it reads as it checks the step.
  - **The hand-overs:** it writes them in the nested form, never as pairs (`stamp.py`). Which step a stamped line names first, and how `relies-on` reaches the stamp, are #1366's to settle.
  - **The anchors:** it writes the journey's actor and each use case in `relies-on`, beside the steps' use cases.
- **The name (#1366 and #1369):** the template's head and the README define a journey as decided, and say it is not a UX journey map. No part's hint describes the kind, so the round reads the maintainer's "hint" as the template's head.
- **DEC-001 first (#1358):** its point 4 names a journey's anchors as its steps' use cases and the code at its seams. `relies-on`, the journey's actor and its records go beyond it, so #1358's refinement says so before any build cites it (core rule 2).
- **The skill and the README (#1369):** the journey sub-procedure's *Fill it* list gives way to the hints.

### The example

The main example is a real core journey of pkit: the adopter's first day with the methodology.

- **The needs it serves:** four of the adopter's (`ACT-adopter`).
  - Install the methodology, and see its wiring into the project.
  - Add a capability.
  - Declare the project's settings once, and have them validated.
  - Make the project's merges wait on the methodology's checks.
- **One actor:** a journey is "an end-to-end path an actor takes" (DEC-001 point 1). The schema's single `actor`, the template and the skill say the same.
  - So the example keeps the adopter. The developer's landing of the install sits at a seam, not among the steps.
  - The sources agree. NN/g asks for "one point of view per map", and Cockburn's summary use case has one primary actor.
  - **What nothing checks:** that each step's use case has the journey's actor. `check.py` holds a step to being a use case in force, and never compares its actor.
- **The use cases:** none exists yet. Each id is `UC-xx` and a digit, so the six stay apart:
  - `UC-xx1 — Install the methodology into a project`
  - `UC-xx2 — See how the methodology is wired into the project`
  - `UC-xx3 — Install a capability`
  - `UC-xx4 — Declare the project's settings`
  - `UC-xx5 — Make the project's merges wait on the methodology's checks`
  - `UC-xx6 — Land a change on the default branch`, the developer's, at a seam only. It is the landing of the use case's round.
- **A repeated step:** step 4 repeats UC-xx2, as the schema allows. It tests `steps-match-front-matter` with a repeat, and the seams with a pair that runs back, UC-xx3 → UC-xx2.
- **A second example:** F, in the recommended parts. The adopter upgrades the methodology and re-pins a rule set, two more of the adopter's needs. It has no read-only step, where the first example reads status twice.
- **Derived from:**
  - the CLI reference (`.pkit/cli/README.md`), for `init`, `status`, a capability's install and plan, the configuration file, `sync`, `pin`, `upgrade`, `validate` and the change check
  - ADR-009 point 3 for a private install, ADR-049 for the pin, and COR-050 points 12 and 15 for the friction mode
  - COR-030 for what a capability requires, COR-053 point 8 for plans and suggestions, COR-054 for the default branch, and COR-051 point 7 for F's pins
  - the code: `install.py` for `init`'s closing steps, `status.py` for what status shows, and `capabilities.py`, `provisioning.py`, `sync.py` and `validate.py` for what fails
- **Core only:** no capability is named. Step 6's pipeline is the project's, since the backbone ships no workflow (`ACT-ci-pipeline`).
- **The same in A to E:** the front matter, the steps and the facts at each seam. E adds `involves` to the front matter.

**What the example left unclear.** The round decides none of these.

1. **How `pkit` gets on the path.** `init`'s closing next steps recommend a symlink to a source checkout's dispatcher (`install.py`). The CLI reference recommends `uv tool install`, after PRJ-004, and keeps the symlink as a contributor's convenience. Question 4 asks about it.
2. **Step 6 is mostly the hosting service's.** The adopter writes the pipeline's job, and sets the required status in the hosting service. The system's part is the checks' unattended run (`ACT-ci-pipeline`).
3. **A newer pkit in the pipeline.** Without a pin, `pkit sync` writes the running pkit's own content (the CLI reference, on `sync`). So a newer pkit checks the project against newer content than its own, beside #1212's refusal of an older one.
4. **The capability.** None is named, so the seams into and out of UC-xx3 hold for any. A capability with no query command has nothing to provision, and the offline risk falls away.
5. **A role conflict.** Two installed providers of one role conflict until the project selects one (COR-053 points 1 and 7). No two capabilities that ship today provide one role (each one's `package.yaml`), so only a third party's or a home-grown capability could raise it.

### The candidates

Each candidate is complete and filled, as the artefact would read on the default branch. Its id is `JRN-xxx`, since the round stamps nothing into `tech-docs/analysis/`.

- **A, today's template** (`journey/A-todays-template.md`): exactly the parts of `SA/templates/journey.md`. They are *Starts*, *Steps*, *Seams to watch* and *Done when*. The instruction line under *Seams to watch* stays, as in every artefact filled from it.
- **B, a journey map** (`journey/B-journey-map.md`): NN/g's components and Adaptive Path's building blocks, adapted only where pkit requires.
  - NN/g's *actor* and Adaptive Path's *lens* are the front matter's `actor`, so the body does not repeat it.
  - *Scenario and expectations* opens it, as in NN/g.
  - Each phase is a heading with *Doing*, *Touchpoints*, *Thinking*, *Feeling* and *Pain points*. Doing, thinking and feeling are Adaptive Path's names for NN/g's actions, mindsets and emotions.
  - Each phase's *Doing* numbers its steps with their use cases, so the steps stay citable. Three phases hold the six steps.
  - *Opportunities* close it, as both sources' maps end. Adaptive Path calls its version takeaways.
  - *Feeling* is inferred from the adopter's needs, since no research of adopters exists.
- **C, the design's first cut:** equal to A in its parts and their order. It differs from A in three ways, and only the first shows in a filled artefact:
  - no instruction line under *Seams to watch*, so a filled C is A without that line, and it has no file of its own
  - each part stamped with a one-line hint, which the writer replaces
  - every part required and checked, *Steps* with the form `steps-match-front-matter` and *Seams to watch* with `seams-match-steps`
- **D, Cockburn's summary-level use case** (`journey/D-summary-use-case.md`): his fully dressed parts at the summary level, adapted as the use case's B was.
  - His section 5.2 gives the model. A summary use case's steps are user-goal use cases, and it has one primary actor (Use Case 6, *Operate an Insurance Policy*).
  - Each step names its use case by id, in place of his italics. Step 6 names two, the adopter's UC-xx5 and the developer's landing.
  - Each break is an extension of the step where its condition arises. Its sub-steps say where the break shows and where the path resumes, as 1b does for a private install.
- **E, the use case's decided parts** (`journey/E-use-case-parts.md`): the nine parts the maintainer chose for the use case, carried to the journey. *Steps* and *Seams* stand in place of *Main path* and *Variants*.
  - Each seam pairs the earlier use case's *Postconditions* with the next one's *Preconditions*, then gives its *Risk*. These are the pairs the brief for this round suggested.
  - Each *Preconditions* follows the decided hint, a state that no step checks. Every one reads none, since each next command checks what it needs.
  - The front matter gains `involves`, as the use case's does.
- **F, a second example in the recommended parts** (`journey/F-second-example.md`): the adopter upgrades the methodology and re-pins a rule set. It has two steps and one seam, and it leaves out both optional parts.
- **G, the chosen template** (`journey/G-chosen-template.md`): the maintainer's five parts, filled with the adopter's first day. It came after the recommendation, and "Decided: the journey" says what filling it showed.

**Sources.** The journey map's parts and Cockburn's summary level were read from these:

- **NN/g:** Sarah Gibbons, "Journey Mapping 101", 9 December 2018 ([page](https://www.nngroup.com/articles/journey-mapping-101/)). Its five components are the actor, the scenario and expectations, the journey phases, the actions, mindsets and emotions, and the opportunities.
- **Adaptive Path:** *Adaptive Path's Guide to Experience Mapping*, first edition, August 2013 ([PDF](https://maeda.pm/wp-content/uploads/2019/12/Adaptive_Paths_Guide_to_Experience_Mapping.pdf)).
  - Its building blocks are doing, thinking and feeling, with place, time, devices, relationships, channels and touchpoints.
  - A map has a lens, a customer journey model and takeaways. Its stages hold pain points and opportunities.
  - It names "transitions between phases" as a dimension worth emphasising, the nearest thing to a seam.
- **Cockburn:** *Writing Effective Use Cases*, pre-publication draft 3 of 21 February 2000, section 5.2 ([extract](https://www.ifi.uzh.ch/dam/jcr:00000000-25a0-3d08-0000-00000ce96422/weuc_extract.pdf)). A summary use case "takes multiple user-goal sessions to complete", and the kite marks one whose steps are user-goal use cases.
- **Not verified:**
  - The published edition of 2001, whose wording may differ from the draft's.
  - The draft numbers two examples Use Case 6. Its table of contents gives the number to *Add New Service (Enterprise)*, and section 5.2 gives it to *Operate an Insurance Policy*.
  - Adaptive Path's own download link answered with a redirect, so the copy read is a third party's.

### At a glance

D says the most, and B gives a script the least to check. Words are counted as in the use case's round: the body, labels included, with the heading and front matter left out.

| Candidate | Parts | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 4: *Starts*, *Steps*, *Seams to watch*, *Done when* | None marked. Today's check catches a placeholder left in, not a part deleted. | 705 | Over B and D, a seam of its own between each two adjacent steps | The instruction line under *Seams to watch*, in every artefact. *Done when* restates UC-xx5's end, with UC-xx4's settings added. |
| B | *Scenario and expectations*, three phases of five parts each (*Doing*, *Touchpoints*, *Thinking*, *Feeling*, *Pain points*), then *Opportunities* | None marked | 591 | The touchpoints, the adopter's expectations, and fixes worth filing | *Thinking* repeats the actor's needs. *Pain points* hold the seams' facts, with no step to name them. *Opportunities* belong to the tracker. |
| C | 4, as A | All four | 685 | As A, with hints and checks | As A, without the instruction line |
| D | 12: *Goal in context*, *Scope*, *Level*, *Stakeholders and interests*, *Precondition*, *Minimal guarantees*, *Success guarantees*, *Trigger*, *Main success scenario*, *Extensions*, *Technology and data variations*, *Related information* | None marked | 793 | Where each break arises, where it shows and where the path resumes. The landing inside step 6, and the frequency. | *Success guarantees* restate UC-xx5's end, as A's *Done when* does. Two interests repeat actors' needs. *Open issues* repeat the tracker. |
| E | 9: *Goal*, *Other actors*, *Preconditions*, *Assumptions*, *Trigger*, *Steps*, *Seams*, *Postconditions*, *Minimal guarantees* | As the use case's | 731 | The goal in the actor's voice, two assumptions and a guarantee of the whole path | Each seam quotes two use cases' parts, and every precondition reads none. *Trigger* restates the first step's. Both other actors take part only inside use cases. |
| F | 4: *Goal*, *Steps*, *Seams*, *Postconditions* | All four | 156 | A seam that meets the next step's trigger | Nothing |
| G | 5: *Goal*, *Steps* with each step's hand-overs, *Variants*, *Postconditions*, *Minimal guarantees* | *Goal*, *Steps* and *Postconditions* | 595 | Each hand-over under the step that needs it, naming the step it comes from. The landing as data and as an anchor. | Variant 1a restates the private install that step 6's hand-over from step 1 names. |

**Note:** G came after the recommendation, and its row is added here to compare.

### Fit with pkit

Only A, C, E and F keep a seam for each step after the first. Filling E and F showed no seam that meets the next use case's *Preconditions*, since pkit's commands check what they need.

- **Steps cited by id, matching the front matter** (the form `steps-match-front-matter`):
  - A, C, E and F write one line for each step, `1. UC-xx1 — …`, in the order of `steps`. A form reads the id after the number.
  - D writes the id last, in parentheses, and its step 6 names two use cases. A form would have to find the step's own id among them.
  - B spreads the steps over three phases, each a heading. A form would read numbered items under headings, and the phases are no data.
- **Seams matching the steps** (the form `seams-match-steps`):
  - A, C and E give each pair of adjacent steps one item, labelled with the pair (`stamp.py`). F labels each item with the step that relies, as question 1 recommends. Either way, a form matches the items to `steps` by position.
  - B has no seam for each step. Its pain points sit inside a phase, so the passage from UC-xx1 to UC-xx2, within one phase, has nothing of its own.
  - D has no seams part. Each break is an extension of the step where its condition arises, and its sub-steps name where it shows, which may be steps later. A seam keyed by an adjacent pair cannot say that (question 1).
- **Seams against the use cases' Preconditions:** the decided hint makes a precondition a state, not an event, that no step checks.
  - **In E, every precondition reads none.** pkit's commands check what they need and refuse without it, as a capability's install does on a missing `.pkit/manifest.yaml` (`capabilities.py`). A fact a step checks belongs among the variants (the use case's question 5).
  - **In F, the seam meets the next step's trigger,** the failed validation that starts the re-pin. It meets no precondition either.
  - **What a seam holds instead:** what the next step relies on, which step or use case made it true, and how that can break. The step relied on is often not the one just before. UC-xx3 and UC-xx4 rely on UC-xx1's install, and the pipeline relies on the developer's landing.
  - **This bears on a decided part.** The maintainer added *Preconditions* because "a journey's seams need them", and here they carry no seam (question 2).
- **No script compares a seam with the use cases** (the design's Decided 2). A tool takes data only from front matter, and a seam and the use cases' parts are body text.
  - Friction catches a stale seam instead. A changed use case flags the journeys through it (DEC-001 point 4).
  - E quotes both use cases at each seam, so a change to either makes the quote stale as well as the seam. A, C and F state each fact once.
- **Anchors** (DEC-001 point 4): a journey anchors to its steps' use cases, and to the code at its seams.
  - **A seam's other use cases cannot be anchored.** `check.py` requires the use-case anchors to equal `steps` exactly. So the landing, UC-xx6, stays unanchored, and a change to it never flags the journey (question 3).
  - **The journey's own actor:** DEC-001 point 4 anchors a journey to its use cases only. Its goal is in the actor's voice and serves the actor's needs, so every candidate anchors `ACT-adopter` too, as a use case anchors its actor. Without it, a changed need reaches the journey only once a step's use case is updated.
  - **Records:** the seams cite six records. DEC-001 point 4 names none for a journey, but it anchors a use case to "the decisions they rely on". The stamp takes `--record` for every kind (`SA/README.md`), and every candidate anchors the six.
  - **Cited and not anchored:** B and D also cite PRJ-004, and D cites COR-002, which the shared front matter leaves out. Filled for real, each would anchor them.
  - **E's `involves`:** the journey's schema refuses an unknown field (`SA/schemas/journey.schema.json`), so `involves` needs a schema change, as the use case's does.
  - **Who flags what:** friction flags the whole journey, never one seam. This table is a reviewer's own mapping:

  | Seam or part | The anchors that would flag it |
  |---|---|
  | UC-xx1 → UC-xx2 | UC-xx1, UC-xx2, `install.py`, `visibility.py`, `status.py` and ADR-009 |
  | UC-xx2 → UC-xx3 | UC-xx2, UC-xx3, `status.py`, `capabilities.py`, `capability_plans.py`, COR-030 and COR-053 |
  | UC-xx3 → UC-xx2 | UC-xx3, UC-xx2, `provisioning.py`, `status.py`, `capability_plans.py` and COR-053 |
  | UC-xx2 → UC-xx4 | UC-xx2, UC-xx4, `status.py`, `default_branch.py` and COR-054 |
  | UC-xx4 → UC-xx5 | UC-xx4, UC-xx5, `visibility.py`, `sync.py`, `validate.py`, `provisioning.py`, `friction_check.py`, `default_branch.py`, ADR-009, ADR-049, COR-050 and COR-054. Not UC-xx6, which today's check keeps out. |
  | B's *Thinking* and *Feeling* | `ACT-adopter`, for the needs that *Thinking* restates. Nothing watches a feeling. |
  | E's *Other actors* | `ACT-developer` and `ACT-ci-pipeline`, directly. Without them, an actor's change reaches the journey only once a step's use case is updated. |

- **Revalidation:** take a change that makes `pkit status` show the default branch. `status.py` changes, so friction flags the journey.
  - **A and C:** seam UC-xx2 → UC-xx4 goes stale. A reviewer rereads five seams to find it.
  - **B:** one pain point of *Gate the merges* goes stale, and one opportunity is met. Nothing flags an opportunity met in any other way, such as by an issue closed.
  - **D:** extension 5a goes stale.
  - **E:** the seam's *Risk* goes stale. Its quote of UC-xx2's *Postconditions* goes stale too, once UC-xx2 is updated for the change.
- **What a script can check:**
  - **A and C:** the heading against the id and title, as today. Then each part present, in order and not empty, and the two forms.
  - **E and F:** as A, and the goal one sentence. A seam's inner labels in E are content, since only declared labels delimit (the design's part 1).
  - **D:** the same for its parts, then *Level* from a closed list, and each extension after a step.
  - **B:** its labels in each phase, and its steps only as numbered items under the phases.
  - **None of them:** whether a seam's words hold against the use cases. Whether a step's use case has the journey's actor is front matter, so a check could hold it (the recommendation).
- **The membership test:** an artefact belongs in the analysis "if a change to the software can make it false" (DEC-001). B's *Feeling* rests on no research, so no revalidation can confirm it, and no anchor watches it. Only a feeling tied to a fact, as "reassured by the backup", can go false with the software.
- **The writing rules:**
  - A's instruction line holds no semicolon, unlike the use case's.
  - B's phases are headings, where the other candidates use bold labels.
  - D names steps by number in its prose, as "resumes at step 6". Such prose goes stale when a step is inserted.

### Recommendation

Ship four required parts, *Goal*, *Steps*, *Seams* and *Postconditions*, and two optional ones, *Variants* and *Minimal guarantees*. Key each seam by the step that relies, check the one actor, and anchor the journey's actor.

**Decided otherwise.** The maintainer nested each hand-over under the step that needs it, so no *Seams* part ships, as "Decided: the journey" says. This recommendation stays as it was made, and each point the decision turned is marked below.

- **The criterion:** a part ships when filling showed that it holds what no step's use case holds. Each of the use case's further parts was weighed by it.
- **Why the four:**
  - *Steps* and *Seams* are DEC-001 point 1's journey, one actor's path across use cases and the seams between them.
    - **Decided otherwise:** *Steps* carries the seams, each nested under the step that needs it (option B).
  - *Goal* and *Postconditions* come from today's template, its *Starts* and *Done when*, renamed as the use case's parts were. The goal is in the actor's voice, as the use case's is (the use case's question 6).
  - A and E filled each of the four. D has no seams part.
- **What a journey's end adds:** its *Postconditions* combine several steps' ends. "Under the settings the project declared" brings UC-xx4's end into UC-xx5's.
- **Where the start goes:** *Starts* held where the actor begins and what they want. What they want is the *Goal*. Where they begin is the first step's *Trigger*, since strict *Preconditions* read none, as UC-xx1's do.
- **The optional parts,** each holding what no step's use case holds:
  - *Variants*: the journey's own branches, as D's 1b and 4a are. A recovery across use cases, or a loop back to an earlier step, belongs to no single use case's variants.
  - *Minimal guarantees*: what still holds when the path stops before its end. E's first holds before UC-xx5 is ever reached, so it is the journey's.
  - F has neither, so it leaves both out.
- **What was weighed and left out:**
  - **Preconditions:** the first step's hold them, and in both examples they read none.
  - **Trigger:** the first step's.
  - **Assumptions:** both of E's are UC-xx5's, the required status and the pipeline's network.
  - **Other actors:** the developer and the CI pipeline take part only inside a use case, whose own *Other actors* names each with what it must protect. So completeness, the maintainer's reason for the use case's part, is met there. If the maintainer wants it on the journey too, it comes optional, with E's `involves`.
  - **B's touchpoints:** the steps' use cases name their commands.
  - **B's thinking and feeling:** *Thinking* restates the actor's needs, and *Feeling* rests on no research.
  - **B's phases:** they group steps for a reader. A project may add sections of its own (the design's part 4).
  - **Opportunities and open issues:** they belong to the tracker, which no anchor watches.
  - **D's level and scope:** the kind implies the level, and the area folder shows the scope, as for the use case.
  - **E's pairs:** every precondition read none, and each quote is one more copy to keep.
- **One actor, checked:** each step's use case has the journey's actor as its `actor`. Both are front matter, so the check and the stamp can hold it (the design's Decided 2). A use case the actor only takes part in, through its `involves`, is no step of theirs, and goes in question 3's list.
- **The journey's actor, anchored:** the goal speaks for the actor and serves its needs, so the journey anchors it, as a use case anchors its own.
- **Labels:** nouns, as the use case's are. *Seams to watch* becomes *Seams*, and the hint carries what "to watch" said.
  - **Decided otherwise:** no *Seams* part ships, so its label goes.
- **Ships with:** every part ships with software-analysis. project-kit adds no part of its own for the journey.

The declaration #1363 would have taken, in this order, before the table in "Decided: the journey" superseded it:

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# JRN-NNN — <title>` | yes | heading | none, since the stamp writes it | `# JRN-003 — Build and export the first report` |
| `goal` | Goal | yes | `sentence` | What the actor wants from the whole path, in one sentence in their own voice. Start with the verb, with *I* and *my* where they refer to themselves. | Build my first report and export it as a file. |
| `steps` | Steps | yes | `steps-match-front-matter` | One line for each use case in `steps`, in order: its id, then what the actor achieves in it. | 1. UC-003 — The analyst signs in. 2. UC-005 — The analyst builds the report. 3. UC-007 — The analyst exports the report as a file. |
| `seams` | Seams | yes | `seams-match-steps` | One for each step after the first, labelled with its id. Say what the step relies on, what made it true, and how that can break. Write `None.` when it relies on nothing. | **UC-007:** the report the analyst saved in UC-005. A report left unsaved is not offered for export. |
| `variants` | Variants | no | `variants`, read against *Steps* | One for each branch of the whole path, lettered after the step it leaves. Say where the path rejoins or ends. | 3a. The analyst wants a second report, and the path rejoins at step 2. |
| `postconditions` | Postconditions | yes | none | The state that shows the whole path succeeded. | The analyst holds a file with their first report. |
| `minimal-guarantees` | Minimal guarantees | no | none | What still holds when the path stops before its end. Name the record or code each rests on. | Stopping after any step leaves every saved report as it was. |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it.
- **The examples:** one neutral journey runs through them all, the analyst's first report. Its last step is the use case's own example, the export.
- **The goal's hint:** it is the use case's, split into two sentences. As one, it runs to 28 words, over RS-WRITE-005's limit.
- **The order:** as the use case's, with *Variants* after the path and *Minimal guarantees* last.

**The two forms, defined** (#1365), as question 1 recommends:

- **Decided otherwise:** `seams-match-steps` goes with the *Seams* part. The forms in "Decided: the journey" replace these.
- **`steps-match-front-matter`:** *Steps* holds one numbered item for each entry of `steps`, in the same order, numbered from 1.
  - Item n opens with its number, then the n-th id of `steps`, then ` — ` and text.
  - A repeated use case repeats its line.
  - Evidence cites a journey's steps by use-case id, each once (`SA/schemas/revalidation-evidence.schema.json`). So renumbering after an inserted step breaks no evidence. It does break prose that names a step by number, such as a variant's "rejoins at step 2", which the same change edits.
- **`seams-match-steps`:** *Seams* holds one top-level item for each step after the first, in the order of `steps`. So n steps give n − 1 items.
  - Item i opens with the bold label `**<id>:**`, the id of step i + 1. Text or `None.` follows on the item's own line, and nested items may follow that.
  - Items match by position, so a repeated step repeats its label. A use case repeated next to itself needs nothing special.
  - As for every list form, a line that is no top-level item is not judged, such as a lead sentence.
- **Keyed by pairs instead** (question 1's alternative): item i opens with `**<step i> → <step i+1>:**`. A use case repeated next to itself then gives a pair such as `UC-005 → UC-005`.
- **What neither form checks:** whether the words are true. Friction flags the journey when a step's use case or a seam's anchor changes, and a reviewer rereads the seams (DEC-001 point 4).
- **Withdrawn steps:** a journey in force may name no withdrawn use case (`check.py`). A withdrawn journey is history, so no form fails it (the design's part 1).
- **The stamp:** it writes each step's line and each seam's label from `steps`, with one hint after each part's label. The forms refuse an item left with no text (the design's part 2).

**For the build:**

- **Decided otherwise:** the list in "Decided: the journey" replaces this one.
- **The parts (#1363):** the table above, in its order, with each part's hint and example.
- **The forms (#1365):** as defined above.
- **DEC-001 first (#1358):** its point 4 names a journey's anchors as its steps' use cases and the code at its seams. The journey's actor, its records and any list from question 3 go beyond it. So #1358's refinement says so before any build cites it (core rule 2).
- **One actor, checked:** the check compares each step's `actor` with the journey's (`SA/scripts/_lib/check.py`), and the stamp refuses the same (`SA/scripts/_lib/stamp.py`). So the check accepts nothing the stamp would refuse. It is filed on the maintainer's answer to this recommendation.
- **The journey's actor, anchored:** the stamp writes it among the artefact anchors, as it writes a use case's actor (`SA/scripts/_lib/stamp.py`).
- **Question 3 (b):** `SA/schemas/journey.schema.json` gains the list. The check requires the use-case anchors to equal `steps` with it, and the stamp writes its anchors.
- **The templates (#1366):** rendered from the table, so *Starts* and *Done when* go, and the instruction line with them.
- **The skill and the README (#1369):** the journey sub-procedure's *Fill it* list gives way to the hints.

**Found on the way:**

- **Two hints for one goal.** The use case's goal hint runs to 28 words in one sentence, over RS-WRITE-005's limit. project-kit holds its templates to `WRITE` (the design's part 5), so the maintainer chooses whether the use case's hint splits too.
  - **Resolved:** the use case's hint is two sentences now, and asks the same ("Decided: the use case").
- **`init`'s symlink under `uv tool install`.** With the tool installed, the source kit is the wheel's bundled tree (`install.py`). So the symlink `init` prints points inside the tool's own environment. Question 4 asks about the next steps.
  - **Filed** as #1376.

### Questions for the maintainer

Each question is one decision, with a recommendation. Questions 1 to 3 shape the journey. Question 4 was found on the way. The maintainer settled all four on 7 October.

1. **Is each seam keyed by the step that relies on it, or by the pair of adjacent steps?**
   - **The case:** the stamp writes one seam for each pair of adjacent steps (`stamp.py`). The example's steps rely on steps further back, as UC-xx3 and UC-xx4 rely on UC-xx1's install. A read-only step leaves a pair with nothing to say, such as UC-xx1 → UC-xx2.
   - **Recommendation:** keyed by the step that relies, `**UC-xx3:**`, with `None.` allowed. The text names what the step relies on and what made it true. #1365 builds the form as defined above.
   - **Else:** today's pair labels, with the hint asking what the next step relies on from any earlier step. The label then names the step just before, which may have no part in it.
   - **Decided:** neither, as such. Each hand-over is nested under the step that needs it (option B in "Decided: the journey"). It names the step it relies on by number and id, and no line names a pair.
2. **Do *Preconditions* stay strict, now that they carry no seam here?**
   - **The case:** the maintainer added *Preconditions* to the use case because a journey's seams need them. Under the decided hint, a precondition is a state that no step checks. pkit's commands check what they need, so every precondition in E reads none, and F's seam meets a trigger.
   - **Recommendation:** yes, they stay strict. A seam states what a step relies on in its own words, checked or not, and *Preconditions* keep what nothing checks. Nothing decided changes, only the reason given for the part.
   - **Else:** the hint loosens, so a precondition may hold what an earlier use case makes true even where a step checks it. Seams could then point at preconditions, at the cost of the line question 5 drew between preconditions and variants.
   - **Decided:** option (a), as recommended. The reason changes: journeys carry their own hand-overs, and the part records the rare state an earlier use case set up that nothing checks again. It is Cockburn's counterpart to *Postconditions*.
3. **Are the use cases a journey relies on, beyond its steps, anchored?**
   - **The case:** the pipeline gates later pull requests only once the developer's landing, UC-xx6, has put the install, the settings and the job on the default branch. Today's check requires the use-case anchors to equal `steps` exactly (`check.py`), so the landing cannot be anchored.
   - **The options:**
     - (a) name them in words only, as today
     - (b) list them in the front matter, as data and as anchors, and require the use-case anchors to equal `steps` with that list
     - (c) make them steps, so a journey may pass through another actor's use case
     - (d) anchor the reliance where a use case states it: UC-xx5 lists the landing, and a journey reaches it through UC-xx5
   - **Recommendation:** (b). It keeps one actor (DEC-001 point 1), and anchors what the journey relies on (DEC-001 point 4). The list's name is the maintainer's, such as `relies-on`.
   - **Else:**
     - (a) leaves a stale seam to a reviewer's memory, since a change to the landing never flags the journey.
     - (c) changes DEC-001 point 1, and a journey stops being one actor's path.
     - (d) serves every journey through UC-xx5 with one declaration. But anchors between use cases need a check against cycles, and the chain stops wherever UC-xx5 is revalidated as unchanged.
   - **Decided:** option (b), as recommended, named `relies-on`. A step that needs something from such a use case says so in a nested line. The check requires the lines and the list to agree, and the use-case anchors to equal the steps plus `relies-on`.
4. **Do `init`'s closing next steps recommend `uv tool install`, as the CLI reference does?**
   - **The case:** `init` ends by recommending a symlink to the source checkout's dispatcher, once per machine (`install.py`). The CLI reference recommends `uv tool install` after PRJ-004, and keeps the symlink for contributors. Under `uv tool install`, the symlink would point inside the tool's environment.
   - **Recommendation:** yes, in a Task of its own that brings the next steps in line with PRJ-004. It is no template decision, so it is filed as the design note filed what it found on the way.
   - **Else:** the two keep differing, and UC-xx1 names no way to put `pkit` on the path.
   - **Decided:** it is no template decision, so it is filed as #1376.

### Review

The critic reviewed the first draft. Each finding below changed the draft, or is answered here.

| Finding | Answer |
|---|---|
| Red flag: E's preconditions broke the decided hint, since a step checked each one, so the reasons no seam was a pair were wrong | E now follows the hint, and every precondition reads none. "Fit with pkit" gives the finding, and question 2 asks about it. |
| Red flag: the reason for shipping no further part contradicted a guarantee of the whole path, which also claimed too much | *Minimal guarantees* ships optional, for the whole path. The guarantee now covers merges made through the hosting service only. |
| Red flag: D was said to put each break at the step where it shows | D's extensions sit where the condition arises, and name where it shows. *Variants* ships optional for such branches. |
| The seams form was keyed by adjacent pairs, against the round's own finding | Question 1 recommends keying by the step that relies, and the form is defined for both keys. |
| The journey's start had no home | The first step's *Trigger* holds it (the recommendation). |
| The journey's own branches had no part | *Variants*, optional |
| Five errors of fact: suggestions with no capability, a backbone range no first day misses, a private install nothing reports, the landing's place, and dormancy | Each corrected in the four candidates. A role conflict, which no two shipped capabilities can raise, gives way to a suggestion. |
| The anchors missed the modules behind three behaviours | `capabilities.py` and `friction_check.py` added. `connections.py` left with the role conflict. |
| The journey's own actor was unanchored | Every candidate anchors it, and the recommendation says so. |
| A proposed rule, RS-WRITE-014, was the reason to anchor records | DEC-001 point 4's decisions for a use case, and the stamp's `--record`, are the reasons now. |
| Renumbering "breaks no citation" holds for evidence only | Limited to evidence, with prose that names a step by number |
| The build of the actor check named only the check | The stamp refuses the same (for the build). |
| Two hints for one goal | Listed under "Found on the way" |
| "These four are DEC-001 point 1's account" | *Goal* and *Postconditions* come from today's template, and the recommendation says so. |
| The claim that no seam is a pair rested on one example with two read-only steps | F, with no read-only step, meets a trigger, not a precondition. |
| B's feeling dismissed by the membership test | It rests on no research, and only a feeling tied to a fact can go false. |
| The repeat charged to D alone | A's *Done when* is charged too, and the recommendation says what a journey's end adds. |
| "A, D and E filled each of them" | A and E did, and D has no seams part. |
| *Other actors* dropped as a repeat, which the maintainer overrode for the use case | Answered under completeness: the use cases' own *Other actors* meet it. |
| Question 1 mixed another actor's use case with the adopter's own | The adopter's own, a role conflict, left the example. Question 3 now covers the landing. |
| Question 2 let in through `involves` what question 1 rejected | The check compares `actor` only, and an involved actor's use case goes in question 3's list. It is now part of the recommendation. |
| Question 3 bundled five parts into one answer | The criterion weighs each part in the recommendation, and two ship optional. |
| Question 4 is no template decision | Marked as found on the way. The round was asked to list it as a question. |
| Missing questions: the seam's key, and strict preconditions | Now questions 1 and 2 |
| Counter-alternative: anchor the reliance where a use case states it | Option (d) of question 3 |
| Writing: two elided verbs, a changed meaning, an ambiguous pronoun, seams named by number | Each fixed |

## The actor

The round fills four candidates with the core developer, and a second actor in the recommended parts. It recommends five elements that ship with software-analysis, and four questions wait for the maintainer.

### The example

The main example is a real core actor, the developer, as merged on main (`tech-docs/analysis/use-case-model/actors.md`).

- **One file per actor** (#1346): each candidate is the file `use-case-model/actors/ACT-developer.md` would be, headed `# ACT-developer — Developer`. Its front matter gains the `id` that #1346 adds to the actor's schema.
- **Why this one:** the developer is the primary actor of both of the use case's examples, the landing and the scratchpad note. Its body uses four of the core actors' nine labels, and each core actor uses four or five.
- **The same in every candidate:** the front matter, with its nine needs and its one anchor, COR-009, as on main. Only the body differs.
- **A second example:** the CI pipeline (`actor/E-second-example.md`), an actor that is no person, as merged. It tests whether each candidate's parts fit a system.
- **Derived from:** the core actors as merged, COR-008, COR-009 and ADR-061 for C's characteristics, and COR-050 for D's frustrations.

**What the example left unclear.** The round decides none of these.

1. **Records cited and not anchored.** The developer's *Core* cites ADR-061 point 3, and its one anchor is COR-009. The CI pipeline's *Note* cites PRJ-002, beside its anchors COR-054 and COR-050. So a change to ADR-061 point 3, which #1222 may bring, never flags the developer. The candidates keep main's anchors.
2. **C's and D's citations.** C cites COR-008 and ADR-061, and D cites COR-050. Filled for real, each would anchor them, as the journey's candidates found for PRJ-004.
3. **D's persona is invented.** No research of developers exists, so its name, age, bio and behaviours are made up, as the journey map's *Feeling* was inferred.
4. **No use case is stamped yet.** C's *Relationships* name the landing as `UC-xxx`, the id the use case's round gave it.

### The candidates

Each candidate is complete and filled, as the actor's file would read on the default branch after #1346.

- **A, today's template** (`actor/A-todays-template.md`): the front matter and one prose section, as `SA/templates/actors.md` asks. Its placeholder asks who this is, when they come to the system, and what they bring with them. So A has no place for the developer's *Core* and *Note*, and drops them.
- **B, the core actors' labels** (`actor/B-core-actors-labels.md`): the developer exactly as merged. These are project-kit's labels, from the style trial, as the design's part 9 lists them.
  - The opening says who the role is, with no label.
  - The list, in order: *The setup*, *Always a person*, *Can be*, *Does*, *Comes*, *Brings*, *In the model*, *Core* and *Note*. Each actor leaves out a label it has nothing for (RS-WRITE-002).
  - The developer uses *Comes*, *Brings*, *Core* and *Note*.
- **The design's first cut** ships B's opening, *Comes* and *Brings*, with the opening required (the design's part 8). project-kit adds the other seven labels (its part 9). So for project-kit the first cut reads as B, and it has no file of its own.
- **C, RUP's actor description** (`actor/C-rup-actor.md`): RUP's actor properties, adapted only where pkit requires.
  - *Name* is the front matter's `name` and the heading.
  - *Brief description* holds the role's sphere of responsibility and what it needs the system for. The needs stay in the front matter, so it summarises them.
  - *Characteristics* holds RUP's list for a human actor, with the frequency of use its guidelines add. Age, gender and cultural background are left out, since nothing about the developer states them.
  - *Relationships* holds the use cases, the other actors and the generalisation. RUP's *Diagrams* are left out, since the analysis has none.
- **D, a UX persona** (`actor/D-ux-persona.md`): NN/g's common pieces, in its order, with three parts its example persona shows.
  - NN/g's pieces: *Persona* for the name and age, then *Tagline*, *Experience*, *Context*, *Goals and concerns* and *Quote*. The photo is left out, since the file is text.
  - From its example persona: *Bio*, *Behaviors* and *Frustrations*.
  - The needs stay in the front matter, as in every candidate.
- **E, a second example** (`actor/E-second-example.md`): the CI pipeline as merged, in one file. Its opening says why it is an actor, and it uses *In the model*.

**Sources.** RUP's actor and the persona were read from these pages:

- **RUP:** the actor artefact ([page](https://www.cin.ufpe.br/~if682/RUP/process/artifact/ar_actor.htm)). Its properties are *Name*, *Brief Description*, *Characteristics*, *Relationships* and *Diagrams*.
  - *Brief Description* is "the actor's sphere of responsibility and what the actor needs the system for".
  - *Characteristics* are "for human actors". They are the physical environment, the number of users the actor represents, their domain knowledge, computer experience and other applications, and general characteristics.
  - Its tailoring says "Decide which properties to use and how to use them."
- **RUP's guidelines for an actor** ([page](https://www.cin.ufpe.br/~if682/RUP/process/modguide/md_actor.htm)):
  - A brief description "should be, at most, a few sentences long".
  - The characteristics add "the frequency with which the actor will use the system".
  - An actor "can be a user, external hardware, or another system".
- **NN/g:** Taylor Dykes, "Personas Make Users Memorable", 3 October 2025 ([page](https://www.nngroup.com/articles/persona/)).
  - A persona is "a fictional, yet realistic, description of a typical or target user of the product".
  - Its common pieces are a name, age, gender and photo, a tagline, the experience level, the context, the goals and concerns, and quotes. Its context asks "How often would they use it?"
  - "Personas must be based on user research to accurately represent a product's users."
- **Cooper:** "The Origin of Personas", Cooper's newsletter of August 2003. Its first three personas were "clearly differentiated by their goals, tasks, and skill levels".
- **Not verified:**
  - Cooper's essay was read only as a third party quotes it ([page](https://www.strehle.de/tim/?p=264)), since its own address is gone.
  - NN/g's example persona was read from its image's description, which names its bio, behaviors, frustrations, goals and tasks.
  - The RUP pages are a university's copy, as in the use case's round.

### At a glance

C and D say the most, and much of it describes people rather than the software. A says the least, and drops the layer line. Words are counted as in the earlier rounds: the body, labels included, with the heading and front matter left out.

| Candidate | Parts | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 1, unlabelled: who the role is, when they come, what they bring | None marked. Today's check catches a placeholder left in, not a part deleted. | 45 | Nothing. It reads fastest. | Nothing, but it drops the layer line and the note |
| B | The opening, then 4 of the 9 labels: *Comes*, *Brings*, *Core*, *Note* | None marked | 93 | The layer line: what in the core makes the role, and what of it is provisional. A work tracker's view of the role. | *Core* names the actor's one anchor, in words. |
| C | 3: *Brief description*, *Characteristics* with six items, *Relationships* with five | None marked. RUP leaves the choice to tailoring. | 234 | The other actors the developer works with, how many people play the role, and the applications they use | The brief description summarises the needs. *Frequency of use* is B's *Comes*, and *Environment* holds B's *Brings*. *Use cases* repeat the use cases' own `actor`. |
| D | 9: *Persona*, *Tagline*, *Bio*, *Experience*, *Context*, *Behaviors*, *Goals and concerns*, *Frustrations*, *Quote* | None marked | 219 | Speed, a quality the developer weighs against accuracy and thoroughness | *Accuracy*, *Thoroughness*, every frustration and the quote restate needs, some inverted. *Context*'s frequency is B's *Comes*. |
| E | The opening, then 5 of the 9 labels: *Comes*, *Brings*, *In the model*, *Core*, *Note* | As B | 180 | Why a system is an actor, and whose goals its runs serve | *Core* names the actor's two anchors, in words. |

**The labels across the core actors.** Each core actor uses four or five of the nine. Every one has the opening, *Comes* and *Core*.

| Label | The core actors that use it | Count |
|---|---|---|
| The opening, unlabelled | all eight | 8 |
| *The setup* | adopter | 1 |
| *Always a person* | merge authoriser | 1 |
| *Can be* | AI agent, component author, methodology maintainer | 3 |
| *Does* | methodology maintainer, operator | 2 |
| *Comes* | all eight | 8 |
| *Brings* | all but the AI agent | 7 |
| *In the model* | AI agent, CI pipeline | 2 |
| *Core* | all eight | 8 |
| *Note* | CI pipeline, component author, developer, merge authoriser, operator | 5 |

**What each source calls the same thing.** All three hold a name, the needs, a short description, when the actor comes and what it brings. Beyond those, each holds what the others lack.

| B | RUP | NN/g's persona |
|---|---|---|
| `name` and the heading | *Name* | the name, a person's rather than a role's |
| `needs` | in *Brief Description*: "what the actor needs the system for" | *Goals and concerns* |
| The opening, and *Does* | in *Brief Description*: "sphere of responsibility" | *Tagline* |
| *Comes* | a characteristic: the frequency of use | in the context: "How often would they use it?" |
| *Brings* | characteristics: the environment, domain knowledge and other applications | the experience level, and the device in the context |
| *Can be* | in the guidelines: several users can play one actor | none |
| *In the model* and *Note*, in part | *Relationships* | none |
| *Core*, *The setup*, *Always a person* | none | none |
| none | the number of users, and general characteristics | the age, gender, photo, bio, behaviours, frustrations and quote |

### Fit with pkit

Only A, B and E keep every part to what the software can make false. C and D add facts about people, and restate needs.

- **The needs stay data** (the design's Decided 2, and #1346). Every candidate keeps them in the front matter, where the schema checks them and the readers filler reads them (`SA/scripts/_lib/readers.py`).
  - A body part that restates them is a second copy, which #1346 rules out.
  - C's *Brief description* summarises them. D's *Goals and concerns*, *Frustrations* and *Quote* restate four of them, some inverted.
- **The voice** (the use case's question 6): every candidate keeps the needs in the actor's own voice, as merged.
  - It holds for a system too. Each of E's needs starts with its verb, and none needs *I* or *my*.
  - D's *Quote* is in the developer's voice, and restates a need.
- **What reaches a reader** (DEC-001 point 8):
  - The filler gives each actor as a reader, such as `act-developer`, with its name and needs as the description.
  - The point's schema asks the description for "who the reader is and what they need" (living-docs' `readers.schema.json`).
  - The opening says who the reader is, but a tool reads only front matter (the design's Decided 2). So the opening never reaches the point, in any candidate.
  - No page names an actor as its reader yet. Every page names `user` or `maintainer` (question 4).
- **Anchors** (DEC-001 point 4):
  - **Records only, for the core actors.** *Core* says in words what the anchors hold as data. In the developer and the CI pipeline, each anchored record is one that *Core* names.
  - **Cited and not anchored:** ADR-061 in B, and PRJ-002 in E, as "What the example left unclear" says.
  - **What an actor's change flags.** An artefact anchor changes whenever the anchored artefact's body or own fields change (COR-050 point 5).
    - A use case anchors its actor, and now each actor in `involves`. A journey anchors its actor.
    - So every edit to an actor's body flags each use case and journey that names it, and each needs an answer.
    - A part that changes often costs most. When #1222 settles where the landing lives, B's *Core* changes. Every use case of the developer is then flagged, the scratchpad note's included, which the landing's home never touches.
    - D's *Bio*, *Behaviors* and *Frustrations* change with the team, not with the software, and so does C's *Number of users*.
  - **Relationships as data would cycle.** C's *Relationships* name other actors in prose. As data and anchors, two actors that name each other would form a cycle, which COR-050 point 5 makes an error. So relations between actors stay prose, as in B's *Note* and C's *Relationships*.
- **The membership test** (DEC-001): an artefact belongs in the analysis "if a change to the software can make it false". The round applies it to each part, as the journey's round did to *Feeling*.
  - **Can go false:** the needs, the opening, *Comes*, *Brings*, *Core* and *In the model*. Each says what the role does with the system, or what the system does for it.
  - **Cannot:** D's *Persona*, *Tagline*, *Bio* and *Quote*, and C's *Number of users* and *Domain knowledge*. They describe people, and no change to the software makes them false.
  - **Tied to a fact:** D's *Frustrations* can go false, since each rests on a record. Each also restates a need.
  - **D's evidence:** NN/g asks a persona to rest on user research. None exists, so D's facts about Dana are invented.
- **An actor that is no person** (E):
  - A and B hold it as they hold a person. E's opening adds why it is an actor, the skill's test "Is it an actor?" written into the artefact.
  - RUP counts "another system" as an actor, but its *Characteristics* are "for human actors". So C would give the CI pipeline only a brief description and relationships.
  - D has no form for a system, since a persona is a person.
  - *In the model* serves the two actors that are no person. It says whose goals their work serves, since a system's goals belong to people.
- **What the use case and the journey ask of an actor:** each decided part that draws on an actor draws on the needs, *Comes* or *Brings*.
  - **A goal is a need** (DEC-001 point 1). The landing's goal is the first part of the developer's need to land a change. The use case's E repeats another need word for word. So the needs' hint mirrors the goal's.
  - **A trigger is one of the actor's occasions.** The CI pipeline's *Comes* lists every event that starts its runs. The landing's trigger, the developer deciding a change is ready, is an occasion of "for every change". So *Comes* is the actor's side of its use cases' triggers.
  - **What a use case relies on, or protects.** The landing's precondition, a committed change, is what the developer's *Brings* names, the change. Its *Other actors* has the CI pipeline run its checks "with no person to answer, against the one base it names". That is the pipeline's *Brings*, and its second need.
  - **Other actors need nothing more.** The use case's F found three of its four interests restating those actors' needs. So the needs are the interests, and an actor needs no part of its own for them.
  - **The journey's one actor:** a journey's goal combines several of its actor's needs, as the first day serves four of the adopter's. It needs nothing more of the actor.
  - **So:** the use cases draw on the needs, *Comes* and *Brings*, and the opening tells a reader who the role is.
- **The layer line, *Core*:** every core actor has one, and it is project-kit's.
  - It says what in the core makes the role exist. project-kit's analysis describes the core, and a capability's view of a role comes with that capability (the developer's *Note*).
  - An adopter's analysis describes one system, with no layer to name.
  - Its general form would say what in the system makes the role exist. DEC-001 point 4 already has each actor anchor that, or give `unanchored-because` where nothing does (question 3).
- **What a script can check:**
  - **A:** the heading against the id and the name, as #1346 asks. Then that some text follows it.
  - **B and E:** the heading, the opening, each declared label in order and not empty, and each need one sentence. Under project-kit's closed list, a label outside the nine is reported (the design's part 4).
  - **C and D:** the same for their own labels. C's six characteristics are content, since only declared labels delimit (the design's part 1).
  - **None of them:** whether a record the body names is among the anchors, or whether *Comes* covers each trigger of the actor's use cases. A later form could check the first, as the use case's round left a form for *Other actors* open.
- **The writing rules:**
  - A's paragraph runs to four sentences, the most RS-WRITE-007 allows.
  - B and E are the style trial's output, and meet `WRITE` as merged.
  - B's labels are verbs and phrases, such as *Comes*, *Brings* and *Can be*. The use case's and the journey's labels are nouns (question 2).

### Recommendation

Ship five elements with software-analysis: the heading, the needs, an opening, *Comes* and *Brings*. *Comes* is required and *Brings* optional. project-kit keeps its seven labels in its own `structures.yaml`, as the design's part 9 has them.

- **The criterion:** an element ships when RUP, the persona and the core actors all hold it, and a use case or a reader draws on it. The five meet it, as the table of what each source calls the same thing shows.
- **Why each:**
  - **The heading:** the stamp writes it, and #1346 checks it against the id and the name.
  - **The needs:** DEC-001 point 1's account of an actor, the readers point's data and the use cases' goals. Each is one sentence (the `sentence` form) in the actor's own voice (the use case's question 6).
  - **The opening, required:** RUP's brief description, NN/g's tagline and every core actor's first line. It has no form, since three core actors' openings run to two sentences.
  - **Comes, required:** RUP's frequency of use, NN/g's "How often would they use it?" and every core actor's. It is the actor's side of its use cases' triggers. It differs from the design's first cut (question 1).
  - **Brings, optional:** RUP's environment, domain knowledge and other applications, and NN/g's experience level. Seven core actors have it. The AI agent's *Comes* says it keeps no memory between sessions beyond what the repository holds, so it brings nothing of its own.
- **What was weighed and left out:**
  - **RUP's further characteristics:** the number of users, domain knowledge and general characteristics describe people, and no change to the software makes them false. RUP also limits them to human actors.
  - **RUP's relationships:** the use cases an actor takes part in are the use cases' own front matter, `actor` and `involves`. So a tool can list them, and the actor would hold a second copy. Relations between actors as data would form cycles. DEC-001 names no generalisation, and no core actor generalises another.
  - **The persona:** it must rest on user research. Its goals, frustrations and quote restate needs, and its other parts cannot go false with the software.
  - **project-kit's seven labels:** each stays project-kit's. *Can be*, *Does* and *In the model* recur in two or three core actors, and *The setup* and *Always a person* in one each. *Note* is project-kit's style (RS-WRITE-004), and *Core* is its layer line (question 3).
  - **In the model, for actors that are no person:** both actors that use it are no person. So any project with a system actor might want it. It recurs in project-kit only, so it waits until real artefacts show it recurs elsewhere (the use case's question 1).
- **Labels:** *Comes* and *Brings*, as the core actors have them (question 2).
- **Ships with:** the five elements ship with software-analysis. project-kit's `structures.yaml` adds its seven labels under the kind `actor`, closed, naming RS-ANALYSIS-002.

**The declaration #1363 would take, in this order:**

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# ACT-<slug> — <name>` | yes | heading | none, since the stamp writes it | `# ACT-analyst — Analyst` |
| `needs` | the front matter's `needs` | yes, at least one | `sentence`, on each | What the actor needs from the system, each in one sentence in their own voice. Start with the verb, with *I* and *my* where they refer to themselves. | Export my report as a file. |
| `opening` | none | yes | none | Who plays this role, and what they do with the system. | Someone who builds reports from their team's data. |
| `comes` | Comes | yes | none | When the actor comes to the system, and how often. | At the end of each week, and whenever a manager asks for figures. |
| `brings` | Brings | no | none | What the actor comes with, such as data, authority or a limit. | Their team's data, and a template an administrator published. |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it.
- **The examples:** one neutral actor runs through them all, the analyst of the use case's and the journey's examples.
  - Its need is the use case's example goal, word for word, since a need is a goal (DEC-001 point 1).
  - Its *Brings* names the template of the journey's example, which an administrator published.
- **The needs' hint:** it is the goal's hint, made plural. The voice ships with software-analysis (the use case's question 6).
- **A hint in the front matter:** `needs` is front matter, where YAML takes comments. How the stamp shows its hint there is #1366's to settle.

**project-kit's own, in `structures.yaml`:** the design's part 9 sketch, with a hint and an example for each. Each is optional, and the list is closed.

| Element | Label | After | Hint | Example |
|---|---|---|---|---|
| `setup` | The setup | `opening` | What this role keeps set up in the project. | which checks the project's merges wait on (`ACT-adopter`) |
| `always-a-person` | Always a person | `setup` | Why no agent may play this role. | the authorisation turns the answers an agent wrote into a person's decision (`ACT-merge-authoriser`) |
| `can-be` | Can be | `always-a-person` | Who may play this role. | project-kit's maintainers, or a fork's (`ACT-methodology-maintainer`) |
| `does` | Does | `can-be` | What this role does, where the opening is too short for it. | choose how much the agents may do without asking (`ACT-operator`) |
| `in-the-model` | In the model | `brings` | How the role appears in the use cases, where its goals belong to others. | its needs are what the system must give an unattended runner (`ACT-ci-pipeline`) |
| `core` | Core | `in-the-model` | What in the core makes this role exist, with the records that say so. | the permission model, its sandbox and the cross-repository gate are this role's controls (`ACT-operator`) |
| `note` | Note | `core` | Side matter: the reason for a name, or an overlap with another role. | the name is not "approver", because project-management uses that word for a reviewer agent (`ACT-merge-authoriser`) |

- **Their hints may carry project-kit's style,** since they are project-kit's own, and the examples quote its own actors. #1368 writes them, and this table is the round's input.
- **The order** is the design's. *The setup* follows the opening, so it comes before the shipped *Comes* (the design's part 4).

**For the build:**

- **The parts (#1363):** the table above, in its order, with each part's hint and example. The actor is a document kind (#1346), and `needs` takes the `sentence` form on the front matter (the design's part 1).
- **The schema (#1346):** it gains the `id` only, unless question 4 adds a field.
- **The stamp and the template (#1366):** rendered from the table, with the hint for `needs` placed in the front matter.
- **project-kit's labels (#1368):** `structures.yaml` as the design's part 9 sketches it, with the hints and examples above.
- **The skill (#1369):** the actor sub-procedure's *Fill it* list gives way to the hints. Its first step, "Is it an actor?", stays, since no hint carries it.
- **DEC-001 first (#1358):** its point 1 names an actor as a role with the needs it brings. A required *Comes*, and *Brings*, go beyond it. So #1358's refinement says so before any build cites it (core rule 2).

**Found on the way:**

- **Two core actors cite a record they do not anchor:** the developer cites ADR-061, and the CI pipeline cites PRJ-002. #1346 moves all eight actors, each with a revalidation, so that change could add them. RS-WRITE-014, still proposed, asks for such anchors.

### Questions for the maintainer

Each question is one decision, with a recommendation.

1. **Is *Comes* required?**
   - **The case:** the design's first cut makes *Comes* and *Brings* optional. Every core actor has *Comes*, and RUP's characteristics and NN/g's context ask for it too. Every actor uses the system (DEC-001 point 1), so each comes at some time.
   - **Recommendation:** yes, required, with no `None.`. *Brings* stays optional.
   - **Else:** optional, as the design's first cut has it.
2. **Do the actor's labels stay *Comes* and *Brings*, or become nouns?**
   - **The case:** the maintainer made the use case's labels nouns, and the journey's are nouns too. The actor's two are verbs, from the style trial, and RS-WRITE-002's example quotes *Comes*.
   - **Recommendation:** keep the verbs. Each completes a sentence about the actor the heading names. No noun fits *Brings* without narrowing it: *Resources* would leave out the CI pipeline's "no person to answer a prompt".
   - **Else:** nouns, such as *Occasions* and *Context*. project-kit then relabels its own to match, and RS-WRITE-002's example changes with them (#1368).
3. **Does the layer line ship, as a part project-kit relabels *Core*?**
   - **The case:** *Core* is in every core actor, as *Comes* is. It says what in the core makes the role exist, often naming the records the actor anchors. An adopter's analysis describes one system, with no layer to name.
   - **Recommendation:** no, it stays project-kit's. DEC-001 point 4 already has each actor anchor what embodies it, or say why nothing does. A shipped part would state the anchors twice, once as data and once in words.
   - **Else:** an optional shipped part, *Basis*, with the hint "What in the system makes this role exist. Name the record or code." project-kit relabels it *Core* (the design's part 4).
4. **Does the opening become front-matter data, so the readers point says who the reader is?**
   - **The case:** the point asks for "who the reader is and what they need". The filler gives the name and the needs, since a tool reads only front matter, so the opening never reaches the point.
   - **Recommendation:** not now. The name and the needs say what a page must serve, and no page names an actor as its reader yet. Revisit when a page first does, and its review finds the name too little.
   - **Else:** a one-sentence field, which the filler adds to the description. The opening leaves the body, as a term's definition is front-matter data (the design's part 6). Three core actors' openings then lose their second sentence to a label.
