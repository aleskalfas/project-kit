---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/backbone/**
        - src/project_kit/backbone_schemas.py
        - src/project_kit/config_validate.py
        - src/project_kit/package_validate.py
        - src/project_kit/data_points.py
        - src/project_kit/data_validate.py
        - src/project_kit/connections.py
        - src/project_kit/friction_discovery.py
        - src/project_kit/friction_validate.py
        - src/project_kit/friction_write.py
        - src/project_kit/friction_check.py
        - src/project_kit/answer_files.py
        - src/project_kit/docs_roots.py
        - src/project_kit/rule_sets.py
        - src/project_kit/working_tree.py
        - .pkit/lifecycle/ownership.py
        - .pkit/capabilities/living-docs/scripts/resolve-source.py
      record: [COR-010, COR-017, "COR-033#P7", COR-041, COR-048, "COR-049#5", COR-050, COR-051, COR-052, COR-053, COR-054, COR-055, COR-056, "COR-058#4", COR-062, "living-docs:DEC-001#3", "COR-064#1", "COR-066#4", COR-068, COR-069, ADR-056, ADR-057, "ADR-058#1", "ADR-058#3", "ADR-058#5", "ADR-068#1"]
      artefact:
        - .pkit/cli/README.md#configuration-file
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#status
        - .pkit/cli/README.md#data-validate-path
        - .pkit/cli/README.md#friction-checks
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - .pkit/cli/README.md#friction-check---all---json
        - .pkit/cli/README.md#friction-artefacts---at-rev---json
        - .pkit/cli/README.md#friction-debt---json
        - .pkit/cli/README.md#friction-explain-artefact---json
        - .pkit/cli/README.md#friction-revalidate-artefact---outcome-updatedunchanged---because-text---keep-anchor---yes----dry-run
        - .pkit/cli/README.md#friction-defer-artefact---anchor-anchor---reason-text---yes----dry-run
        - .pkit/cli/README.md#friction-revisit-artefact---target-anchor---outcome-unchangeddeferred---reason-text---yes----dry-run
        - .pkit/cli/README.md#friction-record-status-artefact---yes----dry-run
        - .pkit/cli/README.md#friction-prune---yes----dry-run---json
        - .pkit/cli/README.md#rule-sets-reach-path---at-rev---preview---json
        - .pkit/lifecycle/manifest.md#the-methodologys-literals
        - .pkit/lifecycle/manifest.md#how-the-wiring-is-resolved
        - .pkit/lifecycle/manifest.md#where-a-project-filler-file-lives-the-address-to-path-mapping
        - .pkit/lifecycle/manifest.md#how-a-data-point-resolves
        - .pkit/lifecycle/manifest.md#how-a-registered-anchor-kind-is-resolved
        - .pkit/lifecycle/manifest.md#the-connection-documentation-and-friction-blocks
        - .pkit/lifecycle/manifest.md#validation-the-package-schema
        - .pkit/lifecycle/manifest.md#strict-on-unknown-keys
        - .pkit/lifecycle/README.md#the-ownership-predicates-ownershippy
---

# Backbone file schemas

The schemas of the files the backbone does not write but validates, and how each such file binds to its schema. Among them are the container that an artefact's front matter holds ([COR-053](../decisions/core/COR-053-connection-points.md) point 10), and the friction block inside it ([COR-050](../decisions/core/COR-050-anchors-and-friction.md)). So are answer files ([COR-062](../decisions/core/COR-062-answers-in-own-files.md)) and rule-set files ([COR-051](../decisions/core/COR-051-rule-sets.md)).

## Contents

<!-- pkit:contents -->
- [What holds for every backbone file schema](#what-holds-for-every-backbone-file-schema)
- [The schemas that ship](#the-schemas-that-ship)
- [The container](#the-container)
- [The friction block](#the-friction-block)
- [Answer files](#answer-files)
- [Rule-set files](#rule-set-files)
<!-- /pkit:contents -->

## What holds for every backbone file schema

Most schemas of this area govern YAML the methodology ships. Such a file is a capability's own data file with its companion, or an instance that points at a shared shape. A second class governs files the backbone does not write but validates. These are the backbone file schemas:

- **the backbone configuration file** ([COR-048](../decisions/core/COR-048-backbone-configuration.md))
- **rule-set files** (COR-051)
- **the project's filler files,** each answering a data point ([COR-052](../decisions/core/COR-052-slots.md) point 2)
- **the block the methodology owns** inside an artefact's front matter (COR-053 point 10)
- **answer files,** which hold each change's answers to friction (COR-062 point 1)

Three things hold for all of them, each decided by the record named.

**They live in the tree,** under `backbone/` in this area, as JSON Schema files with no YAML half.

- **Why there:** schemas are data the methodology propagates. The configuration file's shape is the one the installed backbone defines, and the installed backbone is the tree (COR-048 point 6).
- **One copy:** the binary reads the same files, and carries no second copy.

**They bind by location, never by a field in the file.**

- **The configuration file** binds by its fixed path (COR-048 point 1).
- **An answer file** binds by the folder the backbone fixes, `.pkit/project/friction/answers/` (COR-062 point 2, "Answer files" below).
- **A filler file** binds by the path its point's address gives, under the internal documentation root (COR-052 point 2). The mapping, and its inverse, are [the lifecycle reference's, "Where a project filler file lives"](../lifecycle/manifest.md#where-a-project-filler-file-lives-the-address-to-path-mapping).
- **A rule-set file** binds by the places declared to hold rule sets, a `rule-sets/` folder among them (COR-051 point 2). This area's README lists the folders, under "Rule-set files".
- **The container** binds by the front matter of a Markdown document, or by a collection's entry, in a declared place (COR-050 point 1).
- **Before the binding of adopter data:** a location rule is meant to claim its file before the binding of adopter data reads it. Today only the answer folder's rule does, for `pkit data validate`. Named to that command, the configuration file and a filler file reach the binding, and are refused as having none ([the CLI reference, "data validate"](../cli/README.md#data-validate-path)).
- **A plain YAML data file in a declared place** is no document, so its location claims nothing, and it reaches that binding.

**They are strict at validation.** An unknown key is an error that names the nearest known key. COR-048 point 4 decides it for the configuration file, and each owning record decides it for the rest.

- **Where a version is written:** only where a capability owns the shape. The filler envelope and a role block's point blocks carry the point's `schema_version` (COR-052 point 5).
- **The backbone's own shapes** carry no version, but for package metadata's ("`package.schema.json`" below), and are migrated when they change ([COR-010](../decisions/core/COR-010-resource-lifecycle.md)).

**`pkit validate` runs them,** each as a member of its one registry of validators. The backbone's functionalities join validation by registering validators ([COR-055](../decisions/core/COR-055-validation.md)). Each member renders its findings through one renderer, and the unknown-key message of every member comes from one shared renderer ([the CLI reference, "validate"](../cli/README.md#validate)).

- **The members that apply them:** `configuration`, `connections`, `friction` and `rule-sets`, with `packages` for package metadata. `schemas` load-checks every schema under `backbone/`.
- **The paths:** the configuration file's fixed path is the CLI reference's ("Configuration file"). A filler file's derived path is the lifecycle reference's (linked above).

## The schemas that ship

`backbone/` holds six schemas: one for each kind of file above, and package metadata's, whose file no location rule binds. Each is named below, with:

- what it covers
- what binds a file to it
- what applies it

### `container.schema.json`

The container, in both its forms: a document's front matter, and a collection's entry. It models the `friction` block strictly.

- **The rest is code:** the rule that tells blocks apart, the check of a point's version, the shared renderer of unknown keys and the load-check. They live in `project_kit.backbone_schemas`.
- **The active roles and points** are read from the wiring resolver, `project_kit.connections`.

### `config.schema.json`

The backbone configuration file, at the fixed path the CLI reference's "Configuration file" gives. Its keys:

- `name`
- `decisions`: the key that turns the landing check's refusal on ([COR-066](../decisions/core/COR-066-accepted-before-landing.md) point 4)
- `docs`
- `friction`
- `connections`
- `process`: the logging of journals ([COR-033](../decisions/core/COR-033-process-substrate.md) point P7)
- `repository`: the default branch ([COR-054](../decisions/core/COR-054-default-branch.md))
- `rule-sets`: the budget of the project's own rules file, while it is a plain file ([COR-069](../decisions/core/COR-069-rules-word-budget.md) point 3)
- `project`: a block reserved for the project's own records

It refuses unknown keys at every level the backbone owns, and takes no version key.

- **What applies it:** `pkit validate`'s configuration pass, `project_kit.config_validate`, with the repository checks the owning records ask for.
- **Every key** is documented in the CLI reference's "Configuration file".

### `package.schema.json`

A component's `package.yaml`: every field in use, and the `connections`, `docs` and `friction` blocks. Its required fields are those COR-017 asks of every component.

- **Unknown keys** are refused at every level, as for the rest of the class, each with the nearest known key. The lifecycle reference's "Strict on unknown keys" records when and why the schema, first shipped permissive, became strict.
- **What binds a file to it:** its place, as the `package.yaml` at the root of a component the project registers. Unlike the other schemas here, it binds by no location rule, and its file carries a `schema_version` of its own.
- **What applies it:** `project_kit.package_validate`, with its repository checks. `pkit validate`'s `packages` pass runs it, and so does the pre-flight of `register` ([the lifecycle reference, "Validation: the package schema"](../lifecycle/manifest.md#validation-the-package-schema)).

### `rule-set.schema.json`

A rule-set file's front matter: the set's name, version, inheritance and scope, each rule's machine fields, and the parts of its rules that checks enforce.

- **Unknown keys** are refused at every level. The shape carries no version key of its own.
- **What applies it:** `pkit validate`'s `rule-sets` pass, `project_kit.rule_sets`. The pass adds the checks COR-051 asks for, and the container rule inside every rule. This area's README lists them, under "What the pass checks".

### `filler.schema.json`

The filler envelope a data point is answered in:

- `schema_version`: the point's version, required
- `value`: the point's value, required. The point's own companion schema judges it, never this one.
- `remove`: the project's overrides that remove entries, each `{id, reason}`

It refuses unknown keys.

- **What binds a file to it:** by the location rule, every file under the fillers' prefix of the internal documentation root. The document a command filler prints binds to it too.
- **What applies it:** `project_kit.data_points`, which also resolves each data point. `pkit validate`'s `connections` member runs it.

Its findings, of three severities ([the lifecycle reference, "How a data point resolves"](../lifecycle/manifest.md#how-a-data-point-resolves)):

- **Errors,** which the project can mend whatever the point's inert policy:
  - a file that does not parse
  - a malformed envelope
  - an envelope at another version than its point's, reported under `versions`
  - a value the point's schema refuses
  - removals on a `single` point
- **A warning:** a file under the prefix whose path names no point.
- **A report:** a filler whose point no active provider defines. It is inert: its envelope is checked, and its value never read.

### `friction-answers.schema.json`

An answer file: an `answers` list, each entry holding one artefact's answers ("Answer files" below). Unknown keys are refused at every level, and the shape takes no version key.

- **What binds a file to it:** by the location rule, every YAML file directly in the answer folder.
- **What applies it:** `project_kit.answer_files`. `pkit validate`'s `friction` member runs it, and so does `pkit data validate` for an answer file it is named.

### How `pkit validate` applies them

`pkit validate`'s `friction` member applies the container rule. It finds the artefacts in the declared places ("The friction block" below).

- **One umbrella:** every pass of the class is a registered member of `pkit validate`, rendered by one renderer.
- **One message for an unknown key:** every member takes it from the shared renderer.

## The container

An artefact's front matter may hold one key that the methodology owns: `pkit:` in this distribution ([the lifecycle reference, "The methodology's literals"](../lifecycle/manifest.md#the-methodologys-literals)). For a collection's entry, the entry itself holds it. Everything under the key is the methodology's, and everything outside it is the artefact's own (COR-053 point 10).

Inside the container:

- **A functionality block** is named for a functionality and its command group, and carries no version. `friction` (COR-050) is the first.
- **A role block** is named for a role. Keyed by point, it holds the data that role's provider keeps about the artefact. Every point block carries the `schema_version` of the point it targets.

```yaml
pkit:
  friction:                       # functionality block — shape owned by the backbone
    anchors: { path: [src/cli/**] }
  documentation:                  # role block — one point block per point, each versioned
    reading-evidence:
      schema_version: 1
      last-run: 2026-10-01
```

**How validation reads it** (COR-053 point 10):

- **A key that names a shipped functionality** is that functionality's block.
- **Any other key** is a role block only if every child is a point block that carries `schema_version`.
- **Anything else** is an unknown-key error. It names the nearest known key, from the functionality names, the active role words and their qualified forms. It also reminds that a role block needs a versioned point block.

**What the active wiring decides.** Which roles are active, and at which version each point stands, is read from the wiring resolver. It is read once for each run of `pkit validate` ([the lifecycle reference, "How the wiring is resolved"](../lifecycle/manifest.md#how-the-wiring-is-resolved)). It gives the qualified roles with an active provider. For each, it gives every data point that provider defines, with the point's version and schema.

- **An orphan:** a role block whose role has no active provider. It is kept and reported, never an error, and validated again when a provider returns.
- **A shared bare word:** a bare role word that two active roles share names neither of them. It is an error until the key is written qualified.
- **An inert point block:** inside an active role, a point block whose `schema_version` differs from the provider's point, or that names no data point the provider defines. It is reported, and its body is not validated.
- **A compatible point block:** its body, all but `schema_version`, is validated by the provider's point schema. Its errors fail as any malformed block does. A point schema that cannot be applied is reported, and the body is left alone.
- **So:** a misspelt `frictoin:` fails loudly. A `documentation:` block that an uninstalled capability left behind waits quietly.

**Key form.** A role block's key is the role word alone, and the active provider resolves its qualifier. The qualified form is written in two cases:

- **Two active roles share a word.** The install plan that brings the second role lists the artefacts whose keys change. They are rewritten only with consent.
- **A role word equals a functionality block's name,** always.

## The friction block

The `friction` functionality block is what an artefact carries for COR-050: what makes it true.

- **Its answers live elsewhere.** An answer, such as when the artefact was last revalidated, lives in an answer file of a change's own. It never lives in the block (COR-062 point 1). The checks read answers there, and read an answer in a block only in history.
- **Who owns what:** COR-050 owns the keys, `container.schema.json` fixes their shape, and `pkit validate` applies it.

### Where it sits

The block sits inside the container, in both of the container's forms. The artefact's own fields, such as `id`, `status` and whatever defines it, stay outside the container.

- **A document** carries it in its front matter.
- **A collection file** carries it in each entry. A collection file is a Markdown file whose front matter maps ids to entries. An entry's content is its data, and the body section headed by its id.

```yaml
# a document                              # a collection file
---                                       ---
id: cli-guide                             name: cmn
pkit:                                     RS-CMN-001:
  friction:                                 status: accepted
    anchors: { path: [src/cli/**] }         pkit:
---                                           friction:
                                                anchors: { record: [COR-050] }
                                          RS-CMN-002:
                                            status: draft
                                            pkit: { friction: { anchors: { artefact: [RS-CMN-001] } } }
                                          ---
                                          ## RS-CMN-001 — Name things
                                          …
```

### Fields

The block holds three keys, of which an artefact writes `anchors` or `unanchored-because`, never both:

| Key | Meaning |
|---|---|
| `anchors` | What makes the artefact true, grouped by kind: `path`, `record`, `artefact`, and any kind an installed capability registers. Each list is non-empty, with unique entries. An artefact without anchors is unanchored, which is reported, never an error. |
| `unanchored-because` | In place of `anchors`, for an artefact with nothing to anchor to. It is the reason a person, or the delegate a person named, accepted it with none ([COR-064](../decisions/core/COR-064-answer-delegate.md) point 1). An example is a person's part in the work that no code carries out. It is non-empty text (COR-050 point 1). |
| `last-check` | Written only by a tool: `pkit friction record-status`, the command the job after a merge runs, and only when the status changes. It holds `state` (`current`, `stale` or `deferred`), `as-of`, the commit checked against, and `since`, where the staleness came from. Friction never reads it. |

**The kinds of anchor:**

- **`path`:** files or globs, relative to the repository's root, with `**` across folders. The anchor stands on each file's mode and content.
  - **A Markdown file a place holds** is read as an artefact's content is, with every `pkit` container in it left out. So the status `record-status` writes into such a file asks nothing of the anchor.
  - **Any other file** is read as stored (COR-050 point 5).
- **`record`:** an identified record, such as a decision, or one point of it (COR-050 point 2).
  - **A point** is the record's id, `#`, and the id a point heading opens with, such as `COR-058#4`, `PRJ-NNN#D1` or `living-docs:DEC-001#3`.
  - **A `#` followed by anything else** makes a malformed block.
- **`artefact`:** another artefact, by its id. A document may also be named by its path from the repository's root.
  - **One part of a document** (COR-050 point 2): the artefact, `#` and a heading's slug names one section, such as `docs/guide.md#installing`. The artefact and a bare `#` name its lead, the body before its first heading, such as `docs/guide.md#`.
  - **A slug** is the heading's title in lower case. Every character but letters, digits, spaces and hyphens is dropped, and each space becomes a hyphen.
  - **How a value splits:** a value that names an artefact whole, `#` included, is read whole. Any other value splits at its last `#`. The schema admits any text, and validation judges the part ("Validation findings" below).
- **A kind a capability registers,** as `friction.kinds` in its package metadata. living-docs registers `source`, an outside source, captured as the version read ([the lifecycle reference, "How a registered anchor kind is resolved"](../lifecycle/manifest.md#how-a-registered-anchor-kind-is-resolved)). A kind is a word, and its values are a list, as for the three above.

**`unanchored-because` never stands beside anchors.** The unanchored measure lists an artefact with a reason apart, with its reason. It counts only those without one (COR-050 point 8, [the CLI reference, "friction check --all"](../cli/README.md#friction-check---all---json)). Validation refuses the reason beside anchors ("Validation findings" below).

**Unknown keys** anywhere in the block are refused, except under `anchors`, where a key is a kind. There any word is admitted, and a kind nothing installed resolves is reported, not refused ("What the pass warns of and reports" below). The block carries no version, and is migrated when it changes.

### The block holds no answer

A revalidation, its deferrals and a revisit entry live in answer files of each change's own ("Answer files" below). A `revalidated` block or a `revisited` list left in the block fails validation. The finding names the move that takes it out (COR-062 points 10 and 11).

### Where artefacts are looked for

Artefacts are looked for only in the declared places:

- **The project's places:** `friction.places` in `.pkit/project/config.yaml` <!-- unanchored: names the file the step reads or writes, not its content -->. Each is a path or a glob from the repository's root. A folder, or a glob ending in `**`, means every Markdown file beneath it.
- **Each installed capability's places:** `friction.places` in its `package.yaml`.

**A capability's place** is an object, `{path, location?, type?, revisits?, derived-links?, description?}`. That is the package schema's only shape for it ([the lifecycle reference, "The connection, documentation and friction blocks"](../lifecycle/manifest.md#the-connection-documentation-and-friction-blocks)).

- **With `location`,** `path` lies inside that entry of the capability's `docs.locations`. Without one, `path` is relative to the repository's root.
- **A `type`** names the type the place's artefacts take ("A place may give a type" below).

**Where a location lies** is read one way, by every reader of a capability's locations: the readers of the documentation roots, and this walk.

- **A recorded location wins:** one recorded for the name in `.pkit/capabilities/<name>/project/docs-locations.yaml` ([COR-049](../decisions/core/COR-049-documentation-roots.md) point 5).
- **Otherwise** the entry, `{path, root?}`, lies at `path` under the internal documentation root, or under the user root with `root: user`.
- **The state read:** the walk reads the recorded location from the same state as the rest, the change check's base commit included.

**A capability place that is not walked** is a validation finding. So a place under which nothing is found never looks like an empty one. Such a place is one of these:

- a place in any other shape, plain text included
- a place naming a location that `docs.locations` does not declare, or declares in another shape with nothing recorded
- a place that leaves the repository, through a link included ("Validation findings" below)

**A place is never a synced tree** (COR-050 point 14).

- **What is left out:** a file a declared place matches that arrives in the repository as a copy. That holds for the project's places and the capability's, each glob expanded and each match tested. The place is a validation finding, and its other matches are walked.
- **What a copy is:** one a sync writes, or one pulled whole from the outside source a capability is pinned to ([COR-041](../decisions/core/COR-041-external-source-distribution.md)).
- **Who decides:** the lifecycle's ownership predicate, `is_synced_copy` ([the lifecycle reference, "The ownership predicates"](../lifecycle/README.md#the-ownership-predicates-ownershippy)). It is read from the tree's own `.pkit/lifecycle/ownership.py`, on the working tree's install state.
- **What it keys on:** a capability's recorded origin, and whether the repository is the one the methodology is authored in, never the path.
- **So, by origin:** a backbone area's README, or a `kit-shipped` capability's, is refused in an adopter, and is a place in the methodology's source repository. An `externally-sourced` capability's README is refused in both, since it is authored in another repository.

**A component's held documents are never artefacts** (COR-050 point 1). A capability may declare, in its `friction.held` list, folders of documents that belong to it but are not artefacts. An example is a log of the reviews it carried out, such as software-analysis's revalidation records.

- **Its shape:** `{location, path, description?}`. A held folder names the location it lies within, and is a folder there. Or it is a glob of folders at one depth whose last segment is plain, such as `*/revalidations`, never `**`.
- **How it is read:** it is resolved and matched as a capability's place is. A glob holds every file beneath each folder it names.
- **What it takes out:** no place walks a file it holds, whether a root's, another component's, the project's or its own component's. So neither measure counts such a file.
- **What discovery does with one:** it lists the file with its owner, and with whether `exclude` leaves it out. Its owner then counts an excluded file no more than the measures count an excluded artefact. Discovery reads only its front matter, where a friction block anywhere is a validation finding (below).

**A held folder is bounded,** so that one component holds each held file, and no declaration empties another's. Where it does one of these, it holds nothing, and the packages pass refuses it at its entry ([the lifecycle reference, "Validation: the package schema"](../lifecycle/manifest.md#validation-the-package-schema)):

- it equals or encloses a documentation root, or any declaration's place, its own component's included
- it shares a file with another component's held folder, or with a rule-set folder, whose files are rules and stay artefacts (COR-051 point 2)
- it equals, encloses or lies within another held folder of its own component

**Where a held folder may lie.** It may lie inside a declaration's place, a root's say, or share some of its files, as its own component's place glob may. That is what a held folder is for, and the held folder wins. Where two held folders of one component share some files, the first declared holds each.

**A project declares no held folders** (COR-050 point 14).

- **What it does instead:** it declares its own places, and can narrow them. It keeps what must not count out of the measures with `exclude`.
- **What `exclude` does:** an excluded file is still an artefact, read and its anchors checked. It is only neither counted nor asked for an answer.
- **Why a component needs held folders:** a component's files sit in places it cannot narrow, in a configuration it does not write.

**What the walk reads.** Front matter outside the places is never read, and a plain YAML file in a place is no document.

- **One listing:** the places are matched against one listing of the working tree: the files git sees, tracked and untracked but not ignored. Outside a git work tree, where git gives no view, the listing is every file.
- **The same artefacts everywhere:** that listing is the one the change check reads as its head. So validation, the friction writers and the change check find the same artefacts in the same working tree.
- **A link** is a file of that listing, never followed and never read as a document. Nothing beneath a linked folder is walked, and the walk never reads a file the repository does not hold.

**The rest of the `friction` key** is taken by the same reader: `mode`, `surface` and `exclude`. So the configuration is read once, and what `exclude` leaves out is decided once, there.

- **What the walk records:** on every file, artefact and held document it reads, the `exclude` entry that covers it. The checks read that from the artefact, rather than match its path again.
- **What an excluded artefact is spared:** the measures and the debt, and any answer in the change check ([the CLI reference, "Friction checks"](../cli/README.md#friction-checks)).

**Each state's `exclude` is its own.** The change check reads its base under the exclusions its base declared. The whole-repository check reads an artefact's revalidation point under the exclusions that point declared.

- **So a change to the exclusions** is a change to the path anchors whose files it moves (COR-050 point 7).
- **A narrowing** is always asked for an answer.
- **A widening** is asked for one where a file it took changed while the anchor stood on it. Otherwise it is reported.
- **A state whose `exclude` does not read** is read as the state it is compared with, and reported. It is never read as one that leaves nothing out.

**The places declared to hold rule sets** are walked too, since a rule is an artefact found where artefacts are found (COR-051 point 2). A rule-set file's entries are the values of its `rules` map, one artefact for each rule. Its other keys are the set's own data ("Rule-set files" below).

**`pkit friction artefacts --json`** prints what this walk finds ([the CLI reference, "friction artefacts"](../cli/README.md#friction-artefacts---at-rev---json)). A component's script reads it, instead of walking the places or listing the files itself. It prints:

- the places, with the files each matches and what it skips
- the files
- the artefacts, with their anchors and the rule sets whose scope covers each, and an entry's section span
- the held documents, with their owner
- the files within each capability's documentation location that no place or held folder of that capability holds

With `--at <rev>`, the same walk reads one commit. So a script reads another state, such as what the default branch holds, without listing the commit itself.

### A place may give a type

A type is a declared name for what an artefact is, and an artefact has one type or none ([COR-056](../decisions/core/COR-056-artefact-types.md)).

- **A capability's types:** it declares them in its type registry, `friction.types` in its `package.yaml` ([the lifecycle reference, "The connection, documentation and friction blocks"](../lifecycle/manifest.md#the-connection-documentation-and-friction-blocks)). It names one on a place as `type`. Its full name is `<capability>:<name>`.
- **A project's place** is a bare path, which gives no type, or `{path, type}` in `.pkit/project/config.yaml` <!-- unanchored: names the file the step reads or writes, not its content -->. Its `type` is a bare type of the project's own, or a capability's type whose registry admits project places.
- **What the configuration schema refuses:** a `backbone:` type, since no place names one, and a value that is not a type's name.
- **A rule** is always of the type `backbone:rule`.
- **How a type resolves:** discovery resolves every other artefact's type from the places matching its file, and every reader takes it from there. The order of places, the kind field and the tie are [the CLI reference's, "Artefact types"](../cli/README.md#configuration-file).
- **What a type changes:** neither which files hold artefacts, nor any artefact's content. Friction never reads a type.
- **What `pkit friction artefacts --json` gives:** each artefact's type, the place that gave it, the types in a tie and the matching places in order. It lists every type registry too.

### A place may declare links

A capability names, under `revisits` on one of its places, the links of the artefacts the place holds (COR-050 point 16). A link's source changing asks for a revisit of its targets ([the lifecycle reference, "The connection, documentation and friction blocks"](../lifecycle/manifest.md#the-connection-documentation-and-friction-blocks)).

Each link names the artefact's own fields, outside the `pkit` container, that choose its targets. It does so in exactly one of two ways, and names its trigger fields:

- **`targets`:** the field that lists the link's targets, each by its anchor's value as the anchor writes it. A value names every anchor of the artefact that has it.
- **`all-but`:** the fields that list the anchors that stay out, each by its value. Every other anchor of the artefact is a target, one added later included. Use it where nearly every anchor binds both ways. A field listing the targets would copy the anchors, and an own field is content.
- **`when`:** the trigger fields. A change to one between the base and the head, compared parsed, asks for a revisit of each target.

A field the artefact does not write, or one that is no list of texts, lists nothing. So such a `targets` field gives no target, and such an `all-but` field keeps none out.

- **Which places' links:** an artefact takes the links of every capability place that matches its file. So a broader place of the project's switches none off.
- **A project's place** declares none.
- **What the change check asks of a triggered link** is the CLI reference's, "Friction checks".
- **An older backbone** refuses `revisits` as an unknown key of a place. So a capability that declares a link names, in `requires_backbone`, a backbone that knows it.

### A place may declare derived links

A capability names, under `derived-links` on one of its places, the form of the links its own command writes there (COR-050 point 5). Its check holds those links equal to the data they come from.

- **Each form** is `{target, description?}`. `target` is a regular expression, in Python's dialect, that the target of an inline link `[words](target)` matches whole.
- **A target that does not compile:** the `packages` check fails it, and discovery reads it as declaring nothing.
- **What friction does with them.** Where a check compares the body of a file a place holds, it reads each such link in running text as its words alone. Running text leaves out fenced code, code spans, comments and headings. So a change that only moves such links asks nothing of what rests on the file. The CLI reference, "Friction checks", says how each check reads them.
- **Which declaration.** A comparison reads the forms of its later state, from every capability place matching the file there, and applies them at both states. A project's place declares none.
- **Declared and trusted.** Nothing checks that a form takes only links the command writes. Declare the narrowest form that takes them, since a link of the form that a writer adds is set aside too.
- **Changing a form.** Keep the old form declared beside the new one, so that a state written before the change reads alike.

An older backbone refuses `derived-links` as an unknown key of a place. So a capability that declares one names, in `requires_backbone`, a backbone that knows it.

### What an older backbone does with them

A backbone that predates types reads every declaration forgivingly. It passes over what it does not know, without failing a reading command:

- **A project's place written `{path, type}`** is not read as a place, so nothing under it is walked. That backbone's `pkit validate` refuses the entry, since its schema takes only a path.
- **A capability's `friction.types` and a place's `type`** are not read. The place is walked with no type, and the `packages` check refuses both keys as unknown.
- **A scope written as a mapping** covers nothing, and the `rule-sets` check refuses its shape. A scope written as a list keeps its meaning on every backbone.

So a project that writes a typed place or a mapping scope needs a backbone that knows them. A capability that declares types names that backbone in `requires_backbone`.

### Validation findings

Each of these fails `pkit validate`, in either mode, and names its fix (COR-050 point 12).

**Findings on places and held folders:**

- **A capability place not walked.** It is one not in the shape `{path, location?, type?, revisits?, derived-links?, description?}`. Or it names a location not declared as `{path, root?}`, with nothing recorded for it. Or it leaves the repository: it is absolute, climbs above the root, or resolves outside it through a link.
  - **Where it is reported:** against its `package.yaml`, with a JSON Pointer to the entry.
  - **When:** whenever it is declared, dormant or not. The pass's count line counts it.
- **A place matching a synced copy** (`synced-place`): a declared place, the project's or a capability's, one of whose matches arrives as a copy. "Where artefacts are looked for" above says what a copy is. It is reported against its declaration, `.pkit/project/config.yaml` <!-- unanchored: names the file the step reads or writes, not its content --> or the `package.yaml`, with a JSON Pointer to the entry. It names the synced matches, and is reported and counted as a place not walked is.
- **A capability's surface entry not read.** `friction.surface` is not a list, or an entry in it is not a path or a glob. It is reported against its `package.yaml`, with a JSON Pointer to the entry, or to `friction.surface` itself. It is reported and counted as a place not walked is.
- **A capability's held folder that holds nothing.** It holds nothing, so the places matching its documents read them as artefacts. It is reported whenever declared, dormant or not, against its `package.yaml` and a JSON Pointer to the entry. `pkit friction artefacts` names why, in the folder's `skipped`. It is one of these:
  - one not in its shape `{location, path, description?}`. It has no `location`, or a `**` or a glob in its last segment. Or its path leaves its location, or names a location `docs.locations` does not declare.
  - `friction.held` not a list (`malformed-held`)
  - one leaving the repository through its location or a link (`held-outside-repository`)

**Findings on documents:**

- **A held document whose front matter does not parse** (`held-unparsable-front-matter`), against the document. A friction block in it could not be looked for, so a typo is never a hiding place. It is reported whenever declared, dormant or not.
- **A friction block in a held document** (`held-friction-block`), wherever the front matter holds it. It may be the document's own, an entry's, or a rule's under `rules` or deeper.
  - **Where it is reported:** against the document, with a JSON Pointer to the block, naming the folder that holds it.
  - **Why:** a held document is no artefact, so nothing reads its anchors or its revalidation. It is reported whenever declared, dormant or not.
- **Front matter in a place that does not parse.** It is reported whenever places are declared. It keeps the pass awake, since the check never skips an artefact it cannot parse. So a YAML typo in the only file that carries the container is an error, not silence.
- **Mixed line endings** (`mixed-line-endings`): a file the walk reads, a rule-set file included, written with more than one kind of line ending. It is reported against the file.
  - **Why:** the file is read with every line ending as `\n`. So a carriage return that is part of a value would be read as a line break, and the friction writers refuse the file.
  - **One kind of line ending,** `\r\n` included, reads as the same text with `\n` (the CLI reference, "Friction checks").

**Findings on a block:**

- **A malformed block:** the container schema's errors, or the container rule's. Each is reported against `path` for a document, or `path#id` for an entry, with a JSON Pointer into the block.
- **`unanchored-because` beside anchors** (`unanchored-beside-anchors`): the reason an artefact has none, in a block that lists some. The two contradict each other, so remove one. The schema admits the key alone. The pair is the pass's own finding, against the key's pointer, for a rule of a rule set too.
- **An answer left in an artefact's own block** (`answer-in-block`): a `revalidated` block or a `revisited` list, whatever it holds. No check reads it at the head, only in history.
  - **Its fix:** the error names the move that takes it out, into a new answer file (COR-062 points 10 and 11).
  - **With no answer file at all,** the project's answers have not moved. One error says so (`answers-not-moved`), in place of one for each artefact.
  - **In a file the project receives by sync,** it is a report, since the project cannot mend it there.
  - **Its entries** are also judged for a dangling deferral or revisit, and for a repeated one, below.
