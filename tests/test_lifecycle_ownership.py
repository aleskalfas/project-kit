"""Tests for the lifecycle layer's tier-ownership predicate (ADR-051 / COR-031).

`.pkit/lifecycle/ownership.py` answers "is this path the kit's to manage?" for
every consumer that needs it — a question whose one production consumer is the
agent-overlay write-authority guard, not `pkit sync`, despite the predicate's
name. The module carries a second, narrower predicate —
`is_adopter_owned_by_tier` — whose cases are pinned in
`tests/test_packaging_boundary.py`, not here. Two things are pinned in this file:

- **the tier map** — each boundary instance ADR-051 traces, decided the way that
  record decides it; and
- **the single-implementation invariant** — the guard that fails if an adapter's
  resolver (or the backbone) grows its own copy of the rule instead of importing
  this one, which is the failure mode ADR-051 Decision point 3 forbids.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
OWNERSHIP_PATH = REPO / ".pkit" / "lifecycle" / "ownership.py"


def _load():
    spec = importlib.util.spec_from_file_location("pkit_ownership_under_test", OWNERSHIP_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


own = _load()


# --- fixtures ----------------------------------------------------------------

def _project(tmp_path: Path, *, capabilities: dict[str, str | None] | None = None) -> Path:
    """A project root with a backbone manifest registering *capabilities*.

    Values are the recorded origin, or None to register with the origin key
    omitted (which reads as `kit-shipped` per COR-031 D2).
    """
    root = tmp_path / "proj"
    (root / ".pkit").mkdir(parents=True)
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    for name, origin in (capabilities or {}).items():
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
        if origin is not None:
            lines.append(f"    origin: {origin}")
    (root / ".pkit" / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


# --- the tier map ------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "src/myproject/",
    "docs/architecture/",
    "CONTRIBUTING.md",
    "predicates/is-in-review.sh",
])
def test_outside_the_kit_tree_is_never_sync_managed(tmp_path: Path, path: str) -> None:
    """Adopter territory outside `.pkit/` is not propagated, so not managed."""
    assert own.is_sync_managed(_project(tmp_path), path) is False


@pytest.mark.parametrize("path", [
    ".pkit/agents/core/",
    ".pkit/agents/core/architect.md",
    ".pkit/decisions/core/COR-033-process-substrate.md",
    ".pkit/schemas/_defs/process.schema.json",
    ".pkit/process/README.md",
    ".pkit/rules/core.md",
    ".pkit/scratchpad/README.md",
    ".pkit/adapters/claude-code/deploy-agents.sh",
    ".pkit/lifecycle/ownership.py",
])
def test_core_areas_are_sync_managed(tmp_path: Path, path: str) -> None:
    """Core areas are refreshed on every sync — excluded like any other."""
    assert own.is_sync_managed(_project(tmp_path), path) is True


@pytest.mark.parametrize("path", [
    ".pkit/agents/project/overlay.yaml",
    ".pkit/decisions/project/PRJ-001-x.md",
    ".pkit/skills/project/mine.md",
    ".pkit/rules/project.md",
    ".pkit/scratchpad/active/note.md",
    ".pkit/scratchpad/done/note.md",
    ".pkit/project/config.yaml",
    ".pkit/manifest.yaml",
    ".pkit/version-pin",
])
def test_project_side_paths_are_not_sync_managed(tmp_path: Path, path: str) -> None:
    """The project half of the no-shared-files split is never overwritten."""
    assert own.is_sync_managed(_project(tmp_path), path) is False


def test_kit_shipped_capability_subtree_is_sync_managed(tmp_path: Path) -> None:
    root = _project(tmp_path, capabilities={"shipped": "kit-shipped"})
    assert own.is_sync_managed(root, ".pkit/capabilities/shipped/schemas/flow.yaml") is True
    assert own.is_sync_managed(root, ".pkit/capabilities/shipped/") is True


def test_registration_without_origin_reads_as_kit_shipped(tmp_path: Path) -> None:
    """COR-031 D2: an absent origin on read means `kit-shipped` (additive field)."""
    root = _project(tmp_path, capabilities={"legacy": None})
    assert own.is_sync_managed(root, ".pkit/capabilities/legacy/schemas/flow.yaml") is True


def test_project_tree_inside_kit_shipped_capability_is_adopter_owned(tmp_path: Path) -> None:
    """ADR-051's first boundary instance: adopter-owned *by tier*, so admissible."""
    root = _project(tmp_path, capabilities={"shipped": "kit-shipped"})
    assert own.is_sync_managed(root, ".pkit/capabilities/shipped/project/") is False
    assert own.is_sync_managed(
        root, ".pkit/capabilities/shipped/project/process/predicates/at-review.sh"
    ) is False


