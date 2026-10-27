---
id: ADR-072
title: A release candidate lives only in its tag, and reaches only a project that asks for it
status: proposed
date: 2026-10-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a release candidate, such as `2.0.0rc1`, lets anyone test the next final release before it ships, and nobody receives one unless they ask. The release step computes the versions that final release would write, from `main`'s head and its pending changesets, and writes each with the suffix `rcN`. It writes them on a commit that only the candidate's tag holds, and consumes no changeset. So `main` only ever records release versions, and the final release that ends a line of candidates is the ordinary release from `main` ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) D5).

Everything that reads a version takes a candidate as the pre-release it is, ordered below its final release, and a range admits it wherever its bounds do. `latest`, the tool's own update and a pinned project's upgrade never pick one. A move to a candidate runs its final release's migration folders, and the next move runs them again. So a script a candidate shipped is never edited or removed, and each folder a candidate ships changes nothing when it runs again over its own output.

A project moves to a candidate by running the candidate's own upgrade through the router's bypass, or, from a release whose `pkit pin` takes a candidate, by pinning one. Any other upgrade to a candidate refuses, and a move to a candidate always pins the project. A workflow run on request checks the default branch, cuts the candidate, builds it, pushes its tag alone and publishes its notes as a pre-release.

This record realises PRJ-002 D5, and the candidate tag of [PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md), in project-kit's code. It refines in place the records of the pin (ADR-049), the tool's update (ADR-063), the default pin (ADR-064) and the transition (ADR-065), each with a pointer here.

## Context

#2211 asks how the release step cuts `2.0.0rc1`, a later candidate and the final release `2.0.0`. The maintainer wants to test 2.0.0 before publishing it, and expects changes after the first candidate. On 27 October 2026 the maintainer decided that a candidate consumes no changeset. Each candidate is computed from the pending changesets and leaves them pending, and the final release consumes them once.

PRJ-002 D5 sets the policy that follows, and defines the terms this record uses, from a *release version* and a *final release* to a candidate's *source commit*. PRJ-004 adds the *candidate tag*, `v<major>.<minor>.<patch>rc<N>`, and the pre-release Release. Neither says which part of the code does what, which this record settles.

The code on `main` at `dc195bf6b` reads a pre-release in some places and refuses it in others. A candidate cut there fails before anyone could install it, and an upgrade to one fails halfway.

- **The build.** The wheel's version pattern takes `X.Y.Z` alone, so no wheel builds from a tree that records a candidate.
- **The release step.** Its next version drops the suffix before it bumps, so from a tree at `2.0.0rc1` a major gives `3.0.0`. Its floor check refuses a `release` floor on a pre-release backbone, and its check of the migration folders raises on one. Its changelog heading takes no candidate, and it creates every Release as a plain one, which GitHub would show as the latest.
- **The migration runner.** It raises on a candidate target, after the content is copied. Its comparisons read `2.0.0rc1` as `2.0.0`, so a later candidate, or the final release, runs none of the candidate's folder again.
- **The migration checks.** `check-diff` and the migration stamp refuse a tree that records a candidate. Under this record no tree they read records one: CI reads trees bound for `main`, and the candidate workflow runs its checks before the cut (point 9).
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

**A release candidate holds the versions the next final release would compute from `main`'s pending changesets, each with the suffix `rcN`, on a commit that only its tag holds. Every reader of a version reads a candidate as the pre-release PEP 440 orders below its final release. Only a project that names a candidate, by its pin or by running the candidate's own code through the bypass, moves to one.**

The points that follow:

- **Points 1 to 3** say how the release step cuts and numbers a candidate, which states refuse a cut, and how the final release follows its line.
- **Point 4** says how a range is read.
- **Point 5** says which migrations a move to a candidate runs.
- **Points 6 to 8** say how a pin names a candidate, how an upgrade guards against one nobody asked for, and the ways into a line and on.
- **Point 9** says how a candidate is built and published, and how notes past the host's caps are published.

