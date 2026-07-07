# Changelog

## 1.142.0 — 2026-07-07

### Added
- Releasing a capability now keeps its compatibility claim current: the release step widens the released component's supported backbone range to cover the version it was released under, and a new pre-sharing check reports whether a capability is ready to be shared for another repository to consume. ([#494])
- **project-management 0.48.0** — The merge paths (`done-work` and `merge-pr`) now enforce a CI-status gate in front of the merge (#498): the PR's `statusCheckRollup` must be green, else the merge is refused, naming the failing or still-pending checks. Closes the hole where an APPROVED reviewer verdict merged a PR whose CI was red (PR #496). A non-green check is bypassable-with-audit via a dedicated `--bypass-ci "<reason>"` flag on both scripts, which posts an audit comment to the PR before merging; a non-green check with no `--bypass-ci` is a hard refuse. The CI override is deliberately separate from `done-work`'s general `--bypass` (approval gate) so overriding a flaky reviewer never silently lands a red CI — a merge blocked on both gates needs both flags.

### Changed
- Remediation for PR #496: the COR-041 + ADR-040 decision landing touched the backbone decisions tree with no user-facing surface (design-ahead — the externally-sourced mechanism ships in a later implementation PR), so it is declared `none`. No changelog line.
- The changeset-guard error now points a decision-only PR to the right choice — a `none` changeset for a design-ahead decision, or a real changeset for a self-executing rule change.

[#494]: 494

## 1.141.1 — 2026-07-05

### Fixed
- Filing an issue or PR from a project-kit source checkout no longer posts a spurious version-drift note — the tool now reports its version as the checked-out tree's version. ([#489])

[#489]: https://github.com/aleskalfas/project-kit/pull/489

## 1.141.0 — 2026-07-05

### Added
- Format problems in changeset and changelog files — an unknown category, an empty or malformed entry, or a broken changelog heading — are now caught before they land. ([#478])
- Completing a release PR now has its own checked command, so finishing a release no longer needs a hand-run raw merge.
- Each release now publishes a GitHub Release whose page shows that version's changelog, so you can see what changed at a glance. ([#485])

### Changed
- The changelog now follows Keep a Changelog and Common Changelog — plain, user-facing entries grouped by category, newest first. ([#477])

[#477]: https://github.com/aleskalfas/project-kit/pull/477
[#478]: https://github.com/aleskalfas/project-kit/pull/478
[#485]: https://github.com/aleskalfas/project-kit/issues/485

All notable changes to project-kit from `1.140.0` onward are recorded here,
newest first, following [Keep a Changelog](https://keepachangelog.com) with
[Common Changelog](https://common-changelog.org) language.

**Earlier history (before `1.140.0`) is not tracked per version** — see the git
tags and commit log for the full record. A few notable milestones from that
period:

- The declared, release-driven versioning system: version bumps are declared in
  changeset files and applied once at release time, keeping each tier's version
  independent and safe under concurrent work.
- The project-management workflow: file, validate, and move work items through a
  single validated command surface, with a review gate before anything merges.
- The adversarial review stack: separate critic, architect, methodology, and
  convention reviewers that check work before it lands.
- Steadier tooling: more robust parsing of reviewer verdicts and more faithful
  issue filing, among many smaller fixes.

## 1.140.0 — 2026-07-04

### Changed
- pkit now automatically runs the version each project pins, so one install works everywhere. ([#465])

### Removed
- The separate router shim — pkit installs one binary for everyone now. ([#465])

[#465]: https://github.com/aleskalfas/project-kit/pull/465