def test_incubated_capability_subtree_is_not_sync_managed(tmp_path: Path) -> None:
    """COR-031 D1: an incubated capability has no kit source to reconcile against."""
    root = _project(tmp_path, capabilities={"mine": "incubated-in-repo"})
    assert own.is_sync_managed(root, ".pkit/capabilities/mine/schemas/renovation.yaml") is False


def test_unregistered_capability_subtree_is_not_sync_managed(tmp_path: Path) -> None:
    """ADR-051's second boundary instance: the bootstrap window before registration.

    Sync reconciles only what the component registry lists, so a just-authored
    subtree has nothing managing it — distinct from `read_capability_origin`,
    which collapses "unregistered" into the `kit-shipped` default.
    """
    root = _project(tmp_path, capabilities={"other": "kit-shipped"})
    assert own.is_sync_managed(root, ".pkit/capabilities/fresh/schemas/flow.yaml") is False


def test_no_manifest_means_nothing_is_registered(tmp_path: Path) -> None:
    root = tmp_path / "bare"
    (root / ".pkit").mkdir(parents=True)
    assert own.is_sync_managed(root, ".pkit/capabilities/anything/schemas/f.yaml") is False
    # Core areas do not depend on the registry, so they stay managed.
    assert own.is_sync_managed(root, ".pkit/agents/core/architect.md") is True


def test_unreadable_manifest_falls_back_to_kit_shipped(tmp_path: Path) -> None:
    """The conservative direction: an unparseable registry must not admit paths."""
    root = tmp_path / "broken"
    (root / ".pkit").mkdir(parents=True)
    (root / ".pkit" / "manifest.yaml").write_text("components: [oh: {no", encoding="utf-8")
    assert own.is_sync_managed(root, ".pkit/capabilities/anything/schemas/f.yaml") is True


def test_capabilities_container_itself_is_kit_owned(tmp_path: Path) -> None:
    assert own.is_sync_managed(_project(tmp_path), ".pkit/capabilities/") is True


def test_unknown_kit_subtree_reads_as_managed(tmp_path: Path) -> None:
    """Conservative under `.pkit/`: a tree the map does not know is not admissible.

    A false "not the kit's" hands out write authority over content the next
    refresh deletes, which is why the bias points this way. The converse is
    not as cheap as this test's name suggests: when the misjudged path is the
    adopter's own, there is nowhere else to point it (#823). Formerly: a
    false "not managed" hands out write authority over content sync overwrites.
    """
    assert own.is_sync_managed(_project(tmp_path), ".pkit/some-future-area/thing.yaml") is True


# --- entry normalisation -----------------------------------------------------

@pytest.mark.parametrize("written", [
    ".pkit/agents/core",
    ".pkit/agents/core/",
    "./.pkit/agents/core/",
    ".pkit/agents/project/../core/",
    "  .pkit/agents/core/  ",
])
def test_entry_forms_normalise_to_one_verdict(tmp_path: Path, written: str) -> None:
    assert own.is_sync_managed(_project(tmp_path), written) is True


def test_absolute_path_inside_the_tree_resolves(tmp_path: Path) -> None:
    root = _project(tmp_path)
    assert own.is_sync_managed(root, str(root / ".pkit" / "agents" / "core")) is True


@pytest.mark.parametrize("path", ["/etc/passwd", "../sibling-repo/.pkit/agents/core/", ""])
def test_entries_outside_the_tree_are_not_sync_managed(tmp_path: Path, path: str) -> None:
    """Nothing in the kit tree is named, so there is nothing for sync to manage.

    (Whether such an entry is *sensible* is a different question — the overlap
    check owns that; this predicate only reports what sync touches.)
    """
    assert own.is_sync_managed(_project(tmp_path), path) is False


# --- the write-carrying registry --------------------------------------------

def test_process_authoring_targets_is_write_carrying() -> None:
    """The category ADR-051 introduces is registered, and it is the only one.

    The single-consumer convention (ADR-051 Decision point 7) makes growth here
    a review-time event: a core agent citing a write-carrying category some other
    record introduced is the red flag, so the set is pinned rather than sampled.
    """
    assert own.WRITE_CARRYING_CATEGORIES == frozenset({"process-authoring-targets"})