### 1. A candidate is the final release's own plan, with the suffix added where the step writes

- **The mode is explicit.** `pkit release plan` and `apply` take a candidate mode, and nothing infers it. Without it they plan and cut the final release, as PRJ-002 D3 sets.
- **One plan.** A candidate's plan is the plan the final release would compute from the default branch's head ([COR-054](../../../.pkit/decisions/core/COR-054-default-branch.md)) and the pending changesets. It carries release versions. Every check of the plan reads them, the checks of floors, ranges and migration folders among them, so a cut is refused wherever the final release would be.
- **The suffix is added at the write.** Where the step writes the backbone's version and each version the final release would move, it writes `X.Y.ZrcN`, with one `N` for all of them. A component the final release would not move keeps its version.
- **What else it writes:** the ranges a candidate's tree carries, as PRJ-002 D4 sets them, and the changelog section PRJ-002 D5 sets, headed by the candidate's version.
- **Where it writes.** It deletes no changeset and writes nothing to `main`. It makes its commit on top of the default branch's head, on no branch, and only the candidate's tag holds that commit (PRJ-002 D3). That head is the candidate's source commit.

### 2. A candidate's number comes from the remote's tags, and five states refuse a cut

- **The counter.** `N` is one past the highest candidate tag `vX.Y.ZrcK` the remote holds for the final release's backbone version `X.Y.Z`, and 1 where it holds none. The step reads the remote's tags, never a clone's, and refuses where it cannot read them. No candidate tag is moved or deleted (PRJ-004), so one past the highest reuses no number, as PRJ-002 D5 requires.
- **The step refuses a cut, before it writes anything,** in five states:
  - the final release would move no backbone version. A candidate is a backbone tag, so this also refuses a cut in an adopter's repository, whose release moves only its own components.
  - a component's version in the cut is below its version in the line's previous candidate, whether or not the cut moves it
  - the final release's tag `vX.Y.Z` exists, so its line has ended
  - the default branch's head is the last candidate's source commit, and that candidate is not withdrawn, so the cut would tag the same content again
  - the step runs anywhere but the default branch's head
- **The release README** holds the wording of each refusal.

### 3. The final release is cut only on the last candidate's source commit, and the default branch holds release versions alone

- **A running line.** Whether a line runs is PRJ-002 D5's test. Every check that asks it reads the remote's tags, as the counter does, and refuses where it cannot read them.
- **The final release's source.** While its line runs, `pkit release plan` and `apply` refuse the final release unless the default branch's head is the last candidate's source commit. They refuse it too while the last candidate is withdrawn, which a mark on its Release says. After any other merge, or such a withdrawal, another candidate comes first (PRJ-002 D5).
- **The merge's check.** `pkit release merge` refuses the final release's PR unless the PR is one commit whose parent is the last candidate's source commit, and the default branch's head is that commit when it merges. Otherwise a release PR opened before the last candidate, or a commit pushed onto its branch, would ship versions or code no candidate held.
- **The pause.** The release-PR workflow's scheduled run cuts nothing at a version whose line runs (PRJ-002 D5).
- **The default branch holds release versions alone.** `pkit release check`, which CI runs on every pull request, refuses a tree bound for the default branch whose `.pkit/VERSION` or component version is a pre-release. `pkit release merge` refuses a release PR whose tree records one. Neither reads a candidate's own tree, and both refuse only in the methodology's source repository ([ADR-059](ADR-059-methodology-source-repository.md)), the one place candidates are cut (point 2).
- **The changelog lint** reads a candidate's heading, as `publish-notes` does (point 9).

### 4. Every range is read with its pre-releases admitted

