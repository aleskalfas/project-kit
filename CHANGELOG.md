# Changelog

## 1.142.2 — 2026-07-08

### Added
- **project-management 0.49.0** — Add the `set-instance` command — set (or `--show` / `--clear`) this clone's opt-in, per-clone numeric instance id, the activation gate for instance ownership when one person runs several clones of a repo (DEC-035). The id is written to a git-ignored runtime file and read by the ownership lifecycle; a clone with no id set is unchanged. The claim / clash-guard / signed-listing behaviour that acts on the id follows in subsequent changes.

### Changed
- Documented COR-031's operational collision precedence in the CLI reference: register keeps the in-repo (incubated) copy on a kit-source name collision and surfaces that a kit-shipped version is available; sync leaves incubated untouched (D1). A doc clarification of already-decided behaviour (no COR change, no surface moved).
- **project-management 0.49.0** — Design landing for multi-instance ownership & coordination (DEC-043/044/045, ADR-041; reciprocal notes on DEC-035 and DEC-009) touched the project-management capability decisions tree with no adopter-observable surface — design-ahead, the implementation ships in later Features (#509-#513 under EPIC #508). Declared `none`. No changelog line.
- **project-management 0.49.0** — Feature #509 adds the instance-ownership marker seam (_lib/instance_ownership, ADR-041) and its substrate selector schema (instance-ownership.yaml, DEC-043). This is implementation-ahead: the seam and schema exist but no CLI command reads them yet (set-instance and the claim/handoff wiring land in Feature #510), so there is no adopter-usable surface to advertise. Declared `none`. No changelog line.

### Fixed
- `pkit sync` no longer silently downgrades a capability: when the source ships an older version than the one installed, sync now refuses — naming both versions and leaving the installed tree untouched — instead of overwriting newer work. `pkit sync --force` overrides the guard to downgrade deliberately (and loudly).
- `pkit capabilities register` no longer refuses an already-registered capability outright: it now branches on origin. An entry registered as `incubated-in-repo` is a clean no-op, and one registered `kit-shipped` — including the origin-unset default a manual registration leaves behind — is adopted in place: the origin is set to `incubated-in-repo` on the existing registry entry (no re-copy, no re-deploy) so `pkit sync` stops reconciling it against kit source. `--dry-run` shows the change without writing.

## 1.142.1 — 2026-07-07

### Fixed
- The changeset guard now exempts a release PR — a diff that is exactly `pkit release apply`'s footprint (version bumps, an updated CHANGELOG, and the consumed changesets deleted) passes with no `skip-changeset` label, because it is the release of already-declared changes, not a new surface change. A stray file outside that footprint keeps the guard firing, so the exemption never smuggles real surface through. ([#503])
- `pkit release merge`'s CI gate now dedupes a PR's check rollup to the latest run per check before deciding pass or fail. GitHub keeps every run of a check, so one that failed and was then re-run green (a fix-and-repush, a label re-trigger) previously left a stale failure that wrongly refused the merge; the gate now agrees with what `gh pr checks` reports. ([#504])
- **project-management 0.48.1** — The merge gate behind `merge-pr` and `done-work` now dedupes a PR's check rollup to the latest run per check before deciding pass or fail. GitHub keeps every run of a check, so one that failed and was then re-run green (a fix-and-repush, a label re-trigger) previously left a stale failure that wrongly refused the merge; the gate now agrees with what `gh pr checks` reports. ([#504])

[#503]: https://github.com/aleskalfas/project-kit/issues/503
[#504]: https://github.com/aleskalfas/project-kit/issues/504

## 1.142.0 — 2026-07-07

### Added
- Releasing a capability now keeps its compatibility claim current — the release step widens the released component's supported backbone range to the version it was released under, and a new `pkit release check-shareable` reports whether a capability is ready for another repository to consume. ([#494])
- **project-management 0.48.0** — The merge commands now refuse a pull request whose CI is red or still running, so an approved review can no longer land a failing build; a red check can be overridden deliberately with `--bypass-ci "<reason>"`, which records an audit note. ([#498])

### Changed
- The changeset-guard error now guides a decision-only PR to the right choice — a `none` changeset for a design-ahead decision, or a real one for a self-executing rule change. ([#497])

[#494]: https://github.com/aleskalfas/project-kit/issues/494
[#497]: https://github.com/aleskalfas/project-kit/issues/497
[#498]: https://github.com/aleskalfas/project-kit/issues/498

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
