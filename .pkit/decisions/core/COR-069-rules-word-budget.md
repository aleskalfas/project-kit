---
id: COR-069
title: Each rules file a session loads stays within a word budget
status: proposed
date: 2026-10-29
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every session reads its rules files whole, so each word in them is paid for in every session. Each such file gets a budget, the most words it may hold, set by whoever owns the file. Validation fails a file past its budget where its owner can shorten it, so a larger file is a choice someone makes in a change, not drift. A component keeps the budget of its loaded set's file in the set's own data, and must give one. A project may give the budget of its own rules file in its configuration.

## Context

Operational rules are kept in loaded rule sets, and the file a session loads is generated from its set (COR-068 point 3). A project's own rules may stay a plain file, loaded as it stands (COR-068 point 7). A session reads each of these files whole at its start, so every word in them takes room in every session's context.

Nothing bounds their size. Each rule added is reviewed on its own, and none of its reviews sees what the whole file costs. A rule that carries detail its record already holds is paid for in every session, and the file grows a rule at a time with no change deciding that it should. A capability that ships a loaded set, once a record lets one (COR-068 point 4), adds a file a project receives and cannot shorten.

COR-068 already keeps a loaded set's front matter, its origins and its retired and proposed rules out of the loaded file. So what a session pays for is the loaded file alone. No record says how large such a file may be, how it is measured, or who decides.

## Decision

**Each rules file that sessions load has a budget in words, set by the file's owner. Validation fails a file past its budget, where its owner can correct it. A component's loaded set holds its budget in its own data and must hold one. A project gives the budget of its own rules file in its configuration, and may give none.**

### 1. What a budget measures

- **A rules file** is a file of operational rules that sessions load at their start: the loaded file of a loaded set (COR-068 point 3), or a project's rules kept as a plain file (COR-068 point 7).
- **Its budget** is the most words it may hold. A word is a run of characters between whitespace. The whole file is counted, as a session reads it.
- **What the file does not hold costs nothing.** A loaded set's front matter, and its proposed, superseded and withdrawn rules, are not in its loaded file, so they do not count.
- **Each file has a budget of its own.** None is set on the sum of the files a session loads.

### 2. A component's loaded set holds its budget, and must

- **Where:** each loaded set a component ships gives its loaded file's budget in the set's own data, beside its rules' data (COR-051 point 2).
- **Required:** a component's loaded set without a budget fails validation where the set is authored. Every rules file a project receives by sync is then held to a budget its author keeps.
- **Raised on purpose:** a change that needs more room raises the budget in the set's data, in the same change. The diff shows the raise beside the rule that needs it. The budget is no rule, so a change to it alone requires no new major version (COR-051 point 7).

### 3. A project gives its own rules file's budget in its configuration

- **The key:** a key of the backbone configuration, which this record owns (COR-048 point 2), gives the budget of the project's own rules file in words. It holds whether that file is plain or generated from the project's own loaded set.
- **Its default:** with the key absent, the project's rules file has no budget, and nothing is checked (COR-048 point 3).
- **One place:** a project's own loaded set gives no budget in its data. Validation refuses one there, naming the key.
- **Its writers:** a change to the configuration file, and the backbone's command that sets a key, each with consent as COR-048 point 5 asks. No install, sync or upgrade writes it.

### 4. Validation fails a file past its budget, where its owner can correct it

- **The finding:** a rules file holding more words than its budget is a finding at the failing severity (COR-055 point 5). It names the file, its count, its budget and where the budget is set.
- **A component's file** is checked where its set is authored, as its match with its set is (COR-068 point 3). A project that receives the file by sync is not checked for it, since it cannot correct a file it receives (COR-055 point 1).
- **A project's own file** is checked in the project, against the key's budget.

## Rationale

**Why a budget at all.** Every session pays for every word of its rules files, and the cost grows with each rule added. The review of a rule judges the rule, not the file it lands in, so nothing sees the total until it is large. A budget turns growth into a line of the diff that someone wrote and a person sees.

**Why a failing finding, not a warning.** A word count is deterministic, not a reading of prose, so failing on it fails for the right reason (COR-055, "Why exactly one fails"). A warning would let the file grow past its budget unchecked, which is the drift a budget exists to stop.

**Why words.** A rule is a paragraph, and often a single line, so a count of lines measures almost nothing. Words follow what a reader and a session read. A count of tokens would depend on a model's tokenizer, so one budget would mean different sizes from one harness or model to the next.

**Why a budget per file, not one on everything a session loads.** Each file has one owner, who alone can shorten it. A budget on the sum would fail a project for the backbone's or a capability's growth, which it cannot correct in its own files (COR-055 point 1). What a project controls of the files it receives is which capabilities it installs.

**Why a component's budget sits in its set's data.** The budget belongs to the file the set generates, and the set's front matter is where its data lives (COR-051 point 2). A component cannot write a project's configuration, and a capability adds no key to it (COR-048 point 2). In the set, a raised budget sits in the same diff as the rule that needs the room, before the person who accepts that rule.

**Why a component must give one.** A project receives a component's rules file by sync and cannot shorten it. A budget its author must keep is the one bound on what an upgrade, or installing a capability, adds to every session.

**Why a project's budget is a key.** The budget is the project's declaration to the backbone about its own sessions, the kind of fact its configuration holds (COR-048). One key serves the file in either form, so converting a plain file into a loaded set moves nothing. A plain file has no data of its own to hold it, and front matter in a plain file would be loaded into every session.

**Why a project's budget is optional.** The context the project's own file takes is the project's to spend. The methodology bounds what it ships, and leaves the project to choose whether to bound its own.

### Alternatives considered

- **A budget in lines.** Rejected: a rule is often one line.
- **A budget in tokens.** Rejected: it would measure a model's tokenizer, not the file.
- **One budget on everything a session loads.** Rejected: no owner can correct it, and it fails a project for files it receives.
- **Core's budget in the backbone's code or its reference.** Rejected: a raise would sit apart from the rule that needs it, and no other loaded set could use the same form.
- **A project's budget in its own loaded set's data.** Not taken: a plain file has no data to hold it, and converting the file would move the budget.
- **A budget optional for a component's set.** Rejected: a project would receive a file that nothing bounds.
- **A check of each change that reports a raised budget.** Not taken: the diff already shows the raise, to the reviewers and to the person who authorises the merge.

## Implications

- **The rule-set schema** gains an optional budget on a loaded set. Validation requires it on a component's loaded set where the set is authored, and refuses it on a project's own. COR-051 point 2 and COR-068 point 1 gain forward pointers to this record.
- **The backbone configuration's schema** gains the key, and the CLI reference's configuration table names it with this record as its owner (COR-048 point 2).
- **The CLI reference** says which validator holds the check and what its finding says. The rules area's reference says where each budget is set and how a change raises it.
- **Core's loaded set** takes as its first budget the size of its loaded file when this record is carried out, so the check passes from its first run. A change that trims the rules lowers it.
- **A capability's loaded set,** once a record lets a capability ship one (COR-068 point 4), gives its budget from its first version.
- **No migration.** The key is optional, and its absence means no budget (COR-048 points 3 and 6). The one component loaded set that exists is authored where the methodology is, so no project is failed by the requirement (COR-010).
