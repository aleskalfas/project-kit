---
id: PRJ-004
title: Distribution via direct git URL on github.com (no registry)
status: accepted
date: 2026-05-08
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

PRJ-003 settled the language (Python 3.11+, distributed as a `uv tool install` target). What remained was *where* the package gets installed *from* — registry choice or a direct-from-source path. Candidates considered: PyPI public, a private artifact registry, Homebrew tap, GitHub releases tarball, `curl … | bash` installer, and direct git URL.

project-kit is open-source (MIT) and lives publicly at `github.com/aleskalfas/project-kit`. Its adopter set is small and grows manually; the near-term adopters are a handful of projects authored by the same person. The question this record settles is whether to layer a package registry on top of the public source, or install directly from the git URL. It also settles which ref that install names.

Both `pip` and `uv` install Python tools from git URLs natively. For a Python tool whose source is already on public GitHub, the question is whether to layer a registry on top, or rely on the git URL as the install path.

Which ref the install names decides whether the version a project records names the content it holds (ADR-065 point 12).

## Decision

**Distribute via direct git URL on `github.com`, with no registry layer.** The canonical install path names a release tag:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@v<version>
```

`<version>` names a release. A tagged install ties pkit's version to one content, what its wheel bundles from the tagged tree (ADR-033). So the version a project records names the content it holds ([ADR-065](../../../tech-docs/architecture/decisions/ADR-065-upgrade-runs-the-transition.md) point 12).

`uv tool install` is the **sole sanctioned frontend** (per PRJ-003) — `uv` is a hard requirement, not merely recommended. The former `pip install git+...` fallback is **dropped**: the router hard-assumes `uvx` for pinned re-execution ([ADR-039](../../../tech-docs/architecture/decisions/ADR-039-pkit-entry-point-router.md)), so a `pip`-installed pkit is a latent inconsistency, and self-service tool-update ([ADR-063](../../../tech-docs/architecture/decisions/ADR-063-upgrade-updates-the-tool.md)) runs or prints a `uv` command; supporting a second frontend buys nothing at this project's single-digit-adopter, uv-native scale and only adds a "which pkit am I running" ambiguity. This narrows the *frontend* set, not the channel (still a direct git URL, no registry — so this is an in-place amendment, not a supersession). The HTTPS form (`git+https://github.com/...`) remains supported for users who authenticate to GitHub via PAT instead of SSH. Its canonical form names the same tag.

**The ref** after `@` is a tag, a branch, or a commit SHA:

- `@v<version>` — a tagged release, the canonical form. The release step (PRJ-002) cuts an annotated git tag matching `.pkit/VERSION` on each release that moves it. Tag form: `v<major>.<minor>.<patch>` (e.g., `v0.5.0`).
- `@<branch>` — install a specific branch (useful for adopters trying a kit feature before it lands).
- `@<sha>` — install a specific commit (longest-term-stable form; immune to tag edits).

**An install from main is the development install.** The same URL with no tag installs main's head. Its version names the last release, while its files may be newer. So no version vouches for its content.

An install of any commit no release tags, such as a branch's, is untagged too. Untagged installs are possible. Sync's guard compares their version like any other, and nothing checks whether an install is tagged (ADR-065 points 7 and 12).

**No registry today.** No PyPI, no private artifact registry, no Homebrew tap, no `curl | bash` installer. Direct git URL is the *only* sanctioned install path until the audience grows past what URL-sharing can handle.

**Revisit threshold.** Convert to a registry-based distribution when *any* of the following hold:

- Adoption grows to where PyPI's discoverability + cross-ecosystem version resolution earn their keep — the kit is already public open-source, so PyPI is the natural next channel when scale demands it.
- Adopter count crosses ~25–50 projects, where manually communicating the URL and managing which tag each adopter installs becomes operational overhead.
- Discoverability becomes a real need (the kit gets cited externally; new adopters can't be onboarded by direct contact).

The transition to a registry is itself a future PRJ; this record fixes the channel for the pre-1.0 phase.

## Rationale

**Why git URL beats every registry option for our current scale.** Registries solve discoverability, version resolution across an ecosystem, and download metrics — none of which we need at single-digit adopter count. They cost: provisioning, credential management, tag-publish ceremony, and ecosystem-conventions to learn. For a tool installed by people who already have GitHub auth and already know where the repo is, those costs are pure overhead.

**Why git URL beats GitHub releases tarball.** GitHub releases require a manual gesture per release (cut a release artifact, write release notes). Tagging a commit is already the release artifact (PRJ-002). Adding a release-artifact step layers ceremony without adding capability — `uv tool install git+...@v0.5.0` already installs the tagged commit.

**Why git URL beats `curl … | bash`.** Curl-bash installers trade some safety (executing a fetched script) for ease. We don't need ease — `uv tool install git+ssh://...` is one command and is the modern Python-tool install convention. Curl-bash also requires hosting the installer somewhere reachable, which re-introduces the registry-equivalent infrastructure question we're trying to avoid.

**Why SSH is the recommended URL form.** Most devs already have SSH keys configured for `github.com` (the standard `git clone` path). PAT-based HTTPS is supported for tooling/CI environments that can't use SSH; making it secondary clarifies the default.

**Why tags + `.pkit/VERSION` keep working.** The release step (PRJ-002) writes `.pkit/VERSION` and cuts the matching tag. Adopters installing `@v0.5.0` get the exact source tree at that tag, with auto-broadened `requires_backbone` ranges already applied to kit-shipped components. The whole lifecycle layer per COR-010 works unchanged.

**Why the canonical install names a tag.** A project records the version of the content it holds. Sync's guard compares that version with the running pkit's ([ADR-065](../../../tech-docs/architecture/decisions/ADR-065-upgrade-runs-the-transition.md) point 7). The comparison is sound only where a version names one content, and only a tagged install gives that (ADR-065 point 12).

Main's head can carry the next release's backbone migrations beside the last release's `VERSION`. A project upgraded by a pkit installed from main's head then records the last release over files that need the next one's migrations. The costs of a tagged canonical install:

- a printed install command names a version that ages
- an untagged install is possible, and nothing checks it
- a release that moves only a component cuts no tag, so it reaches a project on a tagged install only with the next backbone release

**Why we set a revisit threshold rather than picking a registry now.** Pre-1.0, the kit's surface and adopter set are both small enough that the simpler distribution wins. The cost of swapping channels later is real but bounded — adopters re-run a one-line install command; tags carry the same versions; `uv tool` handles the swap cleanly. Locking in a registry today commits us to its conventions before we've seen what's painful.

### Alternatives considered

- **PyPI public.** Rejected for now — at single-digit adopter scale the public git URL suffices, and publishing to PyPI adds a publish-ceremony step per release. It is the natural next channel as adoption grows (the kit is already public open-source under MIT).
- **Private artifact registry** (Artifactory, etc.). Rejected — adds an authentication system and publish-to-registry step on top of the GitHub auth and tag-commit step that already exist. The benefit (formal artifact provenance) doesn't justify the cost at single-digit-adopter scale.
- **Homebrew tap** (private or public). Rejected — Homebrew formulas wrap a release artifact; this would either require a parallel GitHub-releases artifact pipeline or a shim that fetches from git, both adding ceremony. Reconsider only if mac-specific install UX becomes a stated goal.
- **GitHub releases tarball.** Rejected — adds a per-release manual gesture without adding install capability. Tagging the commit (which we already do) is the release artifact in `uv tool install`'s view.
- **`curl … | bash` installer.** Rejected — the modern Python-tool install convention is `uv tool install`, not curl-bash. Curl-bash also re-introduces the "host the installer somewhere" question.
- **The URL with no tag as the canonical install.** Rejected: it installs main's head, which no version vouches for, so the version a project records would not name the content it holds.
- **A development version stamped on untagged builds,** such as `1.149.0+g<sha>`, so an install from main never equals a project's recorded version. Rejected, as the maintainer decided for #1429 on 11 October 2026. Every untagged install would meet sync's stop in every project. The router reads such a version as unordered.
- **Wait until 1.0 to settle distribution.** Rejected — there's no install path documented today; adopters are reaching for ad-hoc `git clone + ./.pkit/cli/pkit` symlinks (which is the bootstrap, not the long-term path). Locking in git-URL distribution now gives adopters a sanctioned install command without committing to a registry.

## Implications

- **`pyproject.toml` at the repo root** (per PRJ-003) is required for git-URL install to work. The `[project]` table declares the package name (`project-kit`), version (read from `.pkit/VERSION` or via dynamic versioning), and entry point (`pkit = "project_kit.cli:main"`). **The built wheel also bundles the methodology content as package data, so the installed binary can `init`/`sync`/`upgrade` without a checkout. What it carries is defined by *tier ownership* — the kit-owned tree, with the *contents* of the source project's own `project/` tier withheld — so no adopter receives another project's config, activation switches or audit journals. The few tiers whose scaffolding the installer gates on the bundle's shape ship as empty directory markers. See [ADR-033](../../../tech-docs/architecture/decisions/ADR-033-official-install-bundles-content.md), which clarifies (does not supersede) this implication.**
- **Tagging on release:** the release step's sequence, through `pkit version tag --push` (per #44), is in the release README.
- **Authentication is the user's existing GitHub auth.** SSH key via `~/.ssh/config` for `github.com`, or PAT via `git config credential.helper`. The kit doesn't introduce a new credential surface.
- **CI / automation use** (e.g., adopter projects that install `pkit` in their CI) needs an SSH deploy key or a PAT in the runner's credential store. This is a per-adopter operational concern; the kit documents the pattern in `CONTRIBUTING.md` once it surfaces.
- **Release notes ship as a notes-only GitHub Releases overlay** (the option foreseen here, realized 2026-07-05). `pkit release publish-notes` publishes each version's `CHANGELOG.md` section as the Release body, wired into the tag workflow. It is **notes only — never an attached artifact**: a wheel/tarball would reintroduce the release-artifact channel this record rejects, so attaching one stays forbidden and the install path is unchanged (still the git tag, `uv tool install …@vX`). This realizes a foreseen implication without overturning the decision, so it is recorded here, not superseded (per the channel-change note below).
- **Channel-change path.** If the channel changes (e.g. adding PyPI as adoption grows), the decision is re-opened in a successor PRJ; this record is superseded, not amended (per the spec — supersession is for changes that overturn the original).
- **Adopter doc** (`.pkit/cli/README.md`'s "Installing pkit on PATH" section) recommends the tagged install, and names the install from main as the development install. `pkit init` ends by printing the same command with its own version, `@v<its version>`, and a test holds the two equal (#1376). The repository's top-level README names a tag in its install line too. With the uv-only narrowing above, `uv` is a prerequisite — there is no "machine without `uv`" supported path.
