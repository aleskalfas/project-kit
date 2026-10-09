---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-09
---

# Content conversions — a project's own content follows the methodology's format changes

A design for #1394. It sets how a project's own records, analysis artefacts, pages and data files follow when the methodology changes their format.

- **Raised by:** the part-anchors design's question 4 (#1387, PR #1392). On 9 October the maintainer parked it. A one-off conversion command is the wrong shape, and one general mechanism, part of upgrading, should answer it.
- **Read from main at `78837af9`:** the records, the code and the migrations below. Two designs are read from their branches:
  - **the part-anchors note** at `99636eca`, decided by the maintainer on 9 October except question 4
  - **software-analysis DEC-001** as refined in PR #1391, at `79ce83ea`, which has not landed
- **Citations:** records by id and point. Code, READMEs and migration scripts by file and line at `78837af9`, since their text has no permanent ids.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers the four questions, one at a time. The issues in "Slicing" are filed on the maintainer's go.
- **Note:** the file is named for upgrades, but the note calls the mechanism a *conversion*. "Upgrade" already names `pkit upgrade`, and one word for two things misleads (RS-WRITE-011).

## The question

When the methodology changes the format of content a project owns, how does that content follow, and who decides that it does?

## In short

A conversion moves a project's own content from one format to the next. It is a step of upgrading with a contract of its own, and it changes nothing a person has not reviewed.

- **A step of upgrading:** `pkit upgrade` runs it on every run. The owner of a format ships its conversions beside its migrations.
- **Its own contract:** a migration carries the methodology's data unattended. A conversion rewrites what a project wrote, so it produces a diff for review.
- **Keyed on the content, not on the version:** each conversion can tell which units are still in the old format. So a skipped version, a re-run or an interrupted run needs no ledger.
- **Required or optional:** required when the owner's check fails the old format. Optional when the old format stays valid. A change that needs a person's writing gets a window before it is required.
- **The tool alone, or a person's choice:** the tool converts what reads one way by the owner's rule. A choice that fixes an id is a person's, shown before the merge.
- **Discovery:** the upgrade's output, `pkit status`, validation's severities and the owner's check on each change. `pkit sync` reports and never converts.
- **A mixed state is legitimate and bounded:** old units may stay by the project's recorded choice. The owner's change check flags a new unit in the old format.
- **Friction:** a converted unit flags its dependants. The conversion lists them with its evidence, and writes no answer and no justification.
- **Placement:** a new core record, with COR-010 and COR-001 refined.
- **#1387's question 4:** an optional backbone conversion turns a project's list-form records into headed points. project-kit's own records need not wait for it.

## The cases

Four format changes are decided or planned. One reaches adopters' own content today, and it is optional.

### The four known cases

