---
id: ADR-089
title: A release candidate lives only in its tag, and reaches only a project that asks for it
status: accepted
date: 2026-10-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a release candidate lets anyone test the next final release before it ships, and nobody receives one unless they ask. The release step writes the versions that final release would write, each with the suffix `rcN`, on a commit only the candidate's tag holds, and consumes no changeset, so `main` only ever records release versions. A project moves onto a candidate only when someone asks, and stays pinned there. The final release is cut from the commit the last candidate came from, so it ships what was tested. For example, a tester on `3.0.0rc1` runs `pkit upgrade --pre` and the project moves to `3.0.0rc2`, pinned; once `3.0.0` ships, a plain `pkit upgrade` takes it there.

## Context

[#2211](https://github.com/aleskalfas/project-kit/issues/2211) asks how the release step cuts a release candidate, a later candidate and the final release, so that the maintainer can test the next major before publishing it, expecting changes after the first candidate.

[PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) D5 sets the policy, and defines the terms this record uses, from a *release version* and a *final release* to a candidate's *source commit*. [PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md) adds the *candidate tag*, `v<major>.<minor>.<patch>rc<N>`, and the pre-release Release. Neither says which part of the code does what, which this record settles. The code read a pre-release in some places and refused it in others, so a candidate cut from it failed before anyone could install it. That survey is the evidence of this record's pull request ([project-kit#2224](https://github.com/aleskalfas/project-kit/pull/2224)).

The maintainer chose, on 27 October 2026:
- **A candidate consumes no changeset** ([#2211](https://github.com/aleskalfas/project-kit/issues/2211#issuecomment-6441157139)).
- **Its versions live only in its tag, with the suffix on each component it moves** ([choices 1 and 2](https://github.com/aleskalfas/project-kit/pull/2224#issuecomment-6446992930)).
- **It raises no floor** ([choice 3](https://github.com/aleskalfas/project-kit/pull/2224#issuecomment-6447058417)).
- **Each move runs the final release's folder again, and a script a candidate shipped is corrected only by a new one** ([choice 4](https://github.com/aleskalfas/project-kit/pull/2224#issuecomment-6447177147)).
- **`pkit upgrade --pre` is the way in and on, and testers work on a branch** ([choice 5](https://github.com/aleskalfas/project-kit/pull/2224#issuecomment-6447305289)).
- **One path for every release, the release workflow with a "pre-release" input, and one flag, `--pre`** ([choice 6](https://github.com/aleskalfas/project-kit/pull/2224#issuecomment-6447812213)).
- **The final release is cut from the last candidate's source commit,** so `main` is never frozen ([choice 7](https://github.com/aleskalfas/project-kit/pull/2224#issuecomment-6448154308)).

On 10 November 2026 he chose no second, "final" input ([his answer on #2223](https://github.com/aleskalfas/project-kit/issues/2223#issuecomment-6784950817)).

## Decision

**The release step cuts a candidate from the next final release's own plan onto a commit only its tag holds, every reader of a version takes it as the pre-release PEP 440 orders below its final release, only a project that asks moves onto one, and the final release that ends its line is cut from the last candidate's source commit.**

### 1. A candidate is the final release's own plan, with the suffix added where the step writes

- **`--pre` asks for a candidate.** `pkit release plan --pre` and `apply --pre` plan and write a candidate, and nothing infers one. Without `--pre` they plan and write a final release, from the source point 3 sets.
- **One plan.** A candidate's plan is the one the final release would compute from the default branch's head ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md)) and the pending changesets, at release versions. Every check of the plan reads those, so a cut is refused wherever the final release would be.
- **The suffix is added at the write.** The step writes `X.Y.ZrcN`, with one `N` for all, for the backbone and each version the final release would move. A component it would not move keeps its version.
- **What else it writes:** the ranges PRJ-002 D4 sets for a candidate's tree, and the changelog section PRJ-002 D5 sets, headed by the candidate's version.
- **Where it writes.** It deletes no changeset and writes nothing to `main`. It commits its writes on top of the default branch's head, the candidate's source commit, on no branch, and only the candidate's tag holds that commit (PRJ-002 D3, point 9).

### 2. A candidate's number comes from the remote's tags, and six states refuse a cut

- **The counter.** `N` is one past the highest candidate tag `vX.Y.ZrcK` the remote holds for the final release's backbone version `X.Y.Z`, and 1 where it holds none. The step reads the remote's tags, never a clone's, and refuses where it cannot read them.
- **One version, one content.** No candidate tag is moved or deleted (PRJ-004), so no number is reused (PRJ-002 D5), and a candidate's tag is a tagged install ([ADR-065](ADR-065-upgrade-runs-the-transition.md) point 12).
- **The step refuses a cut, before it writes anything,** where:
  - the final release would move no backbone version, which also refuses a cut in an adopter's repository, whose release moves only its own components
  - a line runs at another backbone version, whose final release comes first (point 3)
  - a component's version in the cut is below its version in the line's previous candidate, whether or not the cut moves it
  - the final release's tag `vX.Y.Z` exists, so its line has ended
  - the default branch's head is the last candidate's source commit, and that candidate is not withdrawn
  - the step runs anywhere but the default branch's head

### 3. The final release is cut from the last candidate's source commit, and the default branch holds release versions alone

- **A running line.** A line runs while the remote holds a candidate tag `vX.Y.ZrcN` and no tag `vX.Y.Z` (PRJ-002 D5). Every check that asks it reads the remote's tags, as the counter does, and refuses where it cannot read them. Only the methodology's source repository asks it.
- **Its source.** While a line runs, `pkit release plan` and `apply` without `--pre` plan its final release from the last candidate's source commit, the parent of the commit that candidate's tag names. They refuse anywhere but that commit, and while the last candidate is withdrawn, which a mark on its Release says (PRJ-002 D5).
- **Its commit and tag.** `apply` writes the final release's versions, ranges and changelog section, and consumes the changesets pending at the source commit. It commits them on top of the source commit, and the tag `vX.Y.Z` takes that commit before any pull request opens (PRJ-002 D3).
- **Its release PR.** The PR's head is the tagged commit itself, on a `release/` branch. `pkit release merge` lands it as one squash commit, which brings into `main` what the tagged commit adds to the source commit: the versions, the changelog section and the deletion of the changesets that release consumed. Changesets merged since the source commit stay pending, and once the PR has merged the tagged commit is held by its tag alone.
- **What cannot wait** is a change merged to the default branch since the source commit that the final release would lose or break (PRJ-002 D5). Such are a migration script in a folder the final release ships, the backbone's or that of a component it moves, an edit to a changeset it consumes, and a range that excludes a version it writes. Each test reads the default branch's head from the remote.
- **At the cut,** `plan` and `apply` without `--pre` refuse during a line while the default branch's head holds such a change. Another candidate, cut from that head, comes first, and its source commit becomes the final release's.
- **At the merge,** `pkit release merge` refuses the final release's PR while the default branch's head holds such a change, or while the squash would not apply cleanly to that head. Its message names each such change, to be reverted on the default branch and land again once the PR has merged; a script may instead move to a folder past the version the final release writes for its tier.
- **The merge's check.** `pkit release merge` reads the remote's tags too, and refuses every release PR while a line runs. A release PR whose head records a version that has a candidate tag merges only when its head is the commit that version's release tag names.
- **The default branch holds release versions alone.** `pkit release check`, which CI runs on every pull request, refuses a tree bound for the default branch whose `.pkit/VERSION` or component version is a pre-release, and `pkit release merge` refuses a release PR whose tree records one. Neither reads a candidate's own tree, and both refuse only in the methodology's source repository ([ADR-059](ADR-059-methodology-source-repository.md)).
- **The changelog lint** reads a candidate's heading, as `publish-notes` does (point 9).

### 4. Every range is read with its pre-releases admitted

- **The reading.** The range reader, which every check of a range calls, reads a range with pre-releases admitted, `packaging`'s `prereleases=True`. So a range that names no pre-release admits a candidate within its bounds, under every `packaging` release.
- **Ordering keeps its exclusions.** `>=2.0.0` refuses `2.0.0rc1`, which sorts below it, and so does `<2.0.0`, since PEP 440 keeps a version's own pre-releases out of `<` that version.
- **A caller that picks chooses its own pre-releases.** A caller that picks a version from a list, rather than judging one, chooses which pre-releases it lets in: the lookups of the latest release none (PRJ-004, ADR-063 point 1), and the lookup of `pkit upgrade --pre` candidates (point 8).
- **For the whole project.** The reading changes how every range is read, an adopter's own `requires_capabilities` among them, and a changeset says so.
- **COR-030 stands.** The reading realises the range gates of [COR-030](../../../.pkit/decisions/core/COR-030-capability-dependencies.md), and changes nothing COR-030 decides.

### 5. A candidate runs its final release's migration folders, and has not finished them

- **The window.** A transition runs each folder above its lower bound in PEP 440 order and at or below its target by minor, for the backbone and, from the version its manifest records, for each component (ADR-065 point 4). So a move to a candidate runs its final release's folder, and the next move runs that folder again, whole.
- **Whole public versions.** Wherever the code compares a recorded version with a bundled one, it compares public versions, the pre-release kept and a local segment dropped, so `0.55.0rc1` to `0.55.0` is a move, and `0.6.0+x` reads as `0.6.0`. A test over every shipped folder holds, for every release version, the window and the comparisons to what a reading that drops the pre-release gives.
- **A migration a pre-release shipped is add-only.** A script the backbone or a component shipped in a pre-release is never edited, renumbered or removed, and a correction is a new script, numbered after every script its folder holds.
- **The scope order yields to it.** A correction to a manifest-schema script a pre-release shipped is numbered last too, where the lifecycle reference's order of scopes would put it first. A script between the two that needs the corrected format is corrected the same way, by a later script.
- **A folder a pre-release ships is idempotent as a whole:** run again over its own output, it changes nothing.
- **A test holds the folder rule.** It takes from the plan the folders the next cut would ship, the backbone's and each moved component's, runs them twice over the migration fixtures, and holds the second run to no change. CI runs it on every pull request.
- **Where the two rules bind:** the migrations of whatever ships pre-releases, here the backbone and each component shipped with it. A component no pre-release ships, such as an adopter's own, meets neither.
- **Each script runs once on the path without candidates.** A project that moves from the latest release to the final release runs the window it would run if no candidate existed. One that follows every candidate runs a script of the final release's folder on each move, up to once for each candidate and once more at the final release, and each candidate's notes say that a rerun may restore a default the project removed, as a final release's do (ADR-065 point 5).

### 6. A pin may name a candidate, and a pin that names one asks for candidates

- **From the first candidate on,** `pkit pin` takes a candidate in PEP 440's normal form, `X.Y.ZrcN`, beside `X.Y.Z`, and refuses another spelling, such as `2.0.0-rc.1`, naming the normal form. It orders the target by PEP 440, and refuses an older version as it does for a release version (ADR-049 point 3).
- **Asking.** A pin that names a candidate asks for candidates, so upgrade's guard lets a move to that pin through (point 7). `pkit pin` with a newer candidate raises the project to it, as to any newer version (ADR-049 point 5).

### 7. An upgrade or an `init` refuses a candidate nobody asked for, and a move to a candidate always pins

- **The guard.** An upgrade whose target is a candidate refuses, and writes nothing, unless someone asked: by `--pre`, a run with routing bypassed, or a pin that names a candidate (point 6). Its message names the ways in of point 8 and, where the running pkit is the installed tool, the install of `latest`.
- **Where it runs:** among upgrade's own checks, after ADR-063's tool step and the hand-over of `--pre`, and before the transition's first step (ADR-065 point 4).
- **A move to a candidate always pins,** and `--no-pin` is refused on it ([ADR-064](ADR-064-upgrade-pins-by-default.md) point 2).
- **A project on a candidate stays pinned.** `pkit unpin` refuses, and writes nothing, in a project whose manifest records a candidate ([ADR-049](ADR-049-per-project-version-pin.md) point 3). Its message names the ways off: leaving the testers' branch, or `pkit upgrade` once the final release ships (point 8).
- **An `init` run by a candidate** refuses unless routing is bypassed, and pins the project it installs at the candidate (ADR-064 point 3). The candidate's upgrade through the bypass finishes such an `init` cut short.
- **A target at a release version never meets the guard,** so an adopter who never takes a candidate never meets it.

### 8. The way into a line, and the way on

- **`pkit upgrade --pre`** moves a project to the newest release, candidates included. Its lookup reads candidate tags beside release tags, from the source ADR-063 point 1 reads (PRJ-004). Where the newest is a candidate above the running pkit, the upgrade hands over to the candidate's own upgrade through the bypass, as a raise does (ADR-049 point 5). Where the newest is a final release, the upgrade runs as it would without `--pre`.
- **A withdrawn candidate is still found.** The lookup reads tags alone, and a withdrawal is a mark on the candidate's Release (PRJ-002 D5), so `--pre` may move a project to a withdrawn candidate until the next one is cut. Its Release says it is withdrawn.
- **Where the hand-over runs.** A pinned project's routed child makes it in place of its hand-over to the latest release (ADR-065 point 9). Any other upgrade makes it after ADR-063's tool step, which installs no candidate, even under `--pre`.
- **A plain `pkit upgrade`** never moves a project onto a candidate its pin does not name. From a candidate it keeps the project at its pin until the final release ships, and then takes it there (ADR-065 point 9).
- **The first hop, from a final release whose pkit has no `--pre`,** is the candidate's own upgrade, through the router's bypass, fetched from the distribution URL compiled into the tool (ADR-063 point 1) at the candidate's tag:

  ```
  PKIT_NO_ROUTE=1 uvx --from <distribution URL>@v<candidate> project-kit upgrade
  ```

  `<candidate>` is the candidate's version in PEP 440's normal form, such as `3.0.0rc1`. The command runs the candidate's code in its own process, and moves the project, pinned (point 7).
- **Testers work on a branch,** and go back by leaving it. Each candidate's notes say so, with the way in and the way on.
- **A move onto a candidate cut short** goes on with the command that started it, run again. For `pkit upgrade --pre`, that hands over to the recorded candidate or a newer one, whose upgrade finishes the move from the recorded states (ADR-065 points 8 and 9). A first hop cut short meets the message of the release the project left, which knows no `--pre`, so each candidate's notes name the command to run again.

### 9. A candidate is cut by the release workflow's pre-release run, and notes past the host's caps are linked

- **On request alone.** The release workflow runs only when a person starts it ([#2232](https://github.com/aleskalfas/project-kit/issues/2232)), and no schedule may start it.
- **The pre-release run.** Started with its input "pre-release", the run first runs point 5's folder test on the default branch's head, the source commit. It then executes `pkit release apply --pre` there, and commits the result as point 1 sets, in place of a release PR. It builds the wheel from the candidate's commit and runs `pkit --version` from it. Only then does it tag that commit, push the tag alone and publish the notes.
- **Runs kept apart, and resumed.** One concurrency group keeps two runs apart. A run that stopped after pushing its tag is resumed by the next run, which first finishes what it had left: the notes, and for a final release its pull request. A pre-release run merges nothing, so the release-tag workflow does not run.
- **How the next run finds what was left.** It reads the remote's tags and Releases before it plans, and a tag with no Release lacks its notes. It finds by its tag a final release whose PR has not landed: a release tag above the version the default branch records. A run without the input then opens that release's PR from the tagged commit, where none is open, and plans no other final release while the tag stands above the default branch.
- **The build.** The wheel's version pattern reads PEP 440's pre-release form, so a tree that records a candidate builds.
- **A pre-release Release.** `pkit release publish-notes` reads a candidate's heading, as the changelog lint does, and marks its Release a pre-release, so GitHub never shows a candidate as its latest release, and `latest` never moves to one (PRJ-004).
- **Notes through a file, linked past the cap.** `publish-notes` passes the body as a file, never as one argument. Where a section exceeds what a Release's body holds, the body is a short summary that links the section in `CHANGELOG.md` at the version's tag, for a final release as for a candidate. The release PR's body links the section the same way, past a pull request's cap.
- **The final release that ends a line.** Started without the input while a line runs, the run cuts that line's final release from its last candidate's source commit (point 3). It builds and checks the package as the pre-release run does, pushes the tag `vX.Y.Z` and publishes a plain Release, and then opens the release PR point 3 sets. When `pkit release merge` lands it, the release-tag workflow finds the tag and only moves `latest`.
- **A final release that ends no line** is the ordinary release PR from the default branch's head, which the release-tag workflow tags once it merges (PRJ-002 D3).

## Rationale

**Point 1, the final release's own plan.** PRJ-002 gives the policy reason for a candidate's versions living in its tag alone ("Why a candidate's versions live only in its tag"). In the code, the release step then needs no arithmetic from a candidate, and no reader of `main`'s versions meets one. The plan's checks know release versions alone, so adding the suffix at the write leaves each as it is, where a plan at candidate versions would teach every check a pre-release, the floor check and the folder check among them. A transition tells a move by comparing versions (ADR-065 point 2), so each move between candidates must show as one (PRJ-002, "Why each moved component carries the suffix").

**Point 2, the counter and the refusals.** A clone may lack a tag cut elsewhere: a cut from it would reuse a number, and a test of the line read from it could miss the line, and cut from `main`'s head a final release no candidate tested. A reused number lets one version name two contents, and sync's guard, which compares versions, is sound only where each version names one content ([COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md) point 9). A candidate is a backbone tag, which the bypass and the pin reach (PRJ-004), and a final release that moves only components cuts no tag (ADR-065 point 12), so its candidate would have nothing to install. A tester follows a line from candidate to candidate, and a component older in the next candidate than in the one before would meet ADR-065 point 7's refusal of a component bundled older. A cut from the last candidate's own source commit would tag the same content again. Without `--pre` the step cuts the running line's final release (point 3), so only one line runs at a time. Leaving a line without its final release is not decided here.

**Point 3, the final release's source.** PRJ-002 gives the policy reason ("Why the final release is cut from the last candidate's source commit"). A candidate's commit sits on top of its source commit, so the tags alone say where that source is, with no record of where a candidate was cut, and every clone that reads the remote's tags finds the same commit. With its head the tagged commit, the release PR's squash tells the changesets apart with no code of its own. The tag comes before the PR since it fixes what ships, the last candidate's content under the final versions, and `latest` follows at the next push to `main`, since only the release-tag workflow writes it (PRJ-004).

While a line runs, a release PR merged into `main` would have the release-tag workflow tag what no candidate held, so with the cut's refusal of a second line, a line ends only with its final release, and only its own candidates and final release ship while `main` takes changes. The merge is the last command that can refuse such a PR before `main` holds it.

The final release ships the source commit's tree, and its PR brings that release's versions into a `main` that has moved since. A script merged since into a folder the release ships never runs for a project at that release, since its tag lacks the script and `main` then records the folder as released. An edit to a changeset the release consumes meets the PR's deletion of it. A range that excludes a version the release writes was never checked, since the broaden and the range checks read the source commit's tree. Such a change cannot be mended on `main` before the PR merges: PRJ-002 D1 keeps `requires_backbone` off a branch, and lets it correct a `requires_capabilities` range only to admit the version the tree carries. Nor does a later check find the script, since the checks of a change read only the scripts it adds, and a folder at or below the recorded version reads as released. So the cut refuses while another candidate can still take the change, and the merge, after the tag, while a revert can. The merge refuses a squash that would not apply cleanly too, since the PR's head is the tagged commit and takes no fix.

A commit that records a candidate could reach a branch, by hand or by a mistaken run. `pkit release check` catches it on every pull request, and `pkit release merge` at the one command that merges a release PR. Candidates are cut only in the methodology's source repository (point 2), the one ADR-059's test finds. Bound anywhere else, these checks would refuse an adopter's own component at a pre-release version, or an adopter's default branch that a tester moved to a candidate, and an adopter whose own tags include one such as `v1.0.0rc1` would seem to run a line.

**Point 4, ranges.** COR-030 gates on whether an installed or moving version satisfies a range: every gate asks whether one version, installed, shipped or named as a target, falls in a range, and none picks a version from a list. PEP 440 leaves pre-releases out only when an installer picks among versions, and lets in one already present or asked for. So the reading takes COR-030's ranges as PEP 440 means them, and a caller that picks keeps its own filter. The explicit flag also fixes a reading that `packaging`'s default has moved on across its releases.

**Point 5, migrations.** The upper bound by minor gives a candidate its final release's folder, since it previews that release. The lower bound in PEP 440 order makes the next move run that folder again, whole, with every script added since. Read without its pre-release, `0.55.0rc1` equals `0.55.0`, so a component's move from its candidate to its final release would show as no move; dropping the local segment keeps a local version reading as the version it is local to.

The migration rule asks each script to be safe to run again ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)). On the path through candidates that is not enough, since an earlier script runs again over a later script's output, which may undo it. Add-only keeps each later folder an extension of the earlier one: it runs the earlier folder's scripts first, in the same order. A folder idempotent as a whole changes nothing when it runs again over its own output. So each move through candidates reaches the state the later folder reaches alone, and the final release's folder reaches the state of the path without candidates. A correction numbered last is safe where the order of scopes would put it first, since the final release ships its last candidate's folders (point 3), so every path runs a folder in the order a candidate shipped it. The runner reads no manifest between a folder's scripts: it lists them before the first, and writes the completion after the last, by an edit of its own line (ADR-065 point 3).

Review reads each script alone, and misses how two scripts of one folder meet, which running the folder twice over the fixtures shows. CI runs the test on each pull request against `main` as it was then, so two pull requests that each pass may still fail together, and the pre-release run runs it on the tree the cut ships (point 9). Only a record of the scripts that ran would give "once" on both paths. A tester who follows every candidate opts into reruns, which the folder rule makes safe, and the notes warn of a restored default. The maintainer waives "once each" for testers, and the path adopters take keeps it.

COR-010 needs no change. It names semantic versioning, and `2.0.0rc1` is PEP 440's spelling of semver's `2.0.0-rc.1`, with the same precedence. Its folders cover a minor's patches, and a candidate is no patch: it carries its final release's folder. The folder rule asks more of a candidate's folders than COR-010 asks of each script, and realises COR-010's idempotence for a folder that runs more than once. Nor does the transition record (COR-059): its point 1 makes a release a backbone version with its components' versions, which a candidate is, its point 6 runs the next transition from the recorded completion, which the window reads in PEP 440 order, and its point 9 holds, since no candidate number is reused.

**Point 6, the pin.** The router routes a pin to the tag `v<pin>` as written, so only PEP 440's normal form reaches a candidate's tag. A pin that names a candidate is a project already on the line, whose plain upgrade must finish a move to that pin.

**Point 7, the guard.** `--pre` and the bypass are a person asking for the move at hand. A pin's code targets its pin or the latest release, and under `--pre` hands a move to a candidate over to the candidate's own code, run through the bypass, so the guard fires only where a candidate runs an upgrade nobody asked it to, such as a candidate installed as the machine's tool. An `init` refuses too, since such a tool would otherwise install each new project at a candidate. An unpinned project at a candidate meets the guard of the candidate's own upgrade, and sync's guard under every older tool. A pin keeps it on the candidate's code through the router, whatever tool is installed, which is also why `pkit unpin` refuses on a candidate.

**Point 8, the way in and on.** Each move runs its target's code: a raise runs the target's upgrade (ADR-049 point 5), and a migration reaches the running pkit (ADR-065 point 14). So only code from the first candidate on has to read a candidate, and no release before it changes. The first hop needs nothing of the release the project leaves. The bypass is the router's own escape, the one a raise runs through (ADR-049 point 5), and typing it is the operator's consent. A plain upgrade stays the channel every adopter takes, and never meets a candidate. The final release orders above its candidates. A tester asks with `--pre` on each move, so a later candidate's changes come only when asked for, and nothing records that a project follows a line. One name, `--pre`, cuts a candidate and moves a project to one, so it is learned once. The hand-over moves the one project, as a raise does, and the tool stays at the latest release. A withdrawn candidate staying the newest until the next is cut is accepted, since the lookup keeps the one source ADR-063 point 1 reads, a remote's tags, which needs nothing of the host's own interface.

**Point 9, the release workflow.** No schedule starts the release workflow, since its run that ends a line pushes the final release's tag before any pull request. A pre-release run merges nothing, so it pushes the candidate's tag itself, where the release-tag workflow tags only after a merge, and pushing the tag alone keeps the commit off every branch (PRJ-004). The folder test reads the plan, which the source commit's tree gives and a candidate's tree, which records pre-releases, does not. The build and `pkit --version` need the candidate's versions, so they run on its commit, after the cut. Either failing stops the run before the tag fixes the candidate's content for good. Once a final release's tag is pushed no line runs, and every other final release is tagged on the commit its PR leaves on the default branch, so a release tag above the version the default branch records marks a final release whose PR has not landed. `main` never records a candidate, so the wheel's pattern reads nothing new there. A changelog section can pass what a Release's body, a pull request's body or one argument holds. A file carries any length, and a link to the section at the tag shows all of it.

### Alternatives considered

- **A candidate's versions written on `main`.** Rejected: `main` would record a pre-release with every changeset pending, every reader of its versions would meet it, and the next candidate or the final release would be computed from a candidate (PRJ-002).
- **A candidate's components at release versions.** Rejected: two candidates would carry one component version for two contents, and a move between them would run no migration (PRJ-002).
- **A candidate's floors raised as pre-releases,** such as `>=2.0.0rc1`. Not taken: testers would run the final release's floors, but D4's rule that a floor names a release version would change, and every floor writer would learn pre-release values (PRJ-002).
- **A candidate read as its final release,** so `2.0.0rcN` reads as `2.0.0` and the candidate writes the final release's floors. Rejected: it misreads a range that names a pre-release, such as `>=2.0.0rc2`, which package validation accepts, and an adopter's `0.5.0rc1` in `requires_capabilities`.
- **A record of the scripts that ran, so each runs once on every path.** Rejected, as the transition record rejects such a ledger (COR-059): it drifts from the files, and conflicts across branches.
- **Edits kept open for scripts a candidate shipped.** Rejected: an edited component script would run over its earlier version's output, which the migration rule's contract for a component's script does not cover (COR-010), so that rule would change.
- **The add-only rule alone, with each script idempotent and no rule for the folder.** Rejected: the path through candidates could end where the path without them does not.
- **`pkit pin <candidate>` as the way in from a release with no `--pre`.** Rejected: it runs under the project's release, whose pin refuses a candidate.
- **`pkit pin <later candidate>` as the way within a line.** Not taken: a tester would look up each candidate's number, where `--pre` finds the newest.
- **`pkit upgrade` follows newer candidates of its pin's line.** Not taken: a project on a candidate would move to a later one unasked.
- **A flag named `--candidate`.** Not taken: the maintainer's one name (Context).
- **No guard on upgrade.** Rejected: a candidate installed as the tool would move each unpinned project it upgrades onto the candidate, and pin it there.
- **The guard before ADR-063's tool step.** Rejected: a tool installed at a candidate would refuse on its own bundle, and never update itself once the final release ships.
- **A candidate installed as the machine's tool, as the way in or by `--pre`.** Rejected: every unpinned project on the machine would sit behind the guard.
- **A branch for each candidate,** such as `release/v2.0.0rc1`. Rejected: a branch can move under one version (PRJ-004, ADR-065 point 12), and it would carry both markers by which `pkit release merge` accepts a release PR.
- **A workflow of its own for candidates.** Not taken: the maintainer's one path (Context).
- **A "final" input of its own,** so a run with neither input refuses while a line runs. Not taken: such a run may cut only that line's final release (point 3), so a second input would name what the absence of the first decides. The cost is that a run started without the input by mistake ships the final release, since it pushes the tag before any pull request.
- **Each candidate's section on `main` as well, under the final release's.** Rejected: each candidate's entries would appear once for each candidate.
- **A candidate's notes in its Release alone,** with no section in its tag's `CHANGELOG.md`. Not taken: a tester reading the installed tree would find no notes for what they run.
- **Candidates cut by the `version` commands,** `pkit version bump --pre rc` and `promote`. Rejected: they write `.pkit/VERSION` alone, consume no changeset, move no component and write no changelog, so a transition would run none of the changed components' migrations. Their retirement is a surface change decided apart.
- **The final release cut from `main`'s head, with `main` held at the last candidate's source commit until its PR lands.** Rejected: `main` would be frozen while candidates are tested (PRJ-002).
- **The final release cut from a later commit a person judges safe.** Not taken: a change judged safe ships untested all the same (PRJ-002).
- **The final release's tag cut on its PR's merge commit,** by the release-tag workflow. Rejected: the tag would take what `main` gained since the source commit, which no candidate held.
- **A release PR built on `main`'s head, carrying the final release's versions,** in place of the tagged commit. Not taken: a check of its own would have to hold its versions and changelog equal to the tag's, where the tagged commit holds them by construction.
- **The final release's PR merged with no check of its head.** Rejected: a release PR opened before the final release, or a commit pushed onto its branch, would put on `main` a state the tag does not hold, from which the next release would be computed.
- **A change that cannot wait mended on `main` after the final release's PR merges.** Rejected: nothing would then run the script for a project at that release, the PR's deletion would meet the edited changeset, and `main` would hold a range no release step checked.
- **The refusal of a pre-release on the default branch as a check of project-kit's own CI,** outside the core commands. Not taken: `pkit release merge` holds it at the merge whether or not CI ran, and a check apart from the release step would split one rule about what `--pre` writes across two homes.

## Implications

- **Records refined in place,** each with a pointer here:
  - ADR-065 point 4: places the hand-over of `--pre` and the refusal of a candidate nobody asked for among upgrade's own checks, and reads step 4's lower bound in PEP 440 order.
  - ADR-065 point 8: gains a row for a recorded target that is a candidate above the running pkit.
  - ADR-065 point 9: its hand-over takes the newest release, candidates included, under `--pre`, and its refusal names `pkit upgrade --pre` where the recorded target is a candidate.
  - ADR-065 point 12: counts a candidate tag as a tagged install.
  - ADR-049: the pin's token takes a candidate in PEP 440's normal form, the refusal of any other pre-release and of build metadata rests on the router's route to the tag `v<pin>`, a pin that names a candidate asks for candidates, `pkit upgrade --pre` raises a pin to the newest release, candidates included, and `pkit unpin` refuses in a project whose manifest records a candidate.
  - ADR-064: `--no-pin` is refused on a move to a candidate, and so is `pkit unpin` on a candidate. An `init` run by a candidate refuses unless routing is bypassed, and pins.
  - ADR-063: its bullet on pre-release tags says the tool step installs no candidate, even under `--pre`.
- **PRJ-002 and PRJ-004 hold the policy,** refined in the same change, and this record cites them for it.
- **No core record changes** (point 4; Rationale, point 5).
- **Docs:**
  - the release README: `--pre` and the wording of each refusal, the counter, the test of a running line, the final release's cut from the source commit and its release PR, the refusals of what cannot wait at that cut and at the merge, the merge's check, the release workflow's "pre-release" input, how a run resumes, and the notes
  - the lifecycle reference: the window in `upgrade-flow.md`, "The steps of a transition", the lower bound in `migrations.md`, "Which version a migration targets", and the add-only rule, the folder rule and the order a correction takes in `migrations.md`, "Script contract", stated for whatever ships pre-releases
  - the migration-authoring skill: the add-only rule, the folder rule and the order a correction takes, in the same terms
  - the CLI reference: `pkit pin`, `pkit upgrade --pre`, upgrade's guard and `--no-pin`, `pkit unpin` on a candidate, a candidate's `init`, and `pkit release plan --pre` and `apply --pre`, with their refusals
  - each candidate's notes: the way in, the way on after a move cut short, how a tester works on a branch, and that a rerun may restore a removed default
- **Task [#2211](https://github.com/aleskalfas/project-kit/issues/2211)** builds the points.
- **No migration.** No installed state changes shape. A pin that names a candidate has the pin file's format, and the behaviour lives in the code that runs each move.
- **Stands on these records, all accepted:** COR-010, COR-030, COR-054 and COR-059; ADR-049, ADR-059, ADR-063, ADR-064 and ADR-065; PRJ-002 and PRJ-004, as refined in the same change.
