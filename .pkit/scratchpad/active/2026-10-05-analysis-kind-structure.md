---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-05
---

# Analysis artefacts follow a declared structure per kind

A design draft for #1352. It folds in #1346 (an actor's needs beside its description) and #1351 (the text the stamp writes).

- **Paths:** `SA/` is `.pkit/capabilities/software-analysis/`, and `LD/` is `.pkit/capabilities/living-docs/`.
- **Read from open pull requests:** the writing rules `WRITE` as pushed on PR #1349 (`tech-docs/rule-sets/writing.md` at `57dc2bdb`), and the core actors on PR #1345 (`tech-docs/analysis/use-case-model/actors.md` at `fb960c45`). The analysis set that PR #1349 is splitting out was not pushed yet.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.

## The question

How does each analysis kind declare its required parts, so a script checks them and a template shows each with a hint and an example?

## The chain

The maintainer's hierarchy is *meta rules > rules > templates > content*. pkit has a concept for each level, and each level has two owners.

| Level | The methodology or the capability owns | The project owns |
|---|---|---|
| Meta rules: decisions | software-analysis DEC-001, and the core records such as COR-051 | its PRJ and ADR records |
| Rules: rule sets (COR-051) | a method rule set: artefacts of a kind follow one format | its own sets, such as project-kit's `WRITE`, for style |
| Templates: templates and declared structures | the shipped structure per kind, and the templates rendered from it | its additions to a kind's structure (part 4) |
| Content: artefacts | none | the analysis, under the internal root's `analysis/` (DEC-001 point 2) |

- **Each fact has one home:**
  - **The decision** names a kind's parts in words (`SA/decisions/DEC-001-software-analysis-discipline.md:26-32`).
  - **The declared structure** lists them as data: which parts, in what order, required or optional, with each part's hint and example.
  - **The template** is the structure rendered for a writer.
  - **A rule** makes a structure bind. The structure is its checkable part, as a schema is (COR-051 point 1), and no part of its content.
  - **A style rule** says how to write. A hint says what data goes in a part, and never repeats a style rule.
- **Each structure binds at the status of the rule in its own column.** The shipped structure binds at the method rule's status. A project's addition binds at its project rule's status (part 4).
- **A structure change is no rule-content change,** so it flags none of the rule's dependants. A tightened structure shows up as validation findings after an upgrade.
- **Today:** software-analysis has no method rule set, and declares a structure for front matter only (`SA/schemas/*.schema.json`). `WRITE` is proposed, scoped to `tech-docs/analysis/**` (`writing.md:4`).

## Today

### What `pkit analysis validate` checks

- Each artefact's own front-matter fields against its kind's schema (`SA/scripts/_lib/check.py:233-247`).
- A placeholder left in a field or the body, matched exactly against every placeholder ever shipped (`check.py:250-297`).
  - The list is append-only (`SA/scripts/_lib/placeholder.py:37-73`).
  - A test holds the list to the templates and the skill (`tests/test_software_analysis_templates.py:340-364`).
- A use case's and a journey's heading against its id and title (`check.py:324-360`).
- Ids, references, anchors, and the revalidation records' front matter (`check.py:158-193`).

### What it does not check

- **A body's parts.** A use case with no *Main path* passes. A placeholder catches a part left unfilled, not a part deleted.
- **Order.** Nothing checks that *Goal* comes before *Main path*.
- **Forms.** The stamp writes some of these, and nothing keeps any of them afterwards (`stamp.py:511-535`, `SA/scripts/_lib/revalidation.py:243-257`):
  - steps numbered, and variants lettered after a step, `1a.`
  - a journey's step lines against its `steps`
  - a record's outcome lines against its `outcomes`
- **An actor's or a term's section.** Only a placeholder in it is caught (`check.py:282-284`).
- **Hints and examples.** A placeholder is the only hint, and no template carries an example. Two templates hold an instruction line that stays in every finished artefact (`SA/templates/use-case.md:32`, `SA/templates/journey.md:32`).

### living-docs, for contrast

- Each page kind declares its structure once, as data (`LD/schemas/page-kinds.yaml:26-32`), with a schema (`LD/schemas/page-kinds.schema.json:34-78`).
- The validator reports a declared heading that a page lacks or carries out of order (`LD/scripts/_lib/formats.py:243-267`).
- RS-LDOC-004 must be accepted for any body to be checked. Under any other status nothing is checked (`LD/scripts/_lib/spaces.py:149`, `:568-632`).
- A structure is never read from a template's text, and a test holds each template to it (living-docs DEC-001 point 3, `LD/decisions/DEC-001-living-docs-discipline.md:57`).
- **Limits:** it reads headings only. A kind that a project adds declares no structure, and its pages are never failed (`LD/README.md:50`).

