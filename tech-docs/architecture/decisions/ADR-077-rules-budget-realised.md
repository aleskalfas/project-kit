---
id: ADR-077
title: Each rules file's budget is set where its owner keeps its data, and validation holds the file to it
status: proposed
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit builds [COR-069](../../../.pkit/decisions/core/COR-069-rules-word-budget.md), under which each rules file a session loads stays within a word budget.
- **The budgets:** a loaded set gives its file's budget as `budget` in its front matter. A project's plain rules file takes its budget from `rule-sets.plain-file-budget` in the backbone configuration.
- **The count:** one function, beside the projection of a loaded set into its file, counts a file's words. The check, the report and the generator all use it.
- **The check and the report:** validation's `rule-sets` member fails a file past its budget where its owner can correct it, and prints each rules file's count against its budget as a summary line in every project.
- **What a change raises:** `pkit rule-sets altered` lists each budget a change raises, so a raise is in front of whoever reviews the change.
- **project-kit's first budgets:** `OPS` at the size of `.pkit/rules/core.md` when the build lands, and project-kit's own `project.md` at its size then.

## Context

COR-069 decides that each rules file a session loads may have a budget in words, that a loaded set holds its budget in its own data, that a backbone configuration key gives a plain project file's, and that validation fails a file past its budget where its owner can correct it and reports every file's count. Its Implications leave to an architecture record:
- the name of the budget in a loaded set's data, and of the configuration key
- the validator that holds the check and the report, and the report's form
- where the count lives
- how the backbone's reading of what a change alters shows a raised budget

