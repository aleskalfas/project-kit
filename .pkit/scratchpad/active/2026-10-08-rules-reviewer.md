---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# One reviewer judges a change against the rules that govern what it touches

A design for #1385, which also designs the merge-gate trigger of #1386. The maintainer asked for both on 8 October, before the rest of the analysis build.

- **Paths:** `PM/` is `.pkit/capabilities/project-management/`, `LD/` is `.pkit/capabilities/living-docs/`, and `SE/` is `.pkit/capabilities/software-engineering/`.
- **Read from main** at commit `78837af9`. Every line number cited here is of that commit.
- **Citations:** by file and line, as the brief for this note asks. RS-WRITE-014, which would drop line numbers, is still proposed and binds nothing.
- **The kind note:** `.pkit/scratchpad/active/2026-10-05-analysis-kind-structure.md`, the design for #1352. This note builds on its reading of scope and its preview.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers "Questions", and the project manager files "Slicing".

## The question

How does one reviewer judge a change against the accepted rules that govern each artefact it touches, and when does the merge gate require it?

- **The maintainer's words, 8 October:** specialised reviewers should not be prompted with fixed rules.
- **What he asked for instead:** one general reviewer that gets the rules governing each changed document. It serves user pages, technical pages and the analysis alike.
- **Why one:** it is "a general mechanism corresponding to the rules general mechanism", that is, to the rule sets of COR-051.
- **It replaces** the separate analysis reviewer and page reviewer proposed earlier on 8 October (#1385, "Related").

## Today

No reviewer at the merge gate reads a rule set, and no rule set in project-kit declares the scope a reviewer would read.

### Who reviews a pull request that changes documentation or the analysis

The gate resolves its reviewers from the closing issue's classification and from whether the diff touches code (project-management DEC-032 point 1).

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
- **The parts of `LDOC` and `USER` that need judgement.** Examples are "every statement is grounded by the page's anchors", "each fact is stated once", and "says only what that reader needs" (`LD/rule-sets/ldoc.md:73-81`).
  - The living-docs agent judges them in a reader-review, and only when someone asks (`LD/agents/living-docs/living-docs.md:38` and `:119`).
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

### 1. Where the reviewer lives

A core agent, `rules-reviewer`, which project-management registers into its merge gate with a new floor (part 5).

**Why core.**

- **Rule sets are core.** COR-051 placed them there because two components and every project need them (COR-051:92).
- **It passes the placement test.** An adopter with no capability installed still finds it useful (COR-026:31). A project with its own rule sets can run it on any diff by hand.
- **Its body names only core things:** rule sets, the artefacts document, an artefact's content (COR-050 point 5), and `pkit connections resolve`.
- **It needs no term of the merge gate.** `review-pr` already puts the verdict grammar into every reviewer's brief (`PM/scripts/review-pr.py:711-747`). It stamps the verdict marker when it posts (`SE/agents/docs-reviewer.md:94`).
  - So the body says only this. When the invoker asks for a verdict line, the reviewer gives it in the form named, blocking whenever any finding blocks.

**Who registers it.** project-management ships a contribution that names the core agent.

- **Core cannot register a reviewer itself.** pm's collector walks the capabilities in the manifest, and core is none of them (`PM/scripts/_lib/review_contributions.py:574-589` and DEC-032:40).
- **The contribution:** `PM/review-contributions.yaml`, one rule, `floor: touches-ruled-artefact` with `reviewer: rules-reviewer`.
- **No layer breaks.** pm depends on core, so pm naming a core agent is a dependency it already has.
- **DEC-032 point 2 needs a refinement.** It says "the contributing capability ships that agent" (DEC-032:42), and it gains "or names a core agent".
  - The format reference says that pm ships no contribution of its own (`PM/schemas/review-contributions.yaml:7-8`). That line changes with it.
- **The opt-out works unchanged.** An adopter lists `{capability: project-management, reviewer: rules-reviewer, reason}` (DEC-032:105).
- **It is always deployed.** It reads no overlay category, so the deploy never skips it. An undeployed reviewer still stays visible and unsatisfied (`review_contributions.py:610-627`).

| Home | For | Against |
|---|---|---|
| **A core agent that pm registers** (chosen) | Rule sets are core. Any project can run it. One agent serves every kind of artefact. | A refinement of DEC-032 point 2 |
| A new capability that ships the agent and its contribution | DEC-032 stays as it is. | A capability for one agent, against COR-007. A core-eligible agent hidden behind an install (COR-014). |
| living-docs | Its agent already judges pages against `LDOC` and a space's rules. | The analysis is another component's, never a page (living-docs DEC-001:36). Project rule sets reach beyond documentation. |
| software-engineering's review panel | The panel's threshold for blocking | Its home is code (software-engineering DEC-002:40). Pages and the analysis are not code. |
| project-management ships the agent | One capability does it all. | Judging against rules would then need pm installed. `pm-reviewer`'s remit is pm's conventions. |

- **Note:** COR-024 split the critic from the architect because the two work at different stages (COR-024:100). It never asked for one reviewer per kind of document. This reviewer keeps one contract, and the rule sets carry what differs between kinds.

### 2. How it finds the rules

From one backbone answer per artefact: the rules that reach it through the scope of a covering set and that set's inheritance.

**The chain, for each artefact the change alters** (part 5 defines "alters"):

1. **The artefact.** The reviewer reads the artefacts document at the base and at the head, `pkit friction artefacts --json --at <rev>` (ADR-057 point 1).
   - For a collection file, an entry's span (`friction_discovery.py:2700-2702`) narrows the review to the entries the diff touches.
2. **The covering sets.** `in_scope_of` names each set whose scope covers the artefact (COR-051 point 2).
3. **Inheritance.** Each covering set's `inherits` is followed through every set it pins, and on up (COR-051:70-72).
   - An inherited rule reaches only as far as the scope of the set that names it. The kind note states this reading (kind note:229).
4. **Status.** Accepted rules only (COR-051:45-52, `rule_sets.py:234-236`). A superseded or withdrawn rule binds nothing, and its successor binds in its place.
5. **Fills.** A rule that offers an extension point takes the fill its chain gives, which fills it at most once (COR-051:72).
   - A fill binds only while the rule it fills and the filling rule are both accepted.
   - With no fill, the offering rule's *How* says what applies, as RS-WRITE-002's does (`tech-docs/rule-sets/writing.md:90`).
6. **A pin behind its set.** The repository holds one version of each set. A pin behind it is validation's finding (COR-051:75), so the reviewer reads the set as the repository holds it.

**One home for the walk.** The trigger and the reviewer ask the same question, so the backbone answers it once.

- **The question:** which accepted rules reach this artefact? Each computation has one home (ADR-057 point 2).
- **The answer:** the artefacts document gains a key on each artefact. It lists each rule that reaches the artefact, with the rule's status and the covering set it comes through.
  - A key added raises no version of the document (`friction_discovery.py:2612-2613`).
  - The walk reuses the rule-set reader's pin resolution (`rule_sets.py:1424`), so a pin resolves one way.
- **Without it:** pm would copy pin resolution into its resolver, and the reviewer would walk the chain by reading files.

**Proposed rules bind nothing** (COR-051:46).

- **At the gate:** the reviewer reports nothing under a proposed rule.
- **On request:** a preview treats every proposed rule in the chain as accepted, and lists what would break. It never blocks.
  - That is the maintainer's answer for `pkit analysis validate --preview` (kind note:27, "Decided 4"). The reviewer follows the same habit.
  - A preview is a run a person asks for by invoking the agent, never a gate run.

**Facts a rule needs about the artefact.** Some rules need more than the text, and the reviewer reaches them through core commands.

- **The example:** RS-LDOC-003 needs the page's reader and what that reader needs (`LD/rule-sets/ldoc.md:81`).
- **The field:** from the artefact's own front matter, which the document gives as `fields`.
- **What the reader needs:** from the data point that the rule's origin decision names, resolved with `pkit connections resolve`.
  - RS-LDOC-003's origin is living-docs DEC-001, whose point 7 names the readers point (living-docs DEC-001:70).
- **A fact it cannot reach** makes the finding a person's call (part 4). It is never passed in silence.

**Coverage, for pages.** Each space's definition declares its scope, and living-docs checks that the scope agrees with the space (question 2).

- **Both directions:** every page of the space lies in its definition's scope, and the scope covers no artefact that is not a page of that space.
- **Why both.** A scope is places, and a place cannot exclude. A `TECH` scope of `tech-docs/**` would also cover 61 decision records, the actors file and two rule sets (`pkit validate`, living-docs' summary).
  - So `TECH`'s scope is `CONTRIBUTING.md` and `.pkit/release/README.md` today.
  - `USER`'s scope is `docs/**`, `README.md` and the 19 READMEs under `.pkit/` that its space holds.
- **The cost:** the page list is written twice, in the friction places and in the scopes. The check keeps the two in step.
- **Later:** living-docs may read a place's space from the scopes, and retire its own assignment list (`LD/project/config.yaml:22-44`).

**Coverage, for the analysis.** It comes with project-kit's planned set `ANALYSIS`.

- **The set:** scope `tech-docs/analysis/**`, inheriting `WRITE@1` (kind note:434-435, its issue 11).
- **A method set with no scope,** such as software-analysis's `SAN`, reaches the reviewer only through a set that inherits it.
  - In the kind note's design, `ANALYSIS` does not inherit `SAN` (kind note:435). So `SAN`'s judgement parts would reach no reviewer.
  - Issue 11 of the kind note can weigh that again (Slicing, "Not filed now").

| Route for pages | For | Against |
|---|---|---|
| **Definitions declare a scope, and living-docs checks it** (chosen) | One coverage answer, in the backbone, readable at any commit with `--at` | The page list is written twice. |
| living-docs fills a backbone point of coverage | No second list | A refinement of COR-051 point 2, and a filler command run at both the base and the head |
| The reviewer reads living-docs' assignment of places | No data changes. | A core agent would depend on a capability (COR-026). It serves no other component. |
| A scope gains exclusions | Short scopes | A schema change. A scope can still drift from its space. |

### 3. What it judges, and what scripts check

It judges only what no check reports, and it repeats no check's finding.

- **It runs the checks first.** `pkit validate` and `pkit friction check --json` run at the head. A finding they report stays theirs.
  - The reviewer may name a failing check in one line, never as a finding of its own.
- **A check that enforces a rule cites it** (COR-051:110). living-docs' summary does, as "page formats (RS-LDOC-004, accepted)". The reviewer leaves to the check the part of the rule the check judges.
- **The living-docs agent already draws this line** (`LD/agents/living-docs/living-docs.md:94` and `:119`). This reviewer draws it for every rule set.

| Rule | A script checks | The reviewer judges |
|---|---|---|
| RS-LDOC-004, pages of a kind follow one format | The sections a kind declares, in order | Whether each section says what its template asks |
| RS-LDOC-003, each page names its reader | That the `reader` field resolves | Whether the change says only what that reader needs |
| RS-LDOC-001, anchors ground every statement | That anchors resolve and friction is answered | Whether the anchors ground each new statement |
| RS-WRITE-005, at most 25 words a sentence | Nothing yet | Each new sentence, until a lint takes the rule |

**What "the change" means.** The text the change adds or edits, and whatever its edit newly breaks.

- **A deletion can break a rule.** A page removed can break the reader paths of RS-USER-001 (`tech-docs/living-docs/rule-sets/user.md:24`).
- **Text the change leaves alone** draws only advisory findings, as in software-engineering DEC-002 point 3.
- **Only content.** The friction block sits in the container, which is no part of an artefact's content (COR-050:57).
  - Its answers are a person's decision, and never reworded for style (`tech-docs/rule-sets/writing.md:224` and `.pkit/rules/core.md` rule 20). So the reviewer never judges them.

### 4. Its verdict

The merge gate's two values, with each finding citing its rule by id and saying whether it blocks, advises or waits for a person.

**The first line** is the one the invoker names. Under `review-pr` it is `Reviewer agent (local, rules-reviewer): APPROVED` or `CHANGES_REQUESTED` (project-management DEC-028:68).

**One bullet per finding,** each holding:

- its tag, from the three below
- the rule's id in its cited form, such as `living-docs:RS-LDOC-003` or `RS-WRITE-005` (`rule_sets.py:354-358`)
- the artefact and the line, with the passage quoted
- what in the passage breaks the rule

**The tags:**

- **`[block]`:** an accepted rule reaches the artefact, the break is in the change's own text, and the rule settles it with no reading to choose.
  - An example is a semicolon in a new sentence of prose (RS-WRITE-008).
- **`[advisory]`:** a softer finding. A finding in text the change left alone is `[advisory] (pre-existing: <reason>)`, as the code-review panel tags it (`SE/agents/docs-reviewer.md:86`).
- **`[person]`:** the rule binds, but judging it needs a reading the rule does not settle, or a fact the reviewer cannot reach.
  - An example is whether a new paragraph says only what the page's reader needs (RS-LDOC-003).
  - It does not block (question 3). It rides an `APPROVED`, and the person who authorises the merge reads it.

**The verdict** is `CHANGES_REQUESTED` exactly when any finding is `[block]`.

**Meaning is kept** (RS-WRITE-013, `tech-docs/rule-sets/writing.md:219`).

- A fix the reviewer suggests adds, drops, weakens or narrows no claim.
- Where keeping the meaning needs a choice of reading, the finding asks the author instead of offering a rewrite.

**Answers stay a person's** (`.pkit/rules/core.md` rule 20).

- The reviewer writes no revalidation, deferral or `unanchored-because`, and runs no friction writer.
- It judges no answer's wording (part 3).

**Read-only,** as every reviewer is. Its working files go in the agent workspace (`SE/agents/docs-reviewer.md:110-112`).

### 5. The trigger (#1386)

A new floor kind, `touches-ruled-artefact`, satisfied when the change alters the content of an artefact that an accepted rule reaches.

**What it fires on:**

- **Which artefacts:** every artefact in a file the diff changes, read at the base and at the head.
- **Altered:** added, removed, or with different content. Content is COR-050's: the body and the artefact's own fields, nothing in the container (COR-050:57).
  - So a change that only writes a revalidation into a page's friction block does not fire it.
  - The artefacts document gains each artefact's content digest, so pm compares the base and the head by the backbone's own reading.
- **Ruled:** at least one accepted rule reaches the artefact, in the state where it is read (part 2).
  - The covering set's own rules and its inherited ones both count. `TECH` has no rule of its own, and its pages are ruled through `LDOC`.
  - #1386 says "in scope of a rule set with an accepted rule", and this note reads it so.
- **Both states count.** An artefact ruled at the base and removed at the head fires it. So does one ruled only at the head.
- **Not through the not-code list.** The list narrows `touches-code` alone.
  - Today `satisfied_floors` applies it to every floor kind (`required_reviewers.py:604`).
  - An adopter who lists `docs/**` as not code would otherwise drop its pages from rules review.

**Freshness.** The reviewer is contributed by a floor alone, so its `APPROVED` stays fresh while later changes alter no ruled artefact (DEC-028:201).

- The freshness rule reads the floor through the same two-state reading, without the not-code list (`verdict_freshness.py:20-28`).
- So a later push that touches only code, or only a revalidation, keeps the rules reviewer's approval.

**Fail-closed, as the gate already is:**

- **The document unreadable** at the base or the head, or a commit still missing after a fetch: the resolution fails with the reason. An unreadable diff fails the same way (`required_reviewers.py:72-78`).
- **A backbone without the new keys:** the same failure, naming the backbone needed. pm's changeset declares that backbone (PRJ-002).
- **The reviewer not deployed:** kept visible and unsatisfied (`review_contributions.py:610-627`).
- **No rule carrying the floor:** the document is never read, as a collection with no floor never reads the diff (`required_reviewers.py:569-571`).

| Trigger | For | Against |
|---|---|---|
| **A floor on ruled artefacts** (chosen) | It reads the rules' own scopes and statuses. No label escapes it. | Two reads of the artefacts document per resolution |
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
| living-docs' agent | Reader-review of a whole page on request, and friction fixes | Judging a change's text against a page's rules at the gate |
| `analysis-resolver` | Proposing revalidation outcomes. It is no reviewer. | Nothing |

- **One passage can draw two findings.** A sentence that contradicts the code is `docs-reviewer`'s. If it is also ungrounded, RS-LDOC-001 is the rules reviewer's. They answer different questions.
- **Later,** where a page's rules cover its style, `docs-reviewer`'s clarity lens could leave style to the rules reviewer. That refines software-engineering DEC-002, and waits until rules cover style.
- **Note:** living-docs DEC-001 point 6 names two reviews, change review and reader-review (living-docs DEC-001:65-67). A change judged against its rules is a third. A sentence in point 6 can say so.

### 7. Cost

One more reviewer run on each round of a pull request that alters a ruled artefact. The prompt holds the rules of the sets the change reaches.

- **Runs.** A classified change to documentation draws two reviewers today. With the floor it draws three, and a code change that also edits a ruled README draws five.
- **Re-runs stay rare.** A later push that alters no ruled artefact keeps the approval (part 5).
  - A revalidation alone never fires the floor. #1193, a record and one README's revalidation, required two reviewers (review-load note:29), and it would still require two.
- **Prompt size.** Only the sets a change reaches, and only their accepted rules, which each rule's span lets it read.
  - Today `LDOC` and `USER` hold seven rules in about 120 lines.
  - `WRITE` adds about 250 lines once `TECH` and `USER` inherit it (#1350).
- **Many rules.** The cost grows with the distinct sets a change reaches, not with the artefacts it alters. A change across both spaces and the analysis reaches five sets.
- **Time.** The artefacts document takes under a second at a commit, and `pkit validate` about 12 seconds (measured on `78837af9`). The review's own run dominates.

## Recommendation

Build one core reviewer, required by a new floor, on one backbone answer.

1. **The reviewer:** a core agent, `rules-reviewer`, that pm registers with a contribution of its own (part 1).
2. **Its rules:** each altered artefact's accepted rules, from the scope of its covering sets and their inheritance, as the artefacts document lists them (part 2).
3. **Coverage:** space definitions declare a scope, and living-docs checks that it agrees with the space. The analysis follows with `ANALYSIS` (part 2).
4. **Its judgement:** only what no check reports, on the change's own content (part 3).
5. **Its verdict:** `[block]` for a settled break of an accepted rule, `[advisory]` otherwise, and `[person]` for a reading the rule does not settle (part 4).
6. **The trigger:** `touches-ruled-artefact`, on content altered at the base or the head, never through the not-code list (part 5).

## Questions

One decision each, each with a recommendation.

1. **Where does the reviewer live, and who registers it?**
   - **(a)** A core agent, registered by a contribution pm ships, refining DEC-032 point 2.
   - **(b)** A new capability that ships the agent and its contribution.
   - **(c)** living-docs.
   - **Recommendation: (a).** Rule sets are core, and so is judging against them. The registration stays pm's, which owns the gate.
2. **How do pages come under a rule set's scope?**
   - **(a)** Each space definition declares its scope, and living-docs' validation checks it against the space.
   - **(b)** living-docs fills a backbone point of coverage, refining COR-051 point 2.
   - **(c)** A scope gains exclusions.
   - **Recommendation: (a).** Coverage stays one backbone answer, readable at any commit. The check keeps the second list honest.
3. **Does a finding a person must judge block the merge?**
   - **(a)** No. It rides an `APPROVED`, tagged `[person]`, for whoever authorises the merge.
   - **(b)** Yes. It requests changes until the person overrides the reviewer, as project-management DEC-050 allows.
   - **Recommendation: (a).** A judgement call that blocks trains the override reflex, as software-engineering DEC-002's rationale warns (DEC-002:46).

## Slicing

Issues to build, in order. #1385 and #1386 exist already, and the rest are new.

1. **The artefacts document gives each artefact's rules and its content digest**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** two keys on each artefact in `pkit friction artefacts --json`. One lists each rule that reaches it, with status and covering set. The other is a digest of its content as COR-050 point 5 defines it.
   - **Records:** none changed. It applies COR-050, COR-051 point 2 and ADR-057 points 1 and 2. The backbone takes a `minor` changeset.
   - **Depends on:** nothing.
2. **#1386, the floor `touches-ruled-artefact`**
   - **Delivers:**
     - the new value in the schema's floor enum
     - the resolver reading the document at the base and the head
     - the not-code list kept to `touches-code`
     - the freshness rule judged per floor kind
   - **Tests:** a change inside and outside every scope, a set whose rules are all proposed, and a change that only writes a revalidation.
   - **Records:** DEC-032's floor paragraph names the new kind, and DEC-028's freshness paragraph names it beside `touches-code`.
   - **Changeset:** project-management `minor`, declaring the backbone of issue 1.
   - **Depends on:** 1.
3. **#1385, the core reviewer and pm's contribution**
   - **Delivers:** `.pkit/agents/core/rules-reviewer.md`, authored with the agent-author skill, and `PM/review-contributions.yaml`. A test holds that the body names no rule id. The agents README and pm's README describe both.
   - **Records:** DEC-032 point 2 refined for a core agent (question 1).
   - **Changesets:** the backbone `minor`, for the core agent, and project-management `minor`.
   - **Depends on:** 2, and the maintainer's answers.
4. **Space definitions declare their scope, and living-docs checks it**
   - **Type:** Task, parent EPIC #234.
   - **Delivers:** the check in both directions, and project-kit's scopes for `TECH` and `USER` in the same change, so validation never fails between them.
   - **Records:** living-docs DEC-001 point 2 says a definition's scope agrees with its space. Point 6 names the third review (part 6).
   - **Changeset:** living-docs `minor`.
   - **Depends on:** the maintainer's answer to question 2. It can land beside 1 to 3.
5. **The first real review**
   - **Delivers:** #1385's last criterion, on the first change to a page after issues 3 and 4 land. One of #1350's page rewrites would do.
   - **Depends on:** 3 and 4.

Not filed now:

- **`ANALYSIS`, the kind note's issue 11,** gains its scope there. It can weigh whether `ANALYSIS` inherits `SAN`, so that `SAN`'s judgement parts reach the reviewer.
- **The preview on request** (part 2), once a person asks for one.
- **`docs-reviewer` leaving style to the rules,** once rules cover a page's style (part 6).

## Review

The critic and then the architect reviewed the draft. Each finding, with its answer.
