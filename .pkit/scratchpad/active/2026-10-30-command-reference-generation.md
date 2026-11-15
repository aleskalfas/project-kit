---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-30
---

# Generating the command reference from the commands' own definitions

## The question

Which parts of the command reference does a generator write, from which source, onto which pages, and what check keeps them fresh? What do the hand-written pages keep? And what does that mean for the accepted records that name the command line's README its spec (#2024)?

- **Why it is asked.** The reference, `.pkit/cli/README.md`, is one hand-written page of about 83,000 words today; #2024 counted 75,700 a few weeks ago. Each command's usage, arguments and options already live in the code. A hand-written copy drifts, and each review re-checks it against the code.
- **What follows from it.** The documentation rework (EPIC #1928) has to decide how to split the command line's page. This note sets the split's shape. Whether the pages restate usage is the one part that waits on the maintainer's answer.
- **It decides nothing.** The maintainer decides. A record, or a refinement of one, then carries the decision, and is accepted before any slice rests on it.
- **Scope.** The backbone's commands, defined with click in `src/project_kit/cli.py`, are the first subject. The capabilities' commands, argparse scripts under `.pkit/capabilities/*/scripts/`, are measured too, and answered in their own section.

## What is decided already

**Where a command's detail is specified.** Five accepted records place it in `.pkit/cli/README.md`:

- **COR-004:** "The current set of commands, their flags, or output formatting" live there as the area's specification, and a new command is documented there (its Context and Implications). The principle behind it: the list is the spec's, not a record's.
- **COR-005:** the authoring commands are "documented in `.pkit/cli/README.md` alongside the consumption commands", and what they stamp "in detail" is there.
- **COR-012:** "the full per-command surface (flag set, exact verb shapes)" is specified in the README's "Authoring commands" section.
- **COR-021:** the README documents the dispatcher's surface, its error wording and the shape of its help output. A capability declares each command in its `commands:` tree with a one-line `help:`. Standardising each script's own `--help` is left to "follow-up records per COR-007 if recurrence justifies them".
- **PRJ-008:** the `report` surface "is spec'd once in `.pkit/cli/README.md`".

The decisions README, PRJ-003 and PRJ-004 name the file in passing too. None of these says the spec must be written by hand: each fixes where it lives.

**Where pages live, and how they link.**

- **Guides and references.** Guides for people sit in `docs/`; references for agents sit under `.pkit/`, beside what they describe, and ship. A reference holds "what each command does and how it fails" (ADR-069 point 1).
- **A README leads its folder** and is its stable address. A lookup page takes a topic name (ADR-069 points 3 and 4).
- **A generated file kept fresh by a test is no page, and sits in a folder of its own** (ADR-069 point 5, on living-docs DEC-001 point 4).
- **A move keeps every address.** A section that leaves a page keeps its old address there, as an HTML id before a sentence that links where it went (`RS-REWORK-002`).
- **A capability's page reaches a backbone page only through its area's README,** or a section of it, or names it by its role (`RS-REWORK-004`, from ADR-069 point 4). So a capability's README may link `.pkit/cli/README.md#…`, and no other page of the CLI area.
- **One home for each fact,** and only what a page anchors grounds what it says (`RS-LDOC-002`, `RS-LDOC-001`).

**What else reads the reference today.**

- **living-docs' mention check** takes `.pkit/cli/README.md` as the file that documents a backbone command, and suggests the heading there that names it (`CLI_REFERENCE` in the capability's `scripts/_lib/mentions.py`).
- **The friction configuration** counts `.pkit/cli/**` as surface (`.pkit/project/config.yaml`, `friction.surface`).
- **A code anchor covers a whole file.** An anchor on one function or class is open work (#2100).

**Four precedents generate text and check it:**

- **software-analysis's overview** is a held document in a folder of its own. It carries a fingerprint of what it draws, and validation fails it when stale (software-analysis DEC-003 point 8, #1805).
- **The rules file a session loads.** One function projects the backbone's loaded rule set into `.pkit/rules/core.md`. A `pkit` command writes it, and a member of `pkit validate` fails a file out of step, only where the set is authored (ADR-075 points 2 and 3). It is a `pkit` command because a project may author a loaded set of its own.
- **The pages' contents lists.** `scripts/page_contents.py` writes a list between two markers inside a page, and `scripts/check.sh` fails a stale one (#2053). A rule set names the script as the check of the rule's part it stands in for (`RS-REWORK-005`).
- **The reference's coverage test.** `tests/test_cli_reference_coverage.py` reads the backbone's click tree and holds the reference to the same commands and options, both ways (#2029).

The pages' console examples are also run as tests, and `--update` rewrites their output (doc-examples, #1807, #2098).

## The measurements

Measured on main at `f25a4107`, with scripts kept in the agent workspace. Words are runs of non-space characters.

### What the reference holds

The body below the front matter holds 82,695 words. Each line was sorted by the section it sits in: a section headed by a command in code, as the coverage test reads one, or any other section.

| Part of the page | Words | Share | Does the code hold it? |
|---|---|---|---|
| Signatures: the headings' command lines and the Surface table's first column | 1,095 | 1.3% | Yes, exactly |
| Bullets that open with an option | 3,417 | 4.1% | A shorter form: each option's help |
| Other sentences, under a command, that name an option | about 2,950 | 3.6% | Partly |
| The Surface table's summaries | 9,451 | 11.4% | Partly: each command's first paragraph of help |
| The Surface table's "Mutates?" and "Idempotent?" columns | 867 | 1.0% | No |
| A command's behaviour: what it reads, writes and refuses, its exit codes, the rules it keeps | about 49,400 | 59.7% | No; the help holds a summary |
| Sections no command heads: installing, the configuration file, the friction concepts, standard flags, output conventions, failure mode | 14,506 | 17.5% | No |
| Other headings, and fenced blocks | 209 | 0.3% | — |

The table scaffolding makes up the remaining 1%. The "other sentences" row is a subtraction of two counts that overlap, so it is rough.

- **At most a fifth of the page is what the code holds,** about 17,000 words, and most of that only in a shorter form. The true share is lower: some Surface cells hold long behaviour.
- **About three quarters is behaviour and concepts,** which the code cannot give.
- **So generation fixes drift, not size.** The size is answered by splitting the page.
- **The Surface table is two things.** Its 140 rows hold 11,685 words. 70 rows, 5,983 words, repeat a command that also has a section. The other 70 rows, 5,702 words, are a command's only home: 64 of the backbone's 146 commands have no section of their own, and some of those rows hold long behaviour, such as `capabilities install`'s refusals.
- **The page holds almost no examples:** 132 words in fenced blocks, none under a command.

### What the code holds

- **179 commands:** 33 groups and 146 commands that run. They take 99 arguments and 303 options.
- **Every command has a help text, and every option has one.** Option help totals 5,091 words, and command help 13,938. Rendered as `--help`, the commands print 23,240 words.
- **The code's help is a second hand-written copy** of much of the behaviour. `pkit friction check --help` gives its exit codes and what it never fails on. `pkit workspace remove --help` lists what it refuses.
- **Few defaults are static.** 60 options have a default in the code, 16 a fixed set of choices, and 30 are required. Most defaults are resolved when the command runs, such as `$PKIT_CHECK_BASE` and then the default branch, and the help states them.
- **A prototype projected it.** About 100 lines turned the click tree into one Markdown file for each top-level command. Each command gets its usage line, the first paragraph of its help, its arguments, and its options with what each takes, its default and its help. The output was 34 files, 13,443 words.
- **The code's help cites project-kit's own records.** The first paragraphs alone cite an ADR or a PRJ record on 25 lines, ADR-047 and ADR-050 most. A shipped page cites only the core's and the capabilities' records (`RS-REWORK-003`). The code's help also names sections of the README in at least ten places, and `install.py`'s output names "Installing pkit on PATH".

### How the page and the code move together

- **The two change together.** Since 1 July, 168 commits on main changed `cli.py`, and 159 of them, 95%, changed the reference too.
- **40% of those changes altered a command's usage.** 68 of the 168 commits added, removed or changed an option, an argument, a command or a group, and each restated the change in the reference by hand. The other changes touched behaviour or help, which generation does not touch.
- **The drift measured is in names and omissions.** #2029 found 26 commands with no section and 33 options named nowhere, and its test now catches both. A value drifting, such as a default or a choice stated wrongly, was not measured.
- **A heading's address carries its options.** The host builds a section's address from its heading, so `friction check [--base <ref>] [--head <rev>] [--json]` becomes `#friction-check---base-ref---head-rev---json`. Other files hold 91 links and anchors into the reference's sections, in 16 files, and 37 of them carry options in the address. Since 1 July, 49 of the reference's 268 commits changed a command's heading, and 19 removed one.
- **Heading signatures have no fixed form.** Of 67 headings that name a single command, 22 list fewer options than the command takes. Some abbreviate on purpose, as `[options]` and `[flags]`; `scratchpad done` simply leaves out its `--dry-run`. 20 name a positional argument in their own style, such as `<n>` where the code says `NUMBER`. None of these is a wrong fact.
- **One page answers for everything.** The page anchors 75 paths and 46 records, so each change to any of them asks the whole page for an answer.

### The capabilities' commands

- **110 commands** in six capabilities' `commands:` trees: project-management 88, software-analysis 12, living-docs 4, demo-recording 3, which are shell scripts, doc-examples 2 and evidence 1.
- **Three hand-written copies:**
  - the `help:` of each leaf in `package.yaml`, 11,783 words in all. COR-021 calls it a one-line description, yet software-analysis's `validate` entry runs past 1,000 words.
  - each script's `--help`, 15,262 words
  - the capabilities' READMEs, 112,330 words, where guide and reference are mixed
- **The parsers are not reachable from outside.** Of 107 Python scripts, 92 build their parser inside `main()`, 12 build it in a function, and 3 use no argparse.
- **`--help` is not uniform.** All 107 answer `--help` without error, in about 15 seconds together. 83 print `usage: <script>.py`, the file's name, 21 print `pkit <capability> <verb>`, and 3 print another name.
- **argparse's layout moves.** Its text depends on the terminal's width. Python 3.13 also changed how an option with a short and a long name shows its value, and project-kit supports 3.11 and later. So captured `--help` text compares byte for byte only under one interpreter and one width.

## What stays written by hand

- **A command's behaviour:** what it reads, what it writes, what it refuses and why, what it prints, its exit codes. The code's help holds a summary, never the whole.
- **The rules a command keeps,** each resting on a record the page anchors. Generated text anchors nothing.
- **Examples,** as console fences that the doc-examples run checks.
- **Concepts across commands:** the configuration file, the friction model, standard flags, output conventions, failure mode.
- **Each page's anchors,** which ground what it says (`RS-LDOC-001`).

## Two questions, and two choices that stand apart

The issue's question splits in two:

1. **Who holds a command's usage?** That is its arguments, options, defaults and fixed choices. Either its definition alone, with the reference showing a projection, or the reference too, restating it by hand. It changes how every later change to a command is documented and reviewed, so it is the maintainer's.
2. **If the definition holds it, where does the projection sit?** In files of their own, in blocks inside the pages, as console fences, or nowhere but `--help`. This follows from the first, and belongs to an architecture record.

Two more choices hold whatever the answers. Neither depends on generation:

- **A heading names the command alone,** such as `### friction check`, so its address survives a new option. The old address stays as an HTML id. This is worth doing whichever answers are chosen.
- **The page splits into topic pages.** The page's size asks for it, and so does the blast radius of its anchors. Its costs, and the refinements of the records it owes, are listed below, apart from generation's.

## 1. Who holds a command's usage

### Yes: the definition alone, and the reference shows a projection

- **Gains:**
  - No change restates usage by hand. That was 68 of the 168 changes to `cli.py` since July.
  - The reference can never state usage the code does not have. A test of names checks only the names.
  - The 64 commands whose only home is a Surface row get a full usage entry.
- **Costs:** a generator and its check, or a pointer to `--help`, and an architecture record that holds the rule.
- **Loses:** hand-written option text where it says no more than the help. Option text that goes past the help stays by hand.
- **Where the rule lives.** Only project-kit's own source authors the backbone's commands, and no adopter acts on the rule. So it is project-kit's architecture, an ADR, not a core record (COR-014). The core records keep naming where the spec lives, and cite nothing of the ADR, since a shipped record's citation of an ADR would resolve against each adopter's own records. If the maintainer wants the rule in the core instead, it must hold for every command, the capabilities' included. COR-021 is then refined with it, and the capabilities' pages state the gap until their parsers meet it (COR-065 point 6). A core rule for the backbone's commands alone is the one shape to avoid.

### No: the reference keeps restating usage, held to the code by a wider test

The coverage test (#2029) grows to check argument names, fixed choices, required options and a fixed form for heading signatures. It already parses headings' signatures, so this extends working code.

- **Gains:** no new file, no generator, no record changes. It is the smallest change.
- **Costs:** the hand restatement goes on, 40% of `cli.py` changes. A default stated in prose, such as "Default: `$PKIT_CHECK_BASE`, else the default branch", stays unchecked.
- **Loses:** nothing, and gains little over today.

**A sequenced form of "no":** split the page now, with command-only headings, and measure real drift for a cycle. Generate later if it shows up. This is the cheapest path. It stakes the choice on a measurement this note could not make: whether stated values drift.

## 2. Where the projection sits

Each option below assumes the answer "yes" to the first question. D, the hand-written reference held by a wider test, is the answer "no" above.

### A. Fully generated pages, one per command

The help text becomes the whole reference. Each command's page is generated from its help, which grows to hold its behaviour.

- **Gains:** one home for everything a command does, in the code.
- **Costs:** about 50,000 words of behaviour move into docstrings, so `cli.py` grows from 10,300 lines to several times that. Generated text anchors nothing (ADR-069 point 5), so no change to a record asks for an answer. The rule-set reviewer judges pages, not docstrings. The help's 25 lines of ADR and PRJ citations would ship.
- **Loses:** friction on the reference, and the reviewer's reading of it. Out of the running.

### B. A generated block under each command's heading

Under each command's heading, a fenced block holds the command's usage, written by a script and checked fresh, as the contents lists are.

- **Gains:** one read per command, with usage and behaviour together. A code block is already left out by the prose lint and by the citation rule (`RS-REWORK-003`). A rule set can name the script as the check of the part it stands in for, as `RS-REWORK-005` does.
- **Costs:** 146 blocks to keep in place, one under each command. The pages grow back by about 13,000 words. Text the code wrote sits inside a reviewed page.
- **Loses:** nothing a reader needs. One block per page instead of per command would cut the markers to a few dozen, but it would lose the locality that is B's one edge over C.

### C. Generated usage files in a folder of their own

A script writes the commands' usage into files in `.pkit/cli/usage/`. The hand-written pages link each command's entry.

- **Gains:** every page stays hand-written, anchored and reviewed. It fits ADR-069 point 5 as written. The pages hold only behaviour, so they are as long as their behaviour needs and no longer.
- **Costs:** a reader opens two files for one command, or runs `--help`. It needs a generator of about 150 lines and a check. The usage files lie under `.pkit/cli/**`, the friction surface, so they need an exclusion. The help's citations of project-kit's own records ship in them, unless the build cleans them.
- **Loses:** reading usage and behaviour in one place.

### E. Nowhere but `--help`

The pages hold behaviour, and name `pkit <command> --help` for the usage. Nothing is generated.

- **Gains:** no generator and no generated file. `--help` matches the installed binary, and shows the whole help.
- **Costs:** an agent must run the binary to see a command's options. A search under `.pkit/` finds no option, and nothing can link one.
- **Loses:** usage that can be read, searched and linked offline.

### F. A console fence of `--help` in each section

Each command's section holds `$ pkit <command> --help` as a console fence. The doc-examples run, already in `scripts/check.sh`, runs it and fails a stale output, and `--update` rewrites it.

- **Gains:** no new generator, folder or markers; only accepted machinery. It shows exactly what `--help` prints. It reaches the capabilities' commands today, with no change to their scripts. An adopter can use the same pattern.
- **Costs:** the whole help lands on the page, 23,240 words for the backbone. Most of it restates behaviour the section states again in its own words, so each page would hold two copies. Output depends on the terminal width and, for the capabilities, on the Python release, so the run must fix both. About 146 more commands run in each check.
- **Loses:** one home for behaviour on the page, unless the code's help shrinks to its summary and options.

## Recommendation

**First question: yes, for the backbone's commands, held as project-kit's own architecture.** A command's usage is held by its definition alone, and the reference shows a projection of it. An ADR records the rule, not a core record (see "Where the rule lives").

- **The evidence is review cost, not broken facts.** Names already agree, since #2029. But 40% of changes to `cli.py` restate usage by hand, and each review re-checks the restatement.
- **The gain is modest,** a fifth of the page at most. The sequenced "no" is the honest alternative, and the maintainer may prefer it.

**Second question: C, with a lean generated command index in the README.**

- **The command index.** The README carries an index of every command, written between markers as the contents lists are. Each row gives the command in code, and links to its section on its topic page and to its usage entry. It holds no help text, so no citation the help carries reaches the README, and an edit to a help line does not change it.
  - It replaces the Surface table on purpose.
  - It gives every command an address in the README, which a capability's page may link (`RS-REWORK-004`).
  - It is where the old sections' addresses stay (`RS-REWORK-002`).
  - The rule set names the generator as the check of the index, as `RS-REWORK-005` names the contents generator, so the reviewer leaves that part to the script.
- **Why C over B.** C keeps text the code wrote out of every page a person reviews. The one generated part a page holds is the index, which holds only commands and links. B reads better for one command. If the maintainer weighs reading in one place above that line, B is the choice, and the rest of this note holds for it.
- **Why not F.** F duplicates behaviour on every page, unless the code's help first shrinks to a summary. If that shrinking is chosen anyway, F becomes the cheapest: no generator, and the capabilities come for free.

### What C looks like

- **The usage files.** `.pkit/cli/usage/` holds the generated usage, from the backbone's own click commands, never a capability's, leaving hidden commands and options out. Each command shows:
  - its usage line
  - the first paragraph of its help
  - its arguments
  - its options, each as an item with an address of its own, with what it takes, its default where the code has one, and its help

  Each file opens with a line saying it is generated and from what. A file holds no front matter, so it is no artefact and no page (COR-050 point 1, living-docs DEC-001 point 4).
- **One walk of the click tree.** The generator, its check and the coverage test read the commands through one function, which reads each group's `commands`, never `list_commands`, as the coverage test does today. The script holds it, and the test imports it. Otherwise the three could disagree on what counts as a command (ADR-057 point 2, one home for each computation).
- **The generator and its check: the contents lists' shape.** One script of project-kit's own writes the usage files and the README's index, with a check mode that fails on a difference and names the script. `scripts/check.sh` runs it, as it runs `scripts/page_contents.py`. That check is the test ADR-069 point 5 asks for, and the rule set can name it.
  - **Not ADR-075's shape.** `rule-sets generate` is a `pkit` command because a project may author a loaded set of its own. No adopter authors the backbone's click tree. So a `pkit` command, a `validate` member or a module under `src/` would ship code that only project-kit's source uses (COR-014).
  - **Deterministic.** It projects click's objects, never rendered `--help` text, and the ADR states the Python release the check is judged under.
- **The hand-written pages.** The README leads the folder (ADR-069 point 3). It holds the purpose line, the command index and the list of pages.
  - **What holds for every command gets a page of its own.** Standard flags, output conventions, failure mode and the refusal inside a migration go to a lookup page, such as `conventions.md`. A topic page that summarises one of them anchors that section (`RS-LDOC-002`). Anchoring a section of the README would be a cycle, since the README anchors each page it lists (ADR-069 point 3, COR-050 point 5).
  - **Topic pages follow the page's own chapters,** each with a topic name, such as `lifecycle.md`, `friction.md` and `pull-requests.md`. The rework plan settles the list, together with the modules of `cli.py` (below).
  - **To the guide.** Installing pkit, and why the command line is shaped as it is, move to the guide, `docs/cli/`.
  - **A pattern for the others.** This is the first reference under `.pkit/` with several pages, so its layout sets the pattern for the areas after it.
- **A command's section** links its usage entry. It names an option only where the option's behaviour goes past its help line.
- **Every command keeps a hand-written section.** The 64 commands whose only home is a Surface row get a short section on their topic page, holding what the row said beyond the help. Nothing the row states is dropped. The coverage test keeps asking for a section for each command, as COR-004's "documenting it" asks. It stops asking for each option to be named, since the usage files name them all.
- **The two columns keep a home.** "Mutates?" and "Idempotent?" are facts no code states today. The Surface table goes only once they have a home. The recommended home, as a point of its own in the ADR or a follow-up: each command declares both in its definition, and the index shows them. That adds data to every command, and gives COR-004's `--dry-run` class a check it lacks today. Failing that, each command's section states them.
- **ADR-069 point 5 is refined.** It allows a generated file in a folder of its own, but does not say such a file is part of an area's reference. The ADR refines it: a reference may include a generated projection, in a folder of its own.

## What splitting costs, whatever the projection

Each of these follows from the split, not from generation.

- **The anchor on `cli.py`.** The file defines every command and holds much of their behaviour, and a code anchor covers a whole file. So each topic page anchors `cli.py`, and each change to it asks every topic page for an answer. That would have been about ten answers for each of the 168 commits since July, where one page answers today.
  - **Recommended: split `cli.py` by command group,** decided with the topic pages in the same ADR, so each topic page anchors the modules of its own groups. Where a page ends and where a module ends become one decision. It is an internal refactor, with no surface change and no changeset, and a module of 10,300 lines gains from it anyway.
  - **Not waiting on #2100.** An anchor on one function changes the anchors record itself (COR-050), and must pass the universal-applicability test as a language-specific reading (COR-014). Its timeline would hold the rework behind a foundational record.
  - **Not anchoring each topic page on its usage file.** That narrows the anchor without #2100, but anchors a generated copy rather than its source, against project-kit's own practice, and misses behaviour written inside the command functions.
  - **Accepting ten answers for each change** is the maintainer's to choose, but it is no neutral third way. Such noise "invites 'unchanged' answers given without reading, which is how a stale page slips through with an answer on it" (#2100), and the whole-repository check reports over-broad anchors for that reason (COR-050 point 7).
- **living-docs' mention check reads the backbone's page layout,** across backbone versions. It names `.pkit/cli/README.md` as the file that documents a backbone command, and reads only its headings.
  - **After the split, it degrades without a sound.** In an adopter's project the topic pages are synced copies, never places, so the check falls back to suggesting the README. A page anchored there is not flagged when its topic page changes, and rests on less than it appears to.
  - **So the index becomes an interface another component reads.** A format others use starts with its record (core rule 23). The ADR fixes the index's form as a contract. The other way: the backbone answers "where is this command documented" through a reading command, as components read the backbone's other answers (ADR-057 point 1).
  - **The ADR chooses** whether living-docs reads both layouts, or raises its floor on the backbone. A raised floor ties every adopter's living-docs upgrade to that backbone release.
- **Section anchors die with their headings.** Of the 87 pointers into the reference's sections from other files, 63 are friction anchors and 24 are links.
  - **An HTML id keeps a link working, never an anchor.** A section anchor names a heading's slug, so a renamed or moved heading leaves it dead, and dead anchors are errors (COR-050 point 7).
  - **So each one is re-pointed and revalidated** in the change that moves its section. The command-only heading form alone kills each anchor whose address carries options, 37 pointers in all, anchors and links together. The split kills every anchor on a moved section, in `README.md`, `.pkit/README.md`, the permissions, schemas and other READMEs, and `docs/permissions/`.
- **The friction configuration.** The README's path anchor `.pkit/cli/**` would cover its sibling pages, which a test of project-kit's own refuses, so it narrows to `.pkit/cli/pkit`. The surface entry `.pkit/cli/**` takes an exclusion for the usage folder. Each topic page needs its place, its space and its place in `REWORK`'s scope.
- **Pointers by section name.** The code's help, `install.py`, and 29 references in shipped skills, agents and rules name the README or its sections. No check follows a pointer by name, so each is found and mended by hand.
- **Moved sections keep their addresses.** About 80 old addresses stay in the README as HTML ids (`RS-REWORK-002`), in the index's rows under C.

## What it means for the records

The records change for two reasons, and each lands in its own place.

- **The split owes a refinement of location, whatever generation's answer.**
  - **Which records:** COR-004, COR-005, COR-012, COR-021 and PRJ-008 each place a command's detail in `.pkit/cli/README.md`, or in one of its sections. Each moves to "the CLI area's reference, led by its README". COR-021 is among them, since the split moves the dispatcher's surface out of the README. The decisions README, PRJ-003 and PRJ-004 name the file in passing, and are mended in the same way. PRJ-004's "Installing pkit on PATH" moves to the guide.
  - **What stands:** what COR-004 decides, that the list is the spec's and not a record's. Only where the spec lives changes.
  - **Who reads them.** The methodology-reviewer reads the new wording. The core records ship, so the maintainer accepts each refinement.
- **The answer "yes" owes an ADR, and changes no core record.** The ADR holds the rule that a backbone command's definition holds its usage. It also holds the build's shape: the usage folder, the one walk, the generator and its check, the index and its contract with living-docs, the heading form, the modules of `cli.py` beside the topic pages, and what the coverage test becomes. It refines ADR-069 point 5. A choice later work builds on starts with its record (core rule 23).
- **No core record cites the ADR.** A shipped record's citation of an ADR would resolve against each adopter's own records.

## Release, changesets and sync

- **The usage files are new shipped files** under a propagated area, so their first change declares a backbone changeset. The living-docs change declares its own.
- **A change to an option's help changes a shipped file.** It adds no surface, since `--help` already shows it, so it needs no changeset of its own.
- **Sync prunes the usage folder, never a topic page.** Sync refreshes an area's subfolder in place and removes what its source no longer holds, so a usage file that goes is pruned. A topic page sits loose at the area's top, which sync never prunes, so a renamed or removed topic page stays behind in an adopter's tree.
- **The migration check sees both.** A removal in a shipped tree fails it without a migration (core rule 7). Removing a top-level command owes one already, as a breaking signature change. But a usage file per top-level command would also fail it when a command is hidden or regrouped, and a renamed topic page owes one each time.

## The capabilities

The backbone comes first. The capabilities follow once a record decides how their usage is projected.

- **A generator cannot reach most parsers.** 92 of 107 scripts build theirs inside `main()`.
- **Reading a parser is awkward even when it can be reached.** argparse keeps its actions in a private attribute. A script that imports the capabilities' scripts to reach their parsers also runs each one's module code.
- **Capturing `--help` is unstable** across terminal widths and Python releases, and 83 scripts give their file's name for the command.
- **Two ways forward:**
  - **F for the capabilities:** a console fence of each command's `--help`, run under one fixed width and interpreter. It needs no change to the scripts, only `prog` set to `pkit <capability> <verb>` so the output names the command.
  - **A record standardising each script's parser,** the follow-up COR-021 left open, so the generator reads it. This is heavier, and an adopter's own capability gains nothing from a script of project-kit's.
- **The `help:` lines would shrink** to the one line COR-021 asks for, whichever way is chosen.
- **The prize is larger there.** The capabilities' READMEs hold 112,330 words. They mix guide and reference, and each needs its own split first.

## What the maintainer must decide

**Is a backbone command's usage, its arguments, options, defaults and fixed choices, held by its definition alone, with the shipped reference showing a generated projection of it rather than restating it?**

**Recommended answer: yes, recorded as project-kit's own architecture, an ADR, not as a core rule.** The ADR then decides where the projection sits, and this note recommends C, with a lean command index in the README. If the maintainer wants the rule in the core instead, it covers every command, the capabilities' included. If no, the sequenced form applies: split with command-only headings, measure drift, and ask again.

What does not wait on this answer, and comes back to the maintainer on its own:

- **The heading form and the split.** The split waits on `cli.py` being split by command group, decided with the topic pages.
- **The location wording** of COR-004, COR-005, COR-012, COR-021 and PRJ-008, which the split owes.
- **The index's form,** a contract living-docs reads, and whether living-docs reads both layouts or raises its floor on the backbone.

## Open questions for the build

These do not block the decision.

- **The help's citations of project-kit's own records.** Clean the 25 lines before they ship in a usage file, or project only the help's first sentence?
- **The help's length.** The code's help is a second copy of behaviour, 23,240 words. Should it shrink to a summary that points to the reference, or stay whole for the terminal? Shrinking it makes F the cheapest projection.
- **One usage file, or one per top-level command?** One file per command keeps each small. One file for all is one place to search, and never fails the migration check when a command is hidden or regrouped. The architect leans to one file.

## Reviews

### The critic

**What changed:**

- **The records.** The first draft said only COR-004 needed a refinement, and read the other records' citations of the README loosely. COR-005, COR-012, COR-021 and PRJ-008 say as much as COR-004 does. The note now reads all five alike.
- **Nothing the Surface table states is dropped.** The first draft let a usage entry stand in for the 64 commands whose only home is a Surface row, and left "Mutates?" and "Idempotent?" without a home. Every command now keeps a hand-written section, and the table goes only once the two columns have a home.
- **The anchor on `cli.py`.** The first draft claimed a change to one module asks one page. For `cli.py`, which every topic page rests on, it asks all of them. The note now names the cost and the ways out.
- **The split's own costs** are listed apart from generation's: `RS-REWORK-004`, living-docs' mention check, the friction configuration, pointers by section name, and the old addresses.
- **The decision.** "Does the reference take shape C?" bundled five choices. The maintainer's decision is now the first question alone: who holds a command's usage. Where the projection sits is an architecture record's.
- **The drift premise.** The note now says what was measured: names and omissions, and 68 of 168 changes to `cli.py` that restated usage by hand. It also says what was not measured: values drifting. The sequenced "no" is named as the honest alternative.
- **Options.** F, a console fence of `--help`, joined the options, and the command index in the README came from the critic's counter-proposals. The heading form no longer counts as C's own gain, since every option can take it. B's costs are corrected, since code blocks are already exempt from the prose lint and the citation rule. D no longer calls parsing signatures fragile, since the coverage test already parses them.
- **Smaller points.** The prototype's options get addresses of their own, and hidden options are left out. ADR-075's shape is set apart from the generator's, with the reason. The release section is new.

**What was pushed back on:**

- **B with one block per page.** The critic proposed a few dozen markers instead of 146. That gives up locality, B's one edge over C, so B is weighed with a block per command.
- **E and C under ADR-069 point 1.** The critic is right that C's usage files are no page either, and E's cost no longer cites point 1. What separates E from C stays: usage that can be read, searched and linked offline.

### The architect

The architect raised an escalation flag: core records change, a scoping call is needed, the split creates an interface between components, and the split's sequencing ties the rework to other work. Each is now named in "What the maintainer must decide".

**What changed:**

- **Where the rule lives.** The critic's round scoped a COR-004 refinement to the backbone's commands. The architect showed that such a core rule fails the scope test: no adopter acts on it, since only project-kit's source authors the backbone's commands (COR-014). The rule now goes into an ADR. The core and PRJ records change only in where the spec lives, a change the split owes whatever generation's answer. COR-021 is among them, since the split moves the dispatcher's surface too. No core record cites the ADR.
- **What holds for every command gets a page of its own.** The draft put standard flags, output conventions and failure mode in the README. A topic page that summarises them must anchor their section, and an anchor on the README, which anchors each page it lists, would be a cycle (ADR-069 point 3, COR-050 point 5).
- **The index is lean.** The draft's index carried each command's first help line, and called itself free of prose. It now holds the command and its links only, so no help citation reaches the README and no help edit churns it. The rule set names its check.
- **living-docs' mention check** degrades without a sound in an adopter's project, and the index becomes an interface across backbone versions. The ADR fixes its form, and chooses between reading both layouts and raising living-docs' floor.
- **`cli.py`.** The recommendation is now to split `cli.py` by command group, decided with the topic pages. Waiting on #2100 would tie the rework to a change of the anchors record. Accepting ten answers for each change is shown as running against the anchors record's own reasoning, not as a neutral third way.
- **Anchors apart from links.** Of 87 pointers into the reference's sections, 63 are friction anchors, which no HTML id keeps alive.
- **Smaller points.** One walk of the click tree serves the generator, its check and the coverage test. The generator takes the contents lists' shape, a script with a check mode run by `scripts/check.sh`. ADR-069 point 5 is refined. The release section names sync's pruning of the usage folder and not of topic pages. The two Surface columns become a point of their own. The question's opening no longer says the split waits on the answer.

**What was pushed back on:** no finding. Two of its citations did not hold, and the note leaves them out. ADR-055 point 5 says nothing of how many answers a change costs, so the note cites #2100's own reason instead. COR-065 point 4 does not treat a moved location as a corrected fact, so each location refinement stays a change the maintainer accepts.
