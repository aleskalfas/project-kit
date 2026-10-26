---
id: ADR-070
title: A document's sidecar sits in .pkit-meta beside it, and never ships
status: accepted
date: 2026-10-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** this record is how project-kit carries out the rule that a document may keep its data in a sidecar ([COR-063](../../../.pkit/decisions/core/COR-063-document-sidecars.md)). A sidecar is a file of its own beside the document.
- **The place** is `<folder>/.pkit-meta/<file name>.yaml`. For `tech-docs/analysis/glossary.md`, it is `tech-docs/analysis/.pkit-meta/glossary.md.yaml`. The place is fixed for good.
- **The permission** is `sidecars: true` on a type's entry in its owner's type registry.
- **The schemas** find a sidecar by a location rule of its own, and read the methodology's block in either home ([ADR-056](ADR-056-backbone-file-schemas-home.md) point 2).
- **No sidecar ships.** The wheel carries none, and no copy into a project carries one.
- **A rename that strands a sidecar** leaves it with no document, and validation fails it.
- **Who anchors what** is asked of `pkit friction artefacts` and `pkit friction explain`, since common search tools skip a dot-folder.

## Context

COR-063 lets a document keep its data in a sidecar. It leaves the realisation to the backbone:
- the rule that derives a sidecar's path from its document's, the same in every project and for good (COR-063 point 1)
- the form of the permission on a type (point 4)
- how validation's schemas find a sidecar's data
- how a component maps a sidecar to its document (COR-063 Implications)

project-kit is both the backbone's source and an adopter of it. Its places include the READMEs it ships under `.pkit/` ([ADR-055](ADR-055-first-adopter-analysis-and-living-docs.md) point 3). Their front matter reaches every adopter, inert, and each edit of it declares a changeset (ADR-055 Implications). A sidecar beside such a README would reach every adopter too, unless the build and every copy leave it out.

## Decision

**A document's sidecar is `.pkit-meta/<file name>.yaml` in the document's folder, a path fixed for good. A type allows one with `sidecars: true` in its owner's type registry. The schemas read a document's data in either home. Nothing an adopter installs carries a sidecar, so a change to a sidecar changes nothing that ships.**

### 1. The place

- **The rule.** A document at `<folder>/<name>` keeps its sidecar at `<folder>/.pkit-meta/<name>.yaml`. `<name>` is the document's whole file name, its extension included. `README.md` at the repository's root keeps its sidecar at `.pkit-meta/README.md.yaml`.
- **The inverse.** A path is a sidecar when its parent folder is named `.pkit-meta` and no folder above it is. Its file name must also be a non-empty name followed by `.yaml`. Its document is that name, in the folder that holds the `.pkit-meta` folder.
- **Read from the path alone.** The rule reads no state and no setting, so it reads alike at every state and in every project. A name is matched exactly, case included, in the listing of the files a state holds ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2), never by asking the disk.
- **For good.** The name `.pkit-meta` and the rule never change once used, since every past state is read through them (COR-063 point 1).
- **Sidecars only.** A `.pkit-meta` folder holds sidecars and nothing else. Validation fails any other file in such a folder or below it. Where it can, the finding names the sidecar name the file may have meant, as for a name ending in `.yml`. A link at a sidecar's path holds no data, since no reader follows a link, and validation fails it too.
- **Received files.** A tree received by sync is the exception to each finding here, as to every finding of COR-063 ("Received files").
- **The text.** A sidecar holds the YAML its document's fences would hold, as written. A writer adds no fence lines and no editor directive, so moving data between homes copies its text unchanged.

### 2. The permission is `sidecars` on a type

- **The key.** A component allows sidecars for one of its types with `sidecars: true` on the type's entry in its type registry. The registry is `friction.types` in the component's package metadata, where the entry's `kind-field` and `project-places` also sit (COR-056 point 2). An entry without the key allows none.
- **The schema.** The backbone's schema for package metadata gains the key, as a boolean. Validation's `packages` member checks it as it checks the entry's other keys.
- **The backbone's own types** allow none. So a document keeps a sidecar only where a component's type allows one.

### 3. The schemas read either home

