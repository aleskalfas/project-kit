---
id: ADR-072
title: A release candidate lives only in its tag, and reaches only a project that asks for it
status: proposed
date: 2026-10-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a release candidate, such as `2.0.0rc1`, lets anyone test the next final release before it ships, and nobody receives one unless they ask. `pkit release apply --pre` computes the versions that final release would write, from `main`'s head and its pending changesets, and writes each with the suffix `rcN`. It writes them on a commit that only the candidate's tag holds, and consumes no changeset. So `main` only ever records release versions.

The final release that ends a line of candidates is cut from the commit the last candidate came from, so it ships what the candidates were tested on. Its tag takes a commit on top of that one, and its release PR then brings its versions into `main`, which is never frozen while candidates are tested ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) D3 and D5). A change merged since that the final release would lose or break, such as a migration in a folder it ships, needs another candidate first, or a revert on `main` once the final release is tagged. No other release ships while a line runs.

Everything that reads a version takes a candidate as the pre-release it is, ordered below its final release, and a range admits it wherever its bounds do. `latest`, the tool's own update and a plain `pkit upgrade` never pick one. A move to a candidate runs its final release's migration folders, and the next move runs them again. So a script a candidate shipped is never edited or removed, and each folder a candidate ships changes nothing when it runs again over its own output.

`pkit upgrade --pre` moves a project to the newest release, candidates included. From a release whose pkit has no `--pre`, the way in is the candidate's own upgrade, run through the router's bypass. Any other upgrade to a candidate its pin does not name refuses, a move to a candidate always pins the project, and `pkit unpin` refuses on one. A person starts the release workflow with its "pre-release" input to cut a candidate, which the run builds and checks before it pushes the tag alone and publishes the notes as a pre-release.

This record realises PRJ-002 D5, and the candidate tag of [PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md), in project-kit's code. It refines in place the records of the pin (ADR-049), the tool's update (ADR-063), the default pin (ADR-064) and the transition (ADR-065), each with a pointer here.

## Context

#2211 asks how the release step cuts `2.0.0rc1`, a later candidate and the final release `2.0.0`. The maintainer wants to test 2.0.0 before publishing it, and expects changes after the first candidate.

On 27 October 2026 the maintainer decided that a candidate consumes no changeset. Each candidate is computed from the pending changesets and leaves them pending, and the final release consumes them once. The maintainer decided the rest on PR #2224 the same day, among them the flag `--pre` for cutting a candidate and for moving a project to one, the release workflow as the one path for every release, and the final release's source.

PRJ-002 D5 sets the policy that follows, and defines the terms this record uses, from a *release version* and a *final release* to a candidate's *source commit*. PRJ-004 adds the *candidate tag*, `v<major>.<minor>.<patch>rc<N>`, and the pre-release Release. Neither says which part of the code does what, which this record settles.

The code on `main` at `dc195bf6b` reads a pre-release in some places and refuses it in others. A candidate cut there fails before anyone could install it, and an upgrade to one fails halfway.

- **The build.** The wheel's version pattern takes `X.Y.Z` alone, so no wheel builds from a tree that records a candidate.
- **The release step.** Its next version drops the suffix before it bumps, so from a tree at `2.0.0rc1` a major gives `3.0.0`. Its floor check refuses a `release` floor on a pre-release backbone, and its check of the migration folders raises on one. Its changelog heading takes no candidate, and it creates every Release as a plain one, which GitHub would show as the latest.
- **The migration runner.** It raises on a candidate target, after the content is copied. Its comparisons read `2.0.0rc1` as `2.0.0`, so a later candidate, or the final release, runs none of the candidate's folder again.
- **The migration checks.** `check-diff` and the migration stamp refuse a tree that records a candidate. Under this record no tree they read records one, since they read trees bound for `main`.
- **The pin.** `pkit pin` refuses a candidate, in every 1.x release.
- **The range reader.** It reads a range by the default of the `packaging` release it runs on. The locked release admits `2.0.0rc1` under `>=1.144.0,<2.1.0`, and an older one, which a fresh `uvx` install may resolve, could refuse it.

Other parts read a candidate as wanted:

- **Tagging** accepts a candidate's tag.
- **"Latest."** The tag `latest`, the tool's lookup of the latest release and a pinned raise all skip a pre-release tag (PRJ-004, [ADR-063](ADR-063-upgrade-updates-the-tool.md) point 1).
- **The router** routes any pin to the tag `v<pin>`, so a candidate pin runs that tag's wheel.
- **Ordering.** Sync's guard, the pin and the comparisons of a move order versions by PEP 440, which puts `2.0.0rc1` below `2.0.0`.
- **The broaden** widens a backbone bound to cover a candidate.

Each move runs its target's code. A raise runs the target's upgrade ([ADR-049](ADR-049-per-project-version-pin.md) point 5), and a migration reaches the running pkit ([ADR-065](ADR-065-upgrade-runs-the-transition.md) point 14). So only code from the first candidate on has to read a candidate, and no 1.x release needs to change.

## Decision

