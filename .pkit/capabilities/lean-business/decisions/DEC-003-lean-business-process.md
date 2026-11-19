---
id: DEC-003
title: Three keyed processes carry the loop, and every judgement in them is the person's
status: accepted
date: 2026-11-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** the capability binds three process definitions to the backbone's process engine: a variant's desk stage, an experiment and a cycle. Where each stands is read from its data whenever it is asked, and dates move an experiment and a cycle on with nobody acting. Each judgement in them is the person's, and no delegation level hands one to an agent: a verdict, a shortlisting, a declaration, an experiment's next action, a cycle's suspension and resumption, and a cycle's decision. The person may suspend a running cycle when life interrupts, and no move extends its window. An idea runs one cycle at a time, exploring one or more shortlisted variants, and an experiment is declared only on a shortlisted variant that the open cycle explores. A cycle's review names the variant that did best and ends in persevere, pivot or pause for it, and a pivot must name its evidence. An assumption's outcome and an idea dropped are read from the data, never states of a process.

## Context

The capability guides one loop of the lean method (DEC-001 point 1), whose facts are data files (DEC-002). Three of those facts move through stages a person needs to see and that some moves must respect: a variant through its desk checks, an experiment from its draft to its decision, and a cycle from its plan to its review. Other facts move only as a reading of these: whether an assumption is supported, and whether an idea is dropped.

