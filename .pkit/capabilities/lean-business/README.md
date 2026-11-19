---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/lean-business/package.yaml
        - .pkit/capabilities/lean-business/scripts/check.py
        - .pkit/capabilities/lean-business/scripts/_lib/*.py
        - .pkit/capabilities/lean-business/schemas/*.schema.json
      record:
        - lean-business:DEC-001#1
        - lean-business:DEC-001#5
        - lean-business:DEC-001#6
        - lean-business:DEC-001#8
        - lean-business:DEC-002#1
        - lean-business:DEC-002#2
        - lean-business:DEC-002#7
        - lean-business:DEC-002#13
        - lean-business:DEC-002#14
      artefact:
        - .pkit/cli/README.md#validate
---

# lean-business capability

lean-business guides a person through the lean method of validating a business model, as Ash Maurya's *Running Lean* (third edition, 2022) teaches it. An idea is sketched as canvases, one for each variant of its business model. The person judges each variant at the desk, for desirability, viability and feasibility, and shortlists the ones worth testing. Then they test the riskiest assumptions in short experiments, declared before they run, inside time-boxed cycles that end in a decision to persevere, pivot or pause. The capability keeps the record of all this as data, works out what follows from it, and leaves every judgement to the person. Install it in any repository where you want to decide what is worth building before building it: a product's own repository, or one kept only for exploring ideas.

"Lean business" here means validating a business model, not running a business at low cost.

## What this capability ships

- `decisions/` — the principles the capability fixes:
  - [lean-business:DEC-001-lean-business-discipline]: what it carries, its words, its seams with other capabilities, and how it credits the method.
  - [lean-business:DEC-002-lean-business-data-model]: an idea as a folder of data files that hold only what a person wrote or decided.
  - [lean-business:DEC-003-lean-business-process]: the processes of a variant, an experiment and a cycle, and why each judgement is the person's.

- `schemas/` — the shape of each file of an idea and of the capability's configuration, each with its reference instance ([lean-business:DEC-002-lean-business-data-model]; "An idea's folder" below). `shapes.schema.json` holds the shapes they share: the ids, the references, a day, a person and a fingerprint.
- `scripts/check.py` — the capability's check, `pkit lean check`, and the `lean-business:check` member of `pkit validate` ("The check" below).
- `scripts/_lib/` — what the check reads through, which the commands are to share: the canonical form and the fingerprints taken over it (`fingerprint`), where a window and a time box fall under a cycle's suspensions (`timeline`), the rules a suspension keeps (`suspensions`), and what follows from the files, such as pricing and an experiment's pass or fail (`readings`).

The process definitions, the other commands and the skill these records decide are being built under project-kit#3426. This README lists them as they land.

## Adopter setup

Install:

```
pkit capabilities install lean-business
```

The ideas live in `lean-business/` at the repository's root, one folder per idea. The first command that writes an idea records that location in the capability's own configuration, `.pkit/capabilities/lean-business/project/config.yaml`. To keep the ideas elsewhere, record another location before the first idea ([lean-business:DEC-002-lean-business-data-model] point 1). An idea's data is as private as the repository that holds it.

## An idea's folder

Each idea is a folder of the location, named by the idea's id. Each file names its schema in `pkit_schema`:

```
<location>/<idea>/goal.yaml                            lean-business:goal
<location>/<idea>/variants/<variant>/canvas.yaml       lean-business:canvas
<location>/<idea>/variants/<variant>/assumptions.yaml  lean-business:assumptions
<location>/<idea>/experiments/<experiment>.yaml        lean-business:experiment
<location>/<idea>/cycles/<cycle>.yaml                  lean-business:cycle
```

- **The goal** is the idea's revenue goal over a number of years, against which its variants' viability and feasibility are judged.
- **A canvas** is one variant of the business model: its archetype, its sides where it serves more than one, its twelve boxes, the inputs of its viability, its traction target, the person's verdict on each step at the desk, and its outcome, shortlisted, shelved or split.
- **The assumptions** of a variant are its risks, ranked, each from an entry of its canvas or an input of its viability.
- **An experiment** tests one assumption, inside one cycle. It is declared before it runs, and frozen once declared; its result and the person's decision are recorded after.
- **A cycle** explores one or more shortlisted variants over a window, 90 days by default, toward an objective. Its suspensions move where the window falls, and its review records the person's decision.

A subject's id is qualified by what holds it: an idea's own subjects by the idea, such as `board-game.direct` for a variant, and a canvas's entries and a variant's assumptions by the variant, such as `board-game.direct.planning-takes-long`. A file refers to another's subject as `[canvas:<id>]`, `[assumptions:<id>]`, `[experiment:<id>]` or `[cycle:<id>]`, and never to another idea's. Each judgement the person made over content keeps a fingerprint of that content, so a later change of it shows ([lean-business:DEC-002-lean-business-data-model] points 7 and 13).

The capability's configuration, `.pkit/capabilities/lean-business/project/config.yaml`, is bound to `lean-business:config` and records the location.

## The check

`pkit lean check` reads the files of the location as they stand, never today's date, and is the `lean-business:check` member of `pkit validate`. An invariant the capability's records own, broken by a command or by a hand edit, is an error, the one severity that fails validation. A guideline of the book, or a judgement gone stale, is a warning. A guideline's ranges count only a box that holds entries, so a first sketch with blanks draws none ([lean-business:DEC-002-lean-business-data-model] point 14).

Each finding carries a label:

| Label | Severity | What it finds |
|---|---|---|
| `location` | error | The configuration cannot be read, or records a location that is refused, such as the repository's top, a folder under `.pkit/` or a hidden one, or one reached through a link. |
| `layout` | error | A file of the capability's where an idea's folder has no place for it, a folder named by no id, or a variant's assumptions without its canvas. |
| `unreadable` | error | A file of the layout that cannot be read as YAML. |
| `binding` | error | A file at a place of the layout that names another schema, or none. |
| `id` | error | An id that does not match the file's place, or is not qualified by what holds it. |
| `duplicate-id` | error | An id given twice for one kind of subject. |
| `reference` | error | A reference that names nothing, or a subject of another idea. |
| `fingerprint` | error | A fingerprint of a canonical form the capability does not know. |
| `sides` | error | A direct model that names sides, a side named that the canvas does not name, or viability inputs given for no side or twice for one. |
| `verdicts` | error | A verdict on a step without a yes on each step before it, or a shortlisting without a yes on all three. |
| `split` | error | A variant split into one that does not name it as the variant it comes from. |
| `declaration-changed` | error | A declared experiment whose declared fields changed since. |
| `declaration-refused` | error | A declaration its gate refuses: a field its kind needs missing, no estimate, a time box over 14 days or ending before it starts, a start before the day it was declared, a declaration after its cycle's window ended, or one on a variant shelved or split before it, or resting on a shortlisting recorded after it. |
| `undeclared` | error | A stopping rule reached, a result or a decision recorded on an experiment never declared. |
| `decision-refused` | error | A decision without a result, a result recorded after its decision, or a decision before its time box ended, under its cycle's suspensions, without a generative experiment's stopping rule reached. |
| `cycle-variants` | error | An experiment on an assumption of a variant its cycle does not explore, a key result that names a variant the cycle does not explore, or an explored variant without a key result. |
| `plan-changed` | error | A cycle whose plan changed since its fingerprint was taken. |
| `one-cycle` | error | Two undecided cycles of one idea, or two whose windows overlap, as worked out. |
| `suspension` | error | A suspension that breaks its rules: its first day outside the window, a day ahead of the day it was recorded, a resumption before its first day, a covered day that holds another act, or two suspensions that overlap. |
| `review-refused` | error | A review its gate refuses: a winning variant the cycle did not explore, a count of what was reached that differs from the key results, a persevere or a pivot for a variant shelved or split before it, a pivot on no decided experiment, or a review before the window ended. |
| `goal-changed` | error | The goal set while one of the idea's cycles was planned, running or suspended. |
| `stale` | warning | A verdict on a variant with no outcome, or a shortlisting, whose content changed since. |
| `guideline` | warning | More than three problems for a side, fewer than three or more than five key metrics, a headline over about 120 characters, or no revenue stream once desirability has a yes. |
| `link` | warning | A problem with no existing alternative, a solution or a value proposition with no problem, an early adopter with no trigger, or a key metric with no step, or one that names an entry its box does not hold. |
| `sides-incomplete` | warning | A model with several sides that names fewer than two, or an entry or a set of inputs that names no side. |
| `assumption-source` | warning | An assumption no declared experiment tests, whose entry its canvas no longer holds. |
| `time-box` | warning | An experiment's time box that does not lie within its cycle's window, as worked out. |
| `persevere-missed` | warning | A review that perseveres with a winning variant that missed the objective. |

## Commands

The commands run as `pkit lean-business <command>`, or `pkit lean <command>` for short.

### `pkit lean check`

Checks the files of the location, as "The check" above says.

- **Reads** the location the capability's configuration records, or `lean-business/` while none is recorded. A location whose folder does not exist yet holds no idea.
- **Prints** a summary, then each finding with its severity, its place and its label: a file relative to the project root, with `#` and a JSON Pointer where it lies within the file. `--json` prints the findings document `pkit validate` reads, `{"summary": [...], "findings": [...]}`, each finding with its `severity`, `location`, `message` and `label`, the errors first.
- **Writes** nothing, and runs offline.
- **Exits** 1 when a finding is an error; 0 otherwise. With `--json` it always exits 0, as `pkit validate` requires.

## Credits and licence

The method is Ash Maurya's, from *Running Lean: Iterate from Plan A to a Plan That Works*, third edition (O'Reilly, 2022). The capability carries the method in its own words and ships no text of the book.

The canvas follows the Lean Canvas, Ash Maurya's adaptation of Alex Osterwalder's Business Model Canvas, both published under the Creative Commons Attribution-ShareAlike 3.0 licence. The capability uses the names of the canvas's boxes as its fields, describes them in its own words, and ships no file under that licence. Wherever it draws a canvas, it draws it with the credit and licence line beneath ([lean-business:DEC-001-lean-business-discipline]).

The names *Running Lean* and *Lean Canvas* may be trademarks of their owners. They are used here only to credit the source.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[lean-business:DEC-001-lean-business-discipline]`. Other capabilities and adopter content use the same form.

## Dependencies

None beyond the backbone. The capability reads no other capability. A later view may read its status's structured form, and the experiments' results may cite evidence records, without either becoming a dependency ([lean-business:DEC-001-lean-business-discipline]).
