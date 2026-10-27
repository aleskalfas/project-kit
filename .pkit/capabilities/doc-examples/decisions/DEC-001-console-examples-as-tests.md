---
id: DEC-001
title: A page's console examples run as tests
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a page that shows a command and what it prints makes a claim about the software's behaviour. This capability runs each such example in a throwaway project, built by the project's own setup step, and fails when the output differs from the page. So a change in behaviour fails the project's checks wherever in the code it comes from, even where no page anchors that code. The run is a program of its own, never a command of the methodology's CLI, so a grant of that CLI never runs what a page holds.

## Context

Living documentation keeps a page true through its anchors ([living-docs:DEC-001-living-docs-discipline] point 3). A change flags a page only through what the page anchors. Code that an anchored file calls grounds nothing, and a change to it flags no page.

A page may show a command and its output in a shell-session fence ([living-docs:DEC-002-visual-elements] point 6). That output is a claim about behaviour, and behaviour runs through code no page anchors. When a file that an anchored file calls changes what the command prints, nothing asks. The page then shows output the software no longer prints.

A run of the example catches that change, wherever it comes from. Three accepted decisions bear on who runs it:
- **living-docs never runs the product.** Running it is testing, and the results of such checks arrive through the reading-evidence point (living-docs DEC-001 points 6 and 7).
- **The runner is the project's, or a capability's.** A project runs its fences with a runner of its own, or one a capability provides (living-docs DEC-002 point 6). That record names the fence and the prompt, and leaves to the runner how output that varies is matched. It deferred a capability of such checks until a second project wanted one (COR-007).
- **A capability is an opt-in discipline** (COR-017). A project that shows no console output has no use for this one.

