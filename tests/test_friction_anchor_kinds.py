"""Anchor kinds a capability registers, and their resolvers (COR-050 point 2; #1261).

Every test stands up a real adopter repository with a fixture capability in it
— no shipped capability registers a kind — whose `package.yaml` registers
anchor kinds under `friction.kinds`, each naming a `commands:` leaf:

- the one registry reads the key: the leaf's script and whether it declares
  the query contract; a kind the backbone resolves is never registered, and a
  kind two capabilities register is refused for both;
- `pkit validate`'s `packages` member reports a resolver without the
  declaration, as it reports a validator and a filler without it, and a kind
  registered twice at each registration;
- the change check, reading the registry from the package metadata, refuses
  an undeclared resolver.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, friction_config, guide

RESOLVER = "scripts/resolve.py"


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _register(
    root: Path,
    name: str,
    *,
    kinds: dict[str, str],
    contract: bool = True,
    script_body: str | None = None,
) -> Path:
    """A fixture capability at `.pkit/capabilities/<name>/`, registered in the backbone
    manifest, registering each `kind -> command reference` under `friction.kinds`. Its
    one leaf, `resolve`, declares the query contract unless told not to; `script_body`
    writes the leaf's script, executable."""
    cap_dir = root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    declaration = "    query-contract: true\n" if contract else ""
    registered = "".join(f"    {kind}:\n      command: {ref}\n" for kind, ref in kinds.items())
    (cap_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n"
        f'description: Fixture capability registering anchor kinds.\nrequires_backbone: ">=0.1.0"\n'
        f"commands:\n  resolve:\n    script: {RESOLVER}\n    help: Resolve an anchor.\n"
        f"{declaration}friction:\n  kinds:\n{registered}",
        encoding="utf-8",
    )
    if script_body is not None:
        script = cap_dir / RESOLVER
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("#!/usr/bin/env python3\n" + script_body, encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability", name=name, manifest=f".pkit/capabilities/{name}/manifest.yaml"
        )
    )
    write_backbone_manifest(root, backbone)
    return cap_dir


def _start(adopter: AdopterRepo, files: dict[str, str]) -> None:
    """Commit the base state on `main` (the install and the fixture capability
    included) and branch `feature` off it."""
    adopter.write({CONFIG: friction_config(), **SOURCE, **files})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


# --- the registry reads the key -------------------------------------------------------


def test_the_registry_reads_each_installed_capability_s_kinds(repo: AdopterRepo) -> None:
    sources = _register(repo.root, "sources", kinds={"source": "resolve", "path": "resolve"})
    _register(repo.root, "tickets", kinds={"ticket": "resolve"}, contract=False)
    registry = fd.registered_anchor_kinds(repo.root)
    assert registry == {
        "source": fd.ResolverCommand(
            "source", "sources", "resolve", query_contract=True, script=sources / RESOLVER
        ),
        "ticket": fd.ResolverCommand(
            "ticket",
            "tickets",
            "resolve",
            query_contract=False,
            script=repo.root / ".pkit/capabilities/tickets" / RESOLVER,
        ),
    }
    # A kind the backbone resolves is never registered: its own resolution stands.
    assert "path" not in registry
    assert fd.unresolved_kind_reason("path", registry) is None


def test_a_kind_two_capabilities_register_is_refused_for_both(repo: AdopterRepo) -> None:
    _register(repo.root, "alpha", kinds={"source": "resolve"})
    _register(repo.root, "beta", kinds={"source": "resolve"})
    registry = fd.registered_anchor_kinds(repo.root)
    assert registry["source"].registrants == ("alpha", "beta")
    reason = fd.unresolved_kind_reason("source", registry)
    assert reason is not None
    assert "the capabilities alpha, beta each register it" in reason
    assert "none of their resolvers runs" in reason

    packages = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert packages.exit_code == 1, packages.output
    for name, other in (("alpha", "beta"), ("beta", "alpha")):
        assert f"error    .pkit/capabilities/{name}/package.yaml:/friction/kinds/source" in (
            packages.output
        )
        assert f"anchor kind 'source' is registered by {other} too" in packages.output


# --- the report at validation, and the refusal before a run ---------------------------


def test_the_packages_member_reports_a_resolver_without_the_declaration(
    repo: AdopterRepo,
) -> None:
    _register(repo.root, "sources", kinds={"source": "resolve"}, contract=False)
    packages = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert packages.exit_code == 1, packages.output
    assert (
        "error    .pkit/capabilities/sources/package.yaml:/friction/kinds/source/command"
        in packages.output
    )
    assert (
        "anchor kind 'source' names command 'resolve' as its resolver, which does not declare "
        "the query contract" in packages.output
    )


def test_the_change_check_refuses_an_undeclared_resolver_it_reads_from_the_package(
    repo: AdopterRepo,
) -> None:
    """The registry is read from package metadata, not handed in: the engine's
    refusal of a resolver without the declaration is reached from the key."""
    _register(
        repo.root,
        "sources",
        kinds={"source": "resolve"},
        contract=False,
        script_body="raise SystemExit('a refused resolver is never started')\n",
    )
    _start(repo, {"docs/guide.md": guide()})
    repo.commit(
        "anchor the guide to a source",
        {"docs/guide.md": guide(anchors={"path": ["src/cli/**"], "source": ["iso-8601"]})},
    )
    result = fc.run_change_check(repo.root, "main")
    [refused] = [f for f in result.findings if f.kind is fc.FindingKind.UNRESOLVED_KIND]
    assert refused.anchor == fd.Anchor("source", "iso-8601")
    assert (
        "the resolver `resolve` that sources registers for it does not declare the query "
        "contract" in refused.message
    )
    assert result.failing
