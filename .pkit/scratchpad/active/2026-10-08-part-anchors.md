---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# Part anchors — an anchor can point at one part of a document

A design for #1387. It lets an anchor name one part of a document, so a change to another part flags nothing that rests on that part alone.

- **Raised by:** the document-versioning design's question 4 (#1383, PR #1384). The maintainer chose on 8 October to anchor to parts, knowing it reopens settled positions.
- **Read from main at `78837af9`:** the records, the code and the counts below. The history counts use the versioning note's window, 27 September to `30cfb15a`.
- **Citations:** records and rules by permanent id and point. Code by file and line at `78837af9`, since code has no permanent ids.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", before the settled positions.
- **Decided:** by the maintainer on 9 October. He authorised the seven settled positions it reopens, and answered questions 1 to 3. Question 4 is parked for #1394.
- **Next:** the issues in "Slicing" are filed on the maintainer's go.

## The question

How does an anchor name one part of a document, and what must stay true of the part's name for friction to compare it?

## In short

A part is a section headed by its id, the shape a collection entry already has. A record's points keep their numbers for good, written as headings. A page's sections are named by their headings, in a slice after the records.

- **Records:** each point becomes a heading, `#### 11. Truth-chain order`. The number it has today is its id for good.
  - **A new point** goes where it belongs and takes the next unused number.
  - **A dropped or split point** keeps its number for good. It is listed in the record's `retired-points`, with the points that carry its text on, and a one-line stub stays where it was.
  - **A numbered list inside a sub-section is no point.** Steps and tests stay lists and renumber, and nothing cites them by point.
- **Anchors:** `record: living-docs:DEC-001#3` names a point. `artefact: .pkit/cli/README.md#authoring-commands` names a page's section, and `.pkit/cli/README.md#` its lead. A rule is already an entry, named by its id.
- **Friction:** compares only the part. A reading of where a part lies is shared with collection entries, and records' points are read in a home of their own.
  - **A point also stands on what makes its record bind:** its status and title, its preamble and Summary, and the Decision's text outside every point and stub.
- **The five cases:** a changed part flags its dependants, and a change elsewhere flags none. A move holds. A removed part is a dead anchor. A split flags, and an anchor on a retired point stands on nothing until re-pointed.
- **Numbering:** a command of its own, beside `pkit migrations check-diff`, fails a change that renumbers or reuses a point, or drops one without retiring it.
- **What it saves:** the two costly dependants were flagged 109 times in the window. Part anchors would have flagged them 10 to 17 times, once the area index says no more than its sources' leads.
- **What it costs:** 86 records' points become headings once, word for word, and 19 records use headings already. The 28 artefacts anchored to the 86 answer once. No citation changes.
- **No migration is due:** nothing an adopter has stops working. An adopter's own records keep working in the list form. How they convert is #1394's, one general mechanism, part of upgrading (question 4, parked).
- **The trade:** a dependant that names too few parts misses a change, as a path anchor's glob can today.
- **It reopens,** with the maintainer's authorisation: COR-050's whole-file anchors and its rejection of section anchors, and COR-051's rejection of ids parsed from prose. It also reopens ADR-057's homes, ADR-058's member order, and the decisions README's rules on refining, the schema and citing.

## Today

An anchor stands on a whole file or a whole artefact, except a collection entry, which is already a part. Records' points are cited by number everywhere, and a refinement may renumber them.

### What an anchor stands on (COR-050)

- **A record anchor:** the record's whole file. Any change to it flags every dependant (COR-050 point 5).
  - **The change check** asks only whether the record's file is in the diff (`src/project_kit/friction_check.py:911-914`).
  - **The whole-repository check and the debt walk** compare the file's object between versions (`src/project_kit/friction_repository.py:917-931`).
- **An artefact anchor:** the artefact's content, its body and its own fields, never its container (COR-050 point 5).
- **A collection entry is already a part:** its data entry with the body section headed by its id (COR-050 point 1). A rule is such an entry (COR-051 point 2).
  - **One reading of the section:** the first heading that opens with the id, to the next heading of the same or a higher level, fenced code skipped (`src/project_kit/friction_discovery.py:2470-2548`).
  - **Its span:** `pkit friction artefacts --json` gives each entry's lines, from the same reading (#1361).
- **A registered kind:** the files its resolver names. A capability gets precision by keeping one value in one file (ADR-057, "Why a resolver answers files").
- **Rejected in COR-050:** "anchors per section, via markers inside the prose", and "anchors on every statement inside a document".

### How records number their points

Records write their points in five forms, and a refinement renumbers them on insertion.

- **The rule:** "A new point goes where it belongs among the others, not at the end of the record" (the decisions README, "Refining an accepted record").
  - **Why it renumbers:** a Markdown list shows numbers counted from its first item. An inserted item moves every later number on screen, so the source is renumbered to match.
- **Where points sit:** in the Decision, at its top level or in one numbering that runs across its group headings, as in COR-050.
  - **105 records have points,** 608 in all. 50 of them are synced to adopters, as core or capability records. 55 are project-kit's own PRJ and ADR records.
  - **17 records hold numbered lists inside a sub-section,** such as COR-024's critic patterns and DEC-028's gate algorithm. They are steps, tests or reasons, and nothing cites them by point.
  - **69 records have no numbered list** in their Decision. Their decisions are prose, or sections under sub-headings.
- **The five forms of the 105:**
  - **A list item with a bold lead,** `5. **Truth-chain order.**`: 67 records.
  - **A bold number,** `**1. Intra-file ownership partition.**` in ADR-002: 13 records.
  - **A bold label,** `**P7 — …**` in COR-033 and `**D1 — …**` in PRJ-002: 7 records. ADR-039 mixes labels with a list.
  - **A numbered heading,** `### 1. Title` in COR-047 and ADR-031: 17 records.
  - **A labelled heading,** `### D1 — …` in [project-management:DEC-032-conditional-reviewer-requirements] and [project-management:DEC-042-label-contributions]: 2 records.
- **Citations:** about 2,900 places cite a record's point by its number, in about 500 files. COR-050 alone is cited by point 676 times.
  - **The count is approximate:** it matches a pattern, "COR-050 point 5" and its variants.
  - **Labels are cited both ways:** COR-033's points are cited by label, as "P7", 66 times, and as "point 7" 72 times.
- **Renumbering in history:** 3 events moved 10 numbers, across 529 versions of 191 records. Only one of them moved points.
  - **COR-050, on 28 September (205f644a):** a refinement moved five points down, point 10 to 14 among them. COR-050 had 7 citations by point then.
  - **[project-management:DEC-028-agent-as-approver-paths] on 1 October,** and [project-management:DEC-029-project-manager-agent-shape] on 3 October, inserted steps into a procedure inside a sub-section. Renumbering those steps was right.
- **The core rules were renumbered too,** on 28 September (c5cfd787). A new rule 16 moved rules 16 to 18 down. The change rewrote the two citations of the cross-repository rule from 18 to 19.

### Other permanent ids

- **Rule ids (COR-051 point 3):** never renumbered, never reused.
  - **A new rule takes the next number and goes where it belongs.** WRITE shows it: RS-WRITE-014 sits before RS-WRITE-013.
  - **A retired rule stays in place** with its id, its status and its successor (COR-051 point 4).
- **Analysis ids:** a use case takes the next free number, never used again (the software-analysis README, "Ids").
  - **Two branches that take one number** meet `pkit analysis check-numbers` before the merge, and validation's duplicate-id check on the merged tree. The first to land keeps the number.
- **Position with a text guard:** [project-management:DEC-038-criterion-addressing] names an acceptance criterion by its index and an optional expected text. It rejected stable ids as not worth a migration of every issue body.

## Naming a part for good

