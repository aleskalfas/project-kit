"""Tests for the wiring resolver (#983, COR-053 point 7): roles and the active
provider, counterparts at compatible and incompatible versions, unfilled points,
every kind of unmet mandatory mark, mandatory cycles, fingerprint disagreements,
each version relation, determinism — and the two passes of `pkit validate`
that carry the findings."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import capabilities as caps
from project_kit import config_validate as cv
from project_kit import connections as cx
from project_kit import package_validate as pv
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from project_kit.package_validate import Severity
from project_kit.report_context import project_config_path
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

ANY_BACKBONE = ">=0.0.0"
DOCS = "pkit::documentation"
READING = f"{DOCS}:reading-evidence"
PAGE_CREATED = f"{DOCS}:page-created"
REVIEW = f"{DOCS}:review"
ANALYSIS = "pkit::analysis"
GLOSSARY = f"{ANALYSIS}:glossary"


# --- staging synthetic capabilities --------------------------------------------


def _package(name: str, version: str = "0.1.0", **overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "schema_version": 1,
        "component": {"kind": "capability", "name": name, "version": version},
        "description": f"Synthetic {name}.",
        "requires_backbone": ANY_BACKBONE,
        # `publish` is every synthetic contribution's filler: a query command.
        "commands": {
            "publish": {"script": "scripts/publish.py", "help": "Publish.", "query-contract": True}
        },
    }
    raw.update(overrides)
    return raw


def _stage(
    repo: AdopterRepo,
    name: str,
    package: dict[str, Any],
    *,
    schemas: dict[str, Any] | None = None,
    definitions: tuple[str, ...] = (),
) -> Path:
    """Write `.pkit/capabilities/<name>/package.yaml` (+ companions) and register
    the capability as incubated, so its package is its version of record."""
    cap_dir = repo.pkit / "capabilities" / name
    (cap_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (cap_dir / "scripts" / "publish.py").write_text("", encoding="utf-8")
    (cap_dir / "schemas").mkdir(exist_ok=True)
    for file, document in (schemas or {}).items():
        (cap_dir / "schemas" / file).write_text(json.dumps(document), encoding="utf-8")
    for process_id in definitions:
        (cap_dir / "schemas" / f"{process_id}.yaml").write_text("process: {}\n", encoding="utf-8")
    yaml = YAML()
    with (cap_dir / "package.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(package, handle)
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(e.name == name for e in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=name,
                manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)
    return cap_dir / "package.yaml"


def _config(repo: AdopterRepo, text: str) -> None:
    path = project_config_path(repo.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _accepts(address: str = READING, version: int = 1, **extra: Any) -> dict[str, Any]:
    point: dict[str, Any] = {
        "schema_version": version,
        "schema": "reading-evidence.schema.json",
        "description": "What readers found.",
    }
    point.update(extra)
    return {address: point}


def _provider(
    name: str = "docs-a",
    *,
    role: str = DOCS,
    accepts: dict[str, Any] | None = None,
    offers: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    points: dict[str, Any] = {}
    if accepts is not None:
        points["accepts"] = accepts
    if offers is not None:
        points["offers"] = offers
    return _package(
        name,
        connections={"roles": [role], "extension-points": points},
        **overrides,
    )


def _contributor(
    name: str = "evidence",
    *,
    point: str = READING,
    version: int = 1,
    mandatory: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    entry: dict[str, Any] = {"point": point, "schema_version": version, "command": "publish"}
    if mandatory:
        entry["mandatory"] = {"reason": mandatory}
    return _package(name, connections={"extensions": {"contributes": [entry]}}, **overrides)


SCHEMA_A = {"type": "object", "properties": {"page": {"type": "string"}}}
SCHEMA_B = {"type": "object", "properties": {"page": {"type": "integer"}}}
COMPANIONS = {"reading-evidence.schema.json": SCHEMA_A}


def _located(repo: AdopterRepo, findings: tuple[cx.Finding, ...]) -> list[tuple[str, str]]:
    return [
        (cx._locate(repo.root, f), f.severity.value)  # pyright: ignore[reportPrivateUsage]
        for f in findings
    ]


def _role(wiring: cx.Wiring, role: str) -> cx.RoleBinding:
    return next(r for r in wiring.roles if r.role == role)


def _binding(wiring: cx.Wiring, capability: str) -> cx.Binding:
    return next(b for b in wiring.bindings if b.counterpart.capability == capability)


# --- roles and the active provider (COR-053 point 1) ---------------------------


def test_one_installed_provider_is_active_with_no_findings(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts()), schemas=COMPANIONS)
    wiring = cx.resolve_wiring(repo.root)
    assert _role(wiring, DOCS).active == "docs-a"
    assert [p.point.address for p in wiring.points] == [READING]
    assert wiring.findings == ()
    assert pv.resolve_active_roles(repo.root) == frozenset({DOCS})


def test_two_providers_without_a_selection_is_a_role_conflict(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts()), schemas=COMPANIONS)
    _stage(repo, "docs-b", _provider("docs-b", accepts=_accepts()), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor())
    wiring = cx.resolve_wiring(repo.root)
    role = _role(wiring, DOCS)
    assert role.providers == ("docs-a", "docs-b") and role.active is None and role.conflict
    assert wiring.points == ()  # nobody's points are defined
    assert _binding(wiring, "evidence").status is cx.BindingStatus.NO_ACTIVE_PROVIDER
    assert _located(repo, wiring.findings) == [
        (".pkit/project/config.yaml:/connections/providers", "error")
    ]
    message = wiring.findings[0].message
    # The exact command that resolves it, once per provider, and the entry it writes.
    assert (
        "select one with `pkit connections providers set pkit::documentation docs-a` or "
        "`pkit connections providers set pkit::documentation docs-b`, which writes the "
        "`connections.providers` entry `pkit::documentation: <one of them>`"
    ) in message


def test_a_provider_selection_resolves_the_conflict_and_the_other_provider_is_inert(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    # docs-a also plugs into another role: as the unselected provider, that is inert.
    _stage(
        repo,
        "docs-a",
        _provider("docs-a", accepts=_accepts())
        | {
            "connections": {
                "roles": [DOCS],
                "extension-points": {"accepts": _accepts()},
                "extensions": {"contributes": [{"point": GLOSSARY, "schema_version": 1}]},
            }
        },
        schemas=COMPANIONS,
    )
    _stage(repo, "docs-b", _provider("docs-b", accepts=_accepts()), schemas=COMPANIONS)
    _config(repo, f"connections:\n  providers:\n    {DOCS}: docs-b\n")
    wiring = cx.resolve_wiring(repo.root)
    role = _role(wiring, DOCS)
    assert role.selected == "docs-b" and role.active == "docs-b" and not role.conflict
    assert [p.point.provider for p in wiring.points] == ["docs-b"]
    assert _binding(wiring, "docs-a").status is cx.BindingStatus.INERT_PROVIDER
    assert _located(repo, wiring.findings) == [
        (".pkit/capabilities/docs-a/package.yaml:/connections/roles/0", "warning")
    ]
    assert "'docs-b' is the selected provider" in wiring.findings[0].message


def test_a_selection_naming_a_non_provider_leaves_the_role_unresolved_without_a_second_finding(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The configuration pass owns the invalid entry; the wiring does not report it twice."""
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts()), schemas=COMPANIONS)
    _stage(repo, "other", _package("other"))
    _config(repo, f"connections:\n  providers:\n    {DOCS}: other\n")
    wiring = cx.resolve_wiring(repo.root)
    assert _role(wiring, DOCS).active is None
    assert wiring.findings == ()
    report = cv.run_configuration_pass(repo.root)
    assert [f.path for f in report.errors] == [f"/connections/providers/{DOCS}"]
    assert "does not provide role" in report.errors[0].message
    assert "the installed providers of the role are 'docs-a'" in report.errors[0].message