The core layer supplies the process substrate: a content-free engine that resolves each subject's position live from reality, checks each move's gate, and explains where a subject stands (COR-033). Every gate must be a predicate the engine evaluates, or a record of an authorisation given by another authority than the one it gates (COR-033 P4). The substrate supplies keyed subjects, many under one definition (COR-032), and a first-class wait, whose question a person's move carries (COR-034). It supplies connections between processes, which the engine never evaluates (COR-038), and the levels at which agents decide in a person's place, where every record places its own questions (COR-072 point 13). The engine does not enforce who may take a move. The caller does (the process area's engine page, "The operations").

## Decision

**Three keyed process definitions carry the loop's stages, each position read from its subject's data and each gate a predicate over it. The person takes every move that judges, at no delegation level, and the script takes the rest, after a date or a suspension the person recorded.**

### 1. Three definitions, one kind of subject each

- **The desk stage,** over a variant; **the experiment,** over an experiment; **the cycle,** over a cycle. Each is keyed (COR-032), its subject named by the subject's id (DEC-002 point 7).
- **Position read from the data.** Each definition detects in the `classified` mode: one predicate reads the subject's file, the dates where they count and, for an experiment, its cycle's suspensions, and answers which state the subject is in (COR-033 P5). The capability's commands and status read positions from the engine, and never work one out again.
- **What the data says first.** A recorded judgement outranks a date, and an outcome outranks a verdict. A cycle's decision outranks a suspension, and an ongoing suspension outranks the cycle's dates. So a decided experiment reads decided whatever its dates say, and a shortlisted variant reads shortlisted whatever its verdicts say. Where the data breaks an invariant, such as a decision recorded before an evaluative experiment's time box ended, the position follows the data and the check fails (DEC-002 point 14).
- **Days, not hours.** Every date the definitions read is a calendar day. A window runs from its first day through its last, passing over the days its cycle was suspended. A time box runs from its first day through its last in the calendar, its first day moved later only where a suspension covered its start (DEC-002 point 12). *Today* is the local date where the command runs. Only the capability's test suite sets it, and no command takes it from a caller, since every recorded *when* comes from that clock, and a date a caller could set would defeat the check's tests of order, such as a decision recorded before a time box ended (DEC-002 point 14). A suspension's first day and the day it resumed are the person's word, as a time box's dates are, while the day it was recorded comes from the clock, so the check can hold them against it.
- **A canvas has no process.** It has versions and no final state (DEC-002 point 4). The desk stage reads a variant's verdicts and outcome, never its boxes' content, except in its gates' checks of completeness.
- **An assumption has no process,** and neither has an idea (point 8).
- **The engine's journal** is kept as the project chooses (COR-033 P7). The capability keeps no audit of its own, and version control is its audit (DEC-002 point 13).

### 2. A variant's desk stage

Each state means what the person has judged of the variant so far:
- **sketched:** a canvas exists, and desirability has no standing yes.
- **desirable, viable, feasible:** the person's yes stands on that step and on each step before it, in that order. The position is the longest run of standing yes verdicts from the first step.
- **shortlisted:** the person chose the variant to test.
- **shelved,** with its reason, and **split,** into the variants it names.

Shortlisted, shelved and split are the variant's outcomes, and the definition's terminal states, so a variant waits on nobody there. Shelved and split are final. Shortlisted keeps the moves below.

Since shortlisted keeps moves, no process composes the desk stage or folds over its outcomes. Composition and cascade read a terminal state as settled (COR-036, COR-037), and a shortlisting can still be withdrawn. The experiment's gate reads a shortlisting live, through the desk stage's own predicate (point 7), which is no such reading. The stage gates DEC-001 point 2 leaves for later arrive as a definition of their own, never as states of this one, which is why no later version needs to add a state here (point 6).

What each move needs:
- **A yes on the next step** is the person's move into that step's state. Its gate checks that each box the step judges holds an entry, and that each step before it has a yes that is not stale (DEC-002 point 13). A missing link between entries draws the check's warning, not a refusal (DEC-002 point 14):
  - desirability judges the customer side: the segments, the early adopters, the existing alternatives, the problems and the unique value proposition
  - viability judges the model against the goal: the idea's goal, the revenue streams and the estimate's inputs, through the one predicate the check shares (DEC-002 point 14)
  - feasibility judges whether the first stage's target can be reached, and needs the target
- **A no on the next step** is recorded as the verdict and moves nothing. The variant stays until its canvas is revised and the step judged again, so a no loops back to the canvas, as the method's desk steps do.
- **A no on a step already passed** is the person's move back, to the state before that step. The command clears the verdicts on the steps after it, since they rested on what the no overturns, and version control keeps them. So a later yes on the step moves the variant one step on, never past steps nobody judged again.
- **A yes on a step already passed** moves nothing, and replaces the verdict, which is how a stale verdict is made fresh.
- **Into shortlisted:** a yes on all three steps, none stale, and the person's shortlisting, which records its fingerprint (DEC-002 point 5).
- **At shortlisted,** the person may judge a step again. A yes moves nothing, and a no is a move back that withdraws the shortlisting, as a no on a passed step is. **Shortlisting again** is the person's move from shortlisted to itself, under the shortlisting's gate, and takes the shortlisting's fingerprint anew. So a variant whose canvas or goal changed is tested again only once the person has judged it again.
- **Into shelved:** from any state but shelved and split, shortlisted included, with a reason. **Into split:** from sketched or a verdict's state, naming the variants it was split into, each of which exists and names this one.
- **A stale verdict holds the position.** The status shows it stale, and the gates that rest on it refuse it. So an edit to a canvas never moves a variant back silently, and nothing new rests on a judgement the canvas outgrew.
- **Taking a shelved story up again** is a new variant, which names the one it comes from.

### 3. An experiment

- **drafted:** a file exists, and its declaration is not recorded. A draft that is never declared is removed, and nothing records it.
- **declared:** its declaration is recorded, and its time box has not started.
- **running:** its time box has started and not ended.
- **due:** its time box has ended, or a generative experiment's stopping rule is recorded as reached, and no decision is recorded.
- **decided:** its result and its next action are recorded. It is the definition's one terminal state.

Declared, running and due read the time box as its cycle's suspensions move it, and a suspension moves only a time box that had not started by its first day (DEC-002 point 12). The detection reads them through the one predicate that also works out where the cycle's own window falls, so an experiment and its cycle never disagree on a day.

What each move needs:
- **Declaring** is the person's move, into declared, or straight into running where the time box starts on the day it is declared. Both moves carry one gate, which checks:
  - every field its kind needs (DEC-002 point 9)
  - a time box of fourteen days at most, starting no earlier than the day it is declared
  - at least one estimate
  - a shortlisted variant, which the open cycle it names explores (point 7)
- **Running and due follow the dates.** The definition declares the moves into them as the script's, gated on the same facts their detection reads, the early stopping rule included, so its path shows whole and no command takes them. So are the moves back, from due to running, and from running or due to declared, which a suspension recorded late brings where it moves a time box that had not started by its first day: one that has resumed can make a due experiment run again, and one still ongoing can leave a time box it reached with no start yet. A suspension that began after the time box started brings no move back, since it leaves the time box's dates as they were. No command takes these either, since they follow from the cycle's data as the others follow from a date. A generative experiment's stopping rule, recorded as reached on the person's word, makes it due early. An evaluative one runs its whole time box, since stopping it on a good early reading would bias its result.
- **Deciding** is the person's move, from due. Its gate checks that the result and a next action are recorded, with who decided and when, and that its cycle is not suspended. Pass or fail is worked out, never chosen (DEC-002 point 10).
- **While its cycle is suspended,** an experiment whose time box started before the suspension's first day keeps its dates. Its days pass in the calendar, since the world goes on answering it, so it runs and becomes due when its end passes, as any experiment does, and a due or decided one stays as it was. One whose time box had not started is moved by the days the suspension covers, so it stays declared while the suspension is ongoing (DEC-002 point 12). No experiment takes any of the person's moves or acts until the cycle resumes. Deciding's gate refuses, and the commands record no result and no stopping rule, and name the move that resumes the cycle. So the result of an experiment that became due waits for the person, recorded once the cycle has resumed. If the absence spoiled it, the person records the measurement as spoiled, which works out to neither pass nor fail, so its assumption reads inconclusive (DEC-002 point 10), and declares it again as a new experiment.
- **No move back to drafted.** A declared experiment is frozen, so no move takes it back to drafted, and a time box is never extended. A suspension of its cycle moves where a time box not yet started falls in the calendar, leaves one already started on its dates, and adds no day to either. A correction is a new experiment.
- **Declared and not run** still reaches due and is decided: its result records that nothing was measured, which works out to neither pass nor fail.

### 4. A cycle

- **planned:** the variants it explores, its window, objective and constraint are recorded (DEC-002 point 11), and its window has not started. The window is sized now, and may still change.
- **running:** its window has started, its end as worked out (DEC-002 point 12) has not passed, and no suspension is ongoing. Its plan is frozen.
- **suspended:** a suspension is ongoing. The person's life has stopped the cycle, and none of its days count toward the window, or toward the time box of an experiment that had not started by the suspension's first day. An experiment already running keeps its dates (point 3). Its plan stays frozen.
- **in review:** its window as worked out has ended, and no decision is recorded.
- **decided:** the person's decision is recorded, with who decided and when. It is the definition's one terminal state.

What each move needs:
- **Planning is no move.** A cycle whose plan is recorded is planned, as an experiment's file is drafted. So no gate keeps a plan's rules, and the command that plans or changes a plan refuses any plan DEC-002 point 11 makes an error, such as a second undecided cycle of the idea, and any variant that is not shortlisted. The check fails what the files can show (DEC-002 point 14).
- **Running and in review follow the dates,** as an experiment's do (point 3). The review comes at the window's end as worked out: its last planned day, moved later by the days the cycle was suspended.
- **Suspending is the person's act, and the move it brings is the script's.** The person records a suspension, with its reason and its first day, and the command holds the act to the person as it holds a move (point 5). It refuses a suspension that breaks DEC-002 point 12's rules, through the predicate the check shares. The definition declares the move into suspended as the script's, gated on the ongoing suspension its detection reads. The command that records the suspension then takes that move, naming the origin it read before the write, so a project's journal shows a suspension as it shows a resumption (the process area's README, "Seam-ordering contract"). It is no `user` move, since the engine reads a state that a `user` move leaves as waiting on the person while no move of the script's is open there (the process area's shape page, "How each wait clears"). A running cycle's move into review is not open until its window ends, so every running cycle would read as waiting on the person, though it waits on nobody.
- **Recorded late.** A first day earlier than today records an absence late, and DEC-002 point 12 keeps a suspension off every day on which the person recorded work on the cycle. A suspension may be recorded once the window has run out, where its first day lies within the window as worked out: the person whose absence outlasted the window has again the days the cycle had left when they stopped. So the move into suspended runs from in review too, and so does the move from in review back to running, which an absence already over brings. Both are the script's, and the command that records the suspension takes them. Time that ran out while the person was working is never given back so. And a suspension recorded late is refused where an act already recorded would read with it as one its gate refuses, such as the goal set at the review, or an experiment's or the cycle's decision, so it takes a cycle back from in review to running only where nothing recorded since needed the window ended (DEC-002 point 12).
- **Resuming** is the person's move, from suspended to running, so a suspended cycle waits on the person (point 6). The person gives the day the cycle resumed, today unless they name an earlier one, and the move's gate checks that the suspension now has a day of resuming that DEC-002 point 12's rules allow. The window, and each time box the suspension reached before it started, then fall later by the days it covered, so the cycle, and each experiment not yet started, has the days it had left when it stopped. An experiment that was running keeps its dates, and its result, once due, waits for the person (point 3).
- **An absence already over** is one act: the command records the suspension with its first day and the day the cycle resumed at once.
- **While the cycle is suspended,** it moves on no date, and nothing on it or its experiments takes a move or an act of the person's but resuming: nothing is declared in it (point 7), and its experiments wait for the person, though one already running comes due on its dates (point 3). The desk stage is not the cycle's, so a suspension holds none of its moves.
- **No move extends a running window.** Once the window has started, no move changes its dates or adds a day to it, and the plan stays frozen (DEC-002 point 11). Time that ran out while the person was working goes to the review, which perseveres into another cycle on the same key results, or pauses. Persevering on a missed objective draws the warning below, and is not refused.
- **Deciding** is the person's move, from in review. Its gate checks that each key result's reach is recorded, that the review names its winning variant among those the cycle explored, neither shelved nor split for persevere or pivot, since those outcomes are final, and one decision of three for that variant, with its reasons:
  - **persevere:** the winning variant's model goes on into the next cycle, as the method has it where its objective was met
  - **pivot:** the winning variant's model changes, on an insight that could reach the objective in one more cycle. The gate checks that the review names at least one decided experiment as its evidence, of whichever variant, since a pivot without evidence is a guess and what one variant's test found can show where another should turn.
  - **pause:** the idea's work stops for now, at a dead end or out of resources, since not even its winning variant justifies another cycle yet