ADR-056 point 2 gains a location rule for sidecars, and its container rule reads a document's data in either home.
- **The sidecar rule claims.** It comes after the filler path, since a sidecar's path is derived from its document's. It claims every sidecar, in a place or not, so a sidecar never falls through to the capability-data resolution of [COR-023](../../../.pkit/decisions/core/COR-023-schema-binds-inline.md). It checks nothing itself.
- **The container rule checks, once.** It checks a document's container in whichever home holds the data, wherever the backbone reads that data (COR-063 point 3). Its findings in a sidecar name the sidecar's path. Each owner checks a document's own fields in either home.
- **Elsewhere,** nothing in a sidecar is checked against a schema. That holds beside a decision record or a rule-set file, outside every place and in a tree received by sync. Validation judges such a sidecar by COR-063's findings alone.
- **Walks for YAML files** skip a `.pkit-meta` folder, such as the walk of `pkit schemas validate` over a folder. A sidecar is read only as its document's data, through the module of point 7.

### 4. No sidecar ships

A sidecar stays part of its document for every judgement made by path (COR-063 point 2). It holds the part of the document that neither the wheel nor a copy into a project carries.
- **The wheel** leaves out every path with a `.pkit-meta` part, in the methodology's trees and in the package. Its filter does so beside the adopter tier's.
- **The sdist** leaves out `.pkit/**/.pkit-meta` by a glob of its own, beside the adopter tier's, so its methodology tree matches the wheel's. Outside `.pkit/`, the sdist stays the tracked tree, sidecars included. No install reads a file of the sdist outside `.pkit/`.
- **A packaging test** adds three tracked sidecars to the tree it builds from: one under `.pkit/`, one in the package and one elsewhere. The wheel must hold none of the three. The sdist must hold the two outside `.pkit/` and not the one under it.
- **Copies into a project** skip every path with a `.pkit-meta` part, by one rule beside the one for Python's caches. That covers first-time install, sync's refresh and a capability's install and refresh, an externally-sourced capability's included. A refresh removes such a path where the tree is the methodology's to manage, as it removes a cache there.
- **Parts, from the root.** Every filter and copy tests a path's parts relative to the repository's root or the copy's, never above it.
- **The changeset guard** reads a change to a sidecar as a change to its document's data. The guard asks whether a change alters what a component ships ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)), and data in a sidecar ships nothing. So `pkit release check` counts a change to sidecars alone as no change to any component.
- **The migration coverage check** reads a sidecar added, removed or renamed as an edit of its document's data. Such an edit owes no migration, and no adopter holds a sidecar to carry across.
- **What arrives anyway** is inert. No synced tree is a place, so no reader reads a received sidecar as data (COR-063 point 3).

### 5. A sidecar left behind is caught

- **A rename that strands its sidecar.** Renaming a document, by git or by hand, leaves its sidecar under the old name. The sidecar then has no document, and validation fails it, naming the document it expects (COR-063 point 4). So the change that strands a sidecar fails the check gate until the sidecar follows.
- **What validation cannot see.** Two documents that swap names swap their data. A document renamed and replaced by a new one at its old path leaves its data to the new one. Every sidecar keeps a document in both, so a reviewer, not validation, catches them.
- **A folder moved whole** carries its `.pkit-meta` folder, so each of its documents keeps its sidecar.
- **One commit, no edit.** The documentation tells a writer to rename a document and its sidecar in one commit, with no edit to either. git then pairs the document's old path with its new one, and the history walk follows that rename (COR-063 point 3).

### 6. Who anchors what is asked of the backbone

- **Search tools skip the folder.** `rg` and `fd` skip a hidden folder by default, and `ls` and most file browsers hide one. So a text search for an anchor from the repository's root, such as `rg COR-050`, misses every sidecar. `git grep` and `rg --hidden` read them.
- **The backbone answers.** `pkit friction artefacts --json` lists each artefact's anchors and the home of its data, and `pkit friction explain` gives one artefact's. Both read either home. A text that teaches how to find what anchors a record or a path names these commands, not a text search.

### 7. One module reads a document's data

Where a document's data lives is computed in one module that every reader calls, as ADR-057 point 2 asks of each computation.
- **What it gives.** For a document at a state, the working tree's or a commit's, the module gives the document's data and body. It also says which home holds the data. It holds the rule of point 1 and its inverse, and no other module derives a sidecar's path or a sidecar's document.
- **Who calls it.** Every reader of a document's data or of a sidecar's path calls it.
  - **Where a sidecar could be judged as a file of its own:** what a path anchor stands on, the excluded paths, the declared surface and both measures (COR-063 point 2).
  - **The other readers:** artefact discovery, which reads a file as artefacts through it, the history walk, both friction checks and the friction writers. Validation and its schema pass, the changeset guard and the migration coverage check call it too.
