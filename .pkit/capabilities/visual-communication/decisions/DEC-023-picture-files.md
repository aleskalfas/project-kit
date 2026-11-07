---
id: DEC-023
title: A piece shows a picture file it holds by name, and a brand gives its logo as a value
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person puts a picture, such as a photo or a logo, in the piece's folder, and the content names it by its file name. Each language may name its own. The capability reads PNG and JPEG files stored in the ways every output draws alike, and refuses the rest with the fix. A library's part may show a file of its own library, the same in every mode. A logo that follows the brand is the brand's value. The foundations declare a picture role, `picture.logo`, which a brand gives a file, perhaps another in a dark mode. No brand owes one, and a part that shows it is not drawn where the brand gives none. The role and its group land before the foundations' first release, since a new group of the shared roles breaks the foundations after it. Each renderer is handed the file to draw, whatever its source. A command that moves a piece onto another brand names each picture file of the piece that stays as it was, and each logo the new brand lacks, and the before-and-after says the same.

## Context

The founding record makes a picture made elsewhere content. It does not follow a brand, and a change of brand reports it ([visual-communication:DEC-001-visual-communication-discipline] point 3). It lies in the piece's folder, apart from what a program writes ([visual-communication:DEC-002-files-and-validation] points 1 and 5). A library's plain files are files of its own, not values (DEC-001 point 5). A brand holds pictures as values, written in the extension point and changed by a value axis ([visual-communication:DEC-004-brands-and-notations] points 1 and 2).

Version 1 of the capability designs web pages, portals and decks under a brand, handed out as HTML and PDF ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)). A piece shows a picture file a person gives it, such as a logo or a photo. Pictures a program makes, such as a 3D render, wait for version 2.

What stands in the way:
- **No picture can reach a piece.** An `image` part shows a produced output alone, and no producer ships. The SVG renderer writes every picture as PNG data, and the PDF renderer refuses every image.
- **A logo cannot follow the brand.** A shared part names no brand, so it cannot name a brand's file. A piece that places `{use: <brand>/logo}` locks that brand, whichever brand it names. The record of a web page leaves a logo in a shared header to this record ([visual-communication:DEC-022-web-site-and-parts], Implications).
- **A file can draw in one output and fail in another.** A PNG may be palette, 16-bit or interlaced, and a JPEG may be CMYK or progressive. A browser draws most of them, and the capability's own PDF renderer draws only what its code decodes.
- **No command changes a brand.** A person edits a field of the piece's file, so the report at a change of brand has no moment yet.
- **A fact on every picture** would fire on every piece and ask nothing of anyone. The record of layouts rejects that shape ([visual-communication:DEC-009-layout-defaults], Alternatives considered).

Three terms:
- A *picture file* is a PNG or a JPEG file that a person puts in a piece or in a library's version. A produced picture is none ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 1).
- A picture file's *encoding* is how it stores its pixels and says how to show them, such as a palette PNG, a progressive JPEG or an orientation tag.
- A picture file's *bare name* is its file name alone, with no folder in it.
- A *picture role* is a role whose value is a picture file of the brand.

## Decision

**A piece holds its picture files in a folder of its own, and content names one by its bare name. A library's part names a file of its own version. A brand gives a picture role, such as `picture.logo`, a file, and no brand owes one. The capability reads the encodings every output draws alike. Each renderer is handed the file each image shows. A new group of the shared roles breaks the foundations once released, so the picture group lands before their first release.**

### 1. Content names a picture file in a field that an `image` part shows

- **What an `image` part shows.** One of four things, each named by one property: `produced`, as format 1 has it, `content`, `file` or `role`. A part names exactly one of them.
- **`content: <field>`.** The field's value is the name of a picture file of the piece (point 2), held as text.
- **Each language names its own.** The value is content, so each content file gives its own, as it gives its own text. So a screenshot can show each language's screen.
- **A picture shared by every language** is named in each content file.
- **An empty field draws nothing.** The part is not drawn, and has zero size at its place ([visual-communication:DEC-005-engine-and-plugins] point 3).
- **A file, never a produced output, for now.** Letting the field name an output too refuses nothing later ([visual-communication:DEC-003-change-over-time] point 3).