A record's point becomes a section headed by its id and its title, as a rule is. The id is the number or label the point has today.

### The form

- **A point:** `### 5. Title`, then the point's text. A point under a group heading, as in COR-050, takes the next level: `#### 11. Truth-chain order`.
- **The id:** the token the heading opens with, then its separator.
  - **A number takes a full stop,** `### 5. Title`, as its list item did. 17 records write their points so already.
  - **A label takes a dash,** `### D1 — Title`, as a rule's heading does. Records that label their points keep their labels, since they are cited by them.
- **The title:** the point's bold lead, word for word, without its closing full stop. Every point in the 86 records to convert has one.
- **The text:** the point's text, word for word, taken out of the list's indent.
- **Which lists are points:** a numbered list at the Decision's top level, or one numbering that runs across its group headings.
  - **A numbered list inside a sub-section** belongs to that sub-section. Its numbers are steps or an order, so it stays a list and renumbers, as a use case's steps do.
  - **The person who converts a record confirms the reading,** since it comes from how the record is cited. The 17 records with such lists have no citation by point.
- **Why headings:**
  - **They render as written.** A list counts from its first item, so an inserted point would show a number it does not have.
  - **They use the heading reading friction already has.** That reading already takes `1. Title` as opening with the id `1` (`src/project_kit/friction_discovery.py:2496-2502`).
  - **They end their sections.** A heading closes the point before it, which a bold label does not, so the one reading can cut a point's text.
  - **19 records use them already,** in the two forms above.
- **A point is looked for in the Decision only.** An entry's id is looked for in the whole body, but a `### 6.` heading in Rationale is never point 6.
- **A misspelt point is never silent:** validation warns of a heading in the Decision that opens with a number or a label in another form. An example is `### 16 - Title`.
  - **No record has one today,** so the warning is silent until someone writes one.
- **Live ids sit in headings, and retired ids in data, each with a stub heading.** A rule's id is defined in data, and its heading only locates its section (COR-051 point 2).
  - **A live point's heading defines its id,** which reopens COR-051's rejection of ids parsed from prose ("Settled positions").
  - **A retired id is defined in `retired-points`.** Its stub is held to that entry ("Writing points").

### Writing points

A point keeps its id for good, and a retired point leaves an entry for tools and a stub for readers.

- **A new point** goes where it belongs and takes the next unused number. That is one past the highest id the record holds, retired ids included.
  - **So numbers can read 4, 16, 5,** as WRITE's rules read 011, 014, 013.
- **No point is renumbered.** Points may be reordered, since a point keeps its id wherever it sits.
- **Amending a point** stays as today: it is edited in place.
- **A retired point leaves two things:** an entry in `retired-points` in the record's front matter, for tools, and a stub where the point was, for readers.
- **A dropped point** is retired with no successor.
- **A split point:**
  - **Where one part keeps the claim,** that part keeps the id, and the rest takes the next unused number.
  - **Where no part continues the claim,** the id is retired, with the points that carry its text on as its successors.
- **A merge:** the point that keeps the claim keeps its id. The other is retired, with that point as its successor.
- **Successors are points of the same record.** A point that another record overturns is a partial supersession, which has its form already.
  - **The point stays as it stood,** and the record's top line reads "Partially superseded by …" (the decisions README, "Refining an accepted record").
  - **That line sits in the preamble,** which every point stands on, so it flags every point's dependants.

**The list,** for tools:

```yaml
retired-points:
  "6": ["7", "16"]
  "9": []
```

- **Its layout:** a block mapping, one retired id to a line, in the order of the ids. Two branches that retire different points then edit different lines.
  - **Successors are not followed further.** A successor retired later keeps its own line, and the earlier line and its stub are not rewritten.
- **Where the field sits:** at the top level of the record's front matter, outside the `pkit:` container. It is the record's own field, as `status` is (COR-053 point 10).

**The stub,** for readers:

```markdown
### 6. Retired
Its content is in points 7 and 16.
```

- **Why a stub:** a record may read 1, 2, 3, 4, 16, 5, 7, 8, and a missing number with no explanation looks like a mistake.
  - **It stays in place,** as a retired rule stays in its rule set (COR-051 point 4), and a repealed section stays in a law.
- **Its heading:** the point's id at the point's level, then the title `Retired`. A point under a group heading takes `#### 6. Retired`.
  - **The title `Retired` marks a stub,** so no live point takes it. No record in project-kit has such a heading today.
- **Its line:** one sentence in one form, written from the entry's successors.
  - **One successor:** "Its content is in point 7."
  - **Several:** "Its content is in points 7 and 16."
  - **None:** "Its content is in no other point."
- **No residue:** the stub names where the content went, and nothing else. It holds no date, no issue and no reason, so it is data a reader sees, not narration.
- **A stub's section is no part.** It holds no point's text, and no point stands on it ("What a point stands on").
  - **An anchor on a retired id** stands on nothing, whatever its stub says.
  - **Editing a stub flags no part anchor's dependant,** since no part anchor stands on it. A whole-record anchor sees it, as it sees any change to the file.

**The list is the source, and the stub follows it.** A tool reads retired ids and their successors from `retired-points` alone. Validation holds each stub to its entry, both ways, as COR-051 point 2 joins a rule's data with its section.

- **So ids sit in two places, by state:** a live id in its heading alone, and a retired id in data, with a stub heading kept in step with it.

**What validation checks,** in the decisions member, from the working tree alone (COR-055 point 2):

- **Fails:**
  - a malformed `retired-points`
  - a retired id with no stub, or a stub whose id is not retired
  - a stub whose line differs from the one its entry gives
  - a live point's heading that uses a retired id
  - a successor that was never a point of the record
- **Why these fail and do not warn:** each follows from the new field or from a stub's heading. An adopter's record that titles a point `Retired` fixes it with a new title.
- **Warns:** a duplicate id, a gap in the ids counting retired ones, and a heading in a form the grammar refuses.
  - **Why it only warns on a record's own headings:** an adopter's record may hold any of these today. A warning fails nothing they have, and the numbering command catches each new one.
  - **No schema for a record's whole front matter:** it would fail adopters' own fields and make a migration due (COR-010). Only the new field's shape is checked.

### The numbering command

A check that compares a change with its base is a command of its own (COR-055 point 2). Checking a change to records is such a check, so it gets one, named here `pkit decisions check-diff`.

- **Where it runs:** as a line of its own in the check gate, beside `pkit migrations check-diff`. It binds only where a project wires it in, which the decisions README and the CLI reference say.
  - **It runs whatever friction's mode,** and whether or not anything is anchored, since numbering binds records nobody anchors.
  - **It reads its base through `project_kit.default_branch`** (COR-054), and its head from the working tree's one file listing (ADR-057 point 2).
  - **It skips a synced copy** in an adopter's project, as the revision-marker warnings do, since that record is refined where it is authored.
- **What it fails,** for each record the change touched:
  - **an id the base holds or retires** that the head neither holds nor retires
  - **a new id** that is not past every id the base holds or retires
  - **a base point's text found at the head only under another id,** the id left out of the comparison. That is a renumbering, or a retirement whose successor kept the claim.
  - **a duplicate id, or a heading in a refused form,** that the change added
  - **a retired id without its stub, or a stub without its entry,** at the head
  - **an id the default branch took** since the branch left it, as `check-numbers` finds a number. The finding lists the change's artefacts that anchor that id, so the author re-points them with the new number.
  - **a record id that the default branch took** since the branch left it. Today two branches that stamp one record number meet only after the merge.
- **What it warns of:**
  - **a base point's title found at the head under another id,** with its text changed. That is likely a renumbering with an edit, but the command cannot be sure.
  - **an item added to a numbered list at a Decision's top level,** or a new record whose Decision is such a list. A list-form record converts before a point is inserted.
