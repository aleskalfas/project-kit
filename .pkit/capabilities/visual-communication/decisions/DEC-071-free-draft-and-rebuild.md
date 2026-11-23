---
id: DEC-071
title: A new piece starts as a free draft the person sees, and is rebuilt with the brand and the libraries
status: proposed
date: 2026-11-23
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the designer starts each new piece with a *free draft*: every page drawn outside the engine, from the piece's words and its brief, with no library and no brand. No review reads it. The person looks at it and chooses whether it is rebuilt, mended or drawn again, or stopped, and the designer waits for that choice. The draft is a working file on the machine that drew it, and is never committed. The designer then rebuilds the chosen draft as the piece, in the engine, with the brand the piece names and the project's libraries. It keeps what the draft shows and takes its values from the brand. It uses a library's component where one draws a part as well as the draft does, and makes the rest local. Each part the brand, the engine or a library could not carry is reported as a *need* on whatever lacks it, so libraries and brands grow from what pieces ask of them. The one round of [visual-communication:DEC-070-ship-call-and-one-round] then runs on the rebuilt piece as on any piece, and never mends it toward the draft. The evidence is two pieces and one person.

## Context

[visual-communication:DEC-070-ship-call-and-one-round] has the person make the ship call on a piece, after one round of mends. It left a free draft first to a record of its own, once a test said one should (DEC-070, Implications, "Left open").

