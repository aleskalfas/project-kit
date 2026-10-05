---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-05
---

# Analysis artefacts follow a declared structure per kind

A design for #1352, which the maintainer decided on 5 and 6 October. It folds in #1346 (an actor's needs beside its description) and #1351 (the text the stamp writes).

- **Paths:** `SA/` is `.pkit/capabilities/software-analysis/`, and `LD/` is `.pkit/capabilities/living-docs/`.
- **Read from main:** the writing rules `WRITE` at 1.0.0 (`tech-docs/rule-sets/writing.md`), and the core actors (`tech-docs/analysis/use-case-model/actors.md`).
- **Citations:** records and rules by permanent id, files by name, never by line number (RS-WRITE-014, proposed).
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the issues in "Slicing", which the project manager files on the maintainer's go.

## Decided

The maintainer answered the note's four open questions on 5 and 6 October, in comments on PR #1353. Each answer is folded into the proposal below.

1. **Is software-analysis installed anywhere outside project-kit?** No. It is installed only in project-kit's own clones.
   - **So:** moving the actors to one file each ships no migration for adopters. Only project-kit's own eight actors move (part 6).
2. **What may a tool read from a body?** Nothing, answer (a). Tools take data only from the front matter.
   - **So:** a body's marks serve the structure check, the hints, readers and the rules, never as data for another tool. Actors move to one file each, and terms stay in the glossary (part 6).
3. **How does a hint reach the writer?** Answer (a): the hint sits in the stamped file as the placeholder, a marked one-line comment.
   - **So:** the check refuses a hint left in, and its messages repeat the hint (part 2).
4. **Is anything reported under a proposed rule?** Answer (c): the normal check reports nothing. A preview on request treats proposed rules as accepted, and lists what would break without failing.
   - **So:** `pkit analysis validate --preview` (part 3). The note proposes the same flag for living-docs once it checks anything a proposed rule gates, and leaves that to the maintainer (part 3).

## The question

How does each analysis kind declare its required parts, so a script checks them and a template shows each with a hint and an example?

## The chain

The maintainer's hierarchy is *meta rules > rules > templates > content*. pkit has a concept for each level, and each level has two owners.

| Level | The methodology or the capability owns | The project owns |
|---|---|---|
| Meta rules: decisions | software-analysis DEC-001, and the core records such as COR-051 | its PRJ and ADR records |
| Rules: rule sets (COR-051) | a method rule set, `SAN`: artefacts of a kind follow one format | its own sets: project-kit's `WRITE` for style, and `ANALYSIS` for its analysis |
| Templates: templates and declared structures | the shipped structure per kind, and the templates rendered from it | its additions to a kind's structure (part 4) |
| Content: artefacts | none | the analysis, under the internal root's `analysis/` (DEC-001 point 2) |

- **Each fact has one home:**
  - **The decision** names a kind's parts in words (DEC-001 point 1).
  - **The declared structure** lists them as data: which parts, in what order, required or optional, with each part's hint and example.
  - **The template** is the structure rendered for a writer.
  - **A rule** makes a structure bind. The structure is its checkable part, as a schema is (COR-051 point 1), and no part of its content.
  - **A style rule** says how to write. A hint says what data goes in a part, and never repeats a style rule.
- **Each structure binds at the status of the rule in its own column.** The shipped structure binds at the method rule's status. A project's addition binds at its project rule's status (part 4).
- **A structure change is no rule-content change,** so it flags none of the rule's dependants. A tightened structure shows up as validation findings after an upgrade.
- **Today:** software-analysis has no method rule set, and declares a structure for front matter only (`SA/schemas/*.schema.json`). `WRITE` is at 1.0.0, with RS-WRITE-002 on labels still proposed. It has no scope, and project-kit's operational rules send whoever writes the analysis to it.

## Today

### What `pkit analysis validate` checks

- Each artefact's own front-matter fields against its kind's schema (`SA/scripts/_lib/check.py`).
- A placeholder left in a field or the body, matched exactly against every placeholder ever shipped (`check.py`).
  - The list is append-only (`SA/scripts/_lib/placeholder.py`).
  - A test holds the list to the templates and the skill (`tests/test_software_analysis_templates.py`).
- A use case's and a journey's heading against its id and title.
- Ids, references, anchors, and the revalidation records' front matter.

### What it does not check

- **A body's parts.** A use case with no *Main path* passes. A placeholder catches a part left unfilled, not a part deleted.
- **Order.** Nothing checks that *Goal* comes before *Main path*.
- **Forms.** The stamp writes some of these, and nothing keeps any of them afterwards (`SA/scripts/_lib/stamp.py` and `revalidation.py`):
  - steps numbered, and variants lettered after a step, `1a.`
  - a journey's step lines against its `steps`
  - a record's outcome lines against its `outcomes`
- **An actor's or a term's section.** Only a placeholder in it is caught.
- **Hints and examples.** A placeholder is the only hint, and no template carries an example. The use case's and the journey's templates each hold an instruction line that stays in every finished artefact.

### living-docs, for contrast

- Each page kind declares its structure once, as data (`LD/schemas/page-kinds.yaml`), with a schema (`LD/schemas/page-kinds.schema.json`).
- The validator reports a declared heading that a page lacks or carries out of order (`LD/scripts/_lib/formats.py`).
- RS-LDOC-004 must be accepted for any body to be checked. Under any other status nothing is checked (`LD/scripts/_lib/spaces.py`).
- A structure is never read from a template's text, and a test holds each template to it (living-docs DEC-001 point 3).
- **Limits:** it reads headings only. A kind that a project adds declares no structure, and its pages are never failed (`LD/README.md`).

The analysis does not fit that reader as it stands. Its bodies use bold labels, such as `**Goal:**` (`SA/templates/use-case.md`). project-kit's writing rules make labels its house style (RS-WRITE-002).

## Proposal

### 1. A declared structure per kind

**A data file with a schema, as living-docs does.** `SA/schemas/artefact-kinds.yaml` declares each kind's structure.

- Its schema is a strict superset of `page-kinds.schema.json`.
- Its missing and out-of-order logic is that of `formats.departures`.
- So a later extraction to the backbone is a move, not a reconciliation.

| Where | For | Against |
|---|---|---|
| **A data file** (chosen) | One home for scripts. The shape living-docs already uses. | A template could drift from it. Rendering the template from it prevents that (part 2). |
| The template itself | One file | living-docs rejected reading a structure from template text. Required, optional and custom parts would need markup. |
| A rule set | Gated by status | A structure is no part of a rule's content (living-docs DEC-001 point 3). Each structure change would version the set. |

**The grammar.** A structure is a list of elements, each with an id such as `goal`. They are checked in that order unless the kind sets `ordered: false`.

