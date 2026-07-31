# Changelog

## 1.142.7 — 2026-07-31

### Fixed
- Roll the backbone to carry the project-management 0.50.2 brownfield create-issue fixes (#557 the `--body-file` first-line check honours an advisory hierarchy; #559 the requiredness-gate substrate-awareness sweep) to adopters through `pkit upgrade`. project-management is a kit-shipped capability delivered bundled with the backbone, so these capability-only fixes need a backbone tag to reach adopters via the normal upgrade path; this bump tags the tree that already contains them. ([#559])
- **project-management 0.50.2** — The create-issue `--body-file` first-line parent-ref check now consults the hierarchy mode, mirroring the requiredness gate above it. Under `hierarchy: advisory` a non-parent-ref first line is accepted (parentless, body verbatim) so a flat brownfield tracker can file a prepared parentless body; greenfield / `hierarchy: gated` still hard-rejects a non-parent-ref first line unchanged. ([#557])
- **project-management 0.50.2** — Swept every create-issue requiredness/format refusal for substrate-map / hierarchy awareness (the create-side mirror of the read-side sweep). The workstream-requiredness gate now MIRRORS the writer's (`_build_labels`) write/no-write decision, reusing the same seam predicates and the same `resolve_write` — so the gate and the resolution cannot drift. It demands `--workstream` only when a workstream LABEL is the substrate (greenfield or an adopter-remapped `label` binding) AND no such label would be written for the omitted value; a `title-prefix` / `derive` / `unsupported` / absent axis is never label-written, so the gate no longer over-fires on those sibling arms (the earlier `served`-only predicate demanded a value for a `title-prefix`- or `derive`-bound axis that `_build_labels` never labels). An adopter-declared `default:` that resolves to a real write covers an omitted `--workstream` (the default supplies the label); a default that itself DEGRADEs does not, so the axis never silently drops. The explicit-`--workstream` value validation is now likewise substrate-aware — skipped under `workstream: unsupported` (the value is discarded by the writer, so validating it would false-refuse), kept for greenfield / served. Greenfield is byte-unchanged. The parent-requiredness, `--body-file` first-line gates were confirmed already substrate-aware; the title-format gate is left unchanged pending the brownfield-title-composition decision it is entangled with. Universal invariants (membership, cross-repo guard, unknown type, the kind/structural mismatch) stay hard. ([#559])

[#557]: https://github.com/aleskalfas/project-kit/issues/557
[#559]: https://github.com/aleskalfas/project-kit/issues/559

## 1.142.6 — 2026-07-30

### Fixed
- Roll the backbone to carry the project-management 0.50.1 brownfield `validate-issue` fix to adopters through `pkit upgrade`. project-management is a kit-shipped capability, so it reaches adopters bundled with the backbone; the fix landed between backbone tags (as a capability-only release), leaving no tag the upgrade path could deliver. This backbone bump tags the tree that already contains the fix so `pkit upgrade` delivers it. ([#553])

[#553]: https://github.com/aleskalfas/project-kit/issues/553

## 2026-07-30

### Fixed
- **project-management 0.50.1** — The `validate-issue` type-axis handling is now fully substrate-aware, so it agrees with `pre-check` on a brownfield repo across every `type` binding. A title carrying the adopter's own prefix (e.g. `[Epic]`, which diverges from the kit's rendered `[EPIC]`) resolves against the substrate-map's declared prefixes instead of false-failing `title.format`; a `type` bound to a label remap now demands one of the adopter's remapped labels (previously a missing type slipped through the close-gate); and a `type` bound to a title-prefix demands no kit `type:*` label but does demand a resolvable declared prefix — a title matching none of the adopter's declared prefixes hard-rejects `title.format` (an undeterminable structural type), consistent with the other served arms. All arms route through the axis-labels seam, and greenfield behaviour (a missing `type:*` label still hard-rejects) is unchanged. ([#553])

[#553]: https://github.com/aleskalfas/project-kit/issues/553

## 1.142.5 — 2026-07-10

### Changed
- **project-management 0.50.0** — Add `show-pr --field review` — surface the DEC-028 reviewer verdict (token + reasons) through the governed pm read path, so the verdict is no longer opaque after `review-pr`.

### Fixed
- The release step now keeps the source repo's own self-host manifest backbone version current on a backbone bump, so `pkit status` no longer misreports the self-host backbone as frozen at genesis.
- **project-management 0.50.0** — The provenance footer no longer stamps `tree unknown` in adopter installs — the backbone version now resolves from `.pkit/manifest.yaml` when `.pkit/VERSION` is absent.

## 1.142.4 — 2026-07-08

### Fixed
- `pkit sync`/`upgrade` no longer silently aborts when a listed skill or agent resolves to no canonical file. The claude-code deploy primitives ran an unguarded resolver whose benign "not found" tripped `set -e`, killing the run mid-way with no diagnostic (only the wrapper's opaque "exited with status 1"). The common trigger is a composite skill folder mid-build (COR-020): sub-procedures present but no `<name>/<name>.md` dispatcher yet. Both deploy scripts now skip the unresolvable item loudly — naming the skill/agent and the defect with a remediation hint — deploy the rest, and exit cleanly with an end-of-run summary. ([#537])

[#537]: https://github.com/aleskalfas/project-kit/issues/537

## 1.142.3 — 2026-07-08

### Fixed
- Scope the COR-018 companion-JSON-Schema requirement to actual schema definitions in `pkit schemas validate` (and register's capability self-consistency check). YAML fixtures under `examples/` (or named `*-example.yaml`) and instances that declare an external/shared `$schema` pointer (a `# yaml-language-server: $schema=` directive or a top-level `$schema:` key at a schema other than their own companion) are no longer wrongly flagged as schema definitions missing a companion. A genuine schema YAML with no companion is still flagged.

## 1.142.2 — 2026-07-08

### Added
- **project-management 0.49.0** — Add the `set-instance` command — set (or `--show` / `--clear`) this clone's opt-in, per-clone numeric instance id, the activation gate for instance ownership when one person runs several clones of a repo (DEC-035). The id is written to a git-ignored runtime file and read by the ownership lifecycle; a clone with no id set is unchanged. The claim / clash-guard / signed-listing behaviour that acts on the id follows in subsequent changes.

### Changed
- Documented COR-031's operational collision precedence in the CLI reference: register keeps the in-repo (incubated) copy on a kit-source name collision and surfaces that a kit-shipped version is available; sync leaves incubated untouched (D1). A doc clarification of already-decided behaviour (no COR change, no surface moved).

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
