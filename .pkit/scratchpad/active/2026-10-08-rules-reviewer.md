---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# One reviewer judges a change against the rules that govern what it touches

A design for #1385, which also designs the merge-gate trigger of #1386. The maintainer asked for both on 8 October, before the rest of the analysis build.

- **Paths:** `PM/` is `.pkit/capabilities/project-management/`, `LD/` is `.pkit/capabilities/living-docs/`, and `SE/` is `.pkit/capabilities/software-engineering/`.
- **Short names:** pm is project-management. The kind note is `.pkit/scratchpad/active/2026-10-05-analysis-kind-structure.md`, the design for #1352. The review-load note is `.pkit/scratchpad/active/2026-10-01-review-load-after-the-fixes.md`.
- **Terms:** a change is a pull request's change. Its diff is the list of files it changes.
- **Read from main** at commit `78837af9`. Every line number cited here is of that commit.
- **Citations:** by file and line, as the brief for this note asks. RS-WRITE-014, which would drop line numbers, is still proposed and binds nothing.
- **Reviewed:** by the critic on the first draft, and by the architect on the revised draft. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers "Questions", and the project manager files "Slicing".
- **Note:** this note builds on the kind note's reading of scope and its preview. The kind note asked for a refinement of COR-051 later (kind note:224-231), and this design needs part of it first (part 2).

## The question

How does one reviewer judge a change against the accepted rules that govern each artefact it touches, and when does the merge gate require it?