- **Element types:**
  - `heading`: a level and, where fixed, its text, as in living-docs.
  - `label`: a bold label, its text then a colon, such as `**Goal:**`. It opens a paragraph or a top-level list item.
  - `opening`: the text before the first label, such as an actor's "who this is".
- **Only declared labels delimit.** A bold run is a label only when the kind declares its text. So a variant's `**1a.**`, a seam's `**UC-000 → UC-001:**` and a step's `**Export:**` stay content.
- **A part's extent:** from its label to the next declared label, or to a heading of the same or a higher level.
- **`required`:** true unless set false. An optional element is checked only when present. A required part may not be empty.
- **`hint` and `example`:** for the template (part 2), and for the check's messages.
- **`form`:** a check on a part's content, from a closed list that software-analysis implements. A list form judges only the part's list items, so a custom line inside the part never breaks it.
  - Generic: `sentence`, one sentence. `numbered-steps`: each item opens with a number, and no number repeats. Numbers need not run in sequence, since steps are append-only (DEC-001 point 3).
  - The analysis' own: `variants`, each item opening with a step of *Main path* and a letter, `2a.`, or the part reading `None.`. Then `steps-match-front-matter`, `seams-match-steps` and `outcomes-match-front-matter`.
- **A form on front matter.** A kind may give a front-matter list a form, as the actor kind gives each of its `needs` the `sentence` form.
  - The schema still checks the field's shape, and binds with no rule, as today.
  - The form lives in the structure because it binds at the method rule's status, as every other form does.

**Data and marks** (Decided 2). A tool takes data only from the front matter. A declared label marks a part for the structure check, the hints, readers and the rules, never as data for another tool.

**Custom content.** A writer may add labels and sections anywhere. The check judges only the declared elements: present, in order, not empty, and of their form. A project that wants its own labels checked declares them (part 4).

**Scope.** A kind's structure covers its body, and any front-matter form it declares. A withdrawn artefact is history, so a part required later never fails it.

- **A document kind** covers the document's body.
- **A collection kind** covers each entry's section, and the file's head: its heading and the opening sentence the stamp writes once (part 5). After part 6 the term is the only collection kind.
  - **The entry's extent is the backbone's.** COR-050 point 1 defines it, friction hashes exactly that text (`src/project_kit/friction_discovery.py`), and each computation has one home (ADR-057 point 2).
  - **software-analysis' own copy reads it differently** (`SA/scripts/_lib/markdown.py`). It would let a part pass the check outside the text friction treats as the entry.
  - **So the artefacts document gives each entry's section span.** `pkit friction artefacts --json` gains the key, and a key added raises no version. software-analysis reads it, as it reads the rest of that document (ADR-057 point 1).

**The check.** `pkit analysis validate` reports an element that is missing, out of order, empty, or not of its form. The message gives the part's hint and example. The rule's status decides whether it is reported at all (part 3).

**Where the reader lives.** software-analysis reads labels, part extents and forms. Four readers exist already:

- living-docs' heading reader (`LD/scripts/_lib/formats.py`)
- software-analysis' heading and section reader (`SA/scripts/_lib/markdown.py`)
- the backbone's two, for rule sets (`src/project_kit/rule_sets.py`) and for collection entries (`friction_discovery.py`)

| Option | For | Against |
|---|---|---|
| **software-analysis reads labels and forms, and the backbone gives the entry's extent** (chosen) | No new general reader in the core. One home for the entry. | Two readers of labels, once a second component reads them |
| The backbone reads headings, labels and extents now | One meaning of *section* and *label* | A reading command for one consumer, and a core record. The analysis' forms stay in the capability anyway. |
| software-analysis calls living-docs' reader | No copy | The capability works alone (DEC-001 point 10). |

**COR-007, applied.** This is the second case of a kind declaring its body structure as data. The variation is only now visible: labels, forms and collection entries. So it is a deliberate decision not to extract yet.

- **The trigger:** a second component that must read declared labels. That is living-docs shipping a page kind with labels, or letting a project add to a kind's structure.
- **What would move:** headings, labels, extents and the generic forms, as a backbone reading command. The analysis' own forms stay.
  - The `sentence` form is generic, but its end of a sentence is defined in RS-SAN-001's *How* (part 3).
  - So an extraction moves that definition into the backbone too.
- **Where it is recorded:** in DEC-001's alternatives, as living-docs DEC-001 records its trigger for the `source` kind.

### 2. Templates with a hint and an example per part

**The template is the declaration rendered, and each part's hint is its placeholder** (Decided 3).

- **Rendered.** The stamp renders the shipped structure plus the project's additions (part 4). The committed `SA/templates/<kind>.md` is made of:
  - the front matter, written by hand and held to the kind's schema, as today
  - the body, rendered from the declaration without additions, and held equal to it by a test
- **Exactly the structure.** In living-docs a template may show more than its structure. Here it shows exactly the structure, and DEC-001 says so.
  - Optional elements are shown too, each with its hint. A writer deletes an optional part they have nothing for.
  - A collection file's head is part of its kind's structure (part 1), so the glossary's heading and opening are rendered as well.
- **One part, as stamped:**

  ```markdown
  **Goal:** <!-- pkit:hint What the actor wants from this use case, in one sentence. Example: Export the report as a file. -->
  ```

- **The hint is the placeholder.** It stands where the content goes, as the angle-bracket hints of Cockburn's use-case template do ([Use Case Template](https://www.cs.otago.ac.nz/coursework/cosc461/uctempla.htm)).
  - The check refuses a part that still holds a hint, and a required part left empty once the hint is deleted.
  - A hint left in is refused by the placeholder check, which binds with no rule, as today. Only the structure check waits for RS-SAN-001 (part 3).
  - A hint is one line. No reader of the analysis skips comments (`SA/scripts/_lib/markdown.py` and `friction_discovery.py`), so a line break in a hint could split a section.
  - The marker is matched outside code spans and fences, so an artefact may quote it. Its `pkit` is the methodology's literal, as the container key is (the lifecycle README).
  - New templates hold no angle-bracket placeholders in their bodies. The append-only list stays for what was stamped before.
- **A hint also reaches a later editor.** The check's message for a missing or empty part, or for a hint left in, gives the hint and its example. The skill's *Fill it* lists give way to "fill each part as its hint says".
- **A hint says what data goes there, and shows one example.** It names no style. The example is plain and written in no project's voice.
- **No hints in a revalidation record.** Its stamp writes every part from the command line (`SA/scripts/_lib/revalidation.py`), so a hint would only be copied into every record.
- **The stamp's body generation is rewritten.** Today it copies template lines and rewrites some by pattern (`SA/scripts/_lib/stamp.py`). It renders from the declaration instead.

