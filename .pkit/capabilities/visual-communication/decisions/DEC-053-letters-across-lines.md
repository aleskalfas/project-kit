---
id: DEC-053
title: The check names a text whose letters touch across its lines, and the engine keeps the brand's line step
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** where a text's lines lie so close that a letter of one line touches a letter of the next, such as the tail of a g and the accent of the á below it, the check names the text and asks the piece's author to widen the step. Letters touch where their shapes meet, as the engine sets them, with no distance added, so the finding is the same at every text size. The check finds them from the shapes of the letters the engine sets, never from the font's line height, which would name texts whose letters lie well apart. It reads no screen, so it names the case the engine settles: where letters meet or part by less than about one to two device pixels, a browser may draw them otherwise, and across that band the check is silent on what a screen shows. The engine keeps the line step the brand gives. For example, a Czech heading set at a step of 1.0 em, a g over an á of the line below, is named, and the same heading at the shipped brand's 1.2 em is not.

## Context

[project-kit#3232](https://github.com/aleskalfas/project-kit/issues/3232) asks what holds where a text's line step lets the letters of one line touch those of the next. The record of forced colours names this a known gap ([visual-communication:DEC-039-forced-colours-grounds-and-edges] point 3). The letters touch in the piece's own colours. The step that sets the lines is the brand's spacing, so no renderer mends them, and a wider line step does. The look report names letters only where they lose strong ink to a part drawn after them, which letters of one colour on one ground do not. Three answers were open: a check that reports such a text, an engine that sets no step below the letters' height, or the gap left unnamed, with its reason.

Terms:
- A text's *line step* is how far apart its lines' baselines lie. The engine gives a text one step, the greatest line height among the typography roles its runs take, each a ratio the brand gives of its font size ([visual-communication:DEC-012-text-runs] point 4). The brand gives the ratio, and the engine takes any number.
- Two lines' *reach* is the step below which their letters overlap: at the one point along the line where it is greatest, how far the upper line's letters fall below its baseline, added to how far the lower line's rise above its own. It is given in the em of the text's size.
- A face's *ascent and descent* are as the engine reads them, from the font's horizontal header. Its *typographic* ascent and descent are those its OS/2 table gives.

### What the probe showed

The probe computed the showcase deck's scenes through the engine's own code, in its two languages, English and Czech, at the projector size the deck names and at the desktop size. It drew each line of each text alone, from the face its run names, shaped as the engine shapes it and placed where the engine places it, at 240 pixels to the em, a pixel counting as ink where it is half covered. It measured each pair of lines' reach: 78 pairs of lines that follow each other in a text, and 6 168 pairs of any two lines that one face sets at one font size, in one language and one scene, as if one text held them one above the other. The deck's brand, the one the capability ships, sets three faces, Source Sans Pro in a regular and a semibold file and Source Code Pro, at steps from 1.1667 em, the deck's title on a projector, and 1.2 em, a heading at a desktop, to 1.5 em, code at a desktop. Its code is thrown away.

- **The deck's own pairs.** At each text's own step no letters touched. The closest pair lay 0.331 em apart, 7.3 px, in code at 22 px. The greatest reach was 0.967 em, a g over a č. Below the brand's steps, 2 of the 78 pairs touched at 0.95 em and 10 at 0.9 em, where the most two lines' letters overlapped was 0.0038 em².
- **Any two lines.** The greatest reach was 0.95 em in English, a g over an f, and 1.017 em in Czech, a g over an á in the semibold. At 1.05 em no pair touched. At 1.0 em 7 did, 0.1 %, all Czech, each an acute under a g, a j or a y: 2.2 % of a 24 px heading's pairs at a desktop. At 0.95 em 2.9 % did, and at 0.9 em 15.6 %. At its role's own step, the closest pair lay 4.7 px apart, a g over an í in a 24 px heading at 1.2 em.
- **Any Latin letter with Czech's.** Set alone, a g over a Ů reached 1.099 em in both Source Sans Pro files and 1.104 em in Source Code Pro. At the brand's tightest steps such letters lay 2.4 px apart in a 24 px heading at 1.2 em, and 3.3 px in a 48 px title at 1.1667 em. In the two Source Sans Pro files, the g and the ring overlapped by 0.005 to 0.006 em² at 1.05 em, and by 0.005 to 0.010 em² at 1.0 em.
- **The faces' measures.** In each of the three faces, the ascent and descent add up to 1.257 em, and the typographic ascent and descent to 1.0 em. The first lies 0.15 em above the greatest reach of any Latin letter with Czech's, so steps between them, the brand's 1.1667 and 1.2 em among them, part every such letter. The second lies 0.1 em below it, so such letters touch at steps above it.
- **The letters' boxes.** Measured by each letter's box, the bounds of its outline, the pairs whose boxes meet across lines at 1.0 em were ten times those whose letters touch: 1.1 % of any two lines against 0.1 %. Measured by each line's deepest foot and highest top, wherever they lie along it, they were 10 %. At each pair's own step no boxes met, the nearest 4.3 px apart.
- **Within a pixel.** A second probe took the furthest-reaching pair, the g over the á in the semibold, and read their outlines exactly: their shapes met at 1.018 em. It set the two lines at exact distances apart, each drawn alone, and moved the device's pixels under them by eighths of a pixel down and quarters across, 32 places, at device scales of 0.625, 1, 1.225 and 2. Letters less than one device pixel apart shared a smoothed pixel at some places and not at others: at 0.1 device px apart at 24 to 28 of the 32, at 0.5 at 10 to 14, and at 0.75 at 1 to 5. From one device pixel apart they shared none. Where they shared one, the fainter of the two letters covered at most 29 % of it at 0.1 device px apart, 10 % at 0.5 and 2 % at 0.75. One device pixel is 1.6 px of the page at a scale of 0.625, and 0.5 px at 2. No one judged whether letters that share such a pixel read as one shape.
- **Characters drawn to join.** Source Code Pro's box drawing reaches 1.4 em, so the lines of the deck's tree of folders meet at their own step of 1.2727 em on a projector, as the font draws them to: 10 of the 78 pairs. Their letters lay apart.
- **A run's sign.** A sign came no nearer a letter of the other line than letters did: its greatest reach was 0.967 em, a sign under a y.

**Not reached:** another brand's faces; a language whose marks rise higher, such as Vietnamese, whose marks stack; another script, such as Greek or Cyrillic; characters other than letters and digits, such as punctuation, brackets and arrows; a browser's drawing of letters that meet or nearly meet across lines; a device scale below 0.625 or above 2; whether letters that share a smoothed pixel without meeting read as one shape; a reader's own text spacing or minimum font size; the lines of two texts set close.

## Decision

**The check names a text where the shape of a letter of one line meets the shape of a letter of the next, as the engine sets them, and asks the piece's author for attention. The engine keeps the line step the brand gives.**

### 1. Letters touch where their shapes meet across a text's lines

- **Which lines.** Each line of a text and the next one, as the engine sets them, across its paragraphs. Lines of two texts are not compared: the layout sets their distance, not the step.
- **What a line draws.** Its letters: the glyphs the engine shapes for each run's text, from the face the run names and at the run's size, each where the engine places it along the line and on the line's baseline. A run's sign counts with them, where the scene places it ([visual-communication:DEC-036-concept-signs] point 3). A character a font draws to join the next line's, such as box drawing, does not count.
- **When they touch.** Two lines' letters touch where the outline of a letter of one line and the outline of a letter of the next share a point, the lower line set the text's step below the upper. So two lines' letters touch at any step at or below their reach, and at none above it, whatever the text's size. Letters that come near without meeting do not touch: no distance is added.
- **Measured from the shapes.** The check reads each letter's outline from the face the scene names, the one the engine measured with. Neither the face's ascent and descent nor a letter's box stands for the shape.

### 2. The finding asks the piece's author for attention

- **Its level.** It asks for attention and never fails. Letters that meet may be what a brand means, such as a display type set tight on purpose, so no record makes their parting an invariant ([visual-communication:DEC-002-files-and-validation] point 7).
- **Where it lies.** At the piece, by the text's trace id, naming no library version, as a text's contrast against its fill does, since the step comes from the brand under the piece's lock.
- **What it says.** The two lines, the letters that meet and the step, with the typography role it comes from and their reach, the step above which they part. Its fix: a wider line step for the role, in the brand, or by the brand's owner where the brand is a released version, or a text that breaks elsewhere.
- **When it is found.** With the scene's other findings, in each language and at each key over the size axes, and kept in the findings record ([visual-communication:DEC-005-engine-and-plugins] point 13).

### 3. The engine keeps the brand's line step

The engine widens no line step for the letters it sets. A step at which letters touch stays as the brand gives it, and the check names the text.

## Rationale

**Why a check, not the engine.** The step is the brand's typography, and a brand gives each role its value ([visual-communication:DEC-004-brands-and-notations]). An engine that widened a step below the face's ascent and descent would widen the shipped brand's 1.1667 and 1.2 em, where no Latin letter, Czech's among them, comes within 2.4 px of the next line. One that widened a step below the reach of the letters each text sets would make the step follow each text's words, so two texts of one role would lie unevenly, and a type set tight on purpose would lose its step. Either way every scene of a brand set tight would change, where a finding changes none and lets a person choose.

**Why not leave the gap unnamed.** The shipped brand parts every Latin letter with Czech's, so only a brand whose step lies below 1.104 em, the furthest such letters reach, lets them touch. The engine takes such a step, and nothing names what it does: at 1.0 em the Czech heading's letters touched in 2.2 % of its pairs of lines, an acute under a g. A check costs one measure of each pair of a text's lines, and the outlines need reading only where the letters' boxes meet. At the shipped brand's steps none did.

**Why from the letters' shapes.** The face's measures miss both ways. Its ascent and descent lie 0.15 em above any Latin letter's reach, so a check by them names each title, and each heading at a desktop, that the shipped brand sets on more than one line. Its typographic ascent and descent lie below the reach of Czech letters, so a check by them misses letters that touch between 1.0 and 1.104 em. A letter's box over-reaches across the line: it named ten times the pairs that touch. The shapes are the letters themselves, read from the face the engine measures with.

**Why letters touch where their shapes meet, with no distance.** Meeting is a relation of the shapes alone, so it holds at every size. A distance in px of the page names other letters on each screen. An HTML page shrinks with a narrow window ([visual-communication:DEC-020-html-page-drawing] point 4), so a px of the page often takes less than one device pixel, and at the device scales the capability's records probed, from 0.625 to 2, one device pixel is 1.6 to 0.5 px of the page. A fixed px is also a larger share of a small text's em than of a large one's. A distance in em would hold at every scale, but nothing measured sets its size. Letters less than a device pixel apart share a smoothed pixel at some places of the pixel grid and not at others, and the fainter of the two covers at most 29 % of it. No one judged whether such letters read as one shape (Context). So the check names letters that meet as the engine sets them, and adds no margin, since no evidence sets one. At the shipped brand's steps no Latin letter with Czech's meets the next line's: the nearest lie 2.4 px apart.

**Where a renderer draws the letters.** The check measures each letter where the engine places it, and reads no renderer's pixels. Each renderer draws each line at the engine's baseline, its letters at or near the engine's places along it. The PDF renderer places each glyph at the advances the engine shaped. A browser held each line's baseline within 0.024 px of the engine's by its layout, and each line's width within 0.41 px. It drew each line's ink within 0.49 device pixels of that baseline at a device scale of 1, within 1.37 at 1.225, and within 1.44 in a 375 px window (DEC-020, Context). It places each line alone (DEC-020 point 2), so one line's letters may come nearer the next line's, or move further from them, by about one to two device pixels, and by more where two lines move opposite ways, which no probe measured. Letters less than a device pixel apart may also share a smoothed pixel (Context). So the check names the case the engine settles, letters that meet as it sets them, and across that band it is silent on what a screen shows: a browser may draw together letters the engine sets apart by less, which the check leaves unnamed, and draw apart letters that meet by less, which it still names. At the shipped brand's steps the nearest Latin letters with Czech's, a g over a Ů 2.4 px of the page apart in a 24 px heading, lie 1.5 device pixels apart at a scale of 0.625, within that band, and 4.8 at 2. The check needs no browser for the case it names.

**Why characters drawn to join are left out.** A font draws box drawing to meet the next line's, so a tree of folders meets at any step below 1.4 em as it is meant to.

**Why a run's sign counts.** It is drawn on the line in the run's paint, and a letter it meets reads as badly as one another letter meets.

**Why it asks for attention.** A tight display type with letters that meet may be what a brand means, and a released brand's step is no file the project corrects. So the finding never fails, and names who acts.

### Alternatives considered

- **The engine widens a step below the face's ascent and descent:** it widens the shipped brand's steps, where no letters touch.
- **The engine widens a step below the reach of the letters a text sets:** two texts of one role lie unevenly, and a brand loses a step it chose.
- **A check by the face's ascent and descent:** it names each title, and each heading at a desktop, that the shipped brand sets on more than one line, its letters 2.4 px apart or more.
- **A check by the typographic ascent and descent:** it misses letters that touch between 1.0 and 1.104 em.
- **A check by the letters' boxes:** it names ten times the pairs whose letters touch.
- **A finding at the brand, for each role, by the reach of every letter of its face in the languages the project sets:** it lies where the fix is and shapes no text, but it names a role set at 1.05 em in a project that sets Czech, where none of the deck's lines touched, for letters such as a g over a Ů that its texts may never set.
- **Letters within a distance in px of the page, such as 1 px:** it names other letters on each screen and at each text size, and means nothing in a PDF.
- **Letters within a distance in em:** nothing measured sets its size.
- **A finding that fails:** a tight setting may be meant.
- **The look report:** it names strong ink lost to a part drawn after a text, which letters of one colour lose none of, and it needs a browser where this measure needs the faces alone.
- **The gap left unnamed:** Czech letters touch at steps the engine takes, and nothing names them.

## Implications

- **An edit to an accepted record,** made once this record is accepted, citing it. Accepting this record accepts it (COR-066 point 5).
  - **DEC-039 point 3, "A known gap: letters that touch across lines".** The bullet comes to read, whole:

    > **A known gap: letters that touch across lines** (refinement per [visual-communication:DEC-053-letters-across-lines]). Where a text's line step is below the height of its letters, a letter of a later line may touch one of the line above, in the piece's own colours, as the SVG renderer's image shows too. The step that sets the lines is the brand's spacing, and no renderer mends it: a wider line step does, or a text that breaks elsewhere. The check names a text whose letters' shapes meet across its lines, as the engine sets them, and asks for attention (DEC-053 points 1 and 2). It reads no screen, so across a band of about one to two device pixels, where a browser may draw letters otherwise than the engine sets them, it is silent on what a screen shows. The look report names such letters only where they lose strong ink to a part drawn after them (DEC-037 point 2), which letters of one colour on one ground do not. Nothing names the letters of two texts that the layout sets close, nor letters the engine sets apart and a browser draws together, nor a letter that meets a character a font draws to join the next line's, such as box drawing.
- **#3232 builds points 1 to 3** in the check. Its test draws letters that touch across lines and finds the text named. It finds letters that come near without meeting, and box drawing that meets, unnamed, and the scene's step the brand's.
- **The capability's page of checks** comes to list the finding among the scenes', with its level, where it lies, its fix and the characters drawn to join that it leaves out, in #3232's change.
- **Read against this record, and left as they stand:**
  - DEC-012 point 4. A run's letters may still reach into the leading. The check names them only where they meet the next line's.
  - [visual-communication:DEC-037-text-the-page-hides] point 2. `dropped` names a text that loses strong ink to a part drawn after it. Letters of one text's lines that meet are this record's finding, never an entry of `dropped`.
  - DEC-005 point 14. Its list of what the engine's checks report gains nothing: this record states its own finding.
- **Revisit this record** if a brand or a language the capability ships sets letters that reach further than Czech's, such as Vietnamese, if a renderer comes to place a line elsewhere than at the engine's baseline, or if letters that share a smoothed pixel without meeting are found to read as one shape.
