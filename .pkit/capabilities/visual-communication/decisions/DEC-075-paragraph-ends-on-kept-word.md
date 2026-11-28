---
id: DEC-075
title: The check names a paragraph that ends on a word kept off a line's end
status: proposed
date: 2026-11-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the engine keeps some words off the end of a line it breaks, as the rules of the scene's language say: each such kept word moves to the next line with the word after it. A line feed in a text ends a paragraph, and no break of the engine's crosses it. So where such a word comes right before a line feed written in the text, and the text goes on after it, the word ends a line, cut from the word it is kept with. The check names that paragraph and asks for attention where the text is written, since only a change to the text can move the word. It never fails, since a paragraph may end on such a word on purpose, as a line of a list may end on a label whose letters spell a kept word. For the piece's own words, the finding lies in the content file of the scene's language, at the field or the run whose text holds the word. Its fix moves the word past the line feeds after it, or rewords the paragraph's end. For example, a text that holds a kept word, then a line feed, then more text, is named. A text that holds the line feed before the kept word is not, nor is one where only spaces and line feeds follow the kept word.

## Context

- **The engine's rules for a line's end.** The engine breaks lines by Unicode's rules and each language's own, which it keeps as data ([visual-communication:DEC-005-engine-and-plugins] point 4). A language's rules may keep a word off the end of a line the engine breaks, and the word then moves to the next line with the word after it ([project-kit#3084](https://github.com/aleskalfas/project-kit/issues/3084)). The capability's components page states each language's rules, under "Breaking lines", and gives them as rules on a word followed by a space.
- **A line feed ends a paragraph.** A line feed in a run's text ends a paragraph, and the next paragraph goes on in the same run ([visual-communication:DEC-012-text-runs] point 1). The engine breaks each paragraph apart, so it cannot carry a word across a line feed to the word after it.
- **Where the two points met.** DEC-005 point 4's example of one language's rule, that a word the language keeps off a line's end never ends a line, read alone, reached the lines the content breaks too. DEC-012 point 1 has a line feed end a paragraph, and so a line, whatever word comes before it. This record narrows the example to the lines the engine breaks, and states it for every language's rules (Implications).
- **Only a reader of the language sees it.** A line that ends on such a word reads as a slip only to a reader of its language, so an author who reads the page in another language never sees it. The showcase deck draws each page in two languages, one beside the other, and its content writes line feeds ([project-kit#2882](https://github.com/aleskalfas/project-kit/issues/2882)).

## Decision

**The check names each paragraph that a line feed ends on a kept word, a word the scene's language's rules keep off a line's end, where the text goes on after the line feed. It asks for attention in the file that holds the word, and never fails. The engine carries no word across the line feed.**

### 1. A paragraph ends on a word kept off a line's end, and its text goes on

- **A kept word.** The rules of the scene's language keep a word off the end of a line the engine breaks where a space follows the word (DEC-005 point 4, as the components page gives them under "Breaking lines"). A *kept word* is such a word, followed here by spaces or by the line feed. The check reads the rules from the data the engine breaks lines by, by the primary subtag of the scene's language, as the engine reads them. A language with no rules of its own keeps no word.
- **What bounds a word.** A word starts where the engine's rules start one: no letter, digit or underscore comes just before it, so the last letters of a longer word are no word of their own, even where they spell a kept word. It ends at the spaces or the line feed after it. So the check finds a kept word where the engine's rules would find one if a space stood in the line feed's place, and nowhere else, whatever the word means (What it costs).
- **When the check names one.** It names a paragraph where all three hold:
  - its last word is a kept word, with nothing after it but spaces;
  - a line feed ends it;
  - the text goes on after that line feed: something other than a space or a line feed comes later in the same text.
- **What leaves it unnamed.** A full stop or a colon after the word does, since the engine keeps no word such a mark follows. So does the text's end, where only spaces and line feeds come after the word, as where a YAML `|` block adds a line feed to the text: a text that ends on a kept word and a line feed is not named, as one that ends on the kept word alone is not.
- **Only a line feed written in the text.** The check reads only a line feed that a run's text holds, written where the text is written: in the content file, or in the file of the component that shows a text no content gives. A line feed the engine adds, wherever it adds one, is none the check reads, so no paragraph it ends is named. The engine adds one after each path of a list of paths but the last, since it shows the list a path to a paragraph ([visual-communication:DEC-056-paths-in-content] point 1). So a path whose last segment is a kept word is not named where another path follows it, since its fix cannot be made in the text.
- **Across its runs.** The check reads the paragraph's text whole, its runs joined, as the engine breaks it (DEC-012 point 4). So a kept word whose letters lie in two runs is one word, and a line feed in a later run than the word's ends its paragraph all the same.
- **In each scene.** It reads every text the scene holds, in each language and at each key over the size axes, by the paragraphs the scene holds for it, whether the content gives the text or not (point 2).

### 2. The finding asks for attention where the word is written

- **Its level.** It asks for attention and never fails, since a paragraph may end on a kept word on purpose, as a line of a list may end on a label whose letters spell a kept word.
- **Where it lies.** By the run whose text holds the kept word's first letter, as that run's source names it:
  - **Text the content gives** lies in the content file of the scene's language, at the run's key path: the field, where the field is given as text, and the run by its place among the field's runs, where it holds a list of runs (DEC-012 point 1). It names no library version. A field drawn on several pages gives one finding, since the content holds it once.
  - **Text no content gives** lies in the file of the component that shows it, as every finding in a component does (the capability's page of checks, "Scenes").
- **Who acts.** Whoever can correct the file it lies in: the piece's author, for the content and for the piece's own component, and for a library's component, the one DEC-005 point 14 names for a finding in a library version, such as a released version's owner.
- **What it says.** The paragraph, by its place among the text's paragraphs, and the kept word, and that the line feed after the word ends the line, so no break carries the word on to what follows it. Its fix: move the word past the line feeds after it, so that it opens the paragraph the text goes on in, or reword the paragraph's end.
- **Its label** is `kept-word-ends-paragraph`. The check compares no scenes, since a paragraph's finding in one scene rests on no other.
- **No reach.** It states no reach, since no reader's instructions read its silence ([visual-communication:DEC-063-where-a-check-measures] point 1).

### 3. The engine keeps a text's paragraphs as written

The engine carries no word across a line feed, drops no line feed and joins no two paragraphs to keep a word off a line's end. A paragraph that ends on a kept word stays as its text is written, and the check names it where point 1 says.

## Rationale

**Why name it.** The engine keeps a kept word on a line with the word after it, so a reader meets one cut from the word after it only where a line feed in the text cut it. Only a change to the text can move it, and an author who reads the page in another language never sees it. The finding names where the text is written, which is where it is mended.

**Why attention, never failing.** A language's rules keep a word by its letters, whatever it means in the text, so they also hold a label that names a variant or a point where its letters spell a kept word, as in a list whose lines each end on such a label. To fail would hold such content to a rule its author may rightly break.

**Why only where the text goes on.** A kept word with nothing after it in its text but spaces and line feeds has no word to be kept with, and no break the engine makes would place it otherwise. Where a phrase runs on into another text, the layout ends it, not a line feed, and a check of one text cannot read the next. A line feed with more of the text after it is a break inside one text, made where the text is written, and a word it cuts from what follows is a slip mended there.

**Why a check of the scene.** It reads a paragraph's runs joined as the engine breaks them, and only text a part draws, both of which the scene holds: a check of the content files reads neither, and the engine, which breaks each line as its rules say, has nothing of its own to report.

**Why where the word is written, by the run.** The fix lies in the words, so the finding points at the file a person edits, as every scene finding does (the capability's page of checks, "Scenes"). The engine breaks a text no content gives by the scene's language as it breaks the content's, so a kept word there is the same slip. Its fix lies in the component that shows the text, and a finding in a component already names who can correct it (DEC-005 point 14). The run's key path names the run that holds the word, as a finding on a run whose concept no notation holds names its run, by its field and its place among the field's runs ([visual-communication:DEC-012-text-runs] point 8).

**Why the engine's own data.** A list of kept words of the check's own would drift from the engine's, and the check would then name a word the engine moves, or miss one it keeps. A new language's rules reach the check with the release that brings them to the engine.

**Why the engine keeps the line feed.** A line feed is its text's author's, and its paragraphs carry meaning, such as the lines of a terminal or of a list. To move a word across it would change what the text says.

### What it costs

- **The engine's rules name meant words too,** since they keep a word by its letters, as the engine bounds one, whatever the text means by it. So the check names each word whose letters spell a kept word but stand for something else, before a line feed with more of the text after it: a flag that ends a terminal's or code's line, a unit after a number, a variable, a numeral, a label that names a variant, and the letters after an apostrophe left untranslated, which the engine bounds as a word of their own. Nothing silences the finding: its author reads past it, and it fails nothing. A filter that left them out would be a rule the engine lacks, so the check would read a paragraph by rules its lines do not break by.
- **A kept word that ends a text is not named,** though a phrase may go on in another text the layout places after it.

### Alternatives considered

- **Fail validation.** Rejected: a paragraph may end on a kept word on purpose.
- **Read every paragraph of a text but its last.** Rejected: a text that ends in a line feed, as a YAML `|` block does, would be named where nothing follows its kept word.
- **Name a kept word that ends the text too.** Rejected: no word follows it for the engine to keep it with, and a phrase another text goes on stays unread all the same.
- **Leave out text no content gives.** Rejected: the engine breaks it by the scene's language as it breaks the content's, so the slip is the same, and a finding in a component already lies at the component's file, naming who can correct it (DEC-005 point 14).
- **Lie at the piece, by the text's trace id,** as letters that touch across lines do ([visual-communication:DEC-053-letters-across-lines] point 2). Rejected: the fix lies in the file that holds the words, and the trace leads there only through the scene's sources.
- **The engine carries the word across the line feed, or joins the paragraphs.** Rejected: that changes what the text says.
- **A list of kept words of the check's own.** Rejected: it would drift from the engine's.
- **A word in the content that marks a paragraph's kept word as meant.** Not taken: an addition to the format, for a finding that fails nothing.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-005 point 4, its bullet "Lines broken by the engine".** Accepting this record narrows what the bullet promises, that a word a language's rules keep off a line's end never ends a line, to the lines the engine breaks: a line that a line feed in the text ends may end on one. Its sentence that gives one language's rule as an example comes to read "A word a language's rules keep off a line's end never ends a line the engine breaks. A line feed in a text ends a paragraph, and the engine carries no word across it (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] point 3)." Its other sentences stand. The edit narrows the sentence to what the bullet's heading already covers, the lines the engine breaks, and states it for each language's rules, which the bullet already keeps as data in the engine, so it refines the point and overturns none of it. Which words a language's rules keep stays with the engine's data, and the capability's components page states them.
  - **The bullet, as it comes to read, whole:**

    > **Lines broken by the engine.** It breaks text into lines by Unicode's rules and each language's own rules, kept as data in the engine. So a new language's rules arrive with a release of the capability. A word a language's rules keep off a line's end never ends a line the engine breaks. A line feed in a text ends a paragraph, and the engine carries no word across it (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] point 3). The engine breaks a paragraph across its runs, each measured in its own typography role (refinement per [visual-communication:DEC-012-text-runs]).
  - **DEC-005 point 14, its bullet "Asks for attention, never failing".** It comes to read, whole:

    > **Asks for attention, never failing:** an overflow measured from a table or by an estimate, a loss nobody has accepted, and a paragraph that a line feed written in the text ends on a word its language's rules keep off a line's end, where the text goes on after the line feed (refinement per [visual-communication:DEC-075-paragraph-ends-on-kept-word] points 1 and 2).
- **The change that builds the check** builds points 1 to 3. Its tests plant, in the content of a language whose rules keep words off a line's end, before a line feed with more of the text after it: a word of each kind the rules keep, in each letter case the engine keeps it in, each in one run; a kept word with its letters in two runs; a kept word with spaces after it; one in a run before the run that holds the line feed; one before two line feeds; and one whose next paragraph opens with a dash. They find each paragraph named at the run's key path in the content file, asking the piece's author for attention, and a kept word in a text no content gives named at the file of the component that shows it. They find unnamed: a kept word with nothing after it to the text's end but spaces and line feeds; one a full stop follows; a longer word whose last letters spell a kept word; the same paragraph in a language with no rules; a paragraph whose line feed comes before the kept word; and a path of a list of paths whose last segment is a kept word, with another path after it. They find the paragraphs the scene holds as the text writes them.
- **The capability's pages** come to say, in the change that builds the check: the page of checks, the finding's row among the scenes', with what it reads, its level, who acts, where it lies and its fix; the components page, under "Breaking lines", that the engine carries no word across a line feed, and that the check names a paragraph that a line feed written in the text ends on a kept word, where the text goes on after it.
- **The capability's version moves,** a `minor`, since a project's validation gains a finding. It owes no migration: no file a project holds changes meaning. An existing piece gives the finding in validation from its next render, or once a file its scenes are computed from changes, not from the release: the findings record's key holds no engine version, so a record that still verifies is read as its render wrote it (DEC-005 point 13). The change's changeset says so.
- **Read against this record, and left as they stand:**
  - DEC-012 point 1. A line feed in a run's text ends a paragraph, as it says, and this record reads its paragraphs so.
  - [visual-communication:DEC-002-files-and-validation] point 7. This record sets the finding's level under its policy, and the finding names who acts, as its bullet "Attention or a fact" asks, so the point gains nothing.
  - DEC-005 point 13. The finding is found with the scene's other findings and kept in the findings record, as every scene finding is, and the record's key gains no engine version.
  - DEC-063 point 1. The check states no reach, which that point lets a check whose silence no reader's instructions read. It then counts as having measured no place, and its findings still reach every reader.
  - [visual-communication:DEC-062-checks-beside-the-frames] point 1. The viewing step's report gives the finding as it gives every scene check's, from scenes it computes itself.
  - [visual-communication:DEC-070-ship-call-and-one-round] points 2 and 3. The finding fails nothing, so the designer does not mend it before the review, and the round mends it only where the review reports it as one of the kinds point 3 names.
  - DEC-070 point 4. Where the designer mends such a paragraph, that point decides, as it stands, whose words it may change alone.
- **Revisit this record** if a project's content gives such findings for words its authors mean, often enough to crowd its validation, or if a language's rules come to keep off a line's end a word that a line feed may rightly follow.
