"""Tests for the capability permission-fragment authoring tooling (#172).

Two surfaces, both built on the already-shipped ADR-016 + ADR-021 mechanism:

- `pkit permissions scaffold <cap>` — stamps a capability's `permissions/`
  fragment skeleton (privilege-catalog.yaml + grants.yaml) with correct shapes
  + inline footgun guidance; refuses an unknown cap; refuses to clobber.
- the fragment-token-resolution lint wired into `pkit schemas validate` —
  fails a grant whose token resolves to no privilege in the MERGED catalog (the
  bare-vs-scoped fail-open case), passes a scoped one, passes when absent.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import permissions as perm
from project_kit import schemas_validate as schemas_mod
from project_kit.cli import main

REPO = Path(__file__).resolve().parent.parent


# --- scaffold ----------------------------------------------------------------


def _project_with_capability(tmp_path: Path, name: str = "demo") -> Path:
    """A minimal project tree with a stamped capability package.yaml."""
    proj = tmp_path / "proj"
    cap_dir = proj / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: " + name + "\n"
        "  version: 0.1.0\nrequires_backbone: \">=1.0.0,<2.0.0\"\n",
        encoding="utf-8",
    )
    return proj


def test_scaffold_stamps_both_fragment_files(tmp_path: Path) -> None:
    proj = _project_with_capability(tmp_path)
    stamped = perm.scaffold_fragment(proj, "demo")
    perms_dir = proj / ".pkit" / "capabilities" / "demo" / "permissions"
    catalog = perms_dir / "privilege-catalog.yaml"
    grants = perms_dir / "grants.yaml"
    assert catalog.is_file()
    assert grants.is_file()
    assert set(stamped) == {catalog, grants}


def test_scaffold_catalog_keys_are_bare_and_ban_guardrail(tmp_path: Path) -> None:
    """The catalog fragment guidance captures footgun 1 (bare keys) + the guardrail ban."""
    proj = _project_with_capability(tmp_path)
    perm.scaffold_fragment(proj, "demo")
    text = (
        proj / ".pkit" / "capabilities" / "demo" / "permissions" / "privilege-catalog.yaml"
    ).read_text(encoding="utf-8")
    # The illustrative key is bare (no `demo:` scope prefix on the key).
    assert "\n  ad-hoc-scraping:" in text
    assert "\n  demo:ad-hoc-scraping:" not in text
    # Both footguns are documented inline.
    assert "BARE" in text
    assert "guardrail: true" in text and "FORBIDDEN" in text


def test_scaffold_grants_uses_the_scoped_token(tmp_path: Path) -> None:
    """The grants fragment references the privilege with the SCOPED token (footgun 2)."""
    proj = _project_with_capability(tmp_path)
    perm.scaffold_fragment(proj, "demo")
    text = (
        proj / ".pkit" / "capabilities" / "demo" / "permissions" / "grants.yaml"
    ).read_text(encoding="utf-8")
    assert "[privilege-catalog:demo:ad-hoc-scraping]" in text
    assert "SCOPED" in text


def test_scaffold_refuses_unknown_capability(tmp_path: Path) -> None:
    """No package.yaml → unknown capability → refuse (don't stamp into a bare dir)."""
    proj = tmp_path / "proj"
    (proj / ".pkit").mkdir(parents=True)
    with pytest.raises(perm.PermissionsError, match="unknown capability"):
        perm.scaffold_fragment(proj, "ghost")


def test_scaffold_refuses_invalid_name(tmp_path: Path) -> None:
    proj = _project_with_capability(tmp_path)
    with pytest.raises(perm.PermissionsError, match="kebab-case"):
        perm.scaffold_fragment(proj, "Bad_Name")


def test_scaffold_no_clobber(tmp_path: Path) -> None:
    """An existing fragment file is left untouched; only the missing one is stamped."""
    proj = _project_with_capability(tmp_path)
    perms_dir = proj / ".pkit" / "capabilities" / "demo" / "permissions"
    perms_dir.mkdir(parents=True)
    authored = perms_dir / "grants.yaml"
    authored.write_text("schema_version: 1\ngrants: []\n", encoding="utf-8")

    stamped = perm.scaffold_fragment(proj, "demo")

    # grants.yaml survived untouched; only privilege-catalog.yaml was stamped.
    assert authored.read_text(encoding="utf-8") == "schema_version: 1\ngrants: []\n"
    assert stamped == [perms_dir / "privilege-catalog.yaml"]


def test_scaffold_is_idempotent_no_op_when_both_present(tmp_path: Path) -> None:
    proj = _project_with_capability(tmp_path)
    perm.scaffold_fragment(proj, "demo")
    second = perm.scaffold_fragment(proj, "demo")
    assert second == []


def test_scaffold_cli_stamps_and_reports(tmp_path: Path, monkeypatch) -> None:
    proj = _project_with_capability(tmp_path)
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["permissions", "scaffold", "demo"])
    assert result.exit_code == 0, result.output
    assert "privilege-catalog.yaml" in result.output
    assert "grants.yaml" in result.output
    assert (
        proj / ".pkit" / "capabilities" / "demo" / "permissions" / "grants.yaml"
    ).is_file()


def test_scaffold_cli_refuses_unknown_capability(tmp_path: Path, monkeypatch) -> None:
    proj = tmp_path / "proj"
    (proj / ".pkit").mkdir(parents=True)
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(main, ["permissions", "scaffold", "ghost"])
    assert result.exit_code != 0
    assert "unknown capability" in result.output


# --- fragment-token-resolution lint ------------------------------------------