- **On a pull request's test merge,** the default branch is already in the head, so the default-branch rules find nothing. There the rule on a duplicate the change added is the gate.
- **Two branches that take one number:** the first to land keeps it, as for analysis ids.
- **Note:** the friction change check could hold these findings. It is not used for them, since it only warns in warning mode and is dormant where nothing is anchored (COR-050 points 12 and 15).

### What replaces the decisions README's rule

The refining rule keeps placement where a point belongs, and gains permanence.

- **Step 1 reads:** "A new point goes where it belongs among the others and takes the next unused number. No point is ever renumbered."
- **Amending a point** stays as the README has it: the point is edited in place.
- **A new step:** a dropped or split point leaves its number to the record's `retired-points`, with the points that carry its text on. A one-line stub stays where the point was.
- **A record whose points are a list** converts before a point is inserted, since a list cannot show a number out of order.
- **Step 3, no residue:** the list and the stub carry no date, no issue and no narration. The list is data a tool reads, and the stub is data a reader sees. Both stand as a retired rule does, in place with its successor (COR-051 point 4).
- **The schema:** "complex decisions may use a numbered list" becomes points as headings, the optional `retired-points`, and a stub for each retired point. A numbered list stays allowed inside a sub-section.
- **"Citing":** a point gets two written forms, "COR-050 point 11" in prose and `COR-050#11` as an anchor's value. The section says which goes where.

### Other documents with numbered parts

- **Rule sets:** already permanent. A rule is an entry, named by its id.
- **The operational rules files:** `.pkit/rules/core.md` and `.pkit/rules/project.md` number their rules, cited as "core rule 20". They were renumbered once (c5cfd787).
  - **Not in this design:** nothing anchors their parts, no check reads their numbers, and they are no rule sets (COR-051 point 1).
  - **Their numbers' permanence is a question of its own,** with the rules area's README as its home ("Found on the way").
- **Analysis artefacts:** an entry is a part already. A use case's numbered steps are no parts in this design.

## What a part anchor looks like

A part anchor is an anchor's value, then `#`, then the part's id. Only the record and artefact kinds take a part.

```yaml
pkit:
  friction:
    anchors:
      record:
        - COR-050                 # the whole record, as today
        - COR-050#11              # point 11 of a core record
        - living-docs:DEC-001#3   # point 3 of a capability's record
        - PRJ-002#D1              # a labelled point
      artefact:
        - .pkit/cli/README.md#                    # the page's lead
        - .pkit/cli/README.md#authoring-commands  # a section of the page
        - RS-LDOC-003                             # a rule: an entry, already a part
```

- **A record's point:** the record's id, `#`, the point's id. A capability's record keeps its prefix, `living-docs:DEC-001#3`.
- **A page's section:** the document's path, `#`, the heading's slug.
  - **The slug:** the heading's text in lower case, with every character but letters, digits, spaces and hyphens dropped, and spaces made hyphens.
  - **The slug rule is pkit's own,** since hosts differ at the edges, such as a second heading with one slug.
  - **The section** runs to the next heading of the same or a higher level, as an entry's does.
  - **Two headings with one slug** make an anchor naming it ambiguous. That is an error, fixed by renaming one heading.
- **An empty slug is refused,** such as that of a heading made only of symbols. So no heading's name is empty.
- **A page's lead:** the path, then `#` with nothing after it. No heading has an empty name, so the lead's name never meets a heading's.
  - **The lead** is the body before its first heading, not counting a first-level heading that opens it. A page without a title, such as a file included under core rule 13, has a lead too.
  - **A retitled page** keeps its lead's name. The title is in the lead's text, so a retitle flags the lead's dependants.
- **An artefact named by its id** takes a part the same way, unless it is a collection entry.
- **A rule, or another collection entry:** named by its id, as today. A collection file's parts are its entries, so a slug on one is refused, naming the entry to use.
- **An anchor on a part of its own artefact** is refused. An artefact rests on what lies outside it.
- **Between artefacts, parts are ignored:** cycles and truth-chain order are judged between whole artefacts (COR-050 points 5 and 11).
- **Not a path anchor:** code has no parts with ids, and a glob of parts means nothing.
- **Not a registered kind:** a resolver still answers files (ADR-057 point 3).
- **Reading the value:** it splits at its last `#`. A value that names a file whole, `#` included, is read whole, so no anchor that works today changes.
- **Why `#`:** COR-051 point 3 names an extension point `RS-CMN-003#cause-location`, so that `#` never clashes with a namespace's colon. A part reads the same way, a named thing inside another.
  - **An extension point is no anchor value,** so `RS-WRITE-002#labels` is refused as one.
- **Why the id the heading shows:** the anchor names what a reader sees, `#11` for `11. Truth-chain order` and `#D1` for `D1 — …`. A prefix such as `P11` would make the two differ.

### Why a page's section has no permanent id

A page's section is named by its heading, which is not permanent. A rename is caught, never silent.

- **Records are cited by point across projects.** A renumbering misleads every citation silently. A page's sections are seldom cited, and their headings are their only structure.
- **A section anchor never crosses a sync:** a synced tree is never a place (COR-050 point 14), so an adopter never anchors a page another project owns. A point anchor does cross it, which is why points need permanent ids and sections can live with renames.
- **A permanent id on a section would be a marker in the prose,** the second convention COR-050 rejected.
- **A renamed heading fails loudly:** the anchor is dead, and the change that renamed it owns the finding (COR-050 point 12).
- **How often:** 5 of the 68 changes to area READMEs in the window renamed a heading. All 5 were CLI command headings, which carry the command's signature.
- **One consumer is measured:** the area index. `CONTRIBUTING.md` anchors the decisions README whole, and the adapters README anchors the Claude Code adapter's README whole. Neither is measured yet.
  - **So page sections are a slice of their own,** after the records, and can wait for a second consumer (question 2).
  - **A heading that carries a signature is a poor anchor:** every new flag renames it, such as `### friction check [--base <ref>] …`. A dependant anchors the enclosing section instead, such as "Authoring commands".

## The five cases

Both checks read each case the same way, since both find a part with one reading. A point's id never moves, and a section's slug moves only with its heading. Flagged means friction to answer, never a dead anchor.

1. **The part's text changes:** its dependants are flagged.
   - **A point's text** is its heading and its section. The heading's level counts too, as it does for an entry.
   - **A point also stands on what makes its record bind** (below). A change there flags the dependants of every point.
   - **The explanation** shows the part's diff alone, so the answerer reads only what changed under the dependant.
2. **Something else changes:** nobody is flagged who anchors only other parts.
   - **In a record:** the other points, Context, Rationale and Implications, and the front matter outside the fields below.
   - **A whole-record anchor** is flagged by any change, as today.
3. **The part moves:** the anchor holds, and nobody is flagged.
   - **A point keeps its id** wherever it sits in its record, and a section keeps its slug.
   - **A record renamed** is followed, as today (COR-050 point 5).
   - **A point renumbered anyway** fails the numbering command, whose fix is to put the id back.
   - **A heading renamed** is no move. The section is gone under its old slug, so case 4 applies.
4. **The part disappears:** the anchor is dead, an error in both checks and in validation (COR-050 point 7).
   - **The change that removed it owns the finding,** which fails in enforcing mode (COR-050 point 12).
   - **A heading added later with an anchored section's slug** makes the anchor ambiguous. That is an error too, owned by the change that added the heading.
   - **A point dropped without being retired** also fails the numbering command, whether anything anchors it or not.
