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
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers "Questions", and the project manager files "Slicing".
- **Note:** this note builds on the kind note's reading of scope and its preview. The kind note asked for a refinement of COR-051 later (kind note:224-231), and this design needs it first (part 2).

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

A core agent, `rules-reviewer`, which pm registers into its merge gate with a new floor (part 5).

**Why core.**

- **Rule sets are core.** COR-051 placed them there because two components and every project need them (COR-051:92).
- **It passes the placement test.** An adopter with no capability installed still finds it useful (COR-026:31). A project with its own rule sets can run it on any change by hand.
- **Its body names only core things:** rule sets, the backbone's reading commands, and an artefact's content (COR-050 point 5).
  - It judges a rule with what the rule's text and the backbone give it, and nothing a capability keeps elsewhere (part 3).
- **It carries no term of the merge gate.** `review-pr` puts the verdict grammar into every reviewer's brief (`PM/scripts/review-pr.py:711-747`). `review-pr` also stamps the verdict marker when it posts (`SE/agents/docs-reviewer.md:94`).
  - So the body says only this. When the invoker asks for a verdict line, the reviewer gives it in the form named, blocking whenever any finding blocks.
  - Its finding tags are the review panel's, which `land-work` reads (`PM/scripts/land-work.py:185-191`). The new `[person]` tag is the one `land-work` must learn (part 4).

**Who registers it.** pm ships a contribution that names the core agent.

- **Core cannot register a reviewer itself.** pm's collector walks the capabilities in the manifest, and core is none of them (`PM/scripts/_lib/review_contributions.py:574-589` and DEC-032:40).
- **The contribution:** `PM/review-contributions.yaml`, one rule, `floor: touches-ruled-artefact` with `reviewer: rules-reviewer`.
- **No layer breaks.** pm depends on core, so pm naming a core agent is a dependency it already has.
- **What DEC-032 point 2 must change.** Each of these says pm contributes nothing of its own, and each gains an exception for a core agent pm registers itself:
  - "pm never names a contributor" (DEC-032:42), and its rationale, "pm stays ignorant of who contributes" (DEC-032:72)
  - "the contributing capability ships that agent", and its `requires_capabilities: project-management`, which pm cannot declare on itself (DEC-032:42)
  - the format reference's "pm ships no reviewer-contribution rules", and its rule pairing a classification predicate (`PM/schemas/review-contributions.yaml:7-12`)
- **The opt-out works unchanged.** An adopter lists `{capability: project-management, reviewer: rules-reviewer, reason}` (DEC-032:105).
- **Deployed with core.** It reads no overlay category, so the deploy never skips it. A project or capability agent of the same name takes its place (`.pkit/adapters/claude-code/deploy-agents.sh:19-21`).
- **The deployed copy is tracked** (`.gitignore:21-22`), so it lands in the change that adds the agent.

| Home | For | Against |
|---|---|---|
| **A core agent that pm registers** (chosen) | Rule sets are core. Any project can run it. One agent serves every kind of artefact. | DEC-032 point 2 is refined in four places. |
| A new capability that ships the agent and its contribution | DEC-032 stays as it is. | A capability for one agent, against COR-007. A core-eligible agent hidden behind an install (COR-014). |
| living-docs | Its agent already judges pages against `LDOC` and a space's rules. | The analysis is another component's, never a page (living-docs DEC-001:36). Project rule sets reach beyond documentation. |
| software-engineering's review panel | The panel's threshold for blocking | Its home is code (software-engineering DEC-002:40). Pages and the analysis are not code. |
| pm ships the agent | One capability does it all. | Judging against rules would then need pm installed. `pm-reviewer`'s remit is pm's conventions. |

- **A core record introduces it.** COR-024 introduced the critic and the architect, and COR-044 introduced `process-author`. This reviewer comes with the refinement of COR-051 in slicing issue 0.
- **Note:** COR-024 rejected one reviewer for two roles, because the roles work at different stages (COR-024:108). It never asked for one reviewer per kind of document. This reviewer keeps one contract, and the rule sets carry what differs between kinds.

