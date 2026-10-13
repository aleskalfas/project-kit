---
id: COR-058
title: A decision record's points keep their ids for good
status: accepted
date: 2026-10-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A decision record often decides several things at once, and its Decision numbers them as points. Other records, rules, documentation and agents' instructions cite a point by its number, such as "point 5". A project that receives a record by sync (COR-001) cites its points the same way, and is not told when a number it cites moves.

A point's number is not permanent. A refinement puts a new point where it belongs among the others (the decision-record specification, "Refining an accepted record"). Records often write their points as a Markdown numbered list, and a list shows numbers counted from its first item. So an inserted point moves every later number on screen, and the source is renumbered to match. Each citation of a moved point then names another point, and nothing says so.

Records also write their points in other forms. A point may be a paragraph that opens with a bold number or a bold label, such as `D1`, or it may be a heading. A bold number or label ends nothing, so nothing can tell where that point's text stops and the next one's begins.

Rules already have the guarantee that points lack. A rule's id is never renumbered and never reused, and a retired rule stays in place with its successor (COR-051 points 3 and 4). Anything that names a point, a citation in prose or a reference kept as data, needs the same of the point's number.

Record numbers meet a related problem. Two branches that each add a record can take one number, and nothing finds the clash until both have merged.

## Decision

**A point of a record's Decision is a heading that opens with its id, and the id names that point permanently. A new point goes where it belongs and takes the next unused number. No point is ever renumbered. A retired point keeps its id in the record's front matter, with the points that took its text, and a one-line stub stays where it was. Validation holds each stub to its entry, and a change's numbering, of points and of records, is checked against its base.**

The points that follow:

- **Points 1 and 2** say what a point is, and which numbered lists hold points in a record that has no point headings yet.
- **Points 3 to 7** say how points are written, retired and validated, in a record whose points are headings.
- **Point 8** checks a change: its points, and the record numbers it takes.
- **Point 9** covers a record whose points are a list, until someone turns them into headings, which is *converting* the record.
- **Point 10** says what this record governs.

### 1. A point is a heading with its id and title

- **The form:** `### 5. Title` for a numbered point, and `### D1 — Title` for a labelled one. The point's text follows its heading.
- **The id** is the token the heading opens with:
  - **a number,** then a full stop and a space, as its list item had
  - **a label,** letters then a number, then a space, an em dash and a space, as a rule's heading has
- **Labels stay.** A record that labels its points keeps its labels, since it is cited by them.
- **The title** names the point in a few words. The title `Retired` marks a stub (point 4), so no live point takes it.
- **The level:** a record's points all sit at one level. That is one below the Decision's heading, or one below the group headings that gather them, as in `#### 11. Title`. It is the level of the Decision's first heading that opens with an id in this form.
- **One id space:** a record's ids are unique across all its groups.
- **The section:** a point's text runs from its heading to the next heading of the same or a higher level.
- **What is no point:**
  - a heading outside the Decision, even one that opens with a number
  - a heading at another level than the points', whatever it opens with. It is not warned of, since a point may hold numbered headings of its own.
  - a heading with no id, which is a sub-section of the Decision
  - a line inside fenced code, which is no heading at all
- **A misspelt point is warned of** (point 7): a heading in the Decision that opens with a number or a label in another form, such as `### 16 - Title` or `### 5.1 Title`.

### 2. Which numbered lists hold a record's points

A record not yet converted writes its points in *list form*: as numbered items, or as paragraphs that open with a bold number or a bold label. Converting it turns each such point into a point heading (point 9).

- **Items that hold points:** a numbered list at the Decision's top level, or one numbering that runs across the Decision's group headings.
- **Items that hold no points:** a numbered list inside a point or inside another sub-section. Its numbers are steps or an order. It stays a list, and renumbers when an item is inserted. Nothing cites its items as points.
- **Once a record has point headings,** every numbered list in it is a list, never points.
- **Whoever converts a record confirms the reading,** since which lists hold points follows from how the record is cited.

