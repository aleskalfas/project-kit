---
rule-set: WRITE
version: 2.0.0
rules:
  RS-WRITE-001:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "Something must show what matters most. In the trial, opening each section with who the actor is made every section scannable (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-002:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, the same labels in the same order were the largest gain for scanning. A reader can jump to one label in any section (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
    offers: [labels]
  RS-WRITE-003:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, pairs and short series stayed in the sentence, so the lists did not clutter the page (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-004:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "Side matter interrupted each role's description. Moved last under Note, it left the description shorter with nothing dropped (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-005:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "Short sentences are easier for every reader. That is the maintainer's view, not a trial finding, since the trial tested no readers. The trial showed that the limit can be kept. The original had ten body sentences over 25 words, and both rewrites brought every one to 25 or fewer (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md). On two reference pages, a quoted message in a code span filled a sentence alone, so splitting added sentences that carry nothing (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-006:
    status: proposed
    origin: {why: "A sentence with one idea is read once, in the maintainer's view. The trial could not show it. This rule was applied with the word limit and the labels, and their effects could not be told apart. Splitting also put meaning at risk. In the trial, a split section contradicted itself. In the core actors, two splits would have chosen a reading, and in the try-outs, splits moved pronouns away from their nouns (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-007:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "A dense paragraph hides what each of its sentences is about. Dense paragraphs were the original's main problem, and eight of its nine ran over four sentences (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-008:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "A semicolon joins two sentences that read better apart. Three of the original's four semicolons split cleanly into sentences or a list. The fourth joined two citations, where a comma would be ambiguous, since a citation can hold a comma itself (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-009:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "An elided verb, as in \"the whole-repository report the developer\", slows every reader down. It slows most a reader whose first language is not English. Both are the maintainer's view, not a trial finding, since the trial tested no readers. The trial's ASD-STE100 rewrite made that clause whole (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md). A table's row names what each cell describes, so a cell need not name it again, as many of the CLI reference's cells show (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-010:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "A reader who picks the wrong referent learns a wrong fact, and nothing warns them. In the trial, naming the harness behind \"it\" made a need clear (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-011:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "Project terms such as review, land and retire have defined meanings. An outside dictionary's nearest words changed those meanings in the trial (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-013:
    status: accepted
    origin: {date: 2026-10-05, by: "Aleš Kalfas", why: "A style that changes meaning is disqualified, since readers rely on the facts a document states. In the trial, rewrites by both guidelines changed what statements claim (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-014:
    status: proposed
    origin: {why: "Line numbers drift whenever the cited file changes, and a section name drifts when its heading is renamed. Nothing checks either. A permanent id and an anchor stay true without upkeep. In the core actors, a line-number citation had already drifted to the wrong lines (#1354)."}
  RS-WRITE-015:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "The CLI reference describes a key in three forms: \"`roots` — the documentation roots\", \"`check` (`change`)\" and \"**`span`** is the lines that part spans\" (.pkit/cli/README.md). One form lets a reader find every key the same way. A path names a key wherever it is written, as `history.cut` already does there. The try-out on two reference pages asked for one form (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-016:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "Text points at a heading or a label by its words or its place, as in (\"Resolver limits\" below). No check follows such a pointer. In the try-out on two reference pages, a move took text out from under the label The three answers, which another item points at (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-017:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "Deep nesting was the first cost of the try-out on two reference pages. Lists for series with detail (RS-WRITE-003) nested the `--json` key lists, and the flags of an answer's line, four levels deep (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md). The CLI reference already nests a key list five levels deep (.pkit/cli/README.md). Every list in this set fits in three levels."}
  RS-WRITE-018:
    status: accepted
    origin: {date: 2026-10-17, by: "Aleš Kalfas", why: "In the try-out on two reference pages, an editing tool wrote a right-to-left override, U+202E, where the CLI reference names its escape. Only a scan of the bytes found it (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md). A control character can move the cursor or erase a line, and a bidirectional one reorders what follows (.pkit/cli/README.md). Either way, a reader and a reviewer see text the file does not hold."}
# The parts of these rules that project-kit's prose lint checks, in the text a change
# adds or moves (COR-051 point 2). Whoever judges the rest of a rule leaves them to it.
checks:
  RS-WRITE-005:
    - check: prose-lint
      part: A sentence that holds text a change adds or moves has at most 25 words, counted as the How counts them, outside the `pkit` container.
  RS-WRITE-008:
    - check: prose-lint
      part: Text a change adds or moves holds no semicolon outside code, quotation marks and the `pkit` container.
  RS-WRITE-017:
    - check: prose-lint
      part: A list item that holds text a change adds or moves, or whose marker's line it alters, sits at most three levels deep.
  RS-WRITE-018:
    - check: prose-lint
      part: Text a change adds or moves, anywhere in the artefact, holds none of the characters the statement forbids.
---

# WRITE — project-kit's general writing rules

These are project-kit's general writing rules. `ANA`, the analysis's own set, inherits them. The documentation spaces will inherit them later (#1350).

- **What matters most:** the meaning. A rewrite keeps it (RS-WRITE-013).
- **Where the rules apply:** everything under `tech-docs/analysis/`, software-analysis's templates, and the structures its kinds declare (software-analysis DEC-001 point 1). project-kit's operational rules send whoever writes any of them here (`.pkit/rules/project.md`). This set has no scope of its own. No scope could reach a template or a structure anyway, since neither is an artefact (ADR-055 point 3).
  - **In shipped text:** where a rule here would carry project-kit's own vocabulary or style into a template or a structure, universal applicability wins (COR-014). Examples are project-kit's glossary terms and its labels. The shipped text stays fit for any adopter.
- **The set for the analysis:** `ANA` (`tech-docs/rule-sets/analysis.md`) inherits this set, and its scope selects the analysis by type. It holds the analysis's own rules.
- **The documentation spaces, next:** the spaces' definitions, `TECH` and `USER`, will inherit this set in a later change (#1350).
- **What an inheriting set may fill:** the list of labels for a kind of document it governs (`RS-WRITE-002#labels`). `ANA` fills it for the analysis.
- **Where the rules come from:** a style trial in October 2026. It rewrote the core actors document by ASD-STE100 and by ISO 24495-1, and kept what helped. The rules were then tried on two reference pages, and the try-out found what such pages need. The trial, the try-out and what they left out are in `.pkit/scratchpad/done/2026-10-05-writing-style-trial.md`.
- **How a rule reads:** a statement, then *How*, then examples. A rule's reason is the `why` of its origin, in the front matter (COR-051 point 5).
  - *Breaks the rule* and *Keeps the rule* quote the core actors: the original document breaks the rule, and the plain rewrite keeps it.
  - *Breaks the rule on a page* and *Keeps the rule on a page* quote a reference page before and after its try-out on `docs/1348-write-tryout`.
  - An example that quotes anything else says so.
- **What binds:** a rule's statement and its *How*. Both are the rule's content in the sense of COR-051 point 2, and the examples only illustrate them. Inside a *How*, a "such as" phrase and a sentence that starts "An example is" only illustrate too. The rest of the *How* binds.
- **What a tool checks:** the `checks` in the front matter name the parts of rules that project-kit's prose lint (`scripts/prose_lint.py`) checks. It checks them in the text a change adds or moves, on the artefacts where these rules bind. A reviewer leaves those parts to the lint there, and judges them on templates and structures (COR-051 point 2).
- **Held back:** RS-WRITE-002, on labels, and RS-WRITE-006, on one idea per sentence, stay proposed. The maintainer held both back on 5 October. RS-WRITE-006's `why` says what the trial could not show, and what splitting put at risk.
- **Proposed:** RS-WRITE-014, on citing by permanent id, waits for the maintainer's acceptance.
- **A number not reused:** RS-WRITE-012 was the rule on needs and goals. It left this set, since needs and goals are the analysis's own, and its number stays unused here.
- **Note:** how rules are named, accepted and inherited is the rule-set record's (COR-051). A rule binds only once it is accepted.

## Structure

These rules lay a document out so that a reader can scan it.

### RS-WRITE-001 — Open with what matters most

Open each section with one sentence that says what matters most in it.

- **How:**
  - Keep that sentence to what matters most, and put the detail in the lines below it.
  - A section that is only a list needs no opening sentence, since its heading says what the list holds. An example is a revalidation record's *Outcomes*.
  - An empty section needs none either, where its document's kind lets it stay empty. An example is a glossary term's section, when its one-sentence definition suffices.
  - Table cells are exempt, since a cell is not a section.
- **Breaks the rule:** "The person who adopts the methodology for a project and keeps its setup: what is installed, at which version, which of their own additions sit beside it, and which checks the project's merges wait on."
- **Keeps the rule:** "The person who adopts the methodology for a project and keeps its setup." The setup follows as a labelled list.
- **Breaks the rule on a page:** the software-analysis README's section on `pkit analysis new` opens with "Create artefacts with the stamp, never by copying a template by hand: it gives each one its id, puts it in its place and writes the anchors it must carry."
- **Keeps the rule on a page:** its try-out opens with "Create artefacts with the stamp, never by copying a template by hand." What the stamp does follows in the next sentence.

### RS-WRITE-002 — Parallel sections share their labels

Give parallel sections their bold labels from one list, in its order, with no pronoun in any label.

- **How:**
  - **The list** (`RS-WRITE-002#labels`) is set for each kind of document. A set that inherits this one may fill this point with the list for a kind it governs. Where no set fills it for a kind, take the labels that the kind's template gives. Where the kind has no template, or its template gives no labels, choose one list for the whole document.
  - A section may leave out a label it has nothing for.
  - A label says what follows it. With no pronoun, one label fits a section about a person and a section about a system alike.
  - Table cells are exempt, since a cell holds no label.
- **Breaks the rule:** the plain rewrite gives one slot two labels, "**When they come:**" for the developer and "**When it comes:**" for the CI pipeline.
- **Keeps the rule:** one label for both, as in the core actors: "**Occasions:** for every change, …" and "**Occasions:** on every pull request, …".
- **Breaks the rule on a page:** after the CLI reference's try-out, `friction check --all`, `friction debt` and `friction explain` share the label *What it reads*, which holds a pronoun.
- **Keeps the rule on a page:** the same three commands and `friction check` share the label *`--json`*, which holds none.

### RS-WRITE-003 — A list for a series that carries detail

Put a series of three or more items in a list with a lead-in when any item is a clause or carries detail.

- **How:**
  - The lead-in is a label or a sentence that says what the list holds. Nest a list where an item has parts of its own.
  - A series of two stays in the sentence, and so does a series of short phrases, such as "decisions, rules, notes, code and its documentation".
  - Text that an accepted decision record holds to one sentence is exempt. An example is an actor's need or a use case's goal (software-analysis DEC-001 point 1). Table cells are exempt too, since a cell holds no list.
- **Breaks the rule:** "That can be an adopter growing a discipline in their own repository, an organisation that keeps private methodology in one repository for its others, or whoever adapts the methodology to a new harness."
- **Keeps the rule:** "**Role holders:**", then one list item for each of the three. The label is the core actors', in place of the plain rewrite's *Who this can be*.
- **Breaks the rule on a page:** in the CLI reference's friction section, "**Writes only with consent** — the consent rule of the configuration writer (COR-048 point 5), applied to the project's artefacts: `--yes` consents non-interactively; on a terminal without it the command shows the diff and asks; …"
- **Keeps the rule on a page:** "**Writes only with consent.** It applies the consent rule of the configuration writer (COR-048 point 5) to the project's artefacts." One list item follows for each case.

### RS-WRITE-004 — Side matter last, under *Note*

Put side matter last in its section, under the label *Note*.

- **How:**
  - Side matter is the reason for a name, or an overlap with another document.
  - Table cells are exempt, since a cell holds no label.
- **Breaks the rule:** in the middle of the merge authoriser's paragraph, "The name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."
- **Keeps the rule:** as the section's last item, "**Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."
- **Breaks the rule on a page:** the CLI reference's friction section gives the reason for the command group's name in its first sentence, "The `friction` command group is everything the anchors-and-friction functionality does (…), named like the block an artefact carries and the configuration key."
- **Keeps the rule on a page:** after its try-out, the reason is the last item of the section's opening. It reads "**Note:** the group is named like the block an artefact carries and the configuration key."

### RS-WRITE-017 — Lists nest at most three levels deep

Nest a list at most three levels deep.

- **How:**
  - An item of a list that sits in no other list is at level one. An item of a list nested in it is at level two.
  - This limit holds over RS-WRITE-003's nesting. Where an item's parts would sit at a fourth level, give the top items sub-headings. Or lift the parts a level, under a label of their own.
  - Code blocks are exempt, since they are not prose. Front matter is exempt too, since its data's shape sets how it nests. Table cells are exempt, since a cell holds no list.
- **Breaks the rule on a page:** after the CLI reference's try-out, the item on the answers a change wrote nests four levels. It holds "**One line per answer:**", which holds "its flags:", which holds "`new`".
- **Keeps the rule on a page:** the same flags lifted a level, under a label of their own beside "**One line per answer:**", sit at level three. That rewrite is on no branch.

## Sentences and paragraphs

These rules keep each sentence and paragraph short enough to read once.

### RS-WRITE-005 — At most 25 words a sentence

Keep every sentence to 25 words or fewer, and count the words in parentheses too.

- **How:** count as the trial did, except for code spans.
  - A word is a token between spaces that holds a letter or a digit, once bold marks and backticks are removed. An id, a file name or a hyphenated word is one word.
  - A code span is at most one word. It is one word where it holds a letter or a digit, and none otherwise. An example is a message the CLI reference quotes in a sentence, `` `friction.exclude` now leaves out 1 file this anchor stood on at the base (…); no change to it in this diff ``.
  - A sentence ends at a full stop, a question mark or an exclamation mark before a space or a line end. Each list item ends one too, and so does each item of a front-matter list, such as an actor's need.
  - A lead-in that ends in a colon is one sentence. Colons and semicolons end none.
  - Headings, bold labels, code blocks and quoted examples of a broken rule are not counted.
- **Breaks the rule:** a sentence of 38 words, "Core: the backbone ships no workflow, only checks made to run unattended, which bind once the project makes them a required status (COR-050 point 12), and one base a pipeline names for all of them (COR-054 point 3)."
- **Keeps the rule:** "the backbone ships no workflow. It ships only checks made to run unattended, and one base a pipeline names for all of them (COR-054 point 3). The checks bind once the project makes them a required status (COR-050 point 12)." Unlike the plain rewrite, this keeps the two items in the sentence (RS-WRITE-003).
- **Breaks the rule on a page:** a sentence of 30 words in the software-analysis README, "Every artefact form also takes `--path <glob>` and `--record <id>`, each repeatable: the code that makes the artefact true and the decisions it relies on, written as its path and record anchors."
- **Keeps the rule on a page:** "Every artefact form also takes `--path <glob>` and `--record <id>`, each repeatable. They are the code that makes the artefact true and the decisions it relies on, written as its path and record anchors."

### RS-WRITE-006 — One idea per sentence

Give each sentence of prose one idea.

- **How:** split where one idea ends, then check that the parts still agree (RS-WRITE-013). Text that an accepted decision record holds to one sentence is exempt. An example is an actor's need or a use case's goal (software-analysis DEC-001 point 1).
- **Breaks the rule:** "They bring the methodology's disciplines (CONTRIBUTING.md), and they are the first adopter of what they ship."
- **Keeps the rule:** "**Context:** the methodology's disciplines (CONTRIBUTING.md). They are the first adopter of what they ship." The label is the core actors', in place of the plain rewrite's *What they bring*.
- **Breaks the rule on a page:** in the CLI reference's section on `friction check`, "It reads the artefacts, never a pull-request description, so it runs the same in CI, for a pull request from any tool, and locally before a commit."
- **Keeps the rule on a page:** "It reads the artefacts, never a pull-request description. So it runs the same in CI, for a pull request from any tool, and locally before a commit."

### RS-WRITE-007 — One topic a paragraph, at most four sentences

Give each paragraph one topic and no more than four sentences.

- **How:**
  - A list item counts as a paragraph. Labels and lists are the usual fix. RS-WRITE-003 says when a series takes a list.
  - Four is project-kit's choice. ASD-STE100 allows six (its 6.6).
  - Table cells are exempt, since a cell holds no paragraph.
- **Breaks the rule:** the operator's section, one paragraph of five sentences on six topics.
- **Keeps the rule:** an opening of two sentences, then one labelled item for each topic, none over two sentences.
- **Breaks the rule on a page:** the software-analysis README's *Ids* item, one list item of thirteen sentences.
- **Keeps the rule on a page:** a lead of three sentences, then twelve labelled items, none over four sentences.

### RS-WRITE-008 — No semicolons

Write no semicolons in prose.

- **How:** make two sentences, or a list. Where two citations share a parenthesis, join them with "and", as in "(PRJ-002 and release README:22-29)". Each citation keeps its own form (RS-WRITE-013). Code and text quoted word for word are exempt.
- **Breaks the rule:** "The role is per machine and per clone; it is not whoever holds the repository's settings, …"
- **Keeps the rule:** "The role is per machine and per clone." The rest moved to the section's *Note*.
- **Breaks the rule on a page:** in the CLI reference's friction section, "Entries are kept in one order — deferrals by anchor kind, then value; keys in the schema's order — so the same input writes the same bytes, …"
- **Keeps the rule on a page:** "Entries are kept in one order. Deferrals are ordered by anchor kind, then value, and keys are in the schema's order."

### RS-WRITE-009 — Each clause has its own verb

In a series of clauses, give each clause its own verb.

- **How:**
  - Repeat a verb that two clauses share, rather than leave the reader to supply it.
  - A table cell may leave out its subject where its row names it, and start with its verb. An example is the CLI reference's row for `friction defer`, after its try-out: "Never touches `at`. Writes only with consent."
- **Breaks the rule:** "the change check serves the developer and the merge authoriser, the whole-repository report the developer"
- **Keeps the rule:** "The change check serves the developer and the merge authoriser." Then "The whole-repository report serves the developer."
- **Breaks the rule on a page:** in the software-analysis README, "An actor is `ACT-<slug>` and a term `TERM-<slug>`"
- **Keeps the rule on a page:** "An actor is `ACT-<slug>`, and a term is `TERM-<slug>`."

## Words and terms

These rules make each pronoun and each pointer lead to one thing, and give each thing one term. A key of a JSON document gets one form too.

### RS-WRITE-010 — Name what a pronoun stands for

Replace a pronoun with the noun it stands for when the pronoun could point at two things.

- **How:** in a rewrite, take the noun from the author, or from a cited source that the author confirms (RS-WRITE-013).
- **Breaks the rule on a page:** in the software-analysis README's section on `pkit analysis new`, "Create artefacts with the stamp, never by copying a template by hand: it gives each one its id, …" *It* could be the stamp or the template.
- **Keeps the rule on a page:** in that section's try-out, "… never by copying a template by hand. The stamp gives each one its id, …", once the author confirms that reading.

### RS-WRITE-011 — One term for one thing, from the glossary

Use one term for one thing, and take it from the project's glossary, not from an outside dictionary.

- **How:** until the glossary holds a word, use the word that the project's records use. Where a document uses two terms, ask the author whether they name one thing.
- **Breaks the rule:** the developer comes "for every unit of work", and the merge authoriser comes "at the end of each piece of work". The two terms may name one thing.
- **Keeps the rule:** one of the two in both places, once the author confirms that they name one thing. The first ASD-STE100 rewrite chose "task" for both without asking.

### RS-WRITE-014 — Cite by permanent id

Cite a decision, a rule, an artefact or an issue by its permanent id, and name a document without a line or section locator.

- **How:** a permanent id never changes and is never reused, so the citation stays true while the cited text moves. Where an artefact depends on what a document says, anchor the artefact to that document, so a change to it flags the artefact. Code and text quoted word for word are exempt.
- **Breaks the rule:** "the changeset guard and the release tag (PRJ-002 and release README:22-29)". Lines 22 to 29 held the README's opening, not either step.
- **Keeps the rule:** "the changeset guard and the release tag (PRJ-002)".

### RS-WRITE-015 — One form for a JSON document's keys

Name a key of a JSON document by its path, in code. An item that describes a key opens with that path and a colon.

- **How:**
  - A path runs from the object its passage describes: the document's top, or an object that a heading or a lead-in names. A dot joins an object to its key, and `[]` follows a key whose value is a list. An example is `answers[].status`.
  - A key that is data, such as each path in a map of files, takes a placeholder. An example is `files.<path>`.
  - Where the passage leaves the document unclear, name it beside the path. An example is "`history.cut` in `check --json`".
  - A value's shape written as an object, such as `{kind, value}`, names its keys inside it and needs no path.
  - An item for an object may name its short keys in its sentence, as RS-WRITE-003 keeps a series of short phrases there.
- **Breaks the rule on a page:** the CLI reference, as main holds it, describes keys in three forms. Its `friction artefacts --json` reads "`roots` — the documentation roots" and "**`span`** is the lines that part spans". Its `friction check --json` reads "`check` (`change`)".
- **Keeps the rule on a page:** after the CLI reference's try-out, the keys of each finding of `friction check` read as "`location`: `path`, or `path#id` for a collection entry".

### RS-WRITE-016 — A label that text points to stays

Keep a heading or a label that other text points to, with its words and what a pointer sends a reader there for. Otherwise, mend every pointer in the same change.

- **How:**
  - A pointer names a heading or a label by its words. A link to a heading counts too, and so does a pointer from another document. An example is ("Resolver limits" below).
  - A pointer that gives a place, such as "below", relies on the label's place too.
  - Moving text out from under a label breaks a pointer, as renaming the label does. The pointer then leads to a label that no longer holds what the reader came for.
  - Where a pointer lies outside what the change can edit, keep the label. An example is a link into a shipped page from an adopter's repository.
  - Before a rename or a move, look for the pointers by words and the links to the heading. A section anchor in a friction block needs no search, since the change check reports it dead (COR-050 point 7).
- **Breaks the rule on a page:** a first pass of the CLI reference's try-out moved the file history out from under the label *The three answers*. *What it compares* still pointed there with ("The three answers"). That pass is on no branch.
- **Keeps the rule on a page:** the try-out kept the file history under *The three answers*, as its item *Telling a written-back answer from a new one*.

## Keeping meaning

This rule protects what a text says whenever someone rewrites it.

### RS-WRITE-013 — A rewrite keeps the meaning

A rewrite adds, drops, weakens or narrows no claim, and asks the author wherever it would have to choose a reading.

- **How:**
  - Flag the passage for the author, and keep the original until the author answers. The flag is a comment on the change's pull request that lists each held spot, as on PR #1345.
  - Project terms and citations stay as written, and a citation's form includes its locator, such as "release README:22-29".
  - Text a person decided, or an answer a reviewer checked, is never rewritten for style, such as a recorded revalidation, a deferral, an `unanchored-because` reason or a revalidation record. Reworded, it would need deciding or checking again (`.pkit/rules/core.md` rule 20).
  - This rule wins wherever another rule of this set or of a set that inherits it would change what a text says.
  - The trial's rewrites changed what a text says in each of these ways:
    - **Adding:** the original "have them validated" names no validator, and the rewrite "let the system validate them" names one.
    - **Dropping:** "every change *passes* the acceptance gate" became "the acceptance gate and the friction check *examine* each change". The duty to pass is gone.
    - **Weakening:** "*Carry* the projects … *across* a breaking change" became "*Help* the projects … to continue to operate". Dropping *own* or *itself* weakens a claim too.
    - **Narrowing:** "*answer* what the methodology gates" became "*accepts or rejects the prompts* at the gates".
    - **Swapping a term:** "the same person's *review* turns a record or rule … into a binding one" became "When the same person *examines* a record or rule …". Reading a draft does not make it binding.
    - **Splitting into parts that disagree:** "only checks …, and one base" became "only checks", then "also one base".
    - **Choosing a reading:** "knowing what each change … means for them" has two readings. One rewrite gave the knowing to the adopters, and the other gave it to the maintainer. A pronoun's referent is a reading too (RS-WRITE-010).
  - The trial also changed a citation's form: "(:65, :67)" became "(lines 65 and 67)". That is a change of form, not of claim, and the citation clause above forbids it too.
- **Breaks the rule:** "Ship a backbone change that breaks installed projects only with the migration that carries them across." (the plain rewrite). It turns the guard "Never … without" into the goal "only with", which adds an implied goal: a wish to ship breaking changes.
- **Keeps the rule:** "Never ship a backbone change that breaks installed projects without the migration that carries them across." (the original)

## Characters

This rule keeps what a reader sees the same as what a file holds.

### RS-WRITE-018 — No control or bidirectional character

Write no control character other than a tab or a line end, and no bidirectional formatting character.

- **How:**
  - A control character is one that Unicode classes as a control (Cc), such as an escape, U+001B. A bidirectional formatting character is one that Unicode marks Bidi_Control: U+061C, U+200E, U+200F, U+202A to U+202E and U+2066 to U+2069.
  - Where a text must name such a character, write its escape in code, such as `\u202e`.
  - The rule reaches the whole artefact: code, front matter, headings and comments included. In a person's answer inside the `pkit` container, ask that person before removing one, since such words are never rewritten unasked (RS-WRITE-013).
- **Breaks the rule on a page:** during the CLI reference's try-out, an editing tool wrote U+202E itself in place of `\u202e`, in the passage that names the escapes. Only a scan of the bytes found it.
- **Keeps the rule on a page:** the passage as main holds it, before and after the try-out, with each escape written as code: "is shown as its escape (`\x1b`, `\u202e`)".

## What this set does not govern

This set leaves three kinds of writing to their own rules, and reaches a table cell only in part.

- **Decision records:** the decision-record specification governs them (`.pkit/decisions/README.md`).
- **Rule sets:** the rule-set record governs them (COR-051). This set keeps its own rules anyway.
- **Agent and skill bodies:** their own disciplines govern them (`.pkit/agents/README.md` and `.pkit/skills/README.md`).
- **Table cells:** a rule that does not reach a cell says so in its *How*, as RS-WRITE-001 to RS-WRITE-004, RS-WRITE-007 and RS-WRITE-017 do.
- **Note:** this set does not inherit `living-docs:LDOC`. LDOC's rules are for pages, and would pull a page's `reader` field (RS-LDOC-003) onto analysis artefacts, which are never pages (living-docs DEC-001 point 1). living-docs DEC-001 point 3 keeps a project's documentation rules in a set that inherits LDOC. Pages will reach WRITE only through `TECH` and `USER`, which inherit LDOC, so every page that takes WRITE will take LDOC beside it.