| Form of a hint | For | Against |
|---|---|---|
| **The hint as the placeholder** (chosen) | One mechanism. Read where the writer writes. Hidden when rendered. | A writer must delete the comment |
| A hint comment under an angle-bracket placeholder | Keeps today's placeholders | Two things to delete per part, and the placeholder list keeps growing |
| Hints only in check messages and the skill | Nothing to delete from an artefact | The first writer, often an agent, meets bare labels |
| The placeholder alone, as today | Nothing new | No room for an example. A long placeholder is hard to keep exact. |

### 3. The meta rule

**A method rule set that the capability ships, `SAN`, with the format rule first and a DEC-001 paragraph behind it.**

- **The rule:** "An analysis artefact carries its kind's declared structure, and each kind has a template." It mirrors RS-LDOC-004.
- **The set:** `SA/rule-sets/san.md`. Like `LDOC`, it has no scope and binds through the capability's check.
- **Its one rule, at first:** RS-SAN-001, the format rule. Its checkable part is the declared structure, forms included. So DEC-001 point 1's "one sentence" for a need and a goal is the `sentence` form, and needs no rule of its own (part 9).
- **Where a sentence ends:** RS-SAN-001's *How* says it for the `sentence` form, since software-analysis cannot cite project-kit's RS-WRITE-005.
  - It ends a sentence as RS-WRITE-005 does: at a full stop, a question mark or an exclamation mark before a space or a line end.
  - So "e.g." ends a sentence under both, and a hint says to avoid it.
- **The name:** `SAN`, for software analysis, as `LDOC` is for living-docs.
  - No rule set in this repository takes it, shipped or project-kit's own.
  - A shipped name is reserved in every adopter that installs the capability, since names are unique among a project's rule sets (COR-051 point 3).
  - A clash cannot be undone for that adopter, since its set's name is in every rule id. `SAN` is a common acronym, such as a storage area network, so a longer name such as `SOFTAN` is less likely to clash.
  - It leaves `ANALYSIS` free for project-kit's own set. A reader may take `RS-ANALYSIS-*` for the capability's, since `analysis` is the capability's alias (part 9).
  - DEC-001 names it, and the maintainer picks both names there, since a name is permanent once on main.
- **Inheriting it is optional.** A project's set inherits it only to fill a point it offers. Then every newly accepted rule is a new major for that project to re-pin (COR-051 point 7). `SAN` offers no point at first.
- **The decision:** DEC-001 gains a paragraph like living-docs' *A kind's structure* (living-docs DEC-001 point 3). It says each kind's structure is data, its template is rendered from it, and it binds at its rule's status. DEC-001 cites no project's rule set.
- **What the set adds over a DEC-001 paragraph alone:** a rule id the check's findings cite, a status the capability flips to turn the check on, and the pattern living-docs already uses.

**Under a proposed rule** (Decided 4):

- **The normal check reports nothing,** as in living-docs (`LD/scripts/_lib/spaces.py`). The same holds for a project's additions under a proposed rule (part 4).
- **`pkit analysis validate --preview` treats every proposed rule as accepted.** That is the method rule, and each rule a project's addition names. The preview lists what would then break.
- **It never fails on what it previews.** Its exit status is the normal check's.
- **A preview finding has the severity `report`, labelled `preview`.** Severities are a closed set that no validator extends (COR-055 point 4), and DEC-001 classifies the finding so.
- **It binds nothing,** so it keeps COR-051 point 4. A superseded or withdrawn rule stays unbound in the preview too.
- **`pkit validate` does not preview, for now.** Its `software-analysis:artefacts` member runs the normal check.
- **DEC-001 says so** in its paragraph on a kind's structure.

**living-docs, proposed and not decided:** give `pkit living-docs validate` the same flag, with the same meaning, once it checks anything a proposed rule gates.

- **Not yet.** Every `LDOC` rule is accepted, and a kind a project adds declares no structure. So a preview would find nothing today.
- **When it comes,** it refines living-docs DEC-001 point 3, which says no body is checked under any other status.
- **Why the same flag:** one habit across both capabilities, for a writer who uses both.

**Worth a core refinement later.** This design makes statements on COR-051's behalf that would then stand in two capability decisions:

- a structure binds at the status of the rule it is the checkable part of (COR-051 point 1)
- a check may preview a proposed rule without failing (COR-051 point 4)
- a fill binds only while the rule it fills binds, and its content may be a declared structure outside the rule (COR-051 point 7)
- an inherited rule reaches only as far as the scope of the set that names it (COR-051 point 2)

A refinement of COR-051 could state each once. A `pkit validate --preview` would also change the validator contract, which runs a validator with `--json` alone (COR-055 point 3 and ADR-058 point 4). So that step waits too.

### 4. What a project may add or narrow

**A file of its own in the capability's project tier, `SA/project/structures.yaml`,** with a schema bound to it by its path (COR-023).

- **Why there.** The project tier is the project's, and sync never touches it (`SA/README.md`). So no shipped file is edited (core rule 1).
- **Why its own file.** It is data the check reads, and `config.yaml` holds settings. A schema binds to it by its path alone, and an edit to the numbering setting never touches it.
- **Keyed by kind.** Each entry names a kind, such as `actor`, never a file. So an entry holds wherever the kind's files sit, as they move in part 6.
- **Uninstalling** the capability removes the project tier (`SA/schemas/config.yaml`), as living-docs says of captured sources.

What a project may change:

- **Relabel a shipped element, and replace its hint and example,** keeping its id, its place and its form. This tightens nothing, so it needs no rule and binds at the method rule's status. A non-English project writes its own labels this way.
- **Tighten, naming the project rule that asks for it:**
  - add labels and sections, each placed `after` a named element, with its hint and example. An addition is optional unless it sets `required: true`.
  - make a shipped optional element required
  - close a kind's label list (`closed: true`), so an undeclared label is reported. RS-WRITE-002's "one list" needs this.
- **What `closed` reports:** a bold run ending in a colon that opens a paragraph or a top-level list item, and is no declared label. A part with a form is skipped, so a seam's and a step's bold runs stay content.
- **May not:** drop or relax a shipped required element, reorder shipped elements, invent a form, or add a kind. A new kind needs its own decision (DEC-001 point 11). DEC-001's paragraph on a kind's structure forbids relaxing it, as COR-051 point 7 forbids relaxing an inherited rule. A structure is data, so here the check can refuse a relaxing entry outright.

Where an addition goes:

- **Right after the element it names.** It comes before any shipped element that follows the same one. Additions that name one element keep their order in the file.
- **After another addition.** An addition may name an earlier addition, as the sketch in part 9 does. A cycle is refused.
- **Across versions.** A shipped element added later lands after the project's additions at its place, so the two never trade places silently.
- **Element ids are permanent once shipped.** An element is retired, never renamed, as a rule id is (COR-051 point 3). DEC-001 says so.
- **Its element retired.** An addition that names a retired element is an error, since the project can mend its own file (COR-055 point 1).

How a tightening binds:

