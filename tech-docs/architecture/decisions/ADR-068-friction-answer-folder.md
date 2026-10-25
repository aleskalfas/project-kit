---
id: ADR-068
title: Friction answers live in .pkit/project/friction/answers/
status: accepted
date: 2026-10-21
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit carries out the rule that a change writes its answers to friction in new files of its own ([COR-062](../../../.pkit/decisions/core/COR-062-answers-in-own-files.md)).
- **The folder** is `.pkit/project/friction/answers/`, in every project. Each file a writer adds is named for the time it was made and a random suffix.
- **A writer** writes only into an answer file that is not yet committed. Once committed, a file is never rewritten. The next answer goes into a new file, which names it.
- **`pkit friction prune`** removes, from the working tree, each answer file in which no answer is live. project-kit runs it by hand, as a pull request of its own.
- **The landing command** reads answer files for the cover of a later head and for its firm stop. It prints the revalidations a merge would leave answered apart, and stops on none of them.
- **Continuous integration** names the pull request's own head to the change check in `PKIT_CHECK_HEAD`, beside the merge GitHub builds, so an answer is judged against what it could read. `--head` keeps its meaning, and the commit it names is its own head.

## Context

COR-062 moves a change's answers out of the artefacts' front matter into answer files of the change's own, which no later change rewrites. It leaves the realisation to the backbone and to each project:
- the literal path of the folder, the same in every project (COR-062 point 2)
- how a file is named, so that no two changes use one name (point 1)
- how a writer tells its own change's file (point 10)
- the command that prunes, and who runs it (point 8)
- how the landing command and continuous integration read the answers (points 4 and 7)

project-kit is both the backbone's source and an adopter of it. The backbone's literal path and the writers are choices every adopter receives. The landing command is project-management's (project-management DEC-055 point 3). The workflow and the prune's schedule are project-kit's own. Each changes how the system's parts meet, so they are recorded here, beside [ADR-057](ADR-057-backbone-engines-and-command-limits.md), which gives the answers their one home in the binary.

## Decision

**The backbone keeps answer files in `.pkit/project/friction/answers/`, each named for its time and a random suffix. A writer writes only into an uncommitted answer file. `pkit friction prune` removes the files no live answer is in, and project-kit runs it by hand. The landing command and the required check read answers from these files, and the check judges what each answer read against the pull request's own head.**

### 1. The folder and the names

- **The folder** is `.pkit/project/friction/answers/`. `.pkit/project/` is the project-owned part of the methodology's tree, where the backbone configuration already sits. No sync reads or writes it. `friction` is the functionality's name, as its command group and its configuration key are.
- **A file a writer adds** is named `<time>-<suffix>.yaml`, such as `20261021T093000Z-3f9a2c1d.yaml`. The time is the UTC time the file was made, and the suffix is eight random hexadecimal digits. The time sorts a listing for people, and nothing reads it. Which answer came first is read from history (COR-050 point 3).
- **A file the move writes** is named `moved-<hash>.yaml`, where the hash is the first twelve hexadecimal digits of the SHA-256 of the artefact's location and of the answers it moves. So two runs of the move over one state write the same file, as a migration must (COR-010). Two lines of work that each ran it over the same answers add the same file with the same content, which git merges cleanly. Run again over answers a block holds later, it writes a file of another name, so one path never holds two contents (COR-062 point 3).

### 2. The file's shape

- **One mapping,** with an `answers` list. Each entry holds one artefact's answers: its location, `read`, and the `revalidated` and `revisited` keys COR-050 names.
- **`read`** sits once in each entry, and holds for every answer in it, since all of them were written against one tree. It lists the other answer files by their names in the folder, not by their paths.
- **The schema** is a backbone file schema under `.pkit/schemas/backbone/`. Its files are found by where they are, by a rule of their own that ADR-056 point 2 gains after the fixed path ([ADR-056](ADR-056-backbone-file-schemas-home.md)).

### 3. A writer writes only into an uncommitted file

- **Its own file.** `pkit friction revalidate`, `defer` and `revisit` write into the answer file in the working tree that HEAD does not hold. Where there is none, they add one.
- **Never a committed file.** A writer never rewrites an answer file a commit holds, even one its own branch added. It adds a new file, which names the committed one in `read` (COR-062 point 4). After a merge of the base, the new answer replaces the committed one, and so names what the merge brought.
- **Refused.** Two uncommitted answer files that each answer one artefact make the writer refuse, naming both (COR-062 point 10).
- **What it names.** The writer fills `read` with every other answer file in the working tree that answers on the artefact.