5. **The part splits:**
   - **The id continues:** its text changed, so its dependants are flagged. The finding names the points the same change added, so the answerer can re-point.
   - **The id is retired:** an anchor on it stands on nothing, at every state where the id is retired. That differs from the old point, so the dependant is flagged once. The stub is no ground for it.
   - **The anchor is no dead anchor:** the record says where the point went. Validation warns of each anchor on a retired id until it is re-pointed, naming the successors.
   - **The answer re-points it** in the same change, as a revalidation that changes the anchor list (COR-050 point 6). An answer that leaves it is not flagged again, and the warning stays.
   - **A page's section** has no retired list. A split that keeps the heading flags the dependants. One that drops the heading leaves a dead anchor.

### What a point stands on, and why

A point binds only as part of its record, so it stands on what says whether and how the record binds.

- **The point's section:** its heading and its text.
- **The record's status, supersession and title fields:** `status`, `supersedes`, `superseded_by` for an ADR, and `title`. A superseded record flags every point's dependants.
  - **Not the rest of the front matter.** A retirement edits `retired-points` and writes a stub, and must flag only the dependants of the retired point.
- **The preamble,** the text before the first section: where a "Partially superseded by …" line sits.
- **A Summary section,** which 38 records have: 36 ADRs, COR-044 and COR-053. The decisions README asks that a summary agree with the Decision, but a long one can state the decision first, as ADR-031's does.
- **The Decision's text outside every point and every stub:**
  - **its lead,** before its first heading. It states the decision every point refines, and holds definitions, as COR-050's five terms.
  - **a group's text** before the group's first point
  - **a sub-section that is neither a point nor a stub,** such as "Lifecycle" after D5 in [project-management:DEC-042-label-contributions]
- **Not a stub.** A retired point's stub is no point's text, and no point stands on it. So a retirement flags no other point's dependants, and neither does an edit to a stub.
- **So the Decision splits whole:** every line of it is in one point or one stub, or it reaches every point. A stub reaches none.
- **Text after a list's last item** would fall into the last point's section on conversion. The conversion asks the person to give it a heading of its own, or a place in the lead.
- **An amendment section** sits outside the Decision, where no point reads it. The decisions README forbids it, and validation warns of it.
  - **Six records hold one:** PRJ-008, [project-management:DEC-028-agent-as-approver-paths], [project-management:DEC-032-conditional-reviewer-requirements], [project-management:DEC-046-override-flag-convention], ADR-044 and ADR-049.
  - **Each is folded into the Decision** before any point of its record is anchored, as a refinement a person decides.
- **What it cost in the window:**
  - **living-docs DEC-001:** none of the six edits since its rules existed touched any of these. Its other edits were to Rationale and Implications, and it has no Summary.
  - **COR-050:** 2 of its 14 edits since 27 September touched its decision lead, both in the paragraph of terms.
- **An artefact's section** stands on its text and the artefact's own fields, such as a page's reader and kind, or a use case's status. A withdrawn use case then flags its sections' dependants.

## Friction's comparison

Both checks compare the part's text between two states, with the reading collection entries already use. Nothing new is stored.

- **The change check:** a part changed when its file is in the diff and the part's text differs between base and head. It reads the file at both sides, and only a changed file.
- **The whole-repository check:** compares the part at each revalidation point with the latest commit (COR-050 point 6).
- **Debt (COR-050 point 9):** walks the file's versions since the point, cuts the part from each, and finds the oldest from which it has differed without returning.
  - **Today the walk compares the file's object.** A version whose object is the same holds the same part, so only versions that changed the file are read.
- **A part missing at a state reads as empty.** So an anchor whose part was not there yet is flagged, never silently held. An example is an `at` from before its record was converted.
- **An anchor on a retired point** stands on nothing at every state where the id is retired, whatever its stub says. So both checks and debt read it alike.
- **No hash is stored.** The checks compare text, and may compare digests in memory. COR-050 rejects a stored hash as the marker, and this design keeps that.
- **Two homes, one over the other** (ADR-057 point 2, refined):
  - **Where a part of a document lies:** a body's headings outside fenced code, a section by its id or its slug, and the lead. Discovery cuts entries with it, and the rule-set pass lists sections with it.
  - **A record's points, over it:** the Decision's extent, which headings are points and which are stubs, retired ids, and what a point stands on. Friction, the debt listing, validation, the numbering command and the conversion call it.
  - **Why not artefact discovery:** a record is not an artefact. Validation, the numbering command and the conversion would depend on the friction engine to read a record, which points the wrong way.
- **Friction builds a part anchor's ground per file version.** The whole-repository check already reads an anchor's content from a file's entry at a commit (`src/project_kit/friction_repository.py:952-991`), so debt needs no second walker.
- **The artefacts document** gives, beside each part anchor, the span it resolves to, as it gives an entry's (#1361). It does not list a record's points.
- **`at` and the revalidation point are unchanged** (COR-050 point 3). What a revalidation answered is what the part held at its point.
- **Re-pointing an anchor** changes the anchor list, so it needs a revalidation in the same change (COR-050 point 6). Going from a whole record to a part costs one answer per dependant, once.
- **Deferrals** name an anchor by kind and value (COR-050 point 4), so a part anchor is deferred as any other.
- **The two checks agree:** both find the part with one reading, as a function of a file and the anchor at any state, and a point's id never moves. The versioning note named stable ids as the precondition for that (alternative E).

## The two costly dependants

Part anchors would have flagged the two costly dependants 10 to 17 times, where they were flagged 109 times in the same window. The area index's share holds only once it says no more than the leads it rests on.

- **The method:** every commit on main in the window that revalidated the dependant, except the one that first anchored it. For each commit, the count reads which parts of the anchored documents changed: points for the record, and leads and sections for the READMEs.
- **Unlike the versioning note,** this counts commits by what they changed, not the answers a rerun change check gave. So it covers the commits the rerun could not.

### The area index, `.pkit/README.md`

- **It rests on:** each area README's lead, which says what the area is for. Its "Where to start" also names two sections:
  - the decisions README's "The no-shared-files invariant"
  - the CLI README's "Authoring commands"
- **Its anchors would be** the ten leads and those two sections, in place of ten whole READMEs.
- **Flagged 67 times in the window,** each time because an area README's body changed. Every answer was `unchanged`.
  - **Not counted:** fae45bc9, on 29 September, which first anchored the index.
- **With part anchors, 3 times:** 621a2451, b6ad50a2 and dc51fc1f each changed a command's sub-section under "Authoring commands". No lead changed.
- **Only once the index says no more than the leads:** its rows also restate the CLI's commands, the core reviewers, the two namespaces and the rules' include line.
  - **Anchored to what it says today,** the index would rest on the CLI README's command sections. That README's body changed in 57 of the 67 commits.
  - **LDOC asks the same of it already:** an index-like file is a signpost, never a summary of its contents (living-docs DEC-001 point 3). So the index is trimmed to what its leads say when it is re-pointed.
- **Dead anchors:** none in the window. The 5 renamed headings were CLI command headings, which the index does not name.

### The seven rules anchored to living-docs DEC-001

- **They rest on point 3,** which lists what the shared rules require. Some rest on more, and which ones is a judgment.
- **Flagged 42 times:** six edits since the rules were written on 29 September, each flagging all seven. The versioning note counted 35, over five of the edits.
- **What the six edits changed:** points 1, 8, 7, 3, 7 and 4, in that order. None changed the record's status, its preamble or the Decision's text outside its points.
- **With part anchors, by what each rule is read to rest on:**
  - **Point 3 alone, the versioning note's reading:** 7 times, all for the edit to point 3 (499deec1).
  - **With point 4 for RS-LDOC-003 and RS-LDOC-004,** which each name a field point 4 puts on a page: 9 times.
  - **With point 4 for RS-LDOC-001 too, and point 7 for RS-LDOC-003 and RS-USER-001:** 14 times. RS-LDOC-001 lists what point 4 says a page anchors. The other two rest on point 7's readers.
