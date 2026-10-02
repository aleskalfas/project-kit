---
variant: universal
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/decisions.py
        - src/project_kit/decisions_validate.py
        - src/project_kit/refs.py
        - src/project_kit/rule_sets.py
      record: [COR-001, COR-019, COR-025, COR-051, COR-053]
    revalidated:
      at: 2026-10-02T02:38:09Z
      outcome: unchanged
      unchanged-because: "the page says ADRs stamp at the overlay-resolved path, which still holds: with adr-records unset the command now records the derived path in the overlay before stamping there; the stub shape, numbering and namespaces this page describes are unchanged, and the CLI reference carries the derivation"
---

# Decision records

This directory holds your project's architectural-decision record: why each significant choice was made, separately from how it is currently implemented. project-kit installs and maintains the decision-record system here, so you can capture your own decisions in a consistent, reviewable form alongside the methodology decisions project-kit ships.

## Two namespaces, two prefixes

| Directory | Prefix | Owner | Lifecycle |
|---|---|---|---|
| `core/` | **COR** | project-kit | Maintained by project-kit; refreshed on sync; **do not edit** |
| `project/` | **PRJ** | Your project | Yours. project-kit never touches it |

The two namespaces have **independent numbering**. `core/COR-001` and `project/PRJ-001` are separate decisions about separate things; neither blocks the other.

The distinct prefixes mean a reference like `COR-002` or `PRJ-007` is unambiguous on sight — no need to know the surrounding directory to know which side of the .pkit/project line it belongs to.

### Two further id-spaces

Beyond the two top-level namespaces, decision records also appear in two other places, each its own independently-numbered **id-space**:

| Location | Prefix | Owner | Per |
|---|---|---|---|
| overlay-resolved `<adr-records>` path (default `docs/architecture/decisions/`) | **ADR** | Your project | COR-025 |
| `.pkit/capabilities/<cap>/decisions/` | **DEC** | The capability | (per-capability) |

A capability's **DEC** records are numbered **per capability** — each capability is its own DEC id-space, so two different capabilities may both hold a `DEC-001` without conflict. Only two records sharing a `DEC-NNN` *within the same capability* collide.

`pkit decisions validate` enforces uniqueness within each id-space (core, project, ADR, and per-capability DEC), and of rule ids across the rule sets (below), and is wired into the project's check gate — it catches two records hand-authored with the same id before they land.

### Rule sets — a separate family with the same guarantees

Rules are not decision records, but they share their guarantees ([COR-051](core/COR-051-rule-sets.md)). A **rule set** is one file holding many one-paragraph rules: the data sits in front matter, and each rule's statement sits in the body, in a section headed by the rule's id. Rules form their own identifier family, **`RS-<SET>-NNN`** — the family prefix, the rule set's name, a number — so a rule id can never collide with a record id. Ids are permanent: a rule is never renumbered, and a retired id is never reused.

- **Statuses.** A rule without a status is **`proposed`** and binds nothing. **`accepted`** rules bind. A **`superseded`** rule names its successor — in the same rule set, or in one that inherits it — and binds nothing. Rules add **`withdrawn`**, which only rules have: a rule retired without a successor, binding nothing. Superseded and withdrawn rules stay in place with their ids.
- **The acceptance gate** applies per rule, wherever the rule set lives. That includes project-owned rule sets outside this folder, under the project's internal documentation root by default. A proposed rule binds nothing, and accepting one is a reviewed change.
- **Origins.** Every accepted rule carries an origin: when it was decided, by whom and why, in the decider's words — or a cited decision record, which must be accepted whenever the rule is.
- **Where rule sets live.** A method rule set ships with its component and is cited with the component's name; a project rule set is the project's, and is cited bare. A project never edits a method rule set: it inherits it, pinning the set's major version.
- **Citing a rule.** `RS-CMN-003` names a rule and `RS-CMN-003#cause-location` an extension point it offers. A method rule set's rules are cited with the component in front — `[living-docs:RS-LDOC-003]` in prose, bracketed like a capability decision citation.
- **Checked by validation.** `pkit validate` checks every rule set — the schema, the join between data and prose, ids, origins, successors and inheritance — and `pkit decisions validate` reports a rule id claimed twice. Where rule-set files live, their front-matter layout and every check are in the schemas reference, "Rule-set files" (`.pkit/schemas/README.md`).

## Citing

Each kind of thing a record, an agent or a skill cites has one written form:

- **A record** by its id: `COR-019`, `PRJ-007`, `ADR-012`. A capability's record goes in brackets with the capability in front: `[project-management:DEC-053-doc-check-slot]`.
- **A rule** by its rule id, as "Rule sets" above describes: `RS-CMN-003`, `[living-docs:RS-LDOC-003]`.
- **A role or a point of a connection** by its address, in brackets ([COR-019](core/COR-019-schema-reference-form.md), [COR-053](core/COR-053-connection-points.md)): `[pkit::documentation]` names the documentation role and `[pkit::documentation:readers]` its readers point. The double colon marks an address; `[issue-types:task]`, with a single colon, stays a schema reference. An address resolves to what an installed capability declares in its package metadata. `pkit refs validate` reports an address that names no declared role or point, and reports a bracketed token with a double colon that is not an address — `[::documentation:readers]`, with no publisher — as malformed. `pkit refs lookup '[pkit::documentation:readers]'` prints where the point is declared.

