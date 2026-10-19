---
name: analysis-author
description: Author the software analysis — an actor, a glossary term, a use case, a journey, a quality requirement, a functional requirement, a constraint, or a revalidation record — through `pkit analysis new`, choosing the slug, the area, the actor and the steps, a requirement's kind, what each artefact anchors to (code, decisions) or why an actor, a term or a requirement stays unanchored, and whether a revalidation leaves a record at all. Also build an analysis bottom-up, from its concepts in the glossary to the journeys last, and choose each kind's parts, the structure its template shows, as a project adopts the capability, from a candidate filled with its own example. Composite skill per COR-020, paired with `pkit analysis new`, with one sub-procedure per kind, one for the build order and one for the choice. Use when adopting software-analysis, building or adding to a project's analysis, or recording a revalidation that found something.
metadata:
  wraps_commands:
    - pkit analysis new
    - pkit analysis validate
    - pkit analysis check-numbers
composes:
  - choose-templates.md
  - build-analysis.md
  - actor.md
  - term.md
  - use-case.md
  - journey.md
  - requirement.md
  - revalidation-record.md
gates:
  - COR-005
  - COR-020
  - COR-049
  - COR-050
  - COR-051
reads:
  records:
    - COR-008
  paths:
    - .pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md
    - .pkit/capabilities/software-analysis/decisions/DEC-002-analysis-requirements.md
    - .pkit/capabilities/software-analysis/README.md
    - .pkit/project/config.yaml
---

# Authoring the software analysis

This is the **software-analysis** capability's authoring skill. It covers what a project writes into its analysis, each stamped by `pkit analysis new`:

- an actor, a glossary term, a use case and a journey
- a requirement of each of three kinds
- a revalidation record

