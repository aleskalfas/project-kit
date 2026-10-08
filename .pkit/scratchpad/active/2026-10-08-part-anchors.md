---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# Part anchors — an anchor can point at one part of a document

A design for #1387. It lets an anchor name one part of a document, so a change to another part asks nothing of the dependant.

- **Raised by:** the document-versioning design's question 4 (#1383, PR #1384). The maintainer chose on 8 October to anchor to parts, knowing it reopens settled positions.
- **Read from main at `78837af9`:** the records, the code and the counts below. The history counts use the versioning note's window, 27 September to `30cfb15a`.
- **Citations:** records and rules by permanent id and point. Code by file and line at `78837af9`, since code has no permanent ids.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers the four questions, one at a time. The issues in "Slicing" are filed on the maintainer's go.

## The question

How does an anchor name one part of a document, and what must stay true of the part's name for friction to compare it?

## In short

A part is a section headed by its id, the shape a collection entry already has. A record's points get permanent ids, written as headings. A page's sections are named by their headings.

- **Records:** each point becomes a heading, `### 5 — Truth-chain order`. The number it has today is its id for good.
  - **A new point** goes where it belongs and takes the next unused number.
  - **A dropped or split point** keeps its number in the record's `retired-points`, with the points that carry its text on.
- **Anchors:** `record: living-docs:DEC-001#3` names a point, and `artefact: .pkit/cli/README.md#authoring-commands` names a page's section. A rule is already an entry, named by its id.
- **Friction:** compares only the part, with one reading of where a part lies, shared with collection entries.
  - **A point also stands on its record's front matter, preamble and decision lead,** since it binds only as part of its record.
- **The five cases:** a changed part flags its dependants, and a change elsewhere flags none. A move holds. A removed part is a dead anchor. A split flags, and says where the text went.
- **What it saves:** the two costly dependants were asked 110 times in the window. Part anchors would have asked them 10 times.
- **What it costs:** 95 records' points become headings once, word for word. The 32 artefacts anchored to them answer once. No citation changes, since each point keeps its number.
- **No migration is due:** nothing an adopter has stops working. An adopter's own records keep the list form until the adopter converts them.
- **The trade:** a dependant that names too few parts misses a change, as a path anchor's glob can today.
- **It reopens:** COR-050's whole-file anchors and its rejection of section anchors, and the decisions README's rules on refining and on the schema. ADR-057 and living-docs DEC-001 are touched and kept.

## Today

An anchor stands on a whole file or a whole artefact, except a collection entry, which is already a part. Records' points are cited by number everywhere, and a refinement may renumber them.

### What an anchor stands on (COR-050)

- **A record anchor:** the record's whole file. Any change to it asks every dependant (COR-050 point 5).
  - **The change check** asks only whether the record's file is in the diff (`src/project_kit/friction_check.py:911-914`).
  - **The whole-repository check and the debt walk** compare the file's object between versions (`src/project_kit/friction_repository.py:917-931`).
- **An artefact anchor:** the artefact's content, its body and its own fields, never its container (COR-050 point 5).
- **A collection entry is already a part:** its data entry with the body section headed by its id (COR-050 point 1). A rule is such an entry (COR-051 point 2).
  - **One reading of the section:** the first heading that opens with the id, to the next heading of the same or a higher level, fenced code skipped (`src/project_kit/friction_discovery.py:2470-2548`).
  - **Its span:** `pkit friction artefacts --json` gives each entry's lines, from the same reading (#1361).
- **A registered kind:** the files its resolver names. A capability gets precision by keeping one value in one file (ADR-057, "Why a resolver answers files").
- **Rejected in COR-050:** "anchors per section, via markers inside the prose", and "anchors on every statement inside a document".

### How records number their points

Records write their points in four forms, and a refinement renumbers them on insertion.

- **The rule:** "A new point goes where it belongs among the others, not at the end of the record" (the decisions README, "Refining an accepted record").
  - **Why it renumbers:** a Markdown list shows numbers counted from its first item. An inserted item moves every later number on screen, so the source is renumbered to match.
