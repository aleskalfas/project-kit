---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-29
---

# The Friday talk — project-kit's building blocks

The talk's notes, its slides as data and its Mural board map live beside this note: `2026-10-29-friday-talk.slides.yaml` (the slides' content, one entry per slide), `2026-10-29-friday-talk.board.yaml` (the board map the mural-boards skill pushes, with its sync state) and `2026-10-29-friday-talk-icons/` (the pictograms the diagrams use). The scratchpad commands move only this note; the three siblings move with it by hand when it is retired.

Started on 26 October in a branch folder (`talk-notes/`), moved here on 29 October.

## Hand-off: where the slides stand, and how to go on (29 October, evening)

The work moves to another clone from here. Everything it needs is on branch `docs/talk-notes`; this clone stops touching the board.

**Where things are.**

- Board: https://app.mural.co/t/ibmresearchdesign6459/m/ibmresearchdesign6459/1793230020758/311a5a3a4aeef1ac127c90b21b7e6ad6292360f8
- `2026-10-29-friday-talk.slides.yaml`: the slides' content, the source of truth for what each slide says (one entry per slide; `minutes` per slide add up to the talk's length).
- `2026-10-29-friday-talk.gen.py`: turns the slides file into instances of the board's templates in the board map. It also renders each terminal panel to a PNG (see "The deck's style").
- `2026-10-29-friday-talk.board.yaml` and `….board.yaml.state.json`: the board map and its sync state, which the mural-boards skill (`~/.claude/skills/mural-boards`, user-level, on this machine) pushes. Both are committed so another clone continues the sync.
- `2026-10-29-friday-talk-icons/`: Carbon pictograms recoloured to the board's roles, and the rendered terminal panels (`term-*.png`).
- `2026-10-29-friday-talk-tools/`: `stray_duplicates.py` (finds and deletes duplicates the board tool leaves), `make_row_icons.py` (recolours Carbon pictograms), `mural_fonts.py` (lists the fonts Mural accepts).

**The loop for one change.** With `A=.pkit/scratchpad/active` and `M=$A/2026-10-29-friday-talk.board.yaml`:

