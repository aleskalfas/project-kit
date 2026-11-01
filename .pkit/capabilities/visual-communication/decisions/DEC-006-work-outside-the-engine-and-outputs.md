---
id: DEC-006
title: A program run while preparing may write a picture that follows the brand, and every export keeps its number
status: proposed
date: 2026-11-01
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a program run while a piece is prepared computes what the engine cannot, such as a ring of items or a 3D render. It may write a local component, and also a picture, which takes its values from the brand alone and holds none of the piece's words. Each such output says what it was made from, so a check can tell when it is stale. Every file a piece is handed out as is kept under a version number.

## Context

The founding record sends work the engine's tools cannot compute to a program run while a piece is prepared, never inside the engine ([visual-communication:DEC-001-visual-communication-discipline] point 8). Examples are items placed on a circle, the layout of a graph and a picture made by a program, such as a 3D render. The program is a *helper*, a script of the project's own, or a *producer*, a plugin the capability ships.

A local component holds no raw values, but a picture holds the brand's values in its pixels, so it needs rules of its own. A case asks for such pictures: a game platform draws its boards in 3D, and wants each in a game's manual, a deck and a documentation page, under each game's brand ([project-kit#2423](https://github.com/aleskalfas/project-kit/issues/2423)).

Three facts shape the rules on such a picture:
- **Text inside a picture** is measured from no committed font, and is not translated with the content.
- **A picture's look depends on the values it reads,** and a brand's modes on several axes multiply the combinations a piece is drawn in.
- **A program may call an outside program,** such as a browser that draws a 3D scene. Such a program can draw differently from one machine to another, and it updates itself outside the project.