- **The winning variant.** Where the cycle explored several, the person names the one that did best, as the method's review leads with it (*Running Lean*, ch. 11, Assemble a Progress Report Pitch Deck, Set context). Where it explored one, the command records that one.
- **The other variants it explored keep their outcomes.** The review decides nothing for them. The person shelves one through the desk stage's own move, with its reason, and one left shortlisted may be explored again by a later cycle.
- **No "stop".** The method ends a cycle in one of these three, and has no separate stop. A dead end is a pause, and ending an idea is shelving its variants (point 8). "Stop the experiment" is one experiment's next action, never a cycle's decision.
- **Persevering where the winning variant missed the objective** passes the gate and draws a warning from the command and from the check (DEC-002 point 14). Whether a near miss still justifies the model is the person's judgement.
- **The review waits on no experiment.** The status lists the cycle's experiments still undecided, and the decision does not wait for them.

### 5. Who takes each move

- **The person's moves:** a yes on a variant's next step, a no on a step already passed, the shortlisting and shortlisting again, shelving and splitting a variant, declaring an experiment, deciding it, resuming a cycle, and deciding a cycle. Each carries `authorisation: user`.
- **The person's acts that take no move of their own,** under the same rule: a no on the next step, a yes on a step already passed, an assumption's rank, a cycle's plan and each change to it while the cycle is planned, a result recorded before the decision, a generative experiment's stopping rule reached, whose effect the date's move covers, and a cycle's suspension, whose effect the script's moves into suspended, and from in review back to running, cover.
- **The script's moves:** the moves the dates make, and those that follow a suspension the person recorded (points 3 and 4). No move is an agent's own.
- **The judgement is the move's authorisation, not its gate.** Each gate is a predicate over the data, which the engine evaluates (COR-033 P4). Whether a person, not an agent, made the judgement is the authorisation's question, and no file an agent can write tells the two apart. So the caller holds the move to the person, and the record claims no checkable trace of another authority for the judgement: the last bullet of this point says what shows it instead.
- **The caller holds them to the person.** The engine does not enforce a move's authorisation, so the capability's commands do, in the consent forms of the backbone's configuration (COR-048 point 5):
  - at a terminal, the command asks the move's question, and moves only on a yes
  - off a terminal, it moves only with an explicit flag that says the person decided, which an agent passes only once the person has answered in the session
  - with neither, it moves nothing, and prints the question
  - each judgement records who decided it and when (DEC-002 point 2)
