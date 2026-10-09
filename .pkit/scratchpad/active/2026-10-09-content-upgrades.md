---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-09
---

# Content upgrades — a project's own content follows the methodology's format changes

A design for #1394. It sets how a project's own records, analysis artefacts and pages follow when the methodology changes their format.

- **Raised by:** the part-anchors design's question 4 (#1387, PR #1392). On 9 October the maintainer parked it. A one-off conversion command is the wrong shape, and one general mechanism, part of upgrading, should answer it.
- **Read from main at `78837af9`:** the records, the code and the migrations below. software-analysis DEC-001 is read as refined in PR #1391, which has not landed.
- **Citations:** records by id and point. Code, READMEs and migration scripts by file and line at `78837af9`, since their text has no permanent ids.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers the four questions, one at a time. The issues in "Slicing" are filed on the maintainer's go.

## The question

When the methodology changes the format of content a project owns, how does that content follow, and who decides that it does?

## In short

A content upgrade converts a project's own content from one format to the next. The component that owns the format ships it beside its migrations, and it changes nothing without consent.

- **Beside migrations, not one of them:** a migration carries installed state across a version. A content upgrade carries the project's own files, which the methodology does not manage.
- **Keyed on the content, not on the version:** each upgrade can tell which units are still in the old format. So a skipped version, a re-run or an interrupted run needs no ledger.
- **Required or optional:** required when the owner's check at the new version fails the old format. Optional when the old format stays valid.
- **The tool alone, or a person's choice:** the tool converts what reads one way. Where a unit reads two ways, it asks or writes a proposal, and never guesses.
- **Discovery:** the upgrade's output, `pkit status`, validation's severities and a check on each change.
- **A mixed state is legitimate and bounded:** old units may stay, by the project's recorded choice. New units follow the current format, and a check on each change keeps it so.
- **Consent and review:** a diff in the working tree, never a commit the tool makes. One content upgrade per commit, and an optional one in a pull request of its own.
- **Friction:** a converted unit flags its dependants. The upgrade lists them and proposes an answer for each, and never writes one.
- **Placement:** a new core record, with COR-010 and COR-001 refined.
- **#1387's question 4:** an optional backbone content upgrade converts a project's list-form records. project-kit's own records go first, by the same command.

## The cases

Four format changes need the mechanism now. The search found others it reaches, and some it leaves to other mechanisms.

### The four known cases

