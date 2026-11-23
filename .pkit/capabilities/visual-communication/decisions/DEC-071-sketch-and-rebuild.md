---
id: DEC-071
title: A new piece starts as a sketch a fresh session draws, and the designer rebuilds it with the brand and the libraries
status: proposed
date: 2026-11-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a new piece, or a whole piece redesigned, starts with a *sketch*. The designer starts a fresh agent session and gives it only the asker's words, the takeaways and where the piece is shown. With no method, no design knowledge, no library and no brand, the session draws every page outside the engine. The designer rebuilds the sketch at once as the piece, by its own method and design knowledge, with the brand the piece names and the project's libraries, and writes the reasons. A part the brand, the engine or a library cannot carry is drawn as the nearest that keeps its meaning, never a bend, and reaches the person as a *need*. No review reads the sketch. The one round of [visual-communication:DEC-070-ship-call-and-one-round] runs on the rebuilt piece. At the ship call the person sees the sketch beside the piece, and may ask for mends toward it. The sketch stays in the clone's local folder, never committed, until the ship call. The person may skip it on any piece. The evidence is two presentations and one person.

## Context

[visual-communication:DEC-070-ship-call-and-one-round] has the person make the ship call on a piece, after one round of mends. It left a free draft first to a record of its own, once a test said one should (DEC-070, Implications, "Left open").

The tests behind DEC-070 had shown free drafts reaching the person's bar. A fresh session, given only a presentation's words and its brief and no design guidance, drew three designs outside the engine. A second fresh session drew another presentation three ways. The person shipped all six, and nothing else in those tests. The capability's own drawing did not ship. Nor did any of the rounds a session drew apart from the capability, under a critic's loop, its first among them, drawn before any critic read it (DEC-070, Context).