- **At no delegation level.** This record keeps each of these questions the person's, and places none at a level (COR-072 point 13). So at every level, ask to accept, no agent decides one in the person's place.
- **What an agent does.** It explains, proposes, works out the numbers, drafts a declaration, and runs a command on the person's word.
- **What checks it.** Nothing in a file proves that a person answered. The flag puts the claim in the command's run, and version control shows who committed each judgement. A judgement written into a file by hand, around the commands, passes as any other edit does, and reaches a person only in review.

### 6. The waits

- **One wait for each definition,** `awaiting-human`, on its subject (COR-034). A subject waits on the person while a move of the person's is its way forward: a variant before its outcome, a draft, an experiment that is due, and a cycle suspended or in review. Nothing expires while it waits, however long that is (DEC-001 point 10).
- **Each person's move carries its question** as its prompt, such as whether a variant is desirable, whether to declare an experiment that cannot change once declared, what an experiment found and what comes next, whether the person is back to resume a cycle, or which variant did best and whether to persevere, pivot or pause for it.
- **No wait for a date.** A definition declares one wait, and the person's matters most. The dates are read by detection, so an experiment or a cycle moves on when its date comes, and the status shows the days left. A position a date reached is no move taken, so the journal, where the project keeps one, shows no entry for it.
- **What the status shows of a date.** The engine's status shows a subject that waits only on a date, an experiment declared or running or a cycle planned or running, as having no legal move. The capability's status says what it waits for: the day its time box or window starts or ends, as worked out (DEC-002 point 12). Under an ongoing suspension no such day exists yet for the cycle, or for an experiment whose time box the suspension moved, and the status names the cycle's resumption as what the subject waits on. An experiment already running when the suspension began keeps its days, and the status shows them.
- **Declared from the start.** Every state of the three definitions, an experiment's running and due and a cycle's suspended among them, is in its first version, so no later version needs to add a state or a wait under live subjects.

