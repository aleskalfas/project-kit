---
id: DEC-030
title: A designer turns a piece's brief into a piece, and a reviewer judges the drawing against faults, rules and the brief
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability has two design agents. `graphic-designer` turns a piece's brief into a piece. It names what the content's structure is before it chooses a form, and writes down why each choice was made. Where the libraries cannot draw the design, it improves a library its owner lets it, makes a component for that piece alone, or stops and says what is missing. It never changes what the piece says to fit what a library draws. It writes only the visual work its repository holds as its own. `graphic-design-reviewer` judges what was drawn: whether a page shows what it should, keeps the capability's rules and does what its brief asks. Each of its findings says what it rests on: a fault, a rule by its id, a part of the brief, or a note, which never fails. It reports, and never redesigns. Both agents read one document the capability ships of what published design practice teaches, each idea cited by its author, and hold no rule of their own. The agent that translates is decided apart.

## Context

The founding record has the capability carry its view of good visual communication as rules a reviewer judges, and as agents that make, review and translate pieces. Records of their own decide them ([visual-communication:DEC-001-visual-communication-discipline] point 1). The viewing step's record gave the reviewer its first form: read-only, advisory, and reporting what no check measures on the drawn result. It left the boundaries among the capability's agents to this record ([visual-communication:DEC-015-viewing-step-and-reviewer] point 7).

The showcase deck of the repository the capability is authored in shows what is missing ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)). Builders fitted each slide into general-purpose parts to meet technical criteria, and nothing was designed. A stepped pyramid that showed an order became five equal bars in five unrelated hues. Elsewhere were grey boxes, small titles, weak hierarchy, crossing arrows and colour with no meaning. Every check passed, and no fault the reviewer looked for was there.