def test_offences_only_reported_for_write_carrying_categories(tmp_path: Path) -> None:
    root = _project(tmp_path)
    managed = [".pkit/agents/core/", ".pkit/decisions/core/"]
    # A read-carrying category legitimately points at kit-shipped content.
    assert own.sync_managed_offences(root, "architecture-docs", managed) == []
    assert own.sync_managed_offences(root, "process-authoring-targets", managed) == managed


def test_offences_pass_adopter_owned_entries(tmp_path: Path) -> None:
    root = _project(tmp_path, capabilities={"mine": "incubated-in-repo"})
    ok = [".pkit/capabilities/mine/schemas/flow.yaml", "predicates/at-review.sh"]
    assert own.sync_managed_offences(root, "process-authoring-targets", ok) == []


def test_rejection_message_names_the_offending_path() -> None:
    lines = own.rejection_message("process-authoring-targets", [".pkit/agents/core/"])
    assert "sync-managed" in lines[0]
    assert ".pkit/agents/core/" in lines[0]
    joined = "\n".join(lines)
    assert "overlay.yaml" in joined and "pkit sync" in joined


def test_undefined_remediation_rules_out_adopt_for_write_carrying() -> None:
    lines = own.undefined_category_remediation("process-authoring-targets")
    assert lines is not None
    joined = "\n".join(lines)
    assert "pkit agents adopt" in joined and "cannot serve" in joined
    assert "pkit agents reconcile --write" in joined


def test_undefined_remediation_absent_for_ordinary_categories() -> None:
    """None means "the generic `adopt` advice applies" — adopt CAN serve these."""
    assert own.undefined_category_remediation("architecture-docs") is None


# --- the single-implementation invariant (ADR-051 Decision point 3) ----------
#
# The predicate is shared so a second harness cannot silently skip the check.
# These guards fail if a consumer grows its own copy instead of importing this
# module — the fork ADR-051 names, caught mechanically rather than by review.

_RESOLVER = REPO / ".pkit" / "adapters" / "claude-code" / "_resolve_agent.py"

# Decision content that only the shared module may carry. `kit-shipped` appears
# as prose in adapter READMEs, so the tokens are matched in their code form
# (quoted / hyphenated wire values) inside executables only.
_FORKED_RULE_TOKENS = (
    "incubated-in-repo",
    '"kit-shipped"',
    "'kit-shipped'",
    "process-authoring-targets",
)


def _adapter_executables() -> list[Path]:
    root = REPO / ".pkit" / "adapters"
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in (".py", ".sh"))


def test_resolver_delegates_to_the_shared_predicate() -> None:
    """The claude-code resolver consumes the module rather than deciding itself."""
    text = _RESOLVER.read_text(encoding="utf-8")
    assert '"lifecycle"' in text and '"ownership.py"' in text   # loads the shared module
    assert "sync_managed_offences" in text                     # … for the write check
    assert "undefined_category_remediation" in text            # … and for the remediation


@pytest.mark.parametrize("script", _adapter_executables(), ids=lambda p: p.name)
def test_no_adapter_executable_forks_the_ownership_rule(script: Path) -> None:
    """No adapter may re-derive the tier map or the write-carrying registry.

    Forward-looking on purpose: this covers every adapter script in the tree, so
    a future harness that reimplements origin handling fails here instead of
    shipping a resolver that quietly validates nothing.
    """
    text = script.read_text(encoding="utf-8")
    for token in _FORKED_RULE_TOKENS:
        assert token not in text, (
            f"{script.relative_to(REPO)} carries {token!r} — the ownership rule and the "
            f"write-carrying registry live once, in .pkit/lifecycle/ownership.py (ADR-051)."
        )


def test_backbone_reads_the_registry_rather_than_restating_it() -> None:
    """`agents_overlay` asks the module which categories are write-carrying."""
    text = (REPO / "src" / "project_kit" / "agents_overlay.py").read_text(encoding="utf-8")
    assert "WRITE_CARRYING_CATEGORIES" in text          # read from the module …
    assert "process-authoring-targets" not in text      # … never hard-coded here
    assert "ownership.py" in text


