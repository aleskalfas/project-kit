---
id: DEC-075
title: The check names a paragraph that ends on a word kept off a line's end
status: proposed
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the engine keeps some words off the end of a line it breaks, such as a Czech one-letter word or short preposition, which moves to the next line with the word after it. A line feed the content writes ends a paragraph, and no break of the engine's crosses it. So where such a word comes right before a line feed, and the text goes on after it, the word ends a line, cut from the word it is kept with. The check names that paragraph and asks the piece's author for attention, since only the content can move the word. It never fails, since a paragraph may end on such a word on purpose, as a line of a list may end on a letter that names a variant. The finding lies in the content file of the scene's language, at the field or the run whose text holds the word. Its fix moves the word past the line feeds after it, or rewords the paragraph's end. For example, the Czech content `"Spojení s\ndatabází"` is named, and `"Spojení\ns databází"` is not, nor is `"Spojení s\n"`, where no word follows the line feed.

## Context

- **The engine's rules for a line's end.** The engine breaks lines by Unicode's rules and each language's own, which it keeps as data ([visual-communication:DEC-005-engine-and-plugins] point 4). In Czech, a one-letter word and a short preposition never end a line the engine breaks: each moves to the next line with the word after it ([project-kit#3084](https://github.com/aleskalfas/project-kit/issues/3084)). The capability's components page lists the words, under "Breaking lines".
- **A line feed ends a paragraph.** A line feed in a run's text ends a paragraph, and the next paragraph goes on in the same run ([visual-communication:DEC-012-text-runs] point 1). The engine breaks each paragraph apart, so it cannot carry a word across a line feed to the word after it.
- **Two accepted points that do not meet.** DEC-005 point 4 says that in Czech a one-letter word never ends a line, and DEC-012 point 1 lets a line feed the content writes end a line on one. Both cannot hold where a line feed follows such a word. Point 3 settles it: the engine keeps the content's line feeds, and DEC-005 point 4's sentence holds of the lines the engine breaks.
- **Only a reader of the language sees it.** A line that ends on such a word reads as a slip only to a reader of its language, so an author who reads the page in another language never sees it. The showcase deck draws each page in Czech beside English, and its content writes line feeds ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)).

## Decision

**Where a word its scene's language keeps off a line's end comes, in text the content gives, before nothing but spaces, then a line feed, then a word of the same text, the check names the paragraph the word ends and asks the piece's author for attention, in the content file that holds the word. It never fails. The engine carries no word across the line feed.**

### 1. A paragraph ends on a word kept off a line's end, and its text goes on

- **A kept word.** A *kept word* is a word the rules of a scene's language keep off the end of a line the engine breaks (DEC-005 point 4). The check reads them from the data the engine breaks lines by, by the primary subtag of the scene's language, as the engine reads them. A language with no rules of its own keeps no word.
- **What bounds a word.** A word's edges are the engine's own. The check finds a kept word wherever the engine's rules find one, and only there, whatever the word means (What it costs).
- **When the check names one.** The kept word is whole, and after it come nothing but spaces, then a line feed, then a word of the same text, past nothing but spaces and further line feeds. The paragraph that line feed ends is the one named. So a full stop or a colon after the word leaves the paragraph unnamed, since the engine keeps no word such a mark follows. So does the text's end after the word, past nothing but spaces and line feeds, as where a YAML `|` block adds a line feed to the text: `"Bod A\n"` and `"Spojení s\n"` are not named, as `"Bod A"` is not.
- **Across its runs.** The check reads the paragraph's text whole, its runs joined, as the engine breaks it (DEC-012 point 4). So a kept word whose letters lie in two runs is one word, and a line feed in a later run than the word's ends its paragraph all the same.
- **Only text the content gives.** The check reads only runs whose text the content gives. A component's own text, a value its file gives, is not read, since its mend lies in that file, whose owner the check does not name.
- **In each scene.** It reads each text the scene holds, in each language and at each key over the size axes, by the paragraphs the scene holds for it.

### 2. The finding asks the piece's author for attention

