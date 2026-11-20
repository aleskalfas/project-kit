---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/lean-business/package.yaml
        - .pkit/capabilities/lean-business/scripts/check.py
        - .pkit/capabilities/lean-business/scripts/set_location.py
        - .pkit/capabilities/lean-business/scripts/set_goal.py
        - .pkit/capabilities/lean-business/scripts/new_variant.py
        - .pkit/capabilities/lean-business/scripts/set_archetype.py
        - .pkit/capabilities/lean-business/scripts/set_authors.py
        - .pkit/capabilities/lean-business/scripts/add_side.py
        - .pkit/capabilities/lean-business/scripts/remove_side.py
        - .pkit/capabilities/lean-business/scripts/add_entry.py
        - .pkit/capabilities/lean-business/scripts/edit_entry.py
        - .pkit/capabilities/lean-business/scripts/remove_entry.py
        - .pkit/capabilities/lean-business/scripts/move_entry.py
        - .pkit/capabilities/lean-business/scripts/set_inputs.py
        - .pkit/capabilities/lean-business/scripts/set_traction.py
        - .pkit/capabilities/lean-business/scripts/judge.py
        - .pkit/capabilities/lean-business/scripts/shortlist.py
        - .pkit/capabilities/lean-business/scripts/shelve.py
        - .pkit/capabilities/lean-business/scripts/split.py
        - .pkit/capabilities/lean-business/scripts/canvas.py
        - .pkit/capabilities/lean-business/scripts/estimate.py
        - .pkit/capabilities/lean-business/scripts/status.py
        - .pkit/capabilities/lean-business/scripts/add_assumption.py
        - .pkit/capabilities/lean-business/scripts/edit_assumption.py
        - .pkit/capabilities/lean-business/scripts/remove_assumption.py
        - .pkit/capabilities/lean-business/scripts/rank.py
        - .pkit/capabilities/lean-business/scripts/plan_cycle.py
        - .pkit/capabilities/lean-business/scripts/change_plan.py
        - .pkit/capabilities/lean-business/scripts/new_experiment.py
        - .pkit/capabilities/lean-business/scripts/draft_experiment.py
        - .pkit/capabilities/lean-business/scripts/remove_experiment.py
        - .pkit/capabilities/lean-business/scripts/record_estimate.py
        - .pkit/capabilities/lean-business/scripts/declare.py
        - .pkit/capabilities/lean-business/scripts/reach_stopping_rule.py
        - .pkit/capabilities/lean-business/scripts/record_result.py
        - .pkit/capabilities/lean-business/scripts/decide.py
        - .pkit/capabilities/lean-business/scripts/_lib/*.py
        - .pkit/capabilities/lean-business/schemas/*.schema.json
      record:
        - lean-business:DEC-001#1
        - lean-business:DEC-001#3
        - lean-business:DEC-001#5
        - lean-business:DEC-001#6
        - lean-business:DEC-001#8
        - lean-business:DEC-001#10
        - lean-business:DEC-002#1
        - lean-business:DEC-002#2
        - lean-business:DEC-002#3
        - lean-business:DEC-002#4
        - lean-business:DEC-002#5
        - lean-business:DEC-002#6
        - lean-business:DEC-002#7
        - lean-business:DEC-002#8
        - lean-business:DEC-002#9
        - lean-business:DEC-002#10
        - lean-business:DEC-002#11
        - lean-business:DEC-002#12
        - lean-business:DEC-002#13
        - lean-business:DEC-002#14
        - lean-business:DEC-002#15
        - lean-business:DEC-003#2
        - lean-business:DEC-003#3
        - lean-business:DEC-003#4
        - lean-business:DEC-003#5
        - lean-business:DEC-003#7
        - lean-business:DEC-003#8
      artefact:
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#data-validate-path
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
- `scripts/*.py`, one for each of the other commands ("Commands" below).
- `scripts/_lib/` — what the check and the commands share. What every write goes through: the context a command runs in, its consent forms, and its acts and moves (`acting`); the hold of a write against the check and the data validation, its commit and its undoing, and the location's record (`writes`); the round-trip edit of a file (`editing`); the ids a write gives (`naming`); the judgements a write leaves stale (`staling`); the process engine's status, can-move and move (`engine`), reached through `pkit` (`backbone`). What the desk commands read and draw: a variant's canvas and its boxes (`canvases`), the estimate (`estimates`), the grid (`grid`) and the status (`briefing`). What the experiment path's commands read and change: a variant's assumptions (`assumptions`), an experiment and the cycle it names (`experiments`), and a cycle's plan (`cycles`). And what the check reads through: the files git sees (`listing`); the place of each file in an idea's folder, and the file of a subject's id (`layout`); an idea's subjects and the lookups between them, each lookup telling a subject found from a reference that names nothing, one into a kind of which the location holds no file, or another idea's subject (`model`); the gates of the moves and the acts, each asked with the day of its act (`gates`); the acts recorded in an idea's files, each with the gate that judges it (`acts`); the canonical form, the fingerprints taken over it, and whether a kept one still matches (`fingerprint`); where a window and a time box fall under a cycle's suspensions, as they stand or as they stood on a day (`timeline`); the rules a suspension keeps, contradicting no act already recorded among them (`suspensions`); the places each schema puts a day (`schemas`); and what follows from the files, such as pricing, an experiment's pass or fail, an assumption's outcome and an idea dropped (`readings`).

The commands that suspend, resume and review a cycle, and the skill these records decide, are being built under project-kit#3426. This README lists them as they land.

## Adopter setup

Install:

```
pkit capabilities install lean-business
```

The ideas live in `lean-business/` at the repository's root, one folder per idea. The first command that writes an idea records that location in the capability's own configuration, `.pkit/capabilities/lean-business/project/config.yaml`. To keep the ideas elsewhere, record another location before the first idea, with `pkit lean set-location <path>` ([lean-business:DEC-002-lean-business-data-model] point 1). Where `lean-business/` already holds files of another kind, the first write is refused, writes nothing and names `set-location`. An idea's data is as private as the repository that holds it.

## An idea's folder

Each idea is a folder of the location, named by the idea's id. Each file names its schema in `pkit_schema`:

```
<location>/<idea>/goal.yaml                            lean-business:goal
<location>/<idea>/variants/<variant>/canvas.yaml       lean-business:canvas
<location>/<idea>/variants/<variant>/assumptions.yaml  lean-business:assumptions
<location>/<idea>/experiments/<experiment>.yaml        lean-business:experiment
<location>/<idea>/cycles/<cycle>.yaml                  lean-business:cycle
```

- **The goal** is the idea's revenue goal over a number of years, against which its variants' viability and feasibility are judged. It names the idea's currency, such as `EUR`, the unit of every sum the idea's files hold.
- **A canvas** is one variant of the business model: its archetype, its sides where it serves more than one, its twelve boxes, the inputs of its viability, its traction target, the person's verdict on each step at the desk, and its outcome, shortlisted, shelved or split. A price among the inputs is what the business keeps from one active customer, on average, each month or year: a one-off sale counts what a customer pays over their lifetime, spread over that lifetime, and a marketplace's side counts what the business keeps from it, not what flows through it ([lean-business:DEC-002-lean-business-data-model] point 4).
- **The assumptions** of a variant are its risks, ranked, each from an entry of its canvas or an input of its viability.
- **An experiment** tests one assumption, inside one cycle. It is declared before it runs, and frozen once declared; its result and the person's decision are recorded after.
- **A cycle** explores one or more shortlisted variants over a window, 90 days by default, toward an objective. Its suspensions move where the window falls, and its review records the person's decision.

A subject's id is qualified by what holds it, its parts joined by two hyphens: an idea's own subjects by the idea, such as `board-game--direct` for a variant, and a canvas's entries and a variant's assumptions by the variant, such as `board-game--direct--planning-takes-long`. A file refers to another's subject as `[canvas:<id>]`, `[assumptions:<id>]`, `[experiment:<id>]` or `[cycle:<id>]`, and never to another idea's. Each judgement the person made over content keeps a fingerprint of that content, so a later change of it shows: every verdict and each shortlisting covers the variant's archetype and its sides, so a change of model shows before any box changes, and a plan covers who planned it and when ([lean-business:DEC-002-lean-business-data-model] points 7 and 13).

The capability's configuration, `.pkit/capabilities/lean-business/project/config.yaml`, is bound to `lean-business:config` and records the location.

## The check

`pkit lean check` reads the files of the location as they stand, never today's date, and is the `lean-business:check` member of `pkit validate`. An invariant the capability's records own, broken by a command or by a hand edit, is an error, the one severity that fails validation. A guideline of the book, or a judgement gone stale, is a warning. A guideline's ranges count only a box that holds entries, so a first sketch with blanks draws none ([lean-business:DEC-002-lean-business-data-model] point 14).

The shape of each file is not the check's: the `data` member of `pkit validate` holds each file to its schema, as `pkit data validate <location>` does alone. Nor is a reference that names nothing among the files of its kind, or an id given twice among the variants, the assumptions, the experiments or the cycles: the schemas mark each reference, and say where each kind of file holds its ids, so the `data` member finds both. The check judges what they leave open, and reads a value of the wrong shape as missing. It reads the files git sees, those it tracks and those it neither tracks nor ignores, as the `data` member does, so a file git ignores is neither's; outside a git repository it reads the files as they lie.

Where a command's gate would refuse an act, the check asks the same gate with the day the act was recorded, and reads the cycles' suspensions as they stood that day. A suspension recorded later contradicts no act already recorded, so where it would turn one let through into one refused, the suspension breaks its rules, and the act stands. Which of an act and a suspension recorded on one day came first cannot be told, so there too the break is the suspension's ([lean-business:DEC-002-lean-business-data-model] point 12).

Each finding carries a label:

| Label | Severity | What it finds |
|---|---|---|
| `location` | error | The configuration cannot be read, or records a location that is refused, such as the repository's top, a folder under `.pkit/` or a hidden one, or one reached through a link; or git cannot list the files. |
| `layout` | error | A file of the capability's where an idea's folder has no place for it, a folder named by no id, or a variant's assumptions without its canvas; a file of the location ending in `.yml` that lies where the layout puts a `.yaml` file, or that names a schema of the capability's; or a file anywhere else that `pkit validate` reads and that names a schema of the capability's, save the configuration in its place. |
| `unreadable` | error | A file of the layout that cannot be read as YAML. |
| `binding` | error | A file at a place of the layout that names another schema, or none. |
| `day` | error | A value written as a day, `YYYY-MM-DD`, at a place its schema puts a day, that names no day of the calendar, such as `2026-02-30`. |
| `id` | error | An id that does not match the file's place, or is not qualified by what holds it. |
| `duplicate-id` | error | An entry's id given twice in one canvas. |
| `reference` | error | A reference to a subject of another idea, or into a kind of subject of which the location holds no file, which the `data` member only warns of. |
| `fingerprint` | error | A fingerprint of a canonical form the capability does not know, or one over data that has no canonical text, such as a number that is not finite. |
| `sides` | error | A direct model that names sides, a side named that the canvas does not name, or viability inputs given for no side or twice for one. |
| `verdicts` | error | A verdict on a step without a yes on each step before it; a verdict on viability or feasibility in an idea with no goal; a yes that still matches the canvas it judged, where that canvas misses what the yes needs; a shortlisting without a yes on all three steps; or a shortlisting that still matches, over a verdict gone stale. |
| `split` | error | A variant split into itself, or into one that does not name it as the variant it comes from. |
| `comes-from` | error | A variant that comes from one neither split nor shelved, or from one split into other variants and not it. |
| `declaration-changed` | error | A declared experiment whose declared fields, or whose record of its declaration, changed since. |
| `declaration-refused` | error | A declaration its gate refuses: a field its kind needs missing, no estimate, a time box over 14 days or ending before it starts, a start before the day it was declared, an expected range whose low is above its high, a declaration after its cycle's window ended, one on a variant shelved or split before it, or one resting on a shortlisting recorded after it, or on another than the one the canvas keeps where that was recorded before the declaration. |
| `undeclared` | error | A stopping rule reached, a result or a decision recorded on an experiment never declared. |
| `stop-refused` | error | A generative experiment's stopping rule reached before its time box started or after it ended. |
| `result-refused` | error | A result recorded as spoiled, where no suspension of its cycle ran through its time box. |
| `decision-refused` | error | A decision without a result, a result recorded after its decision, or a decision before its time box ended, without a generative experiment's stopping rule reached within its time box. |
| `cycle-variants` | error | An experiment on an assumption of a variant its cycle does not explore, a key result that names a variant the cycle does not explore, or an explored variant without a key result. |
| `plan-changed` | error | A cycle whose plan, or the record of who planned it and when, changed since its fingerprint was taken. |
| `plan-refused` | error | A cycle first planned in an idea with no goal, or while another cycle of the idea was undecided, or a plan last changed on its window's first day or later. |
| `one-cycle` | error | Two undecided cycles of one idea, or two whose windows overlap, as worked out. |
| `suspension` | error | A suspension that breaks its rules: its first day outside the window, a day ahead of the day it was recorded, a resumption before its first day, a covered day that holds another act, two suspensions that overlap, a suspension that would make an act recorded no later than it read as one its gate refuses, such as the goal set or a review after the window ended, or a suspension or its resumption recorded after the cycle was decided. Where two suspensions break a rule together, the break is the one recorded last. |
| `review-refused` | error | A review its gate refuses: a winning variant the cycle did not explore, a count of what was reached that differs from the key results, a persevere or a pivot for a variant shelved or split before it, a pivot on no decided experiment, or a review before the window ended. |
| `goal-changed` | error | The goal set while one of the idea's cycles was planned, running or suspended: after the day it was first planned, and no later than its window's last day. |
| `stale` | warning | A verdict on a variant with no outcome, or a shortlisting, whose content changed since: the variant's archetype or sides, the boxes or inputs it judged, or the goal, its currency among it. |
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

### The desk's commands

| Command | What it does | Kind |
|---|---|---|
| `set-location <path>` | Records the folder that holds the ideas, relative to the repository's top. Refused for a folder the location's rules refuse, as for the check's `location` label, and while the location in use holds an idea: move its folder first. | content |
| `set-goal <idea> [--revenue <amount>] [--per month\|year] [--currency <code>] [--years <n>]` | Sets the idea's goal, or changes what it is given; a first goal needs every flag, and creates the idea's folder. Refused while a cycle of the idea is planned, running or suspended, and a change of currency while a declared experiment is undecided. | act |
| `new-variant <idea>--<variant> --archetype direct\|multisided\|marketplace [--author <name>]... [--comes-from <variant>]` | Starts a variant: its canvas and an empty list of assumptions, with the idea's folder where none is. The authors are git's `user.name` where none is given. | content |
| `set-archetype <variant> direct\|multisided\|marketplace` | Changes the variant's archetype. Refused on the way to direct while the canvas names a side: `remove-side` takes each out first. | content |
| `set-authors <variant>\|<experiment> <name>...` | Replaces the authors of a variant, or of a draft experiment, with those named, in order. Refused once the experiment is declared. | content |
| `add-side <variant> <side>` | Names a side, a group of customers a model with several serves. | content |
| `remove-side <variant> <side>` | Takes a side out. Refused while an entry, the estimate's inputs or an assumption still names it. | content |
| `add-entry <variant> <box> <text> [--id <id>] [--side <side>] [links]` | Adds an entry to a box, and prints the id it gives. Its links are flags: `--alternative` on a problem, `--problem` on a value proposition or a solution, `--sub-headline` on a value proposition, `--trigger` on an early adopter, `--kind` on a channel and `--step` on a key metric. A link names an entry by its own part of its id, or by the whole. | content |
| `edit-entry <entry> [--text] [--side] [links] [--clear <field>]... [--drop-alternative <entry>]... [--drop-trigger <text>]...` | Changes an entry's words, side or links. Its id never changes. | content |
| `remove-entry <entry>` | Takes an entry out of its canvas. Where another entry or an assumption still names it, warns and keeps them as they are. | content |
| `move-entry <entry> --to <position>` | Moves an entry to another position in its box, 1 the first; a problem's position is its rank. | content |
| `set-inputs <variant> [--side <side>] [--price <amount> month\|year] [--lifetime <length> month\|year] [--conversion <share>] [--referral-share <share>] [--clear <input>]...` | Gives the estimate its inputs, merged into the set for the side. | content |
| `set-traction <variant> [--multiplier <n>] [--first-stage-metric <metric> --first-stage-target <n>] [--clear]` | Gives the variant its traction target; `--clear` removes it. | content |
| `judge <variant> desirability\|viability\|feasibility yes\|no [--note <text>]` | Records the person's verdict on a step, with the fingerprint of what it judged. A yes on the next step moves the variant on, and a no on a step it passed takes it back to the state before that step, clearing the verdicts after it and its shortlisting. A no on the next step, and a yes on a step it passed, judged again, move nothing. Refused on a shelved or split variant, and on a step after the next. | act, or move |
| `shortlist <variant>` | Shortlists a feasible variant, or takes its shortlisting again, with the fingerprint of its canvas and the goal. | move |
| `shelve <variant> --reason <text>` | Shelves the variant for good, with the reason, from any state but shelved and split: a shortlisting is replaced, and the verdicts stay. Where every variant of the idea not split is then shelved, the idea is dropped, and the command says so. | move |
| `split <variant> --into <variant>...` | Splits a variant with no outcome yet into the variants named, each created as a copy of it ("Splitting a variant" below). | move |
| `canvas <variant> [--ids]` | Draws the canvas as a grid ("The grid" below). | read-only |
| `estimate <variant>` | Works out what the goal asks of the variant ("The estimate" below). | read-only |
| `status [<idea>] [--json]` | Where the ideas stand and what waits on you ("The status" below). | read-only |

**What every write does.** A command builds its write, holds it, then writes it. It holds the files as they would stand to the check and to the `data` member of `pkit validate`, and refuses the write, writing nothing, where it would add an error. An error already in the files refuses nothing: the command names each, and leaves them as they were. Beyond the check, it refuses an id typed with `--id` that is taken, or that a reference still names. It warns of each warning the write adds, and of each verdict and shortlisting the write leaves stale, each with the command that judges it again. A shelved or split variant's content stays editable, and a change to it names none of its verdicts stale, since nothing rests on them any more. A shortlisting gone stale on a variant that a cycle not yet reviewed explores is said louder, since no experiment is declared on the variant until it is judged and shortlisted again ([lean-business:DEC-003-lean-business-process] point 7). The first write records the location (Adopter setup, above). A file written keeps its comments, its quoting and its order; a key a write adds lands where the schema writes it.

**Ids.** An entry's id comes from `--id`, or else from the first words of its text: accents stripped, kebab-cased, a leading digit given a letter, and the box's name where no word is left. The command qualifies it by the variant and prints it. It numbers one taken, `-2`, `-3`, and never gives again an id that a file still names, so a removed entry's id is not reused while an assumption names it. An id never changes when the text does ([lean-business:DEC-002-lean-business-data-model] point 7).

**Splitting a variant.** `split` names each variant it creates by its own part or by its id within the idea, and creates each as a copy of the variant split: its archetype, authors, sides, boxes, inputs and traction target, and its assumptions with their ranks. Each entry and each assumption keeps its own part of its id under the new variant's id, as do the links between entries and the entry each assumption comes from. Each copy names the variant split as the one it comes from, and carries none of its verdicts and no outcome, so it is judged at the desk afresh. A name is refused where its variant exists, or where a file still names its id or an id its copy would give.

**Content, acts and moves.** Content, a canvas's words and links, its inputs, its target and where the ideas live, is written without asking and records nobody. A judgement is the person's ([lean-business:DEC-001-lean-business-discipline] point 3): an act records it, and a move takes the process engine with it ([lean-business:DEC-003-lean-business-process] point 5).

- **The person's word.** At a terminal, the command asks, and a move asks its process's own prompt. Off one, it acts only with `--person-decided`, the flag by which an agent says the person decided in the session. With neither, it prints the question, does nothing and exits 3.
- **Who and when.** An act records the person as git's `user.name`, refusing where git names none, and the day it ran.
- **A move** asks the engine first whether its gate lets it go, writes, then moves the subject to where the engine places it after the write. Where the engine refuses the move after the write, the command undoes everything it wrote, the location's record included, and says so.

**Exit codes.** 0, done or shown; 1, refused, with the reason; 2, a usage error; 3, a question printed for the person, nothing done.

### The commands of assumptions, cycles and experiments

| Command | What it does | Kind |
|---|---|---|
| `add-assumption <variant> <statement> --kind desirability\|viability\|feasibility (--entry <entry> \| --input <input> [--side <side>]) [--id <id>]` | Adds an assumption to the variant's list, from an entry of its canvas or an input of the estimate, and prints the id it gives. It goes one past the highest rank; ranking it is `rank`'s. Refused for an entry the canvas does not hold. | content |
| `edit-assumption <assumption> [--statement <text>] [--kind <step>] [--entry <entry> \| --input <input>] [--side <side>]` | Changes an assumption's words, kind or source. Its id never changes. Warns where a declared experiment tests it. | content |
| `remove-assumption <assumption>` | Takes an assumption out of its list; the others keep their ranks. Refused while an experiment tests it, declared or a draft. | content |
| `rank <variant> <assumption>...` | Ranks the assumptions by risk, the riskiest first: those named take the first ranks, in the order given, and the rest follow as they were ranked. Records no who or when. | act |
| `plan-cycle <idea>--<cycle> --variant <variant>... --start <day> [--days <n>] --objective <text> --key-result <variant>:<step>:<target>... --constraint-step <step> --constraint-evidence <text>` | Plans the idea's next cycle, with who planned it, the day and the plan's fingerprint. Its window holds 90 days where `--days` gives none. Refused for a variant not shortlisted, in an idea with no goal, and while another cycle of the idea is undecided. Warns where the window has started by today. | act |
| `change-plan <cycle> [plan-cycle's flags]` | Changes a planned cycle's plan, each part given replacing that part whole, and takes its fingerprint again; who first planned it stays. Refused once the cycle is not planned, and for a start moved to today or before. | act |
| `new-experiment <idea>--<experiment> --kind generative\|evaluative [--assumption <assumption>] [--cycle <cycle>] [--author <name>]...` | Starts a draft. The assumption and the cycle may wait for `draft-experiment`. The authors are git's `user.name` where none is given. | content |
| `draft-experiment <experiment> [field flags] [--clear <field>]...` | Writes what the draft will declare ("Drafting an experiment" below). Refused once declared. | content |
| `remove-experiment <experiment>` | Removes a draft. Refused once declared. | content |
| `record-estimate <experiment> <value>` | Records your own guess at the number its result is held against, made alone; a second of yours replaces the first. Refused once declared. | act |
| `declare <experiment>` | Declares the experiment, which freezes it: it records who declared it, the day, the shortlisting it rests on and the declaration's fingerprint. A time box starting today takes it into running, and a later one into declared. Refused where the declaring gate refuses it, as for the check's `declaration-refused` label, on a stale shortlisting, and in a cycle that is neither planned nor running. Warns where an assumption ranked riskier is untested. | move |
| `reach-stopping-rule <experiment>` | Records a generative experiment's stopping rule reached, within its time box, which makes it due. Refused on an evaluative experiment, which runs its whole time box. | act |
| `record-result <experiment> [--measured <number>] [--spoiled] --evidence <text> --learned <text>` | Records what a declared experiment found, and says what it works out to: a pass, a fail, or neither. Recorded again before the decision, it replaces the earlier one. Refused for a measurement spoiled where no suspension ran through its time box. | act |
| `decide <experiment> correct-course\|double-down\|stop` | Records your next action on a due experiment whose result is recorded. | move |

An assumption is named by its id, `<idea>--<variant>--<assumption>`, by the part after the idea, `<variant>--<assumption>`, or by its own part; a cycle by its id, `<idea>--<cycle>`, or by its own part. Every command that names one takes each form, save `plan-cycle`, which takes the id of the cycle it plans. A part is completed by the variant the command names, as `rank`'s, or by the idea, as the experiment's id gives `new-experiment` and `draft-experiment`. Where that leaves it short, it names the one of that idea, or else of the location, whose id ends with it, and is refused where none does, or more than one. `--entry` names an entry by its id or its own part. An assumption's id comes from `--id` or its statement, as an entry's does.

**Drafting an experiment.** `draft-experiment` sets a field with each flag, and `--clear <field>` takes one out:

- **Every experiment:** `--kind`, `--assumption`, `--cycle`, and its time box, `--start` and `--end`, fourteen days at most.
- **Generative:** `--learn`, `--stopping-rule`, and `--fit <count>/<what it counts>`.
- **Evaluative:** `--action`; `--metric <step>`; `--direction at-least|at-most` with `--threshold <number>` or `--range <low> <high>`; `--source estimate|traction-target`; `--effect <text>`, each adding one; and `--control cohorts|split`, a split with `--exposed <share>`.

Refused: a time box over fourteen days, or ending before it starts; a range whose low is above its high; a field the experiment's kind does not hold; and a change of kind while the draft holds the other kind's fields, unless `--clear` takes them out in the same run.

**While a cycle is suspended,** `record-estimate`, `declare`, `reach-stopping-rule`, `record-result` and `decide` are refused on its experiments, naming `pkit lean resume <cycle>`. `new-experiment` and `draft-experiment` write the draft, and warn.

### The grid

`pkit lean canvas` draws the canvas's twelve boxes as the book arranges them, five columns over a bottom row:

```
+--------------+-------------+-------------------+------------------+-------------------+
| PROBLEM      | SOLUTION    | UNIQUE VALUE      | UNFAIR ADVANTAGE | CUSTOMER SEGMENTS |
|              |             | PROPOSITION       |                  |                   |
+--------------+-------------+-------------------+------------------+-------------------+
| EXISTING     | KEY METRICS | HIGH-LEVEL        | CHANNELS         | EARLY ADOPTERS    |
| ALTERNATIVES |             | CONCEPT           |                  |                   |
+--------------+-------------+-------------------+------------------+-------------------+
| COST STRUCTURE                         | REVENUE STREAMS                              |
+----------------------------------------+----------------------------------------------+
```

Each column holds its upper box over its lower one, each entry a bullet: a value proposition with its sub-headline, an early adopter with its triggers, a channel with its kind and a key metric with its step. `--ids` adds under each entry its own part of its id, in brackets, which `edit-entry` and `remove-entry` take after the variant's id and `--`. The grid ends with the line that credits the Lean Canvas and the Business Model Canvas it adapts, and names their licence (Credits and licence, below).

### The estimate

`pkit lean estimate` works out, for each side that pays, what the idea's goal asks of the variant through the customer factory ([lean-business:DEC-002-lean-business-data-model] point 4). Nothing it works out is stored.

- **A year's revenue from one customer:** the price, times twelve where it is counted by the month.
- **The active customers needed:** the goal's yearly revenue divided by that, rounded up.
- **The customers lost each year:** the active customers divided by a customer's lifetime in years, and as many won each year to replace them.
- **Won by referral:** the referral share of those, and the rest won through the channels.
- **The leads needed each year:** those won through the channels divided by the conversion.
- **The active customers on the way:** for each year of the goal's span, the last year's the number needed, and each year before it the traction multiplier fewer, rounded up. The multiplier is ten where the variant gives none.

A side that pays nothing counts at nothing. A model with several paying sides is worked out for each as though it alone carried the goal, since the inputs say nothing of how the goal divides among them. Where inputs are missing, the estimate names each of them, and works out each number that rests on none of them. A side that pays nothing needs no input but its price. Whether a number is within reach is the person's judgement, at the viability step.

### The status

`pkit lean status` gives one line for each idea: whether it has a goal, its variants counted by where they stand, and how many things wait on you. `pkit lean status <idea>` gives the idea in full: its goal, each variant, cycle and experiment with where it stands, and what waits on you, each with the command that takes it. Each position is the process engine's ([lean-business:DEC-002-lean-business-data-model] point 15). At the desk, what waits is a goal to set, the next step of a variant to judge, and a feasible variant that may be shortlisted.

`--json` prints its structured form, whose keys a reader may depend on:

- `schema_version`: 1. A change that would break a reader raises it; an added key leaves it.
- `location`: the folder the ideas live in.
- `ideas`: one for each idea, or the one named, each with:
  - `id`;
  - `goal`: `revenue`, `per`, `currency` and `years`, or `null` where the idea has none;
  - `variants`, `cycles` and `experiments`: each an `id`, its `state`, and `why`. Where the engine could not tell where the subject stands, `state` is `null` and `why` says what stopped it; otherwise `why` is `null`;
  - `waiting`: each a `subject`, `what` waits and the `command` that takes it.

## Credits and licence

The method is Ash Maurya's, from *Running Lean: Iterate from Plan A to a Plan That Works*, third edition (O'Reilly, 2022). The capability carries the method in its own words and ships no text of the book.

The canvas follows the Lean Canvas, Ash Maurya's adaptation of Alex Osterwalder's Business Model Canvas, both published under the Creative Commons Attribution-ShareAlike 3.0 licence. The capability uses the names of the canvas's boxes as its fields, describes them in its own words, and ships no file under that licence. Wherever it draws a canvas, it draws it with the credit and licence line beneath ([lean-business:DEC-001-lean-business-discipline]).

The names *Running Lean* and *Lean Canvas* may be trademarks of their owners. They are used here only to credit the source.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[lean-business:DEC-001-lean-business-discipline]`. Other capabilities and adopter content use the same form.

## Dependencies

None beyond the backbone. The capability reads no other capability. A later view may read its status's structured form, and the experiments' results may cite evidence records, without either becoming a dependency ([lean-business:DEC-001-lean-business-discipline]).
