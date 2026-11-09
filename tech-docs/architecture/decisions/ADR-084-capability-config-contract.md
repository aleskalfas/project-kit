---
id: ADR-084
title: The backbone may record a key in any capability's own configuration, guarded by its schema
status: proposed
date: 2026-11-09
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** each capability keeps its settings in a file of its own, the *capability's own configuration*. The file is the project's, and a schema the capability ships checks it. This record lets one backbone command add a key to that file, for any installed capability. It adds one text value where the key is absent, and keeps every other byte as written. It never moves a value the file holds, and writes nothing the capability's schema refuses. It asks consent as the backbone's own configuration does. A capability project-kit ships that records a text value once does it through this command, and only in its own file. For a capability authored elsewhere that rule is provisional, raised for a core record.

Some of this stays open, and the record says so. Anyone who may run the command can add any key a capability's schema accepts as text. Some such text is a program or a command the capability runs. This record takes that to be no more than a hand edit of the same file. No capability can yet keep a key from the command. The record is revisited when a key that only some writers may write comes within its reach.

**Why an ADR, and what is provisional.** The core layer writes a project-owned file only through a writer a record names ([COR-001](../../../.pkit/decisions/core/COR-001-content-mechanisms.md), "Extension"). This record names one. COR-025's first test asks whether another adopter, authoring a similar artefact, would need the rule ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)). The writer, its guards, its reach and its refusals fail that test: they are how project-kit's backbone is built. Two rules pass it, since every capability's author needs them. The file's place and schema name are a contract the backbone writes into, and a capability records through the backbone, not through a writer of its own. Those belong in a core record. This record adopts them provisionally for the capabilities project-kit ships, and raises them for a core decision (point 8). It takes that form from ADR-061, though not its reason: no core record decides these rules either way.

## Context