- **A dangling deferral** (`dangling-deferral`): in such a block, a `deferred[].anchor` that matches no anchor of the artefact, by kind and value. The pointer carries the entry's index as written.
- **A dangling revisit** (`dangling-revisit`): in such a block, a `revisited[].anchor` that no link of the artefact's places takes as a target.
- **A revisit repeated** (`duplicate-revisit`): an entry for a target an earlier entry names. Each pointer carries the entry's index as written (COR-050 point 16).
  - **With no link at all:** where no place of the artefact declares a link, the entries are reported, never failed (below). That happens after the capability that declared it is uninstalled.
- **A link's field in the wrong shape** (`malformed-link-field`): a field a declared link names, written as anything but a list of texts. The field is its `targets`, or one of its `all-but`.
- **A target no anchor has** (`unanchored-target`): a value in a `targets` field that no anchor of the artefact has, which a trigger could never revisit.
  - **In an `all-but` field,** a value no anchor has keeps nothing out. So the check asks more, and the value is not failed.
  - **Where each is reported:** against the field's pointer, such as `/verified-by` (COR-050 point 16).
- **A deferral repeated** (`duplicate-deferral`): in such a block, a `deferred[]` entry for an anchor an earlier entry already defers, by kind and value.
  - **Why:** the list holds one entry for each anchor (COR-050 point 4), so one anchor never carries two reasons.
  - **Where it is reported:** at each later entry, its pointer carrying its index as written.
  - **Within one answer of an answer file,** a repeated deferral or revisit is a finding of "Answer files" below.

