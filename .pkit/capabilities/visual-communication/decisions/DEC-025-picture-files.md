---
id: DEC-025
title: A piece shows a picture file it holds by name, and a brand gives its logo as a value
status: accepted
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person puts a picture, such as a photo, in the piece's `pictures/` folder, and the content names it by its file name, perhaps another in each language. A library's part may show a file of its own library, the same in every mode. A brand gives its logo as the value of the role `picture.logo`, and no brand owes one. The capability reads the PNG and JPEG files every output draws alike, and refuses the rest with the fix. For example, a shared header that shows `picture.logo` shows each brand's logo, a dark one in a dark mode where the brand gives one, and no logo under a brand that gives none.

## Context

Version 1 of the capability designs web pages, portals and decks under a brand, handed out as HTML and PDF ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)). A piece shows a picture file a person gives it, such as a logo or a photo. Pictures a program makes, such as a 3D render, wait for version 2. The records make a picture made elsewhere content, which follows no brand ([visual-communication:DEC-001-visual-communication-discipline] point 3), and let a brand hold pictures as values ([visual-communication:DEC-004-brands-and-notations] points 1 and 2).

What stands in the way:
- **No picture can reach a piece.** An `image` part shows a produced output alone, and no producer ships.
- **A logo cannot follow the brand.** A shared part names no brand, so it cannot name a brand's file, and a piece that places `{use: <brand>/logo}` locks that brand. The record of a web page leaves a logo in a shared header to this record ([visual-communication:DEC-022-web-site-and-parts], Implications).
- **A file can draw in one output and fail in another.** A browser draws most ways a picture is stored, and the capability's own PDF renderer draws only what its code decodes.
- **No command changes a brand.** A person edits a field of the piece's file, so the report at a change of brand has no moment yet.

Terms:
- A *picture file* is a PNG or a JPEG file that a person puts in a piece or in a library's version. A produced picture is none ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 1).
- A picture file's *encoding* is how it stores its pixels and says how to show them, such as a palette PNG, a progressive JPEG or an orientation tag.
- A picture file's *bare name* is its file name alone, with no folder in it.
- A *picture role* is a role whose value is a picture file of the brand.

## Decision

**A part shows a picture file of the piece or of its own library, by its bare name, or the file a brand may give a picture role such as `picture.logo`, and the capability reads such a file only in the encodings every output draws alike.**

### 1. Content names a picture file in a field that an `image` part shows

- **What an `image` part shows.** One of four things, each named by one property: `produced`, as format 1 has it, `content`, `file` or `role`. A part names exactly one of them.
- **`content: <field>`.** The field's value is the name of a picture file of the piece (point 2), held as text.
- **Each language names its own.** Each content file gives its own, as it gives its own text, and a picture shared by every language is named in each.
- **An empty field draws nothing.** The part is not drawn, and has zero size at its place ([visual-communication:DEC-005-engine-and-plugins] point 3).
- **A file, never a produced output, for now.**

### 2. A picture file lies in the piece's `pictures/` folder, under a bare name

- **The folder.** A piece's picture files lie in one folder of its own folder, `pictures/`, apart from what a program writes ([visual-communication:DEC-002-files-and-validation] point 5).
- **A bare name's shape.** Lower-case letters, digits and hyphens, starting with a letter, then a full stop and its extension: `png` for a PNG, `jpg` or `jpeg` for a JPEG.
- **Found by its exact name** among the files of the folder as version control lists them, never by asking the file system. So a file the clone ignores is no picture.
- **Only a name the content gives is judged.** A file of the folder that nothing names takes no finding.
- **No symbolic link.**
- **Its bytes are committed.** A pointer that a large-file store keeps in its place is no picture.
- **No folder within, for now.**
- **One of the piece's own files.** So the findings key and an export's fingerprint read it with no rule of its own, and read the whole folder, a file no part shows included ([visual-communication:DEC-016-what-an-export-reads] points 1 and 2).

### 3. A library's part shows a file of its own version, the same in every mode

- **`file: <name>`.** A part of a library's component names a picture file of that library's version, by a bare name, in the version's `pictures/` folder.
- **A brand's own parts** name the brand's files so (DEC-004 point 1), but show the brand's logo by `role: picture.logo`, never by `file`.
- **A local component's library is the piece,** so its `file` names a picture file of the piece.
- **The component names it, not the content.**
- **One file in every mode and under every brand.** A picture that must follow a mode is a picture role (point 4).
- **Under the lock.** A released version's hash reads every file of its folder, so its pictures change only when a person moves the lock (DEC-001 point 7).

