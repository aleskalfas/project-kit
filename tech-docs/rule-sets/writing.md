---
rule-set: WRITE
version: 0.1.0
scope: [tech-docs/analysis/**]
rules:
  RS-WRITE-001:
    status: proposed
    origin: {why: "Something must show what matters most."}
  RS-WRITE-002:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. In the trial, the same labels in the same order were the largest gain for scanning."}
  RS-WRITE-003:
    status: proposed
    origin: {why: "Lists, nested lists and sub-headings over long paragraphs. Listing only series of three or more kept the trial's lists from cluttering the page."}
  RS-WRITE-004:
    status: proposed
    origin: {why: "Side matter interrupted each role's description. Moved last under Note, it left the description shorter with nothing dropped."}
  RS-WRITE-005:
    status: proposed
    origin: {why: "A script can check it. Both rewrites met it, and the longest sentence fell from 49 words to 25."}
  RS-WRITE-006:
    status: proposed
    origin: {why: "One idea per sentence halved the average sentence of the trial's prose."}
  RS-WRITE-007:
    status: proposed
    origin: {why: "Dense paragraphs were the original's main problem. Eight of its nine ran over four sentences."}
  RS-WRITE-008:
    status: proposed
    origin: {why: "Every semicolon in the original split cleanly into two sentences or a list."}
  RS-WRITE-009:
    status: proposed
    origin: {why: "Elided words such as \"the whole-repository report the developer\" slow every reader down."}
  RS-WRITE-010:
    status: proposed
    origin: {why: "The active voice says who acts. The passive stays where the actor receives, so needs keep \"be told\" and \"be asked\"."}
  RS-WRITE-011:
    status: proposed
    origin: {why: "Naming the harness behind \"it\" made a need clear, and the cited record confirmed the reading."}
  RS-WRITE-012:
    status: proposed
    origin: {why: "An outside dictionary's words changed the meaning of project terms in the trial. The project's own terms carry its meaning."}
  RS-WRITE-013:
    status: proposed
    origin: {why: "A need is one sentence, and an actor's needs are joined into one reader description. First person keeps the actor's voice."}
    pkit:
      friction:
        anchors:
          path: [.pkit/capabilities/software-analysis/scripts/_lib/readers.py]
          record: ["software-analysis:DEC-001"]
  RS-WRITE-014:
    status: proposed
    origin: {why: "Every meaning change in the trial came from a resolved ambiguity, a guard turned into a goal, or a swapped term or citation."}
---

# WRITE — writing for project-kit's documentation

These rules say how project-kit writes its documentation and its analysis.

- **What matters most:** the meaning. A rewrite keeps it (RS-WRITE-014).
- **Where the rules apply:**
  - every page of the technical and user spaces, through their definitions, `TECH` and `USER`, which inherit this set
  - the analysis under `tech-docs/analysis/`, this set's own scope
- **Where they come from:** a style trial in October 2026. It rewrote the core actors document by ASD-STE100 and by ISO 24495-1, and kept what helped.
- **How a rule reads:** one statement, then why and how, then one example. Each *before* is quoted from the trial's documents, so it may break the rule it shows.
- **Note:** how rules are named, accepted and inherited is the rule-set record's (COR-051). A rule binds only once it is accepted.

## Structure

These rules lay a document out so that a reader can scan it.

### RS-WRITE-001 — Open with what it is about

Open each section with one line that says what the section is about.

- **Why:** the reader meets the subject before the detail, and can stop or skip at that line (ISO 24495-1, 5.2.2).
- **How:** name the thing in the first line. Put its parts in the lines below it.
- **Example:**
  - Before: "The person who adopts the methodology for a project and keeps its setup: what is installed, at which version, which of their own additions sit beside it, and which checks the project's merges wait on."
  - After: "The person who adopts the methodology for a project and keeps its setup." The setup follows as a labelled list.

### RS-WRITE-002 — Parallel sections share their labels

Give parallel sections the same bold labels, in the same order.

- **Why:** a reader can jump to the same label in any section (ISO 24495-1, 5.2.3 a).
- **How:** choose the labels once for the whole document. A label says what follows it, such as *When they come*.
- **Example:**
  - Before: "They come for every unit of work, and again when some work recurs often enough to deserve tooling of its own. They bring the change and direct agents to make it."
  - After: "**When they come:** for every unit of work, and again when some work recurs often enough to deserve tooling of its own." Then "**What they bring:** the change. They direct agents to make it."

### RS-WRITE-003 — A list for three or more

Put a series of three or more items in a list with a lead-in, and keep a series of two in the sentence.

- **Why:** a list shows its items at a glance, but a list for every pair clutters the page (Federal Plain Language Guidelines, "Use lists").
- **How:** the lead-in is a label or a sentence that says what the list holds. Nest a list where an item has parts of its own.
- **Example:**
  - Before: "That can be an adopter growing a discipline in their own repository, an organisation that keeps private methodology in one repository for its others, or whoever adapts the methodology to a new harness."
  - After: "**Who this can be:**", then one list item for each of the three.

### RS-WRITE-004 — Side matter last, under *Note*

Put side matter last in its section, under the label *Note*.

- **Why:** the main description stays short, and nothing is dropped (ISO 24495-1, 5.2.5).
- **How:** side matter is a reason for a name, an exception that holds only in this project, or an overlap with another document.
- **Example:**
  - Before: in the middle of the merge authoriser's paragraph, "The name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."
  - After: as the section's last item, "**Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028)."

## Sentences and paragraphs

These rules keep each sentence and paragraph short enough to read once.

### RS-WRITE-005 — At most 25 words a sentence

Keep every sentence to 25 words or fewer, and count the words in parentheses too.

- **Why:** short sentences are easier for every reader, and a script can check the limit (ASD-STE100, 6.3).
- **How:**
  - A word is anything between spaces. An id, a file name or a hyphenated word counts as one.
  - A list item ends a sentence. A lead-in that ends in a colon is one sentence.
  - Code, headings and text quoted word for word are not counted.
- **Example:**
  - Before (38 words): "Core: the backbone ships no workflow, only checks made to run unattended, which bind once the project makes them a required status (COR-050 point 12), and one base a pipeline names for all of them (COR-054 point 3)."
  - After: "the backbone ships no workflow. It ships only:", then one list item for the checks and one for the base.

### RS-WRITE-006 — One idea per sentence

Give each sentence of prose one idea.

- **Why:** a sentence with one idea is read once (Federal Plain Language Guidelines, "Write short sentences").
- **How:**
  - Split where one idea ends, then check that the parts still agree. One split in the trial turned "only checks …, and one base" into "only checks", then "also one base".
  - Needs follow RS-WRITE-013 instead.
- **Example:**
  - Before: "every change passes the acceptance gate and the friction check, whatever tracks the work, and lands as COR-009 sets out."
  - After: "every change passes the acceptance gate and the friction check, whatever tracks the work. It lands as COR-009 sets out."

### RS-WRITE-007 — One topic a paragraph, at most four sentences

Give each paragraph one topic and no more than four sentences.

- **Why:** a dense paragraph hides what each of its sentences is about (ASD-STE100, 6.4 to 6.6).
- **How:** a list item counts as a paragraph. Labels and lists are the usual fix (RS-WRITE-002, RS-WRITE-003).
- **Example:**
  - Before: the operator's section, one paragraph of five sentences on six topics.
  - After: an opening of two sentences, then one labelled item for each topic, none over two sentences.

### RS-WRITE-008 — No semicolons

Write no semicolons in prose.

- **Why:** a semicolon joins two sentences that read better apart (ASD-STE100, 8.1).
- **How:** make two sentences, or a list. Join two citations in one parenthesis with a comma. Code and text quoted word for word are exempt.
- **Example:**
  - Before: "The role is per machine and per clone; it is not whoever holds the repository's settings, …"
  - After: "The role is per machine and per clone." The rest moved to the section's *Note*.

### RS-WRITE-009 — No omitted words

Write out every word that a reader would otherwise have to supply.

- **Why:** an omitted verb or noun slows every reader down, and most of all a reader whose first language is not English (ASD-STE100, 4.2).
- **How:** in a series of clauses, give each clause its own verb.
- **Example:**
  - Before: "the change check serves the developer and the merge authoriser, the whole-repository report the developer"
  - After: "The change check serves the developer and the merge authoriser." Then "The whole-repository report serves the developer."

### RS-WRITE-010 — The active voice when the actor is known

Use the active voice when you know who acts, and keep the passive where the actor receives.

- **Why:** the active voice says who does what. In "Be told when …", the actor receives, so the passive is right (Federal Plain Language Guidelines, "Use active voice").
- **How:** in a rewrite, you know only the actors that the source names. A rewrite never adds one (RS-WRITE-014).
- **Example:**
  - Before: "… and let the system validate them" (a rewrite)
  - After: "… and have them validated" (the original). The original names no actor, so the passive stays.

## Words and terms

These rules make each word point at one thing.

### RS-WRITE-011 — Name what a pronoun stands for

Replace a pronoun with the noun it stands for when the pronoun could point at two things.

- **Why:** a reader who picks the wrong referent learns a wrong fact, and nothing warns them.
- **How:** in a rewrite, take the referent from a cited source or from the author (RS-WRITE-014).
- **Example:**
  - Before: "how far it meets them"
  - After: "how far that harness meets each requirement". COR-047 confirms that the harness is meant.

### RS-WRITE-012 — One term for one thing, from the glossary

Use one term for one thing, and take it from the project's glossary, not from an outside dictionary.

- **Why:** project terms such as *review*, *land* and *retire* have defined meanings. A dictionary's nearest word changed those meanings in the trial.
- **How:**
  - Until the glossary holds a word, use the word that the project's records use.
  - Where a document uses two terms, ask the author whether they name one thing.
- **Example:**
  - Before: "When the same person examines a record or rule that an agent wrote as a draft, that record or rule becomes mandatory." (a rewrite)
  - After: "the same person's review turns a record or rule an agent drafted into a binding one" (the original). Reading a draft does not make it binding. The review does.

## Needs

This rule is for the needs of an actor in the analysis.

### RS-WRITE-013 — One need, one sentence

Write each need as one imperative sentence of at most 25 words, in the actor's own first person.

- **Why:** software-analysis defines a need as "a need in one sentence" (its DEC-001 point 1). It joins an actor's needs into one reader description.
- **How:**
  - Start with the verb, or with *Never* before it.
  - Never split a need into two sentences.
  - Keep *I*, *me* and *my*. Count words as RS-WRITE-005 does.
- **Example:**
  - Before: "Run every check with no terminal and no person to answer. Gate the merge on the check's exit status." (a rewrite)
  - After: "Run every check with no terminal and no person to answer, and gate the merge on its exit status." (the original)

## Keeping meaning

This rule protects what a text says whenever someone rewrites it.

### RS-WRITE-014 — A rewrite keeps the meaning

A rewrite never resolves an ambiguity, turns a *never* into an *only*, or swaps a project term or a citation form without the author.

- **Why:** every meaning change in the trial came from one of these. A style rule must never change a fact.
- **How:**
  - Flag the passage for the author, and keep the original until the author answers.
  - A citation form includes its locator, such as "release README:22-29".
  - Where another rule of this set would change what a text says, this rule wins.
- **Example:**
  - Before: "Ship a backbone change that breaks installed projects only with the migration that carries them across." (a rewrite)
  - After: "Never ship a backbone change that breaks installed projects without the migration that carries them across." (the original). The *only* form reads as a wish to ship breaking changes.

## Considered and not adopted

The trial tested these rules and left them out:

- **ASD-STE100's dictionary, and the rules built on it:** its 875 words serve aircraft maintenance. Project verbs such as *land*, *ship* and *retire* are not among them.
- **ASD-STE100's approved meanings:** each word keeps one physical sense. Eight of the trial's nine meaning changes came from them.
- **ASD-STE100's count of a parenthesis as a sentence of its own:** it let a 35-word need pass a 25-word limit. RS-WRITE-005 counts the parenthesis in.
- **ASD-STE100's American spelling:** the project writes British English, and its ids carry it, as in `ACT-merge-authoriser`.
- **ISO 24495-1's familiar words, in analysis artefacts:** almost every noun there is a project term. RS-WRITE-012 takes terms from the glossary instead.
- **ISO 24495-1's "leave out what readers do not need", in analysis artefacts:** every cut drops a fact. RS-WRITE-004 moves side matter under *Note* instead.