The records this one fits:
- **The loaded set, its file and their check** live in one module beside the rule-set reader, and validation's `rule-sets` member compares each loaded file with its projection where the set is authored ([ADR-075](ADR-075-generated-operational-rules.md) points 2, 5 and 6).
- **One home per computation,** and reading commands for what a component's script needs ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) points 1 and 2).
- **Each validator is a member of `pkit validate`,** whose outcome is summary lines and findings, and `error` is the one severity that fails ([ADR-058](ADR-058-validator-registry.md) points 1 and 2).
- **Rule-set files are checked by a schema the tree ships** ([ADR-056](ADR-056-backbone-file-schemas-home.md) points 1 and 3), and adding an optional key is additive, so it needs no migration ([COR-048](../../../.pkit/decisions/core/COR-048-backbone-configuration.md) point 6, [COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)).
- **A configuration block is named for its functionality and its command group** (the configuration schema's `friction` block), and ADR-075 gives this functionality one name, `rule-sets`.

## Decision

**A loaded set's front matter gives `budget`, a count of words. A project's plain rules file takes `rule-sets.plain-file-budget`. One function counts a file's words. Validation's `rule-sets` member fails a file past its budget where its owner can correct it, and reports each rules file's count as a summary line. `pkit rule-sets altered` lists each budget a change raises.**

### 1. A loaded set gives `budget` in its front matter

- **The key:** `budget`, a whole number of words of at least one, at the top of a loaded set's front matter beside `loaded: true` (refinement of ADR-075 point 6). A loaded set generates one file, so one budget in its data names that file's.
- **The schema** admits `budget` only on a set marked loaded, and refuses it on an ordinary set (COR-069 point 2).
- **The `rule-sets` member** refuses a component's loaded set that gives no `budget`, where the set is authored, by ADR-075 point 5's test of a synced copy. The schema cannot tell who owns a set, so the requirement is the member's, as ADR-075 point 6 splits what the file alone shows from what needs other files.
- **A project's own loaded set** may give one. With none, its file has no budget.

### 2. A plain project file takes `rule-sets.plain-file-budget`

- **The block:** `rule-sets`, named for the functionality and its command group, as the configuration's other blocks are. The rules area keeps the files, but the check, the report and the generator are the `rule-sets` functionality's.
- **The key:** `plain-file-budget`, a whole number of words of at least one. It names the file it bounds, the project's rules kept as a plain file (COR-068 point 7), at the path the project's include reads (ADR-075 point 6). A bare `budget` would read as every budget, while a loaded set's lives in its own data.
- **A key that bounds nothing:** where the project keeps no plain rules file, because the file is absent or the project has a loaded set of its own, the member warns that the key bounds nothing (COR-069 point 3).
- **Its writer:** `pkit config set rule-sets.plain-file-budget <N>`, or an edit to the file, in a change a person authorises. Neither install nor upgrade writes it (COR-069 point 3).

### 3. One function counts a file's words

- **The home:** one function in the module that projects a loaded set into its file (ADR-075 point 2). It takes a file's text and returns its count of words, a word being a run of characters none of which has Unicode's White_Space property (COR-069 point 1). It splits on that set of characters by name, not on whatever a language's default split treats as space, so the count is the record's on every platform.
- **Its readers:** the check, the report and the generator. No other code counts a rules file, so the three never disagree.
- **Not the prose lint's count.** project-kit's prose lint counts words for its writing rules by a different definition. The two serve different rules and stay apart. The references say so (COR-069, Implications).
- **A deployed copy** is not counted. The member counts the loaded file the copy is deployed from (COR-069 point 1).

### 4. Validation's `rule-sets` member holds the check and the report

- **The member:** `rule-sets`, its subject widened from every rule-set file to every rule-set file and every rules file: shape, ids, origins, inheritance, loaded files and their budgets. Its help text says so.
- **The failure:** `rules-file-over-budget`, an `error`, for a rules file whose count exceeds its budget. A component's file is checked only where its set is authored. A project's own file is checked in the project. The finding names the file, its count, its budget and where the budget is set, and says that raising a budget is a person's decision: trim the file, or bring the raise to the person (COR-069 point 4).
- **The missing budget:** `loaded-set-without-budget`, an `error`, for a component's loaded set that gives none, where the set is authored.
- **The key that bounds nothing:** `plain-file-budget-unused`, a `warning`.
- **The report:** one summary line for each rules file, in every project: its path, its count, and its budget or that it has none. The files a project receives are among them. They are summary lines, not `info` findings, as the Rationale says.

### 5. `pkit rule-sets generate` prints each file's count against its budget

Beside whether each file changed, the generator prints the file's count and its budget, with the room left or the words over. Whoever regenerates a file after accepting a rule sees at once whether the change needs a raise, before validation runs.

### 6. `pkit rule-sets altered` lists each budget a change raises

- **The document** gains `budgets` (refinement of ADR-057 point 2): each loaded set whose `budget` differs between the base and the head, and `rule-sets.plain-file-budget` where it differs, each with its value at both states and whether the change raised it, lowered it, added it or removed it. The text output lists the raises first, under a heading of their own.
- **Its version:** a key added, so the document's `schema_version` stays as it is (the reading documents' own rule).
- **Why there:** a budget is outside every rule's content (COR-069 point 2), so nothing that lists what a change does to the rules shows it. `altered` is the reading the rule-set reviewer and a change's other readers take, so a raise is in front of them (COR-069 point 4).

### 7. project-kit's first budgets

- **`OPS`:** `budget` at the word count of `.pkit/rules/core.md`, by point 3's function, on the default branch the build lands on.
- **project-kit's `project.md`:** project-kit sets `rule-sets.plain-file-budget` at the file's count when the build lands. #2262 asks for a budget a project sets, and project-kit's own is that budget at work in the source.
- **No room above the count.** A first budget at the file's size makes the check pass from the day it lands, and makes the next growth a raise a person authorises (COR-069 point 4).

## Rationale

**Why `budget` in a loaded set's data.** COR-069 puts the budget there. One key at the top of the front matter, beside `loaded`, keeps it apart from every rule's data, so changing it is no rule's change. A loaded set generates one file, so the key needs no file's name.

**Why `rule-sets.plain-file-budget`.** The block's name follows the functionality, as `friction`'s does, and ADR-075 gave this functionality its name. The key names the plain file because that is the only file it bounds, and a reader of the configuration should not take it for every budget.

**Why one counting function.** The check, the report and the generator would otherwise each count, and could come to disagree, so that the generator reports room the check then denies (ADR-057, one home per computation). Splitting on White_Space by name, not by a language's default, keeps the count the record's.

