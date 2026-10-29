---
id: COR-069
title: Each rules file a session loads stays within a word budget
status: proposed
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every session reads its rules files whole, so each word in them is paid for in every session. Each such file may have a budget, the most words it may hold, set by whoever owns the file. Validation fails a file past its budget where its owner can shorten it, so a larger file is a raise a person authorises, not drift. A loaded set keeps its budget in its own data, and a component's loaded set must give one. A project with a plain rules file may give its budget in its configuration. Validation also reports, without failing, what each rules file holds against its budget, so a project sees what every file it loads costs.

## Context

Operational rules are kept in loaded rule sets, and the file a session loads is generated from its set (COR-068 point 3). A project's own rules may stay a plain file, loaded as it stands (COR-068 point 7). A session reads each of these files whole at its start, so every word in them takes room in every session's context.

Nothing bounds their size. Each rule added is reviewed on its own, and none of its reviews sees what the whole file costs. A rule that carries detail its record already holds is paid for in every session, and the file grows a rule at a time with no change deciding that it should. A capability that ships a loaded set, once a record lets one (COR-068 point 4), adds a file a project receives and cannot shorten.

COR-068 already keeps a loaded set's front matter, its origins and its retired and proposed rules out of the loaded file. So what a session pays for is the loaded file alone. No record says how large such a file may be, how it is measured, or who decides.

## Decision

**Each rules file that sessions load may have a budget in words, set by the file's owner, and a component's must. Validation fails a file past its budget where its owner can correct it, and reports each file's size against its budget everywhere. A loaded set holds its budget in its own data. A project's plain rules file takes its budget from the project's configuration. A budget is raised only in a change a person authorises.**

### 1. What a budget measures

- **A rules file** is a file of operational rules that sessions load at their start: the loaded file of a loaded set (COR-068 point 3), or a project's rules kept as a plain file (COR-068 point 7).
- **Its budget** is the most words it may hold. A word is a run of characters none of which is white space, as Unicode's White_Space property defines it. The whole file is counted, every character of it as written.
- **Each file is counted as itself.** What an include in it pulls in is counted in the file it comes from, if that is a rules file, and nowhere else.
- **What the file does not hold costs nothing.** A loaded set's front matter, and its proposed, superseded and withdrawn rules, are not in its loaded file, so they do not count.
- **Each file has a budget of its own.** None is set on the sum of the files a session loads.
- **Out of scope:** the host file a session loads, and the descriptions of skills and agents a harness lists in each session. The host file holds what an adapter merges into it beside the project's own instructions, so its owner cannot shorten all of it. The descriptions are a harness's index, sized by their own authors. Neither is a rules file.

### 2. A loaded set holds its budget in its own data

- **Where:** a loaded set gives its loaded file's budget in the set's own data, beside its rules' data (refinement of COR-051 point 2). An ordinary rule set gives none, and validation refuses one there, since it generates no file a session loads.
- **Each form:** where one set is projected into more than one loaded file, one for each form a harness's include requires (COR-068 point 3), each file is held to the set's budget.
- **A component's set must give one.** A component's loaded set without a budget fails validation where the set is authored. Every rules file a project receives from a component is then held to a budget its author keeps, however a capability's loaded file is delivered.
- **A project's own set may give one.** With none, its loaded file has no budget, and nothing is checked.
- **Outside the rules' content.** The budget is none of a rule's fields and no part of its statement, so it is no part of any rule's content (COR-050), as a check's declaration is not (COR-051 point 2). Changing it changes no rule, requires no new major version (COR-051 point 7) and flags nothing anchored to a rule.

### 3. A project's plain rules file takes its budget from a key

- **The key:** a key of the backbone configuration gives the budget, in words, of the project's own rules file kept as a plain file. This record owns the key (COR-048 point 2).
- **Its default:** with the key absent, the plain file has no budget, and nothing is checked (COR-048 point 3).
- **A key that holds nothing:** where the project has no plain rules file, because it has none or keeps its rules as a loaded set, a key that is set bounds nothing. Validation warns of it, so one budget has one place.
- **Its writers:** an install and a change a person authorises, each with consent as COR-048 point 5 asks. An upgrade does not write it.

### 4. A budget is raised only in a change a person authorises

- **A new rule** that needs room raises the budget in the change in which a person accepts the rule (COR-051 point 4, COR-066 point 1). The raise is before that person beside the rule that needs it.
- **Any other raise,** such as for an edit to an accepted rule or for a key, lands only in a change a person authorises to reach the default branch. An agent does not raise a budget on its own to make validation pass.
- **Slack fails nothing.** A budget is a ceiling, not a target. The change that trims a file lowers its budget, and the report of point 5 shows any room left.

### 5. Validation fails a file past its budget where its owner can correct it, and reports every file

- **The failure:** a rules file holding more words than its budget is a finding at the failing severity (COR-055 point 5).
- **A component's file** fails only where its set is authored, as its match with its set does (COR-068 point 3). A project that receives the file is not failed for it, since it cannot correct a file it receives (COR-055 point 1).
- **A project's own file** fails in the project, against its budget.
- **The report:** in every project, validation also reports each rules file's count, against its budget where it has one, at a severity that states a fact and never fails (COR-055 point 5). The files a project receives are among them, so a project sees what each file it loads costs, and how much room a trim left.