### 2. How it finds the rules

From one backbone answer per artefact: the accepted rules that reach it through the scope of a covering set and that set's inheritance.

**The chain, for each artefact the change alters** (part 5 defines "alters"):

1. **The covering sets.** `in_scope_of` names each set whose scope covers the artefact (COR-051 point 2). A component that consumes a set may narrow its reach (COR-051:35).
2. **Inheritance.** Each covering set's `inherits` is followed through every set it pins, and on up (COR-051:70-72).
   - An inherited rule binds within the scope of the set that inherits it (question 1).
3. **Status.** Accepted rules only (COR-051:45-52, `rule_sets.py:234-236`).
   - A superseded or withdrawn rule binds nothing.
   - A successor binds wherever its own set reaches. A sibling set that inherits only the original loses the rule, as COR-051:52 allows.
4. **Fills.** A rule that offers an extension point takes the fill its chain gives, which fills it at most once (COR-051:72).
   - A fill binds only while the rule it fills and the filling rule are both accepted.
   - With no fill, the offering rule's *How* says what applies, as RS-WRITE-002's does (`tech-docs/rule-sets/writing.md:90`).
   - **Two chains, one point.** Two covering sets could fill one point differently for one artefact. COR-051 does not settle that, so validation reports overlapping scopes that do.
5. **A pin behind its set.** Validation fails where the check is enforced (COR-051:75). While it stands, a rule reached through that pin is reported and never blocks.
   - The repository holds only the newer major, and pinning exists so that its rules bind only after a person's review (COR-051:88).

**This reading needs a core record first.** COR-051 does not state steps 1 to 5. The kind note made the same statements on COR-051's behalf, and asked for a refinement later (kind note:224-231).

- **The kind note itself reads reach two ways.** Its rule says the set "that names it" (kind note:229). Its worked case reads a rule's reach from its own set's scope (kind note:471).
- **Under the second reading,** `TECH` would rule nothing, since it holds no rule of its own. `LDOC` would rule no page.
- **So a refinement of COR-051 comes first** (slicing issue 0). Question 1 asks the maintainer to settle reach.

**One home for the walk.** The trigger, the freshness rule and the reviewer ask the same question, so the backbone answers it once.

- **The question:** which artefacts did a change alter between two commits, and which accepted rules reach each? Each computation has one home (ADR-057 point 2).
- **The answer:** one backbone reading command, taking a base and a head.
  - It resolves the base through the backbone's one home for a comparison's base (ADR-057 point 2, COR-054).
  - It compares content as COR-050 point 5 defines it, at both commits.
  - It lists the rules reaching each artefact at each commit, with status, covering set and narrowing.
- **What it costs to build.** The rule-set reader reads only the working tree today (`rule_sets.py:413-436` and `:1424`), so it must learn to read a commit. It imports discovery (`rule_sets.py:65`), so the walk lives beside it, not inside discovery.

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

**Coverage, for pages.** Each space definition takes a root-wide scope, and living-docs narrows its reach to the space's pages (question 3).

- **The scopes:** `TECH` covers `tech-docs/**` and its two out-of-root places. `USER` covers `docs/**` and its out-of-root places.
- **The narrowing,** declared by living-docs as data the backbone applies. A space definition's rules reach only that space's pages, as living-docs DEC-001 point 4 defines a page.
  - A page carries the `reader` and `kind` fields, and no other component claims it (living-docs DEC-001:59).
  - So the 61 decision records, the actors file and the rule sets under `tech-docs/` stay out of `TECH`'s reach.
  - An unclassified document carries neither field, so it stays out too. Onboarding still only reports it (living-docs DEC-001:59).
