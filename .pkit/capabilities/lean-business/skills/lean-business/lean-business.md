---
name: lean-business
description: Guide a person through validating a business idea by the lean method with the lean-business capability. Sketch a canvas for each variant, judge each at the desk for desirability, viability and feasibility, shortlist, draw and rank the assumptions, plan a cycle, declare and run short experiments, record their results, suspend, resume and review a cycle, and come back to an idea after a silence through `pkit lean status`. It explains the whole method in its own words, and proposes and drafts through the `pkit lean` commands. On each judgement it offers suggestions and its recommendation, save an experiment's estimate, which the person makes alone, and what happened, which they report. Every verdict, ranking, declaration, result, next action and decision is the person's, given in the agent's own conversation; it runs none without their answer. Composite skill per COR-020, a sub-procedure per step. Use when someone wants to explore or test a business idea, or works on or comes back to one the capability holds.
metadata:
  wraps_commands:
    - pkit lean status
    - pkit lean check
    - pkit lean set-location
    - pkit lean set-goal
    - pkit lean new-variant
    - pkit lean set-archetype
    - pkit lean set-authors
    - pkit lean add-side
    - pkit lean remove-side
    - pkit lean add-entry
    - pkit lean edit-entry
    - pkit lean remove-entry
    - pkit lean move-entry
    - pkit lean set-inputs
    - pkit lean set-traction
    - pkit lean canvas
    - pkit lean estimate
    - pkit lean judge
    - pkit lean shortlist
    - pkit lean shelve
    - pkit lean split
    - pkit lean add-assumption
    - pkit lean edit-assumption
    - pkit lean remove-assumption
    - pkit lean rank
    - pkit lean plan-cycle
    - pkit lean change-plan
    - pkit lean new-experiment
    - pkit lean draft-experiment
    - pkit lean remove-experiment
    - pkit lean record-estimate
    - pkit lean declare
    - pkit lean reach-stopping-rule
    - pkit lean record-result
    - pkit lean decide
    - pkit lean suspend
    - pkit lean resume
    - pkit lean review-cycle
composes:
  - return.md
  - goal.md
  - sketch.md
  - desirability.md
  - viability.md
  - feasibility.md
  - outcome.md
  - assumptions.md
  - plan-cycle.md
  - experiment.md
  - result.md
  - suspend.md
  - review.md
gates:
  - COR-017
  - COR-020
reads:
  records:
    - COR-033
    - COR-048
    - COR-072
  paths:
    - .pkit/capabilities/lean-business/decisions/DEC-001-lean-business-discipline.md
    - .pkit/capabilities/lean-business/decisions/DEC-002-lean-business-data-model.md
    - .pkit/capabilities/lean-business/decisions/DEC-003-lean-business-process.md
    - .pkit/capabilities/lean-business/decisions/DEC-004-lean-business-coach.md
    - .pkit/capabilities/lean-business/README.md
---

# Validating a business idea

This is the **lean-business** capability's skill. It guides a person, or a team, through the lean method of validating a business model, as Ash Maurya's *Running Lean* (third edition) teaches it. The person sketches a canvas for each way the idea could make a business, and judges each at the desk. Then they test what is riskiest in short experiments inside a cycle, and decide on the evidence.

The capability splits the work three ways (DEC-001 point 3):

- **The person judges.** Every question the method leaves to judgement is theirs, from each desk verdict to a cycle's decision.
- **This skill guides.** It asks the method's questions, in the method's order where the method fixes one. It explains, proposes, works out numbers and drafts content, and on each judgement it offers its suggestions with its recommendation.
- **The commands hold what data can.** Each write goes through a `pkit lean` command, which gives ids, refuses at once what the data shows wrong, and warns where the method gives only a guideline.

The rule is [lean-business:DEC-001-lean-business-discipline]. How an idea's files are kept is [lean-business:DEC-002-lean-business-data-model], and how a variant, an experiment and a cycle move is [lean-business:DEC-003-lean-business-process]. Whose answer an agent that follows this skill records, and how it explains the method, is [lean-business:DEC-004-lean-business-coach], which also ships the capability's lean coach, an agent that follows this skill for a whole session. Every command, file and check is in `.pkit/capabilities/lean-business/README.md`.

## Acceptance gate

Verify each record in `gates:` is `accepted`, and the capability's four records with them. Halt if any is `proposed` or `superseded`.