# --- nested adopter tiers (#823) ---------------------------------------------
#
# The tier rule was depth-1: it saw `.pkit/<area>/project/` and missed
# `.pkit/adapters/<harness>/settings/project/`, which nests one level deeper.
# The closing "everything else under `.pkit/` is the kit's" rule then claimed
# the adopter's own permission allow-list.

@pytest.mark.parametrize(
    "path",
    [
        ".pkit/adapters/claude-code/settings/project/settings.json",
        ".pkit/adapters/claude-code/settings/project/",
        ".pkit/adapters/claude-code/settings/project",
        ".pkit/adapters/some-future-harness/settings/project/settings.json",
        # The adapters AREA tier. An earlier revision of this fix excluded
        # `adapters` from the `<area>/project/` position and so *narrowed* the
        # tier here — the #823 defect one directory over.
        ".pkit/adapters/project/notes.md",
        ".pkit/adapters/project/",
        # The per-component adapter manifest: `install.py` registers it at
        # `.pkit/adapters/<name>/project/manifest.yaml` and `upgrade.py` reads
        # it. Absent from this repo (it is the source, not an adopter), which is
        # why only a declared case catches it.
        ".pkit/adapters/claude-code/project/manifest.yaml",
        ".pkit/adapters/claude-code/project/",
    ],
)
def test_the_declared_adopter_tier_positions_are_theirs(tmp_path: Path, path: str) -> None:
    """The adopter tier is declared by position, and the adapter settings pair is one.

    Depth-1 was too narrow — it missed this pair (#823). A depth-free
    `"project" in parts` test is too wide, and is what the first attempt here
    shipped: it claimed `agents/core/project/` too, which the copy path
    deletes. See `_ADOPTER_TIER_DIRS`.
    """
    assert own.is_sync_managed(_project(tmp_path), path) is False


@pytest.mark.parametrize(
    "path",
    [
        ".pkit/adapters/claude-code/settings/core/settings.json",
        ".pkit/adapters/claude-code/README.md",
        ".pkit/adapters/claude-code/settings/",
        # The cases with teeth: a `project` component that is NOT on the adopter
        # tier, because it sits inside a kit-owned refresh root. The first
        # revision of this test carried only the three above — none of which has
        # a `project` component at all, so they passed identically before and
        # after the widening and could not detect an over-wide rule. These fail
        # against a depth-free `"project" in parts` test, which is what the
        # first attempt at #823 shipped.
        ".pkit/agents/core/project/notes.md",
        ".pkit/skills/core/project/x.md",
        ".pkit/agents/core/project/",
    ],
)
def test_the_kit_side_of_the_settings_pair_is_unaffected(tmp_path: Path, path: str) -> None:
    """The fix widens the adopter's tier; it must not widen it over kit content.

    Guards the direction that matters for ADR-051: this predicate gates *write
    authority*, so a rule answering "not the kit's" too eagerly hands an agent
    write access to paths `refresh_owned_tree` overwrites and orphan-prunes.
    """
    assert own.is_sync_managed(_project(tmp_path), path) is True


def test_a_capability_subdir_named_project_stays_the_kits(tmp_path: Path) -> None:
    """ADR-012 Decision 2 pins the capability rule as top-level-only, positional.

    `_capability_owned` keys on `rel.parts[0] == "project"`, so a `project/`
    directory nested under a capability subdir refreshes like any kit content.
    This predicate must agree, or the write-authority guard grants access to
    paths the capability refresh deletes.
    """
    root = _project(tmp_path, capabilities={"shipped": "kit-shipped"})
    assert own.is_sync_managed(root, ".pkit/capabilities/shipped/schemas/project/flow.yaml") is True
    assert own.is_sync_managed(root, ".pkit/capabilities/shipped/project/config.yaml") is False


def test_a_write_carrying_category_may_name_the_adopters_settings(tmp_path: Path) -> None:
    """The real consumer, and the check that fails on the unfixed predicate.

    This is the falsifiable form of #823's acceptance: the originally-filed
    criterion asked that the file survive a `pkit sync`, which passed on the
    broken code too — sync never consults this predicate. The defect is only
    observable here, at the write-authority guard.
    """
    root = _project(tmp_path)
    category = sorted(own.WRITE_CARRYING_CATEGORIES)[0]
    adopter_owned = ".pkit/adapters/claude-code/settings/project/"

    assert own.sync_managed_offences(root, category, [adopter_owned]) == []
    # …while the kit's half of the same pair is still refused.
    assert own.sync_managed_offences(
        root, category, [".pkit/adapters/claude-code/settings/core/"]
    ) == [".pkit/adapters/claude-code/settings/core/"]