- **What it realises:** COR-051's "a consuming component may narrow it" (COR-051:35), which nothing implements today.
- **The out-of-root places** still appear in the scopes and in living-docs' assignment (`LD/project/config.yaml:22-44`). Later, living-docs may read a place's space from the scopes and retire its list.
- **Existing adopters:** a definition with no scope covers nothing, which is today's state. Nothing fails on upgrade.

| Route for pages | For | Against |
|---|---|---|
| **Root-wide scopes, narrowed to pages by living-docs** (chosen) | No page listed by hand inside a root. Unclassified documents stay reports. | A refinement of COR-051 point 2, and a declaration living-docs ships |
| Scopes listing each page, checked by living-docs | No new mechanism | It revives every in-root place assigned by hand, which living-docs DEC-001:109 rejected. Unclassified documents would fail. |
| A scope gains exclusions | Short scopes | A schema change. Each new folder of non-pages needs an exclusion. |
| The reviewer reads living-docs' assignment | No data changes. | A core agent would depend on a capability (COR-026). |

### 3. What it judges, and what scripts check

It judges what no check enforces, and leaves to a check whatever part of a rule the check declares it enforces.

- **Checks declare what they enforce.** A validator member names, in its registration, each rule whose part it checks, and the part (slicing issue 2).
  - living-docs' validator would name RS-LDOC-004's structure and RS-LDOC-003's field.
  - Today only prose says so (`LD/agents/living-docs/living-docs.md:94` and `:119`), and a check's summary line cites a rule (COR-051:110).
- **The reviewer runs no check.** The pull request's required checks run them, and a failure there is not the reviewer's finding.
- **A part no check declares** is the reviewer's, even where a script could check it.

| Rule | A check enforces | The reviewer judges |
|---|---|---|
| RS-LDOC-004, pages of a kind follow one format | The sections a kind declares, in order | Nothing more until the rule names where a kind's template is (`[person]`) |
| RS-LDOC-003, each page names its reader | That the `reader` field resolves | Whether the new text suits that reader, as a `[person]` finding |
| RS-LDOC-001, anchors ground every statement | That anchors resolve and friction is answered | Whether some anchor grounds each new statement |
| RS-WRITE-005, at most 25 words a sentence | Nothing yet | Each new sentence, until a lint declares the rule (slicing issue 8) |

**What the change owns,** after software-engineering DEC-002 point 3:

- **Its own text:** what it adds, what it moves or copies, and a break its edit introduces or widens.
- **Not its own:** a break its edit only sits beside. Fixing one word in an old 40-word sentence leaves the length pre-existing, so the finding is advisory.
- **A deletion can break a rule.** A page removed can break the reader paths of RS-USER-001 (`tech-docs/living-docs/rule-sets/user.md:24`).
- **Asserted away.** A pre-existing break blocks when the change claims to have fixed it, as DEC-002 point 3 holds (DEC-002:28-29). A rewrite "to `WRITE`" that leaves a 40-word sentence is an example.
- **Only content.** The friction block sits in the container, which is no part of an artefact's content (COR-050:57).
  - Its answers are a person's decision, never reworded for style (`tech-docs/rule-sets/writing.md:224` and `.pkit/rules/core.md` rule 20). So the reviewer never judges them.

### 4. Its verdict

The merge gate's two values, with each finding citing its rule by id and saying whether it blocks, advises or waits for a person.

**The first line** is the one the invoker names. Under `review-pr` it is `Reviewer agent (local, rules-reviewer): APPROVED` or `CHANGES_REQUESTED` (pm DEC-028:68).

**One bullet per finding,** each holding:

- its tag, from the three below
- the rule's id in its cited form, such as `living-docs:RS-LDOC-003` or `RS-WRITE-005` (`rule_sets.py:354-358`)
- the artefact and the line, with the passage quoted
- what in the passage breaks the rule

**The tags:**

- **`[block]`:** an accepted rule reaches the artefact, the change owns the break, and the rule's statement and *How* settle it with no reading to choose.
  - An example is a semicolon in a new sentence of prose (RS-WRITE-008).