On 31 October the maintainer agreed to three agents, split by kind of work rather than by part of design, such as type or colour ([project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584)):
- **A designer,** `graphic-designer`, which makes pieces and builds the project's libraries.
- **A reviewer,** `graphic-design-reviewer`, which reads a whole piece as drawn, checks its facts against the repository, and takes its rules only from the rule sets.
- **A translator,** which writes nothing itself. It is no design agent, and [project-kit#2582](https://github.com/aleskalfas/project-kit/issues/2582) decides it.

Four facts shape the agents:
- **Who owns a library differs by repository.** In a project, a library the capability ships is a copy the project never edits by hand ([visual-communication:DEC-013-shipped-library-releases] point 5), and the capability's folder is a synced copy (COR-001). Where the capability is authored, its folder is the source, and each shipped library's *version being built* is that repository's own file (DEC-013 points 1 and 2).
- **A rule binds on a piece only where the backbone says so.** Rules bind on artefacts, and every reader takes the backbone's one answer (COR-051 point 7). A piece's content is no artefact yet ([visual-communication:DEC-001-visual-communication-discipline], Implications), so no rule binds on it.
- **A piece may keep a brief** that says what it must show and why it is designed so ([visual-communication:DEC-029-piece-brief]).
- **A core reviewer judges a change's text** against the accepted rules that bind on it, every part no check is declared to enforce. It reads the change, each artefact it judges, and what each rule names that it needs (COR-057 point 1). Nothing in that list renders a piece, so it sees a drawing only where a rule names one.

## Decision

**The capability has two design agents. `graphic-designer` turns a piece's brief into a piece by a designer's method. Where the libraries cannot draw the design, it extends a library through its owner's bar, makes a local component, or stops, and never bends what the piece says. It writes only what its repository holds as its own source. `graphic-design-reviewer` judges what was drawn. Its findings are faults, rule findings, brief findings and notes, kept apart by what they cite. The designer mends the faults, the brief findings and each rule finding a binding rule's text settles, and leaves the rest to a person. The reviewer reports and never redesigns. Both read one design reference, which cites the published practice of design by name, and hold no rule. The translator is decided apart.**

### 1. Two agents, by kind of work

- **Where they live.** Both are the capability's agents, since their work implies its discipline (COR-026).
- **One makes, one reads.** The designer produces pieces and libraries. The reviewer reads what was drawn, and changes nothing. Neither does the other's work.
- **The translator** is [project-kit#2582](https://github.com/aleskalfas/project-kit/issues/2582)'s. This record decides nothing of how a translation is made. The designer writes each content file of a piece, a translation included.
- **Neither is a fixer.** A *fixer* is an agent started on what drifted, to propose its mend. It may claim no path and change no file ([project-management:DEC-056-drift-fixers] point 1), and the designer does both. Whether pieces get a fixer waits until a piece's facts carry anchors.

### 2. The designer turns a brief into a piece

- **What it makes.** A piece, from its brief and the facts it is given: the brief's reasons, the piece's own file, its content in every language, and its local components. It renders, checks and looks only through the capability's commands.
- **What it builds.** The project's own libraries: a local component promoted once other pieces need it, a brand, a notation, or a component library of the project's ([visual-communication:DEC-001-visual-communication-discipline] point 5).
- **The brief's intent is the asker's.** It writes the brief's goals and relations from what whoever asked for the piece says ([visual-communication:DEC-029-piece-brief] point 4). It shows them to that person, or returns them to whoever dispatched it, before it designs against them. It writes the reasons as it designs.
- **Run either way.** It works as a session's own agent, or dispatched by another. Where it can start agents, it dispatches the reviewer. Where it cannot, it asks whoever dispatched it to, and says the piece is not reviewed.
- **When it stops.** While it builds, it looks at each page it changes. Before it stops, the reviewer reads every page in every language, mode and size the piece has, each band of a tall page included (DEC-015 point 7; [visual-communication:DEC-022-web-site-and-parts] point 7). It stops when that reading reports no fault, no settled rule finding and no brief finding. It judges its own pages against the same kinds first (point 6).
- **What goes to the person.** Notes, rule findings for a person, and rule findings that inform (point 6). The person decides on them. A finding that two rounds of mending have not cleared goes to the person too, and the designer stops there. It also stops where point 4 says.
- **The report whole.** It hands the person the reviewer's report as the reviewer wrote it, not a summary of it.

### 3. The designer's method

The method makes its choices in the order of the brief's aspects ([visual-communication:DEC-029-piece-brief] point 2). The structure comes first, then the form and the visual variables that carry it, then the hierarchy, and last type, colour and space.
- **The structure before the form.** It names what the content's structure is before it chooses a form. It chooses the form by its job, as the starter's README lists its patterns by the question each answers ([visual-communication:DEC-007-starter-library] point 2).
- **Another form weighed.** It weighs at least one other form, and says why it chose this one.
- **The brand's roles for type, colour and space.** It takes them from the brand the piece names, and a concept's colour from its notation (DEC-001 point 6).
- **The reasons as it chooses.** It writes a reason for each choice into the brief, in the brief's order.
- **The steps are its body's.** How it reads a brief, names a structure, picks the visual variables and looks at its pages, its body says, with the design reference of point 8.

Two habits of the method guide its choices:
- **Fix at the root.** The whole piece's look belongs to the brand and the foundations. A reusable form belongs to a component library, and a concept's look to a notation. Only a true one-off stays in the piece (DEC-001 point 5, DEC-007 point 4).
- **Keep the accepted records' limits.** Where one stands in the design's way, it stops and names the record. It never works around it.

### 4. Where the libraries cannot draw the design

It takes one of three ways, by where the need belongs:
- **Extend a library, through its owner's bar.** A form other pieces need goes to the library that holds such forms. In the project's own library, it goes into a version not yet released ([visual-communication:DEC-003-change-over-time] point 6). Where the capability is authored, it may go into a shipped library's version being built. The owner judges it by the bar that owner keeps, such as the starter's bar for entry (DEC-007 point 3).
- **Make a local component** for a form this piece alone needs ([visual-communication:DEC-001-visual-communication-discipline] point 4), or have a helper write one (DEC-001 point 8).
- **Stop.** Where neither way draws the design, it reports what the design needs, why nothing draws it, and what would. An example is a form that needs a tool the engine lacks (DEC-007 point 2).

Three limits hold on those ways:
- **A library it may not write** takes a request to its owner instead. That is a shipped library in a project, or a library of another repository. Meanwhile the work goes on with a local component, or waits.
- **A shipped library serves every project.** A change to one serves any project, not the piece at hand (COR-014). A shipped brand stays a brand to start from, and one project's identity goes into that project's own libraries (DEC-001 point 9). A choice other libraries build on, such as a new shared role, waits for its record (COR-065 point 3).
- **Never bend the meaning.** It never draws a relation the brief names as another, nor adds or drops a difference the content has, to fit what a library draws. An order drawn as equal bars in unrelated hues is such a bend.

### 5. What the designer may write

- **What people write.** It writes the files of the project's visual work that a person writes ([visual-communication:DEC-002-files-and-validation] points 1 and 5):
  - a piece's own file, but for what commands rewrite in it, and its content, its brief, its local components and its pictures;
  - a version not yet released of the project's own library;
  - a declaration that a brand be written out as code.
- **Where its grant names them,** also a helper script and the shared content its pieces read. Either may belong to another: a helper is the project's code, and a shared model may be another capability's.
- **What commands write** stays theirs (COR-013 point 2): a lock, a findings record, an export, a produced output, a copy of a shipped library, a release. It runs those commands where its body says.
- **Never:**
  - a released version of any library (DEC-003 point 6);
  - a copy of a library the capability ships, which only the command that brings it in writes (DEC-013 point 5);
  - the capability's folder where sync keeps a copy of it (COR-001);
  - a sign-in's secrets, which the methodology's shared sign-in keeps (DEC-002 point 8);
  - a file of another repository, before the person confirms that write.

  Several of these lie in the location, beside what it writes. Its body keeps them apart, since a grant cannot: a version's folder keeps its path once it is released.
- **The grant.** An overlay category of the capability's own names the designer's paths, in its `owns` (COR-013 point 2; the agents README, "Adopter overlay"). No other agent names it. It names the location, and any folder of helpers or shared content a project adds. It names nothing inside the methodology's own folder, where the location never lies (DEC-002 point 1). So no question of what sync manages arises for it, in any repository.
- **Granted before it writes.** While a project leaves the category undefined, the deploy skips the designer, and says which category it lacks (the agents README, "An undefined category"). No conventional folder fills it, so a person writes it into the overlay. So nothing writes the project's visual work until a person grants it. The capability's report of its state, which shows the location, names the overlay line to add.
- **One location, one record.** The location is recorded in the capability's configuration (DEC-002 point 1). Where the category is defined, the capability's check fails a value that does not cover the recorded location, or that lies inside the methodology's folder. The project corrects either in its overlay (DEC-002 point 7). The check resolves the category as the deploy does, a per-agent override included. Moving the location names the overlay line to change, and writes nothing in the agents' area.
- **Where the capability is authored,** the capability's folder is the source, and a shipped library's version being built is that repository's own file (DEC-013 point 2). The designer may change it there, by point 4, as source work outside its grant, as other agents change the capability's code there. It does so only where the capability's folder is no synced copy, the condition the release of a shipped library keeps (DEC-013 point 1). Releasing it stays with whoever maintains the capability. What the change owes besides, such as its changeset (DEC-013 point 4), it names for whoever lands the change. The capability's code, schemas and records are not the designer's.

### 6. The reviewer's four kinds of finding

- **What it judges.** What was drawn, read as the piece's declared audience, where it is shown, in each language and mode. It judges whether a page shows what it should and a reader can read it (DEC-015 point 7). It also judges whether the piece keeps the rules the rule sets hold for it, and shows what its brief asks.
- **Its findings stay apart by what they cite:**
  - **A fault** is one of the agent's list of faults (DEC-015 point 7). A fault is a drawing that does not show what the content, the brand or a passing check says it should. It is never a judgement of how well the page is designed.
  - **A rule finding** cites a rule by its id, read from the rule-set file that holds it, never from the reviewer's own body. It binds only where the backbone's answer says that rule binds on the file the finding names for its fix: a content file, the brief, a local component or the piece's own file. Elsewhere it informs, as a break of a rule that binds nothing does (COR-057 point 1).
  - **A brief finding** cites the part of the brief it rests on, by page and part, and says what the drawing shows against it.
  - **A note** is anything else worth a look: a matter of taste, which names the practice it draws on (point 8), or a doubt it cannot settle, which says why. A note never fails.
- **A binding rule finding, settled or for a person.** It is *settled* where the rule's text settles the break with no reading left to choose. It is *for a person* where judging it needs a reading the rule does not settle, or a fact the rule does not name. The rule-set reviewer tells its settled breaks from its passages for a person the same way, on the text a change owns (COR-057 point 3). This reviewer judges a piece whole, not a change, so it has no ownership to weigh.
- **One observation, one finding.** Where one rests on more than one ground, it cites each. It takes the first of these kinds that applies: a fault, then a rule finding, then a brief finding.
- **Which rules it reads while none binds.** A piece's files are no artefacts yet, so no rule binds on them, and every rule finding informs. Meanwhile it reads the rule sets the capability ships, and any set of the project's own that inherits one, each from its file. The set the capability loads into sessions binds a session's work, not a piece (COR-070), and is not among them.
- **Their reach from the backbone, never from a dispatcher.** Once a rule can bind on a piece's file, the reviewer reads which rules bind from the backbone's own answer, through a read-only query. No one who made the piece hands it that answer. The change that brings a piece's files under rules gives it that query, the one command the reviewer runs (point 7).
- **The reasons last.** It judges a page against the brief's relations, goals and takeaway first, and only then reads the brief's reasons. A reason that does not hold of the drawing is a brief finding. So a reason never stands in for what the page shows.
- **What it says it read.** Its report names the pages, bands, languages, modes and sizes it looked at (DEC-015 point 7; DEC-022 point 7). It also names the brief it read, or that the piece has none, and the rule sets it read.
- **Advice.** Its findings join no validation and hold no merge, until a record gives them a place there ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)). The designer mends faults, settled rule findings and brief findings before it stops (point 2).
- **What records leave to a reviewer's reading of a drawing,** it reads. Examples are a text over a picture ([visual-communication:DEC-004-brands-and-notations] point 8), and a picture with the piece's words drawn into it ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 2). So are the review of a starter component's reference renders (DEC-007 point 3), and a role's default as a fair stand-in as they show it ([visual-communication:DEC-008-library-role-defaults] point 2). Its findings there inform the owner, who decides. A helper's read of a file it did not declare is code, which whoever reviews the project's code judges, not this reviewer.