**Why the `rule-sets` member, not a member of its own.** The budget belongs to the loaded file, whose match with its set the member already checks. It runs after `configuration` (ADR-058 point 3), so the key it reads is already checked for shape. It already reads the rule-set discovery that the warning for an unused key needs. A member of its own would split one subject across two members. The member's subject has widened before, to the loaded file's match with its set, and its help text names the widened subject rather than leaving it implicit.

**Why summary lines, not `info` findings.** An `info` finding states a fact (COR-055 point 5, ADR-058 point 2), so either form could carry a file's count. The member already reports its counts as summary lines, and a count printed for each rules file on every run belongs with those. A reader scans the findings for what needs a decision, and a line on every run among them would bury the one that does.

**Why the generator prints the count.** The person or agent that just accepted a rule runs the generator next. That is where a raise is needed, before validation and before review.

**Why `altered` lists a raise.** A raise is a person's decision (COR-069 point 4), and a raise that nothing lists is seen only by a reviewer who happens to read that line of the diff. `altered` is the one reading of what a change alters, so a raise listed there reaches its readers with no new command.

**Why first budgets with no room.** Room above the count would be growth no change decided. The check passes on the day it lands, and every growth after it is a raise.

### Alternatives considered

- **A member of its own, `rules-budget`.** Not taken: it would split the loaded file's checks across two members.
- **The report as `info` findings.** Not taken: the member reports its counts as summary lines, and a finding on every run would bury the findings that need a decision.
- **A block named `rules`, for the rules area.** Not taken: the configuration's blocks are named for their functionality, and this one's is `rule-sets`.
- **A key named `budget` in the block.** Rejected: it would read as every budget.
- **Counting with the prose lint's word count.** Rejected: it is project-kit's own, for its writing rules, and counts by another definition.
- **A command of its own that lists raised budgets.** Rejected: `altered` already reads the change for its readers.
- **First budgets with room for a few rules.** Rejected: room above the count is growth no change decided. A later change that trims the rules chooses the room it keeps (COR-069 point 4).

## Implications

- **The build of #2262** realises this record:
  - the schema's `budget` on a loaded set, refused on an ordinary one
  - the configuration schema's `rule-sets` block and its key, and the configuration reference's entry naming COR-069 as its owner
  - the counting function, the member's three findings and its summary lines, and its help text
  - the generator's count, and `altered`'s `budgets`
  - `OPS`'s `budget` and project-kit's key, at the counts when it lands
- **Tests:**
  - a file within and past its budget
  - a component's set without a budget where authored, and in a project that receives it
  - an ordinary set with a budget, refused by the schema
  - the key bounding nothing
  - the summary lines in a project that receives `OPS`
  - the count on text with non-ASCII white space
  - `altered` listing a raise, a lowering, an addition and a removal
- **References to update:**
  - the schemas README's "Rule-set files" key table and its "Loaded sets" section: `budget`
  - the rules README: where each budget is set, how a change raises it, and, in its conversion steps, that converting a plain file moves its budget from the key into the set. It also anchors COR-069 and this record.
  - the CLI reference's `validate` section: the member's findings and summary lines, and that this count differs from the prose lint's
  - its configuration table: the key and its owner
  - its `rule-sets generate` and `rule-sets altered` entries
- **Forward pointers.** COR-051 point 2 and COR-068 point 1 point to COR-069, and ADR-075 point 6 and ADR-057 point 2 to this record, once each is accepted.
- **With #2269.** Whichever of #2262's build and #2269's lands second gives the capabilities' loaded sets their `budget`, or adds the forward pointer the other record awaits.
- **Changeset:** one backbone `minor`, for a new key, a new configuration key, new findings and new output. No migration. Adding an optional key is additive (COR-048 point 6, COR-010), and the requirement on a component's set binds only where the set is authored (COR-069 point 5). Today the only component loaded set is the backbone's, authored in the methodology's source.
- **Stands on these records:** COR-010, COR-048, COR-051, COR-055, COR-057, COR-068, COR-069, and ADR-056, ADR-057, ADR-058 and ADR-075.