### 4. The prune

- **What it does.** `pkit friction prune` removes from the working tree each answer file in which no answer is live at HEAD (COR-062 points 5 and 8). It judges liveness as the whole-repository check does, from the full history. A file that holds one live answer stays whole.
- **What it writes.** It removes files and adds none. It stages nothing and commits nothing, and prints each path it removes. `--dry-run` only prints them, and `--json` gives them in machine-readable form.
- **Who runs it.** In project-kit, a person or an agent runs it by hand, on a branch from `main`. The result lands as a pull request of its own, typed `chore` (COR-008). No job runs it. The whole-repository report shows how many files it would remove, so the maintainer sees when to run it.

### 5. Landing

project-management's landing command reads the answer files through the backbone (DEC-055 point 3).
- **The cover of a later head.** `pkit friction since` keeps its name and its flags. It answers whether every change since the authorised head lies in answer files the change adds: files that the base, where the head left it, does not hold.
- **The firm stop** intersects the base's changes since the head left it with the answer files at the head that carry a listed answer. A change answers only by adding, so it fires mostly on a stacked pull request.
- **Answered apart.** Before it stops ready, asks or merges, the landing command runs the change check against the base's tip, fetched for the run. It prints the revalidations that the check's machine-readable output reports as answered apart on the change's documents, beside the list. It stops on none of them.
- **`pkit friction resolve`** has no conflict left to resolve in the answers, since none is written in a block. The build retires it as a surface change, with what that needs (PRJ-002, COR-010).

### 6. Continuous integration

- **The own head.** `pkit friction check --head <rev>` keeps its meaning: it reads commit `<rev>` whole, from git objects, and `<rev>` is the change's own head. It does not read the variable, even where a pipeline set it, so a `<rev>` that is a host's merge is its own head. A run that reads the working tree takes its own head from `PKIT_CHECK_HEAD`, which a pipeline sets beside `PKIT_CHECK_BASE` ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md) point 3). The change check reads which answer files each answer had to name from the own head's tree, and everything else from the checkout, as before (COR-062 point 4). The CLI reference documents it.
- **Read by the change check alone.** `pkit friction since --head` and `pkit rule-sets altered --head` keep their meaning, and neither reads the variable. No query the backbone runs inherits it, as none inherits `PKIT_CHECK_BASE`.
- **What it accepts.** The own head must be the commit checked, HEAD for a run that reads the working tree, or a parent of it. Anything else makes the check refuse to run and say why, failing closed. An empty variable is unset, as the workflow leaves it on a merge queue and on a push. Unset, the change's own head is HEAD, and the working tree is read as it, uncommitted work included, as on a contributor's clone. Where it is unset and HEAD is a merge, a finding that an answer leaves out a file names the variable. A checkout of a host's merge is the likely cause.
- **The pull request's own head.** On a `pull_request` event, `checks.yml` checks out the merge GitHub builds. The workflow sets `PKIT_CHECK_HEAD` to the pull request's head commit, beside `PKIT_CHECK_BASE`, for the full run and the short check alike.
- **A merge queue.** `main` merges through none today ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 5). A queue's merge holds the answers of changes queued ahead, so the check needs each change's own head there too. A queue that cannot give it fails a pull request answering on an artefact that a change queued ahead answers on. So turning a queue on first needs a way for it to give the check each change's own head (refinement of ADR-055 point 5).
- **The short check** ([ADR-067](ADR-067-answers-only-short-check.md)) asks `pkit friction since`, whose predicate moves with the answers (its point 4).
- **The whole-repository report** lists each artefact answered apart in the tracking issue's body. Like a deferral, it does not hold the issue open (ADR-055 point 5). The next revalidation on the artefact clears it, and a much-answered document would otherwise keep the issue open most of the time.

### 7. The move in project-kit

The pull request that builds this runs the backbone's migration on project-kit's own tree. It moves every answer out of the blocks in project-kit's places, the shipped READMEs among them, into moved files (point 1).
- **Open pull requests.** One that answered in a block the move changed conflicts with it, and moves its answer as it merges `main` in (COR-062 point 11).
- **The mend.** `main` requires no up-to-date branch (ADR-055 point 5), so a first answer written into a block could land on checks run before the move. It leaves `main` failing validation. The move, run again as a pull request of its own, takes it out into a new moved file.

## Rationale