- **What stays.** The one reading of a file's fences stays in the module that reads a document's parts.
- **Components.** A component never derives a sidecar's path. It reads each document's home and sidecar from `pkit friction artefacts --json`.
  - **The mapping.** A reading command of the backbone maps a document's path to its sidecar's and back. It takes many paths in one run, and reads the paths alone. So a stamp learns where a new document's sidecar goes, and a component maps the paths of both states of a change (COR-063 Implications).

## Rationale

**Why a folder beside the document.** The data stays with its document. A folder of documents moved elsewhere takes its `.pkit-meta` folder along, which one tree for every document's data would not do (COR-063, "Alternatives considered"). Two changes that edit the data of two documents in one folder write two files, so they never conflict.

**Why `.pkit-meta`.** The name says what the folder holds, data about a document, and whose it is, the methodology's.
- **Left out of a site.** Site generators such as Jekyll and MkDocs skip a dot-folder, so a site built from the documents publishes no sidecar.
- **Shown on the host.** GitHub lists a dot-folder, first in its folder, so a sidecar is in plain sight there.
- **No collision found.** A search of the public web, of the cited tools' documentation and of this repository found no other use of the name.
- **Its form** is hyphenated, like `.agent-workspace`.

**Why the whole file name.** The inverse must give one document for one sidecar. With the extension dropped, `glossary.yaml` could belong to `glossary.md` or to `glossary.markdown`.

**Why a name is matched in the listing.** A file system that ignores case would find `README.md.yaml` for `Readme.md`, and one that keeps case would not. Matching in the listing of a state's files reads alike on both, and at a commit, where no disk is asked.

**Why the folder holds sidecars only.** A writer who names a sidecar `.yml` by hand would otherwise lose its data without a word. The document would read as having none, and nothing would name the file. Failing every other file in the folder names the mistake. The listing holds untracked files too, so a merge tool's leftover in the folder fails validation on a clone until it is removed.

**Why the sidecar holds the fences' text as written.** A move between homes then changes no value, so it owes nothing (COR-063 point 7). A move back gives the document the front matter it had. An editor directive would add a line that no front matter holds, and no backbone schema covers a document's own fields.

**Why a key on the type.** COR-063 point 4 puts the permission where the type is declared. A key beside `kind-field` and `project-places` keeps all that a type's owner says about it in one entry. An entry without the key allows none, so no registry that exists changes meaning.

**Why a location rule of its own.** A sidecar is a plain YAML file, and in a declared place a plain YAML file falls through to COR-023. There it would be checked against a capability's schema, or reported for lacking one. A rule among the derived paths claims it before any later rule could. The container rule then checks its data once, as it checks front matter.

**Why withholding agrees with COR-063 point 2.** Nothing judges a sidecar as a file of its own. A document ships without the part its sidecar holds, and the sidecar goes with that part.
- **The changeset guard and the coverage check** read a change to a sidecar as one to its document's data, as point 2 asks. That data never reaches an adopter, so it changes nothing that ships and needs nothing carried across.
- **Counted otherwise,** each anchor added to a shipped page's sidecar would need a changeset that declares nothing. Moving a shipped page's data back would need a migration for a file that no adopter has.

**Why the guard may pass over sidecars by their place.** PRJ-002 rejected passing over `.pkit/decisions/` by its place, since a change there may or may not reach adopters. A sidecar's place is the build's own rule for what it withholds. So a change to a sidecar never reaches an adopter, and the guard passes over only paths the build withholds.

**Why each distribution keeps its own filter.** The adopter tier is withheld twice, by the wheel's predicate and by the sdist's globs. The build's tests then check each against the other. A sidecar under `.pkit/` follows the same pattern, and the cross-check covers it too. Outside `.pkit/`, the sdist stays exactly the tracked tree, which its own test holds it to.

**Why copies skip sidecars too.** A copy does not always read the build. In a checkout of the methodology's source, first-time install and sync copy from the source tree itself. An externally-sourced capability is fetched from another repository, whose places may hold sidecars. The copies test a path's parts, as for `__pycache__`, since some of them see a folder's name alone.

**Why validation catches a stranded sidecar.** The rule derives a sidecar's path from its document's, so a rename that moves the document alone strands the sidecar. Validation runs at every change's head, so it fails the change that strands one. COR-063 point 9 covers a history that keeps such a commit anyway.

**Why the backbone answers who anchors what.** A search tool's defaults are its user's to choose, and many skip a dot-folder. The backbone reads every home, at every state, and gives the anchors as data. A text search also matches an id in prose, where the backbone gives only anchors.