- **The four forms, 555 points in 97 records:**
  - **A list item with a bold lead,** `5. **Truth-chain order.**`: 76 records, 445 points.
  - **A bold number,** `**1. Intra-file ownership partition.**` in ADR-002: 13 records, 71 points.
  - **A bold label,** `**P7 — …**` in COR-033 and `**D1 — …**` in PRJ-002: 6 records, 29 points.
  - **A heading with a label,** `### D1 — …` in [project-management:DEC-032-conditional-reviewer-requirements] and [project-management:DEC-042-label-contributions]: 2 records, 10 points.
- **The rest:** 94 records have no numbered points. Their decisions are prose, or sections under sub-headings.
- **Where they live:** 50 of the 97 are synced to adopters, as core or capability records. 47 are project-kit's own PRJ and ADR records.
- **Citations:** about 2,900 places cite a record's point by its number, in about 500 files. COR-050 alone is cited by point 676 times.
  - **The count is approximate:** it matches a pattern, "COR-050 point 5" and its variants.
  - **Labels are cited both ways:** COR-033's points are cited by label, as "P7", 66 times, and as "point 7" 72 times.
- **Renumbering in history:** 3 events moved 10 points, across 529 versions of 191 records.
  - **COR-050, on 28 September (205f644a):** a refinement moved five points down, point 10 to 14 among them. COR-050 had 7 citations by point then.
  - **[project-management:DEC-028-agent-as-approver-paths] on 1 October,** and [project-management:DEC-029-project-manager-agent-shape] on 3 October.
- **The core rules were renumbered too,** on 28 September (c5cfd787). A new rule 16 moved rules 16 to 18 down. The change rewrote the two citations of the cross-repository rule from 18 to 19.

### Other permanent ids

- **Rule ids (COR-051 point 3):** never renumbered, never reused.
  - **A new rule takes the next number and goes where it belongs.** WRITE shows it: RS-WRITE-014 sits before RS-WRITE-013.
  - **A retired rule stays in place** with its id, its status and its successor (COR-051 point 4).
- **Analysis ids:** a use case takes the next free number, never used again (the software-analysis README, "Ids").
  - **Two branches that take one number** meet at validation's duplicate-id check on the merged tree, and the first to land keeps it.
- **Position with a text guard:** [project-management:DEC-038-criterion-addressing] names an acceptance criterion by its index and an optional expected text. It rejected stable ids as not worth a migration of every issue body.

## Naming a part for good

A record's point becomes a section headed by its id and its title, as a rule is. The id is the number or label the point has today.

### The form

- **A point:** `### 5 — Truth-chain order`, then the point's text. A point under a group heading, as in COR-050, takes the next level, `####`.
- **The id:** the token the heading opens with.
  - **A number,** as most records have: `5`.
  - **A letter and a number,** where a record labels its points: `D1` in PRJ-002, `P7` in COR-033. Those records keep their labels, since they are cited by them.
- **The title:** the point's bold lead, word for word, without its closing full stop. Every point in the 97 records has one.
- **The text:** the point's text, word for word, taken out of the list's indent.
- **Where points are found:** in the Decision section only. A heading there whose title opens with an id and ` — ` is a point.
- **Why headings:**
  - **They render as written.** A list counts from its first item, so an inserted point would show a number it does not have.
  - **They are what friction already reads.** A point is found as an entry's section is found, by the one reading (ADR-057 point 2).
  - **Two records use them already:** [project-management:DEC-032-conditional-reviewer-requirements] and [project-management:DEC-042-label-contributions].
- **Note:** hosts give each heading a link, so a citation can link to the point.

### Writing points

- **A new point** goes where it belongs and takes the next unused number. That is one past the highest id the record holds, retired ids included.
  - **So numbers can read 4, 16, 5,** as WRITE's rules read 011, 014, 013.
