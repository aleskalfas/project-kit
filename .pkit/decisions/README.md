---
variant: universal
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/decisions.py
        - src/project_kit/decisions_check_diff.py
        - src/project_kit/decisions_landing.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/default_branch.py
        - src/project_kit/docs_roots.py
        - src/project_kit/document_parts.py
        - src/project_kit/path_records.py
        - src/project_kit/record_points.py
        - src/project_kit/refs.py
        - src/project_kit/rule_sets.py
        - src/project_kit/validate.py
        - .pkit/skills/core/decision-author.md
        - .pkit/agents/core/architect.md
      record: [COR-001, COR-002, COR-003, COR-012, COR-014, COR-019, COR-025, COR-041, COR-046, "COR-050#1", "COR-050#2", "COR-050#7", COR-051, COR-053, COR-055, COR-058, "COR-059#3", "COR-063#5", "COR-064#6", COR-065, COR-066, COR-068, "ADR-081#1", "ADR-081#2", "ADR-081#3", "ADR-081#4", "ADR-081#5", "ADR-081#6", "ADR-081#7"]
      artefact:
        - RS-OPS-019
        - RS-LDOC-003
        - .pkit/lifecycle/upgrade-flow.md#the-steps-of-a-transition
        - .pkit/lifecycle/upgrade-flow.md#seed-paths
        - .pkit/lifecycle/README.md#what-sync-writes
---

# Decision records

<a id="why-this-shape"></a>

