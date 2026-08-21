"""Tests for the lifecycle layer's tier-ownership predicate (ADR-051 / COR-031).

`.pkit/lifecycle/ownership.py` answers "does `pkit sync` manage this path?" for
every consumer that needs it. Two things are pinned here:

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

    A false "managed" costs a rejected overlay entry the adopter re-points; a
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
