---
id: DEC-059
title: A brand may give a font family a file for each weight, and a run takes its weight's file or the nearest
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a brand may give one font family a file for each of its weights, such as a regular and a semibold, where today it gives each family one file. A run of text is then measured and drawn from the file of its own weight. Where the family has no file at that weight, the run takes the nearest weight the family has, as a web browser would choose it, and the brand's check fails the typography that asks for it, so its owner gives the file or another weight. A brand built on another adds its weights of a family to its base's, its own winning where both give one, and where either gives the family one file, the brand's replaces its base's. Every renderer draws each character from the file the engine measured it from, and draws a variable font, where it draws one, at its default instance, as the engine measures it. A family given one file, and a weight given as a family of its own, as every brand today gives it, measure and draw as before. Only a variable font in a vector picture or an HTML page draws otherwise: as it was measured. Adding or removing a weight's file breaks nothing, and the seam's version rises once.

## Context

The record of brands decides that a font role gives a list of families, the first measuring each character it has, and that fonts come from committed files, a missing font refusing the render ([visual-communication:DEC-004-brands-and-notations] point 9). A brand names a family's file in the capability's extension point, on a font family token that names the family (DEC-004 point 1). A typography role gives a family, a size, a line height and a weight, and the engine measures each run of a text in the role its style chooses ([visual-communication:DEC-012-text-runs] point 4).

Format 1 gives a family one file:
- **One file for every weight.** The engine measures a run in its family's one file, whatever the run's weight, and each renderer draws it from that file. So a typography that names a family at a weight its file is not, such as a regular file at 600, is measured and drawn in the regular letters.
- **A weight of its own is a family of its own.** A brand that draws a weight from its own file gives it a family name of its own, as the neutral brand gives its semibold.
- **Two files for one family fail.** The check fails a brand that gives one family two files.

Two more things hold in format 1, though no record decides them. A brand built on another that gives a family its base gives replaces its base's entry whole. And while the engine measures a variable font at its default instance, and the PDF renderer draws one with TrueType outlines so, the renderers of vector pictures and of HTML pages keep its variations, so a browser moves its weight axis to each run's weight and draws letters the engine did not measure. One with CFF2 outlines the PDF renderer does not embed, since it embeds CFF and TrueType outlines alone, and it reports the text it leaves out as a loss (DEC-005 point 10).