The analysis does not fit that reader as it stands. Its bodies use bold labels, such as `**Goal:**` (`use-case.md:23-36`). project-kit's writing rules make labels its house style (RS-WRITE-002, `writing.md:80-90`).

## Proposal

### 1. A declared structure per kind

**Recommended: a data file with a schema, as living-docs does.** `SA/schemas/artefact-kinds.yaml` declares each kind's structure.

- Its schema is a strict superset of `page-kinds.schema.json`.
- Its missing and out-of-order logic is that of `formats.departures`.
- So a later extraction to the backbone is a move, not a reconciliation.

| Where | For | Against |
|---|---|---|
| **A data file** (recommended) | One home for scripts. The shape living-docs already uses. | A template could drift from it. Rendering the template from it prevents that (part 2). |
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

**Custom content.** A writer may add labels and sections anywhere. The check judges only the declared elements: present, in order, not empty, and of their form. A project that wants its own labels checked declares them (part 4).

**Scope.** A document kind's structure covers its body. A collection kind's structure covers its entry's section. A withdrawn artefact is history, so a part required later never fails it.

- **The entry's extent is the backbone's.** COR-050 point 1 defines it, friction hashes exactly that text (`src/project_kit/friction_discovery.py:2299`, `:2396`), and each computation has one home (ADR-057 point 2).
- **software-analysis' own copy reads it differently** (`SA/scripts/_lib/markdown.py:74-85`). It would let a part pass the check outside the text friction treats as the entry.
- **So the artefacts document gives each entry's section span.** `pkit friction artefacts --json` gains the key, which raises no version (`friction_discovery.py:2428-2431`). software-analysis reads it, as it reads the rest of that document (ADR-057 point 1).

**The check.** `pkit analysis validate` reports an element that is missing, out of order, empty, or not of its form. The message gives the part's hint and example. The rule's status sets the severity (part 3).

**Where the reader lives.** software-analysis reads labels, part extents and forms. Four readers exist already:

- living-docs' heading reader (`LD/scripts/_lib/formats.py:188-218`)
- software-analysis' heading and section reader (`markdown.py:55-85`)
- the backbone's two, for rule sets (`src/project_kit/rule_sets.py:522`) and for collection entries (`friction_discovery.py:2396`)

| Option | For | Against |
|---|---|---|
| **software-analysis reads labels and forms, and the backbone gives the entry's extent** (recommended) | No new general reader in the core. One home for the entry. | Two readers of labels, once a second component reads them |
| The backbone reads headings, labels and extents now | One meaning of *section* and *label* | A reading command for one consumer, and a core record. The analysis' forms stay in the capability anyway. |
| software-analysis calls living-docs' reader | No copy | The capability works alone (DEC-001 point 10). |

**COR-007, applied.** This is the second case of a kind declaring its body structure as data. The variation is only now visible: labels, forms and collection entries. So it is a deliberate decision not to extract yet.

- **The trigger:** a second component that must read declared labels. That is living-docs shipping a page kind with labels, or letting a project add to a kind's structure.
- **What would move:** headings, labels, extents and the generic forms, as a backbone reading command. The analysis' own forms stay.
- **Where it is recorded:** in DEC-001's alternatives, as living-docs DEC-001 records its trigger for the `source` kind.

### 2. Templates with a hint and an example per part

**Recommended: the template is the declaration rendered, and each part's hint is its placeholder.**

- **Rendered.** The stamp renders the shipped structure plus the project's additions (part 4). The committed `SA/templates/<kind>.md` is made of:
  - the front matter, written by hand and held to the kind's schema, as today
  - the body, rendered from the declaration without additions, and held equal to it by a test
  - In living-docs a template may show more than its structure. Here it shows exactly the structure, and DEC-001 says so.
- **One part, as stamped:**

  ```markdown
  **Goal:** <!-- pkit:hint What the actor wants from this use case, in one sentence. Example: Export the report as a file. -->
  ```

