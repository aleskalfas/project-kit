---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-05
---

# Analysis artefacts follow a declared structure per kind

A design draft for #1352. It folds in #1346 (an actor's needs beside its description) and #1351 (the text the stamp writes).

- **Paths:** `SA/` is `.pkit/capabilities/software-analysis/`, and `LD/` is `.pkit/capabilities/living-docs/`.
- **Read from open pull requests:** the writing rules `WRITE` as pushed on PR #1349 (`tech-docs/rule-sets/writing.md` at `57dc2bdb`), and the core actors on PR #1345 (`tech-docs/analysis/use-case-model/actors.md` at `fb960c45`). The analysis set that PR #1349 is splitting out was not pushed yet.
- **Reviewed:** by the critic. Its findings and the answers are in "Review", at the end.

## The question

How does each analysis kind declare its required parts, so a script checks them and a template shows each with a hint and an example?

## The chain

The maintainer's hierarchy is *meta rules > rules > templates > content*. pkit already has a concept for each level.

| Level | pkit concept | Owns | Today, for the analysis |
|---|---|---|---|
| Meta rules | Decisions, and the capability's method rule that artefacts of a kind follow one format | Which kinds exist and what each must say, in words. That the structure binds. | DEC-001 point 1 names each kind's parts (`SA/decisions/DEC-001-software-analysis-discipline.md:26-32`). No method rule. |
| Rules | The project's rule sets (COR-051) | How to write: style, gated by status | project-kit's `WRITE`, proposed, scoped to `tech-docs/analysis/**` (`writing.md:4`) |
| Templates | Templates and declared structures | The template shows the shape. The structure is the checkable part (COR-051 point 1). | Templates in `SA/templates/`. A structure for front matter only, in `SA/schemas/*.schema.json` |
| Content | Artefacts | What the author writes | Under the internal root's `analysis/` (DEC-001 point 2) |

Scripts work across the levels. The stamp writes an artefact from its template (`SA/scripts/_lib/stamp.py:491-508`), and the check reads the artefact.

Each fact gets one home:

- **The decision** names a kind's parts in words.
- **The declared structure** lists them as data: which parts, in what order, required or optional, with each part's hint and example.
- **The template** is the structure rendered for a writer.
- **The method rule** makes the structure bind. Its status sets the check's severity, as RS-LDOC-004's does for pages.
- **A style rule** says how to write. A hint says what data goes in a part, and never repeats a style rule.

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
- The validator reports a declared heading that a page lacks or carries out of order (`LD/scripts/_lib/formats.py:243-267`). RS-LDOC-004's status sets the severity (`LD/scripts/_lib/spaces.py:568-632`).
- A structure is never read from a template's text, and a test holds each template to it (living-docs DEC-001 point 3, `LD/decisions/DEC-001-living-docs-discipline.md:57`).
- **Limits:** it reads headings only. A kind that a project adds declares no structure, and its pages are never failed (`LD/README.md:50`).

The analysis does not fit that reader as it stands. Its bodies use bold labels, such as `**Goal:**` (`use-case.md:23-36`). project-kit's writing rules make labels its house style (RS-WRITE-002, `writing.md:80-90`).

## Proposal

### 1. A declared structure per kind

**Recommended: a data file with a schema, as living-docs does.** `SA/schemas/artefact-kinds.yaml` declares each kind's structure, in a shape that extends `page-kinds.yaml`.

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
- **`form`:** a check on a part's content, from a closed list that software-analysis implements:
  - `sentence`: one sentence.
  - `numbered-steps`: each item opens with a number, and no number repeats. Numbers need not run in sequence, since steps are append-only (DEC-001 point 3).
  - `variants`: each item opens with a step's number and a letter, `2a.`, naming a step of *Main path*. The part may read `None.` instead.
  - `steps-match-front-matter`, `seams-match-steps` and `outcomes-match-front-matter`: a journey's and a record's lines against their front matter.

**Custom content.** A writer may add labels and sections anywhere. The check judges only the declared elements: present, in order, not empty, and of their form. A project that wants its own labels checked declares them (part 4).

**Scope.** A document kind's structure covers its body. A collection kind's structure covers the entry's section, `## <id> — <name>`, as the core reads it (`src/project_kit/friction_discovery.py:2396`). A withdrawn artefact is history, so a part required later never fails it.

**The check.** `pkit analysis validate` reports an element that is missing, out of order, empty, or not of its form. The message gives the part's hint and example. The method rule's status sets the severity (part 3).

**Where the reader lives.** Four Markdown section readers exist already:

- living-docs' heading reader (`LD/scripts/_lib/formats.py:188-218`)
- software-analysis' heading and section reader (`SA/scripts/_lib/markdown.py:55-85`)
- the backbone's two, for rule sets (`src/project_kit/rule_sets.py:522`) and for collection entries (`friction_discovery.py:2396`)