One project built a runner of its own and hardened it over two changes ([project-kit#1807](https://github.com/aleskalfas/project-kit/issues/1807), [project-kit#2017](https://github.com/aleskalfas/project-kit/issues/2017)). On 26 October 2026 its maintainer chose to ship it to every project before a second one wanted it ([project-kit#1928](https://github.com/aleskalfas/project-kit/issues/1928#issuecomment-6404740628)). The evidence was that a page's claim to stay true held only for what the page anchors. The principle set that day was to close such a gap before narrowing the claim.

## Decision

**A capability of its own runs each console example of a project's pages, in a scratch project the project's own setup step builds, and compares its output with the page's. The contract a page is written against is the capability's versioned surface. The run is a program of its own, never a command of the methodology's CLI, and ships as a check a project's continuous integration runs.**

### 1. The capability ships before a second project wants it

- **What it closes:** anchors flag a page for what it anchors. A run of the page's examples fails it for what the examples print, whatever code prints it.
- **Why not wait for a second project:** the gap lies in a guarantee every project that shows output relies on. Each project that waits has pages that drift unseen.
- **What one project's runner shows, and what it cannot:** it has met the cases one product's examples meet. What varies between projects is which pages, the setup and the placeholders, and the project names each of them (points 3 to 5). Where a second project's examples need more, the surface grows (point 6).

### 2. A console fence is a test

- **Which fences:** a fenced block whose info string's first word is `console`, wherever Markdown nests it, in a list item or a block quote. A fence of any other language never runs. So a command that cannot run as a test goes in a fence of its shell's language, as living-docs DEC-002 point 6 asks. A fence under another name for a shell session, such as `shell-session`, is reported as one no run checks, and fails nothing.
- **How a fence reads:** a line that opens with `$ ` is a command. The lines after it, up to the next command, are its output. A line before the first command, or a fence with no command, fails the fence.
- **How its commands run:** in order, in one POSIX shell for the fence, from the scratch project's root, with their input closed. So a `cd` or a variable carries over to the next command, as it does for the reader who types them. The run needs a POSIX system.
- **What is compared:** what each command printed, its standard output and error together, in the order the command wrote them to one pipe, with no terminal. The spaces that end a line, and the blank lines that end the output, are left out on both sides. The exit status is not compared.

### 3. The pages are the documents of the types the project names

- **The selection:** the capability's project configuration names types, and a page is a document of one of them. The run reads each artefact's type from the backbone's one answer (COR-056 point 6), and resolves none itself.
- **A project's own pages:** a project that wants pages no shipped type selects gives their place a type of its own, and names it (COR-056 point 2).
- **Documents only:** a page is a document, never an entry of a collection. A document is an artefact only where it has front matter and lies in a declared place (COR-050 point 1). So a file the project wants run needs both, even where no other component reads it, such as a top-level README.
- **The default, where living-docs is installed:** with nothing named, the pages are the documents of living-docs' page type. living-docs also counts as a page a document of no type that declares its page kind in an untyped place outside every root ([living-docs:DEC-001-living-docs-discipline] point 4). The default misses such a page until the project types its place.
- **living-docs is an optional dependency.** The default names one specific capability's type, so this capability declares living-docs an optional dependency with a version range (COR-030). Without living-docs it has no default, and runs the pages the project names.
- **A selection the run cannot read** stops it before any command runs, and the run names the fix. Examples are no selection at all, and a type no installed component declares. Validation reports both earlier (point 11).

### 4. The project builds the scratch project

- **Its setup step:** the project names, in the capability's configuration, the commands that build the scratch project, such as an install of its own product. The run runs them once for each run, in an empty folder, with a home of its own. They are given the repository's path, and the guards of point 8 apply to them.
- **No setup named:** the scratch project and its home are empty folders.
- **Nothing of the capability's own:** the capability installs nothing into the scratch project, and assumes no product, the methodology included.
- **Restored before each fence:** each fence starts from the project and the home as the setup left them, at the paths where they were built, and from an empty temporary folder. So no fence sees what another left, and a build that records its own paths still works.
- **What a command is given:** an environment the run builds, holding the caller's `PATH` behind the folders the project names, the variables the project names, and terminal and locale settings the run fixes. A variable takes a value the project writes, or the caller's value of that name. A value may name the run's folders by their placeholders (point 5). Nothing else of the caller's reaches a command, and its home is the scratch home, so no tool reads the caller's configuration through it.
- **A caller's value never reaches a page:** before comparing, the run writes each value a variable takes from the caller as a placeholder of the project's form, the variable's name in upper case. It replaces the value where it stands whole, as a project placeholder's text (point 5), and an empty value nowhere. So an update never writes such a value into a page, whatever a command prints. A variable whose placeholder would take a project placeholder's name fails validation (point 11).

### 5. Placeholders stand for what varies

- **The run's folders:** before comparing, the run writes a placeholder in place of each folder that varies from run to run. These are the scratch project, its home and temporary folder, the run's scratch area and the repository. The capability's README lists their names, such as `<project>`.
- **Any text:** in a page's output, `<any>` stands for any text within one line.
- **The project's own:** a project may declare placeholders of its own, each with a command that prints the text it stands for, such as its product's version. The run runs each such command once, after the setup step, in the scratch project. A command that fails, or prints no text or more than one line, stops the run before any page's command runs.
- **Two forms of name:** the capability's placeholders take lower-case names, and a project's take upper-case names, such as `<VERSION>`. So neither can take the other's name.
- **How a text is matched:** the longest text is replaced first, so no text is replaced inside a longer one. A project placeholder's text is replaced only where it stands whole, never as part of a longer word or number. The capability's README states the exact rule.

### 6. The contract a page is written against is the capability's versioned surface

- **The surface:** what the capability's README documents of points 2 to 5 and 7, and of the exit statuses of point 10. That is the fence form, how commands run with the environment's fixed settings and the default limits, and what is compared. It is also the placeholders with their matching, the default selection and what an update writes.
- **A breaking change:** a change to that contract that would fail a page that passed, or pass a page that failed, is a breaking change of the capability (COR-010). A fix that brings the run back to its documented contract is no breaking change.
- **Pages after a breaking change:** where pages can be rewritten mechanically, as for a renamed placeholder, the change ships a migration that rewrites them (COR-010). Such a rewrite changes the pages' content, so whatever anchors them owes an answer to the change.
- **Where no migration reaches:** a change that only judges pages otherwise alters no installed state, as a rule set's new major judges artefacts otherwise (COR-051 point 7). The release's notes say what to change, and the run's failures show where.
- **The program's path and options only grow.** Each project writes them into its own CI, which no migration reaches. So the path never changes, and no option is removed or given another meaning. A new option may come beside them.

### 7. New output is written into a page only for review

- **Writing it:** asked to update, the run writes each command's new output into its page. It keeps each line of the page's output that still matches, `<any>` included. A person reviews the new output as any change to the page (living-docs DEC-002 point 6).
- **What it never writes:** output with a line that would read as a command or close the fence, so nothing a command prints becomes a command of the next run. Nor output with a line that holds `<any>`, which the next run would read as any text.
- **When it writes:** only once every page's commands have run with no write in the repository (point 8). A page that changed since the run read it is not written, and is reported.

### 8. The run guards the repository and confines nothing

- **What it guards:** every command the run starts, whether of the setup step, of a placeholder or of a page.
- **Its limits:** a command that runs past its time limit or prints past its output limit is stopped, with every process left in the fence's shell. So is the command running when the run is interrupted. A stopped command fails its fence, and the fence's later commands do not run.
- **A write in the repository:** the run detects a file or folder that a command adds, removes or changes in the repository. Such a write fails the test and stops the run, and no page is updated. The repository's git directory is left out, since any process that reads the repository's state may write there. A write by another process during the command is taken for the command's.
- **The scratch area** lies outside the repository, and is removed after the run.
- **What it confines:** nothing. A command runs as the caller, and reads and reaches what the caller can, the network included. The guards keep a mistaken page from harming the checkout, and stop no command written to do harm.
- **So a page's commands are code the project runs,** and so are its setup step and its placeholders' commands. A change that adds or alters one needs the review a change to a test gets.

### 9. The run is no command of the methodology's CLI

- **What the permission model sees:** it decides the calls an agent or the operator makes through a harness (COR-028). A program a call starts makes no call of its own, so the model decides the call that starts the run, never the commands the run starts. So whatever allows that call allows every command the run starts. Inside an operating-system sandbox they are confined as the call is, and where the call runs outside one, so do they.
- **So the run is a program of its own,** which a person or a project's continuous integration starts by its path. No grant of the methodology's CLI allows a call to it. Nor does any other allow the methodology ships, in the grants it ships or in the core baseline an adapter merges into a harness's settings (COR-002). So the harness's own rules decide such a call, as for any program the project has not granted.
- **A privilege of its own:** the capability defines a privilege that recognizes the run, and ships no grant of it. So a project allows running its pages' examples by that name, to whom it chooses, rather than through a grant to run any program.
- **Where another grant allows a call that starts the run,** that grant allows the run too, and this point adds nothing there. Examples are a grant of a wrapper that runs any program, and a grant of a version-control command whose hook starts the run.
- **What the model cannot see is said:** the capability's README says that the run's commands lie below the permission model, and names the grants that reach them. The permission model reports what it cannot enforce in the same way, rather than drop it (COR-028 point 3).

### 10. A check that continuous integration runs, with no kept results yet

- **The check:** continuous integration runs the run by its path from the repository's root, beside the project's tests, and the capability's README says how. The run reads the pages through the methodology's CLI, so it needs that CLI installed.
- **Its exit statuses:** 0 when every fence matches, when no page holds one, or when an update wrote every output that differed, and 1 when a fence fails. It exits 2 when it cannot start: a selection it cannot read, a setup step or a placeholder's command that fails, or a page it cannot read.
- **One program at a desk and in CI:** a person runs the same program, on every page or on the pages named.
- **No kept results yet:** a run's result is its exit status and its report, which nothing keeps. Its results reach no connection point.
- **The follow-up:** a capability fills the reading-evidence point with a command filler, which needs no network and changes nothing (COR-052 point 6). It cannot run the examples itself, so feeding that point needs results kept where a filler can read them. A record of its own decides where they live, as living-docs DEC-002 point 6 expects.

### 11. The CLI holds only what runs nothing of the project's

- **Its commands are queries.** The capability's command line lists the pages this run reads. It also checks, as a member of the methodology's validation (COR-055 point 3), the capability's configuration and the form of each fence.
- **Neither runs a page's commands,** a setup step or a placeholder's command. So a grant of the CLI reaches only this capability's reading, as point 9 requires.
- **The severity of validation's findings** (COR-055 point 4): what would stop the run, or fail a fence before its first command, fails validation. That is a selection the run cannot read, a project's placeholder whose name is not in upper case, two placeholders of the project's form with one name, and a fence that cannot be read. A fence under another name for a shell session is a warning, which fails nothing.

## Rationale

**Why a capability of its own, not living-docs.** Running the product is testing, which living-docs keeps out (living-docs DEC-001 point 6). A capability that runs the examples overturns no record, and its results can later reach living-docs through the reading-evidence point.

**Why now, before a second project.** COR-007 waits for recurrence, so that a pattern's shape is known before it is fixed, and says its threshold is no hard rule. The cost of waiting here is a gap in a guarantee, borne by every project that shows output. A claim narrowed to fit the gap would stay narrow until someone closed it. The price is that one product's examples shaped the surface, so a second project may need it to grow. Point 6 makes each such growth a reviewed version, never a silent change.

**Why the fence is the test.** The page shows what the reader types and sees, and the same fence is the test (living-docs DEC-002, Rationale). No second copy of the example exists to drift from the page.

**Why one shell for a fence.** A reader types a fence's commands into one shell, so a `cd` in the first moves the second. A shell for each command would fail the commonest shape of a tutorial, which moves into a folder and works there. Session-test tools such as cram and scrut run a file's commands in one shell for the same reason.

**Why one pipe, and no terminal.** A terminal changes what many programs print, such as colours and progress bars, and differs from desk to desk. One pipe gives the same order on every run. A program that buffers its output differently on a pipe prints in a different order than at a terminal, and the page shows what the pipe gives.

**Why the exit status is not compared.** The reader sees what a command prints, not its status. A page that means its status shows it, as `$ tool check; echo $?` does. Comparing every status would ask a mark on each command that fails on purpose, beside its output.

**Why types select the pages.** A type is the declared name for what a document is (COR-056), and the backbone's one answer gives it to every reader alike. Selecting by type adds no vocabulary, and the run resolves nothing the backbone already resolves. A project declares what its own files are by typing their place, so naming its pages costs it one type. The default spares a project with living-docs even that. A tree a project receives by sync is never one of its places (COR-050 point 14), so it never runs the pages the methodology ships about itself.

**Why living-docs is named, and optional.** The default means living-docs' page type, not whichever capability provides documentation. One specific capability is meant, so a declared dependency names it (COR-030, Alternatives considered). It is optional because a project that names its pages needs no living-docs. The range couples the two: a new major of living-docs needs a release of this capability that admits it.

**Why the project builds the scratch project.** The capability cannot know a project's product. The runner it grew from installed the methodology into every scratch project, which an adopter's examples do not need. The setup step is where a project puts its own product's install, and its home's configuration, such as a version-control identity that signs nothing.

**Why restore at one path, not a copy for each fence.** A build often records its own path, as a virtual environment's scripts do. A copy at another path would run against the original, and one fence's writes would reach the next. Restoring at the path where the setup built keeps every fence apart, and the scratch project's placeholder stands for one path.

**Why the setup step is guarded too.** A setup that writes in the checkout leaves files the next run, or a person's next commit, picks up. A build that writes beside its sources builds from a copy of them. That is a cost to such a project's setup, paid once.

**Why an environment built from scratch.** A command that reads the caller's environment prints what that desk prints, so CI and a person would disagree. The caller's variables may also hold secrets, which an update could write into a page. The caller's `PATH` is the one exception, since nothing runs without it. Tools on it differ from desk to desk, and a setup step that needs one version puts its own first.

**Why the placeholders are surface.** Every page that shows output is written against them. A silent change would fail pages, or pass pages that should fail, in every project at once. A breaking version makes each project review its pages when it takes the change. Names in two forms keep the capability's growth apart from each project's: a new placeholder of the capability's own takes no name a project's holds.

**Why the program's path and options only grow.** Each project writes them into its own CI, which no migration of the capability reaches. A rename in the capability's tree ships a migration (COR-010), but that migration could not mend a single call. So the path is a stable name for the program, not the name of whatever file implements it, and a call written for one release works with every later one.

**Why the project's placeholders come from a command.** What varies by product, such as a version, changes with each release, so fixed text in the configuration would go stale. A version lives in many forms, and only a command reads each of them. The command runs under the same call and guards as the setup step, so it reaches nothing more. A short text such as `1` would be replaced inside every number, so a project's text is replaced only where it stands whole.

**Why detect writes and confine nothing.** No confinement is portable across the systems a project runs on. The caller's own confinement, such as a sandbox, already applies to every program a call starts. Detection catches the mistake a page most often makes: a command that writes in the checkout it was meant to leave alone.

**Why the run is no command of the CLI.** A grant of the methodology's CLI is commonly given to every agent, and the core baseline an adapter merges into a harness's settings may allow the CLI too. A harness may also run the CLI outside its sandbox, on a system where the CLI cannot run inside it. A CLI command that ran pages would then run their commands both unconfined and unasked. The CLI already runs some code a project writes, such as a capability it incubates or a process's predicates. A page differs: more people and agents write pages than such code, and edit them more casually. Under the CLI's grant, an edit to a page and a run of it would run any command with nobody asked.

The costs are those of a program started by its path (COR-021). The CLI's help lists no run, and no error of the CLI points to it. The path appears in each project's CI as written. A rule's check may be a component's registered command (COR-051 point 2), and the run is none. Point 11 keeps the reading half on the CLI, which recovers the listing and the validation.

**Why a privilege of its own.** Recognizing a call is vocabulary that the owner of the tool extends (COR-028 point 1). Without it, a project that wants agents to run the examples grants them every program, with nothing to show what the grant was for. A privilege no grant references changes no decision.

**Why the CLI keeps the queries.** Listing the pages and validating the configuration run nothing of the project's. So they fit under the CLI's grant, as every query does. Validation finds a mistaken configuration before CI does. The listing is of this run's pages only. The backbone's one answer stays the registry of what a page is, so no other check comes to depend on this capability's configuration.

**Why no kept results yet.** A command filler of the reading-evidence point needs no network and changes nothing (COR-052 point 6), so it can only read results kept somewhere. Where they live, and keyed by which commit, is a choice no reader needs yet. A reader-review that wants the evidence is the trigger (COR-007).

### Alternatives considered

- **A runner inside living-docs.** Rejected. Running the product is testing, which living-docs DEC-001 point 6 keeps out.
- **Waiting for a second project, as living-docs DEC-002 deferred it.** Not taken. The gap lies in a guarantee every project relies on.
- **An existing session-test tool, such as cram, scrut or trycmd.** Not taken. Each brings its own file format or matching rules, and none reads the backbone's selection or detects a write in the repository. Their practice of one shell for a file's commands is taken (point 2).
- **A shell for each command.** Rejected. A `cd` would not carry over, as it does for the reader.
- **Showing each failing status in the page,** as `[1]` after the output. Not taken. It adds a mark to user-facing pages, and a page that means a status can print it.
- **A scope of the capability's own, by paths and types.** Rejected. It would copy the rule-set record's scope rules, and the copies would drift.
- **Pages as the documents a named rule set's scope covers.** Not taken. A scope says where rules bind (COR-051 point 2). An edit to it would change what CI runs, unseen by those who review that set.
- **Pages as wherever a rule of the capability's own binds.** Not taken. A project would adopt a rule set to run a test, and the run is no registered command a rule's check names.
- **Selecting the pages through the documentation role.** Not taken. The role defines no point that lists pages, and the one answer already gives every artefact's type.
- **living-docs as a required dependency.** Rejected. A project that names its pages needs no living-docs.
- **The methodology installed into every scratch project, as the first runner did.** Rejected. An adopter's examples are about its own product.
- **A copy of the built project for each fence.** Rejected. A build that records its own path would run against the original.
- **Comparing the exit status of every command.** Not taken. The reader sees the output, and a page that means a status shows it.
- **The caller's environment passed through.** Rejected. Output would vary by desk, and secrets could reach a page.
- **A project's placeholder as fixed text, or as text read from a file.** Rejected. Fixed text goes stale with each release, and a file holds a version in one form only.
- **One form for every placeholder's name, a project's refused where the capability holds it.** Rejected. Each new placeholder of the capability's own would then be a breaking change.
- **Options after `console`, reserved now for the surface to grow into.** Not taken. A reserved form fails pages that use it today for another purpose, such as a title a site generator reads. A breaking version reviews whatever comes.
- **The surface left provisional while the capability's version is below 1.0.0.** Rejected. Pages in every project rely on it from the first release, and a provisional surface could break them in a version that claims to break nothing.
- **A report-only mode for a project's first run.** Not taken. The run is a step the project adds to its CI once its pages pass, and an update writes their outputs for review.
- **A run that confines its commands, in a container or a sandbox of its own.** Not taken. No such confinement is portable, and the caller's own already applies.
- **A command of the CLI, with a deny of the run that the capability ships.** Rejected. A deny wins over every allow, so no project could then let any agent run it.
- **A command of the CLI that asks a person before it runs.** Rejected. With no terminal it needs a flag, and a call carrying the flag is still a call the CLI's grant allows.
- **Kept results now, feeding the reading-evidence point.** Not taken now. No reader needs them yet (point 10).

## Implications

- **The capability ships** this record, the run as a program outside its command tree, and two commands of the CLI: the listing of the run's pages, and the validator that joins validation. It also ships a privilege of its own with no grant, a schema for its project configuration, and a README. The README documents the contract of point 6, says how a project makes the run a check in its CI, and says what the permission model cannot see (point 9).
- **The run needs no dependency beyond the standard library of the language it is written in,** since nothing provisions a program outside the command tree. It needs the methodology's CLI, which it reads the pages through.
- **Its package metadata** declares living-docs an optional dependency with a version range (COR-030), the two commands as queries, and no command for the run.
- **A configuration key** changes as any surface does. Renaming or removing one ships a migration (COR-010).
- **The capability's tests never reach the network.** They run the run on fixture pages, with a setup that needs none.
- **A test holds point 9 true:** no grant the methodology ships, and no core baseline an adapter merges, allows the run's call.
- **living-docs' README** names this capability where it says a project brings its own runner. living-docs' records change nothing.
- **Two follow-ups:**
  - a record that says where kept results live, so that the run can fill the reading-evidence point (point 10)
  - a core record, with its realization, on the grants that reach a project's own code: the CLI's, through an incubated capability's commands or a process's predicates, and a version-control grant, through a hook. After it, the run may become a command of the CLI (point 9).