**A release candidate holds the versions the next final release would compute from `main`'s pending changesets, each with the suffix `rcN`, on a commit that only its tag holds. Every reader of a version reads a candidate as the pre-release PEP 440 orders below its final release. Only a project that asks for a candidate, with `--pre`, by its pin or through the router's bypass, moves to one. The final release that ends a line is cut from the last candidate's source commit.**

The points that follow:

- **Points 1 to 3** say how the release step cuts and numbers a candidate, which states refuse a cut, how the final release is cut from its line's source commit, and which changes merged since refuse its cut and its merge.
- **Point 4** says how a range is read.
- **Point 5** says which migrations a move to a candidate runs.
- **Points 6 to 8** say how a pin names a candidate, how an upgrade guards against one nobody asked for, and the ways into a line and on.
- **Point 9** says how the release workflow cuts and publishes a candidate and a line's final release, and how notes past the host's caps are published.

### 1. A candidate is the final release's own plan, with the suffix added where the step writes

- **`--pre` asks for a candidate.** `pkit release plan --pre` and `apply --pre` plan and write a candidate, and nothing infers it. Without `--pre` they plan and write a final release, from the source point 3 sets.
- **One plan.** A candidate's plan is the plan the final release would compute from the default branch's head ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md)) and the pending changesets. It carries release versions. Every check of the plan reads them, the checks of floors, ranges and migration folders among them, so a cut is refused wherever the final release would be.
- **The suffix is added at the write.** Where the step writes the backbone's version and each version the final release would move, it writes `X.Y.ZrcN`, with one `N` for all of them. A component the final release would not move keeps its version.
- **What else it writes:** the ranges a candidate's tree carries, as PRJ-002 D4 sets them, and the changelog section PRJ-002 D5 sets, headed by the candidate's version.
- **Where it writes.** It deletes no changeset and writes nothing to `main`. Its writes are committed on top of the default branch's head, on no branch, and only the candidate's tag holds that commit (PRJ-002 D3, point 9). That head is the candidate's source commit.

### 2. A candidate's number comes from the remote's tags, and six states refuse a cut

- **The counter.** `N` is one past the highest candidate tag `vX.Y.ZrcK` the remote holds for the final release's backbone version `X.Y.Z`, and 1 where it holds none. The step reads the remote's tags, never a clone's, and refuses where it cannot read them. No candidate tag is moved or deleted (PRJ-004), so one past the highest reuses no number, as PRJ-002 D5 requires.
- **The step refuses a cut, before it writes anything,** in six states:
  - the final release would move no backbone version. A candidate is a backbone tag, so this also refuses a cut in an adopter's repository, whose release moves only its own components.
  - a line runs at another backbone version, whose final release comes first (point 3)
  - a component's version in the cut is below its version in the line's previous candidate, whether or not the cut moves it
  - the final release's tag `vX.Y.Z` exists, so its line has ended
  - the default branch's head is the last candidate's source commit, and that candidate is not withdrawn, so the cut would tag the same content again
  - the step runs anywhere but the default branch's head
- **The release README** holds the wording of each refusal.

### 3. The final release is cut from the last candidate's source commit, and the default branch holds release versions alone

- **A running line.** A line runs while the remote holds a candidate tag `vX.Y.ZrcN` and no tag `vX.Y.Z`, PRJ-002 D5's test read from the tags. Every check that asks it reads the remote's tags, as the counter does, and refuses where it cannot read them. Only the methodology's source repository asks it, the one place candidates are cut (point 2), so an adopter's own tags never make a line.
- **The final release's source.** While a line runs, `pkit release plan` and `apply` without `--pre` plan its final release, from the last candidate's source commit. That commit is the parent of the commit the last candidate's tag names, so the tags alone say where it is. The two commands run only on it, and refuse anywhere else. They refuse too while the last candidate is withdrawn, which a mark on its Release says, since another candidate comes first (PRJ-002 D5).
- **Its commit and tag.** `apply` writes the final release's versions, ranges and changelog section, and consumes the changesets pending at the source commit. Its writes are committed on top of the source commit, and the tag `vX.Y.Z` takes that commit before any pull request opens (PRJ-002 D3).
- **Its release PR.** The release PR's head is the tagged commit itself, on a `release/` branch. `pkit release merge` lands it as one squash commit, which brings into `main` what the tagged commit adds to the source commit: the versions, the changelog section and the deletion of the changesets that release consumed. Changesets merged since the source commit stay pending for the next release. Once merged, the tagged commit is held by its tag alone, as a candidate's is.
- **What cannot wait.** A change merged to the default branch since the source commit that the final release would lose or break is refused, at that release's cut and at its merge (PRJ-002 D5). Such are a migration script in a folder the final release ships, the backbone's or that of a component it moves, an edit to a changeset it consumes, and a range that excludes a version it writes. Each test reads the default branch's head from the remote, as the test of a running line reads the remote's tags.
- **At the cut.** During a line, `plan` and `apply` without `--pre` refuse while the default branch's head holds a change that cannot wait. Another candidate, cut from that head, comes first, and its source commit becomes the final release's.
- **The merge's check.** `pkit release merge` reads the remote's tags too, and refuses every release PR while a line runs. A release PR whose head records a version that has a candidate tag merges only when its head is the commit that version's release tag names. So neither a release PR opened before the final release nor a commit pushed onto its branch brings into `main` a version or code the tag does not hold.
- **At the merge.** The PR's head stays the tagged commit, so `pkit release merge` refuses the final release's PR while the default branch's head holds a change that cannot wait, or while the squash would not apply cleanly to that head. Its message names each such change, to be reverted on the default branch and to land again once the PR has merged. A script may instead move to a folder past the version the final release writes for its tier.
- **The default branch holds release versions alone.** `pkit release check`, which CI runs on every pull request, refuses a tree bound for the default branch whose `.pkit/VERSION` or component version is a pre-release. `pkit release merge` refuses a release PR whose tree records one. Neither reads a candidate's own tree, and both refuse only in the methodology's source repository ([ADR-059](ADR-059-methodology-source-repository.md)), the one place candidates are cut (point 2).
- **The changelog lint** reads a candidate's heading, as `publish-notes` does (point 9).