**Why `.pkit/project/`.** The answers are the project's, and that is the project-owned part of the tree that every project has. No sync writes there, so no adopter receives project-kit's answers. Answers also leave the shipped READMEs, so a revalidation in project-kit no longer changes a file adopters receive (ADR-055 point 5, "Anchors in shipped READMEs propagate").

**Why a time and a random suffix.** The name must be one no other change uses, on any clone, with no coordination. Eight random hexadecimal digits make a clash between two changes made at the same second rare, and a clash shows as an add/add conflict, never as a silent merge. The time costs nothing and orders a listing for people.

**Why a moved file is named for its artefact.** The move must be safe to run twice (COR-010). A name drawn at random would add a second file for each artefact on the second run, and the two would be answered apart.

**Why a writer writes only into an uncommitted file.** COR-062 point 10 forbids writing into a file another line of work added, a parent's on a stacked branch included. A committed file the branch added cannot be told from a parent's from the tree alone. An uncommitted file is the writer's own beyond doubt. The cost is a file per committed round of answers on a branch. The later ones name the earlier, so only the last on each artefact stays live, and the prune removes the rest.

**Why `read` once per entry.** Every answer in an entry was written against one tree, so each read the same files. One list says that once.

**Why the prune runs by hand.** A prune changes no live answer, so it owes nothing and nothing waits for it. A file left unpruned costs only a longer listing and a little reading time in each check. A job would open a pull request that still needs review and landing. So project-kit runs it by hand, until the folder's size shows a cost. The whole-repository report says when.

**Why the folder's path is for good.** Reading an artefact's answers at a commit needs the folder that commit used. A later path would leave the reader keeping the old one too, for ever. So the path is chosen once.

**Why the workflow names the head.** The merge GitHub builds holds answers landed on `main` after the change answered, which it could not name. Judged against that merge, every later run of the change would fail. Reading the merge's second parent would be a guess that misreads a merge the change made itself. The event names the head, so the workflow passes it on.

### Alternatives considered

- **A setting that places the folder.** Rejected by COR-062 point 2. A reader would need each commit's setting.
- **A folder outside `.pkit/`, such as under `tech-docs/`.** Rejected. Such a folder belongs to a documentation root, so places and the measures would have to leave it out by hand.
- **Names from the branch.** Rejected. A branch name is reused after its branch lands, and two forks may share one.
- **Sequential numbers.** Rejected. Two branches take the same next number.
- **A name from the file's content.** Not taken. Each write of an uncommitted file would rename it, for no gain over a random name.
- **The writer remembering its file in the clone's git configuration.** Rejected. The configuration is not versioned, so a second clone or a fresh one would forget it.
- **A job that prunes after every push to `main`.** Not taken yet, for the reasons above.
- **Checking out the pull request's head instead of GitHub's merge.** Rejected. The other checks of the aggregator read the merge, which is what lands.

## Implications

The build is #1779.
- **The backbone** gains the answer reader (ADR-057 point 2), the schema, the writers that add answer files, `pkit friction prune`, the migration, the change check's own head in `PKIT_CHECK_HEAD`, and the new predicate of `pkit friction since`. It retires `pkit friction resolve`. The CLI reference's "Friction checks" says each.
- **project-management** reads answer files in the landing command's cover and firm stop, and prints the answered-apart report. Its not-code floor leaves the folder out (project-management DEC-032).
- **Software-analysis** reads `at` through the backbone's machine-readable output, not from a file, and declares the backbone it needs.
- **The backbone's readers,** run over a project whose answers have not moved, say so once and name the move (COR-062 point 11).
- **living-docs** gives no doc-check obligation for a page answered apart, as for a deferred page (COR-062 point 7, project-management DEC-053 point 4).
- **Agent bodies and READMEs** that tell a writer to answer in the block are rewritten. Such are software-engineering's, living-docs', demo-recording's and evidence's, and software-analysis's `analysis-resolver`. So are the agents README's "Friction writers" and core rule 20's answer owed for a combined state after a conflict.
- **`checks.yml`** sets `PKIT_CHECK_HEAD` on a pull request, and the backbone drops it from what a query inherits. `friction-report.yml` renders the answered-apart findings and the count the prune would remove.
- **The short check** ([ADR-067](ADR-067-answers-only-short-check.md)) is revisited once the build lands. Its summary's predicate is reworded, and whether it still saves enough to keep is decided from the rounds left.
- **Changesets.** The backbone, project-management, software-analysis and living-docs each declare their surface change (PRJ-002). The three capabilities set `requires_backbone: release`, since they read what the build adds to the backbone.