- **`[advisory]`:** a break the change does not own, tagged `[advisory] (pre-existing: <reason>)` as the code-review panel does (`SE/agents/docs-reviewer.md:86`). A rule reached through a pin behind its set is advisory too (part 2).
- **`[person]`:** the rule binds and the change owns the passage. But judging it needs a reading the rule does not settle, or a fact the rule does not name.
  - An example is whether a new paragraph says only what the page's reader needs (RS-LDOC-003).

**The verdict** is `CHANGES_REQUESTED` exactly when any finding is `[block]`.

**A `[person]` finding reaches the person who authorises the merge** (question 4).

- `land-work` prints it with the change's answers, before it stops ready or asks, as it prints answers (pm DEC-055 point 3).
- A merge authorised up front stops ready on it, since no one has seen it.
- Today `land-work` reads only `[block]` and `[advisory]` (`PM/scripts/land-work.py:185-191` and `:821-825`), and a fix round carries blocking findings only (`PM/skills/pm/transition-state.md:56`).

**Meaning is kept** (RS-WRITE-013, `tech-docs/rule-sets/writing.md:219`).

- A fix the reviewer suggests adds, drops, weakens or narrows no claim.
- Where keeping the meaning needs a choice of reading, the finding asks the author instead of offering a rewrite.

**Answers stay a person's** (`.pkit/rules/core.md` rule 20).

- The reviewer writes no revalidation, deferral or `unanchored-because`, and runs no friction writer.
- It judges no answer's wording (part 3).

**Read-only,** as every merge-gate reviewer is. Its working files go in the agent workspace (`SE/agents/docs-reviewer.md:110-112`).

**The same change may get two verdicts.** A reviewer's verdict can differ between runs (DEC-028:169), and the line between `[block]` and `[person]` is the reviewer's call.

- A check that declares a mechanical rule takes it off the reviewer (part 3). The writing lint of slicing issue 8 does that for word counts and semicolons.

### 5. The trigger (#1386)

A new floor kind, `touches-ruled-artefact`, satisfied when the change alters the content of an artefact that an accepted rule reaches.

**What it fires on,** read from the backbone command of part 2:

- **Altered:** an artefact added, removed, or with different content between the base and the head. Content is COR-050's: the body and own fields, nothing in the container (COR-050:57).
  - So a change that only writes a revalidation into a page's friction block does not fire it.
- **Ruled:** at least one accepted rule reaches the artefact, at the base or at the head (part 2).
  - An artefact ruled at the base and removed at the head fires it. So does one ruled only at the head.
- **Not through the not-code list.** The list narrows `touches-code` alone.
  - Today `satisfied_floors` applies it to every floor kind (`required_reviewers.py:604`).
  - An adopter who lists `docs/**` as not code would otherwise drop its pages from rules review.
  - Three records say a path on the list satisfies no floor, and each names the exception: DEC-032:113, DEC-028:209 and the format reference (`PM/schemas/review-contributions.yaml:46-49`).
- **Note:** #1386 says "touches", and "in scope of a rule set with an accepted rule". This note narrows "touches" to "alters the content of", and counts inherited rules as the set's.

**Freshness.** The reviewer is contributed by a floor alone, so its `APPROVED` stays fresh while the author's later changes alter no ruled artefact (DEC-028:201).

- **Today** the freshness rule takes the paths the author changed since the reviewed head. A clean merge of the base adds none (`PM/scripts/_lib/verdict_freshness.py:156-173`).
- **For this floor,** it asks the backbone command which artefacts in those paths differ between the reviewed head and the current head, and whether any is ruled.
- **So** a later push that touches only code, or only a revalidation, keeps the rules reviewer's approval. A clean merge of the base keeps it too, as DEC-028 requires.

**Fail-closed, as the gate already is:**

- **The command fails** at the base or the head, or a commit stays missing after a fetch: the resolution fails with the reason. An unreadable diff fails the same way (`required_reviewers.py:72-78`).
  - A base whose configuration cannot be read blocks the change that repairs it. That change lands through the audited bypass (pm DEC-026).