### 3. A new point takes the next unused number, and no point is renumbered

- **A new point goes where it belongs** among the others. It takes the next unused number: one past the highest the record holds, retired ids included.
- **A label carries its number.** A record labelled up to D5 goes on with D6. Numbers and each series of labels count apart.
- **Numbers may then read out of order,** such as 4, 16, 5. The order on the page is the order to read in, and the number is the name.
- **No point is renumbered, and no id is reused.** Points may be reordered, since a point keeps its id wherever it sits.
- **Amending a point** edits it in place, under its id.

### 4. A retired point leaves an entry and a stub

A point is retired when no point continues its claim.

- **A dropped point** is retired with no successor.
- **A split point:** where one part keeps the claim, that part keeps the id, and each other part is a new point with the next unused number. Where no part continues the claim, the id is retired, and the points that took its text are its successors.
- **A merge:** the point that keeps the claim keeps its id. The other is retired, with that point as its successor.

**The entry, for tools.** `retired-points` maps each retired id to its successors:

```yaml
retired-points:
  "6": ["7", "16"]
  "9": []
```

- **Its place:** the top level of the record's front matter, outside the methodology's container. It is the record's own field, as `status` is, just as an artefact's own fields sit outside that container (COR-053 point 10).
- **Its layout:** a block mapping, one retired id to a line, in the order of the ids. So two branches that retire different points rarely meet on one line.
- **Successors are not followed further.** A successor retired later gets a line of its own. The earlier line and its stub stay as they are.

**The stub, for readers.** A heading with the retired id at the points' level and the title `Retired`, then one sentence:

```markdown
### 6. Retired
Its content is in points 7 and 16.
```

- **The sentence** is written from the entry, in one form:
  - one successor: "Its content is in point 7."
  - several, in the entry's order, with commas and an "and" before the last: "Its content is in points 7 and 16." or "Its content is in points 7, 12 and 16."
  - none: "Its content is in no other point."
- **It stays where the point was,** as a retired rule stays in its rule set (COR-051 point 4).
- **It says where the content went, and nothing else.** It holds no date, no issue and no reason.
- **A stub is no point.** It holds no point's text.

### 5. Successors are points of the same record

- **Every successor is an id the record holds or retires.** No retired id is its own successor.
- **A successor is a live point when its entry is written.** A later retirement of that successor changes no entry that names it.
- **A point that another record overturns is not retired.** It stays as it stood, and the record's top line reads "Partially superseded by …", the form the decision-record specification gives a partial supersession.

### 6. A live id is defined by its heading, and a retired id in data

- **A live point's id** is the one its heading shows, and is recorded nowhere else in the record.
- **A retired id** is defined in `retired-points`. Its stub's heading and sentence follow the entry.
- **The list is the source.** A tool reads retired ids and their successors from `retired-points` alone. Validation holds each stub to its entry, both ways, as a rule's data is joined with its section (COR-051 point 2).
- **An exception to ids in data.** The rule-set record rejects markers in prose parsed by pattern (COR-051, "Alternatives considered"). A point's heading is read that way, under guards:
  - a heading ends its section
  - validation warns of a misspelt one (point 7)
  - where a project runs the numbering check, a change that adds one fails it (point 8)
- **What the guards miss:** a point written with no id at all. Its heading is a sub-section of the Decision, and nothing reports it.

### 7. What validation checks

Validation checks records in the working tree alone (COR-055 point 2). It skips a record the project receives by sync, which is checked where it is authored, and a superseded record, whose body stays as it stood.

- **It fails on:**
  - a malformed `retired-points`
  - a retired id with no stub, or a stub whose id is not retired
  - a stub whose sentence differs from the one its entry gives
  - a live point whose heading uses a retired id
  - a successor that the record neither holds nor retires, or a retired id named as its own successor
