---
id: COR-063
title: A document may keep its data in a sidecar, where its type allows one
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a document's front matter may move out of its file into a *sidecar*, a file of its own beside the document. A reader of the document then meets its text alone. The owner of the document's type says whether its documents may do so, and validation fails a sidecar that no type allows.

The checks read a sidecar wherever they read its document, whatever the owner says, so old commits never lose their data. A document keeps its data in one of the two files at a time, and moving it between them is no edit. Decision records and rule-set files always keep their front matter.

## Context

A document's front matter holds its data: its own fields, such as its id and status, and the methodology's container with its anchors (COR-053 point 10). The anchors-and-friction record finds an artefact by it (COR-050 point 1). A host that renders the document, such as a code-hosting site, shows the front matter as a table above the text. A document with many anchors, or a collection file with many entries, opens with a table longer than its text.

So the reader who came for the text meets the bookkeeping first. Tools read the data and people read the text, yet both sit in one file, the data first. Moving the data out of the file needs every reader of it to agree where it lives. Those are the checks, validation, the commands that write documents, and every component that judges a change by the paths it touches.

Not every document can move. A project may publish its documents through a site generator that reads keys of its own in their front matter. A decision record or a rule set that the methodology or a component ships is read where it arrives by sync, in a tree that no place reads (COR-050 point 14).

## Decision

**A document may keep its data in a sidecar beside it, where the owner of its type allows one, and validation fails a sidecar that no type allows. The backbone reads a sidecar wherever it reads its document as an artefact, whatever the permission. A decision record and a rule-set file never have one.**

Three terms recur:
- A document's **data** is what its front matter holds: its own fields and the methodology's container (COR-053 point 10). A collection file's data maps its entries by id (COR-050 point 1).
- A **sidecar** is a file beside a document that holds the document's data in place of its front matter (point 1).
- A document's **home** at a state is where its data lives there: its front matter, or its sidecar. Front matter that does not parse, and empty fences, are a home. So is a sidecar that does not parse. Empty fences hold no data, though, which point 9 reads.

Where the records on anchors, connection points and types speak of an artefact's front matter, they mean its data, in either home (COR-050, COR-053 point 10, COR-056 point 4). That reaches an artefact's front matter only, read as its data. A file format a harness calls front matter, such as an agent definition's, keeps its meaning. This record says *front matter* for the form in the file only, where it sets the two homes apart.

**Received files.** In a tree the project receives by sync, validation fails none of this record's findings, since the project cannot mend them there (COR-055 point 1).

### 1. A sidecar, and where it sits

A sidecar is one file for one document, holding the document's data as its front matter would.
- **Its path** is derived from its document's path alone, by a rule the backbone fixes, the same in every project. The rule never changes, since every past state is read through it.
- **A collection file's sidecar** holds what its front matter would, the map of its entries by id included. An entry's content is its entry in the sidecar together with its body section, as COR-050 point 1 reads an entry in front matter.

### 2. A sidecar is part of its document for every judgement made by path

The backbone and every component read a sidecar as part of its document, at the document's path, and never as a file of its own.
- **Anchors.** A path anchor, or an anchor of a registered kind, stands on the documents it names, each with its sidecar's data where point 3 reads it. It never stands on a sidecar's file or its mode. So an anchor that names only sidecars names nothing, and is dead as one that matches only answer files is (COR-062 point 2).
- **The excluded paths and the declared surface** reach a sidecar exactly where they reach its document (COR-050 points 7 and 8).
- **No artefact.** No place reads a sidecar as a document, or as a placed data file (refinement per COR-071), and neither measure counts one (COR-050 point 8).
- **A component** that judges a change by the paths it touches reads a change to a sidecar as one to its document. One such judgement is a review that a change to code requires.

### 3. The backbone reads a sidecar wherever it reads an artefact