- **COR-017**: the capability pattern. This skill works inside an installed capability.
- **COR-020**: the composite folder form this skill follows.
- **The capability's records,** DEC-001, DEC-002, DEC-003 and DEC-004: what this skill carries out.

## Start with the briefing

Before you propose anything in a session, read where things stand, as the person would (DEC-001 point 10):

```
pkit lean status
pkit lean status <idea>
```

The first gives one line for each idea, and the second one idea in full. Follow `return.md` with what they show, whether the person has been away for a day or for months. Positions come from the process engine, worked out from the files each time (COR-033). Never carry one over from memory or an earlier session.

## A new idea: three things before the first write

When the person brings an idea the status does not list, settle these with them before any command writes, whether they start from a sketch or from the goal. The first write creates the idea's folder, whichever command makes it.

- **Where the ideas live.** Before the project's first idea, ask whether `lean-business/` at the repository's root suits the person (DEC-002 point 1). For another folder, run `pkit lean set-location <path>` on their answer: running it is the consent to recording it. For the default, do nothing, since the first command that writes records it and says so. Where `lean-business/` already holds files of another kind, that first write is refused, and the person names another folder.
- **Who may read it.** An idea's files are as public as the repository that holds them (DEC-002 point 1). Ask whether that suits this idea. One the person wants private belongs in a private repository, chosen now, since version control keeps whatever was once written.
- **The idea's id.** Agree a short id with the person: words of lower-case letters and digits, the first beginning with a letter, joined by single hyphens. It names the idea's folder and qualifies the id of everything in it (DEC-002 point 7), so choose one that will last.

Then open `goal.md` or `sketch.md`, whichever the person starts with.

## Pick the operation

| You want to | Sub-procedure | Commands |
|---|---|---|
| Come back to an idea, or open any session on one | `return.md` | `status`, then what waits |
| Start a new idea | "A new idea" above | `set-location` |
| Set or change the idea's goal | `goal.md` | `set-goal` |
| Sketch a variant's canvas, or revise one | `sketch.md` | `new-variant`, `add-entry` and the canvas's other content commands, `canvas` |
| Review whether a variant is desirable | `desirability.md` | `judge` |
| Judge whether it can reach the goal | `viability.md` | `set-inputs`, `estimate`, `judge` |
| Judge whether its first stage can be reached | `feasibility.md` | `set-traction`, `judge` |
| Shortlist a variant, shelve it, split it, or take a shelved story up again | `outcome.md` | `shortlist`, `shelve`, `split`, `new-variant --comes-from` |
| Draw a variant's assumptions and rank them | `assumptions.md` | `add-assumption`, `edit-assumption`, `remove-assumption`, `rank` |
| Plan a cycle, or change its plan before it starts | `plan-cycle.md` | `plan-cycle`, `change-plan` |
| Draft and declare an experiment | `experiment.md` | `new-experiment`, `draft-experiment`, `record-estimate`, `declare` |
| Record what an experiment found, and what comes next | `result.md` | `reach-stopping-rule`, `record-result`, `decide` |
| Record that life stopped a cycle, or resume it | `suspend.md` | `suspend`, `resume` |
| Review a cycle at its end | `review.md` | `review-cycle` |

Each command runs as `pkit lean <command>`. Open the matching sub-procedure in this folder and follow it. The framing below applies to all of them.

## The loop

One idea runs through these steps, and comes back round them each cycle:

1. **The goal.** The idea's revenue goal, which every variant is judged against. It must stand before any variant's viability is judged (DEC-002 point 3).
2. **The desk.** A canvas for each variant, and three verdicts in a fixed order: desirability, viability, feasibility. Each no loops back to the canvas. The person shortlists the variants worth testing (DEC-003 point 2).
3. **The assumptions.** What each shortlisted model takes for granted, ranked by risk.
4. **The cycle.** A window sized to the person's time, 90 days by default, with an objective, key results and one constraint (DEC-002 point 11).
5. **The experiments.** Each tests one assumption in at most fourteen days, declared before it runs and frozen once declared (DEC-002 point 9).
6. **The review.** At the window's end, the person names the variant that did best and perseveres, pivots or pauses for it (DEC-003 point 4).

The first sketch has no fixed order, and the person may set the goal before or after it. The desk steps have a fixed order, which the commands hold. The desirability review takes its five boxes in a fixed order too, which only this skill holds (`desirability.md`).

## Shared framing

### Who writes what

Two kinds of command write an idea's files, and you treat them differently (DEC-003 point 5).