### 2. A picture file lies in the piece's `pictures/` folder, under a bare name

- **The folder.** A piece's picture files lie in one folder of its own folder, `pictures/`, apart from what a program writes (DEC-002 point 5).
- **A bare name's shape.** Lower-case letters, digits and hyphens, starting with a letter, then a full stop and its extension: `png` for a PNG, `jpg` or `jpeg` for a JPEG.
- **What that keeps out.** Such a name holds no `/`. So it cannot leave the folder, start at the root, or reach what a program writes, a version handed out or a published piece's copy ([visual-communication:DEC-016-what-an-export-reads] point 3).
- **Found by its exact name** among the files of the folder, as version control lists them, never by asking the file system. Two names that differ only in case are one file on some file systems and two on others. So `logo.png` never finds `Logo.png`, on any machine, and a file the clone ignores is no picture.
- **Only a name the content gives is judged.** A file of the folder that nothing names takes no finding, so a folder that format 1 accepted stays accepted.
- **No symbolic link,** since one may lead out of the folder, or to a file another clone lacks.
- **Its bytes are committed.** A pointer that a large-file store keeps in its place is no picture, since the engine reads no store (DEC-001 point 8).
- **No folder within, for now.** Allowing one in a name later refuses nothing.
- **One of the piece's own files.** So the findings key and an export's fingerprint read it, with no rule of its own (DEC-016 points 1 and 2). They read the whole folder on purpose, as they read the rest of the piece's own files. So a file that no part shows, added to a published piece, puts its copy out of date.

### 3. A library's part shows a file of its own version, the same in every mode

- **`file: <name>`.** A part of a library's component names a picture file of that library's version, by a bare name, in the version's `pictures/` folder.
- **A brand's own parts** name the brand's files so (DEC-004 point 1). A brand's own part shows the brand's logo by `role: picture.logo`, never by `file`. A brand built on it keeps its parts, so a file there would show the base's logo under every such brand (DEC-004 point 6).
- **A local component's library is the piece,** so its `file` names a picture file of the piece.
- **The component names it, not the content.** A library's plain file is part of its form, not a value a role stands for (DEC-001 point 5).
- **One file in every mode and under every brand.** A plain file follows no mode. A picture that must follow one is a picture role (point 4).
- **Under the lock.** A released version's hash reads every file of its folder, so its pictures change only when a person moves the lock ([visual-communication:DEC-001-visual-communication-discipline] point 7).

### 4. A brand gives a picture role a file, and no brand owes one

