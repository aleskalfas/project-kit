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
- **Status:** the use case, the journey, the actor and the glossary term are fully decided, under one rule for every kind ("Decided: across kinds"). So is the author's question on the system's words ("Decided: two terms", under the term). The revalidation record's candidates are compared, and its recommendation follows.

## Decided: across kinds

The maintainer set one rule for every kind on 7 October, in a comment on PR #1374. Every shipped part of a kind is present in every artefact.

- **The rule:**
  - Every part a kind ships is present in every artefact of that kind.
  - A part with nothing to say reads `None.`.
  - A missing part is always an error.
  - A project's own additions stay outside the rule. Each is optional unless the project marks it required.
- **Why:** `None.` is a deliberate answer. So a script can tell a part considered with nothing to say from a part forgotten.
- **Where it is recorded:** in software-analysis DEC-001, by #1358's refinement.
- **Its effects on the decided kinds:** six parts become required, with `None.` allowed.
  - the use case's *Other actors* and *Assumptions*, which were optional
  - the journey's *Variants* and *Minimal guarantees*, which were optional
  - the actor's *Occasions* and *Context*, which the round had recommended so
- **Which parts may read `None.`:** each kind's table says. A part that every artefact has something for may not, such as a goal, a main path or an actor's opening.
  - **The round's reading:** the rule's "a part with nothing to say" leaves those parts as they were decided, required with no `None.`.
- **Front matter, in the round's reading:** the rule is about a body's parts. A front-matter list with nothing to hold stays absent, as `replaces` does on a term never renamed (`SA/schemas/term.schema.json`).
  - So a use case whose *Other actors* reads `None.` has no `involves`.
  - A journey whose steps need nothing from outside it has no `relies-on`.
- **What it changes in the design's first cut:**
  - **Its part 1** checks an optional element only when present. That now holds only for a project's additions.
  - **Its part 2** shows optional parts in a template, for the writer to delete. A shipped part is never deleted now, and the writer replaces its hint with `None.`.