## Rationale

**Why a budget at all.** Every session pays for every word of its rules files, and the cost grows with each rule added. The review of a rule judges the rule, not the file it lands in, so nothing sees the total until it is large. A budget puts the file's new total in the diff of every change that grows it, and point 4 makes each raise a change a person authorises.

**Why a failing finding, not a warning.** A word count is deterministic, not a reading of prose, so failing on it fails for the right reason (COR-055, "Why exactly one fails"). A warning would let the file grow past its budget unchecked, which is the drift a budget exists to stop.

**Why words.** A rule is a paragraph, and often a single line, so a count of lines measures almost nothing. A count of tokens would depend on a model's tokenizer, so one budget would mean different sizes from one harness or model to the next. A count of characters or bytes tracks what a session pays more closely than words do, since a link, a path or an id counts as one word however long it is. Words still win, because a budget is a ceiling people set and raise: an author writes and trims in words, and a raise of forty words says what it allows where a raise of three hundred characters does not. The cost is that long links and ids are undercounted. Gluing words together to fit a budget is for the writing rules and the reviewers to catch, not for the count.

**Why a budget per file, not one on everything a session loads.** Each file has one owner, who alone can shorten it. A budget on the sum would fail a project for the backbone's or a capability's growth, which it cannot correct in its own files (COR-055 point 1). What a project controls of the files it receives is which capabilities it installs, and the report shows it what each one costs.

**Why a loaded set's budget sits in its data.** The budget belongs to the file the set generates, and the set's front matter is where its data lives (COR-051 point 2). A component cannot write a project's configuration, and a capability adds no key to it (COR-048 point 2). In the set, a raised budget sits in the same diff as the rule that needs the room, before the person who accepts that rule. A project's own loaded set takes the same form, so every rule-set file keeps one shape and one validation, as COR-068 keeps its version.

**Why a component must give one.** A project receives a component's rules file and cannot shorten it. A required budget does not stop the author from growing the file. It makes each growth a raise that a person authorises, and the report shows every project that receives the file what it costs.

**Why a project's plain file takes its budget from a key.** A plain file has no data of its own, and front matter in it would be loaded into every session. The budget is the project's declaration to the backbone about its own sessions, the kind of fact its configuration holds (COR-048). Once the project converts the file into a loaded set, the budget moves into the set's data with the origins the conversion writes, and the key then holds nothing, which validation says.

**Why a project's budget is optional.** The context the project's own file takes is the project's to spend. The methodology bounds what it ships, and leaves the project to choose whether to bound its own.

**Why a raise is a person's.** A budget an agent could raise on its own would bound nothing, since the agent that needs room is the one that would raise it. For a new rule, the raise rides on the person's acceptance of that rule, a review that already happens. For any other raise, the person who authorises the change is the one who sees the diff.

**Why a report that never fails.** A project needs to see what the files it receives cost, but cannot correct them, so their size is a fact for it, not a finding against it (COR-055 point 1). The report also shows the slack a trim leaves, which a ceiling alone hides.

### Alternatives considered

- **A budget in lines.** Rejected: a rule is often one line.
- **A budget in tokens.** Rejected: it would measure a model's tokenizer, not the file.
- **A budget in characters or bytes.** Not taken: closer to what a session pays, but harder to write and raise by, as "Why words" says.
- **One budget on everything a session loads.** Rejected: no owner can correct it, and it fails a project for files it receives. The report shows the files a project loads without failing it.
- **Core's budget in the backbone's code or its reference.** Rejected: a raise would sit apart from the rule that needs it, and no other loaded set could use the same form.
- **A project's budget in the key whatever form its rules take.** Not taken: a project's own loaded set would then be validated unlike every other loaded set, and its budget would sit apart from the rule that needs the room.
- **A budget optional for a component's set.** Rejected: a project would receive a file that nothing bounds.
- **A check that fails on slack, or reports it as a warning.** Rejected: a ceiling with room is no broken invariant, and the report already shows the room.
- **A check of each change that reports a raised budget.** Not taken: the raise is one line of the diff, giving the new total, and for a new rule it lands in the change in which a person accepts that rule.

## Implications

- **The rule-set schema** gains an optional `budget`, a count of words, on a loaded set, and refuses one on an ordinary set. Validation requires it on a component's loaded set where the set is authored. COR-051 point 2 and COR-068 point 1 gain forward pointers to this record.
- **The backbone configuration's schema** gains the key `rules.budget`, and the CLI reference's configuration table names it with this record as its owner (COR-048 point 2).
- **The CLI reference** says which validator holds the check and the report, and what their findings say. It notes that this count of words differs from any word count a project's writing rules use. The rules area's reference says where each budget is set and how a change raises it.
- **Core's loaded set** takes as its first budget the size of its loaded file when this record is carried out, so the check passes from its first run. A change that trims the rules lowers it.
- **A capability's loaded set,** once a record lets a capability ship one (COR-068 point 4), gives its budget from its first version.
- **No migration.** The key is optional, and its absence means no budget (COR-048 points 3 and 6). The one component loaded set that exists is authored where the methodology is, so no project is failed by the requirement (COR-010).