- **A type of role.** A picture role has the type `picture`. Its value is a picture file of the brand's version, in its `pictures/` folder.
- **The shared picture roles lie in one group, `picture`.** The first is `picture.logo`, which the foundations declare with no default. A shared part, such as a header, shows the brand's logo by `role: picture.logo`.
- **Only the foundations declare a picture role, for now.** A library's own picture role waits for a need. Allowing it later refuses nothing.
- **No brand owes a picture role.** A brand that gives one no value is not at fault. A part that shows it is not drawn, and has zero size at its place (DEC-005 point 3).
- **Why only a picture.** A role may go without a value only where its absence draws as a missing optional part does. A picture's does, and a colour's or a size's has no such meaning.
- **So a new picture role breaks no brand.**
- **In every value mode, or in none.** Within one key over the size axes, a brand gives a picture role a value in every combination of the value axes, or in none. Otherwise one scene would draw the part in one mode and not in another.
- **One proportion within a key.** The files a picture role takes over the value axes, within one key, share one proportion of width to height. An image's height may come from that proportion, so another would move the page on a value axis (DEC-004 point 2).
- **By mode and by size, as any value.** A value axis may give a dark mode its own logo. A size axis may give a phone a smaller one (DEC-004 point 2).
- **A brand built on a base** keeps its base's logo, unless the base opens the role (DEC-004 point 6).
- **Its place in the brand's files.** DTCG 2025.10 has no type for a file, and asks every token to use a type it defines. So a picture role's value is an empty group at the role's path. It names the file in the capability's extension point, and aliases nothing (DEC-004 point 1).
- **It stands as the role's token** wherever the records speak of one, as in what a brand exports, opens or changes the type of (DEC-004 points 5, 6 and 11).
- **Merged as a token's value is,** in the Resolver document's order of sources. So a dark mode's source gives the dark logo over the default's.
- **A form kept for good.** The engine keeps reading every form a released brand may name (DEC-004 point 1). A later type for a file in DTCG would be read beside this one, never in its place.
- **Exported where it is given.** A brand exports a picture role only where it gives it a value. Ceasing to give one removes an exported name, which breaks the brand (DEC-004 point 5).
- **Written code.** The document of values comes to hold a picture role's value, the file's name in the brand's version, so its version rises once (DEC-005 point 8). The JSON writer writes that name in a new form. The CSS writer, and the JSON writer's older form, have no form for a file, so each reports the role as a loss (DEC-005 point 9).

### 5. The capability reads the encodings that every output draws alike

An encoding is read where two things hold. Every output version 1 hands out draws it alike. And it gains a picture on a screen more than the decoder it costs a renderer, as it does for the encodings a logo or a photo for a screen usually comes in. Every renderer the capability ships draws each encoding read, or reports a loss (DEC-005 point 9).
- **Read:**
  - a PNG of 8 bits or fewer for each sample, of any colour type, a palette and transparency included, since a logo often comes as one
  - a JPEG of 8 bits, in grey or in colour, baseline or progressive, since a photo often comes as one
- **Refused, each with its fix:**
  - a PNG of 16 bits, which gives a screen nothing, or an interlaced one, which gains nothing in a file that arrives whole. The fix is to save it at 8 bits, not interlaced.
  - an animated PNG, which a browser plays and a PDF cannot. The fix is to save its first frame as a still PNG.
  - a JPEG in CMYK, since version 1 leaves print and CMYK out, and a browser and a PDF viewer convert it to a screen's colours in their own ways. The fix is to save it in RGB.
  - a JPEG whose orientation tag turns it, since a browser turns it and a PDF does not. The fix is to save it upright.
- **The rest.** Every other encoding, such as a JPEG of 12 bits, is refused too. The fix is to save it as a PNG or a JPEG of 8 bits. The capability's reference names each encoding read.
- **What its bytes are.** The file's first bytes say whether it is a PNG or a JPEG, and its extension must say the same. So a JPEG named `.png` is refused.
- **A colour profile is kept.** A picture that carries one, as a phone's photo often does, is drawn by it. Each renderer passes the profile on with the picture, so a browser and a PDF viewer draw it alike.
- **What the viewing step may not show.** Its tool for the SVG renderer's pages may draw a picture without its profile. Its report then says so, as for anything its images cannot show ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3).
- **Widened later at no cost.** Reading an encoding that is refused now refuses nothing (DEC-003 point 3).

### 6. A size shows the same file, fitted to its frame

- **The same file,** drawn whole, centred, as large as its frame allows, as every image is. The part's formulas size the frame from the width it gets, and its height may come from the picture's proportions. So a picture follows the size ([visual-communication:DEC-021-size-and-shape] point 6).
- **Another file at a size** takes a component's switch or a `when` by the size (DEC-021 point 3). It names another field, another file of the library or another role.
- **A picture role may also take another file at a size,** from the brand (point 4).
- **A file has one pixel size.** Shown larger than its pixels, it blurs, and no check reads that yet.

### 7. Each renderer is handed the file each image shows, and the seam's version rises once