- **At the status of the rule it names.** Under a proposed rule the normal check reports nothing of it, and `--preview` shows it (part 3). So no tightening binds before its rule is accepted (core rule 2).
- **And at the method rule's.** An addition extends the shipped structure, so it binds only once RS-SAN-001 is accepted too. Should RS-SAN-001 be superseded, the shipped structure binds at its successor's status.
- **A fill binds only with the rule it fills.** A rule that fills an inherited point binds once both are accepted.
- **The preview** treats every rule in that chain as accepted.
- **Only where that rule's scope reaches.** An addition applies to an artefact only when the named rule's scope covers the artefact's path (COR-051 point 2).
  - The artefacts document says which sets cover each artefact (Slicing, issue 6), so the matching keeps one home (ADR-057 point 2).
  - A named rule whose scope covers no artefact of the kind is reported.
  - DEC-001 states the reading behind it: a rule reaches as far as the scope of the set that names it.
- **Later edits bind without a new acceptance.** Once the named rule is accepted, a later edit to the file binds as it lands.
  - That is the trade of data over rule content, as in living-docs, and each edit is reviewed in its pull request.
  - So a rule names the tightenings it authorises, as RS-ANALYSIS-002 names optional labels and a closed list. Making a part required names a rule that says so.
- **Orphaned when the rule is superseded or withdrawn:** reported and not applied, as an orphaned fill is (`src/project_kit/rule_sets.py`).
- **No core record changes.** Rules are artefacts with their fields in `pkit friction artefacts --json`, so the check reads a rule's status there.

**project-kit's own entries** are its actors' labels, under the kind `actor`, named by RS-ANALYSIS-002 (part 9).

| Alternative, not chosen | Against |
|---|---|
| Project templates beside the shipped ones | Two shapes that drift, which the declaration exists to prevent |
| A project rule set that carries the structure | A structure is no part of a rule's content (part 1). |
| A `structures` key in `config.yaml` | Settings and data in one file. A rule anchored to the file would be flagged by every edit to either. |

### 5. Templates follow the writing rules, and stay project-neutral

The stamp writes only labels and hints, so the shipped templates meet any project's rules through a neutral floor.

The conflict:

- #1351 asks that the stamped body text use "no semicolon and no sentence over 25 words". It also asks that "each template's opening section starts with one sentence that says what it holds".
- `WRITE` is project-kit's, and the templates ship to every adopter.

The resolution:

- **The stamp writes almost no prose that survives filling.** It writes labels and hints. The author's words replace the hints, and labels are not counted as sentences (RS-WRITE-005).
- **#1351's opening sentence, read per kind:**
  - A collection file's opening is the one sentence the stamp writes, once, when the file is created (`SA/templates/glossary.md`). After that it is the project's to reword.
  - A use case, a journey or an actor opens with its first part: *Goal*, *Starts* or its opening. That sentence is the author's, not the stamp's.
- **Shipped hints and examples meet a neutral floor:** short sentences and no semicolons. They carry none of project-kit's style, such as RS-WRITE-002's labels or RS-ANALYSIS-001's voice (COR-014).
- **project-kit holds its own templates to `WRITE`.** In its source repository the shipped trees are authored source (ADR-055 point 3).
  - This reverses the usual ownership, a project rule over shipped content. It is recorded as a refinement of ADR-055 point 3, not left implicit.
  - A rule set's scope names artefacts (`.pkit/schemas/backbone/rule-set.schema.json`), and the templates and the declaration are none. So project-kit's operational rules send whoever writes them to `WRITE`, as they already do for the analysis (`.pkit/rules/project.md`).
  - It never reaches an adopter.
- **An adopter's rules bind what its authors write,** through its own rule sets' scopes.

### 6. The actors' layout (#1346)

**One file per actor**, `use-case-model/actors/ACT-<slug>.md`, as use cases are (Decided 2).

- **Reads as one unit.** The needs sit in the front matter, about ten lines above the description. Today they sit up to 130 lines away in the actors file.
- **The needs stay data.** The schema checks them, and the readers filler reads them from the artefacts document, as today.
- **An actor becomes a document kind,** headed `# ACT-<slug> — <name>`, and checked as a use case is. The collection code stays, for terms.
- **What else changes:**
  - DEC-001 points 2 and 3, and the place in `SA/package.yaml`
  - an `id` field in the actor's schema
  - the stamp, and the skill's actor sub-procedure
  - the readers filler, which now fails closed on any one unreadable actor file

**The criterion: a tool takes data only from the front matter** (Decided 2). Fillers read through the artefacts document, which carries fields and not bodies (ADR-057 point 1).

- The readers filler reads needs today, so needs stay data, and the files move to sit beside the prose.
- A term's definition is what a glossary point would carry, which living-docs DEC-001 already expects to take from "whatever component keeps one". So definitions stay data too, and the glossary stays a collection.
- The cost: a glossary read rendered shows each term's heading, not its definition. A generated view can show both later, never written twice.

| Alternative, not chosen | Against |
|---|---|
| Declared body elements count as data: the needs become a labelled list in the actor's section, parsed for the filler | No file moves. But the filler would parse a body, which the artefacts document does not carry, and the schema could no longer check the needs. |
| Keep the collection, mirror the needs into the section, and check the two equal | A fact written twice by hand, which #1346 rules out |

**The move.** Moving an artefact requires a revalidation in the same change (COR-050 point 3). That answer is a person's (core rule 20).

- **No migration** (Decided 1). software-analysis is installed only in project-kit's own clones, so no adopter's state needs one (COR-010).
- **One mechanical cost stays.** Removing `SA/templates/actors.md` triggers `pkit migrations check-diff`. The file is removed, and a migration that does nothing says why.
- **project-kit's eight actors are on main, so they move.** The move's pull request carries eight revalidations, one per actor, each the maintainer's answer. No artefact anchors to the actors yet.
- **A gap in the change check.** It pairs a moved artefact with its old self only within one kind (`src/project_kit/friction_check.py`).
  - An entry that becomes a document reads as removed and new, and a new artefact counts as revalidated (COR-050 point 6).
  - So today the check would not ask for the eight revalidations.
- **The fix comes first** (Slicing, issue 2). The check then asks for the eight revalidations, so core rule 20's usual path applies. An agent writes them, and the maintainer sees the check's list before authorising the merge.
- **Note:** an adopter that installs software-analysis before this lands needs a lifecycle decision, not a migration. A migration runs after the sync, so its refusal would halt a half-done upgrade, and it would edit adopter-owned files.

### 7. Which writing rules a script can check

A script can check part of eight of `WRITE`'s rules, and judgment keeps the rest.