**What the core decides.**
- **A capability's settings stay in its own subtree,** never in the backbone's configuration ([COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 2).
- **A capability's machine-read data is a schema pair it ships** ([COR-018](../../../.pkit/decisions/core/COR-018-capability-schemas.md)). A data file names its schema in a binding field, with the schema version it was written against ([COR-023](../../../.pkit/decisions/core/COR-023-schema-binds-inline.md)).
- **A documentation location derived from a root is recorded on first use,** in the overlay or in the component's own configuration, and read from then on. An explicit location always wins over a derived one ([COR-049](../../../.pkit/decisions/core/COR-049-documentation-roots.md) points 3 and 5).
- **A project-owned file** is written by the core layer only through a writer a record names, with the consent that record sets. The project may edit it freely (COR-001, "Extension").

**What the backbone has.**
- **The backbone's own configuration** is written by commands that set a key a core record owns (COR-048 point 2). Its *setter*, the command that sets one key, writes through the backbone's text edit of a YAML mapping. That edit keeps every byte it does not change.
- **The location recorder** records a capability's documentation location derived from a root. It writes a file of its own beside the capability's configuration, in a shape the backbone defines. So a *strict* capability schema, one that refuses keys it does not declare, never meets a key it did not declare.
- **Capabilities write their own configuration** in several ways, each through a writer of its own. Some add a value their command chose, once, each with a copy of the text edit and guards of its own.

**What prompted this.** Pull request #2601 (issue #2511) adds a backbone command that records one key in a capability's own configuration, for every capability. The architect's review raised one point for a person to authorise. The backbone becomes a writer of keys another component owns, guarded by that component's schema. The maintainer authorised it on 9 November 2026, and asked for this record.

**What an audit of the keys in reach found.** On the same day, each `config` schema of the capabilities project-kit ships was read for the keys at which it accepts text. Those are doc-examples, living-docs, project-management, software-analysis and visual-communication. Each such key was read against the records that own it.
- **Most set no limit.** The records of most such keys say nothing of who writes them.
- **One limits the channel.** visual-communication starts the browser its configuration names. Its record reads: "A project may name another in its configuration … A caller may not: a command starts what it is told with no prompt, so the choice lies in a file the project reviews, never in a flag" ([visual-communication:DEC-020-html-page-drawing] point 7). Point 9 reads "a caller" as the caller of the command that starts the browser.
- **One asks a review.** doc-examples runs the commands its configuration gives a project's placeholders. A change that adds or alters such a command needs the review a change to a test gets ([doc-examples:DEC-001-console-examples-as-tests] point 8). Its configuration also sets variables every command of its run is given.
- **One key is retired.** project-management's schema still accepts its old setting for the default branch. No component keeps a setting of its own for that branch ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md) point 1).
- **One limits who writes, out of reach.** project-management's grant list of fixers is written only on a person's own answer ([project-management:DEC-056-drift-fixers] point 2). Its entries are mappings that hold lists, which the command does not write.

## Decision

**One backbone command may add a text key, once, to any installed capability's own configuration, guarded by that capability's schema.**

### 1. A capability's own configuration is the project's file, in the capability's shape

A *capability's own configuration* is the file `project/config.yaml` in the capability's folder, bound to the capability's schema named `config` (COR-023). That place and that name are the contract: the backbone finds every capability's configuration there.
- **The file is the project's,** on the project's side of the no-shared-files invariant (COR-001). The project may add, edit or remove what it holds.
- **Its shape is the capability's.** The capability ships the schema pair that judges the file (COR-018), and its records give each key its meaning.
- **The backbone adds keys to it only as this record allows.** Other changes to the file are other records' to allow, such as a capability's migrations ([COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md) point 3).
- **A capability that ships no `config` schema** has no configuration the backbone writes.

### 2. One backbone recorder adds a key, for any capability

The *configuration recorder* is the backbone command that records a key in a capability's own configuration. It is the writer this record names for that file (COR-001, "Extension"). The role is `pkit config record`'s. The change that adds the command, #2601, gives its forms in [the CLI reference](../../../.pkit/cli/README.md). The passages of that reference this record names are that change's.
- **Its scope.** It writes for any installed capability that ships a `config` schema, whoever authored the capability. It writes neither the backbone's own configuration nor an adapter's files, since an adapter has no configuration bound to a schema of its own.
- **Reached by running it.** A capability's script runs the recorder and decides on its machine-readable output, which carries a schema version. That is how a script reaches the backbone's command that lands a pull request, which writes too ([ADR-061](ADR-061-hosting-service-acts-in-the-backbone.md) points 1 and 7). No query calls the recorder, since it writes ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 3).
- **Told apart by whose key it writes.** A writer of the backbone's configuration sets a key a core record owns (COR-048 point 2). The location recorder records a location derived from a root, in a file the backbone shapes (COR-049 point 5). The configuration recorder adds a value a capability's command chose, at a key the capability's schema accepts.

### 3. A capability records a text value once through the recorder, in its own configuration only

This point binds the capabilities project-kit ships, and is provisional for others (point 8).
- **Through the recorder.** A capability's command that records a text value once, in the capability's own configuration, does it through the recorder. It keeps no writer of its own for that, so one computation keeps one home (ADR-057 point 2).
- **In its own configuration only.** A capability records only in its own configuration, never in another capability's, since each keeps its settings in its own subtree (COR-048 point 2). The recorder cannot tell who runs it, so this binds the caller.
- **Other writes stay the capability's.** A value of another type, a change to a held value, a removal, or a value read from a service and stored again on each run is no recording. A capability makes those through the writers its own records name.
- **The put-back.** Before its recording step, a capability's command keeps the file as it found it. Where the step gives no answer, or a later step of its run fails, the command puts the file back as it found it. That is part of the recording, not a second writer of the key.

### 4. One text value, added once, every other byte kept

- **Text only.** The recorder writes a non-empty text value, so that every YAML reader reads it back as written. A value of another type stays with the capability's own writer.
- **Added once, never moved.** A key the file holds with the same value writes nothing. A key it holds with another value, an empty one included, is refused, and a person moves it. COR-049 has an explicit location win, recorded once and read from then on (points 3 and 5). This record extends that rule to any other value a capability's command chooses.
- **Every other byte kept.** The key's line goes in through the backbone's one text edit of a YAML mapping, the edit the setter writes through. Every other byte stays as the recorder read it. An edit made while it asks for consent is lost, as with the setter.
- **Bound where nothing is yet.** An absent file is created bound to the schema, and a file that holds nothing yet gains the binding before the key (COR-023).