- **The reading.** The range reader, which every check of a range calls, reads a range with pre-releases admitted, `packaging`'s `prereleases=True`. So `>=1.144.0,<2.1.0` admits `2.0.0rc1` under every `packaging` release.
- **Ordering keeps its exclusions.** `>=2.0.0` refuses `2.0.0rc1`, which sorts below it. `<2.0.0` refuses it too, since PEP 440 keeps a version's own pre-releases out of `<` that version.
- **A caller that picks keeps pre-releases out itself.** A caller that picks a version from a list, rather than judging one, leaves pre-releases out before it reads a range. The lookups of the latest release do so (PRJ-004, ADR-063 point 1).
- **A reading for the whole project.** It changes how every range is read, an adopter's own `requires_capabilities` among them, and not only a candidate's. A changeset says so.
- **It realises the range gates of [COR-030](../../../.pkit/decisions/core/COR-030-capability-dependencies.md), and changes nothing COR-030 decides.** Every gate asks whether one version, installed, shipped or named as a target, falls in a range. None picks a version from a list, the one case where PEP 440 leaves pre-releases out.

### 5. A candidate runs its final release's migration folders, and has not finished them

- **The window.** A transition runs each folder above its lower bound in PEP 440 order and at or below its target by minor. A move to `2.0.0rcN` runs `2.0.0/`, and a completion at `2.0.0rcN` sits below `2.0.0/`, so the next move runs that folder again, whole. Each component's folders are read the same way, from the version its manifest records (ADR-065 point 4).
- **Whole public versions.** Wherever the code compares a recorded version with a bundled one, it compares public versions, the pre-release kept and a local segment dropped. So `0.55.0rc1` to `0.55.0` is a move, and `0.6.0+x` reads as `0.6.0`. For every release version, a test over every shipped folder holds the window and the comparisons to what they give on `main` at `dc195bf6b`.
- **A migration a pre-release shipped is add-only.** A script that the backbone or a component shipped in a pre-release is never edited, renumbered or removed. A correction is a new script, numbered after every script its folder holds. So each later pre-release's folder, and the final release's, runs the earlier folder's scripts first, in the same order.
- **A folder a pre-release ships is idempotent as a whole.** Run again over its own output, it changes nothing. With the add-only rule, the path through pre-releases then reaches the state the path without them reaches. A test, which the candidate workflow runs on the source commit before each cut (point 9), takes from the plan the folders the cut will ship, the backbone's and each moved component's. It runs them twice over the migration fixtures, and holds the second run to no change.
- **Where the two rules bind.** They bind the migrations of whatever ships pre-releases, the backbone or a component. Here that is the backbone and each component shipped with it, whose candidates are their pre-releases. A component no pre-release ships, such as an adopter's own, meets neither rule, and the lifecycle README's script contract and the migration-authoring skill state both in these terms.
- **Each script runs once on the path without candidates.** A project that follows every candidate runs a script of its final release's folder on each move, up to once for each candidate and once more at the final release. A rerun may restore a default the project removed after the script first ran, and each candidate's notes say so, as a release's do (ADR-065 point 5). A project that moves from the latest release to the final release runs the window it would run if no candidate existed.

### 6. A pin may name a candidate, and is the project's consent to candidates

- **From the first candidate on,** `pkit pin` takes a candidate in PEP 440's normal form, `X.Y.ZrcN`, beside `X.Y.Z`. It refuses another spelling, such as `2.0.0-rc.1`, and names the normal form, since the router routes `v<pin>` as written. It orders the target by PEP 440, and refuses an older version as it does for a release version (ADR-049 point 3).
- **Consent.** A pin that names a candidate is the project's consent to candidates. Upgrade's guard reads only that the pin names one (point 7).
- **Within the line.** A project at one candidate moves to a later one with `pkit pin <later candidate>`, which raises through the bypass as for any newer version (ADR-049 point 5).
- **Upgrade does not follow candidates.** A pinned project's upgrade raises only to the latest release, which is never a candidate (ADR-065 point 9). On a pin that names a candidate, its message names the two ways on: `pkit pin` to a later candidate, and `pkit upgrade` once the final release ships.

### 7. An upgrade or an `init` refuses a candidate nobody asked for, and a move to a candidate always pins