| Rule | A script checks | Judgment keeps |
|---|---|---|
| RS-WRITE-005, 25 words | The count, as its *How* defines it | What is a quoted example of a broken rule |
| RS-WRITE-008, no semicolons | A semicolon outside code and quotes | Nothing |
| RS-WRITE-007, four sentences | The count per paragraph and list item | One topic |
| RS-WRITE-002, labels | Labels from the declared list, in order, with no pronoun | Whether a label fits |
| RS-WRITE-004, *Note* last | *Note* as the last label | What counts as side matter |
| RS-WRITE-001, the opening | A section that opens with a sentence, not a list | What matters most |
| RS-WRITE-014, permanent ids | A line number after a file name | Whether a citation needs an anchor instead |
| RS-WRITE-011, one term | A name that a term `replaces`, still in use, reported and never failed | Two words for one thing, and a common word that is no term |
| RS-ANALYSIS-001, the actor's voice | Nothing beyond the method's `sentence` form (part 9) | An imperative in the actor's voice |
| None | Control characters and list depth | Nothing |

RS-WRITE-003, 006, 009, 010 and 013 stay judgment.

Where a lint would live:

- **Not in this change.** The structure check comes first.
- **Next, a project-kit script** over the analysis, to learn which checks hold on real text. An existing prose linter such as Vale is the alternative. It has sentence-length and banned-token checks, at the cost of a toolchain outside Python.
- **Later, the backbone.** A rule could name a mechanical check from a list the backbone ships, with the project's thresholds. That needs a COR-051 amendment, so it waits for a second rule set that wants it (COR-007).
- **Not software-analysis.** `WRITE` is a project's set, and the capability ships no project's style.

### 8. The parts of each kind, a first cut

Grounded in DEC-001 point 1 and today's templates. Labels keep today's wording, and a project may relabel them (part 4).

**Use case**, its body:

| Element | Required | Form | DEC-001 point 1 | Cockburn | RUP |
|---|---|---|---|---|---|
| `# UC-NNN — <title>` | yes | heading | its goal, in a few words | Use case | use-case name |
| **Goal:** | yes | sentence | "one actor's goal" | Goal in context | brief description |
| **Starts when:** | yes | none | "when it starts" | Trigger | no section |
| **Main path:** | yes | numbered-steps | "the main path" | Main success scenario | basic flow |
| **Variants:** | yes, `None.` allowed | variants | "variants" | Extensions, numbered `3a` | alternative flows |
| **Done when:** | yes | none | "when it is done" | Success end condition | postconditions |

- **Variants required:** a required part makes the writer consider variants, and an omitted one does not.
- **Not adopted:** scope, level, preconditions, stakeholders and interests, minimal guarantees, and special requirements. A project may add them (part 4). Quality requirements are outside DEC-001 (point 11).
- **Sources:** Cockburn's template, linked in part 2. His fully dressed form in *Writing Effective Use Cases* (Addison-Wesley, 2001) adds stakeholders and interests, and minimal guarantees. The RUP column follows a RUP-derived use-case specification ([Use Case Specification Template](https://www.voa.va.gov/DocumentView.aspx?DocumentID=216)).
- **The README** shows *Main path* inline (`SA/README.md`). It follows the template once the template is rendered.

**Journey**, its body, every element required:

- `# JRN-NNN — <title>`
- **Starts:**
- **Steps:**, of form `steps-match-front-matter`
- **Seams to watch:**, of form `seams-match-steps`
- **Done when:**

**Actor**, a document after part 6:

- `# ACT-<slug> — <name>`, required
- an opening, required: who this is
- **Comes:** and **Brings:**, optional, from today's placeholder (`SA/templates/actors.md`)
- in the front matter, each of its `needs` of form `sentence` (DEC-001 point 1)

**Term**, its entry section, its definition staying in the front matter:

- `## TERM-<slug> — <name>`, required
- **Applies to:**, **Not:** and **Example:**, optional, from today's placeholder (`SA/templates/glossary.md`)

**Revalidation record**, its body, written whole by the stamp:

- `# <date> — <subject>`
- `## Outcomes`, of form `outcomes-match-front-matter`
- `## Gaps`: each gap with its resolution, or `None found.`
- **No style lint:** a record's words are a person's decision (RS-WRITE-013, core rule 20).

### 9. Where the analysis set's parts go

The analysis set drafted beside `WRITE` waited for this design, and its parts go to three homes. The method's part goes to software-analysis, the style to project-kit's rule set, and the labels to project-kit's data.

| Part of the draft | Goes to | Why |
|---|---|---|
| A need or a goal is one sentence | software-analysis: the `sentence` form under RS-SAN-001 | DEC-001 point 1 says it, so every adopter gets it. |
| A need or a goal speaks in its actor's voice | project-kit's `ANALYSIS`, as RS-ANALYSIS-001 | A voice is a project's style (COR-014). |
| A need's 25-word limit | `WRITE`, inherited | RS-WRITE-005 already counts each need. |
| The actors' nine labels, in order | project-kit's `structures.yaml`, under the kind `actor` | The check reads a structure as data (part 4). |
| The fill of `RS-WRITE-002#labels` | project-kit's `ANALYSIS`, as RS-ANALYSIS-002 | The rule gives the list an id, a status and a scope. |
| The name `ANALYSIS` | project-kit's set | It names what the set governs, as `TECH` and `USER` do. |

**software-analysis's part.** RS-SAN-001's structure gives *Goal* and each of an actor's `needs` the `sentence` form (part 3).

- So one sentence binds every adopter once RS-SAN-001 is accepted.
- The draft grounded its rule in DEC-001 point 1. That was the sign that the rule is the method's.

**project-kit's set, `ANALYSIS`,** at `tech-docs/rule-sets/analysis.md`:

- **Scope:** `tech-docs/analysis/**`.
- **Inherits:** `WRITE@1`, since `WRITE` is now at 1.0.0. It does not inherit `software-analysis:SAN`, which offers no point to fill (part 3).
- **RS-ANALYSIS-001, the actor's voice:** each need and each goal is an imperative that starts with its verb. It uses *I*, *me*, *my* and *myself* wherever the actor refers to itself.
  - It is retitled to the voice, and its statement drops "one sentence", which the method now checks.
  - Its *How* keeps "*Never* may come before the verb", and drops the line against splitting.
  - Of its examples, only the pair on "Find my role definition" stays. Its `why` is rewritten to give the voice's reason alone.
- **RS-ANALYSIS-002, the labels:** it fills `RS-WRITE-002#labels`. Its statement takes a kind's labels from its declared structure with the project's additions, in that order. It holds no copy of the list.
  - It names the tightenings it authorises: optional labels, and a closed list (part 4).
- **Anchors:** RS-ANALYSIS-002 anchors to RS-WRITE-002, as a fill must (COR-051 point 7).
  - It does not anchor to `structures.yaml`. A structure change is no rule-content change (the chain), and a revalidation could only answer that the rule still points at the list.
  - So a later uninstall leaves the rule no dead anchor.