# --- counterparts and versions (COR-053 point 5) --------------------------------


def test_contribution_at_a_compatible_version_is_bound(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts(version=2)), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(version=2))
    wiring = cx.resolve_wiring(repo.root)
    binding = _binding(wiring, "evidence")
    assert binding.status is cx.BindingStatus.BOUND
    assert binding.point is not None and binding.point.address == READING
    point = wiring.points[0]
    assert point.filled and [b.counterpart.capability for b in point.bound] == ["evidence"]
    assert wiring.findings == ()


def test_contribution_at_an_incompatible_version_is_inert_and_warned(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts(version=2)), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(version=1))
    wiring = cx.resolve_wiring(repo.root)
    assert _binding(wiring, "evidence").status is cx.BindingStatus.INERT_VERSION
    assert not wiring.points[0].filled
    assert _located(repo, wiring.findings) == [
        (
            ".pkit/capabilities/evidence/package.yaml:/connections/extensions/contributes/0",
            "warning",
        )
    ]
    assert "targets version 1, but 'docs-a' defines the point at version 2" in (
        wiring.findings[0].message
    )
    assert wiring.findings[0].relation is cx.Relation.POINT_VERSION


def test_unfilled_point_is_state_not_a_finding(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts()), schemas=COMPANIONS)
    wiring = cx.resolve_wiring(repo.root)
    assert not wiring.points[0].filled and wiring.points[0].bindings == ()
    assert wiring.findings == ()


def test_counterpart_to_an_absent_role_is_inert_and_silent_unless_mandatory(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "evidence", _contributor())
    wiring = cx.resolve_wiring(repo.root)
    assert _binding(wiring, "evidence").status is cx.BindingStatus.NO_ACTIVE_PROVIDER
    assert _role(wiring, DOCS).providers == ()
    assert wiring.findings == ()


def test_counterpart_to_a_point_the_active_role_does_not_define_is_warned(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts()), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(point=f"{DOCS}:reading-evidnece"))
    wiring = cx.resolve_wiring(repo.root)
    assert _binding(wiring, "evidence").status is cx.BindingStatus.NO_SUCH_POINT
    assert [f.severity for f in wiring.findings] == [Severity.WARNING]
    assert f"it defines: '{READING}'" in wiring.findings[0].message