### 4. Every range is read with its pre-releases admitted

- **The reading.** The range reader, which every check of a range calls, reads a range with pre-releases admitted, `packaging`'s `prereleases=True`. So `>=1.144.0,<2.1.0` admits `2.0.0rc1` under every `packaging` release.
- **Ordering keeps its exclusions.** `>=2.0.0` refuses `2.0.0rc1`, which sorts below it. `<2.0.0` refuses it too, since PEP 440 keeps a version's own pre-releases out of `<` that version.
- **A caller that picks chooses its pre-releases itself.** A caller that picks a version from a list, rather than judging one, chooses which pre-releases it lets in. The lookups of the latest release let in none (PRJ-004, ADR-063 point 1), and the lookup of `pkit upgrade --pre` lets in candidates (point 8).
- **A reading for the whole project.** It changes how every range is read, an adopter's own `requires_capabilities` among them, and not only a candidate's. A changeset says so.
- **It realises the range gates of [COR-030](../../../.pkit/decisions/core/COR-030-capability-dependencies.md), and changes nothing COR-030 decides.** Every gate asks whether one version, installed, shipped or named as a target, falls in a range. None picks a version from a list, the one case where PEP 440 leaves pre-releases out.

### 5. A candidate runs its final release's migration folders, and has not finished them

- **The window.** A transition runs each folder above its lower bound in PEP 440 order and at or below its target by minor. A move to `2.0.0rcN` runs `2.0.0/`, and a completion at `2.0.0rcN` sits below `2.0.0/`, so the next move runs that folder again, whole. Each component's folders are read the same way, from the version its manifest records (ADR-065 point 4).
- **Whole public versions.** Wherever the code compares a recorded version with a bundled one, it compares public versions, the pre-release kept and a local segment dropped. So `0.55.0rc1` to `0.55.0` is a move, and `0.6.0+x` reads as `0.6.0`. For every release version, a test over every shipped folder holds the window and the comparisons to what they give on `main` at `dc195bf6b`.
- **A migration a pre-release shipped is add-only.** A script that the backbone or a component shipped in a pre-release is never edited, renumbered or removed. A correction is a new script, numbered after every script its folder holds. So each later pre-release's folder, and the final release's, runs the earlier folder's scripts first, in the same order.
- **The scope order yields to it.** A correction to a manifest-schema script that a pre-release shipped is numbered after every script its folder holds too, where the lifecycle README's order of scopes would put it first. That is safe since the final release ships its last candidate's folders (point 3), so every path runs a folder in the order a candidate shipped it. The runner reads no manifest between a folder's scripts: it lists them before the first, and writes the completion after the last, by an edit of its own line (ADR-065 point 3). A script between the two that needs the corrected format is corrected the same way, by a later script.
- **A folder a pre-release ships is idempotent as a whole.** Run again over its own output, it changes nothing. With the add-only rule, the path through pre-releases then reaches the state the path without them reaches.
- **A test holds the folder rule.** It takes from the plan the folders the next cut would ship, the backbone's and each moved component's, runs them twice over the migration fixtures, and holds the second run to no change. CI runs it on every pull request, and the pre-release run runs it again on the source commit before each cut (point 9).
- **Where the two rules bind.** They bind the migrations of whatever ships pre-releases, the backbone or a component. Here that is the backbone and each component shipped with it, whose candidates are their pre-releases. A component no pre-release ships, such as an adopter's own, meets neither rule, and the lifecycle README's script contract and the migration-authoring skill state both in these terms.
- **Each script runs once on the path without candidates.** A project that follows every candidate runs a script of its final release's folder on each move, up to once for each candidate and once more at the final release. A rerun may restore a default the project removed after the script first ran, and each candidate's notes say so, as a release's do (ADR-065 point 5). A project that moves from the latest release to the final release runs the window it would run if no candidate existed.

### 6. A pin may name a candidate, and a pin that names one asks for candidates

- **From the first candidate on,** `pkit pin` takes a candidate in PEP 440's normal form, `X.Y.ZrcN`, beside `X.Y.Z`. It refuses another spelling, such as `2.0.0-rc.1`, and names the normal form, since the router routes `v<pin>` as written. It orders the target by PEP 440, and refuses an older version as it does for a release version (ADR-049 point 3). So the pin file can name the candidate a project is on.
- **Asking.** A pin that names a candidate counts as asking for candidates, so upgrade's guard lets a move to that pin through (point 7). `pkit pin` with a newer candidate raises the project to it, as it raises to any newer version (ADR-049 point 5).