- **The guard.** An upgrade refuses when its target is a candidate, the project's pin names none, and routing is not bypassed. It writes nothing. Its message names the ways in of point 8, and, where the running pkit is the installed tool, the install of `latest`.
- **Where it runs:** among upgrade's own checks, after ADR-063's tool step and before the transition's first step (ADR-065 point 4). A pin's code targets its pin or the latest release, so the guard fires only where a candidate runs an upgrade nobody routed or bypassed to it, such as a candidate installed as the machine's tool.
- **A move to a candidate always pins.** Such a move ends by pinning the project at the candidate, and `--no-pin` is refused on it ([ADR-064](ADR-064-upgrade-pins-by-default.md) point 2).
- **An `init` run by a candidate** refuses unless routing is bypassed, as the guard does, and pins the project it installs at the candidate (ADR-064 point 3). An interrupted such `init` is finished by the candidate's upgrade through the bypass.
- **A target at a release version never meets the guard,** so an adopter who never takes a candidate never meets it.

### 8. The way into a line, and the way on

- **The way in** is the candidate's own upgrade, through the router's bypass, fetched from the distribution URL compiled into the tool (ADR-063 point 2) at the candidate's tag:

  ```
  PKIT_NO_ROUTE=1 uvx --from <distribution URL>@v<candidate> project-kit upgrade
  ```

  From a 1.x release to the first candidate of 2.0, `<candidate>` is `2.0.0rc1`. The command runs the candidate's code in its own process, moves the project and pins it at the candidate (point 7).
- **The pin, from a release whose `pkit pin` takes a candidate.** From the first candidate's line on, `pkit pin <candidate>` is a way in too, and raises through the bypass (point 6). A 1.x release's `pkit pin` refuses a candidate, so from 1.x the bypass command is the way in.
- **After an interrupted move into a line,** the way on is the command that started it, run again, then `pkit upgrade`. Each candidate's notes say so, since the release the project left may name a `pkit upgrade` that cannot finish the move alone.
- **After an interrupted move from one candidate to a later one,** the project's recorded target is a candidate ahead of a pin that names a candidate. Code from the first candidate on names `pkit pin <that candidate>`, which freezes the project at the version its content records, then `pkit upgrade` (ADR-065 point 8). No latest release finishes such a move while its line runs (ADR-065 point 9).

### 9. A candidate publishes from a workflow of its own, and notes past the host's caps are linked

- **A workflow run on dispatch only.** Before the cut, it runs the checks CI runs on a pull request, on the default branch's head, where nothing records a candidate. It then runs the step's candidate mode there, and commits the result on top of that head, on no branch. After the cut, it builds the wheel from the candidate's commit and runs `pkit --version` from it. Only then does it tag that commit, push the tag alone and publish the notes.
- **Runs kept apart, and resumed.** One concurrency group keeps two runs apart. A run that pushed its tag but not its notes resumes by publishing the notes alone. Nothing merges, so the release-tag workflow does not run.
- **The build.** The wheel's version pattern reads PEP 440's pre-release form, so a tree that records a candidate builds. `main` never records one, so the pattern reads nothing new there.
- **A pre-release Release.** `pkit release publish-notes` reads a candidate's heading, as the changelog lint does, and marks its Release a pre-release. So GitHub never shows a candidate as its latest release, and `latest` stays on the latest release (PRJ-004).
- **Notes through a file, linked past the cap.** `publish-notes` passes the body as a file, never as one argument. Where a section exceeds what a Release's body holds, the body is a short summary that links the section in `CHANGELOG.md` at the version's tag, for a final release as for a candidate. The release PR's body links the section the same way, past a pull request's cap.
- **The final release** is the ordinary release PR from the default branch, merged by `pkit release merge` (point 3). The release-tag workflow tags it, publishes a plain Release and moves `latest`.

## Rationale

**Why a candidate's versions live in its tag alone.** PRJ-002 gives the policy reason, "Why a candidate's versions live only in its tag". The code's side is that the release step needs no arithmetic from a candidate, and no reader of `main`'s versions meets one. `check-diff`, the migration stamp, the rule of which folders count as released, the folder-prediction warning and `uv sync` on `main` read nothing new.