def test_subscription_binds_to_an_event_and_never_to_a_data_point(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    offers = {
        PAGE_CREATED: {
            "kind": "event",
            "schema_version": 1,
            "description": "A page was written.",
            "command": "publish",
            "schema": "page-created.schema.json",
            "subject": "page",
        }
    }
    repo = make_adopter_repo()
    _stage(
        repo,
        "docs-a",
        _provider(accepts=_accepts(), offers=offers),
        schemas=COMPANIONS | {"page-created.schema.json": SCHEMA_A},
    )
    _stage(
        repo,
        "reactor",
        _package(
            "reactor",
            connections={
                "extensions": {
                    "subscribes": [
                        {"point": PAGE_CREATED, "schema_version": 1, "command": "publish"},
                        {"point": READING, "schema_version": 1, "command": "publish"},
                    ]
                }
            },
        ),
    )
    wiring = cx.resolve_wiring(repo.root)
    statuses = [b.status for b in wiring.bindings if b.counterpart.capability == "reactor"]
    assert statuses == [cx.BindingStatus.BOUND, cx.BindingStatus.NO_SUCH_POINT]


# --- mandatory marks (COR-053 point 6) -------------------------------------------


def test_mandatory_accepted_point_filled_only_by_the_default_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(
        repo,
        "docs-a",
        _provider(accepts=_accepts(mandatory={"reason": "pages need evidence"})),
        schemas=COMPANIONS,
    )
    _stage(repo, "evidence", _contributor(version=2))  # inert: wrong version
    wiring = cx.resolve_wiring(repo.root)
    errors = [f for f in wiring.findings if f.severity is Severity.ERROR]
    assert _located(repo, tuple(errors)) == [
        (
            ".pkit/capabilities/docs-a/package.yaml:/connections/extension-points/accepts/"
            f"{READING}/mandatory",
            "error",
        )
    ]
    assert "filled only by its default (declared but not delivered: 'evidence')" in (
        errors[0].message
    )
    assert "the mark is unmet (reason: pages need evidence)" in errors[0].message
    assert errors[0].relation is None  # a mandatory mark is a connection finding


def test_mandatory_contribution_at_an_incompatible_version_refuses_the_carrier_and_warns_the_target(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts(version=2)), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(version=1, mandatory="the pages cite it"))
    wiring = cx.resolve_wiring(repo.root)
    assert _located(repo, wiring.findings) == [
        (
            f".pkit/capabilities/docs-a/package.yaml:/connections/extension-points/accepts/{READING}",
            "warning",
        ),
        (".pkit/capabilities/evidence/package.yaml:/connections/extensions/contributes/0", "error"),
    ]
    assert "the mark is unmet (reason: the pages cite it)" in wiring.findings[1].message
    assert "target version 2 once its contract is met, or drop the mark" in (
        wiring.findings[1].message
    )
    assert "'evidence' carries a mandatory contributes entry" in wiring.findings[0].message
    assert "the error sits with 'evidence'" in wiring.findings[0].message
    # Both belong to the mandatory mark, so both sit under `connections`, not `versions`.
    assert wiring.version_findings() == ()


def test_mandatory_subscription_to_a_role_nobody_provides_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(
        repo,
        "reactor",
        _package(
            "reactor",
            connections={
                "extensions": {
                    "subscribes": [
                        {
                            "point": PAGE_CREATED,
                            "schema_version": 1,
                            "command": "publish",
                            "mandatory": {"reason": "it indexes every page"},
                        }
                    ]
                }
            },
        ),
    )
    wiring = cx.resolve_wiring(repo.root)
    assert [f.severity for f in wiring.findings] == [Severity.ERROR]
    assert "no installed capability provides role 'pkit::documentation'" in (
        wiring.findings[0].message
    )
    assert "install a capability that provides the role" in wiring.findings[0].message


def test_mandatory_counterpart_to_a_point_the_provider_lacks_warns_the_provider(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The direction split: the mark's carrier has the error, the target is warned."""
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts()), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(point=f"{DOCS}:gone", mandatory="the pages cite it"))
    wiring = cx.resolve_wiring(repo.root)
    assert _binding(wiring, "evidence").status is cx.BindingStatus.NO_SUCH_POINT
    assert _located(repo, wiring.findings) == [
        (".pkit/capabilities/docs-a/package.yaml:/connections/roles/0", "warning"),
        (".pkit/capabilities/evidence/package.yaml:/connections/extensions/contributes/0", "error"),
    ]
    assert f"it defines: '{READING}'" in wiring.findings[1].message
    assert "'evidence' carries a mandatory contributes entry" in wiring.findings[0].message


def _depends_on(*entries: dict[str, Any]) -> dict[str, Any]:
    return {
        "connections": {"extensions": {"depends-on": {"generated": True, "entries": list(entries)}}}
    }


def test_mandatory_depends_on_whose_upstream_is_missing_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(
        repo,
        "flow",
        _package("flow")
        | _depends_on(
            {"process": "tracker:issue-lifecycle", "mandatory": {"reason": "it waits on issues"}},
            {"process": REVIEW, "mandatory": {"reason": "it waits on reviews"}},
        ),
    )
    wiring = cx.resolve_wiring(repo.root)
    assert [b.status for b in wiring.bindings] == [
        cx.BindingStatus.NOT_INSTALLED,
        cx.BindingStatus.NO_ACTIVE_PROVIDER,
    ]
    messages = [f.message for f in wiring.findings]
    assert len(messages) == 2 and all("mandatory depends-on entry" in m for m in messages)
    assert "upstream capability 'tracker', which is not installed" in messages[0]
    assert "`pkit capabilities install tracker`" in messages[0]
    assert "no installed capability provides role 'pkit::documentation'" in messages[1]