### 7. An experiment needs a shortlisted variant that an open cycle explores

- **A shortlisted variant.** An experiment is declared only on an assumption of a variant whose shortlisting stands and is not stale. The method tests only what the desk stage let through.
- **An open cycle that explores it.** A cycle is *open* while it is planned or running. An experiment is declared only in an open cycle, never in one that is suspended or reached its review, and only on a variant that cycle's plan names. An idea has one such cycle at most, since it has at most one undecided (DEC-002 point 11).
- **Each is a gate, and an edge declared.** The declaring move's gate checks both, through the predicates the desk stage's and the cycle's detections use, so a gate and a position never disagree. The definition declares each connection as a `depends_on` entry, `gates-on-readiness` and `pull`, toward the desk stage and the cycle (COR-038), so the wiring is visible though the engine never reads it. The edge toward the cycle gives a second reason too: the experiment's detection reads its cycle's suspensions (point 3).
- **Shown later.** The declaration records the day it was made and the shortlisting it rested on (DEC-002 point 9), so the check shows from the files alone that the gate's conditions held, even where a file was written by hand.

### 8. Readings, not states

The status works these out from the data and the positions, and stores none (DEC-002 point 2).
- **An assumption's outcome:**
  - *untested,* while no declared experiment names it
  - *being tested,* while one that names it is declared, running or due
  - otherwise from the one that names it and was decided last: *supported* where it passed, *refuted* where it failed, *inconclusive* where it worked out to neither