### 7. An upgrade or an `init` refuses a candidate nobody asked for, and a move to a candidate always pins

- **The guard.** An upgrade refuses when its target is a candidate and nobody asked for one. Asking is `--pre`, a run with routing bypassed, or a pin that names a candidate (point 6). The guard writes nothing. Its message names the ways in of point 8, and, where the running pkit is the installed tool, the install of `latest`.
- **Where it runs:** among upgrade's own checks, after ADR-063's tool step and the hand-over of `--pre`, and before the transition's first step (ADR-065 point 4). A pin's code targets its pin or the latest release, and under `--pre` hands a move to a candidate over to the candidate's own code, run through the bypass. So the guard fires only where a candidate runs an upgrade nobody asked it to, such as a candidate installed as the machine's tool.
- **A move to a candidate always pins.** Such a move ends by pinning the project at the candidate, and `--no-pin` is refused on it ([ADR-064](ADR-064-upgrade-pins-by-default.md) point 2).
- **A project on a candidate stays pinned.** `pkit unpin` refuses, and writes nothing, in a project whose manifest records a candidate ([ADR-049](ADR-049-per-project-version-pin.md) point 3). Its message names the ways off the candidate: leaving the testers' branch, or `pkit upgrade` once the final release ships (point 8).
- **An `init` run by a candidate** refuses unless routing is bypassed, and pins the project it installs at the candidate (ADR-064 point 3). An interrupted such `init` is finished by the candidate's upgrade through the bypass.
- **A target at a release version never meets the guard,** so an adopter who never takes a candidate never meets it.

### 8. The way into a line, and the way on

- **`pkit upgrade --pre`** moves a project to the newest release, candidates included, and pins it while it is on a candidate. Its lookup reads candidate tags beside release tags, from the source ADR-063 point 1 reads (PRJ-004). Where the newest is a candidate above the running pkit, the upgrade hands over to the candidate's own upgrade through the bypass, as a raise does (ADR-049 point 5). Where the newest is a release, the upgrade runs as it would without `--pre`.
- **A withdrawn candidate is still found.** The lookup reads tags alone, and a withdrawal is a mark on the candidate's Release (PRJ-002 D5), so `--pre` may move a project to a withdrawn candidate until the next one is cut. That is accepted, since the lookup keeps the one source ADR-063 point 1 reads, a remote's tags, which needs nothing of the host's own interface. The withdrawn candidate's Release says it is withdrawn.
- **Where the hand-over runs.** A pinned project's routed child makes it in place of its hand-over to the latest release (ADR-065 point 9). Any other upgrade makes it after ADR-063's tool step, which installs no candidate, even under `--pre`.
- **A plain `pkit upgrade`** never moves a project onto a candidate its pin does not name. From a candidate, it takes the project to the final release once that ships, since the final release orders above its candidates (ADR-065 point 9). Until then it keeps the project at its pin.
- **The first hop, from a release whose pkit has no `--pre`,** is the candidate's own upgrade, through the router's bypass, fetched from the distribution URL compiled into the tool (ADR-063 point 1) at the candidate's tag:

  ```
  PKIT_NO_ROUTE=1 uvx --from <distribution URL>@v<candidate> project-kit upgrade
  ```

  From a 1.x release to the first candidate of 2.0, `<candidate>` is `2.0.0rc1`. The command runs the candidate's code in its own process, moves the project and pins it at the candidate (point 7).
- **Testers work on a branch,** and go back by leaving it. Each candidate's notes say so, with the way in and the way on.
- **After a move onto a candidate is cut short,** the way on is the command that started it, run again. For `pkit upgrade --pre`, that hands over to the recorded candidate or a newer one, whose upgrade finishes the move from the recorded states (ADR-065 points 8 and 9). A first hop cut short meets the message of the release the project left, which knows no `--pre`, so each candidate's notes name the command to run again.

### 9. A candidate is cut by the release workflow's pre-release run, and notes past the host's caps are linked