- **A backbone without the command:** the same failure, naming the backbone needed. pm's changeset declares that backbone (PRJ-002).
- **The reviewer not deployed:** the collection fails for every pull request, not only ruled ones (`required_reviewers.py:454-463`). That is today's rule for any contributed reviewer.
- **No rule carrying the floor:** the command is never run, as a collection with no floor never reads the diff (`required_reviewers.py:569-571`).

**What it costs adopters.**

- **Remote path:** a contributed reviewer is local only (DEC-032:44). A ruled change cannot close without someone running `review-pr`.
- **A stricter gate on upgrade,** wherever a project has a scope over accepted rules. The changeset's segment is a person's judgement (PRJ-002), and slicing issue 5 asks for it.

| Trigger | For | Against |
|---|---|---|
| **A floor on ruled artefacts** (chosen) | It reads the rules' own scopes and statuses. No label escapes it. | One backbone command per resolution, and a new command to build |
| Path globs in each contribution | No read of the backbone | A third copy of each scope. Blind to status and to revalidation-only changes. A capability cannot know a project's paths. |
| A classification match, such as `workstream: docs` | It exists today. | A label escapes it, the gap DEC-032's floor closed (DEC-032:113). |
| The reviewer as a baseline, returning at once when nothing ruled changed | No new floor | A run on every pull request, stale on any change (DEC-028:202) |

### 6. Overlap with the existing reviewers

Each existing reviewer keeps its question, and the rules reviewer takes only the question of the rules.

| Agent | Keeps | Gives to the rules reviewer |
|---|---|---|
| `docs-reviewer` | Docs for new public surface, and a doc that contradicts the code | Nothing now. Its clarity lens is advisory, and project-kit gives it no conventions corpus. |
| `pm-reviewer` | pm's conventions on a pull request | Nothing |
| `methodology-reviewer` | CONTRIBUTING's disciplines on records, while they are authored | Nothing, until those disciplines become a rule set scoped to records |
| `convention-compliance-reviewer` | Commit, branch and surface conventions on a diff | Nothing |
| living-docs' agent | Reader-review of a whole page on request, and friction fixes | Judging a change's own text against a page's rules at the gate |
| `analysis-resolver` | Proposing revalidation outcomes. It is no reviewer. | Nothing |

- **Grounding and truth stay apart.** The rules reviewer asks whether some anchor grounds a new statement (RS-LDOC-001). `docs-reviewer` asks whether the statement matches the code.
  - So one sentence draws two blocks only when it is both ungrounded and false. One fix of the sentence clears both.
- **Reader fit stays reader-review's.** living-docs keeps change review and reader-review apart, since "merging them would blur both" (living-docs DEC-001:100).
  - The rules reviewer reads the diff, so it stays a change review. It asks a reader question only of the change's own text, and only as a `[person]` finding.
  - A sentence in living-docs DEC-001 point 6 can say that a change review includes the rules covering a page (living-docs DEC-001:65-67).
- **Later,** where a page's rules cover its style, `docs-reviewer`'s clarity lens could leave style to the rules reviewer. That refines software-engineering DEC-002.

### 7. Cost

One more reviewer run on each round of a pull request that alters a ruled artefact, and more fix rounds while the rules are new.

- **Runs.** A classified change to documentation draws two reviewers today. With the floor it draws three, and a code change that also edits a ruled page draws five.
- **Rounds.** Each `[block]` costs a fix round. That round re-runs `pm-reviewer` and `docs-reviewer` too, whose approvals go stale on any change (DEC-028:202).
  - After the October fixes, every extra round answered a reviewer's blocking finding, and a change with none landed in one round (review-load note:56).
  - So the first changes that `WRITE` reaches will cost rounds, until their pages keep it.
