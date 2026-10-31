---
id: COR-071
title: A YAML data file is an artefact where its place says it reads data
status: proposed
date: 2026-10-31
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a place may say that it reads *data files*, YAML files whose whole content is data. Each YAML file such a place matches is then an artefact, as a Markdown document with front matter is. Rule sets reach it, anchors name it, and it carries the methodology's container at the top of its data. An anchor names a part of it by the keys that lead to the part, where a document's parts are its headings.

A place that does not say so reads documents only. The methodology's own YAML files, such as its configuration, answer files and sidecars, never become artefacts. Any other YAML file stays data only until a place says it reads it. A project's place never turns a component's own files into artefacts. Nothing that exists changes until someone declares such a place.

## Context

An artefact is a Markdown document with front matter, or one keyed entry of a collection file (COR-050 point 1). The places declared to hold artefacts read Markdown files only. A YAML file in a place is left alone. No anchor can name a part of it, no rule set reaches it, and it carries no friction block.

That line was drawn when only documents needed rules and anchors. A component may keep its content as YAML data bound to a schema (COR-023), such as a talk's slides, one file per language. The rule-set reviewer reads the rules that bind on a file through the backbone's one answer (COR-051 point 7, COR-057). For a YAML file, that answer is empty.

Wrapping the data in a Markdown file, as front matter above an empty body, would make it an artefact. But the data would then take a document's shape only to be read as one. Every tool of the component would read a document where it means data.

A YAML file is no document. It can still be what an artefact is: something that holds against what makes it true, and that rules bind on.

Not every YAML file should become one. A project's places often hold configuration, a site generator's data or examples beside their documents. A component may keep YAML that a tool rewrites at every run beside the content its rules judge. The methodology also keeps its own settings and bookkeeping in YAML, at locations its records fix.

## Decision

**A place may say that it reads data files, and each YAML file it matches is then an artefact read from its data as front matter. An anchor names a part of one by its key path. The methodology's own YAML files never are such artefacts, and a project's place leaves a component's files to the component.**

Four terms recur:
- A **data place** is a place that says it reads data files (point 1).
- A **placed data file** is a YAML file that a data place reads (points 1 and 2). It is one of the data files a schema may bind (COR-023), read by a place. Which file names are YAML is fixed by the backbone, the same in every project.
- Its **data** is the one YAML document the file holds, read as front matter is. Its top is a mapping.
- A **key path** names a value inside the data. It joins with `/` the keys from the data's top down to the value. It names an item of a list by its `id` (point 5).

The records on anchors, connection points and types speak of an artefact's front matter (COR-050, COR-053 point 10, COR-056). There they mean a placed data file's data too.

Where the record on anchors speaks of a section as a part, it means a value of a placed data file too. That value stands on what point 5 says. A placed data file has no body and no lead. So its content is its own fields, and an entry's content is that entry's own fields.

### 1. A place may say that it reads data files

- **Declared on the place.** Whoever declares a place may say, on it, that it reads data files. That is a component in its package metadata, or the project in the backbone configuration (COR-050 points 1 and 14). A place that does not say reads documents only.
- **What it reads.** A data place reads each YAML file it matches as a placed data file. It still reads the Markdown documents it matches, as any place does.
- **Which files.** The data place's path chooses the files. A YAML file that should stay data only, such as one a tool rewrites at every run, is left out by a narrower path. An example is a glob that names the data files alone.
- **A component's files stay its own.** A component's own place that is not root-wide may match a YAML file (COR-056 point 3, on root-wide places). No project place then reads that file as data, and a project data place that yields so is reported, without failing.
  - **Matching.** A place matches a file when its path matches the file's, whatever the place reads.
  - **How a component keeps files out.** It covers them with a place over their folder, or with a held folder where none of them is an artefact (point 2). It reads as data only those its own data places match.
- **One component over another.** A data place of one component may read a YAML file that another component's own place matches. That is reported, and the file stays a placed data file, since the project cannot mend either declaration (COR-055 point 1).
- **Only data places type it.** A placed data file takes its type only from the data places that read it, by the order of COR-056 point 3. A place that reads documents only gives it no type.
- **Read at each state.** Each state's places say which files are placed data files there, as they say which hold documents (COR-050 point 1). Declaring a data place adds the artefacts it reads. Withdrawing the declaration removes them (COR-050 point 6).
- **Friction reads it, and no type does.** Which files hold artefacts is friction's own question about a place (COR-050 point 1). So the declaration is friction's, and places keep two concepts, friction's and types'. A third would move places into a functionality of their own (COR-056 point 7). A type decides nothing here (COR-056 point 5).