- **It warns of, and never fails on:**
  - a duplicate id
  - a gap in the ids, counting retired ones
  - a heading in the Decision that opens with a number or a label in a form that point 1 refuses
- **Validation adds only the new field's shape.** It does not close a record's front matter to a project's own fields.

### 8. A change's numbering is checked against its base

A command of its own checks a change's records against its base, since validation takes no base (COR-055 point 2).

- **What it compares:**
  - **The change's own edits:** from where the change's branch left the default branch, its *branch point*, to the working tree.
  - **Ids another change took:** what the default branch holds now, against where the change's branch left it.
  - **Both states** come from the backbone's one resolution of the default branch, or from a base named for one run (COR-054).
- **It binds where a project runs it on its changes.** It runs whether or not anything names a record's points from data, since citations in prose rest on the numbers too.
- **It reads point headings only,** except in a record the change converts. There it compares the head's points with the list form at the branch point (point 2). Any other record in list form meets only the warning below.
- **It skips a record the project receives by sync,** since that record is refined where it is authored.
- **For each record the change touches, it fails on:**
  - an id the branch point holds or retires that the head neither holds nor retires: a point dropped without being retired
  - a new id that is not past every id of its series that the branch point holds or retires
  - a point whose text, read without its id, sits at the head only under another id. That is a renumbering, or a retirement whose successor kept the claim.
  - a duplicate id, or a heading in a refused form, that the change added
  - a retired id without its stub, or a stub without its entry, at the head
  - a new entry in `retired-points` whose successor is not a live point at the head
  - in a record the change converts, a point whose id differs from the number its numbered item showed at the branch point
  - a point id that another change took on the default branch, in the same record, since the change's branch left it
  - a record id that another change took on the default branch since the change's branch left it
- **It warns of:**
  - a point's title at the branch point found at the head under another id, with its text changed. That is likely a renumbering with an edit, which the command cannot be sure of.
  - in a record the change converts, a point whose id differs from the bold number or bold label that opened it at the branch point
  - a point added to a record in list form, or a new record in list form
- **Two changes that take one number:** the first to land keeps it. The other moves its point to the next unused number.

### 9. A record in list form keeps working until it is converted

- **A record in list form keeps working.** Its points are cited by number as before. A new point goes where it belongs among the others, and in a numbered list every later number moves.
- **Its numbers are not permanent until then.** Nothing fails on them, so nothing that needs a permanent id can rely on them. The numbering check warns of a point added to such a record (point 8). Converting the record first keeps every number.
- **Converting keeps every point's words, and takes the number a reader sees as its id.**
  - A point's bold lead, without its closing full stop, becomes its title. A point without one is given a title by whoever converts it.
  - Its text leaves the list's indent.
  - Text after the last point would fall into that point's section (point 1). Whoever converts gives it a heading of its own, or a place in the Decision's lead.
- **When and how a project converts its own records** is not decided here.
- **Two kinds of record are never converted in a project:** a record it receives by sync, which is converted where it is authored, and a superseded record, whose body stays as it stood.

### 10. What this record governs

- **Decision records' points, and the record numbers a change takes** (point 8). Rules in rule sets have permanent ids already (COR-051 point 3). The methodology's operational rules for agents, and other documents that number their parts, keep their own numbering.
- **Whether and how an anchor names one point** is the anchors-and-friction record's to decide (COR-050), not this record's.

## Rationale

**Why permanent ids.** A point is cited by its number in other records, in rules, in documentation, and in projects that receive the record by sync. A renumbering misleads every such citation, and nothing reports it. A permanent id keeps a citation on the same point for as long as the record stands. A rule's id already works so (COR-051 point 3), and a point is cited as often as a rule.

**Why headings.**
- A heading shows the number written in it. A list counts from its first item, so an inserted point would show a number it does not have.
- A heading ends the section before it. A bold number or label does not, so nothing could cut one point's text from the next.
- A point's section is headed by its id, as a collection entry's section is (COR-050 point 1). Point 1 of this record says where it ends.
- The heading form is already in use, in both forms.

