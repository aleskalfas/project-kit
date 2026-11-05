---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-26
---

# Decision records at the corpus's size

## The question

Do decision records hold at the size this repository has reached, and keep holding as it grows? The critic's sweep of 26 October raised six design questions (#2158). This note maps each one: the problem, with evidence from the records, the forces, two to four candidate answers with what each costs and loses, and a recommendation.

- **It decides nothing.** Each answer becomes a record, or a refinement of one, that the maintainer accepts, or the question is closed with its reason (#2158).
- **Its ground is accepted records.** Where it names a proposed record, the record is evidence of a problem, never ground.
- **Part of question 1 is decided already.** On 17 October the maintainer decided that accepting a record or a rule is always the person's act (`.pkit/scratchpad/done/2026-10-17-autonomous-feature-flow.md`, choices 1 and 3). #1674 carries that into a core record, and is open. Questions 1 and 2 build on it.
- **The defects the sweep found are filed apart:** #2154 for point citations no lookup resolves, #2155 for an accepted record resting on a proposed one, #2156 for the authoring skills, #2157 for ADR-041, and #1493 for revision markers.

**The corpus, on main at `a3d61d1d0`:**

| Id-space | Records | Lines |
|---|---|---|
| COR | 63 | 7 327 |
| PRJ | 11 | 865 |
| ADR | 70 | 11 701 |
| DEC, all capabilities | 79 | 10 896 |
| **All** | **223** | **30 789** |

The questions follow #2158's order. The first is the one the others lean on.

## 1. Who may accept a record, and may an agent accept its own

### The problem

- **The gate's own text names no one.** Acceptance is "a one-line status flip and a commit". The friction is in "the requirement that everyone look at the record and agree before depending on it" (`.pkit/decisions/README.md`, "The acceptance gate"). Who "everyone" is, it does not say.
- **The rule an agent reads every session offers the flip to the agent.** "Do not author dependent code, docs, or downstream decisions citing a proposed record — accept it first (one-line status flip + commit) or pause" (`.pkit/rules/core.md`, rule 2).
- **Accepted records say less than the maintainer decided.**
  - COR-064 point 6 lists "accepting a decision record or a rule, and every change to what an accepted one decides" among what stays a person's. It says so as a limit on the answer delegate, in a record about answers.
  - COR-051 point 4 says it of rules, under a condition: "Where that path involves a person, an agent may draft rules and propose their acceptance, but it is the person's review that accepts them." Whether a person must be on the path, it leaves open.
  - COR-025 asks that an ADR's "promotion to `accepted` is a separate gesture" ("Acceptance gate"), and does not say whose.
- **The maintainer's decision is not yet a record.** It says acceptances come "in batches, in conversation, before the work that depends on them", and the commit records whose word it was and when (the 17 October note, choices 1 and 3). #1674 asks for the core record, a PRJ record naming the maintainer, and the realisation in the README, `core.md` and the decision-author skill.
- **Six ADRs restate the rule, and cite records that do not hold it.** ADR-026, ADR-031, ADR-037 and ADR-054 say "a forward design contract, not self-accepted", each "per PRJ-005". ADR-040 says the same "per COR-041's realising-ADR delegation". ADR-053 says "Maintainer-accepted, not self-accepted". Neither PRJ-005 nor COR-041 says who accepts.
- **The history shows the gap.**
  - 42 commits on main name "the maintainer's delegation of 11 October". The 17 October note found its grant, its scope and its end written nowhere ("This session as evidence").
  - ADR-071 was written as proposed and accepted in one pull request, two commits apart (`2a58440cd`). Its message says "the project manager confirms the readings the architect asked a person to confirm". Whether a second commit in the same change is COR-025's "separate gesture", and whose word accepted it, the history does not say.

### The forces

- **A person binds a choice.** Accepting a decision, authorising a merge and judging whether a change was meant "decide what the project does. No reviewer's check stands in for them" (COR-064, "Why the line falls where it does").
- **The gate's order.** An accepted record comes before the work that depends on it (README, "The acceptance gate"). So a merge cannot accept a record that the same change builds on (the 17 October note, A2).
- **Evidence lives in the repository.** A sandboxed agent reads files, not chat. A delegate named in a session was rejected because it "leaves no record, and an agent could claim it" (COR-064, "Alternatives considered").
- **Attribution is on trust today.** Commits are signed with the person's key, and an agent passes `--yes`. Nothing tells the person's act from an agent's (the 17 October note, G12).
- **It holds for any project.** Every adopter accepts its own PRJ and ADR records, so the answer is a core one (COR-014).

### The candidates

- **A. The commit names whose word it was, given before the dependent work.** This is the maintainer's choice, and #1674's shape.
  - **Costs:** it is a claim, on trust until agents act under identities of their own (#1674's limit). COR-064 rejected a field naming who decided an answer, since "anyone writing the file can write it".
  - **Loses:** a check that the word was given.
- **B. A change that holds only the flip,** authorised by the person. COR-025's "separate gesture" fits it, and so does the analysis's path for acceptance (`UC-040`, step 3).
  - **Costs:** one pull request for each acceptance, or each batch.
  - **Loses:** the speed of a batch given in conversation.
- **C. The landing shows each flip as a finding a person must judge.** A reviewer reports each status flip, and each change to what an accepted record decides, as a `[person]` finding. Project-management DEC-055 point 3 already holds a run authorised up front on such a finding.
  - **Costs:** a reviewer's rule, or a check that emits it. It checks that an acceptance was given, and is not the acceptance.
  - **Loses:** nothing. It combines with A or B.
- **D. The merge authorisation is the acceptance.**
  - **Costs:** dependent work could land in the same change, so "accept first" collapses into one merge. DEC-055 point 3 keeps the two acts apart for answers: "authorising the merge does not give it".
  - **Loses:** the gate's order. The maintainer's choice 3 did not take it.

### Recommendation

**A, carried by #1674, with C as its check.** The question is decided. What this note adds is evidence and cases for #1674 to cover:

- an acceptance given in advance for text not yet written (question 2)
- a direct commit to the default branch, where no merge is authorised
- a merge outside the landing command, where nothing shows the list (DEC-055 point 5)
- in a team, which person may accept a record of the whole project, or of one component

The six ADRs' sentences then cite the new record. Rule 2 of `core.md` is reworded, so that it no longer reads as offering the flip to an agent. #1674 already lists that rewording.

## 2. Refining in place adds decisions without passing through proposed

### The problem

- **Three texts give three tests.**
  - The README edits a record in place "for clarifications, scope tweaks, or refinements that do not invalidate the original decision", and supersedes it for changes "that overturn the original" ("Refining an accepted record").
  - The decision-author skill says "a refinement that introduces no new decision is an edit in place".
  - COR-064 point 6 keeps "every change to what an accepted one decides" a person's. #1674 takes the same test, "in either direction".
- **A change that adds a rule overturns nothing,** so under the README's test it passes as a refinement.
- **ADR-041 point 7 is such a change.** It came into the accepted ADR-041 on 26 October, in the change that also accepted ADR-071 (`2a58440cd`).
- **Its sign-off came before its text.** Project-management DEC-059's Implications name the refinement: the fold takes its inputs from its caller, and reads no other seam. They add that "the maintainer's sign-off on this record covers that refinement, which the architect authors once this record is accepted".
- **Point 7 decides more than that list names.** It decides when a run reads the seats: at its start, and again after it waits on something outside it. It decides that a claim the fold cannot judge comes back with its reason, and that no consumer treats it as free. It also decides what a read of the mirror allows.
- **Two readings of the sign-off.** Read one way, it hands the refinement's authorship to the architect, and the list only summarises it. Read the other, it covers what it names. Nothing says which. A delegate's name has the rule "an authorisation given before that person could see it does not cover it" (COR-064 point 2), and a refinement has none.
- **DEC-035 shows the habit.** Points 1 and 2 each carry a block that calls an addition "refinement-in-place, not a supersession". Each block is also a revision marker the README forbids (#1493).
- **Rules are gated one by one.** Each rule has its own status (COR-051 point 4), and a tightened rule needs a new major version of its set (COR-051 point 7). A record's status is one field for the whole record, so a new point has no proposed state of its own.

### The forces

- **A record reads in the order of its meaning.** A new point goes where it belongs, so the record is no change log (COR-058, "Why the next unused number, and placement where it belongs"). Refining in place keeps one topic in one record.
- **Nothing binds unreviewed.** "If rules bound on being written, any draft, including one an agent wrote on its own, would take effect unreviewed" (COR-051, "Why proposed by default").
- **A drafter does not judge its own draft.** For answers, the delegate "never decides an answer it drafted" (COR-064 point 3). An author who sorts its own edits into "decides" and "does not" is in that place.
- **Supersession has its own costs.** Each partial supersession leaves overturned text in place (question 3), and adds to the records one feature needs (question 4).

### The candidates

- **A. The author lists each edit that changes what a record decides,** for the person who accepts.
  - **Costs:** the author's judgement draws the line, and the person sees only what the author lists.
  - **Loses:** an independent view of what changed.
- **B. A mechanical listing.** `pkit decisions check-diff` already compares each record a change touches with its branch point, point by point (COR-058 point 8). It could list each point of an accepted record that the change adds, alters or retires.
  - **Costs:** a new output of an existing check. It misses text outside the points, such as the Implications where DEC-059's sign-off sits, and records still in list form.
  - **Loses:** nothing. It narrows A's judgement to what it cannot see.
- **C. A status for one point.** A new point of an accepted record lands with an entry in a `proposed-points` field, as `retired-points` is kept, and binds once a later change removes the entry.
  - **Costs:** a field, its validation, and every reader checking two places.
  - **Loses:** simplicity. A record is half proposed, half accepted.
- **D. A new decision is a new record.** It refines the older record by a pointer, as ADR-071 sits beside ADR-041, or supersedes it, the sweep's counter-alternative.
  - **Costs:** more records, and more partial supersessions (question 3).
  - **Loses:** one record per topic.

### Recommendation

**#1674's test in the README's refining rule, shown to the person by B, with A for what B cannot see.** The test is whether an edit changes what a record decides, in either direction. It replaces "overturns" as the line between an edit and an act of acceptance. For an edit that is itself the work, the person's mark on that head is the act (#1674). So an advance sign-off, such as DEC-059's, does not stand in for it. D suits a large addition, or one another owner's record decides. C is not taken: it adds a second vocabulary of statuses.

## 3. A point another record overturns stays as it stood

### The problem

- **The form is deliberate.** A point another record overturns "is not retired. It stays as it stood, and the record's top line reads *Partially superseded by …*" (COR-058 point 5, and the README's "Refining an accepted record", step 2).
- **13 accepted records carry such a line:** COR-001, COR-004, COR-005, COR-017, COR-050, COR-057, PRJ-003, ADR-049, project-management DEC-003, DEC-035 and DEC-045, and software-analysis DEC-001 and DEC-002.
- **DEC-035 point 1 still reads "The presence of the id is the sole activation gate."** DEC-059 overturned that for a project with a topology. The record's top line says so, and the passages are listed in a third place, DEC-059's "What this overturns, and what stands".
- **The same section mixes three things.** DEC-035 point 1 also gained a sentence refined in place for DEC-058. So the section holds text that stands, text overturned for some projects, and text added later.
- **COR-001 still says "the core layer guarantees a one-time write at first install for each declared seed path"** (COR-001, "Install-time seeding"). COR-059 overturned it.
- **A reader who follows a citation lands below the banner.** `pkit refs lookup` prints a point's file and its heading's anchor (README, "Looking a citation up").
- **Friction is not the gap.** A point anchor stands on the record's preamble, its body before the first section (COR-050 point 5). So a page anchored to `DEC-035#1` was flagged when the banner came. The gap is a reader, a person or an agent, who cites or looks up the point.
- **The need surfaces by itself.** DEC-033 carries "Amended in part by DEC-034" inside its body, at the point it concerns, in a form validation warns of.

### The forces

- **An overturned passage keeps its words,** so the history reads true and the overturning record holds the reason.
- **One home for each fact** (COR-006, "The discipline", point 1). The overturning record lists the passages it overturns.
- **An overturn can be partial and conditional.** DEC-059 overturns parts of DEC-035's points, and only "for a project with a topology".
- **COR-058 set the pattern** for a retired point: data for tools, a stub for readers, and validation holding them together (COR-058, "Why both an entry and a stub"). Successors stay in one record, so the entry is checkable from that record alone ("Why successors stay in the record").

### The candidates

- **A. A pointer at the point.** One line under the point's heading, such as "Overturned in part by DEC-059."
  - **Costs:** an edit to the older record at each partial supersession. COR-058 point 5's "stays as it stood" would change.
  - **Loses:** precision. A fixed line cannot say which part is overturned, or for which projects, so the reader still needs the overturning record's list.
- **B. Data in the overturning record, read in reverse.** A field maps each record it overturns in part to the points it touches. The lookup, given a point, finds every record that names it, and prints them with the point.
  - **Costs:** a field, its validation against the overturning record's own list, and a reverse read in the lookup.
  - **Loses:** a person reading the older file sees only the banner.
- **C. The lookup alone.** `pkit refs lookup` prints a record's partial-supersession line with any point of it.
  - **Costs:** the smallest of the four. It needs no field.
  - **Loses:** it says the record is overturned in part, not whether this point is. It reaches only readers who use the tool.
- **D. No partial supersession.** A record that overturns part of another supersedes it whole, and restates what stands.
  - **Costs:** long restatements. DEC-059 would restate most of DEC-035 and DEC-045.
  - **Loses:** every citation of the older record moves, against the permanence COR-058 protects.

### Recommendation

**C at once, then B.** C looks small enough for an issue on its own. B leaves the older record as it stood, so COR-058 point 5 holds, and keeps the list in its one home. B is new data a record decides, so it is accepted as question 1 sets. A is not taken, since one fixed line cannot carry a partial or conditional overturn.

## 4. Records grown into specifications

### The problem

- **Some records are long.** ADR-035 holds 1 312 lines, ADR-041 757, software-analysis DEC-001 670 and ADR-026 645.
- **One feature takes over 2 000 lines.** Instance ownership rests on project-management DEC-026, DEC-035, DEC-043, DEC-045, DEC-058 and DEC-059, with ADR-041 and ADR-071. Together they hold 2 146 lines, overturned passages among them (question 3).
- **They hold the what-is.** ADR-035 names functions and modules, such as "`resolve_children` in `_lib/containment.py`", the fields a call returns, and each site it governs.
- **COR-006 places that in a document, for the records it names.** Its discriminator gives a document "state / reference — the *what-is*: schemas, structures, contracts", and a "Decision (COR/PRJ)" "a choice among alternatives — the *why*" (COR-006, "The discriminator").
- **Whether that reaches ADRs is part of the question.** COR-006 predates the ADR and DEC namespaces. COR-025 gives "What did we build?" as an ADR's question ("Distinct from PRJ"). A family of accepted ADRs calls itself a contract: ADR-026, ADR-031, ADR-035, ADR-041 and ADR-053.
- **project-kit has no architecture document besides its records.** Its overlay names `CONTRIBUTING.md` and the core records as its architecture documents (`.pkit/agents/project/overlay.yaml`, `architecture-docs`). So the ADRs carry the contracts.
- **The what-is drifts inside a record.** ADR-041's Context still calls the feature "gated, not yet built", and the code is built (#2157).
- **A route to catch it exists, unused.** ADRs sit inside the internal documentation root, so they are artefacts that may anchor the code they govern. "A record that anchors the code it governs is what the core record wants" (ADR-055 point 3). None does yet.

### The forces

- **An agent starting cold needs the why,** or it reopens settled questions. A builder needs the what-is. Both are in the records now.
- **A choice is stable, and a description of state moves with the code.** "Decisions are stable choices; docs describe state. Different lifecycles, different audiences" (COR-006, "Alternatives considered").
- **A living document is not gated.** It is friction-checked (COR-050), but nothing accepts it. An invariant moved into one could change with no acceptance, against what question 2 asks.
- **The architect keeps both.** It owns the architecture documents (COR-024), and keeps and audits the ADRs, flagging drift (COR-025, "Custodianship"). Its audit is optional and periodic (the architect's definition, "Periodic — drift audit"), so drift waits for the next one.
- **Length alone is not the fault.** A short record with a long specification costs a builder as much to read. It costs less to whoever reviews the choice.

### The candidates

- **A. A short record, linked to a living specification.** The record keeps the choices and invariants, such as a sole constructor, comment-log-wins, or "no consumer treats an unjudged claim as free". The current names, signatures and call sites move to an architecture document anchored to the code and to the record.
  - **Costs:** a document for each family of seams, a split of the largest ADRs, and the line between an invariant and a signature, drawn by judgement.
  - **Loses:** one file per topic.
- **B. A size warning.** Validation warns of a record over a line count, and fails nothing.
  - **Costs:** almost none.
  - **Loses:** nothing, and settles nothing alone. It can teach authors to trim to the number.
- **C. A digest of what holds now, computed on demand for an area.** A command reads the accepted records, and their overturned points, and prints the points that bind on an area.
  - **Costs:** it needs question 3's data and question 5's lookup. A file it wrote and committed would drift, as COR-051 found for a generated view of rules ("Alternatives considered").
  - **Loses:** the why. A reader still opens the records for it.
- **D. Rules with an origin as the default carrier,** a full record only where alternatives are contested.
  - **Costs:** a rule binds only on artefacts (COR-051 points 1 and 2), and code is no artefact (COR-050 point 1). A design rule on code could not bind without widening both records.
  - **Loses:** the alternatives considered, which keep a rejected idea from coming back.

### Recommendation

**A, for each new ADR, and for an existing one when it next comes up for revision, with B as the prompt to split.** The invariants stay in the record, where question 2's gate reaches them. The current names and sites move to the document, where friction keeps them true. No backfill: one record at a time, as COR-025's Implications take PRJ records into ADRs.

The place may need no record. The technical space at `tech-docs/` already holds maintainer-facing documents (ADR-055 point 3), and the overlay's own comment names `tech-docs/architecture/` for a conventional layout. Repointing `architecture-docs` there also mends a conflict. Today the overlay hands the architect `.pkit/decisions/core/`, while its definition says it owns no path under `.pkit/`.

C waits for questions 3 and 5. D asks more of rules than COR-051 gives them.

## 5. Finding the records that apply

### The problem

- **Lookups go from an id outwards.** `pkit refs lookup` prints the file an id names (README, "Citing"). `pkit refs who-references` takes a path, a record id or a hook, and lists the agents and skills that reference it. Nothing goes from a path, a command or a topic to the records that govern it.
- **Rules have the answer records lack.** "The backbone answers, for each artefact, which accepted rules bind on it. Writers, checks and reviewers all read that one answer" (COR-051 point 7).
- **No rule asks an agent to look.** `core.md` rule 2 tells an agent to act only on accepted records. Nothing tells it to find the records that bear on what it changes. An agent that does not know a record exists will not follow it.
- **An adopter receives every core record.** That is 63 records and 7 327 lines, with each installed capability's records beside them. The project's own PRJ and ADR records stand out only by their prefix.
- **Code cites records in forms no tool reads.** `instance_ownership.py` cites "ADR-041 §2" (#2154).
- **The data for a lookup exists in part.** Documents anchor paths, records and points (COR-050 point 2). Records inside a documentation root may anchor the code they govern too (ADR-055 point 3).

### The forces

- **Records are cited, not loaded.** No agent reads 30 000 lines, so finding a record is what makes citing work.
- **An index kept by hand drifts.** The README allows one, "a `README.md` index … inside `project/`" ("Adding a record"). A computed one is only as good as the anchors it reads.
- **Files only.** A sandboxed agent has no search service, and no network.
- **A record that anchors code owes an answer each time that code changes** (COR-050 point 5). That is the debt, and also the drift check question 4 lacks.

### The candidates

- **A. A computed lookup from a path to its records.** A command reads every anchor in the tree, and lists the accepted records and points tied to a path. A record's own path anchor ties it directly. A document's path anchor ties the records that document anchors.
  - **Costs:** a command over data the tree holds. No new field.
  - **Loses:** a record tied through a document is related to the path, not proven to govern it. A path nothing anchors finds nothing.
- **B. Records anchor the code they govern,** as ADR-055 point 3 wants of a record inside a documentation root.
  - **Costs:** each such record owes an answer when its code changes, and a long specification makes that answer costly (question 4). A record a project receives by sync is never one of its places (COR-050 point 14), so B reaches a project's own records only.
  - **Loses:** some of a record's stillness. A code edit flags it.
- **C. Records name the paths they govern as a scope,** as a rule set does (COR-051 point 2), with no anchors.
  - **Costs:** a field, and a second way to tie a record to code beside anchors.
  - **Loses:** drift goes unflagged, since a scope owes no answer.
- **D. A rule in `core.md`:** before changing a path, look up the records that govern it, and cite them in the change.
  - **Costs:** one rule.
  - **Loses:** nothing, but without A it asks for a search an agent cannot make.

### Recommendation

**A first, then D, with B taken for an ADR as it comes up for revision (question 4).** A rests on anchors COR-050 already decides, so it may need only an issue and the README's text. It can list the project's own records first, which narrows an adopter's search. B is the direction ADR-055 point 3 already takes, and pairs with question 4's split: a short record anchored to the code costs little to revalidate. C is not taken, since it ties code without catching drift.

## 6. Proposed records that linger

### The problem

- **Two records are proposed on main.** Project-management DEC-025 has been proposed since 27 May, and ADR-054 since 15 September.
- **ADR-054 names what it waits on.** "Acceptance is sequenced behind #795", which is open (ADR-054, Implications). DEC-025 waits "until the open-questions section is resolved from lived evidence", with no owner and no date (DEC-025, its status note).
- **A later record decides part of DEC-025's question without citing it.** DEC-059 decides the ready frontier: a worker takes a Task "that names no open issue among its dependencies" (project-management DEC-059 point 7). It leaves the lanes, DEC-025's code-surface half, aside, and names typed dependencies as not built (its Implications).
- **An accepted record leans on it.** DEC-045 rests on "the overload DEC-025 already rejected" (#2155). The gate says decisions "cite only accepted predecessors" (README, "The acceptance gate").
- **Only rules are checked for this.** A rule's cited record must be "accepted whenever the rule is accepted" (COR-051 point 5). Validation knows a record's three statuses as valid values only (`VALID_DECISION_STATUSES` in `src/project_kit/validate.py`). #2155 asks for the check for records.
- **Nothing ends a landed proposal but acceptance or supersession.** "There is no `rejected` state — a rejected proposal is deleted before it lands" (README, "Statuses").
- **DEC-025's own note is still active.** `.pkit/scratchpad/active/2026-05-26-parallelization-primitive.md` mapped the design that DEC-025 recorded.

### The forces

- **A proposal can serve as a map,** cited for its terms. DEC-025 says it lands "for cross-DEC coherence".
- **A scratchpad note is the carrier for what might become** (COR-006, "The discriminator", and COR-012). A record waiting on lived evidence is a scratchpad note in all but its name.
- **A date alone is crude.** A record that waits on a named, open issue is fine.
- **Rules already have a way out.** A rule may be withdrawn, retired without a successor (COR-051 point 4).

### The candidates

- **A. A proposed record names what it waits on,** an issue or a record. A report lists each proposed record whose condition has closed, or that names none. A cheaper form lists each proposed record by its age.
  - **Costs:** a field, and a report that reads the tracker. Validation reads the working tree, and settled state only through a slot (COR-055 point 2), so the report sits beside it, such as in the project's status.
  - **Loses:** nothing a reader needs.
- **B. A `withdrawn` status for records,** as rules have it. A proposal whose reason is gone stays, with its ideas, and binds nothing.
  - **Costs:** a status, its validation, and the README's statuses.
  - **Loses:** the "no rejected state" simplicity.
- **C. The design goes back to its note.** A design that waits on evidence stays a scratchpad note, and the proposed record leaves.
  - **Costs:** removing DEC-025 removes a file a capability ships, a surface change with the migration `core.md` rule 7 asks.
  - **Loses:** a citable id.
- **D. A landed proposal is deleted on the person's word.** The README keeps every superseded record, and says nothing of a proposed one once it landed.
  - **Costs:** for ADR-054, a project-owned file, nothing. For DEC-025, the same migration as C.
  - **Loses:** the record's text, except in history.

### Recommendation

**A as the rule, with question 1's person as the one who closes a proposal.** DEC-025 itself waits for #2155, so that nothing accepted rests on it. Then the person chooses between C and B for it. C is cheaper while DEC-025 is the only case. B earns its cost only if a second case appears (COR-007).

## How the questions couple

- **Every carrier changes accepted text,** so question 1's answer governs how each is accepted.
- **Question 2 leans on question 1** for what the person must be shown, and question 6 for who closes a proposal.
- **Question 2 and question 4 meet at the gate.** Question 4's split keeps invariants in the record, so that question 2's gate still reaches them.
- **Question 4 and question 5 meet at anchors.** A short ADR anchored to its code answers question 4's drift and feeds question 5's lookup.
- **Question 3's data comes before question 4's digest,** and question 5's lookup before its rule.

## What could carry each answer

- **Questions 1 and 2:** #1674's core record, with the cases and the test this note adds. The README's gate, its refining rule and `core.md` rule 2 follow.
- **Question 3:** an issue for the lookup, then a record for the overturning record's new field.
- **Question 4:** the overlay's `architecture-docs` repointed, and the decision-author skill's guidance for ADRs. COR-006's reach over ADRs may need a record of its own.
- **Question 5:** an issue for the lookup, then a rule in `core.md`.
- **Question 6:** a refinement of the README's statuses, beside #2155.

A change to the README alone needs no record. One large enough is a record about that change to the README (`CONTRIBUTING.md`, "Refining the spec itself").