- **On request alone.** The release workflow, `release-pr.yml`, runs only when a person starts it (#2232). Its run that ends a line pushes the final release's tag before any pull request (point 3), so no schedule may start it.
- **The pre-release run.** Started with its input "pre-release", the run executes `pkit release apply --pre` on the default branch's head. It commits the result on top of that head, on no branch, in place of a release PR. It builds the wheel from the candidate's commit and runs `pkit --version` from it. Only then does it tag that commit, push the tag alone and publish the notes.
- **The folder test first.** Before the cut, the pre-release run runs point 5's folder test on the source commit, whose tree the plan reads.
- **Runs kept apart, and resumed.** One concurrency group keeps two runs apart. A run that stopped after pushing its tag is resumed by the next run, which first finishes what it had left: the notes, and for a final release its pull request. A pre-release run merges nothing, so the release-tag workflow does not run.
- **How the next run finds what was left.** It reads the remote's tags and Releases before it plans, and a tag with no Release lacks its notes. Once a final release's tag is pushed no line runs, so the run finds that release by its tag instead: a release tag above the version the default branch records, since every other release is tagged on the commit its PR leaves there. A run without the input then opens that release's PR from the tagged commit, where none is open, and plans no other release while the tag stands above the default branch.
- **The build.** The wheel's version pattern reads PEP 440's pre-release form, so a tree that records a candidate builds. `main` never records one, so the pattern reads nothing new there.
- **A pre-release Release.** `pkit release publish-notes` reads a candidate's heading, as the changelog lint does, and marks its Release a pre-release. So GitHub never shows a candidate as its latest release, and `latest` never moves to one (PRJ-004).
- **Notes through a file, linked past the cap.** `publish-notes` passes the body as a file, never as one argument. Where a section exceeds what a Release's body holds, the body is a short summary that links the section in `CHANGELOG.md` at the version's tag, for a final release as for a candidate. The release PR's body links the section the same way, past a pull request's cap.
- **The final release that ends a line.** Started without the input while a line runs, the run cuts that line's final release from its last candidate's source commit (point 3). It builds and checks the package as the pre-release run does, pushes the tag `vX.Y.Z` and publishes a plain Release. It then pushes the tagged commit on a `release/` branch and opens the release PR. When `pkit release merge` lands it, the release-tag workflow finds the tag and only moves `latest`, which reaches the final release at the next push to `main` after its tag, the PR's merge at the latest.
- **A release that ends no line** is the ordinary release PR from the default branch's head, which the release-tag workflow tags once it merges (PRJ-002 D3).

## Rationale

**Why a candidate's versions live in its tag alone.** PRJ-002 gives the policy reason, "Why a candidate's versions live only in its tag". The code's side is that the release step needs no arithmetic from a candidate, and no reader of `main`'s versions meets one, `check-diff`, the migration stamp, the folder-prediction warning and `uv sync` among them. Those readers also take a folder at or below the version `main` records to hold what that release shipped. The final release's PR keeps that true only because its cut and its merge refuse a script merged since the source commit into a folder the release ships (point 3).

**Why the suffix is added at the write.** The plan's checks know release versions alone. Added at the write, the suffix leaves every check as it is, and a cut is refused exactly where its final release would be. A plan at candidate versions would teach every check a pre-release, the floor check and the folder check among them.

**Why each moved component carries the suffix.** A transition tells a move by comparing versions (ADR-065 point 2). Two candidates at one component version for two contents would show no move, and run none of the migrations added in between (PRJ-002, "Why each moved component carries the suffix").

**Why the counter, and every test of a running line, reads the remote.** A clone may lack a tag cut elsewhere. A cut from it would reuse a number, and a test of the line read from it could miss the line, and cut from `main`'s head a release no candidate tested. A reused number lets one version name two contents, and sync's guard, which compares versions, is sound only where each version names one content (the transition record's point 9, [COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md)).

**Why a cut refuses a component below the line's previous candidate.** A tester follows a line from candidate to candidate. A component older in the next candidate than in the one before would meet ADR-065 point 7's refusal of a component bundled older, at the tester's next move. That holds whether the cut moves the component or leaves it at a release version below the previous candidate's.

**Why a cut refuses while a line at another version runs.** A release without `--pre` cuts the running line's final release (point 3), so only one line may run at a time. With the merge's refusal of every release PR while a line runs, a line ends only with its final release, and no other release ships while it runs, though `main` takes changes throughout. Leaving a line without its final release is not decided here.

**Why a candidate needs a backbone move.** A candidate is a backbone tag (PRJ-004), and the bypass and the pin reach it through that tag. A release that moves only components cuts no tag (ADR-065 point 12), so its candidate would have nothing to install.

**Why the final release's source is read from the tags.** PRJ-002 gives the policy reason, "Why the final release is cut from the last candidate's source commit". A candidate's commit sits on top of its source commit, so the parent of the commit a candidate's tag names is that source. The step needs no record of where a candidate was cut, and every clone that reads the remote's tags finds the same commit.

**Why the release PR's head is the tagged commit.** Its squash merge brings into `main` exactly what that commit adds to the source commit. So the PR consumes the changesets the final release included and leaves later ones pending, with no code to tell them apart. A PR built afresh on `main`'s head would need a check of its own that its versions and changelog equal the tag's.

**Why the final release's tag comes before its PR.** The tag fixes what ships, the last candidate's content under the final versions. Cut on the PR's merge commit, it would take what `main` gained since the source commit, which no candidate held. `latest` follows at the next push to `main`, the PR's merge at the latest, since only the release-tag workflow writes it (PRJ-004).

**Why `pkit release merge` checks the line and the head.** While a line runs, a release PR merged into `main` would have the release-tag workflow tag what no candidate held. After the final release's tag, a release PR opened before it, or a commit pushed onto its branch, would put the final release's version on `main` over a state its tag does not hold, and the next release would be computed from that state. The merge is the last command that can refuse either before `main` holds it.

**Why the final release's cut and its merge refuse what cannot wait.** The final release ships the source commit's tree, and its PR brings that release's versions into a `main` that has moved since. A script merged since into a folder the release ships never runs for a project at that release, since its tag lacks the script and `main` then records the folder as released. An edit to a changeset the release consumes meets the PR's deletion of it. A range that excludes a version the release writes was never checked, since the broaden and the range checks read the source commit's tree.

**Why such a change is refused, not mended on `main`.** Before the final release's PR merges, a branch cannot mend the range: PRJ-002 D1 keeps `requires_backbone` off it, and lets it correct a `requires_capabilities` range only to admit the version the tree carries. Nothing later finds the script either, since `check-diff` reads only the scripts a change adds, and the folder-prediction warning reads a folder at or below the recorded version as released. So the cut refuses while another candidate can still take the change, and the merge, after the tag, while a revert can. The merge refuses a squash that would not apply cleanly too, since the PR's head is the tagged commit and takes no fix.

**Why the default branch is held in two places.** A commit that records a candidate could reach a branch, by hand or by a mistaken run. `pkit release check` catches it on every pull request, and `pkit release merge` refuses it at the one command that merges a release PR.

**Why that refusal, and the test of a running line, bind only in the methodology's source repository.** Candidates are cut only there, since the step refuses a cut whose final release moves no backbone version (point 2). Bound anywhere else, the refusal would refuse an adopter's own component at a pre-release version, or an adopter's default branch that a tester moved to a candidate. An adopter whose own tags include one such as `v1.0.0rc1` would also seem to run a line. Keyed to ADR-059's test of the source repository, every adopter's tree and tags are untouched.

**Why `prereleases=True` realises COR-030's range gates, and changes none of them.** COR-030 gates on whether an installed or moving version satisfies a range. PEP 440 leaves pre-releases out only when an installer picks among versions, and lets in one already present or asked for. Every caller of the range reader judges one such version, so the reading takes COR-030's ranges as PEP 440 means them, and a caller that picks keeps its own filter. The explicit flag also fixes a reading that `packaging`'s default has moved on across its releases.

**Why a candidate runs its final release's folder, and has not finished it.** The upper bound by minor gives a candidate its final release's folder, since it previews that release. The lower bound in PEP 440 order makes the next move run that folder again, whole, with every script added since. Running only the scripts a candidate did not run would need a record of the scripts that ran, which the transition record rejects (COR-059, "Alternatives considered").

**Why the add-only rule, and a folder idempotent as a whole.** The migration rule asks each script to be safe to run again ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)). On the path through candidates that is not enough, since an earlier script runs again over a later script's output, which may undo it. Add-only keeps each later folder an extension of the earlier one, and a folder idempotent as a whole changes nothing when it runs again over its own output. So each move through candidates reaches the state the later folder reaches alone, and the final release's folder reaches the state of the path without candidates.