**Why the next unused number, and placement where it belongs.** A record reads in the order of its meaning, not of its refinements. Points added at the end would turn the record into a change log, which the decision-record specification forbids. The next unused number keeps the place and the name apart. The place serves the reader, and the number serves the citation.

**Why both an entry and a stub.** The entry is data, so a tool reads a retired id and its successors without parsing prose. The stub is for the reader. A record that reads 1, 2, 3, 4, 16, 5, 7 with no 6 looks like a mistake, and the stub says where 6 went. Each alone fails one of the two readers. The list is the source, and validation fails on any difference, so the two never disagree for long.

**Why the stub says nothing else.** A date, an issue or a reason would narrate a revision, which the decision-record specification forbids. The stub is data a reader sees, as the entry is data a tool reads. Its sentence has one form, so validation can hold it to the entry word for word.

**Why `retired-points` sits outside the methodology's container.** A retired point is a fact about the record itself, as its status is. In an artefact, the container holds what the methodology keeps, and the artefact's own fields sit outside it (COR-053 point 10). A record's own fields sit outside it the same way. One retired id to a line keeps two branches that retire different points apart, unless their lines sit side by side.

**Why successors stay in the record.** A successor in another record would mean that record overturns the point. That is a partial supersession, which already has its form. Keeping successors in the record keeps the entry checkable from the record alone. A successor is live when named, so a reader who follows a stub finds a point and not another stub.

**Why a live id is read from its heading.** The rule-set record keeps ids in data, since a misspelt marker in prose becomes a missed rule, silently (COR-051, "Rationale"). Points as data beside their headings would repeat every heading in a list. The heading is guarded instead, by its section's end, a warning and the numbering check. The check guards only where a project runs it. Elsewhere the warning is all there is. A heading written with no id at all is a sub-section, which a record may hold, so that slip is not caught. A retired id has no live heading to carry it, so it stays in data.

**Why one id space and one level.** A citation names a point by the record and the id alone. Two points with one id in different groups, or a point at another level, would make that citation ambiguous.

**Why a list inside a sub-section stays a list.** Its numbers are an order, such as the steps of a procedure. Inserting a step rightly moves the steps after it. Nothing cites them as points, so renumbering them misleads nobody.

**Why validation fails on the new field and the stubs, and warns of the rest.** Each failure follows from the new field or from a stub's heading. One of them can meet a record written before this record: a point titled `Retired` reads as a stub, and fails until it takes another title. That title stays reserved, since a stub must be told from a point by its heading alone. A duplicate id, a gap or a refused heading form may sit in a record a project already holds. A warning fails nothing it has, and the numbering check fails each new one that a change adds.

**Why validation and the numbering check skip a record received by sync.** The project cannot correct that record in its own files, and validation keeps out what a project cannot correct (COR-055 point 1). The record is checked where it is authored, so a fault never reaches the project. A superseded record is skipped by validation for the same reason: its body stays as it stood, so no finding on it could be mended.

**Why numbering is a command of its own.** It compares a change with its base, and validation answers about state alone (COR-055 point 2). The friction change check could have held these findings. It is not used, since it only reports in warning mode, and finds nothing where nothing is anchored (COR-050 points 12 and 15). Numbering binds records that nothing anchors.

**Why the command compares from where the branch left the default branch.** A branch that falls behind holds none of the points the default branch gained meanwhile. Compared with the default branch as it stands, each of those would read as a point the change dropped. The default branch as it stands is read only for the ids another change took. Two branches that take one number each pass alone, and would meet only after the merge. Where the check runs on the change merged into the default branch, the default branch is already in the head. There the rule on a duplicate that the change added is the gate.

**Why the check also catches a record number.** A command that numbers a new record allocates past the default branch (COR-054 point 3). Two branches that each add a record before either lands still take one number. The numbering check already compares the records a change touches with the default branch, so it finds that clash too, before the second change lands. The rule is about records, not points, but it needs the same comparison, so it lives in the same check.