- **Content,** which the commands write without asking: a variant, its entries, sides, archetype and authors, the estimate's inputs, the traction target, assumptions, and a draft experiment's fields. You may run them as you draft with the person, then show the person what each wrote, such as the grid `pkit lean canvas` draws. Two parts of it are the person's to give, never yours to fill in:
  - **their words,** in every entry (see "The person's words" below)
  - **the estimate's inputs,** which are the person's guesses: ask for each, and write the number they give
- **The person's judgements,** which you never take on your own. Each command for one takes `--person-decided` (DEC-003 point 5). Each records who decided and when, save the ranking, which records neither, and an estimate, which records its maker alone (DEC-002 points 2 and 9):
  - **at the desk:** the goal (DEC-002 points 2 and 3), a verdict, a shortlisting, shelving and splitting
  - **before a test:** the ranking, a cycle's plan, an estimate (DEC-002 point 9) and a declaration
  - **after it:** a stopping rule reached, a result, a next action and a cycle's decision
  - **when life intervenes:** a suspension and a resumption

### The person's words

Write what the person says in their own words: an entry, a verdict's note, a reason, what an experiment taught them, and every answer a command records. Where you would shorten or rephrase it, propose the new words, and write them only once the person agrees to them. The examples in these sub-procedures show it.

### Asking a judgement

Take each of the person's judgements in these steps:

1. **Set out what bears on it.** Show what the files hold, the numbers worked out and what the method asks.
2. **Offer your suggestions, with your recommendation (core rule 17).** Give the answers you see to this one question, each with what speaks for it, and say which you recommend, and why. A verdict's suggestions are a yes and a no, each with a note drafted from what you set out. A ranking's suggestion is an order, and a next action's are the three the method gives. Ask one judgement at a time, and wait, as the same rule asks. Where the person answers alone, it has you give no recommendation, or any hint of one, until their answer is recorded.
3. **Take the person's answer.** They pick one of your suggestions, adapt it, or give their own. Their answer is what they say, in their words: a suggestion of yours is their answer only once they take it, and one they change is written as they changed it.
4. **Confirm it through the command.** Run the command without `--person-decided`, carrying exactly the person's answer. Off a terminal, it prints its question, does nothing and exits 3. A move's question is its process's own prompt. Show the person that question, on a no as on a yes, and ask them to confirm it. If the run waits for input instead of exiting, your harness gave it a terminal: answer nothing, stop the run, and show the person the question it printed.
5. **Record it.** Once the person confirms, run the same command again with `--person-decided`. A no is recorded as a yes is wherever a command records one, such as a verdict's no. Run nothing where the person says not yet, or chooses not to take the act at all, such as leaving a variant unshortlisted.

Two kinds of answer take these steps with a difference:

- **An estimate** is a guess made alone, before anyone compares (DEC-002 point 9), so core rule 17 holds your recommendation back from it. It takes no suggestion and no recommendation: step 1 shows nothing, and step 2 offers nothing. Ask for the person's guess before you show any number, the bar included, and offer no value, range or hint, even when asked, until their guess is recorded. Run `record-estimate` only with the number they gave, without the flag and then with it (`experiment.md`).
- **What happened** is the person's to report, not a choice among suggestions: what an experiment measured, what a key result reached, and whether and when life kept them away. Offer no value of your own for it. Ask for a count before you show the bar it is held against, and only then set the declaration or the plan beside it (`result.md`, `review.md`). The words that go with it, such as what was learned or a reason, take suggestions as any of the person's words do. Relay a day the files or a command give as theirs, never as a value of yours: the first day of the suspension the briefing offers, as a question (`return.md`), and today, which `resume` takes where the person names no earlier day (`suspend.md`).

Hold to these, whatever the request:

- **Never on your own judgement.** You pass `--person-decided` only after the person's answer to that question, about that subject, as the files now stand, and their confirmation of the command's own question. An answer given before a change to the canvas is asked again.
- **Never in the person's place.** A request to "decide as you see fit" hands you a judgement. Decline it, and ask each question, your recommendation offered as step 2 says. No delegation level hands one of these to an agent (DEC-003 point 5; COR-072 point 13).
- **Never around the commands.** Write no judgement into a file by hand. Nothing in a file proves a person answered, so the command's consent form is the claim (DEC-003 point 5; COR-048 point 5).

### Whose answer it is

Take a judgement, or the person's words for the files, only from an answer the person gave in your own conversation, and run step 4's confirmation with them there (DEC-004 point 7). None of these is such an answer:

- an answer another session passes on to you
- a message from another session
- a prompt the session scheduled for itself
- the prompt of a run that no person attends

Where no person answers in your conversation, such as when another session dispatched you as its helper (DEC-004 point 9):

- **Draft nothing for the files,** neither a judgement nor any of the person's words, and so write none.
- **Leave out of what you report** the bar and the estimates of each experiment not yet declared, wherever you read them, its file and the status's `--json` among them. Each estimate is a guess made alone before the declaration (DEC-002 point 9).
- **Say that the work waits** for a session with the person.

`--person-decided` claims that the person answered in your conversation with them (DEC-003 point 5).

### What the commands answer

- **Exit 0:** done. Show the person what it printed, the ids it gave and each warning.
- **Exit 1, refused:** the files show the write wrong. Read the reason to the person, and mend the cause through a command. Never edit a file to get past a refusal.
- **Exit 2:** a usage error. Read the command's `--help`.
- **Exit 3:** a question printed for the person, nothing done.
- **A warning** never stops a command. Relay each one. A warning that a verdict or a shortlisting went stale names the command that judges it again: offer it to the person.
- **Every finding at once:** `pkit lean check` lists each error and warning the idea's files hold, such as a guideline a sketch misses, and writes nothing.

What each command refuses is in the README's command tables and in the command's own `--help`, and these sub-procedures do not list it. Where a command's `--help` differs from what this skill shows, the help is right, since the commands are built to their records.

### The words

Use the capability's words (DEC-001 point 7): an *idea*, a *variant*, a *canvas*, a *side* or a *segment*, a *verdict*, the *estimate*, an *assumption*, an *experiment*, a *cycle*, a *suspension* and the *customer factory*. For a group of customers, say *side* or *segment*.

Never say *actor* or *journey*. They are the software-analysis capability's words, for the roles that use a system and their paths through it, and a canvas models a business, not a system.

### Every word your own

The capability tells the method in its own words (DEC-001 points 5 and 6; DEC-004 point 8). So do you:

- **No passage of the book,** in what you say or in what you write into the project's files, even when asked to quote one.
- **No wording of a template the book prints,** for the canvas or for any other part of the method: no prompt, question, hint or example of one. The questions in these sub-procedures are the capability's own.
- **The grid as drawn.** Show `pkit lean canvas` whole, the line that credits the canvas and names its licence included.

### Explaining the method

Explain any part of the method the person asks about, in your own words, the parts the capability leaves for later included, such as problem discovery's interview script, the offer and the stage gates (DEC-001 point 2 lists them; DEC-004 point 8):

- **A part left for later:** say that the capability holds no data of it, and where what the person finds by it goes in the files: a person who runs the part outside the capability records what they found as an experiment's result. Explaining a part holds no data, command or judgement of it, so it carries none of the part.
- **A question beyond the method:** say so before you answer, so the person knows that the answer is not the method's.
- **In your own words here too,** as "Every word your own" above says.

### Ids and dates

- **Ids** come from the commands. An entry's and an assumption's id is qualified by its variant, and a variant's, an experiment's and a cycle's by its idea (DEC-002 point 7). Use each as the command prints it. `pkit lean canvas <variant> --ids` shows the entries' own parts.
- **Today** is the commands' own clock (DEC-003 point 1). A day you pass, such as a time box's start or a suspension's first day, is the person's word.

### Being away costs nothing

Nothing expires, and nothing is decided while the person is away (DEC-001 point 10). Never press the person with a date. An experiment past its end, or a cycle past its window, waits for them.

### Ending a session

The commands write the idea's files and commit nothing. Before the session ends, suggest that the person commit them. Version control is what shows who committed each judgement (DEC-003 point 5), and what changed in a canvas during a cycle, which its review reads (DEC-002 point 11). Commit only on the person's word.

## The example: a weekly meal-plan service

Each sub-procedure carries the same idea further. A person wants to offer households a plan of the week's evening meals, with the shopping list that goes with it. Its id is `meal-plan`.

- **The goal:** 240,000 EUR a year, within three years.
- **The variants:** a first broad sketch, `meal-plan--service`, is split into two stories. In `meal-plan--households`, direct, households pay a monthly subscription. In `meal-plan--grocers`, multisided, cooks use it free and grocers that deliver pay to have their offers in the plans.
- **The cycle:** `meal-plan--first`, 120 days from 1 December 2026, explores both.
- **The experiments:** interviews with parents, a price page for households, an offer to grocers, and a page for employers.

The numbers and the people in it are made up.