- **Point 7 is coarse for them:** it holds both of the capability's data points. Its two edits changed the reading evidence and the documentation check, not the readers.
  - **A part anchor names a whole point,** never an item inside one.

### Against the versioning note's numbers

The two notes count different things, so their numbers agree in direction and are not compared one for one.

- **The versioning note** counted answers in a rerun sample: 62 for the index and 35 for the rules, 97 in all. It said part anchors could spare up to 90 of them.
- **This note** counts commits that revalidated: 67 and 42, 109 in all. Part anchors spare 92 to 99 of them, by what the rules are read to rest on.
- **Both find most of the cost avoidable,** and both find it in the same two dependants.
- **The dependant-side fixes the versioning note proposed:**
  - **living-docs DEC-001 point 3** can keep restating the rules.
  - **The area index** need not be generated. It is trimmed to what its leads say.

## The trade: fewer flags, a chance of a miss

A part anchor flags less, so a dependant that names too few parts misses a change.

- **A whole-record anchor never misses,** and flags every edit.
- **A part anchor flags only its parts.** Naming the parts a dependant rests on becomes a judgment, as a path anchor's glob is today.
- **This design shows the risk on itself:** its draft read the seven rules as resting on fewer points than their own answers name.
  - **RS-LDOC-003's answers** say each edit "touches neither the reader field nor the readers point". Those are points 4 and 7.
  - **The misses were harmless:** each edit left what the rule rests on alone, as the answers say.
- **What limits it:**
  - **A point stands on what makes its record bind,** so a supersession or a new definition still reaches every point's dependants.
  - **The whole record stays available** to a dependant that rests on most of it.
  - **Re-pointing is reviewed with its change.** The revalidation it needs is shown word for word (COR-050 point 3), but the anchor list itself is seen only in the diff.
- **A heading that carries a signature** renames with every new flag. An anchor on it dies, and the change that renamed it re-points it.
- **Not proposed:** telling a part's dependants about the record's other changed points. It would bring back the noise the part removes.

## Migration

No migration is due under COR-010, since nothing an adopter has stops working.

- **Whole-record anchors keep their reading:** the record's whole file, as today.
- **Every citation keeps its meaning,** since each point keeps its number. A list inside a sub-section keeps renumbering, and nothing cites it by point.
- **Synced records arrive converted** with the sync, as kit-owned files.
  - **Every adopter artefact anchored to one is flagged once,** by the sync that brings it.
  - **How many adopters that reaches:** the versioning note rests on the maintainer's statement that pkit has no adopters to migrate (#1383). DEC-042 names a capability incubated in an adopter's repository.
  - **Either way,** the cost is one answer per anchored artefact, and nothing breaks.
- **A synced record that later retires a point** flags the adopters' dependants on it once. Their anchors stand on nothing, none is dead, and validation names the successors.
  - **A point dropped without being retired** fails the numbering command where the record is authored, so it never reaches an adopter.
- **An adopter's own records** keep the list form and keep working unconverted. Their points cannot be anchored until converted.
  - **A part anchor on a list-form record** is dead, and its finding says to convert the record.
  - **A point inserted into a list-form record** converts it first, since a list cannot show a number out of order.
  - **How they convert is parked** (question 4). A project's own content follows format changes through one general mechanism, part of upgrading, which #1394 designs. Its answer covers this conversion.
  - **Two kinds of record are never converted:** a synced copy, which is refined where it is authored, and a superseded record, whose body the README keeps as it stood. This note asks #1394's mechanism to keep both refusals.
- **The new checks fail nothing an adopter has:**
  - **Validation warns of** a duplicate id, a gap and a refused heading form. It fails only on what is new: `retired-points`, stubs and part anchors.
  - **The numbering command** judges a change, so it fails only what a change after the upgrade adds.
- **What would make a migration due here:** failing what an older record may hold. Whether #1394's mechanism counts as a migration is #1394's to settle.
- **In project-kit,** the conversion is a change of its own, not a migration. 86 records convert, and the 28 artefacts anchored to them answer once. Slice D2 says which conversion it uses.
- **One release for the synced conversions:** the 40 synced records among the 86 ship together, so an adopter's artefact is flagged once, not once a release.

## Alternatives weighed

Each alternative was weighed against permanence, how a record reads, and what a script can check.

- **For writing a point's id:**
  - **The list number, never renumbered:** an inserted point would show a number it does not have, since a list counts from its first item. Rejected.
  - **New points at the end of the record:** keeps the list right, but a record then reads in the order of its refinements. That is the change log the decisions README forbids. Rejected.
  - **A letter after the number, as legislation inserts 4A:** reads in order, but needs an order of letters and gives a claim nothing the next number does not. Not taken.
    - **Steps, whose order matters,** stay lists and renumber, since nothing anchors or cites them by number.
  - **A bold label, as PRJ-002's D1:** shows as written, but ends no section, so the one reading cannot cut a point's text. A misspelt label would also be silently no point. Rejected.
  - **A hidden marker, such as an HTML comment:** the reader who cites it cannot see it, and it is a marker in prose. Rejected.
  - **Points as entries of a collection, in COR-051's shape:** each point would be an artefact. A synced tree is never a place (COR-050 point 14), so a core record could not be one in an adopter's project. Rejected.
  - **Points as data beside their headings:** a `points` list in the front matter, joined with the headings as COR-051 joins a rule's data and section. Not taken: the form report and the numbering command catch a misspelt point too, without a list that repeats every heading.
  - **One heading form, `### 5 — Title`:** matches a rule's heading, but converts 17 records that already show their numbers. Not taken.
  - **Position with a text guard, as [project-management:DEC-038-criterion-addressing]:** makes a renumbering loud for an anchor. Every prose citation would still move silently. Rejected.
- **For naming a page's section:**
  - **The title's slug for the lead:** a title's section runs to the end of the page, and a retitle would kill every lead anchor. Not taken.
  - **A reserved `#lead`:** clear, but a heading named "Lead" would meet it. Not taken.
  - **No sections, and the area index generated instead:** the versioning note's fix. It mends one dependant, and every other page keeps anchoring a README whole.
- **For what a point stands on:**
  - **The section alone:** flags least, but a superseded record or a changed definition would reach no point's dependant. Rejected.
  - **The whole front matter:** a retirement would flag every point's dependants. Rejected.
  - **The whole record but Context, Rationale and Implications:** reaches a Summary, and an amendment section too. Not taken: an optional section such as "Alternatives considered" would flag every point's dependants. The Summary is named instead.
- **For an anchor on a retired point:**
  - **Following its successors, as a record anchor follows a rename:** saves the warning until re-pointed, and nothing more. It needs successors read at every state, chains of retirements, and an order of successors. Not taken.
- **For keeping a retired point:**
  - **The list alone:** a tool finds the id, but a reader meets a missing number with no word. Not taken by the maintainer (question 3).
  - **The stub alone:** a reader sees it, but a tool would read the id and its successors from prose, as COR-051 rejected. Not taken.
  - **No list and no stub:** a dropped point is a dead anchor, and its number stays unused by practice alone. Not taken.
- **For where numbering is checked:**
  - **The friction change check:** only warns in warning mode, and is dormant where nothing is anchored. A comparison with a base is a command of its own anyway (COR-055 point 2). Rejected.
  - **`pkit analysis check-numbers`:** belongs to an optional capability, and reads ids from files and their names, not from headings. Rejected.

## Found on the way

1. **A check of citations by point:** once ids are permanent, a warning could report a citation of a retired or missing point.
   - **It would read prose,** as the decisions README's revision-marker warnings do, so it would warn and never fail (COR-055 point 5).
