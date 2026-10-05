---
rule-set: WRITE
version: 0.1.0
rules:
  RS-WRITE-001:
    status: proposed
    origin: {why: "Something must show what matters most. In the trial, opening each section with who the actor is made every section scannable (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-002:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, the same labels in the same order were the largest gain for scanning. A reader can jump to one label in any section (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
    offers: [labels]
  RS-WRITE-003:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, pairs and short series stayed in the sentence, so the lists did not clutter the page (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-004:
    status: proposed
    origin: {why: "Side matter interrupted each role's description. Moved last under Note, it left the description shorter with nothing dropped (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-005:
    status: proposed
    origin: {why: "Short sentences are easier for every reader. That is the maintainer's view, not a trial finding, since the trial tested no readers. The trial showed that the limit can be kept. The original had ten body sentences over 25 words, and both rewrites brought every one to 25 or fewer (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-006:
    status: proposed
    origin: {why: "A sentence with one idea is read once, in the maintainer's view. The trial could not show it. This rule was applied with the word limit and the labels, and their effects could not be told apart. Splitting also put meaning at risk. In the trial, a split section contradicted itself. In the core actors, two splits would have chosen a reading, and in the try-outs, splits moved pronouns away from their nouns (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-007:
    status: proposed
    origin: {why: "A dense paragraph hides what each of its sentences is about. Dense paragraphs were the original's main problem, and eight of its nine ran over four sentences (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-008:
    status: proposed
    origin: {why: "A semicolon joins two sentences that read better apart. Three of the original's four semicolons split cleanly into sentences or a list. The fourth joined two citations, where a comma would be ambiguous, since a citation can hold a comma itself (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-009:
    status: proposed
    origin: {why: "An elided verb, as in \"the whole-repository report the developer\", slows every reader down. It slows most a reader whose first language is not English. Both are the maintainer's view, not a trial finding, since the trial tested no readers. The trial's ASD-STE100 rewrite made that clause whole (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-010:
    status: proposed
    origin: {why: "A reader who picks the wrong referent learns a wrong fact, and nothing warns them. In the trial, naming the harness behind \"it\" made a need clear (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-011:
    status: proposed
    origin: {why: "Project terms such as review, land and retire have defined meanings. An outside dictionary's nearest words changed those meanings in the trial (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-013:
    status: proposed
    origin: {why: "A style that changes meaning is disqualified for analysis artefacts. In the trial, rewrites by both guidelines changed what statements claim (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
---

# WRITE — project-kit's general writing rules

These are project-kit's general writing rules. They bind a document only through a set that inherits them: the analysis set now, and later the documentation spaces (#1350).

- **What matters most:** the meaning. A rewrite keeps it (RS-WRITE-013).
- **Where the rules apply:** wherever a set that inherits this one applies. This set has no scope of its own, so it governs nothing directly.
- **The analysis set:** `ANALYSIS` (`tech-docs/rule-sets/analysis.md`) inherits this set for everything under `tech-docs/analysis/`. project-kit's operational rules send whoever writes the analysis there (`.pkit/rules/project.md`).
- **The documentation spaces, next:** the spaces' definitions, `TECH` and `USER`, will inherit this set in a later change (#1350). That change first adds the exceptions that reference pages need.
- **What an inheriting set fills:** the list of labels for each kind of document it governs (`RS-WRITE-002#labels`).
- **Where the rules come from:** a style trial in October 2026. It rewrote the core actors document by ASD-STE100 and by ISO 24495-1, and kept what helped. The rules were then tried on two reference pages. The trial, the try-out and what they left out are in `.pkit/scratchpad/done/2026-10-05-writing-style-trial.md`.
- **How a rule reads:** a statement, then *How*, then examples. A rule's reason is the `why` of its origin, in the front matter (COR-051 point 5).
  - *Breaks it* and *Keeps it* quote the core actors: the original document breaks the rule, and the plain rewrite keeps it.
  - *Breaks it on a page* and *Keeps it on a page* quote a reference page before and after its try-out, on the branch `docs/1348-write-tryout`.
  - An example that quotes anything else says so.
- **What binds:** a rule's statement and its *How*. Both are the rule's content in the sense of COR-051 point 2, and the examples only illustrate them.
- **Held back:** RS-WRITE-006 stays proposed for now. Its `why` says what the trial could not show, and what splitting put at risk.
- **A number not reused:** RS-WRITE-012 moved to the analysis set as RS-ANALYSIS-001, since needs and goals are the analysis's own. Its number stays unused here.
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
- **Breaks it:** "The person who adopts the methodology for a project and keeps its setup: what is installed, at which version, which of their own additions sit beside it, and which checks the project's merges wait on."
- **Keeps it:** "The person who adopts the methodology for a project and keeps its setup." The setup follows as a labelled list.
- **Breaks it on a page:** the software-analysis README's section on `pkit analysis new` opens with "Create artefacts with the stamp, never by copying a template by hand: it gives each one its id, puts it in its place and writes the anchors it must carry."
- **Keeps it on a page:** its try-out opens with "Create artefacts with the stamp, never by copying a template by hand." What the stamp does follows in the next sentence.

### RS-WRITE-002 — Parallel sections share their labels

Give parallel sections their bold labels from one list, in its order, with no pronoun in any label.

- **How:**
  - **The list** (`RS-WRITE-002#labels`) is set for each kind of document. A set that inherits this one fills this point with the list for each kind it governs. Where no list is filled for a kind, choose the list once for the whole document.
  - A section may leave out a label it has nothing for.
  - A label says what follows it. With no pronoun, one label fits a section about a person and a section about a system alike.
  - Table cells are exempt, since a cell holds no label.
- **Breaks it:** the plain rewrite gives one slot two labels, "**When they come:**" for the developer and "**When it comes:**" for the CI pipeline.
- **Keeps it:** one label for both, from the core actors' list (RS-ANALYSIS-002): "**Comes:** for every unit of work, …" and "**Comes:** on every pull request, …".
- **Breaks it on a page:** after the CLI reference's try-out, `friction check --all`, `friction debt` and `friction explain` share the label *What it reads*, which holds a pronoun.
- **Keeps it on a page:** the same three commands and `friction check` share the label *`--json`*, which holds none.

### RS-WRITE-003 — A list for a series that carries detail

Put a series of three or more items in a list with a lead-in when any item is a clause or carries detail.

- **How:**
  - The lead-in is a label or a sentence that says what the list holds. Nest a list where an item has parts of its own.
  - A series of two stays in the sentence, and so does a series of short phrases, such as "decisions, rules, notes, code and its documentation".
  - Text that an inheriting set's rule holds to one sentence is exempt, such as an actor's need (RS-ANALYSIS-001). Table cells are exempt too, since a cell holds no list.
- **Breaks it:** "That can be an adopter growing a discipline in their own repository, an organisation that keeps private methodology in one repository for its others, or whoever adapts the methodology to a new harness."
- **Keeps it:** "**Can be:**", then one list item for each of the three. The label is the core actors', since the plain rewrite's *Who this can be* holds a pronoun (RS-WRITE-002).
- **Breaks it on a page:** in the CLI reference's friction section, "**Writes only with consent** — the consent rule of the configuration writer (COR-048 point 5), applied to the project's artefacts: `--yes` consents non-interactively; on a terminal without it the command shows the diff and asks; …"
- **Keeps it on a page:** "**Writes only with consent.** It applies the consent rule of the configuration writer (COR-048 point 5) to the project's artefacts." One list item follows for each case.

### RS-WRITE-004 — Side matter last, under *Note*

Put side matter last in its section, under the label *Note*.

- **How:**
  - Side matter is any of these:
    - the reason for a name
    - a fact that holds for project-kit alone, and not for the projects that adopt the methodology
    - an overlap with another document
  - Table cells are exempt, since a cell holds no label.
- **Breaks it:** in the middle of the merge authoriser's paragraph, "The name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."
- **Keeps it:** as the section's last item, "**Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."
- **Breaks it on a page:** the CLI reference's friction section gives the reason for the command group's name in its first sentence, "The `friction` command group is everything the anchors-and-friction functionality does (…), named like the block an artefact carries and the configuration key."
- **Keeps it on a page:** after its try-out, the reason is the last item of the section's opening. It reads "**Note:** the group is named like the block an artefact carries and the configuration key."

## Sentences and paragraphs

These rules keep each sentence and paragraph short enough to read once.

### RS-WRITE-005 — At most 25 words a sentence

Keep every sentence to 25 words or fewer, and count the words in parentheses too.

- **How:** count as the trial did.
  - A word is a token between spaces that holds a letter or a digit, once bold marks and backticks are removed. An id, a file name or a hyphenated word is one word.
  - A sentence ends at a full stop, a question mark or an exclamation mark before a space or a line end. Each list item ends one too, and so does each item of a front-matter list, such as an actor's need.
  - A lead-in that ends in a colon is one sentence. Colons and semicolons end none.
  - Headings, bold labels, code blocks and quoted examples of a broken rule are not counted.
- **Breaks it:** a sentence of 38 words, "Core: the backbone ships no workflow, only checks made to run unattended, which bind once the project makes them a required status (COR-050 point 12), and one base a pipeline names for all of them (COR-054 point 3)."
- **Keeps it:** "the backbone ships no workflow. It ships only checks made to run unattended, and one base a pipeline names for all of them (COR-054 point 3). The checks bind once the project makes them a required status (COR-050 point 12)." Unlike the plain rewrite, this keeps the two items in the sentence (RS-WRITE-003).
- **Breaks it on a page:** a sentence of 32 words in the software-analysis README, "Every artefact form also takes `--path <glob>` and `--record <id>`, each repeatable: the code that makes the artefact true and the decisions it relies on, written as its path and record anchors."
- **Keeps it on a page:** "Every artefact form also takes `--path <glob>` and `--record <id>`, each repeatable. They are the code that makes the artefact true and the decisions it relies on, written as its path and record anchors."

### RS-WRITE-006 — One idea per sentence

Give each sentence of prose one idea.

- **How:** split where one idea ends, then check that the parts still agree (RS-WRITE-013). Text that an inheriting set's rule holds to one sentence follows that rule instead, such as an actor's need (RS-ANALYSIS-001).
- **Breaks it:** "They bring the methodology's disciplines (CONTRIBUTING.md), and they are the first adopter of what they ship."
- **Keeps it:** "**Brings:** the methodology's disciplines (CONTRIBUTING.md). They are the first adopter of what they ship." The label is the core actors', in place of the plain rewrite's *What they bring* (RS-WRITE-002).
- **Breaks it on a page:** in the CLI reference's section on `friction check`, "It reads the artefacts, never a pull-request description, so it runs the same in CI, for a pull request from any tool, and locally before a commit."
- **Keeps it on a page:** "It reads the artefacts, never a pull-request description. So it runs the same in CI, for a pull request from any tool, and locally before a commit."

### RS-WRITE-007 — One topic a paragraph, at most four sentences

Give each paragraph one topic and no more than four sentences.

- **How:**
  - A list item counts as a paragraph. Labels and lists are the usual fix (RS-WRITE-002 and RS-WRITE-003).
  - Four is project-kit's choice. ASD-STE100 allows six (its 6.6).
  - Table cells are exempt, since a cell holds no paragraph.
- **Breaks it:** the operator's section, one paragraph of five sentences on six topics.
- **Keeps it:** an opening of two sentences, then one labelled item for each topic, none over two sentences.
- **Breaks it on a page:** the software-analysis README's *Ids* item, one list item of thirteen sentences.
- **Keeps it on a page:** a lead of three sentences, then twelve labelled items, none over four sentences.

### RS-WRITE-008 — No semicolons

Write no semicolons in prose.

- **How:** make two sentences, or a list. Where two citations share a parenthesis, join them with "and", as in "(PRJ-002 and release README:22-29)". Each citation keeps its own form (RS-WRITE-013). Code and text quoted word for word are exempt.
- **Breaks it:** "The role is per machine and per clone; it is not whoever holds the repository's settings, …"
- **Keeps it:** "The role is per machine and per clone." The rest moved to the section's *Note*.
- **Breaks it on a page:** in the CLI reference's friction section, "Entries are kept in one order — deferrals by anchor kind, then value; keys in the schema's order — so the same input writes the same bytes, …"
- **Keeps it on a page:** "Entries are kept in one order. Deferrals are ordered by anchor kind, then value, and keys are in the schema's order."

### RS-WRITE-009 — Each clause has its own verb

In a series of clauses, give each clause its own verb.

- **How:** repeat a verb that two clauses share, rather than leave the reader to supply it.
- **Breaks it:** "the change check serves the developer and the merge authoriser, the whole-repository report the developer"
- **Keeps it:** "The change check serves the developer and the merge authoriser." Then "The whole-repository report serves the developer."
- **Breaks it on a page:** in the software-analysis README, "An actor is `ACT-<slug>` and a term `TERM-<slug>`"
- **Keeps it on a page:** "An actor is `ACT-<slug>`, and a term is `TERM-<slug>`."

## Words and terms

These rules make each pronoun point at one thing, and give each thing one term.

### RS-WRITE-010 — Name what a pronoun stands for

Replace a pronoun with the noun it stands for when the pronoun could point at two things.

- **How:** in a rewrite, take the noun from the author, or from a cited source that the author confirms (RS-WRITE-013).
- **Breaks it on a page:** in the software-analysis README's section on `pkit analysis new`, "Create artefacts with the stamp, never by copying a template by hand: it gives each one its id, …" *It* could be the stamp or the template.
- **Keeps it on a page:** in that section's try-out, "… never by copying a template by hand. The stamp gives each one its id, …", once the author confirms that reading.

### RS-WRITE-011 — One term for one thing, from the glossary

Use one term for one thing, and take it from the project's glossary, not from an outside dictionary.

- **How:** until the glossary holds a word, use the word that the project's records use. Where a document uses two terms, ask the author whether they name one thing.
- **Breaks it:** the developer comes "for every unit of work", and the merge authoriser comes "at the end of each piece of work". The two terms may name one thing.
- **Keeps it:** one of the two in both places, once the author confirms that they name one thing. The first ASD-STE100 rewrite chose "task" for both without asking.

## Keeping meaning

This rule protects what a text says whenever someone rewrites it.

### RS-WRITE-013 — A rewrite keeps the meaning

A rewrite adds, drops, weakens or narrows no claim, and asks the author wherever it would have to choose a reading.

- **How:**
  - Flag the passage for the author, and keep the original until the author answers. The flag is a comment on the change's pull request that lists each held spot, as on PR #1345.
  - Project terms and citations stay as written, and a citation's form includes its locator, such as "release README:22-29".
  - Text a person decided is never rewritten for style, such as a recorded revalidation, a deferral, an `unanchored-because` reason or a revalidation record. Reworded, it would need that person's decision again (`.pkit/rules/core.md` rule 20).
  - This rule wins wherever another rule of this set would change what a text says.
  - The trial's rewrites changed what a text says in each of these ways:
    - **Adding:** the original "have them validated" names no validator, and the rewrite "let the system validate them" names one.
    - **Dropping:** "every change *passes* the acceptance gate" became "the acceptance gate and the friction check *examine* each change". The duty to pass is gone.
    - **Weakening:** "*Carry* the projects … *across* a breaking change" became "*Help* the projects … to continue to operate". Dropping *own* or *itself* weakens a claim too.
    - **Narrowing:** "*answer* what the methodology gates" became "*accepts or rejects the prompts* at the gates".
    - **Swapping a term:** "the same person's *review* turns a record or rule … into a binding one" became "When the same person *examines* a record or rule …". Reading a draft does not make it binding.
    - **Splitting into parts that disagree:** "only checks …, and one base" became "only checks", then "also one base".
    - **Choosing a reading:** "knowing what each change … means for them" has two readings. One rewrite gave the knowing to the adopters, and the other gave it to the maintainer. A pronoun's referent is a reading too (RS-WRITE-010).
  - The trial also changed a citation's form: "(:65, :67)" became "(lines 65 and 67)". That is a change of form, not of claim, and the citation clause above forbids it too.
- **Breaks it:** "Ship a backbone change that breaks installed projects only with the migration that carries them across." (the plain rewrite). It turns the guard "Never … without" into the goal "only with", which adds an implied goal: a wish to ship breaking changes.
- **Keeps it:** "Never ship a backbone change that breaks installed projects without the migration that carries them across." (the original)

## What this set does not govern

This set leaves three kinds of writing to their own rules, and reaches a table cell only in part.

- **Decision records:** the decision-record specification governs them (`.pkit/decisions/README.md`).
- **Rule sets:** the rule-set record governs them (COR-051). This set keeps its own rules anyway.
- **Agent and skill bodies:** their own disciplines govern them (`.pkit/agents/README.md` and `.pkit/skills/README.md`).
- **Table cells:** a rule that does not reach a cell says so in its *How*, as RS-WRITE-001 to RS-WRITE-004 and RS-WRITE-007 do.
- **Note:** this set does not inherit `living-docs:LDOC`. LDOC's rules are for pages, and would pull a page's `reader` field (RS-LDOC-003) onto analysis artefacts, which are never pages (living-docs DEC-001 point 1). living-docs DEC-001 point 3 keeps a project's documentation rules in a set that inherits LDOC. Pages will reach WRITE only through `TECH` and `USER`, which inherit LDOC, so every page that takes WRITE will take LDOC beside it.