- **The hint is the placeholder.** It stands where the content goes, as the angle-bracket hints of Cockburn's use-case template do ([Use Case Template](https://www.cs.otago.ac.nz/coursework/cosc461/uctempla.htm)).
  - The check refuses a part that still holds a hint, and a required part left empty once the hint is deleted.
  - A hint is one line. No reader of the analysis skips comments (`markdown.py:74-85`, `friction_discovery.py:2396`), so a line break in a hint could split a section.
  - The marker is matched outside code spans and fences, so an artefact may quote it. Its `pkit` is the methodology's literal, as the container key is (the lifecycle README, "The methodology's literals").
  - New templates hold no angle-bracket placeholders in their bodies. The append-only list stays for what was stamped before.
- **A hint also reaches a later editor.** The check's message for a missing or empty part gives the hint and its example. The skill's *Fill it* lists give way to "fill each part as its hint says" (`SA/skills/analysis-author/use-case.md:34-40`, `actor.md:30-33`).
- **A hint says what data goes there, and shows one example.** It names no style. The example is plain and written in no project's voice.
- **No hints in a revalidation record.** Its stamp writes every part from the command line (`revalidation.py:243-257`), so a hint would only be copied into every record.
- **The stamp's body generation is rewritten.** Today it copies template lines and rewrites some by pattern (`stamp.py:505`, `:114-115`). It renders from the declaration instead.

| Form of a hint | For | Against |
|---|---|---|
| **The hint as the placeholder** (recommended) | One mechanism. Read where the writer writes. Hidden when rendered. | A writer must delete the comment |
| A hint comment under an angle-bracket placeholder | Keeps today's placeholders | Two things to delete per part, and the placeholder list keeps growing |
| Hints only in check messages and the skill | Nothing to delete from an artefact | The first writer, often an agent, meets bare labels |
| The placeholder alone, as today | Nothing new | No room for an example. A long placeholder is hard to keep exact. |

### 3. The meta rule

**Recommended: a method rule set that the capability ships, with the format rule first, and a DEC-001 point behind it.**

- **The rule:** "An analysis artefact carries its kind's declared structure, and each kind has a template." It mirrors RS-LDOC-004 (`LD/rule-sets/ldoc.md:83-85`).
- **The set:** `SA/rule-sets/<name>.md`. Like `LDOC`, it has no scope and binds through the capability's check.
- **Its name is distinctive,** as `LDOC` is. A shipped name is reserved in every adopter, since names are unique among a project's rule sets (COR-051 point 3). Choose it beside the one PR #1349 picks for project-kit's analysis set.
- **Inheriting it is optional.** A project's set inherits it only to fill a point it offers. Then every newly accepted rule is a new major for that project to re-pin (COR-051 point 7).
- **Under a proposed status nothing is checked,** as in living-docs (`LD/scripts/_lib/spaces.py:149`). The same holds for a project's additions (part 4).
- **The decision:** DEC-001 gains a point like living-docs' *A kind's structure* (living-docs DEC-001 point 3). It says each kind's structure is data, its template is rendered from it, and it binds at its rule's status. DEC-001 cites no project's rule set.
- **What the set adds over a DEC-001 point alone:** a rule id the check's findings cite, a status the capability flips to turn the check on, and the pattern living-docs already uses. The gain is modest, and the alternative is fair.
- **Worth a core refinement later:** "a structure binds at the status of the rule it is the checkable part of" would stand in two capability decisions. A refinement of COR-051 point 1 could state it once.

### 4. What a project may add or narrow

**Recommended: a file of its own in the capability's project tier, `SA/project/structures.yaml`,** with a schema bound to it by its path (COR-023).

- **Why there.** The project tier is the project's, and sync never touches it (`SA/README.md:227`). So no shipped file is edited (core rule 1).
- **Why its own file.** A pointer to it from a rule may become an anchor, and an anchor sees any change to its file (COR-050 point 5). A key in `config.yaml` would flag it on every edit to the numbering setting.
- **Uninstalling** the capability removes the project tier (`SA/schemas/config.yaml:17-18`), as living-docs says of captured sources.

What a project may change:

- **Relabel a shipped element, and replace its hint and example,** keeping its id, its place and its form. This tightens nothing, so it needs no rule and binds at the method rule's status. A non-English project writes its own labels this way.
- **Tighten, naming the project rule that asks for it:**
  - add labels and sections, each placed `after` a named element, with its hint and example
  - make a shipped optional element required
  - close a kind's label list (`closed: true`), so an undeclared label is reported. RS-WRITE-002's "one list" needs this.
- **May not:** drop or relax a shipped required element, reorder shipped elements, invent a form, or add a kind. A new kind needs its own decision (DEC-001 point 11). COR-051 point 7 forbids relaxing an inherited rule. A structure is data, so here the check can refuse a relaxing entry outright.