- **No point is renumbered.** Points may be reordered, since a point keeps its id wherever it sits.
- **A dropped point** leaves its section, and its id joins `retired-points` in the record's front matter.
- **A split point:**
  - **Where one part keeps the claim,** that part keeps the id, and the rest takes the next unused number.
  - **Where no part continues the claim,** the id is retired, with its successors: `retired-points: {"6": ["7", "16"]}`.
- **A merge:** the point that keeps the claim keeps its id. The other is retired, with that point as its successor.
- **A successor in another record** is written as a part anchor's value, such as `COR-060#2`.
- **What validation checks,** from the working tree alone (COR-055 point 2):
  - **Fails:** an id two headings share, a heading that uses a retired id, and a successor that names no point.
  - **Reports:** a gap in the ids, counting retired ones. A gap is a point dropped without being retired, or an older record's own numbering.
- **What the change check fails:** a point the change removed without retiring it, and a point the change renumbered. The second is a base point's text under another id at the head.
  - **Why there:** both compare a change with its base, which validation never does (COR-055 point 2). A removed point is the record-side twin of a dead anchor.
- **Two branches that take one number** meet as two headings with one id. Validation fails the merged tree, and the first to land keeps the number, as for analysis ids.

### What replaces the decisions README's rule

The refining rule keeps placement where a point belongs, and gains permanence.

- **Step 1 reads:** "A new point goes where it belongs among the others and takes the next unused number. No point is ever renumbered."
- **A new step:** a dropped or split point leaves its number to the record's `retired-points`, with the points that carry its text on.
- **Step 3, no residue:** the retired list is data a tool reads, with no date, no issue and no narration. It stands as a retired rule's successor does (COR-051 point 4).
- **The schema:** "complex decisions may use a numbered list" becomes points as headings, `### N — Title`, and the optional `retired-points`.

### Other documents with numbered parts

- **Rule sets:** already permanent. A rule is an entry, named by its id.
- **The operational rules files:** `.pkit/rules/core.md` and `.pkit/rules/project.md` number their rules, cited as "core rule 20". They were renumbered once (c5cfd787).
  - **They take the same rule and the same form.**
  - **Nothing anchors their parts:** they are neither a record nor an artefact, so no anchor names them except a path.
- **Analysis artefacts:** an entry is a part already. A use case's numbered steps are no parts in this design.

## What a part anchor looks like

A part anchor is an anchor's value, then `#`, then the part's id. Only the record and artefact kinds take a part.

```yaml
pkit:
  friction:
    anchors:
      record:
        - COR-050                 # the whole record, as today
        - living-docs:DEC-001#3   # point 3 of a capability's record
        - PRJ-002#D1              # a labelled point
      artefact:
        - .pkit/cli/README.md#command-line-interface  # the page's lead, named by its title
        - .pkit/cli/README.md#authoring-commands      # a section of the page
        - RS-LDOC-003                                  # a rule: an entry, already a part
```

- **A record's point:** the record's id, `#`, the point's id. A capability's record keeps its prefix, `living-docs:DEC-001#3`.
- **A page's section:** the document's path, `#`, the heading's slug.
  - **The slug:** the heading's text in lower case, punctuation dropped, spaces made hyphens, as hosts name a heading's link.
  - **The section** runs to the next heading of the same or a higher level, as an entry's does.
  - **The title's slug names the lead,** the text before the first sub-heading. The whole document is already named by its path alone.
  - **Two headings with one slug** make an anchor naming it ambiguous. That is an error, fixed by renaming one heading.
- **A rule, or another collection entry:** named by its id, as today. A collection file's parts are its entries, so a slug on one is refused, naming the entry to use.
- **Not a path anchor:** code has no parts with ids, and a glob of parts means nothing.
- **Not a registered kind:** a resolver still answers files (ADR-057 point 3).
- **Why `#`:** COR-051 point 3 names an extension point `RS-CMN-003#cause-location`, so that `#` never clashes with a namespace's colon. A part reads the same way, a named thing inside another.
- **Why a bare number:** the anchor names what the heading shows and what citations say, "point 3". A prefix such as `P3` would make the two differ.