### 7. The reviewer's boundaries

- **With the checks.** What a check measures stays the check's. A part of a rule its owner declares a check enforces is that check's (COR-051 point 2). A fault the check already reports is named in one line.
- **With the rule-set reviewer.** That reviewer judges a change against the accepted rules that bind on what it alters, by hand or where a gate asks (COR-057 points 1 and 5). It judges every part of such a rule that no check is declared to enforce, and sees a drawing only where a rule names one. While no rule binds on a piece, it judges nothing there. This reviewer judges a piece whole, as drawn. Its findings stand for no verdict of the rule-set reviewer's, and that reviewer's for none of this one's. A part judged by both would draw two findings that can disagree (COR-057, Rationale, "Why it never judges a check's part"). The question left open below settles it.
- **It reports, and never redesigns.** Each finding names what is wrong, where, what it rests on, and where the fix belongs: the piece, a local component, a library or the brand. It draws, writes and proposes no new design.
- **Facts from the repository.** It checks each fact a piece shows against the source the piece names, reading the repository, such as a count or a file a command's output was kept in. It guesses none it cannot find, and says what it could not. A fact its source contradicts is a rule finding where a rule asks that facts hold, and otherwise a note that names the source.
- **Read-only.** It changes nothing it reviews. It runs no command but the read-only query of point 6, once a change gives it one.

