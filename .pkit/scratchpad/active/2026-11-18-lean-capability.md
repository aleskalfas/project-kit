---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-11-18
---

# A capability that carries the lean method

Tracked by #3422, under [Milestone 10: Lean experimentation, first loop](https://github.com/aleskalfas/project-kit/milestone/12). It grew from the brainstorm in `2026-11-18-what-next.md`, and retires by producing the plan that files the capability's build, and the records that plan needs.

## The question

What does a capability need, in its data model, its process, its commands and its skill, to guide a person through one loop of the lean method? The loop runs from a lean canvas, through its assumptions ranked by risk, an experiment with an expectation it could fail and a point where it stops, to the result and the decision it leads to. And what does the first slice leave for later?

## Source

*Running Lean*, third edition (Ash Maurya, 2022). The method is distilled here in our own words and credited; no passage of the book is quoted, and the book's text stays out of the repository.

## The method, distilled

Read on 2026-11-18 by five readers, one per group of chapters. Their detailed notes stay in the agent workspace with the book. On 2026-11-19 each claim was checked against the book's text and given the chapter and section it rests on; the excerpts that ground them stay in the agent workspace too.

### The frame

- **What it is:** repeated 90-day cycles of three activities, modelling the business, ranking what is riskiest, and testing it (introduction, A Traction-First Approach; ch. 6, A Typical 90-Day Cycle), across stages: design, then problem/solution fit (three to six months, one or two cycles; corrected from about three months: ch. 7, When Are You Done with Problem/Solution Fit?; ch. 4, Stage 1), product/market fit, then scale (ch. 4, Formulating a Now-Next-Later Rollout Plan).
- **What counts as progress:** traction, meaning evidence that people outside the team care (introduction, A Traction-First Approach), not features built (ch. 6, Time-Box Your Experiments). Test the riskiest assumption first, not the easiest (introduction, A Traction-First Approach).
- **The order:** demo, sell, then build (introduction, Don't Start with an MVP). Nothing is built until customers have committed to an offer (ch. 7, The Mafia Offer Campaign, offer delivery).
- **Customer risk usually outweighs technical risk.** The question is whether to build it, not whether you can (introduction, A Traction-First Approach).

### Design: desk work, about two weeks

1. **The lean canvas.** One page, nine boxes and three sub-boxes (Part I, Don't Write a Business Plan, figure I-1):
   - customer segments, with early adopters
   - problem, with existing alternatives
   - unique value proposition, with a high-level concept
   - solution
   - channels
   - revenue streams
   - cost structure
   - key metrics
   - unfair advantage

   Rules on the boxes:
   - **First sketch:** one sitting, under twenty minutes, in any order (ch. 1, Sketching Your First Lean Canvas).
   - **Blanks:** allowed (ch. 1, Sketching Your First Lean Canvas), but pricing should not be deferred (ch. 1, Revenue Streams and Cost Structure).
   - **Limits:** one to three ranked problems (ch. 1, Problem); a value-proposition headline of about 120 characters at most (ch. 1, Unique Value Proposition, Keep it short); three to five key metrics (ch. 1, Key Metrics).
   - **Unfair advantage:** better blank than weak (ch. 1, Unfair Advantage).
   - **Several actors:** in a model with more than one actor, each entry is tagged with its actor (ch. 1, Customer Segments, Model multiple perspectives).

   A canvas is never finished. It is versioned and reviewed each cycle (ch. 6, Modeling; ch. 11, Preparing for the Meeting). A broad "big idea" canvas is split into variants that each tell one business-model story, of one of three archetypes: direct, multisided or marketplace (ch. 1, Refining Your Lean Canvas). In a team, each member sketches alone first, then the sketches are merged (ch. 1, Sketching Your First Lean Canvas).
2. **Desirability.** The segments, problem and value-proposition boxes are reviewed again, in a fixed order (ch. 2, Using the Innovator's Gift to Stress Test Your Idea for Desirability):
   1. the segments
   2. early adopters, recognised by the event that made them switch, not by a persona (ch. 2, Early Adopters: Forget Personas)
   3. existing alternatives, beyond the product's own category (ch. 2, Existing Alternatives: Transcend Category)
   4. the problems, each framed as a failure of an existing alternative (ch. 2, Problems: What's Broken with the Old Way?)
   5. the value proposition, anchored on those problems (ch. 2, UVP: How Will You Cause a Switch?)

   The lenses it uses:
   - a switching story: customer, job, existing alternative, trigger, problems, new solution (ch. 2, Meet the Innovator's Gift)
   - the job to be done (ch. 2, Unpacking the Innovator's Gift)
   - four forces: push and pull against inertia and friction (ch. 2, Unpacking the Innovator's Gift)

   A switch happens when push and pull outweigh inertia and friction, and the new way should be several times better (ch. 2, Causing a switch starts with a promise of better).
3. **Viability.** The minimum success criteria set a three-year goal, usually as annual recurring revenue (ch. 3, Define a Target Throughput Goal). A five-minute rough estimate runs it through the customer factory: acquisition, activation, retention, revenue, referral (ch. 3, Don't Create a Financial Forecast; Use a Fermi Estimate Instead). It works out (ch. 3, Test Whether Your Idea Can Deliver Your Target Throughput Goal):
   - the customers needed, from the goal and the revenue per customer
   - churn, from a customer's lifetime
   - the acquisition rate needed just to stand still
   - the leads that requires

   The inputs that break the estimate, and then fix it, are the first riskiest assumptions (ch. 3, Running a Fermi Estimate on Your Idea).
4. **Feasibility.** A traction roadmap splits the goal into yearly milestones, by default tenfold growth a year (ch. 4, Charting a Traction Ramp). A now, next, later rollout plan names each stage's riskiest assumptions (ch. 4, Formulating a Now-Next-Later Rollout Plan).
5. **Pitch.** An elevator pitch and a ten-slide deck, shown to advisors (ch. 5, What's Your Elevator Pitch?; ch. 5, Delivering Your Business Model Pitch).

Steps 2 to 4 each end in a yes or no that loops back to the canvas (Part I, The Business Model Design Playbook, figure I-2, whose time axis also gives the phase its two weeks; the text gives no duration). These are desk verdicts, cheap filters before any evidence, not results (ch. 1, What's Next?; ch. 6, Seven Habits for Highly Effective Experiments).

### Validation: the 90-day cycle

- **Time:** weeks one and two model and prioritise. Five two-week sprints test. Day 90 reviews (ch. 6, A Typical 90-Day Cycle).
- **Focus:** one goal per cycle, as an objective with key results taken from the roadmap (ch. 6, The 90-Day Cycle). One constraint: the weakest step of the customer factory (ch. 6, the chapter's opening), which is acquisition before anything runs (ch. 7, Steve Calls a 90-Day Cycle Kickoff Meeting).
- **Converge, diverge, converge** (Part II, Generate a Diverse Set of Possible Solutions):
  1. A kickoff aligns everyone on the goal and the constraint, with no brainstorming of solutions (ch. 7, Steve Calls a 90-Day Cycle Kickoff Meeting).
  2. Each member writes campaign proposals alone. A proposal states the causes of the constraint, the underlying problem with its evidence, the proposed solution, and the expected outcomes (ch. 6, Prioritizing).
  3. A planning meeting pitches the proposals and votes, choosing about one campaign for every two people on the team (ch. 6, Prioritizing).
- **Experiments:** stated as "this one action will drive this measurable outcome within this time box" (ch. 6, Seven Habits, habits 5 and 6). Seven habits govern them (ch. 6, Seven Habits):
  - declare the outcome before running (habit 1)
  - each person estimates alone before the group compares (habit 2)
  - derive the expected number from the roadmap or the estimate, as a point or a 90% range (habit 3)
  - measure what people do, not what they say (habit 4)
  - keep it falsifiable, with one action (habit 5)
  - two weeks at most, never extended (habit 6)
  - compare with a control group: earlier cohorts, or a split (habit 7)

  An experiment is either generative, to discover, or evaluative, to measure traction (ch. 6, Testing). **The book gives no template of an experiment's fields,** only a one-sentence form for the hypothesis (corrected: ch. 6, Seven Habits, habit 5): our fields are a design choice built from these habits.
- **Meetings:** six, each with set attendees: kickoff, planning, sprint planning, daily standup, sprint review, cycle review (ch. 6, Establish a Regular Reporting Cadence; the attendees from its figure 6-4).
- **The default first campaign is the "mafia offer"** (ch. 7, When to Use a Mafia Offer Campaign):
  1. **Problem discovery,** up to two sprints (ch. 7, Running a Mafia Offer Campaign), first broad, then narrowed to early adopters (ch. 8, Broad-Match Versus Narrow-Match Problem Discovery Sprints). It runs on a timed interview script of 30–45 minutes, about past facts only (ch. 8, Conducting Interviews). Each interview gets its own customer forces canvas, and the canvases are grouped into segments by trigger, alternative chosen and desired outcome (ch. 8, Capturing Insights). Its gate is customer/problem fit (ch. 8, When Are You Done with Problem Discovery?):
     - the top three to five customer stories have been found and repeat
     - a problem is big enough to cause a switch
     - enough is already spent on the alternatives
  2. **Solution design,** one sprint (ch. 7, Running a Mafia Offer Campaign).
  3. **Offer delivery,** up to two sprints (ch. 7, Running a Mafia Offer Campaign): one-on-one pitches to qualified early adopters (ch. 10, Running an Offer Delivery Sprint), asking for commitments that cost them something (ch. 10, Act 4: Call-to-action). Its gate is problem/solution fit: enough customers commit, as the roadmap sets, or the cycle runs out of time (ch. 10, When Are You Done with Offer Delivery?). The 60–80% of qualified leads converting is what the offer is optimised toward, not part of the gate (corrected: ch. 10, Running an Offer Delivery Sprint).
- **The cycle review:** a progress report compares the goal with what was reached, and the canvas and roadmap at the cycle's start with now (ch. 11, Assemble a Progress Report Pitch Deck). It ends in one of three decisions (ch. 11, What's next):
  - **persevere:** the goal was met
  - **pivot:** missed, but an insight with evidence could fix it in one more cycle
  - **pause:** a dead end, or out of resources

  There is no separate "stop" (ch. 11, the chapter's opening).

### The hypothesis and test loop, at three scales

The second edition's repeated pattern, a hypothesis, an experiment and what was learned, is still here, but the third edition moves it (not grounded: the third edition's text does not describe the second). Its introduction calls the build, measure, learn loop a fast validator of an idea that only helps when a reasonably good idea goes in; with a bad one, all it teaches is that the idea is bad (introduction, Don't Start with an MVP). So the third edition puts the canvas and its desk tests, and problem discovery, before the loop, and runs the loop inside a fixed cadence (our inference, from the introduction, Don't Start with an MVP, and ch. 6, The 90-Day Cycle). The word "hypothesis" appears mostly in chapter 6 (8 of its 15 uses in the body text; ch. 6, Seven Habits, habit 5).

The chain:
1. A canvas entry is an assumption, a "leap of faith", vague and not yet testable (ch. 6, Seven Habits, habit 5).
2. The riskiest assumptions are ranked (introduction, A Traction-First Approach).
3. Each is rewritten as a falsifiable hypothesis: one action, an outcome you can measure, a time box (ch. 6, Seven Habits, habits 5 and 6).
4. An experiment tests it, inside a campaign that carries a strategy for the cycle's constraint (ch. 6, The 90-Day Cycle; Part II, Avoid the Curse of Specialization).
5. The result is held against the declared expectation, and is either learned from or acted on (ch. 6, Seven Habits, habit 2).

It repeats at three scales:
- **An experiment:** two weeks, ending in pass or fail (ch. 6, Seven Habits, habits 5 and 6) and its next action: correct course (habit 6), double down (Part II, Decide on Next Actions), or stop the experiment (our wording: the book speaks only of invalidating initiatives early, habit 6).
- **A sprint:** two weeks, ending in a sprint review that sets the next sprint's focus (ch. 6, Establish a Regular Reporting Cadence; ch. 8, Steve Reviews the Results of the Broad-Match Problem Discovery Sprint), and at a stage's gates, customer/problem fit and problem/solution fit, a step back on a failed gate (ch. 8, When Are You Done with Problem Discovery?; ch. 7, Running a Mafia Offer Campaign, figure 7-6).
- **A cycle:** 90 days, ending in the review's persevere, pivot or pause, which also updates the canvas and the roadmap for the next cycle (ch. 11, Preparing for the Meeting; ch. 6, A Typical 90-Day Cycle).

### Growth: after customers arrive

The same cycle continues (Part III, The Journey Ahead) with new artefacts: a launch to a small paying group (ch. 12, Roll Out Your MVP in Batches; introduction, A Traction-First Approach), a cohort dashboard, a map of the customer factory's events (ch. 12, Extend Your Customer Factory Metrics Dashboard), and growth tests such as lifetime value above three times the cost to acquire a customer (ch. 14, The Revenue Growth Loop). None of it is needed before there are customers, except that the dashboard and the map extend a weekly one begun before launch, in offer delivery (corrected: ch. 10, Measure Your Customer Factory Metrics Weekly).

### Where the method resists capture

- **Most quality rules are judgements:** a problem framed against an alternative (ch. 2, Problems: What's Broken with the Old Way?), a real advantage against a false one (ch. 1, Unfair Advantage), one story to a canvas (ch. 1, How Do You Know When to Split Your Lean Canvas?). Data can hold the links (a problem to its alternative, the value proposition to the first problem: ch. 1, Connect to your customer's number one problem) and the tags. A person or an agent judges the content.
- **Order is free in one place and fixed in another.** The first sketch has no order (ch. 1, Sketching Your First Lean Canvas); the desirability review has a strict one (ch. 2, Using the Innovator's Gift to Stress Test Your Idea for Desirability).
- **The book's numbers are loose** (for one, ch. 3, Steve estimates how many active customers he'll need), and several figures contradict the text (for one, ch. 4, Steve Charts His Traction Roadmap, figure 4-4). The formulas follow the text. Its sprint allocations are guidelines (ch. 7, Running a Mafia Offer Campaign), so a check of them warns and does not refuse.
- **Two decisions need judgement:** whether interviews have stopped yielding anything new (ch. 8, Running a Problem Discovery Sprint), and pivot against pause after a missed goal (ch. 11, What's next).
- **The licence:** the canvas template is published under Creative Commons BY-SA 3.0 (Part I, figure I-1, its footer), which binds how a shipped template is credited and licensed.

## How a person uses it

Raised by the person on 2026-11-18 as important: will there be a visual part? There are four surfaces:
- **A conversation:** with an agent through the skill, which asks the method's questions in order and runs the commands. This is the main way in.
- **The commands:** at a terminal, for a quick look or a change.
- **The data files:** the canvas, the assumptions and the experiments, readable in the repository.
- **A view:** a page built from the data.

The method is visual by design: a one-page canvas, a roadmap with what was reached drawn over it, a progress report at each review. The person's work-plan page in `agent-effectivity-and-cost` is what gave them sight of their work there. It is a static page built from plan data by a command, with each task's next action worked out.

The options for the view:
1. **A static page built by a command from the capability's data,** opened in a browser. It holds the canvas on one page, the assumptions ranked, each experiment with its state and next action, and the cycle. It is read-only, with no dependency on another capability.
2. **Drawn through the visual-communication capability:** branded, but bound to a capability whose first version is unfinished, and project-kit runs no design loop until its review is calibrated (project rule 5).
3. **The terminal only:** a status command and the next action.

The coordinator's first lean was the first option, kept thin, in the first slice. The second can come once visual communication's version 1 has shipped.

The person's lean (2026-11-18): the terminal for now, until the visual-communication capability is ready.
- **For it:** the first loop holds little data, one canvas, a ranked list and one experiment, which a terminal shows well in a conversation. A page earns its place once a cycle runs for weeks with many experiments. Building a page now builds ahead of need, which the method itself warns against.
- **The risk:** visual communication's version 1 has 71 open issues and keeps growing, so "until it is ready" could mean no view for a long time.
- **Proposed guard:**
  - The commands also print their data in a structured form, so a later view reads it without changing the data model.
  - The view is revisited after the first real loop on the board game, whatever Milestone 7's state is then.

## Mapped onto the capability's layers

A draft for review (2026-11-18). It is for `critic` and `architect` to review before the person sees it; nothing is decided. The capability's working name is `lean`; its name is a question below.

### Data

A project keeps its files in one folder it names, by default `lean/`. Each file is bound to a schema, which `pkit data validate` checks.

1. **Canvas,** one file for each variant.
   - **Its header:** product, variant, archetype (direct, multisided or marketplace), the canvas it was split from, the author, and the date of its version.
   - **Its boxes:** the nine boxes and three sub-boxes as lists of entries. Each entry has an id, its text and, where several actors share the model, its actor.
   - **The links data can hold:**
     - problems ranked one to three
     - each problem to the existing alternatives it is framed against
     - each solution item to its problem
     - the value proposition to the first problem, as a headline and a sub-headline
     - channels marked early or scalable
     - metrics marked by kind
   - **Viability,** in the same file:
     - the minimum success criteria: a recurring-revenue goal, its horizon and who set it
     - the estimate's inputs: price, a customer's lifetime, conversions, the share from referrals
     - a traction target: the growth multiplier, ten by default, and the first stage's target
   - **What the data does not hold:** the estimate's outputs, which the command works out and never stores.
2. **Assumptions,** one list for each canvas.
   - **Each one:** an id, its statement as a leap of faith, where it comes from (a canvas entry or an input of the estimate), its kind (desirability, viability or feasibility), its rank by risk, and its state.
3. **Experiment,** one file each. This is our design, since the book gives no template.
   - **What it links to:** the assumption it tests, its kind (generative or evaluative), and the cycle it runs in.
   - **The hypothesis:** one action, the metric as a step of the customer factory, and the expected outcome as a point or a 90% range, with where that number comes from and the effects known in advance.
   - **How it runs:** a time box of two weeks at most, and the control, either earlier cohorts or a split with the share exposed.
   - **Before it starts:** each person's estimate, recorded then.
   - **Once it has run:** the result with where its evidence lies, pass or fail, the next action (correct course, double down, or stop the experiment), and what was learned.
4. **Cycle,** one file each.
   - **What it holds:** the goal as an objective with key results from the traction target; the constraint, as a step of the customer factory with its evidence; the experiments in it.
   - **Its review:** the goal met or not, what was reached, the decision (persevere, pivot or pause), its reasons and the evidence a pivot rests on, and the canvas versions at the cycle's start and end.

### Process

A process definition of the capability's own.

- **An experiment:** drafted, then declared, then running, then due, then decided.
  - **The gate into declared:** an action, a metric, an expected outcome and a time box of at most fourteen days, and at least one estimate recorded.
  - **Due:** an experiment becomes due when its time box ends, which is never extended.
  - **The gate into decided:** a recorded result, pass or fail, and a next action.
- **An assumption:** untested, then being tested while an experiment on it runs, then supported, refuted or inconclusive, from the outcome of its experiment.
- **A cycle:** planned, then running, then in review, then decided.
  - **The gate into decided:** one of the three decisions.
  - **The checks on that decision:** a pivot cites evidence; persevering on a missed goal draws a warning.
- **A canvas has no final state.** It has versions instead.

### Commands

The capability's commands run as `pkit lean <verb>`, each with tests.

- **Making and changing records:**
  - `new canvas`, and `new variant --from`
  - `estimate`, which works out the viability numbers and names the inputs that break the goal as candidate assumptions
  - `rank`
  - `new experiment`, `start`, `record-result` and `decide`
  - `new cycle` and `review-cycle`
- **Looking:**
  - `status`, which shows the canvas, the ranked assumptions, each experiment's state with its days left and its next action, and a line on what to do next, with `--json` for a later view
  - `check`, which runs the rules data can check
- **What `check` checks:**
  - one to three ranked problems
  - a value-proposition headline of 120 characters at most
  - three to five metrics
  - early adopters with at least one switching trigger
  - existing alternatives not empty
  - each problem linked to an alternative
  - each solution item linked to a problem
  - time boxes within fourteen days
  - estimates recorded before a start
  - a pivot that cites evidence
- **Warnings rather than refusals:** the book's guidelines, such as how sprints are allotted.

### Skill

A composite skill paired with the commands. Its sub-procedures:
1. sketch a canvas in any order, in one sitting
2. review its desirability in the fixed order, with the guiding question for each box and the lenses of the switching story, the job and the four forces
3. estimate viability
4. rank the assumptions
5. declare an experiment
6. record its result and decide
7. review a cycle

The skill carries the judgements, and the commands enforce what data can.

### Records the build needs

- The capability itself: what it carries, what it leaves out, and how it credits the book and keeps its text out.
- The data model.
- The process, with the three decisions and no "stop".
- The experiment's fields, as our design.
- The view: the terminal and structured output.
- Where a project keeps its files.

### Revised after `critic` (2026-11-18)

The draft above is kept as it was reviewed. This revision takes over from it.

**1. Where the slice ends: the person's decision.** The accepted skeleton runs to a result and a decision. The accepted finish line stops at an experiment chosen. The draft built the states the finish line never reaches (running, due, decided, the cycle's review) and left no place for what it does reach: the desk verdicts, a variant shortlisted or shelved, the idea dropped.
- **A.** The slice ends at the finish line: the desk stage and a declared experiment. The result, the decision, an assumption's outcome and the cycle come in the next slice, built once a real experiment is running, which is when their shape stops being a guess (COR-007).
- **B.** The finish line moves out to the first experiment's result.

The coordinator's lean is A. What follows assumes it.

**2. Data:**
- **The goal belongs to the project.** The minimum success criteria sit above the variants, set before the idea, and change only at a review. Kept in each variant, they would drift toward the idea.
- **Each variant has a status:** active, shortlisted, or shelved with its reason. The three desk verdicts are desk notes, not results. When every variant is shelved, the idea is dropped.
- **Several actors are supported.** The estimate's inputs and the value proposition are keyed by actor or side, since a board-game platform is likely multisided. Early-adopter entries carry their switching triggers.
- **An assumption stores no state of its own.**
- **An experiment's declaration depends on its kind,** and is frozen once declared:
  - **generative:** a learning goal, a stopping rule such as an interview count or saturation, and what counts as fit, set in advance
  - **evaluative:** one action, the metric, the expected point or range with where it comes from, and the control

  The book's default first experiment is problem discovery, which is generative, so the draft's single gate didn't fit it.
- **Estimates and authors are lists,** so one person or a team both fit.

**3. Process:** two definitions, each over one subject.
- **A variant's desk journey:** sketched, then desirability, viability and feasibility, then shortlisted or shelved.
  - **Viability** needs pricing and the estimate's inputs.
  - **Feasibility** needs the first stage's target.
- **An experiment:** drafted, then declared. Running and due are read from its dates.
- **Who may take each move:** each transition names it. The verdicts, shortlisting, ranking and declaring are the person's (COR-072).

**4. Commands,** about nine:
- **Making records:** `new canvas`, `new variant`, `estimate`, `target`, `add-assumption`, `rank` and `declare`.
  - **`estimate`** shows its outputs. Where the early-adopter segment's size is given, it sets the customers needed against it. Which outputs are unrealistic is the skill's question, not the command's.
- **Looking:** `status --json`, which reads positions from `pkit process status` and never works them out again, and `check`.
- **What `check` does:**
  - **Ranges:** it applies them only to boxes that hold entries, as warnings on a first sketch.
  - **Pricing:** it requires revenue streams before the viability verdict.
  - **Warnings:** it warns where an experiment tests an assumption while a higher-ranked one is untested, and on a value-proposition headline over 120 characters.

**5. Skill:** sketch, desirability, viability, feasibility, rank, declare.

**6. Records,** three:
- **The capability:** its scope, the credit to the book, the licence and the name.
- **The data model:** where a project keeps its files, the experiment's fields and the structured output.
- **The process.**

**7. The next slice,** once an experiment runs:
- **The result,** with pass or fail worked out from the frozen expectation and the actual, never asserted.
- **The next action,** and the assumption's outcome.
- **The cycle,** and its review.
- **Where versions live.** "Declared before it ran" rests on version control: the declaration's commit comes before the start, and its fields stay unchanged after.

**8. Raised by `critic` for the plan:**
- **The name blocks.** It keys the folder, the commands, the process addresses and the citations, and renaming it after a release needs a migration. Name the discipline, not the book; a candidate is `lean-experiments`.
- **The licence blocks the landing.** The schema mirrors the template's boxes, and the Lean Canvas is itself adapted from the Business Model Canvas, both under CC BY-SA 3.0. Credit both, and decide whether the schema files carry the share-alike licence.
- **Where the first use happens.** The board game lives in another repository, which gets the capability only after it lands and is released. That is a release the plan must name. A business idea's canvas in a public repository is a privacy question too.
- **An alternative to name, not chosen:** build the capability in the board game's own repository, and move it into project-kit once its shape is proven (COR-031).

### Reviewed by `architect` (2026-11-18)

No accepted record is modified. Its findings, adopted into the plan:
- **Versioning is needed in the first slice.** Each verdict and declaration stores a fingerprint of what it judged, so a frozen declaration, an estimate made before the start, and a verdict gone stale after its canvas or the goal changed can be checked in the working tree.
- **Position has one source.** The first slice ends at declared, so the days left are shown as a fact, not a state. Running and due become states in the next slice.
- **The person's moves:** each verdict move has `authorisation: user`, a deterministic completeness gate, and a wait for a human whose prompt is the verdict's question. The process record says the caller enforces the person's authority, not the engine. It places none of these questions at a delegation level (COR-072 point 13).
- **The experiment's wait is declared now,** since adding one later needs `amend`, which pkit has not built. The plan names that dependency of the next slice.
- **`check` joins validation as a member,** with a severity on each finding. The warning about the riskiest assumption stays a command. "Pricing before viability" is the process gate, through one predicate shared with the command.
- **Ids are qualified by variant,** since a duplicate id across the validated folder is an error (COR-029). The variant's stored facts are its verdicts and shortlisted or shelved; "split into other variants" is an outcome of its own.
- **The data's location** defaults under the internal documentation root, recorded through the backbone's location recorder, as software-analysis does (COR-049). It is laid out as `<location>/<idea>/`, with the goal inside each idea.
- **Boundaries:**
  - Use "side" or "segment", not "actor", and name nothing a "journey", since software-analysis owns those words.
  - Link to project-management through the work-tracking role (COR-053), and cite the evidence capability's records in its own form.
  - Make `--json` versioned.
- **The name:** `business-model-validation`, with a short command alias. The first slice is mostly the canvas, so `lean-experiments` covers only what is still to come, and growth is plausibly a capability of its own later.
- **Build it in project-kit.** Moving a capability built in a project into project-kit has no mechanism yet (COR-031). To try it on the board game before it ships, use a release candidate (PRJ-016), once it is checked that candidates can be cut today.
- **Needs the person's authorisation (escalated):**
  - **The licence.** Shipping any CC BY-SA file would be the first non-MIT file project-kit ships, and needs a record first. The recommendation is to ship none: name the fields in the capability's own words and keep the credit in the README.
  - **The data's location,** only if a folder at the repository's root is kept.

**The decisions for the person, in order:** where the slice ends, the name, the licence, the location, versioning.

### Decisions taken

1. **Where the slice ends: B** (the person, 2026-11-19). The finish line moves out to the first experiment's result: declared, run, its result recorded and its next action decided. This slice builds the result, pass or fail worked out from the declaration, the next action, the assumption's outcome, and the cycle with its review.
   - **In the definitions from the start:** running and due are states of the experiment from the start, so the next slice needs no `amend`.
   - **The cycle's review is tested on fixtures.** A real cycle ends only after 90 days, later than the merge.
   - **Updated:** #3426's body says this. The milestone's description still says "first experiment is chosen", and no pkit command edits a milestone's description.
2. **The name: `lean-business`,** with `lean` as the short command alias (the person, 2026-11-19). It is the home of the whole method, so growth will later extend this capability rather than become a capability of its own. Its README says it means validating a business model, not a business run lean.
3. **The licence: nothing ships under CC BY-SA** (the person, 2026-11-19).
   - **The fields:** the schema uses the boxes' names as its field names, with descriptions in the capability's own words. Nothing of the template's prompts or wording is copied.
   - **The grid:** the terminal draws the canvas as a grid arranged as in the book:
     - **Five columns:** problem over existing alternatives; solution over key metrics; unique value proposition over high-level concept; unfair advantage over channels; customer segments over early adopters.
     - **Along the bottom:** cost structure and revenue streams.
   - **The credit:** a credit and licence line under the grid, as the template carries one. The README credits the Lean Canvas and the Business Model Canvas it adapts.
   - **pkit's own files stay MIT.**
4. **The data's location: `lean-business/` at the repository's root** by default, with one folder per idea (the person, 2026-11-19).
   - **Configurable:** it is recorded on first use through the backbone's location recorder, so a project can choose another folder.
   - **The reason, for the data-model record:** this is the working state of a business idea, not documentation of a system, and a repository may exist only to explore ideas. The person's choice is the authorisation `architect` asked for, since it departs from COR-049's documentation roots.
5. **Versioning: fingerprints** (the person, 2026-11-19). Each verdict and each declaration stores a fingerprint of what it judged.
   - **What validation catches:** a declaration edited after it was declared is an error, and a verdict whose canvas or goal changed since is stale.
   - **Git history** stays the audit trail, and the cycle review reads it to show what changed during the cycle.
6. **The first use, before the merge: in this clone, on this branch** (the person, 2026-11-19). The board game's data lives in `.agent-workspace/lean-business/board-game-platform/`, which git ignores, so the idea stays private. After the merge and a release, the folder moves into the board game's own repository.

7. **Where the location is recorded: in the capability's own configuration,** `.pkit/capabilities/lean-business/project/config.yaml`, as visual-communication records its working folder (the person, 2026-11-19). The backbone's recorder places locations only under a documentation root, which decision 4 rejected.

8. **The first use, replacing decision 6: a private board-game repository on the person's machine** (the person, 2026-11-19).
   - **How:** pkit is initialised there, and the capability is installed from this branch at a commit, through `pkit capabilities install lean-business --from <repository> --ref <commit>`. It is set up once the build is ready.
   - **What it keeps:** git history, pkit's data validation and privacy, and it tests the real install.
   - **What it costs:** each fix during the first use means reinstalling, since moving an installed capability's pin waits on #3229.
   - **The ignored workspace folder** of decision 6 would have lost history and validation.
   - **One repository for many ideas:** the private repository explores several ideas, one folder each under `lean-business/`, the board game first. A product repository with one idea uses the same layout, and an idea that graduates moves its folder across unchanged. The drafts already allow this: each idea has its own goal and cycles, and ids are qualified by idea.
9. **How a judgement of the person's is checked: a gate of completeness, and the move held to the person by the command** (the person, 2026-11-19).
   - **The gate** checks only that the data a judgement rests on is complete, such as the goal, the revenue streams and the estimate's inputs for viability.
   - **The judgement** is a move marked as the person's: the command asks at a terminal, needs an explicit flag that the person decided when an agent runs it, and otherwise moves nothing and prints the question.
   - **The record says plainly** that nothing in a file proves a person answered, and that signed commits and review are the audit trail. A trace from a second party, such as a GitHub approval, would come from the same account in a one-person setup.
10. **Cycles: one at a time per idea, exploring one or more shortlisted variants** (the person, 2026-11-19). It replaces the drafts' one variant per cycle, with overlapping cycles across variants.
    - **Why:** the idea has one goal, which may change at a cycle's review, so overlapping cycles would make each other's shortlistings stale mid-cycle (`architect`). The book has one cycle explore several variants, its review leading with the winning one (ch. 11, the cycle review).
    - **The review** names the winning variant where the cycle explored several, and the person decides persevere, pivot or pause for it.
    - **An experiment** belongs to a variant the open cycle explores.
    - **Overlapping cycles** may be allowed later as an addition, while forbidding them later would turn valid data into errors.
11. **How decision 10 was worked out: confirmed** (the person, 2026-11-19, after a worked example of the board game's first cycle). At most one undecided cycle per idea; each key result names its variant, and each explored variant has one; one constraint for the cycle; the review decides for the winning variant only, and the others keep their shortlisting; a pivot may rest on any explored variant's experiments; the goal changes only while no cycle is planned or running; planning a cycle is the person's act; a shelved winner allows only a pause.
12. **Discontinuity: size the window up front, suspend when life interrupts, and brief the person on return** (the person, 2026-11-19). The method is meant for part-time founders too (the book's main character works nights and weekends), yet a time box that can be extended stops being one (ch. 6, habit 6).
    - **The window** is sized at planning to the person's capacity, 90 days by default.
    - **Suspending a running cycle** is the person's move, with a reason, and resuming ends it. The cycle's end, and the end of each experiment running in it, shift by the days suspended. A suspension may be recorded late, from an earlier date, and the review shows when it was recorded.
    - **A running window is never extended.** Time that simply ran out goes to the review: persevere into another cycle on the same key results, or pause. Extension stays a later addition if use shows a need.
    - **Being away costs nothing:** an experiment past its end, or a cycle past its window, waits for the person, and nothing expires.
    - **The return briefing.** The capability orients a returning person from the files alone: when they last acted and what that was; the goal, the cycle's objective, constraint and key results with progress; each experiment's state, with the declared expectation beside one waiting for its result; what waits on them, in order, with each command; and, after a long silence, an offer to record the gap as a suspension from the last activity, with its effect on the cycle's end. Without an idea, the status gives one line per idea. In a session, the agent reads the same briefing. Its layout is the build's.
13. **How decision 12 was worked out: confirmed, with one change** (the person, 2026-11-19, after a worked example). The twelve details the drafter settled stand, listed in the records' review log, except item 6:
    - **An experiment already running when a suspension starts keeps its declared dates.** The world went on answering while the person was away, so shifting it would extend the bet, which the book warns against (ch. 6, habit 6). If the absence spoiled it, the person records it as inconclusive and declares it again.
    - **An experiment that had not started yet shifts** by the days suspended, since nothing had happened in the world yet.
    - This replaces decision 12's "the end of each experiment running in it shift".
14. **The three records accepted** (the person, 2026-11-19): the capability (DEC-001), its data model (DEC-002) and its process (DEC-003), as drafted with decisions 1 to 13 applied, after `critic`, `architect` and two rounds of `methodology-reviewer`. The person saw the processes as diagrams before accepting.
15. **`process-author` writes the predicates** (the person, 2026-11-19). It is granted the three process definitions, their predicate scripts and the module that works out each subject's position, file by file once phase 2 stamps them, and not the capability's whole folder, which the agents README's rules for a write-carrying category refuse. The grant holds while project-kit leaves lean-business unregistered.
16. **References join an id's parts with a double hyphen, and the backbone resolves them** (the person, 2026-11-19). COR-019's grammar admits no full stop, so `[cycle:board-game--first]` replaces `[cycle:board-game.first]`. The backbone learns that a file holding one subject adds its own id to its namespace's pool, through an in-place refinement of COR-029, so the capability marks its references as DEC-002 point 7 says. Preferred over COR-019's three-part form, which would rest on the backbone ignoring three-part tokens and would make an assumption's id unique across the idea's variants.
17. **A late suspension never reopens a window past an act recorded after the window ended** (the person, 2026-11-19, after a worked example): the goal set, or the review. The command refuses it and the check reports it. Coming back after a silence still works, since nothing was recorded after the window ended.
18. **A price is what one active customer brings in each month or year, and the goal names the idea's currency** (the person, 2026-11-19). The one shape `{amount, per}` stays, defined as the book's yearly customer revenue (ch. 3, "Estimate the required number of active customers"): a one-off sale is its yearly average, and a marketplace's sides count what flows through, with the goal set on throughput (ch. 3, the minimum success criteria). The reasoning behind a conversion is an assumption on the variant's list. The goal's currency is the unit of every amount in the idea, and a change of it makes stale what used the goal. The goal requires it, read from the person's "plus currency".
19. **Every desk verdict and each shortlisting cover the variant's archetype and its sides** (the person, 2026-11-19, after a worked example), so a change of model makes them stale before any box changes.
20. **A marketplace's side counts what the business keeps from it** (the person, 2026-11-19, after a worked example of the board game's two variants). It corrects how decision 18 was put: counted as what flows through, a marketplace variant would need a goal of its own, and one idea's variants could no longer share one goal (DEC-002 point 3). The share kept is an assumption of the variant, and a side that pays nothing counts at nothing.
21. **A late suspension contradicts no act already recorded** (the person, 2026-11-20, after a worked example of an experiment decided on day 35 whose time box a suspension recorded on day 40 would move to end on day 39). It widens decision 17's scope: a suspension is refused wherever an act already recorded, the goal set, an experiment's decision, the cycle's decision or any other, would read with it as one its gate refuses. Preferred over holding to the two acts decision 17 named, which would leave an experiment's decision beside a suspension that says its time box had not ended.
22. **The first use reaches the board-game repository through a release candidate cut from this branch** (the person, 2026-11-20). It replaces decision 8's how: `pkit capabilities install --from --ref` is refused until #3349, and lean-business needs the backbone change this branch ships, which no final release holds yet.
    - **How:** once the capability is ready for its first use, the branch takes in the default branch's head and a candidate is cut from it (the release reference, "A release candidate"). In the board-game repository, on a testers' branch, the person runs `pkit upgrade --pre` and then `pkit capabilities install lean-business`, or opens a session there to do it. This session changes nothing there (core rule 19).
    - **What it keeps:** the real install from a release, the backbone it needs, git history and validation, and the idea stays private.
    - **What a fix costs:** a new candidate. A project on a candidate moves to no other release (ADR-092 point 7), so the person starts a new testers' branch from the final release, enters the new candidate there, installs the capability again and brings the idea's folder across from the earlier branch.
    - **The candidate's versions** live only in its tag, raise no floor and consume no changeset (PRJ-016).
23. **Resuming may land in review** (the person, 2026-11-20, after a worked example: a cycle of days 1 to 90, suspended on day 50, resumed as of day 60 but recorded on day 120, so its window as moved ends on day 100). Where the window, moved by the suspension, ended before the day the resumption is recorded, the move of resuming goes from suspended into review, under the same gate, as declaring has two targets. The person records the true day of resuming, and gets back no day they worked. Preferred over refusing such a resumption, which would make them name a later day, and over landing in running past the window's end. Found by `process-author` writing the cycle's gates: the engine refused the move, since the cycle read in review.
24. **A command for every piece of content** (the person, 2026-11-20, option B after a worked example: a problem added to the board game's canvas). Each entry of a canvas and its links, each viability input and the traction target, each assumption, and each field of a draft experiment has a command that writes it, assigns its ids and refuses at once what the data shows wrong, as every write in pkit goes through a command. Preferred over editing the content in the files with two commands beside (`add-assumption`, and copying a canvas on a split). A hand edit stays possible, and the check holds it alike (DEC-002 point 14). Written into DEC-001 point 3 as a refinement.

### Next

1. Stamp the capability through `capability-author`.
2. Draft its three records through `decision-author`: the capability, the data model and the process. Each goes to `critic`, then `methodology-reviewer`, then the person.
3. Build in the order of the Task, the evidence records staying local.

### The commands (phase 3)

The plan the builders follow (2026-11-20). It carries out DEC-001 point 3 as refined by decision 24, DEC-002 and DEC-003, and was reviewed twice by `critic`. Phases 1 and 2 built the check (`scripts/check.py`, `scripts/_lib/`), the three process definitions and their 33 predicates. Every command runs as `pkit lean <verb>`, a flat leaf of the capability's `commands:`, with its tests and its row in the README.

**Every write, alike.**
- **Built, held, then written.** Every command, an act's as well as content's, builds each file as it would stand and holds it to the schema, to the core's reference and duplicate-id pass, and to the check. It refuses where the write adds an error, comparing the findings before and after, and names an error already in the files without refusing, so a file broken by hand never freezes the commands on it. On a refusal it writes nothing, and names the finding as the check would.
- **Refused beyond the check:**
  - a typed id that exists, or that a reference or an assumption's source still names, since an id named is never given again (DEC-002 point 7);
  - on `draft-experiment`, a time box over fourteen days, an end before its start, and a range whose low is above its high, which the declaring gate refuses on any day (DEC-002 point 9);
  - `add-assumption --entry` naming no entry of its canvas, which can only be a typo.
- **Warned of, never refused:**
  - what the check warns of;
  - a change to content a standing verdict fingerprinted, naming each verdict it leaves stale, and louder where it stales the shortlisting of a variant an undecided cycle explores, since no declaration rests on that variant until the person judges again;
  - removing an entry an assumption or another entry still names, since the method removes an entry its experiment refuted (DEC-002 point 7, "One link that may dangle");
  - editing an assumption a declared experiment tests;
  - drafting an experiment of a suspended cycle, naming `resume`.

  A shelved or split variant's content stays editable, since no record freezes it.
- **Ids.** A command gives each id from `--id`, or from the text: accents stripped, ASCII letters and digits kept, the first words in kebab case, a leading digit given a letter before it, and a fallback where nothing is left. It qualifies the id by its variant or idea. The id is unique across the canvas or the location, and never one a reference or an assumption's source still names. It never changes when the text does. The command prints each id it gave. This holds for assumptions too.
- **Round-trip YAML,** keeping comments and order.
- **Content is no judgement.** A content command takes no consent form and records no who or when.
- **Undone where the move refuses.** Where `move` refuses after the write, every file the command wrote or created is put back or removed, the location's record included.

**Every act, in addition.**
- **Today** is read at the command's entry, never from argv or the environment (DEC-003 point 1).
- **The engine connection is injectable.** The engine runs each predicate in a process of its own, which reads the real date. So tests swap in an engine that asks the same predicates in-process through `positions` on the test's day. A few tests run the real engine, with fixture days relative to the real today.
- **The target of a move is never chosen before the write.** Before it, the command refuses where no target its trigger declares opens (`can-move`). After it, the command reads where the subject stands from the engine's status and moves there, `move --to <that> --from <origin>` (DEC-002 point 15).
  - Both of resuming's gates open before the write in decision 23's example: a window of days 1 to 90, suspended on day 50, recorded on day 120. Resuming on day 80 or later lands in running, and earlier in review.
  - Builder 4's tests hold that example by name.
- **The order of a person's move:**
  - check the input against the shared predicate, and ask `can-move`;
  - write;
  - move.
- **The script's moves.** The suspension command validates through `suspensions.of_cycle` and writes. It then takes the cycle's move with `move --from`, never asking `can-move` first. No command takes the experiment's moves on dates (DEC-003 point 3).
- **The consent forms** (DEC-003 point 5):
  - at a terminal, ask the question and act only on a yes;
  - off a terminal, act only with `--person-decided`;
  - with neither, act on nothing and print the question.

  A move's question is its definition's prompt. An act with no move asks in the capability's own words (DEC-001 point 7): a no on the next step, a yes on a passed step, a rank, a plan, an estimate, a result, a stopping rule, a suspension, the goal.
- **Who and when** on each act whose record keeps them; a rank keeps none (DEC-002 point 8). Who is git's `user.name`, never the email.
- **Act details come as flags,** a repeated piece repeating its flag: `--key-result <variant>:<step>:<target>`, `--evidence <experiment>`, `--reached <number>` in key-result order. Nothing of an act is drafted into a subject's file before the act, since the classifiers read a decision's or a window's presence as a position.
- **The location** (DEC-002 point 1):
  - The first write records it without asking, and says what it recorded and where to change it.
  - Where the default folder holds files of another kind, it records nothing and names `set-location`.
  - Any first write may create the idea's folder, since the first sketch's order is free.
- **Ownership.** `_lib/positions.py`, the process definitions and the predicate scripts are `process-author`'s (the overlay's grant). Builders read them, never edit them, and report any change they need.
- **Refusals and warnings the records name:**
  - `set-goal` refuses a change of currency while a declared experiment is undecided, and any change while a cycle is planned, running or suspended (`gates.setting_goal`).
  - Every act on an experiment of a suspended cycle is refused, naming `resume` (DEC-003 point 3): the estimate, the stopping rule, the result. The stopping rule is refused on an evaluative experiment too.
  - `plan-cycle` refuses:
    - no goal;
    - a variant not shortlisted;
    - a second undecided cycle;
    - a variant without a key result;
    - a key result naming a variant the cycle does not explore;
    - a window overlapping another cycle's as worked out;
    - a change that drops a variant one of its experiments tests (DEC-002 point 11, `gates.planning`).
  - `review-cycle` refuses on a suspended cycle, and warns when persevering on a missed objective.
  - `declare` warns when a riskier assumption is untested.

**The surface.** (c) marks content.
- **The location and the idea:** `set-location <path>`, run before the first idea, where running it is the consent (COR-048 point 5); `set-goal <idea> --revenue --per <month|year> --currency --years`.
- **A variant's canvas (c):**
  - `new-variant <idea>--<variant> --archetype [--author <name>]... [--comes-from <shelved variant>]`. It creates the idea's folder where none is, the canvas and its empty assumptions list.
  - `set-archetype <variant> <archetype>`, refused on the way to direct while a side is named.
  - `set-authors <variant|experiment> <name>...`.
  - `add-side <variant> <name>` and `remove-side`, the latter refused while an entry or input names the side.
  - `add-entry <variant> <box> <text> [--id] [--side]`, with the box's links as flags:
    - `--alternative <entry>`... on a problem;
    - `--problem <entry>` on a value proposition or a solution;
    - `--sub-headline` on a value proposition;
    - `--trigger <text>`... on an early adopter;
    - `--kind early|scalable` on a channel;
    - `--step <factory-step>` on a key metric.
  - `edit-entry <entry> [--text] [--side] [link flags] [--clear <field>] [--drop-alternative <entry>] [--drop-trigger <text>]`.
  - `remove-entry <entry>`.
  - `move-entry <entry> --to <position>`, where a problem's position is its rank.
  - `set-inputs <variant> [--side] [--price] [--lifetime] [--conversion] [--referral-share] [--clear <input>]`, merging into the set for its side.
  - `set-traction <variant> [--multiplier] [--first-stage-metric --first-stage-target] [--clear]`.
- **The desk stage:**
  - `judge <variant> <step> <yes|no> [--note]`;
  - `shortlist`;
  - `shelve --reason`;
  - `split <variant> --into <name>...`. It creates each named variant as a copy of the canvas, its ids and links re-qualified and its `comes-from` set. It copies neither verdicts nor outcome. It copies the assumptions, their ids and sources re-qualified.
  - `canvas <variant>`, read-only: the grid and its credit line (DEC-001 point 6).
  - `estimate <variant>`, read-only: the numbers worked out and never stored, the formulas in the README. Which numbers are unrealistic is the skill's question.
- **Assumptions:**
  - `add-assumption <variant> <statement> --kind (--entry <entry> | --input <name> [--side]) [--id]` (c). It is placed one past the highest rank, a placement that judges nothing, and the skill asks the person to `rank` before a declaration.
  - `edit-assumption <assumption> [--statement] [--kind] [--entry|--input]` (c).
  - `remove-assumption` (c), refused while an experiment tests it.
  - `rank <variant> <assumption>...`, an act.
- **Experiments:**
  - `new-experiment <idea>--<experiment> --kind [--assumption] [--cycle] [--author]...` (c), so a draft may come before a cycle is planned.
  - `draft-experiment <experiment>` (c), refused once declared. It has a flag for each field:
    - `--kind`, `--assumption`, `--cycle`;
    - `--learn`, `--stopping-rule`, `--fit <count>/<of>`;
    - `--action`, `--metric`, `--direction` with `--threshold` or `--range <low> <high>`, `--source`, `--effect`...;
    - `--control cohorts|split [--exposed]`;
    - `--start`, `--end`;
    - and `--clear <field>`.
  - `remove-experiment` (c), refused once declared (DEC-003 point 3: a draft never declared is removed).
  - `record-estimate <experiment> <value>`: the person's own guess, an act, since an estimate an agent drafts in the person's name is not made alone. A second estimate by the same person replaces their first. It is refused once declared.
  - `declare`;
  - `reach-stopping-rule`;
  - `record-result <experiment> [--measured] [--spoiled] --evidence --learned`;
  - `decide <experiment> <correct-course|double-down|stop>`.
- **Cycles:**
  - `plan-cycle <idea>--<cycle> --variant <v>... --start [--days, 90 by default] --objective --key-result <variant>:<step>:<target>... --constraint-step --constraint-evidence`;
  - `change-plan <cycle>` with the same flags, while the cycle is planned;
  - `suspend <cycle> --reason --since <day> [--resumed <day>]`;
  - `resume <cycle> [--on <day>]`;
  - `review-cycle <cycle> --reached <number>... [--winning <variant>] --decision --reasons [--evidence <experiment>]...`, where the winner may be left out when the cycle explored one variant.
- **Looking:**
  - `status [<idea>] [--json]`: the return briefing (DEC-001 point 10, DEC-002 point 15), its structured form carrying `schema_version: 1`. It offers to record a suspension after a silence of 14 days, as the README states.
  - `check`, already built.

**The build,** by the first use's path. Each builder works as `software-engineer` in a worktree of its own, and the coordinator brings each builder's commits onto the Task's branch.
1. **The plumbing and the desk path:**
   - every write's rules above, the consent forms and the injectable engine, tested on each of the five ways a command meets the engine:
     - a move with one target;
     - a move with two targets;
     - an act with no move;
     - an act followed by the script's move;
     - a move whose gate the write satisfies;
   - then `set-location`, `set-goal`, `new-variant`, `add-side`, `add-entry`, `edit-entry`, `remove-entry`, `set-inputs`, `set-traction`, `judge`, `shortlist`, `estimate`, `canvas`, and a first `status`.
2. **The experiment path:** `add-assumption`, `edit-assumption`, `remove-assumption`, `rank`, `plan-cycle`, `change-plan`, `new-experiment`, `draft-experiment`, `remove-experiment`, `record-estimate`, `declare`, `reach-stopping-rule`, `record-result`, `decide`.
3. **The rest of the desk:** `remove-side`, `set-archetype`, `move-entry`, `set-authors`, `shelve`, `split`.
4. **Suspensions and reviews:** `suspend`, `resume`, `review-cycle`, and the full briefing.

The skill (phase 4) starts after builder 2, beside builders 3 and 4, since the surface is then fixed. Builders 3 and 4 go in turn, since both edit the `commands:` map and the README's commands.

**The first use** follows the skill. Before the candidate is cut, a dry run in a scratch repository: `pkit upgrade --pre` to a local build, `pkit capabilities install lean-business`, and one command. It confirms that a candidate ships a capability project-kit incubates unregistered. Whether to cut the candidate after builder 2 and the skill, before builders 3 and 4, is the person's to weigh against decision 22's cost of a second candidate. It is put to them when builder 2 lands.

## Deferred past the first slice

- **Team features:** campaigns with individual proposals and a vote, sprints and the six meetings.
- **Problem discovery:** interviews with their script, the customer forces canvas and jobs-based segments.
- **The offer:** the offer and its gates.
- **Planning and pitching:** the rollout plan beyond the first stage's target, and the pitch.
- **Growth.**
- **Tooling:** a coach agent, fixers and artefact anchors.
- **A page view,** revisited after the first real loop.
- **Results that cite evidence records,** joining the evidence capability.

## Questions for the plan

- **What may be published, and under which licence** (raised 2026-11-18, open). project-kit is MIT-licensed and public. Not legal advice, but the lines as the coordinator reads them:
  - **The method itself is free to implement.** Copyright protects how something is expressed, not ideas, methods or systems, so a capability that carries the method in its own words needs no permission. Crediting the book is honest practice, not a legal requirement.
  - **Verbatim excerpts rest on the quotation exception:** the Czech copyright act's provision on quotation, the EU's exception for quotation in criticism or review, and fair use in the US, where GitHub hosts. Each wants the source named, the extent limited to what the purpose needs, and no substitute for the work. A public file of many excerpts that walks the whole method is the weakest case.
  - **The canvas template is CC BY-SA 3.0.** A template shipped from it must credit the author and stay under that licence, apart from the MIT code. A schema in the capability's own terms is less clearly an adaptation.
  - **Names:** "Running Lean", "Lean Canvas" and LEANSTACK may be marks. Refer to them; don't name the capability after them. Their registration is not checked.
- **The view** (decided 2026-11-18): the terminal only for the first slice. The commands also print their data in a structured form, and the view is revisited after the first real loop on the board game, whatever Milestone 7's state is then.
- **The capability's name.**
- **Where versions live:** git history, with the cycle naming the commits of its canvases, or copies kept in the cycle's file.
- **One person or a team:** the per-person estimates and the merged canvases assume a team, while the first use is one person.
- **Whether an experiment links to the tracker,** as a Task or beside one.
