---
id: PRJ-004
title: Distribution via direct git URL on github.com (no registry)
status: accepted
date: 2026-05-08
author: Ales Kalfas <kalfas.ales@gmail.com>
---

## Context

PRJ-003 settled the language (Python 3.11+, distributed as a `uv tool install` target). What remained was *where* the package gets installed *from* — registry choice or a direct-from-source path. Candidates considered: PyPI public, a private artifact registry, Homebrew tap, GitHub releases tarball, `curl … | bash` installer, and direct git URL.

project-kit is open-source (MIT) and lives publicly at `github.com/aleskalfas/project-kit`. Its adopter set is small and grows manually; the near-term adopters are a handful of projects authored by the same person. The question this record settles is whether to layer a package registry on top of the public source, or install directly from the git URL.

Both `pip` and `uv` install Python tools from git URLs natively. For a Python tool whose source is already on public GitHub, the question is whether to layer a registry on top, or rely on the git URL as the install path.

## Decision

**Distribute via direct git URL on `github.com`, with no registry layer.** The canonical install path is:

```
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git
```

`uv tool install` is the recommended frontend (per PRJ-003); `pip install git+...` works as a fallback for environments where `uv` is not available. The HTTPS form (`git+https://github.com/...`) is supported for users who authenticate to GitHub via PAT instead of SSH.

**Pinning** is by tag, branch, or commit SHA, appended after `@`:

- `@v0.5.0` — pin to a tagged release. The kit cuts annotated git tags matching `.pkit/VERSION` whenever PRJ-002 dictates a bump (i.e., on every PR that lands a surface change). Tag form: `v<major>.<minor>.<patch>` (e.g., `v0.5.0`).
- `@<branch>` — install a specific branch (useful for adopters trying a kit feature before it lands).
- `@<sha>` — pin to a specific commit (longest-term-stable form; immune to tag edits).

**No registry today.** No PyPI, no private artifact registry, no Homebrew tap, no `curl | bash` installer. Direct git URL is the *only* sanctioned install path until the audience grows past what URL-sharing can handle.

**Revisit threshold.** Convert to a registry-based distribution when *any* of the following hold:

- Adoption grows to where PyPI's discoverability + cross-ecosystem version resolution earn their keep — the kit is already public open-source, so PyPI is the natural next channel when scale demands it.
- Adopter count crosses ~25–50 projects, where manually communicating the URL and managing tag-pinning across that many adopters becomes operational overhead.
- Discoverability becomes a real need (the kit gets cited externally; new adopters can't be onboarded by direct contact).

The transition to a registry is itself a future PRJ; this record fixes the channel for the pre-1.0 phase.

## Rationale

**Why git URL beats every registry option for our current scale.** Registries solve discoverability, version resolution across an ecosystem, and download metrics — none of which we need at single-digit adopter count. They cost: provisioning, credential management, tag-publish ceremony, and ecosystem-conventions to learn. For a tool installed by people who already have GitHub auth and already know where the repo is, those costs are pure overhead.

**Why git URL beats GitHub releases tarball.** GitHub releases require a manual gesture per release (cut a release artifact, write release notes). Tagging a commit is already the bump artifact (per PRJ-002). Adding a release-artifact step layers ceremony without adding capability — `uv tool install git+...@v0.5.0` already pins to the tagged commit.

**Why git URL beats `curl … | bash`.** Curl-bash installers trade some safety (executing a fetched script) for ease. We don't need ease — `uv tool install git+ssh://...` is one command and is the modern Python-tool install convention. Curl-bash also requires hosting the installer somewhere reachable, which re-introduces the registry-equivalent infrastructure question we're trying to avoid.

**Why SSH is the recommended URL form.** Most devs already have SSH keys configured for `github.com` (the standard `git clone` path). PAT-based HTTPS is supported for tooling/CI environments that can't use SSH; making it secondary clarifies the default.

**Why tags + `.pkit/VERSION` keep working.** The `pkit version bump` command (per PRJ-002) writes `.pkit/VERSION`; the bump commit is followed by `git tag v$(cat .pkit/VERSION)` (recommended convention; not yet automated). Adopters pinning by `@v0.5.0` get the exact source tree at that tag, with auto-broadened `requires_backbone` ranges already applied to kit-shipped components. The whole lifecycle layer per COR-010 works unchanged.

**Why we set a revisit threshold rather than picking a registry now.** Pre-1.0, the kit's surface and adopter set are both small enough that the simpler distribution wins. The cost of swapping channels later is real but bounded — adopters re-run a one-line install command; tags carry the same versions; `uv tool` handles the swap cleanly. Locking in a registry today commits us to its conventions before we've seen what's painful.

### Alternatives considered

- **PyPI public.** Rejected for now — at single-digit adopter scale the public git URL suffices, and publishing to PyPI adds a publish-ceremony step per release. It is the natural next channel as adoption grows (the kit is already public open-source under MIT).
- **Private artifact registry** (Artifactory, etc.). Rejected — adds an authentication system and publish-to-registry step on top of the GitHub auth and tag-commit step that already exist. The benefit (formal artifact provenance) doesn't justify the cost at single-digit-adopter scale.
- **Homebrew tap** (private or public). Rejected — Homebrew formulas wrap a release artifact; this would either require a parallel GitHub-releases artifact pipeline or a shim that fetches from git, both adding ceremony. Reconsider only if mac-specific install UX becomes a stated goal.
- **GitHub releases tarball.** Rejected — adds a per-release manual gesture without adding install capability. Tagging the commit (which we already do) is the release artifact in `uv tool install`'s view.
- **`curl … | bash` installer.** Rejected — the modern Python-tool install convention is `uv tool install`, not curl-bash. Curl-bash also re-introduces the "host the installer somewhere" question.
- **Wait until 1.0 to settle distribution.** Rejected — there's no install path documented today; adopters are reaching for ad-hoc `git clone + ./.pkit/cli/pkit` symlinks (which is the bootstrap, not the long-term path). Locking in git-URL distribution now gives adopters a sanctioned install command without committing to a registry.

## Implications

- **`pyproject.toml` at the repo root** (per PRJ-003) is required for git-URL install to work. The `[project]` table declares the package name (`project-kit`), version (read from `.pkit/VERSION` or via dynamic versioning), and entry point (`pkit = "project_kit.cli:main"`).
- **Tagging on bump** is the new convention: after `pkit version bump <segment>` and the bump commit, the workflow tags the commit `v<major>.<minor>.<patch>` and pushes the tag. `pkit version tag --push` automates the tag + push step (per #44); the workflow is `pkit version bump … && git commit && pkit version tag --push`.
- **Authentication is the user's existing GitHub auth.** SSH key via `~/.ssh/config` for `github.com`, or PAT via `git config credential.helper`. The kit doesn't introduce a new credential surface.
- **CI / automation use** (e.g., adopter projects that install `pkit` in their CI) needs an SSH deploy key or a PAT in the runner's credential store. This is a per-adopter operational concern; the kit documents the pattern in `CONTRIBUTING.md` once it surfaces.
- **No release notes infrastructure** ships today. Tag annotations (`git tag -a v0.5.0 -m "..."`) carry the per-tag rationale; the PR descriptions on each surface-change PR carry the longer prose. If release notes become useful, they can land later as a `CHANGELOG.md` or a GitHub Releases overlay without changing the install path.
- **Channel-change path.** If the channel changes (e.g. adding PyPI as adoption grows), the decision is re-opened in a successor PRJ; this record is superseded, not amended (per the spec — supersession is for changes that overturn the original).
- **Adopter doc** (`.pkit/cli/README.md`'s "Installing pkit on PATH" section) graduates from the bootstrap symlink-pattern to `uv tool install` once the Python runtime ships per the build roadmap. The bootstrap remains as a fallback for machines without `uv`.