### 4. A brand gives a picture role a file, and no brand owes one

- **A type of role.** A picture role has the type `picture`. Its value is a picture file of the brand's version, in its `pictures/` folder.
- **The shared picture roles lie in one group, `picture`.** The first is `picture.logo`, which the foundations declare with no default, and which a shared part, such as a header, shows by `role: picture.logo`.
- **Only the foundations declare a picture role, for now.**
- **No brand owes a picture role.** A brand that gives one no value is not at fault, and a part that shows it is not drawn, with zero size at its place (DEC-005 point 3). So a new picture role breaks no brand.
- **Only where absence draws.** A role may go without a value only where its absence draws as a missing optional part's does, as a picture's does.
- **In every value mode, or in none.** Within one key over the size axes, a brand gives a picture role a value in every combination of the value axes, or in none.
- **One proportion within a key.** The files a picture role takes over the value axes, within one key, share one proportion of width to height.
- **By mode and by size, as any value.** A value axis may give a dark mode its own logo, and a size axis a phone a smaller one (DEC-004 point 2).
- **A brand built on a base** keeps its base's logo, unless the base opens the role (DEC-004 point 6).
- **Its form in the brand's files.** A picture role's value is an empty group at the role's path, which names the file in the capability's extension point and aliases nothing (DEC-004 point 1).
- **It stands as the role's token** wherever the records speak of one, as in what a brand exports, opens or changes the type of (DEC-004 points 5, 6 and 11).
- **Merged as a token's value is,** in the Resolver document's order of sources.
- **A form kept for good.** The engine keeps reading every form a released brand may name (DEC-004 point 1), so a later type for a file in DTCG would be read beside this one, never in its place.
- **Exported where it is given.** A brand exports a picture role only where it gives it a value, so ceasing to give one removes an exported name, which breaks the brand (DEC-004 point 5).
- **Written code.** The document of values holds a picture role's value, the file's name in the brand's version, and its version rises once for this record (DEC-005 point 8). The JSON writer writes that name in a new form, and the CSS writer and the JSON writer's older form, which have no form for a file, each report the role as a loss (DEC-005 point 9).

### 5. The capability reads the encodings that every output draws alike

- **What is read.** An encoding is read where every output version 1 hands out draws it alike, and where it gains a picture on a screen more than the decoder it costs a renderer. Every renderer the capability ships draws each encoding read, or reports a loss (DEC-005 point 9).
- **Read:** a PNG of 8 bits or fewer for each sample, of any colour type, a palette and transparency included, and a JPEG of 8 bits, in grey or in colour, baseline or progressive.
- **Refused, each with its fix:** a PNG of 16 bits, an interlaced or an animated PNG, a JPEG in CMYK, a JPEG whose orientation tag turns it, and every other encoding, such as a JPEG of 12 bits. The capability's reference names each encoding read, and each refused encoding's fix.
- **What its bytes are.** The file's first bytes say whether it is a PNG or a JPEG, and its extension must say the same.
- **A colour profile is kept.** A picture that carries one is drawn by it, and each renderer passes the profile on with the picture.
- **What the viewing step may not show.** Its tool for the SVG renderer's pages may draw a picture without its profile, and its report then says so ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3).

### 6. A size shows the same file, fitted to its frame

- **The same file,** drawn whole, centred, as large as its frame allows, as every image is. The part's formulas size the frame from the width it gets, and its height may come from the picture's proportions ([visual-communication:DEC-021-size-and-shape] point 6).
- **Another file at a size** takes a component's switch or a `when` by the size, which names another field, another file of the library or another role (DEC-021 point 3).
- **A picture role may also take another file at a size,** from the brand (point 4).
- **A file has one pixel size.** Shown larger than its pixels, it blurs, and no check reads that yet.

### 7. Each renderer is handed the file each image shows, and the seam's version rises once

- **The scene's image names what it shows.** A produced output keeps its variants by key and its exposed points (DEC-005 point 5). A picture file is named by where it lies, the piece or a library's version, and its name, and has no points.
- **A picture role stays a role,** as a colour does (DEC-005 point 5). Its value in each combination comes from the document of values (DEC-005 point 7).
- **Each property names its source.** `content` takes the file from the content's field, `file` from the component, as a library's default, and `role` from the brand's value (DEC-005 point 5).
- **The engine resolves every image to a file.** For each combination drawn, it takes a produced output's variant from the scene, and a picture role's file from the document of values. No renderer reads that document for a picture.
- **What a renderer is handed.** For the combination it draws, the file each image shows there, and whether it is a PNG or a JPEG. It draws every image from that, whatever its source, as it is handed the colours of that combination.
- **The seam's version rises, once for this record** (DEC-005 point 8).
- **A page that changes modes while open** needs each mode's logo, as it needs each mode's colours. How a page holds its modes is [visual-communication:DEC-023-html-page-modes]'s.