- **The name:** `ANALYSIS`, for the maintainer to confirm beside the method set's name (part 3). It differs from `SAN` and from every set in this repository.
- **Status:** both rules ship proposed. The maintainer accepts them with RS-WRITE-002.
- **The pin, after that acceptance.** Accepting RS-WRITE-002 adds an accepted rule, so `WRITE` goes to 2.0.0 (COR-051 point 7). The same change re-pins `ANALYSIS` to `WRITE@2`, as each later acceptance in `WRITE` does.

**The label list as data, keyed by kind.** A sketch of project-kit's `structures.yaml`, with hints and examples left out:

```yaml
actor:
  rule: RS-ANALYSIS-002
  closed: true
  add:
    - {id: setup, label: The setup, after: opening}
    - {id: always-a-person, label: Always a person, after: setup}
    - {id: can-be, label: Can be, after: always-a-person}
    - {id: does, label: Does, after: can-be}
    - {id: in-the-model, label: In the model, after: brings}
    - {id: core, label: Core, after: in-the-model}
    - {id: note, label: Note, after: core}
```

- **The shipped labels stay shipped.** *Comes* and *Brings* are the method's (part 8), so the list adds the other seven around them.
- **Every label is optional.** An addition is optional unless it says otherwise (part 4), and RS-WRITE-002 lets a section leave out a label it has nothing for. Today's actors use different subsets.
- **The order holds.** `setup` names the opening, so it comes before the shipped *Comes*, which follows the opening too (part 4).
- **Keyed by kind, not by path.** The draft named the actors file, which part 6 retires. The kind `actor` names every actor's file wherever it sits.
- **The check reads it** with the shipped structure. With `closed: true`, a label outside the list is reported.
- **Gated three times.** It binds once RS-ANALYSIS-002, RS-WRITE-002 and RS-SAN-001 are all accepted (part 4). Until then only `--preview` reports it.
- **In scope.** `ANALYSIS` covers the whole analysis, so the additions reach every actor (part 4). `WRITE` has no scope, so an entry naming RS-WRITE-002 itself would reach none, and be reported.

**RS-WRITE-002 stays proposed until this lands** (Slicing, issue 11). Then the maintainer can accept it with RS-ANALYSIS-001 and RS-ANALYSIS-002.

**A stale example on main.** RS-WRITE-002's *Keeps the rule* quotes the core actors as "**Comes:** for every unit of work, …". The actors now say "for every change". Issue 11 touches RS-WRITE-002, and fixes the quote there.

## Forces and costs

The design breaks what passed before, but before any release and with no adopter to carry.

- **A breaking change, before any release.** A check that fails what it passed before breaks the capability, as living-docs DEC-001 point 3 says of pages. software-analysis is at 0.1.0 (`SA/package.yaml`), and installed nowhere else (Decided 1).
- **Changesets.** software-analysis takes a `minor`, which its first release may absorb. The backbone takes a `minor` for the entry span and the sets that cover each artefact, and software-analysis then requires that release.
- **Adopters, once there are some:**
  - an artefact that lacks a required part is filled in
  - additions are optional, and relabelling needs no rule
  - `--preview` shows what a proposed rule would fail before anyone accepts it
- **Brownfield onboarding** (DEC-001 point 9). An agent derives candidates in bulk, and required parts raise that cost. The stamp's hints guide it, and each candidate fails until a person confirms and fills it, as point 9 wants anyway.
- **Placeholders.** Body placeholders retire for new artefacts. The append-only list stays for old ones.
- **What stays LLM judgment:**
  - whether the content is true, and whether a goal is one user story
  - whether a hint was followed in spirit
  - the writing rules marked judgment in part 7
- **Less LLM use.** The script runs first, so a reviewer reads only artefacts that have their shape.

## Slicing

Thirteen issues build the design, filed in this order. Each is a Task under EPIC #234, sized for one pull request.

- **Docs ride along.** Each issue keeps the README and the skill true for what it changes. Issue 12 then rewrites how they teach.
- **Existing issues:** #1346 is issue 3, and #1351 folds into issue 9. #1352 closes with this note's pull request.
- **Records:** only issue 1 changes decision records. The others apply them, so each waits for their acceptance (core rule 2).
- **Changesets:** each issue that changes what an adopter sees declares its own (PRJ-002).
  - software-analysis takes one in issues 3, 4, 5, 7, 8, 9, 10 and 13. Issue 1 refines a shipped decision ahead of its code, so its segment is `none`.
  - The backbone takes a `minor` in issues 2 and 6.
  - Issue 7 is the first to read issue 6's keys, so its changeset also declares the backbone it requires.

1. **software-analysis's decision covers each kind's declared structure**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** DEC-001 says each kind's structure is data, rendered as its template, with hints as placeholders. It binds at its rule's status, with a preview on request. Each actor becomes a file, and the maintainer picks the method set's name.
   - **Records:** software-analysis DEC-001 points 2 and 3, a new paragraph on a kind's structure, and its alternatives and implications. ADR-055 point 3 holds project-kit's templates to `WRITE`, in wording the architect authors (COR-025).
   - **Depends on:** the maintainer's go on this design.
2. **The change check asks for a revalidation when an entry becomes a document**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** the check pairs a collection entry with the document it becomes. COR-050 point 3's "moving an artefact" covers such a move, and the issue says so.
   - **Records:** none changed. It applies COR-050 point 3.
   - **Depends on:** nothing. It comes before issue 3, so the check asks for that move's revalidations.
3. **An actor's needs read beside its description**
   - **Type:** Task, parent EPIC #234. It is #1346, kept, and its criterion on a migration falls away (Decided 1).
   - **Delivers:** each actor is a file, `use-case-model/actors/ACT-<slug>.md`, with its stamp, heading check, readers filler and skill sub-procedure. Its new template meets the neutral floor, and the old one goes with a migration that does nothing and says why.
   - **The move:** project-kit's eight actors move, each with the revalidation the change check asks for. The maintainer sees the check's list of them before authorising the merge (core rule 20).
   - **Records:** none changed. It applies DEC-001 points 2 and 3, and COR-050 point 3 for the move.
   - **Depends on:** 1 and 2.
4. **software-analysis ships its format rule, proposed**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** the method set, `SA/rule-sets/san.md` under the name issue 1 picks, with RS-SAN-001 proposed and its origin in DEC-001. It has no scope, and binds nothing yet.
   - **Records:** none changed. It applies DEC-001 and COR-051.
   - **Depends on:** 1.
5. **Each analysis kind declares its structure as data**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** `SA/schemas/artefact-kinds.yaml` and its schema, a strict superset of living-docs' `page-kinds.schema.json`. It declares part 8's five kinds with hints, examples and forms by name. A schema test holds it, and nothing else reads it yet.
   - **Records:** none changed.
   - **Depends on:** 1, and 3 for the actor as a document.