- **Wherever the document is read as an artefact.** The backbone reads a document's sidecar wherever it reads the document's content as an artefact's. That is wherever a place holds the document at one of the states compared (COR-050, on what an anchor stands on). A decision record and a rule-set file are the exception (point 5).
- **Found by its document.** At each state, the backbone finds the sidecar from the document's path there, the document's renames followed. A sidecar's own history is never followed apart from its document's.
- **Reading never depends on a permission.** The backbone reads a sidecar whatever the document's type, and whatever a type registry says, at that state or at any other. So history reads a document whose type allowed a sidecar once and no longer does. Friction reads no type (COR-056 point 5).
- **Nowhere else.** Beside a file whose content the backbone does not read as an artefact's, a sidecar is never read as data. No synced tree is a place (COR-050 point 14), so a sidecar a project receives by sync is never read as data.
- **Not beside a placed data file.** A placed data file is its data, so a sidecar beside one is never read as data (refinement per COR-071).

### 4. The owner of a document's type allows a sidecar

- **Declared with the type.** A type's owner says, where it declares the type, whether a document of that type may keep a sidecar. For a component, that is the type's entry in its type registry (COR-056 point 2). A type that does not say allows none.
- **Which documents may.** A document may keep a sidecar only where its type allows one, so a document with no type may not. In a tie, every type in contention must allow one (COR-056 point 3).
- **The type is read from the data in either home.** A kind field in a sidecar types its document as one in front matter does (COR-056 point 4). Reading never depends on the permission, so the type comes first and the permission after.
- **A project's own type allows none.** It has no registry entry, since a project declares it on the place that gives it (COR-056 point 2). A project's document may keep a sidecar where its place gives it a component's type that allows one.
- **Writers.** The permission decides only where data goes that enters a sidecar:
  - **An edit** of data a document has is written in the home it has, an unallowed sidecar included. So a writer, the after-merge status job (COR-050 point 10) among them, never fails on the permission alone.
  - **Into a sidecar** only for a document whose type allows one. That covers a command that makes a document, and one that moves a document's data into its sidecar.
  - **Back into front matter** for any document, so a sidecar no type allows can always be mended.

  Each owner decides in its own records whether its commands write sidecars. A command that moves data between homes leaves the body exactly as it was. Either home stays legal for a document whose type allows a sidecar.
- **Validation** fails each sidecar that no type allows. It reads every sidecar in the repository, beside a placed file or not. So it fails a sidecar beside a file with no type, and a sidecar whose document is missing, as after a rename that left it behind. It fails a sidecar beside a placed data file too, whatever its type allows (refinement per COR-071).

### 5. A decision record and a rule-set file keep their front matter

A decision record and a rule-set file never keep their data in a sidecar, whatever their type.
- **Validation** fails a sidecar beside either.
- **The backbone never reads their data from a sidecar.** A record's content is read from its file wherever it sits (COR-050, on a record's content). A rule set's data is read from its front matter (COR-051 point 2).

### 6. One home at each state

- **One home.** At each state, a document's data lives in its front matter or in its sidecar, never in both. Validation fails a document that has both, empty fences counted as front matter.
- **Where both exist.** A past state, or a branch, may hold both. The sidecar's data is then the document's data. The front matter, fences included, is neither data nor body, so none of its lines reads as text the document says.

### 7. The content is the same in either home

