---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-15
retired: 2026-10-17
produced:
  - https://github.com/aleskalfas/project-kit/issues/1420
  - https://github.com/aleskalfas/project-kit/issues/1634
  - https://github.com/aleskalfas/project-kit/issues/1635
---

# The rule-set reviewer's trials on real changes

The rule-set reviewer was run by hand on ten merged changes (#1418), then on eleven later ones (#1599). This note records how it judged them. It is the trial of the design's slicing issue 8 (#1396, PR #1390). COR-057 point 8 asks for this evidence before a component contributes the reviewer to a gate.

- **The threshold:** at most one wrong `[block]` in a trial. The gate's contribution (#1420) waited on it.
- **What the maintainer did:** he said, for each `[block]`, whether he agrees that the passage breaks the rule. He answered through the project manager, in each table's last column: on 15 October for the first trial ("The blocks", below), and on 17 October for the second ("Its blocks").
- **Where the trials stand:**
  - The first trial's ten reviews are done and judged, and the threshold is not met ("The result").
  - The second trial's eleven reviews are done and judged, and the threshold is met ("The second result"). So the note retires into #1420.
- **Outcomes:**
  - The first trial: 27 `[block]`, 32 `[person]` and 6 `[info]`. The reviewer withheld approval of seven changes and approved three.
  - The second trial: 16 `[block]`, 47 `[person]` and 11 `[info]`. The reviewer withheld approval of six changes and approved five.

## Set-up

Each change was reviewed once, at its own commits, by a reviewer dispatched with no `name`.

- **The reviewer:** `.pkit/agents/core/rule-set-reviewer.md` as commit c9315252 added it (#1385, PR #1558). Its text is unchanged on main through e6ae6e87, and the deployed copy that ran matched it.
  - **Note:** this evidence is for that text. #1560 revised COR-057 point 2 and the reviewer after this trial. The second trial ran the revised text ("Its set-up", below).
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
- **Note:** a change that brings a page under a rule without editing it is outside this trial. That case waited for #1560, and no change of the second trial held it either.

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

- **Ownership:** in each block the change owns the break, as COR-057 point 2 says. Most passages the change added. Where a row names older text, the change's edit introduced or widened the break, and the row says so. The trial agent checked each against the diff.
- **What the column asks:** whether he agrees that the passage breaks the rule, as #1418 words it. A settled break needs more (COR-057 point 3). The change must own the break, and the rule's text must settle it with no reading left to choose.
  - So he may also mark a block as breaking the rule only on a reading.
  - Whether such a block counts as wrong for the threshold is his to decide.

The rules the blocks cite, in their words:
- **RS-LDOC-001:** "Every statement a page makes is grounded by the page's anchors: the code it describes, the decisions and rules it applies, the captured sources it quotes, the analysis artefacts it builds on. The page is anchored, not each sentence; inline citations are optional where a page mixes sources."
- **RS-LDOC-002:** "Each fact is stated once, and other pages link to it."

| Id | Change | Rule | The passage | The trial agent's reading | Maintainer agrees |
|---|---|---|---|---|---|
| B1 | #1545 | RS-LDOC-002 | The CLI row for `decisions check-diff` (line 144) and the decisions README (lines 204 to 220) give the same fail, warn and skip lists. | Breaks. Two pages state the lists, and the row's link does not replace them: "stated once, and other pages link to it". | Yes: one fact on two pages. |
| B2 | #1545 | RS-LDOC-002 | The command's base is given in the row (line 144) and the decisions README (line 202), both added. Line 450, which predates the change, gains the command's name. | Breaks: one fact on two pages, "stated once". The rows for `friction check` and `release check` already stated their base, so the change follows the page's pattern. The rule makes no exception for a pattern. | Yes, as B1. |
| B3 | #1558 | RS-LDOC-001 | "Exit `0` when answered, with no artefact when no rule binds" (CLI reference, line 1312). | Breaks. The change's code now lists an artefact whose only rule is held back. So the anchored code contradicts the sentence, which is not "grounded by the page's anchors". The text predates the change. At the base it was already false for an artefact listed only for a conflict. The change's edit widened that to held rules, so the break is the change's (COR-057 point 2). | Yes. |
| B4 | #1553 | RS-LDOC-002 | That the not-code list narrows only the code floor, at lines 805, 837 and 871 of one page. | Breaks if "stated once" reaches within a page, as its plain words read. The reviewer left that reading to a person in #1573 and #1569. | No. RS-LDOC-002 is about copies on different pages. A repeat within a page is for a person. |
| B5 | #1553 | RS-LDOC-002 | Line 807 repeats three facts from lines 868 and 873 of the same page. | As B4: breaks within a page, on the same reading. | No, as B4. |
| B6 | #1568 | RS-LDOC-002 | The order of `backbone_version` and `completed_version`, in the CLI (lines 214 and 288) and lifecycle (lines 779, 783 and 794) READMEs. | Breaks. Both pages state it, and neither links to the other: "stated once, and other pages link to it". | Yes, as B1. |
| B7 | #1568 | RS-LDOC-002 | The interrupted upgrade and the rollback, CLI line 290 and lifecycle lines 791 and 792. | Breaks, as B6. The two are nearly word for word. | Yes, as B1. |
| B8 | #1568 | RS-LDOC-002 | The replay, CLI lines 291 and 292 and lifecycle lines 798 to 803. | Breaks, as B6. | Yes, as B1. |
| B9 | #1568 | RS-LDOC-002 | An adapter's recorded version, CLI line 293 and lifecycle lines 164 to 168. | Breaks, as B6. | Yes, as B1. |
| B10 | #1568 | RS-LDOC-002 | "Already current", CLI line 294 and lifecycle line 785. | Breaks, as B6. The two are nearly word for word. | Yes, as B1. |
| B11 | #1568 | RS-LDOC-002 | The release step writes `completed_version`, in the release README (lines 350 to 352) and the lifecycle README (line 121). | Breaks: one fact on two pages. Which page keeps it is the `[person]` finding on RS-LDOC-003. | Yes, as B1. |
| B12 | #1571 | RS-LDOC-002 | Sync's guard, in the CLI (lines 269 to 287), lifecycle (811 to 822) and decisions (90) pages, all added. `CONTRIBUTING.md` (135) widens an older sentence to say it. | Breaks. The lifecycle README links to the CLI reference, yet states the conditions and remedies again: not "stated once". | Yes, as B1. |
| B13 | #1571 | RS-LDOC-002 | What sync writes, in the decisions (84 to 90) and CLI (245 to 251) READMEs, both added. The decisions README also restates its older line 82 on merge delivery, at lines 88 and 96. | Breaks across the two pages. The within-page half rests on B4's reading. | Yes across the two pages. The repeats within the decisions README are for a person, as B4. |
| B14 | #1571 | RS-LDOC-002 | A capability by its version, and `--force` ignored, in the CLI (261 to 263, 291) and lifecycle (872 to 876) READMEs. | Breaks, as B6. | Yes, as B1. |
| B15 | #1571 | RS-LDOC-002 | What upgrade does with each capability, CLI line 321 and lifecycle lines 179, 779 and 878. | Breaks, as B6. | Yes, as B1. |
| B16 | #1571 | RS-LDOC-002 | The list of seed paths, three times in the CLI README and on the lifecycle and decisions pages. | Breaks, as B6. | Yes, as B1. |
| B17 | #1571 | RS-LDOC-002 | `pkit agents reconcile --write` repairs the overlay, on the agents, CLI (twice) and lifecycle pages. | Breaks, as B6. | Yes, as B1. |
| B18 | #1571 | RS-LDOC-001 | The decisions README's lines 36 and 84 to 92 on what sync writes, its guard and `.gitkeep`. | Breaks. Line 36's `.gitkeep` and line 87's list of derived state rest on code no anchor reaches. No record the page anchors or cites says them. The rest rests on COR-059, which the page cites but does not anchor, and on COR-001, which grounds part. That half is a reading, which the reviewer left to a person in #1545 and #1569. | Yes, in full. Only what a page anchors grounds a statement. A record it cites but does not anchor grounds nothing. |
| B19 | #1571 | RS-LDOC-001 | The lifecycle README's "Seed paths" paragraph, line 787. | Breaks for the `reconcile --write` sentence, whose code no anchor reaches. The list of seed paths is reached through `upgrade.py`, an anchor that calls the seeding. That half is a reading, which the reviewer left to a person in #1574. | Yes, in full, as B18. Code reached only because an anchored file calls it grounds nothing. |
| B20 | #1574 | RS-LDOC-002 | The transition's order and steps, CLI lines 316 to 335 and lifecycle lines 771 to 788. | Breaks. The CLI copy names the lifecycle README as its source, then states the order again, and the two copies already differ. | Yes, as B1. |
| B21 | #1574 | RS-LDOC-002 | A new collision, CLI lines 336 and 417 and lifecycle lines 796 to 809. | Breaks, as B6, and twice within the CLI README. | Yes across the pages. The two within the CLI README are for a person, as B4. |
| B22 | #1574 | RS-LDOC-002 | The dependency gates and `--force`, CLI lines 337 and 427 and lifecycle lines 811 to 818 and 894. | Breaks, as B6. | Yes, as B1. |
| B23 | #1574 | RS-LDOC-002 | The report and the dry run, CLI line 338 and lifecycle lines 792 and 820 to 822. | Breaks, as B6. | Yes, as B1. |
| B24 | #1574 | RS-LDOC-002 | `pkit capabilities upgrade`'s five steps, CLI lines 403 to 419 and lifecycle lines 862 to 872. | Breaks, as B6. The two copies already word step 5 differently. | Yes, as B1. |
| B25 | #1574 | RS-LDOC-001 | "A release's changelog names each widening too", lifecycle line 822. | Breaks. No anchor, record or code of the page says so. Its only source is an answer in a scratchpad note. | Yes. |
| B26 | #1578 | RS-LDOC-002 | "What binds it" (line 231), which the change added, repeats two facts that the `SAN` section (line 276) already stated at the base. | As B4: breaks within a page. | No, as B4. |
| B27 | #1578 | RS-LDOC-002 | That no check reads the structures yet, at line 233, which the change added, and line 276, whose fact predates it. | As B4: breaks within a page. | No, as B4. |

## What the trial shows so far

These observations hold whatever the maintainer answers. They do not judge the threshold.

- **Two questions drew two kinds.** The reviewer settled each in some runs and left it to a person in others.
  - **A fact stated twice within one page.** It was a `[block]` in #1553 and #1578 (B4, B5, B26, B27). It was a `[person]` in #1573 and #1569. There the reviewer asked whether RS-LDOC-002 reaches within a page at all, since its remedy names other pages. Those four blocks rest on that reading alone. B13, B15, B16, B17, B20, B21 and B22 have within-page parts too, but their cross-page parts stand on their own.
  - **A source the page cites or reaches but does not anchor.** In #1545, #1569 and #1574 the reviewer asked a person whether a cited decision, or code an anchored module calls, grounds a statement. In B18 and B19 it settled that it does not. Half of B18 and half of B19 rest on that reading. B25 does not, since nothing the project records says what it states.
- **The threshold sees one error only.** It counts a wrong `[block]`. A `[person]` given where the rule's words settle the break is an error too, and this trial does not count it. Each split above means one of its two kinds was wrong, and which one depends on the maintainer's reading.
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

COR-057's Rationale names one cost of trying the reviewer by hand: the evidence comes from the rules it was tried on. "What the rules reached" says which those were. The cases a change can hold are a second limit, and these ten held none of the following.

- **A rule the change moves.** No change moved one. #1554 was picked for that case, and it edits rule-set files only in their containers and prose.
- **An added or a removed artefact.** Every artefact in the ten answers was `changed`. So none was judged as added, and none under the base's rules.
- **A held rule, a fill, or a conflict** in the answer.
- **The analysis in depth:** two changes, with one added name, eight new `id` fields and raised headings, and six term switches.

## The result

The maintainer judged the 27 blocks on 15 October. 23 are right and 4 are wrong, so **the threshold, at most one wrong block, is not met.**

- **His readings:**
  - RS-LDOC-002 is about copies on different pages. A fact a page states twice is a passage for a person, not a break.
  - A change that leaves two statements of one fact disagreeing, on one page or two, is a break.
  - Only what a page anchors grounds a statement (RS-LDOC-001). A record the page mentions but does not anchor grounds nothing. Nor does code reached only because an anchored file calls it. A change to either flags no page.
- **What the reviewer judged wrong:**
  - **A repeat within a page, as a break.** The four wrong blocks, B4, B5, B26 and B27, rest on that alone. B13 and B21 also blocked on such a part, and their parts across pages are right. So four runs blocked on that reading: #1553 and #1578 wholly, #1571 and #1574 in part.
  - **Two kinds for one question.** The rules left two questions open: a repeat within a page, and grounding. On each, some runs settled it and others left it to a person. Within a page, the `[person]` findings of #1569 and #1573 were the right kind, and the blocks the wrong one. On grounding, B18 and B19 settled it as he reads it, and the `[person]` findings of #1545, #1569 and #1574 left it open. The threshold counts only the wrong blocks.
- **Why the fix is in the rules' text, not the reviewer:** the reviewer holds no rules of its own (COR-057 point 1). It reads each rule's text, and where the text leaves a reading open, two runs can choose it differently, as these did. So living-docs, which owns the rules, writes the readings into them. Written into the reviewer instead, they would be rules of its own.
- **The follow-ups:**
  - **#1596:** living-docs' rules state these readings. Each fact has one home, and a summary on another page links to it and anchors to its section. A repeat within a page goes to a person, and two disagreeing statements are a break. Only anchors ground a statement. It waits for #1423.
  - **#1597:** the facts of the 19 blocks on copies across pages, B1, B2, B6 to B17 and B20 to B24, each get one home, after #1596.
  - **#1599:** the second trial, on changes made after #1596. It continues this note, and #1420 now waits for it.

## The second trial

The rule-set reviewer was run by hand again (#1599), on eleven changes merged after PR #1603 (#1596). That pull request, merged as 28f7314b, wrote the maintainer's readings of "The result" into living-docs' rules. Only changes made after it test them.

- **The threshold:** at most one wrong `[block]` across the eleven, as in the first trial.
- **What the maintainer did:** he said on 17 October, for each `[block]` in "Its blocks" below, whether he agrees that the passage breaks the rule. His answer is in the table's last column.
- **Where it stands:** the eleven reviews are done and judged. 15 blocks are right and 1 is wrong, so the threshold is met ("The second result", below).
- **Outcome:** 16 `[block]`, 47 `[person]` and 11 `[info]`. The reviewer withheld approval of six changes and approved five.

### Its set-up

It is the first trial's set-up ("Set-up", above), with these differences.

- **The reviewer:** `.pkit/agents/core/rule-set-reviewer.md` as main holds it at 86ffe6d5. Its text last changed in 12c0a665, for #1560, so it reads COR-060 too. The deployed copy that ran matched it.
  - **Note:** #1560 added how the reviewer judges an artefact a change brings under a rule. No change of this trial brought one under a rule, so that part did not run.
- **The rules:** RS-LDOC-001 and RS-LDOC-002 as PR #1603 left them. "Its blocks" quotes the words its readings rest on.
- **The answer it read:** `pkit rule-sets altered --base <base> --head <merge> --json`, run from the backbone at 86ffe6d5.
- **The description:** each pull request's body and squash message, saved to files the brief named.
- **What the brief added:** the checkout to run in, the folder for working files, and where the description was saved. It gave no rule and no hint of what to look for.
- **The cost:** each run took 4 to 15 minutes and 94,000 to 244,000 tokens.

The rules reached what they reached in the first trial ("What the rules reached", above):
- the user space's pages: `LDOC` and `RS-USER-001`
- `CONTRIBUTING.md` and the release README: `LDOC` alone
- the eight actors: `WRITE`'s ten accepted rules

### Its changes

Thirteen changes merged after PR #1603, the first-parent commits from cce2ed9f to 126b172c. For eleven of them `pkit rule-sets altered` named at least one accepted rule that binds. So all eleven were picked, and the table says what each covers. #1624 merged while the trial ran, and was added last.

| Pull request | Issue | Merged as | What it covers |
|---|---|---|---|
| #1605 | #1424 | cce2ed9f | The living-docs README, on anchoring one part of a record or a document |
| #1606 | #1597 | 9fd11906 | The first trial's 19 facts across pages, each given one home, on six pages in both spaces |
| #1604 | #1367 | ccb65b30 | The most text added to one page, the software-analysis README |
| #1611 | #1609 | fd6a62d0 | The CLI and decisions READMEs, where reviewers had found drift |
| #1615 | #1607 | cc6a4292 | One new option, stated on four pages |
| #1618 | #1507 | 6dfea365 | New facts on the software-analysis README, each stated in several sections |
| #1619 | #1617 | b09e4984 | A new skill, described on two pages |
| #1610 | #1475 | 9d50220f | A new section on where a method rule set binds |
| #1621 | #1608 | f90439cc | One page, with a new section on how verbs find a branch |
| #1622 | #1368 | 86ffe6d5 | The only change that alters the analysis: eight actors relabelled |
| #1624 | #1375 | 126b172c | `CONTRIBUTING.md` and the software-analysis README, on a new check of a use case's steps |

Two changes were passed over:
- #1614 (#1612, 665b2a4d): it changes only `CLAUDE.md`, which is no artefact.
- #1620 (#1616, 1bce0420): it changes three pages only inside their container, so it alters no artefact.

The three kinds #1599 names are among the eleven:
- **A page with a fact repeated within it:** #1618 and #1621 most plainly, and #1610 states one fact about ten times. Five other changes drew such a finding too.
- **A statement resting on a source the page does not anchor:** #1619, #1610 and #1624, which drew blocks. #1604 and #1611 drew passages for a person.
- **The analysis:** #1622, the eight actors under `WRITE`.

### Its summary

As in the first trial's summary, LDOC is `living-docs:RS-LDOC-001` to `006`, and WRITE is `WRITE`'s ten accepted rules.

| Change | Rules bound | Verdict | `[block]` | `[person]` | `[info]` |
|---|---|---|---|---|---|
| #1605 | LDOC, RS-USER-001 | WITHHOLD | 1 | 2 | 0 |
| #1606 | LDOC, RS-USER-001 | APPROVE | 0 | 8 | 2 |
| #1604 | LDOC, RS-USER-001 | WITHHOLD | 1 | 6 | 2 |
| #1611 | LDOC, RS-USER-001 | APPROVE | 0 | 8 | 1 |
| #1615 | LDOC, RS-USER-001 | WITHHOLD | 3 | 5 | 1 |
| #1618 | LDOC, RS-USER-001 | APPROVE | 0 | 1 | 0 |
| #1619 | LDOC, RS-USER-001 | WITHHOLD | 3 | 4 | 1 |
| #1610 | LDOC, RS-USER-001 | WITHHOLD | 5 | 5 | 1 |
| #1621 | LDOC, RS-USER-001 | APPROVE | 0 | 2 | 0 |
| #1622 | WRITE | APPROVE | 0 | 4 | 1 |
| #1624 | LDOC, RS-USER-001 | WITHHOLD | 3 | 2 | 2 |
| **All eleven** | | 6 WITHHOLD | **16** | **47** | **11** |

### Its reviews

Each review is in the first trial's form. A line number is at the head unless it says otherwise. A page a change altered only inside its container is not listed as altered.

#### #1605: anchoring one part

- **Commits:** base 28f7314b, merged as cce2ed9f. The pull request's head was 59fe1f12.
- **Altered:** the living-docs README (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B28, RS-LDOC-002: the new paragraph says what a change to another part asks. The CLI reference states that in full, and the page neither links nor anchors it.
  - `[person]` RS-LDOC-002: the paragraph links and anchors the schemas reference for how an anchor names a part. The CLI reference states that in full too, so which page is the home is open.
  - `[person]` RS-LDOC-001: "a change to another point or section of it asks the page nothing". That may not hold for a section nested in the anchored one.

#### #1606: one home per fact

- **Commits:** base cce2ed9f, merged as 9fd11906. The pull request's head was 8f4353d6.
- **Altered:** `CONTRIBUTING.md` and the release README (TECH), the agents, CLI, decisions and lifecycle READMEs (USER). `.pkit/README.md` changed only in its container.
- **Verdict:** APPROVE.
- **What it found of the 19 facts:** each one's other copies are gone. Or each copy links to the home's section, and its page anchors that section.
- **Findings:**
  - `[person]` RS-LDOC-002: the CLI reference restates sync's guard in full beside its link and anchor.
  - `[person]` RS-LDOC-002: the CLI's paragraph on upgrade under the router's fallback is fuller than its home's. So the home may be the CLI reference.
  - `[person]` RS-LDOC-002: the CLI's summary of a transition names all ten of the home's steps.
  - `[person]` RS-LDOC-002: the CLI and decisions READMEs each summarise "What sync writes" whole.
  - `[person]` RS-LDOC-002: the change moved text on merge delivery and the agent workspace into the lifecycle README. Other pages state it, with no link either way.
  - `[person]` RS-LDOC-002: the CLI and agents READMEs say a deleted seed path returns at the next upgrade to a new release. The home says the next transition, which can run at the same version.
  - `[person]` RS-LDOC-002: the release README restates what the replay may restore, beside its link and anchor.
  - `[person]` RS-LDOC-002: the other linked and anchored statements the change wrote, on five pages.
  - `[info]` RS-LDOC-002: the CLI reference states the clash of area names twice, with no link, at the base.
  - `[info]` RS-USER-001: a CLI link to the `pin` / `unpin` heading misses its slug, at the base.

#### #1604: a project's own structures

- **Commits:** base 9fd11906, merged as ccb65b30. The pull request's head was 9b8e6197, and its recorded base cce2ed9f.
- **Altered:** the software-analysis README (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B29, RS-LDOC-002: "A label or a section of your own is never reported" now disagrees with the new closed list of labels. Under that list an undeclared label is reported.
  - `[person]` RS-LDOC-002: "the check reports nothing of a structure" while its rule is proposed. The file's errors are reported whatever any rule's status.
  - `[person]` RS-LDOC-002: "Every part is required", beside an added part that is optional unless it is required.
  - `[person]` RS-LDOC-001: "bound to it by its path (COR-023), so `pkit validate` checks it" cites COR-023, which the page does not anchor.
  - `[person]` RS-LDOC-001: a link to #1607, as what will let the preview read a proposed rule.
  - `[person]` RS-LDOC-002: what `pkit rule-sets reach` gives, and a schema's binding by its path, with no link to the pages that state them.
  - `[person]` RS-LDOC-002: three facts, each stated twice on the page.
  - `[info]` RS-LDOC-002: two statements on which structure a record is held to disagreed at the base.
  - `[info]` RS-LDOC-001: older citations of COR-054 to COR-056, which the page does not anchor.

#### #1611: the guides' drift

- **Commits:** base ccb65b30, merged as fd6a62d0. The pull request's head was 86e37129.
- **Altered:** the CLI and decisions READMEs (USER). ADR-027 to ADR-030 were altered, and no rule binds on them. Five pages changed only in their containers, among them `CONTRIBUTING.md`.
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-LDOC-001: the decisions README says `supersedes:` names only a record the later one replaces whole. Nothing the page anchors says so.
  - `[person]` RS-LDOC-002: "`pkit new decision` numbers a record for you" may state the fact of the CLI's "Where the number comes from". It has no link or anchor. Its paragraph also repeats two of its own page's.
  - `[person]` RS-LDOC-002: that sync writes your files only through merge delivery is stated twice in the decisions README.
  - `[person]` RS-LDOC-002: the new `new capability` entry repeats two other CLI passages.
  - `[person]` RS-LDOC-002: "it registers nothing" may disagree with the section's opening, that the CLI recognises what a `new` command stamps.
  - `[person]` RS-LDOC-002: the `permissions setup autonomy` row writes exclusions to the local settings on macOS. It also calls a local list of them cruft while the sandbox is off.
  - `[person]` RS-LDOC-002: "`new decision` takes no base" repeats that command's own section, with a link.
  - `[person]` RS-LDOC-001: when git cannot read the branches, the "Nothing resolves" bullet may say the references tried are named. The code then names none.
  - `[info]` RS-LDOC-002: the base of `check-numbers`, stated with no link to its home, at the base.

#### #1615: `rule-sets reach --preview`

- **Commits:** base 665b2a4d, merged as cc6a4292. The pull request's head was 6e434665, and its recorded base fd6a62d0.
- **Altered:** the CLI, lifecycle, schemas and software-analysis READMEs (USER). ADR-057 was altered, and no rule binds on it. The decisions README changed only in its container.
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B30, RS-LDOC-002: the schemas README states what `--preview` gives, with no link to the CLI reference and no anchor on it.
  - `[block]` B31, RS-LDOC-002: the lifecycle README's row states it too, word for word as the CLI's table does.
  - `[block]` B32, RS-LDOC-002: the software-analysis README states it too, in a relative clause.
  - `[person]` RS-LDOC-001: whether the docstring of the anchored `backbone.py` grounds that clause.
  - `[person]` RS-LDOC-001: the CLI reference gives a reason why `rule-sets altered` has no preview. ADR-057 gives none.
  - `[person]` RS-LDOC-002: the CLI reference states the preview twice. It also states twice a fill conflict that only the preview finds.
  - `[person]` RS-LDOC-002: the CLI reference says a new major is needed to accept a rule, and what a pin behind its set does. The schemas README states both, and the CLI neither links nor anchors it.
  - `[person]` RS-LDOC-002: "That reading judges the chain too" may state the schemas README's fact on fills.
  - `[info]` RS-LDOC-002: older rows and sentences beside the edits point to the CLI reference in plain text only.

#### #1618: the anchors of use cases and journeys

- **Commits:** base cc6a4292, merged as 6dfea365. The pull request's head was 9dbe4ee5.
- **Altered:** the software-analysis README (USER).
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-LDOC-002: three new facts are each stated in several sections of the page, in agreement.

#### #1619: the `docs-author` skill

- **Commits:** base 6dfea365, merged as b09e4984. The pull request's head was e71126f3, and its recorded base cc6a4292.
- **Altered:** the living-docs and skills READMEs (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B33, RS-LDOC-001: where `pkit sync` deploys the skill rests on nothing the living-docs README anchors.
  - `[block]` B34, RS-LDOC-001: the skills README names `docs-author`, and says a capability's README describes its skills. Nothing it anchors says either.
  - `[block]` B35, RS-LDOC-002: the skill's pairing with `pkit living-docs new` is stated on both pages. Neither links or anchors the other.
  - `[person]` RS-LDOC-002: "The adapter deploys them beside the core ones" may restate the Claude Code adapter's README.
  - `[person]` RS-LDOC-001: "A write that breaks validation is put back" says more than `new space` does.
  - `[person]` RS-LDOC-001: that `new space` finds no scope until the roots are separated says more than the code. The onboarding step it cites is not the one that separates them.
  - `[person]` RS-LDOC-002: two facts on what `new space` writes, each stated twice.
  - `[info]` RS-LDOC-001: the older sentence on where `pkit sync` deploys the agent has B33's gap.

#### #1610: `SAN` binds through a set of the project's own

- **Commits:** base b09e4984, merged as 9d50220f. The pull request's head was 6cf9614d.
- **Altered:** the software-analysis README (USER). `RS-SAN-001` was altered, and no rule binds on it.
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B36, RS-LDOC-001: the `rule-sets` folder, as where a project's set goes by default, rests on nothing the page anchors.
  - `[block]` B37, RS-LDOC-001: that `pkit rule-sets reach` lists the rules a pin behind its set holds back rests on nothing the page anchors.
  - `[block]` B38, RS-LDOC-002: B36's fact, which the schemas README states, with no link or anchor.
  - `[block]` B39, RS-LDOC-002: B37's fact, which the CLI and schemas READMEs state, with no link or anchor.
  - `[block]` B40, RS-LDOC-002: "Changing what a set inherits gives that set a new major", which the schemas README states, with no link or anchor.
  - `[person]` RS-LDOC-001: whether the example set's keys and its pin, `SAN@0`, are statements the page must ground.
  - `[person]` RS-LDOC-002: that the capability always checks a record's structure itself, stated about ten times.
  - `[person]` RS-LDOC-002: that the check is never silent, stated twice.
  - `[person]` RS-LDOC-002: how the preview works, stated twice.
  - `[person]` RS-LDOC-002: "always" may disagree with an older line. Under it no body is held to a structure while the file holds an error.
  - `[info]` RS-LDOC-001 and RS-LDOC-002: an older statement of what `reach` lists, with B37's and B39's gaps.

#### #1621: an issue's branch

- **Commits:** base 1bce0420, merged as f90439cc. The pull request's head was 5cd95600, and its recorded base 9d50220f.
- **Altered:** the project-management README (USER).
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-LDOC-003: a module's path, an issue number, and how `land-work` hands the branch on, on a page written for `user`.
  - `[person]` RS-LDOC-002: `land-work`'s head step repeats two facts the new section states.

#### #1622: the analysis set and the actors' labels

- **Commits:** base f90439cc, merged as 86ffe6d5. The pull request's head was 78fbf674.
- **Altered:** the eight actors `ACT-adopter` to `ACT-operator` (WRITE). No rule binds on the rule-set entries it changed or added.
- **Verdict:** APPROVE.
- **Findings:**
  - `[person]` RS-WRITE-013, `ACT-merge-authoriser`: the label "Always a person" becomes "Human role", which drops "always". The template round recorded the maintainer's choice of that label.
  - `[person]` RS-WRITE-013, `ACT-ai-agent`: "Context: None.", beside a limit the actor states under *Occasions*.
  - `[person]` RS-WRITE-010, `ACT-component-author`: under the noun label *Context*, "They" may point at the list before it.
  - `[person]` RS-WRITE-010, `ACT-methodology-maintainer`: the same.
  - `[info]` RS-WRITE-007, `ACT-ai-agent`: *Occasions* may hold two topics, as *Comes* did at the base.

#### #1624: a use case's steps stay append-only

- **Commits:** base 86ffe6d5, merged as 126b172c. The pull request's head was f55f5ef3, and its recorded base f90439cc.
- **Altered:** `CONTRIBUTING.md` (TECH), and the software-analysis README (USER).
- **Verdict:** WITHHOLD.
- **Findings:**
  - `[block]` B41, RS-LDOC-001: `CONTRIBUTING.md` says what `check-numbers` now fails on. Nothing it anchors says so.
  - `[block]` B42, RS-LDOC-002: the software-analysis README states that fact in full. `CONTRIBUTING.md` neither links nor anchors it.
  - `[block]` B43, RS-LDOC-001: the README's "Not in `pkit validate`" cites COR-055 point 2, which the page does not anchor.
  - `[person]` RS-LDOC-001: "a number, once given, never changes meaning (DEC-001 point 3)" may say more than the point, which says "once settled".
  - `[person]` RS-LDOC-002: that steps and variants stay append-only is restated in four other places on the README.
  - `[info]` RS-LDOC-001 and RS-LDOC-002: the older parts of `CONTRIBUTING.md`'s sentence have B41's and B42's gaps.
  - `[info]` RS-LDOC-001: an older citation of COR-055 on the README, which the page does not anchor.

### Its blocks

Each `[block]` below has a reading of whether the passage breaks the rule. The readings are those of the agent that ran this trial for #1599, not the maintainer's. The last column is his.

- **Ownership:** the change added each passage. In B29 the change's added lines brought in a disagreement with an older line, so it owns that break (COR-057 point 2).
- **What the column asks:** as in the first trial ("The blocks", above).

The rules the blocks cite, in the words the readings rest on:
- **RS-LDOC-001:** "Only what the page anchors grounds a statement." A record the page cites but does not anchor "grounds nothing". So does "code reached only through a call from a file the page anchors". "A statement that rests on anything else breaks this rule until the page anchors what it rests on."
- **RS-LDOC-002:**
  - "Each fact that pages state has one home: the one page that states it in full."
  - "A summary on another page links to the home. That page anchors to the home's section that states the fact. An anchor on the whole home is not that anchor."
  - "A statement of the fact on another page that lacks the link or the anchor breaks this rule."
  - "Two statements of one fact that disagree break this rule on each page that holds one of them, on one page or on two. Two statements disagree where one says what the other rules out."
  - A fact that a page of each space states "has its home on the user space's page".

| Id | Change | Rule | The passage | The trial agent's reading | Maintainer agrees |
|---|---|---|---|---|---|
| B28 | #1605 | RS-LDOC-002 | The living-docs README, line 47: a part is anchored "so that a change to another point or section of it asks the page nothing". The CLI reference's `friction check` section states this in full (line 1215). | Breaks. The page neither links that section nor anchors it: "lacks the link or the anchor". Its new link goes to the schemas reference, which does not state this fact. | Yes. |
| B29 | #1604 | RS-LDOC-002 | The software-analysis README, line 404, older: "A label or a section of your own is never reported." Lines 312 and 397, added: under `closed: true`, a label no part declares "is reported", and the check fails on it. | Breaks. "Never reported" rules out what lines 312 and 397 say, so the two "disagree". | Yes. |
| B30 | #1615 | RS-LDOC-002 | The schemas README, line 583: "With `--preview`, it gives where rules would bind if every proposed rule were accepted". The CLI reference's `rule-sets reach` section states it in full. | Breaks. The page names the CLI reference only in plain text, for the next sentence. It anchors no section of it. | Yes. |
| B31 | #1615 | RS-LDOC-002 | The lifecycle README's row for `rule-sets reach`, line 453: "with `--preview`, where rules would bind if every proposed rule were accepted". | Breaks, as B30. The row names the CLI reference in plain text, with no anchor. Its older rows follow the same pattern, and the rule makes no exception for a pattern (B2). | Yes, as B30. |
| B32 | #1615 | RS-LDOC-002 | The software-analysis README, line 339: "it also reads `pkit rule-sets reach --preview`, which says where the rule would bind if every proposed rule were accepted." | Breaks, as B30. The clause gives the option's whole meaning, so it states the fact. The same run left a shorter clause on line 336 to a person. | Yes. Stating another page's fact needs the link and the anchor, however short. Naming a thing needs neither. |
| B33 | #1619 | RS-LDOC-001 | The living-docs README, line 184: "`pkit sync` deploys it with the other skills, in Claude Code as `.claude/skills/docs-author/`." | Breaks. It rests on sync and the Claude Code adapter's `deploy-skills.sh`, which the page does not anchor. Of its anchors, COR-005 says only that an adapter deploys a harness's content. | Yes. |
| B34 | #1619 | RS-LDOC-001 | The skills README, line 62: a capability's README describes its skills, and "An example is living-docs' `docs-author`, paired with `pkit living-docs new`." | Breaks, as B33. The page anchors core's skills, `deploy-skills.sh` and six core records. None of them names living-docs, or says what a capability's README describes. | Yes, as B33. |
| B35 | #1619 | RS-LDOC-002 | That `docs-author` pairs with `pkit living-docs new`: the skills README, line 62, and the living-docs README, line 184. | Breaks. Neither page links or anchors the other. The living-docs README's section states the skill in full, so it is the home. The skills README's statement "lacks the link or the anchor". | Yes. |
| B36 | #1610 | RS-LDOC-001 | The software-analysis README, line 441: a project's set goes "by default in the `rule-sets` folder under your internal documentation root (COR-049)". | Breaks. COR-049 and COR-051, both anchored, put a project's rule sets under the internal root and name no `rule-sets` folder. The backbone's discovery code and the schemas README name it, and the page anchors neither. | Yes. |
| B37 | #1610 | RS-LDOC-001 | Line 457: "`pkit rule-sets reach` lists each rule a pin behind its set holds back." | Breaks. COR-051 point 7 says such a rule binds nothing and is reported in status, not that `reach` lists it. The anchored `backbone.py` calls `reach`, and the command's code is reached only through that call. | Yes. |
| B38 | #1610 | RS-LDOC-002 | Line 441, B36's passage. The schemas README's "Rule-set files" states the folder in full. | Breaks: no link to it and no anchor on it. | Yes. |
| B39 | #1610 | RS-LDOC-002 | Line 457, B37's passage. The CLI reference states the `held` rules of `reach`. | Breaks: the page links and anchors no page that states it. | Yes. |
| B40 | #1610 | RS-LDOC-002 | Line 458: "Changing what a set inherits gives that set a new major." The schemas README's `version` row states it in full. | Breaks: no link and no anchor. The page anchors COR-051, whose point 7 states the fact, so RS-LDOC-001 holds. The rule names no exception for a fact a record also states. The maintainer may read that otherwise. | No. A decision record the page anchors is the home of the facts it decides. The page may state such a fact in its own words, with no link to another page. |
| B41 | #1624 | RS-LDOC-001 | `CONTRIBUTING.md`, line 42: `check-numbers` fails on "a use case's step or variant renumbered or removed". | Breaks. The page anchors `scripts/check.sh`, which only calls the command. No record or section it anchors says what the command fails on. | Yes. |
| B42 | #1624 | RS-LDOC-002 | B41's clause. The software-analysis README's "Steps and variants stay append-only" states the fact in full. | Breaks. `CONTRIBUTING.md` neither links that section nor anchors it. The README is the home, since a page of each space states the fact. | Yes. |
| B43 | #1624 | RS-LDOC-001 | The software-analysis README, line 503: "Not in `pkit validate`. It reads the base, so it answers about your change rather than the tree (COR-055 point 2)." | Breaks. The sentence cites COR-055, which the page does not anchor. A citation "grounds the sentence only where the page anchors what it cites". | Yes. |

### Its passages for a person the rules' words settle

#1599 asks the note to list each `[person]` finding whose break the rules' words settle. These are they, on this trial agent's reading. They are information, and the threshold does not count them.

- **Settled on the rules' words alone:**
  - #1611, the decisions README, line 209: `supersedes:` names only a record replaced whole. Nothing the page anchors says so, and RS-LDOC-001 gives a page no ground of its own. That holds though COR-058 point 5 leaves the form of a supersession to this page.
  - #1604, the software-analysis README, line 338: "Until #1607 lets it read that". An issue is no anchor, and RS-LDOC-001 binds every statement a page makes.
- **Settled if B32 is right.** Each is a short statement of another page's fact, with no link and no anchor:
  - #1604, line 338: "`pkit rule-sets reach` lists accepted rules only", which the CLI reference states.
  - #1611, the decisions README, line 280: "`pkit new decision` numbers a record for you". The CLI's "Where the number comes from" states it.
- **Settled if B40 is right.** It states a fact that a record the page anchors also states:
  - #1615, the CLI reference, line 1394: "Accepting a rule needs a new major of its set (COR-051 point 7)", which the schemas README states.

If the maintainer holds B32 wrong, its two passages were the right kind, and B32 was the wrong kind. The same goes for B40 and its passage. He held B32 right and B40 wrong ("The second result", below).

### What it shows so far

These observations hold whatever the maintainer answers. They do not judge the threshold.

- **A fact stated twice within one page** drew no block. It went to a person in eight runs, as the rule now says.
- **Grounding:**
  - A record the page cites but does not anchor grounded nothing in every run. B43 settled it. #1604's COR-023 went to a person only on whether the page's anchored schemas ground the clause.
  - Code reached only through a call grounded nothing in B37 and B41.
  - Three new questions went to a person. They are an issue as the ground (#1604), a specification's own convention (#1611), and anchored code describing the command it calls (#1615).
  - On this agent's reading, the rules' words settle the first two. If the maintainer agrees, grounding drew two kinds again, on new questions.
- **Two statements that disagree** drew a block where the words rule each other out (B29). Where it took a reading of a word, it went to a person, as in #1604, #1606, #1610 and #1611.
- **Two more new questions drew two kinds:**
  - **How short a statement of another page's fact can be.** A relative clause was a block in B32. Shorter clauses went to a person in #1604, #1611 and #1615 itself.
  - **A fact that a record the page anchors also states.** B40 blocked on one. #1615 sent a like sentence of the CLI reference to a person.
  - The rules' text settles neither, so the split the first trial showed came back on new questions.
- **Where the blocks fall:**
  - 10 of the 16 cite RS-LDOC-002, and 6 cite RS-LDOC-001.
  - 9 of the 10 on RS-LDOC-002 are a statement on another page that lacks the link and the anchor. B29 is a disagreement within a page.
  - The 16 rest on 13 passages. B38, B39 and B42 judge the passages of B36, B37 and B41 under the other rule. So one wrong reading of such a passage counts twice.
  - 8 of the 16 fall on the software-analysis README, in four changes.
  - #1606, which gave the first trial's 19 facts across pages one home, drew no block.
- **The analysis drew no block,** as in the first trial. Its four passages for a person each turn on a label or an answer that the template round chose.
- **Scope held in every run:**
  - No run judged the container, a file the answer did not list, or a part a check holds.
  - Every finding cited a rule by id, and none was of taste.
  - Each `[info]` named a break that predates its change.

### What it did not try

The first trial's list ("What the trial did not try", above) holds for this trial too.

- **A rule the change moves:** no change made a rule bind, or stop binding, on an artefact its answer listed.
- **An added or a removed artefact:** every ruled artefact in the eleven answers was `changed`.
- **A held rule, a fill, or a conflict:** none was in any answer.
- **The analysis in depth:** one change, with eight actors relabelled.
- **An artefact brought under a rule:** none, so the part of the reviewer #1560 added did not run. A gate would still get that part untried.

## The second result

The maintainer judged the 16 blocks on 17 October. 15 are right and 1 is wrong, so **the threshold, at most one wrong block, is met.**

- **The fourteen blocks that apply his readings of 15 October** ("The result") are right: B28 to B31, B33 to B39 and B41 to B43.
- **His two new readings:**
  - **A short statement (B32):** stating another page's fact needs a link to its home and an anchor on it, however short. Naming a thing needs nothing. So B32 is right. The two passages "Settled if B32 is right" were the wrong kind, and should have been blocks. The threshold does not count them.
  - **A fact a record decides (B40):** a decision record the page anchors is the home of the facts it decides. A page that anchors the record may state such a fact in its own words, with no link to another page. So B40 is wrong, and the passage "Settled if B40 is right" was the right kind.
- **The follow-ups:**
  - **#1634:** living-docs' rule states the two new readings.
  - **#1635:** the fifteen breaks are mended in the pages. So are the four passages his readings settle: the two "Settled on the rules' words alone" and the two "Settled if B32 is right".
  - **#1420:** living-docs and software-analysis contribute the rule-set reviewer to the gate. It waited for this threshold.

## Still to do

- **The follow-ups** of "The second result" carry what remains: #1634, #1635 and #1420. This note is retired into them.
- **The full reviews** of both trials were left in the trials' agent workspaces, which are never committed. This note is the record that remains of them.
