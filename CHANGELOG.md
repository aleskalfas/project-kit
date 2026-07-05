# Changelog

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