6. **The artefacts document gives each entry's span and the rule sets that cover each artefact**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** `pkit friction artefacts --json` gains two keys. One is each entry's section span, computed where friction hashes the entry. The other is, for each artefact, the rule sets whose scope covers it, matched where places are matched.
   - **Records:** none changed. It applies COR-050 point 1, COR-051 point 2 and ADR-057 points 1 and 2. Keys added raise no document version.
   - **Depends on:** nothing. It can land beside 1 to 5.
7. **Analysis bodies are checked against their kind's structure, with a preview**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** `pkit analysis validate` reads labels and extents, and reports a part missing, out of order, empty, or not one sentence. Each message gives the hint and example. Nothing is reported while RS-SAN-001 is proposed, and `--preview` reports what would break, at severity `report`.
   - **Records:** none changed. living-docs stays untouched unless the preview spreads (part 3).
   - **Depends on:** 4, 5 and 6.
8. **Steps, variants, journey steps and record outcomes keep their stamped forms**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** the forms `numbered-steps`, `variants`, `steps-match-front-matter`, `seams-match-steps` and `outcomes-match-front-matter`, under the same gate and preview.
   - **Records:** none changed.
   - **Depends on:** 7.
9. **Templates show each part with a hint, rendered from the declaration**
   - **Type:** Task, parent EPIC #234. It folds in #1351, which its pull request closes.
   - **Delivers:** template bodies rendered from the declaration, each part's hint a one-line `pkit:hint` comment, and the stamp rendering the same way. The placeholder check refuses a hint left in. Shipped hints meet the neutral floor, and old placeholders join the append-only list.
   - **Also:** project-kit's operational rules send whoever writes the templates and the declaration to `WRITE` (part 5).
   - **Records:** none changed. It applies DEC-001 and ADR-055 point 3 as refined in 1.
   - **Depends on:** 3, 5 and 7.
10. **A project adds to an analysis kind's structure in a file of its own**
    - **Type:** Task, parent EPIC #234.
    - **Delivers:** `SA/project/structures.yaml`, keyed by kind, with its schema bound by path. The check and the stamp read its relabels and tightenings, placed as part 4 says. Each binds at its named rule's status and RS-SAN-001's, where issue 6 says the named rule's scope reaches.
    - **Records:** none changed. It applies DEC-001 and COR-051 point 7.
    - **Depends on:** 9, and 6 for scope.
11. **project-kit's analysis has a rule set of its own, and its actors' labels as data**
    - **Type:** Task, parent EPIC #234.
    - **Delivers:** `ANALYSIS`, `tech-docs/rule-sets/analysis.md`, with RS-ANALYSIS-001 and RS-ANALYSIS-002 proposed, and the actors' labels in `structures.yaml` (part 9). It fixes RS-WRITE-002's stale example, and `WRITE`'s opening on #1352. project-kit's operational rule on writing the analysis names `ANALYSIS`.
    - **Records:** none. `WRITE` and project-kit's operational rules change. It needs no changeset, since it is project-kit's alone.
    - **Depends on:** 10.
12. **The analysis-author skill and the README teach writing to hints**
    - **Type:** Task, parent EPIC #234.
    - **Delivers:** the skill's *Fill it* lists give way to "fill each part as its hint says", and its walkthrough runs the preview. The README shows each kind as its rendered template, and documents `structures.yaml`.
    - **Records:** none changed.
    - **Depends on:** 9 and 10.
13. **The analysis structure check binds**
    - **Type:** Task, parent EPIC #234.
    - **Delivers:** the maintainer accepts RS-SAN-001, and the method set goes to 1.0.0. Before that, project-kit's analysis passes `--preview` with no finding from the method set. software-analysis takes a `minor` changeset.
    - **Records:** none changed. A rule's acceptance follows COR-051 point 4.
    - **Depends on:** 3, 8 and 9.

Found on the way, two more to file:

- **The backbone's two readers agree on a rule-set file's sections**
  - **Type:** Task, parent EPIC #234 unless the project manager finds a closer one.
  - **Delivers:** one reading of a section. Today the rule-set reader skips fenced code, and the entry reader does not (`src/project_kit/rule_sets.py` and `friction_discovery.py`). The backbone takes a `patch` changeset.
  - **Depends on:** nothing.
- **Installing a capability refuses a rule-set name the project already uses**
  - **Type:** Task, parent EPIC #234 unless the project manager finds a closer one.
  - **Delivers:** install refuses a capability whose method set takes the name of one of the project's own sets. Today only validation, after the install, finds the clash. The backbone takes a `minor` changeset.
  - **Depends on:** nothing.

Not filed now:

- **The acceptance of project-kit's analysis rules.** The maintainer accepts RS-WRITE-002, RS-ANALYSIS-001 and RS-ANALYSIS-002 together, after issue 11.
  - `WRITE` goes to 2.0.0, and `ANALYSIS` re-pins to `WRITE@2` (part 9).
  - RS-WRITE-002's status is part of its content, so RS-ANALYSIS-002 owes a revalidation in the same change (COR-051 point 2 and COR-050 point 6).
- **living-docs' `--preview`,** proposed in part 3. It waits for the maintainer's word, and refines living-docs DEC-001 point 3 when it comes.
- **A core refinement** stating once what part 3 lists. It waits for a second capability to need it.
- **project-kit's writing lint** (part 7), and **the reader's extraction** once its trigger fires (part 1).

## Review

The critic and then the architect reviewed the drafts, and they reviewed the decided draft in the same order. Each blocking finding and gap, with its answer.

**The critic, on the first draft:**

| Finding | Answer |
|---|---|
| Red flag: moving the actors needs a revalidation per actor, which a migration cannot write (COR-050 point 3) | Confirmed. Part 6 now costs the move, and the architect's review narrowed it further. |
| Red flag: project labels bound at the method rule's status would enforce proposed RS-WRITE-002 | Confirmed. A tightening binds at its own rule's status (part 4). |
| Red flag: analysis forms would move into the backbone | Confirmed. The forms stay in software-analysis (part 1). |
| The label grammar breaks on `**1a.**` and seam lines | Only declared labels delimit, and a part's extent is defined (part 1). |
| `numbered-steps` cannot mean sequential | It means numbered and unique (part 1). |
| A hint marker can be quoted, and a multi-line hint can split a section | One-line hints, matched outside code (part 2) |
| The stamp's rewriting is not costed | The body generation is rewritten, and records carry no hints (part 2). |
| What the committed template is made of | Front matter by hand, body rendered (part 2) |
| Project-kit's voice in shipped examples, and labels no project can rename | A neutral floor, and relabelling without a rule (parts 4 and 5) |
| Part 4 underspecified | `after`, `closed`, no new forms, and a file of its own (part 4) |
| A third home for each part's description | The skill's *Fill it* lists give way to the hints (part 2). |
| Withdrawn artefacts, and brownfield onboarding | Parts 1 and "Forces and costs" |
| #1351's opening-sentence criterion | Quoted and read per kind (part 5) |
| Counter-alternatives: the hint as the placeholder, hints in check messages, #1351 first, an existing prose linter | Adopted in parts 2 and 7. #1351 first was adopted, then folded into issue 9, since rendering retires the text it would reword (Slicing). |
| Smaller citations | Corrected or removed |