- **For the build:**
  - **DEC-001 (#1358):** its paragraph on a kind's structure states the rule.
  - **The declaration (#1363):** every shipped element is required. A flag on each says whether it may read `None.`, and `required: false` is left to a project's additions (the design's part 4).
  - **The check (#1364):** a missing shipped part is an error, and `None.` passes only where its element allows it.
  - **The stamp and the templates (#1366):** they render every shipped part with its hint. A project's optional addition is rendered too, and the writer deletes it when they have nothing for it.
- **The glossary term, under the rule:** both its parts are required, with `None.` allowed ("Decided: the glossary term").
- **The kind still to come:** the revalidation record. Its stamp writes `None found.` under *Gaps* (`SA/scripts/_lib/revalidation.py`), so its round weighs that against `None.`.

## The use case

The maintainer chose nine parts: the design's five, two of them renamed, three of Cockburn's further parts, and *Assumptions*. Under the rule for every kind, all nine are present in every use case. The round had recommended the five alone, and its comparison and recommendation stay below as they were made.

### Decided: the use case

The maintainer chose the use case's parts and their labels on 6 October, in comments on PR #1374, and then answered its last two questions. Every question of the use case is now decided. F fills the parts with both examples (`use-case/chosen-template.md`).

- **Added, with the maintainer's reasons:**
  - *Other actors*, required with `None.` allowed: the other actors who take part, each with what the use case must protect for them. It is Cockburn's stakeholders and interests, added for completeness.
    - **Required since 7 October,** by the rule for every kind. It was first optional.
  - *Preconditions*, required: what the system, or an earlier use case, has already made true before the use case starts. A journey's seams need them, since a seam is where one use case's end must meet the next one's start.
    - **The reason changed** with the journey's question 2. Journeys carry their own hand-overs, and the part records the rare state an earlier use case set up that nothing checks again.
  - *Assumptions*, required with `None.` allowed: what must also be true for the use case to work, but nothing in the system secures. Each names the record that admits it, and each is a candidate for a check. Question 5 gives the reasons.
    - **Required since 7 October,** by the rule for every kind. It was first optional.
  - *Minimal guarantees*, required: what the system still guarantees when the use case ends early or fails. pkit's safety guarantees need a part of their own. It is Cockburn's minimal guarantee, and the round's *Always holds*.
- **Renamed:** *Starts when* is now *Trigger*, and *Done when* is now *Postconditions*, the pair to *Preconditions*.
- **Every label a noun:** the maintainer chose the labels after the parts, in a later comment on the pull request. *Other actors* and *Minimal guarantees* were first *Also involved* and *If it fails*.
- **Otherwise, start small:** any other part is added once real use cases show it recurs.
- **Where each part ships:** with software-analysis, as the round recommended. The maintainer's comments leave that as it was.
- **The actor's voice ships too:** the goal is one sentence in the actor's own voice, as each of an actor's needs is (question 6). It is the mainstream user-story convention, not project-kit's alone. A project that prefers another voice replaces the hint in its own settings.
  - **It may start with *Never*:** a goal starts with its verb, or with *Never* and the verb (the actor's question 4).
- **The append-only check:** a check keeps a use case's steps and variants append-only, filed as #1375 (question 4).

**The declaration #1363 takes, in this order:**

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# UC-NNN — <title>` | yes | heading | none, since the stamp writes it | `# UC-007 — Export the report as a file` |
| `goal` | Goal | yes | `sentence` | What the actor wants from this use case, in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. | Export my report as a file. |
| `other-actors` | Other actors | yes, and `None.` is allowed | none | Each other actor who takes part, and what this use case must protect for them. Write `None.` when there is none. | **Auditor** (`ACT-auditor`): each export is logged with who made it. |
| `preconditions` | Preconditions | yes, and `None.` is allowed | none | What the system, or an earlier use case, has already made true before the use case starts. Each is a state, not an event, and no step checks it. Write `None.` when there is none. | The analyst is signed in. |
| `assumptions` | Assumptions | yes, and `None.` is allowed | none | What must also be true for the use case to work, but nothing in the system secures. Name the record that admits each. Write `None.` when there is none. | The disk keeps the file as the system wrote it (DEC-003). |
| `trigger` | Trigger | yes | none | The event that starts the use case, and who or what causes it. | The analyst asks to export the report on screen. |
| `main-path` | Main path | yes | `numbered-steps` | Numbered steps from the start to the goal, each saying who does what. | 1. The analyst chooses `Export`. 2. The system writes the report to a file. |
| `variants` | Variants | yes, and `None.` is allowed | `variants` | One for each condition, lettered after the step it branches from. Say what happens instead, and where the path rejoins or ends. Write `None.` when there is none. | 2a. The disk is full. The system says so and writes nothing, and the use case ends. |
| `postconditions` | Postconditions | yes | none | The state that shows the goal is met. | The file holds the whole report. |
| `minimal-guarantees` | Minimal guarantees | yes, and `None.` is allowed | none | What the system still guarantees when the use case ends early or fails. Name the record or code each rests on. Write `None.` when there is none. | A failed export leaves no partial file (DEC-003). |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it.
- **The examples:** one neutral use case runs through them all, the design's export. An auditor and a decision of the example's own complete it.
- **The actor's voice:** the goal's hint names it, and its example is in it (question 6). The voice is the method's now, so it is no project's style that the neutral floor of the design's part 5 keeps out.
- **The goal's hint, split:** as one sentence it ran to 28 words, over RS-WRITE-005's limit. It is two sentences now, and asks the same. The journey's round found it.
- **The goal's hint, with *Never*:** its second sentence gains "or with *Never* and the verb" (the actor's question 4). It runs to 19 words.
- **`None.` where a part may read it:** the hints of *Other actors* and *Assumptions* gain the line the other three such parts have, "Write `None.` when there is none."

**The front matter gains `involves`:**

- **What it holds:** the actors of *Other actors*, by id, as a list, such as `involves: [ACT-merge-authoriser, ACT-ci-pipeline]`. It is absent where the part reads `None.`.
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
5. **Question 5, a fact the use case relies on that the system does not secure:** option (c). It goes in *Assumptions*, a part of its own, and *Preconditions* stay strict. The part is required, with `None.` allowed, since the rule for every kind.
6. **Question 6, the actor's voice in the goal hint:** option (b). The first-person voice ships with software-analysis for every project, for an actor's needs and a use case's goal.

**What filling F showed:**

- **The landing's precondition:** it sat in A's *Starts when*. A's trigger read "a committed change", which is a state. F moves the state to *Preconditions*, and *Trigger* keeps the event.
- **E's precondition:** none, so the part reads `None.`. Neither example lists "pkit is installed". Every use case would share it, as "the system is running" would.
- **Facts outside the system:** the landing relies on three that no step checks and nothing in the system secures. F lists them under *Assumptions*, each with the record that admits it.
  - **Where `gh` goes:** the maintainer's example. The caller's environment and the working directory's remote decide the target (ADR-061 point 4), and the guard compares directories only (`session_guard.py`).
  - **The title at a queue's merge:** the queue reads the title at the merge, and the landing makes no rule of a title changed since (ADR-061 point 8).
  - **How soon the service shows a change:** the code names it an assumption (`pull_request_landing.py`). ADR-061 point 7 admits that the service may still apply a change two readings did not see.
- **The four questions, applied:** the committed change is a precondition. GitHub as the host is checked, so it stays variant 6e. The three facts above are assumptions.
- **E's assumptions:** none, so E first left the part out, as it left out *Other actors*. Since the rule for every kind, both read `None.`.
- **The goals, in the voice of question 6:** both already read so, and F keeps them as they are.
  - The landing's starts with *Land*, and says *my change*.
  - E's starts with *Think*. The developer never refers to itself in it, so it needs no *my*.
  - E's repeats one of the developer's needs word for word, and the landing's is the first part of another (`ACT-developer`).
- **Who is involved:** the landing involves four actors, and E involves none, so E's part reads `None.` and its front matter has no `involves`.
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
- **Length:** the landing runs to 1,443 words, against A's 960 and B's 1,282. E runs to 338 with its three parts that read `None.`, against 259 in the recommended parts.

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
- **Why this one:** it crosses three actors and has twenty variants, so it tests every part. It is also heavy on mechanism, so a second, ordinary example checks the recommendation (`use-case/considered/E-second-example.md`).
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

- **A, today's template** (`use-case/considered/A-todays-template.md`): exactly the parts of `SA/templates/use-case.md`. They are *Goal*, *Starts when*, *Main path*, *Variants* and *Done when*. The template's instruction line under *Variants* stays, as in every artefact filled from it.
- **B, Cockburn's fully dressed form** (`use-case/considered/B-fully-dressed.md`): his template's parts, in his order, adapted only where pkit requires.
  - *Primary actor* is the front matter's `actor`, so the body does not repeat it.
  - The front matter carries the id and the friction block.
  - *Extensions* keep his numbering, a letter after the step and then numbered sub-steps, such as `7a1`.
  - *Goal in context* opens with the one-sentence goal (DEC-001 point 1). Its second sentence is the context his template asks for.
  - *Related information* holds two items, the frequency and the open issues. His template leaves that part to each project.
- **C, Cockburn's casual form** (`use-case/considered/C-casual.md`): the main path as a short story, then the variations in prose. His casual "Buy something" (Use Case 4) is the model.
- **D, the design's first cut:** equal to A in its parts, their order and their labels. It differs from A in three ways, and only the first shows in a filled artefact:
  - no instruction line under *Variants*, so a filled D is A without that line
  - each part stamped with a one-line hint, which the writer replaces
  - every part required and checked, with *Variants* allowed to read `None.`
- **E, a second example in the recommended parts** (`use-case/considered/E-second-example.md`): the developer thinks a question through in a scratchpad note. It is an ordinary use case, with six steps and three variants.
- **F, the chosen template** (`use-case/chosen-template.md`): the maintainer's nine parts, filled with both examples, the landing and E. It came after the recommendation, and "Decided: the use case" says what filling it showed.
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
| F | 9: *Goal*, *Other actors*, *Preconditions*, *Assumptions*, *Trigger*, *Main path*, *Variants*, *Postconditions*, *Minimal guarantees* | All nine. *Other actors*, *Preconditions*, *Assumptions*, *Variants* and *Minimal guarantees* may read `None.`, under the rule for every kind. | 1,443 | The other actors as data and anchors, the precondition apart from the trigger, three assumptions, and seven guarantees, each with its record or code | Three interests restate actors' needs. *Minimal guarantees* restates ADR-061 point 5's obligations, and *Assumptions* restate what its points 4, 7 and 8 admit. |

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
    - **Decided otherwise:** *Preconditions* comes, required, since a journey's seams need it. The landing's committed change, which no step checks, is its one precondition. *Assumptions* comes too, for what no step checks and nothing in the system secures (question 5). It is required with `None.` allowed, as *Preconditions* is, under the rule for every kind.
  - **A guarantee over every end, *Always holds*:** the strongest candidate. Question 2 asks about it.
    - **Decided otherwise:** it comes now as *Minimal guarantees*, required, since pkit's safety guarantees need a part of their own.
  - **Scope:** real in pkit, since a use case belongs to the core or to a capability. An area can carry it (`--area`, DEC-001 point 2), and so can the goal's wording.
  - **Level:** DEC-001 names no levels, and a journey already covers a path across use cases. A level would need a rule that DEC-001 lacks.
  - **Stakeholders and interests:** two of the main example's four interests repeat actors' needs, and the steps name the other actors.
    - **Decided otherwise:** they come as *Other actors*, limited to actors, for completeness. The part is required, with `None.` allowed, under the rule for every kind. The actors are also listed as data in the front matter.
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
   - **Decided:** option (c), a part of its own. *Preconditions* stay strict, and such a fact goes in *Assumptions*, right after them. The part was optional, and the rule for every kind made it required, with `None.` allowed.
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

The maintainer chose five parts for the journey: *Goal*, *Steps*, *Variants*, *Postconditions* and *Minimal guarantees*. Under the rule for every kind, all five are present in every journey. Each step carries what it needs from the path, so the round's *Seams* part goes. The comparison and the recommendation stay below as they were made.

### Decided: the journey

The maintainer decided the journey on 7 October, in comments on PR #1374. The journey is fully decided, and G fills its parts with the adopter's first day (`journey/chosen-template.md`).

- **The name stays *journey*:** a summary-level path an actor takes across several use cases, with the seams between them.
  - It is explicitly not a UX journey map.
  - The engineering usage matches ours, such as critical user journeys in reliability engineering and end-to-end testing.
  - The hint and the README say so.
- **The parts, in order:**
  - *Goal*, required: one sentence in the actor's own voice, as a use case's goal is. It starts with its verb, or with *Never* and the verb (the actor's question 4).
  - *Steps*, required: one line for each step, the use case's id and its title exactly as the use case states it, such as `2. UC-002 — See how pkit is wired into my project`. Under a step, one line for each hand-over it relies on.
  - *Variants*, required with `None.` allowed: the journey's own branches.
  - *Postconditions*, required: the state that shows the whole path succeeded.
  - *Minimal guarantees*, required with `None.` allowed: what still holds when the path stops before its end.
  - **Since 7 October:** *Variants* and *Minimal guarantees* were first optional. The rule for every kind made them required.
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
| `goal` | Goal | yes | `sentence` | What the actor wants from the whole path, in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. | Build my first report and export it as a file. |
| `steps` | Steps | yes | `steps-match-front-matter` | One line for each use case in `steps`, in order: its id and its title as the use case states it. Under a step, add one line for each hand-over it needs from an earlier step or from a use case outside the journey. Say what it receives and how that can break. | `3. UC-007 — Export the report as a file`, and under it `**Needs from step 2 (UC-005):** the report the analyst saved. A report left unsaved is not offered for export.` |
| `variants` | Variants | yes, and `None.` is allowed | `variants`, read against *Steps* | One for each branch of the whole path, lettered after the step it leaves. Say where the path rejoins or ends. Write `None.` when there is none. | 3a. The analyst wants a second report, and the path rejoins at step 2. |
| `postconditions` | Postconditions | yes | none | The state that shows the whole path succeeded. | The analyst holds a file with their first report. |
| `minimal-guarantees` | Minimal guarantees | yes, and `None.` is allowed | none | What still holds when the path stops before its end. Name the record or code each rests on. Write `None.` when there is none. | Stopping after any step leaves every saved report as it was (DEC-003). |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it. The stamp writes each hand-over's label, so the hint for *Steps* names none.
- **Since 7 October:** the goal's hint gains "or with *Never* and the verb", as the use case's does. The hints of *Variants* and *Minimal guarantees* gain "Write `None.` when there is none."
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

- **A, today's template** (`journey/considered/A-todays-template.md`): exactly the parts of `SA/templates/journey.md`. They are *Starts*, *Steps*, *Seams to watch* and *Done when*. The instruction line under *Seams to watch* stays, as in every artefact filled from it.
- **B, a journey map** (`journey/considered/B-journey-map.md`): NN/g's components and Adaptive Path's building blocks, adapted only where pkit requires.
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
- **D, Cockburn's summary-level use case** (`journey/considered/D-summary-use-case.md`): his fully dressed parts at the summary level, adapted as the use case's B was.
  - His section 5.2 gives the model. A summary use case's steps are user-goal use cases, and it has one primary actor (Use Case 6, *Operate an Insurance Policy*).
  - Each step names its use case by id, in place of his italics. Step 6 names two, the adopter's UC-xx5 and the developer's landing.
  - Each break is an extension of the step where its condition arises. Its sub-steps say where the break shows and where the path resumes, as 1b does for a private install.
- **E, the use case's decided parts** (`journey/considered/E-use-case-parts.md`): the nine parts the maintainer chose for the use case, carried to the journey. *Steps* and *Seams* stand in place of *Main path* and *Variants*.
  - Each seam pairs the earlier use case's *Postconditions* with the next one's *Preconditions*, then gives its *Risk*. These are the pairs the brief for this round suggested.
  - Each *Preconditions* follows the decided hint, a state that no step checks. Every one reads none, since each next command checks what it needs.
  - The front matter gains `involves`, as the use case's does.
- **F, a second example in the recommended parts** (`journey/considered/F-second-example.md`): the adopter upgrades the methodology and re-pins a rule set. It has two steps and one seam, and it leaves out both optional parts.
- **G, the chosen template** (`journey/chosen-template.md`): the maintainer's five parts, filled with the adopter's first day. It came after the recommendation, and "Decided: the journey" says what filling it showed.

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
| G | 5: *Goal*, *Steps* with each step's hand-overs, *Variants*, *Postconditions*, *Minimal guarantees* | All five. *Variants* and *Minimal guarantees* may read `None.`, under the rule for every kind. | 595 | Each hand-over under the step that needs it, naming the step it comes from. The landing as data and as an anchor. | Variant 1a restates the private install that step 6's hand-over from step 1 names. |

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

**Decided otherwise.** The maintainer nested each hand-over under the step that needs it, so no *Seams* part ships, as "Decided: the journey" says. The two optional parts became required, with `None.` allowed, under the rule for every kind. This recommendation stays as it was made, and each point the decisions turned is marked below.

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
  - **Decided otherwise:** both are required, with `None.` allowed, under the rule for every kind. F would write `None.` in each.
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

The maintainer chose an opening and two noun-labelled parts, *Occasions* and *Context*, both required with `None.` allowed. project-kit's own labels become nouns too, and stay project-kit's. The comparison and the recommendation stay below as they were made.

### Decided: the actor

The maintainer decided the actor on 7 October, in comments on PR #1374. The actor is fully decided. G shows it twice (`actor/chosen-template.md`): the developer as project-kit holds it, and the CI pipeline in the shipped parts alone.

- **What ships with software-analysis:**
  - the heading, which the stamp writes
  - an opening, required: what the role is, and what it does with the system
  - *Occasions*, required with `None.` allowed: when the actor comes to the system
  - *Context*, required with `None.` allowed: what the actor comes with
  - in the front matter, each need in one sentence, in the actor's own voice
- **The round's questions:**
  1. **Question 1, the two parts required:** answered by the rule for every kind. *Occasions* and *Context* are required, with `None.` allowed, as recommended.
  2. **Question 2, the labels:** option (b). software-analysis ships the nouns *Occasions* and *Context*, and project-kit adopts nouns for its own actor parts too.
     - **Decided otherwise:** the round recommended that project-kit relabel the two *Comes* and *Brings*. It relabels nothing that ships.
     - **When:** the eight actors take the noun labels as they move to one file each (#1346).
  3. **Question 3, the layer line:** it stays project-kit's own, as its *Core* part, and does not ship. As recommended.
  4. **Question 4, *Never*:** option (a). A need or a goal starts with its verb, or with *Never* and the verb. The hints for the needs and for the use case's and the journey's goals say so, and #1360's format rule allows it. As recommended.
- **project-kit's labels, in order:** its seven additions are optional, in its own settings. The two shipped parts sit among them.
  - *Setup*, which was *The setup*
  - *Human role*, which was *Always a person*
  - *Role holders*, which was *Can be*
  - *Activities*, which was *Does*
  - *Occasions* and *Context*, the shipped parts, which were *Comes* and *Brings*
  - *Place in the model*, which was *In the model*
  - *Core* and *Note*, as they were
- **As recommended:** the actor is a role, not a persona. RUP's further characteristics, its relationships and the persona's parts stay out, for the reasons the recommendation gives.

**The declaration #1363 takes, for the body, in this order:**

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# ACT-<slug> — <name>` | yes | heading | none, since the stamp writes it | `# ACT-analyst — Analyst` |
| `opening` | none | yes | none | What this role is, and what it does with the system. | Someone who builds reports from their team's figures. |
| `occasions` | Occasions | yes, and `None.` is allowed | none | On what occasions the actor comes to the system. Write `None.` when there is none. | At the end of each week, and whenever a manager asks for figures. |
| `context` | Context | yes, and `None.` is allowed | none | What the actor comes with, such as data, authority or a limit. Write `None.` when there is none. | A spreadsheet of their team's figures, and no right to publish a template. |

**The front matter's form, apart from the body:**

| Field | Form | Hint | Example |
|---|---|---|---|
| `needs` | `sentence`, on each item | What the actor needs from the system, each in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. | Export my report as a file. |

- **Both tables are the recommendation's,** unchanged. The decisions confirmed each shipped part, its label and its hint.
- **The needs' hint in the front matter:** it stays the placeholder need, which the placeholder check refuses when left in (`check.py`). That differs from the body's hints, so #1363 and #1366 say so.

**project-kit's additions, in its `structures.yaml` under the kind `actor`:**

| Element | Label | After | Hint | Example |
|---|---|---|---|---|
| `setup` | Setup | `opening` | What this role keeps set up in the project. | which checks the project's merges wait on (`ACT-adopter`) |
| `human-role` | Human role | `setup` | Why no agent may play this role. | the authorisation turns the answers an agent wrote into a person's decision (`ACT-merge-authoriser`) |
| `role-holders` | Role holders | `human-role` | Who may play this role. | project-kit's maintainers, or a fork's (`ACT-methodology-maintainer`) |
| `activities` | Activities | `role-holders` | What this role does, where the opening is too short for it. | choose how much the agents may do without asking (`ACT-operator`) |
| `place-in-the-model` | Place in the model | `context` | How the role appears in the use cases, where its goals belong to others. | its needs are what the system must give an unattended runner (`ACT-ci-pipeline`) |
| `core` | Core | `place-in-the-model` | What in the core makes this role exist, with the records that say so. | the checks bind once the project makes them a required status (COR-050 point 12) (`ACT-ci-pipeline`) |
| `note` | Note | `core` | Side matter: the reason for a name, or an overlap with another role. | the name is not "approver", because project-management uses that word for a reviewer agent (`ACT-merge-authoriser`) |

- **Each addition is optional,** and the list is closed, naming RS-ANALYSIS-002 (the design's part 4). An actor leaves out an addition it has nothing for.
- **No relabel:** project-kit takes *Occasions* and *Context* as they ship, so its file relabels nothing.
- **The ids follow the labels.** None has reached the default branch, so none is permanent yet (the design's part 4).
- **The hints and the examples** are the recommendation's. The examples quote project-kit's own actors, as its own additions may.
- **The order** is the maintainer's list. *Setup* names the opening, so it comes before the shipped *Occasions* (the design's part 4).

**What filling G showed:**

- **The relabel keeps every item's words.** The developer's two items read under *Occasions* and *Context* as they did under *Comes* and *Brings*. So the move changes labels and no claim (RS-WRITE-013).
- **The developer uses two of the seven additions,** *Core* and *Note*. The other five show in other actors, as "At a glance" counts them.
- **The anchors gain ADR-061,** which the developer's *Core* cites. #1346 adds it, as "For the build" says.
- **The CI pipeline in the shipped parts alone** is F, unchanged, since F already had the noun labels. It shows what an adopter's actor holds when the project adds nothing of its own.
- **An actor with nothing for *Context*:** the AI agent has no *Brings* today. Under the rule for every kind, its *Context* reads `None.`.
- **Length:** the developer runs to 93 words, as B does. The CI pipeline runs to 61.

**For the build:**

- **The parts (#1363):** the two tables of the shipped parts above. The actor is a document kind (#1346).
- **The schema (#1346):** it gains the `id` only.
- **The move (#1346):** the eight actors move to one file each, and take the noun labels as they move.
  - **The labels:** *The setup* becomes *Setup*, *Always a person* becomes *Human role*, and *Can be* becomes *Role holders*. *Does* becomes *Activities*, *Comes* and *Brings* become *Occasions* and *Context*, and *In the model* becomes *Place in the model*.
  - **The words:** every item keeps them, so the move changes no claim.
  - **The AI agent:** it gains *Context*, reading `None.`, under the rule for every kind.
  - **The missing anchors:** the five citations the round found become anchors in the same change. These are ADR-061 in the developer, PRJ-002 in the CI pipeline and DEC-028 in the merge authoriser. CONTRIBUTING.md becomes a path anchor of the methodology maintainer and of the operator.
  - **The revalidations:** each actor owes one for its move already (COR-050 point 3). A changed anchor list owes one too (COR-050 point 6), so the same answer covers both.
- **The stamp and the template (#1366):** the body is rendered from the table, every shipped part with its hint. The needs' hint is the placeholder need, in the front matter written by hand.
- **project-kit's labels (#1368):** `structures.yaml` carries the seven additions as data, each with its hint and example, under the kind `actor`, closed, naming RS-ANALYSIS-002. It relabels nothing.
  - **WRITE's examples:** RS-WRITE-002's example quotes *Comes*. RS-WRITE-003's calls *Can be* the core actors' label, and RS-WRITE-006's says the same of *Brings*. #1368 already fixes RS-WRITE-002's stale example, so it brings all three in line with the new labels.
- **The voice's exception (#1360 and #1363):** the format rule's *How* lets *Never* come before the verb. The hints for the needs and the goals say so. #1368's rule on the voice goes, as decided for the use case.
- **What an actor is not (#1366 and #1369):** the template's head and the README say an actor is a role, not a persona.
- **The skill (#1369):** the actor sub-procedure's *Fill it* list gives way to the hints. Its first step, "Is it an actor?", stays, since no hint carries it.
- **DEC-001 first (#1358):** its point 1 names an actor as a role with the needs it brings. The opening, *Occasions* and *Context* go beyond it, so #1358's refinement says so before any build cites it (core rule 2).
- **The readers point, later:** when a page first names an actor as its reader, its review shows whether the name and the needs say enough. If not, the opening becomes a front-matter field the filler reads.
- **A possible form, not decided:** every record and file a body names is among its anchors. It would have caught the five citations above, and would serve every kind.

### The example

The main example is a real core actor, the developer, as merged on main (`tech-docs/analysis/use-case-model/actors.md`).

- **One file per actor** (#1346): each candidate is the file `use-case-model/actors/ACT-developer.md` would be, headed `# ACT-developer — Developer`. Its front matter gains the `id` that #1346 adds to the actor's schema.
- **Why this one:** the developer is the primary actor of both of the use case's examples, the landing and the scratchpad note. Its body uses four of the core actors' nine labels, and each core actor uses four or five.
- **The same in every candidate:** the front matter, with its nine needs and its one anchor, COR-009, as on main. Only the body differs.
- **A second example:** the CI pipeline, an actor that is no person. E holds it as merged, and F holds it in the parts software-analysis would ship alone.
- **Derived from:**
  - the core actors as merged
  - COR-008, COR-009 and ADR-061, for C's characteristics
  - COR-050, for D's frustrations

**What the example left unclear.** The round decides none of these.

1. **Records cited and not anchored.** The developer's *Core* cites ADR-061 point 3, and its one anchor is COR-009. The CI pipeline's *Note* cites PRJ-002, beside its anchors COR-054 and COR-050. So a change to ADR-061 point 3, which #1222 may bring, never flags the developer. The candidates A to F keep main's anchors.
   - **Decided:** the citations become anchors when the actors move (#1346). G's developer anchors ADR-061.
2. **C's and D's citations.** C cites COR-008 and ADR-061, and D cites COR-050. Filled for real, each would anchor them, as the journey's candidates found for PRJ-004.
3. **D's persona is invented.** No research of developers exists, so its name, age, bio and behaviours are made up. Its goals and frustrations could only come from the needs and the records, so they restate them.
4. **No use case is stamped yet.** C's *Relationships* name the landing as `UC-xxx`, the id the use case's round gave it.

### The candidates

Each candidate is complete and filled, as the actor's file would read on the default branch after #1346.

- **A, today's template** (`actor/considered/A-todays-template.md`): the front matter and one prose section, as `SA/templates/actors.md` asks. Its placeholder asks who this is, when they come to the system, and what they bring with them. So A has no place for the developer's *Core* and *Note*, and drops them.
- **B, the core actors' labels** (`actor/considered/B-core-actors-labels.md`): the developer exactly as merged. These are project-kit's labels, from the style trial, as the design's part 9 lists them.
  - The opening says who the role is, with no label.
  - The list, in order: *The setup*, *Always a person*, *Can be*, *Does*, *Comes*, *Brings*, *In the model*, *Core* and *Note*. Each actor leaves out a label it has nothing for (RS-WRITE-002).
  - The developer uses *Comes*, *Brings*, *Core* and *Note*.
- **The design's first cut** ships B's opening, *Comes* and *Brings*, with the opening required (the design's part 8). project-kit adds the other seven labels (its part 9). So for project-kit the first cut reads as B, and it has no file of its own.
- **C, RUP's actor description** (`actor/considered/C-rup-actor.md`): RUP's actor properties, adapted only where pkit requires.
  - *Name* is the front matter's `name` and the heading.
  - *Brief description* holds the role's sphere of responsibility and what it needs the system for. The needs stay in the front matter, so it summarises them.
  - *Characteristics* holds RUP's list for a human actor, with the frequency of use its guidelines add. Age, gender and cultural background are left out, since nothing about the developer states them.
  - *Relationships* holds RUP's two kinds, the use cases the actor takes part in and its generalisation. RUP's *Diagrams* are left out, since the analysis has none.
- **D, a UX persona** (`actor/considered/D-ux-persona.md`): NN/g's common pieces, in its order, with three parts its example persona shows.
  - NN/g's pieces: *Persona* for the name and age, then *Tagline*, *Experience*, *Context*, *Goals and concerns* and *Quote*. The photo is left out, since the file is text.
  - From its example persona: *Bio*, *Behaviors* and *Frustrations*. Its tasks are left out, since an actor's tasks are its use cases.
  - The needs stay in the front matter, as in every candidate.
- **E, a second example** (`actor/considered/E-second-example.md`): the CI pipeline as merged, in one file. Its opening says why it is an actor, and it uses *In the model*.
- **F, the shipped parts alone** (`actor/considered/F-shipped-parts-only.md`): the CI pipeline as an adopter's template would stamp it under the recommendation, with no label of project-kit's. Its two labels are the nouns question 2 recommends.
- **G, the chosen template** (`actor/chosen-template.md`): the developer as project-kit holds it after the decisions, and F's CI pipeline. It came after the recommendation, and "Decided: the actor" says what filling it showed.

**Sources.** RUP's actor and the persona were read from these pages:

- **RUP:** the actor artefact ([page](https://www.cin.ufpe.br/~if682/RUP/process/artifact/ar_actor.htm)). Its properties are *Name*, *Brief Description*, *Characteristics*, *Relationships* and *Diagrams*.
  - *Brief Description* is "the actor's sphere of responsibility and what the actor needs the system for".
  - *Characteristics* are "for human actors". They are the physical environment, the number of users the actor represents, their domain knowledge, computer experience and other applications, and general characteristics.
  - *Relationships* are "actor-generalizations, and communicates-associations in which the actor participates". A communicates-association links an actor to a use case.
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

C and D say the most, and much of it describes people rather than their dealings with the system. A says the least, and drops the layer line. Words are counted as in the earlier rounds: the body, labels included, with the heading and front matter left out.

| Candidate | Parts | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 1, unlabelled: who the role is, when they come, what they bring | None marked. Today's check catches a placeholder left in, not a part deleted. | 45 | Nothing. It reads fastest. | Nothing, but it drops the layer line and the note |
| B | The opening, then 4 of the 9 labels: *Comes*, *Brings*, *Core*, *Note* | None marked | 93 | The layer line: what in the core makes the role, and what of it is provisional. A work tracker's view of the role. | Nothing |
| C | 3: *Brief description*, *Characteristics* with six items, *Relationships* with two | None marked. RUP leaves the choice to tailoring. | 175 | How many people play the role, the experience it asks, and the applications they use | The brief description summarises the needs. *Frequency of use* is B's *Comes*, and *Environment* and *Other applications* hold B's *Brings*. *Use cases* repeat the use cases' own `actor`. |
| D | 9: *Persona*, *Tagline*, *Bio*, *Experience*, *Context*, *Behaviors*, *Goals and concerns*, *Frustrations*, *Quote* | None marked | 221 | Speed, a quality the developer weighs against accuracy and thoroughness | *Accuracy*, *Thoroughness*, every frustration and the quote restate needs, some inverted. *Context*'s frequency is B's *Comes*. |
| E | The opening, then 5 of the 9 labels: *Comes*, *Brings*, *In the model*, *Core*, *Note* | As B | 180 | Why a system is an actor, and whose goals its runs serve | Nothing |
| F | The opening, *Occasions*, *Context* | All three, as recommended | 61 | Why a system is an actor | Nothing. It lacks whose goals the runs serve, the layer and project-kit's wiring. |
| G, the developer | The opening, *Occasions*, *Context*, then 2 of project-kit's 7 additions: *Core*, *Note* | The opening, *Occasions* and *Context*. The two parts may read `None.`. | 93 | As B, with noun labels and ADR-061 anchored | Nothing |

**Note:** G came after the recommendation, and its row is added here to compare. Its CI pipeline is F's.

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

**What each source calls the same thing.** The core actors, RUP and the persona each say when the actor meets the system and what it comes with. Only the core actors and RUP describe the role itself.

| B | RUP | NN/g's persona, and Cooper |
|---|---|---|
| `name` and the heading | *Name* | the name, a person's rather than a role's |
| `needs` | in *Brief Description*: "what the actor needs the system for" | *Goals and concerns*, and Cooper's goals |
| The opening, and *Does* | in *Brief Description*: "sphere of responsibility" | none. The tagline sums up a person. |
| *Comes* | a characteristic from the guidelines: the frequency of use | in the context: "How often would they use it?" |
| *Brings* | characteristics: the environment and other applications | in the context: the device, and whether the job requires the product |
| *Can be* | in the guidelines: several users can play one actor | none |
| *In the model*, *Core*, *Note*, *The setup*, *Always a person* | none | none |
| none, since the use cases name their actors | *Relationships* | the example's tasks, and Cooper's tasks |
| none | the number of users, domain knowledge, computer experience and general characteristics | the age, gender, photo, tagline, bio, experience level, behaviours, frustrations and quote, and Cooper's skill levels |

### Fit with pkit

The parts about the role's dealings with the system fit pkit, and the parts about the people who play it do not. A, B, E and F hold only the first kind.

- **The needs stay data** (the design's Decided 2, and #1346). Every candidate keeps them in the front matter, where the schema checks them and the readers filler reads them (`SA/scripts/_lib/readers.py`).
  - A body part that restates them is a second copy, which #1346 rules out.
  - C's *Brief description* summarises them. D's *Goals and concerns*, *Frustrations* and *Quote* restate four of them, some inverted.
- **The voice** (the use case's question 6):
  - Every candidate keeps the needs as merged. 51 of the 52 core needs start with their verb.
  - The methodology maintainer's need starts with *Never*. It reads "Never ship a backbone change that breaks installed projects without the migration that carries them across". RS-WRITE-013 keeps that wording as its example, since "Ship … only with" changes the meaning.
  - The design kept "*Never* may come before the verb" in project-kit's rule on the voice (its part 9, and #1368). The voice moved to software-analysis, and the decided hint says only "Start with the verb". So the exception has no home yet (question 4).
  - The voice holds for a system. Each of E's needs starts with its verb, and none needs *I* or *my*.
- **What reaches a reader** (DEC-001 point 8):
  - The filler gives each actor as a reader, such as `act-developer`, with its name and its needs as the description.
  - The point's schema asks the description for "Who the reader is and what they need from the documentation" (living-docs' `readers.schema.json`). The needs say what the role needs from the system. The opening, its *who*, never reaches the point.
  - A tool reads only front matter (the design's Decided 2), so the opening would reach the point only as a field.
  - No page names an actor as its reader yet. Every page names `user` or `maintainer`, so the round leaves this until one does ("For the build").
- **Anchors** (DEC-001 point 4):
  - **Records only, for the core actors.** In the developer, the CI pipeline and the merge authoriser, the records an actor anchors are among those its *Core* names. *Core* names more, such as the acceptance gate and ADR-061 point 3 in the developer's.
  - **Cited and not anchored:** five core actors cite a record or a file they do not anchor ("Found on the way").
  - **What an actor's change flags.** An artefact anchor changes whenever the anchored artefact's body or own fields change (COR-050 point 5).
    - A use case anchors its actor, and now each actor in `involves`. A journey anchors its actor.
    - So every edit to an actor's body flags each use case and journey that names it, and each needs an answer.
    - A part that changes often costs most. When #1222 settles where the landing lives, B's *Core* changes. Every use case of the developer is then flagged, the scratchpad note's use case included, though the landing's home never touches it.
    - project-kit's *Note* costs the same. It is side matter that no use case relies on (RS-WRITE-004). Each edit to it still flags every use case and journey of the actor.
    - D's *Bio* and *Behaviors* change with the team, not with the software, and so does C's *Number of users*.
  - **Relations between actors stay prose.** The component author's and the operator's *Note* each name another actor. As data and anchors, two actors that named each other would form a cycle, which COR-050 point 5 makes an error.
- **The membership test** (DEC-001): an artefact belongs in the analysis "if a change to the software can make it false". The round applies it to each part, as the journey's round applied it to *Feeling*. The line falls between a part about the role's dealings with the system and a part about the people who play it.
  - **The role's dealings:** the needs and the opening, and every label of B, E and F. C's *Brief description*, *Environment*, *Frequency of use*, *Other applications* and *Relationships*. D's *Context*, *Goals and concerns* and *Frustrations*, since each frustration rests on a record.
  - **Closest to the line:** *Comes*. A person's occasions, such as the operator's "every working day", are a habit as much as a dealing.
  - **The people:** D's *Persona*, *Tagline*, *Bio*, *Experience*, *Behaviors* and *Quote*. C's *Number of users*, *Domain knowledge* and *Computer experience*.
    - As filled, C's *Number of users* and *Computer experience* rest on COR-008 and COR-009, so they can go false. As RUP means them, they count and rate people.
  - **D's evidence:** NN/g asks a persona to rest on user research. None exists, so D's facts about Dana are invented.
- **An actor that is no person** (E and F):
  - A and B hold it as they hold a person. E's opening adds why it is an actor, the skill's test "Is it an actor?" written into the artefact.
  - RUP counts "another system" as an actor, but limits its *Characteristics* to "human actors". Its tailoring would let a project keep the frequency of use for a system.
  - D has no form for a system, since a persona is a person.
  - **In the shipped parts alone (F):** the opening, *Occasions* and *Context* still say what the pipeline is, when it runs and what it lacks. What goes is whose goals its runs serve (*In the model*), the layer (*Core*) and project-kit's wiring (*Note*).
  - *In the model* serves the two actors that are no person. It says whose goals their work serves, since a system's goals belong to people.
- **What the use case and the journey ask of an actor:**
  - **A goal is a need** (DEC-001 point 1). The landing's goal is the first part of the developer's need to land a change. The use case's E repeats another need word for word. So the needs' hint mirrors the goal's.
  - **A trigger is a meeting, in the use case's terms.** *Comes* says when the role meets the system, in the actor's terms. The landing's trigger, the developer deciding a change is ready, falls under "for every change". E's trigger, a question too large for one decision, falls under neither of the developer's occasions. So *Comes* sums up no triggers, and holds no copy of them.
  - **What a use case relies on, or protects.** The landing's precondition, a committed change, is what the developer's *Brings* names, the change. Its *Other actors* has the CI pipeline run its checks "with no person to answer, against the one base it names". That is the pipeline's *Brings*, and its second need.
  - **Most interests are needs.** Three of the landing's four interests restate their actors' needs (the use case's F). The AI agent's interest restates none of its five needs. The agent may write answers before anyone accepts them, and never waits on a question nobody can answer. An interest that states no need may show a need the actor lacks.
  - **An actor who takes no step.** The use case's example names an auditor in *Other actors*, whose interest is that each export is logged. The skill names "an outside auditor" as an actor too. Such an actor may never come to the system, so a required *Comes* needs `None.` (question 1).
  - **The journey's one actor:** a journey's goal combines several of its actor's needs, as the first day serves four of the adopter's. It needs nothing more of the actor.
- **The layer line, *Core*:** every core actor has one, and no source has its counterpart.
  - It says what in the core makes the role exist. project-kit's analysis describes the core, and a capability's view of a role comes with that capability (the developer's *Note*).
  - A project whose system has layers, such as a platform and its plugins, may want the same line. A project with one layer has nothing to put there.
  - The part of it a check could use is the records. DEC-001 point 4 already has each actor anchor what embodies it. An actor that nothing embodies gives `unanchored-because` instead (DEC-001 point 9 and COR-050 point 1).
- **What a script can check:**
  - **A:** the heading against the id and the name, as #1346 asks. Then that some text follows it.
  - **B, E and F:** the heading, the opening, each declared label in order and not empty, and each need one sentence. Under project-kit's closed list, a label outside its nine is reported (the design's part 4).
  - **C and D:** the same for their own labels. C's six characteristics are content, since only declared labels delimit (the design's part 1).
  - **None of them:** whether a record or a file the body names is among the anchors. A form could check it for every kind, and "For the build" names it.
- **The writing rules:**
  - A's paragraph runs to four sentences, the most RS-WRITE-007 allows.
  - B and E are the style trial's output, and meet `WRITE` as merged.
  - B's labels are verbs and phrases, such as *Comes*, *Brings* and *Can be*. The use case's and the journey's labels are nouns (question 2).

### Recommendation

Ship an opening and two labelled parts with software-analysis, beside the heading and the needs. Both parts are required, with `None.` allowed. They carry noun labels, which project-kit relabels *Comes* and *Brings*, and project-kit keeps its seven other labels in its own `structures.yaml`.

**Decided otherwise.** The maintainer took the shipped parts as recommended, and project-kit adopts the nouns instead of relabelling them. Its own seven labels become nouns too, as "Decided: the actor" says. This recommendation stays as it was made, and each point the decision turned is marked below.

- **The criterion:** an element ships when DEC-001 or today's template asks for it, nearly every core actor holds it, and it fits a system too. RUP and the persona confirm or question an element, and never veto one.
- **Why each:**
  - **The heading:** the stamp writes it, and #1346 checks it against the id and the name.
  - **The needs:** DEC-001 point 1's account of an actor, the readers point's data and the use cases' goals. Each is one sentence (the `sentence` form) in the actor's own voice (the use case's question 6).
  - **The opening, required:** today's template asks who this is, and every core actor opens so. RUP's brief description is the same. It has no form, since three core actors' openings run to two sentences.
  - **Occasions, required with `None.` allowed:** today's template asks when they come to the system, and every core actor answers it. It tells a reader of the use cases when the actor appears. An actor who takes no step, such as an outside auditor, writes `None.`.
  - **Context, required with `None.` allowed:** today's template asks what they bring with them, and seven core actors answer it. A use case's preconditions and its other actors' interests draw on it. The AI agent would write `None.`.
- **What was weighed and left out:**
  - **RUP's further characteristics:** the number of users, domain knowledge, computer experience and general characteristics count and rate people. RUP also limits them to human actors.
  - **RUP's relationships:** the use cases an actor takes part in are the use cases' own front matter, `actor` and `involves`. So a tool can list them, and the actor would hold a second copy. DEC-001 names no generalisation, and no core actor generalises another.
  - **Relations between actors as data:** two actors that named each other would form a cycle. project-kit's *Note* keeps them in prose.
  - **The persona:** it must rest on user research, and most of its parts describe a person. Where the needs are its only source, its goals and frustrations restate them.
  - **project-kit's seven labels:** each stays project-kit's.
    - *Can be* recurs in three core actors, and *Does* and *In the model* recur in two each. *The setup* and *Always a person* recur in one each.
    - *Note* is project-kit's style (RS-WRITE-004), and *Core* is its layer line (question 3).
    - **Decided otherwise, in their labels:** each stays project-kit's, and each becomes a noun.
  - **In the model, for actors that are no person:** both actors that use it are no person. So any project with a system actor might want it. F shows what a system actor loses without it. It recurs in project-kit only, so it waits until real artefacts show it recurs elsewhere (the use case's question 1).
- **Labels:** the nouns *Occasions* and *Context*, which project-kit relabels *Comes* and *Brings* (question 2).
  - **Decided otherwise:** project-kit takes *Occasions* and *Context* as they ship.
- **Ships with:** the heading, the needs' form, the opening, *Occasions* and *Context* ship with software-analysis. project-kit's `structures.yaml` relabels the two, and adds its seven labels under the kind `actor`, closed, naming RS-ANALYSIS-002.
  - **Decided otherwise:** project-kit's file relabels nothing, and adds its seven labels as nouns.

**The declaration #1363 would take.** The body's elements, in this order. "Decided: the actor" takes both tables below as they are.

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `# ACT-<slug> — <name>` | yes | heading | none, since the stamp writes it | `# ACT-analyst — Analyst` |
| `opening` | none | yes | none | What this role is, and what it does with the system. | Someone who builds reports from their team's figures. |
| `occasions` | Occasions | yes, and `None.` is allowed | none | On what occasions the actor comes to the system. Write `None.` when there is none. | At the end of each week, and whenever a manager asks for figures. |
| `context` | Context | yes, and `None.` is allowed | none | What the actor comes with, such as data, authority or a limit. Write `None.` when there is none. | A spreadsheet of their team's figures, and no right to publish a template. |

The front matter's form, apart from the body:

| Field | Form | Hint | Example |
|---|---|---|---|
| `needs` | `sentence`, on each item | What the actor needs from the system, each in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. | Export my report as a file. |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it. The opening's hint reads for a system as well as a person.
- **The examples:** one neutral actor runs through them all, the analyst of the use case's and the journey's examples.
  - Its need is the use case's example goal, word for word, since a need is a goal (DEC-001 point 1).
  - Its *Context* names a limit, the template it cannot publish. In the journey's example, an administrator publishes it.
- **The needs' hint:** it is the goal's hint, made plural, with question 4's *Never*.
- **At least one need:** the schema's `minItems` asks for it, and binds with no rule. The structure adds only the `sentence` form.
- **A hint in the front matter:** a `pkit:hint` comment cannot sit in YAML, and the template's front matter is written by hand (#1366).
  - **The round's reading:** the needs' hint stays the placeholder need, as today's placeholder is. The placeholder check already refuses it when left in, since it reads fields too (`check.py`).
  - That differs from #1363's and #1366's hints, which are body comments, so both say so.

**project-kit's own, in `structures.yaml`:** it relabels `occasions` *Comes* and `context` *Brings*. It adds the design's part 9 sketch, with a hint and an example for each. Each addition is optional, and the list is closed.

- **Decided otherwise:** the table in "Decided: the actor" replaces this one. It relabels nothing, and its seven labels are nouns.

| Element | Label | After | Hint | Example |
|---|---|---|---|---|
| `setup` | The setup | `opening` | What this role keeps set up in the project. | which checks the project's merges wait on (`ACT-adopter`) |
| `always-a-person` | Always a person | `setup` | Why no agent may play this role. | the authorisation turns the answers an agent wrote into a person's decision (`ACT-merge-authoriser`) |
| `can-be` | Can be | `always-a-person` | Who may play this role. | project-kit's maintainers, or a fork's (`ACT-methodology-maintainer`) |
| `does` | Does | `can-be` | What this role does, where the opening is too short for it. | choose how much the agents may do without asking (`ACT-operator`) |
| `in-the-model` | In the model | `context` | How the role appears in the use cases, where its goals belong to others. | its needs are what the system must give an unattended runner (`ACT-ci-pipeline`) |
| `core` | Core | `in-the-model` | What in the core makes this role exist, with the records that say so. | the checks bind once the project makes them a required status (COR-050 point 12) (`ACT-ci-pipeline`) |
| `note` | Note | `core` | Side matter: the reason for a name, or an overlap with another role. | the name is not "approver", because project-management uses that word for a reviewer agent (`ACT-merge-authoriser`) |

- **Their hints may carry project-kit's style,** since they are project-kit's own, and the examples quote its own actors.
- **#1368 gains this work.** Its body names the seven labels, but not their hints and examples, and the design's sketch left them out.
- **The order** is the design's. *The setup* follows the opening, so it comes before the shipped *Occasions* (the design's part 4).

**For the build:**

- **Decided otherwise:** the list in "Decided: the actor" replaces this one.
- **The parts (#1363):** the two tables above, the body's elements in their order. The actor is a document kind (#1346).
- **The schema (#1346):** it gains the `id` only.
- **The stamp and the template (#1366):** the body is rendered from the table. The needs' hint is the placeholder need, in the front matter written by hand.
- **What an actor is not (#1366 and #1369):** the template's head and the README say an actor is a role, not a persona. The journey's say it is not a UX journey map, and the skill already says "A role, not a person".
- **project-kit's labels (#1368):** `structures.yaml` relabels the two shipped parts and adds the seven, with the hints and examples above.
- **The voice's exception (#1360 and #1363), on question 4's answer:** the format rule's *How* lets *Never* come before the verb, and the hints for the needs and the goal say so. #1368's rule on the voice goes, as decided, so the exception moves here.
- **The skill (#1369):** the actor sub-procedure's *Fill it* list gives way to the hints. Its first step, "Is it an actor?", stays, since no hint carries it.
- **DEC-001 first (#1358):** its point 1 names an actor as a role with the needs it brings. The opening, *Occasions* and *Context* go beyond it, so #1358's refinement says so before any build cites it (core rule 2).
- **The readers point, later:** when a page first names an actor as its reader, its review shows whether the name and the needs say enough. If not, the opening becomes a front-matter field the filler reads, as a term's definition is data (the design's part 6).
- **A possible form:** every record and file a body names is among its anchors. It would serve every kind, and the round does not decide it.

**Found on the way:**

- **Five core actors cite what they do not anchor:**
  - a record: the developer's ADR-061, the CI pipeline's PRJ-002 and the merge authoriser's DEC-028
  - a file: CONTRIBUTING.md, in the methodology maintainer's *Brings* and the operator's *Note*
- **Where to fix them:** #1346 moves all eight actors, each with a revalidation, so that change could add the missing anchors. RS-WRITE-014, still proposed, asks for such anchors.
  - **Decided:** they become anchors in #1346.

### Questions for the maintainer

Each question is one decision, with a recommendation. The maintainer settled all four on 7 October.

1. **Are the two labelled parts required, with `None.` allowed?**
   - **The case:** the design's first cut makes both optional. Every core actor says when it comes, and seven say what they bring. An actor who takes no step, such as an outside auditor, has neither.
   - **Recommendation:** yes, as the use case's *Preconditions*, *Variants* and *Minimal guarantees* are. A required part makes the writer consider it, and `None.` covers an actor with nothing to say.
   - **Else:** both optional, as the design's first cut has them.
   - **Decided:** answered by the rule for every kind. Both are required, with `None.` allowed, as recommended.
2. **Do the shipped labels become nouns, with project-kit relabelling them *Comes* and *Brings*?**
   - **The case:** the maintainer made every use case label a noun, and the journey's labels are nouns too. The actor's two are verbs from the style trial, and RS-WRITE-002's example quotes *Comes*.
   - **Recommendation:** yes. Ship *Occasions* and *Context*, and project-kit relabels them in its `structures.yaml` (the design's part 4). Every shipped label is then a noun, and project-kit's actors and RS-WRITE-002's example stay as they are.
   - **Else:** ship *Comes* and *Brings*, as the core actors have them. The shipped labels then differ in kind from the use case's and the journey's.
   - **Decided:** option (b). software-analysis ships *Occasions* and *Context*, and project-kit adopts nouns for its own actor parts too. It relabels nothing, and its seven labels become nouns when its eight actors move (#1346).
3. **Does the layer line ship, as a part project-kit relabels *Core*?**
   - **The case:** every core actor has *Core*. It says what in the core makes the role exist, and in three actors it names the records the actor anchors. No source has its counterpart, and a system with layers, such as a platform and its plugins, could use it.
   - **Recommendation:** no, it stays project-kit's. A project whose system has layers adds it in its own `structures.yaml`, as project-kit does (the design's part 4). The part of it a check could use, the records, belongs in each actor's anchors (DEC-001 point 4).
   - **Else:** an optional shipped part, *Basis*, with the hint "What in the system makes this role exist. Name the record or code." project-kit relabels it *Core*.
   - **Decided:** the layer line stays project-kit's own, as its *Core* part, and does not ship. As recommended.
4. **Does the voice let *Never* come before the verb?**
   - **The case:** the decided voice starts each need and goal with its verb (the use case's question 6). The methodology maintainer's need starts with *Never*, and RS-WRITE-013 keeps that wording as its example of a rewrite that must keep the meaning. The design's exception for it went with #1368's rule on the voice.
   - **Recommendation:** yes. The hints for the needs and the goal say "Start with the verb, or with *Never* and the verb", and #1360's rule says the same. The goal's decided hint gains those words.
   - **Else:** the hints stay as decided. A writer who follows them would rewrite that need as "Ship … only with", the rewrite RS-WRITE-013 forbids.
   - **Decided:** option (a), as recommended. The hints for the needs and for the use case's and the journey's goals say so, and #1360's format rule allows it.

### Review

The critic reviewed the first draft. Each finding below changed the draft, or is answered here.

| Finding | Answer |
|---|---|
| Red flag: the hint for *Comes* asked how often, which the use case left to project management | The hint asks on what occasions. The case for the part rests on today's template and the core actors. |
| Red flag: the needs' hint, "Start with the verb", would push the rewrite RS-WRITE-013 forbids for the maintainer's *Never* need | Question 4 asks to carry the design's exception into the hints and #1360's rule. |
| Red flag: the criterion counted the tagline, domain knowledge and the experience level, which the round elsewhere filed as about people | The criterion is the earlier rounds': DEC-001 or today's template, recurrence in the core actors, and fit for a system. The sources confirm, and never veto. |
| Two core actors were said to cite a record they do not anchor | Five do: three records, and one file twice ("Found on the way"). |
| C's *Relationships* held other actors, which RUP's property does not | C keeps RUP's two kinds, the use cases and the generalisation. |
| *Core* was said to state the anchors in words, and question 3 rested on it | The anchors are among what *Core* names. Question 3 rests on the design's part 4 instead. |
| `unanchored-because` was credited to DEC-001 point 4 | DEC-001 point 9 and COR-050 point 1 |
| RUP was said to ask the frequency of every actor | Its guidelines add it, for human actors. Its tailoring could keep it for a system. |
| "The needs are the interests" generalised from three of four | Three of the four, and the AI agent's may show a missing need |
| B's *Note* named a capability's role, not an actor | The component author's and the operator's *Note* name other actors. |
| *Brings*' example named a template the system holds | The example is the analyst's spreadsheet, and a right the analyst lacks. |
| The readers point's quote was cut short | Quoted whole, "from the documentation". The readers point moves to "For the build", until a page names an actor. |
| A required *Comes* never met an actor who takes no step | Both parts allow `None.` (question 1). |
| *Comes* was said to sum up the triggers, traced on the landing only | E's trigger falls under no occasion. *Comes* sums up no triggers, and holds no copy. |
| `needs` sat in the body's order | The front matter's form has a table of its own. |
| The needs' hint in the front matter was left to #1366 | The round reads it as the placeholder need, and names the change to #1363 and #1366. |
| No actor was filled in the shipped parts alone | F fills the CI pipeline so, and "Fit with pkit" says what it loses. |
| The membership and cost tests were applied selectively | Every part is classed, and the cost is charged to *Core* and *Note* too. |
| No counterpart to the journey's naming | The template's head and the README say an actor is a role, not a persona. |
| #1368 holds no hints for the seven labels | It gains that work. |
| *Core*'s example named no record | It names COR-050 point 12. |
| D dropped NN/g's tasks without a reason, and Cooper went unused | Tasks are use cases. Cooper's goals, tasks and skill levels are in the source table. |
| The persona could veto any part | The sources no longer veto. |
| Question 2 tested only *Resources* | Question 2 now recommends nouns, which project-kit relabels. |
| Question 3 assumed an adopter's system has no layers | A layered project adds the line in its own `structures.yaml`. |
| *Brings* optional rested on an inference about the AI agent | Both parts are required, and the AI agent writes `None.`. |
| *Comes*, for a person, is a habit | Marked as closest to the line |
| D's repeats come from how it was filled | Said so, among what the example left unclear |
| Counter-alternative: *Comes* required with `None.` | Adopted, as question 1 |
| Counter-alternative: noun labels, relabelled by project-kit | Adopted, as question 2 |
| Counter-alternative: a form for what a body cites | Named in "For the build", and not decided |
| Counter-alternative: Cockburn's kinds of actor | Not adopted. The use case's example auditor makes the case for `None.`, and the round could not read Cockburn's text on actors. |
| Writing: elided verbs, series out of lists, ambiguous pronouns, hints framed for a person | Each fixed. The opening's hint reads for a system too. |

## The glossary term

The maintainer chose two parts for a term's section, *Example* and *Distinctions*, both required with `None.` allowed, and three forms for its front matter. Each of the four questions went as recommended. The comparison and the recommendation stay below as they were made.

### Decided: the glossary term

The maintainer decided the glossary term on 7 and 8 October, in comments on PR #1374. The glossary term is fully decided. E shows both terms in the decided shape (`term/chosen-template.md`).

- **What ships with software-analysis:**
  - the heading of each term's section, which the stamp writes
  - *Example*, required with `None.` allowed: one case of the term in use
  - *Distinctions*, required with `None.` allowed: each word the term could be confused with, and how the two differ
  - in the front matter, the forms of `name`, `definition` and `replaces` below
- **The round's questions, each answered as recommended:**
  1. **Question 1, the two parts:** yes. A term's section ships *Example* and *Distinctions*, each required with `None.` allowed.
  2. **Question 2, the definition:** option (a). A definition is a phrase in ISO's form that could stand in for the term.
     - It starts with its broader kind, and says what sets it apart.
     - It carries no article, no full stop and no repeat of the term.
     - A form of its own lets a script check it.
     - **The system's definition needs new words,** which the maintainer approves when the term is stamped. E first used B's, "software under discussion: pkit, as you install, run and extend it".
     - **Since 8 October,** the words are the maintainer's, "software under discussion, which you install, run and extend" ("Decided: two terms").
  3. **Question 3, `replaces`:** option (a). It lists only the names the term carried in the analysis or in an accepted record. A working name goes under *Distinctions* when it means something else.
     - So revalidation's `replaces` reads `[recheck]`, and *walkthrough* is one of its distinctions.
  4. **Question 4, the name:** option (a). A term's name is written in lower case, with no article, such as `system` and `revalidation`. Running text adds the article.
- **As recommended:** the definition stays data in the front matter. Today's "where it applies", ISO's further parts and C's parts stay out, for the reasons the recommendation gives. project-kit adds no part of its own for the term.

**The declaration #1363 takes, for each term's section, in this order:**

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `## TERM-<slug> — <name>` | yes | heading | none, since the stamp writes it | `## TERM-template — template` |
| `example` | Example | yes, and `None.` is allowed | none | One case of the term, in a sentence or two that use it as the analysis would. Write `None.` when the definition needs none. | the analyst builds the weekly report from the template the administrator published. |
| `distinctions` | Distinctions | yes, and `None.` is allowed | none | Each word the term could be confused with, labelled with that word, and how the two differ. Include a word the project avoids for this thing, or a working name that now means something else. Write `None.` when there is none. | **Report:** what an analyst builds from a template. A template holds no figures. |

**The front matter's forms, apart from the section:**

| Field | Form | Hint | Example |
|---|---|---|---|
| `name` | none | The term as running text writes it, in lower case unless it is a name, and with no article. | template |
| `definition` | `definition`, a form of its own | What the term means, in a phrase of the same part of speech that could replace it. Start with its broader kind, with no article, then say what sets it apart. End with no full stop, and never repeat the term. | layout an administrator publishes, from which an analyst builds a report |
| `replaces` | none | The names this term was written as before, in the analysis or in an accepted record, newest first. | report template |

- **The section's table is the recommendation's,** with one change. The hint for *Distinctions* gains the working name that now means something else, as question 3's answer sends it there.
- **The definition's hint gains two asks** that question 2's answer names: say what sets it apart, and never repeat the term. Each of its three sentences stays under 25 words (RS-WRITE-005).
- **The front matter's hints stay the placeholders,** written by hand, as the actor's needs' does. The placeholder check refuses one left in (`check.py`).
  - **`replaces` has no placeholder,** since a term never renamed has no such field. Its hint goes in the template's head comment, beside today's "put the old one first in `replaces:`".

**The definition's form**, which #1365 builds:

- **What a script checks:** the phrase's first word is no article, *a*, *an* or *the*. Its last character is no full stop. It holds no whole word of the term's own `name`, in any case.
- **What a person judges:** whether the phrase starts with the broader kind, says what sets it apart, and could replace the term. A writer runs that test by putting the phrase where the term stands.
- **A withdrawn term** is history, so no form fails it (the design's part 1).

**What filling E showed:**

- **Revalidation's definition loses its first word, *one*.** With it, "a revalidation" would read "a one review", and the phrase would not start with its broader kind, *review*. The article in running text carries the count.
  - **Otherwise it is B's,** DEC-001 point 5's sentence in ISO's form. The maintainer sees the dropped *one* when the term is stamped, since the change of words chooses a reading (RS-WRITE-013).
- **The system's definition was B's.** It passed the script's three checks, and its words were to be approved by the maintainer when stamped.
  - **Since 8 October,** E holds the maintainer's words, which pass the same three checks ("Decided: two terms").
- **Revalidation's working names:** *walkthrough* is a distinction, which now also names DEC-001 point 7's scripted walk-through, a check that is run. *Walk* gets none. Its other use is the ordinary verb, as in COR-050 point 9's "walks each artefact's history", and the glossary pins no ordinary word.
- **The system's platform:** B's definition no longer calls pkit a platform. So that distinction says only what COR-009's platform is.
- **The headings:** `## TERM-system — system`, while running text keeps "the system".
- **Length:** E runs to 222 words, against D's 214. With the methodology's distinction of 8 October, it runs to 249.

**For the build:**

- **The parts (#1363):** the section's table above. The term stays a collection kind, whose structure covers each entry's section and the file's head (the design's part 1).
- **The forms (#1363):** the front matter's table above, with the form `definition` among the analysis's own forms, beside `variants`.
  - **The schema (#1363):** its description of `definition` asks for "a sentence" today, and becomes the phrase in ISO's form. Its description of `replaces` gains which names count (`SA/schemas/term.schema.json`).
- **The checks (#1364 and #1365):** #1364 reports a missing, out-of-order or empty part, and lets `None.` pass in both. #1365 builds the form `definition`.
- **The stamp (#1366):** a term's default name is its slug in lower case, with hyphens as spaces (`SA/scripts/_lib/stamp.py`). So neither example needs `--name`. An actor's default name keeps its capital.
- **The template (#1366):** the section is rendered from the table, every shipped part with its hint.
  - **The front matter's placeholders** take the hints above: `name` in lower case, and `definition` in ISO's form.
  - **The head comment** says which names `replaces` keeps, and where a working name goes instead.
  - **The file's head** loses its semicolon, as B to E show.
- **The skill and the README (#1369):** the term sub-procedure's *Fill it* list gives way to the hints. Its first step, "Does the word need pinning down?", stays, and *Distinctions* records its answer.
- **DEC-001 first (#1358):** its point 1 names a term's stable id and its record of renames. The two parts, the definition's form and the rule on which names `replaces` keeps go beyond it. So #1358's refinement says so before any build cites it (core rule 2).
- **WRITE's example (#1368):** RS-WRITE-001's *How* gives a term's empty section as its example. No term's section is empty now, so #1368 replaces the example.
- **The check of replaced names** (the design's part 7, not filed): it reads only `replaces`, so it never reports a working name kept under *Distinctions*.
- **Avoided words, later:** a field of their own, such as `avoids:`, would let that check report them. It waits until a project needs one.
- **project-kit's first terms:** when project-kit stamps them, the maintainer approves three texts first.
  - the system's definition, B's words
    - **Since 8 October,** the maintainer's own words, without their first article ("Decided: two terms")
  - the system's reason for no anchor, the round's wording (core rule 20)
  - revalidation's definition, without DEC-001's *one*
  - **Before them,** the author's question below is answered.
    - **Answered on 8 October:** *methodology* joins them as a term of its own ("Decided: two terms").

### Decided: two terms, the system and the methodology

The maintainer answered the author's question on 8 October, in a comment on PR #1374. *System* and *methodology* are two terms for two things.

- **The system:** "the software under discussion, which you install, run and extend".
- **The methodology:** "the body of decision records, rules and conventions the system ships and enforces".
- **Each term's *Distinctions*** points at the other.
- ***pkit*** stays the product's name in prose and commands, while the analysis says *the system*.
- **The actors' sentences** that use *the methodology* for the software switch to *the system*.
  - Two examples are the adopter's "Install the methodology with one command…" and the component author's "Adapt the methodology to another harness…".
  - The *methodology maintainer* keeps its name.
- **In ISO's form** (question 2): a definition carries no article first. So the stamped definitions drop *the*, and the maintainer sees that when the terms are stamped.
  - The system's reads "software under discussion, which you install, run and extend".
  - The methodology's reads "body of decision records, rules and conventions the system ships and enforces".
- **What it changes in the round:**
  - **E's system** takes the maintainer's definition, and its *Distinctions* gain the methodology (`term/chosen-template.md`).
  - **project-kit's first terms** gain *methodology*. Its example and its anchors, or its reason for none, are written when it is stamped (core rule 20).
  - **The journey's example** says *the methodology* where it means the software, as in "Install the methodology into a project" (`journey/chosen-template.md`). Its use cases follow the decision when they are stamped.

**The question, as it was asked.** It stays below as the round put it.

- **The question:** do *the system*, *the methodology* and *pkit* name one thing?
- **Where each is used,** in the core actors (`tech-docs/analysis/use-case-model/actors.md`):
  - **The methodology:** 19 times, and the word *methodology* 27 times, counting the methodology maintainer's name. An example is the adopter's need "Install the methodology with one command".
  - **The system:** 6 times, as in the file's opening, "Who uses the system", and the adopter's need "Report a problem with the system".
  - **pkit:** once in the text, in the operator's need "be told plainly when pkit falls back to my installed tool". The journey's decided example titles a use case "See how pkit is wired into my project".
  - **Two in one sentence:** the AI agent's opening, "An AI agent working under the methodology, acting on the system from outside."
- **What PR #1345 settled:** its question 12 asked whether "the system", "this one" and "pkit" name one thing. The maintainer's answer reserved *the system*, and defined it in the glossary. *The methodology* was not asked, and the operator's need still says *pkit*.
- **Why it comes first:** the system's definition names pkit, so stamping the term answers part of the question. RS-WRITE-011's *How* asks the author first.
- **What either answer brings:**
  - **One thing:** one word stays. Each other use is rewritten to it with the author's word (RS-WRITE-013), or named under *Distinctions*.
  - **Two or three things:** each the analysis uses needs a term of its own, or a distinction under *system* that says how it differs.

### The example

Each candidate is the glossary, `glossary.md` under the analysis location, holding both terms as it would read on the default branch. A term stays an entry of that one collection file, with its definition as data (the design's Decided 2 and its part 6).

- **The system:** the decided first term (PR #1345, question 12). The maintainer defined it as the system under discussion, reserved the word, and had the two "another system" sentences rephrased.
  - **What it is:** pkit, as the platform you install, run and extend, in the words of this round's brief.
  - **Its first words are Cockburn's:** the system under discussion, *SuD*, is his name for the system a use case describes ("Sources").
- **Revalidation:** an ordinary term from pkit's records, chosen over *change* and *anchor*.
  - **The records define it:** DEC-001 point 5 does so by genus and difference, "one review of some artefacts against one version of the system". COR-050 point 3 names the block that records it.
  - **It was renamed:** COR-050 called the act a *recheck* when it was accepted on 27 September (commit `9664ddb5`), and its refinement of the next day renamed it. The design behind DEC-001 had called it *walk*, then *walkthrough* (`2026-09-26-software-analysis-living-docs-design.md`). So it tests `replaces` (question 3).
  - **One word for two things:** COR-050 point 3 and DEC-001 point 4 also call an artefact's record of the act its revalidation. DEC-001 point 6 names a third neighbour, the revalidation record.
  - **Another thing under its old name:** COR-016 calls a part of each storyboard scenario its *Walkthrough*. DEC-001 point 7 sets the act apart from testing.
  - **Why not *change*:** its records give it more than one meaning (item 4), so filling it would have meant choosing one. That choice is the maintainer's.
  - **Why not *anchor*:** COR-050 defines it, but it was never renamed. Its namesake, the session anchor, is in "Found on the way".
- **The same in every candidate:** the front matter, except B's definitions, which follow ISO's rules. Only the sections and the file's head differ.
- **The file's head:** today's opening holds a semicolon. A keeps it as stamped, and B to D write it without one.
- **Names in lower case:** each `name` is written as running text writes the term, as ISO's 16.5.5 asks. The stamp's default capitalises the slug (`SA/scripts/_lib/stamp.py`), so both terms take `--name`. Whether the system's name keeps its article is question 4.
  - **Decided otherwise, for the system:** its name is `system`, with no article, and the stamp's default becomes the slug in lower case (question 4).
- **Derived from:**
  - DEC-001 points 1, 4, 5, 6 and 7, and COR-050 points 3 and 5
  - COR-050 as first accepted, for *recheck*
  - COR-016, for a storyboard's walkthrough, and COR-009 point 1 and its context, for the hosting platform
  - PR #1345's answer to question 12, for the system
  - the use case's landing (`use-case/chosen-template.md`), for the system's example
  - the CLI reference (`.pkit/cli/README.md`), for `pkit friction revalidate`

**What the example left unclear.** The round decides none of these, but items 1 and 2 bear on questions 2 and 4.

1. **The system's definition repeats its term.** "The system under discussion" is Cockburn's term of art, so its words are a citation. Read as a definition, it is circular, which ISO forbids (16.5.6). Its second half, naming pkit, carries the meaning, and B's definition leaves *system* out.
   - **Decided:** a definition never repeats its term, so the system's takes new words (question 2). E first used B's, and holds the maintainer's since 8 October ("Decided: two terms").
2. **Three words may name the system.**
   - **The methodology:** the core actors' main word for what pkit carries, used 19 times in `actors.md`. The word *methodology* is used 27 times there, counting the methodology maintainer's name. The AI agent's opening uses both words: "An AI agent working under the methodology, acting on the system from outside."
   - **The system:** the adopter's needs use it ("Report a problem with the system") beside the methodology ("Install the methodology with one command").
   - **pkit:** the operator's need uses it ("when pkit falls back to my installed tool"). The journey's decided example titles a use case "See how pkit is wired into my project".
   - **Whether any two name one thing** is the author's to say (RS-WRITE-011), and no candidate claims it.
   - **Decided:** two terms, *system* and *methodology*, and *pkit* stays the product's name ("Decided: two terms").
3. **DEC-001 says *the software* too.** Its membership test asks whether "a change to the software can make it false". In project-kit's analysis that is the system, so item 2's question reaches it.
4. ***Change* has more than one meaning in the records.**
   - In DEC-001 point 6, a change carries a revalidation, and is "a tracked work item, a pull request, or a range of commits".
   - In the core actors, it is the core's unit of work (PR #1345, question 11).
   - This round's brief suggests "what reaches the default branch as one commit". That fits a pull request's squash commit (COR-009 point 1). It misses direct work, whose commits land as they were made (COR-009 point 5, and the landing's variant 2a).
5. **The old names live on.** COR-016 gives each storyboard scenario a *Walkthrough*, and DEC-001 point 7 counts "a scripted walk-through" as a check. *Walk* is an ordinary verb, as in COR-050 point 9's "walks each artefact's history". *Recheck* is in no record today.
   - **Decided:** `replaces` keeps *recheck*, the name an accepted record gave the act. *Walkthrough* is a distinction, and *walk* gets none (question 3).
6. **The system's reason for no anchor is the round's wording.** A reason for having no anchors is a person's decision, written only once they accept it (core rule 20). So the maintainer accepts its words when the term is stamped.

### The candidates

Each candidate is complete and filled, as the glossary would read on the default branch. A term is an entry of one collection file, so each candidate holds both terms in one file.

- **Decided otherwise, in every candidate's front matter:** the system's name is `system`, and revalidation's `replaces` reads `[recheck]` (questions 3 and 4). E shows both.
- **A, today's template** (`term/considered/A-todays-template.md`): exactly the parts of `SA/templates/glossary.md`.
  - The entry holds `name`, `status`, `definition` and `replaces`, and the friction block.
  - Its section holds prose, where the template's placeholder asks for "where it applies, what it is not, an example". A writer following `WRITE` puts the four outcomes in a list.
- **B, an ISO terminological entry** (`term/considered/B-iso-terminology-entry.md`): the entry ISO/IEC Directives Part 2 lays out in its clause 16, adapted only where pkit requires.
  - The preferred term is the `name` and the heading. The definition stays the front matter's `definition`, in 16.5.6's form. It is a phrase that could replace the term, with no article first and no full stop.
  - Each definition states its superordinate concept and what sets the term apart, after ISO 1087-1's intensional definition. The concepts are *review* for revalidation, and *software* for the system.
  - The system's genus is not *platform*, the brief's word, since COR-009 already calls the hosting service a platform.
  - The section's parts are the Directives': *Admitted terms*, *Deprecated terms*, *Example*, *Notes to entry* numbered from 1, and *Source*. *Source* says how a definition changed from its source, and *Related terms* holds the cross-references 16.5.4 allows.
  - The Directives print these otherwise, as `EXAMPLE`, `Note 1 to entry:` and `[SOURCE: …]`. B makes each a label.
  - **All six shown:** ISO makes every element but the term and the definition optional. B shows all six, so its cost is the most a project in ISO's style could take. One that shipped only examples and notes would come close to D.
- **C, a ubiquitous-language entry** (`term/considered/C-ddd-ubiquitous-language.md`): built from Evans's definitions and the DDD Crew's bounded context canvas. Neither gives a glossary entry's form, so C assembles one.
  - *Bounded context* holds where the meaning applies. Evans's ubiquitous language is used "within a bounded context", and the canvas asks for "the key domain terms that exist within this context".
  - *Invariants* holds what always holds of the term, each with its record. Evans states invariants as assertions, in the ubiquitous language.
  - *Examples* holds scenarios that use the term. Evans asks the team to "Describe scenarios out loud using the elements and interactions of the model".
  - The meaning is the front matter's `definition`, so C does not repeat it.
- **D, an example and the distinctions** (`term/considered/D-example-and-distinctions.md`): two noun-labelled parts, each from today's placeholder.
  - *Example* holds one case of the term, in a sentence or two that use it as the analysis would.
  - *Distinctions* holds each word the term could be confused with, labelled with that word, and how the two differ.
  - Both are present in every term, under the rule for every kind.
- **E, the chosen template** (`term/chosen-template.md`): D's two parts, with both terms in the decided shape. It came after the recommendation, and "Decided: the glossary term" says what filling it showed.
- **The design's first cut:** *Applies to*, *Not* and *Example*, optional, from today's placeholder (the design's part 8). Under the round's decisions it reads as D with a third part for the scope, so it has no file of its own. C's *Bounded context* fills that third part.

**Sources.** The ISO entry, Evans's terms and Cockburn's were read from these:

- **ISO:** ISO/IEC Directives, Part 2, ninth edition, 2021, clause 16, "Terms and definitions" ([PDF](https://www.cta.tech/media/1ebl2xah/iso-iec-directives-part-2.pdf), the version that marks its changes).
  - 16.5.5 names three kinds of term: preferred, admitted, and deprecated, "no longer in use or whose use is discouraged". Terms are written in lower case, "in their basic grammatical form".
  - 16.5.6: "The definition shall be written in such a form that it can replace the term in its context. It shall not start with an article ("the", "a") nor end with a full stop." Circular definitions "are not allowed".
  - 16.5.7 to 16.5.10 give the examples, the notes to entry and the source. 16.5.4 allows cross-references to other entries.
  - 16.5.2 sends the drafting of entries to ISO 10241-1, and the principles of terminology work to ISO 704.
- **The intensional definition:** ISO 1087-1:2000, entry 3.3.2, "definition which describes the intension of a concept by stating the superordinate concept and the delimiting characteristics". It was read as María Pozzi quotes it, in a paper for the ISO/TC 37 conference of 2007 ([PDF](https://www.ttt.org/tc37/ISO%20Conference%202007_files/Maria_704%20860%201087.pdf)).
- **Evans:** *Domain-Driven Design Reference*, dated June 2014 and published in 2015 ([PDF](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf)).
  - A ubiquitous language is "structured around the domain model". It is "used by all team members within a bounded context to connect all the activities of the team with the software".
  - A context is "The setting in which a word or statement appears that determines its meaning."
  - Its *Ubiquitous Language* pattern says "Recognize that a change in the language is a change to the model." It asks the team to "Describe scenarios out loud using the elements and interactions of the model".
  - Its *Assertions* pattern says "State post-conditions of operations and invariants of classes and aggregates."
- **The DDD Crew:** the Bounded Context Canvas, version 5 ([page](https://github.com/ddd-crew/bounded-context-canvas)). Its *Ubiquitous Language* section asks "What are the key domain terms that exist within this context, and what do they mean?"
- **Cockburn:** *Writing Effective Use Cases*, pre-publication draft 3 of 21 February 2000, the introduction to its part 1 ([extract](https://www.ifi.uzh.ch/dam/jcr:00000000-25a0-3d08-0000-00000ce96422/weuc_extract.pdf)). "A stakeholder is someone or something with a vested interest in the behavior of the system under discussion (SuD)."
- **Not verified:**
  - ISO 704, ISO 1087 and ISO 10241-1 themselves, which are sold, not published. Their current editions are ISO 704:2022 and ISO 1087:2019, which search summaries quote as naming "the immediate generic concept".
  - The Directives were read from a copy a third party hosts, since ISO's own pages refused the request.
  - Evans's book of 2003 was not read. The Reference is his own summary of its definitions and patterns.

### At a glance

B, C and D carry much the same facts under different labels, and A carries them unlabelled. So the choice is which labels give each kind of content a predictable place, and at what cost to every term. Words are counted in the two sections, labels included, with the headings, the file's head and the front matter left out.

| Candidate | Parts of a section | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 1, unlabelled: prose | None marked. Today's check catches a placeholder left in, not a section left empty. | 218 | Every kind of content, with no label to find one by | Its prose restates DEC-001 points 4 to 7 and COR-050 point 3. |
| B | 6: *Admitted terms*, *Deprecated terms*, *Example*, *Notes to entry*, *Related terms*, *Source* | All six, under the rule for every kind. All but *Example* may read `None.`. | 301 | A definition that could replace its term, with no circle. A place for a second name the project admits. The source, the only home of the system's provenance. | *Deprecated terms* repeat `replaces`. The notes restate record points, and *Related terms* restate a word of the definition. |
| C | 3: *Bounded context*, *Invariants*, *Examples* | All three. *Invariants* may read `None.`. | 258 | The rules that always hold of a term, each with its record. That the shipped hints' *the system* is every project's own. | Each invariant restates a record point the term anchors. |
| D | 2: *Example*, *Distinctions* | Both. Each may read `None.`. | 214 | Each neighbouring word under a label of its own, with how it differs | The distinctions restate record points, as B's notes do: DEC-001 points 4, 6 and 7, COR-050 point 3 and COR-016. |
| E | 2, as D | As D | 249, and 222 before the methodology's distinction | As D, with definitions in ISO's form and `replaces` holding *recheck* alone | As D |

**Note:** E came after the recommendation, and its row is added here to compare.

### Fit with pkit

The candidates differ less in what they say than in where they say it. D gives the two kinds of content both examples had, a case and the neighbouring words, a labelled place each.

- **The definition stays data** (the design's Decided 2 and its part 6). Every candidate keeps it in the front matter, where a glossary point could carry it to living-docs (living-docs DEC-001).
  - **The cost the design named:** a rendered glossary shows each term's heading, not its definition (the design's part 6). A generated view can show both later.
  - **One sentence, or a phrase:** the schema asks for "a sentence", and the template's placeholder for one sentence. The design's part 8 gives `definition` no form.
  - **ISO's substitution test, applied:** a definition "can replace the term in its context" (16.5.6).
    - DEC-001's sentence passes once "A revalidation is" goes. In DEC-001 point 4's "Each carries anchors and a revalidation", it fails, since there the word means the record on the artefact. So the test found revalidation's second meaning, which each candidate now names.
    - Substituted into "Report a problem with the system", B's definition of the system reads well only because *the* stays in the sentence (question 4).
  - **ISO's ban on circles is a rule of its own** (16.5.6). It is the one that catches "the system under discussion".
  - **What a script could check:** no article first, no full stop last, and not the term's own name. The last would have caught the system's decided definition.
- **Renamed names kept** (DEC-001 point 1):
  - Every candidate keeps them in `replaces`, newest first, as the schema's words allow: "the names the term was written as before". B repeats them as *Deprecated terms*.
  - **Which names count:** DEC-001 point 1 keeps them "so that renaming a term does not break what cites it". *Recheck* was the act's name in an accepted record. *Walkthrough* and *walk* were working names in a design note, and the glossary has held no name yet (question 3).
  - **The check of the design's part 7:** it would report a replaced name still in use, and never fail. `WRITE` reaches the analysis only, so the check would not read COR-016. It would read the glossary's own *Distinctions*, which names *walkthrough* on purpose, and every *walk* in an artefact.
  - **A word the project avoids, never a name of the term:** no field holds it, so no check reports it. ISO lists it among the deprecated terms. In D it is a distinction, with what it means instead.
- **Anchors** (DEC-001 point 4):
  - **A term anchors where the software or a decision embodies it.** Revalidation anchors COR-050 and DEC-001, which define it.
  - **A record a section only cites is no anchor.** COR-016 names a storyboard's walkthrough and does not embody revalidation, so no candidate anchors it. The system's sections cite DEC-001 point 1, which defines actors, not the system.
  - **RS-WRITE-014, still proposed, would differ:** it asks for an anchor wherever an artefact depends on what a document says. Accepted, it would pull each neighbour's record into the term's anchors, and the system's `unanchored-because` would have to go (COR-050 point 12).
  - **The system has no anchor.** A path anchor on the whole of pkit would match most changes, which COR-050 point 7 warns of. No record defines it. So it carries `unanchored-because` (DEC-001 point 9).
  - **What a term's change flags:** no artefact anchors a term today (DEC-001 point 4). A page may later, by id (COR-050 point 2). Then every edit to a term's section flags that page, since an entry's content includes its section (COR-050 point 1).
  - **Terms between themselves stay prose.** As anchors, two terms whose definitions use each other would form a cycle, an error under COR-050 point 5. B's *Related terms* gives a cross-reference by id, which no check reads.
- **The rule for every kind:** each shipped part is present in every term.
  - **A** ships no labelled part. Its prose is either a required opening, which would read `None.` wherever the definition says enough, or no part at all. RS-WRITE-001's *How* gives that empty section as its example.
  - **B** costs every term six parts, and the system reads `None.` in three of them.
  - **C** costs three. *Bounded context* reads "the analysis" for most terms, since one analysis describes one system.
  - **D** costs two, and both examples have something for each.
- **The writing rules:**
  - **RS-WRITE-011, one term for one thing:** a writer takes the term from the glossary. *Distinctions* tells them which neighbouring word means something else, and *Example* shows the term in use.
  - **RS-WRITE-008:** today's head holds a semicolon. B to D write it without one, and the stamp writes it once (the design's part 5).
  - **RS-WRITE-002, labels, still proposed:** B's notes carry numbered labels, `Note 1 to entry`, so its labels differ from term to term.
- **The membership test** (DEC-001): every part of C and D can go false with the software. B's *Source* records where words came from, and its *Related terms* change only with the glossary.
- **What a script can check:**
  - **Every candidate:** the heading against the id and the name, and the front matter against the schema, as today.
  - **B, C and D:** each part present, in order and not empty.
  - **A definition in ISO's form:** its first word, its last character and the term's own name. Whether the phrase can replace the term stays a person's judgement.

### Recommendation

Ship two parts in a term's section, *Example* and *Distinctions*, each required with `None.` allowed. The definition stays data, in ISO's form, with a form of its own that a script checks.

**Decided as recommended.** The maintainer took the recommendation, and answered each question as recommended. Two hints gain what the answers name, so the tables in "Decided: the glossary term" refine them. This recommendation stays as it was made, and each point the decisions turned is marked below.

- **The criterion:** the actor's, read for a term. A part ships when DEC-001 or today's template asks for it, both examples fill it, and it gives one kind of content a predictable place.
  - **Why not recurrence:** no glossary exists yet, so nothing can recur. Today's template already asks every term for both, so a term is asked no more than today, only in labelled places.
  - **The cost:** under the rule for every kind, both parts sit in every term of every project. A term that only pins a meaning down writes `None.` under *Distinctions*, and many will.
- **Why each:**
  - **The heading:** the stamp writes it, and the check holds it to the id and the name.
  - **The definition:** DEC-001 point 1's account of a term, and data a glossary point can carry. It takes ISO's form (question 2).
  - **`replaces`:** DEC-001 point 1's record of renames, newest first (question 3).
  - **The name:** in lower case, with no article (question 4).
  - **Example:** today's template asks for "an example", and ISO gives every entry room for examples (16.5.7). A case shows a reader the concept, and both terms had one. A term whose definition needs no case writes `None.`.
  - **Distinctions:** today's template asks "what it is not". The skill gives three reasons to add a term: a meaning particular to the project, two words for one thing, or one word for two. *Distinctions* records the last two, and both terms had neighbours, from records or the maintainer's answer.
- **What was weighed and left out:**
  - **A's prose:** it holds every kind of content, with no label to find one by. Under the rule for every kind it is a required part, or no part.
  - **Today's "where it applies", C's *Bounded context*:** in both examples it held a word used in two places, which *Distinctions* holds. For most terms it would read "the analysis".
  - **ISO's admitted and deprecated terms:** a former name is `replaces`, and a word the project avoids is a distinction. An admitted term is a second name for one thing, which RS-WRITE-011 rules out in the analysis.
  - **ISO's notes to entry and C's invariants:** they restate record points, as *Distinctions* does, but give no kind of content a place of its own. Anything goes in a note, and the records hold the rules.
  - **ISO's source:** for an anchored term, the anchors name it. For an unanchored term nothing else holds it, so the system's source survives only as the pull request its distinction cites.
  - **A general part, such as *Usage*:** it would take anything, as A's prose does. *Distinctions* keeps one kind of content in one place.
- **Labels:** nouns, as every decided kind's are. *Distinctions* stands for the brief's "Not to be confused with", which is no noun.
- **Ships with:** both parts ship with software-analysis. project-kit adds none of its own for the term.
- **The file's head:** the stamp writes it without the semicolon, as B to D show.

**The declaration #1363 would take.** The section's elements, in this order:

- **Decided otherwise, in two hints:** the tables in "Decided: the glossary term" replace these. *Distinctions* gains the working name that now means something else, and `definition` gains what sets it apart and no repeat of the term. They add `replaces` to the front matter's table.

| Element | Label | Required | Form | Hint | Example |
|---|---|---|---|---|---|
| `heading` | `## TERM-<slug> — <name>` | yes | heading | none, since the stamp writes it | `## TERM-template — template` |
| `example` | Example | yes, and `None.` is allowed | none | One case of the term, in a sentence or two that use it as the analysis would. Write `None.` when the definition needs none. | the analyst builds the weekly report from the template the administrator published. |
| `distinctions` | Distinctions | yes, and `None.` is allowed | none | Each word the term could be confused with, labelled with that word, and how the two differ. Include a word the project avoids for this thing. Write `None.` when there is none. | **Report:** what an analyst builds from a template. A template holds no figures. |

The front matter's form, apart from the section:

| Field | Form | Hint | Example |
|---|---|---|---|
| `name` | none | The term as running text writes it, in lower case unless it is a name, and with no article. | template |
| `definition` | `definition`, a form of its own | What the term means, in a phrase of the same part of speech that could replace it. Start with its broader kind, with no article and no full stop. | layout an administrator publishes, from which an analyst builds a report |

- **The hints:** each is one line, with short sentences and no semicolon (the design's part 5). They say what goes in a part, never how to format it.
- **A verb or an adjective:** the definition's hint asks for the same part of speech, as ISO does. So *land* is defined by a verb phrase, and *stale* by an adjective phrase.
- **The examples:** one neutral term runs through them all, the template of the journey's example, which an administrator publishes. Its distinction is the report, which the use case's example exports.
- **The front matter's hints:** they stay the placeholders, written by hand, as the actor's needs' does. The placeholder check refuses one left in (`check.py`).

**For the build:**

- **Decided otherwise:** the list in "Decided: the glossary term" replaces this one.
- **The parts (#1363):** the two tables above. The term stays a collection kind, whose structure covers each entry's section and the file's head (the design's part 1).
- **The definition's form (#1363 and #1365), on question 2's answer:** `definition` gets a form of its own, which checks its first word, its last character and the term's own name. It is one of the analysis's own forms, beside `variants`. #1363 also changes the schema's description of `definition`, which today asks for "a sentence" (`SA/schemas/term.schema.json`).
- **The name (#1366), on question 4's answer:** the stamp writes a term's default name in lower case.
- **The stamp and the template (#1366):** the section is rendered from the table, and the file's head loses its semicolon.
- **The skill (#1369):** the term sub-procedure's *Fill it* list gives way to the hints. Its first step, "Does the word need pinning down?", stays, and *Distinctions* records its answer.
- **DEC-001 first (#1358):** its point 1 names a term's stable id and its record of renames. The two parts and the two forms go beyond it, so #1358's refinement says so before any build cites it (core rule 2).
- **WRITE's example (#1368):** RS-WRITE-001's *How* gives a term's empty section as its example. No term's section is empty under the rule for every kind, so #1368 replaces the example.
- **The check of replaced names** (the design's part 7, not filed): it skips the term's own entry, whose *Distinctions* may name an old name on purpose.
- **Avoided words, later:** a field of their own, such as `avoids:`, would let that check report them. It waits until a project needs one.
- **project-kit's first terms:** when project-kit stamps them, the system's reason for no anchor needs the maintainer's acceptance first (core rule 20). Its definition rewords a decided answer, so the maintainer accepts that too.

**Found on the way:**

- **The shipped hints' *the system*.** software-analysis's templates and hints speak of *the system*, which in each project means its own software (`SA/templates/actors.md`). The use case left out *Scope* because it is always the system. A project that needs the word pinned down defines it in its glossary, as project-kit does.
- **Three words for the system** ("What the example left unclear", item 2). It is an author's question for project-kit's analysis, to answer before the system is stamped (RS-WRITE-011).
  - **Decided:** two terms, *system* and *methodology* ("Decided: two terms").
- **The session anchor.** COR-039 point 2 names "the session anchor (the repo the session is rooted in)", and the landing writes "the session's anchor" (`use-case/chosen-template.md`). So *anchor*, once stamped, needs that distinction.

### Questions for the maintainer

Each question is one decision, with a recommendation. The maintainer settled all four on 7 and 8 October, each as recommended.

1. **Does a term's section ship *Example* and *Distinctions*, each required with `None.` allowed?**
   - **The case:** today's template asks every term, in prose, where it applies, what it is not, and for an example. The rule for every kind puts each shipped part in every term. Both terms filled both parts.
   - **Recommendation:** yes. The two parts give what today's template asks a labelled place each, and ask a term for nothing more. Its third ask, the scope, held only distinctions in both terms.
   - **Else:**
     - *Distinctions* alone, since the case for an example is the weaker.
     - Nothing ships, and project-kit adds both as its own optional parts, as it keeps *Place in the model* for the actor. software-analysis ships them once real glossaries show they recur (COR-007).
   - **Decided:** yes, as recommended.
2. **Is a definition a phrase in ISO's form?**
   - **The case:** the schema asks for "a sentence", and DEC-001 writes its own definitions as sentences that name the term. ISO asks for a phrase that can replace the term, with no article first and no full stop, and never circular (16.5.6).
   - **What filling showed:** the substitution test found revalidation's second meaning, and the ban on circles caught the system's decided definition.
   - **Recommendation:** yes, ISO's form, with a form of its own that a script checks. A writer can run the test too: put the phrase where the term stands. The system's definition then needs new words, which the maintainer accepts when it is stamped, and B's are one proposal.
   - **Else:** a sentence that names the term, such as "A revalidation is one review of …", checked as one sentence. The test stays a reviewer's.
   - **Decided:** option (a), as recommended. The definition starts with its broader kind, says what sets it apart, and carries no article, no full stop and no repeat of the term. A form of its own lets a script check it. The system's definition takes new words, which the maintainer approves when the term is stamped.
3. **Does `replaces` keep only the names a term carried in the analysis or in an accepted record?**
   - **The case:** DEC-001 point 1 keeps the names "so that renaming a term does not break what cites it". The schema calls them "the names the term was written as before". Revalidation was *recheck* in COR-050 as accepted, and *walkthrough* and *walk* in a design note. Both of those are still in use for other things, and *walk* is an ordinary verb.
   - **Recommendation:** yes. Revalidation's `replaces` would read `[recheck]`. A working name stays in its note, so the check of replaced names never reports a word nobody cited as the term.
   - **Else:**
     - Every earlier name, working names included, as the candidates show.
     - Only the names the glossary itself held, so revalidation's would be empty.
   - **Decided:** option (a), as recommended. A working name goes under *Distinctions* when it means something else, so revalidation's `replaces` reads `[recheck]`.
4. **Is a term's name written in lower case, with no article?**
   - **The case:** the maintainer's answer names the term "The system". The stamp capitalises the slug by default, and the actors' names are capitalised. ISO writes a term in lower case and in its basic grammatical form (16.5.5).
   - **Why it matters:** substitution works only when the article stays in the sentence. "With the system" becomes "with the software under discussion: …".
   - **Recommendation:** yes. The name is `system`, and running text writes "the system", the reserved word with its article. The stamp's default for a term is the slug in lower case.
   - **Else:** the name keeps its article, `the system`, as the candidates show. Or it keeps the stamp's capital, `System`.
   - **Decided:** option (a), as recommended. The names are `system` and `revalidation`, and running text adds the article.

### Review

The critic reviewed the first draft. Each finding below changed the draft, or is answered here.

| Finding | Answer |
|---|---|
| Red flag: D's distinctions restate the records as B's notes do, yet only B was charged | "At a glance" charges D, and A's prose too. The comparison now weighs labels and a predictable place for each kind of content, and the criterion is the actor's. |
| Red flag: *revalidation* has more than one meaning too, so the reason for passing over *change* fails | *Change* was passed over because filling it meant choosing its meaning, which is the maintainer's. Each candidate now names revalidation's record on the artefact and the revalidation record. The substitution test found the first. |
| Red flag: anchoring every record a section cites was offered as a finding, and the system's example contradicts it | Withdrawn. A term anchors where a decision embodies it (DEC-001 point 4), so COR-016 is no anchor. RS-WRITE-014, still proposed, is named as the rule that would differ. |
| `replaces` rested on an unstated reading of a former name | Question 3 asks it. *Recheck*, COR-050's word when accepted, joins the names, and the check's reach is corrected to the analysis. |
| The name's case and article were decided without asking | Question 4 |
| Question 2 reopened the system's decided definition, and B's genus *platform* clashes with COR-009 | The new words are the maintainer's to accept at the stamp. B's genus is *software*, and D names the platform as a distinction. |
| B dropped DEC-001's "one", and its comma made the definition ambiguous | B keeps "one" and writes "which is". Its *Source* says what changed. |
| The definition's hint fails for a verb or an adjective | The hint asks for the same part of speech, as ISO does. |
| "A term flags nothing" holds only until a page anchors a term | Said so, with COR-050 points 1 and 2. |
| Leaving avoided words to *Distinctions* gives up the only check, unsaid | Said so. A field such as `avoids:` is named for later. |
| Dropping *Source* loses an unanchored term's provenance | Said so. The system's reason for no anchor now gives the reason alone. |
| No script could check the definition, the draft said | Three checks are named, and a form of its own replaces the `sentence` form. |
| *The methodology* was understated as the system's neighbour | Item 2 gives its 27 uses and the AI agent's opening. |
| "System under discussion" is Cockburn's term of art | Verified in Cockburn's draft, and said so. ISO still reads it as circular. |
| Core rule 20 was cited for definitions | It is cited for the reason for no anchor only. |
| RS-WRITE-002 was used without saying it is proposed | Marked proposed. |
| "The earlier kinds' criterion" was false, and the bar should rise | The criterion is the actor's: today's template asks for both parts, so a term is asked no more than today. The cost is stated. |
| The case for a required example was thin | *Example* allows `None.`, and its case rests on today's template and ISO. |
| The skill was misquoted | All three of its reasons are given, and *Distinctions* records two. |
| D's distinctions for the system named no words, or no difference | They are *a system* and *a platform*, each with how it differs. |
| "Each from a record" was false for the reserved word | "From records or the maintainer's answer" |
| B was a strawman, all six parts required | Said so in B's entry: B shows the most a project in ISO's style could take. |
| "Its rules follow from one test" was wrong | The ban on circles is a rule of its own, and the note says which caught what. |
| B's *Related terms* and C's claims were misdescribed | Corrected. C's use case invariant names the system as what fulfils the goal. |
| Counter-alternative: nothing ships, and project-kit adds both | Question 1's second "Else" |
| Counter-alternative: *Example* with a general *Usage* part | Weighed, and left out. |
| Counter-alternative: split question 1 | Its "Else" offers *Distinctions* alone. |
| Counter-alternative: an `avoids:` list | Named for later. |
| Counter-alternative: a form for the definition | Adopted |
| Counter-alternative: fill *anchor* or *change* as a third term | Not adopted. Revalidation has neighbours of each kind, and the session anchor is in "Found on the way". |
| Writing: a contradiction, a phrase that read as two decided terms, an unsourced quote, an unclear pronoun, A's inline series | Each fixed |

## The revalidation record

The revalidation record is the round's last kind, and the maintainer has not decided it yet. Four candidates are filled with the same two records, and compared below.

### The example

Each candidate holds two records, each as it would read on the default branch in `revalidations/` under the analysis location.

- **The planned record:** #1346's revalidation of the eight core actors, before code. #1346 moves each actor to a file of its own, with the labels the actor's round decided.
  - **Why this one:** a planned revalidation always leaves a record (DEC-001 point 6). This one covers eight artefacts and finds one gap.
  - **Its outcomes:** seven actors end `analysis-stale`, since the move is meant and each actor is updated. The merge authoriser ends `gap-found`.
  - **Its gap:** the change check would ask for none of the eight answers the move needs. So the merge authoriser would see none of them in the check's list (#1352's note, part 6). #1359 makes the check ask, and #1346 waits for it.
- **The regression:** a scheduled revalidation finds the landing regressed at its step 4, and the first day's journey holding. A commit cut each answer in the change check's list to its first line.
  - **Why this one:** it is the other kind of record, one an agent proposes and a person confirms. It also copies the evidence it drew on.
  - **The example's own:** the commit `3e9f1c2`, the defect `#xxxx` and the commit in the evidence. The test the evidence names is real, `test_the_human_view_ends_with_every_answer_in_full` in `tests/test_friction_check.py`.
- **The people:** Alex performs the planned revalidation alone. analysis-resolver proposes the regression's outcomes, and Sam confirms them. Alex and Sam are the names in the README's example record.
- **The ids:** `UC-xxx` is the landing, and `JRN-xxx` is the first day, as the use case's and the journey's rounds named them. The schema refuses such ids, since the round stamps nothing.
- **The same in every candidate:** the front matter, with its outcomes and its evidence, and each outcome's justification. Only the parts around them differ.
- **Derived from:**
  - DEC-001 points 5 to 7, the record's schema, the template and its stamp (`SA/scripts/_lib/revalidation.py`)
  - the README's "Revalidation records", and the analysis-resolver's storyboard for a regression recorded with its gap
  - #1346, #1359 and part 6 of #1352's note, for the planned record, and "Decided: the actor" for each actor's labels
  - the landing (`use-case/chosen-template.md`) and the first day (`journey/chosen-template.md`), for the regression

**What the example left unclear.** The round decides none of these.

1. **The change of a scheduled record.** The regression's `change` is one commit, `3e9f1c2`, as the storyboard's is `4c1d2e9`. DEC-001 point 6 names "a tracked work item, a pull request, or a range of commits".
2. **The actors' words for the system.** The maintainer's decision of 8 October switches the actors' sentences that use *the methodology* for the software to *the system* ("Decided: two terms").
   - If #1346 carries the switch, the adopter's and the component author's needs change in the move, and their outcome lines say so.
   - No decision says which change carries it.
3. **Where the planned record's gap sits.** The gap is in the change check, which no artefact describes yet. The record puts it on the merge authoriser, since it leaves that actor's first need with no behaviour.

### The candidates

Each candidate is complete and filled, as the records would read on the default branch.

- **A, today's template** (`revalidation-record/A-todays-template.md`): exactly the parts of `SA/templates/revalidation-record.md`, as its stamp writes them.
  - *Outcomes* holds one line for each artefact: `**<id> — <outcome>.**`, then its justification.
  - *Gaps* holds one line for each gap, `<gap> — **resolved:** <what resolved it>`, or `None found.` when there is none.
  - The stamp takes no evidence, so a person copies each entry into the front matter by hand.
- **B, IEEE 1028's inspection output** (`revalidation-record/B-ieee-1028-inspection-output.md`): the documented evidence an inspection leaves under IEEE 1028-2008, clause 6.7, adapted only where pkit requires.
  - Its parts, in the clause's order: *Team*, *Product*, *Inputs*, *Objectives*, *Anomaly list*, *Disposition*, *Waivers* and *Anomaly summary*.
  - Each anomaly gains what resolved it, as DEC-001 point 6 asks of a gap. Each disposition is an outcome of DEC-001 point 5 with its reason, in place of the standard's dispositions.
  - It leaves out the items a revalidation has no counterpart for, such as the meeting's duration and the rework time.
- **C, an architecture decision record** (`revalidation-record/C-architecture-decision-record.md`): Michael Nygard's parts, in his order, adapted only where pkit requires.
  - *Context* holds the forces: the change, the trigger and what the revalidation read.
  - *Decision* holds each outcome in the active voice he asks for, "We record …".
  - *Status* is always *accepted*, since a record is history, and names who accepted it.
  - *Consequences* holds the gaps with what resolved each, beside what else follows.
  - One of his records holds one decision, and a revalidation record holds one for each artefact.
- **D, each gap by its artefact** (`revalidation-record/D-gaps-by-artefact.md`): A's two parts, as the earlier rounds' decisions shape them.
  - *Gaps* reads `None.` when there is none, by the rule for every kind.
  - Each gap opens with the id of the artefact it was found in, as a bold label. The journey's hand-overs name their step in the same way.
  - What resolved the gap follows under a label of its own, *Resolved*.
- **The design's first cut:** A's parts, with *Outcomes* of the form `outcomes-match-front-matter`, and no hints (the design's parts 2 and 8). A filled first cut reads as A, so it has no file of its own.
- **The one record pkit has written:** the pilot analysis held one, `2026-09-29-multi-clone-coordination.md`. It was a planned revalidation of ten use cases and two journeys against EPIC #943's design.
  - It was added in `780def2f`, before the stamp landed in `5f601406`. It was removed with the pilot in `6107ae77`.
  - So it is no candidate. "Fit with pkit" reads what it grew beyond A's two parts.

**Sources.** IEEE 1028 and Nygard's records were read from these:

- **IEEE 1028:** *IEEE Standard for Software Reviews and Audits*, IEEE 1028-2008, clause 6.7, the output of an inspection.
  - Its list starts with the project, the team, the meeting's duration, the product and the size of the materials.
  - It goes on with the inputs, the objectives, the anomaly list, the disposition and any waivers. The preparation and rework times, an anomaly summary and estimates follow.
- **Nygard:** Michael Nygard, "Documenting Architecture Decisions", 15 November 2011 ([page](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).
  - A title is a short noun phrase, and the records are "numbered sequentially and monotonically".
  - The decision is "stated in full sentences, with active voice", as "We will …".
  - A status is "proposed" or "accepted", and a later decision may make it "deprecated" or "superseded".
  - The consequences describe "the resulting context, after applying the decision". "All consequences should be listed here, not just the "positive" ones."
- **Not verified:**
  - IEEE 1028-2008 itself, which is sold, not published. Its list was read only in a search summary of a paper that reproduces it (arXiv 1401.0503). The summary named the items up to the waivers and the preparation time.
  - So B's later items and their letters rest on no source the round could read.

### At a glance

A and D carry only what DEC-001 point 6 names. B and C add the version reviewed, and restate the front matter in prose. Words are counted in the body, labels included, with the heading and the front matter left out, for the planned record and then the regression.

| Candidate | Parts | Required | Words | Captures what others miss | Repeats |
|---|---|---|---|---|---|
| A | 2: *Outcomes*, *Gaps* | None marked. The stamp writes both, and `None found.` when there is no gap. | 319 and 101 | Nothing over D | Each gap restates what its artefact's outcome line says. No gap names its artefact, so a reader ties the two by reading. |
| B | 8: *Team*, *Product*, *Inputs*, *Objectives*, *Anomaly list*, *Disposition*, *Waivers*, *Anomaly summary* | None marked | 420 and 185 | The version reviewed and what else was read, in *Product* and *Inputs* | *Team* restates `by` and `confirmed-by`. *Objectives* is DEC-001 point 5's in every record, and *Waivers* reads `None.` in both. *Anomaly summary* counts the outcomes, and each anomaly's classification repeats its outcome. |
| C | 4: *Context*, *Decision*, *Status*, *Consequences* | None marked | 428 and 163 | The version reviewed and why the revalidation ran, in *Context*. What follows beyond the gaps, in *Consequences*. | *Status* reads "Accepted" in every record, and names `by` or `confirmed-by` again. The regression's *Decision* opens by restating its outcomes. Three consequences forecast, such as the open regression the check will report. |
| D | 2, as A | Both. *Gaps* may read `None.`, under the rule for every kind. | 310 and 100 | Each gap tied to its artefact by id, so a script can hold the gaps to the outcomes | Each gap restates what its artefact's outcome line says, as in A. |

### Fit with pkit

Every candidate keeps outcome lines a form can read. Only D lets a script tie each gap to its artefact, and only B and C say which version was reviewed.

- **The outcomes match the front matter** (the form `outcomes-match-front-matter`, #1365):
  - Every candidate writes one line for each entry of `outcomes`: `**<id> — <outcome>.**`, then the justification. The stamp writes the lines and the front matter from one list, so both keep its order (`revalidation.py`).
  - B names the part *Disposition*, and C opens its *Decision* with a sentence. A list form judges only the part's list items, so the sentence passes (the design's part 1).
  - The stamp refuses an outcome with no justification, and a form can refuse an empty one. Whether the justification is true stays a person's judgement.
- **Each gap and its artefact** (DEC-001 points 5 and 6):
  - DEC-001 point 5 makes a found gap an artefact's outcome, `gap-found`. Point 6 records "the gaps with what resolved each".
  - The stamp refuses a regression or a found gap with no `--gap`. It takes a `--gap` whose artefacts all hold, though point 5 puts every gap on an outcome.
  - **A:** no gap names its artefact. In the planned record, the merge authoriser's line points at "the gap". With two gaps, only the words tie each to its artefact.
  - **B:** each anomaly names its artefact in its label, as D's gaps do. Its classification repeats the outcome.
  - **C:** each gap is one consequence among others, labelled "A gap:" or "A regression:". A script can find it by that label, but no label names its artefact.
  - **D:** each gap opens with its artefact's id. So a form can hold the gaps and the outcomes `code-regressed` and `gap-found` to each other.
  - **The one real record:** its gaps were lettered, and many spanned artefacts. Gap E names UC-001, UC-004 and JRN-001, so a gap's label may need more than one id.
- **Evidence copied whole** (DEC-001 point 7): every candidate keeps it in the front matter, the one place a tool reads (the design's Decided 2). No candidate repeats it in the body.
  - The stamp takes no evidence, so a person copies each entry by hand. The check holds each copy to its own id, and warns where the point now holds otherwise (`check.py`).
  - The template asks an outcome line to name its evidence "by its id". The regression's line names the test in words, since the id runs to 126 characters.
- **Who decided** (DEC-001 point 5 and core rule 20):
  - The front matter says it. `by` names who performed the revalidation, and `confirmed-by` names the person who confirmed an agent's outcomes. The stamp refuses an agent without that person.
  - Every word of a record is a person's. The stamp writes each text from its command line, refuses a placeholder left in, and asks nothing (the README, "Revalidation records"). An agent proposes the command, and the person runs it.
  - B's *Team* and C's *Status* restate who decided, in prose that no script can hold to the front matter.
  - C's *Status* calls the performance an acceptance. Nygard's status follows a decision from proposed to accepted and later superseded, and a record never moves along it.
- **`None.` against `None found.`** (the rule for every kind):
  - The rule makes `None.` the deliberate answer of a part with nothing to say. *Gaps* has nothing to say in a planned record that finds no gap, and in a record of a stale outcome a person decided.
  - `None found.` says the same in two words, and only in this part. A script would carry a second token for one part of one kind.
  - **No record holds it today.** project-kit's analysis holds no record, and software-analysis is installed nowhere else (the design's Decided 1). So the stamp can switch with no record to change.
  - *Outcomes* may not read `None.`, since the schema asks for at least one outcome.
- **The version reviewed** (DEC-001 point 5): a revalidation is "one review of some artefacts against one version of the system: a proposed design, or the actual code".
  - **The front matter names the change** that carried it, never the version. In both examples the change names the version as well, #1346's design and the code at `3e9f1c2`.
  - **A design moves.** #1346's body may be edited before its code lands, and a scratchpad note retires. A later reader of A or D cannot tell which design the actors were reviewed against.
  - **B and C hold it,** in *Product* and *Inputs*, and in *Context*. A and D hold it only where a line happens to cite it, as the planned gap cites part 6 of #1352's note.
  - **The one real record opened with it,** under "The version walked". It named the design note as committed at `681e819`, and EPIC #943 as it stood on a named day.
- **No revalidation of the record itself:** a record is a held document, not an anchored artefact, so it carries no friction block and nothing flags it (DEC-001 point 2).
  - It is history, so a sentence about the past stays true.
  - A forecast can go false unnoticed, such as C's "a change to ADR-061, PRJ-002, DEC-028 or CONTRIBUTING.md flags the actors that cite it".
  - B's *Product* gives the actors "as the default branch holds them", which a later reader takes as the present.
- **What the one real record grew** beyond A's two parts, in 2,343 words:
  - an opening of 241 words, with the version walked and the three rounds of review behind the findings
  - *Outcomes*, each line citing its gaps by letter, such as "(gap E)"
  - *Gaps* of 1,476 words, in three sub-sections by when each gap was found, each gap lettered and labelled with its artefacts
  - a fourth section, "Needs explicit human authorisation", listing decisions the fixes wait on
  - **So a writer reached for** the version reviewed and a label naming each gap's artefacts. The fourth section belongs to the tracker, as the use case's open issues do.
- **What a script can check:**
  - **Every candidate:** the front matter against its schema, each cited id against the analysis, and each evidence copy against its own id, as today (`check.py`). Then the outcome lines against `outcomes`.
  - **A and D:** both parts present and in order. Then each gap with its resolution, or the part reading `None found.` in A and `None.` in D.
  - **D:** each gap's label names an artefact whose outcome is `code-regressed` or `gap-found`, and each such artefact is named by a gap.
  - **B:** its eight parts present, and the summary's counts against the outcomes. A count a tool can compute is a copy to keep.
  - **C:** its four parts present, and *Status* reading "Accepted".
  - **The heading:** today's check reads no record's heading. A check could hold its date to `date` and to the file's name, as a use case's heading is held to its id and title.
  - **None of them:** whether a justification is true, or whether the version a record names was the one reviewed.
- **The writing rules:**
  - **RS-WRITE-013:** a record's words are a person's decision, so they are never rewritten for style. A part that a later structure requires would fail every older record, and only a rewrite could add it.
  - **RS-WRITE-001:** its *How* names a record's *Outcomes* as a section that is only a list, so it needs no opening sentence. C's *Decision* has one anyway.
