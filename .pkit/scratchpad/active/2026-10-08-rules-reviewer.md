---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# One reviewer judges a change against the rules that govern what it touches

A design for #1385, which also designs the merge-gate trigger of #1386. The maintainer asked for both on 8 October, before the rest of the analysis build.

- **Paths:** `PM/` is `.pkit/capabilities/project-management/`, `LD/` is `.pkit/capabilities/living-docs/`, `SA/` is `.pkit/capabilities/software-analysis/`, and `SE/` is `.pkit/capabilities/software-engineering/`.
- **Short names:** pm is project-management. The kind note is `.pkit/scratchpad/active/2026-10-05-analysis-kind-structure.md`, the design for #1352. The review-load note is `.pkit/scratchpad/active/2026-10-01-review-load-after-the-fixes.md`.
- **Terms:** a change is a pull request's change. Its diff is the list of files it changes.
- **Read from main** at commit `78837af9`. Every line number cited here is of that commit.
- **Citations:** by file and line, as the brief for this note asks. RS-WRITE-014, which would drop line numbers, is still proposed and binds nothing.
- **Reviewed:** by the critic on the first draft, by the architect on the second, and by both on the third draft's changed parts. Their findings and the answers are in "Review", at the end.
- **Decided:** all four questions and question 2's consequence, by the maintainer on 9 October. He also named project-kit's analysis set `ANA`, and software-analysis's method set `SAN`.
- **Next:** the project manager files "Slicing".
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

Eight parts: the reviewer's home, its rules, its judgement, its verdict, the trigger, the overlap with other reviewers, the cost, and how scopes select.

### 1. Where the reviewer lives

A core agent, `rule-set-reviewer`, introduced by a core record of its own. Each capability that owns ruled documents contributes it to pm's merge gate, under a new floor (part 5).

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
- **Its posture:** advisory, unless a component contributes it to a gate. The record mandates no review, so a project without pm can still run it.
- **Its sources:** rule sets only, and the record says how they relate to a project's conventions (part 6).
- **Its promotion to a gate needs evidence,** as COR-024 counsels for a new reviewer (COR-024:48 and :102). Slicing issue 8 names the threshold.

**Who registers it.** Each capability that owns ruled artefacts contributes it, as software-engineering contributes its reviewers (question 2, decided).

- **Core cannot register a reviewer itself.** pm's collector walks the capabilities in the manifest, and core is none of them (`PM/scripts/_lib/review_contributions.py:574-589` and DEC-032:40).
- **pm does not add it.** pm names no contributor, and DEC-032's principle stays as it is (DEC-032:42). Two of its lines are refined in place, below.
- **The contributions:** software-analysis contributes it for the analysis, and living-docs for pages. Each ships a `review-contributions.yaml` with one rule, `floor: touches-ruled-artefact` and `reviewer: rule-set-reviewer`.
- **A core agent's name is accepted.** A contributed name must match a deployed agent file, whoever ships the agent (`PM/schemas/review-contributions.yaml:22-27`). Core deploys this one.
- **Either capability covers every ruled artefact,** as the maintainer decided. The floor fires on any altered artefact that an accepted rule reaches, not only on the contributor's own (part 5).
  - So an adopter with software-analysis alone also meets the gate on a ruled README.
- **Both installed:** the reviewer is required once, since the collector de-duplicates by reviewer name (`PM/scripts/_lib/review_contributions.py:334-345`).
- **The opt-out names both.** An adopter's opt-out withdraws one capability's rule, and the reviewer stays required through the other (`PM/scripts/_lib/review_opt_outs.py:115-125`).
- **Neither installed:** a project that uses rule sets runs the reviewer by hand, or adds it itself.
  - **Through a capability of its own** with a one-rule contribution, as a project may incubate one (COR-031). The gate then fires as it does for a contributor.
  - **As a baseline reviewer** in its pm configuration (DEC-028). That runs it on every pull request, stale on any change (DEC-028:202).