2. **The answers a change wrote could show its changed anchor lists:** COR-050 point 3's list shows the artefact, the outcome and the reason. A narrowed anchor would then be shown word for word too.
   - **It would reopen** COR-050 point 3's list and core rule 20, so it is not part of this design.
3. **Six records hold an amendment section** that the decisions README forbids ("What a point stands on"). Validation warns of each, and none has been folded yet.
4. **The operational rules files' numbers:** cited as "core rule 20", and renumbered once. Permanence would need headings, since a list shows an inserted rule's number wrong. It would need no front matter, since an agent's context takes the files in whole. Its home would be the rules area's README.
5. **An umbrella command for the change checks:** the numbering command would be the sixth line in `scripts/check.sh` that compares a change with a base. COR-055's reason for one validation command, that it forgets nothing registered, applies here too. It is a question for a scratchpad note of its own.
   - **"An id the default branch took" has two instances now,** in `check-numbers` and the numbering command. They read ids differently, so nothing is extracted yet (COR-007).

## Review

### The critic

The critic found five red flags, fourteen gaps, six weak points and seven counter-alternatives. It agreed with permanent ids, comparing text and resolvers that answer files. It also agreed that a renamed heading is a dead anchor, and that other points' changes stay silent.

**Red flags:**

1. **A retirement edits the front matter, which every point stood on.** **Answer:** accepted. A point stands on `status`, `supersedes` and `superseded_by` only ("What a point stands on").
2. **Today's number is no id where lists restart or state an order.** **Answer:** accepted, from a census of all 191 records.
   - **Restarted and ordered lists sit inside sub-sections:** 17 records hold them, none cited by point. Such a list is no point, and stays a list that renumbers ("Which lists are points").
   - **So no citation changes,** and no question is needed. Two of the three renumbering events were such steps, and "Today" says so.
   - **"4A" is not needed:** steps renumber, since nothing anchors or cites them by number.
3. **The census missed `### N. Title`.** **Answer:** accepted. 17 records use it, and it is the form for a number now. The counts are redone: 105 records with points, 86 to convert, and 28 artefacts flagged once.
4. **The numbering checks sat in the friction change check.** **Answer:** accepted. They move to a command of their own in the check gate, as COR-055 point 2 requires. COR-050 points 12 and 15 stay as they are.
5. **"10 of 110" under-anchored the dependants.** **Answer:** accepted, and recounted.
   - **The rules:** 7, 9 or 14 times, by what they are read to rest on. Their own answers support 14.
   - **The index:** 3 times with the draft's anchors, not once. fae45bc9 first anchored the index and is no flag, so the total is 67.
   - **The index restates more than its leads.** The saving holds only once it is trimmed, which LDOC asks of a signpost anyway.

**Gaps:**

6. **A record does not split cleanly into lead, points and group headings.** **Answer:** accepted. A point stands on the Decision's text outside every point, so the Decision splits whole. The conversion asks where trailing text goes, and amendment sections are folded first.
7. **An artefact's section missed its status fields.** **Answer:** accepted. A section stands on its artefact's own fields too.
8. **"Stays flagged" cannot arise under COR-050.** **Answer:** accepted. An anchor on a retired point stands on nothing, at every state, so it is flagged once. Validation then warns of it until re-pointed, naming the successors. A part missing at the earlier state reads as empty.
   - **Revised after the architect's finding 3:** the first answer had the anchor follow its successors. That broke at states after the retirement, and needed chains.
9. **"A point renumbered" was not well defined.** **Answer:** accepted. The command fails only on a base point's text found under another id, the id left out. A title found under another id with its text changed is warned of, not failed.
10. **Two branches taking one number can leave a dependant on the wrong point.** **Answer:** accepted. The command checks the default branch, as `check-numbers` does, and lists the change's anchors on the colliding id. `retired-points` is a block mapping, one id to a line.
11. **"No migration is due" covered only the introduction.** **Answer:** accepted in each part.
    - **A synced record's retired point** is friction for adopters, not a dead anchor. The command keeps a point from being dropped unretired.
    - **An adopter record with restarted headed ids** is warned of, not failed.
    - **A list-form record** converts before a point is inserted.
12. **Naming sections by slug breaks in traced cases.** **Answer:** accepted in each part.
    - **Signature headings** are named as a cost, with the enclosing section as the steadier anchor.
    - **A later duplicate heading** is an error owned by the change that added it.
    - **The lead** is `path#`, defined for pages without a title. The slug rule is pkit's own, and a value naming a file whole is read whole.
    - **The note on linking to a point** is dropped.
13. **The operational rules files cannot take front matter.** **Answer:** accepted. After the architect's finding 9, they leave this design for a question of their own ("Found on the way").
14. **The settled positions were incomplete.** **Answer:** accepted in part.
    - **Added:** ADR-057 point 2, refined rather than kept, and COR-050 point 12's case of an ambiguous anchor. COR-050's "precision comes … from whoever revalidates" is met with the count.
    - **Not reopened, each with its reason:** COR-050's modes and dormancy, COR-055, COR-010, COR-048 point 5 and living-docs DEC-001.
    - **living-docs DEC-001's reason,** revised after the architect's finding 14: captured sources are a registered kind, and a registered kind takes no part.
15. **A successor in another record is a partial supersession.** **Answer:** accepted. Successors stay in their record, and the "Partially superseded by …" line covers the rest.
16. **Re-pointing is not shown word for word.** **Answer:** accepted. "The trade" says the anchor list is seen only in the diff, and "Found on the way" proposes showing it.
17. **"pkit has no adopters today" needs checking.** **Answer:** accepted. The note rests on the maintainer's statement in #1383, and names DEC-042's incubating adopter. Nothing breaks for an adopter either way.
18. **The slicing's order and dependencies.** **Answer:** accepted. The decisions come first, then the reading, validation and commands, then friction, then the conversion. The missing slices are added.
19. **The flagship example had the wrong number.** **Answer:** fixed. Truth-chain order is COR-050 point 11, so its heading is `#### 11. Truth-chain order`.

**Weak reasoning:**

20. **The heading form is a pattern parsed from prose too.** **Answer:** accepted in part. A heading ends its section, which a bold label does not. A misspelt point heading is warned of by validation and fails the command, so it is never silent.
21. **The comparison with the versioning note is not like for like.** **Answer:** accepted. The two counts stand apart and agree in direction. Of the index's 68 commits, 67 were `unchanged` answers and one first anchored it.
22. **The objection to `#lead` hit the title's slug too.** **Answer:** accepted. `path#` names the lead.
23. **A bare number matches only half of COR-033's citations.** **Answer:** accepted. The anchor names what the heading shows.
24. **Some terms drift.** **Answer:** fixed. "Flag" is the one term, and a section's slug moves with its heading.
25. **Two decisions were missing from the questions.** **Answer:** not taken, since neither is open. Restarted lists change no citation (finding 2), and COR-055 point 2 places the checks (finding 4). Question 3 says it stands on question 1.

**Counter-alternatives:**

26. **Points as data plus headings.** **Answer:** weighed, not taken. The form report and the command catch a misspelt point without a list that repeats every heading.
27. **Accept `### N. Title`.** **Answer:** adopted, as the form for a number.
28. **Two kinds of numbered list.** **Answer:** adopted, as "Which lists are points".
29. **A command of its own.** **Answer:** adopted.
30. **A complement rule for what a point stands on.** **Answer:** adopted, inside the Decision. Amendment sections are folded first, since the README forbids them.
31. **An empty part for the lead.** **Answer:** adopted.
32. **A successor for every retired point of a synced record.** **Answer:** not needed. Any retired point flags its dependants once and leaves no dead anchor.

**Agreement and writing:**

- **Findings 33 to 37:** kept as they stand.
- **Finding 38, WRITE:** the note on adopters moved into "Migration", and the two verbless fragments have verbs.

### The architect

