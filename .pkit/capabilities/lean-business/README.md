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
        - .pkit/capabilities/lean-business/scripts/suspend.py
        - .pkit/capabilities/lean-business/scripts/resume.py
        - .pkit/capabilities/lean-business/scripts/review_cycle.py
        - .pkit/capabilities/lean-business/scripts/_lib/*.py
        - .pkit/capabilities/lean-business/schemas/*.schema.json
        - .pkit/capabilities/lean-business/schemas/*.yaml
        - .pkit/capabilities/lean-business/skills/lean-business/lean-business.md
      record:
        - lean-business:DEC-001#1
        - lean-business:DEC-001#3
        - lean-business:DEC-001#4
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
- `schemas/desk-stage.yaml`, `schemas/experiment-lifecycle.yaml` and `schemas/cycle-lifecycle.yaml` — the definitions of the three processes the process engine runs: a variant's stage at the desk, an experiment's life and a cycle's ([lean-business:DEC-003-lean-business-process]).
- `scripts/check.py` — the capability's check, `pkit lean check`, and the `lean-business:check` member of `pkit validate` ("The check" below).
- `scripts/*.py` — one for each of the other commands "Commands" below describes, and the predicates that the process engine, not you, runs for the capability's processes: for each process, the one that tells where a subject stands, and the gates its moves carry.
- `scripts/_lib/` — the code the check and the commands share.
- `skills/lean-business/` — the skill that guides a person through the loop with these commands, one sub-procedure for each step, every judgement left to the person ([lean-business:DEC-001-lean-business-discipline]).

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
- **An experiment** tests one assumption, inside one cycle. It is declared before it runs; its result and the person's decision are recorded after.
- **A cycle** explores one or more shortlisted variants over a window toward an objective. Its suspensions move where the window falls, and its review records the person's decision.

A subject's id is qualified by what holds it, its parts joined by two hyphens: an idea's own subjects by the idea, such as `meal-plan--direct` for a variant, and a canvas's entries and a variant's assumptions by the variant, such as `meal-plan--direct--planning-takes-long`. A file refers to another's subject as `[canvas:<id>]`, `[assumptions:<id>]`, `[experiment:<id>]` or `[cycle:<id>]`, and never to another idea's. Each judgement the person made over content keeps a fingerprint of that content, so a later change of it shows: every verdict and each shortlisting covers the variant's archetype and its sides, so a change of model shows before any box changes, and a plan covers who planned it and when ([lean-business:DEC-002-lean-business-data-model] points 7 and 13).

The capability's configuration, `.pkit/capabilities/lean-business/project/config.yaml`, is bound to `lean-business:config` and records the location.

## The check

`pkit lean check` reads the files of the location as they stand, never today's date, and is the `lean-business:check` member of `pkit validate`. An invariant the capability's records own, broken by a command or by a hand edit, is an error, the one severity that fails validation ([the CLI reference, "validate"](../../cli/README.md#validate)). A guideline of the book, or a judgement gone stale, is a warning. A guideline's ranges count only a box that holds entries, so a first sketch with blanks draws none ([lean-business:DEC-002-lean-business-data-model] point 14).

The shape of each file is not the check's: the `data` member of `pkit validate` holds each file to its schema, as `pkit data validate <location>` does alone. Nor is a reference that names nothing among the files of its kind, or an id given twice among the variants, the assumptions, the experiments or the cycles: the schemas mark each reference, and say where each kind of file holds its ids, so the `data` member finds both. The check judges what they leave open, and reads a value of the wrong shape as missing. It reads the files git sees, those it tracks and those it neither tracks nor ignores, as the `data` member does ([the CLI reference, "validate"](../../cli/README.md#validate)), so a file git ignores is neither's; outside a git repository it reads the files as they lie.

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
| `reference` | error | A reference to a subject of another idea, or into a kind of subject of which the location holds no file, which the `data` member only warns of ([the CLI reference, "data validate"](../../cli/README.md#data-validate-path)). |
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
| `plan-refused` | error | A cycle first planned in an idea with no goal, or while another cycle of the idea was undecided, or a plan last changed on its window's first day or later, save on the day it was first planned, when a change is part of the planning. |
| `one-cycle` | error | Two undecided cycles of one idea, or two whose windows overlap, as worked out. |
| `suspension` | error | A suspension that breaks its rules: its first day outside the window as earlier suspensions move it, a day ahead of the day it was recorded, a resumption before its first day, a covered day that holds work recorded on the cycle, two suspensions that overlap, a suspension that would make an act recorded no later than it read as one its gate refuses, such as the goal set or a review after the window ended, or a suspension or its resumption recorded after the cycle was decided. Work recorded on the cycle is an act on the cycle, on one of its experiments or on the goal, and the recording of another suspension or of its resumption. Where two suspensions break a rule together, the break is the one recorded last. |
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
- **Prints** a summary, then each finding with its severity, its place and its label: a file relative to the project root, with `#` and a JSON Pointer where it lies within the file. `--json` prints the findings document `pkit validate` reads ([the CLI reference, "validate"](../../cli/README.md#validate)), `{"summary": [...], "findings": [...]}`, each finding with its `severity`, `location`, `message` and `label`, the errors first.
- **Writes** nothing, and runs offline.
- **Exits** 1 when a finding is an error; 0 otherwise. With `--json` it always exits 0, as `pkit validate` requires ([the CLI reference, "validate"](../../cli/README.md#validate)).

### What the other commands share

**What every write does.** A command builds its write, holds it, then writes it. It holds the files as they would stand to the check and to the `data` member of `pkit validate`, and refuses the write, writing nothing, where it would add an error. An error already in the files refuses nothing: the command names each, and leaves them as they were. Beyond the check, it refuses an id typed with `--id` that is taken, or that a reference still names. It warns of each warning the write adds, and of each verdict and shortlisting the write leaves stale, naming for a verdict the command that judges it again. A shelved or split variant's content stays editable, and a change to it names none of its verdicts stale, since nothing rests on them any more. A shortlisting gone stale on a variant that a cycle not yet reviewed explores is said louder, since no experiment is declared on the variant until it is judged and shortlisted again ([lean-business:DEC-003-lean-business-process] point 7). A file written keeps its comments, its quoting and its order; a key a write adds lands where the schema writes it.

**Content, acts and moves.** Content, a canvas's words and links, its inputs, its target, the authors of a variant or a draft, and where the ideas live, is written without asking, and records neither who decided it nor when. A judgement is the person's ([lean-business:DEC-001-lean-business-discipline] point 3): an act records it, and a move takes the process engine with it ([lean-business:DEC-003-lean-business-process] point 5).

- **The person's word.** At a terminal, the command asks, and a move asks its process's own prompt. Off one, it acts only with `--person-decided`, the flag by which an agent says the person decided in the session. With neither, it prints the question, does nothing and exits 3.
- **Who and when.** An act records the person as git's `user.name`, refusing where git names none, and the day it ran. Two acts record less: `record-estimate` records the person and no day, and `rank` records neither, so it needs no name from git.
- **A move** asks the engine first whether its gate lets it go, writes, then moves the subject to where the engine places it after the write. Where the engine refuses the move after the write, the command undoes everything it wrote, the location's record included (Adopter setup, above), and says so.

**Exit codes.** 0, done or shown; 1, refused, with the reason; 2, a usage error; 3, a question printed for the person, nothing done.

### The location, the goal and the status

| Command | What it does | Kind |
|---|---|---|
| `set-location <path>` | Records the folder that holds the ideas, relative to the repository's top. Refused for a folder the location's rules refuse, as for the check's `location` label, and while the location in use holds an idea: move its folder first. Naming the location in use, the default while none is recorded, records it as it stands. | content |
| `set-goal <idea> [--revenue <amount>] [--per month\|year] [--currency <code>] [--years <n>]` | Sets the idea's goal, or changes what it is given; a first goal needs every flag, and creates the idea's folder. Refused while a cycle of the idea is planned, running or suspended, and a change of currency while a declared experiment is undecided. | act |
| `status [<idea>] [--json]` | Where the ideas stand and what waits on you ("The status" below). | read-only |

### The desk's commands

| Command | What it does | Kind |
|---|---|---|
| `new-variant <idea>--<variant> --archetype direct\|multisided\|marketplace [--author <name>]... [--comes-from <variant>]` | Starts a variant: its canvas and an empty list of assumptions, with the idea's folder where none is. The authors are git's `user.name` where none is given, and it is refused where git names nobody. | content |
| `set-archetype <variant> direct\|multisided\|marketplace` | Changes the variant's archetype. Refused on the way to direct while the canvas names a side: `remove-side` takes each out first. | content |
| `set-authors <variant>\|<experiment> <name>...` | Replaces the authors of a variant, or of a draft experiment, with those named, in order. Refused once the experiment is declared. | content |
| `add-side <variant> <side>` | Names a side, a group of customers a model with several serves. | content |
| `remove-side <variant> <side>` | Takes a side out. Refused while an entry, the estimate's inputs or an assumption still names it. | content |
| `add-entry <variant> <box> <text> [--id <id>] [--side <side>] [links]` | Adds an entry to a box, and prints the id it gives. Its links are flags: `--alternative` on a problem, `--problem` on a value proposition or a solution, `--sub-headline` on a value proposition, `--trigger` on an early adopter, `--kind` on a channel and `--step` on a key metric. A link names an entry by its own part of its id, or by the whole. | content |
| `edit-entry <entry> [--text] [--side] [links] [--clear <field>]... [--drop-alternative <entry>]... [--drop-trigger <text>]...` | Changes an entry's words, side or links. | content |
| `remove-entry <entry>` | Takes an entry out of its canvas. Where another entry or an assumption still names it, warns and keeps them as they are. | content |
| `move-entry <entry> --to <position>` | Moves an entry to another position in its box, 1 the first; a problem's position is its rank. | content |
| `set-inputs <variant> [--side <side>] [--price <amount> month\|year] [--lifetime <length> month\|year] [--conversion <share>] [--referral-share <share>] [--clear <input>]...` | Gives the estimate its inputs, merged into the set for the side. | content |
| `set-traction <variant> [--multiplier <n>] [--first-stage-metric <metric> --first-stage-target <n>] [--clear]` | Gives the variant its traction target; `--clear` removes it. | content |
| `judge <variant> desirability\|viability\|feasibility yes\|no [--note <text>]` | Records the person's verdict on a step, with the fingerprint of what it judged. A yes on the next step moves the variant on, and a no on a step it passed takes it back to the state before that step, clearing the verdicts after it and its shortlisting. A no on the next step, and a yes on a step it passed, judged again, move nothing. Refused on a shelved or split variant, and on a step after the next. | act, or move |
| `shortlist <variant>` | Shortlists a feasible variant, or takes its shortlisting again, with the fingerprint of its canvas and the goal. | move |
| `shelve <variant> --reason <text>` | Shelves the variant for good, with the reason, from any state but shelved and split: a shortlisting is replaced, and the verdicts stay. Where every variant of the idea not split is then shelved, the idea is dropped, and the command says so. | move |
| `split <variant> --into <variant> [--into <variant>]...` | Splits a variant with no outcome yet into the variants named, each created as a copy of it ("Splitting a variant" below). | move |
| `canvas <variant> [--ids]` | Draws the canvas as a grid ("The grid" below). | read-only |
| `estimate <variant>` | Works out what the goal asks of the variant ("The estimate" below). | read-only |

**Ids.** An entry's id comes from `--id`, or else from the first words of its text: accents stripped, kebab-cased, a leading digit given a letter, and the box's name where no word is left. The command qualifies it by the variant and prints it. It numbers one taken, `-2`, `-3`, and never gives again an id that a file still names, so a removed entry's id is not reused while an assumption names it. An id, an entry's or an assumption's, never changes when its words do ([lean-business:DEC-002-lean-business-data-model] point 7).

**Splitting a variant.** `split` names each variant it creates by its own part or by its id within the idea, and creates each as a copy of the variant split: its archetype, authors, sides, boxes, inputs and traction target, and its assumptions with their ranks. Each entry and each assumption keeps its own part of its id under the new variant's id, as do the links between entries and the entry each assumption comes from. Each copy names the variant split as the one it comes from, and carries none of its verdicts and no outcome, so it is judged at the desk afresh. A name is refused where its variant exists, or where a file still names its id or an id its copy would give. Where the variant split holds an error in what a copy takes, each copy would repeat it, so the split is refused and names the file to fix first.

### The commands of assumptions, cycles and experiments

| Command | What it does | Kind |
|---|---|---|
| `add-assumption <variant> <statement> --kind desirability\|viability\|feasibility (--entry <entry> \| --input <input> [--side <side>]) [--id <id>]` | Adds an assumption to the variant's list, from an entry of its canvas or an input of the estimate, and prints the id it gives. It goes one past the highest rank; ranking it is `rank`'s. Refused for an entry the canvas does not hold. | content |
| `edit-assumption <assumption> [--statement <text>] [--kind <step>] [--entry <entry> \| --input <input>] [--side <side>]` | Changes an assumption's words, kind or source. Warns where a declared experiment tests it. | content |
| `remove-assumption <assumption>` | Takes an assumption out of its list; the others keep their ranks. Refused while an experiment tests it, declared or a draft. | content |
| `rank <variant> <assumption>...` | Ranks the assumptions by risk, the riskiest first: those named take the first ranks, in the order given, and the rest follow as they were ranked. | act |
| `plan-cycle <idea>--<cycle> --variant <variant> [--variant <variant>]... --start <day> [--days <n>] --objective <text> --key-result <variant>:<step>:<target> [--key-result <variant>:<step>:<target>]... --constraint-step <step> --constraint-evidence <text>` | Plans the idea's next cycle, with who planned it, the day and the plan's fingerprint. Its window holds 90 days where `--days` gives none, and 3650 days, ten years, at most. Refused for a variant not shortlisted, and for a first plan the check's `plan-refused` label finds. Warns where the window has started by today. | act |
| `change-plan <cycle> [plan-cycle's flags]` | Changes a planned cycle's plan, each part given replacing that part whole and each part not given left as it is, and takes its fingerprint again; who first planned it stays. Refused once the cycle is not planned, and for a change the check's `plan-refused` label finds. Warns where the window has started by today. | act |
| `new-experiment <idea>--<experiment> --kind generative\|evaluative [--assumption <assumption>] [--cycle <cycle>] [--author <name>]...` | Starts a draft. The assumption and the cycle may wait for `draft-experiment`. The authors are git's `user.name` where none is given, and it is refused where git names nobody. | content |
| `draft-experiment <experiment> [field flags] [--clear <field>]...` | Writes what the draft will declare ("Drafting an experiment" below). Refused once declared. | content |
| `remove-experiment <experiment>` | Removes a draft. Refused once declared. | content |
| `record-estimate <experiment> <value>` | Records your own guess at the number its result is held against, made alone; a second of yours replaces the first. Refused once declared. | act |
| `declare <experiment>` | Declares the experiment, which freezes it: it records who declared it, the day, the shortlisting it rests on and the declaration's fingerprint. A time box starting today takes it into running, and a later one into declared. Refused where the declaring gate refuses it, as for the check's `declaration-refused` label, on a stale shortlisting, and in a cycle that is neither planned nor running. Warns where an assumption ranked riskier is untested. | move |
| `reach-stopping-rule <experiment>` | Records a generative experiment's stopping rule reached, within its time box, which makes it due. Refused on an evaluative experiment, which runs its whole time box. | act |
| `record-result <experiment> [--measured <number>] [--spoiled] --evidence <text> --learned <text>` | Records what a declared experiment found, and says what it works out to: a pass, a fail, or neither. Recorded again before the decision, it replaces the earlier one. Refused for a result the check's `result-refused` label finds. | act |
| `decide <experiment> correct-course\|double-down\|stop` | Records your next action on a due experiment whose result is recorded. | move |
| `suspend <cycle> --reason <text> --since <day> [--resumed <day>]` | Records that your life stopped a running cycle, or one in review, from the first day you were away, today or earlier, so it may be recorded on your return. Where the absence is over, `--resumed` gives the day you came back, which counts again. Says where the window, and each time box it moves, fall before and after. The cycle then goes where its dates place it: into suspended, or from review back to running where the days it gives back reach today. Refused on a cycle planned, since an absence known before the window starts is sized into it, on one suspended or decided, and for a suspension that breaks its rules, as for the check's `suspension` label ("A suspension" below). | act |
| `resume <cycle> [--on <day>]` | Records the day a suspended cycle resumed, today where `--on` gives none. It goes back to running, or into review where its window, moved by the suspension, ended before today. Refused on a cycle not suspended, and for a day the suspension's rules refuse. | move |
| `review-cycle <cycle> --reached <number> [--reached <number>]... [--winning <variant>] --decision persevere\|pivot\|pause --reasons <text> [--evidence <experiment>]...` | Records a cycle's review once its window has ended: what each key result reached, in the plan's order; the variant that did best, which is the one it explored where it explored one; and your decision for it, with your reasons. Says the progress report first: each key result against its target, each suspension with the day it was recorded, and each experiment not yet decided, which the decision does not wait for. Refused on a cycle not in review, with no winner named where it explored several, and where the deciding gate refuses it, as for the check's `review-refused` label. Warns of what the check's `persevere-missed` label finds. | move |

An assumption is named by its id, `<idea>--<variant>--<assumption>`, by the part after the idea, `<variant>--<assumption>`, or by its own part; a cycle by its id, `<idea>--<cycle>`, or by its own part. Every command that names one takes each form, save `plan-cycle`, which takes the id of the cycle it plans. A part is completed by the variant the command names, as `rank`'s, or by the idea, as the experiment's id gives `new-experiment` and `draft-experiment`. Where that leaves it short, it names the one of that idea, or else of the location, whose id ends with it, and is refused where none does, or more than one. `--entry` names an entry by its id or its own part. An assumption's id comes from `--id` or its statement, as an entry's does.

**Drafting an experiment.** `draft-experiment` sets a field with each flag, and `--clear <field>` takes one out:

- **Every experiment:** `--kind`, `--assumption`, `--cycle`, and its time box, `--start` and `--end`.
- **Generative:** `--learn`, `--stopping-rule`, and `--fit <count>/<what it counts>`.
- **Evaluative:** `--action`; `--metric <step>`; `--direction at-least|at-most` with `--threshold <number>` or `--range <low> <high>`; `--source estimate|traction-target`; `--effect <text>`, each adding one; and `--control cohorts|split`, a split with `--exposed <share>`.

Refused: a time box or a range that the declaring gate refuses whatever the day, as for the check's `declaration-refused` label; a field the experiment's kind does not hold; and a change of kind while the draft holds the other kind's fields, unless `--clear` takes them out in the same run.

**A suspension** covers each day from its first day up to the day the cycle resumed, which counts again. Its days count toward no window, and toward no time box of an experiment that had not started by its first day; an experiment already running keeps its dates ([lean-business:DEC-002-lean-business-data-model] point 12). The rules it keeps are those the check's `suspension` label holds it to. `suspend` writes it, then takes the move its dates make. Where the process engine then places the cycle in none of its states, the suspension stands, since it is your act, and the command says that the move waits.

**While a cycle is suspended,** `record-estimate`, `declare`, `reach-stopping-rule`, `record-result` and `decide` are refused on its experiments, and `review-cycle` on the cycle, each naming `pkit lean resume <cycle>`. `new-experiment` and `draft-experiment` write the draft, and warn.

### The grid

`pkit lean canvas` draws the canvas's twelve boxes as the book arranges them, five columns over a bottom row:

```
+------------------+------------------+------------------+------------------+------------------+
| PROBLEM          | SOLUTION         | UNIQUE VALUE     | UNFAIR ADVANTAGE | CUSTOMER         |
|                  |                  | PROPOSITION      |                  | SEGMENTS         |
+------------------+------------------+------------------+------------------+------------------+
| EXISTING         | KEY METRICS      | HIGH-LEVEL       | CHANNELS         | EARLY ADOPTERS   |
| ALTERNATIVES     |                  | CONCEPT          |                  |                  |
+----------------------------------------------------------------------------------------------+
| COST STRUCTURE                               | REVENUE STREAMS                               |
+----------------------------------------------+-----------------------------------------------+
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

`pkit lean status` gives one line for each idea: whether it has a goal, or that its goal's file cannot be read, its variants counted by where they stand, that it is dropped where it is, and how many things wait on you. An idea is dropped once it has a variant and every variant not split is shelved ([lean-business:DEC-003-lean-business-process] point 8). `pkit lean status <idea>` gives the idea's briefing, from its files alone, to bring you back to it after a day or after months ([lean-business:DEC-001-lean-business-discipline] point 10). Its first line names the idea, and says so where the idea is dropped. Then it comes in this order:

1. **An offer, after a silence of 21 days.** Where nothing has been recorded on a running cycle, or on one in review, for 21 days or more of its window, the briefing first offers to record the gap as a suspension. Only the days within the window count: those after the last work, through today or through the window's end where that is earlier, so a cycle long in review is not offered the days after its window. [lean-business:DEC-001-lean-business-discipline] point 10 leaves how long a silence must be to the capability, which sets it at three weeks; use may show it should change. The suspension would start on the day after the last work recorded on the cycle, as the check's `suspension` label counts work, or on the window's first day where that is later. The briefing says where the window's end falls now and where it would fall were you back today, with the `suspend` command that records it. No offer is made where such a suspension would break its rules. It is an offer, never an act: only you know whether the silence was time away.
2. **Your last act:** its day, and each act recorded that day.
3. **The goal,** or which of its values cannot be read, or that its file cannot be read, so whether the idea has a goal cannot be told.
4. **The cycles.** The one not yet decided comes in full: where it stands; the days of its window gone by today, the suspended days not counted; where its window falls as its suspensions move it; its objective; each key result with its target and, once reviewed, what it reached; its constraint; and each suspension with its days, its reason and the day it was recorded. A decided one comes in a line, with its decision and its winning variant.
5. **The variants,** each with where it stands, each of its judgements gone stale, a verdict by its step or its shortlisting, and its assumptions, the riskiest first, each with its rank and its outcome ([lean-business:DEC-003-lean-business-process] point 8):
   - *untested,* while no declared experiment tests it;
   - *being tested,* while one that tests it is declared, running or due;
   - otherwise, from the one that tests it and was decided last: *supported* where its result worked out to a pass, *refuted* where to a fail, and *inconclusive* where to neither.

   An assumption's outcome cannot be told while an experiment's file of the idea cannot be read, since that experiment may test it.
6. **The canvases of the variants in play:** of each variant neither shelved nor split, drawn as `pkit lean canvas` draws it, its credit line beneath ("The grid" above). A variant whose canvas cannot be read is not drawn, and one whose position cannot be told is drawn, since it may still be in play. `pkit lean canvas` draws a shelved or split one.
7. **The experiments.** One not yet decided comes with where it stands. Once declared, it comes too with its time box as its cycle's suspensions move it, or that the time box waits for its cycle to resume, and with its declared expectation, and beside it the result, worked out to a pass, a fail or neither, or that it waits for one. A decided one comes in a line, with your next action and its result.
8. **What waits on you,** each with the command that takes it, in this order:
   - a suspended cycle to resume;
   - a goal to set;
   - a due experiment's result, then its next action;
   - a cycle in review to review;
   - a draft in a planned or running cycle to declare;
   - at the desk, for each variant: a stale verdict to judge again, the next step to judge, a feasible variant to shortlist, and a stale shortlisting to take again;
   - the next cycle to plan, where the idea has a goal and a shortlisted variant whose shortlisting is not stale, no cycle of the idea is undecided, and its last cycle did not pause.

Each position is the process engine's ([lean-business:DEC-002-lean-business-data-model] point 15). Where a window or a time box falls is worked out as the check works it out, and the days are counted to today, read when the command runs.

`--json` prints its structured form, which draws no canvas, and whose keys a reader may depend on:

- `schema_version`: 1. A change that would break a reader raises it; an added key leaves it.
- `location`: the folder the ideas live in.
- `ideas`: one for each idea, or the one named, each with:
  - `id`;
  - `goal`: its `revenue`, the period it is counted `per`, `month` or `year`, its `currency` and its `years`; or `null` where the idea has none or its goal's file cannot be read;
  - `goal_why`: why whether the idea has a goal cannot be told, where its goal's file lies in its place but cannot be read; otherwise `null`;
  - `dropped`: `true` where the idea is dropped, and `false` where it is not. It is `null` where a variant's canvas cannot be read and the canvases that read leave it open;
  - `last_act`: the `day` of your last recorded act, and `what` was recorded that day, each in words; `null` where nothing is recorded;
  - `offer`: the offer to record a silence, or `null` where none is made. It holds the `cycle`, the day of the `last_work` recorded on it, the `first_day` the suspension would cover, the `window_end` now, the `window_end_if_back_today`, and the `command` that records it;
  - `variants`, `cycles` and `experiments`: each an `id`, its `state`, and `why`. A `state` is one of the states its process's definition declares:
    - a variant's, of [`schemas/desk-stage.yaml`](schemas/desk-stage.yaml): `sketched`, `desirable`, `viable`, `feasible`, `shortlisted`, `shelved` or `split`;
    - a cycle's, of [`schemas/cycle-lifecycle.yaml`](schemas/cycle-lifecycle.yaml): `planned`, `running`, `suspended`, `in-review` or `decided`;
    - an experiment's, of [`schemas/experiment-lifecycle.yaml`](schemas/experiment-lifecycle.yaml): `drafted`, `declared`, `running`, `due` or `decided`.

    Where the engine could not tell where the subject stands, `state` is `null` and `why` says what stopped it; otherwise `why` is `null`. Each also has:
    - a variant: `stale`, its judgements gone stale, each a step, `desirability`, `viability` or `feasibility`, or `shortlisting`. Where the goal's file does not read, whether a verdict judged against the goal, or the shortlisting, is stale cannot be told, and `stale` holds neither. And its `assumptions`, the riskiest first, each its `id`, its `rank` and its `outcome`: `untested`, `being-tested`, `supported`, `refuted` or `inconclusive`, `null` where it cannot be told. `assumptions` is `null` where the variant's file of assumptions cannot be read, and empty where it has none;
    - a cycle: `window`, its `start` and `end` as its suspensions move it, the `days` it holds and the days of it `counted` by today; its `objective`; its `key_results`, each a `variant`, a `metric`, the step of the customer factory it counts, `acquisition`, `activation`, `retention`, `revenue` or `referral`, a `target`, and what it `reached`, `null` before the review; its `constraint`, a `step`, one of the same five, and its `evidence`; its `suspensions`, each a `reason`, its `first_day`, the day it `resumed`, `null` while it is ongoing, and the day it was `recorded`; and its `review`, the `decision`, `persevere`, `pivot` or `pause`, the `winning` variant and `when`, or `null` before the review;
    - an experiment: its `kind`, `generative` or `evaluative`; the `assumption` it tests; its `cycle`; its `time_box`, a `start` and an `end`, as its cycle's suspensions move it; what it `expected`, in words; and its `outcome` once its result is recorded, `pass`, `fail` or `neither`, else `null`;
  - `waiting`: each a `subject`, `what` waits and the `command` that takes it.

A day is written `YYYY-MM-DD`. A window's or a time box's `start` or `end` is `null` where an ongoing suspension leaves it none, and any value the files do not give, or that does not read, such as one outside its set, is `null`. A cycle or an experiment whose file does not read is listed all the same, and each of its keys besides `id`, `state` and `why` is `null`, a cycle's `key_results` and `suspensions` too.

## Credits and licence

The method comes from *Running Lean* (third edition, Ash Maurya, 2022). The capability carries the method in its own words and ships no text of the book.

The canvas follows the Lean Canvas, Ash Maurya's adaptation of Alex Osterwalder's Business Model Canvas, both published under the Creative Commons Attribution-ShareAlike 3.0 licence. The capability uses the names of the canvas's boxes as its fields, describes them in its own words, and ships no file under that licence. Wherever it draws a canvas, it draws it with the credit and licence line beneath ([lean-business:DEC-001-lean-business-discipline]).

The names *Running Lean* and *Lean Canvas* may be trademarks of their owners. They are used here only to credit the source.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[lean-business:DEC-001-lean-business-discipline]`. Other capabilities and adopter content use the same form.

## Dependencies

None beyond the backbone. The capability reads no other capability. A later view may read its status's structured form, and the experiments' results may cite evidence records, without either becoming a dependency ([lean-business:DEC-001-lean-business-discipline]).
