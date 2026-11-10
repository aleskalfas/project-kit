---
id: DEC-012
title: A field shown as text may hold runs, each in a style the field declares and perhaps naming a concept
status: accepted
date: 2026-11-03
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a component may let a field of text hold *runs*, spans of the text each set in a style the field names. Content gives such a field a text, as in format 1, or a list of runs, and the component gives each style its font and colour. A run may also name a concept, which gives it its colour family. For example, a terminal's line whose styles are `command`, `prompt` and `comment` takes `line: [{text: "$ ", style: prompt}, pkit visual render deck]`, its command in the first style.

## Context

A slice of the capability draws texts in several styles, such as a terminal's line whose prompt, command and comment take different colours ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501)). Format 1 cannot say so:
- **Content holds no look.** It holds no font or colour, and chooses only among what its libraries declare. A concept says what a thing is, and its component decides how that looks ([visual-communication:DEC-001-visual-communication-discipline] points 3 and 6).
- **A text is set in one style.** A *text part*, the part of a component that draws one of its fields as text, sets it in the *typography role* its `style` names, which gives the font, size, weight and line height, and colours it with its *paint*, the colour role its `fill` names. The record of the engine gives the scene's text paragraphs of runs, but format 1 builds a text of one role and one paint, with no run ([visual-communication:DEC-005-engine-and-plugins] points 1, 4 and 5).
- **The reserved `concept` binds only a mapping that places a component** ([visual-communication:DEC-002-files-and-validation] point 4), so it does not reach a span of text.

Until validation accepts files at an older format number, the format grows only by additions that every file written before still meets ([visual-communication:DEC-003-change-over-time] point 3), so no new reserved key may refuse a field of its name. The records of a list's fields and of ties met that bound on like questions, with fields a pattern declares, a word given on each item, and keys the format fixes on a mapping that places no component ([visual-communication:DEC-010-list-item-fields] points 1, 3 and 5, [visual-communication:DEC-011-tie-ends] point 2).

## Decision

**A field of text its component marks may hold a list of runs, each set by a word of its field's run styles and perhaps naming a concept, and the engine measures each run in its own style and breaks lines across them.**

### 1. A component marks the fields of text that take runs

- **A run** is a span of a text set in one style, perhaps naming a concept. A text is one or more runs joined in order, and a field that may hold them is a *field of runs*.
- **The mark.** A component marks each field of runs with a key format 1's schema of a component does not know. The mark lies directly on one of its fields or on a slot a layout declares, never on a schema within one, such as a list's items, nor on the schema of all its fields, and no `$ref` leads to a marked schema. A field it does not mark takes what its schema says.
- **Only a field of text.** A marked field's `type` is text and no other, and it holds no `enum`, `const` or `$ref`. The mark widens its schema to take a list of runs too, and whatever offers a component's fields to an author, such as the capability's pages, its agents or a schema an editor reads, offers that widened shape.
- **Its value.** A field of runs takes text, read as one run, or a list of runs. A run is text, or a mapping whose `text` holds text, and which may hold `style` (point 2) and `concept` (point 3) and no other key.
- **Joined as written.** The runs' texts are joined in order, with nothing added between them. A line feed in a run's text ends a paragraph, and the next paragraph goes on in the same run.
- **Filled.** A list of runs fills its field, for a part's condition, where one of its runs holds text, as text fills it where it is not empty.
- **Keys the format fixes.** A run places no component, so no reserved key binds it (DEC-002 point 4). The format fixes `text`, `style` and `concept` on a run alone, as it fixes `layout` on a page drawn in a layout (DEC-010 point 5).
- **No id.** A run carries no id, and a list of runs holds runs, not items, so no rule of ids reaches it (DEC-001 point 3). An edit taken back from a renderer finds a run by its place among its field's runs, only while they stay as they were at the render, and changes its text.
- **In each language,** a field's runs are its value, so their number, order and styles may differ, as its text does.
- **Where it lies.** A field of runs is one of a component's own fields: a field of a top or of a component content places, an item included, or a slot a layout declares (DEC-010 point 5). An arrangement field, an end field, an option and a list's component field never take runs (DEC-010 points 1 and 3, DEC-011 point 2).