The architect found the direction sound, with three concerns, ten fit issues, six drifts and four points worth recording. It agreed with the critic's answers except on findings 8, 13 and 14, which are revised above. It raised an escalation, which the settled positions and the questions now carry.

**Architectural concerns:**

1. **The reading of a part should live in a home of its own, in two layers.** **Answer:** accepted ("Friction's comparison").
   - **A reading of where a part lies,** which discovery and the rule-set pass call.
   - **A record's points over it,** which friction, validation and the two commands call.
   - **A point is looked for in the Decision only,** never as an entry is, anywhere in the body.
2. **COR-051's rejection of ids parsed from prose is reopened, and was not listed.** **Answer:** accepted. It is a settled position now, with the argument and the mix it makes: live ids in prose, retired ids in data.
3. **Following a retired point's successors is under-defined.** **Answer:** accepted, with the simpler reading. An anchor on a retired id stands on nothing at every state, and validation names the successors. That removes chains, an order of successors and the state asymmetry.

**Fit issues:**

4. **A point did not stand on a Summary, which 38 records have.** **Answer:** accepted. A point stands on the Summary and on `title` too. The whole record outside three sections stays not taken, since optional sections such as "Alternatives considered" would flag every point.
5. **The numbering command needs tightening.** **Answer:** accepted in each part.
   - **It is named `pkit decisions check-diff`,** and catches a record id two branches took.
   - **It reads its base through `project_kit.default_branch`,** and skips synced copies.
   - **Its first rule covers retired ids.** It warns of a point added to a list-form record, and binds only where a project wires it in.
6. **Severities and ADR-058's member order.** **Answer:** accepted.
   - **A duplicate id, a gap and a refused form** are warnings, not reports.
   - **The member order** is a settled position, decided with A3.
7. **Page sections have one measured consumer.** **Answer:** accepted in part. Page sections are a slice of their own after the records, and question 2 asks whether they wait. The sync-boundary argument and the refusal of an empty slug are added.
8. **The boundary between A1 and A2.** **Answer:** accepted. A1 states a record's anatomy, and A2 states what a point stands on. The CLI reference names the command, and A1 states the rule.
9. **The operational rules files are out of scope.** **Answer:** accepted. They move to "Found on the way", as a question of their own.
10. **The conversion command must refuse some records.** **Answer:** accepted. It refuses a synced copy and a superseded record. Its authority is the refinement in place, with COR-048 point 5 an analogy only.
11. **The artefacts document should not list records' points.** **Answer:** accepted. It gives, beside each part anchor, the span it resolves to.
12. **Cycles, truth-chain order and self-anchors.** **Answer:** accepted. Both are judged between whole artefacts, and an anchor on a part of its own artefact is refused.
13. **The shape of `retired-points`.** **Answer:** accepted. It is the record's own field, outside the `pkit:` container, and only its shape is checked.

**Drift:**

14. **living-docs DEC-001's reason, and its follow-ups.** **Answer:** accepted. The reason is that a registered kind takes no part. The capability's agent, onboarding guidance and grounding checks learning part anchors is a slice now.
15. **The decisions README's "Citing" section.** **Answer:** accepted. It joins the README's reopened sections and slice A4.
16. **COR-025 is not reopened.** **Answer:** accepted. At most its illustrative block changes, in A4.
17. **The texts that follow A3.** **Answer:** noted for A3 and B1: ADR-057 point 3's wording, and the docstrings that move with the reading.
18. **Showing changed anchor lists would reopen COR-050 point 3 and core rule 20.** **Answer:** accepted. "Found on the way" says so, and it does not ride on A2.
19. **Releases.** **Answer:** accepted. A2 is held from a release until C ships, the synced conversions ship in one release, and A4's README rule lands with B4.

**Worth recording:**

20. **ADR-057 point 2's draft text.** **Answer:** the architect authors it in A3, once the maintainer settles the home.
21. **ADR-058 point 3, if reordered.** **Answer:** part of A3.
22. **An umbrella command for the change checks.** **Answer:** in "Found on the way", for a scratchpad note of its own.
23. **"An id the default branch took" has two instances.** **Answer:** noted in "Found on the way", not extracted.

**Escalation:** the architect asks the maintainer to authorise seven things. Five are settled positions below: the home, COR-051's rejection, the reading of retired points, the Summary, and the member order. Page sections are question 2, and the operational rules files left this design.

## Settled positions this reopens

The maintainer authorised all seven on 9 October. Each lands through its own reviewed change, before a record, an ADR or the README changes.

1. **COR-050, what an anchor stands on:** "for a record, the record's file", and for an artefact its content (its opening terms, and points 2 and 5).
   - **Authorised,** to change as below.
   - **The change:** a record or artefact anchor may name a part, and then stands on the part.
   - **What a point stands on:** its section, the record's status, supersession and title fields, its preamble and Summary, and the Decision's text outside every point and stub.
   - **Points 6, 7 and 9 follow:** the change check compares the part, a part that does not resolve is dead, and debt walks the part.
   - **Point 7 gains an exception:** an anchor on a retired point stands on nothing and is no dead anchor. Validation warns of it, naming the successors.
   - **Point 12 gains a case:** an anchor made ambiguous is the change's that made it so, as a dead anchor is.
2. **COR-050's two rejected alternatives:**
   - **Authorised:** sections yes, markers no.
   - **"Anchors per section, via markers inside the prose":** sections, yes, and markers still no. Its reason was "a second convention, parsed out of prose". Points are how records are cited already, and a section is found by its heading, as point 1 finds an entry.
   - **"Anchors on every statement":** stays rejected, since a part is the unit people already cite.
   - **Its reason, "precision comes … from whoever revalidates",** meets the count: the two dependants' answerers gave 109 answers, of which 10 to 17 concerned what they rest on.
3. **COR-051's rejection of "markers in the prose, parsed by pattern":** it chose ids in data, joined with the sections they head.
   - **Authorised,** to change as below.
   - **The change:** a live point's id is defined by its heading. A retired id is defined in data, and validation holds its stub heading to that data.
   - **Why it is safe enough:** a heading ends its section, a misspelt point heading is warned of, and the numbering command fails a change that adds one.
4. **ADR-057 point 2, one home per computation:** gains two homes, one over the other.
   - **Authorised:** the two new homes.
   - **Where a part of a document lies,** which discovery and the rule-set pass call.
   - **A record's points,** which friction, validation, the numbering command and the conversion call. A record is not an artefact, so artefact discovery is not widened.
   - **The architect authors the refinement in place,** as custodian of the ADRs (COR-025).
5. **ADR-058 point 3, the order of validation's members:** `friction` runs before `decisions`, so friction would read point structure that `decisions` checks later.
   - **Authorised,** and the architect decides the order.
   - **The choice:** the members are reordered, or a soft exception is recorded, as `configuration` has. The architect decides which in A3.
6. **The decisions README:**
   - **Authorised:** the refining, schema and citing sections.
   - **"Refining an accepted record":** step 1 gains the next unused number and no renumbering. A new step retires points into the list and a stub, and a list-form record converts first. Step 3's "no residue" reads the list and the stub as data, not narration.
   - **"Schema":** points as headings, the optional `retired-points`, and a one-line stub for each retired point. A numbered list stays allowed inside a sub-section.
   - **"Citing":** a point gets a second written form, its anchor value, `COR-050#11`.
7. **COR-051 point 3:** `#` gains a second use, a part of a record or a page. A sentence says that an extension point is no anchor value.
   - **Authorised.**

**Not reopened:**