### 8. The command that moves a piece onto another brand names what does not follow

- **The moment.** A lock names the brand's version (DEC-001 point 7), so a change of brand is a move of the lock. The render of a draft that is not pinned makes that move, and a pinned or a published piece's lock moves by the command that moves it, or by hand.
- **Who says it.** Each command that moves a piece's lock off one brand and onto another says it in its output.
- **What it says, in each language.** Each picture file of the piece that a scene shows, whoever names it, and each picture role a part shows that the new brand gives no value, each with its trace id.
- **Said, never kept.** No record keeps it, and the check is silent on it.
- **The before-and-after says it too,** wherever its two locks name different brands ([visual-communication:DEC-019-lock-moves-and-pruning] point 5). A reviewer of a published piece's move reads that command and the change, not the run's output.
- **A lock a person writes by hand** moves with no command, under the brand its writer chose. The before-and-after's look back says it to a reviewer of the change.
- **Not a library's own file,** which is part of the form its owner chose for every brand (point 3).

### 9. What the check and an export report

Each finding below fails validation where it lies in a file the project can correct, and asks for attention elsewhere, as in a released library version (DEC-002 point 7).
- **Where each lies.** A finding on a picture of the piece lies at the piece, and one on a library's picture in that version. A fault that only a lock's combination of a base and a brand built on it shows lies at that lock.
- **Fails validation:**
  - an `image` part that names none of `produced`, `content`, `file` and `role`, or more than one
  - a picture's name not of point 2's shape, a name its folder does not hold, or one that names a symbolic link
  - a picture file that cannot be read, that a large-file store holds, of an encoding point 5 refuses, or whose bytes are not what its extension says
  - a `role` that names no picture role, or a picture role's value that names a file its brand's version does not hold
  - a picture role given in some value combinations of a key and not in others, or given files of two proportions there
  - a role of the type `picture` that a library other than the foundations declares
- **Stated as a fact, in a brand's version:** each shared picture role it gives no value, once. No piece states it.
- **An export refuses** a piece whose picture file, the piece's or a library's, is missing or cannot be read, as it refuses a missing produced picture.
- **A release refuses** a version whose picture fails, as it refuses any finding that fails ([visual-communication:DEC-003-change-over-time] point 6).
- **A final piece's pictures are not judged,** as its content is not (DEC-002 point 7).

### 10. A new top group breaks the foundations, so the picture group lands before their first release

- **Every new top group of the shared roles breaks the foundations** once they are released, even where each of its roles carries a default.
- **So the type `picture`, the group `picture` and `picture.logo` land before the foundations' first release** ([project-kit#2611](https://github.com/aleskalfas/project-kit/issues/2611)), with the rule that no brand owes a picture role, a brand's exports of one, and the fact a brand's version states (point 9).

### 11. What stays out