A piece is also handed out as files, such as a PDF of a talk or a picture in a documentation page. The talk the design started from was drawn on a whiteboard service, which exported only whole boards ([project-kit#2424](https://github.com/aleskalfas/project-kit/issues/2424)). Once handed out, a piece's files are its real freeze, as the founding record says ([visual-communication:DEC-001-visual-communication-discipline] point 7). A figure in documentation must be committed for a repository host to show it, and kept fresh.

The core layer supplies one validation that the capability's check joins, with one severity that fails it (COR-055). Software-analysis keeps a fingerprint of the texts that a requirement's revisits depend on ([software-analysis:DEC-006-text-in-body] points 6 and 7). Living-docs decides where a page's images lie ([living-docs:DEC-002-visual-elements] point 5).

## Decision

**A program run while preparing may write a picture, as well as a local component, and the engine never runs it. A picture takes every value from the brand, holds none of the piece's words, and is made once for each distinct set of values it reads. Each such output carries a fingerprint of what it read, kept apart from what is only recorded. Every export keeps a version number, with a record of what it was made from.**

### 1. A program run while preparing may write a picture

A helper or a producer run while preparing may write a local component, and also a picture, such as a 3D render. The engine never runs either. The founding record sets this frame, and lets such a program write a picture ([visual-communication:DEC-001-visual-communication-discipline] point 8). This record decides the rules on both outputs beyond what the founding record sets.
- **Run on purpose.** No render, no check, no export and no upgrade runs a program. A person or an agent runs it.
- **Who starts it.** A helper runs as the project runs any script of its own, under the project's permission model (COR-028). A producer runs through a command of the capability.
- **What it reads is declared first.** Before it runs, a program declares its input files and the brand's values it reads, by name. It also declares what it reads from the engine, such as an element's measured frame.
- **Commands of the capability frame the run.** One, before the run, takes the fingerprint of what was declared (point 5) and hands over the declared values and frames, in the form the record of the engine and its plugins decides. Another, after it, checks that no input changed during the run and writes the record beside the output.
- **A helper stays the project's code.** It never goes into a library, since a library holds data. A helper that several pieces need is a sign that the engine lacks a tool, as the founding record says.
- **A local component that a helper writes** follows the founding record's rules for one, such as no raw values and text taken from the content. This record adds its fingerprint.
- **A graph's layout** is such work: a helper may arrange a graph while preparing. How its positions are kept, and how several views share one model, are decided by the change that builds them.

### 2. A picture takes its values from the brand alone, and holds none of the piece's words

These rules bind every picture made while preparing, whichever program writes it.
- **Values from the brand.** Every value the program applies that a role could stand for, such as a colour, comes from the brand the piece names, under its lock, as the founding record decides ([visual-communication:DEC-001-visual-communication-discipline] point 8). The program reads it through the document of resolved values that the record of the engine and its plugins decides.
- **Roles in what is written for the picture.** The inputs written for the picture, such as a 3D scene's lights and materials, name roles, never raw values. The schema of a producer's inputs refuses a raw value.
- **Art keeps its own.** A model, its texture and any lettering on the thing shown are art, made in the tools made for them. Their own colours and lettering change with neither the brand nor the language, as a content picture's do not.
- **None of the piece's words,** as the founding record decides. The piece places every word it says, such as a label, as ordinary text, measured from the committed fonts and translated with the content.
- **Exposed points.** The program also writes the picture's exposed points, the named points in its pixels that the piece may point at (the record of the engine and its plugins). The piece places a label at one, or ends a connector there, as parts of its content, by an option that names the picture's item and the point (the founding record, [visual-communication:DEC-001-visual-communication-discipline] point 6).
- **The same exposed points in every variant** (point 3), by name, so a label holds in every mode. The variants that one scene holds also keep each point at the same place, as the record of the engine and its plugins requires. A variant for another scene, such as one a size axis changes, may place it elsewhere.
- **What no check sees.** A check reads a program's inputs and the record beside its output, never what the program did. A project's script can read a file it did not declare, which its fingerprint then misses. A reviewer judges such a read, and a picture that breaks these rules, such as one with a label drawn into it.

### 3. One picture for each set of values it reads, at a fixed pixel size

- **Variants.** A picture is made once for each distinct set of the values it reads, never once for each combination of modes. Each is a variant, and combinations that give it the same values share one.
- **An example.** A picture whose colours change between light and dark, and not with contrast, has two variants, however many combinations the piece is drawn in.
- **Named by the brand's key.** A variant takes a key of the combinations it serves, as the record of brands and notations decides. The record beside the variants says which variant each combination takes.
- **Every variant travels with the scene,** so a medium that switches modes while open, such as a web page, switches the picture too. The record of the engine and its plugins decides how the scene holds them.
- **A fixed pixel size.** Each variant is made at a pixel size fixed before the program runs. It is given as an input, or read from the brand as one of its values. A medium that needs more pixels, such as print, gets them through that size, never from a renderer. A size that an axis changes gives a variant of its own, by the rule above.
- **Exposed points scale with the picture.** They are written in the variant's pixels, and the engine maps them into the frame the picture fills.

### 4. Where produced output and written code live

- **In the piece that uses it.** A produced picture, or a local component a helper writes, lives in the folder of the piece that uses it, with its record beside it. It is made under that piece's lock, so another piece under another lock makes its own.
- **Committed.** Both are committed, so the scene and the check read them on a fresh clone without running the program.
- **Apart from content.** Produced output is kept apart from the pictures the content holds, such as a screenshot, as the record of files and validation keeps what a program rewrites apart from what a person writes ([visual-communication:DEC-002-files-and-validation] point 5). Living-docs keeps produced images apart from hand-made ones the same way ([living-docs:DEC-002-visual-elements] point 5).
- **Never in a library copy.** A library copy that a lock names is never rewritten, as the founding record says ([visual-communication:DEC-001-visual-communication-discipline] point 11). A library may hold a model, or a picture, as a plain file, and a component may declare a slot that a produced picture fills.
- **Written code,** such as CSS variables, goes where its declaration names, with its record beside it, as the record of files and validation places them ([visual-communication:DEC-002-files-and-validation] point 1). The code that reads it, such as a web page or a game, lives in the project's tree.
- **Written code follows its declaration's lock,** which a person moves on purpose (the record of the engine and its plugins). The lock says what the code holds, so the code takes no numbered versions.
- **Whether written code is committed** is the project's choice, as for any file its own build writes, and its record goes with it. Where neither is present, as on a fresh clone that commits neither, the check states that as a fact and names the command that writes them.

### 5. A fingerprint says when output is stale, and the rest is only recorded

Each output of point 1, and each file of written code, carries a record beside it. The record holds a hash of each thing the program read, and its *fingerprint* is the hash of them all. A command of the capability writes it, so nobody writes a fingerprint by hand. Every fingerprint the capability keeps, an export's included (point 7), follows this point and the next.
- **What it compares:**
  - each input file, a helper's own files among them
  - each value it read from the brand, in each combination of modes it serves, from the brand version its lock names
  - what it read from the engine, such as an element's measured frame
  - each variant's pixel size
  - a producer's or a code writer's own version
- **Values, not versions.** Everything a program read is compared by its value. So a release of the engine that changes a measurement makes stale only the outputs that read it.
- **A plugin's own version** is the one thing compared by version, since what a plugin does inside is no value a check can read. The record of the engine and its plugins decides how a plugin is versioned.
- **What is only recorded:** each outside program the program called, with its version, and the machine, the time and the capability's version. They are kept beside the fingerprint and never compared.
- **The check verifies it** within validation, and runs no program. An output whose fingerprint no longer verifies is *stale*. The finding names each thing that changed, and the program to run again.
- **A combination that the record maps to no variant,** such as one a brand's new mode adds, makes the picture stale too.

### 6. The fingerprint's form

The fingerprint follows the shape software-analysis gives the fingerprint of a requirement's texts ([software-analysis:DEC-006-text-in-body] point 7). It reads files and values instead of texts.
- **One reading.** Each thing is read in one canonical form, so the same input gives the same fingerprint on every machine.
- **An input** is a file, or a part of a content file named by its path of keys. A file of the capability's format, or a part of one, is read as the value the converters give, in one canonical text (the record of change over time, [visual-communication:DEC-003-change-over-time] point 2). So an edit elsewhere in the file changes nothing. Any other file, such as a model, is read as its bytes.
- **Across a change of format.** A fingerprint names the format number it read at, and the check reads each input converted to that number, so a release that raises the number makes no output stale. The command that rewrites a file to a newer format takes again each fingerprint that verified before it.
- **A value** is read in the form's own canonical text for its type, such as one notation for a colour. So a value written another way gives the same fingerprint, whatever document carried it.
- **Its version and hash.** The fingerprint names the form's version and the hash it uses. A version fixes how each kind of thing is read, and tests of example inputs pin each one.
- **Each version kept.** The check verifies each fingerprint under the version it names, so the capability keeps every version it shipped. The command may rewrite a fingerprint that verifies into the current version without running the program.

### 7. Every export keeps its number

An *export* is a file a piece is handed out as, such as a PDF or a picture, in a format the piece declares. The record of change over time decides a piece's states ([visual-communication:DEC-003-change-over-time] point 8). A final piece was handed out, and a published one is kept current where others read it.
- **Made from the scene.** A renderer that needs no service draws it from the scene. It is never fetched from a medium that others can edit, such as a board. So a handed-out file depends on no service, and on no edit left there.
- **What a run makes.** An export run makes each format the piece declares, in each of its languages and each combination of modes the piece names (the record of the engine and its plugins). A format whose medium switches modes while open, such as a web page, holds the modes of the value axes in one file.
- **A number for each run.** Each export run is one version, numbered within its piece, and every language, format and combination of modes it makes shares that number. So version 3 in English matches version 3 in Czech. No export overwrites another.
- **The name carries it.** Each exported file's name carries its piece's name and its version, since an exported file travels alone.
- **The piece may show it too.** A component may show the facts of the export it is drawn for, such as a version line on a deck's first page: the version, its date and its language, and the piece's state. The export fills them in as text, as an office suite fills a slide number or a date. They are inputs of the scene computed for the export, beside the files, and a preview fills them as the next export would. How the check measures such text, so that the same files still give the same answer, is decided by the change that builds exports.
- **The record of exports** holds, for each version, a fingerprint of every file its scene was computed from. Those are the piece's own files, its lock and the outputs of point 1 among them, and any shared content it reads. It also holds a hash of each file the version wrote. The engine's version is only recorded (below), so a release of the capability makes no export stale.
- **What it only records:** when the version was made, the piece's state then, and the versions of the engine, the renderers and each outside program. It names each output of point 1 the version used, and any it used while stale.
- **No stale output.** An export stops on a stale output of point 1 and names it. The person who runs it may say to use the output as it is. A final piece's exports use its outputs as they were handed out.
- **Where a version lies.** An export run writes its files where previews lie, local to each clone and never committed (the record of files and validation, [visual-communication:DEC-002-files-and-validation] point 1).
- **What is committed, in the piece's folder.** The version a person names as handed out, when marking the piece final (the record of change over time), is moved into the piece's folder and committed as its real freeze. A published piece's current copy and the record of exports lie there and are committed too. So the piece stays one folder, copied, archived or removed in one step. Every other version stays on the machine that made it.
- **A published piece's current copy.** A published piece keeps an unnumbered copy of each file its export makes, which a page links to, since a link cannot follow a number. Where a documentation page shows the copy, it lies where the documentation's rules put that page's produced images ([living-docs:DEC-002-visual-elements] point 5). The piece then names that place, and the copy is written there. Removing the piece removes the copy.
- **Previews are not exports.** A render made for a person to look at takes no number and is never committed.

### 8. What the check reports, and how seriously

These findings join the capability's check within validation, at the severities that the policy of the record of files and validation allows ([visual-communication:DEC-002-files-and-validation] point 7, COR-055). An output that people or other software read directly fails when something it read changed. One that reaches a reader only through a piece asks for attention, since the piece's exports guard it.
- **They fail validation,** each an invariant the project mends in its own files:
  - an output of point 1, or a file of written code, with no record, or a record that names a variant whose file is missing
  - variants of one picture whose exposed points differ in their names, or variants one scene holds that differ in pixel size or in the places of their exposed points (the record of the engine and its plugins)
  - a label placed at an exposed point that the picture's frame cuts off
  - a file of written code, or a published piece's current copy, stale because something it read changed
  - a file of the version a piece was handed out with that is missing, or whose hash no longer matches
- **They ask for attention:** a stale picture or local component, and a published piece's current copy made over a stale output, until both are made again. So is written code stale only by its writer's version: its values still hold, so a release of the capability fails no project.
- **Never reported:** an outside program whose version differs from the one recorded, and a final piece's outputs that a change made stale. A final piece keeps them as they were handed out.

## Rationale

**Why a program may write a picture.** A picture a program makes holds the brand's values in its pixels, so the engine cannot colour it as it colours data. Kept as content made elsewhere, it would follow no brand, and the founding record reports such a picture at every switch ([visual-communication:DEC-001-visual-communication-discipline] point 3). Fed only the brand's values while preparing, it follows the brand, and the engine still runs no program.

**Why a helper runs as the project's own script, framed by commands.** A command of the capability that ran a project's script would run that code with the trust the project gives the capability's commands. Run as the project runs its own scripts, it stays under the project's permission model (COR-028). The commands before and after the run refuse a record whose inputs moved during it. A record written from inputs read after the run could describe inputs the output was not made from.

**Why none of the piece's words in a picture, and why exposed points.** A word that the piece places is measured, broken into lines, translated and checked for fit in each language. A word drawn into a picture is none of these, and would need a picture for each language. An exposed point lets a label point into a picture, and stay text.

**Why one picture for each set of values.** The combinations of modes are the product of each axis's modes, so they multiply fast. A picture made for each combination would repeat identical files wherever an axis changes nothing it reads.

**Why a fixed pixel size.** The same inputs then give the same pixels, and an exposed point has one place in them. A renderer that chose a size would make a picture of its own, which no check could compare.

**Why produced output lives in its piece.** It is made under one piece's lock, from that lock's values, and another piece may lock another version of the brand. A library copy is never rewritten, so it cannot hold output that changes with a brand. The cost is a picture made again for each piece that shows it.

**Why compared by value, and outside programs only recorded.** A value read is what the output depends on, whichever release computed it. Compared by an engine's version instead, every release would make every such output stale, though few measurements change. An outside program, such as a browser, updates on its own and differs between machines. Compared, it would report pictures stale on every machine but one, and recorded, it explains a picture that differs after it is made again.

**Why software-analysis's shape, and why each version is kept.** One canonical reading, with its version and hash named, lets a value verify on every machine and under every later release. Software-analysis reads texts, and this form reads files and values, so only the shape is shared. Every version is kept, since a new one that made every output stale would run each program again with no input changed. A picture made again may differ in its pixels.

**Why a stale picture asks for attention, and what is read directly fails.** People read a published piece's copy, and a project's software reads written code, so either misleads at once when stale. A picture or a local component reaches a reader only through an export, which stops on it. A draft also goes stale and fresh many times while it is made, and its program may need an outside program the machine lacks.
- **The precedent.** Software-analysis fails a stale overview for the same reason as the copy: readers read it ([software-analysis:DEC-003-analysis-diagrams] point 8).

**Why a final piece's outputs are never reported stale.** A final piece keeps what it was handed out with, and making its pictures again would change it. A finding that must never be acted on would only be noise.

**Why every export keeps a number.** A handed-out file is what an audience saw, so it stays as it was, and a hash of it shows if it was overwritten. A number is short, sorts and is easy to say, as in "send me version 3", and the record keeps the time. A deck or a handout often shows its version on its first page, so the reader of a file that travels alone knows which one they hold. Content written by people cannot carry the number, since an export would then rewrite the content, so the export fills it in.

**Why in the piece's folder, and what is committed.** A piece is then one folder: what it is, its content and what it made. A repository host shows only committed files, so a published piece's copy is committed. A large file stays in a repository's history for good, so the versions nobody handed out stay out, local to the clone that made them, where nothing in the piece's folder has to keep them out of version control.

### Alternatives considered

- **A picture made by a program, kept as content made elsewhere.** Rejected. It follows no brand, and a page that switches modes would show the wrong picture.
- **A command of the capability running a project's helper.** Rejected. It would run project code with the trust given to the capability's commands.
- **A record written after the run from the inputs as they then are.** Rejected. An input changed during the run would be recorded as the one the output was made from.
- **One picture for each combination of modes.** Rejected. Identical pictures would multiply with every axis.
- **The engine's version in the fingerprint.** Rejected. Each release would make every output stale that read from the engine, measured or not.
- **Comparing an outside program's version.** Rejected. A browser that updates itself would make pictures stale on every machine but one.
- **A stale picture failing validation.** Rejected. A draft would hold every change of the project until its program ran again.
- **A date and time instead of a version number.** Rejected. It is long and hard to say, and the record keeps the time anyway.
- **Committing every version.** Rejected. Large files nobody handed out would stay in history for good.

## Implications

- **The walking skeleton** proves the seam with a small producer kept for its tests, which calls no outside program. It makes a picture once for each set of values, and places a label at one exposed point. It reports the picture stale when a value it read changes. It writes an export and records its version, and its code fixes the format of exposed points.
- **The change that builds the first real producer** decides the format of a 3D scene file, and may extend that of exposed points. It also tests whether two machines give the same picture, before any piece relies on one. It decides too what the capability adds to the permission model (COR-028) for the outside programs a producer calls.
- **Graph positions and shared models** are decided by the change that builds them, within point 1.
- **The record of the engine and its plugins** decides the document of resolved values, what a plugin declares and how it is versioned. It also decides how the scene holds a picture's variants and exposed points, and the lock in written code's declaration. And it decides how the engine hands a program what it computed, such as measured frames, computed without that program's own output.
- **The record of brands and notations** decides the key that names a combination of modes, and the key a variant takes.
- **The record of change over time** decides the states, how a piece becomes final and when a lock moves ([visual-communication:DEC-003-change-over-time] point 8).
- **A lock move's before-and-after** shows the committed pictures, reports the stale ones and runs no program.
- **The record of files and validation** decides where pieces and the declarations of written code lie, and the severity policy ([visual-communication:DEC-002-files-and-validation] points 1 and 7). It also decides how the outside programs a producer calls are checked ([visual-communication:DEC-002-files-and-validation] point 8).
- **The CLI reference** names the commands that frame a program's run, run a producer, export a piece and list a project's exports.
- **A documentation page** that shows a piece anchors the piece's content, never its copy, as living-docs asks ([living-docs:DEC-002-visual-elements] point 4).
- **Two branches that export one piece** may take one number, and the record of exports conflicts on merge. A version handed out never takes a new number. The other version takes the next free one, its files renamed with it.