### 2. The methodology's own YAML files are never placed data files

A YAML file the backbone finds by a location rule of its own is never a placed data file. A core record fixes each such rule, and the file's shape, for settings or bookkeeping. The backbone knows each rule, so it leaves those files out wherever a data place matches them, without a finding. Such files are, for instance:
- settings: the backbone configuration (COR-048), the overlay (COR-013) and a component's package metadata (COR-017)
- an answer file, whose folder is never a place (COR-062 point 2)
- a sidecar, which no place reads as a document (COR-063 point 2)
- a slot's project file, which may lie where a project's place reaches (COR-052 point 2)

The rest is left to the places:
- **A component's fixed files.** A YAML file that a component reads at a location it fixes itself stays out through the component's own places (point 1). Its own configuration is one.
- **Bound files.** A file a binding finds by a glob (COR-023) is not left out by this point, since the glob binds it and places nothing. A data place may read it.
- **Rule sets.** A rule-set file is a Markdown file (COR-051 point 2), so no placed data file is one.
- **Held and synced files.** A held folder holds the YAML files beneath it as it holds documents, so no data place reads one (COR-050 point 1). Synced copies stay outside every place (COR-050 point 14).

### 3. The container sits at the top of the data, and a collection maps entries by id

- **The container.** A placed data file's data may hold the methodology's container at its top, under the key front matter uses (COR-053 point 10). Everything outside it is the artefact's own. Its blocks, the friction block among them, keep the shape they have in front matter.
- **A collection file.** It is read as front matter is (COR-050 point 1). A placed data file is a collection file when its top holds no container and a mapping at its top holds one. Each mapping at its top is then an entry, keyed by its id, with a container of its own. An entry's content is its entry without that container.
- **Data that is no mapping.** A placed data file whose data is no mapping holds no artefact at that state. Nor does a document whose front matter is no mapping. Examples are an empty file, a list at the top, several YAML documents in one file, and YAML that does not parse. Validation fails such a file. For a path anchor, its content is its whole file as stored (COR-050, on a file's content).
- **Named as a document is.** An answer names a placed data file by its path, and an entry of one by the path, `#` and its id (COR-062 point 1). An artefact anchor names one, and an entry of one, as it names a document and a Markdown entry (COR-050 point 2).

### 4. Its content is its data, without the container

- **Compared parsed.** A placed data file's content is its own fields, compared parsed, as a document's front-matter fields are (COR-050, on an artefact's content). It has no body to compare as text.
- **What is no content.** Comments, the order of a mapping's keys, quoting and layout are no content. Nor is any container, whichever of its blocks changes.
- **No derived links set aside.** A derived link is set aside only in a body (COR-050 point 5). So a link that a command writes into a value is content, like any other text there.
- **A binding's fields are content.** The field that binds the file to its schema, and the schema version it carries (COR-023), are own fields. Changing them changes content, as a migration of the data does.
- **Under a path anchor.** A path anchor, or an anchor of a registered kind, may stand on a placed data file. Where a data place reads the file at either state compared, it is read the same way. Every container in it is left out (COR-050, on a file's content).

### 5. An anchor names a part of a placed data file by its key path

A placed data file's values are its parts, as a document's sections are its parts (COR-050 point 2). A part is named as the artefact is, then `#` and its key path, as in `talks/intro.yaml#slides/fits`.
- **The key path.** In a mapping, a key names its value. In a list, an item is named by its `id`, a text field of the item. The path is read in the data without the container.
- **What has no name.** A key or an `id` that is no text, that is empty, or that holds `/` or `#` names no value. An item of a list has a name only where it is a mapping with an `id` that names. Like a heading with an empty slug, such a value is named only within a larger part (COR-050 point 2).
- **What it stands on.** The part's value, compared parsed, and the fields that bind the file to its schema (COR-023). A change elsewhere in the data changes nothing it stands on. Neither does moving an item within its list, keeping its `id`, or reordering a mapping's keys.
- **Dead and ambiguous.** An anchor on a part is dead where no value has its key path, as after a key is renamed. It is ambiguous where a list on its path holds two items with one `id`. Both are errors wherever COR-050 point 7 reports them.
- **Whose they are.** A pull request makes such an anchor dead by renaming or removing a key or an `id` on its path. It makes one ambiguous by adding an item with the `id`. Each is the pull request's, as a renamed heading or a shared slug is (COR-050 point 12).
- **Refused, each with its reason:**
  - a bare `#` after a placed data file, which has no lead. The refusal names the whole anchor to use.
  - a key path after a collection file, whose entries are artefacts. The refusal names the entry whose id the path opens with, where there is one.
  - a key path after an entry of a collection file, which is cited whole, by its id
- **Cycles and order.** A part anchor counts as one on its whole artefact, for cycles and for the order of reporting (COR-050 points 5 and 11). So an anchor on a part of its own artefact is a cycle.

### 6. The backbone checks the container, and the file's binding checks the rest

- **The containers.** Validation checks a placed data file's container, or each entry's, against the backbone's schema. It checks them as it checks one in front matter (COR-050 point 2, COR-053 point 10).
- **The own fields.** Validation checks them against the schema the file's binding names (COR-023), read without any container. So the container never fails the data against that schema, whatever the schema admits.
- **No binding is asked.** This record asks no binding of a placed data file. One whose binding fails, or that has none, is still an artefact, read from its data.
- **Friction reads no schema.** A placed data file's content, anchors and answers are the same whatever its binding says, as they are whatever its type is (COR-056 point 5).
  - **The binding's field names.** Friction knows only the names of the fields a binding writes in the file (COR-023), so that a part stands on them (point 5).
  - **A file a glob binds** names no schema in its data. A part there stands on its schema version alone, and a glob that binds it to another schema changes nothing a part stands on.

### 7. A placed data file keeps no sidecar

A placed data file is its data, so it never keeps it in a sidecar (COR-063).
- **Validation** fails a sidecar beside a placed data file, whatever its type allows.
- **The backbone never reads one** as a placed data file's data.

### 8. A rule reads a placed data file's text values

A rule set reaches a placed data file as it reaches any artefact, through its scope's paths and types (COR-051 point 2). The backbone's one answer of which rules bind holds placed data files too (COR-051 point 7).
- **Its words.** Where a rule, a check or a reviewer reads an artefact's words, a placed data file's words are its text values outside any container. Keys and comments hold no words. Nor do values that YAML reads as numbers, booleans or dates.
- **Prose and other text.** Some text values hold no prose, such as an id, a path or a name from a fixed list. They give a rule on prose nothing to judge, and a reviewer tells them apart by reading them. A check that cannot tell them apart reads only the fields that its declaration, under the rule set's checks, names (COR-051 point 2).
- **One passage each.** Each text value is a passage of its own, read as the rule reads a block of a document's text, any markup in it included. A finding names the value's line, and its key path where the value has a name.
- **No body.** A placed data file has no headings and no sections. A rule that judges a body judges nothing there.

### 9. A writer keeps what is not its own

- **The backbone's writers** write a placed data file's container and leave the rest of the file as it was, its comments and layout included. One is the after-merge status job (COR-050 point 10). A container a writer adds goes after the own fields it sits beside.
- **A component's writers** that rewrite a placed data file keep its container, and every other key they do not own.

## Rationale

**Why a data file can be an artefact.** An artefact is what holds against what makes it true, and what rules bind on. A YAML file of content is that, as a document is. A document's front matter is data already, so a data file reads as front matter with no body. The checks then read it with the rules they already apply.

**Why the place says so.** The places already say which files hold artefacts (COR-050 point 1). Saying that a place reads data files is the same statement, for a second form of file. Friction reads it at each state, as it reads the places.

**Why the type's owner does not decide it.** COR-063 lets a type's owner allow a sidecar, since its tools must read one. Here the question is whether a file is an artefact at all. A type changes neither what counts as an artefact nor its content, and friction reads no type (COR-056 point 5). Were a type to decide it, retyping a place would add or remove artefacts, and friction would read types at every state.

**Why a project's data place yields to a component's place.** A component's tools write its files, and the component knows which keep a container and which a tool rewrites at every run. A project place that read them as data would hand the component artefacts it never meant. Its tools would drop their containers, and rules would reach files nobody wrote for them. Yielding reads only places, as COR-056 point 3 does for types, so friction stays free of types.
- **What it costs a component.** One that leaves a file out covers its folder with a place, which it needs anyway to keep project types off its files.
- **Why the yield is reported.** Installing or upgrading a component can turn a project's placed data files back into plain data, and anchors on their parts die. A dead anchor is an error, never silence (COR-050 point 7), so the yield that caused it is said too.

**Why only data places give a placed data file its type.** A place that reads documents only was declared for documents. Typing a placed data file from it would bring rules written for those documents to data its owner never typed.

**Why declared, never taken from the file's name.** Read in every place, YAML would turn configuration, a site generator's data and examples into artefacts. Each would count as unanchored, and a rule set whose scope names a folder would reach it, without a word. Declared, nothing that exists changes, and an owner opts in where it means to.

**Why the methodology's own files are never placed data files.** Each is read for a shape of its own, at a location a core record fixes.
- **Answer files.** One read as an artefact would answer to friction itself, the loop that COR-062 point 2 closes.
- **Sidecars.** A sidecar is part of its document (COR-063 point 2).
- **Settings.** The settings files are read as settings, and a path anchor already names one.

The backbone knows its own location rules, so the line is one it can draw. Leaving those files out without a finding lets a broad data place pass them quietly.

**Why YAML, with the container at the top.** Front matter is YAML, and so are the container, the configuration and every binding (COR-023, COR-048). A placed data file then reads with the same parser. Its container has the key and the shape it has in front matter, so one schema checks both, and the backbone's writers write both.

**Why a collection is read as front matter's is.** One reading serves both forms, so a reader who knows a collection file in Markdown knows one in YAML. The cost: data often holds mappings at its top. A key named as the container, inside one of them, would make the file read as a collection. So a data format leaves that key free at its top and at the top of each mapping its top holds.

**Why the content is the data, compared parsed.** A placed data file has no body. What its readers and its tools read is its data, so its data is what holds against its anchors. Front matter's fields are compared parsed (COR-050), and the data is front matter without a body.
- **Comments.** A comment is no content. A note a person keeps in a comment escapes friction and the rules, so a component that wants notes judged keeps them in a field.
- **Values YAML types.** A value YAML reads as a number, a boolean or a date compares as that value. So a change between two spellings of one value is no change. Where a field holds words, its binding's schema asks for text, and validation fails such a value.

**Why a key path names a part.** A document's sections are named by its headings, which its writer chose. A data file's values are mostly named by keys its schema chose. So a key path names a part as stably as a heading names a section. A list's positions move at each insertion, so an item is named by its `id`.
- **Why `/`.** It is JSON Pointer's separator, which readers of a schema know. This form keeps the separator, and names an item by its `id` where JSON Pointer names it by its position.

**Why a part stands on its value and the binding's fields.** A document's section stands on the document's own fields too, since they say whether and how its text holds, as a status does. A data file's fields are its content. A part standing on them all would stand on the whole, and naming a part would gain nothing.
- **The binding's fields.** They are the one kind of field every data file shares. A new schema version may change what a value means while its text stays, so a part stands on them.
- **The cost.** A part does not stand on a field that says whether the whole holds, such as a data format's own status. An anchor that rests on it names it as a part too, or names the whole file.

**Why the binding checks the data without the container.** The container belongs to the methodology in every artefact, so one schema checks it everywhere. A component's schema then needs no knowledge of it to judge its own fields. A schema that admits no unknown key would otherwise fail every placed data file that carries anchors.

**Why the container stays in the file.** The container is bookkeeping, as COR-063 says of a document's data. Kept in the file, it asks a component's writers to keep it (point 9), and its schemas to admit its key. A sidecar would spare both, but it would give the container two homes, a permission and the rename hazard of COR-063 point 9. No component needs one yet.

**Why its text values are its words.** Rules judge what an author wrote, and in a data file that is mostly its text values. Keys are mostly the schema's names, the same in every file it binds. A rule on words that read them would judge the schema.
- **The cost.** Some keys are content, such as a term keyed by its own words, or a table keyed by language. A rule on words does not read them. A format that wants such words judged keeps them in values.

**Why core.** Friction, validation, rule sets and every component that judges a change by its paths must agree on which files are artefacts. Components that must not depend on one another cannot each decide it. Nothing here names a discipline.

### Alternatives considered

- **A Markdown wrapper,** the data as front matter above an empty body. Rejected. The data would take a document's shape only to be read as one. The component's tools would read and write a document where they mean data.
- **Every YAML file in a place.** Rejected. Configuration and other data in places that exist would become artefacts, counted and ruled, without a word.
- **The type's owner allowing data files,** as it allows a sidecar (COR-063). Rejected. A type would decide what counts as an artefact, and friction would read types (COR-056 point 5).
- **The binding's schema declaring its files artefacts.** Rejected. Friction would read schemas, and an edit in a schema's tree would make a file an artefact or stop it being one.
- **A place's path that names YAML files, taken as the declaration.** Rejected. It infers from how a glob is spelt, so an edit of the path would change what the place reads, unseen.
- **Any place reading any file as data, a component's included.** Rejected. A project's broad data place would turn a component's rewritten files into artefacts, with containers its tools drop.
- **The container in a sidecar beside the placed data file.** Not taken now. It would spare writers and editors the container. It would cost a second home for it, a permission and the rename hazard (COR-063 point 9). A component whose tools cannot keep the container would be the case for it.
- **A collection declared on the place.** Not taken. One reading of a collection serves front matter and data alike, and a declaration would make a second.
- **Data that is no mapping read as a gap,** as a missing sidecar is (COR-063 point 9). Not taken. A document whose front matter is no mapping holds no artefact either, and COR-063 kept that reading.
  - **The cost.** In a history that keeps the commits between, a commit that broke the data ends the artefact, and the fix starts a new one.
  - **What limits it.** Validation fails the broken file, so a change that gates on validation cannot land one.
- **Parts named by their position,** as a JSON Pointer names a list's items. Rejected. Inserting an item renames every item after it, and the anchors on them point elsewhere without a word.
- **Keys joined by `.`.** Not taken. A dot can sit in a key as a slash can, such as in a version or a file name. The slash is the separator that readers of a schema know.
- **A part standing on its value alone.** Not taken. A new schema version that changes a value's meaning would flag nothing anchored to it.
- **Comments as content.** Not taken. Front matter's comments are no content either, and no tool that reads the data reads them.
- **Other formats, such as JSON or TOML, now.** Not taken now. No component needs one, and each would need a container form of its own.

## Implications

- **The backbone ships** the declaration on a place, in the package-metadata schema and the configuration schema. It ships the reading of a placed data file wherever it reads an artefact or a placed file, at every state.
  - **Validation's findings:** a placed data file whose data is no mapping, and a sidecar beside one. Also a part anchor on one that is dead, ambiguous or refused.
  - **Reports that do not fail:** a project data place that yields to a component's place, and one component's data place over another's own place.
- **The backbone checks a placed data file twice:** its containers against the backbone's schema, and its own fields against its binding, without the containers. The binding's validator and friction read the same file names as YAML.
- **The backbone's machine-readable output** says, for each artefact, whether its file is a document or a placed data file. A component that lists artefacts tells the two apart there, rather than taking every artefact for a document.
- **The backbone's writers** write a placed data file's container in place, and keep the rest of the file as it was.
- **The rule-set reviewer's instructions** read a placed data file's text values as its passages (point 8).
- **The references** for package metadata, the backbone configuration, the schemas and anchors document the declaration and the key path. They list the backbone's own location rules, whose files point 2 leaves out.
- **A component that keeps content as YAML** may declare data places, and needs a backbone that reads the declaration. It covers, with a place or a held folder of its own, the folders whose other YAML files must stay data only.
  - **Its data format** leaves the methodology's key free at its top, and at the top of each mapping its top holds. It names by an `id` text field each list item that an anchor should reach.
  - **Its schemas,** where an editor applies them to the whole file, admit that key, so an anchored file reads as valid there.
  - **Its commands** that rewrite a placed data file keep the container.
- **A component's release** that adds or withdraws a data place, or changes the path of one, changes which artefacts exist. That is a surface change of the component (COR-010).
  - **Withdrawing one** makes the anchors on its files dead.
  - **Adding one** brings its files under every rule set whose scope reaches them, the project's own included. The change that upgrades the component then owns their text for those rules (COR-057 point 2).
- **A project** may say that its own places read data files, and needs a backbone that reads the declaration.
- **Nothing changes until a place says it reads data files,** so no migration is due (COR-010). Declaring a data place changes how its files compare for a path anchor, another owner's included. From then on, an edit of only a comment, or only a container, is no change to them.
- **Records refined in place,** atomically with this record's acceptance:
  - COR-050 point 1: a place may read data files, each read as front matter with no body
  - COR-050 point 2: a value of a placed data file is a part, named by its key path. The record's sections read as such values too.
  - COR-050 point 5: an anchor on a value of a placed data file stands on that value and the binding's fields
  - COR-050 point 7: when an anchor on a value of a placed data file is dead or ambiguous
  - COR-050 point 14: a project's place may say that it reads data files
  - COR-053 point 10: the container sits at the top of a placed data file's data
  - COR-056 point 3: only data places type a placed data file
  - COR-056 point 4: a placed data file declares its kind at the top of its data
  - COR-062 point 1: an answer names a placed data file by its path
  - COR-063 point 2: no place reads a sidecar as a placed data file
  - COR-063 points 3 and 4: a sidecar beside a placed data file is never read, and validation fails it
  - COR-023: validation of a placed data file's binding reads it without its containers