- **An idea dropped:** it has a variant, and every variant that was not split is shelved. The idea is no subject of a process, and dropping it is no one move but the result of shelving its last variant.
- **Why readings.** An assumption has no move of its own: its outcome follows from its experiments, so a state for it would be a second copy of their facts, and the two would disagree. An idea's stage follows from its variants in the same way.

## Rationale

**Why three definitions, not one.** An idea has many variants and experiments at once, and many cycles over its life, each at its own stage. One definition over the idea would hold one position for all of them. A keyed definition for each kind of subject gives each its own position, and keeps each definition's states few.

**Why `classified`, with an order of precedence.** One predicate reads a subject's file once and names its state, so its states cannot overlap. A file can still hold facts that point two ways, such as a decision and dates that say running, so the definitions name which wins, and the check reports the conflict instead of the position hiding it.

**Why dates move the subjects, not a wait.** A definition declares one wait, and a person's question is what a subject most needs to show. The engine reads reality on every call, so a date passed is a position reached, with nobody to move it and no journal entry to forget.

**Why a declaration may move straight to running.** The command records the declaration before it asks the engine to move, and the engine refuses a move whose subject already stands elsewhere. A time box that starts on the day it is declared is running as soon as it is recorded, so the definition gives the declaring move that target too, rather than make the person wait a day.

**Why the position is the longest run of yes verdicts, and a no clears what follows.** The method judges a variant's steps in order, each resting on the ones before. A no on an earlier step takes away what the later yes verdicts rested on, so clearing them keeps a later yes from carrying the variant past steps nobody judged again.

**Why a stale verdict holds the position.** A canvas changes every cycle. If each edit moved a variant back, the person would redo every verdict after every review, and the position would move without anyone choosing it. Holding the position, showing it stale, and refusing it only where something new rests on it keeps both the person's judgement and its limit in sight. Shortlisting again is how the person lets new experiments rest on a canvas that changed.

**Why every judgement is the person's, at every level.** A record may hand a question to an agent at a level, naming what checks the agent's choice, or saying that the person is told and nothing checks it (COR-072 point 13). These stay the person's for what they are. A verdict on a business, or whether to bet the next cycle on it, states the person's own belief about their customers and their resources. An agent's choice there would be a guess made in the person's name, and a wrong one costs months. So the agent's part is to make the person's judgement well informed. A later record that places one of them at a level waits for a person (COR-072 point 7).

**Why the consent forms.** A command an agent runs off a terminal cannot ask the person, so the claim that the person decided has to be explicit and visible. The backbone's configuration already asks consent in these forms, so the person meets one pattern.

**Why an experiment needs a shortlisted variant that an open cycle explores.** The method tests a model that passed its desk checks, and runs its tests inside a cycle that reviews them. An experiment on an unjudged variant tests what a cheap desk check would have stopped, and one in a reviewed cycle, or on a variant its cycle does not explore, would reach no review of its model.