def test_the_two_predicates_do_not_contradict_on_this_tree() -> None:
    """Adopter-owned by tier implies not the kit's to manage — over the real tree.

    Not equality: the two answer different questions, and `is_sync_managed`
    additionally reads everything outside `.pkit/` as not-its and consults a
    capability's registration. The invariant that must hold is the one whose
    breach #823 reported — a path the tier rule calls the adopter's while this
    predicate claims it for the kit.
    """
    kit = REPO / ".pkit"
    claimed_by_both = []
    claimed_by_neither = []
    for path in kit.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(kit).as_posix()
        tier = own.is_adopter_owned_by_tier(rel)
        kits = own.is_sync_managed(REPO, f".pkit/{rel}")
        if tier and kits:
            claimed_by_both.append(rel)
        # Skip `capabilities/` for the converse: `is_sync_managed` also answers
        # "not the kit's" there for an unregistered or incubated capability —
        # a registration fact, not a tier one, and a documented difference
        # between the two predicates rather than a contradiction.
        if not tier and not kits and not rel.startswith("capabilities/"):
            claimed_by_neither.append(rel)

    # The direction #823 reported: the tier rule calls it the adopter's while
    # this predicate claims it for the kit.
    assert claimed_by_both == []
    # The converse, and the one that matters for write authority: this predicate
    # says "not the kit's" — so the guard grants write — while the tier rule does
    # not recognise it as the adopter's. The first revision of this test asserted
    # only the direction above, which is why it stayed silent on an over-wide
    # rule that granted write authority over kit content.
    assert claimed_by_neither == []


def test_the_two_predicates_agree_on_paths_this_repo_does_not_have() -> None:
    """The real-tree walk is blind to paths that exist only in adopters.

    project-kit is the source repo, so `.pkit/adapters/<name>/project/` — where
    `install.py` registers each adapter's component manifest — does not exist
    here. A tree walk therefore cannot see it, which is how an earlier revision
    of this fix shipped a contradiction on exactly that path. These are declared
    rather than discovered for the same reason `ADOPTER_TIER_MARKERS` is (#813):
    an assertion derived from the tree under test inherits the tree's blind
    spots.
    """
    adopter_owned = [
        "project/config.yaml",
        "agents/project/mine.md",
        "adapters/project/notes.md",
        "adapters/claude-code/project/manifest.yaml",
        "adapters/claude-code/settings/project/settings.json",
    ]
    for rel in adopter_owned:
        assert own.is_adopter_owned_by_tier(rel) is True, rel
        assert own.is_sync_managed(REPO, f".pkit/{rel}") is False, rel


# --- synced copies (living-docs DEC-001 point 1, ADR-055 point 3) -------------
#
# Place eligibility asks whether a path arrives as a synced copy: sync-managed,
# in a repository a sync copies into. Keyed on origin and on the repository
# being the methodology's source, never on the path.