- **Each contributor declares pm as an optional dependency** (question 2's consequence, decided). COR-030 gains optional versioned dependencies for this.
  - **The form:** an entry in `requires_capabilities` may carry `optional: true`. The dependency is then not required, but when it is installed, its version must satisfy the range. That matches npm's optional peer dependencies.
  - **The check:** COR-030's, at install and upgrade, as today (COR-030:19-20). pm's collector reads no edge, as pm DEC-042 records for label contributions (DEC-042:27).
  - **The range:** living-docs and software-analysis each declare pm at least the release with the floor. So neither stops standing alone, as each records it does (living-docs DEC-001:88, software-analysis DEC-001:91 and :118).
  - **DEC-032:42 and :63 are refined in place,** to admit a core agent and an optional dependency. Line 42 says a contributor "ships that agent" and declares `requires_capabilities: project-management`, and core ships this one.
  - **Why an edge.** Without one, nothing would hold pm's version. A pm release without the floor refuses the declaration, so every pull request would fail closed until pm is upgraded (`PM/scripts/_lib/review_contributions.py:521-523`). No opt-out clears it (`PM/scripts/_lib/review_opt_outs.py:126-137`).
  - **Not a hard edge.** software-engineering declares one, since its panel relies on pm's floor (`SE/package.yaml:8-14`). Here it would make pm required for both contributors.
  - **The addition** is a schema field, with no migration. pm's label contributions can use it too (DEC-042).
- **Each contributor declares `requires_backbone`** for a release that ships the agent and optional dependencies (PRJ-002).
- **Every adopter with pm and a contributor carries the floor.** Part 5 says what that costs, and how a pre-filter keeps the cost small.
- **Deployed with core.** It reads no overlay category, so the deploy never skips it. A project or capability agent of the same name takes its place (`.pkit/adapters/claude-code/deploy-agents.sh:19-21`).
- **The deployed copy is tracked** (`.gitignore:21-22`), so it lands in the change that adds the agent.

| Home | For | Against |
|---|---|---|
| **A core agent that each owner of ruled artefacts contributes** (chosen, question 2) | Rule sets are core. Any project can run it. One agent serves every kind of document. pm adds nothing. | Two contributions of one rule. A project with neither contributor wires the reviewer itself. COR-030 gains optional dependencies, and DEC-032:42 and :63 are refined. |
| A core agent that pm registers | One contribution, in every pm adopter's gate | DEC-032's D2 gains a principle. Every pm adopter's resolution reads commits when a Markdown file changes. |
| The project wires the floor to the reviewer in its own pm configuration | DEC-032 stays whole. Only a project that wires it pays the cost or meets the gate. | A new pm configuration key. A project that scopes accepted rules must also remember to wire them. |
| A new capability that ships the agent and its contribution | DEC-032 stays as it is. | A capability for one agent, against COR-007. A core-eligible agent hidden behind an install (COR-014). |
| living-docs ships the agent | Its agent already judges pages against `LDOC` and a space's rules. | The analysis is another component's, never a page (living-docs DEC-001:36). Project rule sets reach beyond documentation. |
| software-engineering's review panel | The panel's threshold for blocking | Its home is code (software-engineering DEC-002:40). Pages and the analysis are not code. |
| pm ships the agent | One capability does it all. | Judging against rules would then need pm installed. `pm-reviewer`'s remit is pm's conventions. |

- **Note:**
  - The name is `rule-set-reviewer`, not `rules-reviewer`. COR-051 keeps rule sets apart from the operational rules in `.pkit/rules/`, which "share the word" (COR-051:29).
  - COR-024 rejected one reviewer for two roles, because the roles work at different stages (COR-024:108). It never asked for one reviewer per kind of document. This reviewer keeps one contract, and the rule sets carry what differs between kinds.
  - A floor that fires only on a contributor's own types was not taken. The maintainer chose that either capability covers every ruled artefact.

### 2. How it finds the rules

From one backbone answer per artefact: the accepted rules that reach it through the scope of a covering set and that set's inheritance.

**The chain, for each artefact the change alters** (part 5 defines "alters"):

1. **The covering sets.** `in_scope_of` names each set whose scope covers the artefact (COR-051 point 2). A scope selects by path, by exclusion and by declared type (part 8).
2. **Inheritance.** Each covering set's `inherits` is followed through every set it pins, and on up (COR-051:70-72).
   - An inherited rule binds within the scope of the set that inherits it (question 1, decided).
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
- **So a refinement of COR-051 comes first** (Slicing, issue 1). The maintainer settled reach with question 1.
- **The refinement carries only how rules reach an artefact:** reach, fills, successors, pins, the scope's form, and the declarations of part 3. The review itself goes in the reviewer's own record (part 1).

**One home for each computation.** The trigger, the freshness rule and the reviewer ask the same question, so one backbone command answers it.

- **The question:** which artefacts did a change alter between two commits, and which accepted rules reach each?
- **What already has a home** (ADR-057 point 2). The command builds on each, and computes none of them again.
  - **Which sets cover an artefact:** discovery's covering function (`src/project_kit/friction_discovery.py:2564-2581`), which feeds `in_scope_of`. The scope's exclusions and types apply there too, so the artefacts document and the command agree (part 8).
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
- **An ADR records these homes** (Slicing, issue 4). Type resolution's home goes in ADR-057 point 2 instead (issue 3).

**Proposed rules bind nothing** (COR-051:46).

- **At the gate:** the reviewer reports nothing under a proposed rule.
- **On request, later:** a preview could treat every proposed rule in the chain as accepted, and list what would break without blocking. The first agent ships without it.
- **Note:** that is the maintainer's answer for `pkit analysis validate --preview` (kind note:27, "Decided 4").

**Facts a rule needs.** The reviewer judges a rule with what the rule and the backbone give it, and guesses nothing.

- **The case:** RS-LDOC-003 needs the page's reader and what that reader needs (`LD/rule-sets/ldoc.md:81`). RS-LDOC-004 needs the kind's template (`ldoc.md:85`).
- **The artefact's own fields** come from the backbone, as the artefacts document gives them.
- **Anything else** must be named by the rule, in its statement or its *How*. The reviewer resolves what the rule names through core commands, such as `pkit connections resolve`.
- **Where the rule names nothing,** the judgement is a `[person]` finding (part 4). RS-LDOC-003 names no readers point today, and RS-LDOC-004 names no template.

**Coverage.** Each set says which artefacts it reaches, by path and by the type the artefact's owner declares (part 8, question 3).

- **The analysis:** project-kit's `ANA` comes forward now, a scope over the four analysis types that inherits `WRITE@1` and holds no rules yet (part 8). Its rules come with the kind note's issue 11 (kind note:432-445, there under an earlier name).
- **A method set with no scope,** such as software-analysis's planned `SAN`, reaches the reviewer only through a set that inherits it. In the kind note's design, `ANA` does not (kind note:435).
- **Pages:** each space definition selects `living-docs:page` within its space's paths. So the 61 decision records, the actors and the rules under `tech-docs/` stay out of `TECH`'s reach.
- **The backbone need not know which sets define a space.** Only living-docs' configuration says so (`LD/project/config.yaml:13-20`), and the backbone never reads it. Each set narrows itself instead.
- **Two lists of out-of-root places remain.** The scopes name them, and so does living-docs' assignment, which "lives here" (living-docs DEC-001:35).
  - living-docs' validation joins the two lists. A place assigned to a space must be in that space definition's scope, and in no other space definition's scope.
  - Retiring one list later refines living-docs DEC-001 point 1 ("Not filed now").
- **Existing adopters:** a definition with no scope covers nothing, which is today's state. Nothing fails on upgrade.

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
| RS-WRITE-005, at most 25 words a sentence | Nothing yet | Each new sentence, until a lint declares the rule (slicing issue 7) |

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

- A check that declares a mechanical rule takes it off the reviewer (part 3). The writing lint of slicing issue 7 does that for word counts and semicolons.

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
- **Types keep the floor's meaning.** They change which artefacts are ruled, and so which changes fire it (part 8).
- **Note:** #1386 says "touches", and "in scope of a rule set with an accepted rule". This note narrows "touches" to "alters the content of", and counts inherited rules as the set's.

**Only when a Markdown file changed.** An artefact can be altered only if its file is in the diff, and discovery reads only Markdown files (`src/project_kit/friction_discovery.py:174`).

- So the resolver runs the backbone command only when a changed path in `gh`'s list is Markdown.
- It runs the command only while a rule carrying this floor remains, so an adopter who opts out pays nothing new.

**Freshness.** The reviewer is contributed by a floor alone, so its `APPROVED` stays fresh while the author's later changes alter no ruled artefact (DEC-028:201).

- **Today** the freshness rule takes the paths the author changed since the reviewed head. A clean merge of the base adds none (`PM/scripts/_lib/verdict_freshness.py:156-173`).
- **For this floor,** it asks the backbone command which artefacts in those paths differ between the reviewed head and the current head, and whether any is ruled. The Markdown pre-filter applies here too.
- **So** a later push that touches only code, or only a revalidation, keeps the rule-set reviewer's approval. A clean merge of the base keeps it too, as DEC-028 requires.

**Fail-closed, as the gate already is:**

- **Every adopter with pm and a contributor carries the floor.** living-docs or software-analysis ships the rule (part 1). For everyone else, the command never runs, since no rule carries this floor.
  - A change that touches a Markdown file then needs the base and head commits, a merge base, and a backbone with the command. That holds for `review-pr`, `done-work`, `pre-check` and `show-pr` alike.
  - A missing commit is first fetched by its object name, as freshness does (DEC-028:211). A shallow checkout, or a path with no checkout, still fails closed for such a change.
  - DEC-032's floor amendment and DEC-028's paragraph on local state come to say so (Slicing, issue 9). DEC-032's D2 stays as it is, but for the two lines that question 2's consequence refines (part 1).
- **The command fails** at the base or the head: the resolution fails with the reason. An unreadable diff fails the same way (`required_reviewers.py:72-78`).
  - A base whose configuration cannot be read blocks the change that repairs it. That change lands through the audited bypass (pm DEC-026).
- **A backbone without the command:** the same failure, naming the backbone needed. pm's changeset declares that backbone (PRJ-002).
- **The reviewer not deployed:** the collection fails for every pull request, not only ruled ones (`required_reviewers.py:454-463`). That is today's rule for any contributed reviewer.
  - pm's message tells the adopter to redeploy the capability's agents (`PM/scripts/_lib/review_contributions.py:612-618`). For a core agent the fix is a sync, so the message names it too (issue 9).
- **A pm too old for the floor:** each contributor's optional dependency on pm refuses it, at install and upgrade (part 1). Issue 9's unknown-floor rule stays as a second guard, for a contributor that declares no range on pm.

**What it costs adopters.**

- **Remote path:** a contributed reviewer is local only (DEC-032:44). A ruled change cannot close without someone running `review-pr`.
- **A stricter gate on upgrade,** wherever a project with a contributor has a scope over accepted rules. The contributors' changesets carry the segment, a person's judgement (PRJ-002), and slicing issue 11 asks for it.
- **A project without a contributor** gets no gate. It runs the reviewer by hand, or adds it itself, best through a capability of its own (part 1).

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
| `methodology-reviewer` | CONTRIBUTING's disciplines on records, while they are authored | Nothing, until those disciplines become a rule set scoped to records, by a type the project gives their place (part 8) |
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

- **Runs.** A classified change to documentation draws two reviewers today. Where a contributor is installed, the floor makes it three, and a code change that also edits a ruled page draws five.
- **Rounds.** Each `[block]` costs a fix round. That round re-runs `pm-reviewer` and `docs-reviewer` too, whose approvals go stale on any change (DEC-028:202).
  - After the October fixes, every extra round answered a reviewer's blocking finding, and a change with none landed in one round (review-load note:56).
  - So the first changes that `WRITE` reaches will cost rounds, until their pages keep it.
- **Holds.** Once the writing lint takes the mechanical rules, most findings left on pages will be `[person]` findings.
  - So the gate's real force is the hold on merges authorised up front (part 4).
  - That makes question 4 the decision with the most consequence.
- **Re-runs of this reviewer stay rare.** A later push that alters no ruled artefact keeps its approval (part 5).
  - A revalidation alone never fires the floor. #1193, a record and one README's revalidation, required two reviewers (review-load note:29), and it would still require two.
- **Prompt size.** The rules of the sets a change reaches, and whatever those rules need read.
  - Today `LDOC` and `USER` hold seven rules in about 120 lines. `WRITE` adds about 250 lines once it reaches pages (#1350).
  - Some rules need more than the change. RS-LDOC-001 needs the anchored code and records, and RS-LDOC-002 and RS-USER-001 need the rest of the space.
- **Time.** The artefacts document takes under a second at a commit, measured on `78837af9`. The command runs no query, so git is its only cost, and the review's own run dominates.

### 8. How a scope selects artefacts

A scope selects by path, with wildcards and exclusions, and by the artefact's declared type (question 3).

- **The maintainer's direction, 9 October:** a scope selects documents as precisely as needed.
  - By paths with wildcards and exclusions, as ESLint's flat config aims its rules with `files` and `ignores`, and Vale with globbed sections.
  - By kinds of document that their owner declares, never inferred from fields. Kubernetes selects by a declared `kind`, and DITA declares a topic's type.
- **Why not the fields an artefact carries.** Different kinds of document can carry the same fields and still differ.
  - living-docs' page templates carry `reader` and `kind` by design (`LD/scripts/_lib/spaces.py:19-20`).
  - A project may use a `kind` field for its own purpose.
  - So `carrying: [reader, kind]`, the second draft's filter, would select documents it never meant.
- **Today:** a scope is a list of places (`.pkit/schemas/backbone/rule-set.schema.json:31-39`). The artefacts document gives each artefact its form, `document` or `entry`, and no declared type.

**Terms.** This note calls the new concept an artefact's *type*, since "kind" already names four other things.

- **An artefact type:** what an artefact is, as its owner declares it. The key is `type` on a place and in the artefacts document, and `types` in a scope.
- **An artefact's form:** `document` or `entry`, under the key `kind` in the artefacts document. The key keeps its name, since renaming it would raise the document's version.
- **A page kind:** living-docs' `kind` field, such as `reference` or `signpost` (living-docs DEC-001 point 4).
- **An anchor kind:** a capability's `friction.kinds`, such as living-docs' `source` (`LD/package.yaml:60-62`).
- **A component's kind:** `component.kind` in its package metadata, such as `capability`.
- **Note:**
  - "Type" is DITA's word, in its "topic type". pm's `type` axis classifies an issue, never an artefact, and the two never share a file.
  - A component's registry of types, `friction.types`, would sit beside its anchor kinds, `friction.kinds`. The two keys differ by their word, as their terms do.
  - The kind note calls the analysis' types its kinds, and scopes `ANA` by path (kind note:434). Slicing issue 6 revises it to match.
  - The kind note keys software-analysis' structures by `actor` and the like (kind note:452). Those are the component's own names in its own file, not a project's types.

**What a type is.** One declared name for what an artefact is, or none.

- **Its id:** `<component>:<name>` for a component's type, such as `software-analysis:use-case` or `living-docs:page`.
  - The backbone's own are `backbone:<name>`, as its method rule sets are cited (`src/project_kit/friction_discovery.py:185-186`).
  - A project's own are bare, as a project rule set is cited bare (COR-051 point 6).
- **Its name:** lower-case words joined by hyphens, as an anchor kind's name is. The `/` is reserved for sub-types, which are not built now (below).
- **An entry takes its file's type.** So every actor in a collection is `software-analysis:actor`.
- **No type:** a document in no place has none, and neither has a held document or an artefact no typed place gives one. A `types` selector never matches it.

**Who declares types, and where.** Each component in a registry of its own, each owner on its own places.

- **A component's registry:** one entry per type it owns, under `friction.types` in its package metadata. Each entry holds:
  - a description
  - its kind field, if it has one: the own field in which each artefact of the type declares its kind
  - whether a project may give the type to its own places
- **A component's places** name a type of its registry, as `type: <name>`.
- **A kind field:** an artefact in a place of such a type takes the type only when it declares its kind there.
  - living-docs names `kind` for `page`, the field living-docs DEC-001 point 4 already gives that meaning.
  - So a document in a root that declares no page kind takes no type, and stays an unclassified document for onboarding (living-docs DEC-001:59).
- **The project:** on its own places in the backbone configuration, as `{path, type}` beside a bare path.
  - A project place may take a bare type of its own, or a component's type whose registry admits project places.
  - living-docs admits them for `page`, since its validator checks project places (`LD/scripts/_lib/spaces.py:5-13`). software-analysis admits none, since it checks only its own places (`SA/package.yaml:57-74`).
  - So project-kit's 22 out-of-root places take `living-docs:page`. Each of their documents declares its page kind, so each is a page.
  - A bare name equal to an installed component's type name is refused. Otherwise `type: page` would make a project type and miss `living-docs:page` without a word. The install plan reports a component that would take a name a bare project type uses.
- **The backbone:** `backbone:rule`, which every rule takes by the location rule, whatever place matches its file (COR-051 point 2).
  - It restates the artefacts document's `rule_set` key, derived from the same rule (`friction_discovery.py:2801`).
  - It matters, since rules would otherwise take the type of a place around them, such as living-docs' new definitions place.

| Component | Place | Type |
|---|---|---|
| software-analysis | `analysis/glossary.md` | `term`, each entry |
| software-analysis | `analysis/use-case-model/actors.md` | `actor`, each entry |
| software-analysis | `analysis/use-case-model/use-cases` | `use-case` |
| software-analysis | `analysis/use-case-model/journeys` | `journey` |
| living-docs | each documentation root, `**` | `page`, with the kind field `kind`, project places admitted |
| living-docs | its definitions location, `**`, a new place | `template` |

- software-analysis' revalidation records sit in a held folder, so they take no type (`SA/package.yaml:71-74`).
- The kind note's move of the actors to one file each turns their place into a folder, of the same type (kind note, part 6).

**How the core resolves a type.** From the places that match an artefact's file, read from package metadata and the backbone configuration. It reads no capability's configuration, and no field but a type's declared kind field.

1. **A rule is `backbone:rule`.** The location rule claims rule-set files before any place does (COR-051 point 2).
2. **A root-wide place comes last.** A typed place that equals or encloses a documentation root yields to every typed place that spans no root. The artefacts document marks such a place, under `encloses`.
3. **Otherwise the most specific place wins,** whoever declares it.
   - An exact file beats a folder, and a folder beats a glob.
   - Between folders the longer wins, and between globs the longer literal prefix wins.
   - This is living-docs' order (`LD/scripts/_lib/spaces.py:198-209`).
4. **A tie between two types fails validation.** That covers two places of equal specificity, and two root-wide places.
5. **A project place never takes a component's artefact.** A more specific project place that gives another type to a file a component's own place holds fails validation. A component's artefacts stay its own (living-docs DEC-001:36).
6. **An untyped place takes no part.** It gives no type, and it shadows none.
7. **A conflict fails closed.** While steps 4 or 5 fail, the artefact counts as each type in contention, so every scope that selects either reaches it.

- **The overlap in project-kit.** living-docs' internal root, `tech-docs/**`, matches the actors file, and so does software-analysis' place for it. The artefacts document lists both, as places 23 and 26.
  - Discovery reads a file under the first place that matches it, so the actors' `place` is living-docs' root (`friction_discovery.py:2043-2044`).
  - The type does not follow `place`. Step 2 gives the file to software-analysis' place, so each actor is `software-analysis:actor`. The artefacts document names the place that typed it (below).
- **How living-docs tells pages today.** By claims, then fields (`LD/scripts/_lib/spaces.py:278-297`).
  - **No page:**
    - a document that another component's place or held folder holds
    - a rule-set file
    - a document whose `id` reads as a decision record's
    - anything in the definitions location
  - **A page:** any other document that carries `reader` or `kind`.
  - **Types give the same answer in project-kit.** Another component's places are narrower than a root, rules are `backbone:rule`, the ADRs declare no page kind, and the definitions location is typed `template`.
- **Where they differ,** living-docs keeps a finding.
  - A document whose `id` reads as a decision record's, and which declares a page kind, takes the page type. living-docs reports it, as it fails one today.
  - An assigned out-of-root place that is not typed `living-docs:page` fails living-docs' validation, but only where its space's definition selects by type. Otherwise a type-selecting scope would miss its pages without a word.
- **living-docs keeps its order of places for spaces.** A type says what a document is, never which space holds it (living-docs DEC-001:37). A test pins the two orders' agreement where they overlap (ADR-057:62).
- **Templates.** A template copied into the definitions location carries `reader` and `kind`. living-docs' new place for that location wins over the root, so a template is `living-docs:template`, and its `kind` is never read.
- **A project's own `kind` field** is read only in a place typed `living-docs:page`. Under a root, living-docs already reads it as a page kind (`LD/schemas/page.schema.json`). A project that uses it otherwise there gives that folder a type of its own, which wins over the root.

**The artefacts document** keeps `place` as it is, and gains three keys, all within version 1 (`friction_discovery.py:2610-2614`).

- **`type`** on each artefact: the full id, or `null`.
- **`type_place`** on each artefact: the index of the place that typed it, so no reader takes the type from `place`.
- **`type_conflict`** on each artefact: the types in contention, empty when there is none (step 7).
- **The registry,** each component's types with their kind fields and admissions, so living-docs and the rule-sets pass read it there (ADR-057 point 1).
- **A place's `written`** stays a path, for a project place given as `{path, type}` too.

**Sub-types are not built now.** A page kind could be a sub-type, such as `living-docs:page/reference`, read from the kind field.

- **Why not now:** no scope selects one. The page kinds are living-docs' vocabulary, so the backbone could not tell a misspelt sub-type in a selector from one no page has yet.
- **What stays:** the kind field, as the page's declaration that it has the type, and the `/` reserved in a type's name ("Not filed now").

**The scope's form and meaning.**

```yaml
scope:
  paths: [<glob>, ...]     # where: artefacts whose file one of these matches
  exclude: [<glob>, ...]   # less: artefacts whose file one of these matches
  types: [<type>, ...]     # what: artefacts of these types
```

- **How the keys combine:** an artefact is in scope when a `paths` entry matches its file, no `exclude` entry does, and its type is in `types`. Within one key, any entry suffices.
- **Each path reads as a place does:** a glob with `**` across folders, a file, or a folder and every file beneath it (`friction_discovery.py:1145-1174`).
- **A key left out:**
  - Without `paths`, any path matches. So a set with `types` alone is allowed, and it reaches its types wherever their places lie.
  - Without `types`, any type matches, and so does no type. That keeps today's meaning for a set that gives paths alone.
  - Without `exclude`, nothing is left out.
- **Refused:** an empty list, which could read as nothing or as everything, and a scope with neither `paths` nor `types`.
- **No scope** covers nothing, as today (`friction_discovery.py:2564-2572`). Such a set reaches artefacts only through a set that inherits it.
- **A method set takes no scope.** With types, a shipped scope would bind every adopter's artefacts of a type, with no project set inheriting it. That would remove the choice not to inherit (COR-051:73).
  - No shipped set declares a scope today, `LDOC` and the planned `SAN` included.
  - So "a consuming component may narrow it" leaves COR-051 point 2 and the schema (COR-051:35, `rule-set.schema.json:32`). A set narrows itself.
- **Today's list** stays valid, read as `paths`. So no existing set changes.
- **An unknown type** fails validation in the rule-sets pass, checked against the registries. The finding says whether the type's component is missing, or installed without that type.
  - Uninstalling a component leaves a project set that names its types failing. COR-030's uninstall gate cannot see it, so the project mends its set, as it mends an anchor whose kind lost its resolver.
- **Note:** a scope's `exclude` is not the configuration's excluded paths (COR-050 point 7). Those leave an artefact out of the measures and the answers, and it stays in any scope that selects it. ESLint's key, `ignores`, would keep the two words apart, and this note keeps `exclude`, the word the design was asked for.

**Worked scopes for project-kit.**

`TECH`, every technical page:

```yaml
scope:
  paths: [tech-docs/**, CONTRIBUTING.md, .pkit/release/README.md]
  types: [living-docs:page]
```

`USER`, every user page:

```yaml
scope:
  paths: [docs/**, README.md, .pkit/**/README.md]
  exclude: [.pkit/release/README.md]
  types: [living-docs:page]
```

- **The type keeps out** the 61 ADRs, the actors and the rules under `tech-docs/`. The ADRs declare no page kind, so no folder needs a type.
- **The wildcard replaces** `USER`'s 20 listed places. Its one exclusion is the release README, a technical page under `.pkit/` (`LD/project/config.yaml:24`).

`ANA`, the analysis, brought forward now as a scope that inherits `WRITE@1` and holds no rules yet:

```yaml
inherits: [WRITE@1]
scope:
  types: [software-analysis:actor, software-analysis:term, software-analysis:use-case, software-analysis:journey]
```

- **No paths:** the analysis is found wherever software-analysis places it.
- **Its rules come later,** with the kind note's issue 11.
- **No revalidation record is reached.** A held document is no artefact, so no scope reaches it, by path or by type. Its words are a person's decision (RS-WRITE-013).

**`WRITE` could take a scope of its own, and this note recommends against it.**

- **What it would give:** the analysis covered before `ANA` exists. `ANA` brought forward gives that too.
- **What it would cost:**
  - Two paths to one artefact, through `WRITE`'s scope and through `ANA`'s inheritance. COR-051 fills per chain (COR-051:72), so the refinement would need a rule for an artefact that one chain fills and another does not.
  - The pins in `TECH`, `USER` and `ANA` would stop gating `WRITE`'s new rules, which would bind through `WRITE`'s own scope at once.
- **So `WRITE` stays without a scope.** Its opening and its note on how pages reach it stand (`tech-docs/rule-sets/writing.md:52` and `:246`).

**What it changes.**

- **Type resolution** lives in discovery, beside the covering function (`friction_discovery.py:2564`). ADR-057 point 2 makes discovery the one home of what artefacts declare (ADR-057:27).
- **The covering function** reads each artefact's type, and applies `paths`, `exclude` and `types` (`friction_discovery.py:2564-2606`). `in_scope_of` keeps its meaning: the sets whose scope covers the artefact.
- **The schemas:**
  - the rule-set schema's `scope` takes the mapping beside the list
  - the package schema gains `friction.types`, and a place an optional `type`
  - the configuration schema's project place takes `{path, type}` beside a bare path
- **living-docs:**
  - Its registry declares `page` and `template`, and its places name them.
  - Its validator reads each document's type in place of its own claims. Its order of places stays, for spaces.
  - It keeps the two findings above, where types and its claims differ.
  - **Its assignment of out-of-root places stays** (living-docs DEC-001:35). Its validation joins the assignment with the definitions' scopes. A definition's scope could replace the assignment later ("Not filed now").
- **software-analysis:** its registry declares its four types, and its places name them.
- **The floor `touches-ruled-artefact`** keeps its meaning. Types change which artefacts are ruled, and so which changes fire it.

**Which records change.**

- **A short core record on artefact types,** refining COR-050 points 1 and 14 in place, as COR-053 refined point 1 (COR-050:27). Refining COR-050 directly is the minimum. It states:
  - who declares types and where, and how the core resolves them
  - that friction never reads a type, and a type never changes what counts as an artefact or its content
  - when to revisit: one more concept on places, beside friction's, moves places into a functionality of their own
- **Why not in COR-051's refinement:** the configuration keys are `friction`'s, and the record that owns a key defines it (COR-048:25). living-docs also reads types, outside how rules reach an artefact. So question 3 reaches past question 1.
- **Why the key may hold a type:** living-docs DEC-001 rejected "an audience attribute on each friction-key entry", since a capability may not extend a core key (living-docs DEC-001:107). Here the core record owns and defines the key, and the value is a namespaced id, as an anchor kind is.
- **COR-051 point 2,** inside question 1's refinement: the scope's form and meaning, a method set taking no scope, and `types` selecting by the type the core record gives.
- **ADR-057 point 2,** refined in place: type resolution's home is discovery.
- **living-docs DEC-001:**
  - Point 1 hands its claims to the core's types, keeps its order of places for spaces, and answers its alternative at :107.
  - Point 2 types the definitions location.
  - Point 4 says a page is a document of type `living-docs:page`, which declares its page kind in `kind`. A decision record that declares one is reported.
- **software-analysis DEC-001 point 2:** its registry and its places' types.

**Migration and versions.** Nothing that exists breaks, so no migration is due (COR-010, `.pkit/rules/core.md` rule 7).

- **Today's scopes** keep their list form and their meaning, and no shipped method set declares a scope.
- **The rule-set shape** carries no version of its own (`rule-set.schema.json:5`), and the mapping adds to it.
- **The package and configuration schemas** gain optional keys and forms.
- **The artefacts document** stays at version 1.
- **living-docs' findings** change only where a definition selects by type. Today no adopter's definition has a scope, so none sees a new finding.
  - A project that adds `types` to a definition's scope types its out-of-root places first. A capability migration may not write the backbone configuration, so the configuration command offers it, with consent (COR-048 point 5).
- **An older backbone** passes over a `{path, type}` place and a mapping scope without a word, so the place goes unread until validation runs (`friction_discovery.py:2588-2590` and `:2605`). COR-048 point 6 covers this, and the references say it.
- **Changesets** (PRJ-002): the backbone takes `minor`. living-docs and software-analysis each take `minor`, with `requires_backbone` for the release that ships types.

| Selection | For | Against |
|---|---|---|
| **Paths, exclusions and declared types, a page's type following its declared page kind** (chosen) | Paths say where, and a type says what. Each owner declares its own once. Unclassified documents stay unclassified. | A new concept in a core record. A type on each project place outside the roots. |
| The fields an artefact carries, such as `carrying: [reader, kind]` | No new concept | Rejected by the maintainer. A template and a page carry the same fields, so selecting by fields infers what a document is. |
| Every document in a root typed a page | No field read at all | An unclassified document becomes a page that the rules reach, and a change adding one draws `[block]` findings. Every ADR folder under a root needs a type. |
| Paths with exclusions only | ESLint's and Vale's form. No new concept. | `TECH` must exclude every other owner's folder under its root. A folder a capability adds later joins `TECH` unseen. |
| Types only | Short scopes. `ANA` needs no paths. | Both spaces hold pages, so a type alone cannot tell `TECH` from `USER`. |
| The owner of an artefact's place | No new declaration, since each place names its owner | Places outside the roots are the project's, so their owner cannot tell its pages from its other documents. |
| A selector language, such as Kubernetes' `matchExpressions` | One grammar for any later need | A language to build and teach for three needs. Its tests on fields bring inference back. |
| Types inferred by each component's validator at run time | Each component keeps its own classification. | A query per component at each commit, where git is today's only cost. Inference, which the maintainer rejected. |
| A type in every artefact's own front matter | Exact for every artefact, as Kubernetes and DITA declare it | One more field on every artefact, where a place already says what most of them are. Kept for pages, where one place holds many kinds. |

## Recommendation

Settle in COR-051 how rules reach an artefact, and in a core record on COR-050's places what type each artefact is. Give COR-030 optional dependencies, so the contributors hold pm's version without requiring pm. Give the reviewer a core record of its own, build it on one backbone command, and try it by hand before the gate requires it. The maintainer decided each question on 9 October.

1. **Reach:** an inherited rule binds within the inheriting set's scope. A refinement of COR-051 states it, and carries only how rules reach an artefact (question 1).
2. **The reviewer:** a core agent, `rule-set-reviewer`, in a core record of its own. living-docs and software-analysis each contribute it under the floor, and pm adds nothing (part 1, question 2).
3. **Its contributors and pm:** each declares pm as an optional dependency, at least the release with the floor. COR-030 gains optional versioned dependencies, and DEC-032:42 and :63 are refined in place (part 1, question 2's consequence).
4. **Its rules:** each altered artefact's accepted rules, at the head for what it holds and at the base for what it removes. One backbone command gives them, built on the homes that exist (part 2).
5. **Coverage:** a scope selects by paths, exclusions and the types their owners declare, a page's type following its declared page kind. A short core record on artefact types refines COR-050 points 1 and 14. `ANA` comes forward as a scope over the analysis types (part 8, question 3).
6. **Its judgement:** what no check is declared to enforce, on what the change owns. Each rule's owner declares the part a check enforces (part 3).
7. **Its verdict:** `[block]` for a settled break the change owns, and `[advisory]` for one it does not. `[person]` marks a reading the rule does not settle, and pm DEC-028 owns the tags (part 4).
8. **Who sees a `[person]` finding:** the person who authorises the merge. `land-work` shows it before merging, and DEC-055 point 3 gains the hold (part 4, question 4).
9. **The trigger:** `touches-ruled-artefact`, on content altered at the base or the head, read only when Markdown changed, never through the not-code list (part 5).
10. **The rollout:** the agent runs by hand on ten real changes first. living-docs and software-analysis contribute it once those show at most one wrong `[block]`, and once COR-030 takes optional dependencies (Slicing, issues 8 and 11).

## Questions

All four questions are decided, by the maintainer on 9 October, and so is question 2's consequence. Each says what it authorises.

1. **Does an inherited rule bind within the scope of the set that inherits it?** **Decided: (a),** by the maintainer on 9 October.
   - An inherited rule binds within the scope of the set that inherits it. A set inherits its parents' rules unchanged (COR-051:71).
   - **What it authorises:** a refinement of COR-051 that carries only how rules reach an artefact (Slicing, issue 1). The review itself goes in the reviewer's own record (part 1).
   - **Not taken:** (b), a rule binds only within its own set's scope (kind note:471).
2. **Does pm put the core reviewer into every adopter's merge gate?** **Decided: no, a new option (d),** by the maintainer on 9 October.
   - **The agent stays core.** It reads only rule sets, which are core, and it serves every kind of document.
   - **pm does not add it to the gate.** Each capability that owns ruled documents contributes it, as software-engineering contributes its reviewers. software-analysis contributes it for the analysis, and living-docs for pages.
   - **Each contribution uses the floor `touches-ruled-artefact`.** So either capability installed covers every ruled document.
   - **DEC-032's principle stays as it is,** with no exception for core agents. The contribution format already accepts any deployed agent's name (`PM/schemas/review-contributions.yaml:22-27`). The consequence below refines two of its lines in place.
   - **A project with neither capability** runs the reviewer by hand, or adds it itself (part 1).
   - **What it authorises:** the reviewer as a core agent (Slicing, issues 2 and 8). living-docs and software-analysis contribute it under the floor (issue 11), and DEC-032's principle stays as it is.
   - **Not taken:** (a) pm registers it, (b) each project wires it in its pm configuration, and (c) a new capability ships it.
   - **Its consequence: how does each contributor stand toward pm's version?** **Decided: (iii), an optional dependency,** by the maintainer on 9 October.
     - **What it settles.** DEC-032:42 says a contributing capability "ships that agent" and declares `requires_capabilities: project-management`. Core ships this agent, and a hard edge would make pm required for two capabilities that stand alone (part 1).
     - **The answer:** COR-030 gains optional versioned dependencies. An entry in `requires_capabilities` may carry `optional: true`. The dependency is then not required, but when it is installed, its version must satisfy the range.
     - **The check:** at install and upgrade, as today. That matches npm's optional peer dependencies.
     - **The contributors:** living-docs and software-analysis declare pm as an optional dependency, at least the release with the floor. So neither stops standing alone.
     - **What it authorises:**
       - a refinement of COR-030, a core record, with the schema field and the resolver work (Slicing, issue 11a)
       - no migration, since the addition is a schema field
       - DEC-032:42 and :63 refined in place, to admit a core agent and an optional dependency (issue 11b)
     - **Who else can use it:** pm's label contributions (DEC-042).
     - **Not taken:**
       - **(i)** the hard edge, as software-engineering declares it. pm would become required for living-docs and software-analysis (living-docs DEC-001:88, software-analysis DEC-001:91 and :118).
       - **(ii)** no edge, which this note recommended. A pm release without the floor would fail every pull request closed until pm is upgraded.
     - **(ii)'s mitigations become secondary** (Slicing, issue 9). The unknown-floor rule stays, since it still serves a contributor that declares no range on pm. Settling the lifecycle README's two statements on `pkit upgrade` stays too (`.pkit/lifecycle/README.md:758` and `:767`).
3. **How does a scope select the artefacts its rules reach?** **Decided: (a),** by the maintainer on 9 October.
   - **The problem:** a scope is a list of paths today, and one root holds pages, analysis artefacts, decision records and rules (part 8). The maintainer rejected selecting by the fields an artefact carries.
   - **The answer:** a scope selects by paths with wildcards, by exclusions, and by the artefact types each document's owner declares. A page's type follows the page kind it declares, never the fields it carries. The core resolves overlapping places (part 8).
   - **What it authorises:** a short core record on artefact types, refining COR-050 points 1 and 14 (part 8, Slicing issue 1b). That reaches past question 1's refinement of COR-051, which keeps the scope's own form.
     - The record owns the type on the friction key's places. That answers living-docs DEC-001:107, which rejected a capability's attribute on a core key.
     - A project that later selects pages by type types its out-of-root places first. No adopter's definition selects by type today, so none sees a new finding.
   - **What it keeps:** living-docs' definition of a page, and its unclassified documents, which take no type and so no page rules.
   - **What it leaves out:** a method set takes no scope, so no type binds an adopter's artefacts without a project set (COR-051:73). Self-scoping method sets would need the maintainer's word.
   - **Not taken:**
     - **(b)** paths with wildcards and exclusions only, as ESLint and Vale aim their rules. `TECH` would exclude every other owner's folder under its root, and a folder a capability adds later would join `TECH` unseen.
     - **(c)** declared artefact types beside today's paths, with no exclusions. `USER` would list its 20 out-of-root places one by one.
     - **(d)** a general selector language, such as Kubernetes' `matchExpressions`, over paths, types and fields. A language would be built for three needs, and its tests on fields bring back the inference the maintainer rejected.
     - **A type field on every artefact,** as Kubernetes and DITA declare one. It costs a field where a place already says what most artefacts are, so (a) uses it for pages alone.
4. **Who sees a finding a person must judge?** **Decided: (c),** by the maintainer on 9 October.
   - **The answer:** the person who authorises the merge. `land-work` shows a `[person]` finding before merging, as it shows the change's answers. A run authorised up front merges only on a verdict posted before the run started, for the head it merges (part 4).
   - **What it authorises:** pm DEC-028 owns the tags, and DEC-055 point 3 gains the hold (Slicing, issue 10).
   - **Not taken:**
     - **(a)** whoever reads the verdict, the finding riding an `APPROVED` and blocking nothing. No step would route it to anyone.
     - **(b)** the author, with changes requested until someone overrides the reviewer (pm DEC-050). A judgement call would block, and train the override reflex (software-engineering DEC-002:46).

## Slicing

Issues to build, in order. #1385 and #1386 exist already, and the rest are new. Each issue runs `pkit migrations check-diff`, though none triggers a migration. Every agent, command, floor value, contribution, type and schema key here is an addition (COR-010).

1. **Rule sets: how rules reach an artefact, in two refinements**
   - **Type:** Task, parent EPIC #234.
   - **1a, now: COR-051's refinement,** authored with the decision-author skill. It states:
     - where an inherited rule binds (question 1, decided)
     - how a fill binds, and that two chains may not fill one point differently for one artefact
     - how a successor reads, and that a rule reached only through a pin behind its set binds nothing until the pin is updated
     - the scope's `paths` and `exclude`, what a key left out means, and that a method set takes no scope (part 8)
     - that a rule's owner declares the part a check enforces, beside the rule and outside its content. Question 1 was put with part 2's list, which names this. The issue shows it apart, so the maintainer can move it to the reviewer's record.
   - **1b, now too: the core record on artefact types,** authored with the decision-author skill, refining COR-050 points 1 and 14 (part 8, question 3). COR-051's refinement gains `types` once 1b is accepted.
   - **Leaves out:** the review, which issue 2's record holds. The preview stays out too, since it would change the validator contract (kind note:231).
   - **Depends on:** nothing. Questions 1 and 3 are decided.
2. **The rule-set reviewer's core record**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** a new core record, authored with the decision-author skill.
     - It states the contract, placement, stage and posture of part 1, and how rule sets relate to conventions (part 6). It mandates no review.
     - It states that a contribution of this reviewer covers every ruled artefact, not only the contributor's own. That departs on purpose from a contribution being its contributor's discipline (DEC-032:72).
   - **Depends on:** 1a accepted.
3. **Artefact types and scopes in the backbone**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:**
     - ADR-057 point 2 refined in place: type resolution's home is discovery. It is accepted before the code is written.
     - `friction.types` and a place's `type` in the package schema, and `{path, type}` in the configuration schema
     - type resolution in discovery, with validation of conflicting types, of unknown types and of a bare name that equals a component's
     - `type`, `type_place`, `type_conflict` and the registries in the artefacts document
     - the scope's mapping in the rule-set schema, applied in discovery's covering function, and a method set's scope refused
     - a test pinning living-docs' order of places to the core's, where they overlap
   - **Docs:** the CLI reference on the artefacts document's new keys (`.pkit/cli/README.md:1176`), and the configuration and package references on types. The schemas README on scopes and typed places, and on what an older backbone does with them.
   - **Changeset:** the backbone, `minor`.
   - **Depends on:** 1a and 1b accepted.
4. **The backbone tells which artefacts a change altered, and the rules reaching each**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:**
     - an ADR, "The rules that reach an artefact have one home", authored with the decision-author skill and accepted before the code is written. It fixes the homes of part 2, and the command's name and JSON in a new `rule-sets` group. The question the command answers is COR-051's, and `friction` gains no second rules field.
     - the declaration of the part a check enforces, read and listed on each rule
     - the change check's pairing and content comparison, pulled out into one function
     - the rule-set reader, reading through discovery's tree at any commit
     - the reading command, which runs no query and gives rules, rule text and spans per commit
   - **Docs:** the new command in the CLI reference.
   - **Changeset:** the backbone, `minor`.
   - **Depends on:** 3.
5. **living-docs and software-analysis declare their types**
   - **Delivers:**
     - software-analysis' registry and its four places' types
     - living-docs' registry, `page` with `kind` as its kind field and project places admitted, and `template`. Its roots name `page`, and its definitions location becomes a new place of type `template`.
     - living-docs' validator reading each document's type in place of its own claims. It keeps its order of places for spaces, and the two findings where types and claims differ.
     - living-docs' validation joining each space's out-of-root places with its definition's scope
     - `LDOC` declaring the parts its checks enforce, RS-LDOC-004's structure and RS-LDOC-003's field
   - **Records:** living-docs DEC-001 points 1, 2, 4 and 6, and software-analysis DEC-001 point 2. They are accepted before the code is written.
   - **Changeset:** living-docs and software-analysis, `minor` each. Each declares `requires_backbone` for the later of issue 3's and issue 4's releases, or `release` if they ship together.
   - **Depends on:** 3 and 4.
6. **project-kit's scopes**
   - **Delivers:**
     - project-kit's 22 out-of-root places typed `living-docs:page`
     - `TECH` and `USER` with the scopes of part 8
     - `ANA`, `tech-docs/rule-sets/analysis.md`, inheriting `WRITE@1` with the scope of part 8 and no rules yet
     - the kind note revised to match: `ANA`'s scope by types, and its file brought forward (kind note:432-445)
   - **Changeset:** none, since the places and sets are project-kit's alone.
   - **Depends on:** 5. `ANA`'s rules come with the kind note's issue 11.
7. **project-kit's writing lint**
   - **Delivers:** a check of RS-WRITE-005 and RS-WRITE-008. `WRITE` declares the parts it enforces, which takes the mechanical rules off the reviewer.
   - **Changeset:** none, since the lint and `WRITE` are project-kit's alone.
   - **Depends on:** 4. It comes before #1350 brings `WRITE` to every page.
8. **#1385, first half: the core reviewer, run by hand**
   - **Delivers:** `.pkit/agents/core/rule-set-reviewer.md`, authored with the agent-author skill, with its deployed copy. A test holds that its body names no rule id.
   - **Tried:** by hand on at least ten real changes, pages and the analysis among them. Each `[block]` is recorded with whether the maintainer agrees it breaks the rule.
   - **Threshold for issue 11:** at most one wrong `[block]` across the ten changes. COR-024 asks for evidence before a gate (COR-024:102).
   - **Docs:** the agents README, and in `CLAUDE.md` the reviewer table and the line "Five universal core agents shipped today".
   - **Changeset:** the backbone `minor`.
   - **Depends on:** 2 accepted, and 4. Its trial needs 6.
9. **#1386, the floor `touches-ruled-artefact`**
   - **Delivers:**
     - the new value in the schema's floor enum
     - the resolver reading the command of issue 4, only when a changed path is Markdown
     - the not-code list kept to `touches-code`
     - the freshness rule judged per floor kind, as part 5 says
     - the undeployed-reviewer message naming a sync for a core agent
   - **Secondary guards,** since the contributors' optional dependency on pm refuses a pm too old for the floor (issue 11a):
     - an unknown floor that requires its reviewer on every change, rather than refuse the whole declaration. So a later floor meets an older pm with a required reviewer, never with every pull request blocked. It still serves a contributor that declares no range on pm.
     - whether `pkit upgrade` moves capability versions, settled on the way. The lifecycle README says it does not (`.pkit/lifecycle/README.md:758`), and that it moves every kit-shipped capability at once (`:767`).
   - **Tests:**
     - a change inside and outside every scope
     - a set whose rules are all proposed
     - a change that only writes a revalidation
     - a clean merge of the base after an approval
     - a change that touches no Markdown file, which reads no commit
     - a declaration with an unknown floor
   - **Records:** DEC-032's floor amendment with its local-state requirement and its unknown floor, DEC-028's freshness, not-code and local-state paragraphs, and the format reference. They are accepted before the code is written.
   - **Changeset:** pm `minor`, with `requires_backbone` for issue 4's release.
   - **Depends on:** 4.
10. **pm routes a finding a person must judge**
    - **Delivers:** `review-pr`'s brief names the tags, and `land-work` prints `[person]` findings and holds as question 4 says.
    - **Records:** DEC-028 owning the tags, and DEC-055 point 3 for the hold. They are accepted before the code is written.
    - **Changeset:** pm `minor`.
    - **Depends on:** nothing. Question 4 is decided.
11. **#1385, second half: the owners of ruled artefacts contribute the reviewer, in two parts**
    - **11a, first: COR-030's optional dependencies** (question 2's consequence)
      - **Type:** Task, parent EPIC #234.
      - **Delivers:**
        - COR-030's refinement, authored with the decision-author skill. An entry in `requires_capabilities` may carry `optional: true`. Such a dependency is not required, but when it is installed, its version must satisfy the range.
        - the package schema's `requires_capabilities` entry taking `optional: true`
        - the resolver's dependency check at install, at both upgrade entry points and in `pkit validate`. An absent optional dependency passes, and an installed one meets its range as today (COR-030:19-20).
      - **Left to the refinement:** what COR-030's uninstall gate does with an optional dependency. The maintainer's answer names install and upgrade only.
      - **Docs:** the lifecycle README's `requires_capabilities` row and its install, upgrade and uninstall gates (`.pkit/lifecycle/README.md:188`).
      - **Changeset:** the backbone, `minor`. No migration is due, since the field is an addition.
      - **Depends on:** nothing.
    - **11b, then: the contributions**
      - **Delivers:** a `review-contributions.yaml` in living-docs and one in software-analysis, each with one rule, `floor: touches-ruled-artefact` and `reviewer: rule-set-reviewer`. Each capability declares pm as an optional dependency, at least the release with the floor (issue 9).
      - **Records:**
        - DEC-032:42 and :63 refined in place, to admit a core agent and an optional dependency. No principle changes.
        - Each capability's decision gains a sentence on its review contribution and its optional dependency on pm. It stands apart from the contributions the decision addresses to roles (living-docs DEC-001 point 7, software-analysis DEC-001:87).
      - **Changeset:** living-docs and software-analysis, each at the segment the maintainer judges for a stricter gate. Each declares `requires_backbone` for the latest of the releases that ship the agent, the command and optional dependencies (issues 4, 8 and 11a).
        - Without it, an upgrade leaves `rule-set-reviewer` undeployed, and the collection fails for every pull request (part 5).
        - It also keeps `optional: true` from reaching a backbone that does not know the field.
      - **Depends on:** 11a, issue 8's trial meeting its threshold, 9 and 10.

Not filed now:

- **The preview on request** (part 2), once a person asks for one.
- **Rules that name what they need.** RS-LDOC-003 could name the readers point, and RS-LDOC-004 where a kind's template is (part 2). Each is a change to `LDOC`.
- **One list of out-of-root places.** living-docs could read a place's space from the scopes and retire its assignment, refining living-docs DEC-001 point 1 (part 8).
- **Sub-types,** such as `living-docs:page/reference`, once a scope needs one (part 8).
- **A type for decision records,** once a rule set scopes records. A project can give its records' place a bare type of its own meanwhile (part 6).
- **`docs-reviewer` leaving style to the rules,** once rules cover a page's style (part 6).
- **Whether `ANA` inherits `SAN`,** so that `SAN`'s judgement parts reach the reviewer. The kind note's issue 11 weighs it.
- **Other fixed prompts.** `pm-reviewer`'s checklist and the review panel's universal criteria are fixed rules too. Whether they move into rule sets is a later question.
- **pm's label contributions on an optional dependency.** They can use issue 11a's field too, where pm DEC-042 declined a hard edge (DEC-042:27).

## Review

The critic reviewed the first draft, the architect the second, and both the third draft's changed parts. Each finding, with its answer as the note now stands.

**The critic, on the first draft:**

| Finding | Answer |
|---|---|
| Red flag: how an inherited rule reaches an artefact is contested. The kind note reads it two ways, and no record states it. | Confirmed. A refinement of COR-051 comes first (issue 1), and the maintainer settled reach with question 1. |
| Red flag: a successor in an inheriting set, and a pin behind its set, break the walk. | A successor binds where its own set reaches. A rule reached only through a pin behind binds nothing until the pin is updated (part 2, issue 1). |
| Red flag: nothing routes a `[person]` finding to a person. | Confirmed. `land-work` prints it, and holds a run authorised up front on a verdict it posted itself (part 4, question 4). |
| Red flag: listing each page in a scope revives what living-docs DEC-001:109 rejected, and fails unclassified documents. | Adopted the critic's counter: scopes wider than one page, narrowed to pages. After the maintainer's answer, they select pages by declared type (part 8, question 3). |
| The freshness claim cannot be built as written. | Defined: artefacts in the author's changed paths that differ between the reviewed head and the current head (part 5). |
| Keeping the not-code list off the new floor changes three records, not one name. | Named: DEC-032:113, DEC-028:209 and the format reference (part 5, issue 9). |
| The rollout's reach is understated. | Named: an undeployed reviewer, a broken base configuration, the remote path, a stricter gate, and the tracked deployed copy (parts 1 and 5). |
| Running the checks at the head has no mechanism. | The reviewer runs no check. Each rule's owner declares the part a check enforces (part 3, issues 1 and 4). |
| The backbone command's slice is bigger than reusing pin resolution. | Costed, then rebuilt on the homes the architect named (part 2, issues 3 and 4). |
| A core body cannot find a kind's template, nor know which part a check covers, and the readers chain is a guess. | The reviewer judges only with what a rule and the backbone give it. A rule that names nothing it needs yields a `[person]` finding (part 2). |
| The analysis gets nothing. | Issue 6 brings `ANA` forward, a scope over the analysis types that inherits `WRITE` and holds no rules yet (part 8). |
| Two covering sets can fill one point differently. | The refinement forbids it, and validation reports it (part 2, issue 1). |
| An edited pre-existing break has no rule, and DEC-002's asserted-away clause was dropped. | Defined what the change owns, the clause included (part 3). |
| A new core gate agent has no core record. | It gets a core record of its own (part 1, issue 2). |
| DEC-032's refinement is understated. | Listed in full, then turned into one principle after the architect's review. The maintainer then chose (d), and DEC-032 stays as it is (question 2). |
| Questions missing: "touches" narrowed, and other fixed prompts. | The narrowing is stated (part 5). Other fixed prompts are a later question ("Not filed now"). |
| Cost leaves out fix rounds, and the reading some rules need | Added (part 7). |
| `[block]` against `[person]` is decided afresh on each run, and `[advisory]` was undefined. | Named, with the writing lint as the mitigation. `[advisory]` now means a break the change does not own (part 4). |
| "Needs no term of the merge gate" is not quite true. | Reworded: the agent takes its verdict line and tags from its invoker, and `land-work` must learn `[person]` (parts 1 and 4). |
| "A place cannot exclude" ignores the narrowing COR-051 already allows | Adopted. A scope now narrows itself, with exclusions and types (part 8). |
| A third kind of review skips living-docs DEC-001:100. | Answered: the rule-set reviewer stays a change review, and asks a reader question only as a `[person]` finding (part 6). |
| One defect can draw two blocks. | Grounding and truth are kept apart, and one fix clears both (part 6). |
| Counter-alternatives: core refinement first, lint first, advisory first, a middle answer for person findings, one backbone command, narrowing, an analysis stub | All adopted, in issues 1, 7, 8, 10, 4, 3 and 6. |
| Smaller points: a miscited line, an undefined short name, a misquote, a planned set shown as real, the preview's status, and the note's own writing | Corrected. |

**The architect, on the revised draft:**

| Finding | Answer |
|---|---|
| 1. The COR-051 refinement carries too much. The agent needs a record of its own, and a pin behind its set reads as a third binding state. | Agreed. The refinement carries how rules reach an artefact (issue 1), and the agent gets its own record (issue 2). A rule behind a pin binds nothing (part 2). |
| 2. Every pm adopter's reviewer resolution gains a way to fail. | Agreed. The command runs only when Markdown changed, and DEC-032's floor amendment and DEC-028 state the requirement (part 5, issue 9). Under question 2's answer, only adopters with a contributor carry the floor. |
| 3. DEC-032's D2 loses its central claim in four places. | Resolved by the maintainer's answer to question 2. pm registers nothing, and D2's principle stays as it is (part 1). |
| 4. Narrowing has no way to name the sets it narrows, and two lists of places will drift. | Agreed. Each set narrows itself. After the maintainer rejected a field filter, a scope selects by paths, exclusions and declared types (part 8, question 3). living-docs' validation joins the two lists (issue 5). |
| 5. Most of what the command needs already has a home. | Agreed. The command builds on discovery's covering, the change check's pairing, discovery's tree, `range_admits` and `default_branch`. An ADR fixes them (part 2, issue 4). |
| 6. Validators declaring rule parts sit at the wrong level, and miss the change check and project checks. | Agreed. The rule's owner declares the part beside the rule, one surface for every kind of check. The principle goes in the COR-051 refinement (part 3, issues 1 and 4). |
| 7. The `[person]` tag needs an owning record and a proxy for "shown". | Agreed. DEC-028 owns the tags, DEC-055 point 3 gains the hold alone, and a run merges only on a verdict posted before it (part 4). |
| 7, continued: two reviewers would treat similar findings differently. | Agreed. A judgement under an accepted rule binds, and taste does not. Part 4 and the agent's record say so. |
| 8. The note never says whether the reviewer judges against the base's rules or the head's. | Agreed. The head's rules judge what the head holds, and the base's rules judge what the change removes. A rule changed beside its text draws a `[person]` finding (part 2). |
| 8, continued: unchanged content, and the reviewed commit | Agreed. Unchanged content fires nothing, and the command carries rule text and spans tied to a commit (parts 2 and 5). |
| 9. The name "rules" is already taken. | Agreed. The agent is `rule-set-reviewer` (part 1). |
| 10. Projects now have two ways to give a reviewer their rules. | Agreed. Conventions guide producers, and rule sets are named, binding criteria. The agent's record says so (part 6, issue 2). |
| Doc drift: this section, `CLAUDE.md`, the CLI reference, living-docs DEC-001, and the changesets | Fixed. This table is the review, and issues 3, 4, 5, 8, 9 and 11 name the docs, records and `requires_backbone` declarations. |
| Migrations: none triggered, and each slice runs the check | Agreed (Slicing). |
| Worth recording: an ADR on one home, and the agent's core record | Adopted as issues 4 and 2. |
| Escalations 1 to 5 | Questions 1 to 3 held them. The maintainer decided questions 1 and 2 on 9 October. Question 3 now also asks for a core record on COR-050's places. |
| Slicing: narrowing built with the command, checks of every kind, the dependencies, and holds in the cost | Adopted in issues 1 to 4 and 8 to 11, and in part 7. Promotion needs ten reviews and a threshold of wrong blocks (issue 8). |
| On the questions | Followed. Question 3 states the problem first. After the maintainer's answer, it recommends declared types. |

**The critic, on the third draft's changed parts:**

| Finding | Answer |
|---|---|
| Red flag: every document in a root became a page, so page rules reached unclassified documents, and the mitigation undid itself. | Adopted the critic's counter. A type may name a kind field, and a page's type follows the page kind it declares. An unclassified document takes no type, and the ADRs need no typed folder (part 8). |
| Red flag: question 2's consequence reread DEC-032:42 instead of showing the conflict, and the precedents point to the hard edge. | Reframed. The consequence states that (d) already departs from DEC-032:42's first half. It weighs the hard edge, no edge and a conditional edge, and still recommends no edge, with its cost stated. |
| Each contribution reaches past "for the analysis" and "for pages". | The maintainer's answer says either capability covers every ruled document. Part 1 states what that means for a lone contributor and for the opt-out. A floor scoped to its owner is named as not taken. |
| Type resolution breaks on two root-wide places, a broad project place over a narrow one, a tie within one owner, and a conflict. | Rewritten. A root-wide place comes last, and the most specific wins whoever declares it. A tie fails, a project place never takes a component's artefact, and a conflict counts as each type in contention (part 8). |
| living-docs' order of places also decides spaces, and its claims are categorical. | Corrected. living-docs keeps its order for spaces, and part 8 lists its claims as they are. |
| `core:` names the backbone a second way, and a bare project type can miss without a word. | Types are `backbone:`, as its rule sets are cited. A bare name equal to an installed component's type name is refused (part 8). |
| Types sit in the friction key, though friction never reads them. Do they belong in COR-050? | Put to the architect, below. |
| The kind note diverges in more than its word. | Named in part 8's Note, and slicing issue 6 revises the kind note. |
| `WRITE`'s own scope weakens the pins of the sets that inherit it. | Adopted after the architect's review. `WRITE` stays without a scope, and `ANA` comes forward instead (part 8). |
| The baseline reviewer offered as a fallback is the trigger the note rejects. | A capability of the project's own comes first. The baseline is named with its cost (part 1). |
| The contribution does not fit the decisions' points on contributions to roles. | Issue 11 gives it a sentence of its own. |
| Declaring the part a check enforces is not reach. | Question 1 was put with part 2's list, which names it. Issue 1 shows it apart, so the maintainer can move it. |
| The precedents back a type declared in the document. | Cited for what they show. A page declares its kind, and question 3 weighs a type field on every artefact. |
| "Types change nothing here" and "reads no field" contradict the note. | Corrected (parts 5 and 8). |
| Counter-alternatives: the page's declared kind, `WRITE` on the analysis only until `ANA`, a conditional edge, a floor scoped to its owner, and selection by owner | The first is adopted, and so is the second, in its `ANA` form. The conditional edge is option (iii) of question 2's consequence, and selection by owner is a row of part 8's table. The owner's floor is not taken, by the maintainer's answer. |
| Smaller points: a shortcut, early review claims, a fifth "kind", a miscitation, two meanings of `exclude`, documents and artefacts, "realises", uninstalling, and a type's reach | Corrected. `exclude` stays as the word asked for, with ESLint's `ignores` named. Uninstalling is stated, and the decision-record type is deferred (part 8). |

**The architect, on the third draft's changed parts:**

| Finding | Answer |
|---|---|
| 1. Types belong to COR-050's artefact layer, not to COR-051's refinement. The record that owns a key defines it. | Agreed. A short core record on artefact types refines COR-050 points 1 and 14, and states that friction never reads a type. Question 3 asks for it, and answers living-docs DEC-001:107 (part 8). |
| 2. No registry of types | Adopted. Each component declares its types once, under `friction.types`, and the artefacts document lists them (part 8). |
| 3. A project could give any component's type to its own places. | A type's registry entry says whether it admits project places. living-docs' `page` does, and software-analysis' types do not (part 8). |
| 4. The claim of no new report fails, and point 4 overclaims. | Corrected. living-docs fails an untyped assigned place only where its definition selects by type. It keeps a finding for a decision record that declares a page kind (part 8). |
| 5. Sub-types and a decision-record type are speculative. `backbone:rule` carries weight. | Both deferred ("Not filed now"). `backbone:rule` stays, and part 8 says it restates the `rule_set` key. |
| 6. `place` and `type` disagree in the artefacts document. | Adopted. Each artefact gains `type_place` and `type_conflict`, and `written` stays a path (part 8). |
| 7. Type resolution belongs inside discovery, in ADR-057 point 2. | Adopted. Issue 3 refines ADR-057 point 2 in place, and a test pins living-docs' order to the core's (part 8). |
| 8. A method set that scopes itself would bind every adopter's artefacts. | Adopted. A method set takes no scope, in issue 1a, and "a consuming component may narrow it" leaves COR-051 (part 8). |
| 9. `WRITE`'s own scope makes two paths to one artefact. | Adopted. `WRITE` stays without a scope, `ANA` comes forward, and the rule for one chain filling and another not leaves the note (parts 2 and 8). |
| 10. Endorse no edge, on two conditions, and refine DEC-032:42 and :63 in place. | Adopted. Question 2's consequence recommends no edge with both lines refined. Issue 9 settles the lifecycle README and makes an unknown floor require its reviewer. |
| 11. Split issue 1, accept issue 3's record before code, set issue 5's floor, and name issue 4's group. | Adopted. Issue 1 splits into 1a and 1b, issue 5 takes the later release, and issue 4's command goes in a `rule-sets` group (Slicing). |
| No concern: the resolution order, the prefix, the scope's keys, today's list and empty lists. A collision a later install brings | The install plan reports it (part 8). |
| Doc drift: records missing from the list, the narrowing clause, the references, an older backbone, the lifecycle README, and "point 2" for D2 | Fixed in part 8's records and migration, issues 3 and 9, and the note's wording. |
| Worth recording: ADR-057 point 2, issue 4's ADR, and the reviewer's record on what a contribution covers | Adopted in issues 3, 4 and 2. |
| Escalations: question 3 with the core record, DEC-001:107 and the adopter impact, and question 2's consequence with DEC-032 | Questions 2 and 3 hold them. The note stays at four questions. |