The tests behind DEC-070 had shown free drafts reaching the person's bar. A fresh session, given only a presentation's words and its brief and no design guidance, drew three designs. A second fresh session drew another presentation three ways. The person shipped all six. Neither the designs a loop drew round after round, nor the capability's own drawing, shipped (DEC-070, Context). The test of [project-kit#3470](https://github.com/aleskalfas/project-kit/issues/3470) then ran the capability's own agents on the same two presentations. Each of its questions was read against a pass fixed before it ran. Its results are in the scratchpad note `design-review-ship-call` of the repository the capability is authored in ([project-kit#3468](https://github.com/aleskalfas/project-kit/issues/3468)):
- **Drawing freely in the engine did not reach the bar.** The capability's designer drew the first presentation freely, in the engine, with a project's brand. The person shipped neither that drawing nor the version its round mended. Each was better than the other in some parts and worse in others.
- **A free draft survived a rebuild once in two.** The designer took a free draft the person had shipped, drawn outside the engine, one from each presentation. It rebuilt each as a piece, with the project's brand and libraries.
  - The first rebuild shipped, as its draft had.
  - The second fell short. The person was first unsure: the rebuild lost a meaning its draft carried, and drew running text too small for where the piece is shown. After one round on the person's own notes, the person called it shippable save one page. That page's text needed a size of type the brand gave a piece's own components no way to reach.
- **What the rebuilds could not carry lay in the brand, the engine and the libraries,** not in the designer. The brand lacked sizes and styles of type that a piece's own components could reach, and colours. The engine lacked tools of drawing. A library drew only the page's layout and a few blocks. The rest was drawn as local components, and some of these were general enough for other pieces.

**How far it goes.** Two pieces, both presentations that explain, judged by one person.
- **Who drew the drafts.** The drafts that reached the bar were drawn by fresh sessions, not by the capability's designer. Whether the designer, with its method and its design knowledge, draws a draft as good is untested.
- **Why they worked.** Nothing shows why the free drafts worked: their lack of guidance, their lack of a library and a brand, or that they were drawn before the content's structure was mapped.
- **Which drafts were rebuilt.** Only drafts the person would ship were rebuilt, and one rebuild of two shipped. No rebuild of a draft the person would not ship was tried.
- **The round.** The round that brought the second rebuild near the bar mended the person's notes, not the review's findings. Nothing tested a review of a rebuild against its draft.
- **Other kinds.** No piece of another kind, such as a figure or a poster, was drawn.

The words it uses:
- **The person, the asker, the ship call and the round** are DEC-070's. The person is whom the designer works for, and the asker whoever asked for the piece. The ship call is the decision that a piece goes to its audience as it stands. A round is one mend by the designer, then a review of every page.
- **The engine** is the capability's code that computes a piece's scene from its content and its libraries ([visual-communication:DEC-001-visual-communication-discipline] point 2).
- **A library** is a named, versioned set that pieces share, and a brand is one. A **local component** is one made inside a piece, for that piece alone (DEC-001 points 4 and 5).
- **A free draft** is a drawing of a whole piece made outside the engine, with no library and no brand (point 1).
- **The rebuild** is the designer's drawing of a free draft as the piece itself (point 4).
- **A need** is what a library, the brand or the engine lacks for a part a piece asks of it, named on what lacks it (point 5). DEC-070 point 5's need, a tool the engine lacks, is one.

## Decision

**The designer starts each new piece with a free draft, drawn outside the engine from the piece's words and its brief, with no library and no brand. The person sees it and chooses whether it is rebuilt. It stays a working file on the machine that drew it. The designer rebuilds the chosen draft as the piece, with the brand the piece names and the project's libraries, and reports each part they could not carry as a need on what lacks it. DEC-070's round then runs on the piece, and never mends it toward the draft.**

### 1. A new piece starts with a free draft

- **What it is.** A drawing of every page of the piece, in the shape its pages take where it is shown. The designer draws it in a medium it draws freely and the person can open, such as a web page it writes by hand. The engine computes none of it, and none of the capability's formats, commands or checks apply to it.
- **No library and no brand.** It takes no component from a library and no value from a brand. Its type, colour and space are its own.
- **From the piece's words and its brief.** It shows the text of the piece's content, in the language the piece is first written in. It draws to the brief's intent: its goals, its relations and a page's takeaway ([visual-communication:DEC-029-piece-brief] point 2). The designer shows the goals and relations to the asker before it draws against them ([visual-communication:DEC-030-design-agents] point 2).
- **One source of words.** The draft shows the content's words as they stand. A word the designer would change, it changes in the content, as DEC-070 point 4 lets it, and the draft then shows it. So no word lives in the draft alone.
- **The method still guides it.** The designer's method and its design knowledge guide the draft as they guide any new design (DEC-030 points 3 and 8), save the brand's roles, which the rebuild takes (point 4).
- **No review and no round.** No review reads the draft, and no round mends it. The person alone judges it (point 2).
- **Which pieces.** Each new piece the designer makes, and not a piece it changes. A copy of a final piece is drawn already ([visual-communication:DEC-003-change-over-time] point 8). The person may ask for a free draft on a piece the designer changes, or ask it to skip the draft on a new one. Skipping it, the designer designs in the engine from the start (DEC-030 point 3).

### 2. The person chooses whether the draft is rebuilt

- **Shown, then waited for.** The designer shows the person every page of the draft and where it lies (point 3). It rebuilds nothing until the person chooses. Returning the draft to whoever dispatched the designer is not showing it to the person.
- **The person's choice.** The person chooses one of three ways:
  - the draft is rebuilt as it stands;
  - it is mended, or drawn again, on what the person says, and shown again;
  - the piece stops.

  The person chooses by their own judgement. In the tests, the drafts rebuilt were drafts the person would ship.
- **No ship call.** The draft never goes to an audience. The ship call stays on the rebuilt piece (DEC-070 point 1), and choosing a draft commits the person to nothing there.
- **At every level.** This record places the choice at no level of the delegation setting ([COR-072](../../../decisions/core/COR-072-delegation-levels.md) point 13). So it stays the person's at every level, and no agent makes it in the person's place, the designer, the reviewer and a delegate among them.
- **Its words, seen.** Showing the draft to the asker shows them its words, which become the asker's as DEC-070 point 4 says.

### 3. The draft is a working file, kept on the machine that drew it

- **In the agent workspace.** The designer keeps the draft in the agent workspace, the folder of each checkout where agents keep their working files, which no commit takes (`RS-OPS-016`). It lies nowhere in the capability's location or in a piece's folder ([visual-communication:DEC-002-files-and-validation] point 1), and is never committed.
- **Until the ship call.** It is kept at least until the person's ship call on the rebuilt piece, so the person can set the piece beside it (point 6).
- **Read by the designer and the person.** No command, check or review reads it. Once the rebuild is drawn, nothing draws from the draft: the piece's source is its content and its libraries (DEC-001 point 2).

### 4. The rebuild carries the draft into the brand and the libraries

- **What it is.** The designer draws the chosen draft as the piece itself, in the engine: its content in every language, under the brand the piece names, with the libraries the project holds.
- **What it keeps.** Each page and what it shows: the content's structure, the form and the visual variables that carry it, the hierarchy, and the arrangement (DEC-030 point 3).
- **What it takes from the brand.** For each choice of type, colour and space the draft made, the brand's role that carries what that choice did, such as an accent where the draft set one thing apart. It writes no raw value, since only a brand holds one (DEC-001 point 5).
- **A library's component, or a local one.** It uses a library's component where one draws a part of the draft as well as the draft does, and draws the rest as local components. Whether a component draws a part as well is the designer's judgement.
- **Nothing extended.** It extends no library and no brand. A part no library draws is local, and what the brand or the engine lacks is a need (point 5).
- **The nearest, never a bend.** Where the brand or the engine lacks what a part of the draft needs, it draws the nearest they allow, and reports the need. It never bends the meaning to fit (DEC-030 point 4). A difference or a relation the draft shows that the nearest would lose, it carries by another means they allow. Where none does, it stops on that part, as DEC-030 point 4 says.
- **The reasons.** It writes the brief's reasons as it rebuilds (DEC-030 point 3). They are the piece's reasons, those of the choices it keeps from the draft among them.

### 5. What the rebuild could not carry becomes a need on what lacks it

- **Each part reported.** Each part of the draft the rebuild could not carry as the draft draws it is reported, with what lacks it and what the rebuild drew in its place. What lacks it is one of three:
  - **the brand,** a value or a role it lacks, such as a size of type a piece's own components can reach, or a colour;
  - **the engine,** a tool it lacks;
  - **a library,** a component for a part other pieces could use, which the rebuild drew local. A part this piece alone needs is no need, since a true one-off stays in the piece (DEC-030 point 3).
- **To the person, with the piece.** The needs reach the person with the rebuilt piece, at the round's end (point 6). A need stops nothing: the rebuild draws the nearest it can and goes on.
- **A need on its owner.** For each need, the designer proposes to the person a task on the owner of what lacks it, as DEC-030 point 2 has it propose a request to a library's owner. That owner is the project for its own libraries, whoever maintains the capability for the engine and the libraries the capability ships, and another repository's owner for a library of that repository. The owner judges the need by the bar it keeps (DEC-030 point 4).
- **Libraries grow from below.** A library or a brand takes a need only through its owner, in a version of its own, as work apart from the piece. A piece takes what was added when its lock moves ([visual-communication:DEC-003-change-over-time] point 8). No count of needs decides ([visual-communication:DEC-007-starter-library] point 1). No new rule of promotion or pruning holds: a local component moves into a library once other pieces need it (DEC-030 point 2).

### 6. The round after the rebuild mends what DEC-070 names, and never toward the draft

- **The round, as on any piece.** DEC-070's round runs on the rebuilt piece, and mends what DEC-070 point 3 names, and nothing else.
- **Nothing against the draft.** The review is not handed the draft, and reads the piece as DEC-070 point 5 says. A difference between the piece and the draft is no finding, and the round mends nothing toward the draft. Whether the piece keeps what made the draft good is the person's to judge, at the ship call.
- **Nothing extended before the ship call.** Until the person's ship call on the piece, the designer extends no library and no brand on its own, in the round or in a round the person asks for. A fix that belongs to a library, it draws as a local component. A finding that only a value or a role the brand lacks would clear, the review marks a need, as it marks one only a tool the engine lacks would clear (DEC-070 point 5). The round mends no marked finding.
- **A need met at once.** Where the person asks that a need be met before the ship call, meeting it is work of its own, through its owner's bar (DEC-030 point 4). The piece takes it as its lock moves.
- **What goes to the person.** With what DEC-070 point 2 hands over go the rebuild's needs, each with what the rebuild drew in its place, and where the draft lies, so the person can set the piece beside it.

## Rationale

**Why a free draft first.** In both tests, free drafts drawn outside the engine reached the person's bar. The designs the capability drew in the engine did not: its own drawing in the first test, and its designer's free drawing with a project's brand in the second. A library's components and a brand's values, met first, pull each page toward what they already draw, which is the loss the design agents were made to stop (DEC-030, Context). A draft drawn free of them shows what the content asks for. The rebuild then shows where the brand, the engine and the libraries fall short of it.

**Why the method still guides the draft.** The tests cannot tell what made the free drafts work (Context, "How far it goes"). The method keeps the order of choices and the reasons a reviewer and a later designer rely on (DEC-030, "Why this record decides the method's order, and the body its steps"). Dropping it would overturn DEC-030 on evidence that does not isolate it. Its alternative's trigger waits for evidence that does.

**Why the person chooses, and the rebuild waits.** The person's judgement was the one that held in the tests (DEC-070, Rationale, "Why the person makes the ship call"). A rebuild spends a whole design in the engine. The tests rebuilt only drafts the person would ship, and even so one of two fell short. A rebuild of a draft the person would not choose starts below the bar. Waiting brings the person's word to the draft, before that cost is spent. It is no ship call, since nothing reaches an audience, and a rebuild may lose what the person saw in the draft or gain on it. Nothing checks the choice in the person's place, so no level hands it on (COR-072 point 13).

**Why no review reads the draft.** The free drafts that reached the bar had no review. The person ranked the polished rounds of a loop that a critic read below an earlier round of it (DEC-070, Context). The review also reads what the viewing step drew, with its frames and its report (DEC-070 point 5), and a draft has none of them.

**Why the draft stays a working file.** A draft holds what the capability keeps out of a piece's files: literal positions, raw values and fonts (DEC-001 points 3 and 5). It also holds the piece's words in one language, which would drift from the content. Committed, it would be a second source of the design beside the logical layer (DEC-001 point 2). Its files would stay in history for good, as the files of an export nobody handed out would (DEC-006, "Why in the piece's folder, and what is committed"). The agent workspace is where every agent already keeps its working files, so the designer needs no new grant, and the capability no new path and no new kind of file. The draft lasts until the ship call, since whether a rebuild keeps what made its draft good was what the test asked the person. The cost is that it lies in one checkout on one machine, so a person who wants it elsewhere, or later, copies it.

**Why the rebuild keeps the form and takes the brand's values.** The draft's structure, form and hierarchy are what the person chose. Type, colour and space are a brand's to give (DEC-001 point 5), so the piece looks like the project's other pieces, and switching its brand restyles it. Taking the role that carries what each of the draft's choices did keeps what those choices meant under the brand's look.

**Why the rebuild extends nothing, and reports needs.** A library is shared, so a component added to it in the middle of one piece is shaped by that piece alone, and the piece waits on the owner's bar. The test found the rebuilds falling short through the brand and the engine, not through the designer. Its list of what they lacked came from the rebuilds themselves. Reported as needs, those lacks reach the owner who can meet them for every piece, each with the piece that asked for it, and the person meets the piece with each loss in sight. A renderer reports what its medium could not draw (DEC-001 point 2), and the rebuild reports what the brand, the engine and the libraries could not carry in the same way. So a library grows from what pieces drew, beside the jobs the starter builds ahead of need (DEC-007 point 1).

**Why the round mends nothing toward the draft, and the review never reads it.** No test measured a model's reading of a rebuild against its draft beside the person's. A difference from the draft may be a loss or a gain, a judgement of taste, which the tests found the person alone made reliably (DEC-070, Rationale, "Why the round mends these, and leaves the rest"). A round that mended toward the draft would be a round of polish, and the rounds of polish in the tests ranked below an earlier round. The person sees the draft beside the piece at the ship call, and a round they ask for mends what they name (DEC-070 point 2), as the round on the person's notes did in the test.

**Why a lack in the brand is marked a need.** In the round, the designer may not change the brand, so a finding only a value the brand lacks would clear is one no fix it may make would clear, which DEC-070 point 5 marks. Unmarked, the round would owe a mend it cannot make.

### Alternatives considered

- **The designer draws freely in the engine, with the brand, from the start,** as DEC-030 point 3 has it. Rejected: in the test, that drawing and its mended version did not reach the bar.
- **The draft only shown, and rebuilt at once.** Not taken: a rebuild would be spent on drafts the person might not choose, and the tests rebuilt only drafts the person would ship. Its trigger to revisit: across pieces, the person chooses nearly every draft as it was drawn, and waiting for the choice becomes the bottleneck (COR-007).
- **The person's look as a ship call on the draft.** Rejected: the draft reaches no audience, and the rebuild may lose or gain what the person judged.
- **A review of the draft before the person sees it.** Rejected: no review read the free drafts that reached the bar, and the review reads what the viewing step drew.
- **A draft drawn with no design guidance,** as the tests' sessions drew, or by a session the designer starts with the words and the brief alone. Not taken: the tests do not tell guidance apart from the other differences, and dropping the method would overturn DEC-030 points 3 and 8 on that evidence. Its trigger to revisit: across pieces, the person chooses few of the designer's drafts, or a test that draws drafts with and without the guidance finds the person prefers those drawn without.
- **Several drafts, for the person to choose among.** Not taken: one draft reached the bar in each test, and the person may ask for another (point 2). Its trigger to revisit: the person often asks for another draft.
- **The draft committed in the piece's folder.** Rejected, for point 3's reasons ("Why the draft stays a working file").
- **The draft kept where the previews lie.** Rejected: that place lies in the methodology's own folder, where the designer's grant names nothing (DEC-030 point 5), and only commands write there (DEC-002 points 1 and 9).
- **The rebuild extends a library or the brand as it goes,** by DEC-030 point 4's first way. Rejected, for the reasons of "Why the rebuild extends nothing, and reports needs".
- **The review handed the draft, to report what the rebuild lost.** Not taken: no test measured such a reading. Its trigger to revisit: a test finds that a model's reading of rebuilds against their drafts draws the person's line.
- **The round mends the piece toward the draft.** Rejected: it would be a round of polish, on a judgement of taste.

## Implications

- **Edits made in this change once this record is accepted** (COR-066 point 5). Accepting this record accepts them. Each narrows, widens or completes the passage it edits, and its record's decision stands, so each is made in place, with a forward pointer to this record:
  - **DEC-030 point 3.** Its opening comes to say that a new piece starts with a free draft the person chose, which the rebuild carries into the piece (points 1, 2 and 4). "The brand's roles for type, colour and space" comes to say that a free draft takes none of them, and that the rebuild takes from the brand the role that carries what each of the draft's choices did (points 1 and 4).
  - **DEC-030 point 4.** "Extend a library, through its owner's bar" comes to say that from the rebuild of a free draft until the person's ship call on that piece, the designer extends no library and no brand on its own, and reports a need instead, and that meeting a need is work of its own (points 5 and 6). "Stop" comes to say that in a rebuild, what the brand or the engine lacks is drawn the nearest they allow, without bending the meaning, and reaches the person as a need with the piece (points 4 and 5).
  - **DEC-070 point 2,** "What goes to the person", comes to add, after a rebuild, the rebuild's needs, each with what it drew in its place, and where the draft lies (point 6).
  - **DEC-070 point 5,** "A need", comes to add a finding that only a value or a role the brand lacks would clear. The need names what lacks it (point 6).
- **Read against this record, and left as they stand:**
  - DEC-001 points 2, 3 and 5, since the draft is no piece, is never drawn from, and holds no file of the piece, and raw values stay the brand's;
  - DEC-002 point 1, since the draft lies outside the location;
  - DEC-006 point 7, since the draft is no export and no preview;
  - DEC-007 point 1, since a need is a reason for a library's owner, and no count decides;
  - [visual-communication:DEC-029-piece-brief], since the brief's reasons describe the rebuilt piece;
  - DEC-030 points 1, 2 and 5 to 8, beyond the edits above, since the agents, their writes, the review's kinds of finding and the design knowledge stay as they are;
  - DEC-070 points 1, 3, 4 and 6, since the ship call, what the round mends, whose words are whose and where a fix belongs stay as they are, the brand being already a place a fix belongs (DEC-030 point 7);
  - DEC-070's Implications, whose item "Left open" on a free draft first this record answers;
  - COR-072, since this record places no question at a level.
- **Left to the slices under [project-kit#3468](https://github.com/aleskalfas/project-kit/issues/3468),** each filed once this record is accepted: the designer's definition, for the draft, the person's choice, where the draft lies, the rebuild and its needs; the skill that guides building a piece; the reviewer's definition, for the need it marks on the brand; UC-111, "Have a piece designed and judged by the principles of visual communication", whose main path comes to start with the free draft and the person's choice; and the capability's README.
- **The scratchpad note** `design-review-ship-call` keeps the evidence. Its proposal "A free draft first" drew in the engine with the project's brand, which the test did not support, and this record decides otherwise. The note stays active for page marks, and retires as it says.
- **Its changeset.** This change declares in its changeset that it moves no surface of the capability. It owes no migration (COR-010).
- **Left open:**
  - **page marks against a project's shipped examples,** as DEC-070 leaves them;
  - **pieces of other kinds than presentations.** The person may skip the draft on any piece (point 1). Its trigger to revisit: the person skips it on most pieces of a kind.