**Why a test holds the folder rule, and where it runs.** Review reads each script alone, and misses how two scripts of one folder meet. Running the folder twice over the fixtures shows it. CI runs the test on each pull request against `main` as it was then, so two pull requests that each pass may still fail together. The pre-release run runs it on the source commit itself, the tree the cut ships (point 9).

**Why the migration rule needs no change (COR-010).** It names semantic versioning, and `2.0.0rc1` is PEP 440's spelling of semver's `2.0.0-rc.1`, with the same precedence. Its folders cover a minor's patches, and a candidate is no patch: it carries its final release's folder. The folder rule of point 5 asks more of a candidate's folders than COR-010 asks of each script, and realises COR-010's idempotence for a folder that runs more than once, so COR-010 stands.

**Why the transition record needs no change (COR-059).** Its point 1 makes a release a backbone version with its components' versions, which a candidate is. Its point 6 runs the next transition from the recorded completion, which the window reads in PEP 440 order. Its point 9 holds, since no candidate number is reused (PRJ-002 D5).

**Why each script runs once only on the path without candidates.** Only a record of the scripts that ran would give "once" on both paths. A tester who follows every candidate opts into reruns, which the folder rule makes safe, and the notes warn of a restored default. The maintainer waives "once each" for testers, and the path adopters take keeps it.

**Why whole public versions.** Read without its pre-release, `0.55.0rc1` equals `0.55.0`, so a component's move from its candidate to its final release would show as no move. Comparing the pre-release keeps the move. Dropping the local segment keeps the reading of a local version that `main`'s comparisons give.

**Why the first hop is the candidate's own upgrade.** It needs nothing of the release the project leaves. A 1.x release knows no `--pre`, its `pkit pin` refuses a candidate, and no 1.x release changes, since each move runs its target's code. The bypass is the router's own escape, the one a raise runs through (ADR-049 point 5), and typing it is the operator's consent.

**Why `--pre` asks on each move.** A plain upgrade stays the channel every adopter takes, and never meets a candidate. A tester asks with `--pre` on each move, so a later candidate's changes come only when asked for, and nothing records that a project follows a line. One name, `--pre`, cuts a candidate and moves a project to one, so it is learned once.

**Why `--pre` moves the project and never the tool.** The hand-over moves the one project, as a raise does, and the tool stays at the latest release. A candidate as the machine's tool would put every unpinned project on the machine behind the guard.