def _source_repository(root: Path) -> Path:
    """Give *root* the two markers of the methodology's source repository.

    Source-shaped by construction. Sync runs over it only in
    `test_the_source_discriminator_agrees_with_syncs_own_decision`, under the
    route-1 simulation there, which makes sync's test hold: sync self-hosts and
    never reaches the refusal to propagate over the source (#1070), which it
    would meet under this suite's own code instead.
    """
    (root / "src" / "project_kit").mkdir(parents=True)
    (root / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    (root / ".pkit" / "cli").mkdir(parents=True, exist_ok=True)
    (root / ".pkit" / "cli" / "pkit").write_text("", encoding="utf-8")
    return root


@pytest.mark.parametrize("path", [
    ".pkit/decisions/README.md",
    ".pkit/cli/README.md",
    ".pkit/adapters/claude-code/README.md",
    ".pkit/capabilities/shipped/README.md",
])
def test_kit_trees_in_an_adopter_are_synced_copies(tmp_path: Path, path: str) -> None:
    root = _project(tmp_path, capabilities={"shipped": "kit-shipped"})
    assert own.is_methodology_source(root) is False
    assert own.is_synced_copy(root, path) is True


@pytest.mark.parametrize("path", [
    "README.md",
    "CONTRIBUTING.md",
    "docs/guide.md",
    ".pkit/capabilities/mine/README.md",        # incubated: the adopter's own source
    ".pkit/capabilities/fresh/README.md",       # unregistered: nothing copies it
    ".pkit/capabilities/shipped/project/notes.md",  # the project tier of a shipped one
    ".pkit/decisions/project/PRJ-001-x.md",
])
def test_what_no_sync_copies_is_never_a_synced_copy(tmp_path: Path, path: str) -> None:
    root = _project(tmp_path, capabilities={"shipped": "kit-shipped", "mine": "incubated-in-repo"})
    assert own.is_synced_copy(root, path) is False


def test_nothing_in_the_methodology_source_is_a_synced_copy(tmp_path: Path) -> None:
    """The source is what a sync copies from, so the kit's trees there are originals.

    They stay the kit's to manage — write authority does not move — which is
    exactly why this is a question of its own rather than `is_sync_managed`.
    """
    root = _source_repository(_project(tmp_path, capabilities={"shipped": "kit-shipped"}))
    assert own.is_methodology_source(root) is True
    for path in (".pkit/decisions/README.md", ".pkit/capabilities/shipped/README.md"):
        assert own.is_sync_managed(root, path) is True, path
        assert own.is_synced_copy(root, path) is False, path


def test_one_marker_alone_is_not_the_source(tmp_path: Path) -> None:
    """An adopter has the in-tree dispatcher; only the source has the package beside it."""
    root = _project(tmp_path)
    (root / ".pkit" / "cli").mkdir(parents=True)
    (root / ".pkit" / "cli" / "pkit").write_text("", encoding="utf-8")
    assert own.is_methodology_source(root) is False


def test_the_source_discriminator_is_the_routers(tmp_path: Path) -> None:
    """One idea of "the methodology's source", held by two modules that cannot share code.

    The router is on the stdlib-only hot path of the installed binary; this module
    is loaded by path where `project_kit` is not importable. They must agree.
    """
    from project_kit.router import is_source_checkout

    adopter = _project(tmp_path)
    source = _source_repository(_project(tmp_path / "src-repo"))
    for root in (adopter, source, REPO):
        assert own.is_methodology_source(root) is is_source_checkout(root), root


def test_the_source_discriminator_agrees_with_syncs_own_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The marker test and sync's test recognise the same repository (ADR-059).

    Holding the predicate to the router's markers holds one copy of the marker
    test to the other, not to sync's test: sync's could change and nothing would
    notice. So this asks sync. Route 1 is what makes the two agree — where the markers hold, the
    router execs that tree's dispatcher, which runs that tree's own package — so
    each tree is synced by the code route 1 would run there: its own package
    where the markers hold, and this test's checkout (the tool) everywhere else.
    Without that simulation the source-shaped tree meets the refusal to propagate
    over the source, the gap's answer (#1070; `test_source_repository_refusal.py`).
    """
    from project_kit import install, sync
    from project_kit.router import is_source_checkout

    class _Propagates(Exception):
        """Sync passed its self-host branch: it would copy into the tree."""

    def _propagates(*_args: object, **_kwargs: object) -> None:
        raise _Propagates

    # Nothing is written. The self-host branch's deploy and render steps are
    # stubbed, and so is provisioning, which would ask uv about the real
    # checkout's query commands; the first steps past the branch — the source
    # guard, then propagation — stop the run.
    monkeypatch.setattr(install, "run_installed_adapter_primitives", lambda _ctx: None)
    monkeypatch.setattr(install, "_render_runtime_ignore", lambda _ctx: None)
    monkeypatch.setattr(install, "provision_query_commands", lambda _ctx: None)
    monkeypatch.setattr(install, "refuse_if_source_kit_incomplete", _propagates)
    monkeypatch.setattr(install, "_install_area", _propagates)

    def sync_self_hosts(root: Path) -> bool:
        with monkeypatch.context() as route:
            if is_source_checkout(root):
                # Route 1 without the exec: the package that runs is the tree's
                # own, and `source_checkout_root` derives the checkout from the
                # running package's location.
                route.setattr(install, "__file__", str(root / "src" / "project_kit" / "install.py"))
            try:
                sync.run_sync(root)
            except _Propagates:
                return False
            return True

    adopter = _project(tmp_path)
    source = _source_repository(_project(tmp_path / "src-repo"))
    (source / ".pkit" / "decisions").mkdir()  # a source tree carries its decisions
    for root in (adopter, source, REPO):
        assert own.is_methodology_source(root) is sync_self_hosts(root), root