| Case | Owner | Class | Who converts |
|---|---|---|---|
| A record's points become headings (#1387) | backbone | optional | the tool, where a record has one list. Otherwise a person chooses. |
| An analysis kind's structure changes (DEC-001 point 1 as refined in PR #1391, #1363 to #1368) | software-analysis | required for live artefacts. Never for revalidation records or withdrawn artefacts. | the tool adds the part's heading and hint. A person fills the part. |
| Actors move to one file each (#1346) | software-analysis | required | the tool. Each move owes a revalidation, a person's decision (COR-050 point 3). |
| A page kind's structure changes (`page-kinds.yaml`, RS-LDOC-004) | living-docs | required where the validator fails a page without the new section | the tool adds the heading. A person writes the section. |

- **The records:** 555 points in 97 records, in four forms (the part-anchors note, "How records number their points"). 47 of the 97 are project-kit's own.
- **Note:** #1346 owes adopters nothing, since software-analysis is installed only in project-kit's clones (#1346, "No migration for adopters").

### Others the search found

- **Within reach:**
  - **#1366, templates rendered from a kind's structure:** a reworded template keeps its old placeholders recognised, append-only (`.pkit/capabilities/software-analysis/scripts/_lib/placeholder.py:18-22`). That is tolerance, the way a change avoids being required.
  - **#1367, a project's own `structures.yaml`:** project data with a `schema_version`. A shipped structure change can orphan its entries.
  - **project-management's workflow overrides:** three migrations only warn about an override at an old `schema_version` (`.pkit/capabilities/project-management/migrations/0.15.0/001-workflow-yaml-schema-v2.sh:16-22`). Editing it "would silently clobber adopter intent" (project-management DEC-033 D6).
- **Outside it:**
  - **#1350, pages rewritten to WRITE, and #859 and #1177, records without revision narration:** each needs a person's reading of every sentence. No transform exists, so discovery stays with the rule sets and the validator's warnings (`src/project_kit/decisions_validate.py:288-296`).
  - **#1334, markers on pkit's parts of issues and pull requests:** that content lives in the tracker, not in the repository.
  - **#842, label palettes:** tracker state. Its posture, to report and never delete, matches this design's.

## Today

Migrations carry a project's installed state across a version. No rule says plainly what a migration may touch.

### What a migration is (COR-010)

- **Its job:** bridge installed state from one version to the next (COR-010, "Three migration scopes per tier").
- **Its trigger:** a change that breaks against installed state ships one in the same change-set (COR-010, "Migrations are mandatory on adopter-breaking surface changes").
- **Its form:** a bash script under `<major>.<minor>.0/`, run with `ROOT` set. It is idempotent by detecting applied state (`.pkit/lifecycle/README.md:676-713`).
- **Its window:** every version directory above the installed minor, up to the target's (`src/project_kit/migrations.py:55-96`). Nothing records which scripts ran.
- **Unattended:** it cannot ask, and a non-zero exit halts the run (`src/project_kit/migrations.py:99-141`).
- **The author's check:** `pkit migrations check-diff` finds renames and removals in kit-owned trees (`src/project_kit/migrations.py:220-286`). A modified file triggers nothing.

### What a migration may touch

No one rule settles it, and three sources pull different ways.

- **COR-001 keeps the core off project-owned paths:** "The core layer never reads from or writes to these paths" (`.pkit/decisions/core/COR-001-content-mechanisms.md:33`). A seeded file is the project's once written (line 51).
- **COR-010 keeps removal off adopter content:** "Adopter content is never touched" (COR-010, "Lifecycle operations apply uniformly", item 4). Adopter customisations "are never core-managed by definition" (its Implications).
- **COR-048 opens one door:** a configuration key may be written "by an upgrade migration that the owning record specifies, where running the upgrade is the consent" (COR-048 point 5).
- **In practice, several scripts write project-owned files.** Each writes configuration, wiring or seeded state, never prose:
  - `.pkit/migrations/backbone/1.150.0/001-keep-process-journal-logging.sh:11` adds a configuration key, citing COR-048 point 5.
  - `.pkit/migrations/backbone/1.54.0/001-seed-architect-overlay-categories.sh:23` adds categories to the project's overlay.
  - project-management's `0.5.0/001` and `0.55.0/004` move keys between its configuration and the backbone's.
  - claude-code's `0.5.0/001` adds an include line to the host `CLAUDE.md`.
- **Where intent could be lost, migrations only warn,** as for project-management's workflow overrides (DEC-033 D6).
- **No migration has rewritten** a record, an analysis artefact, a page or a scratchpad note. Such changes were made by hand (#860, #1350) or avoided by tolerance (#1366, #797).

### The ownership predicates

- **`is_sync_managed`:** whether a path is the methodology's to manage (`.pkit/lifecycle/ownership.py:275`). Everything outside `.pkit/` reads as unmanaged (`.pkit/lifecycle/README.md:799`).
- **`is_synced_copy`:** whether a path arrives as a copy a sync makes (`.pkit/lifecycle/ownership.py:402`). In the methodology's source repository nothing is a copy (`.pkit/lifecycle/README.md:809`).
- **No migration asks either.** A script runs in bash with `ROOT`, and nothing checks what it writes.

### Consent precedents

- **The configuration writer (COR-048 point 5):**
  - interactively, by asking once
  - non-interactively, only with an explicit confirmation flag
  - by an upgrade migration its owning record specifies, where running the upgrade is the consent
  - with nobody to ask and no flag, nothing is written
- **Role-block keys (COR-053 point 10):** an install plan lists the artefacts whose keys would change, "rewritten only with consent". The lifecycle README says "rewriting it is the project's, with consent" (`.pkit/lifecycle/README.md:621`).
- **Friction's writers (COR-050 points 3 and 13, core rule 20):** nothing is written as a side effect of checking. An answer on an artefact is a person's decision, shown word for word.
- **Rule-set pins (COR-051 point 7):** a new major of an inherited set is reported in status. It fails validation until the project reviews it and updates the pin.
- **Point blocks (COR-053 point 10):** a point block carries its schema version. One the active provider does not match is inert and reported, never rewritten.

### Upgrade, sync and capability versions

The lifecycle README contradicts itself at lines 758 and 767. Line 767 holds.

- **Line 758 says** the backbone-wide upgrade "does not move capability versions". Line 723 says so too, and so do the code's comments (`src/project_kit/upgrade.py:794`, `:829-830` and `:1044-1054`).
- **Line 767 says** it "moves every kit-shipped capability at once".
- **The code moves them.** `pkit upgrade` runs sync (`src/project_kit/upgrade.py:213`), and sync refreshes each installed kit-shipped capability (`src/project_kit/sync.py:376-382`). The refresh runs the capability's migrations, copies its tree and restamps its version (`src/project_kit/capabilities.py:1124-1173`).
- **What line 758 gets right:** the backbone-wide dependency check reads the installed versions before sync. So only the refusing direction applies (`src/project_kit/upgrade.py:1038-1095`).
- **Three paths move a capability's version:** `pkit sync`, `pkit upgrade` through sync, and `pkit capabilities upgrade` (`src/project_kit/cli.py:4314`). Only `pkit upgrade` runs the backbone's migrations.
- **Why it matters here:** a required content upgrade hooked to one path would be skipped by the other two.

### Pins and skipped versions (ADR-049)

- **A pin routes every command** to the pinned release's code (ADR-049 points 1, 2 and 4). So every clone of a project sees the content upgrades of the release its pin names.
- **`pkit upgrade` goes to the latest release** and raises the pin last (ADR-049 point 7, `src/project_kit/upgrade.py:219-227`). A project can skip many versions in one hop.
- **There is no path down.** An older pkit refuses a project whose content or pin is newer (`.pkit/lifecycle/README.md:732-739`).

## Established practice

Each tool below answers part of the question. What each teaches is under its *Teaches*.

- **Angular, `ng update`:** a package ships migrations with its release, and the update runs them on the user's code.
  - Required migrations run during the update. Optional ones are announced, then run by name with `--migrate-only` and a version range.
  - It refuses a working tree with changes unless `--allow-dirty` is given. `--create-commits` makes one commit per migration.
  - **Teaches:** the owner of a format ships its transform, and required and optional ones are kept apart. A clean tree and a commit per migration let each diff be reviewed alone.
- **Rust, editions and `cargo fix --edition`:** each crate declares its edition, and crates of different editions build together, indefinitely.
  - Compatibility lints point at what would move. `cargo fix` applies the fixes a machine can make and leaves the rest as warnings. The person then raises the edition field.
  - **Teaches:** a mixed state can be legitimate and permanent. The tool does the mechanical part and shows the rest.
  - **Note:** the edition is declared because the same text can mean different things in two editions.
- **Rails, `app:update`:** it walks each file the new version's generator would change. It shows a diff and asks per file whether to overwrite, skip or show the diff.
  - New defaults arrive in a file of their own, flipped one by one before `load_defaults` is raised.
  - **Teaches:** a file a person may have edited changes only with that person's consent. A project-level format can move in steps.
- **Django, migrations:** `migrate` applies pending migrations, recorded in a table, and `showmigrations` lists them.
  - `makemigrations --check` fails a change whose models moved without a migration.
  - **Teaches:** an author-side check that a format change ships its transform, and a listing of what is pending. Its ledger suits a database, whose state cannot be read back from a file's shape.
- **Codemods, jscodeshift and `@next/codemod`:** a named transform runs on chosen paths, with a dry run, and leaves a diff. Nothing records that it ran.
  - Next.js later folded its codemods into `@next/codemod upgrade`, which offers the ones relevant to the versions crossed.
  - **Teaches:** standalone transforms drift into the upgrade path, since people do not know which to run.
- **Terraform, `0.12upgrade` and `0.13upgrade`:** each shipped in one release line and was removed in the next.
  - A project two versions behind had to install the release in between to run it.
  - **Teaches:** a transform tied to one transition strands a project that skips it. Tie it to the content's format, and keep it while old content can exist.

## What a content upgrade is

A content upgrade converts units of a project's own content from one format to the next. The component that owns the format ships it, and the project consents to what it writes.

- **A unit:** one record, one artefact, one page or one collection file. An upgrade converts a unit whole or leaves it.
- **Who ships it:** the owner of the format.
  - **The backbone** owns the record format, so turning points into headings is the backbone's.
  - **A capability** owns its kinds. An analysis kind's structure is software-analysis's, and a page kind's is living-docs'.
  - **A project** ships none to itself, since it changes its own formats as it likes.
- **What it declares:**
  - **an id,** permanent and namespaced, such as `software-analysis:actor-files`
  - **the version** of its component that introduced the new format
  - **its class,** required or optional
  - **its reach,** the kinds of unit it may convert
  - **the upgrades it builds on,** if any
  - **a detect command and an apply command**
- **Where it is declared:** a capability names its commands in its package metadata, as it names a validator (COR-055 point 3). The backbone keeps its own in its code.
- **Detect:** a read-only query under the backbone's command limits (ADR-057 point 3). For each unit in reach it answers *convertible*, *needs a choice* with the candidates, or *waiting* for an earlier upgrade.
- **Apply:** converts the units named, with the choices given. It writes the working tree and nothing else.

### What it may touch

A content upgrade touches only the format of project-owned units in its reach.

- **Never a synced copy** (`is_synced_copy`). A synced copy arrives converted, with the sync that brings it.
- **Never history:** a revalidation record, a withdrawn artefact, or any text a person decided (DEC-001 point 1 as refined, RS-WRITE-013).
- **Never an answer or an anchor:** a unit's `revalidated` block, its deferrals and its anchors stay byte for byte. Re-pointing an anchor is a revalidation, so it is a person's (COR-050 point 6).
- **Never a claim of judgment:** it writes no `None.` into a part it adds, since `None.` says a person considered the part (DEC-001 point 1 as refined).
- **Never another component's units:** a capability converts its own kinds, in the places it declares (COR-050 point 1).

### How it differs from a migration

| | Migration (COR-010) | Content upgrade |
|---|---|---|
| Carries | installed state | the project's own content |
| Runs | unattended, in bash | by a command that can ask |
| What is pending | the version window | what detect finds |
| Consent | running the upgrade | asked, or running the upgrade for a required one |
| Leaves | changed installed state | a diff in the working tree |
| Friction | none, since a synced tree is never a place | on every dependant of a converted unit |

## Required versus optional

A content upgrade is required when the owner's check, at the version that ships it, fails a unit left in the old format. Otherwise it is optional.

- **Required:** the old format no longer passes, so the project cannot stay valid without converting.
  - **DEC-001's live artefacts** are "always migrated to the current structure" (DEC-001 point 1 as refined, "When a structure changes").
  - **It is a COR-010 trigger in all but name:** the change breaks against what a project has. So the change that makes the check fail ships the required upgrade in the same change-set.
- **Optional:** the old format stays valid, and the new one gains something, such as part anchors.
  - **A project's list-form records** stay valid, and cannot be anchored by part until converted (the part-anchors note, "Migration").
- **How the class is declared:** in the upgrade's declaration. A test holds it honest: the owner's check fails a unit in the old format exactly when the class is required.
- **A change may avoid being required** by tolerating the old format, as #1366's append-only placeholders do. The owner chooses, and ships an optional upgrade or none.
- **A required upgrade that cannot finish alone** converts what it can and lists the rest. The owner's check keeps failing those units, so the upgrade's pull request carries them to the end.
- **What an added part holds until a person fills it** is the owner's choice: a placeholder its check fails, or a marked one it warns on. DEC-001 leaves that to the change that adds the part (its Implications, as refined).

## A person's reading

The tool converts a unit alone only where the unit reads one way. Where it reads two ways, a person chooses, and the tool never guesses.

- **The tool alone:** a record whose Decision section holds one top-level numbered list, each item opening with a bold lead. Its points become headings, word for word.
- **A person's choice:**
  - **which list holds the points,** where the Decision section holds several, or a list nested in prose
  - **what a point's id is** in the bold-number and bold-label forms, as ADR-002's `**1. …**` and PRJ-002's `**D1 — …**`
  - **whether a record without a list has points at all**
- **How the choice is asked:**
  - **Interactively, on a terminal:** one unit at a time, with the candidates shown. The person picks one, or skips the unit.
  - **As a proposal:** with no terminal, or on request, apply writes the diff it would make and each open choice to the agent workspace (core rule 16). A person or an agent fills the choices, and apply takes the file.
  - **With nobody to ask and no answers,** a unit that needs a choice stays as it was and is listed. That is COR-048 point 5's rule.
- **An agent may prepare a proposal and apply it.** The diff is then reviewed like any change. A choice of form is no answer on an artefact, so core rule 20 does not reach it.
- **A transform checks its own claim:** one that moves text word for word checks that each unit's words are unchanged, apart from the structure it adds. It refuses a unit that fails.

## Discovery

A project learns what is pending from five places. Each answers a different reader at a different moment.

- **`pkit upgrade` and its dry run:**
  - **before writing:** the required upgrades it will apply, with their unit counts
  - **after:** each file changed, the units that need a choice, the optional upgrades now available, and the dependants friction will ask
- **`pkit status`:** a section listing each upgrade with pending units, its class, the count, and the project's recorded choice to keep, if any.
- **`pkit validate`, a backbone member:**
  - **error:** a required upgrade with pending units, naming the command that converts them
  - **info:** an optional upgrade with pending units, unless the project recorded its choice to keep them
  - **error:** a recorded choice naming an upgrade that does not exist, as COR-048 point 2 has for a stale entry
- **A check on each change:** it fails a unit the change adds, or converts back, in a superseded format.
- **CI:** the project's pipeline runs validation and the change checks. They bind once the project makes them required statuses (COR-050 point 12).
- **The release notes:** each content upgrade ships with a changeset that names it (PRJ-002), so the release announces it.

Some of these choices need a reason:

- **Why validation errs on a required upgrade:** the owner's check fails the unit anyway. The backbone's finding names the fix, beside a bare structure error.
- **Why info on an optional one, not a warning:** a mixed state is legitimate. Warnings for it would teach people to skip warnings.
- **Why the change check is a command of its own:** it compares a change with a base, which a validator never does (COR-055 point 2). It joins the check aggregator beside `friction check` (`.pkit/cli/README.md:988`).
- **The author's side, as Django's `makemigrations --check`:** `pkit migrations check-diff` gains a check. A change to a declared format source ships a content upgrade, or declares that none is owed and why.
  - **Format sources:** a kind's structure, a page kind, the record template. Each owner declares its own.

## A mixed state

A mixed state is legitimate where the upgrade is optional, and it may only shrink. Each unit's format is read from its shape, and the project's choice to keep old units is recorded once.

- **Legitimate:** an optional upgrade leaves the old format valid, as Rust's editions stay valid side by side.
- **Bounded:** new units follow the current format. The stamp writes it, and the check on each change fails a unit added in a superseded one. So the old set never grows.
- **Deliberate:** a project that keeps its old units records that choice once per upgrade, with a reason, in the backbone configuration. Validation's info then goes quiet, and status shows the choice.
- **Reported:** status counts the old units per upgrade, and lists them on request.
- **Two branches:** one converts a unit while another edits it in the old format, so they meet as a conflict. The change check fails a resolution that brings the old format back.
- **Inferred, not declared:** detect reads each unit's format from its shape.
  - **Every known case shows its format:** a list or headings, a part present or missing, an entry or a file, a section present or not.
  - **A marker on every unit is rejected.** It adds a field to every document, and repeats what the shape already says.
  - **The exception:** where an owner's old and new shapes look alike, the owner keeps a marker inside the methodology's container. A change there is no content change, so it flags nobody (COR-050 point 5, COR-053 point 10).
- **Not a ledger:** what is converted is read from the files. A ledger would drift from files edited by hand and conflict across branches, as COR-050 point 9 avoids for debt.
- **Note:** Rust declares an edition because one text can mean two things in two editions. A document's format rarely has that problem.

## Consent and review

A content upgrade writes a diff to the working tree, and a person commits it. The tool commits nothing, and rewrites nothing silently.

- **Consent follows COR-048 point 5's rule, applied to content:**
  - **interactively,** by asking once per upgrade, with the diff shown
  - **non-interactively,** only with an explicit confirmation flag
  - **inside an upgrade, for a required one,** running the upgrade is the consent, and its dry run shows the plan first
  - **with nobody to ask and no flag,** nothing is written
- **A clean start:** apply refuses when a file it would write has uncommitted changes. So the diff is the upgrade's alone, as `ng update` refuses a changed tree.
- **The unit of consent:** one upgrade, over every pending unit or the units named. A large corpus is split by naming units, and Rails' per-file prompting is one unit at a time.
- **How it lands:**
  - **One content upgrade per commit,** with a message that names it.
  - **A required one** rides in the upgrade's pull request, in a commit after the version change. That pull request cannot pass without it.
  - **An optional one** lands in a pull request of its own, never mixed with other work.
- **Why apart:** the reviewer checks one claim, that the text is unchanged. Mixed with other edits, a reworded sentence could pass as format (RS-WRITE-013).
- **Not proposed now:** the tool making the commit or the pull request, as `ng update --create-commits` does. The person's commit suffices until the need recurs (COR-007).

## Friction

A converted unit flags its dependants like any change. The upgrade lists them and proposes an answer for each, and a person decides every answer.

- **What is flagged:**
  - **A converted record:** a record anchor stands on the whole file (COR-050 point 5), so every dependant is asked once.
  - **A converted artefact:** its body or its own fields changed, so every artefact anchored to it is asked.
  - **A moved artefact,** such as an actor leaving the collection file: the move itself owes a revalidation in the same change (COR-050 point 3).
- **Who answers:** each dependant's owner, as for any change. The answer is a person's decision, shown word for word (COR-050 point 3, core rule 20).
- **What the upgrade may do:** list every dependant the change check will ask, each with a proposed `unchanged-because` naming the upgrade, and the command that records it.
- **What it never does:** write an answer. Writing is a separate command, never a side effect (COR-050 point 13).
- **An agent that runs the upgrade as its change** falls under core rule 20's exception, as for any change. It may write the answers the check asks first, then shows the check's list to the person who authorises the merge.
- **No marker spares the dependants:** on 8 October the maintainer declined a mark that a change keeps a document's meaning (PR #1384, question 2). Content upgrades add to the count that would reopen it.
- **Part anchors lower the cost later:** once a record is converted, a dependant anchored to one point is asked only when that point changes (#1387).

## Skipped versions, re-runs and partial runs

What is pending is what detect finds in the files, so the version a project came from does not matter.

- **A skipped version:** a project jumping from 1.140 to 1.170 gets every upgrade whose detect finds units. An optional upgrade the project passed over at 1.150 is still offered at 1.170.
- **Order:** by the version that introduced each upgrade, then by what each builds on. Each apply reads the format its predecessor writes. A unit in an older format is *waiting* for that predecessor, never converted out of turn.
- **Keep the transform:** an upgrade ships while any supported version can leave content in its old format. Retiring one is a major surface change, and validation then names the format and the last release that converts it.
- **A re-run:** detect finds no converted unit, so a re-run does nothing. That is COR-010's script contract, kept by detection.
- **A partial run:** each unit is written whole or not at all. An interrupted run leaves some units converted, and the next run continues.
- **The recorded version moves first:** sync records the backbone's new version before any later step runs (`src/project_kit/upgrade.py:208-213`). Keying on the files makes that harmless.
- **A pin:** a pinned project sees the upgrades of its pin's release, in every clone. A pin raise runs the upgrade, so new ones arrive with it (ADR-049).

## The methodology's own source repository

Nothing runs a content upgrade automatically in project-kit's own repository. The change that ships an upgrade applies it to project-kit's content itself.

- **No version moves there:** upgrade delegates to sync and runs no migrations (ADR-059 point 2, `src/project_kit/upgrade.py:115-127`).
- **Nothing is a synced copy there** (`.pkit/lifecycle/README.md:809`). So an upgrade's reach includes the core and capability records, and one command converts all 95 list-form records.
- **What ships must be converted first:** an adopter's synced copies arrive as the source holds them, and no upgrade may touch them. So the source applies each upgrade to what it ships before the release.
  - **A release gate:** `pkit release check` fails while detect finds a pending unit in a tree the release ships.
- **project-kit's own records and artefacts** follow the same rules as an adopter's. For #1387 the recommendation is to convert them now (the part-anchors note, "Recommendation").
- **The first user:** project-kit runs each upgrade on its own content before any adopter does.

## Placement

A new core record holds the mechanism. COR-010 and COR-001 are refined to make room for it.

- **A new core record, "A project's own content follows format changes":** what a content upgrade is, its reach and its two classes. Also consent, discovery and its severities, the mixed state, friction's obligations, keying on the files, and the source repository.
- **Why not a refinement of COR-010:** COR-010 governs what the core installs, and says adopter customisations are never core-managed (its Implications). A content upgrade changes exactly what COR-010 leaves out, with its own consent and its own friction.
- **COR-010, refined:**
  - **The upgrade flow** gains a step after component migrations, for required content upgrades.
  - **Every path that moves a component's version** runs that step: upgrade, sync's refresh and capability upgrade.
  - **The mandatory rule** names the case: a change that makes the owner's check fail a project's content ships a required content upgrade.
- **COR-001, refined:** its extension contract gains one exception. The core writes a project-owned path only through a consented writer a record names, as COR-048 point 5's configuration writer and the content upgrade.
- **COR-048, unchanged:** the new record owns its configuration key, for the recorded choices, under COR-048 point 2.
- **COR-050 and COR-055, unchanged:** friction applies as it stands, and the severities exist.
- **software-analysis DEC-001, once PR #1391 lands:** its line on structure changes cites the new record.
- **The lifecycle README:** a section on content upgrades, the new step, and line 758 corrected.
- **The CLI README:** the command group, its name settled in the build.

## Alternatives weighed

- **A one-off command per format change,** as the part-anchors note's B3. Rejected, for the maintainer's reason and Terraform's lesson. It tells a project nothing, and strands one that skips.
- **Migrations that rewrite project content.** Rejected. A script runs unattended, cannot ask, keys on the version window, and leaves no diff anyone consented to. project-management already refuses it for its overrides (DEC-033 D6).
- **Tolerance only,** old formats valid for ever. Kept as an owner's choice per change. As a mechanism it never converges, and tells nobody anything.
- **A format marker on every unit.** Rejected for documents, as "A mixed state" says.
- **A ledger of applied upgrades,** as Django's table. Rejected, since the files already say it.
- **The tool commits, or opens the pull request.** Not now (COR-007).
- **Convert a unit whenever a change edits it.** Not a rule, since a format change inside an unrelated edit hides both. An owner may offer it.

## Recommendation

Make content upgrades a mechanism of their own, in a new core record, keyed on what the files hold.

- **Required ones** run in every path that moves their owner's version. Running it is the consent, and the result is a diff.
- **Optional ones** run by command, with consent. A project may keep its old units by a recorded choice, and new units follow the current format.
- **Discovery** comes from the upgrade's output, status, validation and the check on each change.
- **Friction's answers** are proposed by the upgrade and decided by people.
- **The first use** is #1387's records, as an optional backbone upgrade, applied to project-kit's records first.

## Questions for the maintainer

Each question is one decision, with a recommendation. Ask them one at a time.

1. **Is a content upgrade a mechanism of its own, in a new core record?**
   - **Recommendation:** yes. COR-010 gains a step and a trigger, and COR-001 gains the exception for consented writers.
   - **Else:** refine COR-010 so migrations may rewrite project content, with a consent step added.
2. **Does a required content upgrade run inside the upgrade, with running it as the consent?**
   - **Recommendation:** yes, in every path that moves its owner's version, as a diff the upgrade's pull request carries. COR-048 point 5 already counts running the upgrade as consent for a configuration key.
   - **Else:** every content upgrade runs only by its own command, and validation fails a required one until it runs.
3. **How is a mixed state kept deliberate?**
   - **Recommendation:** each unit's format is read from its shape. A project records once per optional upgrade that it keeps its old units, and a check on each change keeps new units current.
   - **Else:** each unit declares its format, as a crate declares its edition, and status counts the declarations.
4. **How does a project's own record gain point ids (#1387, question 4)?**
   - **Recommendation:** by an optional backbone content upgrade that makes points headings. It converts alone where a record has one list, and asks otherwise. project-kit's records go first, in the change that ships it.
   - **Else:** a required upgrade, which converts every project record on upgrade.

## Slicing

On the recommended answers, the work comes in five groups, in this order.

- **A, the records:**
  - **A1, the new core record,** through the decision-author skill.
  - **A2, COR-010 and COR-001 refined,** through the decision-author skill.
  - **A3, the lifecycle README and the CLI README:** the mechanism's specification, and line 758 corrected.
- **B, the mechanism:**
  - **B1, the declaration and the runner:** the backbone's list, the package-metadata entry, detect and apply under the command limits, and the proposal file.
  - **B2, the hook:** the step in upgrade, in sync's refresh and in capability upgrade.
  - **B3, discovery:** the status section, the validation member, and the configuration key for recorded choices.
- **C, the change side:**
  - **C1, the check on each change,** in the check aggregator.
  - **C2, the author's check** in `migrations check-diff`, and the release gate.
- **D, the first upgrade, #1387's records:** detect and apply for a record's points, then project-kit's records converted by it. This replaces the part-anchors note's B3, and carries out its A3.
- **E, the capabilities:** software-analysis's first structure change ships its upgrade, and DEC-001 cites the record. living-docs' first page-kind change does the same.
  - **#1346 need not wait,** since no adopter has the old actors.
- **Changesets:** each issue declares its segment by PRJ-002. The segment is the maintainer's judgment.

## Found on the way

1. **The lifecycle README's lines 723 and 758** say the backbone-wide upgrade moves no capability version. So do the comments at `src/project_kit/upgrade.py:794`, `:829-830` and `:1044-1054`. It does move them, through sync.
2. **The backbone migrations README says it is "Empty today"** (`.pkit/migrations/backbone/README.md:5`), beside seven version directories.
3. **`pkit migrations check-diff` reads renames and removals only** (`src/project_kit/migrations.py:244-284`). A modified template or schema that changes a format triggers nothing.

## Review

*Pending: the critic, then the architect.*