How a tightening binds:

- **At the status of the rule it names.** Under a proposed rule nothing of it is checked, as for the method rule (part 3). So a settings file never tightens a check past the acceptance gate (core rule 2).
- **Only within that rule's scope.** The check reports a named rule whose set does not cover the analysis (COR-051 point 2).
- **Orphaned when the rule is superseded or withdrawn:** reported and not applied, as an orphaned fill is (`rule_sets.py:578`).
- **No core change.** Rules are artefacts with their fields in `pkit friction artefacts --json`, so the check reads a rule's status there.
- **Order across versions.** An addition follows the element it names. A later shipped element lands after its own anchor, so the two never trade places silently.

project-kit's own entries:

- **Its actor labels** name RS-WRITE-002, which is proposed. They are written once it is accepted.
- **One home for the list.** PR #1349's split is to give the analysis set a fill of RS-WRITE-002's label list. The pushed `writing.md` offers no such point yet. Once it does, the fill points at `structures.yaml` rather than copying the list.

| Alternative | Against |
|---|---|
| Project templates beside the shipped ones | Two shapes that drift, which the declaration exists to prevent |
| A project rule set that carries the structure | A structure is no part of a rule's content (part 1). |
| A `structures` key in `config.yaml` | Every edit to the file would flag a rule anchored to it. |

### 5. Templates follow the writing rules, and stay project-neutral

The conflict:

- #1351 asks that the stamped body text use "no semicolon and no sentence over 25 words". It also asks that "each template's opening section starts with one sentence that says what it holds".
- `WRITE` is project-kit's, and the templates ship to every adopter.

The resolution:

- **The stamp writes almost no prose that survives filling.** It writes labels and hints. The author's words replace the hints, and labels are not counted as sentences (RS-WRITE-005).
- **#1351's opening sentence, read per kind:**
  - A collection file's opening is the one sentence the stamp writes, once, when the file is created (`SA/templates/glossary.md:25`). After that it is the project's to reword.
  - A use case or a journey opens with its first part, *Goal* or *Starts*. That sentence is the author's, not the stamp's.
- **Shipped hints and examples meet a neutral floor:** short sentences and no semicolons. They carry none of project-kit's style, such as RS-WRITE-002's labels or RS-WRITE-012's first person (COR-014).
- **project-kit may hold its own templates to `WRITE`.** In its source repository the shipped trees are authored source (ADR-055 point 3), so `WRITE`'s scope there can reach them.
  - This reverses the usual ownership, a project rule over shipped content. It is recorded as a refinement of ADR-055 point 3, not left implicit in a scope.
  - A rule set's scope names artefacts (`.pkit/schemas/backbone/rule-set.schema.json:32`). The templates and the declaration are not artefacts, so `WRITE` says in one sentence that its scope reaches them.
  - It never reaches an adopter.
- **An adopter's rules bind what its authors write,** through its own rule sets' scopes.

### 6. The actors' layout (#1346)

**Recommended: one file per actor**, `use-case-model/actors/ACT-<slug>.md`, as use cases are.

- **Reads as one unit.** The needs sit in the front matter, about ten lines above the description. Today they sit up to 130 lines away (`actors.md:1-132` against `:134-232`).
- **The needs stay data.** The schema checks them, and the readers filler reads them from the artefacts document, as today.
- **An actor becomes a document kind,** headed `# ACT-<slug> — <name>`, and checked as a use case is. The collection code stays, for terms.
- **What else changes:**
  - DEC-001 points 2 and 3, and the place in `SA/package.yaml:62-64`
  - an `id` field in the actor's schema
  - the stamp, and the skill's actor sub-procedure
  - the readers filler, which now fails closed on any one unreadable actor file

**The criterion behind it: what a filler might read stays front-matter data.** Fillers read through the artefacts document, which carries fields and not bodies (ADR-057 point 1).

- The readers filler reads needs today, so needs stay data, and the files move to sit beside the prose.
- A term's definition is what a glossary point would carry, which living-docs DEC-001 already expects to take from "whatever component keeps one". So definitions stay data too, and the glossary stays a collection.
- The cost: a glossary read rendered shows each term's heading, not its definition. A generated view can show both later, never written twice.

