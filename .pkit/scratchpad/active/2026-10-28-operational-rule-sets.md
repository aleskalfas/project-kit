---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-28
---

# Operational rules as a rule set

**The question:** should the operational rules that every session loads (`.pkit/rules/core.md`, `.pkit/rules/project.md`) become rule sets under COR-051, rather than gaining an id family of their own?

The answer decides #2260 (each operational rule keeps its number for good). #2260 is paused until this note settles, since ids it gives now would change a second time if the rules later become a rule set. The maintainer is discussing a similar question in another clone, so this note is shared between the two.

## Where this came from

#2260's first design, reviewed by critic and architect on 28 October, gave operational rules an id family of their own:
- **Ids:** `RUL-NNN` for core and a second prefix for project, the number kept, so core rule 19 became `RUL-019`.
- **Form:** a heading per rule (`### RUL-016 — Title`) under the existing sections.
- **Retirements:** listed outside the loaded files, the core layer's in the rules README.
- **Checks:** ids and retirements in `pkit validate`, renumbering against the base in the numbering check.
- **Old citations:** "core rule N" kept as an alias.
- **A new core record,** refining COR-058 point 10.

Asked how rules could be grouped, such as general software-engineering rules with a Python specialization, the answer was that rule sets already do that (COR-051 point 7). The maintainer then pointed out that rule sets, used until now for how documents are written, could hold the operational rules too. Most of what the first design rebuilt already exists there.

## What is already known

**Operational rules today:**
- `core.md` holds rules 1 to 22 and `project.md` rules 1 to 4, numbered lists under H2 sections. Every session loads both through the host `CLAUDE.md`'s `@`-include. Core rule 13 forbids an H1 in an included file.
- **Ownership:** `core.md` is backbone-owned and synced (COR-001). `project.md` is the project's (COR-014, and `.pkit/lifecycle/ownership.py` exempts that one path).
- **Records that keep them apart:** COR-051 point 1 says they are "a different thing that shares the word, and are not governed by this record". COR-058 point 10 says they "keep their own numbering".
- **Analysis:** the glossary's `TERM-operational-rule` and the domain-model view `010-the-system-and-its-methodology.md` both say they carry no id, origin or status.
- **Cited by number** in about 68 lines of live text across 41 files, counting `.pkit/`. With answer files, scratchpad notes and changesets: 160 lines in 61 files. The three stale citations #1687 found are in project-management DEC-045 (lines 212 and 233, "rule-18" for today's rule 19) and `2026-08-06-report-command-upstream-feedback.md` line 94.
- **Earlier thinking:** `2026-10-08-part-anchors.md`, "Found on the way" item 4, says their permanence would need headings and no front matter, with the rules README as its home.

**Rule sets today (COR-051, accepted):**
- **In use:** `WRITE` (`tech-docs/rule-sets/writing.md`), `ANA` (`tech-docs/rule-sets/analysis.md`, inherits `WRITE@2` and `software-analysis:SAN@1`), and `SAN`, shipped by software-analysis. Project rule 3 points agents at `WRITE` and `ANA`.
- **What they give:**

| Operational rules need | Rule sets have (COR-051) |
|---|---|
| Permanent ids | `RS-<SET>-NNN`, never renumbered or reused (point 3) |
| A retired rule kept, with where it went | superseded with a successor, or withdrawn, kept in place (point 4) |
| Validation | `pkit validate`'s `rule-sets` member |
| A reason for each rule | an origin: the decider's words, or a record (point 5) |
| Core and project layers | method sets and project sets (point 6) |
| Grouping and specialization | inheritance, pins, extension points and fills (point 7) |
| Acceptance by a person | proposed or accepted (point 4, COR-066) |
| A reviewer | `rule-set-reviewer`, reading `pkit rule-sets reach` and `altered` |

- **Their shape:** data in front matter (status, origin, fills, anchors), prose in the body, one section per rule headed `### RS-<SET>-NNN — Title` (point 2).
- **What they bind on:** artefacts, files selected by a scope's paths and types (point 2). A method set has no scope, and binds only through a project set that inherits it (point 7).

## Forces

- **One mechanism, not two.** A second id, retirement and check scheme beside COR-051's is the duplication COR-007 warns against, and two families to cite.
- **The loaded context is small and meant to shrink.** #2261 (the rules every session loads are short again) and #2262 (`pkit validate` holds the rules to a size budget) follow #2260. Front matter, retired rules and origins in the loaded file work against both.
- **Ids must be settled once.** Every citation, in this repository and in adopters, moves with the id form.
- **Agents read the file whole,** through the include. An agent needs the statement, not the data.
- **COR-051 is foundational and accepted,** and its point 1 was a deliberate choice. Reopening it is a refinement a person accepts.
- **Grouping is wanted beyond core and project,** such as a capability's rules for the agents that work in its area, and a language's rules on top of general ones.

