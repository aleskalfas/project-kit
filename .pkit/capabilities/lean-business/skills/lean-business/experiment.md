# Drafting and declaring an experiment

An *experiment* tests one assumption in a time box of fourteen days at most. It is declared before it runs, and judged against what it declared (DEC-001 point 7). A declaration is frozen: a correction comes as a new experiment, never as an edit (DEC-002 point 9). The draft is content you may write with the person. The estimates and the declaration are the person's.

## Before you start

- **An open cycle explores the variant.** A cycle is open while it is planned or running (DEC-003 point 7). Where none is, take `plan-cycle.md` first.
- **The variant's shortlisting stands,** and is not stale (`outcome.md`).
- **Its assumptions are ranked** (`assumptions.md`).

## 1. Choose the assumption

Propose the riskiest untested assumption of a variant the open cycle explores. The person may choose another. Where a riskier one stays untested, `declare` will warn, and the order of work is theirs.

## 2. Choose the kind

- **Generative,** to discover. It learns until a stopping rule ends it, and its result is held against a count set in advance. Talking with customers about their problem is the usual first experiment, and the person runs the interviews outside the capability. Problem discovery fits two such experiments of two weeks at most, a broad one and then a narrow one (DEC-001 point 2).
- **Evaluative,** to measure traction. One action, one number measured at a step of the customer factory, held against an expected outcome. It runs its whole time box, since stopping it on a good early reading would bias it (DEC-003 point 3).

Start the draft:

```
pkit lean new-experiment <idea>--<experiment> --kind generative|evaluative --assumption <assumption> --cycle <cycle> [--author <name>]...
```

## 3. Draft what it does

Write each field with `pkit lean draft-experiment <experiment>` as you agree it, and `--clear <field>` to take one out.

- **The time box,** `--start` and `--end`: fourteen days at most, starting no earlier than the day it is declared, and inside the cycle's window. A test that seems to need longer aims lower, or becomes two experiments. A time box is never lengthened.
- **A generative experiment:** `--learn`, what it sets out to learn, and `--stopping-rule`, what ends it early, such as a number of interviews, or a run of them that brings nothing new.
- **An evaluative experiment:** `--action`, its one action, and `--metric`, the step of the customer factory it measures. Measure what people do, such as paying, signing up or coming back, not what they say they would do.
- **An evaluative experiment's control:** `--control cohorts`, compared with earlier customers, or `--control split --exposed <share>`, where only a share of people meet the action.

## 4. Each author's estimate, made alone

Each author guesses the number the result will reach, alone, before anyone compares (DEC-002 point 9). An estimate you suggest is not made alone, so:

- **Ask for the person's guess before you show any number** of yours, the expected outcome included.
- **Never propose a value,** a range or a hint.
- **Record their guess** on their answer, which records them as its maker:

  ```
  pkit lean record-estimate <experiment> <their guess> --person-decided
  ```

- **In a team,** each author runs `record-estimate` themselves, so each guess carries its maker's name. A second guess by the same person replaces their first.

## 5. Set the bar the result is held against

Only now work out the expected number with the person, from the model rather than from hope:

- **A generative experiment:** `--fit "<count>/<what it counts>"`, the count its result must reach to count as fit, set in advance. Without it, any result could be read as a pass after the fact.
- **An evaluative experiment:** `--direction at-least|at-most`, with `--threshold <number>` or `--range <low> <high>`, a range the person is nine-in-ten sure of. Name where the number comes from, `--source estimate` or `--source traction-target`. Add each effect known in advance that may move it, such as a holiday, with `--effect`.

## 6. Declare it

1. **Show the whole draft,** each field as written, and the estimates beside it.
2. **Say what declaring does:** the declaration is frozen, and a time box starting today runs at once.
3. **Get the question,** by running `pkit lean declare <experiment>` without the flag, and ask it.
4. **On the person's yes:**

   ```
   pkit lean declare <experiment> --person-decided
   ```

The command records who declared it and when, the shortlisting it rests on and the declaration's fingerprint. It refuses a missing field, no estimate, a time box over fourteen days or starting before today, a stale shortlisting, and a cycle neither planned nor running.

After that, the experiment moves on its dates with nobody acting: declared, then running, then due (DEC-003 point 3). A draft never declared may be removed with `remove-experiment`. While the cycle is suspended, a draft can still be written, and the estimate and the declaration wait for `resume`.

## Example

The open cycle `board-game--first` explores `board-game--hosts`, whose riskiest assumption is `dates-cost-hours`. The person will interview hosts, so it is generative:

```
pkit lean new-experiment board-game--host-interviews --kind generative --assumption hosts--dates-cost-hours --cycle first
pkit lean draft-experiment board-game--host-interviews --learn "Whether hosts of regular game nights lose real time settling dates" --stopping-rule "Twelve interviews, or three in a row that bring nothing new" --start 2026-12-01 --end 2026-12-14
```

You ask how many of twelve hosts the person thinks will tell of an evening lost to settling a date, and say nothing of your own. They guess six, and you record it with `--person-decided`. Then you agree the bar: seven hosts who tell of an evening lost to settling a date. You draft it as the fit, show the whole draft, and ask the declaring question. They answer yes on 29 November, and the experiment is declared, starting on 1 December.

Their second experiment, `board-game--price-page`, is evaluative. It tests `four-percent-pay` with one action: a page offering early access at 4 EUR a month, paid at sign-up, shown in two forums. Half the visitors see it, and half a free waiting list, so its control is a split with half exposed. The person guesses 4 paying hosts. Only then do you work out the bar from the estimate's conversion: of about 150 visitors who see the price, 4% is 6. They declare it at least 6, sourced from the estimate, with the holidays as an effect, from 15 to 28 December.