- **A picture's text,** what a reader who does not see it gets, is left to the record of a run's structure ([project-kit#2739](https://github.com/aleskalfas/project-kit/issues/2739)).
- **What else waits,** beyond what a point marks as waiting, is listed under Implications.

## Rationale

**What waits.** Each rule marked "for now", and each encoding refused, widens later without refusing a file that was accepted (DEC-003 point 3), so the narrower rule comes first.

**Why each language names its own.** A picture the content names is content, as its text is, and a picture every language shares costs one line in each content file.

**Why a bare name, found among the listed files.** A name with no `/` cannot leave the folder, start at the root, or reach what a program writes, a version handed out or a published piece's copy (DEC-016 point 3). Version control's list gives one answer on every file system, where two names that differ only in case are one file on some and two on others. A symbolic link may lead out of the folder or to a file another clone lacks, and the engine reads no large-file store (DEC-001 point 8). Judging only a name the content gives keeps every folder that format 1 accepted accepted, and the folder keeps a piece's pictures with it when it is copied, archived or removed (DEC-002 point 1). Reading the folder whole, as the rest of the piece's own files are read, costs this: a file no part shows, added to a published piece, puts its copy out of date.

**Why a library's file is the component's.** A library's plain files are part of its form, set apart from raw values (DEC-001 point 5), and which file a mode shows is the brand's to choose. A brand built on another keeps its parts, so a `file` in a brand's own part would show the base's logo under every such brand (DEC-004 point 6).

**Why a logo is a brand's value.** Three forms were weighed:
- **A logo given as content, and a brand's own logo drawn by the brand's drawing of a layout** ([visual-communication:DEC-009-layout-defaults] point 2). Rejected. It asks for nothing new, but a logo given as content stays when the brand changes (DEC-001 point 3), and a dark mode has no logo of its own. A brand takes over a whole layout to show its logo, and its drawing still cannot reach inside a `header` that a slot holds.
- **A named file of the brand, which a part asks the piece's brand for.** Rejected. It needs no new type of role, but it follows no mode, and needs rules of its own for a base, for what a base opens and for what a brand exports, which roles already have.
- **A picture as a brand's value,** the form chosen. A brand already holds pictures as values, which a value axis changes and a part names by role (DEC-004 points 1 and 2). For a type and one rule, a dark logo, a phone's logo and a base's logo need nothing new.

**Why no brand owes a picture role, and only a picture goes without.** A shared role with no default breaks every brand once the foundations are released (DEC-004 point 5), and a default aliases an older role, never a value (DEC-004 point 7), where no picture role exists to alias. A part not drawn takes the place a missing optional part takes, which every formula already holds (DEC-005 point 3). A missing colour or size has nothing to draw in its place.

**Why every value mode or none, and one proportion.** Without both, one scene would draw the part in one mode and not in another, or move the page on a value axis, since an image's height may come from the picture's proportion (DEC-004 point 2). A produced picture's variants share one pixel size because its exposed points are measured in pixels (DEC-005 point 5). A picture role has no points, so a dark logo saved at twice the pixels still fits.

**Why one group, the foundations' alone for now.** One group reserves once, for every later picture role, a name no library may take (DEC-004 point 7). A library's own picture role would need rules against those that make a brand owe a library's role with no default ([visual-communication:DEC-008-library-role-defaults] point 4), and no part needs one yet.

**Why the group stands as its token.** DEC-004 words what a brand exports, opens and types in terms of tokens (points 5, 6 and 11), so one sentence keeps each of those rules, where an exception in each would spread the type through them all.

**Why an empty group.** DTCG 2025.10 has no type for a file, and asks every token to use a type it defines. An empty group may carry extension data, which tools keep ("Groups" in DTCG 2025.10), so other tools read the brand's file and skip the role, where a token of another type, such as a number, would mislead them. The cost is a second form to read for good, if a later change takes the type for a file that DTCG lists among those still to document.

**Why only the encodings every output draws alike.** A picture that draws in the HTML and fails in the PDF is found only once it is handed out. Refusing an encoding costs a person one save, and reading it costs the PDF renderer, which embeds each picture by its own code, a decoder. A palette PNG and a progressive JPEG, the forms a logo or a photo for a screen usually comes in, are worth theirs. A 16-bit PNG gives a screen nothing, and an interlaced one gains nothing in a file that arrives whole. CMYK belongs to print, which version 1 leaves out, and a browser and a PDF viewer convert it in their own ways. A browser plays an animation and turns a photo by its orientation tag, and a PDF does neither. An extension is only a name, and a renderer that trusted it would embed a JPEG as a PNG.

**Why a colour profile is kept, and a turned photo refused.** A phone's photo often carries a gamut wider than sRGB. Dropping its profile would dull it everywhere, refusing it would refuse most phones' photos, and a browser and a PDF viewer both draw by a profile passed on with the picture. One save fixes a turn and loses nothing, where nothing removes a profile without changing the photo's colours.

**Why the same file at every size.** The frame follows the size, so the picture does too, and the switch that chooses another file needs nothing new.

**Why a picture role stays a role in the scene.** The scene holds every value that moves nothing as its role, so one scene serves every value mode (DEC-005 point 5).

**Why the seam rises.** A renderer built for an earlier seam looks a picture up by its produced output and writes it as PNG data, so it would draw a picture file, a picture role or a JPEG wrong with no error. The version exists so the engine refuses such a renderer, and rose so for runs ([visual-communication:DEC-012-text-runs], Implications). The seam is never kept, so the rise costs nothing outside the capability.

**Why the command that moves the lock says it.** The lock's move is the one moment a command sees the old brand and the new, and none of the piece's picture files follows the new brand (DEC-001 point 3). The check reads the files as they are, so it cannot tell a change of brand from a piece that always had its brand (DEC-002 point 7), and said at every render the report would ask nothing of anyone. A comparison is a command's (DEC-002 point 7), and the before-and-after is the one a reviewer runs.

**Why a fact in the brand, and none at the piece.** A brand's owner may forget its logo, and one fact in its version tells them. A piece meets a brand without a logo at the change of brand, where point 8 says it.

**Why every new top group breaks the foundations, and the picture group lands first.** A new top name fails any library already named so, at its lock (DEC-004 point 7), as a later `shadow` or `radius` with defaults would. Before the first release no released foundations exist for anything to build on, so the group breaks nothing then.

### Alternatives considered

- **A shared picture role whose default is a blank picture.** Rejected. A blank would draw an empty frame under every brand without a logo.
- **A path relative to the piece's folder.** Rejected. Each way out of the folder would need a rule of its own.
- **One file for every language.** Rejected. It would refuse a screenshot, which shows its language.
- **A `content` field that may also name a produced output.** Put off until a producer ships.
- **A pinned decoding library for the PDF renderer.** Put off. It would add only a 16-bit or an interlaced PNG, and an animation, a turn and CMYK would still draw otherwise in a browser and in a PDF.
- **A fact at each picture, or at each piece whose part shows no logo.** Rejected. Each fires on every piece and asks nothing of anyone, the shape DEC-009 rejects in its Alternatives considered.
- **The change of brand stated by the check, from a brand recorded at the last render.** Rejected. The check would read a moment that has passed, not the files as they are.
- **A picture role's value as a token of the capability's own type.** Rejected. The brand's file would leave the DTCG format.
- **A picture role's files carried in the scene, as a produced picture's variants are.** Rejected. A value would reach a renderer two ways, and the scene would hold a brand's files.
- **A shared picture role at the top of the shared roles, as `logo`.** Rejected. Each later picture role would reserve one more library name.
- **The picture group after the foundations' first release, in their next major.** Rejected. Every library and piece built on the foundations would move to that major for one name, and a shared header would show no logo until then.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-001 point 3, "A picture made elsewhere is content"** comes to say that it lies in the piece's folder, under a name its content gives, and that a command moving the lock onto another brand names it.
  - **DEC-004 point 1, "Each role is a token"** comes to say that a picture role's value is an empty group at its path, which names its file in the extension point, aliases nothing, merges in the Resolver's order of sources, and stands as the role's token wherever the records speak of one.
  - **DEC-004 point 5, its opening** comes to say that a brand exports a picture role only where it gives it a value.
  - **DEC-004 point 5, "Breaking changes"** comes to count a new shared role with no default as breaking only where it is no picture role, and adds, for the foundations, a new top group of the shared roles, which may meet a library's name. **"Not breaking"** comes to add a new picture role, and a brand that comes to give one a value.
  - **DEC-004 point 7, "A shared role the foundations add after their first version"** comes to except a picture role, which carries no default and which no brand owes.
  - **DEC-004 point 11, "a role with no value in some combination"** comes to except a picture role, and to add a picture role given in some value combinations of a key and not in others, or given files of two proportions there.
  - **DEC-005 point 5, the image's bullet,** comes to say that an image shows a produced output, a picture file of the piece or of a library, or a picture role, which stays a role, and that only a produced output holds variants and exposed points.
  - **DEC-008 point 2, "After it, the role carries a default"** comes to except a picture role, which needs no default and no major.
  - **DEC-008 point 4, "What it owes a library it names"** comes to say "as it gives every shared role but a picture role one".
  - **DEC-008 point 5, "A brand's exports"** comes to leave out a shared picture role the brand gives no value.
  - **DEC-014 point 1, "Read in full first"** comes to add that the full read reads each picture file the version holds, as the engine reads it.
  - **DEC-022's Implications, under "Left open"** come to answer "A logo in a header that follows the brand" with `picture.logo` shown by the header, and "A site shown inside a slide" with a picture of the page, given as a picture file, which does not follow the site.
- **Left open:**
  - **A content picture for each mode of a value axis,** such as a partner's logo on a dark page. A component cannot choose by a value mode (DEC-021 point 3), so it waits for a need.
  - **A part that shows something else where the brand gives no logo,** such as the site's name. A `when` that reads a role waits for a need.
  - **A picture in written code that code outside the location can find,** since the JSON writer writes the file's name in the brand's version, which only the library copy holds.
  - **A bound on a picture's file size.**
  - **A notation's marks,** which reach a part with the icons a notation maps, in a later change (DEC-004 point 10).
  - **A picture that reads another piece,** so that a site shown in a slide follows the site, waits.
  - **An SVG file as a picture, and a picture cropped to fill its frame.** A person saves a logo as a PNG large enough for its largest frame.