| Option | For | Against |
|---|---|---|
| **software-analysis extends its own reader** with labels and part extents (recommended) | No new reader, and no core change. Labels and forms have one consumer today, and COR-007 waits for a second. | Two readers of labels once living-docs needs them |
| The backbone reads headings, labels and extents, with a schema and a query command | One meaning of *section* and *label* for the methodology | The backbone grows for one consumer, and needs a core record. The forms stay software-analysis' all the same. |
| software-analysis calls living-docs' reader | No copy | The capability works alone (DEC-001 point 10). |

**The trigger to extract.** `WRITE` plans to reach the documentation pages next (`writing.md:58`). Pages would then carry labels, and living-docs would need the same reader. That is the second consumer. The generic part — headings, labels and extents — then moves to the backbone, under a core record. The forms never move: they are this capability's semantics.

### 2. Templates with a hint and an example per part

**Recommended: the template is the declaration rendered, and each part's hint is its placeholder.**

- **Rendered.** The stamp renders the shipped structure plus the project's additions (part 4). The committed `SA/templates/<kind>.md` is made of:
  - the front matter, written by hand and held to the kind's schema, as today
  - the body, rendered from the declaration without additions, and held equal to it by a test
- **One part, as stamped:**

  ```markdown
  **Goal:** <!-- pkit:hint What the actor wants from this use case, in one sentence. Example: Export the report as a file. -->
  ```

- **The hint is the placeholder.** It stands where the content goes, as the angle-bracket hints of Cockburn's use-case template do ([Use Case Template](https://www.cs.otago.ac.nz/coursework/cosc461/uctempla.htm)).
  - The check refuses a part that still holds a hint. It refuses a required part left empty after the hint is deleted.
  - A hint is one line. No reader of the analysis skips comments (`markdown.py:74-85`, `friction_discovery.py:2396`), so a line break in a hint could split a section.
  - The marker `<!-- pkit:hint` is matched outside code spans and fences, so an artefact may quote it.
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
- **The set:** `SA/rule-sets/<name>.md`. Its scope is the analysis places, so it binds through the capability's check, inherited or not. Its name is chosen now, beside the one PR #1349 picks for project-kit's analysis set, since names are unique among rule sets (COR-051 point 3).
- **Inheriting it is optional.** A project's set inherits it only to fill a point it offers. Then every newly accepted rule is a new major for that project to re-pin (COR-051 point 7).
- **The decision:** DEC-001 gains a point like living-docs' *A kind's structure* (living-docs DEC-001 point 3). It says that each kind's structure is data, and that its template is rendered from it.
- **What the set adds over a DEC-001 point alone:** a rule id the check's findings cite, a status the capability flips to turn the check on, and the pattern living-docs already uses. The gain is modest, and the alternative is fair.

### 4. What a project may add or narrow

**Recommended: a `structures` key in the capability's settings file, `SA/project/config.yaml`.** The file is the project's, and sync never touches it (`SA/README.md:227`). So no shipped file is edited (core rule 1). The key is not `kinds`, a word anchors already use.

- **May:**
  - add labels and sections to a kind, each placed `after` a named element, with its hint and example
  - make a shipped optional element required
  - relabel a shipped element, and replace its hint and example, keeping its id, its place and its form
  - close a kind's label list (`closed: true`), so an undeclared label is reported. RS-WRITE-002's "one list" needs this.
- **May not:** drop or relax a shipped required element, reorder shipped elements, invent a form, or add a kind. A new kind needs its own decision (DEC-001 point 11). COR-051 point 7 forbids relaxing an inherited rule. A structure is data, so here the check can refuse a relaxing entry outright.
- **An addition binds at its own rule's status.** Each addition names the project rule that asks for it, and the check takes that rule's status.
  - project-kit's actor labels name RS-WRITE-002, which is proposed. They are reported, never failed, until it is accepted.
  - Without this, a proposed rule's content would fail validation through a settings file, past the acceptance gate (core rule 2).
- **One home for the labels.** PR #1349's split is to give the analysis set a fill of RS-WRITE-002's label list. The pushed `writing.md` offers no such point yet. Once it does, the fill points at the `structures` entry rather than copying the list.
- **Order across versions.** An addition follows the element it names. A later shipped element lands after its own anchor, so the two never trade places silently.

| Alternative | Against |
|---|---|
| Project templates beside the shipped ones | Two shapes that drift, which the declaration exists to prevent |
| A project rule set that carries the structure | A structure is no part of a rule's content (part 1). |
| A file of its own in the project tier | Workable. A key in the existing settings file reuses that file's schema and its check. |