### 8. Both read one design reference, and hold no rule

The capability ships one *design reference*: a document of what the established practice of visual communication teaches, each idea cited by its author and work. Both agents read it, and neither body copies it. It covers at least six topics:
- the message first, and a piece that explains told apart from one that only shows;
- a form that says what the content says, and the visual variables that carry it;
- hierarchy, grouping and alignment;
- type, grid and space;
- colour for meaning and for contrast, never the only cue;
- diagrams, and consistency across a piece.

The reference chooses the works it cites under each topic, and says what each teaches.

What that knowledge is, and is not:
- **How to design and judge, never what to require.** A requirement that fails a piece is a rule in a rule set, with its id and origin (COR-051), or a part of its brief. A value, such as a type size or a colour, is a brand's (DEC-001 point 5). A threshold a check measures is the check's.
- **The canon, not one project's taste.** It is what the field teaches, so it serves every project (COR-014). A project's taste lives in its own brand and rule sets (DEC-001 point 9).
- **One reference for both.** So the designer designs to what the reviewer reads by. A rule that rests on one of its sources cites that source in its own origin, and the reference does not restate the rule.

## Rationale

**Why a designer with a method.** The deck failed because nobody designed it: each slide was fitted into the nearest part. A method that names the structure before it chooses a form catches the pyramid's loss before anything is drawn. That is what Mackinlay's expressiveness asks: a form shows all of the content's structure, and nothing it lacks. The reasons it writes let the next designer, or the reviewer, see what each choice was for.