### 5. The capability's schema guards each write

- **Nothing written on a doubt.** The result must read back as the file plus that key, or nothing is written.
- **No new error.** The result is validated against the capability's `config` schema. A result with an error the file did not have is refused. An error the file already had is left to its owner.
- **How errors are told apart.** Each key a schema does not declare is an error of its own, at its own place, from the backbone's one renderer of unknown keys ([ADR-056](ADR-056-backbone-file-schemas-home.md) point 4). So a strict schema refuses each such key. Other errors are told apart by their place and the schema rule they break. So a second break of a rule the file already breaks at the same place passes unseen, such as a second name that a mapping's name pattern refuses.
- **As strong as the schema.** A mapping the schema leaves open admits keys it does not name, and a key the schema still accepts is recorded. Closing either is the capability's choice.
- **Not the capability's whole judgement.** A capability's validator may judge what its schema does not, such as the form of a name. A recording the schema accepts can fail that validator, which validation reports, as for a hand edit.
- **A file its schema cannot judge is refused:** one that names another schema, or another version of it (COR-023). The CLI reference names the other files refused.

### 6. Consent in the backbone configuration's forms

- **The forms.** This record gives the recorder the consent forms of the backbone's own configuration ([COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 5). It asks once at a terminal. Off one, it writes only with its confirmation flag. With nobody to ask and no flag, it writes nothing.
- **Why more than the least.** Running a command is the consent only for a location already in use, and a component may ask more (COR-049 point 5). A typed value need not be in use anywhere yet.
- **A capability's command passes the flag** only where its own records make running that command the consent. Whether they do is the capability's question, not the backbone's.

### 7. What it never writes

- **A binding key.** The recorder never records a binding key, nor changes the binding of a file that holds keys. The binding is what lets the schema judge the file (COR-023).
- **Another file.** It writes only the named capability's own configuration. It never writes the backbone's configuration, a capability's recorded documentation locations, or an adapter's files.
- **Through a link.** It never writes a file it reaches through a link, since a whole-file write would replace the link.

### 8. The rule for capabilities is provisional, and raised for a core record

- **What is universal here.** Two rules bind every capability's author, wherever the capability is authored. Its own configuration's place and schema name are a contract the backbone writes into (point 1). And it records a text value once through the recorder, passing the flag only where its own records make running its command the consent (points 3 and 6). By COR-025's first test, a core record decides such rules.
- **Adopted provisionally.** This record adopts the two rules for the capabilities project-kit ships, and raises them for a core decision, as ADR-061 point 3 did with its placement.
- **The carrier until then.** This record never reaches a project that installs the methodology (COR-025, "Propagation isolation"). The CLI reference does, so it states the contract to capabilities authored elsewhere.
- **When to revisit:** when that core decision is made.

### 9. The limit, and when to revisit

- **Its reach.** With its flag, whoever may run the recorder can add any key at which an installed capability's schema accepts text. Some such text is a program or a command the capability starts.
- **No more than a hand edit, as an assumption.** This record assumes the recorder makes no write that a hand edit of the same file could not. That holds where whoever may run it may also edit the file. A permission model may let an agent run the backbone's commands yet deny it edits of that file. There the recorder gives the agent a write it lacked. A capability's script also runs the recorder below such a model's hook, where the model checks nothing.
- **How the keys in reach stand.** The audit found three kinds of limit besides silence (Context). Each holds against a recording as it holds against a hand edit:
  - **A limit on the channel holds.** This record reads "a caller may not" as the caller of the command that starts the browser, passing a flag to that run ([visual-communication:DEC-020-html-page-drawing] point 7). A recording is an edit of the file instead, open to the project's review like any other edit, and it shows in the diff. So the choice still lies in that file.
  - **What that reading concedes.** Off a terminal, with the flag, a caller's argument to the recorder chooses the program the next run starts, before any review. A hand edit does the same. If "a caller may not" means any caller's argument, the recorder's value is that channel, and the trigger below is met.
  - **A limit on review holds.** A recording is a change to the file, and that change's diff carries it to the review its record asks ([doc-examples:DEC-001-console-examples-as-tests] point 8).
  - **A retired key is the schema's to refuse.** No component keeps a setting of its own for the default branch (COR-054 point 1). So recording the retired key puts back a setting the core retired, as a hand edit would. The guard is as strong as the schema (point 5), so the remedy is a schema that no longer accepts the key. Until then the key is in reach.
  - **Silence sets no limit.** A record that says nothing of who writes its key leaves the recorder free to write it. A record that means to limit its writer says so, and that is the trigger below.
