---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-05
---

# Analysis artefacts follow a declared structure per kind

A design draft for #1352. It folds in #1346 (an actor's needs beside its description) and #1351 (the text the stamp writes).

- **Paths:** `SA/` is `.pkit/capabilities/software-analysis/`, and `LD/` is `.pkit/capabilities/living-docs/`.
- **Read from open pull requests:** the writing rules `WRITE` as pushed on PR #1349 (`tech-docs/rule-sets/writing.md` at `57dc2bdb`), and the core actors on PR #1345 (`tech-docs/analysis/use-case-model/actors.md` at `fb960c45`). The analysis set that PR #1349 is splitting out was not pushed yet.

## The question

How does each analysis kind declare its required parts, so a script checks them and a template shows each with a hint and an example?

## The chain

The maintainer's hierarchy is *meta rules > rules > templates > content*. pkit already has a concept for each level.

| Level | pkit concept | Owns | Today, for the analysis |
|---|---|---|---|
| Meta rules | Decisions: the core records and the capability's DEC-001 | Which kinds exist and what each must say, in words. How rules work (COR-051). | DEC-001 point 1 names each kind's parts (`SA/decisions/DEC-001-software-analysis-discipline.md:26-32`) |
| Rules | Rule sets (COR-051): a method set a capability ships, and the project's own sets | Binding statements, gated by status | No method set. project-kit's `WRITE` is proposed, scoped to `tech-docs/analysis/**` (`writing.md:4`) |
| Templates | Templates and declared structures | The template shows the shape. The structure is the checkable part (COR-051 point 1). | Templates in `SA/templates/`. A structure for front matter only, in `SA/schemas/*.schema.json` |
| Content | Artefacts | What the author writes | Under the internal root's `analysis/` (DEC-001 point 2) |

Scripts work across the levels. The stamp writes an artefact from its template (`SA/scripts/_lib/stamp.py:491-508`), and the check reads the artefact.

Each fact gets one home:

- **The decision** names a kind's parts in words.
- **The declared structure** lists them as data: which parts, in what order, required or optional.
- **The template** is the structure rendered for a writer, with a hint and an example per part.
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
- **Forms.** The stamp writes these, and nothing keeps them so afterwards (`stamp.py:511-535`, `SA/scripts/_lib/revalidation.py:243-257`):
  - steps numbered `1.`, and variants lettered after a step, `1a.`
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

**The grammar.** A structure is a list of elements, checked in that order unless the kind sets `ordered: false`.

- **Element types:**
  - `heading`: a level and, where fixed, its text, as in living-docs.
  - `label`: a bold label that opens a paragraph or a top-level list item, such as `**Goal:**`.
  - `opening`: a paragraph before the first label, such as an actor's "who this is".
- **`required`:** true unless set false. An optional element is checked only when present.
- **`form`:** an optional check on what follows the element, from a closed list the code implements. A first list is `sentence`, `numbered-steps`, `variants`, `steps-match-front-matter`, `seams-match-steps` and `outcomes-match-front-matter`.
- **`hint` and `example`:** for the template (part 2). The check ignores them.

**Custom content.** A writer may add labels and sections anywhere. The check judges only the declared elements: present, in order, and of their form. A project that wants its own labels checked declares them (part 4).

**Scope.** A document kind's structure covers its body. A collection kind's structure covers the entry's section, `## <id> — <name>`, as the core reads it (`src/project_kit/friction_discovery.py:2396`).

**The check.** `pkit analysis validate` reports an element that is missing, out of order, or not of its form. The method rule's status sets the severity (part 3).

**Where the reader lives.** Three Markdown section readers exist already:

- living-docs' heading reader (`LD/scripts/_lib/formats.py:188-218`)
- software-analysis' heading and section reader (`SA/scripts/_lib/markdown.py:55-85`)
- the backbone's, for rule sets and collection entries (`src/project_kit/rule_sets.py:522`, `friction_discovery.py:2396`)

| Option | For | Against |
|---|---|---|
| **The backbone reads structure** (recommended): a declaration schema and a query command both capabilities call, as they call `pkit friction artefacts` | One meaning of *section* and *label* for the methodology. This is the second consumer, the recurrence COR-007 waits for. | The backbone grows, and a core record has to say so. |
| software-analysis copies living-docs' reader and adds labels | No backbone change | A fourth reader to keep in step |
| software-analysis calls living-docs' reader | No copy | The capability works alone (DEC-001 point 10). |