**Findings on anchors:**

- **A cycle between artefacts,** reported once with its path, such as `A -> B -> A`. A self-anchor is `A -> A`.
  - **Where it is reported:** against the anchor by which the cycle's first member rests on the next, under `anchors.artefact` or `anchors.record`.
  - **How it is found:** along the anchors between artefacts, as the order of the truth chain follows them (COR-050 points 5 and 11). An `artefact` anchor counts, an anchor on a section or a document's lead counting as one on the document. So does a `record` anchor, whole or on a point, on a record a place holds, whose file is an artefact.
  - **What closes none:** a record no place holds carries no anchors the checks read, so no cycle passes through it. A `path` anchor names files, so it closes no cycle, even on an artefact's file.
  - **An anchor on a part of its own artefact** is a cycle, and the finding says so. The artefact's own edits would flag it, and so would its own revalidation. So is a record's anchor on itself, or on one of its own points.
- **A dead or ambiguous anchor on a record's point** (`dead-point-anchor`, `ambiguous-point-anchor`), against the anchor's pointer (COR-050 points 7 and 12).
  - **Dead:** its record does not resolve, or holds no point with the id. Or the record writes its points as a list, whose numbers no anchor can rely on until the record is converted to point headings.
  - **Ambiguous:** two points of the record have the id.
  - **How the record is read:** from the working tree, its points as validation's `decisions` member reads them.