def _lint_project(
    tmp_path: Path,
    *,
    cap_name: str,
    cap_catalog: str | None,
    cap_grants: str | None,
) -> Path:
    """A project tree with the real decision core + catalog, a manifest
    registering `cap_name`, and the capability's permission fragment(s)."""
    proj = tmp_path / "proj"
    (proj / ".pkit" / "schemas").mkdir(parents=True)
    for f in ("privilege-catalog.yaml", "privilege-catalog.schema.json"):
        shutil.copy(REPO / ".pkit" / "schemas" / f, proj / ".pkit" / "schemas" / f)
    (proj / ".pkit" / "permissions").mkdir(parents=True)
    shutil.copy(
        REPO / ".pkit" / "permissions" / "decide.py",
        proj / ".pkit" / "permissions" / "decide.py",
    )
    (proj / ".pkit" / "manifest.yaml").write_text(
        "schema_version: 1\nbackbone_version: 1.0.0\ncomponents:\n"
        f"  - kind: capability\n    name: {cap_name}\n"
        f"    manifest: .pkit/capabilities/{cap_name}/manifest.yaml\n",
        encoding="utf-8",
    )
    perms_dir = proj / ".pkit" / "capabilities" / cap_name / "permissions"
    perms_dir.mkdir(parents=True)
    (proj / ".pkit" / "capabilities" / cap_name / "package.yaml").write_text(
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {cap_name}\n"
        "  version: 0.1.0\nrequires_backbone: \">=1.0.0,<2.0.0\"\n",
        encoding="utf-8",
    )
    if cap_catalog is not None:
        (perms_dir / "privilege-catalog.yaml").write_text(cap_catalog, encoding="utf-8")
    if cap_grants is not None:
        (perms_dir / "grants.yaml").write_text(cap_grants, encoding="utf-8")
    return proj


_FRAG_CATALOG = (
    "schema_version: 1\nprivileges:\n"
    "  ad-hoc-scraping:\n"
    "    description: raw shell scrapers\n"
    "    recognize:\n      bash:\n        - cmd: curl\n"
)


def test_lint_fails_a_bare_token(tmp_path: Path) -> None:
    """A grant authored BARE against a capability privilege resolves to nothing —
    the fail-open case the lint exists to catch."""
    bare_grants = (
        "schema_version: 1\ngrants:\n"
        "  - subject: agent:researcher\n"
        "    privilege: '[privilege-catalog:ad-hoc-scraping]'\n"
        "    effect: deny\n"
    )
    proj = _lint_project(
        tmp_path, cap_name="trip-planning", cap_catalog=_FRAG_CATALOG, cap_grants=bare_grants
    )
    issues = perm.lint_capability_fragment_grants(proj)
    assert len(issues) == 1
    assert issues[0].token == "[privilege-catalog:ad-hoc-scraping]"
    assert "trip-planning:ad-hoc-scraping" in issues[0].fix_hint  # names the likely fix


def test_lint_passes_a_scoped_token(tmp_path: Path) -> None:
    """The correctly-scoped token resolves to the merged privilege — no issue."""
    scoped_grants = (
        "schema_version: 1\ngrants:\n"
        "  - subject: agent:researcher\n"
        "    privilege: '[privilege-catalog:trip-planning:ad-hoc-scraping]'\n"
        "    effect: deny\n"
    )
    proj = _lint_project(
        tmp_path, cap_name="trip-planning", cap_catalog=_FRAG_CATALOG, cap_grants=scoped_grants
    )
    assert perm.lint_capability_fragment_grants(proj) == []


def test_lint_passes_a_backbone_token(tmp_path: Path) -> None:
    """A deny against a backbone privilege is referenced bare and resolves fine."""
    backbone_grants = (
        "schema_version: 1\ngrants:\n"
        "  - subject: agent:project-manager\n"
        "    privilege: '[privilege-catalog:issue-tracker-write]'\n"
        "    effect: deny\n"
    )
    proj = _lint_project(
        tmp_path, cap_name="project-management", cap_catalog=None, cap_grants=backbone_grants
    )
    assert perm.lint_capability_fragment_grants(proj) == []


def test_lint_passes_when_no_fragment_present(tmp_path: Path) -> None:
    """A capability that ships no grants fragment contributes no issues."""
    proj = _lint_project(
        tmp_path, cap_name="trip-planning", cap_catalog=None, cap_grants=None
    )
    assert perm.lint_capability_fragment_grants(proj) == []


def test_lint_noop_without_decision_core(tmp_path: Path) -> None:
    """No propagated decide.py → no permission subsystem → lint is a no-op."""
    proj = tmp_path / "proj"
    (proj / ".pkit").mkdir(parents=True)
    assert perm.lint_capability_fragment_grants(proj) == []


def test_validate_all_surfaces_the_bare_token_issue(tmp_path: Path) -> None:
    """The lint is wired into `pkit schemas validate` (no-PATH gate)."""
    bare_grants = (
        "schema_version: 1\ngrants:\n"
        "  - subject: agent:researcher\n"
        "    privilege: '[privilege-catalog:ad-hoc-scraping]'\n"
        "    effect: deny\n"
    )
    proj = _lint_project(
        tmp_path, cap_name="trip-planning", cap_catalog=_FRAG_CATALOG, cap_grants=bare_grants
    )
    report = schemas_mod.validate_all(proj)
    assert not report.is_clean
    offending = [i for i in report.issues if "[privilege-catalog:ad-hoc-scraping]" in i.message]
    assert len(offending) == 1
    assert "permissions/grants.yaml" in offending[0].location