### 2. A run names a style by a word its field declares

- **Run styles.** For each field of runs the component declares the words of its *run styles*. Each word takes the shape of a name and appears once, and each field declares its own.
- **The first word is the default,** for a run that names no style and for a field given as text.
- **One word on each run,** given as `style: <word>`. It is no role, font or value: content chooses among what its component declares (DEC-001 point 3).
- **The text part chooses by it, as by an option's word.** A text part that shows a field of runs gives each run the typography role and the paint its style chooses, declared, never computed (DEC-005 point 1), and two words may share a role. Where a field declares more than one word, at least one text part of the component that shows the field chooses its role, its paint or both by them. Another may show the field in one look, and draws every run in it.
- **Only how the run is set.** A run's word chooses only that run's typography role and paint, never a place, a size, another part, a named value of the component or an option of a placed component. A text part chooses by the words of the field it shows, and by no other field's.
- **Drawn where it is declared.** Only a text part shows a field of runs: one of the component that declares it, or, for a top, one of a drawing of its layout. A part's condition may read whether the field is filled, and no other part reads it. No part of the component that declares it passes it on to a component it places, for now, though a part may pass a field of text on to a placed field of runs, which reads it as one run in its first style.
- **Under every drawing.** A brand's drawing of a layout takes a field's words as words the top declares, and gives each its own look (DEC-009 point 5). It takes those a text part of it that shows the field chooses by, only the first where none does, and no run where it passes the field on, so it then fits only an instance that gives the field text. An instance whose runs name a word the drawing does not take is drawn by the top's own drawing (DEC-009 point 6). A run's concept counts for no drawing's fit, so no change of a top that this record's point 6 counts as not breaking fails a brand's drawing.

### 3. A run names a concept with the key `concept`

- **The key `concept`.** A run may name a concept as `concept: <notation>/<concept>`, in the shape an item's concept takes, read with its notation's name from the notations the piece names (DEC-004 point 10). It means what the run stands for, and the format fixes it on a run with the reserved key's name, shape and meaning, adding no reserved key.
- **A run's family.** A run that names a concept takes that concept's colour family, before its instance's own, as an item's family is its own before that of the component it sits in (DEC-010 point 6). A run that names none takes the family of the instance whose text part draws it.
- **A state reaches every run.** A state its component gives a family replaces the instance's family, its own concept's included, and the family of each of its runs, a run's concept included. Content keeps no run's concept under such a state.
- **A run's paint** is the paint its style chooses, or the role an `override` points its part at (DEC-001 point 6). A paint `:colour.<member>` takes that member of the run's family, and a paint that names a role takes that role, whatever the run's concept. So a concept colours a run only where the component paints the run's style from a family.
- **Guarded as drawn.** Each run is measured against the fill under it, at its own size and weight and in its own paint, as every drawn text is (DEC-004 point 8). That measure alone guards the colour a run's concept gives it.
- **The bound on concepts.** A run's concept counts toward the bound on how many concepts one piece tells apart by colour, as an item's does, and this record narrows no rule of DEC-004 point 10.

### 4. Each run is measured in its own style, and lines break across runs

- **Its own role.** The engine measures each run in the typography role its style chooses, from the files the brand gives that role's families (DEC-005 point 4, DEC-004 point 9). A role it cannot read, or a character no family of the role measures, is reported or refuses the render as for any text.
- **Breaks across runs.** The engine finds where a paragraph may break in its whole text, across its runs, by Unicode's rules and the language's own, and measures each piece of a line in its own run's role. So a word whose letters lie in two runs stays one word. Its margin against the planned width is taken at the greatest font size among the styles the text's runs take (DEC-005 point 4).
- **One line height for the text.** Each line takes the greatest line height among the styles the text's runs take, and the text's measured height is its lines times that height, so the scene's text keeps one line height (DEC-005 point 5). A text whose runs all take one style is measured as format 1 measures it.
- **One baseline on each line.** The runs of a line stand on one baseline, placed as format 1 places it where they all take one style, and from their metrics where they take several. A run's letters may reach into the leading where its style's line height is less than its font's ascent and descent, as in format 1.
- **A weight's own file.** Each run is measured and drawn from the files its role's families name, so a brand that gives a weight a family of its own gives it its own file, with no change of format.