**Why a guard, and what counts as asking.** Without it, a candidate installed as the machine's tool would move each unpinned project in which someone runs `pkit upgrade`, and pin it at the candidate. `--pre` and the bypass are a person asking for the move at hand. A pin that names a candidate is a project already on the line, whose plain upgrade must finish a move to that pin. An `init` refuses too, since such a tool would otherwise install each new project at a candidate.

**Why the guard comes after the tool step.** After it, a tool installed at a candidate updates itself once the final release ships, rather than refusing on its own bundle.

**Why a move to a candidate always pins.** An unpinned project at a candidate meets the guard of the candidate's own upgrade, and sync's guard under every 1.x tool. A pin keeps it on the candidate's code through the router, whatever tool is installed. `pkit unpin` refuses on a candidate for the same reason.

**Why the release workflow, started with an input.** The maintainer chose one path for every release, the release workflow a person starts. A pre-release run merges nothing, so it pushes the candidate's tag itself, where the release-tag workflow tags only after a merge. Pushing the tag alone keeps the commit off every branch (PRJ-004). No schedule starts the workflow, since its run that ends a line pushes the final release's tag before any pull request.

**Why the run tests before the cut, and builds after it.** The folder test reads the plan, which the source commit's tree gives, and a candidate's tree, which records pre-releases, does not. The build and `pkit --version` need the candidate's versions, so they run on its commit, after the cut. Either failing stops the run before the tag fixes the candidate's content for good.

**Why notes through a file and a link.** The pending final release's section is some 550,000 characters. A pull request's body holds 65,536, a Release's about 125,000, and one argument on Linux 128 KiB. A file carries any length, and a link to the section at the tag shows all of it, for the final release as for each candidate.

### Alternatives considered

- **A candidate's versions written on `main`.** Rejected: `main` would record a pre-release with every changeset pending. Every reader of `main`'s versions would meet it, and the next candidate or the final release would be computed from a candidate (PRJ-002).
- **A candidate's components at release versions.** Rejected: two candidates would carry one component version for two contents, and a move between them would run no migration (PRJ-002).
- **A candidate's floors raised as pre-releases,** such as `>=2.0.0rc1`. Not taken: testers would run the final release's floors, but D4's rule that a floor names a release version would change, and every floor writer would learn pre-release values (PRJ-002).
- **A candidate read as its final release,** so `2.0.0rcN` reads as `2.0.0` and the candidate writes the final release's floors. Rejected: it misreads a range that names a pre-release, such as `>=2.0.0rc2`, which package validation accepts. It would also read an adopter's `0.5.0rc1` as `0.5.0` in `requires_capabilities`.
- **A record of the scripts that ran, so each runs once on every path.** Rejected, as the transition record rejects such a ledger (COR-059): it drifts from the files, and conflicts across branches.
- **Edits kept open for scripts a candidate shipped.** Rejected: an edited component script would run over its earlier version's output, which the migration rule's contract for a component's script does not cover (COR-010), so that rule would change.
- **The add-only rule alone, with each script idempotent and no rule for the folder.** Rejected: an earlier script run again over a later script's output may undo it, so the path through candidates could end where the path without them does not.
- **`pkit pin <candidate>` as the way in from 1.x.** Rejected: it runs under the project's 1.x release, whose pin refuses a candidate.
- **`pkit pin <later candidate>` as the way within a line.** Not taken: a tester would look up each candidate's number. `--pre` finds the newest, and `pkit pin` names a given one for whoever wants it.
- **`pkit upgrade` follows newer candidates of its pin's line.** Not taken: a project on a candidate would move to a later one unasked. `--pre` asks on each move.
- **A flag named `--candidate`.** Not taken: the maintainer chose one name, `--pre`, for cutting a candidate and for moving a project to one.
- **No guard on upgrade.** Rejected: a candidate installed as the tool would move each unpinned project it upgrades onto the candidate.
- **The guard before ADR-063's tool step.** Rejected: a tool installed at a candidate would refuse on its own bundle, and never update itself once the final release ships.
- **A candidate installed as the machine's tool, as the way in or by `--pre`.** Rejected: every unpinned project on the machine would sit behind the guard.
- **A branch for each candidate,** such as `release/v2.0.0rc1`. Rejected: a branch can move under one version (PRJ-004, ADR-065 point 12). It would also carry both markers by which `pkit release merge` accepts a release PR.
- **A workflow of its own for candidates.** Not taken: the maintainer chose one path for every release, the release workflow with an input.
- **A "final" input of its own,** so a run with neither input refuses while a line runs. Not taken: the maintainer chose one input. While a line runs, a run without it may cut only that line's final release (point 3), so a second input would name what the absence of the first already decides. The cost is that a run started without the input by mistake ships the final release, since it pushes the tag before any pull request.
- **Each candidate's section on `main` as well, under the final release's.** Rejected: each candidate's entries would appear once for each candidate, the duplication the 27 October decision avoids.
- **A candidate's notes in its Release alone,** with no section in its tag's `CHANGELOG.md`. Not taken: a tester reading the installed tree would find no notes for what they run.
- **Candidates cut by the `version` commands,** `pkit version bump --pre rc` and `promote`. Rejected: they write `.pkit/VERSION` alone, consume no changeset, move no component and write no changelog. A transition would then run none of the changed components' migrations. Their retirement is a surface change decided apart.
- **The final release cut from `main`'s head, with `main` held at the last candidate's source commit until its PR lands.** Rejected: `main` would be frozen while candidates are tested (PRJ-002).
- **The final release cut from a later commit a person judges safe.** Not taken: a change judged safe ships untested all the same (PRJ-002).
- **The final release's tag cut on its PR's merge commit,** by the release-tag workflow. Rejected: the tag would take what `main` gained since the source commit, which no candidate held.
- **A release PR built on `main`'s head, carrying the final release's versions,** in place of the tagged commit. Not taken: a check of its own would have to hold its versions and changelog equal to the tag's, where the tagged commit holds them by construction.
- **The final release's PR merged with no check of its head.** Rejected: a release PR opened before the final release, or a commit pushed onto its branch, would put on `main` a state the tag does not hold.
- **A change that cannot wait mended on `main` after the final release's PR merges.** Rejected: a script in a folder that release ships would never run for a project at it, an edited changeset would meet the PR's deletion of it, and `main` would hold a range no release step checked (point 3).
- **The refusal of a pre-release on the default branch as a check of project-kit's own CI,** outside the core commands. Not taken: `pkit release merge` holds it at the merge whether or not CI ran, and a check apart from the release step would split one rule about what `--pre` writes across two homes. Scoped to the source repository, the core commands bind no adopter.

