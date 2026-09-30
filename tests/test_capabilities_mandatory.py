"""The capability lifecycle as the one reader of the mandatory mark (#995, COR-053
point 6), with COR-030's direction split:

- the side carrying the mark — `install`, `register`, `upgrade` — is refused while
  a mandatory upstream is missing or at another interface version, the reason
  shown as the mark gives it; there is no `--force`, since the operator picks
  which version of the carrier to install;
- the side the mark targets — `upgrade`, `uninstall` — is warned, each
  counterpart named, and proceeds only under `--force`, never a hard block.

The marks are read from each capability's generated `depends-on` list — written
here by the refresh itself from the capability's process definitions — and
judged by the wiring resolver."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import capabilities as caps
from project_kit import cli as cli_mod
from project_kit import process_dependencies as deps
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

ISSUES = "tracker:issue-lifecycle"
DOCS = "pkit::documentation"
REVIEW = f"{DOCS}:review"
REASON = "it waits on issues"


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


@pytest.fixture
def kit_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch kit source the CLI installs and upgrades from; below the project
    root, so the project is never taken for the self-host."""
    source = tmp_path / "elsewhere" / ".kit-source"
    (source / "capabilities").mkdir(parents=True)
    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: source)
    return source


def _definition(process_id: str, depends_on: list[dict[str, Any]]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "id": "open",
        "meaning": "Open.",
        "detection": {"mode": "inferred", "predicate": {"run": "detect"}},
    }
    if depends_on:
        state["depends_on"] = depends_on
    return {
        "process": {
            "id": process_id,
            "version": 1,
            "subject": {"cardinality": "singleton"},
            "states": [state],
            "transitions": [],
        }
    }


def _coupling(upstream: str, *, mandatory: str | None = REASON, **extra: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "upstream": upstream,
        "relation": "gates-on-readiness",
        "mode": "pull",
        "why": "It starts once the upstream is ready.",
        **extra,
    }
    if mandatory is not None:
        entry["mandatory"] = {"reason": mandatory}
    return entry


