---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-27
---

# Release candidates

## The question

How does the release step cut `2.0.0rc1`, a later candidate and the final `2.0.0`? Anyone must be able to move a project to a candidate on purpose, and nobody may receive one by default (#2211). The maintainer wants to test 2.0.0 before publishing it, and expects changes after rc1. This note maps the eight questions #2211's design asks: what exists today, the options, and what the maintainer decided.

- **The first choice.** The maintainer decided on 27 October that "a release candidate does not consume the changesets. Each candidate is computed from the pending changesets and leaves them pending. The final release consumes them once" (#2211, second comment). The note builds on that decision.
- **The other choices.** The maintainer decided each of the eight questions on 27 October, in comments on PR #2224. Three of them revised the note's recommendation: the way in and on (choice 5), publishing with one flag name, `--pre` (choice 6), and the final release's source (choice 7). Each section below states the decision, and "Decisions taken" lists them.
- **Where they are carried.** Each decision is carried by a refinement of an accepted record, PRJ-002, PRJ-004, ADR-049, ADR-063, ADR-064 or ADR-065, or by the new ADR-072. The maintainer accepts them on PR #2224.
- **Two of them change what PRJ-002 D3 decides.** A candidate's versions are written off main, and the final release that ends a line is cut from a commit behind main's head. The maintainer authorised both (choices 1 and 7). The other refinements add a candidate's case to what their records decide, and wait for the same acceptance.
- **Its ground is accepted records and the code on `origin/main` at `dc195bf6b`.** Every claim about the code was checked on that tree, most with a read-only probe under the locked `packaging` 26.2.
- **Words.** A *release* is a version with no pre-release suffix, and a *candidate* is a version `X.Y.ZrcN`. "The latest release" never names a candidate, as PRJ-004 and ADR-063 already read it. A candidate is still a release in COR-059 point 1's sense: a backbone version with its components' versions.

## What a candidate meets today

The code reads a pre-release version in some places and refuses it in others. A candidate cut today fails before anyone could install it, and an upgrade to one fails halfway.

| Where | What it does with `2.0.0rc1` | Effect |
|---|---|---|
| `pyproject.toml`, `[tool.hatch.version]` | its pattern takes `X.Y.Z` alone | no wheel builds, and `uv sync` fails, on a tree that records a candidate |
| `versioning.next_version` | drops the suffix, then bumps: a major gives `3.0.0`, a minor `2.1.0` | a release from a tree at a candidate skips its final |
| `release.floor_problems` | refuses `requires_backbone: release` when the shipped backbone is a pre-release | 72 pending changesets declare `release`, so a release whose backbone is a candidate refuses |
| `release.migration_dir_mismatches` | `minor_of("2.0.0rc1")` raises, outside its guard | `pkit release plan --json` fails on a plan whose backbone is a candidate |
| `migrations.pending_migration_scripts` | `parse_version_tuple("2.0.0rc1")` raises | `pkit upgrade` to a candidate fails at step 4, after it recorded the target and copied the content |
| `upgrade.as_recorded_version`, `_same_version` | read `2.0.0rc1` as `2.0.0`, and `0.55.0rc1` as `0.55.0` | a later candidate, or the final, runs no script of the candidate's folder |
| `migrations.recorded_version`, `migration_target` | refuse a tree that records `2.0.0rc1` | `check-diff` and `pkit new migration` stop on such a tree |
| `release._CHANGELOG_VERSION_HEADING_RE` | matches no `## 2.0.0rc1 — <date>` | the lint refuses the section, and `publish-notes` finds none |
| `release._gh_release_create_notes` | creates the Release without `--prerelease` | GitHub would show the candidate as its latest release |
| `upgrade._normalize_pin_version` | refuses `2.0.0rc1` | `pkit pin` cannot name a candidate, in any release so far |

What already reads a candidate as wanted:

- **Tagging.** `pkit version tag` and `untag` accept a PEP 440 pre-release, so `v2.0.0rc1` can be cut. `tag_version` does not check that the commit is on main.
- **"Latest".** `scripts/latest_tag.py` and `upgrade._max_released_tag` skip pre-release tags. So `latest`, the tool step and a pinned raise never pick a candidate (PRJ-004, ADR-063 point 1).
- **The router.** It routes any pin to the tag `v<pin>` (`router._pinned_base`), so a pin of `2.0.0rc1` runs that tag's wheel once one builds. ADR-049's note that such pins "need a router change" no longer holds.
- **Ordering.** Sync's guard, `_moves_up` and the pin's order compare through `packaging.version.Version`, which puts `2.0.0rc1` below `2.0.0`.
- **The broaden.** `versioning.broaden_requires_backbone` widens `<1.150.0` to `<2.1.0` for `2.0.0rc1`.
- **Each hop runs its target's code.** A raise runs the target's upgrade (ADR-049), and a migration reaches the running pkit (ADR-065 point 14). So only code from rc1 on must read a candidate.

**The pending release, for scale:** six backbone `major` changesets move the backbone to 2.0.0, and eight components move with it. Of 768 pending changesets, 541 move a version. Its changelog section renders at 550,767 characters (question 6).

## 1. Versions

### Today

- **The form.** `versioning._PEP440_RE` reads `X.Y.Z(a|b|rc)N`, PEP 440's normal form, with no separator.
- **The `version` commands run outside the changeset flow.** `pkit version bump <segment> --pre rc`, `bump_pre` and `promote` write `.pkit/VERSION` alone. They consume no changeset, move no component and write no changelog. A candidate cut with them ships changed components under unchanged versions, and a transition then runs none of those components' migrations.
- **The release step** computes each tier from the tree it runs in. PRJ-002 D3 has it write version numbers on `main` alone, through a release PR.
- **The tag.** `tag_version` cuts `v` and `.pkit/VERSION`, a pre-release included. PRJ-004 names only `v<major>.<minor>.<patch>` among release tags.

### Options

- **The candidate's form:** PEP 440's `2.0.0rc1`, or semver's `2.0.0-rc.1`. The tag must equal `v` and `.pkit/VERSION` (PRJ-004), and the wheel's version is PEP 440's. Only the first spells tag, file and wheel alike.
- **Where a candidate's versions are written:**
  - **(M) On main.** Main then records `2.0.0rc1` with every changeset still pending, and the next candidate or the final is computed from a tree at a candidate.
  - **(R) In its tag alone.** The candidate's release commit is made on main's head, tagged, and only the tag is pushed. Main stays at 1.149.0, and each later candidate, and the final, is computed from main again.
- **A component's version in a candidate:**
  - **(a) A candidate of its own,** such as `project-management 0.55.0rc1`.
  - **(b) A release version,** such as `project-management 0.55.0`.

### Decided: (R), with (a)

- **(R), with (a),** as the maintainer decided (choices 1 and 2). A candidate is the next release that main's pending changesets compute, with every version it writes given the suffix `rcN`. The backbone and each component that release moves carry the same `N`. A component it does not move keeps its version.
- **Why (R).** The 27 October decision keeps the changesets pending, so main's tree plus its changesets already is "the next release". Computing each candidate from it needs no arithmetic from a candidate, and main never records one. So `check-diff`, the migration stamp, the released-folder rule, the folder-prediction warning and `uv sync` on main read nothing new. The final is computed the same way, from the last candidate's source commit, and consumes the changesets it includes once (question 6).
- **Why (a) under the decision.** Under (b), rc1 and rc2 would both carry `project-management 0.55.0`, each computed from 0.54.0, with different content. A project moving between them would see no move, and run none of the new migrations. A version names one content only if each candidate's component versions carry its suffix.
- **What (M) would cost.** Main would record a candidate, so every row of the table above would bind. The next release would need its arithmetic from a candidate, and floors raised on main would need a reading for pre-releases.
- **(R) changes PRJ-002 D3, which the maintainer authorised.** D3 wrote every version number on main, through a release PR, each with one authoring commit there. A candidate's versions live on a commit main never holds. D3's title says it: "Every version that reaches `main` is written there by the release PR". Its wording covers candidates and the final release that ends a line (question 6), and no maintenance branch, which raises other questions.
- **No branch, the tag alone.** A branch `release/v2.0.0rcN` with a `chore(release):` commit carries both of the markers by which `pkit release merge` accepts a release PR. Merged, it would put a candidate on main with every changeset pending. A branch is also an install ref that can move under the same version, against ADR-065 point 12.
- **Main is held to releases.** `pkit release check`, which CI runs on every PR, refuses a pre-release `.pkit/VERSION` or component version on the default branch. `pkit release merge` refuses a PR whose tree records one.
- **`N`** is one past the highest `vX.Y.ZrcK` tag for the release's backbone version `X.Y.Z`, read from the remote's tags, not a clone's. A candidate tag is never deleted or moved. A withdrawn candidate is marked so on its Release, and the next one takes `N + 1`. A reused `N` would let one version name two contents (COR-059 point 9).
- **The mode is explicit:** `pkit release plan --pre` and `apply --pre`. The maintainer chose one flag name for cutting and for installing, `--pre`, and the records keep "release candidate" for the thing itself.
- **A candidate is refused,** before anything is written, when:
  - the release moves no backbone version, since a candidate is a backbone tag. This also refuses it in an adopter's repository, whose release moves only the adopter's own components.
  - its backbone version differs from the open line's, or any version is below the previous candidate's. A tester at that candidate would meet ADR-065 point 7's refusal of a component bundled older.
  - `vX.Y.Z` is already tagged, so the line is finished
  - main's head is the commit the last candidate was cut from, so the candidate would tag the same content again
  - it runs anywhere but the default branch's head (COR-054)
- **The `version` commands stay as they are.** Retiring them is a surface change of its own, decided apart.

## 2. Changesets and notes

### Today

The release step consumes every pending changeset, prepends one `CHANGELOG.md` section keyed by the backbone's version, and deletes the changesets. `pkit release publish-notes` publishes one section as the body of a notes-only GitHub Release.

### The decision, and what follows from it

- **A candidate consumes nothing** (27 October). Its release commit writes versions, and a changelog section, in its tag alone.
- **A candidate's section,** `## 2.0.0rc1 — <date>`, lists every pending entry, since 1.149.0. Its tag carries it, and its pre-release publishes it.
- **Main's `CHANGELOG.md` gains one section, the final's,** written when the final consumes the changesets. So it covers everything the candidates shipped, and lists nothing twice.
- **Each candidate's notes repeat the earlier candidates' entries.** That is what a candidate's notes say: everything it holds over 1.149.0. A list of what is new since the previous candidate could follow later.
- **The issue's words.** Its notes say a later candidate or the final "follows from the same changesets", which (R) does literally.

### The options left

- **A candidate's section on main as well,** under the final's. Rejected: each candidate's entries would appear once per candidate, the duplication the decision avoids.
- **A candidate's notes in its Release alone,** with no section in its tag's `CHANGELOG.md`. Possible, but a tester reading the installed tree would find no notes for what they run.

### Decided

The candidate's section in its tag, published as its pre-release, and the final's single section on main.

## 3. Floors and ranges

### Today

- **A floor is raised only to a release version, never to a pre-release** (PRJ-002 D4). The release step resolves `release` to the backbone it ships, and refuses when that is a pre-release.
- **Every reader compares a range through `connections.range_admits`,** a PEP 440 specifier set. `>=2.0.0` excludes `2.0.0rc1`, which sorts below it. `<2.1.0` admits it, and `<2.0.0` excludes it, since PEP 440 keeps a version's own pre-releases out of `<` that version.
- **How a specifier set reads a pre-release by default** has changed across `packaging` releases. The locked 26.2 admits `2.0.0rc1` under `>=1.144.0,<2.1.0`. `pyproject.toml` allows `packaging>=24.0`, and a `uvx` install resolves fresh, so an older default could refuse it.

### Options

Under (R), main writes the release's floors at the final as today. The question is what a candidate's own tree carries.

- **(iii) The floors wait for the final, the bounds do not.** The candidate raises no floor. It writes the broaden, and each upper bound a changeset declares, as the release would. Both are release versions, such as `<2.1.0` and `<2.0.0`.
- **(iv) The release's floors, as candidates.** The candidate writes every floor the release would, with each version this release writes given the suffix: `>=2.0.0rc1`, `>=0.55.0rc1`.
- **(v) A candidate read as its release.** The candidate writes `>=2.0.0`, and every reader reads `2.0.0rcN` as `2.0.0`.

### Decided: (iii)

- **(iii),** as the maintainer decided (choice 3). It leaves D4 as it stands, and no floor writer changes: a candidate's tree names no pre-release floor. The candidate's plan still checks every floor and range as the final's would, since it is the release's plan. So `check_raised_ranges` and `dependency_range_problems` refuse a candidate exactly where they would refuse the final.
- **Its cost.** A component whose floor the final will raise is admitted on an older backbone in the candidate's tree. Within one release that cannot matter, since a transition moves every shipped component together (COR-059 point 7). It can for a consumer that takes one capability from a candidate's tag on an older backbone (COR-041), which candidates do not support.
- **Bounds must be written.** A bound the release widens is computed from the release's version: `<2.0.0` for `project-management 1.0.0`, which admits `1.0.0rc1` as written. Without it, the candidate's own dependents would refuse it.
- **`range_admits` passes `prereleases=True`.** A range that names no pre-release, such as `>=1.144.0,<2.1.0`, then admits `2.0.0rc1` under any `packaging` release. Ordering still excludes a pre-release where PEP 440 does: `<2.0.0` refuses `2.0.0rc1` with or without it.
- **Why that is a realisation, not a change to COR-030.** Every caller of `range_admits` asks whether one version, already installed, shipped or named as a target, is admitted. No caller picks a version from a list. PEP 440 excludes pre-releases only from such picking, and lets in one already present or asked for. Picking is `_max_released_tag`'s and `latest_tag.py`'s, which skip pre-releases.
- **(iv) was the alternative.** Testers would run the final's floors. It changes what D4 decides, and the floor writers learn pre-release values.
- **(v) is rejected.** It misreads a range that names a pre-release, such as `>=2.0.0rc2`, which `package_validate` accepts. It would also apply to `requires_capabilities`, reading an adopter's `0.5.0rc1` as `0.5.0`.

## 4. Migrations

### Today

- **The folder.** A migration lives in `<X.Y.0>/`, and the folder covers every patch of its minor (COR-010).
- **The window,** `pending_migration_scripts`, runs each folder whose minor is above the lower bound's and at or below the target's. The backbone's lower bound is `completed_version` (ADR-065 point 3). A component's is the version its manifest records.
- **On a candidate the runner breaks twice:**
  - `parse_version_tuple` raises on the target `2.0.0rc1`, after propagation has run
  - `as_recorded_version` and `_same_version` read `2.0.0rc1` as `2.0.0` and `0.55.0rc1` as `0.55.0`. So a project at a candidate never runs that folder again, and a component's move from its candidate to its release looks like no move.
- **What (R) leaves alone.** Main never records a candidate, so `check-diff`, the stamp, which folders count as released, and the folder-prediction warning stay as they are. The warning reads the release's plan, whose versions carry no suffix.

### Options

- **(A) A candidate carries its release's folder, and has not finished it.** The upper bound is read by minor, so a transition to `2.0.0rcN` runs `2.0.0/`. The lower bound is read in PEP 440 order, so a completion of `2.0.0rcN` sits below `2.0.0/`. The next transition runs that folder again, whole. The same holds for each component's folders.
- **(B) Each script once on every path.** A project at rc1 moving to rc2 would have to know which scripts of `2.0.0/` rc1 shipped. Folder names cannot say it, since every candidate is cut from main's `2.0.0/`. Only a ledger of the scripts that ran could, and COR-059 rejects one: it drifts from the files, and conflicts across branches.

### Decided: (A)

- **(A), with an add-only rule,** as the maintainer decided (choice 4). A script a candidate shipped is never edited, renumbered or removed. A correction is a new script in the same folder. The candidate path and the stable path then run the same scripts. A repeat reruns an unchanged script, which every migration's idempotence covers (COR-010, core rule 5).
- **Why add-only.** COR-010 makes only backbone migrations safe over any state. Without the rule, an edited component script would run over its earlier version's output, which its contract does not cover. A removed one would leave testers with an effect the stable path never gets. Keeping edits instead would change COR-010 for components.
- **The add-only rule is held by review for 2.0.** The lifecycle README's "Script contract" and the migration-authoring skill state it. A check follows if a second candidate line happens (COR-007).
- **Each folder a candidate ships changes nothing when run again over its own output.** Review of the drafted records found that add-only alone leaves the two paths apart, as when a rerun of an early script undoes a later one. A test runs the folders a cut will ship twice over the migration fixtures. CI runs it on every pull request, and the pre-release run runs it again on the source commit before each cut (ADR-072 point 5).
- **The runner's change:** the parsing of a candidate, one comparison for the lower bound, and whole public versions where `as_recorded_version`'s callers compare. "Public" keeps the pre-release and drops a local segment, so `0.6.0+x` still reads as `0.6.0`, as today.
- **The walk under (A):**

| Transition | Backbone folders that run | `project-management` folders that run |
|---|---|---|
| 1.149.0 → 2.0.0rc1 | `1.150.0/`, `2.0.0/` as rc1 holds it | `0.55.0/`, from 0.54.0 to 0.55.0rc1 |
| 2.0.0rc1 → 2.0.0rc2 | `2.0.0/` again, with every script added since rc1 | `0.55.0/` again |
| 2.0.0rc2 → 2.0.0 | `2.0.0/` again | `0.55.0/` again |
| 1.149.0 → 2.0.0 | `1.150.0/` and `2.0.0/`, each script once | `0.55.0/`, each script once |

- **"Once each" does not hold on the candidate path.** A project that follows every candidate runs a script of `2.0.0/` once on each hop. That is up to once for each candidate, and once more at the final. It holds on the path without candidates, and no option short of a ledger gives it on both. The maintainer waived it for testers who follow every candidate (choice 4).
- **A script a candidate shipped is corrected only by a new script,** as the maintainer decided (choice 4).
- **A script merged after the last candidate's source commit** into a folder the final ships would never run for a project at the final. The final is cut from that commit, and a project at 2.0.0 runs no `2.0.0/` script again. So the final's cut and its release PR's merge refuse while main holds such a script, and another candidate, or a later folder, takes it in (PRJ-002 D5, ADR-072 point 3).
- **A rerun may restore a default the project removed** after the script first ran (COR-010, ADR-065 point 5). Each candidate's notes say so, as a release's do.
- **The final's own window is unchanged** for a project at 1.149.0, so adopters on the stable path see nothing new.

## 5. Install and upgrade

### Today

- **What runs a command** is the project's pin, through the router, or else the installed tool (ADR-039, ADR-049). So `pkit pin` runs under the project's current release. `pkit init` writes no pin (ADR-064 point 3), and `pkit upgrade --no-pin` writes none (ADR-064 point 2).
- **"Latest" never picks a candidate.** The tool step and a pinned raise read the highest release tag, and skip pre-releases (ADR-063 point 1). `latest` follows release tags alone (PRJ-004).
- **Nothing stops a candidate's own pkit from moving an unpinned project.** A tool installed at `2.0.0rc1` finds the latest release below itself, and its `pkit upgrade` moves the project and pins it there.
- **An interrupted move to a candidate names no way on.** ADR-065 point 9 has the latest release's upgrade finish an interrupted raise, and no latest release is a candidate.

### Options

- **The way in from 1.x:**
  - **the candidate's own upgrade, through the bypass** that ADR-065 point 9 names. Under `PKIT_NO_ROUTE` it runs in process, moves the project, and pins it at the candidate.
  - **`pkit pin 2.0.0rc1`.** It runs under the project's 1.x release, whose pin refuses a candidate, and no 1.x release will change that.
- **Moving within the line:**
  - **`pkit pin 2.0.0rc2`,** once a candidate's own code accepts a candidate pin
  - **or** `pkit upgrade` follows newer candidates of the line its pin names
  - **or** an upgrade with a flag that asks for candidates, each time
  - **to the final:** `pkit upgrade`, which hands over to a newer release already (ADR-065 point 9)
- **Guarding the default channel:** an upgrade to a candidate refuses unless the project asked for it, or it proceeds as today.

### Decided

The maintainer decided choice 5 on 27 October, and revised the recommendation: a flag asks for candidates, each time.

- **`pkit upgrade --pre`** moves a project to the newest release, candidates included, and pins it while it is on a candidate. Testers move within a line with it.
- **A plain `pkit upgrade`** never moves a project onto a candidate its pin does not name. From a candidate, it takes the project to the final once that is out.
- **The first hop from 1.149.0,** whose pkit has no `--pre`, is the one-off command, which runs the candidate's own upgrade through the bypass:

  ```
  PKIT_NO_ROUTE=1 uvx --from git+ssh://git@github.com/aleskalfas/project-kit.git@v2.0.0rc1 project-kit upgrade
  ```

- **rc1 ships the pin change.** `pkit pin` accepts `X.Y.ZrcN`, ordered by PEP 440, and refuses an older version as today. So the pin file can name the candidate a project is on, and naming one by hand stays a gesture.
- **An upgrade to a candidate nobody asked for refuses,** and writes nothing. Where the guard runs, and what counts as asking, ADR-072 points 6 and 7 say.
- **A move to a candidate always pins.** A project left unpinned at a candidate meets the guard of the candidate's own upgrade, and the sync guard of every 1.x tool. So `--no-pin` is refused on a move to a candidate, `init` by a candidate pins the project it installs, and `pkit unpin` refuses while the project records a candidate (ADR-072 point 7).
- **A withdrawn candidate stays the newest** until the next is cut, and `pkit upgrade --pre`, which reads tags alone, may take it. Its Release says it is withdrawn (ADR-072 point 8).
- **An interrupted move names its way on.** For the first hop, each candidate's notes say: run the same command again. A move between candidates cut short has the remedy ADR-072 point 8 gives.
- **Testers work on a branch,** and go back by abandoning it. `2.0.0/002-move-answers-to-files.sh` moves answers out of artefacts outside `.pkit/` and adds answer files, so a checkout of `.pkit/` alone no longer brings a project back. PR #2219 made rolling back a revert of each upgrade's commit, which restores the files outside `.pkit/` too (ADR-049 point 3).
- **Not the global tool.** `uv tool install --force …@v2.0.0rc1` puts every unpinned project on the machine behind a candidate's guard.
- **The development install is unchanged.** Under (R), main never carries a candidate's version, so an install from main stays the development install it is today (PRJ-004).

## 6. Publishing

### Today

`release-pr.yml` opens a release PR on dispatch and every Monday, and does nothing when no changeset moves a version. Its body holds the generated changelog section. `release-tag.yml` cuts `v` and `.pkit/VERSION` on each push to main, publishes the notes-only Release with the section as one `--notes` argument, and moves `latest`.

### Decided

The maintainer decided choices 6 and 7 on 27 October, and revised the recommendation. The note had a workflow of its own for candidates, and the final release cut from main's head, held at the last candidate's commit.

- **No workflow of its own.** The existing `release-pr` workflow gains a "pre-release" input. With it, the run:
  - runs `pkit release apply --pre` on main's head, which writes the `rcN` numbers and leaves the changesets pending
  - commits the result on a commit on no branch, in place of a release PR
  - builds and checks the package
  - pushes the tag `vX.Y.ZrcN` alone, and runs `publish-notes` marked pre-release
- **Nothing merges, so `release-tag.yml` does not run.** `pkit release plan --pre` previews a candidate beforehand.
- **The notes.** `publish-notes` reads the candidate's heading, and creates its Release with `--prerelease`, so GitHub never shows a candidate as its latest release. `latest` never moves to a candidate.
- **No scheduled run.** PR #2233 removes the weekly release run, so a release is cut only when the maintainer starts it (#2232). The stale release PR #800 is closed.
- **The notes do not fit, candidate or final.** The section is 550,767 characters, and three limits stand in its way:
  - a pull request's body, at 65,536 characters
  - a GitHub Release's body, at about 125,000
  - one argument on Linux, at 128 KiB, which `--notes` passes the body as
- **So the notes are written to a file and linked past the cap.** `publish-notes` writes the body through `--notes-file`. Where the section exceeds the cap, the body becomes a short summary that links the section in `CHANGELOG.md` at the tag. The release PR's body links the section the same way.
- **No artifact,** as PRJ-004 rules.
- **The final is cut from the commit the last candidate came from,** not from main's head. A change merged after that candidate would ship untested, a documentation fix included.
  - A commit on top of the last candidate's source commit carries the final versions and takes the tag `vX.Y.Z`.
  - A pull request then brings those versions into main, and consumes the changesets the final included. Changesets merged since stay pending for the next release.
  - Main is never frozen while candidates are tested, so the note's question of the line's length falls away.
  - A withdrawn last candidate still needs another candidate first.
  - The release PR's head is the tagged commit itself, and `pkit release merge` lands it only while its head is the commit the final's tag names. ADR-072 point 3 says how the step finds the source commit from the tags.
- **What cannot wait.** A change merged since the source commit that the final would lose or break cannot wait for the next release. Such are a migration in a folder the final ships, an edit to a changeset it consumes, and a range that excludes a version it writes. Before the final's tag, such a change needs another candidate first. After it, the change is reverted on main, or a migration moved to a later folder, and lands again once the release PR has merged (PRJ-002 D5, ADR-072 point 3).
- **The looser test,** the maintainer's judgement of what may ship untested, was the alternative, and so was main held at the last candidate's commit until the final.

## 7. Which records change

The maintainer decided the carriers as recommended (choice 8): PRJ-002 and PRJ-004 refined, the new ADR-072, and ADR-049, ADR-063, ADR-064 and ADR-065 refined, each pointing to it. PR #2224 holds them, for the maintainer to accept in one step.

| Record | Change | Why |
|---|---|---|
| PRJ-002 | refined in place, with the maintainer's authorisation | It is project-kit's release policy, and (R) and the final's source change what D3 decides. D3, its sentence on the tagged main commit, the Rationale's "one authoring commit, on main" and the Implications' writes on main gain the candidate's case and the final's. A candidate is cut on request from the default branch, from the pending changesets, which stay pending. Its versions exist only in its tag. The final is cut from the last candidate's source commit, and its release PR brings its versions into main. D4 stands under (iii), its title saying a floor rises only in a final release. The mechanics, such as the counter and the refusals, go to the release README, as "Policy, not mechanics" asks. |
| PRJ-004 | refined in place | It fixes the tag form and the install refs. It gains the tags `vX.Y.ZrcN` on a commit main never holds, never deleted or moved, and no branch as an install ref. `latest` is never on one, and of the readers that pick a version to install, only one asked for candidates picks them. Its Release is marked a pre-release, and notes past the cap are linked. |
| a new ADR | recommended | One home for the realisation that spans the release step, the range reader, the runner, the pin, the guard and the notes. Only a new record can carry the options and why each was rejected, and ADR-065 already holds 14 points (COR-025). It records `prereleases=True` as a reading for the whole project, since it changes how every adopter's ranges are read, not only a candidate's. |
| ADR-065 | refined in place | Point 4 gains the hand-over of `--pre` and the guard among upgrade's own checks, and step 4's lower bound in PEP 440 order. Point 8 gains a row for a recorded target that is a candidate above the running pkit, whose remedy is `pkit upgrade --pre`. Point 9's hand-over takes the newest release, candidates included, under `--pre`. Point 12 says a candidate's tag names one content and never moves. |
| ADR-049 | refined in place | Its pin token widens to `X.Y.ZrcN`, and the refusal's reason, a router change, is corrected. Point 3's `pkit upgrade` raises a pin under `--pre` to the newest release, candidates included. Its rollback, a revert of each upgrade's commit, is main's since PR #2219. |
| ADR-064 | refined in place, before rc1 | Point 2's `--no-pin` and point 3's unpinned `init` do not apply to a move to a candidate, which always pins. |
| ADR-063 | one bullet | Its Implications' "Pre-release tags" bullet says the tool step installs no candidate, even under `pkit upgrade --pre`, which moves the one project. |
| COR-010 | no change, given the add-only rule | It names semantic versioning. `2.0.0rc1` is PEP 440's spelling of semver's `2.0.0-rc.1`, with the same precedence. Its folder rule covers a minor's patches, and a candidate is none. Only edits to shipped component scripts would need a change, and the add-only rule rules them out. |
| COR-059 | no change | Point 1's release is a backbone version and its components' versions, which a candidate is. Point 6 runs the next transition "from the recorded completion", which (A) reads in PEP 440 order. Point 9 holds because a candidate number is never reused. |
| COR-030 | no change | `prereleases=True` judges one version, never a pick from a list (question 3). |

**Docs:**

- the release README: `--pre` and its refusals, the counter, the final's cut from the source commit and its release PR, the release workflow's "pre-release" input, and the notes
- the lifecycle README: the window in "The upgrade flow", the lower bound in "Which version a migration targets", and the add-only rule in "Script contract"
- the migration-authoring skill: the add-only rule
- the CLI README: `pkit pin`, `pkit upgrade --pre`, upgrade's guard and `--no-pin`, and `release plan --pre` with its refusals

### What changes for an adopter who never takes a candidate

- **Range checks** admit a pre-release version under any `packaging` release. A changeset says so.
- **The window and the version comparisons** read whole public versions. A test over every shipped folder holds them equal to today's for every release version.
- **A Release whose notes pass the cap** shows a summary with a link.
- **Unchanged:** the window from 1.149.0 to 2.0.0, and `latest`, the tool step and a pinned raise, which never pick a candidate. The guard never fires on a release target.

## 8. The smallest path to a usable 2.0.0rc1 this week

**Before rc1.** The maintainer accepts the records on PR #2224, and one change builds, merged to main before the cut:

1. `pyproject.toml`'s version pattern admits `X.Y.Z(a|b|rc)N`.
2. The release step's `--pre` mode. It takes the release's plan, suffixes every version it writes and raises no floor. It reads the counter from the remote's tags, refuses as question 1 lists, and leaves the changesets in place. The lint and `publish-notes` read the candidate's heading.
3. `pkit release check` and `pkit release merge` refuse a pre-release version on the default branch, and `pkit release merge` refuses every release PR while a line runs.
4. `range_admits` passes `prereleases=True`.
5. The runner's window, and whole public versions in `as_recorded_version`'s callers.
6. `pkit pin` accepts a candidate, `pkit upgrade --pre` moves to the newest release, candidates included, an upgrade refuses a candidate nobody asked for, a move to a candidate always pins, and `init` by a candidate pins.
7. `publish-notes` writes through `--notes-file`, links the section past GitHub's cap, and marks a candidate's Release a pre-release.
8. The `release-pr` workflow's "pre-release" input, whose run runs the folder test of ADR-072 point 5 before each cut.
9. A changeset for the backbone, the docs above, and the add-only rule.

The maintainer then starts the release workflow with its "pre-release" input, which tags `v2.0.0rc1` and publishes its pre-release. Testers move a project, on a branch, with the one-off command.

**Before the last candidate:** the release step's cut of the final, with its refusal of what cannot wait, and the release PR's body that links the section, must be in the last candidate's source commit, since the final is cut there. The final's notes are as large as rc1's. `pkit release merge`'s check of the final's release PR lands before that PR merges (ADR-072 point 3).

**After the final:** the open questions below.

## Decisions taken

The maintainer decided each question on 27 October. The decision that a candidate leaves the changesets pending came first, on #2211, and the eight below on PR #2224.

1. **Candidates off main:** a candidate's versions exist only in its tag, (R), which changes what PRJ-002 D3 decides ("ok agree"). Carried by PRJ-002 D3 and D5, PRJ-004's candidate tag, and ADR-072 points 1 to 3.
2. **A component's version in a candidate:** a candidate of its own, (a), on the backbone and on each component the candidate moves, since a project must record that it is on a candidate to be upgraded to the final. Carried by PRJ-002 D5 and ADR-072 point 1.
3. **Floors in a candidate's tree:** none until the final, (iii). The final raises them, ranges count a candidate as inside them where they are checked, and upper bounds still widen ("agree"). Carried by PRJ-002 D4 and ADR-072 point 4.
4. **The migration window:** (A). A move to a candidate runs its release's folder, and each later hop runs it again, every script idempotent and held by a test. A script a candidate shipped is corrected only by a new script, and "run once each" is waived for testers who follow every candidate ("agree"). Carried by ADR-072 point 5 and ADR-065 point 4.
5. **The way in and on:** `pkit upgrade --pre` moves a project to the newest release, candidates included, and pins it while on a candidate. A plain `pkit upgrade` never moves a project onto a candidate, and from a candidate takes it to the final once out. The first hop from 1.149.0 is the one-off command, and testers work on a branch ("yes"). Carried by ADR-072 points 6 to 8, with ADR-049, ADR-063, ADR-064 and ADR-065.
6. **Publishing:** through the existing release path, not a workflow of its own. The `release-pr` workflow gains a "pre-release" input, `pkit release plan --pre` and `apply --pre` write the `rcN` numbers, and the run pushes the tag alone and publishes notes marked pre-release. One flag name on both sides, `--pre`, and `latest` never moves to a candidate ("yes"). Carried by PRJ-004 and ADR-072 point 9.
7. **The final's source:** the commit the last candidate came from, not main's head. A commit on top of it carries the final versions and takes the tag, and a pull request brings them into main, consuming the changesets the final included. Main is never frozen, and the weekly release run goes, so a release is cut only when the maintainer starts it (#2232, PR #2233) ("ok"). Carried by PRJ-002 D3 and D5, and ADR-072 points 3 and 9, with what review found follows from it: a change merged since that the final would lose or break needs another candidate first, or a revert on main after the tag.
8. **The records' carriers:** PRJ-002 and PRJ-004 refined, the new ADR-072, and ADR-049, ADR-063, ADR-064 and ADR-065 refined, each pointing to it.

## Open questions

Nothing below is decided. Each waits for a case or for 2.0.0.

- **A development version on main.** The maintainer okayed, as a design question for after 2.0.0, main holding the next version as a development version, such as `2.0.0.dev0`. Main's number would then be honest between releases. It touches the release step, the readers of main's versions and PRJ-004's development install, and nothing in this note or its records rests on it.
- **What is new since the previous candidate,** listed in each candidate's notes beside everything since the last release.
- **A check of the add-only rule,** if a second line happens (COR-007).
- **The `version` commands' retirement,** `pkit version bump --pre` and `promote`, as a surface change of its own.
- **A run that ends a line by mistake.** Started without its "pre-release" input while a line runs, the release workflow cuts the final and pushes its tag before any pull request, so a forgotten input ships the final. ADR-072 point 9 keeps the one input the maintainer chose. An input of its own for the final's run would refuse a run that names neither. The architect recommends it, and PR #2224 puts it to the maintainer before the build for #2211 cuts a final.
- **Leaving a line without its final.** A cut refuses while a line at another version runs, and no other release ships while a line runs, so a line ends only with its final release. Nothing yet withdraws a whole line.
- **New migrations during a line.** While a line runs, `pkit new migration` targets the folder the final ships, since that folder already waits. So each backbone migration merged during a line needs another candidate, or a move to a later folder, before the final. A `check-diff` finding during a line would say so at the pull request, a rule nobody has decided.

## Review

The critic and the architect read earlier drafts. Their findings changed the note as follows.

- **The 27 October decision** was missed by the first draft, which had candidates consume their changesets. The note now builds on it, and (R) with (a) follows from it.
- **`pkit pin` from 1.x** cannot name a candidate, so the bypass command is the way in, and rc1 ships the pin change.
- **The notes' size** blocks the final as well as rc1, so notes are written to a file and linked past the cap.
- **Reading a candidate as its release** misread pre-release bounds, so it gave way to (iii) and `prereleases=True`.
- **The default channel** gained a guard, the always-pin rule, and a way on after an interrupted move.
- **The architect's escalations.** The change to PRJ-002 D3 is decision 1. The change to D4 is avoided by (iii), and the change to COR-010 by the add-only rule.
- **The architect's concerns** are answered in questions 1, 5 and 6. They covered the branch, the counter, rising versions, the unchecked candidate commit and the final's source.
- **The architect's review of the decided records** kept an adopter's own tags from making a line, by asking the test of a running line only in the methodology's source repository. It restored the refusal of a cut while a line at another version runs, and named the two open questions on ending a line. It also found that PR #2233, which removes the weekly run, must land before the code that cuts a final reaches the workflow.
- **The critic's review of the decided records** found that a migration, a range or a changeset edit merged after the last candidate's source commit could be lost, or break main, when the final lands. So the final's cut and its merge refuse them (PRJ-002 D5, ADR-072 point 3). It also had `pkit unpin` refuse on a candidate, the rollout name what rc1 needs, and the records say that a line holds back every other release and that `--pre` may take a withdrawn candidate.
- **Not verified:** no wheel was built at a pre-release tag. The build and `--version` run of the release workflow's pre-release run are that check. The router's notice when it cannot fetch a candidate pin shows a generic warning, which is cosmetic.