### Why a page's section has no permanent id

A page's section is named by its heading, which is not permanent. A rename is caught, never silent.

- **Records are cited by point across projects.** A renumbering misleads every citation silently. A page's sections are seldom cited, and their headings are their only structure.
- **A permanent id on a section would be a marker in the prose,** the second convention COR-050 rejected.
- **A renamed heading fails loudly:** the anchor is dead, and the change that renamed it owns the finding (COR-050 point 12).
- **How often:** 5 of the 68 changes to area READMEs in the window renamed a heading. All 5 were command headings in the CLI README.

## The five cases

Both checks read each case the same way, since both find a part with one reading and its id never moves.

1. **The part's text changes:** its dependants are flagged.
   - **A point's text** is its heading and its section. The heading's level counts too, as it does for an entry.
   - **A point also stands on its record's front matter, preamble and decision lead.** A change to any of them flags the dependants of every point (below).
   - **The explanation** shows the part's diff alone, so the answerer reads only what changed under them.
2. **Something else changes:** nobody is flagged who anchors only other parts.
   - **In a record:** Context, Rationale and Implications sit in no point, and neither does a group heading in the Decision.
   - **A whole-record anchor** is flagged by any change, as today.
3. **The part moves:** the anchor holds, and nobody is flagged.
   - **A point keeps its id** wherever it sits in its record, and a section keeps its slug.
   - **A record renamed** is followed, as today (COR-050 point 5).
   - **A point renumbered anyway** fails the change check, whose fix is to put the id back.
   - **A heading renamed** is no move. The section is gone under its old slug, so case 4 applies.
4. **The part disappears:** the anchor is dead, an error in both checks and in validation (COR-050 point 7).
   - **The change that removed it owns the finding,** which fails in enforcing mode (COR-050 point 12).
   - **A point dropped without being retired** also fails the change check, whether anything anchors it or not.
5. **The part splits:**
   - **The id continues:** its text changed, so its dependants are flagged. The finding names the points the same change added, so the answerer can re-point.
   - **The id is retired with successors:** its dependants are flagged, not failed. The finding names the successors.
   - **The answer is a revalidation that changes the anchor list** (COR-050 point 6). An anchor left on a retired point stays flagged, and its debt dates from the retirement.
   - **A page's section** has no retired list. A split that keeps the heading flags. One that drops the heading leaves a dead anchor.

- **Note:** a synced record that drops a point with no successor kills every adopter anchor on it. The adopter's sync change then fails until they re-point. A successor turns that into friction they answer.

### What a point stands on, and why

A point binds only as part of its record, so it stands on what says whether and how the record binds.

- **The point's section:** its heading and its text.
- **The record's front matter:** its status above all, so a superseded record flags every point's dependants.
- **The preamble,** the text before the first section: where a "Partially superseded by …" line sits (the decisions README, "Refining an accepted record").
- **The decision lead,** the Decision's text before its first heading. It states the decision every point refines, and holds definitions, as COR-050's five terms.
- **What it cost in the window:**
  - **living-docs DEC-001:** none of the six edits since its rules existed touched the three.
  - **COR-050:** 2 of its 14 edits since 27 September touched its decision lead, both in the paragraph of terms.
- **A page's section** stands on its text alone. A page's own fields say who reads it and its kind, not what a section says.

## Friction's comparison

Both checks compare the part's text between two states, with the reading collection entries already use. Nothing new is stored.

- **The change check:** a part changed when its file is in the diff and the part's text differs between base and head. It reads the file at both sides, and only a changed file.
- **The whole-repository check:** compares the part at each revalidation point with the latest commit (COR-050 point 6).
- **Debt (COR-050 point 9):** walks the file's versions since the point, cuts the part from each, and finds the oldest from which it has differed without returning.
  - **Today the walk compares the file's object.** A version whose object is the same holds the same part, so only versions that changed the file are read.
