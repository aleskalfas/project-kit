---
id: ADR-033
title: Official install bundles methodology content, version-locked to the binary
status: accepted
date: 2026-06-26
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The official adopter install (`uv tool install git+ssh://…project-kit.git`, per PRJ-004)
**cannot actually set up or upgrade an adopter project** — `init`/`sync`/`upgrade` all fail
from the installed binary. That directly contradicts what PRJ-004 and the CLI README promise
(the binary "works against any adopting project", listing `init`/`sync`). Issue #333 under
EPIC #332.

The cause: the built wheel ships only the Python package (`src/project_kit`) plus the VERSION
file — it does **not** carry the `.pkit/` methodology tree (decisions, schemas, skills,
agents, adapters, capabilities, migrations). `find_source_kit()` resolves the propagation
source by walking the filesystem relative to the installed package (`<pkg>/../../.pkit`), so
inside a `uv tool` venv it points at a path that does not exist — `init` raises a clean guard
error, while `upgrade`/`sync` crash with a raw `FileNotFoundError`. The scratchpad note
`.pkit/scratchpad/active/2026-06-26-pkit-install-versioning-model.md` works the design space
and identifies the root cause and the two-version-axes drift problem (binary version vs the
adopter's `.pkit/VERSION`).

## Decision

The official install **resolves methodology content from package data bundled in the wheel,
version-locked to the binary.** `find_source_kit()` prefers a real checkout when present and
falls back to the bundled content otherwise. Concretely — the four points below are cited from
code and from other records both as `§N` and as `DN`; the two forms mean the same point:

### 1. Bundle the kit-owned tier, not the whole `.pkit/` tree

The wheel bundles the methodology tree under the package path `project_kit/_kit/`, minus every
path that is **adopter-owned by tier** — the project side of COR-001's no-shared-files split.
The rule — not the list — is what this decides: the existing core/project ownership boundary
determines what's in, and deliberately **not** the set `pkit sync` propagates (Rationale gives
why). By that rule the bundle **excludes** adopter-owned subtrees (for example a `project/`
directory such as `decisions/project/`, `capabilities/<name>/project/` or
`adapters/<harness>/settings/project/`; the maintainer's `scratchpad/{active,done,dropped}`
notes; `manifest.yaml`; and `.gitignore` — illustrative of the rule's reach, not an
authoritative list).

**The boundary is stated once per artifact, independently.** The wheel's build hook asks
`.pkit/lifecycle/ownership.py`'s `is_adopter_owned_by_tier` of every file, so the build carries
no copy of the rule and no hand-kept manifest. The sdist's `.pkit/` is filtered by the globs in
the build hook's `withhold` option, run inside the hook. The globs are deliberately independent
of the wheel's predicate: a second statement of the boundary, so the two can check each other
rather than share one mistake.

**The bundle is a superset of what sync propagates.** In an official install the bundle *is*
the source `pkit sync` reads, so it carries everything sync propagates; it additionally carries
capability source, which §3 ships and sync never propagates. Rationale gives why this direction
is required rather than incidental.

**Build caches are excluded by a second mechanism, not by this rule.** `__pycache__`, `.pyc`
and `.pyo` are not adopter-owned — the ownership predicate answers False for them — and
`pyproject.toml`'s `exclude` cannot filter force-included paths, which is the whole reason the
hook exists. So the hook applies those patterns itself (`EXCLUDED_PARTS` / `EXCLUDED_SUFFIXES`
in `hatch_build.py`); omitting them shipped 87 `.pyc` files on the first attempt, trading 41
unwanted files for 87 different ones. Two obligations on the bundle, not one — an author who
reimplements it from the ownership rule alone reproduces that bug.