## Implications

- **Records refined in place,** each with a pointer here:
  - ADR-065: point 4 places the hand-over of `--pre` and the refusal of a candidate nobody asked for among upgrade's own checks, and reads step 4's lower bound in PEP 440 order. Point 8 gains a row for a recorded target that is a candidate above the running pkit. Point 9's hand-over takes the newest release, candidates included, under `--pre`, and its refusal names `pkit upgrade --pre` where the recorded target is a candidate. Point 12 counts a candidate tag as a tagged install.
  - ADR-049: the pin's token takes a candidate in PEP 440's normal form, the refusal's reason is the router's route to the tag `v<pin>`, a pin that names a candidate asks for candidates, and `pkit upgrade --pre` raises a pin to the newest release, candidates included. `pkit unpin` refuses in a project whose manifest records a candidate.
  - ADR-064: `--no-pin` is refused on a move to a candidate, and so is `pkit unpin` on a candidate. An `init` run by a candidate refuses unless routing is bypassed, and pins.
  - ADR-063: its bullet on pre-release tags says the tool step installs no candidate, even under `--pre`.
- **The policy is PRJ-002's and PRJ-004's,** refined in the same change. This record cites them for the policy it rests on.
- **No core record changes.** The migration rule and the transition record hold (COR-010, COR-059), as the Rationale says, and the range gates hold (COR-030), as point 4 says.
- **Docs:**
  - the release README: `--pre` and its refusals, the counter, the test of a running line, the final release's cut from the source commit and its release PR, the refusals of what cannot wait at that cut and at the merge, the merge's check, the release workflow's "pre-release" input, how a run resumes, and the notes
  - the lifecycle README: the window in "The upgrade flow", the lower bound in "Which version a migration targets", and the add-only rule, the folder rule and the order a correction takes in "Script contract"
  - the migration-authoring skill: the add-only rule, the folder rule and the order a correction takes
  - the CLI reference: `pkit pin`, `pkit upgrade --pre`, upgrade's guard and `--no-pin`, `pkit unpin` on a candidate, a candidate's `init`, and `pkit release plan --pre` and `apply --pre`, with their refusals
  - each candidate's notes: the way in, the way on after a move cut short, and how a tester works on a branch
- **What changes for an adopter who never takes a candidate:**
  - a range check admits a pre-release under every `packaging` release, which a changeset says
  - the window and the comparisons read whole public versions, which a test holds equal for every release version
  - a Release whose notes pass the cap shows a summary with a link
  - unchanged: an adopter's own component at a pre-release version, and an adopter's own tags, which the release commands leave alone outside the methodology's source repository (point 3)
  - unchanged: the window from one final release to the next, and `latest`, the tool step and a plain upgrade, which never pick a candidate
- **The rollout:**
  - **Before the first candidate is cut:** every point the cut and a move read, `pkit upgrade --pre` among them, since only code from the first candidate on reads a candidate. Also the merge's refusal of every release PR while a line runs, and point 5's folder test, which the pre-release run runs before each cut. Both act from the first cut on.
  - **Before the last candidate is cut:** the release step's cut of the final release, with its refusal of what cannot wait, and the release PR's link to its section. They run on the last candidate's source commit (point 3), so they must be in its tree. The link is needed since the final release's notes are as large as the first candidate's.
  - **Before the final release's PR merges:** the merge's check of that PR, with its refusal of what cannot wait.
- **No migration.** No installed state changes shape. A pin that names a candidate has the pin file's format, and the behaviour lives in the code that runs each move.
- **Stands on these records, all accepted:**
  - COR-010, COR-030, COR-054 and COR-059
  - ADR-049, ADR-059, ADR-063, ADR-064 and ADR-065
  - PRJ-002 and PRJ-004, as refined in the same change