The test of [project-kit#3470](https://github.com/aleskalfas/project-kit/issues/3470) then ran the capability's own agents on the same two presentations. Each of its questions was read against a pass fixed before it ran. Its results are in the scratchpad note `design-review-ship-call` of the repository the capability is authored in ([project-kit#3468](https://github.com/aleskalfas/project-kit/issues/3468)):
- **Drawing freely in the engine did not reach the bar.** The capability's designer drew the first presentation freely, in the engine, by its method and with one brand. The person shipped neither that drawing nor the version its round mended. Each was better than the other in some parts and worse in others.
- **A shipped free draft survived a rebuild once in two.** The designer rebuilt one free draft of each presentation that the person had shipped, as a piece, with that brand and the libraries.
  - The first rebuild shipped, as its draft had.
  - The second fell short. A sequence whose colours carried its meaning lost that meaning, and running text was drawn at the screen's size for a piece shown in a room. After one round on the person's own notes, the person called it shippable save one page, whose text needed a size the brand gave a piece's own components no way to reach.
- **What the rebuilds could not carry lay partly in the designer.** Dropping the meaning the colours carried is a bend [visual-communication:DEC-030-design-agents] point 4 forbids: the designer carries such a difference another way, or stops. Drawing running text at the screen's size for a room is a choice of the type's role for where the piece is shown, which is the designer's.
- **The rest lay in the brand, the engine and the libraries.** The brand lacked sizes and styles of type that a piece's own components could reach, and colours. The engine lacked tools of drawing. A library drew only the page's layout and a few blocks. The rest was drawn as local components, and some of these were general enough for other pieces.

**How far it goes.** Two pieces, both presentations that explain, drawn with one brand and judged by one person.
- **The condition tested.** What reached the bar was drawn by a fresh session with no design guidance, outside the engine, from the words and the brief. The loop's first round was drawn outside the engine too, and did not ship, so drawing outside the engine is not alone what made the drafts work. Nothing shows which part of the condition did: the fresh session, the lack of guidance, the lack of a library and a brand, or drawing before the content's structure was mapped.
- **A guided first drawing.** Whether the designer, by its method and with its design knowledge, would draw a first drawing as good is untested. The one guided drawing in the evidence, the designer's in the engine, did not reach the bar.
- **Which drafts were rebuilt.** Only drafts the person shipped were rebuilt, and one rebuild of two shipped. No rebuild of a draft the person would not ship was tried.
- **The round.** The round that brought the second rebuild near the bar mended the person's notes, not the review's findings. Nothing tested a review of a rebuild against its draft.
- **Other kinds, and other brands.** No piece of another kind, such as a figure or a poster, was drawn. The one brand lacked much the rebuilds asked of it.

The words it uses:
- **The person, the asker, the ship call and the round** are DEC-070's. The person is whom the designer works for, and the asker whoever asked for the piece. The ship call is the decision that a piece goes to its audience as it stands. A round is one mend by the designer, then a review of every page.
- **The engine** is the capability's code that computes a piece's scene from its content and its libraries ([visual-communication:DEC-001-visual-communication-discipline] point 2).
- **A library** is a named, versioned set that pieces share, and a brand is one. A **local component** is one made inside a piece, for that piece alone (DEC-001 points 4 and 5).
- **The clone's local folder** is the path the capability declares local to each clone, which the core keeps out of version control, where what a render, an export or the viewing step makes lies uncommitted ([visual-communication:DEC-002-files-and-validation] point 1).
- **A sketch** is a drawing of a whole piece, made outside the engine by a fresh session from the piece's words, its takeaways and where it is shown alone (point 1). The tests called it a free draft. "Draft" already names a piece's state ([visual-communication:DEC-003-change-over-time] point 8) and the words the designer drafts (DEC-070 point 4), so this record calls it a sketch.
- **A fresh session** is an agent session started for the sketch alone, which holds nothing of the work before it.
- **The asker's text** is the words the asker gives for a piece before it is drawn (point 2).
- **The rebuild** is the designer's drawing of a sketch as the piece itself (point 4).
- **A need** is what the brand, the engine or a library lacks for a part of a sketch that the rebuild could not carry, named on what lacks it (point 5). It is of the kind of DEC-070 point 5's need, a tool the engine lacks.

## Decision

**A new piece, or a whole piece redesigned, starts with a sketch: a fresh session the designer starts draws every page outside the engine, from the piece's words, its takeaways and where it is shown alone. The designer rebuilds the sketch at once as the piece, by its method, with the brand the piece names and the project's libraries. Where they cannot carry a part, it draws the nearest that keeps the part's meaning and reports a need. DEC-070's round runs on the piece, and the person sees the sketch beside it at the ship call. The sketch stays in the clone's local folder, never committed, until then.**

### 1. A new piece starts with a sketch, which a fresh session draws

- **What it is.** A drawing of every page of the piece, in the shape its pages take where it is shown. The session draws it in a medium it draws freely and the person can open, such as a web page it writes by hand. The engine computes none of it, and none of the capability's formats, commands or checks apply to it.
- **A fresh session draws it.** The designer starts a fresh session for it. It hands the session only the piece's words and its takeaways (point 2), and where the piece is shown. It hands it no method, no design knowledge, no library and no brand, and the session works outside the engine. Where the designer cannot start a session, it asks whoever dispatched it to start one, and hands them the same, as it does for the review (DEC-030 point 2).
- **No review and no round.** No review reads the sketch, and no round mends it.
- **Which pieces.** A new piece, and a redesign of a whole piece. A change to some of a piece's pages takes no sketch, since its other pages keep their design. A copy of another piece is drawn already, so it takes a sketch only where it is redesigned whole (DEC-003 point 8).
- **Skipped only on the person's word.** The person may have the designer skip the sketch on a piece. The designer then designs that piece in the engine from the start (DEC-030 point 3). This record places the skip at no level of the delegation setting ([COR-072](../../../decisions/core/COR-072-delegation-levels.md) point 13), so no agent skips the sketch in the person's place. Whether a project may skip it by kind of piece is left open (Implications).

### 2. The sketch draws the piece's words as given, and the rebuild puts them in the content

- **The words come first.** Before the sketch, a new piece's words exist as the asker's text: the words the asker gives for the piece, in the language it is first written in. No content file need exist yet. For a whole piece redesigned, the words are its content's, in that language.
- **The takeaways.** The sketch reads the takeaways from the asker's text, where the asker states them. Before the content exists, nothing else holds one. For a whole piece redesigned, they are its pages' leads and its brief's takeaways ([visual-communication:DEC-029-piece-brief] point 2).
- **Drawn as given.** The sketch draws the words as given, and changes none of them. It draws each page so that it carries its takeaway.
- **Into the piece at the rebuild.** The rebuild takes the words from the asker's text, or from a redesigned piece's content, never from the sketch. It puts them in the piece's content, then in every language. It puts each takeaway where DEC-029 point 2 puts one: in the brief, for a page whose content states its point in no lead. So no word reaches the piece from the sketch alone. A word the sketch shows that neither holds is the designer's, within DEC-070 point 4.

### 3. The sketch is kept in the clone's local folder until the ship call

- **Where.** The designer keeps the sketch in the clone's local folder, beside the images the viewing step draws ([visual-communication:DEC-015-viewing-step-and-reviewer] point 4). It lies nowhere in the capability's location, where the project's work lies (DEC-002 point 1), and no file of it is committed. The designer's grant, which names the location alone, stays as it is (DEC-030 point 5).
- **How long.** It is kept at least until the person's ship call on the piece, so the person can set the piece beside it (point 6). A later sketch of the same piece replaces it.
- **Who reads it.** The designer, to rebuild it, and the person. No command, check or review reads it. Once the rebuild is drawn, nothing draws from it: the piece's source is its content and its libraries (DEC-001 point 2).
- **Outside the capability's commands.** The session draws the sketch, and the designer reads it, outside the commands, which draw and show only what the engine computes. In this, the sketch departs from DEC-030 point 2, by which the designer renders, checks and looks only through those commands. The rebuilt piece is rendered, checked and looked at only through them.

### 4. The designer rebuilds the sketch at once, by its method

- **At once.** The designer rebuilds the sketch as soon as it is drawn. The person does not choose it first, and sees it at the ship call (point 6).
- **What the rebuild is.** The designer draws the sketch as the piece itself, in the engine: its content in every language, under the brand the piece names, with the libraries the project holds.
- **By the method.** The designer's method and its design knowledge govern the rebuild, as they govern any design (DEC-030 points 3 and 8). It writes the brief's goals and relations from what the asker says, and shows them to the asker before it designs against them (DEC-030 point 2).
- **What it keeps.** Each page and what it shows: the structure, the form and the visual variables that carry it, the hierarchy and the arrangement. The method names the structure each page shows before it carries the form, weighs another form, and says why it keeps the sketch's. It departs from the sketch's form only where that form bends the content's meaning (DEC-030 point 4), and says why.
- **What it takes from the brand.** For each choice of type, colour and space the sketch made, the brand's role that does that choice's job where the piece is shown. Examples are an accent where the sketch set one thing apart, and a size of text read across a room, for a piece shown in one. It writes no raw value, since only a brand holds one (DEC-001 point 5).
- **A notation's concepts.** Where a notation the piece names holds a concept that a part of the sketch shows, the rebuild maps the sketch's colour meanings to the notation's concepts. That part then takes its colour from its concept (DEC-001 point 6).
- **A library's component, an extension or a local one.** It uses a library's component where one draws a part of the sketch as well as the sketch does. Otherwise it takes one of DEC-030 point 4's ways: it extends a library through its owner's bar, or draws the part as a local component. Whether a component draws a part as well is the designer's judgement.
- **The reasons.** It writes the brief's reasons as it rebuilds, in the brief's order (DEC-030 point 3). They are the piece's reasons, those of the choices it keeps from the sketch among them.

### 5. What the rebuild cannot carry is drawn the nearest, and becomes a need

- **The nearest, never a bend.** Where the brand, the engine or a library lacks what a part of the sketch needs, and no way of DEC-030 point 4 that the designer may take draws the part as the sketch does, the rebuild draws the nearest they allow that keeps the part's meaning. It never bends the meaning to fit (DEC-030 point 4). A difference or a relation the nearest would lose, such as one the sketch's colours carry, it carries by another means they allow. Where none keeps the meaning, it stops on that part, as DEC-030 point 4 says.
- **Each part reported.** Each such part is reported, with what lacks it and what the rebuild drew in its place. What lacks it is one of three:
  - **the brand,** a value or a role it lacks, such as a size of type a piece's own components can reach, or a colour;
  - **the engine,** a tool it lacks;
  - **a library the designer may not write,** a component for a part other pieces could use, which the rebuild drew local.
- **A need of DEC-070's kind.** A need reaches the person with the piece, at the round's end (point 6). It goes as a question that names what the design needs, as DEC-070 point 5's need does, and stops only the work that rests on it. The nearest keeps the part's meaning, so the rest of the piece goes on.
- **On its owner.** For each need, the designer proposes to the person a task on the owner of what lacks it, as DEC-030 point 2 has it propose a request to a library's owner. That owner is the project for its own libraries, whoever maintains the capability for the engine and the libraries the capability ships, and another repository's owner for a library of that repository. The owner judges the need by the bar it keeps (DEC-030 point 4).
- **Libraries grow from below.** A library or a brand grows from what pieces ask of it: by an extension the designer makes through its owner's bar, and by a need its owner takes, in a version of its own. A piece takes what was added when its lock moves (DEC-003 point 8). No count of needs decides ([visual-communication:DEC-007-starter-library] point 1).

### 6. The round runs on the rebuilt piece, and the person sees the sketch beside it at the ship call

- **The round, as on any piece.** DEC-070's round runs on the rebuilt piece. It mends what DEC-070 point 3 names, and nothing else.
- **Nothing against the sketch.** The review is not handed the sketch, and reads the piece as DEC-070 point 5 says. A difference between the piece and the sketch is no finding, and the round mends nothing toward the sketch.
- **Side by side at the ship call.** With what DEC-070 point 2 hands over go the rebuild's needs, each with what it drew in its place, and where the sketch lies, so the person sets it beside the piece. Whether the piece keeps what made the sketch good is the person's to judge.
- **Mends toward the sketch, on the person's word.** The person may ask for mends toward the sketch, as for any mend: the designer mends what the person names, and the review reads every page again (DEC-070 point 2).
- **Starting again.** A piece the person would have start again is a whole piece redesigned, which starts with a new sketch (point 1).

## Rationale

**Why a sketch first, drawn by a fresh session.** In both tests, what a fresh session drew outside the engine, with no guidance, reached the person's bar. Nothing the capability drew in the engine did: its own drawing in the first test, and its designer's drawing by its method in the second. The loop's first round, drawn outside the engine too, did not ship, so drawing outside the engine is not alone what made the free drafts work. So this record takes whole the condition the tests found working: a fresh session, no guidance, no library and no brand, outside the engine. It claims nothing of which part of it worked. A library's components and a brand's values, met first, pull each page toward what they already draw, which is the loss the design agents were made to stop (DEC-030, Context). The rebuild then shows where the brand, the engine and the libraries fall short of what the content asked for.

**Why the method governs the rebuild, and not the sketch.** The method's worth is the order of its choices and the reasons a reviewer and a later designer rely on (DEC-030, "Why this record decides the method's order, and the body its steps"). Both are written at the rebuild, so the method governs where its worth lies. A sketch the method guided was never observed: every free draft that shipped was unguided, and the one guided drawing in the evidence did not ship. Guiding the sketch would try an untested condition on the person's pieces. The sketch is no piece, and no design of the designer's, so drawing it unguided leaves the method standing for every design the designer makes.

**Why the rebuild runs at once, and the person sees the sketch at the ship call.** The person's time is what a piece spends most dearly, and the ship call already asks for it (DEC-070 point 1). A look before the rebuild would ask the person twice for one piece, and would judge a drawing the piece will never look like: in the test, a shipped free draft became a shipped piece once in two. Seen beside the piece at the ship call, the sketch shows the person what the rebuild kept and what it lost, in one look. A mend toward the sketch is then a mend the person asks for, which DEC-070 point 2 gives them already. The cost is a rebuild spent on a sketch the person would not have chosen. The person then asks for mends, or has the piece start again.

**Why no review reads the sketch.** The free drafts that reached the bar had no review. The person ranked the polished rounds of a loop that a critic read below an earlier round of it (DEC-070, Context). The review also reads what the viewing step drew, with its frames and its report (DEC-070 point 5), and a sketch has none of them.

**Why the words come from the asker's text.** A piece's content chooses among what its libraries declare, its layouts and components among them (DEC-001 point 3), and the brief is keyed by the content's pages (DEC-029 point 3). Written before the sketch, the content would bring a library's structure in first, which the sketch is drawn to keep out. The asker's text holds the words before any of that. The sketch draws them as given, so from the rebuild on, the content is their one source, and DEC-070 point 4 says whose each word is.

**Why the sketch is kept in the clone's local folder.** A sketch holds what the capability keeps out of a piece's files: literal positions, raw values and fonts (DEC-001 points 3 and 5). It also holds the piece's words in one language, which would drift from the content. Committed, it would be a second source of the design beside the logical layer (DEC-001 point 2). Its files would stay in history for good, as the files of an export nobody handed out would ([visual-communication:DEC-006-work-outside-the-engine-and-outputs], "Why in the piece's folder, and what is committed"). The clone's local folder holds what the person looks at and nobody commits, the viewing step's images among them, so the person finds the sketch where they find the pages drawn. It lasts until the ship call, where the person sets the piece beside it. The cost is that it lies in one clone, so a person who wants it on another machine, or after a later sketch replaced it, copies it.

**Why the rebuild keeps the form and takes the brand's values.** The rebuild keeps of the sketch what no brand gives: its structure, form, hierarchy and arrangement. Type, colour and space are a brand's to give (DEC-001 point 5), so the piece looks like the project's other pieces, and switching its brand restyles it. Taking the role that does each of the sketch's choices' job where the piece is shown keeps what those choices meant under the brand's look. A notation's concept keeps a meaning a colour carries the same in every piece that shows it (DEC-001 point 6). The rebuild has a measured cost: all six free drafts shipped, and one rebuild of two shipped. That is what a piece pays for one source in the logical layer and a brand it can switch (DEC-001 points 2 and 5).

**Why the nearest, never a bend.** Part of what the second rebuild lost was the designer's. It dropped a meaning the sketch's colours carried, a bend DEC-030 point 4 forbids, and it drew running text at the screen's size for a room. The nearest that keeps the meaning, never a bend, answers the first (point 5), and the brand's role for where the piece is shown answers the second (point 4). The rest lay in the brand, the engine and the libraries, and a rebuild that stopped on each would bring the person no piece to judge. Drawn the nearest and reported, each lack reaches the owner who can meet it for every piece, with the piece that asked for it, and the person meets the piece with each loss in sight. A renderer reports what its medium could not draw in the same way (DEC-001 point 2).

**Why a need is DEC-070's kind.** DEC-070 point 5 already sends what the engine lacks to the person as a question that stops only the work resting on it. A rebuild's need asks the same question of a part of a sketch. So both reach the person alike, and the owner of what lacks it reads one kind of request.

**Why DEC-030 point 4's ways stand.** The test extended no library and no brand, so it gives no reason to bar an extension through its owner's bar during a rebuild. That bar already keeps a shared library from a form shaped by one piece alone (DEC-030, "Why extend, make or stop, and never bend").

**Why the round mends nothing toward the sketch, and the review never reads it.** No test measured a model's reading of a rebuild against its sketch beside the person's. A difference from the sketch may be a loss or a gain, a judgement of taste, which the tests found the person alone made reliably (DEC-070, Rationale, "Why the round mends these, and leaves the rest"). A round that mended toward the sketch would be a round of polish, and the tests' rounds of polish ranked below an earlier round. The person sees the sketch beside the piece, and a mend they ask for mends what they name, as the round on the person's notes did in the test.

**Why a whole redesign, and not a change to some pages.** The tests drew whole presentations whose words already existed, which is a whole piece redesigned. A sketch of some pages, drawn free of the brand and the libraries, would be rebuilt beside pages it never saw, and no test drew one.

**Why a project's skip by kind waits for a record.** A skip in a project's configuration would add a key every project carries, with its schema and its check, on evidence of one kind of piece. Which kinds a project would skip is not known until pieces of other kinds are sketched. Meanwhile the person may skip the sketch on any piece, which serves a kind as well, piece by piece.

**Why every project, on this evidence.** The evidence is one person and two pieces of one kind (Context, "How far it goes"). The other way, the designer drawing in the engine from the start, failed in the same test, so neither way rests on more. The person may skip the sketch on any piece, and each trigger below reads what the person says at ship calls, or a committed test.

### Alternatives considered

- **The designer draws freely in the engine, with the brand, from the start,** as DEC-030 point 3 has it. Rejected: in the test, that drawing and its mended version did not reach the bar.
- **A sketch the method guides,** drawn by the designer, or by a session given the method and the design knowledge. Not taken: no such drawing was observed, and the one guided drawing in the evidence did not ship. Its trigger to revisit: a committed test shows a guided drawing reaching the person's bar as often as a sketch.
- **The person chooses the sketch before the rebuild.** Not taken: the person would look twice at one piece, the first time at a drawing the piece will never look like, and a shipped free draft became a shipped piece once in two. Its trigger to revisit: at ship calls, the person often says a rebuild was spent on a sketch they would not have had rebuilt.
- **The person's look as a ship call on the sketch.** Rejected: the sketch reaches no audience, and the rebuild may lose or gain what the person judged.
- **A review of the sketch.** Rejected: no review read the free drafts that reached the bar, and the review reads what the viewing step drew.
- **Several sketches, for the person to choose among.** Not taken: one reached the bar in each test, and the person may have a piece start again. Its trigger to revisit: at ship calls, the person often has a piece start again from a new sketch.
- **The sketch committed in the piece's folder.** Rejected, for the reasons of "Why the sketch is kept in the clone's local folder".
- **The sketch kept in the agent workspace.** Rejected: there a capability's lasting files lie under a folder of its own name, a path the capability would declare as well, and the person would find the sketch apart from the pages the viewing step drew.
- **The rebuild extends no library and no brand until the ship call.** Rejected, for the reasons of "Why DEC-030 point 4's ways stand".
- **The review handed the sketch, to report what the rebuild lost.** Not taken: no test measured such a reading. Its trigger to revisit: a committed test finds that a model's reading of rebuilds against their sketches draws the person's line.
- **The round mends the piece toward the sketch.** Rejected: it would be a round of polish, on a judgement of taste.
- **A project skips the sketch by kind of piece, in its configuration.** Not taken, for the reasons of "Why a project's skip by kind waits for a record". Its trigger is the one "Left open" gives in the Implications.
- **A sketch for a change to some pages.** Rejected, for the reasons of "Why a whole redesign, and not a change to some pages".

## Implications

- **Edits made in this change once this record is accepted** (COR-066 point 5). Accepting this record accepts them. Each passage is sorted as the decisions README sorts it ("Refining an accepted record").
  - **Overturned in part: DEC-030.** Its top line, *Partially superseded by …*, comes to name this record beside DEC-070, and to say what each overturns. Overturned by DEC-071: point 2's "It renders, checks and looks only through the capability's commands", so far as a fresh session the designer starts draws a sketch outside them, and the designer reads it there (points 1 and 3). The line says too that the rebuilt piece is rendered, checked and looked at only through them. That passage stays as it stood, and the rest stands.
  - **Edited in place,** each narrowing, widening or completing its passage while its record's decision stands, with a forward pointer to this record:
    - **DEC-030 point 3,** its opening, comes to add that a new piece, or a whole piece redesigned, starts with a sketch, and that the method governs its rebuild. The method names the structure each page of the sketch shows, weighs another form and keeps the sketch's, departing only where it bends the meaning. It takes from the brand the role that does each of the sketch's choices' job where the piece is shown, and a concept's colour from its notation (points 1 and 4).
    - **DEC-030 point 4,** "Stop", comes to add that in the rebuild of a sketch, where no way draws a part as the sketch does, the designer meanwhile draws the nearest that keeps the part's meaning and goes on, as it goes on with a local component around a library it may not write. The need reaches the person with the piece (point 5).
    - **DEC-030 point 5** comes to add a bullet: the designer keeps a piece's sketch in the clone's local folder, outside its grant, which names the location alone, and commits none of it (point 3).
    - **DEC-002 point 1,** its bullet on what is never committed, comes to add a piece's sketch, which the designer keeps in the clone's local folder until the ship call (point 3).
    - **DEC-070 point 2,** "What goes to the person", comes to add, for a piece rebuilt from a sketch, where the sketch lies, and the rebuild's needs, each with what it drew in its place (point 6).
- **Read against this record, and left as they stand:**
  - DEC-001 points 2, 3, 5 and 6, since the sketch is no piece and nothing draws from it, it holds no file of a piece, raw values stay the brand's, and a concept's colour stays its notation's;
  - DEC-002 point 9, since the sketch is no command's file;
  - DEC-006 point 7, since the sketch is no export and no preview;
  - DEC-007 point 1, since a need is a reason for a library's owner, and no count decides;
  - DEC-029, since the takeaways reach the brief at the rebuild, and the brief's reasons describe the rebuilt piece;
  - DEC-030 points 1, 6, 7 and 8, and its points 2 to 5 beyond the top line and the edits above, since the agents, the review and the design knowledge stay as they are, and DEC-030 point 4's ways stand;
  - DEC-070 points 1 and 3 to 9, since the ship call, what the round mends, whose words are whose, the need, where a fix belongs and the triggers stay as they are;
  - DEC-070's Implications, whose item "Left open" on a free draft first this record answers;
  - COR-072, since this record places nothing at a level.
- **Left to the slices under [project-kit#3468](https://github.com/aleskalfas/project-kit/issues/3468),** each filed once this record is accepted: the designer's definition, for the fresh session and what it hands it, where it keeps the sketch, the rebuild and its needs, and what it hands the person at the ship call; the skill that guides building a piece; the capability's README and its page on files, for the sketch in the clone's local folder; and UC-111, "Have a piece designed and judged by the principles of visual communication", whose main path comes to start with the sketch and end with the person seeing the sketch beside the piece.
- **The scratchpad note** `design-review-ship-call` keeps the evidence. Its proposal "A free draft first" drew in the engine with the brand, which the test did not support, and this record decides otherwise. Its reading that the rebuilds fell short through the brand and the engine, not through the designer, this record reads as partly the designer's (Context). The note stays active for page marks, and retires as it says.
- **Its changeset.** This change declares in its changeset that it moves no surface of the capability. It owes no migration (COR-010).
- **Left open:**
  - **page marks against a project's shipped examples,** as DEC-070 leaves them;
  - **pieces of other kinds than presentations, and a project's skip of the sketch by kind of piece.** Its trigger to revisit: at the ship calls of pieces of one kind, the person says of most that the sketch did not help, or a committed test finds so.
