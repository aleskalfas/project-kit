---
id: DEC-060
title: One entry accepts every loss of a plugin's limit, across a piece or written code
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a renderer whose medium sets a property itself, such as a whiteboard service that sets its own line height, loses that property on every element that has it. Today each such loss is accepted by an entry of its own, which in a deck of two languages means hundreds. Such a loss is of a *limit*: a term of the capability's formats, such as a primitive, a property or a value type, that the plugin's declaration says it takes none of. The capability finds a limit's losses from the declaration before the plugin runs, and names the limit on each. One entry names the plugin and a limit, with a reason, and accepts every loss of it across the piece, or across written code for a code writer, those a later change brings included. Every other loss, such as a font a renderer cannot draw or a picture file missing, may be one nobody judged, so it is accepted at its place, as today. A renderer reports a font it cannot draw at the role that gives it, so one entry accepts it there. A renderer's declaration may say what it does with a primitive or a property it does not draw as given. A limit's name follows from its term, and a change to a term maps old names to new. The check fails an entry whose limit no term gives, and asks for attention to one that accepts nothing. The format gains one optional field, and the seam's version stays.

## Context

The record of the engine and its plugins gives every plugin, whether a renderer, a producer or a code writer, one form of loss report. Each loss names what was lost, by an element's trace id or a token path, what the plugin did instead, and why. A known loss may be accepted where the output is declared: in a piece for a renderer's or a producer's, and in written code's declaration for a code writer's. The check then stops repeating it ([visual-communication:DEC-005-engine-and-plugins] point 9), and a loss nobody has accepted asks for attention (DEC-005 point 14). An entry under `accept-losses` names the plugin, what it loses and a reason. It matches a loss by its plugin and what it loses alone, whatever mode the loss lies in (the capability's reference, "Accepting a loss").

So one entry accepts the losses at one element or one token. That serves a loss at a few places, such as a picture a renderer cannot draw. It does not serve a loss that follows from the medium:
- **A renderer for a whiteboard service** draws text at a line height the service sets, and may draw no path. It loses the first on every text, and the second on every path a piece holds. A deck of some hundred texts in two languages asks for an entry for each, and each text a later change adds is reported again.
- **A code writer** already loses so, at each token path. The CSS writer reports each token it writes that a size changes ([visual-communication:DEC-021-size-and-shape] point 8), and each picture role, for which it has no form.

The capability finds most losses before a plugin runs, from its declaration (DEC-005 point 9): a primitive a renderer refuses, a property of one it leaves out, a top's physical size it does not map, a value type a code writer has no form for, and a kind of axis it does not spell. A renderer finds the rest while it draws, and each the shipped renderers find so is a fault or depends on a value. One is a font file the PDF renderer cannot embed, which it reports at each text drawn in it.

