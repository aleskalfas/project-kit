---
id: DEC-006
title: An artefact's text lives in its body alone, and a fingerprint triggers a requirement's revisits
status: proposed
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the words a reader comes for live in an artefact's body, where a repository host shows them, and nowhere else. Those are a term's definition, a requirement's statement, measure and scope, and an actor's needs. A tool reads each from the part of the body that holds it, found by the part's permanent id.

A requirement's front matter keeps `obligation`, a fingerprint of its three texts. So a change to what the requirement obliges still asks for a revisit of what it anchors, though the texts are no longer fields.

## Context

[software-analysis:DEC-001-software-analysis-discipline] point 1 lets a tool take data from an artefact's front matter. Of a body, a tool reads only the links to the terms that a command writes there. So each text a tool reads was put in front matter:
- a term's definition (DEC-001 point 1)
- an actor's needs, and its summary, the first sentence of its opening said again (DEC-001 point 1)
- a requirement's statement, measure and scope, the fields the core's revisit signal reads ([software-analysis:DEC-002-analysis-requirements] point 4, COR-050 point 16)

[software-analysis:DEC-004-domain-model-views] point 7 calls them data, which takes no link.

A repository host shows a document's front matter as a table above its body. On 25 October, the core's glossary opened with a table 1,065 lines long. None of its 80 sections stated what its term means, so a link to a term led to a section without its definition ([project-kit#2051](https://github.com/aleskalfas/project-kit/issues/2051)).

The core's record on sidecars lets a document's data move out of its file (COR-063). Moved there, these texts would leave the page a reader reads.

The capability foresaw the step. As its next step, [software-analysis:DEC-003-analysis-diagrams] point 3 names tools that read a body's parts by their permanent id. The change that builds it refines DEC-001 point 1. DEC-001's alternatives leave that change to decide whether an actor's summary stays.

The capability's maintainer decided the design on 25 October ([project-kit#2051](https://github.com/aleskalfas/project-kit/issues/2051)). The texts move into the body as their only home, and are not copied there. A requirement's revisits fire on a fingerprint of its texts that a command computes, which needs no change to the core.

## Decision

**An analysis artefact's text lives in its body alone, and its front matter keeps the data tools find, relate and list artefacts by. A tool reads a text from the part that holds it, by the part's permanent id. Each requirement carries `obligation`, a fingerprint of its statement, measure and scope, which a command writes and the check holds equal to them. Its revisits fire when the fingerprint changes.**

### 1. The texts live in the body

Five texts move from front matter into the body, each into a part of its kind's structure (DEC-001 point 1):
- a term's definition
- a requirement's statement, its measure and its scope, which says where it holds, for each of the three kinds (DEC-002 point 4)
- an actor's needs

The needs a glossary's head lists beside an actor are text too, which point 5 places. What each text says stays as DEC-001 and DEC-002 decide it.
- **Their parts.** Each part's permanent id is the name of the field it replaces: `definition`, `statement`, `measure`, `applies-to` and `needs`. The structure gives each its label, its hint and its example, as it gives every part.
- **Where they stand.** The definition is a term's first part. The statement, the measure and the scope are a requirement's first three parts, in that order. A reader comes to the artefact for them first. The structure places an actor's needs among its parts.
- **Their forms move with them.** The definition keeps its form. The statement stays one sentence, and the needs one sentence for each need, one item each. The measure may read `None.`, and the scope never does.
- **One home.** No field holds a text, or says one again.
- **Where they bind.** Each part is checked as every part is. Its presence, its order and its form bind where the format rule binds, and at its status (DEC-001 point 1).

### 2. What stays data

Front matter keeps the data a tool finds, relates, lists or links artefacts by. That is an artefact's id and status, the relations its anchors are written from, and the names a check or a link reads. A term's noun forms and the names it replaces are such names. Front matter also keeps the fields a command computes, such as `obligation` (point 6).
- **A title and a name stay data.** A tool lists, links and draws an artefact by its title, and an actor or a term by its name. The heading of the artefact, or of the term's entry, says it again for a reader. The check holds that heading equal to the data, whatever any rule's status, as it holds every other kind's heading.
- **Text or data.** A field of the capability's kinds whose words a reader reads to learn what the artefact says is a text, and lives in the body. A field a reader meets only as a label, or through a tool, is data. The methodology's container is no field of a kind, so the reasons the core keeps there stay there (COR-050 point 1).

### 3. A tool reads a text by its part's permanent id

A tool takes an artefact's data from its front matter, and a text from the part that holds it. The texts a tool reads are those point 1 moves. So are the first sentence of an actor's opening (point 4) and the needs a glossary's head lists (point 5). Of the rest of a body, a tool reads only the links to the terms (DEC-001 point 1).
- **By its permanent id.** A tool finds a part as the check finds it, by the id the structure gives it, never by its label. So a project's relabel changes no tool's reading, once its artefacts carry the new label (DEC-001 point 1).
- **Its words.** A tool that shows or compares a text reads each derived link in it as its words alone. That holds where the place declares the link's form at the state read, as friction reads such a link (COR-050 point 5).
- **A part the body lacks** gives no text, and a tool reads it as absent. It never reads another part's text in its place. So a missing part is no tool's finding, and its presence stays the format rule's to hold.
- **A body it cannot read.** A tool that cannot read an artefact's body gives no answer, rather than a partial one that would read as whole (DEC-003 point 7).

### 4. An actor says who it is in its opening alone

- **No summary.** An actor's `summary` goes. The first sentence of its opening says who the actor is, as its one home (DEC-001 point 1).
- **The overview reads it there.** Its table of who takes part shows that sentence, read from the opening (DEC-003 point 8). It shows the sentence's words, since a link written for the actor's folder would not resolve from the overview's.

### 5. The glossary's head states the needs it lists

Beside each actor a glossary's head lists from another analysis, the head states the needs that actor brings to this one (DEC-001 point 2). Those needs are text, so the head is their one home.
- **Where.** In the head's opening, under the actor's line, one item for each need, each one sentence, as an actor's own needs are.
- **The data.** The glossary's front matter keeps each analysis the head lists, with the version its links name, its terms and its actors. The check holds the head's text equal to that data, as DEC-001 point 2 decides.
- **Read by a tool.** The filler of the readers point reads these needs from the head's opening, by the part's permanent id. It reads an actor's own needs from the actor in the same way (DEC-001 point 8).
- **No term's.** The head belongs to no term (DEC-001 point 1). So a change to the needs it states, or their move from its data, changes no term's content.

### 6. A requirement's revisits fire on a fingerprint of its texts

Each requirement, of each of the three kinds, carries `obligation`: a fingerprint of its statement, measure and scope. A withdrawn requirement carries it too, so its schema stays one. It is an own field of the requirement, outside the methodology's container, since the core's signal reads a source's own fields (COR-050 point 16).
- **Its value** is a hash of the three texts, read in the canonical form of point 7. It names the form's version and the hash it uses, as the overview's fingerprint names its version (DEC-003 point 8).
- **Written by a command.** A command of the capability writes it from the texts, so nobody writes it by hand. Validation names that command wherever the field is missing or no longer verifies. Where a part reads as absent, the finding names that part first, so a writer mends a label rather than writes a new value.
- **Held always.** The check holds it equal to the texts, whatever any rule's status. A requirement without it fails too.
- **The trigger.** The link each requirement's place declares fires on `obligation` alone. Its targets stay as DEC-002 point 4 gives them: every anchor but those its `actors` and `refines` list.
- **What fires it.** A change to the words of the statement, the measure or the scope, as point 7 reads them. Moving a text between homes fires nothing, and nor does emphasis, wrapping or a link the command that links terms moved.
- **No second home.** No reader can read a text from its fingerprint, so the field holds no copy of one.

### 7. The fingerprint's canonical form

The fingerprint reads each text in one canonical form, so one text gives one value in either home. The form reads a text's characters as written, never a rendering of them, and reads both homes the same way.
- **The rule.** The form sets aside what changes only how a text looks, or where a link the command that links terms wrote leads. It counts everything that can change what the text says.
- **A text's characters:**
  - in front matter, the field's value once the front matter is parsed, never the marks that quote it
  - in the body, the part's characters after its label, up to the next part, as the check finds the part
- **What the first version sets aside:**
  - each derived link of a form the place declares at the state read, read as its words alone, as friction reads one (COR-050 point 5)
  - each comment, such as the escape that marks a mention as no mention (DEC-004 point 7)
  - the marks of emphasis and strong emphasis, found as Markdown finds them in those characters
  - wrapping: each run of white space, line breaks included, read as one space, and none at either end
- **What the first version counts as written:** every word with its case and its punctuation, and every other mark. That includes a code span, strikethrough, an escape, an entity, inline HTML and a list's marker. A link of a form no place declares counts as written too.
- **The scope** is read as the other two are: the whole of its part, every sentence of it, never its first sentence alone.
- **The three together.** The form takes them in one order, the statement, the measure and then the scope, each under its part's permanent id. So a text moved from one part to another changes the fingerprint.
- **A part a requirement lacks** reads as absent, which differs from `None.` and from an empty text. So the fingerprint is always defined, and a part removed changes it.
- **Its versions.** A version of the form fixes its rules of reading under the rule above. They are what it sets aside, how it finds where a part ends, and how it finds emphasis. The link forms and the labels it applies come from the state read, as friction and the check read them. Tests of example texts pin each version, in both homes.
- **Each version kept.** The check verifies each value under the version it names, so the capability keeps every version it shipped. The command writes a value under the current version wherever the value a requirement holds no longer verifies.

### 8. The links in the texts

The links between terms reach the texts as they reach every part of a body (DEC-004 point 7).
- **These take links:** a term's definition, a requirement's statement, measure and scope, and the first sentence of an actor's opening. The first mention of a term in each part links to the term's entry. A term is never linked in its own entry. A requirement's texts so count among what is built on a concept, which each view lists (DEC-004 point 7).
- **The needs stay plain,** an actor's own and those a glossary's head lists. A need is a user story, as a use case's goal is, and stays plain as a goal does.
- **Front matter stays plain.** No field holds a text, so no field takes a link.

### 9. Moving the texts

The texts move from front matter, their data home, into the body, one artefact at a time.
- **One home at a time.** Until every live artefact holds its texts in the body, the capability reads each text in either home. An artefact keeps each text in one of them, and validation fails a text written in both.
- **The fingerprint first.** Every requirement carries `obligation` before its revisits fire on it. So the release that moves the trigger comes after a release that ships the fingerprint without it. A project takes the two apart, and the change that moves its trigger finds the field at both states it compares (COR-050 point 16).
- **Word for word.** The move writes each text's characters as they stand, and adds no escape. So a text gives one fingerprint in either home (point 7), and moving it asks for no revisit of what the requirement anchors.
- **A move changes content.** A field that becomes body text changes its artefact's content, so the move flags what anchors the artefact, once (COR-050 point 5). The change that moves an artefact's texts answers what it flags.
- **The head's needs** move in the change that moves their glossary's terms. That changes no term's content (point 5).
- **Withdrawn artefacts move too.** Their kinds' schemas lose the fields, so a withdrawn artefact's texts move with the rest. The move changes no word of a text, so the artefact still reads as it was written.
- **The end.** Live artefacts always move to the current structure (DEC-001 point 1). Once every artefact holds its texts in the body, front matter loses the text fields and `summary`. Their parts are then required as every part is.
- **A summary that differs.** The change that ends the data home drops an actor's summary where it equals the first sentence of the actor's opening. Where one differs, its migration stops and names each such actor. A person settles each before the data home ends.

### What this overturns, and what stands

This record partially supersedes DEC-002. Each overturned passage stays in DEC-002 as it stood.
- **Overturned:**
  - in point 4, that the statement, the measure and where it holds are front-matter fields a tool reads, listed among its fields. They are parts of the body (point 1 here).
  - in point 4, under "What triggers it", the three fields as the link's trigger fields. The link fires on `obligation` (point 6 here).
  - in point 4 and in "Why the declaration leaves the other changes out", that a body part changes none of the obligation. The parts that hold none of the three change none of it.
  - in the Rationale paragraph "Why the statement, the measure and where it holds are front-matter fields", its first two sentences. They say a tool reads front matter only, so the parts the core's signal reads are fields.
  - in the Alternatives considered, the rejection of the three as body parts
- **Stands:**
  - what each of the three says, the fields `actors` and `refines`, and the other parts
  - that a change to any of the three changes the obligation, where it holds included. The rest of that Rationale paragraph says why, and stands.
  - "the three fields", where a standing passage of DEC-002 says it, read as the three texts
  - the link's targets, and the rest of what the declaration leaves out
  - points 1 to 3 and 5 to 9, whole
- **Refined in place,** each naming this record: DEC-001 points 1 and 2, DEC-003 points 3 and 8, DEC-004 point 7 and DEC-005 point 3.
- **Why refined, and not superseded.** DEC-001 left this change to decide whether the summary stays, and DEC-003 point 3 named the change that refines DEC-001 point 1. DEC-002 rejected the three texts as body parts, so this record overturns that choice.

## Rationale

**Why the body is the texts' one home.** A reader reads an artefact on a repository host, where front matter shows as a table above the body. Moved into a sidecar, front matter would not show at all (COR-063). The texts are what the reader came for.
- **In the body** they read in order, under the heading, beside the parts that explain them.
- **One home** keeps them from drifting, as each piece of content has one home (COR-006).

**Why a tool reads them there, by permanent id.** The check reads every part by the id its structure gives it (DEC-001 point 1). So a tool that reads a text there reads what the check holds, and a relabelled part reads the same. DEC-003 point 3 named this as the next step for the capability's tools.

**Why only the texts.** A tool needs a few texts: the readers point carries an actor's needs, and the overview shows who an actor is. Friction needs a change to what a requirement obliges. The rest of a body explains, and no tool needs it. Kept from tools, it stays free to be rewritten for its readers.

**Why a missing part gives no text, and no finding.** The format rule holds a part's presence where it binds (DEC-001 point 1). A tool that failed on a missing part would hold it everywhere else too, and part of one rule would be enforced two ways (COR-051). Read as absent, a missing part leaves each tool an answer, such as an empty cell in the overview.

**Why titles, names and relations stay data.** A tool finds, lists, links and draws artefacts by them, and the anchors are written from the relations. A reader meets a title or a name in the heading, and a relation as a link or a list. So none of them needs a home in a text.

**Why the summary goes.** The summary was the opening's first sentence again, kept in front matter because a tool read front matter alone (DEC-001 point 1). A tool now reads the opening. The copy would add a form to hold and a sentence to write twice, and give a reader nothing.

**Why a fingerprint triggers the revisits.** The core's signal compares a source's own fields (COR-050 point 16). A fingerprint carries a change of the three texts into one field, so the signal follows the obligation with no change to the core.
- **Not a core hook.** A hook that asked a component whether its parts changed would refine COR-050 point 16 for one component's need. A second component that needs a revisit on a body's text is the trigger to weigh it (COR-007).
- **Not any change.** A trigger on any change of content would revisit every anchor for a reworded reason, or a test named again.
- **The maintainer chose it** on 25 October ([project-kit#2051](https://github.com/aleskalfas/project-kit/issues/2051)).

**Why one reading of the characters.** A field's value passes through the front matter's parser, and a body through Markdown, so a rendering of each would differ. Read as characters, by one reading, a text moved word for word gives its old value in every case. The tests of each version hold it there.

**Why the form sets aside emphasis, though friction counts it.** Friction asks whether an artefact's content changed, so it counts every mark a writer makes (COR-050 point 5). This signal asks only whether the obligation changed, for the solution that must meet it, as DEC-002 point 4 narrows it. Emphasis and wrapping change how a text looks, never what it obliges. The requirement's own dependants still see such a change, through its content.

**Why it keeps the rest.** A word, its case or its punctuation can change what a text obliges, as "must" and "must not" do, or a number. So can strikethrough, which removes words without deleting them. A link of another form says where the text points, and a code span names something exactly. So each counts.

**Why the form carries its version.** Unversioned, any change to the form would change every fingerprint, and fire every revisit at once. With its version in the value, an old value still verifies under its own version. A requirement takes the new version when its texts next change.
- **Unlike the overview's.** The overview's fingerprint carries its version too, and an overview under an old one is rewritten freely (DEC-003 point 8). A rewritten `obligation` is a trigger, and fires its revisits. So the check verifies each value under its own version, and every version is kept.

**Why the link forms and the labels come from the state.** The places' declarations are the forms' one home, and friction reads them there (COR-050 point 5). Fixed in a version too, the forms would have two homes, which drift apart (COR-006). A command that comes to write a new form declares it, so the values its links touch keep verifying. A part's end is found the same way, by the version's rule and the structure's labels.

**Why the check holds the fingerprint always.** Friction reads the field to decide whether a change asks for a revisit, wherever the analysis lies. A fingerprint that disagreed with its texts would let a changed obligation pass unrevisited. The check holds it whatever binds, as it holds a shortfall's entries (DEC-001 point 1) and a term's link to its view (DEC-004 point 7). It is no part of a kind's structure, so no rule is enforced two ways (COR-051).

**Why a missing part reads as absent in the fingerprint.** The fingerprint is then defined for every requirement, and removing a part changes it, so the revisit still fires. The fingerprint's check asks for no part, which the format rule holds.

**Why the needs stay plain, and the first sentence takes links.** A need is a user story, as a goal is. The maintainer chose to keep a goal plain, so it reads as the need it states ([project-kit#1895](https://github.com/aleskalfas/project-kit/issues/1895)). In the body, a need stays plain for the same reason. An actor's first sentence stayed plain because it said its summary again, and with no summary it is text like any other.

**Why the glossary's head states its needs.** The needs beside a listed actor are this analysis's to meet, and its reader reads them in the head (DEC-001 point 2). A copy in data was there only for a tool, and the filler now reads text. So the copy would be a second home that serves nothing.

**Why the fingerprint comes before the trigger moves.** The core's signal fires where a trigger field differs between the two states. A field absent at one state differs (COR-050 point 16). Added in the change that moves the trigger, the field would fire every requirement's revisits at once. Present at both states, it fires only where a text changed.

**What it costs.**
- **Checks bind with the rule.** A requirement's texts, a term's definition and an actor's needs were checked by their kind's schema, whatever any rule's status. As parts, they bind only where the format rule binds. In an analysis no rule of `SAN` binds on, a text can go missing unreported, though validation says where no rule binds (DEC-001 point 1).
- **A label gone wrong.** Where the format rule does not bind, a part whose label is misspelled reads as absent. Once its fingerprint is written again, it follows none of that part's text, and no change to the text fires a revisit.
- **What the state supplies.** A project's tightening that adds a label can end a part earlier, in a requirement that already holds that bold text. A place that comes to declare a link form can set aside a link a text already holds. Either way the value stops verifying, and writing it again fires that requirement's revisits once.
- **Text that reads as markup.** A text in front matter may hold characters Markdown reads as markup in a body, such as a tag. Moved word for word, it may show differently. A person who escapes it, in a change of its own, fires its revisits once.
- **One more command.** Each edit of a requirement's texts runs the command that writes its fingerprint. An edit that names a term runs the command that links terms in the same way. Validation names each.
- **Conflicts.** Two branches that edit one requirement's texts conflict on its `obligation` line. The command, run again on the merged text, mends it.
- **Old versions kept.** The capability keeps the code of each version of the form it shipped.
- **A value no reviewer reads.** A change to a requirement's texts changes a hash. The reviewer reads the texts in the change, as for any change of content.
- **A move flags what rests on it, once.** Moving a text changes its artefact's content. So the change that moves it answers each use case and journey that lists a moved requirement. It also answers each view that explains a moved term, and each artefact that anchors a moved actor. Once the moved texts take links, a view's list of what is built on its concepts changes too (DEC-004 point 7). That flags what anchors the view.
- **One upgrade across both steps.** A project that skips the fingerprint's release, and takes both in one upgrade, sees each requirement's revisits fire once, in that change. The field is absent at its base, so nothing in the core can spare it.
- **Answered twice.** A project that takes the steps one at a time answers what anchors each requirement twice. It answers once when the fingerprint is added, and once when the texts move.
- **Each adopter's own move.** A project's analysis moves by a migration, and the project answers what each move flags.
- **Data only front matter shows.** A reader meets some data only in front matter, such as the names a term replaces. A later record of this capability that allows an analysis file a sidecar settles how a reader still sees it.

### Alternatives considered

- **The texts kept in data, said again in the body and held equal by a form.** Rejected by the maintainer ([project-kit#2051](https://github.com/aleskalfas/project-kit/issues/2051)). Two homes would be kept in step for a tool that can read the body. Moved into a sidecar, the data would be the copy no reader sees.
- **The three requirement texts kept in data, and the rest moved.** Not taken. It was the fallback, had neither the fingerprint nor a core hook been taken. A reader would still meet a requirement's obligation in a table.
- **A core hook that asks a component whether its parts changed.** Not taken. It refines COR-050 point 16, and needs the backbone's work, for what one field gives.
- **A trigger on any change to a requirement's content.** Rejected. A reworded reason, or a test named again, would ask for a revisit of every anchor.
- **A fingerprint of the text as written.** Rejected. Moving a text, or a run of the command that links terms, would change it, and fire every revisit.
- **A form read from a rendering of each home.** Rejected. The front matter's parser and Markdown read the same characters differently, so a text moved word for word could change its value.
- **A form that also sets aside case and punctuation.** Rejected. Each can change what a text obliges.
- **A form fixed for good, with no version.** Rejected. Any change to it would fire every revisit at once.
- **The link forms fixed in each version.** Not taken. They would have a second home beside the places' declarations. A new form the command that links terms writes would then count as written, and fire the revisits of each text that holds one.
- **A fingerprint for each text.** Not taken. One field is one trigger, and the link names a list of fields either way.
- **The fingerprint inside the requirement's friction block.** Rejected. The core's signal reads a source's own fields, never its block (COR-050 point 16).
- **The fingerprint checked only where the format rule binds.** Rejected. Friction reads it wherever the analysis lies, so a stale value would hide a changed obligation there.
- **A tool, or the fingerprint's check, failing on a part the body lacks.** Not taken. It would hold a part's presence where the format rule does not bind, so part of that rule would be enforced two ways (COR-051).
- **An actor's summary kept, held equal to its opening.** Rejected by the maintainer. The opening says it, and a tool reads the opening.
- **Titles and names moved into the body too.** Rejected. A tool lists, links and draws by them, and the heading shows each to a reader.
- **The needs taking links, as other text does.** Not taken. A need is a user story, and stays plain as a goal does.
- **The head's needs kept as data.** Rejected. A reader reads them in the head, and a copy in data would be a second home.
- **A tool finding a part by its label.** Rejected. A project may relabel a part, and the tool would lose it.
- **Every part of a body readable by a tool.** Not taken. No tool needs more than the texts. A use case's path and a journey's seams wait for a step of their own (DEC-003 point 3).

## Implications

- **The capability builds it in steps,** each a change of its own:
  - the fingerprint on each requirement, the command that writes it and its check, with a migration that writes it for adopters
  - each text read in either home, the trigger moved to `obligation`, and each reader of a text following it
  - a command that moves an artefact's texts into its body, and a stamp that writes them there
  - the end of the data home: the fields and `summary` leave the schemas. A migration moves an adopter's texts and its own structures' hints (COR-010).
- **Adding `obligation`** changes each requirement's content once, so the change that adds it answers what anchors each requirement. Its migration writes the field on withdrawn requirements too.
- **The releases.** The release that moves the trigger comes after one that ships the fingerprint alone (point 9). The later release tells a project that skips the earlier one what skipping costs.
- **The check** holds a term's heading to its id and its name, whatever any rule's status, as it holds every other kind's heading (point 2). A glossary that passed before may fail, so it lands with the end of the data home, the capability's breaking change (DEC-001 point 1).
- **The overview** reads the first sentence of each actor's opening, so the version its fingerprint carries rises (DEC-003 point 8).
- **The command that links terms** links the texts point 8 names, and leaves the needs plain.
- **`SAN`'s rules** that name a text read it in the body, once the data home ends. A project's own rules that read a text follow.
- **The authoring skill and the capability's agent** teach the texts in the body.
- **DEC-002** is partially superseded, as "What this overturns, and what stands" lists. DEC-001 points 1 and 2, DEC-003 points 3 and 8, DEC-004 point 7 and DEC-005 point 3 name what this record adds to them.