def test_depends_on_upstream_exists_through_an_offered_point_or_a_definition_file(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    offers = {
        REVIEW: {
            "kind": "process",
            "schema_version": 3,
            "description": "The review process.",
            "process": "page-review",
        }
    }
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(offers=offers), definitions=("triage",))
    _stage(
        repo,
        "flow",
        _package("flow")
        | _depends_on(
            {"process": REVIEW, "schema_version": 3},  # role form, compatible
            {"process": REVIEW, "schema_version": 2},  # role form, inert
            {"process": "docs-a:page-review", "schema_version": 3},  # implementation form → point
            {"process": "docs-a:triage", "mandatory": {"reason": "x"}},  # definition file only
            {"process": "docs-a:nowhere", "mandatory": {"reason": "y"}},  # nothing
        ),
    )
    wiring = cx.resolve_wiring(repo.root)
    assert [b.status for b in wiring.bindings] == [
        cx.BindingStatus.BOUND,
        cx.BindingStatus.INERT_VERSION,
        cx.BindingStatus.BOUND,
        cx.BindingStatus.BOUND,
        cx.BindingStatus.NO_SUCH_POINT,
    ]
    assert _located(repo, wiring.findings) == [
        # The target of the unmet mandatory entry is warned, the file as a whole.
        (".pkit/capabilities/docs-a/package.yaml", "warning"),
        (
            ".pkit/capabilities/flow/package.yaml:/connections/extensions/depends-on/entries/1",
            "warning",
        ),
        (
            ".pkit/capabilities/flow/package.yaml:/connections/extensions/depends-on/entries/4",
            "error",
        ),
    ]
    assert wiring.findings[1].relation is cx.Relation.INTERFACE_VERSION
    assert "neither offers nor defines at schemas/nowhere.yaml" in wiring.findings[2].message
    assert wiring.checked[cx.Relation.INTERFACE_VERSION] == 3  # entries 0-2 carry a version