The Feature that draws a piece for a whiteboard service without signing in needs this first ([project-kit#2569](https://github.com/aleskalfas/project-kit/issues/2569)). Which losses that renderer has, and the outcome its declaration states for each, is for the record of its projection to decide, drafted under [project-kit#3278](https://github.com/aleskalfas/project-kit/issues/3278). This record decides, for every plugin, what a limit is and how a loss is accepted by it, and for every renderer, where it reports a font it cannot draw and how its declaration states an outcome.

The capability's format grows by additions: no field becomes required, and no value accepted before is refused ([visual-communication:DEC-003-change-over-time] point 3).

## Decision

**A loss is of a limit where its plugin's declaration says the plugin takes none of a term the capability's formats define. The capability names the limit on each such loss, from the declaration, before the plugin runs. An entry under `accept-losses` names the plugin and either what is lost or a limit, with a reason. One that names a limit accepts every loss of it across the piece, or across the written code where it is declared. Every other loss is accepted at its place. A limit's name follows from its term, and a change to a term carries a map from old names to new. The check fails an entry whose limit no term gives, and asks for attention to one that accepts nothing. A renderer reports a font it cannot draw once at each role that gives it, and its declaration may state which outcome it gives a primitive or a property. The format gains the field by addition alone, and the seam's version stays.**

### 1. A limit is a term of the formats that a plugin takes none of

- **What it is.** A loss is of a *limit* where its plugin's declaration says the plugin takes none of a term the capability's formats define, such as a primitive, a property, a value type, a kind of axis, a kind of picture or a physical size, with one outcome. Each member of a vocabulary the formats close is such a term, as each kind of picture is.
- **Never narrowed.** No term is narrowed by whether a value, or a file's content, is one the plugin can take. So a font family, a font file's outlines and a page larger than a reader holds are no terms, and their losses are of no limit.
- **Wherever its term is present.** A limit is reported wherever its term is present, whatever its value. A property is present at each element that gives it, and a kind of axis at each token the plugin writes whose value an axis of that kind changes. A token the plugin leaves out for its type has the loss of that type alone, and an element it refuses for its primitive the loss of that primitive alone. A whiteboard service that sets the line height of every text takes no line height a piece gives. So its renderer loses the line height of every text, one whose value matches the service's among them.
- **One outcome.** Its plugin approximates the term, draws it as a picture, leaves it out or refuses it, as its declaration states (point 2).
- **Every other loss is no limit,** and is accepted at its place (point 3). Examples are a font a renderer cannot draw, a role with no colour, a picture file missing, and a picture another key shows otherwise.

### 2. The capability names each limit from the declaration, before a plugin runs

- **Found before a run.** The capability compares what a plugin will be handed with what it declares, and reports what it cannot take (DEC-005 point 9). Each loss it so finds, of a term the declaration says the plugin takes none of, names that term as its limit. A loss a plugin reports while it runs names none, and no plugin names one. So a loss found while drawing is never of a limit.
- **The outcome a declaration states.** A renderer's declaration may state, for a primitive or a property it does not draw as given, which of DEC-005 point 9's four outcomes it gives it: it approximates it, draws it as a picture, leaves it out or refuses it. Where it states none, it refuses a primitive and leaves out a property, as today. So a limit may be approximated, as a whiteboard service's line height is, or drawn as a picture.
- **Its name.** A limit is named after its term, as the formats name it. A property is named with its primitive, as `text.line-height` is, so a limit of a text's line height accepts nothing of another primitive. How a name is derived from the terms is part of the format of the files that hold entries: a piece's own file and written code's declaration.
- **A change to a term maps its name.** A change to a term carries a map from each old name to the names of the terms that take its place, or to none where the term is gone, as a change to how trace ids are derived carries one (DEC-005 point 11). The check and each command read an entry written before through it, and keep its value as written (DEC-003 point 2). No name the map holds is given to another term.
- **In the loss report.** A loss of a limit names it, as `limit`, beside its plugin, what it loses, what the plugin did, why, and its key where it has one. Every other loss names none. The check and each command that prints a loss name its limit. The fix they offer for a loss nobody accepted offers an entry by `limit` only where the loss names one.
- **Listed.** The capability's reference lists the limits each plugin's declaration gives it, and how their names are derived.

### 3. An entry accepts what is lost at one place, or one limit across the piece

- **Its form.** An entry under `accept-losses` names the plugin, a reason that is not blank, and one of two things: `what`, the trace id or token path of what is lost, or `limit`, a limit of that plugin. It never names both.
- **By limit.** It accepts every loss of that limit the plugin reports: at every element or token, in each language and each combination of modes, in each format the plugin draws, and in each key. A loss a later change brings is accepted too. In a piece, it accepts a renderer's limit across the piece. In written code's declaration, it accepts a code writer's limit across that written code.
- **By what is lost.** It accepts every loss of the plugin at that trace id or token path, whatever its limit and key, as an entry does today.
- **Where it goes** is unchanged: where the output is declared (DEC-005 point 9).

### 4. The check reports an entry by limit that accepts nothing, by its cause

- **A name no term gives fails.** An entry whose `limit` is derived from no term of the formats, and is held in none of their maps of old names, fails validation, as one whose name is misspelt does. No release causes it, and the project can correct its own file ([visual-communication:DEC-002-files-and-validation] point 7). The fix is to correct the name.
- **Any other entry that accepts nothing asks for attention.** Its name is a term that is no limit of its plugin, or one the formats no longer have. Or its plugin draws or writes nothing of the piece, or nothing loses its limit any more, across the piece or the written code where it is declared. A release whose plugin comes to take a term may cause it, as may a change to the piece. The check names the entry, its plugin, its limit and the cause. It asks the piece's author for an entry in a piece, and the project that keeps the declaration for one in written code. The fix is to remove the entry. It never fails validation.
- **Where each lies.** In a piece, the check computes both with the piece's scenes, and the piece's findings record keeps them (DEC-005 point 13). In written code, the check computes them with the losses it computes for the declaration.
- **Not in a final piece.** The check computes no scene of a final piece, so it judges none of its entries (DEC-002 point 7).

### 5. A renderer reports a font it cannot draw at the role that gives it

- **Once for each role.** A renderer reports each font it cannot draw as one loss at the token path of each typography role that gives it, never as one at each text drawn in it. Where a role gives that font in some keys and not others, the loss lies in each key that gives it, naming that key. Its `why` says how many texts the font falls on.
- **No limit.** A renderer takes some fonts and not others, so a font is no term (point 1). One entry by what is lost accepts the font at that role, across the piece, and no loss of another role.

### 6. The format grows by one field, and the seam's version stays

- **In a piece and in written code.** The entry of `accept-losses` gains `limit`, and needs `what` only where it gives no `limit`. Every file written before still meets the format, and no value accepted before is refused. So the format number stays, and no migration runs (DEC-003 point 3).
- **In the loss report.** A loss gains `limit`, by addition. A producer's record keeps none, since a producer has no limit until its declaration can state a term it takes none of.
- **In a declaration.** A renderer's declaration gains the outcome of point 2, by addition.
- **The seam's version stays.** No plugin reads or writes anything new: the capability reads each outcome stated, and names each limit (DEC-005 point 8). No plugin's version rises, since nothing it draws or writes changes. The PDF renderer moves where it reports a font, not what it draws.

## Rationale

**Why a limit, not a pattern of places.** The losses that recur are the medium's limits, not faults at one place: a whiteboard service sets the line height of every text. A person judges such a limit once for the piece, and one entry by limit says so. A loss a later change brings is of the same limit, so the judgment holds for it too. No pattern of trace ids gathers a limit's losses, since they lie wherever its term is present, and the pattern of every element also accepts every other loss there.

**Why only a limit is accepted across a piece.** Where a limit's term is given, no value avoids its loss, since its plugin takes none of the term. Only giving none avoids it, as a piece with no path does, or a token no size changes. So a later loss of it is one its entry judged, and reporting it again prompts no act. Every other loss falls only where a value its plugin cannot take is given, or where something is at fault, so a later one may be one nobody judged. One who accepts a decorative family the PDF renderer cannot embed has not accepted the body text left out when a later change gives the body a font of the same outlines. One who accepts a picture file missing has not accepted the next. The cost is that such a loss is accepted at each place its plugin reports it, which point 5 keeps small for fonts.

**Why the capability derives the limit, not each plugin.** The capability already finds, from the declaration before a run, every loss that could be a limit. Those a plugin finds while it runs are faults, or depend on a value. A flag each plugin asserted would let the grain at which it names a loss decide whether that loss is a limit: a run's font is none, yet "a font file embedded" could be called one. Since the capability derives it, no plugin can file a loss under a limit. Every limit is known before any run, so the check judges each entry by limit from the declarations and the scenes, and no report after a run is needed, which a run of one language or one format would mislead.

**Why every member of a closed vocabulary is a term, and none is narrowed.** Then the formats fix the grain, and no plugin chooses it. A term narrowed by a value or by a file's content would let a later value bring a loss of it, so an entry by it would accept a loss nobody judged.

**Why a limit is reported wherever its term is present.** Then the capability finds it from the declaration and from where the term is present in what the plugin is handed, never from whether a value is one the plugin can take. Whether a value happens to match what the medium sets asks just that, a condition on a value which point 1 leaves out of every term. Whether an axis changes a token asks nothing of the plugin: it compares the token's values with each other.

**Why a limit fixes one outcome.** A person who accepted a line height approximated has not accepted it left out. What the plugin does instead is part of what they judged.

**Why a declaration may state the outcome.** A whiteboard service approximates a line height rather than leaving it out, and a renderer may draw a primitive as a picture rather than refusing it. Without a way to say so, the capability would report such a limit as left out or refused, and the loss would misstate what the medium does. The words are DEC-005 point 9's four outcomes, the same for every renderer, so each renderer's record states its own in them, and not in a form of its own.

**Why a limit's name follows from its term, and a change maps it.** Entries name a limit in files people wrote, which a migration may move but never rewrite (DEC-003 point 2). A name a plugin chose could change with its wording. One derived from the formats' terms changes only when a term does, and the map then reads each entry written before as its author meant. A change to how trace ids are derived carries such a map for a lasting medium's record (DEC-005 point 11). The seam is still never kept (DEC-005 point 8), so its terms may still change. Only the names derived from them are kept, and those through the map.

**Why a name no term gives fails, and any other entry that accepts nothing asks for attention.** A misspelt name accepts nothing, and no release made it so. The project can correct its own file, so the severity policy fails it (DEC-002 point 7). Every other cause may come from a release, as when a plugin comes to take a term, which would otherwise fail every piece that accepted it, for a change nobody in the project made. Such an entry accepts no loss anyone saw, and would accept unseen whatever of its limit came later, such as a loss a plugin's later version brings back. So someone is expected to act, which the policy marks as attention.

**Why a renderer reports a font at the role that gives it.** A role gives a text its font, so a font a renderer cannot draw falls on every text of that role. Reported at each text, it asks for an entry at each, hundreds in a deck, and a font is no limit to accept them at once. Reported at the role, one entry accepts it across the piece, a text a later change adds in that role among them. A font another role gives is still reported. An entry at a role accepts what the role loses, as one at an element accepts what the element loses.

**What deriving the limit gives up.** A limit only a run could find cannot be one, so its losses are accepted at their places. Nor has a producer any limit until its declaration can state a term it takes none of. A declaration can gain either later, by addition.

**Why the seam's version stays.** It rises only when a plugin must read something differently, so that the engine refuses a plugin that would misread it (DEC-005 point 8). Here the capability reads more of a declaration, and no plugin reads or writes anything new.

### Alternatives considered

- **A flag each plugin asserts,** saying which of the kinds of loss it reports is a limit. Rejected. The grain at which a plugin names a loss would decide whether it is a limit. A loss met while drawing would need a report after each run, which a partial run would mislead and the check would never read. A producer's kept record would need the flag too. The capability already finds from the declaration every loss that could be a limit.
- **A kind named on every loss, a limit or not.** Rejected. Only a limit is accepted by its name, so a kind on every other loss names what no entry uses, ahead of any need for it (COR-007).
- **The field named `kind`.** Rejected. Every declaration already has a `kind`, which says whether its plugin is a renderer, a producer or a code writer. A code writer declares `kinds` and `axis-kinds`, the seam has its kinds of picture, and a loss's words name its plugin's kind. So `plugin: x` beside `kind: y` would read as the plugin's kind.
- **The field named `loss-kind`.** Rejected. It collides with no other field, but names a kind of every loss, which this record does not give.
- **A pattern of trace ids in `what`,** such as one that ends in a wildcard. Rejected. A trace id may hold any character but a space, so a pattern would change what an entry written before accepts, which the format allows only by addition (DEC-003 point 3). Nor does any pattern gather a limit's losses, for the reason above.
- **An entry that names the plugin alone,** accepting everything it loses. Rejected. It accepts losses nobody has seen, the ones a person would mend among them.
- **A term narrowed by a value or a file's content,** such as a font family, or a font file whose outlines a PDF cannot embed. Rejected. Its loss falls only where that value is given, so a later one may be one nobody judged, for the reason above.
- **A limit reported only where its value differs from the medium's.** Rejected. It would ask whether a value is one the plugin can take, and a plugin takes none of a limit's term: a text whose line height matches the service's has it from the service, not from the piece. A kind of axis is no such case, since a token no axis of that kind changes gives none of it.
- **A limit's name that never changes.** Rejected. Its term belongs to formats that may change it, as the seam may (DEC-005 point 8). The map keeps each entry's meaning, and remembers each name it retires.
- **A font reported at each text drawn in it,** as the PDF renderer does today. Rejected, for the reason above.
- **A font's grain, and the words of a declared outcome, left to the whiteboard renderer's record.** Rejected. Both bind every renderer. Each renderer's record would choose its own, and a person would accept a font one way in one medium and another way in the next.
- **An entry by a value, such as a font, across the piece.** Rejected. Point 5 places a font's loss at the role that gives it, so one entry by what is lost serves, with no field each plugin fills.
- **A count of the losses each entry by limit accepts, printed after a run,** so an entry that grows shows. Not taken. Each loss it gains is of the limit its entry judged, and the viewing step's report already names each loss accepted ([visual-communication:DEC-015-viewing-step-and-reviewer] point 3).
- **An entry matched by the words of a loss's `why`.** Rejected. Those words are for people, change with a plugin's wording, and hold values of the piece.
- **A limit accepted for every plugin, naming none.** Rejected. Each medium's loss is judged apart, and one plugin's limit says nothing of another's.
- **A limit accepted in the project's configuration, for every piece.** Rejected. A loss is accepted where the output is declared (DEC-005 point 9), and a project-wide entry would accept losses in pieces whose authors never saw them.
- **An entry that names both a limit and what is lost.** Rejected for now. No loss asks for it, and the format can gain it later by addition, since it accepts no such entry today.
- **An entry by limit that accepts nothing, left unreported,** as an entry by what is lost is. Rejected, for the reason above.
- **One finding that asks for attention, whatever the cause.** Rejected. A misspelt name is the project's to correct, and no release caused it, so the severity policy fails it (DEC-002 point 7). Its fix is to correct the name, not to remove the entry.
- **Every such entry failing validation, or stated as a fact.** Rejected. The first fails pieces for a change nobody in the project made, and the second expects no act where one is expected (DEC-002 point 7).
- **The seam's version raised.** Rejected, for the reason above.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). Each refines its record in place.
  - **DEC-005 point 9:**
    - **"Each declares what it supports":** after its sentence "A renderer declares, for each primitive and property, whether it draws it, updates it in place, recreates it, or reads it back." comes: "For one it does not draw as given, it may also declare which of the four outcomes below it gives it. Where it declares none, it refuses a primitive and leaves out a property (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] point 2)."
    - **"One form of loss report":** after its sentence "It approximated it, drew it as a picture, left it out, or refused it." comes: "A loss the capability finds before a run, of a term the plugin's declaration says it takes none of, also names that term as its *limit* (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] points 1 and 2)."
    - **"A known loss may be accepted"** comes to read: "**A known loss may be accepted** where the output is declared: in a piece for a renderer's or a producer's, and in written code's declaration for a code writer's. An entry accepts what is lost at one trace id or token path, or every loss of one limit across the piece or the written code (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] point 3). The check then stops repeating it."
  - **DEC-005 point 10** gains a last bullet: "**A font a renderer cannot draw,** in any profile, is one loss at the token path of each typography role that gives it, never one at each text drawn in it. Where a role gives that font in some keys and not others, the loss lies in each key that gives it, naming that key, and its why says how many texts it falls on (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] point 5)."
  - **DEC-005 point 14:**
    - **"Fails validation"** gains a last item: "an entry under `accept-losses` whose limit no term of the formats gives and no map of their old names holds (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] point 4)".
    - **"Asks for attention, never failing":** "an overflow measured from a table or by an estimate, and a loss nobody has accepted." comes to read: "an overflow measured from a table or by an estimate, a loss nobody has accepted, and an entry by a limit that accepts nothing, its name being a term or one the formats no longer have (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] point 4)."
  - **DEC-021 point 8, "The CSS writer":** "and reports as a loss each token a size changes." comes to read: "and reports as a loss each token it writes that a size changes, a loss of the limit of the kind of axis it does not spell. A token it leaves out for its type has the loss of that type alone (refinement per [visual-communication:DEC-060-losses-accepted-by-limit] point 1)."
- **Read against this record, and left as they stand:**
  - DEC-001 point 2, since a renderer still reports what it lost, and a limit adds to the report;
  - DEC-002 point 7, whose policy point 4's two findings follow;
  - DEC-003 points 2 and 3, since the format grows by addition alone, and an entry written before is read through a map of names, its value kept as written;
  - DEC-004 point 9, since a font missing from the project's files still refuses the render, and point 5 places only a font a renderer cannot draw;
  - DEC-005 point 8, since the scene itself is still never kept: a change of the seam may still rename a term, and only the name of a limit an entry derives from it is kept, read through the map of point 2;
  - DEC-005 point 11, whose map from old trace ids to new is the one point 2 follows for a limit's name;
  - DEC-005 point 13, since the entries already count toward the findings record's key, so a changed entry is judged at once, while a plugin that comes to take a term reaches a piece at a render a person runs, as a new engine does;
  - DEC-015 point 3, since the viewing step's report keeps each loss as it is reported, its limit with it, and a font's loss at its role;
  - DEC-016 points 1 and 2, since the losses a piece accepts, by what or by limit, still pass from what an export reads, and still count toward the findings key;
  - DEC-023 point 8, since an entry by limit matches whatever key, as an entry by what is lost does;
  - DEC-033 point 9, since a format read whole reports no loss of the reader's side, so has no limit of it;
  - DEC-034 point 3, since a top's physical size that a renderer whose format has a page does not map is a limit, its declaration saying so.
- **An entry by what is lost that accepts nothing** stays unreported. It reaches one element or token, so it can accept unseen only a later loss at that place.
- **Each loss nobody accepted** is still reported at its place, with its limit where it has one, until an entry accepts it.
- **A role with no colour** is still reported at each element drawn in it (DEC-023 point 8). Reporting it once at the role's token path, as point 5 reports a font, is left to a follow-up of its own, [project-kit#3281](https://github.com/aleskalfas/project-kit/issues/3281).
- **The record of the signed-out whiteboard renderer** ([project-kit#3278](https://github.com/aleskalfas/project-kit/issues/3278)) decides which limits that renderer has, such as a text's line height, and states the outcome of each in point 2's words. It reports a font the service lacks as point 5 says. This record decides how its losses are accepted.
- **The Task that builds it,** under [project-kit#2569](https://github.com/aleskalfas/project-kit/issues/2569), filed once this record is accepted: each loss the capability finds before a run names its limit where it has one; a code writer's loss at a token of two kinds of axis it does not spell becomes one for each, so each loss names one limit; a renderer's declaration may state an outcome; the PDF renderer reports a font it cannot embed at each role that gives it; the entry's `limit` in the form a piece and written code share; the matching in the check and in each command that prints a loss, with their fix texts; and the findings of point 4. The capability's pages change with it: the loss report and accepting a loss, the reference's list of each plugin's limits and how their names are derived, the checks, the files, and the visual-author skill's build loop.
- **No migration.** Nothing a project holds changes (DEC-003 point 3; COR-010).