### 5. Templates follow the writing rules, and stay project-neutral

The conflict:

- #1351 asks that the stamped body text use "no semicolon and no sentence over 25 words". It also asks that "each template's opening section starts with one sentence that says what it holds".
- `WRITE` is project-kit's, and the templates ship to every adopter.

The resolution:

- **The stamp writes almost no prose that survives filling.** It writes labels and hints. The author's words replace the hints, and labels are not counted as sentences (RS-WRITE-005).
- **#1351's opening sentence, read per kind:**
  - A collection file's opening is the one sentence the stamp writes, once, when the file is created (`SA/templates/glossary.md:25`). After that it is the project's to reword.
  - A use case or a journey opens with its first part, *Goal* or *Starts*. That sentence is the author's, not the stamp's.
- **project-kit holds its templates to `WRITE`.** In its source repository the shipped trees are authored source (`LD/README.md:136`). So `WRITE`'s scope there can add the declaration and the templates. The maintainer's "templates are written to the writing rules" then has its home, and binds when `WRITE` is accepted.
- **Adopters receive plain text** and are bound by none of `WRITE`. Their own rules bind what their authors write, through their own rule sets' scopes.

### 6. The actors' layout (#1346)

**Recommended: one file per actor**, `use-case-model/actors/ACT-<slug>.md`, as use cases are.

- **Reads as one unit.** The needs sit in the front matter, about ten lines above the description. Today they sit up to 130 lines away (`actors.md:1-132` against `:134-232`).
- **The needs stay data.** The schema checks them, and the readers filler reads them as today.
- **An actor becomes a document kind,** headed `# ACT-<slug> — <name>`, and checked as a use case is. The collection code stays, for terms.
- **The cost of a move.** Moving an entry between files requires a revalidation in the same change (COR-050 point 3). That answer is a person's (core rule 20), so a migration cannot write it.
  - **project-kit avoids it:** the layout lands before PR #1345 merges, so the eight core actors are created as files and never move.
  - **An adopter's migration** moves the files with no hand edits, and refuses while any actor has unanswered friction. A moved file is new in its change, so it would hide that friction (COR-050 point 6). The upgrade's pull request then carries one revalidation per actor, which a person answers.
- **What else changes:**
  - DEC-001 points 2 and 3, and the place in `SA/package.yaml:62-64`
  - an `id` field in the actor's schema
  - the stamp, and the skill's actor sub-procedure
  - the readers filler, which now fails closed on any one unreadable actor file

| Alternative | Against |
|---|---|
| Keep the collection, mirror the needs into the section, and check the two equal | A fact written twice by hand, which #1346 rules out |
| Keep the collection, with the needs as a labelled list in the section, parsed for the filler | No move, and no revalidations. But data a tool reads would be parsed out of prose, which COR-051 rejects for rule sets ("Markers in the prose"). The schema could no longer check it. |

**The glossary stays a collection, and a definition moves into its section.** A glossary is read as one list, and nothing but the schema reads `definition` (`SA/schemas/term.schema.json:17-20`).

- The definition becomes the section's opening sentence, of form `sentence`. It then reads where it stands, and no entry moves.
- The cost: the term's schema drops `definition`, and the content change flags whatever anchors to a term.

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

**Term**, its entry section:

- `## TERM-<slug> — <name>`, required
- an opening of form `sentence`, required: the definition (part 6)
- **Applies to:**, **Not:** and **Example:**, optional, from today's placeholder (`SA/templates/glossary.md:29`)

**Revalidation record**, its body, written whole by the stamp:

- `# <date> — <subject>`
- `## Outcomes`, of form `outcomes-match-front-matter`
- `## Gaps`: each gap with its resolution, or `None found.`
- **No style lint:** a record's words are a person's decision (RS-WRITE-013, core rule 20).

## Forces and costs

- **A breaking change.** A check that fails what it passed before breaks the capability, as living-docs DEC-001 point 3 says of pages. software-analysis is at 0.1.0 (`SA/package.yaml:5`), and project-kit's own pilot analysis was removed (`6107ae77`). So the method rule can ship accepted, and a departure fails from the first release.
- **Migration:** the actors' split, with its revalidations (part 6), and the terms' definitions moved into their sections.
- **Adopters:**
  - an artefact that lacks a required part is filled in, or the capability is not upgraded yet
  - an adopter with actors upgrades through a pull request with one revalidation per actor
  - an adopter answers for what anchors to a moved actor or a changed term
  - additions are optional