A decision record states one choice among alternatives, with its context and reasons, and binds only once a person accepts it. This README is the decision-record specification, and the records that decide its parts include [COR-001](core/COR-001-content-mechanisms.md), [COR-058](core/COR-058-record-points.md) and [COR-066](core/COR-066-accepted-before-landing.md). Where an accepted record decides, the rest of the system carries its decision out ([COR-065](core/COR-065-records-and-projection.md)). Why records exist, and how people record, accept and refine one, is in [the decision records' guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/decisions/README.md).

## Contents

<!-- pkit:contents -->
- [Two namespaces, two prefixes](#two-namespaces-two-prefixes)
- [The no-shared-files invariant](#the-no-shared-files-invariant)
- [File naming](#file-naming)
- [Schema](#schema)
- [Statuses](#statuses)
- [The acceptance gate](#the-acceptance-gate)
- [Adding a record](#adding-a-record)
- [Writing a record](#writing-a-record)
- [Refining an accepted record](#refining-an-accepted-record)
- [Citing](#citing)
- [Finding the records a path leads to](#finding-the-records-a-path-leads-to)
- [Checking a record's points](#checking-a-records-points)
- [Checking a change's numbering](#checking-a-changes-numbering)
- [Checking what a change lands](#checking-what-a-change-lands)
<!-- /pkit:contents -->

## Two namespaces, two prefixes

A record's folder and prefix say who owns it, and each namespace numbers its records apart ([COR-001](core/COR-001-content-mechanisms.md)):

| Folder | Prefix | Owner | How it changes |
|---|---|---|---|
| `core/` | **COR** | core | Refreshed by every sync, and never edited in a project |
| `project/` | **PRJ** | the project | Written by the project alone. The folder is a [seed path](../lifecycle/upgrade-flow.md#seed-paths), created where it is missing |

- **Numbering:** `COR-001` and the project's first record are separate decisions about separate things, numbered apart, and neither blocks the other.
- **A prefix names its side.** An id such as `COR-NNN` or `PRJ-NNN` says whether core or the project holds it, with no folder named.

### Two further id-spaces

Records also sit in two further places, each its own id-space, numbered apart:

| Location | Prefix | Owner | Decided by |
|---|---|---|---|
| The folder `adr-records` names in the agents overlay | **ADR** | the project | [COR-025](core/COR-025-adr-decision-space.md) |
| `.pkit/capabilities/<capability>/decisions/` | **DEC** | the capability | the capability |

- **The ADR folder** is the first entry of `adr-records` in the agents overlay, which the agents area's README describes. Where that key is absent, the CLI reference, `new decision`, says where the stamp puts an ADR. Every other reader takes the folder from the key alone, so without the key no ADR is read.
- **DEC numbers:** each capability numbers its own records. Two capabilities may each hold a `DEC-001`, and only two records with one `DEC-NNN` in one capability collide.
- **One id to a record in each id-space.** The id check below fails on each of these:
  - two records with one id in one id-space
  - a record whose id differs from its file name's number
  - a rule id claimed twice across the rule sets ("Rule sets" below)

  ```
  pkit decisions validate
  ```

- **Validation runs it too,** among the checks of its `decisions` member, which the CLI reference lists (`validate`).
- **One tree:** the check reads one tree, so it finds two records with one id only once both are in that tree. A gate that checks a pull request merged with the default branch finds them before the second lands. A gate that checks the branch alone finds them only after both land. The record that landed later then moves to the next unused number of its id-space, and its citations are mended ("Checking a change's numbering" below).
- **Against the default branch:** the numbering check compares a change with the default branch. Where the project runs it, it fails a change whose new record takes an id another change has already landed ("Checking a change's numbering" below).

Validation checks the project's own records only ([COR-055](core/COR-055-validation.md) point 1). A record that arrives as a synced copy is checked where it is authored, since the next sync overwrites an edit here.

- **Synced copies:** a core record, a record of a capability the methodology ships, and one of an externally-sourced capability. The project pulls the last whole, from the source the capability is pinned to ([COR-041](core/COR-041-external-source-distribution.md)).
- **What is left out:** neither check reports on such a copy, not its front matter, its id against its file name, or an id only copies share.
- **What is still reported:** a record of the project's own that takes a copy's id, on the project's record, since the copy keeps its id.

### Rule sets — a separate family with the same guarantees

Rules are not decision records, but they share their guarantees ([COR-051](core/COR-051-rule-sets.md)). A **rule set** is one file holding many one-paragraph rules. Its data sits in front matter, never in a sidecar beside the file ([COR-063](core/COR-063-document-sidecars.md)). Each rule's statement sits in the body, in a section headed by the rule's id.

Rules form their own identifier family, **`RS-<SET>-NNN`**: the family prefix, the rule set's name and a number. So a rule id can never collide with a record id. Ids are permanent: a rule is never renumbered, and a retired id is never reused.

- **Statuses:**
  - A rule without a status is **`proposed`**, and binds nothing. **`accepted`** rules bind.
  - A **`superseded`** rule names its successor, in the same rule set or in one that inherits it, and binds nothing.
  - Rules add **`withdrawn`**, which only rules have: a rule retired without a successor, binding nothing.
  - Superseded and withdrawn rules stay in place with their ids.
- **The acceptance gate** applies per rule, wherever the rule set lives. That includes project-owned rule sets outside this folder, under the project's internal documentation root by default. A proposed rule binds nothing, and accepting one is a reviewed change.
- **Origins.** Every accepted rule carries an origin: when it was decided, by whom and why, in the decider's words. Or the origin is a cited decision record, which must be accepted whenever the rule is.
- **Where rule sets live.** A method rule set ships with its component, and is cited with the component's name. A project rule set is the project's, and is cited bare. A project never edits a method rule set: it inherits it, pinning the set's major version.
- **Loaded rule sets.** A *loaded* set keeps operational rules ([COR-068](core/COR-068-loaded-rule-sets.md)). Its accepted rules bind on the work of each session that loads the file generated from it, never on an artefact. No set inherits it.
  - **Core's** operational rules are the backbone's loaded set `OPS`, so core rule 19 is `backbone:RS-OPS-019`.
  - **Where they live:** the rules area's README says where the set and its file are kept.
- **Citing a rule.** `RS-CMN-003` names a rule, and `RS-CMN-003#cause-location` names an extension point it offers. A method rule set's rules are cited with the component in front, `[living-docs:RS-LDOC-003]` in prose, bracketed like a capability decision citation.
- **Checked by validation.** Validation checks every rule set: the schema, the join between data and prose, ids, origins, successors and inheritance. The id check above reports a rule id claimed twice. The schemas reference, "Rule-set files", says where rule-set files live, and gives every check. Its page on backbone files, "Rule-set files", gives their front-matter layout.

## The no-shared-files invariant

Every file has exactly one owner, core or the project, and the two never share a path ([COR-001](core/COR-001-content-mechanisms.md)). The namespaces above rest on it, and so does every other area of `.pkit/`.

- **Core's files** are refreshed by every sync. A project never edits one, since the next sync overwrites the edit.
- **The project's files:** sync reads from them what it needs, such as the versions the project records. It writes into one only through merge delivery's tier that asks nothing, which adds core's entries and never removes one the project wrote. What sync writes, and what it never writes, is the lifecycle reference's ([its "What sync writes"](../lifecycle/README.md#what-sync-writes)).
- **A version transition,** such as an upgrade, creates each seed path that is missing, never over one that exists ([the lifecycle reference, "Seed paths"](../lifecycle/upgrade-flow.md#seed-paths)). Every migration runs inside a transition ([the lifecycle reference, "The steps of a transition"](../lifecycle/upgrade-flow.md#the-steps-of-a-transition)). A migration changes a project's file only within what the record that owns the file allows ([COR-059](core/COR-059-version-transition.md) point 3).
- **Extending core's content:** the same `core/` and `project/` pattern governs other areas, such as `.pkit/agents/` and `.pkit/rules/`. To extend core's content, add sibling files in the matching `project/` folder, and never edit a core file.
- **A file at a fixed path** that the project extends, such as `CLAUDE.md`, stays the project's. Core ships its content at a separate path, and merge delivery adds what is missing into the project's file in place. It never removes or rewrites what the project wrote ([COR-002](core/COR-002-merge-delivery.md)).
- **Note:** when each file is first written and when it is updated is COR-001's.

## File naming

A record's file is `<PREFIX>-NNN-<slug>.md`:

- **`<PREFIX>`** is `COR` in `core/`, `PRJ` in `project/`, `ADR` in the architecture records' folder, or `DEC` in a capability's `decisions/` ("Two further id-spaces" above).
- **`NNN`** is a zero-padded serial within the id-space: `001`, `002`, … `099`, `100`. Each prefix numbers apart, and each capability numbers its `DEC` records apart.
- **`<slug>`** is a kebab-case shorthand of the title, short enough to keep listings readable, and long enough to identify the decision without opening the file.

Examples: `COR-001-content-mechanisms.md`, a core record, and `PRJ-NNN-our-architecture.md`, a project's record.

## Schema

Each record is a Markdown file with YAML front matter and four required sections. A record keeps its front matter in its own file, never in a sidecar beside it ([COR-063](core/COR-063-document-sidecars.md) point 5).

```markdown
---
id: PRJ-NNN          # for the project's own records; core records use the COR prefix
title: Short imperative title
status: proposed | accepted | superseded
date: YYYY-MM-DD
author: Name <email>  # primary author (git-style)
supersedes: PRJ-NNN  # optional — a record this one replaces whole, in its namespace
retired-points:      # optional — each retired point's id, with the points that took its text
  "2": ["3"]
---

## Context

What situation or question prompted this decision?

## Decision

What was decided. Single sentence ideally. A decision of several parts gives each part a point, and the top line stays crisp.

### 1. A point's title

The point's text, up to the next heading of the same or a higher level.

### 2. Retired
Its content is in point 3.

### 3. Another point's title

Its text.

## Rationale

Why this choice over the alternatives? What goes wrong with a different choice?

## Implications

What does this mean for the code, the tests, the workflow, downstream decisions?
```

The four headings are the contract. A larger record may add sub-sections of its own, such as *Alternatives considered* or *Migration path*.

**`author`** is the person responsible for the record, as `Name <email>`, matching the identity they commit with. Git history holds the rest, such as each commit's author and its `Co-Authored-By` trailers.

**`supersedes`** names a record this one replaces whole, in the same namespace. The lookup from a path to its records reads the field so ("Finding the records a path leads to" below). In place of a superseded record an anchor names, the lookup lists each accepted record that replaces the superseded one:

- a record whose `supersedes` names the superseded record
- a record that the superseded record's own `superseded_by` names

**Points.** A Decision of several parts writes each part as a *point*: a heading that opens with the point's id, then its title. The id names the point for good ([COR-058](core/COR-058-record-points.md) points 1 and 3). The example's retired point 2 only shows the form, and a new record retires nothing.

- **The form:** `### 5. Title` for a numbered point: a number, then a full stop and a space. `### D1 — Title` for a labelled one: letters then a number, then a space, an em dash and a space. A record that labels its points keeps its labels.
- **The level:** one below `## Decision`, or one below the group headings that gather the points, as in `#### 11. Title`. The Decision's first heading in this form sets the level, and a heading in this form at another level is no point. A record's points all sit at one level, and their ids are unique across its groups.
- **The text** runs from the heading to the next heading of the same or a higher level.
- **A numbered list stays allowed** inside a point or another sub-section, for steps or an order. Once a record has point headings, every numbered list in it is a list, never points. Its items renumber when an item is inserted.
- **`retired-points`** is optional. It maps each retired id to the list of points that took its text. It holds one id to a line, in the order of the ids, at the top level of the front matter. A point no other point took writes an empty list, `"9": []`.
- **A stub** stays where each retired point was: a heading with its id and the title `Retired`, then one sentence written from its entry. It says nothing else, and no live point takes the title `Retired` (COR-058 point 4). The sentence takes one of these forms:
  - "Its content is in point 7."
  - "Its content is in points 7 and 16."
  - "Its content is in points 7, 12 and 16."
  - "Its content is in no other point."

A record whose points are still a numbered list, or paragraphs that open with a bold number or label, is in *list form*. It keeps working. A point inserted into a numbered list moves the numbers after it (COR-058 point 9).

## Statuses

A record has one of three statuses, and moves only forward through them: `proposed`, then `accepted`, then `superseded`.

- **`proposed`:** under discussion, within the change that proposes it. It binds nothing, and no work may rest on its content ("The acceptance gate" below). It belongs only on that change's branch, and reaches the default branch only once accepted ([COR-066](core/COR-066-accepted-before-landing.md) point 1).
- **`accepted`:** in effect. Work complies with it.
- **`superseded`:** replaced whole by a later record, whose `supersedes` names it. The superseded record adds a *Superseded by …* line at the top of its body, and is kept, never deleted ("Refining an accepted record" below).
- **No `rejected` status.** A refused proposal never lands, since its change is closed. A refused proposal whose reasoning is worth keeping becomes a scratchpad note, dropped with the reason it was refused ([COR-012](core/COR-012-scratchpad-notes.md)).
- **A proposed record already on the default branch** stays until a person accepts it or it is deleted (COR-066 point 4).
- **Within one namespace:** a record supersedes only a record of its own namespace.

## The acceptance gate

Work depends only on accepted records: code, content, tooling, and records that build on others. A proposed record is a draft, useful for discussion and binding nothing.

- **Who accepts:** a person. An agent writes `accepted` only once a person has accepted the record, and never accepts one itself ([COR-064](core/COR-064-answer-delegate.md) point 6).
- **When:** in the change that proposes the record, before work in that change rests on it. Work in that change, or in a change built on it that lands no earlier, may then rest on the record (COR-066 point 1).
- **Records** that build on other records cite only accepted ones. The reference-rot report lists each accepted record whose body cites a proposed record, and exits 0. It reads a capability's decision cited as `[<capability>:DEC-NNN]`, or as a bare `DEC-NNN` in that capability's own records:

  ```
  pkit refs rot
  ```

- **Documents** that describe what a record decides wait until it is accepted.
- **Before the merge:** the person who authorises it sees each record the change makes accepted, added accepted or set to accepted. Where no component that carries out merges shows that list, the change's author shows it. An edit made to such a record after its acceptance in the change is accepted only through that list (COR-066 point 3).
- **An edit to a record accepted where the branch left the default branch** that changes what it decides is a person's to accept. The numbering check lists it ("Refining an accepted record").
- **A new decision record's edits to accepted records** follow its acceptance, in the change that proposes it ([COR-066](core/COR-066-accepted-before-landing.md) point 5):
  - **Named first:** its Implications name each edit its change makes to an accepted record, one it refines, overturns in part or replaces whole. Each name states what the edit makes that record say, not only where it goes. Which edits those are, and how each is made: "Refining an accepted record" below.
  - **Then the edits:** a person accepts the new record in its change, and the edits follow there, as work resting on it. A change built on this one may land later, so the edits do not wait for it.
  - **Who accepts them:** accepting the new record accepts the edits its Implications name. An edit beyond them that changes what a record decides is a decision of its own.
  - **Read before the merge:** these edits are shown beside the list above ("Before the merge"), by whoever shows it. The person who authorises the merge reads each before the change lands. They are the edits the numbering check lists, and those the list above shows for a record accepted in a change this one builds on.
  - **A record the project receives from elsewhere:** the new record decides nothing against it. A change it needs there is proposed where that record is kept, and nothing rests on that change until the project receives it accepted.
  - **A rule:** an edit the new record forces on a rule of the project's own rule sets is named and made like its edits to records ([COR-051](core/COR-051-rule-sets.md)). An example is the edit to an origin that cites a record the new record supersedes. An edit to a rule set the project receives is proposed where that set is kept.
- **Not enforced yet:** the landing check refuses a merge that lands a proposed record, and lists what a change makes accepted (COR-066 points 2 and 3). It binds only where a project turns its key on, and a merge component or the host runs it ("Checking what a change lands" below). Until then, have a person accept each record a change adds before it lands.

## Adding a record

A project adds its own records in its own namespaces: `project/`, its architecture records' folder, and the `decisions/` of a capability it authors. A choice that later work will build on starts with its record, accepted before work rests on it ([COR-065](core/COR-065-records-and-projection.md) point 3).

Stamp the record with the authoring command, which the `decision-author` skill pairs with. The CLI reference's `new decision` gives the command's output, its numbering and its refusals:

```
pkit new decision <namespace> <slug>
```

- **The namespace** is `project` for a PRJ record, or `adr` for an ADR. For a DEC, it is the name of a capability the project authors ("Two further id-spaces" above).
- **The body:** fill in the sections ("Writing a record" below). A person accepts the record in its change before it lands ("The acceptance gate" above).
- **The index** of `project/` is its file listing, since each file name carries its slug. A project with many records may add a `README.md` inside `project/` as an index.
- **Core records** are refreshed on every sync, so a project never edits one. To change the methodology itself, with a new core record, a refinement or a supersession, propose it where the methodology is kept.

The stamped heading puts the record's points in the heading form from the start ("Schema" above):

- **Its level is the points' level.** To gather points under group headings, move it one level down, below the first group heading.
- **A numbered list written beside it** is a list, never points.
- **A decision with no parts** has no points. Delete the heading before the record first lands. A point dropped after that is retired, with a stub ("Refining an accepted record" below).

## Writing a record

Every record follows the four disciplines below, and states the present with no log of its revisions ("Refining an accepted record" below). An architecture record adds one more discipline, and a core record adds two more.

### Every record

- **Lead with meaning.** The title is short and states the decision, not the mechanism behind it. A plain-language summary opens the record, so a reader grasps the decision in under a minute, before the detail, the citations and the rejected alternatives. Each point cites what it needs, about one reference a point, and says what a reference holds before its identifier. The depth stays, and no boilerplate is asked for: the summary goes in front of the depth, never in its place.
- **Principles, not inventory.** A record captures a rule chosen among viable alternatives, with the reason that tells them apart. It lists no current state, such as paths, commands, files or the present members of a set. That state lives in a reference document the record points at, such as an area's README.
  - **Before drafting,** tag each piece of content as a rule or as state. Give state one cross-reference, not a list, and count an item between the two as state unless its reason is contested.
- **Name the role, not its current holder.** Where a record means whatever plays a part, such as what owns a boundary, it names the part, not the component that plays it today. Where the name is itself what the record decides, or belongs to something outside the project, the record names it plainly. Either way it describes the part sharply enough that only one thing could play it ([COR-046](core/COR-046-records-name-roles.md)).
- **Defined terms.** A record uses only terms that the project's accepted records or the methodology's define, generic English, and the tools it names. A term it needs that no record defines, it defines where it first uses it, or it waits for the record that decides the term. A core record holds the stricter form below, the axiom discipline.

### An architecture record (ADR)

- **Architectural fit.** An ADR records what the project built and why: a system boundary, a technology, an integration pattern, a key abstraction or a deployment topology. How the project works, its workflow, tooling and process, is a PRJ record's ([COR-025](core/COR-025-adr-decision-space.md), "Distinct from PRJ"). A decision that touches both takes its architectural side into an ADR, which cites a PRJ record for the rest.

### A core record (COR), the methodology maintainers' case

Two more disciplines bind a core record. Core records are written where the methodology is kept, and reach each project by sync ("Adding a record" above).

- **Axiom discipline.** The core records form an axiom system, which a reader can follow forward from the first. A core record uses only terms an earlier core record defines, generic English, filesystem or Markdown vocabulary, and external tools it names. It may point forward to a later record for navigation, but depends on none.
  - **Nothing undecided:** nor does it depend on a command, convention or tool that no record has decided yet. So it writes "the sync operation", say, until a record decides the command's name.
- **Refined with a later citation.** A record refined in place may still cite a later accepted record, if the citation states what the refinement adds. The record's original decision must still read without the later records.
- **Project-neutrality.** A core record makes sense, and applies, in any project that adopts the methodology. A choice about how the methodology's own source project is built, such as its CLI's name, is that project's own record instead. The same test places every artefact that has a core side and a project side, a rule, a skill or an agent among them ([COR-014](core/COR-014-universal-applicability.md)).

## Refining an accepted record

Edit an accepted record in place for a clarification, a scope tweak or a refinement where its decision stands: narrowed, widened or completed. Git history is the change log, so the record does not repeat it. Where a change overturns the record, in whole or in part, so that another record decides otherwise, write a new superseding record instead.

**A new record's edits to the records it changes** are named in its Implications. They are made once a person accepts it ("The acceptance gate" above, and COR-066 point 5). Each is of one of these kinds:

- **A record it refines:** each point it narrows, widens or completes, rewritten in place, and each point it adds, under the next unused number (step 1 below). Each takes a forward refinement pointer, in the form the in-body markers below give, where the Implications name one.
- **A record it overturns in part:** its *Partially superseded by …* line ("To supersede" below).
- **A record it replaces whole:** its `status: superseded` and its *Superseded by …* line, and in an ADR its `superseded_by` too ("To supersede" below).

**One test sorts the edits made in place: does the edit change what the record decides, in either direction?**

- **An edit that changes it** adds to what the record decides, narrows it or widens it. A point added, rewritten or retired in place can do so (step 2 below). It is a decision of its own. Like accepting the record, it stays a person's ([COR-064](core/COR-064-answer-delegate.md) point 6).
- **An edit that does not** leaves every choice as it stood. Examples are a typo fixed, a citation updated after a rename, and a fact corrected where the decision stands.
- **What a change edits in an accepted record** is listed by the numbering check, for whoever judges the edits ("Checking a change's numbering" below). It names each point and each other part of the record that the change edits, without quoting the words. So the judge reads the edit in the change itself.

**Editing in place means editing in place.** Fold a correction into the body, so the record simply states what is true. Append no amendment section, dated correction marker or "previously we believed" passage. If a record was wrong about a fact and the decision has not changed, fix the sentence. If the decision was overturned, in whole or in part, supersede.

To refine a record in place:

1. **Rewrite the section the change belongs to,** such as the decision point or the rationale paragraph. It states the corrected fact as part of the decision. A new point goes where it belongs among the others, not at the end of the record.
   - **In a record whose points are headings,** the new point takes the next unused number: one past the highest the record holds, retired ids included. A label carries its number, so a record labelled up to D5 goes on with D6, and numbers and each series of labels count apart. No point is renumbered, and no id is reused, so the numbers may read out of order, such as 4, 16, 5. A point amended or moved keeps its id ([COR-058](core/COR-058-record-points.md) point 3).
   - **In a record in list form,** the new point goes where it belongs. In a numbered list, the numbers after it move (COR-058 point 9).
2. **Keep the id of a point no other point continues.** This applies in a record whose points are headings. A point is retired when no point continues its claim. Its id goes into `retired-points`, with the points that took its text. A one-line stub stays where it was ("Schema" above, and COR-058 point 4).
   - **A dropped point** is retired with no successor.
   - **A split point:** where one part keeps the claim, that part keeps the id, and each other part is a new point with the next unused number. Where no part keeps it, the id is retired, with the new points as its successors.
   - **A merge:** the point that keeps the claim keeps its id. The other is retired, with that point as its successor.
   - **A successor retired later** gets a line of its own. The earlier line and its stub stay as they are.
   - **A point another record overturns** is not retired. It stays as it stood, and the record's top line reads *Partially superseded by …* (COR-058 point 5, and "To supersede" below).
   - **In a record in list form,** a dropped point goes, and in a numbered list the numbers after it move. Nothing is retired there, since its numbers are not permanent (COR-058 point 9).
3. **Add no revision marker,** such as an amendment heading or a block stamped with a date or an issue number. Add no note that the record was amended in place rather than superseded.
4. **Leave no residue of the change.** A word that makes sense only against the old text, such as "now", "no longer", "still" or "corrected above", is restated as plain fact. An issue number in a record cites evidence, and never dates a revision. A `retired-points` entry and its stub are data, not residue: they say where a point's content went, never when or why.
5. **Check the rest of the record agrees:** the summary, the Context, and any other sentence that restates the fact.

The commit message says what changed and why.

**To supersede**, write a new record whose `supersedes` names the old record's id. In the old record, set `status: superseded`, and put a *Superseded by …* line at the top of its body. Leave the rest of the body as it stood. For an ADR, also set `superseded_by` in the old record's front matter (the ADR schema in COR-025).

**A record a later one overturns only in part** stays `accepted`, and its top line reads *Partially superseded by …* instead. That line is its superseded-by line. The later record names it in no `supersedes`, which names only a record replaced whole ("Schema" above).

Two in-body markers do not narrate a revision, and are kept. Each points at another record rather than at a discarded belief:

- **The superseded-by line,** whole or partial.
- **A forward refinement pointer,** `(refinement per <record>)`, naming a later record that narrows, widens or completes this one. It goes on the sub-section heading, decision point or sentence refined.

Validation warns of each line of a record that narrates its own revision, naming the file and the line:

- **What it reads as narration:**
  - an amendment heading or marker: `## Amendment (…)`, `**Amendment 1**`, `**Amended by …**`
  - a revision stamped with an issue number or a date: `**Update (#252)**`, `(clarified, #813)`
  - change-log phrasing: "this record originally…", "previously we believed…"
- **What it does not read:** fenced blocks and inline code spans, a superseded record, and a synced copy, which is refined where it is authored. The two markers above match none of the shapes.
- **Warnings only:** they fail nothing, since the shapes are read from prose ([COR-055](core/COR-055-validation.md), "Why exactly one fails").

## Citing

Each kind of thing a record, an agent or a skill cites has one written form, and a point of a record has two:

- **A record** by its id, such as `COR-019`, `PRJ-NNN` or `ADR-NNN`. A capability's record goes in brackets with the capability in front, as in `[<capability>:DEC-NNN-<slug>]`.
- **A point of a record** by the record and the point's id: "COR-050 point 2" in prose, and `COR-050#2` as an anchor's value. COR-050 point 2 gives both forms.
  - **A labelled point** is named by its label, as in `PRJ-NNN#D1`.
  - **A capability's record** keeps its brackets in prose, "[<capability>:DEC-NNN] point 3", and drops them in an anchor's value, `<capability>:DEC-NNN#3`.
  - **A point written as a heading** keeps its id for good, so its citations stay on it ("Schema" above). A record whose points are still a list holds no point an anchor can name, since its numbers move (COR-050 point 7).
- **A rule** by its rule id, as "Rule sets" above describes: `RS-CMN-003`, `[living-docs:RS-LDOC-003]`.
- **A role or a point of a connection** by its address, in brackets ([COR-019](core/COR-019-schema-reference-form.md), [COR-053](core/COR-053-connection-points.md)). `[pkit::documentation]` names the documentation role, and `[pkit::documentation:readers]` names its readers point.
  - **The double colon** marks an address, and `[issue-types:task]`, with a single colon, stays a schema reference.
  - **An address resolves** to what an installed capability declares in its package metadata.

Two checks read these citations, and each warns at the file and the line:

```
pkit decisions validate   # the citations in records
pkit refs validate        # the citations and addresses in agents and skills
```

- **A point that is not there:** each warns of a citation of a point its record neither holds nor retires. It reads a point written after the record's id as `#N`, as `point N` or `points N and M`, or as a label alone, such as `D6`.
- **A record whose points are still a list:** the numbers its list shows are read as its points.
- **An address:** the second reports one that names no declared role or point. It also reports a bracketed token with a double colon that is not an address, such as `[::documentation:readers]`, with no publisher, as malformed.
- **A bare `DEC-NNN`** is read as the capability's own decision in that capability's record, agent or skill. Elsewhere it is read only where the text names a single capability for it, in brackets or by a link.
- **Warnings only:** neither fails on such a citation, since the citations are read from prose.

### Looking a citation up

This command prints where a citation lies, and resolves a point of a record and a rule's heading too:

```
pkit refs lookup <id> [--json]
pkit refs lookup <id>... --json
```

- **A record** prints its file, such as for `COR-019`, or for a capability's record, `<capability>:DEC-NNN`, with its slug or without.
- **A point of a record,** written as an anchor's value, prints its record's file and the anchor GitHub gives its heading, such as for `COR-050#2`. A retired point gives its stub's heading. A record whose points are still a list gives a point no heading, so it prints the file alone. An id the record neither holds nor retires does not resolve.
- **A point of a record that another record overturns in part** also prints the record's top line, *Partially superseded by …*, after the point's place. The point stays as it stood, so a reader sent to the point lands below that line (COR-058 point 5). The line names the overturning record, but not whether this point is among what that record overturns.
- **A rule** prints its place, and `--json` gives its heading's anchor too.
- **An address** prints where the role or point is declared, such as for `[pkit::documentation:readers]`.
- **With `--json`,** the command takes several ids. One document answers them in the order given, each with where it lies or why it does not resolve.
  - **Each answer** gives the file in `path` and the anchor in `anchor`. Its `received` says whether the file arrives as a synced copy.
  - **A point's answer** gives that top line in `partial_supersession`. The key is `null` where the record has no such line, and in every answer that is not a point's.

The way back, from a file to the records its anchors lead to, is in "Finding the records a path leads to" below.

## Finding the records a path leads to

This command goes from the files a change touches to the accepted records their anchors lead to ([COR-050](core/COR-050-anchors-and-friction.md) point 2). Records are cited, not loaded, and a project receives every core record and each installed capability's beside its own. So an agent that does not know a record exists finds it here:

```
pkit refs records-for <path>... [--json]
```

It goes the other way from looking a citation up, and declares nothing new. It takes every file a change will commit in one run.

- **Tied directly.** A record that a declared place holds is an artefact (COR-050 point 1). Each file its own path anchor matches is tied to the whole record. The artefact at a path ties each record it anchors, whole or at the points it names. These are the records to read before changing the file.
- **Through another artefact.** An artefact whose path anchor matches a file rests on each record it anchors. Its path anchors and its record anchors are two lists, not pairs. So such a record is related to the file, not shown to govern it. The answer lists these artefacts apart, each with the records it rests on, the one resting on the fewest first.
  - **What to do:** read the artefact, and follow the records it rests on that bear on the change.
- **How a path is matched.** An anchor matches a path as both friction checks match it. A path under `friction.exclude` is one no path anchor stands on (COR-050 point 7), so only the artefact at it ties anything. A file not yet written is matched by the globs that would cover it, and a folder is refused.
- **What it leaves out.** Only accepted records are listed, and a superseded one by each accepted record that replaces it ("Schema" above). A path anchor of a record that is not accepted ties nothing. Neither does any anchor of an artefact that arrives by sync, since it was written where the methodology is authored. Artefact anchors, and anchors of a kind a capability registers, are not followed.
- **The order.** The project's own records come first, then those it receives by sync.
- **An empty answer** is no sign that no record governs a file, since only what the anchors say is found. The answer says when no artefact carries anchors at all. It also names each file in a place whose front matter could not be read, since its anchors were not read.
- **With `--json`,** one document answers each path in the order given. It gives the records tied directly with their ties, and the artefacts with the records they rest on. Each record comes with its title and its file, and says whether it arrives by sync.

## Checking a record's points

A record's points keep their ids for good ([COR-058](core/COR-058-record-points.md)). Validation and the id check ("Two further id-spaces" above) check each record's points, as COR-058 point 7 sets out. They read the records the narration warnings read, so a superseded record and a synced copy are left out.

- **They fail on:**
  - a malformed `retired-points`: one that is not a mapping of retired ids to lists of ids, or one in front matter that does not parse
  - a retired id with no stub, or a stub whose id is not retired
  - a stub whose sentence differs from the one its entry gives, such as "Its content is in points 7 and 16."
  - a live point whose heading uses a retired id
  - a successor that the record neither holds nor retires, or a retired id named as its own successor
- **They warn of, and never fail on:**
  - a duplicate id
  - a gap in the ids, counting retired ones
  - a heading in the Decision that opens with a number or a label in another form, such as `### 16 - Title` or `### 5.1 Title`
- **Each finding names the file and the id,** as `<file>#<id>`. A finding on the shape of `retired-points` is at `<file>:/retired-points`, and its message names the entry's id when the finding is on one entry.
- **Only the field's shape is read** of the front matter, so a project's own fields pass.
- **A record in list form fails nothing,** unless it writes `retired-points`. Its points are a numbered list, or paragraphs that open with a bold number or label, not yet converted to headings. Its numbers move when a point is inserted, so no duplicate or gap in them is read (COR-058 point 9).

## Checking a change's numbering

The numbering check compares each record a change touches with its state where the branch left the default branch (COR-058 point 8). A record's state alone cannot show that a number moved, and validation takes no base. So the numbering check is a command of its own:

```
pkit decisions check-diff [--base <ref>] [--head <rev>] [--json]
```

- **Wire it in** as a line of its own in the project's check gate, beside its other checks of a change. It binds only where the project runs it. It runs whether or not anything is anchored, since citations in prose rest on the numbers too.
  - **Its base** is `--base`, else `$PKIT_CHECK_BASE`, else the default branch the configuration declares (the CLI reference, `repository base`). A pipeline that sets `PKIT_CHECK_BASE` to a pull request's target points this check there too.
  - **Its history:** it reads where the branch left the base, so a pipeline fetches enough history to find that point, such as a full clone.
  - **What it skips:** a record the project receives by sync, which is checked where it is authored, and a record the change removes.
  - **When it runs:** it reads the base as the clone holds it, and fetches nothing. So a change that lands on the base after a run is found only by a later run, such as where the merge is decided.
  - **A record in list form** meets only the warning below, unless the change converts it to point headings. Then each point's id is held to the number or label it showed.
- **It fails on,** for each record the change touches:
  - an id the branch point holds or retires that the head neither holds nor retires: a point dropped without being retired
  - a new id that is not past every id of its series that the branch point holds or retires
  - a point whose text, read without its id, sits at the head only under another id. That is a renumbering, or a retirement whose successor kept the claim.
  - a duplicate id, or a heading in a refused form, that the change added, also in a record with neither point headings nor a list
  - a retired id without its stub, or a stub without its entry
  - a new entry in `retired-points` whose successor is not a live point
  - in a record the change converts from list form, a point whose id differs from the number its numbered item showed
  - a point id or a record id the change takes that another change took on the default branch since the branch left it
- **It warns of, and never fails on:**
  - a point's title found under another id, with its text changed: likely a renumbering with an edit
  - in a record the change converts, a point whose id differs from the bold number or label that opened it
  - a point added to a record in list form, or a new record in list form. The list may stay under the refining rule above, or the record may be converted to point headings by hand first, so every number stays.
- **Each finding names the record and the id,** as `<file>#<id>`, or `<file>` for a record id. The command exits 1 on an error and 0 on warnings alone.
- **It lists, and fails nothing on,** each record accepted at the branch point that the change alters or removes. The list is for whoever judges the edits ("Refining an accepted record" above):
  - each point the head adds, alters or retires, with its title, and each it removes, which also fails. A point is compared without its id, its whitespace folded, so a reflowed point is no change.
  - each of its title, status and supersession fields that changed
  - a change to the text its points stand on: its preamble, its Summary and the Decision's text outside the points. A record with no points is read this way, its Decision being that text.
  - a change to its other text, such as its Context, Rationale or Implications
  - a record in list form at the branch point or at the head, as a whole, since its points are not told apart
  - a record the change removes, or moves where no record at the head pairs with it
  - nothing for a record proposed at the branch point, or one the change adds
- **`--head <rev>`** reads the records of that commit from git objects, instead of the working tree's. Where the ADR folder is, and which records the project receives by sync, come from the working tree either way. **`--json`** prints the findings and the list as one document, for a command that shows the list, such as a landing command.
- **Two changes that take one number:** the first to land keeps it. The other moves its point, or its record, to the next unused number, which the finding names.
  - **No clash:** a point the default branch holds under that id with the change's very text is the change's own work landed, such as a parent branch's. So is a record the default branch holds at the change's own path.
  - **A parent's point edited since** fails, and merging the default branch in clears it.

## Checking what a change lands

The landing check judges what a change's merge would land, and lists what the change makes accepted (COR-066 points 2 and 3). It is a command of its own, apart from the numbering check:

```
pkit decisions check-landing --base <ref> [--head <rev>] [--json]
```

- **What it judges** is the *landing state*: git's merge of the head into the base's tip. It compares each record and rule there with its state at that tip, so one the merge leaves alone lands nothing.
- **What the change cannot move.** The key and the default branch's name are read at the base's tip. Which files the project receives is read at that tip and at the landing state. The working tree is never read, though its copy of the synced-copy test runs.
- **It reports** each record and rule proposed at the landing state and not proposed at the tip. One proposed at both is already on the base, and blocks nothing.
  - **A record** is paired by the numbering check's pairing, so a record moved to another path is not added.
  - **A rule** is judged on its own, however many rules its file holds. A rule moved to another set takes a new id, so it is judged as added.
  - **What it cannot read counts as proposed,** with why. That holds for each of these:
    - a file that is not text
    - front matter that does not parse
    - a status its kind lacks
    - a rule-set file the reader cannot read, or one with no mapping of rules or a key written twice, which counts as one proposal
    - an overlay at the landing state whose ADR folder cannot be read, which counts as one proposal even where the tip's cannot be read either
- **It skips** a record or rule set the project receives by sync, which is judged where it is kept. The synced-copy test tells such a file, not the kind of set, so a method rule set a project authors is judged.
  - **Two readings.** The test is asked of the tip and of the landing state. A file either skips is skipped, and each file they disagree on is reported for the person to see.
  - **A state that cannot tell** skips no capability's file, and the check says why. A manifest that does not read is one such state.
- **The refusal.** `decisions.refuse-proposals` at the base's tip decides whether a reported proposal fails the landing. Only a landing on the default branch can fail, told by the name the run gives its base. Otherwise the check passes and says why.
  - **A doubt counts as the default branch.** A base named by anything but a branch counts, such as a commit or `origin/HEAD`. So does any base while the default branch's declared name does not read.
- **A change to the key** is reported, with its value at each state, and counts once it has landed. On the run whose landing turns it on, the check also lists the proposals the tip holds. They block nothing, and a person settles each.
- **The list** gives, for each record and rule the change makes accepted:
  - each commit that accepted it, with the rest of that commit's work
  - the change's commits before that one that touch anything else, one on a parallel line among them. For a rule, an edit to another rule in its file counts.
  - how its text at the landing state differs from its text at that commit, a record's point by point
- **Only what lands is shown** of a commit's work, so a parent's work the base already holds is not shown again. A commit left with nothing to show stays listed, and says so.
- **A second list** gives each record and rule the tip holds accepted and the branch point does not, where the merge changes it. It shows how it differs at the landing state from the tip.
- **No answer** is never a pass, never an empty list and never the refusal off. The check gives none where it cannot compute what lands, and exits apart from a refusal. A caller holds the merge on it, whatever the key says.

Its options, exits, document and no-answer cases are in [the CLI reference](../cli/README.md#decisions-check-landing---base-ref---head-rev---json). Where a project runs it:

- **Through a merge component,** a component that carries out merges on a person's authority. It runs the check before it merges, after the reviewers have judged the change, and shows the person the list. It does not merge while the check refuses or gives no answer. The backbone's own merge commands are not one.
- **A project without one** has its host require the check, on a pipeline line of its own. The line names the pull request's target by its branch name as base, and its own head as head. It fetches their history first.
  - **With the key off,** only no answer fails that line, so it can be wired before the key is turned on.
  - **Its pass can go stale.** It holds for the tip it ran against. A project that wants no stale pass requires each change to be up to date with its base, or merges through a queue.
- **A direct commit.** A person accepts each record and rule the commit makes accepted before the commit. Whoever commits straight to the default branch then runs the check before the push, and pushes only on a pass. The check's head is the commit, and its base is the fetched default branch. A project may wire a hook for such a push, and the backbone installs none.
- **Never in the check gate.** The check gate, a hook run on every push and the numbering check never run it. So the refusal blocks no push and hides no other check.
- **What meets no refusal.** A merge sent past those places meets neither the refusal nor the list. It may go by the host's own controls, or by a backbone command such as `pkit pull-request land` or the release merge. So does an administrator merge past a host check.