- **Its level.** It asks for attention and never fails. A paragraph may end on a kept word on purpose, as a line of a list may end on a letter that names a variant, and no record makes the language's rule an invariant over a break the content makes ([visual-communication:DEC-002-files-and-validation] point 7).
- **Who acts.** The piece's author, whose content holds the word and the line feed.
- **Where it lies.** In the content file of the scene's language, at the key path of the run whose text holds the kept word's first letter, as that run's source names it: the field, where the field is given as text, and the run by its place among the field's runs, where it holds a list of runs (DEC-012 point 1). It names no library version. A field drawn on several pages gives one finding, since the content holds it once.
- **What it says.** The paragraph, by its place among the text's paragraphs, and the kept word, and that the line feed after the word ends the line, so no break carries the word on to the word after it. Its fix: move the word past the line feeds after it, so that it opens the paragraph of the word after it, or reword the paragraph's end.
- **In the asker's words.** The first fix changes no word, only where the line feeds lie, so it changes none of the asker's words, which [visual-communication:DEC-070-ship-call-and-one-round] point 4 names by their words. The designer may then make it in them without asking, where the meaning holds, and tells the person afterwards, as of every change it makes alone. Rewording the paragraph's end there changes them, and waits for the asker's word, as that point says.
- **Its label** is `kept-word-ends-paragraph`. The check compares no scenes, since a paragraph's finding in one scene rests on no other.
- **No reach.** It states no reach, since no reader's instructions read its silence ([visual-communication:DEC-063-where-a-check-measures] point 1).

### 3. The engine keeps the paragraphs the content writes

The engine carries no word across a line feed, drops no line feed and joins no two paragraphs to keep a word off a line's end. A paragraph that ends on a kept word stays as the content writes it, and the check names it where point 1 says.

## Rationale

**Why name it.** The engine keeps a kept word on a line with the word after it, so a reader meets one cut from the word after it only where a line feed of the content cut it. Only the content can move it, and an author who reads the page in another language never sees it. The finding names the field, where the author mends it.

**Why attention, never failing.** A one-letter word is a kept word whatever it means, so the rule also holds a letter that names a variant or a point, as in a list whose lines end "Varianta A" and "Varianta B". To fail would hold such content to a rule its author may rightly break, and a reading of taste fails nothing (DEC-002 point 7).

**Why only where a word follows.** A kept word with no word after it in its text, at the text's end or before only line feeds, has no word to be kept with, and no break the engine makes would place it otherwise. Where a phrase runs on into another text, the layout ends it, not a line feed, and a check of one text cannot read the next. A line feed with more of the text after it is the author's break inside one text, and a word it cuts from the word after it is a slip the author mends in place.

**Why a check of the scene.** It reads a paragraph's runs joined as the engine breaks them, and only text a part draws, both of which the scene holds: a check of the content files reads neither, and the engine, which breaks each line as its rules say, has nothing of its own to report.