### 5. How each choice is given, beside the records of a list's fields and of ties

- **The forms those records chose.** Each choice takes a form those records chose under the same bound: a field the component declares, a word given on each run, and keys the format fixes on a mapping that places no component (DEC-010 points 1, 3 and 5). `concept` keeps format 1's shape there, as an end field keeps an option's (DEC-011 point 2).
- **No clash.** A run's keys are the format's alone, and its words its field's, so no other library's keys or words meet them (DEC-010 point 2, DEC-011 point 1).
- **No new rule of fit.** A field of runs, its words and the text parts of its component that draw it lie in one version of one library, and no part of that component passes it on, so no versions cease to fit together over runs (DEC-011 point 4). A brand's drawing, which another library holds, draws a top's field of runs only where it fits the instance (point 2), by the record of layouts' fit, which needs no new rule either (DEC-009 point 6).

### 6. What breaks

A run style's word is a name a piece uses, so removing or renaming it, or changing what it means, breaks its library ([visual-communication:DEC-003-change-over-time] point 6). Beyond it:

- **Breaking:** a field that ceases to take runs, and a change of a field's first word, a new word put first included.
- **Not breaking:** a field of text that comes to take runs, a new word after the first, and a change of the role or paint a word chooses, which a piece meets only when its lock moves (DEC-003 point 8).

### 7. What this adds to format 1, and what it keeps

- **Each addition this record makes is optional:** no component need mark a field, and no content need give runs. The schema of a content file gains no key, since it names no field's value.
- **How content is read.** The check reads a field of runs as text, against its schema, or as a list of runs, never against the schema's type, each run against its field's words and the piece's notations. It reads every other field as in format 1.
- **The scene.** The scene's text holds its runs, each with its typography role, its paint and its fonts, under the one line height point 4 gives it.
- **Every file format 1 accepted** is read and drawn as before, and raises no finding format 1 did not. Format 1's schemas refuse the mark, so none of its fields takes runs, and each text it shows is one run, in the role and the paint its part gives it.

### 8. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct. Elsewhere, as in a released library version, it asks for attention and names who can correct it. A final piece's drawing is not judged ([visual-communication:DEC-002-files-and-validation] point 7).

- **Where each lies.** A finding on what a component declares, or on what one of its parts gives, lies in the component's version. One on a brand's drawing lies in the brand's version, judged when the brand is checked alone (DEC-009 point 9). One on a run lies in the content file, at the run, named by its field and its place among the field's runs. One on how a run is drawn lies at the piece.
- **Fails validation:**
  - in a component: a mark anywhere but directly on one of its fields or on a slot a layout declares, a `$ref` that leads to a marked schema, or a mark on a field whose schema takes more than text or holds `enum`, `const` or `$ref`; a field of runs with no word; a word that does not take the shape of a name, or appears twice
  - in a component, a top's own drawing of a layout included: a text part that chooses by a word its field does not declare, or by a switch that leaves one of the field's words out; a field of more than one word that no text part chooses by; a part that passes a field of runs on to a component it places; a part other than a text part that reads one, beyond a condition on whether it is filled
  - in a component or a brand's drawing: a choice by a run's style anywhere but the typography role and paint of a text part that shows its field
  - in a brand's drawing: a text part that chooses by a word the top's field does not declare (DEC-009 point 9)
  - in content: a list in a field of text that takes no runs; a run that is neither text nor a mapping whose `text` holds text, or that holds a key other than `text`, `style` and `concept`; a style its field does not declare; a concept of another shape, from a notation the piece does not name, or that its notation does not hold (DEC-004 point 11)
  - at a piece: a run below the contrast it must reach against the fill under it (DEC-004 points 8 and 11), or whose family has no member its paint reads
- **Asks for attention, never failing:**
  - in a brand's drawing, naming the brand's owner: a text part that leaves one of its field's words out, or chooses by none where the field declares more than one, or a part that passes a field of runs on. The piece states each instance the top's own drawing draws in its place (DEC-009 point 9).
  - at a piece: a run that names a concept but is painted with a role, by its style or by an `override` on its part, so that its concept shows in no colour. It names the run, and its style or the override.

