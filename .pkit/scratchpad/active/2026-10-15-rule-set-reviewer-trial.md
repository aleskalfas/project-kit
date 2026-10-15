---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-15
---

# The rule-set reviewer's trial on ten real changes

The rule-set reviewer was run by hand on ten merged changes, and this note records how it judged them (#1418). It is the trial of the design's slicing issue 8 (#1396, PR #1390). COR-057 point 8 asks for this evidence before a component contributes the reviewer to a gate.

- **The threshold:** at most one wrong `[block]` across the ten. The gate's contribution (#1420) waits on it.
- **What the maintainer does:** he says, for each `[block]` in "The blocks" below, whether he agrees that the passage breaks the rule. He answers through the project manager, in the table's last column.
- **Where the trial stands:** the ten reviews are done, and the maintainer's answers are open. The threshold is judged once he has answered, so this note stays in `active/`.
- **Outcome:** 27 `[block]`, 32 `[person]` and 6 `[info]`. The reviewer withheld approval of seven changes and approved three.

## Set-up

Each change was reviewed once, at its own commits, by a reviewer dispatched with no `name`.

- **The reviewer:** `.pkit/agents/core/rule-set-reviewer.md` as commit c9315252 added it (#1385, PR #1558). Its text is unchanged on main through e6ae6e87, and the deployed copy that ran matched it.
  - **Note:** this evidence is for that text. #1560 will revise COR-057 point 2 and the reviewer. If it lands before #1420, the gate gets a reviewer this trial did not try.
- **The answer it read:** `pkit rule-sets altered --base <base> --head <merge> --json`, run from the backbone at e6ae6e87. The command reads the rules at each change's own base and head.
- **The change:** the base is the commit the squash merge landed on, and the head is the merge commit. So the diff is exactly what landed. A pull request's own recorded base can be older. #1573 recorded 48174bcc and landed on 5cf698a3, for example.
- **The description:** the reviewer read each pull request's body and squash message. COR-057 point 2 needs them for a break a change says it fixes.
- **The form,** as COR-057 point 3 lets the invoker name it:
  - the verdict on one line, `VERDICT: APPROVE` or `VERDICT: WITHHOLD`
  - `[block]` for a settled break
  - `[person]` for a passage for a person
  - `[info]` for a finding that informs
- **What the brief added:** the worktree to run in, and the folder for working files. It gave no rule and no hint of what to look for.
- **The cost:** each run took 6 to 12.5 minutes and 100,000 to 210,000 tokens.

### What the rules reached

Pages and the analysis came under different rules in these changes.

- **A page in the user space** (`USER`): `living-docs:RS-LDOC-001` to `RS-LDOC-006` and `RS-USER-001`.
- **A page in the technical space** (`TECH`): `living-docs:RS-LDOC-001` to `RS-LDOC-006`. `CONTRIBUTING.md` and the release README were the only ones.
- **An analysis artefact** (`ANA`, which inherits `WRITE`): `RS-WRITE-001`, `003`, `004`, `005`, `007`, `008`, `009`, `010`, `011` and `013`.
- **Left to checks:** the prose lint holds the checked parts of `RS-WRITE-005` and `RS-WRITE-008`. `living-docs:validate` holds the `reader` field of `RS-LDOC-003` and the sections of `RS-LDOC-004`. The answer said each check was there, and no run judged those parts.
- **Not reached:** `WRITE` does not reach pages until #1350, so no page was judged under it.
- **Note:** a change that brings a page under a rule without editing it is outside this trial. That case waits for #1560, which is not built yet.

## The changes

The candidates were the 24 changes merged to main after both #1413 and #1415, the first-parent commits after e9265a16. For 21 of them `pkit rule-sets altered` named at least one accepted rule that binds.

### Picked, and why

The ten cover both spaces, the analysis, and changes of very different size.

| Pull request | Merged as | Why |
|---|---|---|
| #1545 | 0c4be88f | A new command's section in the decisions README, and `CONTRIBUTING.md` in the technical space |
| #1558 | c9315252 | One of the two changes that alter the analysis, one line of `ACT-ai-agent`, beside five pages. It is also the reviewer's own change. |
| #1554 | 9cbc06ac | A change to where `LDOC` binds, to see whether the reviewer treats it as a rule the change moves |
| #1553 | 8d74aca4 | One page with a new section on the gate this reviewer would serve |
| #1568 | 3f72064f | The release README, a technical page under a `.pkit/` path, beside two user pages |
| #1571 | 48174bcc | Six pages in both spaces, the widest spread |
| #1574 | 5cf698a3 | The most text added to pages, and the top-level README |
| #1573 | e535788b | The analysis: eight actors moved to files of their own, with edits to their terms |
| #1569 | bdfe42e6 | 52 altered artefacts, of which 48 ADRs that no rule binds, to see that the reviewer leaves those alone |
| #1578 | ff5918c8 | One page with much new text |

### Looked at and passed over

Fourteen changes were passed over.

- **No accepted rule binds on what they alter:**
  - #1527 (dd277081): it adds ADR-065.
  - #1555 (5161d741): it alters no artefact.
  - #1561 (ce1b1a6f): it changes ADR-058.
- **Little added text:**
  - #1549 (00a30be7): three pages, mostly rewording.
  - #1550 (3a54999e): two lines of the CLI reference.
  - #1556 (0f456b6a): seven lines on two pages.
  - #1564 (f89a1770): fourteen lines of the CLI reference.
- **Pages the picked changes already cover:**
  - #1541 (461b409e): the decisions README and the CLI reference, as in #1545.
  - #1563 (e6755d2b): `CONTRIBUTING.md`, as in #1545 and #1571.
  - #1566 (baa40bc9): the CLI and lifecycle READMEs.
  - #1575 (2e147b45): the same two and `CONTRIBUTING.md`, mostly rewording.
  - #1576 (68ace525): the software-analysis README. Its new rule, RS-SAN-001, is a rule-set entry that no rule binds.
  - #1580 (5942f925): the CLI and lifecycle READMEs.
  - #1581 (e6ae6e87): the software-analysis README.

## Summary

In the table, LDOC is `living-docs:RS-LDOC-001` to `006`, and WRITE is `WRITE`'s ten accepted rules.

| Change | Rules bound | Verdict | `[block]` | `[person]` | `[info]` |
|---|---|---|---|---|---|
| #1545 | LDOC, RS-USER-001 | WITHHOLD | 2 | 3 | 2 |
| #1558 | LDOC, RS-USER-001, WRITE | WITHHOLD | 1 | 4 | 0 |
| #1554 | LDOC, RS-USER-001 | APPROVE | 0 | 3 | 0 |
| #1553 | LDOC, RS-USER-001 | WITHHOLD | 2 | 3 | 1 |
| #1568 | LDOC, RS-USER-001 | WITHHOLD | 6 | 4 | 1 |
| #1571 | LDOC, RS-USER-001 | WITHHOLD | 8 | 2 | 1 |
| #1574 | LDOC, RS-USER-001 | WITHHOLD | 6 | 3 | 1 |
| #1573 | LDOC, RS-USER-001, WRITE | APPROVE | 0 | 3 | 0 |
| #1569 | LDOC, RS-USER-001 | APPROVE | 0 | 3 | 0 |
| #1578 | LDOC, RS-USER-001 | WITHHOLD | 2 | 4 | 0 |
| **All ten** | | 7 WITHHOLD | **27** | **32** | **6** |

## The reviews

Each review lists the commits, the altered artefacts with the rules that bound, the verdict, and each finding in one line. A line number is at the head unless it says otherwise.

### #1545: decisions check-diff

- **Commits:** base 461b409e, merged as 0c4be88f. The pull request's head was d0f4088a.
- **Altered:** `CONTRIBUTING.md` (TECH), the CLI reference and the decisions README (USER). `README.md` and `.pkit/README.md` changed only in their container, so they were not listed.
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B1, RS-LDOC-002: the CLI row for `decisions check-diff` and the decisions README's new section give the same lists of what fails or warns.
  - `[block]` B2, RS-LDOC-002: how the command's base resolves is stated in the row, in the decisions README, and in the CLI reference's list of comparisons.
  - `[person]` RS-LDOC-002: `CONTRIBUTING.md` glosses what the check catches without a link.
  - `[person]` RS-LDOC-001: the CLI row states the module's detail and cites COR-058, which is not among the page's anchors.
  - `[person]` RS-LDOC-001: the decisions README's section applies COR-058, which is not among its anchors.
  - `[info]` RS-LDOC-002: the `decisions validate` row already repeated the README's lists at the base.
  - `[info]` RS-LDOC-001: both pages already cited COR-058 without anchoring it at the base.

### #1558: the rule-set reviewer

- **Commits:** base 0f456b6a, merged as c9315252. The pull request's head was d22574f9.
- **Altered:** the agents, software-engineering, CLI, lifecycle and schemas READMEs (USER), and the actor `ACT-ai-agent` in `actors.md` (WRITE). ADR-057 was altered, and no rule binds on it.
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B3, RS-LDOC-001: "Exit `0` when answered, with no artefact when no rule binds" is no longer true.
  - `[person]` RS-LDOC-002: the CLI reference lists which artefacts `reach` lists in three places.
  - `[person]` RS-LDOC-002: the lifecycle README's row for `reach --json` summarises keys the CLI reference states, beside a link.
  - `[person]` RS-LDOC-002: the schemas README restates the `checks` and `held` keys.
  - `[person]` RS-LDOC-001: the schemas README says a held-back rule is named as held, which does not hold for a rule that fills.
  - No finding on `ACT-ai-agent`, whose one edit adds an agent's name to a list.

### #1554: LDOC binds only through scoped spaces

- **Commits:** base c9315252, merged as 9cbc06ac. The pull request's head was 8cc135b4.
- **Altered:** the living-docs README (USER). The change edits `ldoc.md` and `user.md` outside any status, scope or pin, and the reviewer found that it moves no rule.
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-LDOC-001: lines 26, 123 and 166 can be read to make a space's definition LDOC's only route. That says more than the anchors do.
  - `[person]` RS-LDOC-001: line 166 says a page a scope leaves out is "never failed", and the anchored validator fails some.
  - `[person]` RS-LDOC-002: line 123 applies to LDOC what the schemas README states for every method rule set.

### #1553: the ruled-artefact floor

- **Commits:** base baa40bc9, merged as 8d74aca4. The pull request's head was 98d3ae65.
- **Altered:** the project-management README (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B4, RS-LDOC-002: that the not-code list narrows only the code floor is said three times on the page.
  - `[block]` B5, RS-LDOC-002: the bullet "What a rule change does not re-open" repeats three facts of the new section's bullets.
  - `[person]` RS-LDOC-001: the page says without exception that a change to rules alone fires no floor, and DEC-032 and DEC-028 name an exception.
  - `[person]` RS-LDOC-001: "fixes those" may claim a remedy for a failing command that no anchor gives.
  - `[person]` RS-LDOC-002: a reason clause recalls a fact stated two bullets earlier.
  - `[info]` RS-LDOC-002: the code floor's surviving approval was stated twice at the base.

### #1568: an upgrade records its target first and its completion last

- **Commits:** base 8d74aca4, merged as 3f72064f. The pull request's head was fe5258ef.
- **Altered:** the release README (TECH), the CLI and lifecycle READMEs (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B6, RS-LDOC-002: the order of the two recorded states is stated in the CLI and lifecycle READMEs.
  - `[block]` B7, RS-LDOC-002: how the next upgrade finishes an interrupted one, and the rollback, are stated on both.
  - `[block]` B8, RS-LDOC-002: the replay is stated on both.
  - `[block]` B9, RS-LDOC-002: what a transition records for an adapter is stated on both.
  - `[block]` B10, RS-LDOC-002: when an upgrade is already current is stated on both.
  - `[block]` B11, RS-LDOC-002: the release step's write of `completed_version` is stated in the release README and the lifecycle README.
  - `[person]` RS-LDOC-002: the `new migration` sentence restates the script contract it points to.
  - `[person]` RS-LDOC-002: the release README's new section gives the replay as context beside a pointer.
  - `[person]` RS-LDOC-002: the change adds one clause to both copies of two refusals that both pages stated before.
  - `[person]` RS-LDOC-003: passages on the methodology's own repository sit on pages written for `user`.
  - `[info]` RS-LDOC-001: an older sentence on the order of migrations and sync no longer matches the code.

### #1571: sync works at the project's own version

- **Commits:** base 3f72064f, merged as 48174bcc. The pull request's head was 7042103f.
- **Altered:** `CONTRIBUTING.md` (TECH), the agents, project-management, CLI, decisions and lifecycle READMEs (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B12, RS-LDOC-002: sync's guard is stated on four pages.
  - `[block]` B13, RS-LDOC-002: what sync writes, and what it does not, is stated in the decisions and CLI READMEs. The decisions README repeats part twice more.
  - `[block]` B14, RS-LDOC-002: how sync treats a capability by its version, and `--force` ignored, are stated in the CLI and lifecycle READMEs.
  - `[block]` B15, RS-LDOC-002: what `pkit upgrade` does with each capability is stated in the CLI README and three times in the lifecycle README.
  - `[block]` B16, RS-LDOC-002: the seed paths are listed three times in the CLI README and again on two pages.
  - `[block]` B17, RS-LDOC-002: that `pkit agents reconcile --write` repairs a missing overlay is stated on three pages.
  - `[block]` B18, RS-LDOC-001: the decisions README's new statements on sync and the seed paths rest on nothing the page anchors.
  - `[block]` B19, RS-LDOC-001: the lifecycle README's "Seed paths" paragraph rests partly on code the page does not anchor.
  - `[person]` RS-USER-001: the agents README's first link into `tech-docs/` points at nothing in an adopter's copy.
  - `[person]` RS-LDOC-003: the lifecycle README gains the methodology's build plan, as issue numbers.
  - `[info]` RS-LDOC-002: the CLI `upgrade` entry already restated two lifecycle sections at the base.

### #1574: an upgrade runs its migrations in COR-010's order

- **Commits:** base 48174bcc, merged as 5cf698a3. The pull request's head was 81825009.
- **Altered:** `README.md`, the CLI and lifecycle READMEs (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B20, RS-LDOC-002: the transition's order and what its steps do are stated in the CLI and lifecycle READMEs.
  - `[block]` B21, RS-LDOC-002: a new collision and how it is settled are stated twice in the CLI README, and once in the lifecycle README.
  - `[block]` B22, RS-LDOC-002: the dependency gates and what `--force` overrides are stated on both pages.
  - `[block]` B23, RS-LDOC-002: what the report and the dry run show is stated on both pages.
  - `[block]` B24, RS-LDOC-002: `pkit capabilities upgrade`'s five steps are stated on both pages.
  - `[block]` B25, RS-LDOC-001: "A release's changelog names each widening too" rests on nothing the page anchors.
  - `[person]` RS-LDOC-002: the top-level README's collision promise restates the other pages without a link.
  - `[person]` RS-LDOC-003: a source function's name and issue numbers on pages written for `user`.
  - `[person]` RS-LDOC-001: new passages apply ADR-065 and records that the pages do not anchor, through code they do.
  - `[info]` RS-LDOC-002: the CLI `upgrade` entry already restated the lifecycle README at the base.

### #1573: each actor is a file of its own

- **Commits:** base 5cf698a3, merged as e535788b. The pull request's head was 6ec2d77d.
- **Altered:** the software-analysis README (USER), and the eight actors `ACT-adopter` to `ACT-operator` (WRITE), each moved from `actors.md` to a file of its own.
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-WRITE-011, `ACT-component-author`: the change brings in "the system" where the actor still says "the methodology" for what may be one thing.
  - `[person]` RS-WRITE-011, `ACT-adopter`: "Install the system" now sits beside "the methodology's" files on the same topic.
  - `[person]` RS-LDOC-002, the software-analysis README: three facts about actor files are each stated twice on the page.
- **What it owned:** not the move itself. It owned the new `id` field, the raised heading and six term switches. It found that the maintainer's decision of 8 October settles the switches under RS-WRITE-013.

### #1569: record points as headings

- **Commits:** base e535788b, merged as bdfe42e6. The pull request's head was 89268c15.
- **Altered:** 52 artefacts. Four are pages under rules: the Claude Code adapter, CLI, decisions and permissions READMEs (USER). The other 48 are ADRs, and no rule binds on them.
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-LDOC-002: the decisions README states what a point is in its "Schema" and again in later sections.
  - `[person]` RS-LDOC-002: the CLI reference and the decisions README both describe the stamped point heading.
  - `[person]` RS-LDOC-001: the CLI reference cites COR-058, which is not among its anchors.

### #1578: each analysis kind declares its structure

- **Commits:** base 2e147b45, merged as ff5918c8. The pull request's head was 5a57d195.
- **Altered:** the software-analysis README (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B26, RS-LDOC-002: "What binds it" repeats what the page's `SAN` section already said.
  - `[block]` B27, RS-LDOC-002: that no check reads the structures yet is said twice on the page.
  - `[person]` RS-LDOC-002: what a revalidation's `change` names appears in a parenthesis and in an example's comment.
  - `[person]` RS-LDOC-002: two tables restate what the kinds' data file declares.
  - `[person]` RS-LDOC-003 with RS-LDOC-006: a section on the data's shape, which nothing reads yet, on a page written for `user`.
  - `[person]` RS-LDOC-001: a claim about living-docs' schema, a file the page does not anchor.

## The blocks

Each `[block]` below has a reading of whether the passage breaks the rule. The readings are those of the agent that ran the trial for #1418, not the maintainer's. The last column is his.

- **Ownership:** in each block the change owns the break, as COR-057 point 2 says. Most passages the change added. Where a row names older text, the change's edit introduced or widened the break, and the row says so. I checked each against the diff.
- **What the column asks:** whether he agrees that the passage breaks the rule, as #1418 words it. A settled break needs more (COR-057 point 3). The change must own the break, and the rule's text must settle it with no reading left to choose.
  - So he may also mark a block that breaks the rule only on a reading.
  - Whether such a block counts as wrong for the threshold is his to decide.

The rules the blocks cite, in their words:
- **RS-LDOC-001:** "Every statement a page makes is grounded by the page's anchors: the code it describes, the decisions and rules it applies, the captured sources it quotes, the analysis artefacts it builds on. The page is anchored, not each sentence; inline citations are optional where a page mixes sources."
- **RS-LDOC-002:** "Each fact is stated once, and other pages link to it."

| Id | Change | Rule | The passage | My reading | Maintainer agrees |
|---|---|---|---|---|---|
| B1 | #1545 | RS-LDOC-002 | The CLI row for `decisions check-diff` (line 144) and the decisions README (lines 204 to 220) give the same fail, warn and skip lists. | Breaks. Two pages state the lists, and the row's link does not replace them: "stated once, and other pages link to it". | |
| B2 | #1545 | RS-LDOC-002 | The command's base is given in the row (line 144) and the decisions README (line 202), both added. Line 450, which predates the change, gains the command's name. | Breaks: one fact on two pages, "stated once". The rows for `friction check` and `release check` already stated their base, so the change follows the page's pattern. The rule makes no exception for a pattern. | |
| B3 | #1558 | RS-LDOC-001 | "Exit `0` when answered, with no artefact when no rule binds" (CLI reference, line 1312). | Breaks. The change's code now lists an artefact whose only rule is held back. So the anchored code contradicts the sentence, which is not "grounded by the page's anchors". The text predates the change, and the change's edit made it false, so the break is the change's (COR-057 point 2). | |
| B4 | #1553 | RS-LDOC-002 | That the not-code list narrows only the code floor, at lines 805, 837 and 871 of one page. | Breaks if "stated once" reaches within a page, as I read its plain words. The reviewer left that reading to a person in #1573 and #1569. | |
| B5 | #1553 | RS-LDOC-002 | Line 807 repeats three facts from lines 868 and 873 of the same page. | As B4: breaks within a page, on the same reading. | |
| B6 | #1568 | RS-LDOC-002 | The order of `backbone_version` and `completed_version`, in the CLI (lines 214 and 288) and lifecycle (lines 779, 783 and 794) READMEs. | Breaks. Both pages state it, and neither links to the other: "stated once, and other pages link to it". | |
| B7 | #1568 | RS-LDOC-002 | The interrupted upgrade and the rollback, CLI line 290 and lifecycle lines 791 and 792. | Breaks, as B6. The two are nearly word for word. | |
| B8 | #1568 | RS-LDOC-002 | The replay, CLI lines 291 and 292 and lifecycle lines 798 to 803. | Breaks, as B6. | |
| B9 | #1568 | RS-LDOC-002 | An adapter's recorded version, CLI line 293 and lifecycle lines 164 to 168. | Breaks, as B6. | |
| B10 | #1568 | RS-LDOC-002 | "Already current", CLI line 294 and lifecycle line 785. | Breaks, as B6. The two are nearly word for word. | |
| B11 | #1568 | RS-LDOC-002 | The release step writes `completed_version`, in the release README (lines 350 to 352) and the lifecycle README (line 121). | Breaks: one fact on two pages. Which page keeps it is the `[person]` finding on RS-LDOC-003. | |
| B12 | #1571 | RS-LDOC-002 | Sync's guard, in the CLI (lines 269 to 287), lifecycle (811 to 822) and decisions (90) pages, all added. `CONTRIBUTING.md` (135) widens an older sentence to say it. | Breaks. The lifecycle README links to the CLI reference, yet states the conditions and remedies again: not "stated once". | |
| B13 | #1571 | RS-LDOC-002 | What sync writes, in the decisions (84 to 90) and CLI (245 to 251) READMEs, both added. The decisions README also restates its older line 82 on merge delivery, at lines 88 and 96. | Breaks across the two pages. The within-page half rests on B4's reading. | |
| B14 | #1571 | RS-LDOC-002 | A capability by its version, and `--force` ignored, in the CLI (261 to 263, 291) and lifecycle (872 to 876) READMEs. | Breaks, as B6. | |
| B15 | #1571 | RS-LDOC-002 | What upgrade does with each capability, CLI line 321 and lifecycle lines 179, 779 and 878. | Breaks, as B6. | |
| B16 | #1571 | RS-LDOC-002 | The list of seed paths, three times in the CLI README and on the lifecycle and decisions pages. | Breaks, as B6. | |
| B17 | #1571 | RS-LDOC-002 | `pkit agents reconcile --write` repairs the overlay, on the agents, CLI (twice) and lifecycle pages. | Breaks, as B6. | |
| B18 | #1571 | RS-LDOC-001 | The decisions README's lines 36 and 84 to 92 on what sync writes, its guard and `.gitkeep`. | Breaks, on a reading. Their sources are COR-059 and `sync.py`, and neither is an anchor of the page. COR-001, which is, grounds only part. I read an inline citation as no anchor. The reviewer left that question to a person in #1545. | |
| B19 | #1571 | RS-LDOC-001 | The lifecycle README's "Seed paths" paragraph, line 787. | Breaks for the `reconcile --write` sentence, whose code no anchor reaches. The list of seed paths is reached through `upgrade.py`, an anchor that calls the seeding. That half is a reading, which the reviewer left to a person in #1574. | |
| B20 | #1574 | RS-LDOC-002 | The transition's order and steps, CLI lines 316 to 335 and lifecycle lines 771 to 788. | Breaks. The CLI copy names the lifecycle README as its source, then states the order again, and the two copies already differ. | |
| B21 | #1574 | RS-LDOC-002 | A new collision, CLI lines 336 and 417 and lifecycle lines 796 to 809. | Breaks, as B6, and twice within the CLI README. | |
| B22 | #1574 | RS-LDOC-002 | The dependency gates and `--force`, CLI lines 337 and 427 and lifecycle lines 811 to 818 and 894. | Breaks, as B6. | |
| B23 | #1574 | RS-LDOC-002 | The report and the dry run, CLI line 338 and lifecycle lines 792 and 820 to 822. | Breaks, as B6. | |
| B24 | #1574 | RS-LDOC-002 | `pkit capabilities upgrade`'s five steps, CLI lines 403 to 419 and lifecycle lines 862 to 872. | Breaks, as B6. The two copies already word step 5 differently. | |
| B25 | #1574 | RS-LDOC-001 | "A release's changelog names each widening too", lifecycle line 822. | Breaks. No anchor, record or code of the page says so. Its only source is an answer in a scratchpad note. | |
| B26 | #1578 | RS-LDOC-002 | "What binds it" (line 231), which the change added, repeats two facts that the `SAN` section (line 276) already stated at the base. | As B4: breaks within a page. | |
| B27 | #1578 | RS-LDOC-002 | That no check reads the structures yet, lines 233 and 276. | As B4: breaks within a page. | |

## What the trial shows so far

These observations hold whatever the maintainer answers. They do not judge the threshold.

- **Two questions drew two kinds.** The reviewer settled each in some runs and left it to a person in others.
  - **A fact stated twice within one page.** It was a `[block]` in #1553 and #1578 (B4, B5, B26, B27). It was a `[person]` in #1573 and #1569. There the reviewer asked whether RS-LDOC-002 reaches within a page at all, since its remedy names other pages. Those four blocks rest on that reading alone. B13, B15, B16, B17, B20, B21 and B22 have within-page parts too, but their cross-page parts stand on their own.
  - **A decision the page cites but does not anchor.** In #1545 and #1569 the reviewer asked a person whether such a decision grounds a statement. In B18 it settled that it does not. B18, and half of B19, rest on that reading. B25 does not, since nothing the project records says what it states.
- **The threshold sees one error only.** It counts a wrong `[block]`. A `[person]` given where the rule's words settle the break is an error too, and this trial does not count it. The splits above suggest it happened.
- **Where the blocks fall:**
  - 23 of the 27 cite RS-LDOC-002, and 4 cite RS-LDOC-001.
  - 15 of the 23 name both the CLI reference and the lifecycle README. The two pages restated each other before these changes too, as the `[info]` findings of #1571 and #1574 say.
- **The analysis drew no block.** Nine actor artefacts were judged under `WRITE`. Two findings on them went to a person, both under RS-WRITE-011 on #1573's actors. #1558's one-line edit of `ACT-ai-agent` drew none.
- **Scope held in every run:**
  - No run judged the container, a file the answer did not list, or a part a check holds.
  - No run judged the 48 ADRs of #1569.
  - Every finding cited a rule by id, and none was of taste.
  - Each `[info]` named a break that predates its change.

### What the trial did not try

COR-057's Rationale names the cost of a trial by hand: the evidence comes from what the reviewer was tried on. These ten changes left four cases untried.

- **A rule the change moves.** No change moved one. #1554 was picked for that case, and it edits rule-set files only in their containers and prose.
- **A removed artefact,** judged under the base's rules.
- **A held rule, a fill, or a conflict** in the answer.
- **The analysis in depth:** two changes, one added name and six term switches.

## Still to do

- The maintainer answers the last column of "The blocks", through the project manager.
- **The threshold:** at most one block he disagrees with, across the ten.
  - If it is met, this note retires into #1420.
  - If it is not, this note names what the reviewer judged wrong. A follow-up revises the reviewer and runs a second trial, and #1420 waits for it.
- **Whether RS-LDOC-002 reaches within a page** is for living-docs, which owns the rule, to say in it. Until it does, the reviewer may split on it at a gate too, whatever the maintainer answers on B4.
- **The full reviews** were left in the trial's agent workspace, which is never committed. This note is the record that remains of them.
