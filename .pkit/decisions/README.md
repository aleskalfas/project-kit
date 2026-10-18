---
variant: universal
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/decisions.py
        - src/project_kit/decisions_check_diff.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/record_points.py
        - src/project_kit/refs.py
        - src/project_kit/rule_sets.py
      record: [COR-001, COR-019, COR-025, COR-041, "COR-050#2", "COR-050#7", COR-051, COR-053, COR-055, COR-058, "COR-059#3"]
      artefact:
        - .pkit/lifecycle/README.md#the-steps-of-a-transition
        - .pkit/lifecycle/README.md#seed-paths
        - .pkit/lifecycle/README.md#syncs-guard-no-path-down-and-no-migration-passed-over
        - .pkit/lifecycle/README.md#what-sync-writes
    revalidated:
      at: 2026-10-18T15:13:51Z
      outcome: unchanged
      unchanged-because: Points 2 and 7 are reached through the Decision's text outside its points, which gains a sentence on a link that asks for a revisit of its targets (point 16). This page names a record's point by its id as an anchor's value (point 2) and keeps a retired point's id with a stub (point 7), and both read as before.
---

# Decision records

This directory holds your project's architectural-decision record: why each significant choice was made, separately from how it is currently implemented. project-kit installs and maintains the decision-record system here, so you can capture your own decisions in a consistent, reviewable form alongside the methodology decisions project-kit ships.

## Two namespaces, two prefixes