**Why this record decides the method's order, and the body its steps.** The order of the choices, and the reasons they leave in the brief, are what a reviewer and a later designer rely on, so they hold for every design. How each choice is made is judgement, applied with the knowledge the role reads (COR-006). The skill that guides building a piece holds the tool's procedure: render, check, look and mend. A person follows it as the agent does.

**Why extend, make or stop, and never bend.** Bending is how the pyramid became bars. A stop brings a missing form into view, so it is built once, at its root. An extension through the owner's bar keeps a shared library's promise to every piece that uses it.

**Why the designer clears only settled rule findings.** A rule binds only where the backbone says, so that a project chooses its rules by its sets, their statuses and their pins (COR-051 point 7). An agent that cleared every rule it read would bind rules wherever it runs, a proposed one among them. A binding rule whose text leaves a reading open is a person's to judge (COR-057 point 3). The person sees the rest and decides.

**Why two rounds, then the person.** A finding that one mend did not clear may have been mended at the wrong root, and a second mend can find the right one. A finding that two mends did not clear is one the designer cannot settle alone. Further rounds would spend the person's wait with no news.

**Why the grant names only the location.** The location lies outside the methodology's folder in every repository (DEC-002 point 1). So the grant never meets what sync manages, and needs no guard of its own over it, in a project or where the capability is authored. Where the capability is authored, a shipped library's version being built is source work, done there as the capability's code is, on the condition its release keeps (DEC-013 point 1). A synced copy would be overwritten by the next sync, and a shipped copy replaced by the command that brings it in (COR-001, DEC-013 point 5), so neither is written at all. The check holds the grant to the recorded location, so a moved location leaves no stale grant.

**Why one reviewer, and not a second.** One reading of the drawn pages, with one account of what was looked at, serves every kind of finding. A second agent would read the same images again, and the line between a fault and a rule finding would fall between agents rather than between citations. Kept apart by what they cite, each finding is weighed by what it rests on. A fault is weighed by what the page should show, and a rule finding by the rule's status and reach. A brief finding is weighed by the intent, and a note by the practice it names.