**Why the suffix is added at the write.** The plan's checks know release versions alone. Added at the write, the suffix leaves every check as it is, and a cut is refused exactly where its final release would be. A plan at candidate versions would teach every check a pre-release, the floor check and the folder check among them.

**Why each moved component carries the suffix.** A transition tells a move by comparing versions (ADR-065 point 2). Two candidates at one component version for two contents would show no move, and run none of the migrations added in between (PRJ-002, "Why each moved component carries the suffix").

**Why the counter, and every test of a running line, reads the remote.** A clone may lack a tag cut elsewhere. A cut from it would reuse a number, and a test of the line read from it could miss the line and let a final release go out untested. A reused number lets one version name two contents, and sync's guard, which compares versions, is sound only where each version names one content (the transition record's point 9, [COR-059](../../../.pkit/decisions/core/COR-059-version-transition.md)).

**Why a cut refuses a component below the line's previous candidate.** A tester follows a line from candidate to candidate. A component older in the next candidate than in the one before would meet ADR-065 point 7's refusal of a component bundled older, at the tester's next move. That holds whether the cut moves the component or leaves it at a release version below the previous candidate's.

**Why a candidate needs a backbone move.** A candidate is a backbone tag (PRJ-004), and the bypass and the pin reach it through that tag. A release that moves only components cuts no tag (ADR-065 point 12), so its candidate would have nothing to install.

**Why the final release's source is checked in plan, apply and merge.** A change merged after the last candidate would ship untested (PRJ-002 D5). Checked in `plan` and `apply`, the refusal comes before anything is written. Those two cannot see a release PR opened before the last candidate, or a commit pushed onto its branch, so `pkit release merge` checks the PR's one commit and its parent. After the merge, a refusal would come with the final release on `main`, too late to keep it from shipping.

**Why the default branch is held in two places.** A commit that records a candidate could reach a branch, by hand or by a mistaken run. `pkit release check` catches it on every pull request, and `pkit release merge` refuses it at the one command that merges a release PR.

**Why that refusal binds only in the methodology's source repository.** Candidates are cut only there, since the step refuses a cut whose final release moves no backbone version (point 2). So the refusal guards what only that repository's release step makes. Bound anywhere else, it would refuse an adopter's own component at a pre-release version, or an adopter's default branch that a tester moved to a candidate. Keyed to ADR-059's test of the source repository, every adopter's tree is untouched.

**Why `prereleases=True` realises COR-030's range gates, and changes none of them.** COR-030 gates on whether an installed or moving version satisfies a range. PEP 440 leaves pre-releases out only when an installer picks among versions, and lets in one already present or asked for. Every caller of the range reader judges one such version, so the reading takes COR-030's ranges as PEP 440 means them, and a caller that picks keeps its own filter. The explicit flag also fixes a reading that `packaging`'s default has moved on across its releases.

**Why a candidate runs its final release's folder, and has not finished it.** The upper bound by minor gives a candidate its final release's folder, since it previews that release. The lower bound in PEP 440 order makes the next move run that folder again, whole, with every script added since. Running only the scripts a candidate did not run would need a record of the scripts that ran, which the transition record rejects (COR-059, "Alternatives considered").

**Why the add-only rule, and a folder idempotent as a whole.** The migration rule asks each script to be safe to run again ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)). On the path through candidates that is not enough, since an earlier script runs again over a later script's output, which may undo it. Add-only keeps each later folder an extension of the earlier one, and a folder idempotent as a whole changes nothing when it runs again over its own output. So each move through candidates reaches the state the later folder reaches alone, and the final release's folder reaches the state of the path without candidates.

**Why a test holds the folder rule.** Review reads each script alone, and misses how two scripts of one folder meet. Running the folder twice over the fixtures shows it. The suite runs on every pull request, and the candidate workflow runs CI's checks before each cut (point 9).

