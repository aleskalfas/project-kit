---
name: lean-business
description: Guide a person through validating a business idea by the lean method with the lean-business capability. Sketch a canvas for each variant of the idea, judge each at the desk for desirability, viability and feasibility, shortlist, draw and rank the assumptions, plan a cycle, declare and run short experiments, record their results, suspend and resume a cycle, review it, and come back to an idea after a silence through `pkit lean status`. The skill explains, proposes and drafts through the `pkit lean` commands. Every verdict, ranking, declaration, result, next action and decision is the person's, and it runs none without their answer. Composite skill per COR-020, one sub-procedure for each step of the loop. Use when someone wants to explore or test a business idea, works on an idea the capability holds, or comes back to one.
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
    - .pkit/capabilities/lean-business/README.md
---

# Validating a business idea

This is the **lean-business** capability's skill. It guides a person, or a team, through the lean method of validating a business model, as Ash Maurya's *Running Lean* (third edition) teaches it. The person sketches a canvas for each way the idea could make a business, and judges each at the desk. Then they test what is riskiest in short experiments inside a cycle, and decide on the evidence.

The capability splits the work three ways (DEC-001 point 3):

- **The person judges.** Every question the method leaves to judgement is theirs, from each desk verdict to a cycle's decision.
- **This skill guides.** It asks the method's questions, in the method's order where the method fixes one. It explains, proposes, works out numbers and drafts content.
- **The commands hold what data can.** Each write goes through a `pkit lean` command, which gives ids, refuses at once what the data shows wrong, and warns where the method gives only a guideline.

The rule is [lean-business:DEC-001-lean-business-discipline]. How an idea's files are kept is [lean-business:DEC-002-lean-business-data-model], and how a variant, an experiment and a cycle move is [lean-business:DEC-003-lean-business-process]. Every command, file and check is in `.pkit/capabilities/lean-business/README.md`.

## Acceptance gate

Verify each record in `gates:` is `accepted`, and the capability's three records with them. Halt if any is `proposed` or `superseded`.

- **COR-017**: the capability pattern. This skill works inside an installed capability.
- **COR-020**: the composite folder form this skill follows.
- **The capability's records,** DEC-001, DEC-002 and DEC-003: what this skill carries out.

## Start with the briefing

Before you propose anything in a session, read where things stand, as the person would (DEC-001 point 10):

```
pkit lean status
pkit lean status <idea>
```

The first gives one line for each idea, and the second one idea in full. Follow `return.md` with what they show, whether the person has been away for a day or for months. Positions come from the process engine, worked out from the files each time (COR-033). Never carry one over from memory or an earlier session.

## Pick the operation

| You want to | Sub-procedure | Commands |
|---|---|---|
| Come back to an idea, or open any session on one | `return.md` | `status`, then what waits |
| Set or change the idea's goal | `goal.md` | `set-location`, `set-goal` |
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

The first sketch has no fixed order, and the person may set the goal before or after it. The desk steps and the desirability review have a fixed order, and the commands hold it.

## Shared framing

### Who writes what

Two kinds of command write an idea's files, and you treat them differently (DEC-003 point 5).

- **Content,** which you may write as you draft: a variant, its entries, sides, archetype and authors, the estimate's inputs, the traction target, assumptions, and a draft experiment's fields. Run the command, then show the person what it wrote, such as the grid `pkit lean canvas` draws. The person's words win over yours, so ask before you rephrase what they said.
- **The person's judgements,** which you never take on your own. Each command for them records who decided and when, and takes `--person-decided`:
  - **at the desk:** the goal, a verdict, a shortlisting, shelving and splitting
  - **before a test:** the ranking, a cycle's plan, an estimate and a declaration
  - **after it:** a stopping rule reached, a result, a next action and a cycle's decision
  - **when life intervenes:** a suspension and a resumption

### Asking a judgement

Take each of the person's judgements in these steps:

1. **Get its question.** Run the command without `--person-decided`. Off a terminal, it prints its question, does nothing and exits 3. A move's question is its process's own prompt.
2. **Set out what bears on it.** Show what the files hold, the numbers worked out and what the method asks. You may say which way you lean and why.
3. **Ask the one question,** and wait. Ask one judgement at a time.
4. **Run it on the answer.** Once the person has answered that question in the conversation, run the command with `--person-decided`, with exactly what they answered. Where they answer no, or not yet, run nothing.

Hold to these, whatever the request:

- **Never on your own judgement.** You pass `--person-decided` only after the person's answer to that question, about that subject, as the files now stand. An answer given before a change to the canvas is asked again.
- **Never in the person's place.** A request to "decide as you see fit" hands you a judgement. Decline it, and ask each question. No delegation level hands one of these to an agent (DEC-003 point 5; COR-072 point 13).
- **Never around the commands.** Write no judgement into a file by hand. Nothing in a file proves a person answered, so the command's consent form is the claim (DEC-003 point 5; COR-048 point 5).

### What the commands answer

- **Exit 0:** done. Show the person what it printed, the ids it gave and each warning.
- **Exit 1, refused:** the files show the write wrong. Read the reason to the person, and mend the cause through a command. Never edit a file to get past a refusal.
- **Exit 2:** a usage error. Read the command's `--help`.
- **Exit 3:** a question printed for the person, nothing done.
- **A warning** never stops a command. Relay each one. A warning that a verdict or a shortlisting went stale names the command that judges it again: offer it to the person.
- **Every finding at once:** `pkit lean check` lists each error and warning the idea's files hold, such as a guideline a sketch misses, and writes nothing.

Where a command's `--help` differs from what this skill shows, the help is right, since the commands are built to their records.

### The words

Use the capability's words (DEC-001 point 7): an *idea*, a *variant*, a *canvas*, a *side* or a *segment*, a *verdict*, the *estimate*, an *assumption*, an *experiment*, a *cycle*, a *suspension* and the *customer factory*. For a group of customers, say *side* or *segment*. The words of software analysis for its roles and their paths name no part of a business model.

### Every word your own

The capability tells the method in its own words (DEC-001 points 5 and 6). So do you:

- **No passage of the book,** in what you say or in what you write into the project's files.
- **No prompt, question, hint or example of the canvas template.** The questions in these sub-procedures are the capability's own.
- **The grid as drawn.** Show `pkit lean canvas` whole, the line that credits the canvas and names its licence included.

### Ids and dates

- **Ids** come from the commands. An entry's and an assumption's id is qualified by its variant, and a variant's, an experiment's and a cycle's by its idea (DEC-002 point 7). Use each as the command prints it. `pkit lean canvas <variant> --ids` shows the entries' own parts.
- **Today** is the commands' own clock (DEC-003 point 1). A day you pass, such as a time box's start or a suspension's first day, is the person's word.

### Being away costs nothing

Nothing expires, and nothing is decided while the person is away (DEC-001 point 10). Never press the person with a date. An experiment past its end, or a cycle past its window, waits for them.

## The example: a board-game idea

Each sub-procedure carries the same idea further. A person wants to build a platform for people who play board games together. Its id is `board-game`.

- **The goal:** 120,000 EUR a year, within three years.
- **The variants:** a first broad sketch, `board-game--platform`, is split into two stories. In `board-game--hosts`, direct, the hosts of regular game nights pay a subscription. In `board-game--venues`, multisided, players use it free and game cafés pay to fill their tables.
- **The cycle:** `board-game--first`, 120 days from 1 December 2026, explores both.
- **The experiments:** interviews with hosts, a price page for hosts, an offer to cafés, and a page for clubs.

The numbers and the people in it are made up.