### 2. Templates with a hint and an example per part

**Recommended: the template is the declaration rendered, and each element carries its hint as a marked comment.**

- **Rendered.** The stamp renders the shipped structure plus the project's additions (part 4). The committed `SA/templates/<kind>.md` is the render without additions, and a test holds it equal. So a project's labels reach every new artefact, each with its hint. This mirrors how agent templates take project values at deploy time (COR-013 rule 5).
- **One element, as stamped:**

  ```markdown
  **Goal:** <the goal>
  <!-- pkit:hint What the actor wants from this use case, as one user story. Example: Export the report as a file I can send. -->
  ```

- **Kept out of the finished artefact.** The check refuses a placeholder still in place, as today. It also refuses any comment that opens `<!-- pkit:hint`.
  - The marker is the methodology's own token, so a match by shape never catches an author's words.
  - Inline placeholders stay matched exactly, against the append-only list.
  - Readers that skip comments never take a hint for a heading (`LD/scripts/_lib/formats.py:19-24`).
- **A hint says what data goes there, and shows one example.** It names no style, since style is the project's rules.
- **Precedent.** Cockburn's use-case template gives each field a hint in angle brackets ([Use Case Template](https://www.cs.otago.ac.nz/coursework/cosc461/uctempla.htm)). Its name field asks for "<the name should be the goal as a short active verb phrase>".

| Form of a hint | For | Against |
|---|---|---|
| **A marked comment under the element** (recommended) | Read where the writer writes. Hidden when rendered. Refused when left. | One more line per element to delete |
| The placeholder alone, as today | Nothing new | No room for an example. A long placeholder is hard to keep exact. |
| Hints in the declaration only, printed by the stamp | Never in an artefact | An agent that fills the file later never sees them |
| Hints in the skill | Agents read the skill already | A second home for each part's description |

### 3. The meta rule

**Recommended: a method rule set that the capability ships, with the format rule first, and a DEC-001 point behind it.**

- **The rule:** "An analysis artefact carries its kind's declared structure, and each kind has a template." It mirrors RS-LDOC-004 (`LD/rule-sets/ldoc.md:83-85`).
- **The set:** `SA/rule-sets/<name>.md`, its name unique among rule sets (COR-051 point 3). A project's analysis set inherits it, pinned to its major (COR-051 point 7).
- **The decision:** DEC-001 gains a point like living-docs' *A kind's structure* (living-docs DEC-001 point 3). The point says that each kind's structure is data, and that its template is rendered from it.
- **Alternative, a DEC-001 point alone:** no status would gate the severity, and a project's set would have nothing to inherit.

### 4. What a project may add or narrow

**Recommended: a `kinds` key in the capability's settings file, `SA/project/config.yaml`.** The file is the project's, and sync never touches it (`SA/README.md:227`). So no shipped file is edited (core rule 1).

- **May:**
  - add labels and sections to a kind, each with its place in the order, its hint and its example
  - make a shipped optional element required
  - declare its label list for a kind, such as project-kit's actor labels (`actors.md:142-231`, RS-WRITE-002)
- **May not:** drop or relax a shipped required element, reorder shipped elements, or add a kind. A new kind needs its own decision (DEC-001 point 11). The check refuses a relaxing entry, as COR-051 point 7 refuses a relaxed rule.
- **One home for the labels.** The analysis set that PR #1349 is splitting out fills `RS-WRITE-002#labels`. That fill points at the project's `kinds` entry rather than copying the list.

| Alternative | Against |
|---|---|
| Project templates beside the shipped ones | Two shapes that drift. The stamp's step and seam rewriting assumes one shape (`stamp.py:511-535`). |
| A project rule set that carries the structure | A structure is no part of a rule's content (part 1). |
| A file of its own in the project tier | Workable. A key in the existing settings file reuses that file's schema and its check. |

### 5. Templates follow the writing rules, and stay project-neutral

The conflict:

- #1351 asks that the stamped text pass `WRITE`, which forbids semicolons (RS-WRITE-008).
- `WRITE` is project-kit's, and the templates ship to every adopter.

The resolution:

- **The stamp writes almost no prose that survives filling.** It writes labels, placeholders and hints. The author's words replace or remove all but the labels, and labels are not counted as sentences (RS-WRITE-005).
- **One sentence survives, at most.** Only a collection file's opening survives, written once when the file is created (`SA/templates/glossary.md:25`). After that the file is the project's to reword.
- **A plain floor for shipped text.** No sentence over 25 words, no semicolon, and each part opening with one sentence: #1351's bar. A project-kit test holds the templates, hints and examples to it. `WRITE`'s scope never reaches `SA/`.
- **The project's rules bind what the author writes,** through its own rule set's scope.

### 6. The actors' layout (#1346)

**Recommended: one file per actor**, `use-case-model/actors/ACT-<slug>.md`, as use cases are.

- **Reads as one unit.** The needs sit in the front matter, about ten lines above the description. Today they sit up to 130 lines away (`actors.md:1-132` against `:134-232`).
- **Fits the check.** An actor becomes a document kind, headed `# ACT-<slug> — <name>`, and is checked as a use case is.
- **Simpler stamp.** No sorted insertion into a shared file (`stamp.py:538-565`), and no conflict between neighbouring ids.
- **Costs.** DEC-001 point 2 changes, the place in `SA/package.yaml:62-64` becomes a folder, and a migration splits existing files.

| Alternative | Against |
|---|---|
| Keep the collection, mirror the needs into the section, and check the two equal | A fact written twice by hand, which #1346 rules out |
| Keep the collection, with the needs only in the body | The needs leave the front matter, where the schema checks them and the readers filler reads them |

**The glossary stays a collection.** A glossary is read as one list, and a definition is one sentence. A term's section may stay empty (RS-WRITE-001). Whether a definition should sit beside its section is for #1346 to settle with the actors.

### 7. Which writing rules a script can check

| Rule | A script checks | Judgment keeps |
|---|---|---|
| RS-WRITE-005, 25 words | The count, as its *How* defines it (`writing.md:124-128`) | Nothing |
| RS-WRITE-008, no semicolons | A semicolon outside code and quotes | Nothing |
| RS-WRITE-007, four sentences | The count per paragraph and list item | One topic |
| RS-WRITE-002, labels | Labels from the declared list, in order, with no pronoun | Whether a label fits |
| RS-WRITE-004, *Note* last | *Note* as the last label | What counts as side matter |
| RS-WRITE-001, the opening | A section that opens with a sentence, not a list | What matters most |
| RS-WRITE-012, needs and goals | One sentence, within 25 words | An imperative in the actor's voice |
| RS-WRITE-011, one term | A name that a term `replaces`, still in use | Two words for one thing |
| None | Control characters and list depth | Nothing |

RS-WRITE-003, 006, 009, 010 and 013 stay judgment.

Where a lint would live:

- **Not in this change.** The structure check comes first.
- **Next, a project-kit script** over `WRITE`'s scope, to learn which checks hold on real text.
- **Later, the backbone.** A rule could name a mechanical check from a list the backbone ships, with the project's thresholds. That needs a COR-051 amendment, so it waits for a second rule set that wants it (COR-007).
- **Not software-analysis.** `WRITE` is a project's set, and the capability ships no project's style.

### 8. The parts of each kind, a first cut

Grounded in DEC-001 point 1 and today's templates. Labels keep today's wording.

**Use case**, its body:

| Element | Required | Form | DEC-001 point 1 | Cockburn | RUP |
|---|---|---|---|---|---|
| `# UC-NNN — <title>` | yes | heading | its goal, in a few words | Use case | use-case name |
| **Goal:** | yes | sentence | "one actor's goal" | Goal in context | brief description |
| **Starts when:** | yes | none | "when it starts" | Trigger | preconditions |
| **Main path:** | yes | numbered-steps | "the main path" | Main success scenario | basic flow |
| **Variants:** | yes, `None.` allowed | variants | "variants" | Extensions, numbered `3a` | alternative flows |
| **Done when:** | yes | none | "when it is done" | Success end condition | postconditions |