- **COR-025's ADR schema:** ADRs take the README's schema by reference. At most its illustrative block gains the field.
- **ADR-057 point 3:** a resolver still answers files.
- **living-docs DEC-001:** no text changes. Its rejected "counting only some fields of a source's file" stays rejected, since captured sources are a registered kind, which takes no part.
- **COR-050's modes and dormancy (points 12 and 15):** the numbering findings live in a command of their own.
- **COR-010:** no trigger is met ("Migration").
- **COR-055:** the numbering check is a command of its own, as point 2 requires.
- **COR-048 point 5:** untouched. The point governs configuration keys, and how a conversion asks for consent is #1394's.
- **COR-050 point 3 and core rule 20:** untouched, unless the maintainer takes "Found on the way" item 2.
- **The versioning note's recommendation for its question 4,** fixing the two dependants with what exists: not a settled position. The maintainer's choice of 8 October replaces it.

## Recommendation

Points become headings with permanent ids, and part anchors reach records first and pages after them. A retired point stays as an entry in a list and as a stub where it was. The maintainer decided these on 9 October, and parked how an adopter's records convert, for #1394. Convert project-kit's records now, while few or no adopters hold a copy.

- **Why now:** each point keeps its number, so no citation changes. Each adopter artefact anchored to a converted record is flagged once by the sync, and nothing breaks.
- **Page sections next, as a slice of their own** (question 2): the area index needs them, and a second consumer can be measured meanwhile.
- **The order:** the decisions, then the reading, validation and the numbering command, then friction. The conversion, page sections and the two costly dependants come last.
- **The conversion:** an adopter's records follow #1394's mechanism. project-kit's own convert by that mechanism if it has landed, and otherwise by a project-kit-only conversion (Slicing, B4 and D2).
- **The area index needs its own fix too:** it is trimmed to what its leads say when it is re-pointed.
- **Recount afterwards,** over a later window and by part, before relying on the numbers.

## Questions for the maintainer

The maintainer decided questions 1 to 3 on 9 October, after authorising the settled positions. Question 4 is parked for #1394.

1. **Do a record's points become headings with permanent ids?** **Decided: yes,** by the maintainer on 9 October.
   - **The answer:** a record's points become headings carrying the number they have today, which is their id for good. The forms are `### 5. Title` for a number and `### D1 — Title` for a label.
   - **Writing:** a new point goes where it belongs and takes the next unused number. A list inside a point stays a list.
   - **Asked first:** whether existing projects need a migration or lose links.
   - **Answered:** no number changes, and no file is renamed. Whole-record anchors keep working, and a project's own list-form records keep working unconverted ("Migration").
   - **What it authorises:** A1, and the reading, validation and numbering command for records (B1 to B3), then friction for points (C).
   - **Not taken:** keeping the list, and adding each new point at the end of the record.
2. **Are a page's sections anchored by their headings now, or after a second consumer?** **Decided: (a), now,** by the maintainer on 9 October.
   - **The answer:** a page's sections and its lead are anchored by heading slug, as a slice after the records. The area index is trimmed to what its leads say when it is re-pointed.
   - **What it authorises:** slice E, and the area index's half of G.
   - **Not taken:** records only, until a second page is measured, with the area index anchoring its sources whole meanwhile, or generated.
3. **Does a retired point keep its id in the record, with its successors?** **Decided: yes, with a visible stub,** the maintainer's option (b), on 9 October.
   - **The answer:** a removed or split point keeps its number for good, in `retired-points` with its successors, for tools. A one-line stub also stays where the point was, for readers ("Writing points").
   - **The reader's concern behind it:** a record may read 1, 2, 3, 4, 16, 5, 7, 8, and a missing number with no explanation looks like a mistake.
   - **Validation** checks that the stub and the list agree. Amending stays as today, edited in place.
   - **What it authorises:** the list, the stub and their checks, in A1, A4, B2 and B3.
   - **Not taken:** the list alone, which this note recommended, and no list, where a dropped point is a dead anchor.
4. **How do an adopter's own records gain point ids?** **Parked,** by the maintainer on 9 October.
   - **Why:** a one-off conversion command is the wrong shape. A project's own content follows format changes through one general mechanism, part of upgrading. Several changes need it: this one, analysis structure changes, and #1346.
   - **Where it is answered:** #1394 designs that mechanism after this design and #1385's are finished, and that design answers this question.
   - **Until then:** B4 and D2 say which conversion each follows ("Slicing").
   - **Not taken:** the one-record conversion command this note recommended. Converting every record on upgrade, the note's other answer, is #1394's to weigh.

## Slicing

On the maintainer's answers, the work comes in seven groups, in this order. Each decision is accepted before the work that cites it (the acceptance gate).

- **A, the decisions:**
  - **A1, a core record on a record's anatomy:** the point form, which lists are points, the next unused number, retired points with their successors and their stubs. It also says that a change's numbering is checked against its base. It is authored with `pkit new decision core`, through the decision-author skill.
  - **A2, COR-050 refined:** a record or artefact anchor may name a part, and what a part stands on. It gains the five cases, the retired point's exception and whose an ambiguous anchor is. It is refined through the decision-author skill, and held from a release until C ships.
  - **A3, ADR-057 point 2 refined,** with ADR-058 point 3 if the members are reordered. The architect authors both.
  - **A4, the texts that follow:** the decisions README's refining, schema and citing rules, with the stub, the record template, COR-025's illustrative block, and COR-051 point 3's sentence.
    - **It lands with D2,** so project-kit's converted records and the rules that describe them arrive together.
    - **Its sentence that a list-form record converts first** waits for B4. So an adopter meets that rule with the conversion it needs.
- **B, the reading, the checks and the conversion, for records:**
  - **B1, the two homes of A3:** where a part of a document lies, and a record's points. The artefacts document gives, beside each part anchor, the span it resolves to.
  - **B2, validation:** the decisions member's warnings, the shape of `retired-points`, and each stub held to its entry. The friction member's dead and ambiguous part anchors, and anchors on retired ids.
  - **B3, the numbering command,** `pkit decisions check-diff`, a line of its own in the check gate. It fails a retired id without its stub, and a stub without its entry. The CLI reference names it.
  - **B4, the conversion of an adopter's records: #1394's mechanism.** B4 is filed under #1394's build, not here.
    - **Why:** an adopter's records are a project's own content, the case #1394 exists for. The maintainer ruled out a one-off conversion command.
    - **Why it can wait:** a list-form record keeps working unconverted. Only its part anchors wait.
    - **What this note asks of it:** that it refuses synced copies and superseded records ("Migration").
- **C, friction for points:** the change check, the whole-repository check, the debt listing and the explanation compare the part. The container schema accepts `#<part>` on the record kind.
- **D, project-kit's records:**
  - **D1, the six amendment sections folded** into their records' Decisions, as refinements a person decides.
  - **D2, the 86 records converted,** word for word, with the 40 synced ones in one release. The 28 artefacts anchored to them answer once, and may re-point in the same answer.
    - **By #1394's mechanism,** if it has landed when C ships.
    - **Otherwise by a project-kit-only conversion:** a change of its own, which ships no command to adopters.
    - **Why it need not wait for #1394:**
      - The 40 synced records are converted where they are authored, and reach adopters by the sync. Converting them is project-kit's authoring, not a project's content following a format change.
      - G's re-pointing of the seven rules needs living-docs DEC-001 converted. Waiting would hold that saving for #1394 too.
- **E, page sections** (question 2): the slug and the lead in B1's reading, validation and friction for them, and `#<part>` on the artefact kind.
- **F, living-docs learns part anchors:** its agent, its onboarding guidance (DEC-001 point 8) and the checks of LDOC's grounding rule.
- **G, the two costly dependants:** the seven rules re-point to DEC-001's points, after D. The area index is trimmed to what its leads say, then re-pointed to them and the two sections, after E. Then the count again, by part.
- **Changesets:** each issue declares its segment by PRJ-002. The segment is the maintainer's judgment.