- **No hash is stored.** The checks compare text, and may compare digests in memory. COR-050 rejects a stored hash as the marker, and this keeps that.
- **One reading of where a part lies,** in artefact discovery, shared by entries, points and sections (ADR-057 point 2).
  - **Its readers:** the checks, validation and the artefacts document.
  - **The artefacts document** gives each part's span, as it gives an entry's (#1361).
- **`at` and the revalidation point are unchanged** (COR-050 point 3). What a revalidation answered is what the part held at its point.
- **Re-pointing an anchor** changes the anchor list, so it needs a revalidation in the same change (COR-050 point 6). Going from a whole record to a part costs one answer per dependant, once.
- **Deferrals** name an anchor by kind and value (COR-050 point 4), so a part anchor is deferred as any other.
- **The two checks agree:** both find the part with one reading, and its id never moves. The versioning note named stable ids as the precondition for that (alternative E).

## The two costly dependants

Part anchors would have asked the two costly dependants 10 times, where they were asked 110 times in the same window.

- **The method:** every commit on main in the window that revalidated the dependant. For each, which parts of its anchored documents changed: by point for the record, by section for the READMEs.
- **Unlike the versioning note,** this counts commits by what they changed, not the answers a rerun change check asked. So it covers the commits the rerun could not.

### The area index, `.pkit/README.md`

- **It rests on:** each area README's lead, which says what the area is for. Its "Where to start" also names two sections:
  - the decisions README's "The no-shared-files invariant"
  - the CLI README's "Authoring commands"
- **Its anchors would be** the ten leads and those two sections, in place of ten whole READMEs.
- **Asked 68 times in the window,** each time because an area README's content changed. The versioning note counted 62 answers in its sample.
- **With part anchors, once:** on 29 September (fae45bc9), a change rewrote four READMEs' leads and the CLI README's "Authoring commands".
- **Dead anchors:** none in the window. The 5 renamed headings were CLI command headings, which the index does not name.

### The seven rules anchored to living-docs DEC-001

- **They rest on point 3,** which lists what the shared rules require.
  - **RS-LDOC-003 and RS-LDOC-004 also rest on point 4:** each names a front-matter field, `reader` or `kind`, and point 4 says a page carries it.
  - **The versioning note read all seven as resting on point 3 alone.**
- **Their anchors would be** `living-docs:DEC-001#3`, with `#4` beside it for RS-LDOC-003 and RS-LDOC-004.
- **Asked 42 times:** six edits since the rules were written on 29 September, each asking all seven. The versioning note counted 35, over five of the edits.
- **What the six edits changed:** points 1, 8, 7, 3, 7 and 4, in that order. None changed the front matter, the preamble or the decision lead.
- **With part anchors, 9 times:** all seven for the edit to point 3 (499deec1), and the two field rules again for the edit to point 4 (1a3468a0).
  - **With point 3 alone, 7 times.** That is the versioning note's reading.

### Against the versioning note's numbers

- **It said:** anchors on the parts could spare up to 90 of the 97 answers the two dependants gave.
- **This count:** part anchors spare 100 of the 110 times the two were asked, counted by commit over the same window.
- **The dependant-side fixes it proposed are not needed for these two:**
  - **living-docs DEC-001 point 3** can keep restating the rules.
  - **The area index** need not be generated.

## The trade: fewer questions, a chance of a miss

A part anchor asks less, so a dependant that names too few parts misses a change.

- **A whole-record anchor never misses,** and asks about every edit.
- **A part anchor asks only about its parts.** Naming the parts a dependant rests on becomes a judgment, as a path anchor's glob is today.
- **The versioning note shows the risk:** it read the seven rules as resting on point 3 alone, and two rest on point 4 too.
  - **The edit to point 4 was harmless for them:** RS-LDOC-003 answered that it "touches neither the reader field nor the readers point".
- **What limits it:**
  - **A point stands on its record's front matter, preamble and lead,** so a supersession or a new definition still reaches every point's dependants.
  - **The whole record stays available** to a dependant that rests on most of it.
  - **Re-pointing is a person's decision,** shown word for word, since it is a revalidation (COR-050 point 3).
- **Not proposed:** telling a part's dependants about the record's other changed points. It would bring back the noise the part removes.

## Migration

No migration is due under COR-010, since nothing an adopter has stops working.

- **Whole-record anchors keep their reading:** the record's whole file, as today.
- **Every citation keeps its meaning,** since each point keeps its number.
- **Synced records arrive converted** with the sync, as kit-owned files.
  - **Every adopter artefact anchored to one is asked once,** by the sync that brings it.
  - **pkit has no adopters today,** so that cost is nothing now, and grows with every adopter.
- **An adopter's own records** keep the list form and stay valid. Their points cannot be anchored until converted.
  - **A part anchor on a list-form record** is dead, and its finding says to convert the record.
  - **A command converts one record,** word for word, under the consent rule of the configuration writer (COR-048 point 5).
- **The new checks fail nothing an adopter has:**
  - **A list-form record** has no headed points, so validation checks nothing in it.
  - **A gap in a headed record's ids** is reported, not failed.
  - **The change check's new findings** reach only changes made after the upgrade.
- **What would make a migration due:** converting every adopter record on upgrade (question 4), or failing a gap in an existing record.
- **In project-kit,** the conversion is a change of its own, not a migration. 95 records change, since two use headings already, and the 32 artefacts anchored to them answer once.

## Settled positions this reopens

Each is listed for the maintainer's authorisation, before a record or the README changes.

1. **COR-050, what an anchor stands on:** "for a record, the record's file", and for an artefact its content (its opening terms, and points 2 and 5).
   - **The change:** a record or artefact anchor may name a part, and then stands on the part.
   - **Points 6, 7 and 9 follow:** the change check compares the part, a part that does not resolve is dead, and debt walks the part.
2. **COR-050's rejected "anchors per section, via markers inside the prose":** sections, yes. Markers, still no.
   - **Its reason, "a second convention, parsed out of prose":** points are already how records are cited. A section is found by its heading, which COR-050 point 1 already reads for an entry.
   - **The other rejected alternative stays rejected:** anchors on every statement. A part is the unit people already cite.
3. **The decisions README:**
   - **"Refining an accepted record":** step 1 gains the next unused number and no renumbering, and a new step retires points. Step 3's "no residue" reads the retired list as data.
   - **"Schema":** points as headings, and the optional `retired-points`.
4. **COR-025's ADR schema, "uniform with COR/PRJ/DEC":** the optional field joins every id-space's front matter.
5. **ADR-057, touched and kept:** a resolver still answers files. Point 2's homes gain one reading of where a part lies, in artefact discovery.
6. **living-docs DEC-001, touched and kept:** a captured source stays one file whose every change counts. Its rejected "counting only some fields" stays rejected.
   - **Its reason was growing "the backbone for one consumer".** Parts serve every consumer of record and artefact anchors, so the reason does not reach them.
7. **COR-051 point 3, kept:** `#` gains a second use, a part of a record or a page. An extension point is no anchor value, so `RS-WRITE-002#labels` is refused as one.

- **Note:** the versioning note's recommendation for its question 4, fixing the two dependants with what exists, is not a settled position. The maintainer's choice of 8 October replaces it.

## Alternatives weighed

Each alternative was weighed against permanence, how a record reads, and what a script can check.

- **For writing a point's id:**
  - **The list number, never renumbered:** an inserted point would show a number it does not have, since a list counts from its first item. Rejected.
  - **New points at the end of the record:** keeps the list right, but a record then reads in the order of its refinements. That is the change log the decisions README forbids. Rejected.
  - **A letter after the number, as legislation inserts 4A:** reads in order, but needs an order of letters and gives nothing the next number does not. Rule sets already take the next number. Not taken.
  - **A bold label, as PRJ-002's D1:** shows as written, but a second reader must parse a marker out of prose. COR-051 rejects markers parsed by pattern. Rejected.
  - **A hidden marker, such as an HTML comment:** the reader who cites it cannot see it, and it is a marker in prose. Rejected.
  - **Points as entries of a collection, in COR-051's shape:** each point would be an artefact. A synced tree is never a place (COR-050 point 14), so a core record could not be one in an adopter's project. Rejected.
  - **Position with a text guard, as [project-management:DEC-038-criterion-addressing]:** makes a renumbering loud for an anchor. Every prose citation would still move silently. Rejected.
- **For naming a page's section:**
  - **A reserved `#lead`:** clear, but a reserved word can meet a heading named "Lead". Not taken: the title's slug names the lead.
  - **No sections, and the area index generated instead:** the versioning note's fix. It mends one dependant, and every other page keeps anchoring a README whole.
- **For a point's content:**
  - **The section alone:** asks least, but a superseded record or a changed definition would reach no point's dependant. Rejected.

## Recommendation

Choose permanent point ids written as headings, part anchors for records and pages, and retired points with their successors. Convert project-kit's records now, while no adopter holds a copy.

- **Why now:** each point keeps its number, so no citation changes. No adopter's artefacts are asked by the converted records.
- **The order:** the records first, then the reading and validation, then friction, then the two costly dependants.
- **Recount afterwards,** over a later window and by part, before relying on the numbers.

## Questions for the maintainer

Each question is one decision, with a recommendation. Ask them one at a time.

1. **Do a record's points become headings with permanent ids?**
   - **Recommendation:** yes, `### 5 — Title`, each with the id it has today. A new point takes the next unused number where it belongs.
   - **Else:** keep the list, and add each new point at the end of the record.
2. **Is a page's section named by its heading?**
   - **Recommendation:** yes, by the heading's slug, and the title's slug names the lead. A renamed heading is a dead anchor.
   - **Else:** records only. The area index is then generated, as the versioning note proposed.
3. **Does a retired point keep its id in the record, with its successors?**
   - **Recommendation:** yes, in `retired-points` in the front matter. A split then flags its dependants, and says where the text went.
   - **Else:** no list. A dropped point is a dead anchor, and its number stays unused by practice alone.
4. **How do an adopter's own records gain point ids?**
   - **Recommendation:** on request, by a command that converts one record word for word. No migration is due.
   - **Else:** a backbone migration converts every record in an adopter's project on upgrade.

## Slicing

On the recommended answers, the work comes in four groups, in this order.

- **A, the records:**
  - **A1, a core record:** a record's points are permanent identifiers. It sets the form, the next unused number, retired points and successors. Authored with `pkit new decision core`, through the decision-author skill.
  - **A2, the decisions README and the record template:** the refining rule, the schema and `retired-points`. The decision-author skill's guidance follows.
  - **A3, project-kit's records converted:** the 95 records, word for word, by the command of B3. The 32 artefacts anchored to them answer once.
  - **A4, the operational rules files:** the same rule and form for `.pkit/rules/core.md` and `.pkit/rules/project.md`.
- **B, the reading and validation:**
  - **B1, one reading of where a part lies:** points, sections and entries, in artefact discovery. The artefacts document gives each part's span.
  - **B2, validation:** the failing findings and the reported gap of "Writing points".
  - **B3, the conversion command:** one record at a time, under the consent rule.
- **C, friction:**
  - **C1, COR-050 refined:** a record or artefact anchor may name a part. Through the decision-author skill.
  - **C2, the checks:** the change check, the whole-repository check, the debt listing and the explanation compare the part.
    - The container schema accepts `#<part>` on the two kinds.
    - The change check fails a point removed without being retired, and a point renumbered.
- **D, the two costly dependants:** the seven rules re-point to DEC-001's points, and the area index to the leads and two sections. Then the count again, by part.
- **Changesets:** each issue declares its segment by PRJ-002. The segment is the maintainer's judgment.

## Found on the way

1. **A check of citations by point:** once ids are permanent, a warning could report a citation of a retired or missing point.
   - **It would read prose,** as the decisions README's revision-marker warnings do, so it would warn and never fail (COR-055 point 5).