### Alternatives considered

- **A file beside the document, such as `glossary.pkit.yaml`.** Not taken. It needs no folder, and a rename forgets it less easily. But a site generator publishes it as a static file, and every listing of a folder doubles.
- **`.pkit-data`.** Rejected. project-management already marks quoted untrusted text with `pkit-data`.
- **`.meta` or `_meta`.** Rejected. Neither says whose the folder is, and both are in use. Exercism's tracks keep a `.meta` folder, and Nextra reads `_meta` files.
- **`.pkit`.** Rejected. It reads as the methodology's install. The root's sidecar would sit inside the methodology's tree, as `.pkit/README.md.yaml`.
- **The document's name without its extension.** Rejected. Two documents that differ only by extension would share a sidecar, and the inverse would not give one document.
- **One exclusion for both distributions, as for build caches.** Not taken. The sdist would stop being the tracked tree outside `.pkit/`. The two distributions would also share a filter that the cross-check cannot test.
- **A refinement of COR-063 point 2 that sets shipping apart.** Not taken. Point 2 reads a sidecar as part of its document, and that part ships nothing. So the checks that judge what ships need no exception from it, and a principle every component applies stays free of how one distribution builds.
- **The changeset guard counting a sidecar as a change to its document's shipped file.** Rejected. It would ask a changeset for an edit that no adopter receives.
- **A repository setting that brings `.pkit-meta` into text searches.** Not taken. It would reach only the tools that read it, and a text search would still match ids in prose.

## Implications

- **The backbone** (#2077) gains the module of point 7, the `sidecars` key in its schema for package metadata, and the location rule of point 3.
  - **Validation** reports the findings COR-063 lists and those of point 1.
  - **The build** leaves sidecars out as point 4 says, with the packaging test, and every copy into a project skips them.
  - **The checks of a change.** `pkit release check` and `pkit migrations check-diff` read a sidecar as its document's data. Every walk for YAML files skips a `.pkit-meta` folder.
  - **The reading commands.** `pkit friction artefacts --json` names each document's home and sidecar. A reading command maps paths both ways, and the CLI reference names it.
  - **An uninstall plan** reports the sidecars it would leave unallowed (COR-063 Implications).
  - **One literal.** The name `.pkit-meta` joins the methodology's literals in the lifecycle README. A test keeps each copy of it equal: the module's, the copies', `hatch_build.py`'s and the sdist's glob.
  - **Timing.** The build measures validation and both checks on one analysis moved by hand, against the time a component's command gets (ADR-057 point 3).
- **The migration.** The release that first reads sidecars ships a backbone migration (COR-063 Implications). It moves and deletes nothing ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)).
  - **Its sign.** It stops on each file in a `.pkit-meta` folder that validation fails, by a finding of point 1 or of COR-063, naming each. It reads them from the backbone and judges no type itself (ADR-057 point 2). So a run over a project that already keeps its sidecars passes.
  - **Its stop** names the way back into front matter that #2079 builds.
  - **Its cost.** A transition copies the new content in before the migration runs. Take a file already in the folder, beside a document with no front matter. Where the same release allows that document's type a sidecar, the file passes and is read as the document's data. No migration mends that, as no migration mends such a file in history (COR-063 Implications).
- **The backbone's documentation** states the place, since adopters never receive project-kit's architecture records. The schemas README, the CLI reference, the release README's account of what a change touches and the lifecycle README's literals say it (#2077).
- **The command that moves data** into a sidecar, and back into front matter, is #2079's.
- **Owners** allow `sidecars` in their own records and registries: living-docs and project-management (#2075), and software-analysis (#2076). The schema refuses the key on a backbone that does not know it, so each owner's changeset declares `requires_backbone`.
- **Texts that teach a search for anchors** name `pkit friction artefacts` and `pkit friction explain` (point 6), as the writers' steps rewrite those texts (#2078, #2081).
- **Records refined in place,** atomically with this record's acceptance:
  - ADR-056 point 2: a location rule for sidecars, and a container rule that reads either home
  - ADR-057 point 2: the module of point 7 among the homes, and a placed file's content read from its data in either home
  - ADR-033 point 1: sidecars withheld from the bundle beside build caches
  - ADR-055 point 5: the after-merge job's writes to a sidecar neither sync nor need a changeset
  - ADR-055 Implications: anchors in a shipped page propagate only while it keeps its front matter