**Why rules only from the rule-set files, and their reach from the backbone.** A copy in an agent has no id, no status and no acceptance, and drifts from its set (COR-057, Context). A shipped agent that held one project's rules would carry that project's taste to every project (COR-014). Once a rule can bind on a piece, the reviewer asks the backbone itself which rules bind, as the rule-set reviewer does. So nobody who made the piece stands between it and the answer. Until then the answer is the same for every piece's file, so the query waits for the change that makes it differ (COR-007).

**Why the reasons are read last.** A reviewer that reads the designer's reasons first sees the page through them. A reviewer kept from them could check no reason against the drawing. So it reads them, but only after it has judged the page against its intent.

**Why notes never fail.** A reading of taste never fails (DEC-002 point 7), and a doubt is not yet a finding. A note that cites its source still teaches, and the person decides.

**Why it never redesigns.** A reviewer that redesigns becomes a second designer, and its review of its own design is no review. Naming where the fix belongs is enough for whoever mends it.

**Why one design reference, cited by name, and no numbers.** A cited idea can be checked and learned, and a reader can tell the field's practice from an agent's habit. One reference read by both agents cannot drift into two versions. Its topics are what every design asks about, so this record decides them. Which works it cites is the reference's to choose, so a better work can replace one with no change of record. Numbers such as a type size are values, and differ from brand to brand. In an agent they would ship one brand's values to every project.

### Alternatives considered

- **A second reviewer for the rules and the brief, beside the reviewer of faults.** Rejected: two readings of the same pages, and a boundary between agents where one between citations serves.
- **The rules written into the reviewer's body.** Rejected: a copy drifts, and would carry one project's taste to every project.
- **The answer of which rules bind, handed to the reviewer by whoever dispatches it.** Rejected: the designer would hand the answer that decides whether its own findings bind.
- **The reviewer kept from the reasons entirely.** Rejected: no reason would be checked against the drawing.
- **The design knowledge copied into each body.** Rejected: two copies drift.
- **The works the reference cites, named in this record.** Rejected: each would bind as a floor with no reason of its own, and a better work could not replace one without a change of record.
- **The designer as the fixer of pieces.** Rejected: a fixer may claim no path and change no file ([project-management:DEC-056-drift-fixers] point 1).
- **A designer that writes only inside its piece.** Rejected: no library could be improved, and every form would be rebuilt in each piece.
- **A designer that may edit any library it uses, a shipped copy included.** Rejected: the next sync or the command that brings it in would undo the edit (COR-001).
- **A grant over each shipped library's version being built, where the capability is authored.** Rejected: the grant would reach into the methodology's folder, where a grant may name nothing sync manages (the agents README, "Write-carrying categories"). Allowing it needs a refinement of the core's rule for write grants first, and a capability's own category that carries writes. The version being built is source work there anyway.
- **A guard of the capability's own over a grant that reaches a synced copy.** Rejected: it would decide write authority a second way, beside the core's one rule.
- **A reviewer that proposes the redesign.** Rejected: it would review its own proposal.
- **The method in the skill that guides building a piece.** Rejected: the skill is the tool's procedure for everyone, and the method needs the knowledge the role reads.

## Implications

- **Edits made in this change once this record is accepted,** each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-015 point 7, "It reads, and does not draw,"** comes to add that the reviewer also reads the piece's brief, the rule-set files, and the sources in the repository that the piece's facts name (points 6 and 7).
  - **DEC-015 point 7, "Its remit,"** comes to add whether the piece keeps the rules the rule sets hold for it, and whether it shows what its brief asks (point 6).
  - **DEC-015 point 7, "Its findings,"** comes to say that they are of four kinds, a fault, a rule finding, a brief finding and a note, kept apart by what they cite, and that a fault is no judgement of design (point 6).
  - **DEC-015 point 7, "Nothing unseen reads as clean,"** comes to add that the report names the sizes it looked at, the brief it read or that the piece has none, and the rule sets it read (point 6).
  - **DEC-015 point 7, "Left to others,"** comes to say that the reviewer judges a piece against the rule sets' rules, and that this record decides the agents and their boundaries. It names the translator as [project-kit#2582](https://github.com/aleskalfas/project-kit/issues/2582)'s.
  - **DEC-001's Implications, "Left to later records or refinements,"** comes to name the agent that translates in place of the agents.
  - **The reviewer's agent file** comes to say what points 6 and 7 decide:
    - its description names the four kinds;
    - its body reads its rules only from the rule-set files, and reads the brief, its reasons last;
    - its faults are defined as point 6 defines them, and a doubt is a note;
    - it states the boundaries of point 7;
    - it drops "Whether a piece keeps to the rules of visual communication is not your question";
    - its reads gain this record and [visual-communication:DEC-029-piece-brief].