- **Records keep their force.** The recorder gives no one a right to write a key. Recording a key whose own record names other writers breaches that record, as a hand edit would.
- **When to revisit.** Revisit this record when a key whose own record limits who may write it in the file comes within the recorder's reach. The grant list of [project-management:DEC-056-drift-fixers] point 2 is of that kind, written only on a person's own answer. Such a key comes within reach when its schema starts accepting text there, or when the recorder writes values other than text. The change that brings it within reach also brings a way for a capability to keep a key from the recorder.
- **This narrows the authorised wording.** The maintainer authorised "the first key whose record limits its writer" as the trigger. Read literally, project-management's grant list already meets it, though it is out of reach because its entries are not text. So this record words the trigger by reach, and whoever accepts the record accepts that narrowing.
- **Where it shows.** The recorder does not detect the trigger. It shows in a change that alters a capability's `config` schema, or that writes a record limiting who writes one of its keys. For a capability authored elsewhere, nothing in this project sees it.

## Rationale

**Why one backbone recorder.** Capabilities that record a chosen value once each keep a copy of the text edit, with guards of their own. Copies of one computation drift, and the backbone keeps one home for each (ADR-057 point 2). A capability's script never imports the backbone, so it reaches that home by running a command (ADR-057 point 1). Every capability then gets the same guards.

**Why the capability's schema is the guard.** The schema already says what the file may hold (COR-018). A list of the backbone's own would state that shape a second time, and drift from it. With the schema as the guard, the backbone knows nothing of any capability's keys, so it serves one it has never seen. What the schema leaves to the capability's validator stays there, where validation runs it.

**Why text only.** A text value reads back as written under every YAML reader. Each value a capability's command records once today is a name or a path. A number, a yes-or-no or a list would each need a rule of its own, and a list can hold a key of the grant list's kind (Context). So other values stay with the capability's own writer.

**Why added once, never moved.** Others come to rely on a value a command chose, as on a recorded location (COR-049 point 5). So it stays until a person moves it, by a change a review sees. A recorder that replaced values would be a second setter, aimed at files whose keys the backbone does not own.

**Why the stricter consent.** A value the caller types may be in use nowhere yet, so recording it can change what the capability does next. COR-048 point 5's forms put that choice to a person, or into a flag a review can see.

**Why authorise it before a capability can keep keys out.** On the assumption of point 9, the recorder reaches nothing a hand edit does not. On point 9's reading of the browser's record, no key in its reach has a record that limits who may write it in the file. The limits the audit found hold against a recording as against a hand edit. A way to keep keys out, built now, would set a form for a case nobody has met ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)). It would also bind every capability's package metadata, ahead of the core decision point 8 raises.

**Why the trigger is worded by reach.** The recorder exposes no key it cannot reach. Worded as authorised, the trigger fires on a key no recording can touch, so it marks nothing. Worded by reach, it fires when a key that needs a limit can first be recorded.