## Rationale

**Why a list of runs.** Each run lies apart, so the check reads its style and concept, and translators, agents and edits taken back from a renderer change words, never marks among them. The cost is length: a text with one span set apart is three runs.

**Why the component marks the fields.** The component decides how its texts look (DEC-001 point 6), so runs reach only the fields whose owners chose them, and each such field holds its words before a run names one.

**Why only a field of text, widened by the mark.** Such a field refuses nothing it held when it comes to take runs, and its schema keeps checking its text. No tool of format 1 but the check reads content against a component's fields, and one that offers them later reads the mark with the schema (point 1), so the two never disagree in use. The cost is a schema that says text where a list may stand.

**Why words, not roles.** A word says what the run is, and the component how it looks, so switching the brand restyles every run with no content changed (DEC-001 point 5).

**Why the words lie with the field.** Content writes them, so the component declares them for content, as it declares its options' words, and each field holds its runs to the things it sets apart.

**Why the first word is the default.** It is how an option and an arrangement field take theirs (DEC-010 point 3). So a component whose field comes to take runs asks nothing of its content, and a run writes a word only where it differs. A word says what a run is, so changing the first changes what every unstyled run is (point 6).

**Why the key is `style`.** It is the word an author reaches for, and in content it can name only a word. The cost: it names a typography role in a component and the scene, so a reader must know which file it is in.

**Why the format fixes a run's keys.** Runs then read alike in every component, for people, agents and translators, and `concept` means one thing wherever content writes it. A run holds no other key, so a later key, such as a run's link (DEC-005 point 5) or the methodology's container's key, is an addition, and none is kept free on a run (DEC-002 point 4).

**Why a run's concept reaches only the paints that read a family.** A concept does so on every component content places, which leaves the component deciding how a run looks, and keeps a run's concept out of a drawing's fit. No member is promised where a run's text lies, so neither rule would make its colour safer, and a piece may pass under one brand and fail under another, though both meet every pair they are given. The cost is a concept that shows in no colour.

**Why that asks for attention.** An item's look is its component's alone, but a run's is the style or the `override` its content chose, so its author can often mend it. Where every word of the field paints with a role, the mend is the owner's of what paints the style: the component's, or a brand's where its drawing draws the run.

**Why a state reaches a run that names a concept.** A state says something of its whole instance, such as a step dropped from a flow, and its component gives the state its look (DEC-001 point 6). An item inside another keeps its own concept, being an instance with states of its own (DEC-010 point 6), and a run has none.

**Why one line height for the text.** It keeps a paragraph's lines even, gives each run at least its own style's line height, and leaves a text in one style as format 1 sets it.

**Why a field of runs is drawn where it is declared, for now.** Passing it on needs a map of its words onto the placed component's, a spelling of its own, which no slice needs yet, and lifting the refusal later refuses nothing. The cost is reuse: a card whose title takes runs cannot hand it to a heading block, though small parts are what a project reuses (DEC-007 point 1).

**Why the forms of a list's fields and of ties.** Those records chose them under the same bound (DEC-003 point 3), so runs read like what content already writes.

### Alternatives considered