A typeface ships as one family with a file for each weight, and DTCG's typography gives the family and the weight apart, as design tools export them. A *face* is one family at one weight, as CSS names a font it chooses or embeds. A brand taken from such a tool must rename each weight as a family before its weights draw. The record of runs left a family's file for each weight to the record of brands (DEC-012, Implications), whose point 9 does not decide it. The Feature of drawing for a whiteboard service without signing in takes up the gap ([project-kit#2569](https://github.com/aleskalfas/project-kit/issues/2569)).

## Decision

**A brand gives a font family one file, which serves every weight, or a file for each weight it gives. A run is measured and drawn from its weight's file, or else from the nearest weight's, chosen as CSS chooses a face. A typography role that asks for a weight its family has no file for fails at the brand, and still draws. A weight's file added, replaced or removed breaks nothing. Each renderer draws each character from the file the engine measured it from, and a variable font, where it draws one, at its default instance. It names each face at the weight the scene draws it at, and the seam's version rises once. A brand built on another merges its weights of a family over its base's, unless either gives the family one file, when the brand's entry replaces its base's.**

### 1. A family takes one file, or a file for each weight

- **Where.** A brand names a family's files where format 1 names its one file: in the capability's extension point on a font family token that names the family, under the family's name in `files`.
- **One file,** as format 1 gives it: a path within the brand's version folder, or the hash of a file the project commits (DEC-004 point 9). It serves every weight.
- **A file for each weight:** a mapping from weights to files, such as `{"400": "fonts/Inter-Regular.otf", "600": "fonts/Inter-SemiBold.otf"}`. Each key is a weight, a whole number from 1 to 1000 written in digits, as a typography's weight gives it. Each value is one file, in either of format 1's forms. The mapping gives at least one weight.
- **Told apart by their keys.** A file named by its hash is a mapping of `hash` alone, and a mapping of weights holds weights alone, so no entry reads two ways.
- **One entry for a family.** Two tokens of one brand that name the same family give it the same entry, as format 1 asks of its one file. So within one brand a family's weights come from one entry, which a brand built on another merges with its base's (point 8).

### 2. A run takes the file of its weight, or of the nearest weight its family has

- **Its weight's own file.** Each family of a run's typography role measures and draws the run from the file of the role's weight, where the family gives one.
- **Else the nearest,** chosen as the font matching of [CSS Fonts Module Level 4](https://www.w3.org/TR/css-fonts-4/) chooses a face by weight. A weight below 400 looks to lighter weights first, the heaviest of them first, then to heavier ones. A weight above 500 looks to heavier weights first, the lightest of them first, then to lighter ones. A weight from 400 to 500 looks to heavier weights up to 500, then to lighter ones, then to those above 500.
- **A family of one file** has that file at every weight, as in format 1.
- **By its family and its weight alone.** Within a scene, a family's file depends on the family and the weight it is drawn at, and on nothing else, such as the characters a run holds or the part that draws it.
- **Its characters are the chosen file's.** A family measures a run's characters that its chosen file has, and the role's next family the rest (DEC-004 point 9). So where two weights of a family hold different characters, each run is measured by its own weight's file.
- **The scene names it.** Each run names, for each family that measured it, the file chosen, with its hash, as it names its fonts in format 1 ([visual-communication:DEC-005-engine-and-plugins] point 5). It also names each other family of its role's list that is given a file for each weight, with the file chosen at the run's weight and its hash, marked as having measured none of the run's characters, so a renderer can give it its face (point 5). A family of one file that measured none of them is not named, as in format 1.
- **In every profile that measures from files.** Wherever a font profile measures a family from its files (DEC-004 point 9), it measures by this point.

### 3. A weight a family has no file for fails at the brand, and still draws

- **At the brand.** A typography role, as the brand resolves it in some combination of its axes, whose weight one of its families, given a file for each weight, has no file for, is a finding of the brand's. It fails validation where the project can correct the brand, and elsewhere asks for attention, naming the brand's owner ([visual-communication:DEC-002-files-and-validation] point 7). It names the role, the combination's key, the family, the weight asked and the weight drawn instead. The owner mends it by giving the weight's file, or by giving the role a weight the family has.
- **In a scene, never a refusal.** A run whose family has no file at its weight is measured and drawn from the nearest weight's file (point 2). So a released brand with such a role, or a brand whose base came to give fewer weights, still draws, in the weight nearest the one asked.
- **A missing font stays a missing font.** A family measured from its files that has no file, a file named that nothing holds, whether a family's one file or a weight's, and a character no family measures each refuse the render, as DEC-004 point 9 decides. A weight with no file of its own is none of these.
- **A weight no role asks for raises nothing,** since a brand may give weights for the brands built on it.
- **A family of one file names no weight,** so none of its weights is missing, and a brand format 1 accepted raises no new finding.

### 4. A weight's file added, replaced or removed breaks nothing

- **A changed value.** A font file is a raw value, which only a brand holds (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 5). So a weight's file added, replaced or removed, and a family that comes to be given by weight or by one file, each change a value, which breaks nothing (DEC-004 point 5).
- **Nothing that drew ceases to.** A run whose weight lost its file takes the nearest (point 2). A piece meets the change only when its lock moves, as it meets any changed value.
- **The brand's own roles are checked first.** A version is checked before it is released ([visual-communication:DEC-003-change-over-time] point 6), so no version is released whose own roles ask for a weight its families lack.
- **A brand built on it** whose role then asks for a weight the family, merged with its base's (point 8), no longer has finds it in its own check (point 3), as it finds the combinations a base's new mode gives it (DEC-004 point 5).

### 5. Each renderer draws each character from the file the engine measured it from

- **The scene's file.** A renderer draws each run from the file the scene names for each family that measured it, and chooses no file itself, since it decides nothing the scene sets (the founding record, DEC-001 point 2). The engine hands it the file for a family at a weight by the hash the scene names it with, never by family alone.
- **Named at the weight it is drawn at.** A medium that matches a face by its family and weight, as CSS does in the renderers of vector pictures and of HTML pages, gets a face for each family and weight its runs draw in, named at the weight the scene draws it at, even where its file is the nearest weight's. So the medium matches it exactly, and neither picks another face nor makes the letters bolder than the file draws them. Format 1 draws a family of one file so at every weight.
- **A face for each family given by weight.** For each family of a run's list that is given a file for each weight, such a medium also gets a face at the run's weight, even where the family measured none of the run's characters. Its file is the one the scene names for the family at the run's weight, as it names one for each such family (point 2). So for a character the engine passed to the next family, the medium never reaches another weight's file of the family passed over. A family of one file gets no such face, since the scene names none for it, so format 1's output gains none.
- **Its face alone.** A renderer draws no character from a family the scene marks as having measured none of a run's characters, and takes none of the run's measures from it, such as how high and how low the run's line reaches. Nor does the viewing step count it among the families a run was measured in (DEC-015 point 2).
- **A variable font at its default instance.** A renderer that draws a variable font, a file that holds a range of weights or of other variations, draws it at its default instance, as the engine measures it. The PDF renderer already draws one with TrueType outlines so. One with CFF2 outlines it does not embed, and it reports the text it leaves out as a loss, as it does in format 1 (DEC-005 point 10). A medium that would move its axes to a run's weight, as a browser does, is handed the file without its variations.
- **A file once.** A medium that names a font by its file, as PDF does, embeds each file once, however many weights draw from it.
- **What the viewing step draws.** It takes each face as the page names it, by its family and its weight ([visual-communication:DEC-015-viewing-step-and-reviewer] point 2), so it draws the file the renderer embedded.

### 6. The seam's version rises once

The engine hands a renderer the file for a family at a weight, by the hash the scene names it with, never by family alone, where format 1 handed it one file for each family. A renderer that took a family's file by its family alone would embed one weight's file for every weight of a family given several, and draw letters the engine did not measure. That is one reason the seam's version rises, in the change that builds this record (DEC-005 point 8). The other is that the scene grows. Each run already names each of its fonts with its file and its hash (DEC-005 point 5), and comes also to name each other family of its list given by weight, marked as having measured none of it (point 2). A renderer that read each font a run names as one that measured it would take measures from a family that draws nothing of the run. One rise covers both.

### 7. Every brand format 1 accepted is read as before, and drawn as before but for a variable font

- **The same scenes and the same bytes.** A family of one file measures and draws every weight from it. So a brand that gives a weight a family of its own, as every brand format 1 accepted gives it, keeps its families, its files, its renders and its scenes, but for the seam's version each scene names (point 6), and raises no finding it did not. The one exception is a variable font, which a vector picture or an HTML page comes to draw at its default instance, as the engine measured it (point 5).
- **An addition to the format.** A file for each weight is a form format 1 refused, and nothing format 1 accepted is refused, so the format grows by an addition ([visual-communication:DEC-003-change-over-time] point 3).
- **A brand that uses it** needs a release of the capability that reads the form, and its version names that release as the one it needs ([visual-communication:DEC-013-shipped-library-releases] point 3, [visual-communication:DEC-014-own-library-needed-release] point 1).

### 8. A brand built on another merges its weights of a family over its base's

- **Both by weight, merged weight by weight.** Where a brand gives a family a file for each weight, and its base has the family so, its own bases merged in, the family has each weight either gives, from the brand's own file where both give one. So a brand adds a weight to its base's family, or replaces one weight's file, and keeps its base's other files.
- **One file on either side, replaced whole.** Where the brand gives the family one file, or its base has it so, its own bases merged in, the brand's entry replaces its base's whole. That is format 1's rule, which the capability already follows and no record stated. So a brand that gives by weight a family its base gives one file gives each weight its roles ask for, or its check finds the rest (point 3).
- **Merged before a run chooses.** A run takes its weight's file, or the nearest, from the merged family (point 2), and the brand's check judges its roles against it (point 3).
- **How, not whether.** This point decides how a brand's entry for a family meets its base's. Whether a brand may give its own files to a family its base gives at all, which changes the letters of roles its base keeps closed (DEC-001 point 5), is left to a follow-up (Implications).

### 9. What the checks report, and how severely

Each finding below fails validation where it lies in a file the project can correct, and elsewhere asks for attention, as DEC-004 point 11 says.
- **Fails validation:**
  - a family's entry that is neither one file nor a mapping of weights to files, a key of such a mapping that is no weight, or a mapping that gives no weight
  - one family given two different entries in one brand
  - a weight's file that nothing holds, as for a family's one file
  - a typography role whose weight, in some combination, a family of it given a file for each weight has no file for (point 3)
- **Refuses the render,** as DEC-004 point 9 decides: a family measured from its files that has no file, a file named that nothing holds, whether a family's one file or a weight's, and a character no family measures. A weight with no file of its own refuses nothing.

## Rationale

**Why a mapping of weights, beside the one file.** A typeface ships one family in a file for each weight, and a typography gives its family and its weight apart. A mapping under the family's name keeps a family's files in one place, as format 1 keeps its one file, and reads like the typeface it describes. The one file keeps its form, so nothing format 1 accepted changes.

**Why weights as keys.** A mapping gives each weight once, where a list of faces could give one twice. The cost: JSON writes a key as text, so a weight is `"600"` there, where a typography writes `600`.

**Why the nearest, by CSS's rule.** A family of one file already draws every weight from the one file it has, which is the nearest it has. The nearest by CSS's rule carries that to several files with no second rule. It is the rule a designer meets in every browser, so a browser handed every face of the family would choose the same file. The engine measures the file it draws, so every box is the right size whichever file that is.

**Why the brand fails, and the scene does not refuse.** The owner who gave a family its weights and a role its weight can mend a role that asks for a weight with no file, so the check fails there, before a piece draws it. A refusal at the render answers measuring in one font and drawing in another, which makes every box the wrong size (DEC-004, Rationale). Here the engine measures and draws one file. A refusal would stop pieces under a released brand that only its owner can mend.

**Why a failure, not attention.** A failure lifted to attention later refuses nothing, where attention raised to a failure later would refuse a brand the format accepted (DEC-003 point 3).

**Why adding or removing a weight's file breaks nothing.** A font file is a value, and a value changes freely (DEC-004 point 5). A missing weight draws from the nearest, so nothing that drew ceases to. A break would make the weights each font token reaches a promise, which a token pointed at another family, a changed value too, could break as well.

**Why a face at the weight it is drawn at.** A face named at its file's weight would leave the medium to match the weight the run is drawn at against it. A browser may then make a lighter face's letters bolder for a bold run, as no file draws them and the engine did not measure them. Named at the weight it is drawn at, the face matches exactly, and the medium draws the file measured.

**Why a face at the run's weight for each family given by weight.** A span names its role's whole list of families, and the medium looks through that list for each character, as the engine did. A family given by weight that measured none of a run's characters would have no face at the run's weight, so the medium would take its nearest face, another weight's file, which may hold a character the engine gave the next family. Its face at the run's weight, made from the file the engine looked in, holds none of them, so the medium passes them on as the engine did. Each face of a family of one file holds that one file, which lacks them too, so format 1 needs no such face.

**Why the scene names a family that measured nothing.** A renderer adds no font of its own to what the scene sets (DEC-001 point 2), and a span names its families by name alone. So only the scene can tell a renderer that a family is given by weight, and which file it has at a run's weight. No other file will do: another weight's file may hold a character the file at the run's weight lacks, and the medium would draw that character from it. Marked as having measured nothing, the family gives its face, and no measure of the run is taken from it.

**Why a variable font at its default instance.** The engine measures a variable font at its default instance, and the PDF renderer draws one with TrueType outlines so, without its variations. One with CFF2 outlines it does not embed, and it reports the text left out as a loss, which this record leaves as it is. A browser handed its variations moves its weight axis to the run's weight, and draws letters wider or narrower than the boxes the engine measured. Drawn at its default instance in every medium that draws it, it is drawn as measured, from the file the scene names. Drawing it at each weight it holds would have the engine measure each instance, a form of its own, left to later (Implications).

**Why the seam rises.** A renderer that took one file for each family would draw a family given several weights in one of them, and one that read each font a run names as one that measured it would take measures from a family that draws nothing, as point 6 says.

**Why a brand's weights merge over its base's.** A value a brand gives a role its base opens wins over its base's in the combinations it covers, and its base's holds elsewhere (DEC-004 point 6). Merged weight by weight, a family's files follow that rule: a brand changes the weights it names, keeps its base's other files, and takes each weight its base later adds or replaces. A family's one file is no one weight's, so it has nothing to merge with, and replaces or is replaced whole, as format 1 has it, so every brand format 1 accepted keeps its fonts (point 7).

### Alternatives considered

- **No change: a family of its own for each weight.** Rejected. A typography's weight then chooses no file, so a brand taken from a design tool, which gives one family several weights, draws them all in one file's letters.
- **Only the exact weight, any other refused.** Rejected. A brand whose base came to give fewer weights would stop drawing, and a weight's file removed would have to break, through a promise of the weights each font token reaches. The failure at the brand catches what the exact rule would, where it can be mended.
- **The nearest by distance alone, ties going heavier.** Rejected. It is a rule of the capability's own, which no browser follows.
- **A weight with no file of its own asks for attention only.** Rejected, for now, for the reason above.
- **A list of faces, each with its weight and its file.** Rejected. A weight could appear twice, and each face would repeat its keys.
- **A key of its own beside `files`, such as `weights`.** Rejected. A reader would look in two places for one family's files.
- **A weight's file on a font weight token, or on the typography.** Rejected. A weight serves every family, and a typography is not where format 1 names a family's files.
- **A brand that lists a family's files, each file's weight read from the font.** Rejected. The weight a file states is its maker's, two files may state one, and a reader of the brand would have to open each font to learn which file draws a weight.
- **The nearest weight's face named at its file's weight.** Rejected, for the reason above.
- **One face for each file, under a name the renderer makes.** Rejected. It renames every face, so every export of format 1 changes its bytes, and it strips the brand's family names, which design tools read.
- **A face that holds no character, for a family that measured none of a run's, with the scene as it is.** Rejected. The scene names a family's file only where it measured, and a family given by weight that draws at one weight reads there as a family of one file. So the renderer could not tell which families are given by weight but by reading the brand, which would have it add a font the scene does not name (DEC-001 point 2). Else it would give such a face to every family a run passed over, families of one file among them, and format 1's output would gain faces (point 7).
- **Point 5 for files with no weight axis alone.** Rejected. It would keep, as a stated exception, a variable font drawn at weights the engine did not measure, so its boxes may be the wrong size.
- **A weight's file added or removed counted as a break.** Rejected, for the reason above.
- **The base's weight wins, and the brand only fills gaps.** Rejected. It reverses the rule that a brand's value wins over its base's where it gives one (DEC-004 point 6), and leaves a brand no way to replace one weight's file but by giving the family one file.
- **A brand's entry replaces its base's whole, in either form.** Rejected. A brand that adds one weight would copy every file of its base's family, and miss each weight its base later adds or replaces.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-004 point 9** gains a bullet after "A font role gives a list of families": "**A family may take a file for each weight.** A brand gives a family one file, which serves every weight, or a file for each weight it gives. A run takes its weight's file, or else the nearest weight's, as CSS chooses among a family's weights, and a weight with no file of its own is no missing font. Within a scene, a family's file depends on the family and the weight it is drawn at, and on nothing else (refinement per [visual-communication:DEC-059-font-files-by-weight] points 1 to 3)."
  - **DEC-004 point 5, "Not breaking":** after "Nor is a changed value, an alias pointed elsewhere included." it comes to add "Nor is the file of one weight of a family given a file for each weight added, replaced or removed, nor a family that comes to be given by weight or by one file (refinement per [visual-communication:DEC-059-font-files-by-weight] point 4)." The edit leaves undecided whether removing a family's only file breaks, since a brand built on another may draw that family from its base's file and then fail.
  - **DEC-004 point 6** gains a bullet after "Merged before aliases are resolved": "**A font family's files.** Where the brand gives a font family its base has, its own bases merged in, its entry replaces its base's whole, unless both give the family a file for each weight. Then the brand's weights merge over its base's, its own file winning where both give one. Whether a brand may give its own files to a family its base has at all is not decided here (refinement per [visual-communication:DEC-059-font-files-by-weight] point 8)."
  - **DEC-004 point 11, "Fails validation"** gains a bullet: "a family's files in neither of their forms, one family given two different entries, or a typography role whose weight a family of it, given a file for each weight, has no file for (refinement per [visual-communication:DEC-059-font-files-by-weight] point 9)".
  - **DEC-005 point 4, "Measured from the brand's fonts":** after "and reads font metrics with an established font library." it comes to add "Each such piece is shaped from its family's file at the run's weight, or the nearest weight's (refinement per [visual-communication:DEC-059-font-files-by-weight] point 2)."
  - **DEC-005 point 10, "By default, the brand's own files":** after "pointed at those files, never at the machine's." it comes to add "It draws each character from the file the engine measured it from, and a variable font, where it draws one, at its default instance. Where its medium matches a font by its family and weight, it gives each family a run draws in a face at the weight the scene draws it at, and also each family the scene names for the run as having measured none of it, from the file the scene names, so the medium never reaches another weight's file of a family the engine passed over (refinement per [visual-communication:DEC-059-font-files-by-weight] point 5)."
  - **DEC-012 point 4, "A weight's own file":** after "so a brand that gives a weight a family of its own gives it its own file, with no change of format." it comes to add "A brand may also give one family a file for each weight, and a run's weight then chooses among them (refinement per [visual-communication:DEC-059-font-files-by-weight] point 2)."
  - **DEC-012's Implications, "A weight's own file":** "Whether a brand may give one family a file for each weight is its declaration of its fonts, left to the record of brands and notations (DEC-004 point 9); this record decides nothing of it." comes to read "A brand may give one family a file for each weight, as [visual-communication:DEC-059-font-files-by-weight] decides."
- **Read against this record, and left as they stand:**
  - DEC-001 point 2, since a renderer embeds the file the scene names, and adds no font;
  - DEC-001 point 5, since point 8 decides how a brand's entry for a family meets its base's, and leaves whether it may give one to a follow-up;
  - DEC-003 points 3 and 6, since the form is an addition, and a version is checked before it is released;
  - DEC-005 point 5 and DEC-012 point 7, since each gives a run its fonts and says no more of which they are, so neither changes when a run comes also to name each other family of its list given by weight, with its file and its hash, marked as having measured none of it (points 2 and 6);
  - DEC-005 point 13, since each file a scene reads is in its findings record's key;
  - DEC-015 point 2 and [visual-communication:DEC-020-html-page-drawing] point 6, since the viewing step reads each face, and finds a span with no face, by its family and its weight, and counts among the families a run was measured in none marked as having measured nothing (point 5).
- **The records drafted beside it.** The record drafted under [project-kit#3275](https://github.com/aleskalfas/project-kit/issues/3275) decides how a font profile measures a medium's own fonts, and how a family says how it is measured, in the same extension point. A family measured from its files names them in either form of point 1, whatever that record decides of the rest of the extension. The record drafted under [project-kit#3274](https://github.com/aleskalfas/project-kit/issues/3274) touches nothing here.
- **The Task that builds it,** under [project-kit#2569](https://github.com/aleskalfas/project-kit/issues/2569), filed once this record is accepted:
  - the brand reads both forms, merges a family's weights over its base's as point 8 decides, and its check gives point 9's findings. The finding that a family's files are not of their shape (`font-shape`) ceases to fail a family given by weight, and a weight's file that nothing holds is a missing font (`font-missing`), as a family's one file is. A role that asks for a weight its family has no file for takes a finding apart from a missing font's, since it refuses nothing;
  - the engine measures each run from its weight's file, names in each run each other family of its list given by weight with its file at the run's weight, marked as having measured nothing, and hands each renderer the file the scene names, by its hash, with the seam's rise. Each renderer embeds it as a face of the run's weight, and gives a face at the run's weight to each family a run names so. The HTML renderer's reach of a line, and the viewing step's runs measured in more than one family, leave such a family out. The renderers of vector pictures and of HTML pages draw a variable font without its variations, as the PDF renderer draws one it embeds;
  - a brand of the capability's tests gives one family two weights, and a brand built on it adds a weight and replaces another. Every brand format 1 accepted gives the same scenes, but for the seam's version, and the same bytes, but for a variable font in a vector picture or an HTML page (point 7). The neutral brand, which keeps its families of their own and gives no variable font, is among them.
  The capability's pages of a brand's fonts, of text, of outputs and of checks change with that Task.
- **Left to a follow-up, [project-kit#3280](https://github.com/aleskalfas/project-kit/issues/3280):** whether a brand built on another may give its own files to a family its base gives at all. It changes the letters of roles its base keeps closed, where a brand changes only the values its base opens (DEC-001 point 5). The capability lets it today, and this record changes nothing of that. Point 8 decides only how the two entries meet where it does.
- **No migration.** Nothing a project holds changes (COR-010).
- **Left to later changes:** a variable font drawn at each weight it holds, as a form of a family's entry of its own, told apart by its keys as point 1 tells its two forms apart, so a brand opts into it, and any other variable font stays at its default instance (point 5); a face's style, such as italic, which a typography does not name.