- **Brownfield onboarding** (DEC-001 point 9). An agent derives candidates in bulk, and required parts raise that cost. The stamp's hints guide it, and each candidate fails until a person confirms and fills it, as point 9 wants anyway.
- **Friction.** A structure change is no rule-content change (part 1), so it flags none of the rule's dependants.
- **Placeholders.** Body placeholders retire for new artefacts. The append-only list stays for old ones.
- **What stays LLM judgment:**
  - whether the content is true, and whether a goal is one user story
  - whether a hint was followed in spirit
  - the writing rules marked judgment in part 7
- **Less LLM use.** The script runs first, so a reviewer reads only artefacts that have their shape.

## Slicing

1. **Plain stamped text (#1351),** alone: reword the surviving sentences, and append the old placeholders to the list.
2. **Decision:** DEC-001 gains the structure point, and points 2 and 3 take the actors' layout. The maintainer accepts it.
3. **One file per actor (#1346),** before PR #1345 merges: the place, the schema, the stamp, the check, the readers filler, the skill and a migration.
4. **Structure check:** the declaration and its schema, the method rule set, labels and extents in the reader, and `pkit analysis validate` checking bodies.
5. **Forms:** numbered steps, lettered variants, a journey's steps and seams, a record's outcomes, and a term's one-sentence definition.
6. **Rendered templates:** hints as placeholders, the stamp rendering from the declaration, the skill's *Fill it* lists retired, and `WRITE`'s scope in project-kit extended to the templates.
7. **Project additions:** the `structures` key, each addition bound at its rule's status, and project-kit's actor labels.
8. **Later:** project-kit's writing lint. The generic reader moves to the backbone when living-docs needs labels.

## Open questions for the maintainer

1. **Where does the structure reader live?** Recommended: software-analysis extends its own, and the generic part moves to the backbone when living-docs needs labels. The alternative is the backbone now, under a core record.
2. **How does a hint reach the writer?** Recommended: the hint is the placeholder, a one-line marked comment, and the check's messages repeat it. The alternative keeps hints out of artefacts, in check messages and the skill only.
3. **One file per actor?** Recommended: yes, landed before PR #1345 merges, with a migration that refuses while friction is open. The alternative keeps the collection and parses the needs from a labelled list, so nothing moves.
4. **Whose status binds a project's additions?** Recommended: the project rule each addition names, so a proposed rule never fails a check. The alternative is the method rule's status for every addition.

## Review

The critic reviewed the first draft. Each red flag and gap, with its answer:

| Finding | Answer |
|---|---|
| Red flag: moving the actors needs a revalidation per actor, which a migration cannot write (COR-050 point 3) | Confirmed. Part 6 now lands the layout before PR #1345, has the migration refuse while friction is open, and leaves the revalidations to a person. |
| Red flag: project labels bound at the method rule's status would enforce proposed RS-WRITE-002 | Confirmed. Each addition binds at its own rule's status (part 4), and that is now question 4. |
| Red flag: analysis forms would move into the backbone | Confirmed. The forms stay in software-analysis, and the reader is extracted only on a second consumer (part 1). |
| The label grammar breaks on `**1a.**` and seam lines | Only declared labels delimit, and a part's extent is defined (part 1). |
| `numbered-steps` cannot mean sequential | It means numbered and unique (part 1). |
| A hint marker can be quoted, and a multi-line hint can split a section | One-line hints, matched outside code (part 2). The living-docs citation is gone. |
| The stamp's rewriting is not costed | Part 2 says the body generation is rewritten, and records carry no hints. |
| What the committed template is made of | Front matter by hand, body rendered (part 2). |
| A shipped example in project-kit's voice, and labels no project can rename | Examples are plain, and a project may relabel and replace hints (part 4). |
| Part 4 underspecified | `after`, `closed`, no new forms, and the key renamed `structures` (part 4). |
| A third home for each part's description | The skill's *Fill it* lists give way to the hints (part 2). |
| Withdrawn artefacts | A part required later never fails one (part 1). |
| Brownfield onboarding | Added to forces and costs. |
| DEC-001 point 3 and the filler | Listed in part 6. |
| Meta rules at the wrong level of the chain | The table now puts the method rule beside the decisions. |
| #1351's opening-sentence criterion | Quoted and read per kind (part 5). |
| The glossary deferred to #1346 circularly | Decided: a definition moves into its section (part 6). |
| The "plain floor" had no home | project-kit's `WRITE` scope covers the templates instead (part 5). |
| Hints in check messages and the skill (counter-alternative) | Adopted beside the hint in the artefact (part 2). |
| A hint that replaces the placeholder (counter-alternative) | Adopted as the recommended form (part 2). |
| Ship #1351 first, alone (counter-alternative) | Slice 1. |
| An existing prose linter (counter-alternative) | Named as the lint's alternative (part 7). |
| Smaller citations: reader count, COR-051 point 7, RUP's trigger, `actors.md:29`, the COR-013 analogy | Corrected or removed. |