def _capability(
    base: Path,
    name: str,
    version: str = "0.1.0",
    *,
    definitions: dict[str, list[dict[str, Any]]] | None = None,
    offers: dict[str, int] | None = None,
) -> Path:
    """A capability subtree under `base`: its process definitions, the processes it
    offers under the documentation role (address → interface version), and its
    generated `depends-on` list, produced by the refresh from the definitions."""
    cap_dir = base / name
    (cap_dir / "schemas").mkdir(parents=True, exist_ok=True)
    (cap_dir / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    package: dict[str, Any] = {
        "schema_version": 1,
        "component": {"kind": "capability", "name": name, "version": version},
        "description": f"Synthetic {name}.",
        "requires_backbone": ">=0.0.0",
    }
    if offers:
        package["connections"] = {
            "roles": [DOCS],
            "extension-points": {
                "offers": {
                    address: {
                        "kind": "process",
                        "schema_version": interface,
                        "process": address.rsplit(":", 1)[1],
                        "description": "An offered process.",
                    }
                    for address, interface in offers.items()
                }
            },
        }
    yaml = YAML()
    with (cap_dir / "package.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(package, handle)
    for process_id, depends_on in (definitions or {}).items():
        with (cap_dir / "schemas" / f"{process_id}.yaml").open("w", encoding="utf-8") as handle:
            yaml.dump(_definition(process_id, depends_on), handle)
    deps.refresh(cap_dir)
    return cap_dir


def _source(kit_source: Path, name: str, version: str = "0.1.0", **kwargs: Any) -> Path:
    return _capability(kit_source / "capabilities", name, version, **kwargs)


def _install(repo: AdopterRepo, kit_source: Path, name: str) -> None:
    source = caps.find_capability_in_source(kit_source, name)
    assert source is not None
    caps.install_capability(repo.root, source)


def _cli(*args: str) -> Any:
    return CliRunner().invoke(main, list(args))


# --- the side carrying the mark: refused ------------------------------------------


def test_install_refuses_a_mandatory_upstream_whose_capability_is_missing(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _source(kit_source, "flow", definitions={"flow": [_coupling(ISSUES)]})
    _source(kit_source, "tracker", definitions={"issue-lifecycle": []})

    refused = _cli("capabilities", "install", "flow")
    assert refused.exit_code != 0
    assert "capability 'flow' v0.1.0 has 1 unmet mandatory process connection(s):" in (
        refused.output
    )
    assert (
        f"- '{ISSUES}': its capability 'tracker' is not installed (mandatory: {REASON})"
        in refused.output
    )
    assert "Install or upgrade the upstream first, then retry (COR-053 point 6)." in refused.output
    assert not caps.is_installed(repo.root, "flow")

    assert _cli("capabilities", "install", "tracker").exit_code == 0
    installed = _cli("capabilities", "install", "flow")
    assert installed.exit_code == 0, installed.output


def test_install_refuses_a_mandatory_upstream_the_capability_does_not_define(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _source(kit_source, "tracker")
    _install(repo, kit_source, "tracker")
    _source(kit_source, "flow", definitions={"flow": [_coupling(ISSUES)]})
    refused = _cli("capabilities", "install", "flow")
    assert refused.exit_code != 0
    assert "'tracker' neither offers nor defines process 'issue-lifecycle'" in refused.output


def test_install_refuses_a_role_addressed_upstream_at_another_interface_version(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _source(kit_source, "docs-a", offers={REVIEW: 1})
    _install(repo, kit_source, "docs-a")
    _source(kit_source, "flow", definitions={"flow": [_coupling(REVIEW, version=2)]})
    refused = _cli("capabilities", "install", "flow")
    assert refused.exit_code != 0
    assert (
        f"- '{REVIEW}': 'docs-a' offers it at interface version 1, and the entry targets "
        f"version 2 (mandatory: {REASON})"
    ) in refused.output


def test_install_refuses_a_role_nobody_provides(repo: AdopterRepo, kit_source: Path) -> None:
    _source(kit_source, "flow", definitions={"flow": [_coupling(REVIEW)]})
    refused = _cli("capabilities", "install", "flow")
    assert refused.exit_code != 0
    assert f"no installed capability provides role '{DOCS}'" in refused.output


def test_an_optional_connection_never_refuses(repo: AdopterRepo, kit_source: Path) -> None:
    _source(kit_source, "flow", definitions={"flow": [_coupling(ISSUES, mandatory=None)]})
    result = _cli("capabilities", "install", "flow")
    assert result.exit_code == 0, result.output


def test_register_refuses_an_incubated_carrier_like_install(repo: AdopterRepo) -> None:
    cap_dir = _capability(
        repo.pkit / "capabilities", "flow", definitions={"flow": [_coupling(ISSUES)]}
    )
    # Every YAML under `schemas/` ships a companion (COR-018), as register checks.
    (cap_dir / "schemas" / "flow.schema.json").write_text('{"type": "object"}', encoding="utf-8")
    refused = _cli("capabilities", "register", "flow")
    assert refused.exit_code != 0
    assert f"'{ISSUES}': its capability 'tracker' is not installed" in refused.output
    assert not caps.is_installed(repo.root, "flow")


def test_upgrade_refuses_a_new_version_that_adds_an_unmet_mark(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _source(kit_source, "flow")
    _install(repo, kit_source, "flow")
    _source(kit_source, "flow", "0.2.0", definitions={"flow": [_coupling(ISSUES)]})
    refused = _cli("capabilities", "upgrade", "flow", "--force")
    assert refused.exit_code != 0  # `--force` is the target's override, never the carrier's
    assert "capability 'flow' v0.2.0 has 1 unmet mandatory process connection(s):" in (
        refused.output
    )
    assert caps.get_installed_capability_version(repo.root, "flow") == "0.1.0"


# --- the side the mark targets: warned, proceeds only under --force ----------------


def _wired(repo: AdopterRepo, kit_source: Path) -> None:
    """`flow` installed with a mandatory connection `tracker` meets."""
    _source(kit_source, "tracker", definitions={"issue-lifecycle": []})
    _source(kit_source, "flow", definitions={"flow": [_coupling(ISSUES)]})
    _install(repo, kit_source, "tracker")
    _install(repo, kit_source, "flow")


def test_uninstall_warns_and_refuses_then_proceeds_under_force(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _wired(repo, kit_source)

    refused = _cli("capabilities", "uninstall", "tracker")
    assert refused.exit_code != 0
    assert (
        "Warning: uninstalling 'tracker' would leave 1 mandatory process connection(s) unmet:"
    ) in refused.output
    assert (
        f"- 'flow' depends on '{ISSUES}': its capability 'tracker' is not installed "
        f"(mandatory: {REASON})"
    ) in refused.output
    assert "or pass --force to proceed anyway" in refused.output
    assert caps.is_installed(repo.root, "tracker")

    forced = _cli("capabilities", "uninstall", "tracker", "--force")
    assert forced.exit_code == 0, forced.output
    assert "Warning (--force): uninstalling 'tracker' leaves 1 mandatory process" in forced.output
    assert not caps.is_installed(repo.root, "tracker")


def test_upgrade_of_the_target_warns_and_proceeds_only_under_force(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _source(kit_source, "docs-a", offers={REVIEW: 1})
    _source(kit_source, "flow", definitions={"flow": [_coupling(REVIEW, version=1)]})
    _install(repo, kit_source, "docs-a")
    _install(repo, kit_source, "flow")
    # The provider's next version breaks the offered process's interface.
    _source(kit_source, "docs-a", "0.2.0", offers={REVIEW: 2})

    refused = _cli("capabilities", "upgrade", "docs-a")
    assert refused.exit_code != 0
    assert (
        "Warning: upgrading 'docs-a' to v0.2.0 would leave 1 mandatory process connection(s) unmet:"
    ) in refused.output
    assert (
        f"- 'flow' depends on '{REVIEW}': 'docs-a' offers it at interface version 2, and the "
        f"entry targets version 1 (mandatory: {REASON})"
    ) in refused.output
    assert caps.get_installed_capability_version(repo.root, "docs-a") == "0.1.0"

    forced = _cli("capabilities", "upgrade", "docs-a", "--force")
    assert forced.exit_code == 0, forced.output
    assert "Warning (--force): upgrading 'docs-a' to v0.2.0 leaves 1" in forced.output
    assert caps.get_installed_capability_version(repo.root, "docs-a") == "0.2.0"


def test_a_mark_already_unmet_is_not_the_operations_to_warn_about(
    repo: AdopterRepo, kit_source: Path
) -> None:
    """Only the marks the operation itself leaves unmet are named."""
    _wired(repo, kit_source)
    # A second carrier registered by hand, its mark unmet before anything moves.
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    _capability(
        repo.pkit / "capabilities", "stray", definitions={"stray": [_coupling("gone:nothing")]}
    )
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name="stray",
            manifest=".pkit/capabilities/stray/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(repo.root, backbone)

    broken = caps.mandatory_counterparts_left_unmet(repo.root, "tracker")
    assert [(b.capability, b.process) for b in broken] == [("flow", ISSUES)]