- **Read against this record, and left as they stand:**
  - DEC-001 point 1, since the design reference of point 8 is the agents' reading, not a third carrier of the capability's view beside its rules and its agents.
  - DEC-015 point 7's "Whose" and "Advice, for now", which the reviewer keeps.
  - DEC-002 point 9, since the designer's writes are a person's, and the commands' stay theirs.
  - DEC-006 point 2, since its reviewer of a picture with words drawn into it is this one, and its reviewer of a helper's undeclared read is whoever reviews the project's code.
  - DEC-007 point 3, since its owner judges a component's entry.
  - DEC-022 point 7, since the reviewer names each size the piece names.
- **This record rests on [visual-communication:DEC-029-piece-brief],** so that record is accepted first.
- **[project-kit#2583](https://github.com/aleskalfas/project-kit/issues/2583)** asked who judges a piece against the rules of visual communication (DEC-015 point 7). This record answers it, so that Feature keeps only which rules ship.
- **Tasks filed under [project-kit#2584](https://github.com/aleskalfas/project-kit/issues/2584) once this record is accepted:**
  - **The design reference of point 8,** with the reviewer's reading of it. It starts from these works, and may replace any with a better: Michael Alley, Barbara Minto, Ben Shneiderman, Nancy Duarte and Richard Mayer on the message; Cole Nussbaumer Knaflic on explaining and showing; Jock Mackinlay, Jacques Bertin, Lohse and others, and Yuri Engelhardt on form; Adam Wathan and Steve Schoger, Gestalt and Robin Williams on hierarchy; Tim Brown, Robert Bringhurst and Josef Müller-Brockmann on type and grid; Josef Albers, Cynthia Brewer and WCAG 1.4.1, 1.4.3 and 1.4.11 on colour; Colin Ware, Edward Tufte and Jakob Nielsen on diagrams and consistency.
  - **The designer agent,** authored with the skill that authors agents, with its overlay category. Its body starts from the design notes written for the showcase deck's redesign ([project-kit#2883](https://github.com/aleskalfas/project-kit/issues/2883)). The Task strips from them what is no knowledge: the numbers, which are a brand's values; the pass bar, which is a project's; and one project's audience and paths (COR-014).
  - **The check of the designer's grant** against the recorded location, and the overlay line the capability's report of its state names (point 5).
  - **The capability's pages,** where they describe the reviewer, and the skill that guides building a piece, where it hands work to the reviewer.
- **Left open:**
  - **How a part of a rule that only a drawing shows is judged** once a piece's files are artefacts. The rule-set reviewer owns every part no check enforces, sees a drawing only where a rule names one, and approves nothing it cannot judge (COR-057 points 1 and 3). So before a rule set of a project's own selects a file of a piece, the core says how such a part is judged, or the capability's rules keep it out of rules that bind on text ([project-kit#2416](https://github.com/aleskalfas/project-kit/issues/2416), [project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676)). From then on, any component that contributes the rule-set reviewer to a gate covers those files (COR-057 point 6). This record is revisited then.
  - a fixer of pieces, once a piece's facts carry anchors;
  - a required review of a piece's change ([project-kit#2676](https://github.com/aleskalfas/project-kit/issues/2676));
  - the translator ([project-kit#2582](https://github.com/aleskalfas/project-kit/issues/2582));
  - drawing another capability's visuals, through a contract (DEC-001 point 10).