- **The maintainer's words, 8 October:** specialised reviewers should not be prompted with fixed rules.
- **What he asked for instead:** one general reviewer that gets the rules governing each changed document. It serves user pages, technical pages and the analysis alike.
- **Why one:** it is "a general mechanism corresponding to the rules general mechanism", that is, to the rule sets of COR-051.
- **It replaces** the separate analysis reviewer and page reviewer proposed earlier on 8 October (#1385, "Related").

## Today

No reviewer at the merge gate reads a rule set, and no rule set in project-kit declares the scope a reviewer would read.

### Who reviews a change to documentation or the analysis

The gate resolves its reviewers from the closing issue's classification and from whether the diff touches code (pm DEC-032 point 1).

- **`pm-reviewer`:** the project's baseline, on every pull request (`PM/project/config.yaml:120-121`).
- **`docs-reviewer`:** on every classified pull request, through `type: "*"`, and on any diff that touches code (`SE/review-contributions.yaml:58-62`).
- **`code-reviewer` and `security-reviewer`:** only when the diff touches code. A Markdown file is documentation (`PM/scripts/_lib/required_reviewers.py:738` and `:776`).
- **An unclassified pull request that touches no code:** `pm-reviewer` alone. software-engineering names that gap and accepts it (`SE/review-contributions.yaml:27-30`).

So a classified change to a page or to an actor draws two reviewers: `pm-reviewer` and `docs-reviewer`.

### What those two check

- **`pm-reviewer`:** the branch, the title, the classification, the closing link, migrations and shared files (`PM/agents/pm-reviewer.md:60-67`).
- **`docs-reviewer`:** three lenses (`SE/agents/docs-reviewer.md:29-33`).
  - It blocks on new public surface left undocumented, and on a doc that contradicts the code (`:45-48`).
  - Clarity and style findings are advisory (`:49`).
  - It reads a project's own rules from the `<project-conventions>` overlay category (`:39-41`). project-kit's overlay defines no such category (`.pkit/agents/project/overlay.yaml`), so it reviews as a generalist.
- **Neither reads a rule set.** The rules that govern a page or an actor reach neither prompt.

### What scripts check

The check aggregator runs `pkit validate` and `pkit friction check` on every pull request (`scripts/check.sh:159-161`).

- **The rule-set pass:** the checks COR-051 asks for, such as origins, ids, the join between data and prose, and inheritance (`src/project_kit/rule_sets.py:1-40`).
- **living-docs' pass:** the checkable parts of its rules. A page's sections against its kind's structure (RS-LDOC-004), its `reader` resolving, and its anchors.
- **software-analysis' pass:** each artefact's front matter and placeholders.
- **The change check:** every artefact whose anchors changed carries an answer (COR-050 point 6).

### What nobody checks at the gate

- **`WRITE` on the analysis.** project-kit's operational rules send whoever writes the analysis to `WRITE` (`.pkit/rules/project.md` rule 3). No check and no reviewer holds a change to it.
- **The parts of `LDOC` and `USER` that need judgement** (`LD/rule-sets/ldoc.md:73-81`), such as:
  - "Every statement a page makes is grounded by the page's anchors"
  - "Each fact is stated once"
  - "says only what that reader needs"
- **Only on request.** The living-docs agent judges them in a reader-review, and only when someone asks (`LD/agents/living-docs/living-docs.md:38` and `:119`).
- **So a change can break an accepted rule and still pass every review.** A 40-word sentence in an actor, or a fact a second page already states, would draw no finding from either reviewer.

### What coverage data exists

The artefacts document names, on each artefact, the rule sets whose scope covers it, and today it names none.

- **The key:** `in_scope_of`, added by #1361 (`src/project_kit/friction_discovery.py:2564-2581` and `:2808`).
- **Measured on `78837af9`:** `pkit friction artefacts --json` lists 111 artefacts, and `in_scope_of` is empty on every one.
- **Why:** no rule set in project-kit declares `scope`.
  - **`WRITE`:** "This set has no scope of its own" (`tech-docs/rule-sets/writing.md:52`).
  - **`TECH` and `USER`:** each inherits `living-docs:LDOC@1` and declares no scope (`tech-docs/living-docs/rule-sets/technical.md:1-6` and `user.md:1-5`). They bind through living-docs' assignment of places to spaces (`LD/project/config.yaml:13-44`).
  - **`LDOC`:** no scope. It binds through living-docs' own check.
- **A scope is checked for shape only** (`.pkit/schemas/README.md:519`). Nothing reads it but the artefacts document.
- **So a trigger on `in_scope_of` would fire on nothing in project-kit today,** and a reviewer reading it would find no rules. Part 2 says what coverage needs.

## Proposal

Seven parts: the reviewer's home, its rules, what it judges, its verdict, the trigger, the overlap with other reviewers, and the cost.

### 1. Where the reviewer lives

A core agent, `rule-set-reviewer`, introduced by a core record of its own, which pm registers into its merge gate with a new floor (part 5).

**Why core.**

- **Rule sets are core.** COR-051 placed them there because two components and every project need them (COR-051:92).
- **It passes the placement test.** An adopter with no capability installed still finds it useful (COR-026:31). A project with its own rule sets can run it on any change by hand.
- **Its body names only core things:** rule sets, the backbone's reading commands, and an artefact's content (COR-050 point 5).
  - It judges a rule with what the rule's text and the backbone give it, and nothing a capability keeps elsewhere (part 2).
- **It carries no term of the merge gate.** `review-pr` puts the verdict line into every reviewer's brief (`PM/scripts/review-pr.py:711-747`). `review-pr` also stamps the verdict marker when it posts (`SE/agents/docs-reviewer.md:94`).
  - So the body defines its three classes of finding by what they mean. The agent takes the verdict line and the tags from the invoker's brief.
  - `review-pr`'s brief names no tags today. The brief gains them, and pm DEC-028 comes to own them (part 4).

**Its own core record.** COR-024 introduced the critic and the architect in a record of their own (COR-024:117), and COR-044 did the same for `process-author`. This reviewer follows them, and COR-051 stays a record about rules and their machinery.

- **Its contract:**
  - It takes its rules only from the rule sets, through the backbone.
  - It judges only the parts of a rule that no check is declared to enforce (part 3).
  - It never writes or judges an answer (`.pkit/rules/core.md` rule 20).
  - It takes its verdict line and its tags from whoever invokes it.
- **Its placement:** core, by COR-026's test.
- **Its stage:** it reviews a diff, beside `convention-compliance-reviewer` in COR-024's stack.
- **Its posture:** advisory, unless a gate owner registers it. The record mandates no review, so a project without pm can still run it.
- **Its sources:** rule sets only, and the record says how they relate to a project's conventions (part 6).
- **Its promotion to a gate needs evidence,** as COR-024 counsels for a new reviewer (COR-024:48 and :102). Slicing issue 7 names the threshold.

**Who registers it.** pm ships a contribution that names the core agent (question 2).

- **Core cannot register a reviewer itself.** pm's collector walks the capabilities in the manifest, and core is none of them (`PM/scripts/_lib/review_contributions.py:574-589` and DEC-032:40).
- **The contribution:** `PM/review-contributions.yaml`, one rule, `floor: touches-ruled-artefact` with `reviewer: rule-set-reviewer`.
- **DEC-032 point 2 gains one principle:** pm names no capability's agent. It may register a core agent, because core is always present and pm already depends on it.
  - The rationale's concern is coupling pm to a discipline most adopters never install (DEC-032:15). A core agent is no such discipline, so the principle keeps that concern whole.
  - The sentences that state the old principle are rewritten to it. They are "pm never names a contributor" (DEC-032:42), "pm stays ignorant of who contributes" (DEC-032:72), and "pm ships no reviewer-contribution rules" (`PM/schemas/review-contributions.yaml:7-8`).
  - A core agent needs no `requires_capabilities: project-management`, which pm could not declare on itself (DEC-032:42).
- **Every pm adopter then carries a floor.** Part 5 says what that costs, and how a pre-filter keeps the cost small.
- **The opt-out works unchanged.** An adopter lists `{capability: project-management, reviewer: rule-set-reviewer, reason}` (DEC-032:105).
- **Deployed with core.** It reads no overlay category, so the deploy never skips it. A project or capability agent of the same name takes its place (`.pkit/adapters/claude-code/deploy-agents.sh:19-21`).
- **The deployed copy is tracked** (`.gitignore:21-22`), so it lands in the change that adds the agent.

| Home | For | Against |
|---|---|---|
| **A core agent that pm registers** (chosen) | Rule sets are core. Any project can run it. One agent serves every kind of artefact. | DEC-032 point 2 gains a principle. Every pm adopter's resolution reads commits when a Markdown file changes. |
| The project wires the floor to the reviewer in its own pm configuration | DEC-032 stays whole. Only a project that wires it pays the cost or meets the gate. | A new pm configuration key. A project that scopes accepted rules must also remember to wire them. |
| A new capability that ships the agent and its contribution | DEC-032 stays as it is. | A capability for one agent, against COR-007. A core-eligible agent hidden behind an install (COR-014). |
| living-docs | Its agent already judges pages against `LDOC` and a space's rules. | The analysis is another component's, never a page (living-docs DEC-001:36). Project rule sets reach beyond documentation. |
| software-engineering's review panel | The panel's threshold for blocking | Its home is code (software-engineering DEC-002:40). Pages and the analysis are not code. |
| pm ships the agent | One capability does it all. | Judging against rules would then need pm installed. `pm-reviewer`'s remit is pm's conventions. |

- **Note:**
  - The name is `rule-set-reviewer`, not `rules-reviewer`. COR-051 keeps rule sets apart from the operational rules in `.pkit/rules/`, which "share the word" (COR-051:29).
  - COR-024 rejected one reviewer for two roles, because the roles work at different stages (COR-024:108). It never asked for one reviewer per kind of document. This reviewer keeps one contract, and the rule sets carry what differs between kinds.

### 2. How it finds the rules

From one backbone answer per artefact: the accepted rules that reach it through the scope of a covering set and that set's inheritance.

**The chain, for each artefact the change alters** (part 5 defines "alters"):

1. **The covering sets.** `in_scope_of` names each set whose scope covers the artefact (COR-051 point 2). A scope may also name the fields an artefact must carry (question 3).
2. **Inheritance.** Each covering set's `inherits` is followed through every set it pins, and on up (COR-051:70-72).
   - An inherited rule binds within the scope of the set that inherits it (question 1).
3. **Status.** Accepted rules only (COR-051:45-52, `rule_sets.py:234-236`).
   - A superseded or withdrawn rule binds nothing.
   - A successor binds wherever its own set reaches. A sibling set that inherits only the original loses the rule, as COR-051:52 allows.
4. **Fills.** A rule that offers an extension point takes the fill its chain gives, which fills it at most once (COR-051:72).
   - A fill binds only while the rule it fills and the filling rule are both accepted.
   - With no fill, the offering rule's *How* says what applies, as RS-WRITE-002's does (`tech-docs/rule-sets/writing.md:90`).
   - **Two chains, one point.** Two covering sets could fill one point differently for one artefact. COR-051 does not settle that. The refinement forbids it, and validation reports overlapping scopes that do.
5. **A pin behind its set.** Validation fails where the check is enforced (COR-051:75). Until the pin is updated, a rule reached only through it binds nothing, and the reviewer may report it as advisory.
   - The repository holds only the newer major, and pinning exists so that its rules bind only after a person's review (COR-051:88).

**Which commit's rules.** The head's rules judge what the head holds, and the base's rules judge what the change removes.

- **What the head holds:** the accepted rules that reach it at the head.
- **What the change removes:** the accepted rules that reached it at the base. Part 3 gives an example.
- **A rule changed beside the text it governs:** a change that alters a rule's status or a set's scope, and also text that rule reaches, draws a `[person]` finding.
  - Accepting a rule is a person's review (COR-051:51), so that person sees the text the rule now reaches.
- **Rule changes alone fire nothing.** An artefact whose content is unchanged is not altered, whether it moved or a scope edit brought it under new rules (part 5).

**This reading needs a core record first.** COR-051 does not state steps 1 to 5. The kind note made the same statements on COR-051's behalf, and asked for a refinement later (kind note:224-231).

- **The kind note itself reads reach two ways.** Its rule says the set "that names it" (kind note:229). Its worked case reads a rule's reach from its own set's scope (kind note:471).
- **Under the second reading,** `TECH` would rule nothing, since it holds no rule of its own. `LDOC` would rule no page.
- **So a refinement of COR-051 comes first** (Slicing, issue 1). Question 1 asks the maintainer to settle reach.
- **The refinement carries only how rules reach an artefact:** reach, fills, successors, pins, the field filter, and the declarations of part 3. The review itself goes in the reviewer's own record (part 1).

**One home for each computation.** The trigger, the freshness rule and the reviewer ask the same question, so one backbone command answers it.

- **The question:** which artefacts did a change alter between two commits, and which accepted rules reach each?
- **What already has a home** (ADR-057 point 2). The command builds on each, and computes none of them again.
  - **Which sets cover an artefact:** discovery's covering function (`src/project_kit/friction_discovery.py:2564-2581`), which feeds `in_scope_of`. The field filter goes there too, so the artefacts document and the command agree.
  - **Which base artefact is which head artefact:** the change check's pairing, which follows renames and identities (`src/project_kit/friction_check.py:794-805`). The pairing and the comparison of content (`:870`) move into one function that both callers use.
  - **Reading a commit:** discovery's tree, which reads the working tree and history alike (ADR-057:27). The rule-set reader (`rule_sets.py:413-436`) learns to read through it, so no second reader of commits appears.
  - **Whether a pin is behind:** the resolver's one version relation, `range_admits` (ADR-057:29).
  - **The base:** the backbone's one home for a comparison's base, `default_branch` (COR-054).
- **The command:** one reading command, taking a base and a head.
  - Its group is named on purpose, `friction` or `rule-sets`, since one functionality has one name (COR-053:38).
  - It runs no query, meaning no resolver and no filler, so git is its only cost.
  - Its output lists each altered artefact with the rules reaching it at each commit, with status, covering set and declared check parts.
  - Its output also carries each rule's text and each artefact's span, tied to a commit. `review-pr`'s checkout may not be at the reviewed head (`PM/scripts/review-pr.py:741`).
- **Where the walk lives:** beside the rule-set reader, not inside discovery, since the reader imports discovery (`rule_sets.py:65`).
- **An ADR records these homes** (Slicing, issue 3).

**Proposed rules bind nothing** (COR-051:46).

- **At the gate:** the reviewer reports nothing under a proposed rule.
- **On request, later:** a preview could treat every proposed rule in the chain as accepted, and list what would break without blocking. The first agent ships without it.
- **Note:** that is the maintainer's answer for `pkit analysis validate --preview` (kind note:27, "Decided 4").

**Facts a rule needs.** The reviewer judges a rule with what the rule and the backbone give it, and guesses nothing.

- **The case:** RS-LDOC-003 needs the page's reader and what that reader needs (`LD/rule-sets/ldoc.md:81`). RS-LDOC-004 needs the kind's template (`ldoc.md:85`).
- **The artefact's own fields** come from the backbone, as the artefacts document gives them.
- **Anything else** must be named by the rule, in its statement or its *How*. The reviewer resolves what the rule names through core commands, such as `pkit connections resolve`.
- **Where the rule names nothing,** the judgement is a `[person]` finding (part 4). RS-LDOC-003 names no readers point today, and RS-LDOC-004 names no template.

**Coverage, for the analysis.** It needs a set with a scope, and nothing new in the backbone.

- **The set:** project-kit's planned `ANALYSIS`, scope `tech-docs/analysis/**`, inheriting `WRITE@1` (kind note:434-435, its issue 11).
- **Brought forward:** a file with that scope and inheritance and no rules yet gives the analysis coverage now. Its name waits for the maintainer (kind note:445).
- **A method set with no scope,** such as software-analysis's planned `SAN`, reaches the reviewer only through a set that inherits it. In the kind note's design, `ANALYSIS` does not (kind note:435).

**Coverage, for pages.** Each space definition takes a root-wide scope with a field filter, so its rules reach only its space's pages (question 3).

- **What a page is:** a document that carries the `reader` and `kind` fields, which no other component claims (living-docs DEC-001:59).
- **What the backbone cannot know:** which rule sets define a space.
  - Only living-docs' project configuration says so (`LD/project/config.yaml:13-20`), and the backbone must not read a capability's configuration.
  - Package metadata is shipped and synced, so it cannot name a project's sets either.
- **The answer recommended:** a scope may name the fields an artefact must carry, such as `carrying: [reader, kind]`, beside its places. The backbone applies the filter in the covering function.
  - living-docs' validation checks that each space definition carries the filter.
  - So the 61 decision records, the actors file and the rule sets under `tech-docs/` stay out of `TECH`'s reach.
  - An unclassified document carries neither field, so it stays out too. Onboarding still only reports it (living-docs DEC-001:59).
- **What it refines:** COR-051 point 2, which gives a scope "as places" (COR-051:35). living-docs, which consumes the sets, requires the filter. That realises COR-051's "a consuming component may narrow it", which nothing implements today.
- **The scopes:** `TECH` covers `tech-docs/**` and its two out-of-root places. `USER` covers `docs/**` and its out-of-root places.
- **Two lists of out-of-root places.** The scopes list them, and so does living-docs' assignment, which "lives here" (living-docs DEC-001:35). `USER` has about 20 (`LD/project/config.yaml:22-44`).
  - living-docs' validation joins the two lists. A place assigned to a space must be in that space definition's scope, and in no other space definition's scope.
  - Retiring one list later refines living-docs DEC-001 point 1 ("Not filed now").
- **Existing adopters:** a definition with no scope covers nothing, which is today's state. Nothing fails on upgrade.

| Route for pages | For | Against |
|---|---|---|
| **Root-wide scopes with a field filter, which living-docs requires** (chosen) | No page listed by hand inside a root. Unclassified documents stay reports. Each scope reads whole in its own file. | A rule-set schema key. Each space definition repeats the filter. |
| A filter that `LDOC` declares once, which every set inheriting it takes | One declaration, which no project can forget | A filter that travels along inheritance, a new rule beside COR-051 point 7 |
| A data point that living-docs fills, naming the sets it narrows | No rule-set schema change | A query in every covering computation, and a channel between components |
| Scopes listing each page, checked by living-docs | No new mechanism | It revives every in-root place assigned by hand, which living-docs DEC-001:109 rejected. Unclassified documents would fail. |
| A scope gains exclusions | Short scopes | A schema change. Each new folder of non-pages needs an exclusion. |
| The reviewer reads living-docs' assignment | No data changes. | A core agent would depend on a capability (COR-026). |

### 3. What it judges, and what scripts check

It judges what no check enforces, and leaves to a check whatever part of a rule is declared as that check's.

- **The rule's owner declares the part a check enforces,** beside the rule, and names the check. The principle goes in the refinement of COR-051 (Slicing, issue 1).
  - **One surface for every check.** A rule's entry reaches a backbone check, a change check, a component's validator and a project's own lint alike.
  - **What a check's registration would miss.** The change check is no validator (ADR-058:31), and a project cannot register a validator (COR-055:21).
  - **Outside the rule's content.** The declaration sits beside the rule, as a kind's structure does (living-docs DEC-001:57). So declaring a check flags no artefact anchored to the rule.
  - **Another owner's rule.** A check's owner cannot declare a part of a rule someone else owns. The reviewer then judges that part too, which costs at worst a duplicate finding, never a missed one.
  - **A declaration that outlives its check.** Validation reports a declaration that names a validator no component registers. Any other check's name is trusted.
  - **Why core.** Component authors write the declaration, so the contract is core's, and the literal is the ADR's (COR-055:40).
- **Today only prose says what a check covers** (`LD/agents/living-docs/living-docs.md:94` and `:119`), and a check's summary line cites a rule (COR-051:110).
- **The reviewer runs no check.** The pull request's required checks run them, and a failure there is not the reviewer's finding.
- **A part no check declares** is the reviewer's, even where a script could check it.

| Rule | A check enforces | The reviewer judges |
|---|---|---|
| RS-LDOC-004, pages of a kind follow one format | The sections a kind declares, in order | Nothing more until the rule names where a kind's template is (`[person]`) |
| RS-LDOC-003, each page names its reader | That the `reader` field resolves | Whether the new text suits that reader, as a `[person]` finding |
| RS-LDOC-001, anchors ground every statement | That anchors resolve and friction is answered | Whether some anchor grounds each new statement |
| RS-WRITE-005, at most 25 words a sentence | Nothing yet | Each new sentence, until a lint declares the rule (slicing issue 6) |

**What the change owns,** after software-engineering DEC-002 point 3:

- **Its own text:** what it adds, what it moves or copies, and a break its edit introduces or widens.
- **Not its own:** a break its edit only sits beside. Fixing one word in an old 40-word sentence leaves the length pre-existing, so the finding is advisory.
- **A deletion can break a rule.** A page removed can break the reader paths of RS-USER-001 (`tech-docs/living-docs/rule-sets/user.md:24`). The base's rules judge it (part 2).
- **Asserted away.** A pre-existing break blocks when the change claims to have fixed it, as DEC-002 point 3 holds (DEC-002:28-29). A rewrite "to `WRITE`" that leaves a 40-word sentence is an example.
- **Only content.** The friction block sits in the container, which is no part of an artefact's content (COR-050:57).
  - Its answers are a person's decision, never reworded for style (`tech-docs/rule-sets/writing.md:224` and `.pkit/rules/core.md` rule 20). So the reviewer never judges them.

### 4. Its verdict

The merge gate's two values, with each finding citing its rule by id and saying whether it blocks, advises or waits for a person.

**The first line** is the one the invoker names. Under `review-pr` it is `Reviewer agent (local, rule-set-reviewer): APPROVED` or `CHANGES_REQUESTED` (pm DEC-028:68).

**One bullet per finding,** each holding:

- its tag, from the three below
- the rule's id in its cited form, such as `living-docs:RS-LDOC-003` or `RS-WRITE-005` (`rule_sets.py:354-358`)
- the artefact and the line, with the passage quoted
- what in the passage breaks the rule

**The tags:**

- **`[block]`:** an accepted rule reaches the artefact, the change owns the break, and the rule's statement and *How* settle it with no reading to choose.
  - An example is a semicolon in a new sentence of prose (RS-WRITE-008).
- **`[advisory]`:** a break the change does not own, tagged `[advisory] (pre-existing: <reason>)` as the code-review panel does (`SE/agents/docs-reviewer.md:86`).
  - A rule reached only through a pin behind its set binds nothing, and the reviewer may report it here too (part 2).
- **`[person]`:** the rule binds and the change owns the passage. But judging it needs a reading the rule does not settle, or a fact the rule does not name.
  - An example is whether a new paragraph says only what the page's reader needs (RS-LDOC-003).

**Who owns the tags.** pm DEC-028 owns the verdict grammar, so it comes to own the tags too (question 4).

- Today the tags exist only as a code comment in `land-work` (`PM/scripts/land-work.py:185-191`).
- `review-pr`'s brief comes to name them, and the core agent takes them from the brief.

**Why `[person]` holds a merge and taste does not.** `docs-reviewer` posts subjective findings as advisory, with no hold (SE DEC-002:26). A `[person]` finding judges under an accepted rule, which binds (COR-051:47). Taste binds nothing, and the agent's record says so.

**The verdict** is `CHANGES_REQUESTED` exactly when any finding is `[block]`.

**A `[person]` finding reaches the person who authorises the merge** (question 4).

- `land-work` prints it with the change's answers, before it stops ready or asks, as it prints answers (pm DEC-055 point 3).
- **The hold.** A run authorised up front merges only if the verdict carrying the `[person]` findings was posted before the run started, for the head it merges.
  - A verdict the run posted itself stops it ready. Its identical re-run then merges, as DEC-055's does (DEC-055:23).
  - That is the analogue of DEC-055's hold, which merges only a list already in the description (DEC-055:17).
  - Like DEC-055's hold, it cannot tell that a person read the findings. Showing them stays the agent's duty (DEC-055 point 5).
- **The records.** DEC-055 point 3 is refined for the hold alone. DEC-055's subject is the change check's own list, never what an agent composed (DEC-055:17 and :29), so the findings never join it.
- **Today** `land-work` reads only `[block]` and `[advisory]` (`PM/scripts/land-work.py:185-191` and `:821-825`), and a fix round carries blocking findings only (`PM/skills/pm/transition-state.md:56`).

**Meaning is kept** (RS-WRITE-013, `tech-docs/rule-sets/writing.md:219`).

- A fix the reviewer suggests adds, drops, weakens or narrows no claim.
- Where keeping the meaning needs a choice of reading, the finding asks the author instead of offering a rewrite.

**Answers stay a person's** (`.pkit/rules/core.md` rule 20).

- The reviewer writes no revalidation, deferral or `unanchored-because`, and runs no friction writer.
- It judges no answer's wording (part 3).

**Read-only,** as every merge-gate reviewer is. Its working files go in the agent workspace (`SE/agents/docs-reviewer.md:110-112`).

**The same change may get two verdicts.** A reviewer's verdict can differ between runs (DEC-028:169), and the line between `[block]` and `[person]` is the reviewer's call.

- A check that declares a mechanical rule takes it off the reviewer (part 3). The writing lint of slicing issue 6 does that for word counts and semicolons.

### 5. The trigger (#1386)

A new floor kind, `touches-ruled-artefact`, satisfied when the change alters the content of an artefact that an accepted rule reaches.

**What it fires on,** read from the backbone command of part 2:

- **Altered:** an artefact added, removed, or with different content between the base and the head. Content is COR-050's: the body and own fields, nothing in the container (COR-050:57).
  - So a change that only writes a revalidation into a page's friction block does not fire it.
  - The change check's pairing decides which base artefact a head artefact is. So a move that keeps the content alters nothing.
- **Ruled:** at least one accepted rule reaches the artefact, at the base or at the head (part 2).
  - An artefact ruled at the base and removed at the head fires it. So does one ruled only at the head.
- **Not through the not-code list.** The list narrows `touches-code` alone.
  - Today `satisfied_floors` applies it to every floor kind (`required_reviewers.py:604`).
  - An adopter who lists `docs/**` as not code would otherwise drop its pages from rules review.
  - Three records say a path on the list satisfies no floor, and each names the exception: DEC-032:113, DEC-028:209 and the format reference (`PM/schemas/review-contributions.yaml:46-49`).
- **Note:** #1386 says "touches", and "in scope of a rule set with an accepted rule". This note narrows "touches" to "alters the content of", and counts inherited rules as the set's.

**Only when a Markdown file changed.** An artefact can be altered only if its file is in the diff, and discovery reads only Markdown files (`src/project_kit/friction_discovery.py:174`).

- So the resolver runs the backbone command only when a changed path in `gh`'s list is Markdown.
- It runs the command only while a rule carrying this floor remains, so an adopter who opts out pays nothing new.

**Freshness.** The reviewer is contributed by a floor alone, so its `APPROVED` stays fresh while the author's later changes alter no ruled artefact (DEC-028:201).

- **Today** the freshness rule takes the paths the author changed since the reviewed head. A clean merge of the base adds none (`PM/scripts/_lib/verdict_freshness.py:156-173`).
- **For this floor,** it asks the backbone command which artefacts in those paths differ between the reviewed head and the current head, and whether any is ruled. The Markdown pre-filter applies here too.
- **So** a later push that touches only code, or only a revalidation, keeps the rule-set reviewer's approval. A clean merge of the base keeps it too, as DEC-028 requires.

**Fail-closed, as the gate already is:**

- **Every pm adopter carries the floor.** pm ships the rule (part 1), so the shortcut for a collection with no floor no longer applies to anyone with pm (`required_reviewers.py:569-571`).
  - A change that touches a Markdown file then needs the base and head commits, a merge base, and a backbone with the command. That holds for `review-pr`, `done-work`, `pre-check` and `show-pr` alike.
  - A missing commit is first fetched by its object name, as freshness does (DEC-028:211). A shallow checkout, or a path with no checkout, still fails closed for such a change.
  - DEC-032 and DEC-028's paragraph on local state come to say so (Slicing, issue 8). Question 2 asks the maintainer to accept it.
- **The command fails** at the base or the head: the resolution fails with the reason. An unreadable diff fails the same way (`required_reviewers.py:72-78`).
  - A base whose configuration cannot be read blocks the change that repairs it. That change lands through the audited bypass (pm DEC-026).
- **A backbone without the command:** the same failure, naming the backbone needed. pm's changeset declares that backbone (PRJ-002).
- **The reviewer not deployed:** the collection fails for every pull request, not only ruled ones (`required_reviewers.py:454-463`). That is today's rule for any contributed reviewer.

**What it costs adopters.**

- **Remote path:** a contributed reviewer is local only (DEC-032:44). A ruled change cannot close without someone running `review-pr`.
- **A stricter gate on upgrade,** wherever a project has a scope over accepted rules. The changeset's segment is a person's judgement (PRJ-002), and slicing issue 9 asks for it.

| Trigger | For | Against |
|---|---|---|
| **A floor on ruled artefacts** (chosen) | It reads the rules' own scopes and statuses. No label escapes it. | One backbone command per resolution that changes Markdown, and a new command to build |
| Path globs in each contribution | No read of the backbone | A third copy of each scope. Blind to status and to revalidation-only changes. A capability cannot know a project's paths. |
| A classification match, such as `workstream: docs` | It exists today. | A label escapes it, the gap DEC-032's floor closed (DEC-032:113). |
| The reviewer as a baseline, returning at once when nothing ruled changed | No new floor | A run on every pull request, stale on any change (DEC-028:202) |

### 6. Overlap with the existing reviewers

Each existing reviewer keeps its question, and the rule-set reviewer takes only the question of the rules.

| Agent | Keeps | Gives to the rule-set reviewer |
|---|---|---|
| `docs-reviewer` | Docs for new public surface, and a doc that contradicts the code | Nothing now. Its clarity lens is advisory, and project-kit gives it no conventions corpus. |
| `pm-reviewer` | pm's conventions on a pull request | Nothing |
| `methodology-reviewer` | CONTRIBUTING's disciplines on records, while they are authored | Nothing, until those disciplines become a rule set scoped to records |
| `convention-compliance-reviewer` | Commit, branch and surface conventions on a diff | Nothing |
| living-docs' agent | Reader-review of a whole page on request, and friction fixes | Judging a change's own text against a page's rules at the gate |
| `analysis-resolver` | Proposing revalidation outcomes. It is no reviewer. | Nothing |

- **Grounding and truth stay apart.** The rule-set reviewer asks whether some anchor grounds a new statement (RS-LDOC-001). `docs-reviewer` asks whether the statement matches the code.
  - So one sentence draws two blocks only when it is both ungrounded and false. One fix of the sentence clears both.
- **Reader fit stays reader-review's.** living-docs keeps change review and reader-review apart, since "merging them would blur both" (living-docs DEC-001:100).
  - The rule-set reviewer reads the diff, so it stays a change review. It asks a reader question only of the change's own text, and only as a `[person]` finding.
  - A sentence in living-docs DEC-001 point 6 can say that a change review includes the rules covering a page (living-docs DEC-001:65-67).
- **Conventions and rule sets stay apart.** A project can give a reviewer rules in two ways: the `<project-conventions>` category (ADR-013:23-29, SE DEC-002:31) and its rule sets.
  - Conventions are prose guidance for producers and the code-review panel, with no ids or statuses. Rule sets are named, gated criteria that a finding cites.
  - The rule-set reviewer reads rule sets only. A convention that should bind at the gate moves into a rule set.
  - The reviewer's record states this, which keeps the two from drifting apart (part 1).
- **Later,** where a page's rules cover its style, `docs-reviewer`'s clarity lens could leave style to the rule-set reviewer. That refines software-engineering DEC-002.

### 7. Cost

A change that alters a ruled artefact costs one more reviewer run each round. While the rules are new, it also costs fix rounds and merges held for a person.

- **Runs.** A classified change to documentation draws two reviewers today. With the floor it draws three, and a code change that also edits a ruled page draws five.
- **Rounds.** Each `[block]` costs a fix round. That round re-runs `pm-reviewer` and `docs-reviewer` too, whose approvals go stale on any change (DEC-028:202).
  - After the October fixes, every extra round answered a reviewer's blocking finding, and a change with none landed in one round (review-load note:56).
  - So the first changes that `WRITE` reaches will cost rounds, until their pages keep it.
- **Holds.** Once the writing lint takes the mechanical rules, most findings left on pages will be `[person]` findings.
  - So the gate's real force is the hold on merges authorised up front (part 4).
  - That makes question 4 the decision with the most consequence.
- **Re-runs of this reviewer stay rare.** A later push that alters no ruled artefact keeps its approval (part 5).
  - A revalidation alone never fires the floor. #1193, a record and one README's revalidation, required two reviewers (review-load note:29), and it would still require two.
- **Prompt size.** The rules of the sets a change reaches, and whatever those rules need read.
  - Today `LDOC` and `USER` hold seven rules in about 120 lines. `WRITE` adds about 250 lines once `TECH` and `USER` inherit it (#1350).
  - Some rules need more than the change. RS-LDOC-001 needs the anchored code and records, and RS-LDOC-002 and RS-USER-001 need the rest of the space.
- **Time.** The artefacts document takes under a second at a commit, measured on `78837af9`. The command runs no query, so git is its only cost, and the review's own run dominates.

## Recommendation

Settle in COR-051 how rules reach an artefact, and give the reviewer a core record of its own. Build the reviewer on one backbone command, and try it by hand before the gate requires it.

1. **Reach:** an inherited rule binds within the inheriting set's scope, stated in a refinement of COR-051 that carries only how rules reach an artefact (question 1).
2. **The reviewer:** a core agent, `rule-set-reviewer`, in a core record of its own. pm registers it under one principle added to DEC-032 point 2 (part 1, question 2).
3. **Its rules:** each altered artefact's accepted rules, at the head for what it holds and at the base for what it removes. One backbone command gives them, built on the homes that exist (part 2).
4. **Coverage:** the analysis comes under a scoped `ANALYSIS` now. Pages come under root-wide scopes, whose field filter living-docs requires (part 2, question 3).
5. **Its judgement:** what no check is declared to enforce, on what the change owns. Each rule's owner declares the part a check enforces (part 3).
6. **Its verdict:** `[block]` for a settled break the change owns, and `[advisory]` for one it does not. `[person]` marks a reading the rule does not settle, and pm DEC-028 owns the tags (part 4).
7. **The trigger:** `touches-ruled-artefact`, on content altered at the base or the head, read only when Markdown changed, never through the not-code list (part 5).
8. **The rollout:** the agent runs by hand on ten real changes first. pm registers it once they show at most one wrong `[block]` (Slicing, issue 7).

## Questions

One decision each, each with a recommendation. They hold the architect's five escalations.

- Question 1 holds the scope of the COR-051 refinement.
- Question 2 holds the change to DEC-032, the cost to every pm adopter, and the first core agent whose verdict can block.
- Question 3 holds the narrowing, and question 4 needs no escalation.

1. **Does an inherited rule bind within the scope of the set that inherits it?**
   - **What the answer authorises:** a refinement of COR-051 that carries only how rules reach an artefact. The review itself goes in the reviewer's own record (question 2).
   - **(a)** Yes. A set inherits its parents' rules unchanged (COR-051:71), so they bind where the inheriting set's scope reaches.
   - **(b)** No. A rule binds only within its own set's scope, as the kind note's worked case reads it (kind note:471).
   - **Recommendation: (a).** Under (b), `TECH` rules nothing and `LDOC` reaches no page, though living-docs builds each space's definition on `LDOC` (living-docs DEC-001 point 2).
2. **Does pm put the core reviewer into every adopter's merge gate?**
   - **Given:** the reviewer is a core agent, in a core record of its own that mandates no review (part 1).
   - **(a)** Yes. pm ships the contribution, and DEC-032 point 2 gains the principle that pm may register a core agent. An adopter opts out as from any contribution.
   - **(b)** No. A project wires the floor to the reviewer in its own pm configuration, and DEC-032 stays whole.
   - **(c)** A new capability ships the agent and its contribution.
   - **What (a) authorises:**
     - the first core agent whose verdict can block a merge, where COR-024 counsels advisory first (COR-024:48)
     - every pm adopter's resolution reading the change's commits when a Markdown file changes, and failing closed when it cannot (part 5)
   - **Recommendation: (a).** Accepted rules bind (COR-051:47), and a project already opts in when it scopes a set with accepted rules. Under (b), it must remember a second step. Under (c), a core-eligible agent hides behind an install (COR-014). The trial by hand comes first, as COR-024 counsels.
3. **How does a space definition's reach narrow to its space's pages?**
   - **The problem:** the backbone cannot tell which sets define a space. Only living-docs' project configuration says so, and the backbone must not read it (part 2).
   - **(a)** A scope names the fields an artefact must carry, such as `carrying: [reader, kind]`. living-docs' validation checks that each space definition carries the filter.
   - **(b)** `LDOC` declares the filter once, and every set that inherits it takes the filter.
   - **(c)** living-docs fills a data point that names the sets it narrows (COR-052 and COR-053).
   - **Under each,** living-docs' validation joins its own list of out-of-root places with the scopes (part 2).
   - **Recommendation: (a).** It needs no channel between components, and each scope reads whole in its own file. Under (b), a filter travels along inheritance, a new rule beside COR-051 point 7. Under (c), every covering computation runs a query.
4. **Who sees a finding a person must judge?**
   - **(a)** Whoever reads the verdict. It rides an `APPROVED` and blocks nothing.
   - **(b)** The author. It requests changes until someone overrides the reviewer (pm DEC-050).
   - **(c)** The person who authorises the merge. `land-work` prints it. A run authorised up front merges only on a verdict posted before the run started, for the head it merges (part 4).
   - **Recommendation: (c).** Under (a), no step routes it to anyone. Under (b), a judgement call blocks and trains the override reflex (software-engineering DEC-002:46). pm DEC-028 then owns the tags, and DEC-055 point 3 gains the hold.

## Slicing

Issues to build, in order. #1385 and #1386 exist already, and the rest are new. Each issue runs `pkit migrations check-diff`, though none triggers a migration: every agent, command, floor value, contribution and schema key here is an addition (COR-010).

1. **Rule sets: how rules reach an artefact**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** a refinement of COR-051, authored with the decision-author skill. It states:
     - where an inherited rule binds (question 1)
     - how a fill binds, and that two chains may not fill one point for one artefact
     - how a successor reads, and that a rule reached only through a pin behind its set binds nothing until the pin is updated
     - that a scope may name the fields an artefact must carry (question 3)
     - that a rule's owner declares the part a check enforces, beside the rule and outside its content
   - **Leaves out:** the review, which issue 2's record holds. The preview stays out too, since it would change the validator contract (kind note:231).
   - **Depends on:** the answers to questions 1 and 3.
2. **The rule-set reviewer's core record**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** a new core record, authored with the decision-author skill. It states the contract, placement, stage and posture of part 1, and how rule sets relate to conventions (part 6). It mandates no review.
   - **Depends on:** the answer to question 2, and issue 1 accepted.
3. **The backbone tells which artefacts a change altered, and the rules reaching each**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:**
     - an ADR, "The rules that reach an artefact have one home", authored with the decision-author skill. It fixes the homes of part 2, and the command's name, group and JSON.
     - the field filter in the rule-set schema, applied in discovery's covering function
     - the declaration of the part a check enforces, read and listed on each rule
     - the change check's pairing and content comparison, pulled out into one function
     - the rule-set reader, reading through discovery's tree at any commit
     - the reading command, which runs no query and gives rules, rule text and spans per commit
   - **Docs:** `in_scope_of` in the CLI reference (`.pkit/cli/README.md:1176`), and the new command.
   - **Changeset:** the backbone, `minor`.
   - **Depends on:** 1.
4. **The analysis comes under a scope**
   - **Delivers:** project-kit's analysis set, with its scope and its inheritance of `WRITE@1`, and no rule of its own yet. The kind note's issue 11 adds its rules later.
   - **Changeset:** none, since the set is project-kit's alone.
   - **Depends on:** the set's name, which the maintainer confirms (kind note:445).
5. **Pages come under their space's scope**
   - **Delivers:**
     - project-kit's `TECH` and `USER` with root-wide scopes and the field filter
     - living-docs' validation checking each space definition's filter, and that its out-of-root places agree with the assignment
     - `LDOC` declaring the parts its checks enforce, RS-LDOC-004's structure and RS-LDOC-003's field
   - **Records:** living-docs DEC-001 points 1, 2 and 6. Point 4 stays, since the filter reads its definition of a page.
   - **Changeset:** living-docs `minor`, with `requires_backbone` for issue 3's release.
   - **Depends on:** 1 and 3.
6. **project-kit's writing lint**
   - **Delivers:** a check of RS-WRITE-005 and RS-WRITE-008. `WRITE` declares the parts it enforces, which takes the mechanical rules off the reviewer.
   - **Changeset:** none, since the lint and `WRITE` are project-kit's alone.
   - **Depends on:** 3. It comes before #1350 brings `WRITE` to every page.
7. **#1385, first half: the core reviewer, run by hand**
   - **Delivers:** `.pkit/agents/core/rule-set-reviewer.md`, authored with the agent-author skill, with its deployed copy. A test holds that its body names no rule id.
   - **Tried:** by hand on at least ten real changes, pages and the analysis among them. Each `[block]` is recorded with whether the maintainer agrees it breaks the rule.
   - **Threshold for issue 9:** at most one wrong `[block]` across the ten changes. COR-024 asks for evidence before a gate (COR-024:102).
   - **Docs:** the agents README, and in `CLAUDE.md` the reviewer table and the line "Five universal core agents shipped today".
   - **Changeset:** the backbone `minor`.
   - **Depends on:** 2 accepted, and 3. Its trial needs 4 and 5.
8. **#1386, the floor `touches-ruled-artefact`**
   - **Delivers:**
     - the new value in the schema's floor enum
     - the resolver reading the command of issue 3, only when a changed path is Markdown
     - the not-code list kept to `touches-code`
     - the freshness rule judged per floor kind, as part 5 says
   - **Tests:**
     - a change inside and outside every scope
     - a set whose rules are all proposed
     - a change that only writes a revalidation
     - a clean merge of the base after an approval
     - a change that touches no Markdown file, which reads no commit
   - **Records:** DEC-032's floor paragraph with its local-state requirement, DEC-028's freshness, not-code and local-state paragraphs, and the format reference. They are accepted before the code is written.
   - **Changeset:** pm `minor`, with `requires_backbone` for issue 3's release. A capability other than pm that contributes this floor declares the pm version that ships it.
   - **Depends on:** 3.
9. **#1385, second half: pm requires the reviewer**
   - **Delivers:** `PM/review-contributions.yaml`. `review-pr`'s brief names the tags, and `land-work` prints `[person]` findings and holds as question 4 says.
   - **Records:** DEC-032 point 2's added principle, DEC-028 owning the tags, and DEC-055 point 3 for the hold. They are accepted before the code is written.
   - **Changeset:** pm, at the segment the maintainer judges for a stricter gate. It declares `requires_backbone` for the release that ships the agent and the command.
     - Without it, an upgrade leaves `rule-set-reviewer` undeployed, and the collection fails for every pull request (part 5).
   - **Depends on:** the answers to questions 2 and 4, issue 7's trial meeting its threshold, and 8.

Not filed now:

- **The preview on request** (part 2), once a person asks for one.
- **Rules that name what they need.** RS-LDOC-003 could name the readers point, and RS-LDOC-004 where a kind's template is (part 2). Each is a change to `LDOC`.
- **One list of out-of-root places.** living-docs could read a place's space from the scopes and retire its assignment, refining living-docs DEC-001 point 1 (part 2).
- **`docs-reviewer` leaving style to the rules,** once rules cover a page's style (part 6).
- **Whether `ANALYSIS` inherits `SAN`,** so that `SAN`'s judgement parts reach the reviewer. The kind note's issue 11 weighs it.
- **Other fixed prompts.** `pm-reviewer`'s checklist and the review panel's universal criteria are fixed rules too. Whether they move into rule sets is a later question.

## Review

The critic reviewed the first draft, and the architect reviewed the revised one. Each finding, with its answer as the note now stands.

**The critic, on the first draft:**

| Finding | Answer |
|---|---|
| Red flag: how an inherited rule reaches an artefact is contested. The kind note reads it two ways, and no record states it. | Confirmed. A refinement of COR-051 comes first (issue 1), and question 1 asks the maintainer to settle reach. |
| Red flag: a successor in an inheriting set, and a pin behind its set, break the walk. | A successor binds where its own set reaches. A rule reached only through a pin behind binds nothing until the pin is updated (part 2, issue 1). |
| Red flag: nothing routes a `[person]` finding to a person. | Confirmed. `land-work` prints it, and holds a run authorised up front on a verdict it posted itself (part 4, question 4). |
| Red flag: listing each page in a scope revives what living-docs DEC-001:109 rejected, and fails unclassified documents. | Adopted the critic's counter: root-wide scopes, narrowed to pages. After the architect's review, question 3 weighs three ways to narrow them (part 2). |
| The freshness claim cannot be built as written. | Defined: artefacts in the author's changed paths that differ between the reviewed head and the current head (part 5). |
| Keeping the not-code list off the new floor changes three records, not one name. | Named: DEC-032:113, DEC-028:209 and the format reference (part 5, issue 8). |
| The rollout's reach is understated. | Named: an undeployed reviewer, a broken base configuration, the remote path, a stricter gate, and the tracked deployed copy (parts 1 and 5). |
| Running the checks at the head has no mechanism. | The reviewer runs no check. Each rule's owner declares the part a check enforces (part 3, issues 1 and 3). |
| The backbone command's slice is bigger than reusing pin resolution. | Costed, then rebuilt on the homes the architect named (part 2, issue 3). |
| A core body cannot find a kind's template, nor know which part a check covers, and the readers chain is a guess. | The reviewer judges only with what a rule and the backbone give it. A rule that names nothing it needs yields a `[person]` finding (part 2). |
| The analysis gets nothing. | Issue 4 brings the analysis set forward with its scope and no rules. |
| Two covering sets can fill one point differently. | The refinement forbids it, and validation reports it (part 2, issue 1). |
| An edited pre-existing break has no rule, and DEC-002's asserted-away clause was dropped. | Defined what the change owns, the clause included (part 3). |
| A new core gate agent has no core record. | It gets a core record of its own (part 1, issue 2). |
| DEC-032's refinement is understated. | Listed in full, then turned into one principle after the architect's review (part 1). |
| Questions missing: "touches" narrowed, and other fixed prompts. | The narrowing is stated (part 5). Other fixed prompts are a later question ("Not filed now"). |
| Cost leaves out fix rounds, and the reading some rules need | Added (part 7). |
| `[block]` against `[person]` is decided afresh on each run, and `[advisory]` was undefined. | Named, with the writing lint as the mitigation. `[advisory]` now means a break the change does not own (part 4). |
| "Needs no term of the merge gate" is not quite true. | Reworded: the agent takes its verdict line and tags from its invoker, and `land-work` must learn `[person]` (parts 1 and 4). |
| "A place cannot exclude" ignores the narrowing COR-051 already allows | Adopted (part 2). |
| A third kind of review skips living-docs DEC-001:100. | Answered: the rule-set reviewer stays a change review, and asks a reader question only as a `[person]` finding (part 6). |
| One defect can draw two blocks. | Grounding and truth are kept apart, and one fix clears both (part 6). |
| Counter-alternatives: core refinement first, lint first, advisory first, a middle answer for person findings, one backbone command, narrowing, an analysis stub | All adopted, in issues 1, 6, 7, 9, 3, 5 and 4. |
| Smaller points: a miscited line, an undefined short name, a misquote, a planned set shown as real, the preview's status, and the note's own writing | Corrected. |

**The architect, on the revised draft:**

| Finding | Answer |
|---|---|
| 1. The COR-051 refinement carries too much. The agent needs a record of its own, and a pin behind its set reads as a third binding state. | Agreed. The refinement carries how rules reach an artefact (issue 1), and the agent gets its own record (issue 2). A rule behind a pin binds nothing (part 2). |
| 2. Every pm adopter's reviewer resolution gains a way to fail. | Agreed. The command runs only when Markdown changed, and DEC-032 and DEC-028 state the requirement (part 5, issue 8). Question 2 asks the maintainer to accept it. |
| 3. DEC-032 point 2 loses its central claim in four places. | Agreed. One principle replaces the four exceptions (part 1). The opt-in a project wires itself is weighed in part 1 and question 2. |
| 4. Narrowing has no way to name the sets it narrows, and two lists of places will drift. | Agreed. Part 2 states the problem, and question 3 weighs three ways, recommending a field filter. living-docs' validation joins the two lists (issue 5). |
| 5. Most of what the command needs already has a home. | Agreed. The command builds on discovery's covering, the change check's pairing, discovery's tree, `range_admits` and `default_branch`. An ADR fixes them (part 2, issue 3). |
| 6. Validators declaring rule parts sit at the wrong level, and miss the change check and project checks. | Agreed. The rule's owner declares the part beside the rule, one surface for every kind of check. The principle goes in the COR-051 refinement (part 3, issue 1). |
| 7. The `[person]` tag needs an owning record and a proxy for "shown". | Agreed. DEC-028 owns the tags, DEC-055 point 3 gains the hold alone, and a run merges only on a verdict posted before it (part 4). |
| 7, continued: two reviewers would treat similar findings differently. | Agreed. A judgement under an accepted rule binds, and taste does not. Part 4 and the agent's record say so. |
| 8. The note never says whether the reviewer judges against the base's rules or the head's. | Agreed. The head's rules judge what the head holds, and the base's rules judge what the change removes. A rule changed beside its text draws a `[person]` finding (part 2). |
| 8, continued: unchanged content, and the reviewed commit | Agreed. Unchanged content fires nothing, and the command carries rule text and spans tied to a commit (parts 2 and 5). |
| 9. The name "rules" is already taken. | Agreed. The agent is `rule-set-reviewer` (part 1). |
| 10. Projects now have two ways to give a reviewer their rules. | Agreed. Conventions guide producers, and rule sets are named, binding criteria. The agent's record says so (part 6, issue 2). |
| Doc drift: this section, `CLAUDE.md`, the CLI reference, living-docs DEC-001, and the changesets | Fixed. This table is the review, and issues 3, 5, 7, 8 and 9 name the docs, records and `requires_backbone` declarations. |
| Migrations: none triggered, and each slice runs the check | Agreed (Slicing). |
| Worth recording: an ADR on one home, and the agent's core record | Adopted as issues 3 and 2. |
| Escalations 1 to 5 | Questions 1 to 3 hold them. Question 2 holds the DEC-032 change, the cost to every pm adopter, and the first core agent that can block. |
| Slicing: narrowing built with the command, checks of every kind, the dependencies, and holds in the cost | Adopted in issues 1, 2, 3, 7, 8 and 9, and in part 7. Promotion now needs ten reviews and a threshold of wrong blocks (issue 7). |
| On the questions | Followed. Question 3 states the problem first and recommends the field filter. |