**Why the check reads point headings only.** A record in list form has no permanent ids to protect. Inserting a point into a numbered list moves the numbers after it, as the specification allows until the record converts. Failing that would fail ordinary work on every record not yet converted. A warning says the record would keep its numbers if it converted first.

**Why a conversion is checked.** A conversion turns the numbers a reader sees into permanent ids. A wrong number there would mislead every citation. So the check compares each new heading with the item it came from. A numbered list's numbers are read as Markdown shows them, so a difference fails. A bold number or label is read by pattern, so a difference is warned of.

**Why a record and not only the specification.** The decision-record specification states the shape of every record, and stays the place a reader learns it. Which form a point takes, and how a retired point is kept, are choices among viable alternatives, with reasons and costs. Such choices are recorded as decisions, and the record that owns a check decides its findings' severities (COR-055 point 4). The specification follows this record.

### Alternatives considered

- **The list number, never renumbered.** Rejected. A list counts from its first item, so an inserted point would show a number it does not have.
- **New points at the end of the record.** Rejected. The record would read in the order of its refinements, the change log that the decision-record specification forbids.
- **A letter after the number, as legislation inserts 4A.** Not taken. It reads in order, but needs an order of letters, and gives a point nothing that the next number does not.
- **A bold label.** Rejected. It shows as written, but ends no section, and a misspelt label would silently be no point.
- **A hidden marker, such as an HTML comment.** Rejected. The reader who cites the point cannot see it, and it is a marker in prose.
- **Points as entries of a collection, in the rule-set shape.** Rejected. Each point would be an artefact, and a synced tree is never one of a project's places (COR-050 point 14). A record a project receives by sync could not hold its points that way.
- **Points as data beside their headings.** Not taken. The warning on a misspelt heading and the numbering check catch a misspelt point, without a list that repeats every heading.
- **One heading form for both, `### 5 — Title`.** Not taken. It matches a rule's heading, but changes every record that already shows its numbers as `### 5. Title`.
- **A point named by its position and an expected text.** Rejected. It makes a renumbering loud for that one reference. Every citation in prose would still move silently.
- **The retired-points list alone.** Not taken. A tool finds the id, but a reader meets a missing number with no word.
- **The stub alone.** Rejected. A tool would read the id and its successors from prose.
- **Neither a list nor a stub.** Rejected. A dropped point's number would stay unused by practice alone.
- **Numbering checked by the friction change check.** Rejected. It only reports in warning mode, and finds nothing where nothing is anchored. A comparison with a base is a command of its own anyway.

## Implications

- **The decision-record specification follows:**
  - its refining rule, in two branches. In a record whose points are headings, a new point goes where it belongs and takes the next unused number. No point is ever renumbered. In a record in list form, a new point goes where it belongs, as point 9 says, until the record converts.
  - a new step: a dropped or split point leaves its id to `retired-points`, with its successors, and a stub where it was
  - its rule against residue, which reads the entry and the stub as data, not narration
  - its schema, which shows points as headings, the optional `retired-points` and a stub for each retired point, with a numbered list allowed inside a sub-section
- **The record template** shows points as headings.
- **Validation's check of decision records** gains the findings of point 7.
- **The numbering check** is a new command. The CLI reference names it, and a project runs it beside its other checks of a change.
- **Records that the backbone or a component ships** convert once, word for word, where they are authored. Every point keeps its number, so no citation changes.
- **Nothing that needs a permanent id** can rely on a list-form record's numbers (point 9). An anchor on one point, should the anchors-and-friction record allow one, would be such a thing.
- **The rule-set record's rejected "markers in the prose, parsed by pattern"** names this record's point headings as an exception.
- **Nothing migrates.** The one finding a record written before this one can meet is a point titled `Retired`, which a new title clears.
- **A project's own records** keep their list form, and keep working, until the project converts them.
