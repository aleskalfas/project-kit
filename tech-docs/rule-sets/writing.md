---
rule-set: WRITE
version: 0.1.0
scope: [tech-docs/analysis/**]
rules:
  RS-WRITE-001:
    status: proposed
    origin: {why: "Something must show what matters most. In the trial, opening each section with who the actor is made every section scannable (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-002:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, the same labels in the same order were the largest gain for scanning. A reader can jump to one label in any section (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-003:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, pairs and short series stayed in the sentence, so the lists did not clutter the page (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-004:
    status: proposed
    origin: {why: "Side matter interrupted each role's description. Moved last under Note, it left the description shorter with nothing dropped (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-005:
    status: proposed
    origin: {why: "Short sentences are easier for every reader. The original had ten body sentences over 25 words, and both rewrites brought every one to 25 or fewer (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-006:
    status: proposed
    origin: {why: "A sentence with one idea is read once. One idea per sentence halved the average sentence of the trial's prose (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-007:
    status: proposed
    origin: {why: "A dense paragraph hides what each of its sentences is about. Dense paragraphs were the original's main problem, and eight of its nine ran over four sentences (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-008:
    status: proposed
    origin: {why: "A semicolon joins two sentences that read better apart. Three of the original's four semicolons split cleanly into sentences or a list. The fourth joined two citations, where a comma would be ambiguous, since a citation can hold a comma itself (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-009:
    status: proposed
    origin: {why: "An elided verb, as in \"the whole-repository report the developer\", slows every reader down. It slows most a reader whose first language is not English (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-010:
    status: proposed
    origin: {why: "A reader who picks the wrong referent learns a wrong fact, and nothing warns them. In the trial, naming the harness behind \"it\" made a need clear (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-011:
    status: proposed
    origin: {why: "Project terms such as review, land and retire have defined meanings. An outside dictionary's nearest words changed those meanings in the trial (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
  RS-WRITE-012:
    status: proposed
    origin: {why: "A need is one sentence, and so is a use case's goal (software-analysis DEC-001 point 1). An actor's needs are joined into one reader description, and first person keeps the actor's voice (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
    pkit:
      friction:
        anchors:
          path: [.pkit/capabilities/software-analysis/scripts/_lib/readers.py]
          record: ["software-analysis:DEC-001"]
  RS-WRITE-013:
    status: proposed
    origin: {why: "A style that changes meaning is disqualified for analysis artefacts. In the trial, rewrites by both guidelines changed what statements claim (.pkit/scratchpad/done/2026-10-05-writing-style-trial.md)."}
---

# WRITE — writing for project-kit's documentation

These rules say how project-kit writes its documentation and its analysis.

- **What matters most:** the meaning. A rewrite keeps it (RS-WRITE-013).
- **Where the rules apply:**
  - every page of the technical and user spaces, through their definitions, `TECH` and `USER`, which inherit this set
  - the analysis under `tech-docs/analysis/`, this set's own scope
- **Where they come from:** a style trial in October 2026. It rewrote the core actors document by ASD-STE100 and by ISO 24495-1, and kept what helped. The trial, and what it left out, are in `.pkit/scratchpad/done/2026-10-05-writing-style-trial.md`.
- **How a rule reads:** a statement, then *How*, then text that *Breaks it* and text that *Keeps it*. Unless an example says otherwise, *Breaks it* quotes the original actors document and *Keeps it* the plain rewrite. A rule's reason is the `why` of its origin, in the front matter (COR-051 point 5).
- **Note:** how rules are named, accepted and inherited is the rule-set record's (COR-051). A rule binds only once it is accepted.

## Structure

These rules lay a document out so that a reader can scan it.

### RS-WRITE-001 — Open with what matters most

Open each section with one sentence that says what matters most in it.

- **How:** keep that sentence to what matters most, and put the detail in the lines below it.
- **Breaks it:** "The person who adopts the methodology for a project and keeps its setup: what is installed, at which version, which of their own additions sit beside it, and which checks the project's merges wait on."
- **Keeps it:** "The person who adopts the methodology for a project and keeps its setup." The setup follows as a labelled list.

### RS-WRITE-002 — Parallel sections share their labels

Give parallel sections their bold labels from one list, in that list's order.

- **How:** choose the list once for the whole document. A section may leave out a label it has nothing for. A label says what follows it, such as *When they come*.
- **Breaks it:** "They come for every unit of work, and again when some work recurs often enough to deserve tooling of its own. They bring the change and direct agents to make it."
- **Keeps it:** "**When they come:** for every unit of work, and again when some work recurs often enough to deserve tooling of its own." Then "**What they bring:** the change. They direct agents to make it."

### RS-WRITE-003 — A list for a series that carries detail

Put a series of three or more items in a list with a lead-in when the items are clauses or carry detail of their own.

- **How:**
  - The lead-in is a label or a sentence that says what the list holds. Nest a list where an item has parts of its own.
  - A series of two stays in the sentence, and so does a series of short phrases, such as "decisions, rules, notes, code and its documentation".
  - Needs and table cells are exempt. A need is one sentence (RS-WRITE-012), and a table cell holds no list.
- **Breaks it:** "That can be an adopter growing a discipline in their own repository, an organisation that keeps private methodology in one repository for its others, or whoever adapts the methodology to a new harness."
- **Keeps it:** "**Who this can be:**", then one list item for each of the three.

### RS-WRITE-004 — Side matter last, under *Note*

Put side matter last in its section, under the label *Note*.

- **How:** side matter is any of these:
  - the reason for a name
  - a fact that holds for project-kit alone, and not for the projects that adopt the methodology
  - an overlap with another document
- **Breaks it:** in the middle of the merge authoriser's paragraph, "The name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."
- **Keeps it:** as the section's last item, "**Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."

## Sentences and paragraphs

These rules keep each sentence and paragraph short enough to read once.

### RS-WRITE-005 — At most 25 words a sentence

Keep every sentence to 25 words or fewer, and count the words in parentheses too.

- **How:** count as the trial did.
  - A word is a token between spaces that holds a letter or a digit, once bold marks and backticks are removed. An id, a file name or a hyphenated word is one word.
  - A sentence ends at a full stop, a question mark or an exclamation mark before a space or a line end. Each list item and each need ends one too.
  - A lead-in that ends in a colon is one sentence. Colons and semicolons end none.
  - Headings, bold labels, code blocks and quoted examples of a broken rule are not counted.
- **Breaks it (38 words):** "Core: the backbone ships no workflow, only checks made to run unattended, which bind once the project makes them a required status (COR-050 point 12), and one base a pipeline names for all of them (COR-054 point 3)."
- **Keeps it:** "the backbone ships no workflow. It ships only:", then one list item for the checks and one for the base.

### RS-WRITE-006 — One idea per sentence

Give each sentence of prose one idea.

- **How:**
  - Split where one idea ends, then check that the parts still agree. One split in the trial turned "only checks …, and one base" into "only checks", then "also one base".
  - Needs follow RS-WRITE-012 instead.
- **Breaks it:** "every change passes the acceptance gate and the friction check, whatever tracks the work, and lands as COR-009 sets out."
- **Keeps it:** "every change passes the acceptance gate and the friction check, whatever tracks the work. It lands as COR-009 sets out."

### RS-WRITE-007 — One topic a paragraph, at most four sentences

Give each paragraph one topic and no more than four sentences.

- **How:** a list item counts as a paragraph. Labels and lists are the usual fix (RS-WRITE-002 and RS-WRITE-003). Four is project-kit's choice. ASD-STE100 allows six (its 6.6).
- **Breaks it:** the operator's section, one paragraph of five sentences on six topics.
- **Keeps it:** an opening of two sentences, then one labelled item for each topic, none over two sentences.

### RS-WRITE-008 — No semicolons

Write no semicolons in prose.

- **How:** make two sentences, or a list. Where two citations share a parenthesis, join them with "and", as in "(PRJ-002 and release README:22-29)". Each citation keeps its own form (RS-WRITE-013). Code and text quoted word for word are exempt.
- **Breaks it:** "The role is per machine and per clone; it is not whoever holds the repository's settings, …"
- **Keeps it:** "The role is per machine and per clone." The rest moved to the section's *Note*.

### RS-WRITE-009 — Each clause has its own verb

In a series of clauses, give each clause its own verb.

- **How:** repeat a verb that two clauses share, rather than leave the reader to supply it.
- **Breaks it:** "the change check serves the developer and the merge authoriser, the whole-repository report the developer"
- **Keeps it:** "The change check serves the developer and the merge authoriser." Then "The whole-repository report serves the developer."

## Words and terms

These rules make each word point at one thing.

### RS-WRITE-010 — Name what a pronoun stands for

Replace a pronoun with the noun it stands for when the pronoun could point at two things.

- **How:** in a rewrite, take the noun from the author, or from a cited source that the author confirms (RS-WRITE-013).
- **Breaks it:** "say requirement by requirement how far it meets them". *It* could be the methodology or the harness.
- **Keeps it:** "Say how far that harness meets each requirement", once the author confirms the reading that COR-047 gives.

### RS-WRITE-011 — One term for one thing, from the glossary

Use one term for one thing, and take it from the project's glossary, not from an outside dictionary.

- **How:** until the glossary holds a word, use the word that the project's records use. Where a document uses two terms, ask the author whether they name one thing.
- **Breaks it:** the developer comes "for every unit of work", and the merge authoriser "at the end of each piece of work". The two terms may name one thing.
- **Keeps it:** one of the two in both places, once the author confirms that they name one thing. The first ASD-STE100 rewrite chose "task" for both without asking.

## Needs and goals

This rule is for an actor's needs and a use case's goal, in the analysis.

### RS-WRITE-012 — One need or goal, one sentence

Write each need of an actor, and each use case's goal, as one first-person sentence that starts with its verb.

- **How:**
  - *Never* may come before the verb. Keep *I*, *me* and *my*.
  - Never split one into two sentences, and keep it within the limit of RS-WRITE-005.
  - A use case's goal is the same user story as a need (software-analysis DEC-001 point 1), so it takes the same form.
- **Breaks it:** "Run every check with no terminal and no person to answer. Gate the merge on the check's exit status." (the plain rewrite)
- **Keeps it:** "Run every check with no terminal and no person to answer, and gate the merge on its exit status." (the original)

## Keeping meaning

This rule protects what a text says whenever someone rewrites it.

### RS-WRITE-013 — A rewrite keeps the meaning

A rewrite adds, drops, weakens or narrows no claim, and asks the author wherever it would have to choose a reading.

- **How:** flag the passage for the author, and keep the original until the author answers. Project terms and citations stay as written, and a citation's form includes its locator, such as "release README:22-29". This rule wins wherever another rule of this set would change what a text says. The trial's rewrites changed what a text says in each of these ways:
  - **Adding:** the original "have them validated" names no validator, and the rewrite "let the system validate them" names one.
  - **Dropping:** "every change *passes* the acceptance gate" became "the acceptance gate and the friction check *examine* each change". The duty to pass is gone.
  - **Weakening:** "*Carry* the projects … *across* a breaking change" became "*Help* the projects … to continue to operate". Dropping *own* or *itself* weakens a claim too.
  - **Narrowing:** "*answer* what the methodology gates" became "*accepts or rejects the prompts* at the gates".
  - **Swapping a term:** "the same person's *review* turns a record or rule … into a binding one" became "When the same person *examines* a record or rule …". Reading a draft does not make it binding.
  - **Changing a citation's form:** "(:65, :67)" became "(lines 65 and 67)".
  - **Splitting into parts that disagree:** "only checks …, and one base" became "only checks", then "also one base".
  - **Choosing a reading:** in "knowing what each change … means for them", one rewrite made the adopters the ones who know, and the other the maintainer. A pronoun's referent is a reading too (RS-WRITE-010).
- **Breaks it:** "Ship a backbone change that breaks installed projects only with the migration that carries them across." (the plain rewrite)
- **Keeps it:** "Never ship a backbone change that breaks installed projects without the migration that carries them across." (the original). The *only* form reads as a wish to ship breaking changes.