**Why the migration rule needs no change (COR-010).** It names semantic versioning, and `2.0.0rc1` is PEP 440's spelling of semver's `2.0.0-rc.1`, with the same precedence. Its folders cover a minor's patches, and a candidate is no patch: it carries its final release's folder. The folder rule of point 5 asks more of a candidate's folders than COR-010 asks of each script, and realises COR-010's idempotence for a folder that runs more than once, so COR-010 stands.

**Why the transition record needs no change (COR-059).** Its point 1 makes a release a backbone version with its components' versions, which a candidate is. Its point 6 runs the next transition from the recorded completion, which the window reads in PEP 440 order. Its point 9 holds, since no candidate number is reused (PRJ-002 D5).

**Why each script runs once only on the path without candidates.** Only a record of the scripts that ran would give "once" on both paths. A tester who follows every candidate opts into reruns, which the folder rule makes safe, and the notes warn of a restored default. The maintainer waives "once each" for testers, and the path adopters take keeps it.

**Why whole public versions.** Read without its pre-release, `0.55.0rc1` equals `0.55.0`, so a component's move from its candidate to its final release would show as no move. Comparing the pre-release keeps the move. Dropping the local segment keeps the reading of a local version that `main`'s comparisons give.

**Why the way in is the candidate's own upgrade.** It needs nothing of the release the project leaves. From 1.x, `pkit pin` runs under the project's 1.x release, whose pin refuses a candidate, and no 1.x release changes, since each move runs its target's code. The bypass is the router's own escape, the one a raise runs through (ADR-049 point 5), and typing it is the operator's consent. From the first candidate's line on, a release's `pkit pin` takes a candidate, so the pin is a way in too.

**Why a guard, and why after the tool step.** Without it, a candidate installed as the machine's tool would move each unpinned project in which someone runs `pkit upgrade`, and pin it at the candidate. After the tool step, a tool installed at a candidate updates itself once the final release ships, rather than refusing on its own bundle. An `init` refuses for the same reason, since such a tool would otherwise install each new project at a candidate.

**Why a move to a candidate always pins.** An unpinned project at a candidate meets the guard of the candidate's own upgrade, and sync's guard under every 1.x tool. A pin keeps it on the candidate's code through the router, whatever tool is installed.

**Why upgrade does not follow candidates.** Each candidate is an opt-in of its own, and a later one may bring changes the tester has not chosen. Following a line is a later addition, if testers ask for it.

**Why a workflow of its own, on dispatch.** A candidate is cut on request (PRJ-002 D5), and nothing merges, so the release-tag workflow, which runs on a push to `main`, never sees it. Pushing the tag alone keeps the commit off every branch (PRJ-004).

**Why the workflow checks before the cut, and builds after it.** CI's checks read the default branch, where nothing records a candidate, so they run on the source commit, before the cut. The build and `pkit --version` need the candidate's versions, so they run on its commit, after the cut. Either failing stops the run before the tag fixes the candidate's content for good.

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
- **`pkit upgrade` follows newer candidates of its pin's line.** Not taken for 2.0: each candidate stays an opt-in. It is a later addition if testers ask for it.
- **No guard on upgrade.** Rejected: a candidate installed as the tool would move each unpinned project it upgrades onto the candidate.
- **The guard before ADR-063's tool step.** Rejected: a tool installed at a candidate would refuse on its own bundle, and never update itself once the final release ships.
- **A candidate installed as the machine's tool, as the way in.** Rejected: every unpinned project on the machine would sit behind the guard.
- **A branch for each candidate,** such as `release/v2.0.0rc1`. Rejected: a branch can move under one version (PRJ-004, ADR-065 point 12). It would also carry both markers by which `pkit release merge` accepts a release PR.
- **Each candidate's section on `main` as well, under the final release's.** Rejected: each candidate's entries would appear once for each candidate, the duplication the 27 October decision avoids.
- **A candidate's notes in its Release alone,** with no section in its tag's `CHANGELOG.md`. Not taken: a tester reading the installed tree would find no notes for what they run.
- **Candidates cut by the `version` commands,** `pkit version bump --pre rc` and `promote`. Rejected: they write `.pkit/VERSION` alone, consume no changeset, move no component and write no changelog. A transition would then run none of the changed components' migrations. Their retirement is a surface change decided apart.
- **The final release cut from a later commit a person judges safe.** Not taken: a change judged safe ships untested all the same (PRJ-002).
- **The final release's source checked in `plan` and `apply` alone.** Rejected: a release PR opened before the last candidate, or a commit pushed onto its branch, would ship versions or code no candidate held.
- **The final release's source checked after the release PR's merge.** Rejected: the final release is on `main` by then.
- **The refusal of a pre-release on the default branch as a check of project-kit's own CI,** outside the core commands. Not taken: `pkit release merge` holds it at the merge whether or not CI ran, and a check apart from the release step would split one rule about what the step's candidate mode writes across two homes. Scoped to the source repository, the core commands bind no adopter.