- **Variants required:** an empty part makes the writer think about variants, which an omitted one does not.
- **Not adopted:** scope, level, stakeholders and interests, minimal guarantees, and special requirements. A project may add them (part 4). Quality requirements are outside DEC-001 (point 11).
- **Sources:** Cockburn's template, linked in part 2. His fully dressed form in *Writing Effective Use Cases* (Addison-Wesley, 2001) adds stakeholders and interests, and minimal guarantees. The RUP column follows a RUP-derived use-case specification ([Use Case Specification Template](https://www.voa.va.gov/DocumentView.aspx?DocumentID=216)).

**Journey**, its body, every element required:

- `# JRN-NNN — <title>`
- **Starts:**
- **Steps:**, of form `steps-match-front-matter`
- **Seams to watch:**, of form `seams-match-steps`
- **Done when:**

**Actor**, a document after part 6:

- `# ACT-<slug> — <name>`, required
- an opening, required: who this is
- **Comes:** and **Brings:**, optional, from today's placeholder (`actors.md:29`)
- project-kit adds its own list (part 4)

**Term**, its entry section:

- `## TERM-<slug> — <name>`, required
- **Applies to:**, **Not:** and **Example:**, optional, from today's placeholder (`glossary.md:29`)

**Revalidation record**, its body, written whole by the stamp:

- `# <date> — <subject>`
- `## Outcomes`, of form `outcomes-match-front-matter`
- `## Gaps`: each gap with its resolution, or `None found.`
- **No style lint:** a record's words are a person's decision (RS-WRITE-013, core rule 20).

## Forces and costs

- **A breaking change.** A check that fails what it passed before breaks the capability, as living-docs DEC-001 point 3 says of pages. software-analysis is at 0.1.0 (`SA/package.yaml:5`), and project-kit's own pilot analysis was removed (`6107ae77`).
- **Migration:**
  - The actors' split needs a migration (#1346). Ids do not change, so anchors by id still resolve.
  - Moving an actor changes its content, so friction asks each anchored use case and page for an answer. That answer is a person's (core rule 20). Main holds no use cases today, so the cost is lowest now.
  - project-kit's eight core actors (PR #1345) move with the split, and gain the declared labels.
- **Adopters.** Nothing to do unless they add labels. An artefact that lacks a required part is fixed, or waits while the rule is proposed.
- **Friction.** A structure change is no rule-content change (part 1), so it flags none of the rule's dependants.
- **Placeholders.** The append-only list still grows with each reworded placeholder. Hints leave it, matched by their marker.
- **What stays LLM judgment:**
  - whether the content is true, and whether a goal is one user story
  - whether a hint was followed in spirit
  - the writing rules marked judgment in part 7
- **Less LLM use.** The script runs first, so a reviewer reads only artefacts that have their shape.

## Slicing

1. **Decision:** DEC-001 gains the structure point and the actors' layout, and the maintainer accepts it.
2. **Backbone structure reader:** headings, labels and forms, with the declaration's schema and a query command.
3. **Structure check:** `SA/schemas/artefact-kinds.yaml`, the method rule set, and `pkit analysis validate` checking bodies.
4. **Rendered templates:** hints and examples, a check that refuses a leftover hint, and shipped text at the plain floor (#1351).
5. **One file per actor** (#1346): the place, the stamp, the check, the readers filler, a migration, and project-kit's actors.
6. **Project additions:** the `kinds` key, its refusal of a relaxing entry, and project-kit's actor labels.
7. **Forms:** numbered steps, lettered variants, a journey's steps and seams, and a record's outcomes.
8. **Later:** project-kit's writing lint, and living-docs moved onto the backbone reader.

## Open questions for the maintainer

1. **Where does the structure reader live?** Recommended: the backbone, called by both capabilities, since this is its second consumer. The alternative is a copy in software-analysis.
2. **How does a hint reach the writer?** Recommended: a marked comment under each element, refused when left in. The alternative is hints that only the stamp prints.
3. **One file per actor?** Recommended: yes, since it settles #1346 and fits the check. The alternative keeps the collection file.
4. **Does a departure fail from the first release?** Recommended: yes, with the rule accepted, since few analyses exist yet. The alternative ships the rule proposed, so it binds nothing until accepted.