def test_mandatory_cycle_is_an_error_on_every_mark_in_it(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(
        repo,
        "docs-a",
        _provider(accepts=_accepts())
        | {
            "connections": {
                "roles": [DOCS],
                "extension-points": {"accepts": _accepts()},
                "extensions": {
                    "contributes": [
                        {"point": GLOSSARY, "schema_version": 1, "mandatory": {"reason": "terms"}}
                    ]
                },
            }
        },
        schemas=COMPANIONS,
    )
    _stage(
        repo,
        "analysis",
        _provider("analysis", role=ANALYSIS, accepts=_accepts(GLOSSARY))
        | {
            "connections": {
                "roles": [ANALYSIS],
                "extension-points": {"accepts": _accepts(GLOSSARY)},
                "extensions": {
                    "contributes": [
                        {"point": READING, "schema_version": 1, "mandatory": {"reason": "evidence"}}
                    ]
                },
            }
        },
        schemas=COMPANIONS,
    )
    wiring = cx.resolve_wiring(repo.root)
    assert all(b.status is cx.BindingStatus.BOUND for b in wiring.bindings)
    cycle = [f for f in wiring.findings if "mandatory cycle" in f.message]
    assert _located(repo, tuple(cycle)) == [
        (".pkit/capabilities/analysis/package.yaml:/connections/extensions/contributes/0", "error"),
        (".pkit/capabilities/docs-a/package.yaml:/connections/extensions/contributes/0", "error"),
    ]
    assert "among 'analysis', 'docs-a'" in cycle[0].message
    assert "no member could be installed first" in cycle[0].message


def test_no_cycle_is_drawn_through_a_role_in_conflict_until_a_provider_is_selected(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Which provider is selected decides whether a cycle exists, so a role without
    an active provider draws no edge: the conflict is the only finding until then."""
    repo = make_adopter_repo()
    for name in ("docs-a", "docs-b"):
        _stage(
            repo,
            name,
            _package(
                name,
                connections={
                    "roles": [DOCS],
                    "extension-points": {"accepts": _accepts()},
                    "extensions": {
                        "contributes": [
                            {"point": GLOSSARY, "schema_version": 1, "mandatory": {"reason": "t"}}
                        ]
                        if name == "docs-a"
                        else []
                    },
                },
            ),
            schemas=COMPANIONS,
        )
    _stage(
        repo,
        "analysis",
        _package(
            "analysis",
            connections={
                "roles": [ANALYSIS],
                "extension-points": {"accepts": _accepts(GLOSSARY)},
                "extensions": {
                    "contributes": [
                        {"point": READING, "schema_version": 1, "mandatory": {"reason": "e"}}
                    ]
                },
            },
        ),
        schemas=COMPANIONS,
    )
    conflicted = cx.resolve_wiring(repo.root)
    assert _located(repo, conflicted.findings) == [
        (".pkit/project/config.yaml:/connections/providers", "error")
    ]

    _config(repo, f"connections:\n  providers:\n    {DOCS}: docs-a\n")
    selected = cx.resolve_wiring(repo.root)
    cycle = [f for f in selected.findings if "mandatory cycle" in f.message]
    assert [(f.file.parent.name, f.severity.value) for f in cycle] == [
        ("analysis", "error"),
        ("docs-a", "error"),
    ]


# --- fingerprints (COR-053 point 5) ---------------------------------------------


def test_two_providers_with_different_schema_shapes_at_one_version_disagree(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts()), schemas=COMPANIONS)
    _stage(
        repo,
        "docs-b",
        _provider("docs-b", accepts=_accepts()),
        schemas={"reading-evidence.schema.json": SCHEMA_B},
    )
    _config(repo, f"connections:\n  providers:\n    {DOCS}: docs-a\n")
    wiring = cx.resolve_wiring(repo.root)
    disagreements = [f for f in wiring.findings if "different companion schemas" in f.message]
    assert _located(repo, tuple(disagreements)) == [
        (
            ".pkit/capabilities/docs-a/package.yaml:/connections/extension-points/accepts/"
            f"{READING}/schema",
            "error",
        ),
        (
            ".pkit/capabilities/docs-b/package.yaml:/connections/extension-points/accepts/"
            f"{READING}/schema",
            "error",
        ),
    ]
    fingerprints = {p.provider: p.fingerprint for p in wiring.declarations.points}
    assert fingerprints["docs-a"] != fingerprints["docs-b"]
    assert all(len(fp or "") == 64 for fp in fingerprints.values())


def test_same_shape_in_different_key_order_is_one_fingerprint(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts()), schemas=COMPANIONS)
    reordered = {"properties": {"page": {"type": "string"}}, "type": "object"}
    _stage(
        repo,
        "docs-b",
        _provider("docs-b", accepts=_accepts()),
        schemas={"reading-evidence.schema.json": reordered},
    )
    _config(repo, f"connections:\n  providers:\n    {DOCS}: docs-a\n")
    wiring = cx.resolve_wiring(repo.root)
    assert not any("different companion schemas" in f.message for f in wiring.findings)
    assert len({p.fingerprint for p in wiring.declarations.points}) == 1


# --- version relations (COR-030, COR-010) -----------------------------------------


def test_requires_backbone_outside_the_installed_backbone_is_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "old", _package("old", requires_backbone="<0.0.1"))
    wiring = cx.resolve_wiring(repo.root)
    assert _located(repo, wiring.findings) == [
        (".pkit/capabilities/old/package.yaml:/requires_backbone", "error")
    ]
    assert f"but {wiring.backbone_version} is installed" in wiring.findings[0].message


def test_capability_dependency_absent_and_out_of_range_split_by_direction(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "base", _package("base", version="2.0.0"))
    _stage(
        repo,
        "dependent",
        _package(
            "dependent",
            requires_capabilities=[
                {"name": "base", "version": ">=1.0.0,<2.0.0"},
                {"name": "gone", "version": ">=1.0.0"},
            ],
        ),
    )
    wiring = cx.resolve_wiring(repo.root)
    assert _located(repo, wiring.findings) == [
        (".pkit/capabilities/base/package.yaml:/component/version", "warning"),
        (".pkit/capabilities/dependent/package.yaml:/requires_capabilities/0", "error"),
        (".pkit/capabilities/dependent/package.yaml:/requires_capabilities/1", "error"),
    ]
    assert "outside the range declared by 'dependent (>=1.0.0,<2.0.0)'" in (
        wiring.findings[0].message
    )
    assert "but 2.0.0 is installed" in wiring.findings[1].message
    assert "`pkit capabilities install gone`" in wiring.findings[2].message


def test_a_dependency_range_naming_an_adapter_is_not_an_installed_capability(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """As the install gate reads it: only a capability satisfies `requires_capabilities`."""
    repo = make_adopter_repo()
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    adapter = next(e.name for e in backbone.components if e.kind == "adapter")
    _stage(
        repo,
        "dependent",
        _package("dependent", requires_capabilities=[{"name": adapter, "version": ">=0.0.0"}]),
    )
    wiring = cx.resolve_wiring(repo.root)
    assert [(f.path, f.relation) for f in wiring.findings] == [
        ("/requires_capabilities/0", cx.Relation.CAPABILITY_RANGE)
    ]
    assert "which is not installed" in wiring.findings[0].message


@pytest.mark.parametrize(
    ("version_range", "version", "admits"),
    [
        (">=0.1.0,<1.0.0", "0.5.0", True),
        (">=0.1.0,<1.0.0", "1.0.0", False),
        (" >=0.1.0, <1.0.0 ", "0.9.9", True),
        ("", "0.5.0", None),  # no range declared: no constraint
        ("not a range", "0.5.0", None),  # malformed: the packages pass reports it
        (">=0.1.0", "not a version", None),
        (None, "0.5.0", None),
        (">=0.1.0", None, None),
    ],
)
def test_range_admits_is_the_one_comparison_of_a_version_range(
    version_range: str | None, version: str | None, admits: bool | None
) -> None:
    assert cx.range_admits(version_range, version) is admits


def test_the_install_gate_and_validation_compare_a_dependency_range_alike(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Both read the range through `range_admits`, so they refuse the same versions."""
    repo = make_adopter_repo()
    dependency = {"name": "evidence", "version": ">=0.2.0,<1.0.0"}
    _stage(repo, "notes", _package("notes", requires_capabilities=[dependency]))
    for version, refused in (("0.1.0", True), ("0.2.0", False), ("1.0.0", True)):
        _stage(repo, "evidence", _package("evidence", version=version))
        validated = [
            f
            for f in cx.resolve_wiring(repo.root).errors()
            if f.relation is cx.Relation.CAPABILITY_RANGE
        ]
        gated = caps.check_capability_dependencies(
            repo.root, (caps.CapabilityDependency(**dependency),)
        )
        assert bool(validated) is bool(gated) is refused, version


def test_installed_version_of_record_comes_from_the_component_manifest(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A kit-shipped capability's installed version is what its manifest says."""
    repo = make_adopter_repo(capabilities=("evidence",))
    _stage(
        repo,
        "dependent",
        _package("dependent", requires_capabilities=[{"name": "evidence", "version": "<0.0.1"}]),
    )
    wiring = cx.resolve_wiring(repo.root)
    evidence = wiring.declarations.by_name("evidence")
    assert evidence is not None and evidence.version is not None
    assert any(f.path == "/requires_capabilities/0" for f in wiring.findings)


def test_no_filler_file_is_no_project_filler_and_resolve_judges_what_the_hook_reports() -> None:
    """Without a file at the filler path there is no project filler; `resolve`
    compares whatever version the hook reports, located at the filler (the
    filler files themselves: `tests/test_data_points.py`)."""
    assert cx.project_filler(Path("/nowhere"), READING) is None
    package = _provider(accepts=_accepts(version=2, mandatory={"reason": "r"}))
    installed = cx.Installed(
        "docs-a", "capability", "0.1.0", Path("/p/package.yaml"), Path("/p"), package
    )
    declarations = cx.Declarations.from_installed((installed,))
    filler_file = Path("/p/docs/reading-evidence.yaml")

    def filler(version: int) -> Callable[[str], cx.ProjectFiller | None]:
        def answer(_address: str) -> cx.ProjectFiller | None:
            return cx.ProjectFiller(filler_file, version)

        return answer

    filled = cx.resolve(declarations, cx.Selections(), "1.0.0", filler=filler(2))
    assert filled.points[0].filled and filled.findings == ()
    assert filled.checked[cx.Relation.FILLER_VERSION] == 1

    stale = cx.resolve(declarations, cx.Selections(), "1.0.0", filler=filler(1))
    assert not stale.points[0].filled  # a filler at another version fills nothing
    assert [(f.file, f.path, f.relation) for f in stale.version_findings()] == [
        (filler_file, "/schema_version", cx.Relation.FILLER_VERSION)
    ]
    assert [f.severity for f in stale.findings] == [Severity.ERROR, Severity.ERROR]
    assert "the project filler for" in stale.findings[0].message
    assert "its `schema_version` (COR-052 point 2)" in stale.findings[0].message


def test_rule_set_pins_are_a_version_relation_that_finds_nothing_without_rule_sets(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The pins themselves are covered in `test_rule_sets.py`."""
    repo = make_adopter_repo()
    assert cx.rule_set_pin_findings(()) == []
    assert cx.resolve_wiring(repo.root).checked[cx.Relation.RULE_SET_PIN] == 0


# --- contributor selection (COR-052 point 4) ------------------------------------


def test_two_contributors_to_a_single_point_need_a_selection(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts(combination="single")), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor("evidence"))
    _stage(repo, "notes", _contributor("notes"))
    wiring = cx.resolve_wiring(repo.root)
    assert _located(repo, wiring.findings) == [
        (".pkit/project/config.yaml:/connections/selections", "error")
    ]
    assert "'evidence', 'notes' contribute to it" in wiring.findings[0].message

    _config(repo, f"connections:\n  selections:\n    {READING}: notes\n")
    resolved = cx.resolve_wiring(repo.root)
    assert resolved.findings == () and resolved.points[0].selected == "notes"
    assert cv.run_configuration_pass(repo.root).errors == ()


def test_configuration_pass_checks_a_contributor_selection_for_real(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts(combination="union")), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor("evidence"))
    _stage(repo, "bystander", _package("bystander"))
    _config(
        repo,
        f"connections:\n  selections:\n    {READING}: evidence\n    {DOCS}:missing: evidence\n",
    )
    report = cv.run_configuration_pass(repo.root)
    messages = {f.path: f.message for f in report.errors}
    assert set(messages) == {
        f"/connections/selections/{READING}",
        f"/connections/selections/{DOCS}:missing",
    }
    assert (
        "is not a `single` point (declared: union)"
        in messages[f"/connections/selections/{READING}"]
    )
    assert (
        "no installed capability defines a data point"
        in messages[f"/connections/selections/{DOCS}:missing"]
    )

    _stage(repo, "docs-a", _provider(accepts=_accepts(combination="single")), schemas=COMPANIONS)
    _config(repo, f"connections:\n  selections:\n    {READING}: bystander\n")
    report = cv.run_configuration_pass(repo.root)
    assert len(report.errors) == 1
    assert "'bystander' declares no contribution" in report.errors[0].message
    assert "its installed contributors are 'evidence'" in report.errors[0].message
    assert report.by_severity(cv.Severity.INFO) == ()


def test_configuration_pass_findings_on_a_valid_selection_are_pinned(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Two providers of the role, one selected; two contributors to its `single` point,
    one at another version, one selected. The configuration pass finds nothing here, and
    reading the selections through the resolved wiring (ADR-057 point 2) must keep it so."""
    repo = make_adopter_repo()
    single = _accepts(combination="single")
    _stage(repo, "docs-a", _provider("docs-a", accepts=single), schemas=COMPANIONS)
    _stage(repo, "docs-b", _provider("docs-b", accepts=single), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor("evidence"))
    _stage(repo, "notes", _contributor("notes", version=2))
    _config(
        repo,
        f"connections:\n  providers:\n    {DOCS}: docs-a\n  selections:\n    {READING}: notes\n",
    )
    wiring = cx.resolve_wiring(repo.root)
    assert _role(wiring, DOCS).active == "docs-a"
    (point,) = wiring.points
    assert {b.counterpart.capability: b.status for b in point.bindings} == {
        "evidence": cx.BindingStatus.BOUND,
        "notes": cx.BindingStatus.INERT_VERSION,
    }
    assert cv.run_configuration_pass(repo.root).findings == ()


def test_a_contributor_selection_is_judged_against_the_active_providers_point(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The configuration pass reads the point the resolver defines — the active
    provider's — never another installed provider's declaration of it (COR-053 point 1)."""
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts={}), schemas=COMPANIONS)
    _stage(
        repo,
        "docs-b",
        _provider("docs-b", accepts=_accepts(combination="single")),
        schemas=COMPANIONS,
    )
    _stage(repo, "evidence", _contributor("evidence"))
    selection = f"  selections:\n    {READING}: evidence\n"

    # Only the unselected provider declares the point: the project defines none.
    _config(repo, f"connections:\n  providers:\n    {DOCS}: docs-a\n{selection}")
    (error,) = cv.run_configuration_pass(repo.root).errors
    assert error.path == f"/connections/selections/{READING}"
    assert error.message.startswith(
        f"'docs-a', the active provider of role '{DOCS}', defines no data point '{READING}' "
        f"— only 'docs-b' declare it"
    )

    # No active provider: the role conflict is the finding, not the selection too.
    _config(repo, f"connections:\n{selection}")
    assert cv.run_configuration_pass(repo.root).errors == ()
    assert [f.path for f in cx.resolve_wiring(repo.root).errors()] == [
        f"/connections/{cx.PROVIDERS_KEY}"
    ]

    # The active provider's point is `union`, whatever another provider declares.
    _stage(
        repo,
        "docs-a",
        _provider("docs-a", accepts=_accepts(combination="union")),
        schemas=COMPANIONS,
    )
    _config(repo, f"connections:\n  providers:\n    {DOCS}: docs-a\n{selection}")
    (error,) = cv.run_configuration_pass(repo.root).errors
    assert "is not a `single` point (declared: union)" in error.message


# --- the one resolver, for plans too (COR-053 point 8) --------------------------------


def test_a_plan_resolves_a_hypothetical_set_with_the_same_resolver(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A plan adds a candidate to the installed declarations and resolves; nothing
    on disk is read for the candidate beyond what its `Installed` carries."""
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider(accepts=_accepts()), schemas=COMPANIONS)
    live = cx.load_declarations(repo.root)
    candidate_dir = repo.root / "elsewhere" / "evidence"
    candidate = cx.Installed(
        "evidence",
        "capability",
        "0.1.0",
        candidate_dir / "package.yaml",
        candidate_dir,
        _contributor(),
    )
    plan = cx.resolve(
        cx.Declarations.from_installed((*live.installed, candidate)),
        cx.load_selections(repo.root),
        cx.resolve_wiring(repo.root).backbone_version,
    )
    assert _binding(plan, "evidence").status is cx.BindingStatus.BOUND
    assert plan.points[0].filled
    assert cx.resolve_wiring(repo.root).bindings == ()  # the live wiring is untouched


# --- what container validation reads (COR-053 point 10) -----------------------------


def test_container_wiring_carries_the_active_roles_and_their_data_points(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Each active role with its provider; each data point with its version and a
    validator built from its point schema — `$ref`s into a sibling companion
    resolve; a companion that does not parse leaves the point without one, and
    says why. An event point has no data to keep in an artefact."""
    broken = f"{DOCS}:broken"
    offers = {
        PAGE_CREATED: {
            "kind": "event",
            "schema_version": 1,
            "description": "A page was written.",
            "command": "publish",
            "schema": "page-created.schema.json",
            "subject": "page",
        }
    }
    repo = make_adopter_repo()
    package = _stage(
        repo,
        "docs-a",
        _provider(
            accepts=_accepts(version=2) | _accepts(broken, schema="broken.schema.json"),
            offers=offers,
        ),
        schemas={
            "reading-evidence.schema.json": {"$ref": "page.schema.json"},
            "page.schema.json": {"$id": "page.schema.json", **SCHEMA_A},
            "page-created.schema.json": SCHEMA_A,
        },
    )
    (package.parent / "schemas" / "broken.schema.json").write_text("{not json", encoding="utf-8")

    wiring = cx.container_wiring(repo.root)

    assert wiring.providers == {DOCS: "docs-a"}
    assert sorted(wiring.points) == [broken, READING]
    reading = wiring.points[READING]
    assert reading.version == 2 and reading.validator is not None
    assert not reading.validator.is_valid({"page": 5})  # through the sibling's `$ref`
    assert reading.validator.is_valid({"page": "index"})
    assert wiring.points[broken].validator is None
    assert "capabilities/docs-a/schemas/broken.schema.json is not valid JSON" in (
        wiring.points[broken].unavailable or ""
    )


# --- determinism and the shipped state -------------------------------------------


def test_same_input_twice_yields_identical_wiring(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _stage(
        repo,
        "docs-b",
        _provider("docs-b", accepts=_accepts(mandatory={"reason": "r"})),
        schemas=COMPANIONS,
    )
    _stage(
        repo,
        "docs-a",
        _provider("docs-a", accepts=_accepts()),
        schemas={"reading-evidence.schema.json": SCHEMA_B},
    )
    _stage(repo, "zeta", _contributor("zeta", version=2, mandatory="m"))
    _stage(
        repo,
        "alpha",
        _contributor("alpha", requires_capabilities=[{"name": "gone", "version": ">=1"}]),
    )
    first = cx.resolve_wiring(repo.root)
    second = cx.resolve_wiring(repo.root)
    assert first == second
    assert first.findings and first.findings == second.findings


def test_shipped_capabilities_wire_clean(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo(
        capabilities=(
            "evidence",
            "demo-recording",
            "living-docs",
            "software-analysis",
            "project-management",
            "software-engineering",
        )
    )
    wiring = cx.resolve_wiring(repo.root)
    assert wiring.findings == (), [f.message for f in wiring.findings]
    assert wiring.roles == () and wiring.points == () and wiring.bindings == ()


# --- `pkit validate` -----------------------------------------------------------------


def test_connections_member_carries_the_wiring_errors_the_packages_member_does_not(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts()), schemas=COMPANIONS)
    _stage(repo, "docs-b", _provider("docs-b", accepts=_accepts()), schemas=COMPANIONS)
    packages = pv.validate_installed_packages(repo.root)
    assert packages.errors == 0  # every file is well-formed
    outcome = cx.connections_outcome(repo.root)
    assert [f.location for f in outcome.errors] == [
        ".pkit/project/config.yaml:/connections/providers"
    ]


def test_pkit_validate_prints_the_connections_heading_and_fails_on_a_wiring_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts(version=2)), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(version=1, mandatory="the pages cite it"))
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    assert "connections" in result.output
    assert f"{DOCS} → docs-a" in result.output
    assert f"{READING} (data v2, docs-a) ← evidence (contributes, inert (version))" in result.output
    assert "1 error(s), 1 warning(s)" in result.output
    assert ".pkit/capabilities/evidence/package.yaml:/connections/extensions/contributes/0" in (
        result.output
    )


def test_pkit_validate_reports_a_wiring_warning_without_failing(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts(version=2)), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(version=1))
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "warning " in result.output and "is inert until the versions agree" in result.output


def test_pkit_validate_reports_version_relations_under_their_own_heading(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Each relation is counted, and each version finding is labelled with its
    relation under `versions`; the connections heading keeps its own findings."""
    repo = make_adopter_repo()
    _stage(repo, "docs-a", _provider("docs-a", accepts=_accepts(version=2)), schemas=COMPANIONS)
    _stage(repo, "evidence", _contributor(version=1))
    _stage(
        repo,
        "dependent",
        _package("dependent", requires_capabilities=[{"name": "gone", "version": ">=1"}]),
    )
    wiring = cx.resolve_wiring(repo.root)
    assert [f.relation for f in wiring.version_findings()] == [
        cx.Relation.CAPABILITY_RANGE,
        cx.Relation.POINT_VERSION,
    ]
    assert wiring.connection_findings() == ()
    assert wiring.checked[cx.Relation.CAPABILITY_RANGE] == 1
    assert wiring.checked[cx.Relation.POINT_VERSION] == 1
    assert wiring.checked[cx.Relation.BACKBONE_RANGE] >= 3  # every staged package declares one

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    connections, versions = result.output.split("  connections\n", 1)[1].split("  versions\n", 1)
    assert "0 error(s), 0 warning(s)" in connections
    assert "1 capability dependency range(s), 1 point version(s)" in versions
    assert "1 error(s), 1 warning(s)." in versions
    assert "/requires_capabilities/0  [capability dependency range]" in versions
    assert "/connections/extensions/contributes/0  [point version]" in versions
    assert versions.index("[capability dependency range]") < versions.index("[point version]")


def test_pkit_validate_says_when_nothing_is_wired(make_adopter_repo: MakeAdopterRepo) -> None:
    make_adopter_repo(capabilities=("evidence",))
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "no connection points declared by installed components." in result.output
    assert "  versions\n    checked: " in result.output