## Implications

- **Records refined in place,** each with a pointer here:
  - ADR-065: point 4 names upgrade's refusal of a candidate nobody asked for among its own checks, and reads step 4's lower bound in PEP 440 order. Point 8 gains a row for a candidate ahead of a pin that names a candidate. Point 9 says no latest release finishes a move to a candidate while its line runs, and point 12 counts a candidate tag as a tagged install.
  - ADR-049: the pin's token takes a candidate in PEP 440's normal form, the refusal's reason is the router's route to the tag `v<pin>`, and a pin that names a candidate is the project's consent to candidates.
  - ADR-064: `--no-pin` is refused on a move to a candidate, and an `init` run by a candidate refuses unless routing is bypassed, and pins.
  - ADR-063: its bullet on pre-release tags says when a pin names a candidate.
- **The policy is PRJ-002's and PRJ-004's,** refined in the same change. This record cites them for the policy it rests on.
- **No core record changes.** The migration rule and the transition record hold (COR-010, COR-059), as the Rationale says, and the range gates hold (COR-030), as point 4 says.
- **Docs:**
  - the release README: the candidate mode, its refusals, the counter, the test of a running line, the merge's check, the workflow and the notes
  - the lifecycle README: the window in "The upgrade flow", the lower bound in "Which version a migration targets", and the add-only rule and the folder rule in "Script contract"
  - the migration-authoring skill: the add-only rule and the folder rule
  - the CLI reference: `pkit pin`, upgrade's guard and `--no-pin`, a candidate's `init`, and the release step's candidate mode with its refusals
  - each candidate's notes: the way in, the way on after an interrupted move, and how a tester works with a candidate
- **What changes for an adopter who never takes a candidate:**
  - a range check admits a pre-release under every `packaging` release, which a changeset says
  - the window and the comparisons read whole public versions, which a test holds equal for every release version
  - a Release whose notes pass the cap shows a summary with a link
  - no scheduled release ships at a version whose line runs
  - unchanged: an adopter's own component at a pre-release version, which `pkit release check` and `pkit release merge` leave alone outside the methodology's source repository (point 3)
  - unchanged: the window from one final release to the next, and `latest`, the tool step and a pinned raise, which never pick a candidate
- **The rollout.** Only code from the first candidate on reads a candidate, since each move runs its target's code. So the first candidate ships every point but two, which the final release needs before it is cut. One is the release PR's link to its section, since the final release's notes are as large as the first candidate's. The other is the merge's check of the final release's source (point 3).
- **No migration.** No installed state changes shape. A pin that names a candidate has the pin file's format, and the behaviour lives in the code that runs each move.
- **Stands on these records, all accepted:**
  - COR-010, COR-030, COR-054 and COR-059
  - ADR-049, ADR-059, ADR-063, ADR-064 and ADR-065
  - PRJ-002 and PRJ-004, as refined in the same change