**The cost.** Until the trigger, the schema is the only limit:
- An agent given the flag can add any text key a schema accepts, in any capability's configuration. Some of that text is a program or a command the capability runs.
- A mapping a schema leaves open, or a retired key it still accepts, lets a recording through.
- Where a permission model denies an agent edits of the file, the recorder still lets it write there (point 9).
- A capability authored elsewhere comes under the contract by its schema's name. If its `config` schema judges another file, the recorder creates one it never reads.
- Nothing checks the trigger for a capability authored elsewhere.
- A way to keep keys out that refuses every key not declared would break each capability that already records one. Brought later, it either keeps undeclared keys recordable, or comes with a change to each such capability.

### Alternatives considered

- **Each capability keeps its own writer.** Rejected: the copies drift, and each must rebuild the guards for text, bytes and the schema.
- **Record a capability's value in a file the backbone shapes,** as a documentation location is. Rejected: the value is the capability's setting, which its code reads from its own configuration (COR-048 point 2). The capability's schema declares the key, so a strict schema meets no key it did not declare.
- **Keys a capability declares recordable, now, every other key refused.** It would keep out the keys the audit found, give a capability an explicit opt-in, and avoid a later breaking change. Not taken: no key in reach needs it more than a hand edit does, or more than point 9's remedies give. And the declaration binds every capability's package metadata, so it belongs with the core decision of point 8.
- **A short list of keys kept out, now.** Rejected: the backbone would name capabilities' keys, and know what only their schemas and records should say.
- **Only location-shaped text.** Rejected: a path is location-shaped, and the browser key holds the path of a program.
- **Run the capability's validator after the schema.** Not taken: it would run a capability's command inside a backbone write, under no contract for such a run. Validation reports what the schema leaves out, as for a hand edit.
- **Ask nothing, as recording a location does.** Rejected: that least consent covers only a location already in use (COR-049 point 5).
- **Let the recorder replace a held value.** Rejected: a person moves a held value, and replacing keys is the setter's, for the backbone's own file.
- **Reach adapters too.** Not taken: an adapter's configuration would first need a home and a binding, which is a decision of its own.
- **The whole contract as a core record.** Not taken: the recorder, its guards and its reach are how project-kit's backbone is built, which an ADR records. Only the two rules of point 8 pass COR-025's first test, and they are raised for a core decision.
- **The two rules of point 8 as a core record now, this record realising them.** COR-025 would put them there. Not taken now: the way to keep a key from the recorder would bind every capability's package metadata too, so it belongs in the same core decision. Deciding the two rules apart from it would have that core record revised at the trigger. Until the core decision, this record holds them for the capabilities project-kit ships.

## Implications

- **The CLI reference** cites this record in the recorder's section, once the record is accepted. It stays the home of the recorder's mechanics, and carries the contract to capabilities authored elsewhere (point 8).
- **Each capability that keeps a writer of its own for such a recording** moves it to the recorder. Before it passes the flag, it checks that its own records make running its command the consent (point 6).
- **project-management's schema** stops accepting its retired setting for the default branch, so the guard refuses it (point 9).
- **A check that pins the keys in reach** for the capabilities project-kit ships would make a change of reach show in review (point 9).
- **The two rules of point 8** are raised for a core decision.
- **The way to keep a key out** starts, at the trigger, from a hypothesis: a declaration by the capability, in its package metadata, of the keys the recorder may record, read before any write. The record the trigger brings decides its form and its home.
- **Follow-ups that bear on the contract:**
  - **The quoting rule** for text values could move into the shared text edit, so the setter quotes as the recorder does.
  - **The capability-author skill** could teach the convention once a core record decides it (point 8): a `config` schema that declares its version, and its file's place.
  - **Uninstall** deletes a capability's `project/` folder, and the recorded keys with it. That folder is the project's, and the lifecycle record has removal touch no project content ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md), "Lifecycle operations apply uniformly"). This record does not endorse the deletion. The CLI reference's sentence on how long a recorded key lasts states today's behaviour only. The conflict is older than this record, and issue #1879 owns it.
  - **project-kit's use-case model** (`tech-docs/analysis/`) has no use case yet that covers recording a capability's key.
- **No migration.** The recorder is an addition (COR-010).
- **No accepted record is edited.** ADR-057 point 2's list of homes may gain the recorder's by a refinement of its own.