- **An artefact's content** is its body and its own fields, wherever they live, without the methodology's container in either home (COR-050, on an artefact's content).
- **A placed file's content,** for a path anchor or an anchor of a registered kind, is read the same way. That is its body and the fields of its data, in either home.
- **A sidecar that does not parse to a mapping** leaves its document's content as its file and its sidecar, each as stored. That is how COR-050 reads front matter that does not parse.
- **A move between homes changes nothing.** A change that moves a document's data from one home to the other, unchanged, changes no content. It flags no dependant and owes no answer. It moves no artefact either, so it asks no revalidation (COR-050 point 3).
- **An edit in a sidecar is an edit of its document.** A field changed only in the sidecar changes its document's content, and flags what rests on it.

### 8. No answers in a sidecar

A sidecar's friction block keeps what the block keeps in front matter: the anchors, the reason for having none and the tool-written status (COR-062 point 1). It holds no answer to friction, since answers live in answer files.
- **Validation** fails an answer in a sidecar, as it fails one left in front matter (COR-062 point 10).
- **Read as in front matter.** An answer left in a sidecar is read as one left in a block in front matter: only in history, for its points (COR-062 point 1).

### 9. A sidecar gone missing leaves a gap

A document whose data lived in its sidecar may lose it, as where a rename leaves the sidecar behind. A **gap** is each state where it then has no sidecar, and no front matter but empty fences. Over a gap, the document holds no artefact.
- **A gap, not an end.** Where the data comes back, it is the artefact it was, not a new one. That holds where the document's file stayed in a place throughout. A removal in between, its file deleted or moved out of every place, ends the artefact as COR-050 point 6 reads it.
- **The change that brings the data back** adds no artefact (COR-050 point 6). The change check judges the artefact against its revalidation points instead of the base, and its answers clear it as any artefact's do.
- **While in a gap,** anchors that name the document are dead (COR-050 point 7), and its answers are not live (COR-062 point 5). A prune may then remove them. Where none is left, the artefact is measured from where its block was first introduced (COR-050 point 3).
- **Links.** A source that enters a gap is one the change removes, so it triggers nothing (COR-050 point 16). A source back from a gap is compared with its data where the gap began, so data restored unchanged triggers nothing.
- **A collection file** in a gap puts each entry it held in a gap. An entry missing from the map of a file whose data is there is removed, as COR-050 point 6 reads a removal.
- **Front matter is read as COR-050 reads it.** A document whose front matter goes, with no sidecar before it, holds no artefact from then on, and data that comes back makes a new one (COR-050 point 6).

## Rationale

**Why a sidecar.** Front matter puts a document's data in front of the reader who came for its text. A file of its own beside the document keeps the data in the repository, versioned with the document, where every tool reads it. The document's file is left to its text.

**Why a path derived from the document's alone.** A reader at any state finds the data from the document, with no setting to read at that state. A rule the backbone fixes reads the same in every project, as the answer folder's fixed path does (COR-062 point 2). A changed rule would strand every sidecar written under the old one, so it never changes.

**Why the type's owner allows it.** The owner of a type ships the tools that read and write its documents, so it knows whether they read a sidecar. A sidecar beside a document whose owner's tools read only front matter would hide its data from them. A type is declared once and reaches every place that gives it, a project's places included. The permission is an attribute of a type, so it adds no concept to places (COR-056 point 7).

**Why a project keeps front matter where it needs it.** A project knows where its own site generator reads front matter, and the owner of a type does not. Either home stays legal, and a writer edits a document's data in the home it has. So a document the project keeps in front matter stays there until someone moves it.

**Why reading never depends on the permission.** The checks read past states, and a permission may change between them. Read only where a type allows it, a sidecar would vanish from history once its owner withdrew the permission, or once its component was uninstalled. The document would then read as having lost its data. Reading every sidecar alike also keeps friction from reading a type (COR-056 point 5), and lets a kind field in a sidecar type its document.

**Why the permission gates only data entering a sidecar.** A writer that refused to edit an unallowed sidecar would stop the after-merge job, and one that wrote front matter beside it would make two homes, where the sidecar wins and the edit is lost. Editing data where it is keeps every writer working, and validation names the sidecar until it moves back.

**Why validation fails a sidecar no type allows, wherever it sits.** A sidecar that no type allows holds data that no writer of the type keeps. A sidecar left behind by a rename holds data that no document has. The project can mend both in its own files, and a writer can always move data back into front matter. Validation that looked only in places would miss a sidecar beside a file that a change took out of one.

The cost is a tree the project copies in whole, such as vendored code, that holds another project's sidecars. Validation fails them, and the project drops them from its copy.

**Why a project's own type allows none.** A project's type has no registry entry to say so, and a project declares it on its places alone (COR-056 point 2). A permission there would add a concept to places beside friction's own and types (COR-056 point 7). A project that wants sidecars gives its place a component's type that allows them.

**Why records and rule-set files keep their front matter.** A record is read by its content wherever it sits, in a place or not (COR-050, on a record's content). A record or a method rule set also arrives by sync in a tree that no place reads (COR-050 point 14). A sidecar is read as data only beside a document read as an artefact, so such a file would arrive without its data.
- **A record's data is short,** and is what its reader needs first: an id, a title and a status.
- **A rule-set file is found by its location,** so one rule serves every rule-set file, the project's own included. The cost is that a project's own rule set, whose data map is long, keeps it as a table above its rules.

**Why one home at each state.** Two homes at one state would need a rule for which field wins, field by field. A writer would not know which home to edit, and a reader would not know which to believe. One home gives one answer.

**Why the sidecar wins where both exist.** Validation fails both homes at every state it checks, so which wins matters only in history and on a branch before validation runs. What is left there beside a sidecar is most likely a copy a move forgot, or empty fences an editor kept. Reading the sidecar reads both without a false change.
- **Read as body,** those lines would change the document's text at every state that holds them.
- **The cost.** A field edited in front matter left beside a sidecar is unseen by friction until the state is mended. Such an edit comes from a merge resolved by hand, or from a tool that does not know sidecars.

**Why the content is the same in either home.** A move changes where the data is kept, not what the document says. Read by home, each move would flag every dependant, and a field edited in the sidecar would change nothing a path anchor stands on. Read the same in either home, a move owes nothing, and an edit owes what it always owed.

**Why a sidecar is part of its document for every judgement made by path.** A component that judges a change by its paths would otherwise judge a sidecar by its own path, as a data file of the project's code, say. A change that edits only a page's data would then require a review of code. A path anchor over a folder would also gain a file at each move, and be flagged by a change that changed nothing. As part of its document, a sidecar is judged as the document it belongs to.

**Why no answer in a sidecar, read as in front matter.** Answers live in answer files, so no change writes one into a document's data (COR-062 point 1). The friction block keeps the same keys in either home, so an answer left in it is found and read the same in either. Reading one in a sidecar differently would make the block's meaning turn on its home.

**Why a sidecar gone missing leaves a gap.** A rename that leaves the sidecar behind leaves the document with no data, until a later change restores it. Read as new there, the restored artefact would count as revalidated, and its debt would vanish without a word. Read as a gap, the change that restores it owes what changed since its last revalidation.
- **The guard in the same change** is validation, which fails the sidecar left with no document. The gap covers a history that keeps the commits between, where the head of each change was valid.
- **What it rests on.** The gap holds only where the history pairs the document's old path with its new one, as a rename. Where it does not, the new path is a file newly added, and its data is a new artefact, as for any unpaired move (COR-050 point 3).
- **After a prune,** the artefact is measured from where its block was first introduced. That errs toward more friction.
- **Empty fences** an editor leaves in place of the sidecar hold no data. Read as a home, they would make each entry of a collection file read as removed, and its debt would vanish where the data comes back.

A document whose sidecar is removed on purpose bears a cost. Anchors that name it are dead, and its answers are not live. Data brought back later is judged against what its answers left, so the change that brings it back answers what changed since. A document that should start afresh is removed first, its file deleted or moved out of every place.

**Why front matter keeps its reading.** COR-050 point 6 counts a document whose front matter comes back as a new artefact. A sidecar is a file of its own, so a change can lose it without touching the document. Front matter is lost only by an edit of the document that the change shows. Reading a gap for front matter too would change what COR-050 point 6 decides for every document that exists, which this record does not do.

**Why core.** Friction, validation and every component that reads a document's data or judges a change by its paths must agree on where the data lives. Components that must not depend on one another cannot each decide it. Nothing here names a discipline.

### Alternatives considered

- **A comment that hides the front matter from the reader.** Rejected. Only the hosts that honour the comment hide it, and it stays in the file for every other reader.
- **One tree holding every document's data.** Rejected. A folder of documents moved elsewhere would leave its data behind, and every change that writes data would write in the one tree.
- **One data file per folder, mapping the folder's documents.** Rejected. Two changes that edit the data of two documents in one folder would conflict, which COR-062 removed for answers.
- **Only the methodology's container in a sidecar.** Not taken. A document's own fields would still open it as a table, and its data would have two homes, by kind of data.
- **Every document whose type allows a sidecar moved into one.** Rejected. A project's site generator may read keys of its own in front matter, and a forced move would break its pages.
- **A permission on each place.** Rejected. A place would carry a concept beside friction's own and types (COR-056 point 7). A project's place that gives a component's type would also decide what only the type's owner knows.
- **A permission the project sets.** Not taken. The owner of a type knows whether its tools read a sidecar. A project keeps front matter where it needs it, since either home stays legal.
- **A sidecar read only where a type allows one.** Rejected. History would lose a document's data wherever its owner later withdrew the permission.
- **A writer that refuses an unallowed sidecar.** Rejected. The after-merge job would stop, and every edit of such a document would wait for its data to move back.
- **Front matter winning where both exist.** Not taken. What is left beside a sidecar is most likely a copy or empty fences, and the sidecar reads both without a false change.
- **Both homes read as stored where both exist.** Not taken. It errs toward more friction, but a state that held an identical copy would raise friction nobody caused.
- **Content read by home, each move answered by a revalidation.** Rejected. Each move would flag every dependant, and each answer could only say that the data moved.
- **A sidecar judged by its own path.** Rejected. A component would judge it as a file of another kind, such as a data file of the project's code, and a path anchor would gain a file at each move.
- **A sidecar gone missing read as a removal, its data back read as new.** Rejected. A forgotten sidecar restored later would erase the artefact's debt without a word.
- **A gap for front matter too.** Not taken. It would change what COR-050 point 6 decides for every existing document.
- **A sidecar beside a decision record or a rule-set file.** Rejected. A record and a method rule set are read where no sidecar is read as data.
- **A project's own type allowing a sidecar.** Not taken. It has no registry entry to carry the permission. Carrying it on the project's places would add a concept to places (COR-056 point 7), so a later record would move places into a functionality of their own first.
- **The schema-binding file the binding records rejected (COR-022, COR-023).** A file beside each data file was rejected there for the files it adds and for drifting from its data. A sidecar adds one file per document too, which is its purpose. It holds the data itself rather than a pointer to it, so nothing can drift from it, and validation fails one left without its document.

## Implications

- **The backbone ships** the reading of a sidecar wherever it reads an artefact's content, and the permission on a type in the type registry's schema. It also ships validation's findings:
  - a sidecar that no type allows, its document missing included
  - a document with data in both homes
  - an answer in a sidecar
  - a sidecar beside a decision record or a rule-set file
- **The backbone answers,** for any path, the document a sidecar there belongs to, or none. The rule reads the path alone, so the answer needs no state, and a component judging a change maps the paths of both its states with it. The backbone's machine-readable output also names each document's home, so a component need not derive either. The backbone documents the rule that places a sidecar.
- **The backbone ships a way to move data back** into front matter, so a project can mend a sidecar no type allows without the component that wrote it.
- **A component that reads data itself,** of a type that allows a sidecar or of another owner's type, reads it in either home. One that judges a change by its paths takes each sidecar's document from the backbone.
- **A component allows sidecars** for its types in its type registry, and decides in its own records whether its commands write them. One that allows them needs a backbone that reads them.
- **What leaves a sidecar unallowed.** A release that withdraws the permission, retypes a place, adds a kind field or adds a place that makes a tie may leave unallowed a sidecar its earlier release allowed. So may an uninstall, or a place the project retypes. Validation then fails each such sidecar until its data moves back.
  - **A component's release** that leaves unallowed a sidecar its earlier release allowed ships a migration that moves the data back (COR-010).
  - **An uninstall plan** reports the sidecars it would leave unallowed, beside the types it takes off the project's places (COR-056 point 2).
- **A file already where a sidecar would sit.** Validation would read it as a sidecar. So the release that fixes the rule ships a migration that finds such files in each project, and stops, naming each one. It moves and deletes none, since only a positive sign may move a file (COR-010). Past states are read through the fixed rule too, so such a file reads as a sidecar in history, a cost no migration mends.
- **Nothing else that exists changes.** Every document keeps its front matter until a command or a person moves it. The permission is an optional addition.
- **Records refined in place,** atomically with this record's acceptance:
  - COR-050 point 1: front matter, in that record, is a document's data in its file or in a sidecar
  - COR-050 point 5: a sidecar is part of its document, so a move between homes adds or removes no file
  - COR-050 point 6: a document whose sidecar went missing is not new where its data comes back
  - COR-051 point 2: a rule-set file keeps its front matter
  - COR-053 point 10: the methodology's container sits in either home
  - COR-056 point 2: a type registry entry may allow a sidecar
  - COR-056 point 4: a document may declare its kind in its sidecar
  - the decision-record spec: a record keeps its front matter