| Alternative | Against |
|---|---|
| Declared body elements count as data: the needs become a labelled list in the actor's section, parsed for the filler | No file moves. But the filler would parse a body, which the artefacts document does not carry, and the schema could no longer check the needs. |
| Keep the collection, mirror the needs into the section, and check the two equal | A fact written twice by hand, which #1346 rules out |

**The move, and who pays for it.** Moving an artefact requires a revalidation in the same change (COR-050 point 3). That answer is a person's (core rule 20).

- **software-analysis looks unreleased.** Its 25 changesets are all in `.changes/unreleased/`. The last release, 1.149.0, is dated 2026-08-24 (`CHANGELOG.md:3`), before DEC-001 (2026-09-27). If no adopter has it, no installed state needs a migration (COR-010).
- **One mechanical cost stays.** Removing `SA/templates/actors.md` triggers `pkit migrations check-diff`. The file is kept, or a migration that does nothing says why.
- **project-kit's eight actors (PR #1345):**
  - created as files, if the layout lands first
  - moved, if #1345 merges first. Then the layout's pull request carries eight revalidations the maintainer writes. Nothing anchors to the actors yet.
- **If an adopter does have it,** a migration is the wrong tool. It runs after the sync, so a refusal halts a half-done upgrade (`src/project_kit/migrations.py:135-140`). It would also edit adopter-owned files.
- **A gap, whatever is decided.** The change check pairs a moved artefact with its old self only within one kind (`src/project_kit/friction_check.py:817-823`). An entry that becomes a document reads as removed and new, and a new artefact counts as revalidated (COR-050 point 6). So COR-050 point 3 goes unenforced for this move. It needs an issue of its own.

### 7. Which writing rules a script can check

| Rule | A script checks | Judgment keeps |
|---|---|---|
| RS-WRITE-005, 25 words | The count, as its *How* defines it (`writing.md:124-128`) | What is a quoted example of a broken rule |
| RS-WRITE-008, no semicolons | A semicolon outside code and quotes | Nothing |
| RS-WRITE-007, four sentences | The count per paragraph and list item | One topic |
| RS-WRITE-002, labels | Labels from the declared list, in order, with no pronoun | Whether a label fits |
| RS-WRITE-004, *Note* last | *Note* as the last label | What counts as side matter |
| RS-WRITE-001, the opening | A section that opens with a sentence, not a list | What matters most |
| RS-WRITE-012, needs and goals | One sentence, within 25 words | An imperative in the actor's voice |
| RS-WRITE-011, one term | A name that a term `replaces`, still in use, reported and never failed | Two words for one thing, and a common word that is no term |
| None | Control characters and list depth | Nothing |

RS-WRITE-003, 006, 009, 010 and 013 stay judgment.

Where a lint would live:

- **Not in this change.** The structure check comes first.
- **Next, a project-kit script** over `WRITE`'s scope, to learn which checks hold on real text. An existing prose linter such as Vale is the alternative. It has sentence-length and banned-token checks, at the cost of a toolchain outside Python.
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
- **The README** shows *Main path* inline (`SA/README.md:104`). It follows the template once the template is rendered.

**Journey**, its body, every element required:

- `# JRN-NNN — <title>`
- **Starts:**
- **Steps:**, of form `steps-match-front-matter`
- **Seams to watch:**, of form `seams-match-steps`
- **Done when:**

**Actor**, a document after part 6:

- `# ACT-<slug> — <name>`, required
- an opening, required: who this is
- **Comes:** and **Brings:**, optional, from today's placeholder (`SA/templates/actors.md:29`)

**Term**, its entry section, its definition staying in the front matter:

- `## TERM-<slug> — <name>`, required
- **Applies to:**, **Not:** and **Example:**, optional, from today's placeholder (`SA/templates/glossary.md:29`)

**Revalidation record**, its body, written whole by the stamp:

- `# <date> — <subject>`
- `## Outcomes`, of form `outcomes-match-front-matter`
- `## Gaps`: each gap with its resolution, or `None found.`
- **No style lint:** a record's words are a person's decision (RS-WRITE-013, core rule 20).

## Forces and costs

- **A breaking change, probably before any release.** A check that fails what it passed before breaks the capability, as living-docs DEC-001 point 3 says of pages. software-analysis is at 0.1.0 (`SA/package.yaml:5`) and looks unreleased (part 6).
- **Changesets.** software-analysis takes a `minor`, which its first release may absorb. The backbone takes a `minor` for the entry span, and software-analysis then requires that release.
- **Adopters:**
  - an artefact that lacks a required part is filled in
  - additions are optional, and relabelling needs no rule