**Why the review names one winning variant and decides for it alone.** The method's review leads with the variant that did best, and its decision is which model the next cycle bets on. The other variants the cycle explored keep their outcomes, since shelving one is the person's judgement of that variant, with a reason of its own, which the desk stage already takes as a move. A review that shelved them would make that judgement for the person, for every variant at once. A variant that did worse in one cycle may still be worth another, so it stays shortlisted until the person shelves it.

**Why an evaluative experiment cannot end early.** A result read at the first good moment is a biased result, which is why the book fixes the time box (ch. 6, Seven Habits for Highly Effective Experiments, habit 6). A generative experiment ends at its stopping rule by design, since its point is to learn until nothing new appears.

**Why persevering on a missed objective warns and does not refuse.** The method's review is a judgement over a progress report, and a near miss with a clear cause may justify going on. The warning puts the miss in front of the person, and the decision stays theirs.

**Why a running window is suspended, and never extended.** The book makes an experiment's time box a fixed point for the next review, whatever its results. Where a box is too short for its goal, the book lowers the goal or splits the work across two boxes, and never lengthens the box (ch. 6, Seven Habits, habit 6). This record holds a cycle's window to the same rule, since the window is the time box of the cycle's work. A window the person could lengthen once its results disappoint would stop being one. A suspension is not that. It records that the person's life, not the results, stopped the work, and gives back only days on which nothing the cycle rests on was recorded (DEC-002 point 12). It gives an experiment already running no day back, since what that experiment times is the world's answer, which the absence did not stop. Time that simply ran out goes to the review, which carries the same key results into another cycle, as the book splits a box, or pauses.

**Why suspending is the person's act and resuming the person's move.** Each is the person's to say, and the command holds each to the person alike (point 5). The engine reads a subject as waiting on the person at any state that a `user` move leaves, unless a move of the script's is open there now. A suspended cycle should read so, since only the person's return moves it on. A running cycle should not, so the move into suspended is the script's, following the person's recorded act, as the moves that follow a date are.

**Why nothing but resuming is recorded on a suspended cycle.** A suspension says the person is away, and an act says they are back, so it starts with resuming. Work recorded while the cycle stood suspended would fall on days the window does not count, a window lengthened under another name.

**Why an experiment already running keeps its dates through a suspension.** The book holds an experiment's time box fixed once it is declared (ch. 6, Seven Habits, habit 6). The world went on answering a running experiment while the person was away, so shifting it would lengthen its bet after it was made (DEC-002 point 12). It comes due on its dates, and its result waits for the person, since recording it is the person's act, which starts with resuming. Where the absence spoiled what it measured, the person says so, the assumption reads inconclusive (DEC-002 point 10), and the test is declared again, as any correction is a new experiment, so no result is read on terms other than those declared. An experiment not yet started has had nothing happen in the world, so it moves with the window, and keeps the days the person declared for it.

**Why a suspension may be recorded once the window has run out.** Being away costs nothing (DEC-001 point 10). A window that ran out while the person was away ran out of days nobody used, and without this the person would come back to a review they never had the time for. Since a suspension covers no day on which the person recorded work on the cycle (DEC-002 point 12), a late one never gives back a day they used.

**Why no "stop".** The book has none (ch. 11, the chapter's opening; ch. 11, Assemble a Progress Report Pitch Deck, What's next), and a decision the method does not hold would invite one it does not mean: a pause keeps the idea's record whole and lets it be taken up again.

### Alternatives considered

