---
id: DEC-075
title: The check names a paragraph that ends on a word kept off a line's end
status: proposed
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the engine keeps some words off the end of a line it breaks, such as a Czech one-letter word or short preposition, which moves to the next line with the word after it. A line feed the content writes ends a paragraph, and no break of the engine's crosses it, so a paragraph that ends on such a word ends its last line on it. The check names that paragraph and asks the piece's author for attention, since only the content can move the word. It never fails, since a paragraph may end on such a word on purpose, as a line of a list may end on a letter that names a variant. The finding lies in the content file of the scene's language, at the field or the run whose text holds the word. Its fix moves the line feed before the word, or rewords the paragraph's end. For example, the Czech content `"Spojení s\ndatabází"` is named, and `"Spojení\ns databází"` is not.

## Context

- **The engine's rules for a line's end.** The engine breaks lines by Unicode's rules and each language's own, which it keeps as data ([visual-communication:DEC-005-engine-and-plugins] point 4). In Czech, a one-letter word and a short preposition never end a line the engine breaks: each moves to the next line with the word after it ([project-kit#3084](https://github.com/aleskalfas/project-kit/issues/3084)). The capability's components page lists the words, under "Breaking lines".
- **A line feed ends a paragraph.** A line feed in a run's text ends a paragraph, and the next paragraph goes on in the same run ([visual-communication:DEC-012-text-runs] point 1). The engine breaks each paragraph apart, so it cannot carry a word across a line feed to the word after it.
- **Nothing names it.** The list of what the engine's checks report holds no such paragraph (DEC-005 point 14). Only a person who reads the page drawn in that language sees it. The showcase deck draws each page in Czech beside English, and its content writes line feeds ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)).

## Decision

**Where a line feed ends a paragraph of a text, and the paragraph ends on a word its scene's language keeps off a line's end, the check names the paragraph and asks the piece's author for attention, in the content file that holds the word. It never fails. The engine carries no word across the line feed.**

### 1. A paragraph ends on a word kept off a line's end

- **A kept word.** A *kept word* is a word the rules of a scene's language keep off the end of a line the engine breaks (DEC-005 point 4). The check reads them from the data the engine breaks lines by, by the primary subtag of the scene's language, as the engine reads them. A language with no rules of its own keeps no word.
- **Which paragraphs.** Each paragraph of a text in the scene that a line feed ends: every paragraph of the text but its last. The last, which the text's end ends, is not read (Rationale).
- **When it ends on one.** The paragraph's last word is a kept word, whole, and nothing but spaces follows it, as the engine's rules find a kept word before a space. So a full stop or a colon after the word ends the paragraph on no kept word, since the engine keeps no word such a mark follows.
- **Across its runs.** The check reads the paragraph's text whole, its runs joined, as the engine breaks it (DEC-012 point 4). So a kept word whose letters lie in two runs is one word, and a line feed in a later run than the word's ends its paragraph all the same.
- **In each scene.** It reads each text the scene holds, in each language and at each key over the size axes, by the paragraphs the scene holds for it.

### 2. The finding asks the piece's author for attention

- **Its level.** It asks for attention and never fails. A paragraph may end on a kept word on purpose, as a line of a list may end on a letter that names a variant, and no record makes the language's rule an invariant over a break the content makes ([visual-communication:DEC-002-files-and-validation] point 7).
- **Who acts.** The piece's author, whose content holds the word and the line feed.
- **Where it lies.** In the content file of the scene's language, at the key path of the run whose text holds the kept word's first letter, as that run's source names it: the field, where the field is given as text, and the run by its place among the field's runs, where it holds a list of runs (DEC-012 point 1). It names no library version. A field drawn on several pages gives one finding, since the content holds it once. A fact's text holds no line feed, so it gives none.
- **What it says.** The paragraph, by its place among the text's paragraphs, and the kept word, and that the line feed after the word ends the line, so no break carries the word on to the word after it. Its fix: move the line feed before the word, so that the word opens the next paragraph with the word after it, or reword the paragraph's end.
- **When it is found.** With the scene's other findings, and kept in the findings record (DEC-005 point 13). Each finding is one scene's, and the check compares no scenes. Its label is `kept-word-ends-paragraph`.
- **No reach.** No reader's instructions read the check's silence, so it states no reach. It counts as having measured no place, and its findings still reach every reader ([visual-communication:DEC-063-where-a-check-measures] point 1). The change that teaches a reader to read its silence writes its reach.
- **In the designer's round.** It fails nothing, so the designer does not mend it before the review ([visual-communication:DEC-070-ship-call-and-one-round] point 2). It reaches the review and the person in the viewing step's report, as every scene check's finding does ([visual-communication:DEC-062-checks-beside-the-frames] point 1). The round mends it only where the review reports it as one of the kinds DEC-070 point 3 names, and changes the words only as DEC-070 point 4 lets it.

### 3. The engine keeps the paragraphs the content writes

The engine carries no word across a line feed, drops no line feed and joins no two paragraphs to keep a word off a line's end. A paragraph that ends on a kept word stays as the content writes it, and the check names it.

## Rationale

**Why name it.** The engine keeps a kept word off the end of each line it breaks, so a reader meets one at a line's end only where a line feed of the content put it there. Only the content can move it, and an author who reads the page in another language never sees it. The finding names the field, where the author mends it.

**Why attention, never failing.** A one-letter word is a kept word whatever it means, so the rule also holds a letter that names a variant or a point, as in a list whose lines end "Varianta A" and "Varianta B". To fail would hold such content to a rule its author may rightly break, and a reading of taste fails nothing (DEC-002 point 7).

**Why only a paragraph a line feed ends.** A text's last paragraph ends where the text ends. A text that ends on a kept word most often ends on a letter that names a thing, such as a label "Bod A", since a phrase rarely ends on a preposition. Where a phrase runs on into the next text, the layout ends it, not a line feed, and a check of one text cannot read the next. A line feed is the author's break inside one text, and a word it cuts from the word it opens is a slip the author mends in place.

**Why at the content, by the run.** The fix lies in the words, so the finding points at the file a person edits, as every finding in what the content gave does (the capability's page of checks, "Scenes"). The run's key path names the run that holds the word, as a run's concept that no notation holds is named.

**Why the engine's own data.** A list of kept words of the check's own would drift from the engine's, and the check would then name a word the engine moves, or miss one it keeps. A new language's rules reach the check with the release that brings them to the engine.

**Why the engine keeps the line feed.** A line feed is the content's, and its paragraphs carry meaning, such as the lines of a terminal or of a list. To move a word across it would change what the content says.

### What it costs

- **A kept word meant to end a paragraph is named,** as a letter that names a variant, and nothing silences the finding. Its author reads past it, and it fails nothing. A word in the content that marks such a paragraph as meant would be an addition to the format for a finding that fails nothing.
- **A kept word that ends a text is not named,** nor one that ends a phrase another text goes on.

### Alternatives considered

- **Fail validation.** Rejected: a paragraph may end on a kept word on purpose.
- **Name the text's last paragraph too.** Rejected: a label that ends on a letter would be named in every piece, and a phrase another text goes on stays unread all the same.
- **Lie at the piece, by the text's trace id,** as letters that touch across lines do. Rejected: the fix lies in the content, and the trace leads there only through the scene's sources.
- **The engine carries the word across the line feed, or joins the paragraphs.** Rejected: that changes what the content says.
- **A list of kept words of the check's own.** Rejected: it would drift from the engine's.
- **A word in the content that marks a paragraph's kept word as meant.** Not taken: an addition to the format, for a finding that fails nothing (What it costs).

## Implications

- **Edits to accepted records,** made once this record is accepted, citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-005 point 4, its bullet "Lines broken by the engine".** "In Czech, for example, a one-letter word never ends a line." comes to read "In Czech, for example, a one-letter word never ends a line the engine breaks. A line feed the content writes ends a paragraph, and the engine carries no word across it, so the check names a paragraph that ends on such a word (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 3)." Its other sentences stand.
  - **The bullet, as it comes to read, whole:**

    > **Lines broken by the engine.** It breaks text into lines by Unicode's rules and each language's own rules, kept as data in the engine. So a new language's rules arrive with a release of the capability. In Czech, for example, a one-letter word never ends a line the engine breaks. A line feed the content writes ends a paragraph, and the engine carries no word across it, so the check names a paragraph that ends on such a word (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 3). The engine breaks a paragraph across its runs, each measured in its own typography role (refinement per [visual-communication:DEC-012-text-runs]).
  - **DEC-005 point 14, its bullet "Asks for attention, never failing".** It comes to read, whole:

    > **Asks for attention, never failing:** an overflow measured from a table or by an estimate, a loss nobody has accepted, and a paragraph that a line feed ends on a word its language keeps off a line's end (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 2).
- **The change that builds the check** builds points 1 to 3. Its tests plant, before a line feed in Czech content, a one-letter word and each short preposition, in lower case and in upper case, each in one run and with its letters in two runs, and find the paragraph named at the run's key path in the content file, asking the piece's author for attention. They find unnamed: a kept word that ends the text's last paragraph, one a full stop follows, a word that holds a kept word but is none, the same paragraph in a language with no rules, and a paragraph whose line feed comes before the kept word. They find the paragraphs the scene holds as the content writes them.
- **The capability's pages** come to say, in the change that builds the check: the page of checks, the finding's row among the scenes', with what it reads, its level, who acts, where it lies and its fix; the components page, under "Breaking lines", that the engine carries no word across a line feed, and that the check names a paragraph that ends on a kept word before one.
- **The capability's version moves,** a `minor`, since a project's validation gains a finding. It owes no migration: no file a project holds changes meaning.
- **Read against this record, and left as they stand:**
  - DEC-012 point 1. A line feed in a run's text ends a paragraph, as it says, and this record reads its paragraphs so.
  - DEC-002 point 7. Its bullet "A reading of taste never fails" holds the finding at attention, and no file gives the judgement it calls for, so the bullet gains nothing.
  - DEC-063 point 1. The check states no reach, which that point lets a check whose silence no reader's instructions read.
  - DEC-062 point 1. The viewing step's report gives the finding as it gives every scene check's.
  - DEC-070 points 2 to 4. The round treats the finding as it treats every finding that fails nothing.
- **Revisit this record** if a project's content gives such findings for words its authors mean, often enough to crowd its validation, or if a language's rules come to keep off a line's end a word that a line feed may rightly follow.