- **Brownfield onboarding** (DEC-001 point 9). An agent derives candidates in bulk, and required parts raise that cost. The stamp's hints guide it, and each candidate fails until a person confirms and fills it, as point 9 wants anyway.
- **Placeholders.** Body placeholders retire for new artefacts. The append-only list stays for old ones.
- **What stays LLM judgment:**
  - whether the content is true, and whether a goal is one user story
  - whether a hint was followed in spirit
  - the writing rules marked judgment in part 7
- **Less LLM use.** The script runs first, so a reviewer reads only artefacts that have their shape.

## Slicing

1. **Plain stamped text (#1351),** alone: reword the surviving sentences, and append the old placeholders to the list.
2. **Decision:** DEC-001 gains the structure point, the data criterion, the actors' layout in points 2 and 3, and the extraction trigger. The maintainer accepts it.
3. **The entry's span** in the backbone's artefacts document.
4. **One file per actor (#1346):** the place, the schema, the stamp, the check, the readers filler and the skill. project-kit's actors are created as files, or moved with eight revalidations.
5. **Structure check:** the declaration and its schema, the method rule set, labels and extents, and `pkit analysis validate` checking bodies.
6. **Forms:** numbered steps, lettered variants, a journey's steps and seams, and a record's outcomes.
7. **Rendered templates:** hints as placeholders, the stamp rendering from the declaration, the skill's *Fill it* lists retired, and the ADR-055 refinement for `WRITE` over the templates.
8. **Project additions:** `structures.yaml` and its binding. project-kit's actor labels follow once RS-WRITE-002 is accepted.
9. **Later:** project-kit's writing lint, and the reader's extraction when its trigger fires.

Found on the way, each an issue of its own:

- The change check does not pair an entry with the document it becomes (part 6).
- The backbone reads a rule-set file two ways: its rule-set reader skips fenced code, and its entry reader does not (`rule_sets.py:522-539`, `friction_discovery.py:2396`).

## Open questions for the maintainer

1. **Is software-analysis installed anywhere outside project-kit?** Recommended: treat it as unreleased, ship no actor migration, and let PR #1345 merge when ready. If it is installed, the move needs a lifecycle decision, not a migration.
2. **What may a tool read from a body?** Recommended: nothing a filler reads. Needs and definitions stay front-matter data, so actors move to one file each and terms stay in the glossary. The alternative counts declared body elements as data, so the needs become a labelled list and nothing moves.
3. **How does a hint reach the writer?** Recommended: the hint is the placeholder, a one-line marked comment, and the check's messages repeat it. The alternative keeps hints out of artefacts, in check messages and the skill only.
4. **Under a proposed rule, is anything reported?** Recommended: no, as in living-docs, for the method rule and a project's additions alike. The alternative reports a preview in both capabilities, which refines living-docs DEC-001 point 3.

## Review

The critic and then the architect reviewed this note. Each blocking finding and gap, with its answer.

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
| Counter-alternatives: the hint as the placeholder, hints in check messages, #1351 first, an existing prose linter | All adopted (parts 2 and 7, slice 1) |
| Smaller citations | Corrected or removed |

**The architect, on the second draft:**

| Finding | Answer |
|---|---|
| Concern: a collection entry's extent would be computed outside the backbone, which owns it | Adopted. The artefacts document gives the span (part 1, slice 3). |
| Concern: additions reported under a proposed rule, where living-docs checks nothing | Adopted: nothing is checked under a proposed rule (parts 3 and 4). A preview is question 4's alternative. |
| Concern: the actor migration is likely unneeded, and would fail mid-upgrade and edit adopter files | Adopted. Release state is question 1, and the gap in move pairing is its own issue (part 6). |
| Data or prose decided two ways for actors and terms | One criterion, what a filler reads, so definitions stay data (part 6, question 2) |
| The chain mixed a rule's level with its owner | Two axes (the chain) |
| Part 4: which entries need a rule, scope, superseded rules | Relabelling needs none. Scope and orphans are checked (part 4). |
| `structures` in `config.yaml` | A file of its own (part 4) |
| The extraction trigger mis-stated | A component that must read declared labels. Generic forms move with it (part 1). |
| `WRITE` over shipped templates crosses an ownership line | Recorded as an ADR-055 refinement, with a neutral floor for adopters (part 5) |
| Custom labels inside a part with a form | List forms judge only list items (part 1). |
| The method set's scope and name | No scope, and a distinctive name (part 3) |