## The fit problems

### 1. What an operational rule binds on

A rule-set rule binds on artefacts its scope selects. "Pause before a destructive operation" binds on what an agent does in a session, and on no file. Options:
- **a. A second kind of target:** a set declares that it binds on sessions, or on agents, instead of artefacts. Point 7's reach answers which rules bind on each session.
- **b. Bind on the agent definitions:** the rules bind on the agent files they govern (`.pkit/agents/**`, `.claude/agents/**`), so reach works as today. This bends what "binds on" means, since the rule is about behaviour, not the file's text.
- **c. A set with no reach at all:** COR-051's ids, statuses, origins and retirements, but not point 7. Loading decides where it applies (problem 2).

### 2. What a session loads

The loaded text should be the accepted statements only. Options:
- **a. Load the rule-set file as it is.** Front matter and retired rules go into every session. This works against #2261 and #2262.
- **b. Generate the loaded file from the set.** The rule set is the source, and `core.md` becomes a generated projection: accepted rules only, heading and statement, no front matter. Sync or the adapter writes it, and a check fails when it is stale. COR-028's permission model is the precedent: the model is authoritative, and harness state is generated from it.
- **c. Keep data elsewhere.** The loaded file holds headings and statements, and the data lives in a sidecar. COR-051 point 2 and COR-063 forbid a sidecar.

### 3. Layers and grouping

- **Core:** a method set the backbone ships, such as `OPS`. Core rule 19 becomes `RS-OPS-019`. The name is a placeholder.
- **Project:** a project set that inherits the core set, as `ANA` inherits `WRITE`. Today's `project.md` becomes it.
- **A capability:** a method set of its own, cited `software-engineering:RS-SWE-…`, loaded only in projects that install it.
- **Specialization:** a set inheriting another and filling its extension points.
- **Open:** does a session load every operational set installed, or only those for its agent or the files it touches? Loading by agent or files is the deferred "slicing rules by the files they govern" the #2260 notes mention.

### 4. What changes

- **COR-051:** points 1 (operational rules governed), 2 (a target that is no artefact, if 1a), 6 (where the operational sets live), and possibly 7.
- **COR-058 point 10:** operational rules no longer keep their own numbering.
- **COR-014:** the split test stays; the core / project rules files are now sets.
- **Adapter and sync:** what generates and includes the loaded files, if 2b.
- **The glossary term and its view,** the rules README, `CLAUDE.md`'s includes, and about 68 citations, unless "core rule N" stays an alias of `RS-OPS-0NN`.
- **Adopters:** their `project.md` is a numbered list they own. It needs converting, or toleration as list form until converted (COR-058 point 9's precedent), and a migration if the file moves or changes shape (COR-010).

## Candidate alternatives

- **A. Rule sets, generated loaded file.** Operational rules become method and project rule sets (problem 3), binding by target kind (1a or 1c), and the loaded files are generated from them (2b). One mechanism, a small loaded context, and grouping for free. It reopens COR-051 and adds a generator.
- **B. An id family of their own** (#2260's first design, above). Small, fits the Task as filed, no foundational record reopened. Leaves two mechanisms, and its ids would change if A follows later.
- **C. B now, shaped for A later.** Give the ids A would give (`RS-OPS-019` style) without the rest of COR-051, so a later move to A changes no id. This only works if A's set name and numbering are settled now.
- **D. Permanent numbers, no new ids.** Keep "core rule N" as the citation and make the number permanent. No rewrite, but no id a tool can read in the file, which the maintainer did not want.

## Open questions

1. Is a session a target of rule sets (1a), or do operational sets reach nothing (1c)?
2. Is the loaded file generated (2b), and by what: sync, the adapter, or a command of its own?
3. The core set's name, and whether "core rule N" stays an alias.
4. What the other clone's discussion decided or found. Merge it here before any record is drafted.
5. Does #2260 wait for this note's record, or land C first?

## Review

Not reviewed yet. Critic and architect reviewed the first design (B) on 28 October. Their findings that carry over to A:
- **Shared with A:** a core record decides it; headings rather than paragraphs; retired rules kept out of the loaded file; a core rule never names a project successor; the check skips answer files, scratchpad notes, changesets and superseded records; citations read from prose are warnings.
- **The architect's alias:** "core rule N" stays valid as an alias of the new id, so history is never rewritten.