**The architect, on the second draft:**

| Finding | Answer |
|---|---|
| Concern: a collection entry's extent would be computed outside the backbone, which owns it | Adopted. The artefacts document gives the span (part 1, issue 6). |
| Concern: additions reported under a proposed rule, where living-docs checks nothing | Adopted: the normal check reports nothing under a proposed rule. The maintainer added a preview on request (Decided 4, parts 3 and 4). |
| Concern: the actor migration is likely unneeded, and would fail mid-upgrade and edit adopter files | Adopted. No adopter has the capability (Decided 1), and the gap in move pairing is its own issue (part 6). |
| Data or prose decided two ways for actors and terms | One criterion, which the maintainer set as the front matter only, so definitions stay data (part 6, Decided 2) |
| The chain mixed a rule's level with its owner | Two axes (the chain) |
| Part 4: which entries need a rule, scope, superseded rules | Relabelling needs none. Scope and orphans are checked (part 4). |
| `structures` in `config.yaml` | A file of its own (part 4) |
| The extraction trigger mis-stated | A component that must read declared labels. Generic forms move with it (part 1). |
| `WRITE` over shipped templates crosses an ownership line | Recorded as an ADR-055 refinement, with a neutral floor for adopters (part 5) |
| Custom labels inside a part with a form | List forms judge only list items (part 1). |
| The method set's scope and name | No scope, and the name `SAN` (part 3) |

**The critic, on the decided draft:**

| Finding | Answer |
|---|---|
| Red flag: two elements follow one anchor, so the order of additions is undefined | A tie-break: an addition sits right after its element, before a shipped one. A lost element orphans it (part 4). |
| Red flag: additions are required by default, so every actor would fail | An addition is optional unless set required (parts 4 and 9). |
| `closed` reports labels no rule describes | A label-shaped run is defined, and parts with a form are skipped (part 4). |
| Additions could bind while RS-SAN-001 is proposed | An addition also waits for RS-SAN-001 (parts 4 and 9). |
| Does a hint left in wait for RS-SAN-001? | No. The placeholder check refuses it, with no rule, as today (part 2). |
| Accepting RS-WRITE-002 breaks the `WRITE@1` pin | `WRITE` goes to 2.0.0, and the same change re-pins `ANALYSIS` (part 9). |
| RS-ANALYSIS-001's examples and `why` still argue for one sentence | Retitled to the voice, with one example pair and a new `why` (part 9) |
| RS-ANALYSIS-002 points at a list that lacks the shipped labels | It takes the declared structure with the additions (part 9). |
| A scope can cover part of the analysis | An addition applies only where the named rule's scope covers the artefact (part 4). |
| Changesets missing from most issues | A changeset line in Slicing, with issue 7's backbone need |
| No issue sends template writers to `WRITE` | Issue 9 adds the operational rule. |
| Without the pairing fix, the actor revalidations are not answers the check asks | The pairing fix now comes first, as issue 2, so the check asks for them (part 6). |
| The COR-051 refinement is not tracked | Listed under "Not filed now" |
| The old actors template: kept, or removed? | Removed, with a migration that does nothing (issue 3) |
| `sentence` has no defined end | RS-SAN-001's *How* defines it (part 3). |
| The glossary's head is in no structure, and optional parts are unstated | A collection kind declares its file's head, and templates show optional parts (parts 1 and 2). |
| Uninstalling leaves RS-ANALYSIS-002 a dead anchor | RS-ANALYSIS-002 no longer anchors to the file (part 9). |
| "May not relax" cites inheritance where none exists | Grounded in DEC-001's paragraph (part 4) |
| A path anchor to `structures.yaml` makes busywork | Dropped. A structure change is no rule-content change (part 9). |
| Front matter gets two checks | The schema binds with no rule, and the form binds at RS-SAN-001's status (part 1). |
| `SAN` is a common acronym | Stated, with `SOFTAN` as a less common choice. The maintainer picks in issue 1 (part 3). |
| The stale example is a dated quotation, so editing it changes a rule | Kept: the maintainer named it stale. RS-WRITE-002 is proposed, and the fix lands with the fill (issue 11). |
| Counter-alternative: preview as a backbone concept | "Not yet" (part 3) |
| Counter-alternative: split issue 10 | Kept as one. Rendering the additions is small once issue 9 renders, and both share one merge of the structure. |

**The architect, on the decided draft:**

| Finding | Answer |
|---|---|
| Concern: `--json` must not add a severity or a key for the preview | A preview finding has the severity `report`, labelled `preview`, as DEC-001 classifies it (part 3). |
| A per-capability flag is the right altitude now, and a `pkit validate --preview` changes the validator contract | Agreed, and the later step names COR-055 point 3 and ADR-058 point 4 (part 3). |
| The core-refinement list misses two statements made on COR-051's behalf | Added: a fill binds only with its rule, and may hold a structure. A rule reaches as far as its set's scope (part 3). |
| Scope matching would sit outside its one home | Issue 6 gives the sets that cover each artefact, and issue 10 reads them (part 4). |
| Additions have no pin against the shipped structure | Element ids are permanent, an addition naming a retired one is an error, and a chain of additions is allowed without cycles (part 4). |
| Once the rule is accepted, later edits to the file bind with no new acceptance | Stated as the trade, and a rule names the tightenings it authorises (parts 4 and 9). |
| `SAN` is reserved only where the capability is installed, and a clash cannot be undone | Stated (part 3). An install check for a clashing name is filed as found on the way. |
| `RS-ANALYSIS-*` may read as the capability's | Stated, for the maintainer to weigh beside the method set's name (parts 3 and 9). |
| The acceptance of project-kit's analysis rules is untracked | Listed under "Not filed now", with the re-pin and RS-ANALYSIS-002's revalidation |
| Two definitions of where a sentence ends | RS-SAN-001 ends a sentence as RS-WRITE-005 does (part 3). |
| The extraction would move a capability rule's definition | Stated in the extraction trigger (part 1) |
| Changesets missing for issue 1 and the backbone fixes | Issue 1 takes `none`, and each backbone issue names its segment (Slicing). |
| The ADR-055 refinement is the architect's to author | Issue 1 says so. |
| Make the actor move depend on the pairing fix | Done: the fix is issue 2, and issue 3 depends on it. |