**The rule withholds adopter-owned *content*, not adopter-owned *shape* — one bounded
exception.** The rule above cannot erase a directory's existence, because the installer reads
the bundle's shape as well as its contents: it stubs an adopter's `project/` tier only where
the source bundle *has* that directory (`(src / "project").is_dir()` for an area,
`project_src.is_dir()` for an adapter's settings pair). A per-file include ships files, not
directories, so withholding every file in such a directory deletes the directory from the
artifact, and the official install silently stops creating that scaffolding — a regression
invisible to tests that assert file presence. So the wheel ships one **empty** `.gitkeep` at
each of four *declared* adopter-owned paths — `agents/project`, `permissions/project`,
`skills/project`, `adapters/claude-code/settings/project` (`ADOPTER_TIER_MARKERS` in
`hatch_build.py`). They are layout, not adopter data: each is asserted byte-empty by test, the
set is declared in code rather than discovered from the filesystem (Rationale gives why), and
none reaches an adopter, because the install path stubs those trees rather than copying them.
**Finding `agents/project/.gitkeep` in the wheel is this rule working, not a leak to fix.** The
ownership predicate answers only *may this content be distributed?*; which directory shapes the
artifact must carry is a separate fact, declared separately, because a consumer drives it
rather than ownership. The general principle, and the bar any future exception must clear: a
consumer that reads the artifact's *shape* constrains what the ownership rule may erase — and
the carve-out stays bounded, declared, empty, and test-asserted.

**The markers are declared positions, not a depth rule.**
`adapters/claude-code/settings/project` is among them at depth 3 because `install.py` gates
that adapter's settings scaffolding on it. Nor does a `project/` component at any depth make a
directory the adopter's: one nested below a kit-owned tier — inside an area's `core/`, or below
a capability's top level, which [ADR-012](ADR-012-ownership-aware-tree-refresh.md) point 2 pins
as kit-owned — is refreshed and orphan-pruned by the copy primitive like any other kit content.
An ownership predicate that answered "the adopter's" there would contradict the copy path.

### 2. Checkout-first resolution is a contract

`find_source_kit()` returns a real checkout's `.pkit/` when `(.pkit/"decisions").is_dir()`
holds; otherwise it returns the bundled `project_kit/_kit/`, resolved via
`importlib.resources`. The bundle is a *fallback*, never consulted when a real checkout is
present, and is resolved so it can never be mistaken for a checkout `.pkit/`.

### 3. Capability source is a distribution medium, not an activation surface

All shipped capabilities' source travels in the wheel (the "repository"); `capabilities
install <name>` remains on-demand into the adopter (COR-017's opt-in boundary unchanged —
the existing available-in-source vs installed split).

**"Source" means the capability's kit-owned tier only.** A capability's `project/` subtree in
this repo is *this project's* live instance state rather than anything the capability ships —
the reading [ADR-012](ADR-012-ownership-aware-tree-refresh.md) point 2 pins — so D1's rule
withholds it. This point decides that capability source is a *medium*, not that everything
sitting under a capability's directory travels; reading "all source travels" as a licence for
the whole subtree would ship one project's config, its default-agent activation switch, its
bootstrap stamp and its per-issue journals to every adopter (#811).

### 4. Migrations and capabilities must reach adopters

This fixes a pre-existing omission: `migrations/` and `capabilities/` are read from the
source kit but are absent from the propagation set, so backbone migrations have never reached
a non-self-host adopter and could not run.

## Rationale

**Why version-locking is the feature, not a side effect.** The scratchpad's failure-mode
analysis shows the wedging hazard is a pinned binary running against mismatched `.pkit/`
content. When the binary carries its own content, "binary version" and "the content it syncs"
are identical by construction — one of the two drift axes collapses for the official install.
That is the load-bearing reason to bundle the content over the alternatives below.

**Why bundle-the-kit-owned-tier beats bundle-the-tree.** Keying the bundle on the core/project
ownership boundary makes the PRJ-record exclusion, the manifest exclusion, and the scratchpad
exclusion all fall out of one existing rule. A blanket "copy `.pkit/`" rule sweeps
adopter-owned and maintainer-only artifacts into adopters.

**Why tier ownership and not the sync surface.** Sync-management is not a statement about tier.
It additionally depends on whether a capability is *registered* — so the same file can answer
differently depending on the build machine's manifest state — and it reads everything outside
`.pkit/` as unmanaged, so `src/`, which legitimately ships, answers "not propagated". A
packaging rule keyed on it therefore cannot answer *may this be distributed?* It points at a
predicate with no opinion on the question being asked, so the packaging manifest keeps its own
idea of the boundary and nothing can notice the two disagreeing — which is how 51 adopter-owned
files, every capability's `project/` subtree plus this project's own permission allow-list from
`adapters/<harness>/settings/project/`, travelled in the 1.149.0 wheel.

**Why the bundle must be a superset of the propagation surface.** In an official install the
bundle is the source sync reads, so anything sync propagates and the bundle withholds is
silently un-propagated for every tool-installed adopter. Superset is therefore the direction
this record requires, not an accident it gets away with; D1's `.gitkeep` carve-out is the same
obligation one level down, at shape rather than content. The adapter settings pair is no
exception: `pkit sync` never copies `settings/project/settings.json` — init seeds it from a
constant and sync leaves it alone — and both ownership predicates read it as the adopter's,
`is_sync_managed` because it tests the adopter tier by declared position before dispatching on
capability registration. The kit's own set is a different comparison. Against what
`is_sync_managed` calls *the kit's* — a different set from what sync copies, since sync does
not consult that predicate at all — neither side contains the other: `.pkit/release/` and
`.pkit/README.md` are the kit's and deliberately undistributed, while the four `.gitkeep`
markers are distributed and are not the kit's.

**Why the marker set is declared rather than discovered.** Discovery fails on both build paths.
Collecting the parent of every withheld file makes the artifact depend on untracked state:
withheld files include git-ignored ones, so a working tree emits a marker for a directory that
exists locally only because of untracked journals, and a clean clone of the same commit does
not (419 `_kit` entries against 418). And the sdist prunes `**/project`, so a wheel built
*from* an sdist — what `pip install` does with a source distribution — finds no such directory,
emits no markers, and loses the scaffolding on the path most adopters take. A declared tuple
lives in the code, and the code travels in both artifacts, so both build paths emit the same
set; a test asserts the tuple against the source tree so the declaration cannot drift into
fiction.

**Why the mechanism is packaging-agnostic (and therefore final, not interim).** "Bundle
content as package data + resolve via `importlib.resources`" is identical whether pkit is
delivered by git URL (today), a registry, or frozen into a standalone binary. Only the
delivery wrapper changes up the distribution ladder; the resolution mechanism does not. So
this is the durable foundation, not a throwaway step.

### Alternatives considered

- **Fetch source at sync/upgrade time** from the pinned git ref. Rejected — reintroduces
  network access and auth at upgrade time, and keeps content separate from the binary
  (preserving the drift axis this decision collapses).
- **Concede the gap** — revise PRJ-004 + README to declare the tool install operational-only,
  keep a checkout as the sanctioned propagation path. Rejected — leaves the golden path
  broken (B4–B6), forces adopters to clone, and contradicts the install-experience goal.
- **Define the bundle as what `pkit sync` propagates.** Rejected — sync-management is not a
  statement about tier, so it cannot answer *may this be distributed?* (Rationale), and it
  would make the bundle's contents depend on the build machine's capability registrations.

## Implications

- **Clarifies (does not supersede) PRJ-004.** PRJ-004's decision (direct git URL, no
  registry) is untouched; bundling is fully compatible with it. What changes is PRJ-004's
  imprecise *implication* that the wheel ships only the package. A one-line forward-pointer
  is added to PRJ-004 referencing this ADR.
- **CLI README correction.** The "works against any adopting project" claim becomes true once
  bundled; the README is updated to describe what the official install can do (closes
  scratchpad item B10).
- **Migration framework (COR-010) unchanged in contract, fixed in coverage.** The tier model
  holds; package-data-vs-checkout only changes where `find_source_kit()` points. The
  `migrations/` propagation omission is fixed in the same change (per `rules/core.md` #7,
  which presumes migrations reach adopters).
- **COR-007 follow-on: one predicate per question, not one declaration for both.** The wheel's
  force-include and the propagator's area set do not share a single declaration of the
  kit-owned tree, because *may this be distributed?* and *does sync propagate this?* are
  different questions and no single declaration serves both. §3 makes them differ by design
  (capability source ships but is never propagated), and sync-management additionally turns on
  a capability's *registration* while reading everything outside `.pkit/` as unmanaged. Each
  ownership question has exactly one definition instead — `is_adopter_owned_by_tier` (*may this
  be distributed?*) and `is_sync_managed` (*is this the kit's?*), both in
  `.pkit/lifecycle/ownership.py` — and the build asks the first rather than carrying its own
  copy of the rule.
- **The follow-on that remains.** Three hand-maintained enumerations of
  top-level `.pkit/` trees remain — the build hook's filtered set, `pyproject.toml`'s static
  force-include, and the propagator's area set. Merging them is *not* the fix; they are meant
  to differ. The live recurrence is narrower: a newly added tree that lands in none of them
  silently never ships, and that is currently caught by a test rather than prevented by
  construction. Recorded as the follow-on.
- **The artifacts' contents are a function of tracked state.** Two *clean* checkouts of one
  commit build the same file set, in the wheel and the sdist alike. The property follows from
  D1's rule: with the methodology bundle (`_kit/` in the wheel, `.pkit/` in the sdist) derived
  from a predicate over the tracked tree, two clean checkouts build the same methodology file
  set. "Tracked" means membership in the git index, minus files deleted from the working tree;
  the bytes shipped are the working tree's. So the property is about the file *set*, not the
  bytes: an uncommitted edit to a tracked file ships as edited. A wholesale include does not
  have the property — some adopter-owned state it would carry is git-ignored, so the artifact
  would depend on the build machine's untracked files (a released 1.149.0 wheel carried 14
  per-issue journals, one built from a working tree 36). A future change to what either
  artifact carries must preserve this. D1's directory-marker carve-out is held to the same bar:
  discovering the marker set from withheld files would read git-ignored state and emit a marker
  no clean clone produces, so *declaring* the set is what preserves the property — the
  declaration is load-bearing for this obligation, not a stylistic choice.
  A predicate over the tree is not yet a predicate over the *tracked* tree: a filesystem walk
  ships an untracked, non-ignored file in a local checkout (an editor backup, a `.DS_Store`).
  So the build enumerates tracked files (`git ls-files`; #909 for `.pkit/`, #930 for the rest)
  wherever the source has its own `.git`, for every file the hook ships — the whole sdist, and
  the wheel's package as well as its bundle — and fails rather than walk the tree when git
  cannot answer. Otherwise it walks the tree, and the walk is sound only under one
  precondition: a build from a git work tree, or from an artifact assembled from one (an sdist,
  or a git archive). A wheel built from an sdist is the common case — no `.git`, but the
  unpacked tree carries only tracked files because the sdist was assembled from them. When the
  hook sees neither a `.git` nor a `PKG-INFO` it warns, since it cannot tell such a tree from an
  arbitrary one; a git archive carries neither marker, so it builds with that warning even though
  it meets the precondition.
  **The property covers every file in both artifacts.** The Python package and the sdist's
  non-`.pkit` content are enumerated the same way as the bundle: hatchling's own walk is
  switched off for both, and the build hook force-includes them from the tracked set instead,
  because the walk can only be narrowed by static configuration and the tracked set changes
  with every commit. Two things sit outside, both bounded. The editable wheel's *package* is
  outside by construction: it ships a path to `src/`, not files, so whatever sits there imports
  — which is what an editable install is for. Its bundle is force-included like the standard
  wheel's, so that part stays inside. And hatchling adds a few root files to the sdist itself
  — `pyproject.toml`, the build hook, the root `.gitignore`, the README, the licence files —
  outside the hook's enumeration. Configuration names every one of them, so they cannot be
  strays. That includes the licence file, which `pyproject.toml` declares explicitly in
  `license-files`: left undeclared, hatchling finds licence files by glob (`LICEN[CS]E*`,
  `COPYING*`, `NOTICE*`, `AUTHORS*`), so an untracked `LICENSE.orig` at the root would ship in
  the sdist and in the wheel's `.dist-info`. Declaring it closes that residual too.
- **Wheel size** grows (all methodology content + capability source ship in `site-packages`),
  acceptable at current scale; revisit if a future capability bundles large binary assets.
- **Surface change** → version bump per PRJ-002, and the migration-coverage check runs against
  the propagation-set change.
- **Self-host coherence preserved.** In a project-kit checkout the real `.pkit/` wins
  (checkout-first), so self-host detection and dev live-edit are unaffected; the bundled
  `_kit/` is only consulted in adopter venvs, where self-host is never true.
- **One predicate-level divergence stays open.** `is_adopter_owned_by_tier` withholds a
  `project/` directory at any depth, while `is_sync_managed` reads the adopter tier by declared
  position; so a `project/` directory nested inside a kit-owned refresh root —
  `agents/core/project/…` — would be withheld from the bundle while the copy path refreshes it
  as kit content. No such path exists in this tree; the reconciliation is #838.
- **Two tests hold the predicates together, and neither claims more than it can see.** One
  walks the real tree and asserts no contradiction on it; the other asserts agreement on
  **declared** paths this repository does not have, such as the per-component manifest
  `install.py` writes at `.pkit/adapters/<name>/project/manifest.yaml` in every tool-installed
  adopter. The second exists because the first cannot see those paths: an assertion derived
  from the tree under test inherits that tree's blind spots, and the paths that matter most
  here are the ones only an adopter has. It is the marker tuple's declared-not-discovered
  argument, applied to the predicates.
- **Dependents stand on the version-lock, not on D1's mechanism.** The entry-point router's
  soundness argument (ADR-039), the per-project pin's content-locked-to-binary sequencing
  (ADR-049) and PRJ-004's clarified implication rest on the bundled content being
  version-locked to the binary, so how D1 computes its boundary does not move them.
