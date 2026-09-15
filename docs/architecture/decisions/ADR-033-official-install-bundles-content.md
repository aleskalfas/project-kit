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
determines what's in. By that rule the bundle **excludes** adopter-owned subtrees (for example
a `project/` directory at any depth, such as `decisions/project/` or
`capabilities/<name>/project/`; the maintainer's `scratchpad/{active,done,dropped}` notes;
`manifest.yaml`; and `.gitignore` — illustrative of the rule's reach, not an
authoritative list).

**Build caches are excluded by a second mechanism, not by this rule.** `__pycache__`, `.pyc`
and `.pyo` are not adopter-owned — the ownership predicate answers False for them — and
`pyproject.toml`'s `exclude` cannot filter force-included paths, which is the whole reason the
hook exists. So the hook applies those patterns itself (`EXCLUDED_PARTS` / `EXCLUDED_SUFFIXES`
in `hatch_build.py`); omitting them shipped 87 `.pyc` files on the first attempt, trading 41
unwanted files for 87 different ones. Two obligations on the bundle, not one — an author who
reimplements it from the ownership rule alone reproduces that bug.

**The rule withholds adopter-owned *content*, not adopter-owned *shape* — one bounded exception
(#813).** The rule above cannot erase a directory's existence, because the installer reads the
bundle's shape as well as its contents: it stubs an adopter's `project/` tier only where the source
bundle *has* that directory (`(src / "project").is_dir()` for an area, `project_src.is_dir()`
for an adapter's settings pair). Withholding every file in such a directory therefore deleted
the directory from the artifact, and the official install silently stopped creating scaffolding
it had created before. So the wheel ships one **empty** `.gitkeep` at each of four *declared*
adopter-owned paths — `agents/project`, `permissions/project`, `skills/project`,
`adapters/claude-code/settings/project` (`ADOPTER_TIER_MARKERS` in `hatch_build.py`). They are
layout, not adopter data: each is asserted byte-empty by test, the set is declared in code
rather than discovered from the filesystem, and none reaches an adopter, because the install
path stubs those trees rather than copying them. **Finding `agents/project/.gitkeep` in the
wheel is this rule working, not a leak to fix.** The general principle, and the bar any future
exception must clear: a consumer that reads the artifact's *shape* constrains what the
ownership rule may erase — and the carve-out stays bounded, declared, empty, and test-asserted.
The amendment at the foot gives the mechanism and why the set is declared.

*Corrected (#813).* This point originally defined the set as "exactly what `pkit sync`
propagates", and inferred that the bundle could therefore never drift from what sync copies.
The set is now defined by tier ownership, deliberately **not** by the sync surface, and is
computed from one shared predicate rather than a hand-kept manifest. The amendment at the foot
of this record explains why the original mechanism could not answer the question D1 asks.

### 2. Checkout-first resolution is a contract

`find_source_kit()` returns a real checkout's `.pkit/` when `(.pkit/"decisions").is_dir()`
holds; otherwise it returns the bundled `project_kit/_kit/`, resolved via
`importlib.resources`. The bundle is a *fallback*, never consulted when a real checkout is
present, and is resolved so it can never be mistaken for a checkout `.pkit/`.

### 3. Capability source is a distribution medium, not an activation surface

All shipped capabilities' source travels in the wheel (the "repository"); `capabilities
install <name>` remains on-demand into the adopter (COR-017's opt-in boundary unchanged —
the existing available-in-source vs installed split).

**"Source" means the capability's kit-owned tier only** (clarified, #813). A capability's
`project/` subtree in this repo is *this project's* live instance state rather than anything
the capability ships — the reading ADR-012's amendment pins — so D1's rule withholds it. This
point decides that capability source is a *medium*, not that everything sitting under a
capability's directory travels; taking "all source travels" to license the whole subtree is
what shipped one project's config, its default-agent activation switch, its bootstrap stamp
and its per-issue journals to every adopter (#811). The medium-not-activation-surface decision
itself is unchanged.

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
exclusion all fall out of one existing rule. A blanket "copy `.pkit/`" rule would sweep
adopter-owned and maintainer-only artifacts into adopters — which is precisely what it did
until #813 made the boundary a predicate the build asks. *(This paragraph originally justified
keying the bundle on the sync-propagation surface, and claimed that guaranteed the wheel could
not drift from what sync copies; the amendment below retires both.)*

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
- **COR-007 follow-on, restated (#813) — do not read the original form as in progress.** As
  first written this said: two hand-maintained lists must agree (the wheel's force-include and
  the propagator's area set), and the robust design is *a single declaration of the kit-owned
  tree consumed by both build and propagator*. **That goal is retired**, because its premise
  is false: "may this be distributed?" and "does sync propagate this?" are different
  questions, so no single declaration can serve both. §3 already makes them differ by design
  (capability source ships but is never propagated), and sync-management additionally turns on
  a capability's *registration* while reading everything outside `.pkit/` as unmanaged. Each
  question now has exactly one definition instead — `is_adopter_owned_by_tier` and
  `is_sync_managed`, both in `.pkit/lifecycle/ownership.py` — and the build asks the first
  rather than carrying its own copy of the rule. One predicate per question, each defined
  once, is the better shape; measured against the original wording that is *further* away,
  measured against the recurrence it was reacting to it is closer.
- **The follow-on that remains.** Three hand-maintained enumerations of
  top-level `.pkit/` trees remain — the build hook's filtered set, `pyproject.toml`'s static
  force-include, and the propagator's area set. Merging them is *not* the fix; they are meant
  to differ. The live recurrence is narrower: a newly added tree that lands in none of them
  silently never ships, and that is currently caught by a test rather than prevented by
  construction. Recorded as the sharpened follow-on.
- **The artifact's contents are a function of tracked state alone.** A property of D1's rule
  worth pinning here, because it was silently absent before: with the bundle derived from a
  predicate over the tracked tree, two builds of one commit carry the same content set. Under
  the original wholesale include they did not — some adopter-owned state that rode along is
  git-ignored, so the artifact depended on the build machine's untracked files (the released
  1.149.0 wheel carried 14 per-issue journals; a wheel built from a working tree carried 36).
  A future change to the bundle definition must preserve this. D1's directory-marker carve-out
  is the first thing that had to clear this bar and nearly failed it: discovering the marker set
  from withheld files read git-ignored state and emitted a marker no clean clone would produce
  (419 `_kit` entries against 418 for the same commit). *Declaring* the set is what preserves
  the property — the declaration is load-bearing for this obligation, not a stylistic choice.
- **Wheel size** grows (all methodology content + capability source ship in `site-packages`),
  acceptable at current scale; revisit if a future capability bundles large binary assets.
- **Surface change** → version bump per PRJ-002, and the migration-coverage check runs against
  the propagation-set change.
- **Self-host coherence preserved.** In a project-kit checkout the real `.pkit/` wins
  (checkout-first), so self-host detection and dev live-edit are unaffected; the bundled
  `_kit/` is only consulted in adopter venvs, where self-host is never true.

> **Amendment (#813 / PR #820) — the bundle is defined by tier ownership, not by the sync
> surface.** The short version: D1 said the wheel bundles "exactly what `pkit sync`
> propagates", and inferred from that framing that the bundle can "never drift from what sync
> copies". The framing was a *proxy* for what D1 actually set out to decide — the core/project
> ownership boundary — and the proxy does not hold. That boundary is now asked directly, as
> `.pkit/lifecycle/ownership.py`'s `is_adopter_owned_by_tier`, by both build targets: the
> wheel's build hook calls it per file, and the sdist mirrors it as an `exclude` glob because
> config globs cannot call a predicate. D1, §3, the corresponding Rationale paragraph and the
> COR-007 follow-on are corrected above, and D1 now also records the one bounded exception the
> new mechanism forced (next paragraph but one). Checkout-first resolution (§2) and the
> migrations-must-reach-adopters fix (§4) are untouched.
>
> **Why the old rule was wrong, not merely imprecise.** Sync-management is not a statement
> about tier. It additionally depends on whether a capability is *registered* — so the same
> file can answer differently depending on the build machine's manifest state — and it reads
> everything outside `.pkit/` as unmanaged, so `src/`, which legitimately ships, answers "not
> propagated". A rule keyed on it therefore cannot answer *may this be distributed?* And as
> stated the rule was never actually implemented: the wheel bundles the tree by
> `force-include`, which hatchling's `exclude` cannot filter, so eleven `.pkit/` trees shipped
> wholesale. **51 adopter-owned files travelled in the real 1.149.0 wheel** — every
> capability's `project/` subtree, plus this project's own permission allow-list from
> `adapters/<harness>/settings/project/`. Defining the bundle by the propagation surface is
> what permitted that: the definition pointed at a predicate with no opinion on the question
> being asked, so the packaging manifest kept its own idea of the boundary and nothing could
> notice they disagreed.
>
> **The new mechanism forced one carve-out: the bundle carries shape, not only content.**
> Replacing a wholesale `force-include` with a per-file one ships *files* — so a directory whose
> every file is withheld vanishes from the artifact altogether. That is not cosmetic, because
> `install.py` gates the adopter-side `project/` scaffolding on the source bundle *having* that
> directory. The four adopter-tier directories disappearing meant the official wheel install
> stopped stubbing `.pkit/<area>/project/` at all: a real regression, caught in review of this
> PR and structurally invisible to tests that assert file presence. The fix ships an empty
> `.gitkeep` at each of the four, declared as `ADOPTER_TIER_MARKERS` in `hatch_build.py`; D1
> states the carve-out and the bar a future one would have to clear. Note what this says about
> the boundary rule generally — `is_adopter_owned_by_tier` answers *may this content be
> distributed?*, and that is the only question it answers. Which directory *shapes* the artifact
> must carry is a separate fact, separately declared, because it is driven by a consumer rather
> than by ownership.
>
> **Why that set is declared in code rather than discovered from the tree.** Two failures, both
> measured on this branch. Collecting the parent of every withheld file made the artifact depend
> on untracked state — withheld files include git-ignored ones, so this working tree produced
> 419 `_kit` entries against 418 from a clean clone of the same commit, the extra marker standing
> for a directory that exists locally only because of untracked journals. And the sdist prunes
> `**/project`, so a wheel built *from* an sdist — what `pip install` does with a source
> distribution — found no such directory, emitted no markers, and restored the regression on the
> path most adopters take. A declared tuple lives in the code, and the code travels in both
> artifacts, so both build paths emit the same set; a test asserts the tuple against the source
> tree so the declaration cannot drift into fiction. Depth is deliberately not the rule — the
> tuple includes `adapters/claude-code/settings/project` at depth 3 because `install.py` gates
> that adapter's settings scaffolding on it. **Read that as "the tuple is not derived from depth",
> not as "a `project/` component at any depth is the adopter's".** The tuple is a declared
> enumeration of the adopter-tier *positions*, and the second reading is false: a `project/`
> directory nested below a kit-owned tier marker — inside an area's `core/`, or below a
> capability's top level, which [ADR-012](ADR-012-ownership-aware-tree-refresh.md) D2 pins as
> kit-owned — is refreshed and orphan-pruned by the copy primitive like any other kit content.
> An ownership predicate that answered "the adopter's" there would contradict the copy path.
>
> **The drift D1 called impossible does exist, on one path — and it is not the bundle's bug.**
> `.pkit/adapters/claude-code/settings/project/settings.json` is adopter-owned by tier (so the
> bundle withholds it) while `is_sync_managed` still calls it managed.
> `.pkit/adapters/claude-code/README.md` describes that file as the adopter's own
> project-specific additions, so the *sync* predicate is the side that is wrong. The same
> divergence settles the relation between the two sets: the bundle omits a path sync propagates,
> so bundle and sync surface merely **overlap** — neither contains the other, and the bundle is
> in particular not a superset of what sync copies. Tracked as **#823**, deliberately unfixed in
> PR #820 because correcting it changes adopter-visible sync behaviour and wants its own
> change-set. Recorded here so a future reader meets the divergence as a known, located bug
> rather than as evidence against this rule — do not reconcile it by reverting D1.
>
> **Closed (#823 / PR #844) — the divergence above no longer exists, and the set relation it
> settled does not survive it.** `is_sync_managed` now tests the adopter tier by declared
> **position** (`.pkit/project/`, `<area>/project/`, `capabilities/<name>/project/`,
> `adapters/<harness>/settings/project/`) before dispatching on capability registration, so the
> settings pair reads adopter-owned under both predicates. Measured against what `pkit sync`
> actually copies, the bundle is therefore a proper **superset** of the propagation surface
> rather than an overlapping set: it additionally carries capability source, which §3 decides
> ships and never propagates. The retired witness was in fact never sound — #823 also
> established that sync does not consult `is_sync_managed` at all, and sync never *copies*
> `settings/project/settings.json` (init seeds it from a constant, sync leaves it alone), so
> that path sat in the predicate's set and never in the propagation surface. And superset is
> the direction this record **requires**, not an accident it got away with: in an official
> install the bundle *is* the source sync reads, so anything sync propagates and the bundle
> withholds is silently un-propagated for every tool-installed adopter — D1's `.gitkeep`
> carve-out is that same obligation one level down, at shape rather than content. What survives
> of the overlap claim is narrower and owes nothing to #823: against what `is_sync_managed`
> calls *the kit's* — a different set from what sync copies — neither side contains the other,
> since `.pkit/release/` and `.pkit/README.md` are the kit's and deliberately undistributed,
> while the four `.gitkeep` markers are distributed and are not the kit's. That is the COR-007
> follow-on restated: *may this be distributed?* and *is this the kit's?* remain different
> questions. One predicate-level divergence stays open, with no instance in this tree:
> `is_adopter_owned_by_tier` is still depth-free where `is_sync_managed` is now positional, so a
> `project/` directory nested inside a kit-owned refresh root would be withheld from the bundle
> while sync copies it. A test now asserts the two agree over the real tree; the reconciliation
> is tracked separately.
>
> **The two descriptions that carried the retired phrasing were corrected in this PR.** PRJ-004's
> `pyproject.toml` implication and `.pkit/cli/README.md`'s install section both glossed the bundle
> as the propagation surface; each now defines it by tier ownership, matching D1. The phrase
> survives only where the retirement itself is what's being described — naming the gloss in order
> to disown it, never to define the bundle.
>
> **Amended in place, not superseded — and here is the line.** What this record decides is
> that the official install resolves methodology content from package data bundled in the
> wheel, version-locked to the binary. That is untouched, and so is D1's own stated intent:
> "the rule — not the list — is what this decides: the existing core/project ownership
> boundary determines what's in." What moved is *which mechanism expresses that boundary*, plus
> one guarantee inferred from the wrong mechanism — a refinement of how this decision's own
> rule is realised, not an overturning of the decision. Every dependent stands on the
> version-lock rather than on D1's mechanism, so none of them move: the entry-point router's
> soundness argument (ADR-039), the per-project pin's content-locked-to-binary sequencing
> (ADR-049), and PRJ-004's clarified implication. A superseding record would have to restate
> §2 through §4 verbatim to remain operative, splitting one live decision across two records
> for no semantic gain.