| Case | Owner | Class | Who converts |
|---|---|---|---|
| A record's points become headings (#1387) | backbone | optional | the tool, by the decided rule. A person confirms the reading. |
| An analysis kind's structure changes (DEC-001 point 1 as refined, #1363 to #1368) | software-analysis | required for live artefacts. Never for revalidation records or withdrawn artefacts. | the tool adds the part's heading and hint. A person fills the part. |
| Actors move to one file each (#1346) | software-analysis | required | the tool. Each move owes a revalidation, a person's decision (COR-050 point 3). |
| A page kind's structure changes (`page-kinds.yaml`, RS-LDOC-004) | living-docs | required where the validator fails a page without the new section | the tool adds the heading. A person writes the section. |

- **The records:** 105 records hold 608 points, in five forms. 86 records convert, 40 of them synced, with 28 artefacts anchored to them (the part-anchors note, "Migration").
- **Who is reached today:** software-analysis is installed only in project-kit's clones (#1346, "No migration for adopters"). So the two analysis rows reach no adopter yet.
- **Note:** a page kind's structure checks headings only (`.pkit/capabilities/living-docs/schemas/page-kinds.yaml:11-16`). So nothing checks that a person wrote the section the tool headed.

### Others the search found

- **Within reach:**
  - **Project data in a component's format:** project-management's workflow overrides, a project's own `structures.yaml` (#1367), and process definitions. Each carries a `schema_version`. Today a mismatch is refused (`src/project_kit/data_validate.py:524-546`) or only warned about.
  - **Workflow overrides, warned about:** three migrations warn of an override at an old `schema_version` and edit nothing. The script's comment says editing "would silently clobber adopter intent" (`.pkit/capabilities/project-management/migrations/0.15.0/001-workflow-yaml-schema-v2.sh:20-22`, project-management DEC-033 D6).
- **Tolerance, the way a change avoids being required:**
  - **A grace period:** the old `Milestone: #N` line is accepted with a warning "during the grace period" (`.pkit/capabilities/project-management/scripts/validate-issue.py:722-724`).
  - **A shape kept compatible:** #797 keeps the overlay's `adr-records` back-compatible "to keep this out of migration territory".
- **Not tolerance, though it looks like it:** #1366 keeps an old template's placeholders on an append-only list. So a unit stamped before still fails until filled (`.pkit/capabilities/software-analysis/scripts/_lib/placeholder.py:20-22`). That is a check following its own template, and old units keep failing.
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

- **COR-001 keeps the core off project-owned paths:** "The core layer never reads from or writes to these paths", and they "are not touched by sync" (`.pkit/decisions/core/COR-001-content-mechanisms.md:33` and `:37`). The sentences sit under extension content, delivered by sync.
- **COR-010 keeps removal off adopter content:** "Adopter content is never touched" (COR-010, "Lifecycle operations apply uniformly", item 4).
- **COR-048 opens one door:** a configuration key may be written "by an upgrade migration that the owning record specifies, where running the upgrade is the consent" (COR-048 point 5).
- **COR-053 opens another, inside documents:** a functionality block in an artefact's front matter "carries no version — the backbone owns its shape and migrates it" (COR-053 point 10).
- **In practice, several scripts write project-owned files.** Each writes the methodology's data or wiring, never prose a person wrote:
  - `.pkit/migrations/backbone/1.150.0/001-keep-process-journal-logging.sh:11` adds a configuration key, citing COR-048 point 5.
  - `.pkit/migrations/backbone/1.54.0/001-seed-architect-overlay-categories.sh:23` adds categories to the project's overlay.
  - project-management's `0.5.0/001` and `0.55.0/004` move keys between its configuration and the backbone's.
  - claude-code's `0.5.0/001` adds an include line to the host `CLAUDE.md`, under the merge contract (COR-002).
- **No migration has rewritten** a record, an analysis artefact, a page or a scratchpad note. Such changes were made by hand (#860, #1350), or avoided by tolerance.

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
- **Point blocks (COR-053 point 10):** a point block carries its schema version. One the active provider does not match is inert and reported, its body unvalidated.

### Upgrade, sync and versions

The lifecycle README contradicts itself at lines 758 and 767. Line 767 holds.

- **Line 758 says** the backbone-wide upgrade "does not move capability versions". Line 723 says so too, and so do the code's comments (`src/project_kit/upgrade.py:794`, `:829-830` and `:1044-1054`).
- **Line 767 says** it "moves every kit-shipped capability at once".
- **The code moves them.** `pkit upgrade` runs sync (`src/project_kit/upgrade.py:213`), and sync refreshes each installed kit-shipped capability (`src/project_kit/sync.py:376-382`). The refresh runs the capability's migrations, copies its tree and restamps its version (`src/project_kit/capabilities.py:1124-1173`).
- **What line 758 gets right:** the backbone-wide dependency check reads the installed versions before sync. So only the refusing direction applies (`src/project_kit/upgrade.py:1038-1095`).
- **Every path that moves a version:**
  - **`pkit sync`** moves each kit-shipped capability's version, and records the backbone's (`src/project_kit/sync.py:143`). It runs no backbone migration.
  - **`pkit upgrade`** does both through sync, then runs the backbone's migrations.
  - **`pkit capabilities upgrade`** moves one capability (`src/project_kit/cli.py:4314`).
- **`pkit upgrade` returns early twice,** before sync and migrations: when the project is at the target (`src/project_kit/upgrade.py:190-201`), and in a pinned project at the latest release (`:553-555`).
- **Why it matters here:** a step hooked behind those returns, or to one path, is skipped once another path has moved the version.

### Pins and skipped versions (ADR-049)

- **A pin routes every command** to the pinned release's code (ADR-049 points 1, 2 and 4). So every clone of a project sees the conversions of the release its pin names.
- **`pkit upgrade` goes to the latest release** (ADR-049 point 7) and flips the pin last (point 1, `src/project_kit/upgrade.py:219-227`). A project can skip many versions in one hop.
- **There is no path down.** An older pkit refuses a project whose content or pin is newer. A project rolls back with `git checkout <ref> -- .pkit/` (`.pkit/lifecycle/README.md:732-739`).

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
  - **Teaches:** a file a person may have edited changes only with that person's consent. A new default can be offered first and required later.
- **Django, migrations:** `migrate` applies pending migrations, recorded in a table, and `showmigrations` lists them.
  - `makemigrations --check` fails a change whose models moved without a migration.
  - **Teaches:** an author-side check that a format change ships its transform, and a listing of what is pending. Its ledger suits a database, whose state cannot be read back from a file's shape.
- **Codemods, jscodeshift and `@next/codemod`:** a named transform runs on chosen paths, with a dry run, and leaves a diff. Nothing records that it ran.
  - Next.js later folded its codemods into `@next/codemod upgrade`, which offers the ones relevant to the versions crossed.
  - **Teaches:** standalone transforms drift into the upgrade path, since people do not know which to run.
- **Terraform, `0.12upgrade` and `0.13upgrade`:** each shipped in one release line and was removed in the next.
  - A project two versions behind had to install the release in between to run it.
  - **Teaches:** a transform tied to one transition strands a project that skips it. Tie it to the content's format, and keep it while old content can exist.

## Where a migration ends and a conversion begins

A migration changes what the methodology keeps for itself. A conversion changes what the project wrote. The test is where the change lands, not which file holds it.

- **A migration's ground:**
  - installed state, and the manifests (COR-010)
  - a configuration key a record owns (COR-048 point 5)
  - the methodology's container in a document's front matter, such as the friction block (COR-053 point 10)
  - wiring a merge contract delivers into a shared file, such as `CLAUDE.md`'s include line (COR-002)
- **A conversion's ground:** everything a project wrote in a format a component defines.
  - **Documents:** a record's or an artefact's body and its own fields, outside the container. Pages and rule-set files too.
  - **Project data:** a file the project fills in a component's format, such as a workflow override or `structures.yaml`.
- **Why the line falls there:** a person reads and wrote the second kind. A change to it needs review, and friction treats it as content (COR-050 point 5). The first kind only tools read, so a migration may change it unattended.
- **Traced against the cases:**
  - **A change to the friction block's shape:** a migration, as COR-053 point 10 says. It stays inside the container, so it flags nobody.
  - **Role-block keys rewritten at install:** container data, on COR-053 point 10's consent. Neither mechanism changes.
  - **The overlay's categories and the journal key:** the methodology's data. Migrations, as today.
  - **The include line in `CLAUDE.md`:** wiring under the merge contract. A migration, as today, though the file is the project's.
  - **Workflow overrides at an old `schema_version`:** project data. The warning-only migration becomes a conversion the project can accept.
  - **Records, analysis artefacts and pages:** conversions.
- **Note:** COR-010 already makes a `schema_version` bump a migration trigger. For a format a project fills, the trigger is met by a conversion.

## What a conversion is

A conversion moves units of a project's own content from one format to the next. The component that owns the format ships it, and a person reviews what it writes.

- **A unit:** one record, artefact, page or project data file. A collection entry is converted with its collection file.
- **Who ships it:** the owner of the format.
  - **The backbone** owns the record format, so headed points are the backbone's.
  - **A capability** owns its kinds. An analysis kind's structure is software-analysis's, and a page kind's is living-docs'.
  - **A project** ships none to itself, since it changes its own formats as it likes.
- **What it declares:**
  - **an id,** permanent and namespaced, such as `software-analysis:actor-files`
  - **the version** of its component that introduced the new format
  - **its class,** required or optional, and for a required one the release it becomes required in
  - **its reach,** the kinds of unit it may convert
  - **the conversions it builds on,** if any
  - **a detect command and an apply command**
- **Where it is declared:** a capability names its commands in its package metadata, as it names a validator (COR-055 point 3). The backbone keeps its own in its code.
- **Detect:** a read-only query under the backbone's command limits (ADR-057 point 3). For each unit in reach it answers *convertible*, *needs a choice* with the candidates, *waiting* for an earlier conversion, or *interrupted*.
  - **It reads units through the backbone's readers,** never by walking places itself (ADR-057 point 2). So a record at a path the overlay resolves, such as an ADR, is found as validation finds it.
- **Apply:** converts the units named, with the choices given. It writes the working tree and nothing else.
  - **A unit that spans several files is written whole.** Apply stages every file, then swaps them in. Detect reports a half-written unit as *interrupted*, and apply completes it.

### What it may touch

A conversion touches only the format of project-owned units in its reach. Its owner sets the reach.

- **The reach follows the format, not the tree.** The backbone's record conversion reaches every project-owned record, an incubated capability's included. In the source repository it reaches capability records too.
- **Never a synced copy** (`is_synced_copy`). A synced copy arrives converted with the sync that brings it.
- **Never history:**
  - a superseded record, whose body stays "as it stood" (`.pkit/decisions/README.md:161`)
  - a revalidation record or a withdrawn artefact (DEC-001 point 1 as refined)
  - a scratchpad note
  - any other text a person decided
- **Never an answer or an anchor:** a unit's `revalidated` block, its deferrals and its anchors stay byte for byte. Re-pointing an anchor is a revalidation, so it is a person's (COR-050 point 6).
- **Never a claim of judgment:** it writes no `None.` into a part it adds, since `None.` says a person considered the part (DEC-001 point 1 as refined).
- **Never a referrer:** a path anchor or a link to a file the conversion moves goes dead, an error the change owns (COR-050 points 7 and 12). The conversion lists the referrers it can find, and a person re-points them in the same change.

## Required versus optional

A conversion is required when the owner's check fails a unit left in the old format. Otherwise it is optional.

- **Required:** the old format no longer passes, so the project cannot stay valid without converting.
  - **DEC-001's live artefacts** are "always migrated to the current structure" (DEC-001 point 1 as refined, "When a structure changes").
  - **A COR-010 trigger:** the change breaks against what a project has. So the change that makes the check fail ships the required conversion in the same change-set.
- **Optional:** the old format stays valid, and the new one gains something, such as part anchors.
  - **A project's list-form records** keep working unconverted. Their points cannot be anchored until converted (the part-anchors note, "Migration").
- **How the class is declared:** in the conversion's declaration. A test holds it honest: the owner's check fails a unit in the old format exactly when the class is required.
- **A window for writing only a person can do:** a change whose units need a person's writing ships optional first, warned about, and required at a later release it names.
  - **Why:** DEC-001 refuses "a hint left in" whatever a rule's status (DEC-001 point 1 as refined, "Hints"). So a part the tool adds fails every live artefact at once, and no release can merge until each part is written.
  - **The precedent:** project-management's grace period for the old milestone line, and Rails' new defaults, offered before they are required.
  - **DEC-001 leaves it open:** the change that adds a part "settles how a part it adds is answered" (DEC-001 Implications, as refined).
- **A required conversion never builds on an optional one.** A project's choice to keep the optional one would leave the required one waiting for ever. The owner makes the earlier one required first.
- **A required conversion that cannot finish alone** converts what it can and lists the rest. The owner's check keeps failing those units until a person settles them.

## A person's reading

The tool converts a unit alone where the owner's rule reads it one way. A choice that the rule leaves open is a person's, and the tool never guesses.

- **The rule settles most cases.** For records, the decided design says which lists are points (the part-anchors note, "Which lists are points"). They are a numbered list at the Decision's top level, or one numbering across its group headings.
  - **So a record without such a list has no points.** It is current as it stands, and detect never asks about it.
- **What remains a choice:** a record that mixes labels with a list, as ADR-039 does, and any unit the rule cannot place.
- **A reading confirmed by a person:** the decided design asks the person who converts a record to confirm the reading, since it comes from how the record is cited.
- **How a choice is asked:**
  - **Interactively, on a terminal:** one unit at a time, with the candidates shown. The person picks one, or leaves the unit as it is.
  - **As a proposal:** with no terminal, or on request, apply writes the diff it would make and each open choice to the agent workspace (core rule 16). A person or an agent fills the choices, and apply takes the file.
  - **With nobody to ask and no answers,** a unit that needs a choice stays as it was and is listed. That is COR-048 point 5's rule.
- **"Leave it as it is" is recorded,** in the project's choices for that conversion, naming the unit. Detect then skips it, and status shows it as kept.
- **A choice that fixes a permanent id is a person's.** Citations and part anchors depend on it for good.
  - **An agent may propose it.** The conversion lists every id chosen, word for word, beside the change check's list of answers. The person who authorises the merge sees both (core rule 20's discipline).
- **A transform checks its own claim:** one that moves text word for word checks that each unit's words are unchanged, apart from the structure it adds. It refuses a unit that fails.

## Discovery

A project learns what is pending from six places. Each answers a different reader at a different moment.

- **`pkit upgrade` and its dry run,** on every run, whatever the versions:
  - **before writing:** the required conversions it will apply, with their unit counts
  - **after:** each file changed, the units that need a choice, the optional conversions available, and the dependants friction will ask
- **`pkit sync`:** a closing line naming each required conversion with pending units, and the command that applies it. It converts nothing.
- **`pkit status`:** a section listing each conversion with pending units, its class, the count, and what the project chose to keep.
- **`pkit validate`, a backbone member:**
  - **error:** a required conversion with pending units, naming the command that converts them
  - **warning:** an optional conversion in its window, before the release that requires it
  - **info:** any other optional conversion with pending units the project has not chosen to keep
  - **warning:** a recorded choice naming a conversion that no longer exists, as COR-048 point 2 reports a stale entry
- **The owner's check on each change:** it flags a unit the change adds, or converts back, in a superseded format.
  - **For records it exists already in the decided design:** `pkit decisions check-diff` warns of a new record whose Decision is a numbered list (the part-anchors note, "The numbering command").
  - **It is the owner's,** since only the owner knows its format. The mechanism lends it detect.
- **The release notes:** each conversion ships with a changeset that names it (PRJ-002), so the release announces it.
- **On install:** installing or registering a capability whose units are in an old format, as after a reinstall, reports them as status does.

Some of these choices need a reason:

- **Why sync never converts:** COR-001 says project-owned paths "are not touched by sync". Sync is the refresh people run often, so it reports and leaves the writing to the upgrade.
- **Why every upgrade run:** a version moved by sync, or by an interrupted upgrade, would otherwise leave the step unreached for good.
- **Why validation errs on a required conversion:** the owner's check fails the unit anyway. The backbone's finding names the fix, beside a bare structure error.
- **Why info on an optional one, not a warning:** a mixed state is legitimate. Warnings for it would teach people to skip warnings.
- **Where it binds:** the owner's change check binds only where the project wires it into its pipeline (COR-050 point 12, COR-054 point 3). Elsewhere, status shows the old count growing.
- **Not proposed now:** an author-side check that a change to a format ships a conversion, as Django's `makemigrations --check`. A format also lives in code, such as a heading's reading, so the check would guess. It waits for a missed conversion (COR-007).

## A mixed state

A mixed state is legitimate where the conversion is optional. Each unit's format is read from its shape, and what the project keeps is recorded once.

- **Legitimate:** an optional conversion leaves the old format valid, as Rust's editions stay valid side by side.
- **Bounded:** new units follow the current format. The stamp writes it, and the owner's change check flags a unit added in a superseded one.
- **Deliberate:** a project that keeps its old units records the choice in the backbone configuration, with a reason. It covers a whole conversion, or the units it names.
  - **Validation's info then goes quiet,** and status shows the choice.
- **Reported:** status counts the old units per conversion, and lists them on request.
- **Two branches:** one converts a unit while another edits it in the old format, so they meet as a conflict. The owner's change check flags a resolution that brings the old format back.
- **Inferred, not declared:** detect reads each unit's format from its shape.
  - **Every known case shows its format:** a list or headings, a part present or missing, an entry or a file, a section present or not.
  - **No marker on a unit.** It would add a field to every document, and repeat what the shape already says. The container has no place for one, since COR-053 point 10 admits only functionality and role blocks there.
  - **An owner whose old and new shapes look alike** changes the new shape until they differ.
- **Not a ledger of applied conversions:** what is converted is read from the files. A ledger would drift from files edited by hand and conflict across branches, as COR-050 point 9 avoids for debt.
- **Note:** Rust declares an edition because one text can mean two things in two editions. A document's format rarely has that problem.

## Consent and review

A conversion writes a diff to the working tree, and the review of that diff is the consent. The tool commits nothing, and rewrites nothing silently.

- **What writes the diff:**
  - **a required conversion:** `pkit upgrade`, whose dry run shows the plan first
  - **an optional one:** its own command, run on purpose, asking once on a terminal and needing an explicit flag without one
- **What consents:** the person's commit, then the pull request's review. Running the command only produces the diff to review.
- **A clean start:** a run refuses when a file it would write has uncommitted changes from before the run. So the diff is the conversions' alone, as `ng update` refuses a changed tree.
- **A chain on one unit:** two conversions crossed in one run that touch the same unit compose in the working tree. They land as one commit that names both.
- **How it lands:**
  - **Each conversion in a commit of its own,** apart from every other edit, except a chain as above.
  - **A required one** rides in the upgrade's pull request, in a commit after the version change.
  - **An optional one** lands in a pull request of its own.
  - **An optional one an edit forces,** as a point inserted into a list-form record, lands first in the same pull request, in a commit of its own (the part-anchors note, "Migration").
- **Why apart:** the reviewer checks one claim, that the text is unchanged. Mixed with other edits, a reworded sentence could pass as format (RS-WRITE-013).
- **Rolling back:** a conversion is undone by reverting its commit. `git checkout <ref> -- .pkit/` restores no unit outside `.pkit/`, such as an analysis artefact.
- **Not proposed now:** the tool making the commit or the pull request, as `ng update --create-commits` does. The person's commit suffices until a chain shows otherwise (COR-007).

## Friction

A converted unit flags its dependants like any change. The conversion lists them with its evidence, and a person writes every answer.

- **What is flagged:**
  - **A converted record:** a record anchor stands on the whole file (COR-050 point 5), so every dependant is asked once.
  - **A converted artefact:** its body or its own fields changed, so every artefact anchored to it is asked.
  - **A moved artefact,** such as an actor leaving the collection file: the move itself owes a revalidation in the same change (COR-050 point 3).
  - **A synced record that arrives converted:** each adopter artefact anchored to it is flagged by the sync that brings it, outside any conversion. The 40 synced records ship in one release, so each dependant is flagged once (the part-anchors note, "Migration").
- **Who answers:** each dependant's owner, as for any change. The answer is a person's decision, shown word for word (COR-050 point 3, core rule 20).
- **What the conversion gives:** each dependant the change check will ask, the conversion's own evidence, and the command that records an answer.
  - **The evidence:** its check that each unit's words are unchanged, and the part of the diff the dependant stands on.
- **What it never gives:** an `unchanged-because` sentence. That sentence is "the one piece of judgment the tool cannot supply" (COR-050 point 3).
- **What it never does:** write an answer. Writing is a separate command, never a side effect (COR-050 point 13).
- **An agent that runs the conversion as its change** falls under core rule 20's exception, as for any change. It may write the answers the check asks, then shows the check's list to the person who authorises the merge.
- **This is #1384's question 2 again, in another form.** A conversion is the clearest case of an edit that keeps meaning. The maintainer deferred a marker for that on 8 October, to be revisited by a count between two releases (PR #1384). Conversions add to that count.
- **Part anchors lower the cost later:** once a record is converted, a dependant anchored to one point is asked only when that point changes (#1387).

## Skipped versions, re-runs and partial runs

What is pending is what detect finds in the files, so the version a project came from does not matter.

- **A skipped version:** a project jumping from 1.140 to 1.170 gets every conversion whose detect finds units. An optional conversion the project passed over at 1.150 is still offered at 1.170.
- **Order:** by the version that introduced each conversion, then by what each builds on. Each apply reads the format its predecessor writes. A unit in an older format is *waiting* for that predecessor, never converted out of turn.
- **Every upgrade run reaches the step,** before its early returns. So a version sync moved, or an interrupted run, never strands a conversion.
- **Keep the transform:** a conversion ships until a major release retires it, said in the changelog. Validation then names the format and the last release that converts it.
  - **Its cost:** detect runs in status and validation, within the backbone's command bound. A cheap detect reads what the owner's validator already reads.
- **A re-run:** detect finds no converted unit, so a re-run does nothing. That is COR-010's script contract, kept by detection.
- **A partial run:** each unit is written whole, or completed when *interrupted*. The next run continues where the last stopped.
- **A pin:** a pinned project sees the conversions of its pin's release, in every clone. A pin raise runs the upgrade, so new ones arrive with it (ADR-049).

## The methodology's own source repository

Nothing runs a conversion automatically in project-kit's own repository. The change that ships a conversion applies it to project-kit's content itself.

- **No version moves there:** upgrade delegates to sync and runs no migrations (ADR-059 point 2, `src/project_kit/upgrade.py:115-127`).
- **Nothing is a synced copy there** (`.pkit/lifecycle/README.md:809`). So a conversion's reach includes the core and capability records.
- **What ships must be converted first:** an adopter's synced copies arrive as the source holds them, and no conversion may touch them. So the source applies each conversion to what it ships before the release.
  - **A release gate:** `pkit release check` fails while detect finds a pending unit in a tree the release ships.
- **project-kit's own records and artefacts** follow the same rules as an adopter's.
- **#1387's D2 need not wait for this design.** The part-anchors note converts project-kit's 86 records by this mechanism if it has landed, and otherwise by a project-kit-only conversion (its "Slicing", D2).
  - **Converting the 40 synced records** is authoring where they are authored, not content following a format change.

## Placement

A new core record holds the conversion's contract. COR-010 makes it a step of upgrading, and COR-001 names who may write a project's paths.

- **A new core record, "A project's own content follows format changes":** the line between migration and conversion, the reach, the two classes and the window, and consent. Also discovery and its severities, the mixed state, friction's obligations, keying on the files, and the source repository.
- **Why not a fourth scope of COR-010:** COR-010's scopes order scripts that share one contract, unattended and keyed on the version window. A conversion differs in its keying, its consent, its friction and its discovery, so a scope would share only a name.
- **COR-010, refined:**
  - **The upgrade flow** gains a step that every run reaches: the conversions.
  - **The mandatory rule** names the case: a change that makes the owner's check fail a project's content ships a required conversion.
  - **Its migrations** stay on the migration's ground, as the new record draws it.
- **COR-001, refined:** its extension contract keeps "not touched by sync". It drops "never reads", which validation already contradicts. The core writes a project-owned path only through a writer a record names:
  - an upgrade migration, on its ground (COR-010)
  - the configuration writer (COR-048 point 5)
  - a conversion (the new record)
- **COR-048, unchanged:** the new record owns its configuration key, for the recorded choices, under COR-048 point 2.
- **COR-050 and COR-055, unchanged:** friction applies as it stands, and the severities exist.
- **software-analysis DEC-001, once PR #1391 lands:** its line on structure changes cites the new record and its window.
- **The lifecycle README:** the conversion step, lines 723 and 758 corrected, and the rollback line naming content outside `.pkit/`.
- **The CLI README:** the command group, its name settled in the build.
- **Note:** the new record must state its rules in core terms. RS-WRITE-013 and PRJ-002 are project-kit's, cited here as the source of each rule only.

## Alternatives weighed

- **A one-off command per format change,** the part-anchors note's first answer to its question 4. Rejected, for the maintainer's reason and Terraform's lesson. It tells a project nothing, and strands one that skips.
- **Migrations that rewrite project content.** Rejected. A script runs unattended, cannot ask, keys on the version window, and leaves no diff anyone reviewed. project-management already refuses it for its overrides (DEC-033 D6).
- **A fourth scope in COR-010,** named content. Weighed as question 1's alternative.
- **Required at once, with no window.** Kept for changes the tool finishes alone. For writing only a person can do, it holds every release hostage.
- **Tolerance only,** old formats valid for ever. Kept as an owner's choice per change. As a mechanism it never converges, and tells nobody anything.
- **Sync converts, or refuses to move a version past a pending conversion.** Rejected. Sync never touches project-owned paths (COR-001), and refusing would block the routine refresh.
- **A format marker on every unit.** Rejected, as "A mixed state" says.
- **A ledger of applied conversions,** as Django's table. Rejected, since the files already say it.
- **The tool commits, or opens the pull request.** Not now (COR-007).
- **Convert a unit whenever a change edits it.** Not a rule. An owner may require it where an edit needs the new format, as the record design does for an inserted point.

## Recommendation

Make conversions a step of upgrading with a contract of their own, in a new core record, keyed on what the files hold.

- **Required ones** run on every `pkit upgrade`. The diff's review is the consent. A change that needs a person's writing gets a window first.
- **Optional ones** run by their own command. A project may keep old units by a recorded choice, and the owner's change check keeps new units current.
- **Sync reports,** and never converts.
- **Discovery** comes from the upgrade's output, status, validation and the owner's change check.
- **Friction's answers and their sentences** stay with people. The conversion gives the evidence.
- **The first use** is #1387's B4, an optional backbone conversion of a project's records.

## Questions for the maintainer

Each question is one decision, with a recommendation. Ask them one at a time.

1. **Is a conversion a step of upgrading with its own contract, in a new core record?**
   - **Recommendation:** yes. COR-010 gains the step and the trigger, and COR-001 names the writers of a project's paths. The contracts differ in keying, consent and friction.
   - **Else:** a fourth migration scope in COR-010, named content, with its own rules inside that record.
2. **How does a required conversion run?**
   - **Recommendation:** on every `pkit upgrade`, as a diff whose review is the consent. Sync only reports. A change that needs a person's writing ships optional first, with a window.
   - **Else:** only by its own command, with validation failing until the project runs it.
3. **How is a mixed state kept deliberate?**
   - **Recommendation:** each unit's format is read from its shape. A project records what it keeps, per conversion or per unit, and the owner's change check flags a new unit in an old format.
   - **Else:** each unit declares its format, as a crate declares its edition, and status counts the declarations.
4. **How does a project's own record gain point ids (#1387, question 4)?**
   - **Recommendation:** by an optional backbone conversion, #1387's B4. It converts by the decided rule, and a person confirms each record's reading. project-kit's 86 records follow #1387's D2 and need not wait.
   - **Else:** a required conversion, which turns every project record into headed points on upgrade.

## Slicing

On the recommended answers, the work comes in four groups. The optional path comes first, since only #1387 reaches adopters now.

- **A, the records:**
  - **A1, the new core record,** through the decision-author skill.
  - **A2, COR-010 and COR-001 refined,** through the decision-author skill.
  - **A3, the lifecycle README and the CLI README:** the step, lines 723 and 758 corrected, and the rollback line.
- **B, the optional path, with #1387's B4 as its first conversion:**
  - **B1, the declaration and the runner:** the backbone's list, the package-metadata entry, detect and apply under the command limits, staging and the proposal file.
  - **B2, the step:** every `pkit upgrade` run reports, and the conversion's own command applies. Sync's closing line.
  - **B3, discovery:** the status section, the validation member's info and warnings, and the configuration key for what a project keeps.
  - **B4, the record conversion** (#1387's B4): detect and apply for headed points, refusing synced copies and superseded records. `pkit decisions check-diff` reads its detect.
- **C, the required path,** when the first required change reaches an adopter:
  - **C1, the step applies required conversions,** and validation's error.
  - **C2, the window:** the release a conversion becomes required in, and the warning before it.
- **D, the release gate in the source:** `pkit release check` fails while a shipped tree holds a pending unit.
- **The capabilities:** software-analysis's first structure change that reaches an adopter ships its conversion, and DEC-001 cites the record. living-docs' first page-kind change does the same. #1346 need not wait, since no adopter has actors.
- **Changesets:** each issue declares its segment by PRJ-002. The segment is the maintainer's judgment.

## Found on the way

1. **The lifecycle README's lines 723 and 758** say the backbone-wide upgrade moves no capability version. So do the comments at `src/project_kit/upgrade.py:794`, `:829-830` and `:1044-1054`. It does move them, through sync.
2. **The backbone migrations README says it is "Empty today"** (`.pkit/migrations/backbone/README.md:5`), beside seven version directories.
3. **`pkit migrations check-diff` reads renames and removals only** (`src/project_kit/migrations.py:244-284`). A modified template or schema that changes a format triggers nothing.
4. **A page kind's structure checks headings only.** An empty section under a fixed heading passes (`.pkit/capabilities/living-docs/schemas/page-kinds.yaml:11-16`).
5. **Each check on a change is a line of its own in a project's pipeline:** `friction check`, `migrations check-diff`, and the coming `decisions check-diff`. One command an adopter wires once would bind them all. That is a design of its own.

## Review

### The critic

The critic found five red flags, fourteen gaps, six weak points, six counter-alternatives and nine factual errors. It agreed with keying on the files, with writing no answer and no `None.`, and with refusing synced copies.

**Red flags:**

1. **A chain of conversions met the clean start and one commit per conversion.** **Answer:** accepted. The clean start is taken once, before the run. Two conversions on one unit compose and land as one commit naming both ("Consent and review").
2. **Inferring from shape could not record "leave this unit as it is".** **Answer:** accepted, in two parts.
   - **The decided record design** says which lists are points, so a record without one is current, and detect never asks.
   - **Where a person still answers "leave it",** the project's recorded choices name the unit ("A person's reading").
3. **The hooks missed sync's move of the backbone's version and upgrade's early returns.** **Answer:** accepted. Every upgrade run reaches the step, before its early returns. Sync converts nothing and names what is pending, as COR-001 requires.
4. **No line between a migration and a conversion.** **Answer:** accepted. A new section draws it by where a change lands. It traces the line against six cases, from the friction block to records and pages.
5. **The slicing cited the wrong part-anchors items.** **Answer:** accepted, from the note at `99636eca`. B4 is the conversion of an adopter's records, and D2 converts project-kit's 86.

**Gaps:**

6. **The COR-001 refinement broke shipped migrations.** **Answer:** accepted. COR-001 keeps "not touched by sync" and names three writers, an upgrade migration on its own ground among them.
7. **Adopters are flagged by converted synced copies.** **Answer:** accepted. "Friction" states it, with the part-anchors note's single release.
8. **Superseded records were missing.** **Answer:** accepted. They are history, never converted.
9. **A conversion breaks references in other files.** **Answer:** accepted. It lists the referrers it finds, and a person re-points them in the same change.
10. **A conversion that writes several files is not atomic.** **Answer:** accepted. Apply stages and swaps, and detect reports a half-written unit as *interrupted*.
11. **A required conversion that needs writing holds the release hostage.** **Answer:** accepted. Such a change ships optional first, with a window, and the page-kind gap goes to "Found on the way".
12. **A required conversion could build on an optional one.** **Answer:** accepted. It never does.
13. **A marker in the container conflicts with COR-053 point 10.** **Answer:** accepted. The exception is gone. An owner makes its shapes differ instead.
14. **An edit forces the optional record conversion.** **Answer:** accepted. A conversion an edit forces lands first in the same pull request, in a commit of its own.
15. **The bound on a mixed state depends on each pipeline.** **Answer:** accepted. "Discovery" states the condition.
16. **An agent would choose permanent ids.** **Answer:** accepted. A chosen id is listed word for word for the person who authorises the merge.
17. **A proposed `unchanged-because` sat uneasily with COR-050 point 3.** **Answer:** accepted. The conversion gives evidence and no sentence. The note says plainly this is #1384's question 2 in another form.
18. **The rollback advice breaks outside `.pkit/`.** **Answer:** accepted. A conversion is undone by reverting its commit, and the lifecycle README's line follows.
19. **Smaller gaps:**
    - **(a) install meets old units:** accepted. Install and register report them.
    - **(b) formats in code, and where "none owed" is recorded:** accepted. The author-side check is not proposed now.
    - **(c) a stale choice:** accepted. It is a warning.
    - **(d) no support policy:** accepted. A conversion ships until a major release retires it, and detect reads what the validator reads.
    - **(e) reading through the engines:** accepted. Detect reads through the backbone's readers, overlay paths included.
    - **(f) project neutrality:** accepted. The record restates both rules in core terms.
    - **(g) the reach of the record conversion:** accepted. The owner of a format sets the reach.
    - **(h) the order of #1387 and #1394:** accepted. #1387's D2 need not wait.

**Weak reasoning:**

20. **The analogy behind question 2 was thin.** **Answer:** accepted. The review of the diff is the consent, and running the command only produces it.
21. **The case against refining COR-010 was weak, and the headline read as disagreeing with the maintainer.** **Answer:** accepted. The headline says a step of upgrading. Question 1's alternative is now a fourth scope, and the reason against it is the contract.
22. **#1366 was read as tolerance.** **Answer:** accepted. It keeps old units failing. The tolerance examples are now the milestone line's grace period and #797.
23. **The urgency was overstated.** **Answer:** accepted. Only #1387 reaches adopters, so the optional path is built first and the required path waits for a case.
24. **"Upgrade" named two things.** **Answer:** accepted. The mechanism is a *conversion*.
25. **A count did not match.** **Answer:** fixed.

**Counter-alternatives:**

26. **A fourth migration scope.** **Answer:** question 1's alternative.
27. **A deprecation window.** **Answer:** taken, for changes that need a person's writing.
28. **One path moves versions, and sync refuses.** **Answer:** taken in part. Sync reports and never converts, but does not refuse, since that would block the routine refresh.
29. **The tool commits each conversion.** **Answer:** not taken. Composing a chain in one commit solves red flag 1 without it.
30. **Build for #1387 first.** **Answer:** taken. "Slicing" builds the optional path first.
31. **One umbrella change check.** **Answer:** noted in "Found on the way", as a design of its own.

**Factual errors:** all nine fixed.

- **F1, the counts:** 105 records with 608 points, five forms, 86 to convert, 40 synced and 28 anchored artefacts.
- **F2, the labels:** B4 and D2, and the one-off command as the part-anchors note's first answer.
- **F3:** the quoted words are the migration script's comment, not DEC-033 D6.
- **F4:** an out-of-step point block is "inert and reported, its body unvalidated".
- **F5:** COR-048 point 2 gives no severity, and the note proposes a warning.
- **F6:** #1366, as in 22.
- **F7:** the pin is flipped last by ADR-049 point 1, and point 7 drops `--to`.
- **F8:** PR #1384's question 2 was deferred, with a count to revisit it.
- **F9:** sync also records the backbone's version.