| Directory | Prefix | Owner | Lifecycle |
|---|---|---|---|
| `core/` | **COR** | project-kit | Maintained by project-kit; refreshed on sync; **do not edit** |
| `project/` | **PRJ** | Your project | Yours. project-kit creates the folder where it is missing, as a [seed path](../lifecycle/README.md#seed-paths), and never writes your records |

The two namespaces have **independent numbering**. `core/COR-001` and `project/PRJ-001` are separate decisions about separate things; neither blocks the other.

The distinct prefixes mean a reference like `COR-002` or `PRJ-007` is unambiguous on sight — no need to know the surrounding directory to know which side of the .pkit/project line it belongs to.

### Two further id-spaces

Beyond the two top-level namespaces, decision records also appear in two other places, each its own independently-numbered **id-space**:

| Location | Prefix | Owner | Per |
|---|---|---|---|
| overlay-resolved `<adr-records>` path (default `docs/architecture/decisions/`) | **ADR** | Your project | COR-025 |
| `.pkit/capabilities/<cap>/decisions/` | **DEC** | The capability | (per-capability) |

A capability's **DEC** records are numbered **per capability** — each capability is its own DEC id-space, so two different capabilities may both hold a `DEC-001` without conflict. Only two records sharing a `DEC-NNN` *within the same capability* collide.

`pkit decisions validate` enforces uniqueness within each id-space (core, project, ADR, and per-capability DEC), and of rule ids across the rule sets (below), and is wired into the project's check gate. It reads one tree. So it finds two records with one id only once both are in the tree it checks. A gate that checks a pull request merged with the default branch as it stands at the merge finds them before the second lands. A gate that checks the branch alone finds them only after both landed. The numbering check, `pkit decisions check-diff` (below), compares a change with the default branch. Where your project runs it, it fails a change whose new record takes an id that another change has already landed.

Validation checks your own records only. A record that arrives as a synced copy is a core record, or a kit-shipped capability's, in your project. It is checked where it is authored, since the next sync overwrites an edit here. So is a record of an externally-sourced capability, which your project pulls whole from the source it is pinned to and uses as it arrives ([COR-041](core/COR-041-external-source-distribution.md)). Validation fails a project only for what it can correct in its own files ([COR-055](core/COR-055-validation.md) point 1). So `pkit validate` and `pkit decisions validate` report nothing on such a copy: not its front matter, not its id against its filename, and not an id only copies share. A record of yours that takes a copy's id is still reported, on your record, because the copy keeps its id.

### Rule sets — a separate family with the same guarantees

Rules are not decision records, but they share their guarantees ([COR-051](core/COR-051-rule-sets.md)). A **rule set** is one file holding many one-paragraph rules: the data sits in front matter, and each rule's statement sits in the body, in a section headed by the rule's id. Rules form their own identifier family, **`RS-<SET>-NNN`** — the family prefix, the rule set's name, a number — so a rule id can never collide with a record id. Ids are permanent: a rule is never renumbered, and a retired id is never reused.

- **Statuses.** A rule without a status is **`proposed`** and binds nothing. **`accepted`** rules bind. A **`superseded`** rule names its successor — in the same rule set, or in one that inherits it — and binds nothing. Rules add **`withdrawn`**, which only rules have: a rule retired without a successor, binding nothing. Superseded and withdrawn rules stay in place with their ids.
- **The acceptance gate** applies per rule, wherever the rule set lives. That includes project-owned rule sets outside this folder, under the project's internal documentation root by default. A proposed rule binds nothing, and accepting one is a reviewed change.
- **Origins.** Every accepted rule carries an origin: when it was decided, by whom and why, in the decider's words — or a cited decision record, which must be accepted whenever the rule is.
- **Where rule sets live.** A method rule set ships with its component and is cited with the component's name; a project rule set is the project's, and is cited bare. A project never edits a method rule set: it inherits it, pinning the set's major version.
- **Citing a rule.** `RS-CMN-003` names a rule and `RS-CMN-003#cause-location` an extension point it offers. A method rule set's rules are cited with the component in front — `[living-docs:RS-LDOC-003]` in prose, bracketed like a capability decision citation.
- **Checked by validation.** `pkit validate` checks every rule set — the schema, the join between data and prose, ids, origins, successors and inheritance — and `pkit decisions validate` reports a rule id claimed twice. Where rule-set files live, their front-matter layout and every check are in the schemas reference, "Rule-set files" (`.pkit/schemas/README.md`).

## Citing

Each kind of thing a record, an agent or a skill cites has one written form, and a point of a record has two:

- **A record** by its id: `COR-019`, `PRJ-007`, `ADR-012`. A capability's record goes in brackets with the capability in front: `[project-management:DEC-053-doc-check-slot]`.
- **A point of a record** by the record and the point's id: "COR-050 point 11" in prose, and `COR-050#11` as an anchor's value ([COR-050](core/COR-050-anchors-and-friction.md) point 2). A labelled point is named by its label, as in `COR-033#P3`. A capability's record keeps its brackets in prose, "[project-management:DEC-055] point 3", and drops them in an anchor's value, `project-management:DEC-055#3`. A point written as a heading keeps its id for good, so its citations stay on it (see "Schema" below). A record whose points are still a list holds no point an anchor can name, since its numbers move (COR-050 point 7).
- **A rule** by its rule id, as "Rule sets" above describes: `RS-CMN-003`, `[living-docs:RS-LDOC-003]`.
- **A role or a point of a connection** by its address, in brackets ([COR-019](core/COR-019-schema-reference-form.md), [COR-053](core/COR-053-connection-points.md)): `[pkit::documentation]` names the documentation role and `[pkit::documentation:readers]` its readers point. The double colon marks an address; `[issue-types:task]`, with a single colon, stays a schema reference. An address resolves to what an installed capability declares in its package metadata. `pkit refs validate` reports an address that names no declared role or point, and reports a bracketed token with a double colon that is not an address — `[::documentation:readers]`, with no publisher — as malformed. `pkit refs lookup '[pkit::documentation:readers]'` prints where the point is declared.

## The no-shared-files invariant

Every file has exactly one owner — kit or project — and they never share a path.

This invariant is what makes the namespace split above operationally safe. project-kit's sync operation copies a fixed set of kit-owned paths. There is no conflict UI, no marker comments, no include-with-substitution mechanism.

Sync reads from your side what it needs, such as the versions your project records. It writes into a file of yours only through merge delivery's tier that asks nothing. That tier adds the kit's entries and never removes one you wrote ([the lifecycle README, "What sync writes"](../lifecycle/README.md#what-sync-writes)). Sync **cannot** produce a conflict, and it cannot break anything you wrote.

Sync runs at the versions your project records, and moves none of them ([COR-059](core/COR-059-version-transition.md)). It writes the methodology's content at those versions, the state derived from your own declarations, and your project-owned paths through merge delivery only, and nothing else. It runs no migration, and writes no recorded version, no manifest and no seed path ([the lifecycle README, "What sync writes"](../lifecycle/README.md#what-sync-writes)).

Under a pkit at another version than your project records, or over an unfinished upgrade, sync stops before it writes anything, and its message names the command that gets you on ([the lifecycle README, "Sync's guard"](../lifecycle/README.md#syncs-guard-no-path-down-and-no-migration-passed-over)).

`pkit upgrade` is the command that moves your project to another release. It also creates each seed path that is missing, such as the agents overlay, never over one that exists ([the lifecycle README, "Seed paths"](../lifecycle/README.md#seed-paths)). Every migration runs inside it ([the lifecycle README, "The steps of a transition"](../lifecycle/README.md#the-steps-of-a-transition)), and a migration changes a file of yours only within what the record that owns the file allows.

The same `core/` / `project/` pattern (and the same invariant) governs other kit areas in your project — `.pkit/agents/`, `.pkit/rules/`, and so on. To extend kit-shipped content, add sibling files in the matching `project/` directory; never edit a kit-owned file.

Some files must live at fixed paths that you will want to extend — root `CLAUDE.md` and `.claude/settings.json` are the canonical examples. Each stays yours. The kit ships its canonical content at a separate path, and merge delivery adds what it needs into your file in place (COR-002): the line in `CLAUDE.md` that includes the kit's rules from that path, and the kit's entries in `.claude/settings.json`. It adds only what is missing, and never removes or rewrites what you wrote. The lifecycle that supports this — when files are first written, when they are updated — is detailed in COR-001.

## File naming

`<PREFIX>-NNN-slug.md`, where:

- `<PREFIX>` is `COR` (in `core/`), `PRJ` (in `project/`), `ADR` (architecture records), or `DEC` (a capability's own `decisions/`) — see "Two further id-spaces" above for ADR and DEC.
- `NNN` is a zero-padded serial within the id-space (`001`, `002`, …, `099`, `100`); each prefix numbers independently, and DEC numbering is per-capability.
- `slug` is a kebab-case shorthand of the title — short enough to keep file listings self-documenting, long enough to identify the decision without opening the file.

Examples: `COR-001-init-vs-synced-lifecycle.md` (kit-owned, read-only), `PRJ-001-our-architecture.md` (yours).

## Schema

Each record is a Markdown file with YAML frontmatter and four required sections:

```markdown
---
id: PRJ-NNN          # for your own records; COR records you receive use the COR prefix
title: Short imperative title
status: proposed | accepted | superseded
date: YYYY-MM-DD
author: Name <email>  # primary author (git-style)
supersedes: PRJ-NNN  # optional — same-namespace prefix as the superseded record
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

Larger records may add sub-sections (e.g. *Alternatives considered*, *Migration path*). Those four headings are the contract; everything else is optional.

**Points.** A Decision of several parts writes each part as a *point*: a heading that opens with the point's id, then its title. The id names the point for good ([COR-058](core/COR-058-record-points.md) points 1 and 3). The example's retired point 2 only shows the form. A new record retires nothing.

- **The form:** `### 5. Title` for a numbered point, a number then a full stop and a space. `### D1 — Title` for a labelled one, letters then a number, then a space, an em dash and a space. A record that labels its points keeps its labels.
- **The level:** one below `## Decision`, or one below the group headings that gather the points, as in `#### 11. Title`. The Decision's first heading in this form sets the level, and a heading in this form at another level is no point. A record's points all sit at one level, and their ids are unique across its groups.
- **The text** runs from the heading to the next heading of the same or a higher level.
- **A numbered list stays allowed** inside a point or another sub-section, for steps or an order. Once a record has point headings, every numbered list in it is a list, never points. Its items renumber when an item is inserted.
- **`retired-points`** is optional. It maps each retired id to the list of points that took its text, one id to a line, in the order of the ids, at the top level of the front matter. A point no other point took writes an empty list, `"9": []`.
- **A stub** stays where each retired point was: a heading with its id and the title `Retired`, then one sentence written from its entry. The sentence is "Its content is in point 7.", "Its content is in points 7 and 16.", "Its content is in points 7, 12 and 16." or "Its content is in no other point." It says nothing else, and no live point takes the title `Retired` (COR-058 point 4).

A record whose points are still a numbered list, or paragraphs that open with a bold number or label, is in *list form*. It keeps working. A point inserted into a numbered list moves the numbers after it (COR-058 point 9).

The **`author`** field captures responsibility for the record — git-style `Name <email>` matching the value the author would use as their git commit identity. When multiple users collaborate on a project, this makes per-record authorship explicit at a glance; git history captures the rest (commit author, `Co-Authored-By` trailers). The schema may grow a `co-authors` list if frequent multi-author records earn it.

## Statuses

- **`proposed`** — under discussion. Not binding. **Implementation must not depend on the record's content** — see "The acceptance gate" below.
- **`accepted`** — in effect. Implementation must comply.
- **`superseded`** — replaced by a newer record. The successor sets `supersedes: PRJ-NNN` (or `COR-NNN`) in its frontmatter; the superseded record adds a *Superseded by …* line at the top of its body. The superseded record is preserved as historical material — never deleted.

A record moves only forward through these states: `proposed → accepted → superseded`. There is no `rejected` state — a rejected proposal is deleted before it lands.

Supersession is always within a single namespace.

## The acceptance gate

Implementation work — code, content, tooling, downstream decisions — depends only on **accepted** decisions. Proposed records are draft hypotheses, useful for discussion but not authoritative. Authoring work that would cite a still-proposed record violates the gate; either accept the record first (a one-line status flip and a commit) or pause the implementation.

The gate applies to every kind of dependent work:

- **Decisions** that build on other decisions cite only accepted predecessors.
- **Docs** describing systems built on a decision wait until that decision is accepted.
- **Skills and agents** that automate work depending on a decision verify acceptance before running. The mechanism for declaring and verifying decision dependencies is part of each artifact area's own README (e.g. `.pkit/skills/README.md`, `.pkit/agents/README.md`).

Acceptance is intentionally cheap — flipping `proposed → accepted` is one line and one commit. The friction is not in the flip; it's in the requirement that everyone look at the record and agree before depending on it.

## Refining an accepted record

For clarifications, scope tweaks, or refinements that do not invalidate the original decision: edit the record in place. Git history is the change log — the spec does not duplicate it inside the record itself. For changes that overturn the original, write a new superseding record instead.

**Editing in place means editing in place.** A correction is folded into the body so the record simply states what is true; it is not appended as an amendment section, a dated correction marker, or a "previously we believed" passage. Those turn a record into a changelog with a statement buried in it, and each one looks like diligence, so the habit spreads by imitation. If a record was wrong about a fact and the decision has not changed, fix the sentence. If the decision changed, supersede.

To refine a record in place:

1. **Rewrite the section the change belongs to** — the decision point, the rationale paragraph, the implication — so it states the corrected fact as part of the decision. A new point goes where it belongs among the others, not at the end of the record.
   - **In a record whose points are headings,** the new point takes the next unused number: one past the highest the record holds, retired ids included. A label carries its number, so a record labelled up to D5 goes on with D6, and numbers and each series of labels count apart. No point is renumbered, and no id is reused, so the numbers may read out of order, such as 4, 16, 5. A point you amend or move keeps its id ([COR-058](core/COR-058-record-points.md) point 3).
   - **In a record in list form,** the new point goes where it belongs. In a numbered list, the numbers after it move (COR-058 point 9).
2. **Keep the id of a point no other point continues.** This applies in a record whose points are headings. A point is retired when no point continues its claim. Its id goes into `retired-points`, with the points that took its text, and a one-line stub stays where it was ("Schema" above) (COR-058 point 4).
   - **A dropped point** is retired with no successor.
   - **A split point:** where one part keeps the claim, that part keeps the id, and each other part is a new point with the next unused number. Where no part keeps it, the id is retired, with the new points as its successors.
   - **A merge:** the point that keeps the claim keeps its id. The other is retired, with that point as its successor.
   - **A successor retired later** gets a line of its own. The earlier line and its stub stay as they are.
   - **A point another record overturns** is not retired. It stays as it stood, and the record's top line reads *Partially superseded by …* (COR-058 point 5, and "To supersede" below).
   - **In a record in list form,** a dropped point goes, and in a numbered list the numbers after it move. Nothing is retired there, since its numbers are not permanent (COR-058 point 9).
3. **Add no revision marker** — no amendment heading, no block stamped with a date or an issue number, no note that the record was amended in place rather than superseded.
4. **Leave no residue of the change.** A word that makes sense only against the old text — "now", "no longer", "still", "corrected above" — is restated as plain fact. An issue number in a record cites evidence; it never dates a revision. A `retired-points` entry and its stub are data, not residue: they say where a point's content went, never when or why.
5. **Check the rest of the record agrees** — the summary, the Context, and any other sentence that restates the fact.

The commit message says what changed and why.

**To supersede**, write a new record that sets `supersedes:` to the old record's id. In the old record, set `status: superseded`, put a *Superseded by …* line at the top of its body, and leave the rest of the body as it stood; if it is an ADR, also set `superseded_by:` in its front matter (the ADR schema in COR-025). A record that a later one overturns only in part stays `accepted`, and its top line reads *Partially superseded by …* instead — that line is its superseded-by line. The later record sets no `supersedes:` for the earlier record, since that field names only a record the later one replaces whole.

Two in-body markers are *not* narration of a revision and are correct to keep: the **superseded-by** line, whole or partial, and a **forward refinement pointer** naming a later record that extends this one — `(refinement per <record>)` on the sub-section heading, decision point or sentence it extends. Both point at another record rather than at a discarded belief.

`pkit decisions validate` warns of each line of a record that narrates its own revision — an amendment heading or marker (`## Amendment (…)`, `**Amendment 1**`, `**Amended by …**`), a revision stamped with an issue number or a date (`**Update (#252)**`, `(clarified, #813)`), or change-log phrasing ("this record originally…", "previously we believed…") — naming the file and line. It does not read fenced blocks or inline code spans, a superseded record, or a record that arrives as a copy — a core record, or a kit-shipped or externally-sourced capability's, in your project — since that record is refined where it is authored, not here. The two markers above match none of these shapes. The warnings do not fail the command, because the shapes are read from prose and a gate that fails on a heuristic reading of prose fails for the wrong reasons — the reason [COR-055](core/COR-055-validation.md) gives for letting one severity alone fail validation ("Why exactly one fails").

## Checking a record's points

A record's points keep their ids for good ([COR-058](core/COR-058-record-points.md)). A point is a heading in the Decision that opens with its id, `### 5. Title` or `### D1 — Title`. A retired point keeps its id in the record's `retired-points`, with the points that took its text, and a one-line stub stays where it was. `pkit validate` and `pkit decisions validate` check each record's points, as COR-058 point 7 sets out. They read the records the narration warnings read, so a superseded record and a synced copy are left out.

- **They fail on:**
  - a malformed `retired-points`: one that is not a mapping of retired ids to lists of ids, or that sits in front matter that does not parse
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

A renumbered point misleads every citation of it, and a record's state alone cannot show that a number moved. `pkit decisions check-diff` compares each record a change touches with its state where the change's branch left the default branch, as COR-058 point 8 sets out. Validation takes no base, so this check is a command of its own.

- **Wire it in** as a line of its own in your project's check gate, beside your other checks of a change, such as `pkit migrations check-diff`. It binds only where your project runs it. It runs whether or not anything is anchored, since citations in prose rest on the numbers too.
  - **Its base** is `--base`, else `$PKIT_CHECK_BASE`, else the default branch your configuration declares. `pkit repository base` shows it. A pipeline that sets `PKIT_CHECK_BASE` to a pull request's target points this check there too.
  - **Its history:** it reads where the branch left the base, so a pipeline fetches enough history to find that point, such as a full clone.
  - **What it skips:** a record your project receives by sync, which is checked where it is authored, and a record the change removes.
  - **A record in list form** meets only the warning below, unless the change converts it to point headings. Then each point's id is held to the number or label it showed.
- **It fails on,** for each record the change touches:
  - an id the branch point holds or retires that the head neither holds nor retires: a point dropped without being retired
  - a new id that is not past every id of its series that the branch point holds or retires
  - a point whose text, read without its id, sits at the head only under another id: a renumbering, or a retirement whose successor kept the claim
  - a duplicate id, or a heading in a refused form, that the change added, also in a record with neither point headings nor a list
  - a retired id without its stub, or a stub without its entry
  - a new entry in `retired-points` whose successor is not a live point
  - in a record the change converts from list form, a point whose id differs from the number its numbered item showed
  - a point id the change takes that another change took on the default branch since the branch left it, and a record id the same way
- **It warns of, and never fails on:**
  - a point's title found under another id, with its text changed: likely a renumbering with an edit
  - in a record the change converts, a point whose id differs from the bold number or label that opened it
  - a point added to a record in list form, or a new record in list form. You may keep the list under the refining rule above, or convert the record to point headings by hand first, so every number stays.
- **Each finding names the record and the id,** as `<file>#<id>`, or `<file>` for a record id. The command exits 1 on an error and 0 on warnings alone.
- **Two changes that take one number:** the first to land keeps it. The other moves its point, or its record, to the next unused number, which the finding names. A point the default branch holds under that id with the change's very text, or a record it holds at the change's own path, is the change's own work landed, such as a parent branch's, and is no clash. A parent's point edited since fails, and merging the default branch in clears it.

## Adding a record

You add records to `project/` — your own architectural decisions, in your own namespace.

The recommended path is the kit's authoring command (specified in `.pkit/cli/README.md`):

```
pkit new decision project <slug>
```

This stamps `PRJ-NNN-slug.md` with the schema's frontmatter, the four section headers and a first point heading, `### 1. Point title`, under `## Decision`. You fill in the body and flip status to `accepted` once agreed.

The stamped heading puts the record's points in the heading form from the start ("Schema" above):

- **Its level is the points' level.** To gather points under group headings, move it one level down, below the first group heading.
- **A numbered list you write beside it** is a list, never points.
- **A decision with no parts** has no points. Delete the heading before the record first lands. A point dropped after that is retired, with a stub ("Refining an accepted record" above).

The same command stamps the other id-spaces by passing a different namespace: `core` (COR), `adr` (ADR, at the overlay-resolved path), or a **capability name** (DEC, under `.pkit/capabilities/<capability>/decisions/`, numbered per capability). The capability must already exist; the command refuses an unknown name.

If you prefer to author by hand, the procedure is:

1. Pick the next available number in `project/`. `pkit new decision` numbers a record for you. A number picked by hand can be one another change has landed on the default branch since your branch left it. `pkit decisions check-diff` finds that ("Checking a change's numbering" above).
2. Create `PRJ-NNN-slug.md` with the frontmatter and the four sections above. Leave out the example's `retired-points` and its stub, and number your points from 1 with no gap.
3. Open it as `proposed` if it is still under discussion, `accepted` once agreed.

The directory listing in `project/` serves as the index — file names carry their slugs, and most projects' corpora are small enough that no separate index is needed. If yours grows numerous, a `README.md` index can be added inside `project/` as a convenience.

Records in `core/` are managed by project-kit. **Do not edit them** — they are refreshed on every sync, and your edits would be overwritten. To propose a change to the methodology itself (a new core record, a refinement of an existing one, or a supersession), contribute to project-kit upstream.

## Why this shape

A few choices in the system above are deliberate:

**Markdown, not a structured store.** Records are read by humans and AI agents alike. Both want plain text in a versioned repo.

**Two distinct prefixes (COR/PRJ), not a shared one.** A shared prefix would force you either to coordinate numbering with the kit or to live with collisions. Distinct prefixes make ownership self-evident at every reference and let each side number from 1 independently.

**Four required sections, not more.** Context, Decision, Rationale, Implications cover what every reader needs. Larger records can add sub-sections without those becoming mandatory in small ones.

**Conflicts impossible, not resolvable.** project-kit makes file-conflict scenarios structurally unreachable rather than introducing a UX to resolve them. Sync never asks "what do I do now?".
