# Recording a result and the next action

An experiment is *due* once its time box has ended, or once a generative experiment's stopping rule is recorded as reached (DEC-003 point 3). Its result is held against what it declared, and whether it passed is worked out, never chosen (DEC-002 point 10). What was measured, what was learned and what comes next are the person's.

## Before you start

- **The cycle is not suspended.** While it is, no result, stopping rule or decision is recorded, and each command names `resume`. Take `suspend.md` first.
- **The result waits.** Nothing expires: an experiment due for months is taken as one due today.

## 1. A generative experiment that ended early

A generative experiment may reach its stopping rule before its time box ends, such as the interviews that stopped bringing anything new. On the person's word that it did, and within its time box, record it as the dispatcher's "Asking a judgement" says:

```
pkit lean reach-stopping-rule <experiment> --person-decided
```

It makes the experiment due. An evaluative experiment has no such end, and runs its whole time box.

## 2. Ask what happened, then set it beside what was declared

Ask first, one at a time, before you read the bar back, so the count is taken from the evidence and not toward the bar:

- **What was measured:** the count or the number, at the step it declared.
- **Where the evidence lies:** a link, a folder, or a sentence saying where.
- **What was learned,** in the person's words.

Then show the declaration as it was frozen: the bar, its direction, and each author's estimate. The result is held against that, the expectation fixed before the run, never one memory reshapes after it (DEC-001 point 10).

Three cases give no comparison, and work out to neither a pass nor a fail (DEC-002 point 10):

- **Nothing was measured,** such as an experiment declared and never run. Leave out `--measured`.
- **A suspension spoiled it:** the cycle was suspended while its time box ran, and the absence spoiled what it measured. Record it with `--spoiled`, and offer to declare the test again as a new experiment.
- **A generative experiment cut short by its time box:** its count stayed below its fit, and its stopping rule was never reached. Record the count as measured. The test ended before it could either pass or fail.

## 3. Record the result

Show the person what you will record, in their words, run the command without the flag to show its question, and on their confirmation run:

```
pkit lean record-result <experiment> [--measured <number>] [--spoiled] --evidence "<where>" --learned "<their words>" --person-decided
```

The command says what it works out to: a pass, a fail, or neither. Read it out as it is. Never argue a fail into a pass, nor read the bar again in a kinder way. A result recorded again before the decision replaces the earlier one.

## 4. The next action

The next action is the person's (DEC-002 point 10). Explain the three:

- **Correct course:** the test or the model was off, and a changed test comes next, as a new experiment.
- **Double down:** it worked, and the next experiment does more of what worked.
- **Stop:** the experiment ends here, and nothing follows from it.

Say which you recommend, and why, and ask which they take. Then confirm their answer through the command's question, and on their confirmation run:

```
pkit lean decide <experiment> correct-course|double-down|stop --person-decided
```

## 5. What follows

- **The assumption's reading changes,** worked out from its last decided experiment: supported, refuted or inconclusive (DEC-003 point 8).
- **A refuted assumption asks for a canvas change.** The method removes or rewrites the entry the test refuted, through the content commands (`sketch.md`). That makes the verdicts that judged it stale. Offer to judge them again and to shortlist again (`outcome.md`).
- **Correcting course,** or declaring a spoiled test again, starts at `experiment.md`.

## Example

On 10 December, the person has run twelve interviews, and the last three brought nothing new. On their word, you record the stopping rule reached for `meal-plan--parent-interviews`. You ask what they counted: eight parents told of an evening a week lost to planning. Only then do you read back its bar, seven such parents, and their own guess of six. You ask where the notes are and what they learned, and write both in their words:

```
pkit lean record-result meal-plan--parent-interviews --measured 8 --evidence "Notes of the twelve interviews, in the idea's shared folder" --learned "Parents in their first months back plan in a rush. Those back a year have a routine." --person-decided
```

It passes. You recommend doubling down on parents in their first months back, since they told the burden most sharply, and ask what comes next. The person doubles down on them, and you record it.

The price page ended on 28 December. You ask what it measured: three households paid. Its bar was at least 6, so it fails. Two of the visitors asked whether their employer could pay instead. You recommend correcting course toward employers, since that question came unprompted. The person decides to correct course, and declares a page for employers as a new experiment.

The grocers offer ran through the person's absence in January. Two grocers asked for a call that nobody answered. Once the cycle has resumed, the person records it as spoiled, and its assumption reads inconclusive. They declare the offer again for February.