- **The scene's image names what it shows.** A produced output keeps its variants by key and its exposed points (DEC-005 point 5). A picture file is named by where it lies, the piece or a library's version, and its name. It has no points.
- **A picture role stays a role,** as a colour does (DEC-005 point 5). Its value in each combination comes from the document of values (DEC-005 point 7), so one scene serves every value mode.
- **Each property names its source.** `content` takes the file from the content's field, `file` from the component, as a library's default, and `role` from the brand's value (DEC-005 point 5).
- **The engine resolves every image to a file.** For each combination drawn, it takes a produced output's variant from the scene, and a picture role's file from the document of values. No renderer reads that document for a picture.
- **What a renderer is handed.** For the combination it draws, the file each image shows there, and whether it is a PNG or a JPEG. It draws every image from that, whatever its source, as it is handed the colours of that combination.
- **So the seam's version rises, once for this record.** A renderer reads an image otherwise than before, and a file that may be a JPEG (DEC-005 point 8). It rose so for runs ([visual-communication:DEC-012-text-runs], Implications). The seam is never kept, so the rise costs nothing outside the capability.
- **A page that changes modes while open** needs each mode's logo, as it needs each mode's colours. How a page holds its modes, both together, is [project-kit#2738](https://github.com/aleskalfas/project-kit/issues/2738)'s ([visual-communication:DEC-020-html-page-drawing] point 10).

### 8. The command that moves a piece onto another brand names what does not follow

- **The moment.** A lock names the brand's version (DEC-001 point 7), so a change of brand is a move of the lock. The render of a draft that is not pinned makes that move. A pinned or a published piece's lock moves by the command that moves it, or by hand.
- **Who says it.** Each command that moves a piece's lock off one brand and onto another says it in its output.
- **What it says, in each language.** Each picture file of the piece that a scene shows, whoever names it, since none follows the new brand (DEC-001 point 3). It also names each picture role a part shows that the new brand gives no value. Each is named with its trace id.
- **Said, never kept.** It tells of a move, and validation answers about the files as they are (DEC-002 point 7). So no record keeps it, and the check is silent on it.
- **The before-and-after says it too,** wherever its two locks name different brands ([visual-communication:DEC-019-lock-moves-and-pruning] point 5). A reviewer of a published piece's move reads that command and the change, not the run's output.
- **A lock a person writes by hand** moves with no command. Whoever writes it chose the brand. The before-and-after's look back says it to a reviewer of the change.
- **Not a library's own file.** It is part of the form its owner chose for every brand (point 3).

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
- **Stated as a fact, in a brand's version:** each shared picture role it gives no value, once. No piece states it, since it would fire on every piece under that brand.
- **An export refuses** a piece whose picture file, the piece's or a library's, is missing or cannot be read, as it refuses a missing produced picture.
- **A release refuses** a version whose picture fails, as it refuses any finding that fails (DEC-003 point 6). So a released version that keeps its hash holds no such picture.
- **A final piece's pictures are not judged,** as its content is not (DEC-002 point 7).

### 10. A new top group breaks the foundations, so the picture group lands before their first release

- **Every new top group of the shared roles breaks the foundations** once they are released. Its name is one no library may take (DEC-004 point 7), so it fails any library already named so, at its lock. That holds for a group whose roles carry defaults too.
- **So the type `picture`, the group `picture` and `picture.logo` land before the foundations' first release** ([project-kit#2611](https://github.com/aleskalfas/project-kit/issues/2611)). They land with the rule that no brand owes a picture role, a brand's exports of one, and the fact a brand's version states (point 9).
- **A Task of their own carries them,** apart from the rest of the picture file, so the first release waits only for it.
- **A later picture role lies in the group,** and breaks no brand (point 4).

### 11. What stays out

- **A picture's text,** what a reader who does not see it gets, is left to the record of a run's structure ([project-kit#2739](https://github.com/aleskalfas/project-kit/issues/2739)).
- **What else waits** is listed under Implications, each with what it needs.

## Rationale

**Why a logo is a brand's value.** Three forms were weighed.
- **A logo given as content, and a brand's own logo drawn by the brand's drawing of a layout** (DEC-009 point 2). It asks for nothing new. But a logo a person gives a shared part is content, so it stays when the brand changes (DEC-001 point 3). A dark mode has no logo of its own. A brand takes over a whole layout to show its logo, and its drawing still cannot reach inside a `header` that a slot holds.
- **A brand gives a picture as a value.** The records already hold this model: a brand holds pictures as values, which a value axis changes and a part names by role (DEC-004 points 1 and 2). It costs a type and one rule, that no brand owes a picture role. A dark logo, a phone's logo and a base's logo then need nothing new.
- **A brand holds a named file, which a part asks the piece's brand for.** It needs no new type of role. But it follows no mode. It needs rules of its own for a base, for what a base opens and for what a brand exports, which roles already have.

**Why no brand owes a picture role.** A shared role with no default breaks every brand once the foundations are released (DEC-004 point 5). A default aliases an older role of its type, never a value (DEC-004 point 7), and no picture role exists to alias. A part not drawn takes the place a missing optional part takes, which every formula already holds (DEC-005 point 3). Many brands have no logo, such as the neutral brand, and their pages draw no empty frame.

**Why the exception is a picture's alone.** Every other rule of roles assumes each role has a value in every combination. A missing colour or size has nothing to draw in its place. A missing picture has one: no part, at zero size. So another type joins only where its absence draws as plainly.

**Why a picture role's group stands as its token.** The records word what a brand exports, opens and types in terms of tokens (DEC-004 points 5, 6 and 11). One sentence that the group stands as the token keeps each of those rules as it is. An exception in each would spread the type through every rule.

**Why one proportion, not one pixel size.** A produced picture's variants share one pixel size, since its exposed points are measured in pixels (DEC-005 point 5). A picture role has no points. So only the proportion moves the page, and a dark logo saved at twice the pixels still fits.

**Why a fact in the brand, and none at the piece.** A brand's owner may forget its logo, and one fact in its version tells them. At each piece it would fire on every page under that brand, and ask nothing of the piece's author. That is the shape DEC-009 rejects. The moment a piece meets a brand without a logo is the change of brand, and point 8 says it there.

**Why one group for the shared picture roles, and only the foundations' for now.** No library takes the name of a top group of the shared roles (DEC-004 point 7). One group reserves one name, once, and every later picture role lies under it. A library's own picture role would need its own rules against the rules of a library's roles, which make a brand owe a role with no default ([visual-communication:DEC-008-library-role-defaults] point 4). No part needs one yet.

**Why every new top group breaks the foundations, and why the picture group lands first.** A shared role's first segment is a name no library may take, so a new one fails any library already named so, at its lock. That holds for a role with a default too, such as a later `shadow` or `radius`. So DEC-004 point 5 comes to count every new top group as breaking, not `picture` alone. Before the first release no released version of the foundations exists for anything to build on, so the group breaks nothing then. After it, the group waits for a major, which every library and piece built on the foundations must move to. A Task of its own keeps the first release from waiting on the rest of the picture file.

**Why a bare name, found among the listed files.** A path could leave the folder, start at the root, or reach what a program writes or what was handed out. Each would need a rule of its own, and a bare name keeps all of them out by its shape. Finding it among the files version control lists gives one answer on every file system, where asking each would not. A piece's pictures stay in its folder, copied, archived or removed with it in one step (DEC-002 point 1).

**Why each language names its own.** A screenshot shows its language. A rule that one file serves every language would refuse it, and naming one file in each language costs a line.

**Why only the encodings every output draws alike, and worth their decoder.** Version 1 hands a piece out as HTML and as PDF. A picture that draws in one and fails in the other is found only once it is handed out. Refusing an encoding at the check costs a person one save. Reading it costs the PDF renderer, which embeds each picture by its own code, a decoder for it. So an encoding is read only where what it gains a screen is worth that decoder. A palette PNG and a progressive JPEG are common, and every output can embed them. A 16-bit or interlaced PNG gives a screen nothing. CMYK belongs to print, which version 1 leaves out. A browser draws an animation or a turned photo otherwise than a PDF does. Refusing first is the side that can widen, since reading an encoding later refuses nothing (DEC-003 point 3).

**Why a colour profile is kept.** A phone's photo often carries a wider gamut than sRGB. Dropping its profile would dull it everywhere, and refusing it would refuse most phones' photos. A browser and a PDF viewer both draw by a profile passed on with the picture, so they draw it alike.

**Why a turned photo is refused, though a phone's portrait often is one.** One save fixes a turn and loses nothing. Nothing removes a profile without changing the photo's colours. So a turn costs the person one step, and a profile would cost the photo.

**Why the extension must match the bytes.** An extension is only a name. A renderer that trusts it would embed a JPEG as a PNG, so the check holds the two to each other.

**Why a library's file is the component's, and the same in every mode.** The founding record sets a library's plain files apart from raw values (DEC-001 point 5). A picture role makes a picture a value only where a brand gives it. A component that names its own file asks nothing of a brand, and the version's hash keeps it under a lock. A picture that follows a mode is a brand's choice, so it is a role.

**Why the same file at every size.** The frame follows the size, so the picture does too. A component's switch or a `when` already chooses by the size (DEC-021 point 3), and another file needs nothing more.

**Why a picture role stays a role in the scene.** The scene holds every value that moves nothing as its role, so one scene serves every value mode (DEC-005 point 5). A colour already reaches a renderer so. Putting the role's files in the scene would make a second way to carry a value.

**Why the seam rises.** Under the seam's version 3, a renderer looks a picture up by its produced output, and writes it as PNG data. A picture file or a picture role has no output, and may be a JPEG. A renderer built for version 3 would draw it wrong with no error, and the seam's version exists so the engine refuses such a renderer. The seam rose the same way for runs (DEC-012, Implications).

**Why the command that moves the lock says it, and the before-and-after.** No command changes a brand: a person edits a field. The lock's move is the one moment a command sees the old brand and the new. The check reads the files as they are, so it cannot tell a change of brand from a piece that always had its brand (DEC-002 point 7). Said at every render, it would ask nothing of anyone, as a fact on every picture would. A comparison is a command's (DEC-002 point 7), and the before-and-after is the one a reviewer runs, so it says it too.

**Why an empty group in the brand's files.** DTCG asks every token to use a type it defines, so a token of a type of the capability's own leaves the file outside the format. A token of another type, such as a number, misleads every tool that reads it. A group may be empty and carry extension data, which tools keep ("Groups" in DTCG 2025.10). So other tools read the file and skip the role. DTCG lists a type for a file among those still to document. The cost is a second form to read for good, if a later change takes that type.

### Alternatives considered

- **A logo given as content, with a brand's drawing for a brand's own.** Rejected, for the reasons above.
- **A named file of the brand, outside the roles.** Rejected, for the reasons above.
- **A shared picture role whose default is a blank picture.** Rejected. A default aliases a role, never a value (DEC-004 point 7). A blank would also draw an empty frame under every brand without a logo.
- **A path relative to the piece's folder.** Rejected. Each way out of the folder would need a rule of its own.
- **One file for every language.** Rejected. A screenshot shows its language.
- **A `content` field that may also name a produced output.** Put off. It refuses nothing to widen later, once a producer ships.
- **Every encoding a browser draws.** Rejected. The PDF renderer would need a decoder for each, or a picture would fail in one output.
- **A pinned decoding library for the PDF renderer.** Put off. It would read a 16-bit or interlaced PNG, which gives a screen nothing. An animation, a turn and CMYK would still draw otherwise in a browser and in a PDF.
- **A colour profile dropped, or refused.** Rejected, for the reasons above.
- **A fact at each picture, or at each piece whose part shows no logo.** Rejected. Each fires on every piece, and asks nothing of anyone.
- **The change of brand stated by the check, from a brand recorded at the last render.** Rejected. The check would read a moment that has passed, not the files as they are.
- **A picture role's value as a token of the capability's own type.** Rejected. The brand's file would leave the DTCG format.
- **A picture role's files carried in the scene, as a produced picture's variants are.** Rejected. A value would reach a renderer two ways, and the scene would hold a brand's files.
- **A shared picture role at the top of the shared roles, as `logo`.** Rejected. Each later picture role would reserve one more library name.
- **The picture group after the foundations' first release, in their next major.** Rejected. Every library and piece built on the foundations would move to that major for one name, and a shared header would show no logo until then.
- **The first release held for the whole picture file.** Rejected. Only the group meets a library's name. The rest breaks nothing when it comes later.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5).
  - **DEC-001 point 3, "A picture made elsewhere is content"** comes to say that it lies in the piece's folder, under a name its content gives. It adds that a command moving the piece's lock onto another brand names each such picture.
  - **DEC-004 point 1, "Each role is a token"** comes to say that a picture role's value is an empty group at its path, since DTCG has no type for a file. The group names its file in the extension point, aliases nothing, and merges in the Resolver's order of sources. It stands as the role's token wherever the records speak of one.
  - **DEC-004 point 5, its opening** comes to say that a brand exports a picture role only where it gives it a value.
  - **DEC-004 point 5, "Breaking changes"** comes to count a new shared role with no default as breaking only where it is no picture role. It comes to add, for the foundations, a new top group of the shared roles, which may meet a library's name. **"Not breaking"** comes to add a new picture role, and a brand that comes to give one a value.
  - **DEC-004 point 7, "A shared role the foundations add after their first version"** comes to except a picture role, which carries no default and which no brand owes.
  - **DEC-004 point 11, "a role with no value in some combination"** comes to except a picture role. It comes to add a picture role given in some value combinations of a key and not in others, or given files of two proportions there.
  - **DEC-005 point 5, the image's bullet,** comes to say that an image shows a produced output, a picture file of the piece or of a library, or a picture role. Only a produced output holds variants and exposed points, and a picture role stays a role.
  - **DEC-008 point 2, "After it, the role carries a default"** comes to except a picture role, which needs no default and no major, since no brand owes it.
  - **DEC-008 point 4, "What it owes a library it names"** comes to say "as it gives every shared role but a picture role one".
  - **DEC-008 point 5, "A brand's exports"** comes to leave out a shared picture role the brand gives no value.
  - **DEC-014 point 1, "Read in full first"** comes to add that the full read reads each picture file the version holds, as the engine reads it.
  - **[visual-communication:DEC-022-web-site-and-parts]'s Implications, under "Left open"**: "A logo in a header that follows the brand" comes to name this record's answer, `picture.logo` shown by the header. "A site shown inside a slide" comes to name its answer too: a picture of the page, given as a picture file, which does not follow the site.
- **Read against this answer, and left as they stand:**
  - DEC-001 point 5, since a library's plain files and the pictures in content stay files of their own, and a brand holds pictures as values.
  - DEC-001 point 8, since a picture file is made by no program the capability runs.
  - DEC-002 points 1 and 5, since a piece's pictures lie in its folder, apart from what a program writes.
  - DEC-002 point 3, "Other formats carry no binding", since a picture keeps its own format.
  - DEC-002 point 4, since a file's name is a field's value, not a name of the content's grammar.
  - DEC-002 point 7, since a change of brand is said by commands, and the check judges the files as they are.
  - DEC-003 point 3, since every file format 1 accepted reads as before: a file of `pictures/` that nothing names takes no finding. A new top group is a breaking change of the foundations, which DEC-004 point 5 comes to count.
  - DEC-003 point 6, since a release checks a version in full, its pictures among it.
  - DEC-003 point 8, since an unpinned draft's render moves its lock, and so makes the change of brand.
  - DEC-004 point 2, since a value axis already changes pictures.
  - DEC-004 point 3, since only a produced picture has variants.
  - DEC-004 points 5, 6 and 11, where they speak of a token, since a picture role's group stands as its token.
  - DEC-005 point 1, since its component chooses nothing: a part with no picture is not drawn, as one with no produced output is not.
  - DEC-005 points 7 and 9, since the document of values holds a picture role a brand gives, and a code writer reports a value it has no form for.
  - DEC-005 point 8, since the seam's version and the document's each rise once, as that point asks.
  - DEC-006 point 2, since a picture file's own colours and lettering change with neither the brand nor the language, though each language may name its own file.
  - DEC-006 points 3 and 4, since a produced picture keeps its rules, and lies apart from the piece's pictures.
  - DEC-006 point 7, since an export refuses a missing picture as it refuses a missing produced one.
  - DEC-008 points 3, 7 and 9, since only the foundations declare a picture role, so no library's own role is one.
  - DEC-009's rejection of a fact at each piece, since this record puts none there.
  - DEC-013 point 6, since the capability's own checks of its shipped versions take the full read of DEC-014 point 1.
  - DEC-015 point 3, since its opening sentence already has the viewing step's report say what its images cannot show, and a profile is among it.
  - DEC-016 points 1 and 2, since a picture file is one of the piece's own files, read whole on purpose.
  - DEC-016 point 3, since a bare name reaches neither folder.
  - DEC-019 points 1 and 5, since this record's point 8 adds what they say at a change of brand.
  - DEC-020 point 4, since a page file holds its pictures inside it, a PNG or a JPEG.
  - DEC-021 points 3 and 6, since a picture follows a size through its frame, or by a component's switch.
- **The Task that declares the picture role,** under [project-kit#2792](https://github.com/aleskalfas/project-kit/issues/2792), lands before the foundations' first release ([project-kit#2611](https://github.com/aleskalfas/project-kit/issues/2611)), which comes to wait for it (point 10). It adds the type `picture`, the group and `picture.logo` to the foundations' version being built, with the rule that no brand owes a picture role, a brand's exports of one, and the fact a brand's version states.
- **The Task that builds the picture file,** under the same Feature, builds the rest of points 1 to 9. It adds the three properties, the `pictures/` folders, the encodings read and the findings. It teaches the SVG and HTML renderers a JPEG and a colour profile, and the PDF renderer every image. It raises the seam's version, and the document's with the JSON writer's new form. A release comes to read each picture its version holds. It changes the capability's pages.
- **The Task of the web parts** shows `role: picture.logo` in the shared header, and a picture file in a part that shows one.
- **The use cases of giving a piece another brand and of making a brand** (UC-098's variant 3a, a picture that does not follow the brand, and UC-105's step 2, a brand's logo) come to read as this record decides, with the Task that builds it.
- **Left open:**
  - **A content picture for each mode of a value axis,** such as a partner's logo on a dark page. A component cannot choose by a value mode (DEC-021 point 3), so it waits for a need.
  - **A part that shows something else where the brand gives no logo,** such as the site's name. A `when` that reads a role waits for a need.
  - **A library's own picture role,** which waits for a part that needs one.
  - **A picture in written code that code outside the location can find.** The JSON writer writes the file's name in the brand's version, which only the library copy holds.
  - **A picture shown larger than its pixels,** which blurs, and a bound on a picture's file size.
  - **A notation's marks** reach a part with the icons a notation maps, in a later change (DEC-004 point 10).
  - **A site shown in a slide** takes a picture of its page as a picture file, which does not follow the site. A picture that reads another piece waits.
  - **An SVG file as a picture, and a picture cropped to fill its frame.** A person saves a logo as a PNG large enough for its largest frame.