- **A dead, ambiguous or refused anchor on a document's section or its lead** (`dead-section-anchor`, `ambiguous-section-anchor`, `refused-section-anchor`). It is reported against the anchor's pointer, whatever made it so, its artefact gone included (COR-050 points 2, 7 and 12).
  - **Dead:** no artefact has the name before the `#`, or no heading of the document has the slug. A renamed heading leaves its anchors dead, and a revalidation records the anchor re-pointed.
  - **Ambiguous:** two headings of the document have the slug.
  - **Refused:** the anchor is on a section or the lead of a collection file, of a collection's entry, or of a record a place holds. The finding names the anchor to use.
  - **For a collection file:** its entries are named by their ids. Use the entry whose id follows the `#`, or whose section holds the heading.
  - **For a collection's entry:** it is cited whole by its id, as is an extension point of a rule, such as `RS-CMN-003#cause-location` (COR-051 point 3).
  - **For a record a place holds:** its parts are its points. Use the record anchor on the point whose id follows the `#`, or whose heading has the slug, or else the whole record.
  - **A whole artefact anchor that names nothing** stays the checks' finding.

### What the pass warns of and reports

**A warning, which fails nothing:** an anchor on a retired point (`retired-point-anchor`). The record retires the id, so the anchor stands on nothing until it is re-pointed. The warning names the point's successors, from the record's `retired-points` (COR-050 point 7).