1. Edit the slides file (and the generator, for a new kind of visual).
2. Where a slide's parts change, take the old parts off the board first, by their exact instance ids: `uv run --script ~/.claude/skills/mural-boards/scripts/mural_boards.py remove $M <ids> --yes`. List the ids from the map; a prefix can match another slide's parts (`T-opening-c` matched the opening's cards `T-opening-c1`…).
3. Generate: `uv run --no-project --with pyyaml python $A/2026-10-29-friday-talk.gen.py $A/2026-10-29-friday-talk.slides.yaml $M`.
4. Dry run, then push and verify: `… mural_boards.py push $M --brief`, then `… push $M --yes --brief --verify`. Only library `FIT` lines are expected (six); a `FIT T-…` line is a slide's text too long for its box.
5. Clear duplicates: `uv run --no-project --with pyyaml --with jsonschema python $A/2026-10-29-friday-talk-tools/stray_duplicates.py ~/.claude/skills/mural-boards/scripts/mural_boards.py $M` (add `--yes` to delete). After a push the board service sometimes fails a request after making the object, the tool retries, and a second copy stays, invisible but in the way of `remove`. The script deletes only an undescribed object with a described twin of the same type, title, position and parent, and holds one that contains anything else (agreed with the maintainer on 29 October).
6. Commit (signed) and push the branch.

**What the board tool taught.**

- Areas cannot move: a slide that shifts in its row is rebuilt (taken down and made again), which the tool does on its own when everything inside is described.
- A colour in a template is written in eight hex digits (`#262626FF`); six digits are refused by the API. Colours inside a text box's html spans take six.
- Mural accepts 12 fonts, none monospace (`mural_fonts.py` lists them), so a terminal is rendered by the generator to a PNG in IBM Plex Mono (installed on this machine; the renderer is `rsvg-convert`) and placed as an image.
- `pull` before editing when the maintainer may have edited on the board; a text moved by hand shows as a `CONFLICT` on push.
- Never read `~/.config/mural-boards/.env` or `token.json`.

**The deck's style (decided 29 October).**

- Length: 30 minutes, 15 slides (the slides file's `minutes`). Part 1's order stays Decisions → Checked → Rules and processes as data → What every session is told. Scratchpad notes are a spoken line on the decisions slide. Schemas and processes are one slide; staying current and what comes next are one slide ("Over time").
- The opening ("Why pkit?") pairs each common practice with pkit's opinion: four rows, a grey problem box (pictogram, what usually happens) and a light purple answer box (pictogram, what pkit asks you to do, the part of the talk), joined by bold purple arrows. The maintainer's point: projects do not usually keep decisions, conventions, tied docs or written permissions; pkit's value is its opinion that they should.
- One style for anything shown as a command line: a light terminal panel (`#F4F4F4`, border `#E0E0E0`), IBM Plex Mono; prompt and `#` comments grey, the command green (`#198038`), its arguments near black. In a listing, what is pkit's is purple (`#6929C4`) and what is yours blue (`#0043CE`), with a legend line.
- Something to take away (such as `pkit visibility private` on the install slide) is a yellow note: light yellow box, yellow bar on its left, a dark-yellow pictogram, a question as heading, a small terminal and one line.
- Slides done in this style: "Why pkit?", "Install pkit" (the commands; the full tree of what `pkit init` creates, taken from a real install, `.claude/` shown as yours with pkit's added; the visibility note), "Decision records" and "Decided once, found later". The maintainer split the decisions slide in two on 29 October, since the audience will ask how COR, PRJ and ADR differ: the first shows the four kinds as rows in their owner's colour (what each decides, its count, a real file) beside one real record, PRJ-002; the second carries the takeaway "decided once, found later" in three steps (the agent drafts it, you accept it, a later session finds it) over a real `pkit refs records-for` of `workflow.yaml`, which leads to DEC-006. Counts are main's on 29 October: COR 39 at the end of June, 67 now; PRJ 11 and ADR 74 in project-kit; DEC 83.

**In review: "How pkit fits together", slide 2, before "Install pkit" (swapped by the maintainer, 29 October; the part is now "pkit at a glance").** The maintainer asked for it on 29 October: the audience should see how pkit's parts rest on each other, with the decisions at the top, before the slides take the folders one by one. Its ground is COR-065 (accepted): where an accepted record decides, the rest of the system is its projection; a disagreement is read first as the projection falling short; a record changes only when a person accepts a new one; scratchpad notes come before a record. It is in the slides file (`fits`, the generator's `pyramid` kind) and on the board, and its wording awaits the maintainer's review. It follows the design below, with these changes: "Working rules" for "Rules" (the slides file's vocabulary); "checked first" for "fixed first" (COR-065 point 4); "carries out" for "is the projection of"; plain heads beside real arrows; the bottom line names this week's COR-065; no limit line, which would pass the footer, so the weak spot (hand-made layers can lag) is in the notes. The lead answers the title instead (the maintainer, 29 October: read aloud after "How pkit fits together?", the proposed lead was no answer): "In five layers, from your decisions down to your code: each carries out the ones above it." The proposed lead may go to the decisions slide, not yet decided. The scratchpad box became "Where ideas start: in conversation, and in a scratchpad note when one needs longer" (the maintainer: ideas are shaped in conversation too). It sits left of the apex, tinted purple, its arrow pointing right into Decisions, so the slide reads from left to right (the maintainer); the pyramid moved right and narrowed a little to make room (`center`, `top_w`, `step`), and "Carried out" and "Checked" each take half the right column. The design proposed:

- Left, a stepped pyramid, darkest at the top (Carbon purples, white text on the two darkest): **Decisions** (the why, accepted by you) → **Rules · schemas · processes** (the exact what, read by every session and tool) → **Skills · agents · permissions** (how agents act, in which role, with what rights) → **pkit's commands and checks** (they carry it out, and check it on every change) → **Your code and documents** (the work itself, tied to what it depends on).
- Right, three relation boxes: **Scratchpad notes**, with an arrow into the apex (they explore a question before it is decided); **↓ carried out** (each layer is the projection of the decisions above it); **↑ checked** (where a layer and a decision disagree, the layer is fixed first, and a decision changes only when you accept a new one).
- Lead: "Decisions are the source: everything else in pkit carries them out, and is checked against them." Bottom line: COR-065.
- Time: 1.5 minutes, taken from Install (2 → 1.5), project-management (3.5 → 3) and Checked (1.5 → 1).

**Next, slide by slide.** After the pyramid: "Checked every time", "Rules and processes as data" and "Over time" (the two merged slides, which the maintainer has not reviewed), then the rest in order. Each slide that shows commands or files (checked: `pkit validate`; rules and processes: `workflow.yaml`; sessions: `CLAUDE.md`; docs: `pkit friction check`) still uses the old grey code box, and moves to the terminal style. Refreshing the "this week" evidence lines with 29 October's events was proposed and set aside by the maintainer ("not important now"). This note's "Time (45 minutes …)" table below is superseded by the slides file's minutes.

Working notes for the Friday talk (goal reconsidered 26 October: present project-kit, its building blocks and its motives; show how light it is and what it gives without capabilities). One block at a time, with the maintainer. For each: what it is, the problem it answers, the adopter's gain, its weight, evidence, and the honest weak spot.

## The list

**A. What the agent remembers**
1. Decision records: `.pkit/decisions/`
1b. Validation: one check that every file's form and every pointer between files hold (moved here from 11 on 28 October)
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
11. (moved to 1b)

**E. How it reaches a project and stays current**
12. (folded into 4 and 13 on 28 October: the CLI is the deterministic half paired with skills; its lifecycle commands go with 13)
13. Lifecycle: install, sync, upgrade, and migrations
14. Ownership: core files and project files, never shared (`.pkit/project/`)
15. Versioning and release

**F. How it is extended**
16. Schemas: rules as data
17. Process substrate: staged processes with gates
18. Connections: how components hand each other data
19. Capabilities: opt-in disciplines (project-management, software-engineering, software-analysis, living-docs; and evidence, doc-examples, demo-recording)

## The talk's order (agreed 28 October, completed 29 October)

The flow follows an adopter: install it, learn it, keep it current, see what comes next.

1. **Install pkit** — `pkit init`, what lands in your project, and the one-owner rule: the methodology's files and your files are never shared. One line on adapters (install wires pkit into your AI tool, today Claude Code); `status`, `visibility`, `config`.
2. **Decision records**
3. **Checked every time** — validation: files point at each other, pointers break quietly, one command walks them all
4. **Schemas: what the tools read** — the exact rules in YAML: decisions say why, schemas say what, validation checks both hold (and `data`)
5. **Processes as data** — the process substrate: staged work with a check of every move and a memory of every subject, shown through project-management's issue lifecycle
6. **What every session is told** — the operational rules loaded into every session
7. **Scratchpad notes**
8. **Skills and the commands they pair with** — the judgement and the mechanics together (and the hook registry)
9. **Agents: roles with limits** (and storyboards: how an agent's behaviour is designed)
10. **Permissions you write down** — first line: "not the tool's guesses"; and where agents write
11. **Docs that know when they're wrong** — anchors and answers
12. **Writing rules** (rule sets) — skipped for now while the rules are reworked
13. **Capabilities:**
    - **project-management: "One project manager, many builders"** (landing a change lives here)
    - **software-engineering, with connections:** the builders follow your conventions, three reviewers check the result, and the reviewers plug into project-management's merge gate through a connection point, with nothing to wire
14. **Stay current** — sync, upgrade, migrations, versioning and release, `pin`; and the report channel: updates come down, reports go up
15. **What's next (experimental)** — software-analysis, living-docs, and real multi-clone parallel work (seats and pools): all three run today, all three still being shaped


### Time (45 minutes, agreed 29 October; superseded by 30 minutes, see the hand-off above)

| # | Block | Minutes |
|---|---|---|
| | Opening: the problem pkit solves | 2 |
| 1 | Install pkit | 3 |
| 2 | Decision records | 3½ |
| 3 | Checked every time | 2 |
| 4 | Schemas: what the tools read | 1½ |
| 5 | Processes as data | 1½ |
| 6 | What every session is told | 2 |
| 7 | Scratchpad notes | 1 |
| 8 | Skills and the commands they pair with | 2½ |
| 9 | Agents: roles with limits | 3 |
| 10 | Permissions you write down | 2½ |
| 11 | Docs that know when they're wrong | 3½ |
| 13 | Capabilities: project-management 5, software-engineering with connections 3 | 8 |
| 14 | Stay current | 2 |
| 15 | What's next | 2 |
| | Questions | 5 |
| | Total | 45 |

No title uses the word "rules" (decided 29 October): each block is named for what the audience sees.


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

## 1b. Validation: checked every time (draft, 28 October; placed after decisions)

*Facts checked against the repository on 28 October.*

- **What:** `pkit validate` runs every registered check of the project's state in one command, grouped: manifests, schemas, configuration, packages, connections, versions, decisions, friction, rule sets, references, processes, data, and each installed capability's own checks (16 validators here today). Only errors fail; warnings and reports print. Checks that judge a change rather than the state (`friction check`, `migrations check-diff`, `release lint`) run per change, in CI and before landing.
- **Problem:** a methodology made of files breaks quietly: a citation to a record that no longer exists, a schema a file no longer matches, a number used twice, a capability that needs a newer backbone. Nobody notices until something reads it wrong.
- **Gain:**
  - one command says whether the project's own structure holds, before a person or an agent relies on it
  - a capability brings its checks with it, so installing one adds its rules to the same command
  - CI runs it on every change, so a break is caught where it is made
- **Weight:** one command; seconds to run; nothing in a session's context.
- **Evidence (this session):** every builder ran it before opening a pull request; `pkit decisions check-diff` caught the DEC-062 number taken twice; it reported 61 warnings today (for example, citations to a point a record does not hold), none failing.
- **Weak spot:**
  - warnings pile up (61 today) and are easy to ignore
  - it checks structure, not meaning: a record can be valid and wrong
- **Maintainer's notes:**
  - Decided 28 October: a block of its own, told through the mechanism and the why. Headline: **"Checked every time."** The mechanism in three layers: each kind of file has a declared shape (schemas); each connection is written so a machine can follow it (typed citations, anchors); each part registers its own checks (core and every capability), and `pkit validate` runs them all. The why: agents act on what they read, so a deterministic check catches what a person would notice and an agent would not; it is the mechanical half of carrying out decisions ("rules, not guesses" applied to the project's own structure); and it lets the system grow without anyone knowing all of it. The honest example: 61 warnings had piled up (42 of them broken citations), because each check was introduced as a warning and never finished; #2300 clears them, and #2301 makes each cleared kind fail from then on (a project chooses, so adopters are not broken).

  - Placed after block 1 on 28 October: the clearest examples are about records (two records numbered DEC-062 in different pull requests; reviewer instructions citing a point "D4" that DEC-002 does not have), and once the audience has seen numbered records the next question is what keeps their numbers and citations from breaking. It stays a block of its own because it checks every kind of file; each later block can say "and validation checks this too". The plain telling: the files point at each other; pointers break quietly; a person notices a dead link, an agent follows it; one command walks all files and pointers.

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
  - Discoverability: installed skills are discoverable already (the harness shows each one's name and description to every session). What the agent cannot see is pkit's offering beyond what is installed. Agreed design (28 October), the same pattern skills use: each capability's short description, written as when to reach for it ("use when …"), sits in every session, uninstalled capabilities included, generated at sync from `package.yaml`; one sentence tells the agent that where a capability may already solve the problem, it reads the full description (the capability's README, which `pkit capabilities show` would need to print for one not installed) before building its own. Covers every place work is shaped: conversation, scratchpad notes, batch planning.
  - Kept in these notes, not filed yet: it and the COR-007 refinement are one change, "pkit leads with its own patterns", filed after the walk through blocks 5 to 19.

  - Decided 28 October: the CLI is folded in here — block 4 becomes "skills and the commands they pair with": the skill carries the judgement, the command the part that must come out the same every time (stamping, checks, gated moves). Its lifecycle commands (init, sync, upgrade) go with block 13.
## 5. Agents (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** an agent is a standing role: a point of view with limits — what it reads, what it may write, which tools it has, what it never does (COR-006: a skill is a procedure, an agent a role; COR-013 its shape). project-kit deploys 14: six from core (`critic`, `architect`, `methodology-reviewer`, `convention-compliance-reviewer`, `rule-set-reviewer`, `process-author`) and eight from capabilities (`project-manager`, `pm-reviewer`, `software-engineer`, `code-reviewer`, `docs-reviewer`, `security-reviewer`, `living-docs`, `analysis-resolver`). Two kinds: those that produce (the engineer, the project manager, the process author; living-docs and analysis-resolver propose, never apply) and those that review. A project fits them to itself without editing them: the overlay names its paths (where its ADRs live, its conventions), and the deploy writes a copy with those filled in.
- **Problem:** one agent doing everything judges its own work, and an agent asked to check its own work agrees with itself. A single generalist also carries every concern at once, so each is held loosely.
- **Gain:**
  - a second opinion before the person sees a proposal (the critic), and a check of the big picture (the architect)
  - each reviewer catches one kind of failure (conventions, the methodology's disciplines, the rules a document is held to, code, security, docs), and the merge gate requires their verdicts (project-management DEC-028)
  - reviewers are read-only, so they report and never quietly fix
  - one role definition serves every project, fitted by the overlay
- **Weight:** only each agent's description sits in a session's context; its body (about 900 to 5 200 words) loads when it is started. The cost is in running them: a pull request's review starts five reviewers at once, each reading the change.
- **Relation to blocks 1 to 4:** records decide, rules say what every session does, skills say how a kind of task is done; an agent says who looks at the work, from where, and with what limits. A skill can be run by any agent.
- **Evidence (this week):**
  - the pools change (#2257): the docs reviewer found a deferral naming the very issue the change closed, and the rule-set reviewer a glossary term used for a second thing; both fixed before landing
  - the critic changed two designs in two days: the pools design, and today's idea of anticipating carriers (the three tiers)
  - the two workers and this planner are the `project-manager` agent in different seats
- **Weak spot:**
  - cost and time: every review round runs every reviewer, and a fix round runs them again
  - agents lean toward the framing they are given: a brief that carries the answer gets it back
  - findings set aside pile up (#908 collects the code-review panel's set-aside defects)
  - remits overlap at the edges (the docs reviewer, the rule-set reviewer and the methodology reviewer all read documents), so the boundaries need care
  - the harness can quietly cut a named helper's answer at 4 064 characters (agent teams); the guard is a discipline in the dispatching agent, not a check
  - a reviewer runs in an environment, and a wrong one gives false findings (the reviewers started outside the project root, #2255)
- **Maintainer's notes:**
  - Agents are not just generator versus reviewer: five reasons for many roles — separation, focus (each carries only its knowledge), least privilege (tools and writes per role), a place in the flow, growth with what is installed. Present agents as roles with limits.
  - The ideal (maintainer): each agent works only with the information and tools its role needs. Tools, writes and reads are limited per role today; skills reach an agent only by hand; every session loads every rule. Claude Code allows a helper's `skills:` (preloaded) and `omitClaudeMd`; main sessions always load `CLAUDE.md`.
  - Rules, decided 28 October after two critic rounds and the architect: rules about files stay in rule sets (grouping and specialisation there: a Python set inheriting software-engineering's, scoped to `**/*.py`, binds whoever writes Python). Rules about behaviour take a record's point form (COR-058): permanent numbers, one-line stubs, each citing its record or issue, one record deciding it (#2260). Capabilities ship their own rules file in that form, loaded by installation (Claude Code: deployed into `.claude/rules/`), with a check that each is loaded; a new Task builds it. Targeting rules by agent is set aside: an agent is not a role (planner, workers and the person's conversation all run as one agent).

## 6. Adapters (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** the translation of pkit's content, written once and harness-neutral (COR-006), into what one AI harness reads. One adapter ships today, Claude Code's (`.pkit/adapters/claude-code/`). The lifecycle (init, sync, upgrade, a capability's install and removal) runs its scripts by name: merge the settings (COR-002's merge primitive, so a project's own settings survive), merge `CLAUDE.md`'s includes, deploy the skills (links) and the agents (copies with the project's paths filled in), and undeploy a capability. Beside those, the adapter carries the harness's hooks: the permission hook on every tool call, deciding through a harness-neutral core (COR-028), and the start hook on every session and helper; and the runner that starts an agent unattended in a confined run (ADR-066).
- **Problem:** without it, the content is either written for one tool and stuck there, or wired into each project by hand, file by file, and drifts.
- **Gain:**
  - records, rules, skills and agents are written once, in plain Markdown and YAML, for any harness; a new harness is a new adapter, not a rewrite
  - a project's own settings are merged, never overwritten
  - the harness's own mechanisms (hooks, settings, sandbox) enforce the permission model
  - what the methodology needs from a harness is declared as data (COR-047), and each adapter answers it: two requirements today (a delegated result arrives complete; an agent runs unattended and confined), both "at a cost" on Claude Code; an unanswered requirement reads as undetermined, never as met
- **Weight:** none in a session's context; the scripts run at init and sync (about 20 000 words of them). The permission hook runs on every tool call.
- **Relation to blocks 1 to 5:** they are the content; the adapter is how it reaches the harness, and the only place that knows Claude Code's file names.
- **Evidence (this week):**
  - the Claude Code facts checked today (an agent's `skills:` preloads, `omitClaudeMd`, `.claude/rules/` loading at start) are exactly what the adapter will use to deliver each role's slice and each capability's rules (#2269)
  - the hazard of a named helper whose answer is cut at 4 064 characters is a harness property, declared as the requirement `delegated-result-complete`
- **Weak spot:**
  - harness-neutral is a claim with one test case: with a single adapter, nothing proves the content really is neutral
  - the harness moves under us: each Claude Code change (agent teams, new frontmatter fields) lands in the adapter first, and some only as a discipline (the 4 064-character cut)
  - it grows with every capability that needs delivery (rules by installation, #2269)
- **Maintainer's notes:**
  - Decided 28 October: not a block of its own until a second adapter exists. The talk folds it into the lifecycle (block 13) as one line: "install wires pkit into your AI tool: today that's Claude Code". A spike on a second harness is parked (#2298).

## 7. Permission model and sandbox (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** permissions as one model in the project's own terms, owned by the methodology, which the adapter enforces through the harness (COR-028): the model is the source, the harness's settings a generated projection of it. A catalog of 15 privileges, in three kinds: **guardrails**, always denied to every agent and impossible to grant around (recursive deletion, `sudo`, force-push); **enablers**, usable only where granted (docker, the issue tracker, the CLI, reading the repository, read-only text filters); and **surgical denies** for one agent (the project manager may not mutate issues with raw `gh`, so it goes through the validating commands). Named profiles (read-only, non-destructive, autonomous) set a posture. A hook checks every tool call against the model. An OS sandbox, where the platform allows it, lets scripting run without prompts inside the box. Commands to see and test it: `explain` (who may do what), `probe` (proves what the model allows and refuses), `diagnose` (finds where the prompts come from), `setup autonomy`.
- **Problem:** in a raw harness, what an agent may do is scattered across tool-specific files in tool-specific words; when something is wrongly allowed or blocked nobody can tell why; and the operator drowns in confirmations (a single session produced dozens), approving them unread, which is worse than no gate.
- **Gain:**
  - one place, in your words, says what each agent may do, and `explain` shows it
  - a floor of destructive acts no agent can do, whatever is granted
  - fewer prompts where it is safe (the workspace, read-only filters, the validated commands), so the prompts that remain get read
  - agents steered onto the validating paths: raw mutations denied, the command that checks is the easy way
- **Weight:** nothing in a session's context beyond two rules (14 and 15) and the workspace rule (16); the hook runs on every tool call.
- **Evidence (this session):** a builder's `rm -rf` of its scratch files was refused by the guardrail, and it asked the planner to delete them instead; the planner refused (permission laundering) and told the person. The reviewers' false blocks when started outside the project root (#2255) came from settings not loading.
- **Weak spot:**
  - a deny list is a speed bump, not a security boundary: a `bash -c` wrapper or a raw `gh api` call walks around a deny (the catalog says so itself); only the OS sandbox confines
  - the sandbox is off on macOS today (ADR-014), so scripting still prompts there
  - posture is lenient: anything the model does not know goes to the harness's own prompt
  - it is the largest area to learn (its README is about 7 500 words)
- **Maintainer's notes:**
  - Decided 28 October: flow is mostly the harness's job now (Claude Code's auto mode decides which actions are safe enough to run unasked), so the block does not lead with fewer prompts. Its argument is what auto mode does not give: fixed rules instead of a judgement per action; steering agents onto the validating commands (process, not only safety); different rules per role; and the rules written down in one place, in the project's words. Headline: **"Your rules, not the tool's guesses."** The honest limit stays said: the lists stop ordinary commands, not a determined workaround; only the sandbox is a wall, off on macOS today.

## 8. The agent workspace and the cross-repository guard (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** two small rules about *where* an agent writes.
  - **The agent workspace:** every checkout has one folder, `.agent-workspace/`, where agents keep their scratch files (a pull-request body, a script, captured output). It is never committed, each worktree has its own, and every agent may write there without a prompt, through its file tools only (core rule 16).
  - **The cross-repository guard:** a session changes only the repository it was started in (COR-039, core rule 19). A change aimed at another repository is stopped and put to the person, once per change; reading another repository is fine. pkit's own commands check it (`--allow-foreign-repo` is the person's confirmation); for a raw command it is a discipline.
- **Problem:** agents scatter scratch files in `/tmp`, the home folder or the project, so the operator is asked about each one (dozens of harmless prompts, approved unread), and files leak into commits. And a session that wanders into a sibling repository changes it under the wrong project's rules, with nobody noticing.
- **Gain:**
  - one place for scratch, no prompts for it, nothing in a commit
  - a repository is changed only by a session that carries its own rules
- **Weight:** two rules in every session; no command to learn.
- **Evidence (this session):** every brief, body and script of today's work lived in the workspace; reading mockingbird (another repository) for the comparison was fine, changing it would have been stopped; a builder's scratch projects stayed inside its worktree's workspace.
- **Weak spot:**
  - the guard is an interlock against accidents, not a security boundary: a raw command can still reach another repository
  - a shell redirect into the workspace still prompts; only the file tools are free there
- **Maintainer's notes:**
  - Decided 28 October: folded into block 7 as "and where agents write"; the workspace is the concrete example of a rule that removes prompts safely.

## 9. Anchors and answers (friction): documents know what they rest on (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** any document, use case, glossary entry or skill may declare its **anchors**: the code, records or other documents that make it true (COR-050). When an anchor changes, the document has **friction**, and the change that caused it must answer for it, in the document's own answer, never in a pull-request description: **updated** (it was rewritten), **still accurate** (with the reason), or **out of date, fixed later** (a deferral naming its follow-up). The change check (`pkit friction check`) lists what a change owes; answers are written by commands (`revalidate`, `defer`), kept in answer files of their own (COR-062); a reviewer checks them (the docs reviewer); the pull request lists them for the person, as information. `pkit friction debt` shows what is out of date or deferred across the project (50 entries today). A delegate agent may answer what no change owes (COR-064), and fixers propose the fixes after a merge (`fix-drift`).
- **Problem:** documentation rots silently. Code and decisions change, and nothing tells you which pages, requirements or use cases now say something false; you find out when someone acts on them.
- **Gain:**
  - a change cannot land while a document it makes untrue goes unanswered: rewrite it, say why it still holds, or name when it will be fixed
  - "out of date" is visible and counted, not discovered
  - the reasoning is kept: each "still accurate" says why, and a reviewer can check it
- **Weight:** a few lines of front matter per document; one check per change; the answers are files, not prose to read.
- **Evidence (this session):** every pull request today had the check ask for answers (the pools build answered 20 analysis documents); the docs reviewer caught a deferral that named the very issue the change closed, and a "still accurate" that was false (REQ-042 after the move back); the merge-time fixers ran and found nothing out of date.
- **Weak spot:**
  - it only covers what is anchored; an unanchored document rots as before
  - it adds work to every change, and answers can be written lazily ("still accurate") — the reviewer is the only check on their honesty
  - the machinery is heavy to learn (COR-050 alone has 16 points)
- **Maintainer's notes:**
  - Headline (decided 28 October): **"Docs that know when they're wrong."**

## 10. Rule sets: rules a reviewer judges (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** a project writes down how its files must be written, as numbered rules in a rule set, each with an id that never changes, a status (a person accepts each rule), and its origin (COR-051). A set applies to the files its scope selects (by path and type), and a set may inherit another, pinned to a version: project-kit's `ANA` (7 rules, for its analysis) inherits `WRITE` (17, its general writing rules) and software-analysis's `SAN` (16); living-docs ships `LDOC` (8). Today they bind 323 files. A reviewer, `rule-set-reviewer`, judges each change against the rules that bind on the files it touches (COR-057), citing the rule, the line and the passage; where a check can enforce part of a rule (the prose lint, the analysis validator), the reviewer leaves that part to it. `pkit rule-sets reach` says which rules bind on a file.
- **Problem:** writing guidelines live in a wiki nobody reads, or in a reviewer's head; each review re-argues taste; an AI writer follows whatever it was last told.
- **Gain:**
  - the rules are files, versioned and accepted like decisions; a rule that changes is a visible change
  - grouping and specialisation: a general set, a capability's set, a language's set inheriting them (decided today for Python under software-engineering)
  - every change is judged against the rules that bind on what it touches, by a reviewer that cites the rule; what a rule leaves to judgement goes to a person, marked as such
- **Weight:** nothing in a session's context; the reviewer runs per change; the writer reads the rules for the files it writes (a bridge rule for that is filed, #2274).
- **Evidence (this session):** the rule-set reviewer caught a glossary term used for a second thing (pools), a fact stated twice in disagreement (living-docs setup), and kept marking judgement calls for a person instead of blocking on them.
- **Weak spot:**
  - today it covers documentation, not code: software-engineering ships no rule set yet
  - many findings are judgement calls a person must settle, which adds to the review queue
  - inheritance with version pins is a lot of machinery for a handful of sets
- **Maintainer's notes:**
  - Decided 28 October: skipped for now; the rules are being reworked (operational rules becoming rule sets, #2270). Revisit for the talk once that lands, probably together with block 2.

## 16. Schemas: rules as data (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** a rule precise enough for a program to apply is written as data, a YAML file with a JSON Schema companion that says what the file must look like (COR-018). Code, skills and agents read the YAML at run time instead of carrying the rule in their own text. project-management alone has 20 (`workflow.yaml`: the five states, every allowed move and who authorises it; `titles.yaml`: the title formats; `git-conventions.yaml`: branch names and pull-request bodies; `topology.yaml`: seats and pools; …); 29 across capabilities, 8 in core. A schema names another's entry with a typed token, such as `[validation-severity:hard-reject]` (COR-019), so the references between them can be checked. A project's own data files (its `config.yaml`, its topology) say which schema they follow (`pkit_schema:`, COR-023), so `pkit validate` checks them against it.
- **The division of labour:** a decision says *why* (the principle, the alternatives); a schema says *what*, exactly (the states, the regex, the transition graph); the code only applies it. Change the rule, and you change one YAML line, not three scripts and a prompt.
- **Problem:** a rule written only in prose is applied differently by each script and each agent that reads it; a rule written only in code is invisible and duplicated.
- **Gain:**
  - one place for each concrete rule, read the same way by every script and agent
  - a project can see the rules its tools apply, and the checks hold them to their shape
  - the rule and the code that applies it can change apart: a new state or title format is a data change
- **Weight:** nothing in a session's context; an agent reads a schema when its task needs it (the project manager reads the eight it uses).
- **Evidence (this session):** the move back is two transitions in `workflow.yaml`, whose settings (who may make the move, how strictly it is refused) the commands read, beside its own checking code in `move-issue`; the critic of the Icebox found that a sixth state would touch every place that hard-codes five, which is exactly where a rule was not yet data.
- **Weak spot:**
  - not everything is data yet: some code still hard-codes what a schema declares (the order of states)
  - a YAML rule with no prose beside it can be applied without anyone knowing why; the decision must stay linked
- **Maintainer's notes:**

## 17. The process substrate: staged processes with gates (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** a reusable state machine with no content of its own (COR-033). A capability describes its own staged process as data, a *process definition*: the states, the moves between them, the gate each move must pass, how a parent follows its children. The substrate's engine then gives every such process two things: a **deterministic check of each move** (may this subject move here now?) and a **memory of where each subject stands** (a journal per subject, with why each move happened). project-management's issue lifecycle (Todo → Backlog → In Progress → Review → Done) is bound onto it: each issue has a journal (`project/process/issue-lifecycle/<n>.journal.jsonl`), and the cascade of a parent following its children is the substrate's composition. A second, separate binding grounded the design. A `process` skill helps author a definition's shape, and the `process-author` agent writes the predicates behind each gate (COR-044).
- **Problem:** every discipline with stages (an issue's life, a release, a build, a review) invents its own state handling, its own "may I move?" checks and its own history, each slightly different, none explainable the same way.
- **Gain:**
  - one engine for every staged process: an agent asks the same three questions anywhere (where am I, may I move, am I valid) and gets a deterministic answer
  - a history per subject, readable by a person with no manual
  - a new process is a definition, not new machinery
- **Weight:** nothing in a session; adopters meet it only through a capability's process (the issue lifecycle).
- **Evidence (this session):** the move back and the completed close were added as moves in the lifecycle's definition; every move today was journalled, and the critic of the Icebox found exactly where the engine's fixed order of states would resist a new state.
- **Weak spot:**
  - abstract: hard to show without a capability on top of it
  - two bindings so far; whether it fits a third discipline is untested
- **Maintainer's notes:**
  - Decided 28 October: a block of its own (the maintainer: not folded into capabilities), placed after schemas, shown through the capabilities that use it: project-management's issue lifecycle (states, moves, who authorises each, each issue's journal, today's move back and completed close added as definition changes) and the second binding, which shows the engine is shared.

## 18. Connections: how capabilities hand each other data (draft, 28 October)

*Facts checked against the repository on 28 October.*

- **What:** when one capability needs something from another, it never names the other. It declares a *connection point* under a **role**, and whichever installed capability provides that role answers it (COR-053). A role is written `pkit::documentation`, `pkit::work-tracking`, `pkit::analysis`; a point is a role plus a name, such as `pkit::work-tracking:fixers` (which agent fixes each kind of document) or `pkit::documentation:readers` (who reads each page). Every connection is optional unless it says, with a reason, that it is mandatory. Three kinds share one mechanism: data slots, process connections, and events. One wiring graph shows it all (`pkit status`, "Connections"; `pkit connections`), and validation checks it.
- **Here today:** three roles, each provided by one capability (analysis → software-analysis, documentation → living-docs, work-tracking → project-management); six points, four filled. For example, software-analysis and living-docs each tell project-management which agent fixes their documents, and that is how `fix-drift` knows whom to start after a merge, without project-management knowing either capability exists.
- **Problem:** capabilities that call each other by name are welded together: replace one and everything that names it breaks; install one without the other and its references dangle.
- **Gain:**
  - swap one capability for another that provides the same role, and nothing connected to it notices
  - install only what you need: a missing provider leaves an optional point unfilled, not broken
  - one picture of how the installed parts are wired, checked every time
- **Weight:** nothing in a session; a capability declares its points in its package.
- **Weak spot:**
  - abstract, and only visible through what it enables (fixers after a merge, readers of a page)
  - each role has exactly one provider so far, so swapping is designed, not yet shown
- **Maintainer's notes:**
  - Decided 28 October: placed right after the capabilities block, not before it: connections between capabilities only make sense once capabilities are introduced. The example: fixers started after a merge, through `pkit::work-tracking:fixers`.

## Areas found uncovered on 29 October, and where each goes

- **The report channel** (`pkit report`, `report-author`): an adopter sends a bug, change request or feedback upstream; it is linked to the issue that fixes it. In the closing block, "Stay current": updates come down, reports go up.
- **Storyboards** (COR-016, `storyboard-author`): an agent's behaviour written as scripted scenarios before the agent itself (the project manager's batch planning is one). In the agents block, as how an agent's behaviour is designed.
- **Landing a change as a whole** (a record accepted before it lands, COR-066, and the landing guard; the merge gate's reviewer verdicts; `pkit pull-request`, `land-work`): inside project-management in the capabilities block.
- Folded in: `status`, `visibility`, `config` → Install; `pin`, `version` → Stay current; `data` → schemas; the hook registry (COR-013) → skills and agents; documentation roots (COR-049) → living-docs.

## 19. Capabilities

### 19a. project-management (draft, 29 October)

*Facts checked against the repository on 29 October.*

- **What:** the way work is tracked and run, on GitHub issues and pull requests. It ships 62 records, 20 schemas, 88 commands (`pkit pm …`), the `pm` skill (filing, checking a body, moving an issue, batch planning, the work loop, the fixers) and two agents: the **project manager** (files, plans, moves, lands) and the **pm reviewer** (checks a pull request against the conventions).
- **What it gives an adopter, in the order the audience meets it:**
  - **a structure for the work:** EPIC → Feature or Umbrella → Task, native sub-issues, milestones; each issue's body checked for its parts (what, criteria, doc impact)
  - **a lifecycle with gates:** Todo → Backlog → In Progress → Review → Done, every move checked, the person holding the scheduling, the end and the move back, parents following their children; it runs on the process substrate, with a journal per issue
  - **landing a change:** a pull request named and described by convention; the reviewers' verdicts required by the merge gate (pm, code, security, docs, rule-set, as installed); a record accepted before it lands; `land-work` does review, checks and merge in one command
  - **planning:** a fuzzy intent becomes one plan of Features and Tasks, reviewed by the critic, approved once (batch planning)
  - **parallel agents:** seats for a planner and workers in their own clones, pools that say which milestones each worker takes from, claims so two never take the same Task
  - **after a merge:** fixers propose fixes for what the merge left out of date
  - **a board:** a Projects v2 board kept as a view of each issue's state, and, by a project's choice, the home of state, priority and workstream
- **Evidence (this week):** every issue and pull request of this session; two workers and a planner ran through seats and pool `alpha`; the move back, the completed close and the board's Status were added to it today, each through its own records and reviews.
- **Weak spot:**
  - it is large: 62 records, 88 commands, a README of some 50 000 words; an adopter meets it through the agent, not the manual
  - GitHub only, today
  - it checks an issue's shape, not its sense: a bare dependency, a Task hung on the wrong parent, pass validation (found on 28 October; the cleanup and a typed `Blocked by:` follow)
  - project-kit itself was not using it well until this week's cleanup
- **Maintainer's notes:**
  - Decided 29 October: the headline is **"One project manager, many builders"**: you talk to one agent; it files and plans; it dispatches software-engineering builders in parallel, each in its own worktree; it runs the reviewers, brings the decisions to you, and lands what you approve (evidence: six builders in one evening, four pull requests merged). Seats and pools are one honest line: multi-clone parallel work exists and runs, but is experimental, the promise for what comes next.

### 19b. software-engineering (draft, 29 October)

*Facts checked against the repository on 29 October.*

- **What:** code that agents write follows the project's own conventions, and code is reviewed before it merges (DEC-003). Small: 4 records, a README of some 3 000 words, and four agents:
  - the **software-engineer**, the builder: it carries no coding opinions of its own and reads the project's conventions corpus first (the overlay names where it lives), then conforms to it (DEC-001); building a walking skeleton, it writes the conventions the skeleton settles into that corpus, for a person to accept (DEC-004)
  - the **code-review panel** (DEC-002): a **code reviewer** (correctness, quality, interface design), a **security reviewer** (auth, secrets on the command line, shell injection, crypto, dependencies) and a **docs reviewer** (missing docs for new surface, docs that contradict the code, and the answers a change owes its documents). Each blocks only on an objective failure in its own remit, and posts the rest as comments.
  - the panel plugs into project-management's merge gate through a connection point: every pull request that touches code requires the code, security and docs reviewers; every classified one requires the docs reviewer
- **Problem:** an AI writes code in its own default style, not the project's; and code it writes is merged on a glance, or reviewed by the same agent that wrote it.
- **Gain:**
  - the builder follows your conventions, written down once, not its habits
  - three independent reviewers on every code change, each blocking only on what it can prove, so a block means something
  - nothing to wire: installing it adds its reviewers to the merge gate
- **Evidence (this session):** every builder tonight was the software-engineer; the code reviewer blocked a board writer that could not find an org-owned board (fixed before merge); the docs reviewer blocked answers that were no longer true (UC-063, REQ-042); the security reviewer passed every change.
- **Weak spot:**
  - the conventions corpus is only as good as what the project wrote; an empty corpus leaves the builder with generic habits
  - no rule set for code yet (the Python set decided on 28 October is still to be written)
  - every review round costs three to five agent runs
- **Maintainer's notes:**

## Block 1 of the talk: Install pkit (draft, 29 October)

*Facts checked against the repository on 29 October.*

- **What happens:** `pkit init` in a project's repository, in order:
  1. the methodology's files are written into `.pkit/`: decision records, rules, skills, agents, schemas, the CLI's area specs
  2. the project's own starting files are seeded once (its `project/` folders, its configuration)
  3. the AI tool's settings are merged with what the project already has, never overwritten (`.claude/settings.json`; `CLAUDE.md` gains the includes of the rules)
  4. the agent workspace is created and kept out of git
  5. the adapter deploys the skills and agents where Claude Code reads them
  Then `pkit capabilities install <name>` adds a discipline (project-management, software-engineering, …), each adding its own records, skills, agents and checks.
- **The one rule to learn first: every file has one owner.** The methodology's files (`.pkit/decisions/core/`, `.pkit/skills/core/`, …) are pkit's: an upgrade replaces them, so you never edit them. Your files (`.pkit/decisions/project/`, every `project/` folder, your configuration) are yours: nothing pkit does ever writes them. To extend, you add your own file beside pkit's, never change pkit's (COR-001). This is what lets block "Stay current" promise that upgrades never touch your work.
- **Seeing it:** `pkit status` shows how pkit is wired here: the version, the adapter, the capabilities, the skills and agents deployed, the connections. `pkit visibility` chooses pkit's git footprint: committed for the team, or private to your clone (ADR-009). `pkit config` holds the backbone's own settings.
- **Problem:** a methodology adopted by copying documents is frozen the day it is copied, and the moment you edit the copy you can no longer take an improvement.
- **Gain:** one command installs a working methodology the agent uses from the first session; you know from the start which files are yours.
- **Weight:** a `.pkit/` folder in the repository, a few lines in `CLAUDE.md`, the tool's settings merged.
- **Weak spot:**
  - the `.pkit/` tree is large, and a newcomer opening it sees everything at once
  - "never edit pkit's files" surprises people; the way to extend (a sibling file) must be shown, not just said
- **Maintainer's notes:**

## Block 14 of the talk: Stay current (draft, 29 October)

*Facts checked against the repository on 29 October.*

- **What:** pkit improves, and your project takes the improvements by command, without losing your work.
  - **Versions:** the backbone (records, rules, CLI) has one version (1.149.0 today); each capability and adapter has its own, and declares which backbone versions it needs. Semantic versioning: a major version may break, a minor adds, a patch fixes.
  - **`pkit sync`** refreshes the methodology's files at the installed version; **`pkit upgrade`** moves the project to a newer one. Both replace only pkit's files (the one-owner rule from block 1).
  - **Migrations:** when a new version renames or restructures something, it ships a small script that brings each project's state across. A migration is safe to run twice, and a change that needs one cannot be released without it (a check in CI, COR-010). An upgrade checks compatibility first, and refuses rather than leave a project half-moved.
  - **`pkit pin`** fixes a project to one version until it chooses to move (ADR-049).
  - **The changelog** says what each release changed, written from the change notes each pull request declares.
  - **The report channel:** `pkit report` sends a bug, a change request or feedback upstream to project-kit, composed with the `report-author` skill; it is linked to the issue that fixes it. Updates come down, reports go up.
- **Problem:** a methodology you cannot update rots; one that updates by overwriting destroys your customisations; a breaking change with no repair leaves every project to fix it by hand.
- **Gain:**
  - improvements arrive by one command
  - your files survive every upgrade, by design, not by care
  - a breaking change brings its own repair
  - you can talk back: what hurts you reaches the people who fix it
- **Evidence:** the 2.0.0 release is being prepared now (release candidates, #2211); this week's pull requests each declared their change notes for it.
- **Weak spot:**
  - a migration is only as good as its author: one that misses a case leaves a project partly moved
  - release cadence is in the maintainer's hands; candidates are new
- **Maintainer's notes:**

## The slides' structure (agreed 29 October)

**The deck:** a title slide; the opening (the problem pkit solves); one slide per block in the agreed order, capabilities taking two (project-management; software-engineering with connections); what's next; questions.

**Every block slide has the same fields**, kept as data, one entry per slide in `2026-10-29-friday-talk.slides.yaml`, from which the slides are generated:

| Field | Holds |
|---|---|
| **title** | the block's name |
| **message** | the one sentence said |
| **problem** | one line |
| **does** | what pkit does, 2–4 short bullets |
| **show** | one concrete thing on screen (a command, a file, a real case from the week) |
| **visual** | its kind (diagram, screenshot or none), what it shows, and its source (a diagram is written as text, for example Mermaid, and rendered; a screenshot comes from real work) |
| **limit** | the honest weak spot, one line, on the slide |
| **minutes** | the time budget |
| **notes** | the speaker notes, not on the slide |

**Layout:** text left (title, message, problem, bullets, show), the visual right, the limit as one small line at the bottom; a slide with no visual uses the full width. Whether the mural-boards skill can place images is to be checked; if not, visuals are placed by hand.


---

## Appendix A. Earlier working notes (27 October)


Started 25 October. Talk on Friday 30 October. Side quest beside the build work.

### The maintainer's ask

- An honest discussion first: what project-kit is good for, and what it is not.
- Find good use cases, and build the presentation on them.
- Ideal demo: a user installs project-kit, sets up project-management, software-engineering, software-analysis and living-docs, and builds a project with work running in parallel.

### Existing material

- `.agent-workspace/living-docs/talk-outline.md`: 18 slides and 6 demos built on the README's problems (forgetting, prompts, stale docs, self-graded work, copies that rot, updates that overwrite). It covers the backbone only; the capabilities get one slide (12).
- `README.md` on main: "Why project-kit", six highlights, the table against a hand-kept setup, "When not to use it".

### Honest assessment (PM's first take, to discuss)

**Where it earns its keep, from this week's work on project-kit itself**
- **Agents deliver, a person decides.** One project-manager agent files issues, dispatches builders, gathers reviewer verdicts and merges behind a gate. Dozens of pull requests landed this week that way; the maintainer took only the decisions.
- **Review that catches real errors.** Reviewers judge every pull request against accepted rules. Example: on #2062 the docs reviewer found three pages that still described the old behaviour, which the builder had marked as updated.
- **Docs that cannot go stale silently.** A change to code a page rests on asks for an answer, and a reviewer checks the answer.
- **Decisions that survive the session.** Records, the acceptance gate, rules loaded into every session.
- **Parallel work without collisions.** Each task runs on its own branch in its own worktree; answers live in files of their own (COR-062), so pull requests touching the same document no longer conflict.

**Where it costs, said plainly**
- **Running cost.** Answers, reviews and fix rounds take time and tokens: one link pass owed 109 answers (#2064 now fixes that), and this session hit a weekly usage limit.
- **Ceremony and learning curve.** Many concepts: records, places, anchors, answers, rule sets, gates.
- **Claude Code only.** One adapter.
- **Not finished.** Fixers not switched on; the analysis is hard to read on GitHub until #2065 lands; the adoption path is still open (#775).

**Parallel workstreams, what exists**
- project-management's *workstream* is a label that groups issues, not a way to run work in parallel.
- Running in parallel is what the project-manager agent does with the harness: builders in their own git worktrees, one issue and branch each, reviewers run at once, a merge gate. project-kit supplies the rails (issue per task, branch names, answer files that do not conflict, the gate, integration branches for a chain, DEC-013). No single command fans the work out.

### Audience (decided 25 October)

Colleagues who develop an AI agentic platform: users create agents and interact with them, each agent running in its own sandbox. So they build agent runtimes themselves. What they care about: governing what an agent may do, sandboxes, agents delegating to agents, human-in-the-loop, memory across sessions, running many agents at once, cost.

**Angle this suggests:** project-kit as a field report on running a team of AI agents on a real codebase, and the rails that made it safe. Their platform's problems (permissions, sandbox gaps, delegation, approvals, parallel agents) are project-kit's daily problems, solved at the repository layer.

**Lessons from this week that speak to them directly:**
- A named sub-agent's result arrived cut at 4,064 characters, and the prefix read as complete (the harness requirement `delegated-result-complete`, COR-047).
- A message from a sub-agent is not the user's approval: the permission-laundering rule.
- A builder wrote outside the sandbox's granted folder and put a prompt on the maintainer's phone at night (#2026); the fix was a binding rule and a workspace folder every agent is granted.
- Prompt fatigue: the permission model exists so the person reads the prompts that matter (COR-028).
- Reviews in rounds: each fix round found more stale text, until the builder was told to sweep the whole page.
- Cost: a weekly usage limit stopped four agents mid-work; each resumed from its worktree.

### Parallel work: what exists and what is in progress

- **Works today, proven this week:** one project-manager session fans out builders, each in its own git worktree on its own issue branch; reviewers run at once; a merge gate lands each pull request; answers live in files of their own so parallel pull requests do not conflict (COR-062).
- **Built:** instance ownership for several clones of one repository: an instance id, claims and handoff (DEC-035, DEC-043, DEC-045 accepted; `set-instance`, `handoff-issue`), on EPIC #508.
- **Proposed:** the parallelization primitive (DEC-025, proposed; scratchpad `2026-05-26-parallelization-primitive.md`, from the interaction-gateway project): lanes, typed `Blocked by:`, the ready frontier; EPIC #564. The ladder of what can start now and what can run side by side (#1548).
- **Postponed until software-analysis and living-docs existed, which they now do:** multi-clone coordination, recovering every clone's direction after all sessions die (EPIC #943).
- **Agents do the work, the person decides in batches** (EPIC #1673): a chain merging into an integration branch (#1676), agents building only on merged work (#1680), decisions in one batch (#1675).

### Angle (decided 25 October)

**A field report:** "Running a team of AI agents on a real codebase", with project-kit as the rails and the install-and-build demo as the high point.

**Numbers for the hook** (GitHub search, 25 October): 156 pull requests merged on project-kit in the last 7 days, 492 in the last month; 234 issues filed in the last 7 days. Mostly agent-built, merged behind the gate; the maintainer took the decisions.

### Draft skeleton (about 25 minutes)

1. **Hook** — 156 pull requests in a week; one person deciding. What made that safe?
2. **The team** — a diagram: the person, the project-manager agent, builders in their own worktrees, the reviewer panel, the merge gate.
3. **Lessons, each a failure paired with the rail that fixed it**
   - Memory: Monday forgot Friday → records, the acceptance gate, rules in every session.
   - Permissions: prompt fatigue and the sandbox edge → one permission model, a workspace every agent is granted.
   - Delegation: a truncated hand-off read as complete; a sub-agent's "approval" → dispatch rules, no laundering.
   - Self-graded work → reviewers that judge against accepted rules, a merge gate.
   - Stale docs → a change to what a page rests on asks for an answer.
   - Parallel collisions → one branch and worktree per issue, answers in files of their own.
   - Cost → the honest bill: answers, review rounds, usage limits.
4. **Demo** — install, four capabilities, a project sliced and built in parallel.
5. **Limits and what is next** — Claude Code only; the parallelization EPICs.
6. **What carries over to an agent platform** — the takeaways for people who build sandboxed agents.

### Demo format (decided 25 October)

**Recorded.** Real evidence from this week's work backs the lessons.

### Trial install (25 October), in short

Full log: `trial-run.md`. Setup took about 77 s of commands from `init` to a passing `pkit validate`; nothing crashed. software-analysis and living-docs work fully offline; project-management needs a GitHub repository set up first, and the review panel acts through its merge gate. The stale-docs moment works and makes a clear demo beat. Rough edges filed under the adoption EPIC #775: #2083 (init's next steps), #2084 (documentation roots collide), #2085 (status labels), #2086 (false "question not asked"), #2087 (pm says late that it needs GitHub), #2088 (analysis hints), #2089 (living-docs placeholders pass), #2090 (output noise). #2083 and #2087 are being built for the demo.

**Demo prerequisites:** a fresh GitHub repository for the demo project, created by the maintainer; the internal docs root set before software-analysis installs (`pkit config set docs.internal tech-docs`), until #2084 lands; installs run at a real terminal so the fixer questions are asked.

### Direction change (25 October, later)

The maintainer reconsidered the field report: he wants a **feature demonstration on the agentic platform**. A repository with project-kit and the needed capabilities installed, set up for parallel work across workstreams: two or three agents, each with its own checkout of the same repository, each working on a different area. Possibilities to be discussed; he suggests **finishing the parallel work organization first**.

**The platform's sandboxes run Claude Code** (other runtimes too, but the demo focuses on Claude Code). So project-kit works there in full: agents, skills, rules, the permission hook. An inventory of what project-kit offers for parallel clones today is being gathered.

**Topologies to choose from:**
- (a) **A planner and builders:** one project-manager session slices the work and files it per workstream; two or three platform agents, each a Claude Code session in its own clone, named and bound to a workstream, pull their workstream's issues, build, open pull requests, and land behind the gate. Recommended.
- (b) **Peers:** each platform agent owns a workstream end to end, planning included.
- (c) **One session fanning out:** builders in worktrees of one clone, as this week; it shows nothing of the platform.

### What is built for parallel clones (inventory, 25 October)

- **Built on main:** workstreams in full (DEC-018; `add-workstream`, `create-issue --workstream`, `context-workstream`); `set-instance` records a clone's id, and nothing reads it yet; the ownership seam library, which no command calls; the assignee gate in `start-work` (tells people apart, not clones); integration-branch bases (DEC-013); a decision-number clash warning (`pkit decisions check-diff`).
- **Decided, not built:** claim at creation and release at close (#519), the clash guard (#520), signed listings and `handoff --to-instance` (#521), named instances routed by workstream (#512), `create-instance` (#513), the audit-log facility (#511); a worktree inheriting its clone's id (#1140).
- **Proposed only:** lanes, typed `Blocked by:`, the ready frontier (DEC-025); the ladder (#1548).
- **The project-management README's instance section overstates:** it says create-issue, start-work and handoff-issue write the ownership marker; none does.
- **Gaps that would bite two clones under one login:** clone B can start clone A's issue; two clones starting one issue at once both succeed; nothing shows who owns what; routing by workstream rests on the prompt; dependencies are prose.
- **Smallest set to close them:** #519, #520, #521; #512 for routing; #1140 if agents use worktrees. Order and file overlap need DEC-025.

### (a) and (b) compared on an example

Example project: a link shortener with three workstreams, `api` (a REST service), `web` (a page that calls it) and `docs`.

| Moment | (a) A planner and builders | (b) Peers |
|---|---|---|
| Kickoff: "build a link shortener" | The planner writes the analysis (who uses it, what they do), slices it into issues per workstream, and files the API contract as the first `api` task. The person approves one plan. | Each peer plans its own workstream from the brief. Three plans, written at once, each with its own guess at the API's shape. |
| `web` needs `POST /links` | The plan already orders it: the web form depends on the contract task; the web agent starts with the page layout meanwhile. | The web peer files a request in `api` or waits; the API peer has to notice it. Coordination by issue comments. |
| Both want to edit the shared `README.md` | The planner sees it at slicing and gives it to `docs`. | Nobody sees it until the second pull request conflicts. |
| A task turns out twice as big | The builder stops and reports; the planner re-slices; the person decides once. | The peer re-plans on its own; the person learns of it in its next pull request. |
| The person's load | One conversation, one batch of decisions. | Three conversations, decisions from three directions. |
| Ownership in project-kit | The planner creates every issue, so builders must take them over: needs handoff to an instance or a claim at start (#521). | Each peer creates its own issues, so it owns them at creation (DEC-035 point 3): needs only #519. |
| On stage | A clear story: one plan, three lanes, one gate. Rests on a good plan up front. | Looks more autonomous; riskier live, and project-kit has no built coordination between peers. |

**A middle way:** the planner files one Feature per workstream and the cross-workstream contracts; each workstream agent slices its own Feature into tasks, owning them at creation, and builds them.

### Why not one agent with subagents? (honest comparison, 25 October)

**One session with subagents, as this week:**
- Gains: one mind holds the whole picture, so coordination is free; the planner gives each builder a different issue, so nothing collides and no claim machinery is needed; proven at 156 pull requests a week; the person talks to one agent.
- Costs, lived this week:
  - **One context holds all coordination.** The planner's context filled and was compacted several times; once it lost track of two open pull requests (#1997, #1869) until a later check found them.
  - **One failure stops everything.** A usage limit stopped four builders at once.
  - **Subagents are fire-once.** They cannot ask the person, cannot be continued, and report once; a subagent at the nesting limit cannot dispatch its own reviewers (the #1869 fixer had no Agent tool).
  - **The planner is the bottleneck.** Every review settlement and every merge passes through it, one at a time.
  - **One sandbox, one account, one set of permissions** for every builder.
  - **No memory per area.** Each builder starts cold and re-reads its brief.

**Separate agents, each in its own sandbox and clone:**
- Gains: isolation per agent (permissions, secrets, quota, blast radius); one agent failing leaves the others running; each keeps its own context, and can stay with its area for days and learn it; a person, or several people, can talk to each agent directly; it scales past one machine and one account.
- Costs: coordination must live outside any one mind, in the tracker: claims, a clash guard, visibility of who owns what, dependencies, contracts between workstreams; more tokens, since each agent reads the repository itself; more for the person to watch unless a planner gathers the decisions.

**The key point:** in the one-session model, the coordination state lives in the planner's context, which is fragile. With separate agents it must live in the tracker, which is durable, inspectable and survives a crash. project-kit already puts it there (issues, branches, answers in files, the gate); the clone-ownership pieces (#519, #520, #521) finish it.

**When each wins:** one person, one machine, work that fits in days: one agent with subagents. Isolation needed, several people, work that outlives a session, or one failure must not stop the rest: separate agents. Both compose: each separate agent may use subagents of its own.

### Business value of separate agents, not buzzwords (25 October)

The maintainer asked for real value: does it speed up or improve development significantly?

**Where a pull request's time went last week** (the 100 most recent merged, `pr_stats.py`): median 1.3 hours from open to merge (middle half 0.6 to 2.9); a median 35 minutes between consecutive merges into `main`; at most 7 merges in one hour; CI's full suite takes about 30 minutes (18,724 tests). So for one person the limits are CI, the serial merge into `main` and the person's decisions, not how many agents type code.

**Honest conclusion:** for one person, separate agents add little speed over one agent with subagents. The significant gains are elsewhere:
1. **Development capacity scales with people, not with one session.** One planning session serves one person. A team of five, each directing an agent in their own area, decides five times as much in parallel; project-kit keeps their agents from colliding. This is the platform's business case: it serves teams.
2. **No ceiling on one context.** The planner here was compacted several times in one day and lost track of two pull requests. Small, separate contexts lose less; measurable as dropped or redone work.
3. **Specialised agents, if it holds:** an agent that stays with one area for days should need fewer review rounds than a builder starting cold (this week, #2062 took four rounds as each found more). A hypothesis to measure, not a claim.
4. **Capacity:** one account's limit stopped four builders at once; separate sandboxes spread the load.

**What would speed up both shapes:** a merge queue (#1867) and a faster CI, since they bound merges into `main` either way.

**Proposal: measure instead of claim.** Run the demo project's backlog twice, one agent with subagents and then three separate agents, and report: hours to land the backlog, minutes of the person's time, review rounds per pull request, tokens, and work dropped or done twice.

### Direction: configurable topologies (25 October)

The maintainer agreed to measure, and asked first to finish parallelization in project-kit: project-kit provides the possibility and the adopter chooses the topology. Strategies to support: one planner and several workers; several separate agents, each running its own subagents, each in its own domain, by area (api, web, docs) or by discipline (design, development, testing).

**Started:** #519 (claims written at creation and start, released at close) and #1140 (a worktree reads its clone's id, which subagent workers need) are being built. A design note on configurable topologies is being drafted (`design-topologies.md`), to go to the critic and the architect before the maintainer decides, one decision at a time.

**Decided (25 October):** the topology setup is shared through the project's committed pkit configuration. This overturns project-management DEC-045 point 2 (per-user, machine-local, never committed) for shared platforms; recorded on #512.

**The ownership issues are from 7 July** (#508, #510–#513, #519–#521, filed with DEC-045 the same day), three and a half months and many changes ago (answer files, the merge gate, a separate audit trail in DEC-049, workstreams in their own file). Likely outdated: #512 (per-user topology, now overturned), #511 (overlaps DEC-049's audit trail), #513 (provisioning clones is the platform's job), and #519's claim at creation (in planner-and-workers the planner creates everything, so workers must claim at start). Likely still valid: the clash guard (#520) and the signed listing (#521). After the design note, each is checked against today's code and the new direction, then rewritten or closed. #519's pull request is held until the claim rule is settled.

### Where the analysis comes in (proposed, 25 October)

The method says analysis first: the project manager reads the use cases before slicing, and each planned Feature and Task names the use case it serves (project-management DEC-054); a feature's analysis lands ahead of its code (#1680). So:
1. **Analysis now**, in project-management's analysis (`tech-docs/analysis/project-management/`, which has UC-060 to UC-064 and ACT-planner today): the actors (the person, a planner agent, a worker agent, a domain agent) and the use cases of parallel work, such as configuring the setup, planning across domains, a worker taking its next task, two agents reaching for one task, handing work from design to development, an agent resuming after its session died, seeing who works on what, and measuring a setup. Starting material: the pilot's ten coordination use cases, removed with the pilot (#890), readable at commit f78ec818 (`tech-docs/analysis/use-case-model/use-cases/coordination/`), and the design note being drafted.
2. **Walk the design note against the use cases**, then its decisions with the maintainer, one at a time.
3. **Records:** the setup in the project configuration, DEC-045 point 2 overturned, DEC-025 promoted or replaced.
4. **Rewrite or close the July issues,** each naming its use cases; then build. #519's pull request waits for this.

The analysis can be part of the demo: use cases written first, agents building against them.

### Review of #2103, decisions so far (26 October)

- **ACT-director removed:** the maintainer asked why not the person who onboards a project. The core's ACT-adopter is that person: UC-082 (set up the topology), UC-091 (measure topologies) and JRN-004 become the adopter's; UC-090 (see who works on what) the planner's; the operator still starts each agent's session.
- **An instance's identity, recommended:** a clone sets itself by name (`set-instance api-worker`), the name must be an entry of the committed topology; the number DEC-035 uses for the lowest-wins tie-break and the `instance:N` label is derived from the entry's position, never typed. Refines DEC-035 point 1 and DEC-045 point 1. Taken unless the maintainer objects.

### The maintainer's model of parallel clones (26 October)

1. The adopter defines the topology in a committed project config, shared through git: the seats, each with a role and its workstreams or domain (how they are targeted is open), and the agent a seat acts as, plus settings a seat may need.
2. A clone claims a seat, then acts by that seat's role. Claims are not committed: they live on GitHub (option b).
3. Workers sharing one pool lock an issue and release it when done or stopped (DEC-035's ownership, #519–#521); a dead agent's lock needs a release.
4. **A new kind of issue for shared state** (his words: "living state issue"), as a general mechanism for various configs: one issue per piece of shared, changing state, outside the work hierarchy. Its comments are the event log and its description the current state derived from them (the comment-log substrate DEC-043 and ADR-041 already decide). A seat is the first such state; claiming a seat is the same lock as claiming a task. What is reviewed stays in committed config; what changes at run time lives in state issues.

### UC-082 and the clone's side, decided so far (26 October)

- Seat claims live on GitHub, one **state issue per seat** (option b, then 1): claiming a seat is the same lock as claiming a task.
- **State issues** are a general mechanism for shared runtime state (the maintainer's "living state issue").
- **A clone picks its seat (c):** by name when given (`take-seat api-worker`), else the first free seat, optionally of a role (`take-seat --role worker`).
- Harness-agnostic wording throughout: "an agent session in its harness", never a named harness.
- **Task locks vs seats differ:** a task lock follows the four layers (release on done or stop, renewal by the work, a generous limit, a returning clone re-checks before writing). A seat's idle sensitivity is configurable; **the first mode is the most tolerant: a seat stays claimed until the clone releases it, or the organizer clone releases it by force.** No silence-based expiry in that mode.
- **A clone becomes its seat's agent (c):** the project-manager agent by default, reading the seat's role (planner, worker, lead) and running that role's procedure; a seat may name another agent, which drives the seat's work through the same take, lock and land procedure the project-manager agent's skill provides.
- **How a seat targets its work:** by default no scope: workers take the next ready task from one shared pool, highest priority first, skipping tasks that wait on others; the planner slices work vertically, so one agent can finish a task or Feature end to end across layers; the issue lock keeps agents apart. Scope stays an optional filter: by discipline for specialist seats (design, testing), later by workstream for an owned area. Workstreams as software layers are not the partition (component teams cost cross-layer coordination).
- **The organizer (c):** a seat marked as organizer in the topology (typically the planner's) may force-release other seats, and the adopter can always force-release from any clone; each force release is recorded on the seat's state issue.

### Open questions (one at a time)

1. ~~Audience~~, ~~angle~~, ~~demo format~~: decided above.
2. The skeleton, item by item, starting with the hook.
2. Live or recorded demo of the agent work.
3. Which toy project to build in the demo.
4. A GitHub repository for the demo project (needed by project-management).

### Trial run

A trial install into a scratch project in the workspace, to find the rough edges before we promise anything: see `trial-run.md` when it lands.

### Goal reconsidered (decided 26 October, afternoon)

The maintainer reconsidered Friday: the main goal is to present project-kit itself, its building blocks and the motives behind it. Show how lightweight it is and what it gives without any capability. Present the capabilities too, more briefly. The parallel-clones showcase moves to a later talk, once there are comparison data (one agent without pkit against clones with pkit, plus a day-two change). The seats build loses its Friday deadline. Candidate base: `.agent-workspace/living-docs/talk-outline.md` (18 slides, 6 live demos on the backbone, one slide on capabilities).


## Appendix B. Trial run: installing project-kit and four capabilities as a newcomer (27 October)


25 October, 22:44–22:54. Scratch project `trial/demo-app`: a 4-file Python CLI (`greet`), `git init`, one commit, **no remote**.

### How it was run

- **pkit:** built from this checkout (main at 1aa50092, backbone 1.149.0) into `presentation/venv`. That is the same wheel a `uv tool install …@latest` builds, without the global install. The global `~/.local/bin/pkit` was kept off PATH.
- **Environment:** every command ran from `demo-app` in a clean environment: no `CLAUDE*` variables and the venv first on PATH. So pkit saw a plain shell, not an agent session.
- **Prompts:** commands ran without a terminal first. Where one deferred a question to a terminal, I answered it under a pseudo-terminal (`expect`).
- **Files:** raw output of each command is in `trial/raw/<label>.txt`. Timings are in `trial/raw/_index.tsv`, made by `trial/run.sh`.
- **GitHub:** nothing touched. No repository, label, issue or push. Only `pre-check` ran `gh auth status` (a read).

Times are wall-clock per command. Total pkit command time was about 134 s. About 77 s of that took the project from `init` to a green `pkit validate`. That excludes reading: the four capability READMEs are 3,700 lines.

### Step log

### 0. `pkit --help` (the README's "Verify"), 2.3 s, nothing asked
Lists 33 commands. The help text cites record ids (`[COR-021]`, `ADR-011`) that mean nothing to a newcomer.

### 1. `pkit init`, 8.7 s, nothing asked, exit 0
- **First line:** says where it installs ("git repository root — your current directory"). Good.
- **Output:** 110 lines, mostly `installed` / `created` file lines, and "Done." printed twice in the middle.
- **Next steps it prints,** some confusing:
  1. "Install pkit on PATH" with the `uv tool install` command, which you just used to run `init`.
  2. "Fill in `.pkit/capabilities/<name>/project/config.yaml`", before any capability is installed.
  3. "Backup at `.claude/settings.json.pre-pkit`": no backup exists, since there was no settings file before.
  4. Asks you to hand-edit `.gitignore` with 4 lines, including `!.claude/skills/`, and doesn't say why init doesn't write them.
- **Dangling include:** `CLAUDE.md` includes `@.pkit/rules/project.md`, which init does not create.
- **Settings:** `.claude/settings.json` gains 40 allows, including `Bash(ssh:*)`, `Bash(mv:*)`, `Bash(find:*)` and `Bash(gh:*)`. The README warns about this.

### 2a. project-management
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install project-management` | 7.5 s | deferred 1 | ok; deployed `pm` skill, `project-manager` and `pm-reviewer` agents |
| `pkit project-management ask-fixers` (at a terminal) | 1.9 s | no | "No fixer waits for an answer." |
| hand-write `project/config.yaml` (README example), then `pkit data validate …` | 0.9 s | no | ok |
| `pkit project-management bootstrap --dry-run` | 1.3 s | no | plans 15 labels; exit 0 |
| `pkit project-management pre-check` | 3.6 s | no | **FAILED**: 5 fail, 8 skip, 5 ok |
| `pkit project-management self-test --dry-run` | 1.1 s | no | prints its 6-step plan |

- **False alarm:** install ends with "1 question(s) … were not asked … Run each at a terminal: `pkit project-management ask-fixers`". Run at a terminal, that command has nothing to ask, because no installed capability declares a fixer yet.
- **No early warning about the missing repository:** `bootstrap --dry-run` shows `target repo: <unresolved>` and still exits 0. You learn you need a GitHub repository only at `pre-check`.
- **pre-check failures:** no bootstrap stamp, `gh repo view` failed, label list ×2, default branch. It also calls `workstreams:` in config.yaml, which the README's example uses, a "legacy config.yaml fallback". The config's reference comments mention "the 0.55.0 upgrade" while v0.54.0 is installed.
- **uv line leaks:** capability scripts print uv's "Installed 1 package in 2ms" before their own output.
- **Stopped here, needs GitHub:** `bootstrap` (labels; optional starter EPIC), a passing `pre-check`, `self-test` (creates and closes an issue and a milestone). Every pm verb except bootstrap, pre-check, migrate, adopt-existing and self-test refuses until bootstrap has run. That includes the `project-manager` agent ("Then use").

### 2b. software-engineering
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install software-engineering` | 8.3 s | no | ok; 4 agents: software-engineer, code-, security-, docs-reviewer |
| `pkit agents reconcile` / `--write` | 0.5 / 0.6 s | no | appends a commented `project-conventions` stub; clear "optional" message |

Nothing to configure. "would add 1 optional categor(ies)" reads oddly. The review panel works only through pm's merge gate on pull requests, so it needs GitHub too.

### 2c. software-analysis
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install software-analysis` | 11.9 s | deferred 1 | ok; created rule set `ANALYSIS` at `docs/rule-sets/analysis.md`; `analysis-author` skill, `analysis-resolver` agent |
| `pkit project-management ask-fixers` (terminal) | 3.9 s | **yes** | "software-analysis can keep your actors … true on its own … Turn this on? [Y/n]". Answered y; recorded in pm's config.yaml |

The question is plain and good. The rule set lands under `docs/` because both doc roots still default to `docs/` (see 2d). README adoption step 2, choosing each kind's parts with `validate --preview`, is a walkthrough for the skill in Claude. A CLI user has nothing to run for it.

### 2d. living-docs
| Command | Time | Asked | Result |
|---|---|---|---|
| `pkit capabilities install living-docs` | 11.2 s | deferred 1 | ok; `docs-author` skill, `living-docs` agent |
| `pkit project-management ask-fixers` (terminal) | 2.0 s | **yes** | "living-docs can keep your pages true … Turn this on?". y |
| `pkit living-docs validate` | 1.9 s | no | 0 errors, 3 reports; "both documentation roots are 'docs' … onboarding separates them" |
| `pkit config set docs.internal tech-docs` | 1.2 s | **yes** (consent) | ok; also adds `docs/rule-sets` to `friction.places` so ANALYSIS stays found |
| `pkit living-docs new space user` / `technical` | 3.6 / 2.6 s | no | definitions under `tech-docs/living-docs/rule-sets/`; clear next steps |

- **Layout decision with no guidance:** on a fresh project both roots are `docs/`, and no space or page can be created until they differ. Neither the validator report nor the README says what to set. The only hint is a `tech-docs/` example in the CLI README's status section. Nested roots are refused, so `docs/internal` doesn't work.
- **Install order matters, and nothing says so:** because software-analysis went first, its ANALYSIS rule set stays under the **user** root, and the overlay's default ADR folder (`docs/architecture/decisions`) is under it too. Nothing flags either.

### 3. `pkit status` 5.9 s, `pkit validate` 8.9 s, nothing asked
- **`validate`:** 15 validators, **all checks passed**.
- **`status`:** 160 lines. Its terms (roles, points, fillers, "inert fail", "union · inert fallback") are heavy going for a newcomer.
- **Mislabelled agents and skills:** `status` lists the capability-deployed skills and agents (`pm`, `analysis-author`, `project-manager`, `code-reviewer` …) as "**user-managed (untouched by pkit)**". That is wrong-sounding.
- **Connections wired automatically:** 3 roles active, the fixers and doc-check points filled.

### 4. Analysis and a docs page
| Command | Time | Result |
|---|---|---|
| `pkit analysis new actor cli-user --name "Command-line user" --path src/greet/cli.py` | 3.4 s | recorded location `tech-docs/analysis`, wrote an overview page, stamped ACT-cli-user |
| `pkit analysis new use-case greet-someone --actor ACT-cli-user --title … --path …` | 2.9 s | stamped UC-001 |
| `pkit analysis validate` (unfilled) | 1.9 s | **exit 1, 16 errors**: every hint, reported twice ("still holds its hint" and "is empty") |
| (filled both by hand) `pkit analysis validate` | 1.9 s | **exit 1, 3 errors** |
| `pkit analysis overview`, then `validate` (and `--preview`) | 2.3 / 1.9 s | passes |
| `pkit living-docs new page docs/usage.md --space user --kind reference --reader user --title "Using greet" --path src/greet/cli.py --artefact UC-001` | 3.7 s | stamped; lists 3 placeholder lines |
| `pkit living-docs validate` (placeholders **still in**) | 3.1 s | **0 errors** |
| (filled) `pkit living-docs validate`, `pkit validate`, `pkit friction check` | 3.1 / 9.9 / 1.0 s | all pass |

- **The hint's own example fails:** the hints show `1. … 2. …` inline. Written that way, the Main path and Variants fail ("holds no numbered step"); they must be Markdown lists.
- **Overview needs a manual refresh:** the auto-written overview page goes stale on any edit, and the fix is a manual `pkit analysis overview` run.
- **Placeholders pass in living-docs:** a page full of template `<placeholders>` passes, because the `reference` kind requires only its H1. That is inconsistent with software-analysis, which fails every leftover hint.
- **Cross-capability touch:** the analysis actor automatically became a docs reader (`act-cli-user`).
- **The overview suggests a next step:** "No record states what the system is for yet. Write one with `pkit new decision` …".
- **No-remote warning everywhere:** most commands print "warning: the default branch 'main' is read from the local branch … (COR-054 point 2)".

### 5. Bonus: the stale-docs promise
I committed the setup (689 files, about 160,000 lines, for a 4-file project) and changed the greeting text in `cli.py`.
- **Flagged:** `pkit friction check` (1.3 s) flagged ACT-cli-user, UC-001 and `docs/usage.md`. The page's console example is now really wrong.
- **Answered:** `pkit friction revalidate … --outcome unchanged --because … --yes` (0.8 s) wrote an answer file.
- **Demo value:** this works and makes a clear demo moment.

### What worked smoothly
- **Install commands:** `init` and the four installs, 7–12 s each, with no errors and no surprises. Agents, skills and settings were deployed, and the capabilities wired to each other with no configuration.
- **Validation:** `pkit validate` is green right after setup. Validator messages say what to write and why.
- **Prompts:** the consent prompt of `config set` and the fixer questions are in plain language and explain their side effects.
- **Stamp commands:** `new space`, `new page` and `analysis new` are fast and say exactly what they wrote and what comes next.
- **Stale-doc detection:** a code change flags the documents resting on it, and `revalidate` answers them.

### What broke
- **pm cannot be set up without GitHub:** `pre-check` fails 5 checks, and every pm verb refuses until `bootstrap` has run against a GitHub repository.
- **Validation fails on freshly stamped artefacts:** stamped analysis artefacts fail until filled (by design), and the hint's own example form fails too.
- **Misleading output:**
  - the "question not asked" note after the pm install points to a command with nothing to ask;
  - `bootstrap --dry-run` gives no warning that there is no repository;
  - init's next steps name a backup that doesn't exist and an install you already did;
  - `CLAUDE.md` includes a `project.md` that doesn't exist.

Nothing crashed. The only non-zero exits were pre-check (no GitHub) and the analysis validator (unfilled artefacts).

### What needs GitHub
- **project-management:**
  - `bootstrap`: creates 15 labels and optionally a starter EPIC;
  - a passing `pre-check`: repository, labels, default branch, bootstrap stamp;
  - `self-test`: issue and milestone;
  - every issue and pull-request verb, `land-work`, the merge gate;
  - the `project-manager` agent ("File an EPIC for …");
  - `fix-drift`, which starts the granted fixers after a merge.
- **software-engineering:** its review panel and `docs-reviewer` act on pull requests through pm's merge gate.
- **The rest:** `pkit upgrade` (`git ls-remote` of the release tag) and `pkit report`. Neither was run.
- **Works fully offline:** software-analysis and living-docs: stamping, validating, the friction check and revalidating.

### Five roughest edges a live demo would hit
1. **project-management needs a real GitHub repository, prepared in advance.** Without one, `pre-check` prints 5 failures and nothing in pm runs, and `bootstrap --dry-run` doesn't warn first. A live bootstrap creates 15 labels on that repository.
2. **The documentation roots collide on a fresh project.** You must choose a layout (`pkit config set docs.internal tech-docs`) before living-docs can make a space, with no recommended value. Do it **before** installing software-analysis. Otherwise its rule set, and the default ADR folder, sit under the user docs root.
3. **Stamped analysis artefacts are red until hand-written.** Two files gave 16 errors, each reported twice. The hints' inline `1. … 2. …` example is rejected, and the overview needs `pkit analysis overview` after each edit. On stage, use the `analysis-author` skill in Claude or have the text ready to paste.
4. **Questions appear only at a real terminal.** Run from a script or an agent, each install defers the fixer question with a "not asked" note. After the pm install, the command that note names has nothing to ask. Run the installs at a real terminal, or pre-answer with `ask-fixers`.
5. **Output is long and dense.**
   - **Long:** `init` prints 110 lines, `status` 160 and `validate` 73.
   - **Repeated noise:** record ids like "(COR-054 point 2)" on almost every line, the no-remote warning on most commands, and uv's "Installed N packages" lines.
   - **Misleading:** `status` labels capability agents "user-managed".
   - **Scale of the commit:** the first commit is 689 files.
   - **For the demo:** filter output with `grep` or `tail`, or show it pre-recorded.