- **Re-runs of this reviewer stay rare.** A later push that alters no ruled artefact keeps its approval (part 5).
  - A revalidation alone never fires the floor. #1193, a record and one README's revalidation, required two reviewers (review-load note:29), and it would still require two.
- **Prompt size.** The rules of the sets a change reaches, and whatever those rules need read.
  - Today `LDOC` and `USER` hold seven rules in about 120 lines. `WRITE` adds about 250 lines once `TECH` and `USER` inherit it (#1350).
  - Some rules need more than the change. RS-LDOC-001 needs the anchored code and records, and RS-LDOC-002 and RS-USER-001 need the rest of the space.
- **Time.** The artefacts document takes under a second at a commit, measured on `78837af9`. The review's own run dominates.

## Recommendation

Settle the reading of reach in COR-051, then build one core reviewer on one backbone command, tried by hand before the gate requires it.

1. **Reach:** an inherited rule binds within the inheriting set's scope, stated in a refinement of COR-051 (question 1).
2. **The reviewer:** a core agent, `rules-reviewer`, that pm registers with a contribution of its own (part 1).
3. **Its rules:** each altered artefact's accepted rules, from one backbone command (part 2).
4. **Coverage:** the analysis through a scoped `ANALYSIS` now, and pages through root-wide scopes that living-docs narrows to pages (part 2).
5. **Its judgement:** what no check declares it enforces, on what the change owns (part 3).
6. **Its verdict:** `[block]` for a settled break the change owns, and `[advisory]` for one it does not. `[person]` marks a reading the rule does not settle (part 4).
7. **The trigger:** `touches-ruled-artefact`, on content altered at the base or the head, never through the not-code list (part 5).
8. **The rollout:** the agent runs by hand on real changes first, and pm registers it once those reviews show its findings hold (Slicing).

## Questions

One decision each, each with a recommendation.

1. **Does an inherited rule bind within the scope of the set that inherits it?**
   - **(a)** Yes. A set inherits its parents' rules unchanged (COR-051:71), so they bind where the inheriting set's scope reaches.
   - **(b)** No. A rule binds only within its own set's scope, as the kind note's worked case reads it (kind note:471).
   - **Recommendation: (a).** Under (b), `TECH` rules nothing and `LDOC` reaches no page, though living-docs builds each space's definition on `LDOC` (living-docs DEC-001 point 2).
2. **Where does the reviewer live, and who registers it?**
   - **(a)** A core agent, registered by a contribution pm ships, refining DEC-032 point 2.
   - **(b)** A new capability that ships the agent and its contribution.
   - **(c)** living-docs.
   - **Recommendation: (a).** Rule sets are core, and so is judging against them. The registration stays pm's, which owns the gate.
3. **How do pages come under a rule set's scope?**
   - **(a)** Root-wide scopes, which living-docs narrows to each space's pages by data the backbone applies.
   - **(b)** Scopes that list each page, which living-docs checks against its spaces.
   - **(c)** A scope gains exclusions.
   - **Recommendation: (a).** It realises COR-051's narrowing, lists no in-root page by hand, and leaves unclassified documents as reports.
4. **Who sees a finding a person must judge?**
   - **(a)** Whoever reads the verdict. It rides an `APPROVED` and blocks nothing.
   - **(b)** The author. It requests changes until someone overrides the reviewer (pm DEC-050).
   - **(c)** The person who authorises the merge. `land-work` prints it, and a merge authorised up front stops ready on it, as for answers (pm DEC-055 point 3).
   - **Recommendation: (c).** Under (a), no step routes it to anyone. Under (b), a judgement call blocks and trains the override reflex (software-engineering DEC-002:46).

## Slicing

Issues to build, in order. #1385 and #1386 exist already, and the rest are new.

0. **Rule sets: reach, narrowing and review**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** a refinement of COR-051, authored with the decision-author skill. It states:
     - where an inherited rule binds (question 1)
     - how a fill binds, and that two chains may not fill one point for one artefact
     - how a successor and a pin behind its set read
     - how a consuming component narrows a scope, as declared data
     - that a change is reviewed against the accepted rules reaching what it alters, by a reviewer that takes its rules only from the sets
   - **Also:** the kind note's other statements on COR-051's behalf, such as the preview (kind note:224-231).
   - **Depends on:** the maintainer's answers to questions 1 and 3.
1. **The backbone tells which artefacts a change altered, and the rules reaching each**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** one reading command, taking a base and a head. It lists each artefact whose content differs, with the accepted rules reaching it at each commit.
   - **Builds:** the rule-set reader learns to read a commit. The walk lives beside it.
   - **Changeset:** the backbone, `minor`.
   - **Depends on:** 0.
2. **Validators declare the rules they enforce**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** each validator member names the rules whose part it checks, and the part. The command of issue 1 lists them on each rule. living-docs declares its two.
   - **Records:** the validator registry's record, ADR-058, refined.
   - **Changesets:** the backbone `minor`, and living-docs `patch`.
   - **Depends on:** 1.
3. **#1385, first half: the core reviewer, run by hand**
   - **Delivers:** `.pkit/agents/core/rules-reviewer.md`, authored with the agent-author skill, with its deployed copy. A test holds that its body names no rule id.
   - **Tried:** on three real changes, run by hand. One is a change to the analysis, once issue 6 lands.
   - **Docs:** the agents README, and the reviewer table in `CLAUDE.md`.
   - **Changeset:** the backbone `minor`.
   - **Depends on:** 1 and 2.
4. **#1386, the floor `touches-ruled-artefact`**
   - **Delivers:**
     - the new value in the schema's floor enum
     - the resolver reading the command of issue 1
     - the not-code list kept to `touches-code`
     - the freshness rule judged per floor kind, as part 5 says
   - **Tests:**
     - a change inside and outside every scope
     - a set whose rules are all proposed
     - a change that only writes a revalidation
     - a clean merge of the base after an approval
   - **Records:** DEC-032's floor paragraph and DEC-028's freshness and not-code paragraphs name the new kind.
   - **Changeset:** pm `minor`, declaring the backbone of issue 1.
   - **Depends on:** 1.
5. **#1385, second half: pm requires the reviewer**
   - **Delivers:** `PM/review-contributions.yaml`, and `land-work` printing `[person]` findings as question 4 says.
   - **Records:** DEC-032 point 2 in the four places of part 1, and DEC-055 for `[person]` findings.
   - **Changeset:** pm, at the segment the maintainer judges for a stricter gate.
   - **Depends on:** 3's three reviews, and 4.
6. **The analysis comes under a scope**
   - **Delivers:** project-kit's analysis set, with its scope and its inheritance of `WRITE@1`, and no rule of its own yet. The kind note's issue 11 adds its rules later.
   - **Changeset:** none, since the set is project-kit's alone.
   - **Depends on:** the set's name, which the maintainer confirms (kind note:445).
7. **Pages come under their space's scope**
   - **Delivers:** living-docs' narrowing to pages, declared as data. project-kit's `TECH` and `USER` take root-wide scopes in the same change.
   - **Records:** living-docs DEC-001 points 2 and 6.
   - **Changeset:** living-docs `minor`.
   - **Depends on:** 0 and 1.
8. **project-kit's writing lint**
   - **Delivers:** a check of RS-WRITE-005 and RS-WRITE-008 that declares both rules (issue 2). It takes the mechanical rules off the reviewer.
   - **Depends on:** 2. It comes before #1350 brings `WRITE` to every page.

Not filed now:

- **The preview on request** (part 2), once a person asks for one.
- **Rules that name what they need.** RS-LDOC-003 could name the readers point, and RS-LDOC-004 where a kind's template is (part 2). Each is a change to `LDOC`.
- **`docs-reviewer` leaving style to the rules,** once rules cover a page's style (part 6).
- **Whether `ANALYSIS` inherits `SAN`,** so that `SAN`'s judgement parts reach the reviewer. The kind note's issue 11 weighs it.
- **Other fixed prompts.** `pm-reviewer`'s checklist and the review panel's universal criteria are fixed rules too. Whether they move into rule sets is a later question.

## Review

The critic and then the architect reviewed the draft. Each finding, with its answer.

**The critic, on the first draft:**

| Finding | Answer |
|---|---|
| Red flag: how an inherited rule reaches an artefact is contested. The kind note reads it two ways, and no record states it. | Confirmed. A refinement of COR-051 comes first (slicing issue 0), and question 1 asks the maintainer to settle reach. |
| Red flag: a successor in an inheriting set, and a pin behind its set, break the walk. | A successor binds where its own set reaches. A rule reached through a pin behind is advisory (part 2). Issue 0 states both. |
| Red flag: nothing routes a `[person]` finding to a person. | Confirmed. `land-work` prints it, and an up-front authorisation stops ready on it (part 4, question 4). |
| Red flag: listing each page in a scope revives what living-docs DEC-001:109 rejected, and fails unclassified documents. | Adopted the critic's counter: root-wide scopes, narrowed to pages by living-docs as data (part 2, question 3). |
| The freshness claim cannot be built as written. | Defined: artefacts in the author's changed paths that differ between the reviewed head and the current head (part 5). |
| Keeping the not-code list off the new floor changes three records, not one name. | Named: DEC-032:113, DEC-028:209 and the format reference (part 5, issue 4). |
| The rollout's reach is understated. | Named: an undeployed reviewer, a broken base configuration, the remote path, a stricter gate, and the tracked deployed copy (parts 1 and 5). |
| Running the checks at the head has no mechanism. | The reviewer runs no check. Validators declare the rule parts they enforce (part 3, issue 2). |
| Slice 1 is bigger than reusing pin resolution. | Costed: the rule-set reader learns to read a commit, and the walk lives beside it to avoid an import cycle (part 2, issue 1). |
| A core body cannot find a kind's template, nor know which part a check covers, and the readers chain is a guess. | The reviewer judges only with what a rule and the backbone give it. A rule that names nothing it needs yields a `[person]` finding (part 2). |
| The analysis gets nothing. | Issue 6 brings the analysis set forward with its scope and no rules. |
| Two covering sets can fill one point differently. | Validation reports it, and issue 0 states it (part 2). |
| An edited pre-existing break has no rule, and DEC-002's asserted-away clause was dropped. | Defined what the change owns, the clause included (part 3). |
| A new core gate agent has no core record. | Issue 0's refinement introduces it (part 1). |
| DEC-032's refinement is understated. | Listed in four places (part 1). |
| Questions missing: "touches" narrowed, and other fixed prompts. | The narrowing is stated (part 5). Other fixed prompts are a later question ("Not filed now"). |
| Cost leaves out fix rounds, and the reading some rules need | Added (part 7). |
| `[block]` against `[person]` is decided afresh on each run, and `[advisory]` was undefined. | Named, with the writing lint as the mitigation. `[advisory]` now means a break the change does not own (part 4). |
| "Needs no term of the merge gate" is not quite true. | Reworded: the tags are the panel's, and `land-work` must learn `[person]` (part 1). |
| "A place cannot exclude" ignores the narrowing COR-051 already allows | Adopted (part 2). |
| A third kind of review skips living-docs DEC-001:100. | Answered: the rules reviewer stays a change review, and asks a reader question only as a `[person]` finding (part 6). |
| One defect can draw two blocks. | Grounding and truth are kept apart, and one fix clears both (part 6). |
| Counter-alternatives: core refinement first, lint first, advisory first, a middle answer for person findings, one backbone command, narrowing, an analysis stub | All adopted, in issues 0, 8, 3, 5, 1, 7 and 6. |
| Smaller points: a miscited line, an undefined short name, a misquote, a planned set shown as real, the preview's status, and the note's own writing | Corrected. |
