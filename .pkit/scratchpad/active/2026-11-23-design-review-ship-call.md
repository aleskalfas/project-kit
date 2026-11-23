---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-11-23
---

# The design review informs the person's ship call

Exploratory note (COR-012). It holds the evidence of the tests the maintainer ran on a development set of designs, which the Context of [visual-communication:DEC-070-ship-call-and-one-round] cites. It also keeps the proposals a later test weighs: page marks against a project's shipped examples, and a free draft first. It retires by producing the records that follow that test, under [project-kit#3468](https://github.com/aleskalfas/project-kit/issues/3468), or by being dropped.

## The question

[visual-communication:DEC-042-grades-bar-and-loop] had the graphic-design review grade each rule in words, and a project's bar end the designer's loop once a calibration of the review was accepted. No calibration met its conditions. The first passed no design. The second graded more leniently than its outside judges ([visual-communication:DEC-068-focal-point-in-the-content], Context).

So what judges a piece well enough to end the designer's loop? And how should the review and the loop serve the person who decides whether a piece ships?

## What the tests found, and how far it goes

**The set.** One presentation of ten slides that explains, projected and read from six metres. It has twelve designs:
- six rounds drawn by one agent session under a critic loop, from a first draft to two rounds of polish. The critic was core's `critic` agent, sent the same brief each round and asked what blocks;
- two weak designs drawn on purpose;
- the capability's own drawing, with its starter library;
- three designs drawn by one fresh session given only the words and the brief, and no design guidance.

**The person's line.**
- The person shipped the three fresh designs, and none of the other nine.
- The person ranked an earlier round of the loop above its polished rounds. The first draft, drawn before any critic, did not ship either.
- One more fresh session drew a second, unrelated presentation three ways, and the person shipped all three.

The sample is small. Two fresh sessions drew the six designs the person shipped, and one loop drew six of the nine that failed.

**What a model judging one design alone does.** A model judged each of the twelve alone, once for each setup:
- **Plain:** it passed the loop's rounds.
- **With one principle (below):** it passed two polished rounds, and failed two fresh designs over one slide each.
- **Beside the three shipped designs of the second presentation:**
  - Without the principle, it called the rounds "plainer, a difference of style, not of level".
  - With the principle, its answer on the whole design failed all twelve.
  - Its marks on each slide, though, split the two groups. The fresh designs each missed one or two slides of content, each a drawing that missed part of its point. The rounds missed the pages that open and divide the piece, and its pictures, in the person's own terms "a tidy template, not a designed piece".
- **A rule fixed in writing before two more runs:** a design ships where at least 8 of its 10 slides are marked at the level. It matched the person on 11 of 12 designs in each of three runs, and every miss sat at exactly 8.

**The principle,** as the judge read it: "Judge two things apart, on each slide and on the whole: its finish: whether it looks designed by a professional, in its pictures, colours, type and details, or made by hand in an office program; its clarity: whether what is drawn carries the slide's point. Neither makes up for the other. A hand-made finish fails a slide as surely as a missed point does."

**What this supports:**
- **The person's call held.** It was the one judge that drew a line the other readings could be measured against.
- **Examples help.** Beside a person's shipped work, and with the principle, a model's reading page by page points at what the person sees.
- **Polish did not help.** Here, the rounds of polish made the design worse.
- **A free draft can reach the bar.** A fresh session with no guidance reached the person's bar.

**What it does not support:**
- **A verdict on a whole design that replaces the person.** The count was chosen after a run, its margin is thin, and it breaks on long pieces: a piece of forty slides that fails only its opening and dividing pages and its pictures still passes.
- **Any claim about why the fresh designs worked.** It could be the lack of guidance, the lack of a library, or drawing before mapping.
- **That the judge would fail a weak free draft, or pass good work by another hand.** Neither was in the set.

## What the record takes from it

[visual-communication:DEC-070-ship-call-and-one-round] takes only what the tests support without a further test:
- **The person makes the ship call,** and the review informs it. No grade, bar, hold, verdict or calibration ends the designer's loop.
- **The loop is one round of mends.** The designer mends what is plainly wrong once, the review reads again, and the piece goes to the person. No round runs for polish.
- **The rule sets stay** as the canon both agents read and cite, and nothing grades them rule by rule.

## What a test may add

These are proposals, not decisions. The Feature [project-kit#3468](https://github.com/aleskalfas/project-kit/issues/3468) runs a test before any of them becomes a record.

### Page marks against a project's shipped examples

- **The examples.** A project may keep designs a person marked as shipped, by kind of piece, from pieces other than the one under review. The reviewer looks at every page of those of the same kind first. They show the level the project ships, not a style to match. Where a project has none of that kind, the reviewer reads with the principle alone, and says so.
- **Each page.** The reviewer marks each page at the level or below it, with a one-line reason that names finish or clarity. The marks inform the person and point the designer's mends. Nothing counts them.
- **The designer never reads the examples.** Reading them would let it design toward what the reviewer compares with. This rests on its restraint, as the reviewer's restraint over the brief's reasons does, and its report says what it read.
- **Where the examples live and who adds them.** In a folder the capability's configuration names, in the project's own files. Only a person adds a design, by marking it shipped. An adopter that has shipped nothing starts with none.
- **What the one round would then mend:** each page marked below the level, as a mend of that page, never a redesign.

### A free draft first, and libraries that grow from below

- **A free draft first.** The designer draws the whole piece in the engine from its words and its brief, with the project's brand, before it reaches for a library's parts. Where a library's part draws a part of the draft as well, it uses it. Otherwise the part stays local to the piece.
- **Libraries grow from below.** A local part moves into a library once other pieces need it, as [visual-communication:DEC-030-design-agents] point 2 already says. No new rule of promotion or pruning.

### Open

- **The principle's source.** [visual-communication:DEC-028-principles-of-visual-communication] wants a named source for a rule, and DEC-030 point 8 keeps a project's taste out of the design knowledge. The principle may be the project's, kept beside its examples, rather than the capability's.
- **One test before building.** Have the capability's own designer draw the development piece free-first in the engine, with the brand, and have the person mark it. It tells whether the designer reaches the bar, or whether the fresh session's lack of guidance was the reason. Page marks against examples, and one round of mends, can be weighed on the same run.