**Reports, which fail nothing:**

- **An answer on what is gone** (`answer-on-what-is-gone`). It is an answer in an answer file whose location, followed through its file's renames, holds no artefact. Or it defers an anchor, or revisits a target, its artefact no longer has. It answers nothing, and no change can rewrite the landed file that holds it (COR-062 points 5 and 10).
- **Revisit entries on an artefact whose places declare no link** (`orphaned-revisit`), once for its `revisited` list. They are kept, and judged again once a place declares a link (COR-050 point 16).
- **Orphaned role blocks and inert point blocks** in the container, read against the active wiring ("The container" above).
- **An anchor kind nothing resolves** (`unresolved-kind`), against the kind's pointer. It is a kind outside the backbone's three that no installed capability registers, with the nearest known kind as a suggestion. Or it is one whose registration is refused, which fails once, at the registration, in the packages pass.
  - **What the pass does:** it runs no resolver. The change check fails such an anchor where the diff adds it, or takes its resolver away ([the CLI reference, "Friction checks"](../cli/README.md#friction-checks)).
  - **Meanwhile,** its artefact is not judged.
- **A provider's point schema that cannot be applied.**
- **Schema unavailable:** the tree has no container schema that reads, so the block check was skipped. Sync the tree.
- **Ownership unavailable:** places are declared, but the tree carries no `.pkit/lifecycle/ownership.py`. So no match could be told a synced copy, and every match was walked. Sync the tree.

### The configuration's own findings

The settings themselves are the configuration pass's findings, since it owns the file ([the CLI reference, "Configuration file"](../cli/README.md#configuration-file)):

- an invalid `friction.mode`, outside the schema's enum, which is never switched off silently
- a place, a surface path or an exclude path outside the repository: absolute, climbing above the root, or resolving outside it through a link

**A capability's `friction` entries** are the packages pass's, which judges their shape but not where they resolve. So a capability place the walk does not follow, and a surface entry it does not read, are the friction pass's findings too (above).

- **A place matching a synced copy,** of either kind, is the friction pass's as well, since only the walk expands it.
- **What the friction pass never walks:** a place that leaves the repository, and a synced copy a declared place matches.

### When the pass is dormant

The pass is dormant, and prints its counts and nothing else about artefacts, in two cases:

- **No places are declared.**
- **Nothing in them needs judging:** no artefact carries the container, and no file failed to parse.

Dormancy is about artefacts, not declarations. Each of these is reported, and fails `pkit validate`, dormant or not:

- a capability place the walk cannot follow (`malformed-place`, `place-outside-repository`)
- a place matching a synced copy (`synced-place`)
- a capability's surface entry the walk cannot read (`malformed-surface`)
- a held folder that holds nothing (`malformed-held`, `held-outside-repository`)
- a held document that does not parse or carries a friction block (`held-unparsable-front-matter`, `held-friction-block`)

### Rule-set files in the friction pass

The rule-set rule claims a rule-set file before the container rule does. So the `rule-sets` pass reports, once, its front matter that does not parse, and the malformed container of one of its rules. The friction pass still takes its rules into the checks of a reason beside anchors, of deferrals and of cycles.

### What the friction pass leaves to others

Friction itself is the `friction` command group's ([the CLI reference, "Friction checks"](../cli/README.md#friction-checks)). This pass never touches git.

- **The change check,** `pkit friction check`: the three answers, bumps with nothing behind them, and dead anchors of a change. So are an outdated base, the modes and the `--json` document.
- **The whole-repository check,** `pkit friction check --all`: the stale and deferred debt derived from git, with their origins, every dead anchor, anchors too broad, and the two measures. `pkit friction debt` lists its debt oldest first. `pkit friction explain` explains its findings on one artefact.
- **The writers.** `revalidate`, `defer` and `revisit` write answer files. `record-status` writes the block's `last-check`. Each writes only with consent, and never what this pass would refuse.
- **`prune`** removes, only with consent, the answer files in which no answer is live.

## Answer files

A change's answers to friction live in answer files of its own. They never live in an artefact's block, or in a pull request's description (COR-062 point 1).

- **No conflicts:** two changes that answer on one artefact each add a file no other change writes. So their answers never conflict.
- **Its schema:** `backbone/friction-answers.schema.json` fixes the shape.
- **Its reader:** one module, `project_kit.answer_files`, reads answer files for both checks and for every writer.

### Where answer files are: the location rule

An answer file is a YAML file directly in `.pkit/project/friction/answers/`. The backbone fixes the folder, the same in every project (COR-062 point 2).

- **Its owner:** the folder is the project's, and no sync reads or writes it.
- **Its binding:** the file's location binds it to the schema. That rule runs after the configuration file's fixed path, and before every other location rule.
- **What it is not:** no place reads a file there as an artefact, and no anchor stands on one. The declared surface leaves the files out.

```yaml
answers:
  - artefact: docs/guide.md                   # a document's path, or a collection file's path, `#` and the entry's id
    read: [20261021T093000Z-3f9a2c1d.yaml]    # the other answer files on it, present at the change's own head
    revalidated:
      at: 2026-10-22T10:15:00Z
      outcome: unchanged
      unchanged-because: The flag rename leaves the steps as written.
      deferred:
        - anchor: {kind: path, value: src/cli/**}
          reason: The redesign rewrites the page, in #1234.
```

### The fields of an answer file

An answer file holds one list, `answers`, with one entry for each artefact it answers on:

| Key | Meaning |
|---|---|
| `answers` | One entry for each artefact the file answers on. An empty list is refused. |
| `artefact` | The artefact's location when the answer was added: a document's path, or a collection entry's file path, `#` and its id. The checks follow it through the renames of the artefact's file since then (COR-062 point 10). |
| `read` | The other answer files that held an answer on the artefact at the change's own head, live or not (COR-062 point 4). Each is named by its name in the folder. It holds for every answer in the entry. An answer replaces the answers of its kind that it read (point 5). |
| `revalidated` | The revalidation, its deferrals, or both ("`revalidated`" below). |
| `revisited` | One entry for each target of a link whose source's change asks for a revisit of it (COR-050 point 16, "`revisited`" below). |

**`revalidated`** is written on a person's decision, or by an agent that makes a change, and then checked by a reviewer (COR-050 point 3). It is written by hand, or with `pkit friction revalidate` and `pkit friction defer`.

- **`at`:** a timestamp in UTC, `YYYY-MM-DDTHH:MM:SSZ`.
  - **The revalidation point** is the commit where the artefact's answers first carried this parsed value. That is in any answer file, or in history in its block (COR-062 point 6).
  - **Writing back an earlier value** is not a revalidation (COR-050 point 3).
- **`outcome`:** `updated` or `unchanged`. `at` and `outcome` come together.
- **`unchanged-because`:** required with `outcome: unchanged`. It says why the content still holds against this change.
- **`deferred`:** one entry for each anchor whose friction is postponed on purpose. Each holds `anchor: {kind, value}`, any anchor of the artefact named by its kind and value, and a `reason`. The list is kept sorted by anchor.
- **An entry may carry `deferred` alone.** An empty `revalidated` is refused.

**`revisited`** holds one entry for each target, written by hand or with `pkit friction revisit`. A component declares the links on its places ("A place may declare links" above).

- **Each entry's fields,** all three required:
  - `anchor: {kind, value}`: the target, named as the artefact's anchor on it
  - `outcome`: `unchanged`, the target still stands, or `deferred`, a follow-up revisits it
  - `reason`
- **Its order:** sorted by anchor, one entry for each target.
- **Its reach:** an entry answers only the change that writes its reason. It is no revalidation: it changes no content, and moves no revalidation point.

An entry holds a `revalidated` mapping, a `revisited` list, or both. Unknown keys are refused at every level. The shape carries no version, and is migrated when it changes, keeping the parsed value of `at`.

### A change adds answer files

A change adds answer files, and rewrites none its base holds (COR-062 point 3). It removes one only to prune, or to revert.

- **The move,** done once, took each project's answers out of the artefacts' blocks into answer files of their own (COR-062 point 11).
- **What each writer and the move write** is the CLI reference's, "Friction checks".

### A prune is a change of its own

`pkit friction prune` removes each answer file in which no answer is live at HEAD, and adds none (COR-062 point 8).

- **What it keeps:** a file whose removal would change a live answer, such as one whose removal brings back an answer it replaced.
- **What it owes:** committed alone, the removal owes no answer.

### What validation finds in an answer file

Validation checks answer files whenever one exists, dormant or not, through `pkit validate`'s `friction` member (COR-062 point 10). Each of these fails it, in either mode:

- **An answer file that cannot be read** (`unreadable-answer-file`): it does not read as a YAML mapping.
- **An answer file that departs from the schema** (`malformed-answer-file`): no `answers`, an entry naming no artefact, or an unknown key.
- **A second entry for one artefact in one file** (`duplicate-answer-entry`).
- **A second deferral of one anchor, or a second revisit entry for one target, within one answer** (`duplicate-answer-deferral`, `duplicate-answer-revisit`).
- **Two answers that each name the other's file** (`mutual-read`), since neither read the other.

An answer on what is gone is reported, never failed ("What the pass warns of and reports" above). `pkit data validate <path>` applies the schema to an answer file it is named.

## Rule-set files

This section gives a rule-set file's shape: its front matter, its body and its ids. `rule-set.schema.json` fixes the shape of its front matter ("The schemas that ship" above). This area's README holds the rest, under "Rule-set files":

- what a rule set is
- where rule-set files lie
- the checks of their pass
- how their rules bind

### The front matter

A rule-set file's front matter holds the set's data and each rule's machine fields, as in this example:

```yaml
---
rule-set: DOC                          # the set's name, unique among rule sets
version: 2.1.0                         # the set's own version; inheritors pin its major
inherits: [living-docs:LDOC@1]         # a method set with its component, a project set bare
scope: {paths: [docs/**], types: [guide]}  # optional: a plain list of paths is its `paths`
rules:
  RS-DOC-001:
    status: accepted
    origin: {date: 2026-09-27, by: A. Person, why: "A reader finds the answer first."}
    offers: [example-kind]             # an extension point, cited RS-DOC-001#example-kind
  RS-DOC-002:                          # no status: proposed, and binds nothing
    fills: [living-docs:RS-LDOC-003#reader]
    pkit:
      friction:
        anchors: {artefact: [living-docs:RS-LDOC-003]}
  RS-DOC-003:
    status: superseded
    successor: RS-DOC-004
    origin: {decision: PRJ-012}
  RS-DOC-004:
    status: accepted
    origin: {decision: PRJ-012}
checks:                                # optional: the parts of rules that checks enforce
  RS-DOC-001:
    - {check: writing-lint, part: "The first paragraph is at most three sentences."}
---

## RS-DOC-001 — Answer first

The statement.
```

| Key | Meaning |
|---|---|
| `rule-set` | Required. Upper-case letters and digits, starting with a letter. It is unique among all rule sets, and every rule id carries it. |
| `loaded` | `true` makes the set a loaded one ([COR-068](../decisions/core/COR-068-loaded-rule-sets.md)). Its accepted rules bind on the work of the sessions that load its generated file, and on no artefact (this area's README, "Loaded sets"). Absent or `false`, the set is an ordinary one. |
| `budget` | A loaded set's alone: the most words its loaded file may hold, a whole number of at least one (COR-069). A component's loaded set must give one, and a project's own may. An ordinary set takes none, and the schema refuses one there. It is none of a rule's fields, so changing it changes no rule, and needs no new major (this area's README, "Loaded sets"). |
| `version` | Required. The set's own semantic version, not its component's. A new major is due for each change listed below the table (COR-051 point 7). |
| `inherits` | The sets this one inherits, each pinned to a major: `<SET>@<major>` for a project rule set, `<component>:<SET>@<major>` for a method one. |
| `scope` | Which artefacts the set's rules apply to, by the paths of their files and by their types (COR-051 point 2). Its keys are below the table. |
| `rules` | Required. Each rule's id, mapped to its machine fields below. |
| `status` | `proposed`, `accepted`, `superseded` or `withdrawn`. A rule with no status is proposed. |
| `origin` | Where the rule came from, in one of two forms, never both. It is the decider's own words, `date` (`YYYY-MM-DD`), `by` and `why`. Or it is a decision record, `decision: COR-NNN`, `PRJ-NNN`, `ADR-NNN` or `<capability>:DEC-NNN`. Either form may add `source: {kind, value}`, a captured record of where the words were said. |
| `offers` | The extension points the rule offers, by kebab-case name. |
| `fills` | Extension points of inherited rules that this rule fills: `RS-<SET>-NNN#<point>`, optionally with the owning component in front. |
| `successor` | The rule that replaces a superseded one. Written by, and only by, a superseded rule. |
| `pkit` | The methodology's container, with the friction block every artefact may carry ("The container", "The friction block" above). |
| `checks` | The parts of the set's rules that checks enforce, as the rules' owner declares them (COR-051 point 2). Its form is below the table. |

**When a new major is due** (COR-051 point 7):

- an accepted rule is withdrawn, superseded or tightened
- an offered extension point is removed
- a new accepted rule is added
- what the set inherits changes: a set added or dropped, or a pin moved to another major

**The keys of `scope`.** A scope is a mapping of three keys, each a list that is not empty:

- **`paths`** selects an artefact whose file one of them matches. Each path is read as a place is.
- **`exclude`** leaves a selected artefact out.
- **`types`** selects an artefact whose type, or a type in contention for it, is one of them (COR-056 point 3). A type is `<component>:<name>`, `backbone:rule`, or a bare type a project's place gives. A type no owner declares is an error.
- **A key left out** selects everything: every file for `paths`, every artefact, typed or not, for `types`, and nothing left out for `exclude`.
- **A scope needs `paths` or `types`.** A plain list of paths is its `paths`, so a scope written as a list keeps its meaning.
- **A method rule set takes no scope,** and a scope on one is an error.
- **`pkit friction artefacts`** names on each artefact the rule sets whose scope covers it.

**The form of `checks`.** Each rule's id maps to a list of declarations, each `{check, part}`.

- **`check`** names the check, and whose it is:
  - `backbone:<command>` for a check of the backbone: a `pkit` command, its words separated by spaces, such as `backbone:friction check`
  - `<component>:<command>` for a command a component registers in its package metadata, such as `living-docs:validate`
  - a bare name for the project's own tool
- **`part`** says which part of the rule the check settles.
- **Where a check enforces its part:** only where the rule binds (this area's README, "Where an accepted rule binds"). Whoever judges the rest of the rule leaves that part to it.
- **Beside the rules, never in them.** The declarations sit beside the rules, never in a rule's entry. So they are no part of a rule's content. Declaring a check, or changing one, flags nothing anchored to the rule.
- **`pkit rule-sets reach`** lists the declarations on each rule, each with whether its check is there.

Unknown keys are refused at every level, each with the nearest known key. The shape carries no version of its own, and is migrated when it changes.

### The body

The body holds one section for each rule, headed by its id and its title, such as `## RS-DOC-001 — Answer first`, at any heading level. The section holds the rule's statement.

- **A rule's content,** for friction, is its data entry together with that section.
- **Headings inside fenced code** are not sections.

### Ids

A rule's id is `RS-<SET>-NNN`: the family prefix, the set's name, and a number of at least three digits, zero-padded below 100 (COR-051 point 3). An extension point is written after `#`, as in `RS-DOC-001#example-kind`.

- **Never renumbered, never reused.** Superseded and withdrawn rules stay in the file with their ids and sections. So a new rule under a retired id is a duplicate.
- **What this pass cannot see:** whether an id was reused after its rule was deleted outright. One state of the repository does not show it, and this pass reads no history.