## The no-shared-files invariant

Every file has exactly one owner — kit or project — and they never share a path.

This invariant is what makes the namespace split above operationally safe. project-kit's sync operation works on a fixed set of kit-owned paths; project-owned paths are never read or written by sync. There is no merge logic, no conflict UI, no marker comments, no include-with-substitution mechanism.

Sync **cannot** produce a conflict. You can run it whenever you like — it cannot break anything you wrote.

The same `core/` / `project/` pattern (and the same invariant) governs other kit areas in your project — `.pkit/agents/`, `.pkit/rules/`, and so on. To extend kit-shipped content, add sibling files in the matching `project/` directory; never edit a kit-owned file.

Some files must live at fixed paths that you will want to extend — root `CLAUDE.md` is the canonical example. The invariant rules out editing such files in place to add kit content; the resolution is to keep the fixed-path file project-owned and ship the kit's canonical content at a separate path that the project's file references. The lifecycle that supports this — when files are first written, when they are updated — is detailed in COR-001.

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
---

## Context

What situation or question prompted this decision?

## Decision

What was decided. Single sentence ideally; complex decisions may use a numbered list (1., 2., …) but the top line stays crisp.

## Rationale

Why this choice over the alternatives? What goes wrong with a different choice?

## Implications

What does this mean for the code, the tests, the workflow, downstream decisions?
```

Larger records may add sub-sections (e.g. *Alternatives considered*, *Migration path*). Those four headings are the contract; everything else is optional.

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
2. **Add no revision marker** — no amendment heading, no block stamped with a date or an issue number, no note that the record was amended in place rather than superseded.
3. **Leave no residue of the change.** A word that makes sense only against the old text — "now", "no longer", "still", "corrected above" — is restated as plain fact. An issue number in a record cites evidence; it never dates a revision.
4. **Check the rest of the record agrees** — the summary, the Context, and any other sentence that restates the fact.

The commit message says what changed and why.

**To supersede**, write a new record that sets `supersedes:` to the old record's id. In the old record, set `status: superseded`, put a *Superseded by …* line at the top of its body, and leave the rest of the body as it stood; if it is an ADR, also set `superseded_by:` in its front matter (the ADR schema in COR-025). A record that a later one overturns only in part stays `accepted`, and its top line reads *Partially superseded by …* instead — that line is its superseded-by line.

Two in-body markers are *not* narration of a revision and are correct to keep: the **superseded-by** line, whole or partial, and a **forward refinement pointer** naming a later record that extends this one — `(refinement per <record>)` on the sub-section heading, decision point or sentence it extends. Both point at another record rather than at a discarded belief.

`pkit decisions validate` warns of each line of a record that narrates its own revision — an amendment heading or marker (`## Amendment (…)`, `**Amendment 1**`, `**Amended by …**`), a revision stamped with an issue number or a date (`**Update (#252)**`, `(clarified, #813)`), or change-log phrasing ("this record originally…", "previously we believed…") — naming the file and line. It does not read fenced blocks or inline code spans, a superseded record, or a record that arrives as a synced copy — a core record, or a kit-shipped capability's, in your project — since that record is refined where it is authored and an edit here is overwritten by the next sync. The two markers above match none of these shapes. The warnings do not fail the command, because the shapes are read from prose and a gate that fails on a heuristic reading of prose fails for the wrong reasons (ADR-058).

## Adding a record

You add records to `project/` — your own architectural decisions, in your own namespace.

The recommended path is the kit's authoring command (specified in `.pkit/cli/README.md`):

```
pkit new decision project <slug>
```

This stamps `PRJ-NNN-slug.md` with the schema's frontmatter and four section headers; you fill in the body and flip status to `accepted` once agreed.

The same command stamps the other id-spaces by passing a different namespace: `core` (COR), `adr` (ADR, at the overlay-resolved path), or a **capability name** (DEC, under `.pkit/capabilities/<capability>/decisions/`, numbered per capability). The capability must already exist; the command refuses an unknown name.

If you prefer to author by hand, the procedure is:

1. Pick the next available number in `project/`.
2. Create `PRJ-NNN-slug.md` with the frontmatter and the four sections above.
3. Open it as `proposed` if it is still under discussion, `accepted` once agreed.

The directory listing in `project/` serves as the index — file names carry their slugs, and most projects' corpora are small enough that no separate index is needed. If yours grows numerous, a `README.md` index can be added inside `project/` as a convenience.

Records in `core/` are managed by project-kit. **Do not edit them** — they are refreshed on every sync, and your edits would be overwritten. To propose a change to the methodology itself (a new core record, a refinement of an existing one, or a supersession), contribute to project-kit upstream.

## Why this shape

A few choices in the system above are deliberate:

**Markdown, not a structured store.** Records are read by humans and AI agents alike. Both want plain text in a versioned repo.

**Two distinct prefixes (COR/PRJ), not a shared one.** A shared prefix would force you either to coordinate numbering with the kit or to live with collisions. Distinct prefixes make ownership self-evident at every reference and let each side number from 1 independently.

**Four required sections, not more.** Context, Decision, Rationale, Implications cover what every reader needs. Larger records can add sub-sections without those becoming mandatory in small ones.

**Conflicts impossible, not resolvable.** project-kit makes file-conflict scenarios structurally unreachable rather than introducing a UX to resolve them. Sync never asks "what do I do now?".