It also covers the choice of each kind's parts, which comes first when a project adopts the capability, and the order an analysis is built in. The command owns the file's correctness: its id, its place, the anchors the rule asks for. This skill owns the choices behind it: which slug, which actor, which steps, what the artefact rests on, and whether a revalidation has anything to record (COR-005's skill and command pairing).

The rule is [software-analysis:DEC-001-software-analysis-discipline], and the rule for requirements is [software-analysis:DEC-002-analysis-requirements]. The layout, every field and every command are in `.pkit/capabilities/software-analysis/README.md`.

## Acceptance gate

Verify each record in `gates:` is `accepted`; halt if any is `proposed` or `superseded`.

- **COR-005** — skill and command pairing: every artefact and record here is written through `pkit analysis new`, never by hand.
- **COR-020** — the composite folder form this skill follows.
- **COR-049** — documentation roots: the analysis lives under the internal root, and its location is recorded the first time something is stamped.
- **COR-050** — anchors and friction: the block every artefact carries, and the answers that clear friction.
- **COR-051** — rule sets: the set of the project's own through which `SAN` binds, and the rule each part a project adds names.

## Pick the operation

| You want to | Sub-procedure | Command |
|---|---|---|
| Choose each kind's parts, as you adopt the capability | `choose-templates.md` | `pkit analysis validate --preview`, on a candidate stamped as the kind's sub-procedure says |
| Build an analysis, or an area of it, from its concepts up | `build-analysis.md` | the commands of each kind it walks, in its order |
| Name a role that uses the system, and what it needs | `actor.md` | `pkit analysis new actor <slug>` |
| Pin down a domain word, or rename one | `term.md` | `pkit analysis new term <slug>` |
| Describe one actor's goal and how the system fulfils it | `use-case.md` | `pkit analysis new use-case <slug> --actor <ACT-id>` |
| Describe a path an actor takes across several use cases | `journey.md` | `pkit analysis new journey <slug> --actor <ACT-id> --step <UC-id> …` |
| State what must hold beyond one actor's goal: how well the system behaves, behaviour that holds across use cases, or a limit on the solution | `requirement.md` | `pkit analysis new quality-requirement <slug>`, `functional-requirement <slug>` or `constraint <slug>` |
| Record a revalidation that found something, or was planned | `revalidation-record.md` | `pkit analysis new revalidation <slug> …` |

A kind's parts are chosen before its first artefact or record is written, with `choose-templates.md`. The shipped parts are a starting point the project reviews, never a default it skips (DEC-001 point 1).

For a part of the product not yet described, follow `build-analysis.md`, which builds it from its concepts up (DEC-001 point 12): the glossary and the actors first, the journeys last. Open the matching sub-procedure in this folder and follow it. The framing below applies to all of them.

Judging whether existing artefacts still hold after a change is the capability's `analysis-resolver` agent's work. This skill writes what it, or you, decided.

## Shared framing

### Stamp, never copy

The stamp does what a copied template gets wrong:

- it gives a use case, a journey or a requirement the next free number, on the default branch and in the working tree, a requirement's across its three kinds
- it refuses an actor's or term's id already held
- it puts each artefact in its place, and writes the anchors the rule asks for
- it adds a collection entry where its id sorts
- it records the analysis location the first time

Each part of the body holds its hint, a one-line comment `<!-- pkit:hint … -->` that says what goes there and gives an example. So does each front-matter field you fill: an actor's `needs`, as its one item, a term's `definition`, and a requirement's `statement`, `measure` and `applies-to`.

### Choosing the slug

A slug is a word: a lowercase letter, then lowercase letters, digits and hyphens.

- **An actor's or term's slug is its id for ever** (`ACT-<slug>`, `TERM-<slug>`), and an id is never used again, even after it is withdrawn. Name the role or the word as the domain says it, in the singular: `tester`, `release-manager`, `sandbox`. The display name (`--name`) may change later; the slug may not.
- **A use case's or journey's number is its id**; the slug only names the file. Name the goal, verb first: `run-suite`, `export-report`, `first-run`.
- **A requirement's number is its id** too, one numbering across its three kinds. Name the obligation in a few words: `fast-report`, `client-country`.

### What an artefact anchors to

An anchor says *if this changes, check me*. Anchor what makes the artefact true, and nothing broader:

- **`--path <glob>`** — the code that embodies it: the entry point and the files that do the behaviour, not a whole tree. An anchor matching more than half the tracked files is reported as over-broad, because it would make every change a revalidation.
- **`--record <id>`** — a decision it relies on: an architecture decision, a capability's decision, a project record or a core record. For a use case, that is each record it rests on and each record that answers it. The anchor runs from the analysis only. Records carry no drivers: a record never anchors an analysis artefact, not even the use case it was made to meet, so no cycle runs between the two (DEC-001 point 11).
- **An architecture view** that realises a use case, where the project keeps one: `--path` on the view's file. Where a place holds the view, write an artefact anchor on it instead. A view never anchors the analysis back.
- **The analysis's own artefact anchors are the stamp's.** A use case anchors to its actor and each other actor it involves, and a journey to its actor and to the use cases of its steps and its `relies-on`. Each also anchors to the requirements it lists in `requirements`. A requirement anchors to its `actors` and to the requirements it `refines`. So a changed actor flags its use cases, journeys and requirements. A changed use case flags the journeys that pass through it or rely on it. A changed requirement flags the requirements that refine it, and the use cases and journeys that list it. Never write them by hand.

**Quote the code you describe.** When a use case's step names a command, a flag, a function or a message, write it in backticks. What an artefact quotes from the code it anchors to is how a revalidation tells a change that leaves the description true from one that removes what it says — the resolver agent's first reading of a flagged artefact rests on it.

The code the analysis ought to cover is the project's to declare, as the declared surface in the friction key of `.pkit/project/config.yaml`; what no artefact anchors to there is reported as uncovered surface.

### Name the source of what the system must do

Analysis written first lets an agent invent what the system must do, and everything built after rests on it. So each goal, minimal guarantee and requirement you write names its source, in one of these forms:

- **A record:** an accepted decision record the artefact anchors with `--record`, which decides the item or was made to meet it.
- **A requirement's reason:** its *Rationale*, or a constraint's *Imposed by*, filled rather than `None.`.
- **Existing behaviour:** code the artefact anchors with `--path`, which already does what the item says. Code shows what the system does, never how well, so it sources no value a requirement's `measure` sets.
- **A quoted decision:** the words of the person who decided, quoted in the artefact, with their name and the date. Quote a requirement's in its *Rationale* or *Imposed by*, and a guarantee's beside it. A goal holds one sentence, so quote its decision under a heading of your own after the last part, such as `## Sources`, and name the goal in plain words. The check never reports a heading of your own. Where the project closes the kind's labels, it reports a bold label of your own, so write none there.

A source covers only what it bears out, so a requirement's sources together cover what its `statement` asks and any value its `measure` sets. Nothing else is a source: not the need a goal states, and not a proposed record. A *Rationale* or an *Imposed by* counts once it is filled, so write in it the reason the person who decides or a record gives, never one you supply. Where you find no source, do not write the item. Ask the person who decides, and quote the answer. `SAN`'s `RS-SAN-007` asks the same. While it is proposed, it binds nothing.

### Use the glossary's terms

Each artefact you write uses a concept of the domain only where a term of the glossary defines it, and names the concept by that term's name. A term's definition does the same. `SAN`'s `RS-SAN-008` asks it, and its *How* says what counts. While it is proposed, it binds nothing.

- **No term yet.** Stamp the term first (`term.md`), then use the concept.
- **One name.** Never name a defined concept by another word, a name the term replaces included. Never use a term's name in another meaning, unless the term tells that meaning apart from its own.
- **One term.** Before you stamp a term, check that no term in force defines its concept already.
- **A definition.** It names the concepts it uses by their terms too. It holds no word of its own term's name, so it names a concept whose term's name is such a word in other words.
- **A changed term.** A rename, a withdrawal or a changed definition flags none of the artefacts that use the term, so find and mend them in the same change (`term.md`, "Later").
- **What uses no concept.** An actor's name, an artefact's id, a proper name, the names of the analysis's own kinds and parts, words you quote from a person or a document, and code you quote in backticks.

### An actor, a term or a requirement nothing embodies

An actor, a term or a requirement with nothing to anchor is stamped with `--unanchored-because "<why nothing embodies it>"` instead of anchors. Examples are a sponsor, an outside regulator, a word of the business the software never names, and a requirement a stakeholder states. The stamp writes the reason as `unanchored-because` in the artefact's friction block, the core's key. An unanchored artefact is reported as a measure and never fails a check. The reason is what onboarding accepts, and the core's measure lists the artefact apart with it rather than counting it (`pkit friction check --all`). A use case or a journey is never unanchored: it always rests on its actor, or its steps. A requirement takes the reason only with no anchor at all: no actor, nothing it refines, and no path or record (DEC-002 point 6). The reason is a person's decision, accepted before it is written (COR-050 point 1): an agent following this skill shows the person the reason word for word and stamps only once they accept it.

### After stamping

1. **Fill each part as its hint says.** Write in each hint's place what it asks for, and delete the hint. A part with nothing to say reads `None.`, where its hint says so. Fill an actor's `needs`, a term's `definition`, and a requirement's `statement`, `measure` and `applies-to` the same way. This skill lists no kind's parts: a part's hint is its one description, in the kind's declared structure (DEC-001 point 1).
2. **Check what you wrote** with `pkit analysis validate --preview`, and read its findings on your artefact. Then run `pkit friction check`, the core's change check. An artefact new in a change counts as revalidated, and an anchor that resolves to nothing fails.
   - **Why `--preview`.** It runs the capability's check, with its findings and its exit status. It adds what a proposed rule would report where it would bind, as reports that open `preview:` and never fail. So it shows what you wrote against its kind's structure even while the format rule is proposed. `pkit validate` runs the same check with no preview.
   - **Its structure.** The check holds the body to its kind's structure: each part present, in order, not empty, and of its form. Each message gives the part's hint and example.
     - **A revalidation record** is held to it always, whatever any rule's status: no rule binds on a record, so the capability checks it itself.
     - **An artefact** is held to it where the format rule, `RS-SAN-001`, is accepted and binds. While the rule is proposed, the preview reports what would break where the rule would bind. `SAN` binds only through a rule set of the project's own that inherits it. So an artefact no such set selects is neither checked nor previewed. The check says so: its summary counts those artefacts, and where `SAN` binds on none of the analysis, it reports it, or warns once a rule of `SAN` is accepted. The README's "Where `SAN` binds" says how to write the set.
   - **The project's own parts.** A project may relabel a kind's parts and add its own, in the capability's `project/structures.yaml`, as it chooses them in `choose-templates.md`. The stamp writes them, each added part's hint naming the rule that asks for it. Delete an optional one you have nothing for. The check holds an added part only where its rule binds. The preview places one whose rule is still proposed where the rule would bind, as `pkit rule-sets reach --preview` reads it. A record's kind takes no added part, since no rule binds on a record. The README's "A project's own structures" says how.
3. **Before merging a use case, a journey or a requirement** — `pkit analysis check-numbers`: a number the default branch gave another file since your branch left it is renumbered, and the stamp gives the next free one. It also fails on a use case's step or variant renumbered or removed, which you put back (`use-case.md`, "Later").
4. **Commit** per COR-008, one artefact or one revalidation per commit where you can.

### Withdrawing, never deleting

An artefact is withdrawn, never deleted: set its `status` to `withdrawn` and keep the file or the entry, so that records and journeys citing it still resolve. Its id is never used again. An artefact in force never rests on a withdrawn one — withdraw or re-point the use cases of an actor before withdrawing the actor, or the check refuses them.

The one exception is a pilot abandoned before anything cited it. To clear one so the analysis numbers from `UC-001` again, delete its files in one commit and declare their ids free in the numbering setting (the capability's README, "Configuration"). An entry there is a person's declaration that nothing cites those ids, and the README says what cites an id: an agent following this skill may propose one, showing the ids, where it looked and what it found, and never writes one to make a check pass. Where anything cites them, restore the artefacts as withdrawn instead.