**Why at the content, by the run.** The fix lies in the words, so the finding points at the file a person edits, as every finding in what the content gave does (the capability's page of checks, "Scenes"). The run's key path names the run that holds the word, as a run's concept that no notation holds is named.

**Why the engine's own data.** A list of kept words of the check's own would drift from the engine's, and the check would then name a word the engine moves, or miss one it keeps. A new language's rules reach the check with the release that brings them to the engine.

**Why the engine keeps the line feed.** A line feed is the content's, and its paragraphs carry meaning, such as the lines of a terminal or of a list. To move a word across it would change what the content says.

### What it costs

- **The engine's edges name meant words too,** each a word of one letter as the engine bounds one: a terminal's or code's line that ends on a flag (`ls -a`), a unit after a number (`5 m`), an apostrophe left untranslated (`pkit's`), a variable of one letter, a Roman numeral of one letter and a letter that names a variant. Each is named before a line feed and a word, and nothing silences the finding: its author reads past it, and it fails nothing. A filter that left them out would be a rule the engine lacks, so the check would read a paragraph by rules its lines do not break by.
- **A kept word that ends a text is not named,** though a phrase may go on in another text the layout places after it.
- **A kept word in a component's own text is not named,** so its library's owner finds it only by reading the page.

### Alternatives considered

- **Fail validation.** Rejected: a paragraph may end on a kept word on purpose.
- **Read every paragraph of a text but its last.** Rejected: a text that ends in a line feed, as a YAML `|` block does, would be named where no word follows its kept word.
- **Name a kept word that ends the text too.** Rejected: no word follows it for the engine to keep it with, and a phrase another text goes on stays unread all the same.
- **Read a component's own text too.** Rejected: the finding would lie in a file whose owner the check does not name.
- **Lie at the piece, by the text's trace id,** as letters that touch across lines do. Rejected: the fix lies in the content, and the trace leads there only through the scene's sources.
- **The engine carries the word across the line feed, or joins the paragraphs.** Rejected: that changes what the content says.
- **A list of kept words of the check's own.** Rejected: it would drift from the engine's.
- **A word in the content that marks a paragraph's kept word as meant.** Not taken: an addition to the format, for a finding that fails nothing.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-005 point 4, its bullet "Lines broken by the engine".** "In Czech, for example, a one-letter word never ends a line." comes to read "In Czech, for example, a one-letter word never ends a line the engine breaks. A line feed the content writes ends a paragraph, and the engine carries no word across it, so the check names a paragraph that a line feed ends on a word its language keeps off a line's end, where a word of the same text follows (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 3)." Its other sentences stand. The edit narrows the sentence to what the bullet's heading already covers, the lines the engine breaks, so it refines the point and overturns none of it.
  - **The bullet, as it comes to read, whole:**

    > **Lines broken by the engine.** It breaks text into lines by Unicode's rules and each language's own rules, kept as data in the engine. So a new language's rules arrive with a release of the capability. In Czech, for example, a one-letter word never ends a line the engine breaks. A line feed the content writes ends a paragraph, and the engine carries no word across it, so the check names a paragraph that a line feed ends on a word its language keeps off a line's end, where a word of the same text follows (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 3). The engine breaks a paragraph across its runs, each measured in its own typography role (refinement per [visual-communication:DEC-012-text-runs]).
  - **DEC-005 point 14, its bullet "Asks for attention, never failing".** It comes to read, whole:

    > **Asks for attention, never failing:** an overflow measured from a table or by an estimate, a loss nobody has accepted, and a paragraph that a line feed ends on a word its language keeps off a line's end, where a word of the same text follows (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 2).
- **The change that builds the check** builds points 1 to 3. Its tests plant, in Czech content, before a line feed and a word of the same text: a one-letter word and each short preposition, in lower case and in upper case, each in one run; a preposition with its letters in two runs; a kept word with spaces after it; one in a run before the run that holds the line feed; and one before two line feeds. They find each paragraph named at the run's key path in the content file, asking the piece's author for attention. They find unnamed: a kept word with nothing after it to the text's end but spaces and line feeds, as in `"Spojení s\n"`; one a full stop follows; a word that holds a kept word but is none; the same paragraph in a language with no rules; a paragraph whose line feed comes before the kept word; and a kept word in a component's own text. They find the paragraphs the scene holds as the content writes them.
- **The capability's pages** come to say, in the change that builds the check: the page of checks, the finding's row among the scenes', with what it reads, its level, who acts, where it lies and its fix; the components page, under "Breaking lines", that the engine carries no word across a line feed, and that the check names a paragraph that a line feed ends on a kept word, where a word of the same text follows.
- **The capability's version moves,** a `minor`, since a project's validation gains a finding. It owes no migration: no file a project holds changes meaning. An existing piece gives the finding in validation from its next render, or once a file its scenes are computed from changes, not from the release: the findings record's key holds no engine version, so a record that still verifies is read as its render wrote it (DEC-005 point 13). The change's changeset says so.
- **Read against this record, and left as they stand:**
  - DEC-012 point 1. A line feed in a run's text ends a paragraph, as it says, and this record reads its paragraphs so.
  - DEC-002 point 7. Its bullet "A reading of taste never fails" holds the finding at attention, and no file gives the judgement it calls for, so the bullet gains nothing.
  - DEC-005 point 13. The finding is found with the scene's other findings and kept in the findings record, as every scene finding is, and the record's key gains no engine version.
  - DEC-063 point 1. The check states no reach, which that point lets a check whose silence no reader's instructions read. It then counts as having measured no place, and its findings still reach every reader.
  - [visual-communication:DEC-062-checks-beside-the-frames] point 1. The viewing step's report gives the finding as it gives every scene check's, from scenes it computes itself.
  - DEC-070 points 2 and 3. The finding fails nothing, so the designer does not mend it before the review, and the round mends it only where the review reports it as one of the kinds point 3 names.
  - DEC-070 point 4. It names the asker's words by their words, and a line feed is none, so the point gains nothing (this record's point 2).
- **Revisit this record** if a project's content gives such findings for words its authors mean, often enough to crowd its validation, or if a language's rules come to keep off a line's end a word that a line feed may rightly follow.