- **One process over the idea.** Rejected. It would give many subjects one position.
- **An assumption as a process.** Rejected. Its outcome follows from its experiments, and a state would be a second copy.
- **Running and due as facts of the status, not states.** Rejected. The definition carries the result and the decision, so the experiment's whole path is in it from the start.
- **An `awaiting-condition` wait for the time box.** Rejected. A definition declares one wait, and the person's moves need it.
- **A time box that starts the day after its declaration at the earliest.** Rejected. It would make the person wait a day for no reason the method gives.
- **A stale verdict that moves the variant back.** Rejected. Each edit of a canvas would undo the desk stage with no one choosing it.
- **A declaration that only warns on a stale shortlisting.** Rejected. An experiment would then test a model no one judged since it changed, and shortlisting again costs one move.
- **A no that leaves the later verdicts standing.** Rejected. A yes on the step again would carry the variant past steps judged on what the no overturned.
- **Placing the verdicts or the cycle's decision at a delegation level.** Rejected. The judgement is the person's belief about their business, which an agent can only guess.
- **A gate that reads a record of the person's consent.** Rejected. An agent writes the same files, so such a record would be the gated party's own assertion, which a gate may not rest on (COR-033 P4).
- **A fourth decision, "stop".** Rejected. The method has none, and a pause covers a dead end.
- **Refusing to persevere on a missed objective.** Rejected. It would put a rule above the person's reading of their own review.
- **Embedding the experiment in the variant's process as a subprocess.** Rejected. An experiment is no stage of a variant, and the coupling is a readiness condition on one move, not an outcome to wait for.
- **A review that shelves the variants that did not win.** Rejected. Shelving is the person's judgement of each variant, with its reason, and a variant that did worse in one cycle may be worth another.
- **A decision of persevere, pivot or pause for each variant the cycle explored.** Rejected. The method's review leads with one variant and decides which model goes on. A variant left shortlisted is explored again or shelved through the moves it already has.
- **Extending a running window.** Rejected for now. The book never lengthens a time box, and a window extended once its results disappoint stops being one. A later record may add extension as a move of the person's if real use shows a need. Adding it leaves every valid file valid.
- **Suspending as a `user` move.** Rejected. The engine would read every running cycle as waiting on the person.
- **Allowing the person's acts on a suspended cycle.** Rejected. Work recorded during a suspension would fall on days the window does not count.
- **Moving every experiment of a suspended cycle,** a running one included. Rejected. Shifting a running experiment would lengthen its bet after it was made, which the book forbids (ch. 6, Seven Habits, habit 6), while the world went on answering it. Only an experiment not yet started, in which nothing has happened in the world, moves.
- **Suspending one experiment alone.** Not taken. A person's absence stops the whole cycle at once, and an experiment already running goes on in the world whatever is suspended.
- **A suspension planned ahead, from a day still to come.** Not taken. An absence known at planning is sized into the window, and one that begins later is recorded when it begins, or on return.
- **Suspending only a running cycle.** Rejected. A person whose absence outlasted the window would come back to its review, having lost the days the cycle had left.
- **An early review of a cycle.** Not taken. The review comes at the window's end, which the person sets when planning the cycle. A later record may add one once a real cycle needs it.

## Implications

- **The three definitions** are authored through the substrate's authoring layer, each detecting in the classified mode, with a prompt on each person's move and the predicates behind each detection and gate.
- **The gates and the check share predicates** where they judge one fact (DEC-002 point 14), and the detections share the one that works out where a window and a time box fall (DEC-002 point 12).
- **The experiment's `depends_on`** entries are declared in its definition, and the capability's generated `depends-on` list is refreshed from them (COR-053 point 4).
- **The commands** take the person's moves and acts in the consent forms of point 5, record who decided and when, and clear the later verdicts on a no as point 2 says. The command that plans a cycle refuses any plan DEC-002 point 11 makes an error, and any variant that is not shortlisted, as point 4 says. The command that records a suspension refuses one DEC-002 point 12 forbids, and the commands take no act on a suspended cycle or its experiments but resuming it.
- **The cycle's review, and its suspensions, are tested on fixtures,** with today set by the test, since a real cycle's window runs for months.
- **The skill** walks the person through each move's question in the method's order, and runs no person's move without the person's answer.
- **No accepted record is edited.** The questions this record keeps are its own, so it changes nothing the delegation levels place (COR-072).