- **Marks inside the text, such as Markdown's or tags:** a `*` written as a character would become a mark, so text format 1 accepted would change its meaning, and need escaping.
- **A run that names its typography role and its colour role:** content would set a look span by span, which no brand could restyle.
- **Every field shown as text takes runs, with no mark:** a text drawn in one style for a reason, such as a tag, would take spans from any content.
- **A schema that says the field takes a list of runs, as `type` and `items` do:** each component would write the run's shape again, perhaps differently.
- **Fields of runs declared apart from `fields`, as arrangement fields are (DEC-010 point 2):** a reader would look in two places for one field.
- **Runs in any field, whatever its schema takes:** a number, a list or a word a field held would change its meaning, or be refused.
- **Run styles declared by the text part that draws the field:** content would give what a drawing declares (DEC-009 point 5), and two parts that show one field could declare two sets.
- **One set of words for all of a component's fields:** a title's run could name `prompt`, which the title draws no differently.
- **Words the format or the foundations fix for every field, such as `strong`:** what sets a span apart differs from one kind of text to another.
- **A run as an item that places a component:** a run would take a frame of its own, and lines could not break across runs.
- **New reserved keys, such as `text` and `style`:** they would refuse fields format 1 accepts, such as one named `text` (DEC-002 point 4).
- **Keys each component names for its runs:** runs would read differently in each component.
- **A run as a mapping from its word to its text, such as `strong: the exact version`:** runs would read differently in each field, and a word could take a fixed key's name.
- **Paragraphs as a list of lists of runs:** every text of runs would nest one level deeper, where a line feed already ends a paragraph.
- **An id on a run:** nothing names a run, and ids would ask each language for the same runs, though word order differs.
- **A run's concept that paints it in its family's member for text, whatever its style's paint:** the format, not the component, would decide how the run looks.
- **A run's concept that wins over its instance's state:** a component switches on no state, so a dropped step could not grey a run that names a concept.
- **Lines each as tall as their own runs, as CSS's line boxes are:** a paragraph's lines would lie unevenly.
- **Every line at the first style's line height:** a larger run's letters would reach into the line above further than its style lets them.
- **A line height taken from every word the field declares:** every text of the field would be set wide, text already written included.

## Implications

- **Edits to accepted records,** each citing this record:
  - DEC-001 points 3 and 6: a field's run words among content's choices, a list of runs with no ids that may differ between languages, and a run's concept and family under a state.
  - DEC-002 points 3 and 4: a run's three fixed keys in the strict reading, which takes a list of runs only in a field marked to take them, with no ids and no key kept free, and a run style's word with no path marks.
  - DEC-004 point 8: each run measured against the fill under it, at its own size and weight.
  - DEC-005 points 1, 4 and 5: a text part's choice by a run's style, each run shaped and measured in its own role, lines broken across runs, and a text's runs with their paint and fonts under one line height, each saying how it was measured.
  - DEC-007 point 3: each run word of each field drawn once in a component's reference renders.
  - DEC-009 points 5, 6 and 9: the words a drawing takes from the top's fields of runs, its fit by them, and the findings point 8 gives a brand's drawing.
- **The scene and the seam.** A renderer reads each run's paint and fonts, so the seam's version rises with runs (DEC-005 point 8), and a renderer that cannot draw a run's style reports the loss (DEC-005 point 9).
- **Sources and traces.** A run's source in the scene names it as point 8's findings do (DEC-005 point 5), and a text's trace id stays its part's.
- **The starter's README** names each field of runs with its words, which count toward no guide of how many options a pattern holds ([visual-communication:DEC-007-starter-library] point 2).
- **The release's comparison** of a library's stable components with its previous version reads fields of runs and their words, under point 6 (DEC-003 point 7).
- **A weight's own file.** Whether a brand may give one family a file for each weight is its declaration of its fonts, left to the record of brands and notations (DEC-004 point 9); this record decides nothing of it.
- **Left to later changes:**
  - a run's link, a key the format adds on a run (DEC-005 point 5)
  - a sign beside a run's colour, such as its concept's icon or a chip on its family's fill, and a finding where two concepts of a piece share a family, with the change that builds icons and a legend, for runs and items alike (DEC-004 point 10)
  - a field of runs passed on to a component a part places, its words mapped as an option's switch maps them, which the starter's blocks may need when they compose ([project-kit#2501](https://github.com/aleskalfas/project-kit/issues/2501), T12)
  - a state's declaration of whether it reaches runs that name a concept, an optional key on a state whose default keeps the state's family over a run's concept
  - the structure a tagged document or a web page gives a run, such as emphasis or code, since a run's word is its field's own and says nothing of structure to a renderer (DEC-005 point 5)
  - whether the check holds anything of a field's runs equal across languages, such as the concepts they name, left to translation (DEC-001 point 3)
  - how an edit that splits or joins runs comes back, and how a medium that returns plain text keeps them, left to the record of taking edits back (DEC-001, Implications)
