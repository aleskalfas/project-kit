# project-kit's building blocks: why each is there, and what an adopter gains

Working notes for the Friday talk (goal reconsidered 26 October: present project-kit, its building blocks and its motives; show how light it is and what it gives without capabilities). One block at a time, with the maintainer. For each: what it is, the problem it answers, the adopter's gain, its weight, evidence, and the honest weak spot.

## The list

**A. What the agent remembers**
1. Decision records: `.pkit/decisions/`
2. Rules: `.pkit/rules/`
3. Scratchpad notes: `.pkit/scratchpad/`

**B. How the agent works**
4. Skills: `.pkit/skills/`
5. Agents, the reviewers among them: `.pkit/agents/`
6. Adapters: `.pkit/adapters/`

**C. What the agent may do**
7. Permission model and sandbox: `.pkit/permissions/`
8. Agent workspace, and the cross-repository guard

**D. What stays true over time**
9. Anchors and answers (friction): documents know what they rest on
10. Rule sets: writing rules a reviewer judges
11. Validation: `pkit validate`, one check of everything

**E. How it reaches a project and stays current**
12. The CLI: `pkit`
13. Lifecycle: install, sync, upgrade, and migrations
14. Ownership: core files and project files, never shared (`.pkit/project/`)
15. Versioning and release

**F. How it is extended**
16. Schemas: rules as data
17. Process substrate: staged processes with gates
18. Connections: how components hand each other data
19. Capabilities: opt-in disciplines (project-management, software-engineering, software-analysis, living-docs; and evidence, doc-examples, demo-recording)

## 1. Decision records

- **What:** each significant choice is a record with one shape: front matter (id, title, status, date, author) and four sections, Context, Decision, Rationale, Implications, the decision split into numbered points that keep their numbers for good. Four namespaces: COR for the methodology's own (63), PRJ for the project's way of working (11 here), ADR for its architecture (70 here), DEC for each capability's (78). A record is proposed, accepted or superseded.
- **Problem:** the why behind a choice lives in someone's head or a chat that ends. Code shows what was built, not why, nor what was rejected. An agent starting cold re-opens settled questions, proposes what was already rejected, or reverses a choice without knowing it was one.
- **Gain:**
  - one place for every why, with the alternatives that lost, so a rejected idea is not proposed again
  - the acceptance gate: only an accepted record may be built on. A proposed record is a draft, and an agent may not write code or other records that rest on it. A person's acceptance is the moment a choice binds.
  - a stamp command and an authoring skill, so numbering, front matter and the disciplines are never hand-made
  - stable ids and point numbers, so anything can cite exactly what it rests on ("DEC-059 point 7"), and a check finds every citation that no longer resolves
  - the adopter gets the same for its own records (PRJ, ADR), with the same tooling and checks
- **Weight:** Markdown files, no runtime. The real cost is the discipline: writing a record for each significant choice, and reviewing it.
- **Evidence:** 26 October, DEC-060 (foundation before slices): four rounds of critic and methodology-reviewer before acceptance found real flaws, such as a skeleton built on proposed records and coupled choices decided by several agents at once, all before any code rested on it.
- **Weak spot:** records grow long and dense (DEC-059 is some 200 lines). The "lead with meaning" discipline (a plain-terms summary first) answers it in part. Writing and reviewing a record takes time, worth it only for choices that matter.
- **Maintainer's notes:** decisions come first: the rest of the methodology is built from them.

### Grilling decision records (26 October)

Objections raised by the project manager, with its answers and where they are weak:

1. *Git history is the record.* Commits are scattered, uncurated, never marked replaced; no agent reads 2 000 PR bodies. Concession: most choices need only a commit message; a record only for a choice that binds future work.
2. *Agents do not read them; 220 records cannot fit a context.* They are cited, not loaded, and citations are checked. Weak: discovery; an agent that does not know a record exists will not follow it.
3. *Ceremony costs more than it saves.* DEC-060 took about two hours of rounds; the one-sentence version had four real holes. Weak: returns diminished after round two; no rule for when to stop reviewing.
4. *Records drift from the code.* Documents resting on records are flagged; the analysis boxes decided-not-built steps. Weak: nothing checks code against a record; hence the gap-first principle.
5. *The gate is a one-person bottleneck.* Deliberate: a person binds a choice. Weak: in a team, who accepts which record is undecided; COR-064's delegate covers answers, not records.
6. *ADR tools exist (MADR, adr-tools, log4brains).* The format is close to MADR; pkit adds the gate agents obey, stable point ids, citation checks, the link to documents. Concession: for ADRs alone, MADR suffices.
7. *Four namespaces confuse.* They follow ownership. Concession: an adopter reads COR and writes PRJ and ADR; show those two.
8. *Does it change agent behaviour?* Anecdotes only (builders stop on proposed records; reviewers block on broken citations); no measurement.

Survives: records for binding choices, the gate, precise citations. To admit: most choices need none, discovery is not guaranteed, no code-against-record check, no stopping rule for reviews, team acceptance undecided.

The critic's independent attack (26 October), in short:

- **Red flags:**
  1. The gate is hollow at two seams: nothing says who may accept, or forbids an agent accepting its own record; and refining in place adds new rules to accepted records without passing through proposed (ADR-041 point 7, written after DEC-059's sign-off).
  2. Partial supersession leaves overturned text unmarked at the point; a lookup by point skips the banner (DEC-035 points 1 and 2, COR-001's seeding). An agent reads the section it was pointed at and believes it.
  3. The repository breaks its own rules: revision markers (DEC-033, -035, -041, -047, -049); accepted DEC-045 leans on proposed DEC-025; ADR-041's Context says "not yet built" of built code; 42 citations in a form no tool resolves ("DEC-035 D6"); inventory and issue plans inside records.
  4. Records grew into specs: corpus about 29 000 lines; ADR-035 1 312 lines; one feature (ownership) means 2 000+ lines of records to read.
  5. The decision-author skill, shipped to adopters, rests on CONTRIBUTING.md sections that adopters never receive, and on example projects they do not have.
- **Gaps:** no lookup of records by topic or path; the gate is enforced in code for rules but not for records (capability DEC statuses are not indexed, a bare DEC-NNN is not parsed); proposed records never expire; at 2 000 records nothing addresses retrieval; every adopter receives 63 COR records (about 7 300 lines).
- **Survives:**
  1. plain files in the repository, which a sandboxed agent reads with no network or tracker access (the strongest point for this audience, and the README does not make it)
  2. stable ids and one citation form, so code, rules and skills point at the why, and the rules file stays short
  3. a person ratifies an agent's draft, by one diffable line
  4. number clashes between parallel branches are caught (COR-058 point 8)
  5. the ownership split: received records arrive read-only and refresh on sync
  6. "Alternatives considered" as memory against re-arguing (plausible; get one real case)
  7. the format works at small size (PRJ-001 35 lines, ADR-001 90)
- **Net claim that holds:** short, ratified, citable why-documents in the repository, which sandboxed agents can reach and code can point at.
- **Counter-alternatives worth naming:** short immutable MADR-style records; rule-with-origin as the default and a full record only when alternatives are contested; a short decision linked to a living spec; a generated "what holds now" digest per area.

### The maintainer's framing (26 October, after the attack)

Decisions are the system's design source, not runtime context. The system is built logically from arguments: when the maintainer and the agent change the system, they create or amend the decisions first, and the system (code, docs, rules, skills, schemas) is the projection of the new state. At runtime, agents load the projection (the rules file, skills, commands), and a rule only cites its record for the why. Agents read records in one mode: changing the system (design, building a record, reviewing a change against what is accepted), which rule 22 now names.

What this does to the attack: the context-size objection dissolves (nobody loads all records); "records grew into specs" gets stronger (implementation detail is projection leaking into the source; #2164); drift, unmarked overturned points and who accepts stay real, because they damage the source.

Talk claim: decisions are the source, the system is their projection. Change the decision first, then the system follows, and checks show where the projection lags (the analysis's "not built yet" boxes, the change check).

Finding: pkit does not state this anywhere an adopter reads. COR-006 gives records the why; CONTRIBUTING's axiom framing is maintainer-only; the acceptance gate says only "build on accepted"; core analysis has UC-037 (record a decision) and JRN-003 (deliver a change built on accepted records), but no flow "a change starts with its decision, and the system follows".

## 2. Rules

- **What:** one file of operational rules (`core.md`, 21 rules, about 2 400 words) loaded into every session through the harness's include, plus the project's own `project.md`, which the project owns.
- **Problem:** an agent starts each session knowing nothing of the project's working rules. Without them it is told again each time, or breaks them.
- **Gain:** every session and every agent starts from the same rules, with no re-explaining. Each rule is short and cites where its reason lives. Updates arrive with sync, and the project's own rules are never overwritten.
- **Weight:** one file in the context of every session (about 2 400 words for core).
- **Evidence:** rules born from incidents: the agent workspace (#1043, prompts on the maintainer's phone at night), retry once then stop (#1648).
- **Relation to records:** the rules are the operational digest of the records, each citing the record behind it.
- **Weak spot:** a rule loaded is not a rule followed. Rules state; other blocks (permissions, validation, reviewers) enforce.
- **Maintainer's notes:** see the draft below.

## 2. Rules (draft for discussion, written overnight by the project manager's helper)

*Facts checked against the repository on 27 October. The short draft above says 21 rules and about 2 400 words; since rule 22 merged, core holds 22 rules and 2 531 words.*

- **What:** numbered instructions that every agent session loads before it does anything. Two files. `core.md` ships with the methodology: 22 rules in seven sections, 81 lines, 2 531 words. Sync replaces it, and a project may not edit it. `project.md` is the project's own: in project-kit, 4 rules, 14 lines, 406 words. Sync never touches it. The project's `CLAUDE.md` pulls both in with two include lines, which install adds after its first heading without touching the rest. A rule is one bold sentence, a few lines on how to apply it, and a pointer to where its reason lives: a record, an area README, or, where neither holds it, the issue that decided it.
- **Not rule sets (block 10):** an operational rule is an instruction every session loads, with a number but no id, origin or status; a rule in a rule set is a writing rule with an id, accepted through review, that a reviewer judges a document against.
- **Problem:** an agent starts each session knowing nothing of how the project works. Yesterday's instructions are gone. So the person repeats them in every prompt, or the agent breaks them. Instructions kept in prompts are also never reviewed: on 17 October, over two hundred brief files in the agent workspace repeated the same stop rules, and no commit carried them.
- **Gain:**
  - every session and every helper agent starts from the same rules, with no re-explaining
  - a rule stays short because its reason lives elsewhere; the why is one link away
  - one test decides where a rule goes: would it be useful in any project (COR-014)? If yes, it ships in core and arrives updated on sync. If not, it goes in the project's file, which sync never overwrites.
  - documents that rest on the rules file are asked to recheck when it changes (16 of them here)
  - a rule is the cheapest home for how an agent should behave: one sentence, no code. When the behaviour must hold even under pressure, a mechanism takes it over (a permission deny, a check, a reviewer), and the rule stays as the teaching.
- **Weight:** one file in every session and every helper agent: about 17 KB, roughly 4 000 tokens (estimated from size, not measured). Plus the project's own rules. Nothing runs at session time. The real cost is keeping the file short and current.
- **Evidence:**
  - Grown from need, one rule at a time: 13 rules and 925 words on 13 June, 22 rules and 2 531 words on 27 October, 15 commits in between.
  - Rule 22 (when you change the system, read first the accepted records its files lead to) came out of preparing this talk. Issue #2165 opened in the afternoon of 26 October. The maintainer accepted the rule that day, with the maintainer's own framing as its second sentence: "The records are where the system is decided, and the files carry those decisions out." It merged at 00:19 on 27 October (ba8a03615).
  - Rule 21 (retry once, then stop) and the recommendation in rule 17 came from the maintainer's answer of 17 October (#1648). The stop rules lived only in briefs, repeated over two hundred times and never reviewed. Each went to a home by its kind: conduct for any agent into the core rules, signing into project-kit's own rules (project rule 4), two into deny rules of the permission profiles, two into the pm skill.
  - Rule 16 (keep scratch files in the agent workspace) came from #1043: every write outside the repository asked the operator, one file at a time, for the whole session, until the operator approved without reading.
  - The core and project split at work: in June a sandbox rule moved from `project.md` to `core.md`, reworded to fit any project, so adopters get it (#71).
  - The repository names the limit itself. ADR-028: "a teaching rule is advice, not a mechanism". So the sandbox escape that rule 14 forbids is also sealed by configuration when agents run unattended, and the rule stays.
  - Rules reach a session only when it starts. The helper that wrote this draft had core rules 1 to 21 in its context, not 22: its copy was loaded before rule 22 merged, though the file on disk holds it.
- **Weak spot:** a rule loaded is not a rule followed, and nothing measures how often it is. The file grows, and the rules lengthen: the first thirteen rules average 60 words today, the nine added since 161. Rule 20 is 340 words in some fifteen sentences; the README's "terse" does not describe it. Rules have numbers, not ids, and the numbers move.
- **Maintainer's notes (28 October):** rules are the projection of the decisions into every session (block 1's framing carried into run time). Not every session needs every rule, but slicing was examined and deferred: by permission it couples two unrelated things, by agent it misses the main session, and by the files a rule governs it arrives late or never where the breaking act is the first touch, and fails silently ([scratchpad](https://github.com/aleskalfas/project-kit/blob/docs/scratchpad-rules-sliced/.pkit/scratchpad/active/2026-10-28-rules-sliced-by-files.md)). Now: permanent rule numbers (#2260), the rules trimmed (#2261), a size budget `pkit validate` checks (#2262), and the missing rule on when a record starts (#2258).

### Grilling rules

Objections a sceptical engineering audience would raise, with the honest answer and where it is weak:

1. *It is just a prompt file.* The content is. pkit adds what sits around it: an owner for each file, a test for where a rule belongs, a reason behind each rule, a reviewer agent meant for each change (methodology-reviewer), documents that recheck when the file changes, and the move to a mechanism when a rule must hold. Weak: the file itself has none of what records have. No id, no status, no gate, no check that its citations resolve.
2. *Agents ignore long instructions.* Partly true, and the repository agrees: ADR-028 sealed the sandbox escape because rule 14 alone is "advice an agent under pressure can still override". The answer by design: keep each rule short, cite out for the why, and back anything that must hold with a mechanism. Some sign that agents follow: the 17 October note records a builder that stopped on signing that failed twice, and before a destructive operation (rule 8). Weak: anecdotes, not measurement. And the file pulls the other way: 2.7 times the words since June.
3. *Rules drift from the records they cite.* They do, and the repository shows it. Rule 12 still calls `deploy-agents.sh` "future", though it is in the repository's first commit. Rule 7 says `pkit migrations check-diff` verifies "when available"; it runs in CI on every pull request. Numbers move: "one decision at a time" was rule 14, then 15, 16, and now 17. DEC-045 still cites "rule-18" for the cross-repository rule, now 19; issue #1687 has been open since 17 October. Rules are cited by number at least 91 times in 53 files. What protects: documents resting on the rules file recheck when it changes. Weak: nothing goes the other way. `pkit refs records-for .pkit/rules/core.md` reports no record tied to the file, so a change to a cited record asks no rule to recheck. And the citation check reads skills and agents, not the rules file.
4. *Every project has a CLAUDE.md already.* True, and pkit keeps it. Install adds two include lines after the first heading and never rewrites the rest. The gain is sharing: 22 rules kept by someone else, each with its reason, current after each sync, and the project's own rules left alone. Weak: for one project alone, a hand-written CLAUDE.md does most of this. And project-kit blurs its own split: its CLAUDE.md is 1 981 words, close to `core.md`, and restates rules 2, 7 and 9. That makes three places for instructions where the README names two.
5. *Who decides a rule?* For core, the methodology's maintainer, in a pull request checked against the test of usefulness to any project. For project rules, the project. Weak: rules have no proposed state. A rule binds as soon as it is in the checkout a session starts from, so a branch's edit binds that branch's agents before any review. No skill or command adds a rule (rule 3's list leaves rules out), and CONTRIBUTING says nothing on it. An adopter cannot switch a core rule off. It can only add rules in `project.md`, and where the two disagree, the agent picks.
6. *Context cost.* About 4 000 tokens per session, and again per helper agent, since each one loads the file. Small next to the whole context, large next to a typical prompt. Weak: not measured. And much of it serves pkit itself, not the adopter's work. Rules 5, 7 and 13 bind whoever writes a migration, changes a methodology-owned file, or writes a file meant for include; most adopter sessions do none of these, yet carry them. By my count, seven rules (8, 9, 15, 17, 18, 19, 21) are conduct any agent needs anywhere; the other fifteen steer pkit's own parts.
7. *Then why not records, or code, for everything?* A record explains a choice and is read when the system changes; a rule is the short form every session needs. Behaviour such as "ask one decision at a time" or "say what a rule means before its id" cannot be a check. Weak: where a rule ends and a mechanism must start is judged case by case. On 17 October two stop rules were sent to deny rules in the permission profiles; I could not find them in the shipped profiles.

Survives: one short file every session loads, owned and refreshed by the methodology, beside one the project owns; each rule pointing to its reason; one test for what goes where; and the habit that lets the file grow honestly: text repeated in prompts becomes a rule (over two hundred briefs became rule 21, a line of rule 17 and project rule 4), and a rule that must hold gets a mechanism behind it (rule 14 and ADR-028).

To admit: a rule is advice, and how often agents follow it is not measured; the file has nearly tripled since June, and some rules are long; numbers move, and stale citations exist (#1687); nothing asks a rule to recheck when the record it cites changes; a rule change reaches a running session only when a new one starts; rules have no proposed state, and an adopter cannot switch a core rule off; several core rules serve only those who change pkit itself; project-kit's own CLAUDE.md restates rules the file already holds.

## 3. Scratchpad notes (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** a working draft for a question too big to decide on the spot (COR-012). One Markdown file per question in `.pkit/scratchpad/`; the folder is its state: `active/` while it is worked, `done/` once it has produced records, documents or tools (its front matter lists what), `dropped/` when the line is abandoned, with the reason. It is not normative: it may restate, contradict, try and discard. `pkit new scratchpad <slug>` starts one (with the `scratchpad-author` skill); `pkit scratchpad done <slug> --produced <ref>…` and `pkit scratchpad drop <slug>` retire it.
- **Problem:** a large question does not fit a record on the first pass, and a conversation is gone the next session. Without a place for the exploring, the agent either decides too early or the reasoning, the rejected lines included, is lost.
- **Gain:**
  - the exploring has a home that outlives the session, and anyone, agent or person, can pick it up
  - rejected lines are kept with why they fell, so nobody walks them again
  - a retired note names what it produced, so a record can be traced back to how it was reached
- **Weight:** nothing loads at session time; a note is read only when its question is worked. One small area README and four commands.
- **Relation to blocks 1 and 2:** decisions are the source, and rules their projection; a scratchpad note is where a decision is worked out before it becomes a record.
- **Evidence:**
  - 57 notes since 22 May: 25 retired as done, 32 active, none dropped
  - the 25 done notes produced between 1 and 14 artefacts each; most retired within a few days of starting (the multi-clone coordination arc: 5 days, 14 artefacts; the autonomous feature flow: 1 day, 14)
  - the walk through a brownfield project that produced the first core records (`done/2026-05-04-inventory.md`) is named in `CLAUDE.md` but is not in the repository: it predates the repository's first commit
  - this week: release candidates (the note became the records of PR #2224), what answers are and should be called (on its own branch), which rules reach which session (on its own branch, written today after two critics took the slicing apart)
- **Weak spot:**
  - nothing checks a note's state: one note sits in both `active/` and `done/` (#2263)
  - non-normative by design, so nothing stops someone building on a note's idea before it is a record; the acceptance gate speaks of records only
- **Maintainer's notes (28 October):** a scratchpad is the desk of a home office: papers where ideas are caught before they become real assignments, issues or records. Like papers on a desk, some stay a long time while it is not decided whether they are wanted, and that is fine: 16 notes older than July are undecided ideas, not neglect, and none dropped means none was decided against. Branches are parallel universes of the same office: a note on a branch lives in that universe; some universes join the original, some wait for their moment, and some notes never need to outlive theirs. The scratchpad is not rigid: it is a place for ideas, and when the person picks one up, the machinery is there to track it into issues and records. Talk line: question, then a note, then a record, then the rules.

## 4. Skills (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** a skill is a procedure an agent runs when a kind of task comes up: write a decision record, file an issue, author a migration, plan a batch of work. project-kit deploys 14: eleven from core (nine authoring skills, such as `decision-author`, `migration-author`, `scratchpad-author`, and two composite ones, `schema` and `process`) and three from capabilities (`pm`, `analysis-author`, `docs-author`). Each lives once in `.pkit/` and the adapter links it into `.claude/skills/`. A skill is paired with a command (COR-005): the command does the deterministic part (the next number, the file's layout), the skill carries the judgement (which kind of record, the disciplines, the wording). A composite skill (COR-020) dispatches to sub-procedures: `pm` holds create-issue, validate-body, transition-state, batch-plan, fix-drift and work-loop.
- **Problem:** asked to "add a decision", an agent improvises: it picks a number, a layout and a level of care, differently each time. The rule "invoke the skill, never hand-stamp" (core rule 3) came from a record filed by hand with the wrong number (PR #16).
- **Gain:**
  - the procedure is written once and runs the same way every time, for any agent
  - judgement in the skill, determinism in the command: neither has to do the other's job
  - each skill names the records it rests on (`gates:`) and stops if one is not accepted, so a procedure never runs on a draft decision
- **Weight:** only each skill's description sits in a session's context (31 to 169 words; 14 of them); a skill's body loads when it is invoked. Bodies run from about 900 words (`scratchpad-author`) to about 2 600 (`capability-author`); the composites are larger (`schema` and `process` about 5 800 each, `pm` and `analysis-author` about 15 000) but load one sub-procedure at a time.
- **Relation to blocks 1 to 3:** records decide, rules state what every session must do, and a skill is the projection of decisions into one kind of task: the how.
- **Evidence:**
  - PR #16 and core rule 3
  - this session's issue work all ran through the `pm` skill's commands (filing, moving, ticking criteria, landing), and today's scratchpad note through `pkit new scratchpad`
  - the `pm` skill's batch planning is what plans the shared choices as records before the slices (project-management DEC-060)
- **Weak spot:**
  - a skill helps only when it is invoked; rule 3 requires it for authoring, but nothing checks it was: the command stamps either way
  - every session carries every description, and they grow (`analysis-author`'s is 169 words)
  - the core skills are anchored to none of the records they follow (only the `analysis-author` skill carries some), so when a record changes nothing asks a core skill to recheck; `gates:` checks only that the record is accepted, not that the skill still says what it decides
  - composites grow large (`pm` about 15 000 words with its sub-procedures)
- **Maintainer's notes:**
  - Skills and scripts belong together: both are the projection of decisions into a kind of task (the how).
  - Lifecycle (who creates them, when, how, why): pkit answers when and why (COR-007: on recurrence) and which carrier (COR-006), barely how (no `pkit new skill`, no skill for authoring skills; no home for a project's own scripts), and not who notices, how they stay in step with their records, or how they retire.
  - The main case should be anticipation, not recurrence: pkit's value is its opinion on how to build a project with AI, its own tooling included, so when work starts that will not be a one-off, the agent proposes the skills, agents, scripts and records around it on pkit's foundations. Agreed direction, after a critic's review (28 October), three tiers:
    1. **Reuse** what pkit ships: always, through a lookup before anything is built.
    2. **Apply a pkit shape** (an authored kind → command plus skill; a perspective → agent; a shared choice → record; a repeated procedure → skill) to the project's new work, where the plan shows two or more cases or the work recurs by its nature, and the shape itself came from recurrence. The planner proposes it at the first stage of batch planning (DEC-060); the person accepts at the plan's gate.
    3. **Invent** a new carrier on recurrence (COR-007), with a noticing review someone owns.
  - Needs a record refining COR-007 first; prerequisites: authoring skills (`pkit new skill`), and retiring a carrier.
