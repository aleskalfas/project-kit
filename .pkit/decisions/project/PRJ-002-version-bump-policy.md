---
id: PRJ-002
title: Version-bump policy for project-kit (pre-1.0 hybrid)
status: accepted
date: 2026-05-08
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

COR-010 fixes that backbone and components use semver, components declare `requires_backbone` ranges, and migrations land per `<major>.<minor>.0/`. What COR-010 deliberately does *not* cover — because it is project-neutral — is *when* the source kit's backbone version actually bumps and *who* performs the bump. That is a project-kit-the-project policy.

`.pkit/VERSION` declares the current backbone version (`0.1.0` today). Without a bump policy, every PR creates ambiguity: should this change bump the backbone? Which segment? Per-PR with no rule risks two failure modes — version churn (every doc-fix bumps; the number stops meaning anything) or version freeze (nothing bumps; the number stops tracking reality). Either way the version stops being a useful compatibility signal for the lifecycle machinery.

Mid-conversation alternatives were considered: bump on every merged PR (too noisy pre-1.0); bump only at "release moments" (requires a release concept the kit does not yet have); calver instead of semver (rejected by COR-010). The hybrid below is the third path.

## Decision

**A PR bumps `.pkit/VERSION` if and only if it lands a *surface change*.** Otherwise no bump.

A **surface change** is anything an adopter could observe, depend on, or break against:

- A new CLI command or subcommand.
- A new principle in an accepted COR (or any new COR).
- A breaking change to an existing CLI / spec / contract.
- A new area, area variant, or component type.
- A schema change to manifests / `package.yaml` / `.pkit/VERSION`.
- A new convention adopters are expected to follow (e.g., the git-conventions and PR-workflow records of COR-008 / COR-009).

A **non-surface change** does not bump:

- Documentation refinement (clarity, typos, prose tightening) where the underlying contract is unchanged.
- Internal refactors of project-kit's own tree that adopters do not see.
- Bug fixes that do not change observable behaviour.
- Test additions or test-only changes.
- New PRJ records (project-kit-internal; not adopter-facing).
- README cross-reference updates that follow already-landed surface changes.

**Bump segment** per semver:

- **Patch** — backward-compatible bug fix to existing surface (e.g., a CLI command had a wrong error message; the spec is unchanged).
- **Minor** — new surface added (new command, new principle, new area). Pre-1.0, this is the typical bump and *may carry breaking changes* (per semver convention for `0.x` releases).
- **Major** — reserved for `1.0.0` itself and post-1.0 spec breakage. Pre-1.0, do not bump major.

**Bump cadence**: at most one bump per PR, performed via `pkit version bump <segment>` as a commit *within* the PR (so reviewers see the version delta and the surface change in the same diff). PRs that bundle multiple surface changes pick the highest applicable bump.

**Authority**: the PR author bumps; reviewers can request a different segment as a review comment. The PR template's checklist surfaces the question explicitly.

**Mode promotion (post-1.0)**: this hybrid policy is pre-1.0. Once `1.0.0` lands and the surface stabilises, the policy promotes to *release-driven*: a separate "cut release" PR rolls up accumulated surface changes into one bump, with each contributing PR linked from the release notes. The promotion is a refinement of this record (direct edit per the spec's refinement rule), not a supersession.

## Rationale

**Why hybrid over per-PR.** Pre-1.0 the kit lands many small docs / cleanup / internal commits that adopters do not observe. Bumping minor on every merged PR turns the version into a commit counter — the number loses its compatibility-signal role. Hybrid keeps the version meaningful by tying it to surface changes that an adopter could break against.

**Why hybrid over release-driven.** Release-driven assumes a release concept (release notes, tag-and-publish gesture) that project-kit does not yet have. Pre-1.0 the kit is still establishing its surface; "releases" would either be artificial (one per week regardless of content) or very long (one per major milestone, leaving the version far behind the actual surface for stretches). Putting the bump in the same PR as the surface change ties the version to the contract change directly, with no batching latency.

**Why per-PR within the PR's commits, not as a follow-up.** A bump landed in a follow-up PR after the surface PR merges has the same problem release-driven has: the version lags the change. Reviewers also lose the ability to push back on the segment ("you marked this minor but it looks like a breaking change"). Co-locating bump and surface change in one PR is the cheapest review surface for both.

**Why pre-1.0 doesn't reserve major for breakage.** Per semver, `0.x` releases are explicitly allowed to carry breaking changes at minor bumps; major is conventionally held until the project declares stability. Bumping major before `1.0.0` would be premature. Adopters of a `0.x` kit understand they are on a pre-stable channel.

**Why the bump is a `pkit` subcommand and not a manual edit.** `.pkit/VERSION` is a single line — the script is small, but per COR-007 mechanical work earns tooling regardless of size, and a script enforces the parse-bump-write sequence consistently (no off-by-one, no accidentally non-semver values, no losing a digit during a manual edit).

### Alternatives considered

- **Per-PR bump on every merged PR.** Rejected — too noisy pre-1.0; version stops being a compatibility signal and starts being a commit counter.
- **Release-driven from day one.** Rejected — requires a release concept the kit does not have; bumps would lag changes by weeks, defeating the version-as-current-state property.
- **Calver instead of semver.** Rejected by COR-010 (semver is the kit-wide rule).
- **No policy; bump ad-hoc when it "feels right".** Rejected — leads to drift; version becomes meaningless without consistent rules; reviewers cannot dispatch on a stable definition of "surface change".
- **Author bumps + reviewer veto.** This is what we have. Considered alternatives where reviewers bump or where bumps are post-merge automation; rejected as too far from where the surface decision is made.

## Implications

- **`pkit version bump <segment>`** exists in the CLI dispatcher. Reads `.pkit/VERSION`, validates the segment, parses the current version, computes the new version per semver rules, writes back. The PR author runs it once they know which segment applies.
- **Auto-broaden of kit-shipped components.** After writing the new backbone version, the command walks every `package.yaml` under `$SOURCE_KIT` and broadens each one's `requires_backbone` upper bound to `<NEW_MAJOR.(NEW_MINOR+1).0` *if* the new backbone version is at or beyond the existing upper bound. Components whose range still includes the new version are left alone (idempotent for patch bumps that stay within the existing minor line, and for minor bumps where the upper bound was already broad enough). This dogfoods the lifecycle compatibility model: kit and components co-evolve in lockstep pre-1.0, so the bump that ships a backbone change is the same bump that absorbs it on the components shipped from the same source. Component authors who want a tighter range (deliberately excluding the new backbone) narrow it manually after the bump.
- **`.github/PULL_REQUEST_TEMPLATE.md`** carries a checklist item: "Surface change? If yes, bump the version (see PRJ-002)." Reviewers can flag PRs that look like surface changes but skipped the bump (or vice versa).
- **Bump commits** use conventional-commits format per COR-008. Recommended message: `chore(versioning): bump backbone <old> -> <new>` (type `chore` because the bump itself is mechanical; the surface change is in another commit of the same PR with its own type).
- **The lifecycle README's worked example** uses fictional version numbers (`v2.1.0`, etc.) for illustrative breadth; this policy applies only to the actual `.pkit/VERSION` of project-kit-the-project.
- **Post-1.0 transition** is captured by amending this record (direct edit, per the spec's refinement rule), introducing a "Mode" section and noting the date the kit promoted from hybrid to release-driven.
