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
  an undeclared resolver;
- a resolver that may run is run under the query policy — the anchor value
  and `--json`, the offline marker set, the base override removed, from the
  project root, once per anchor value — and answers the files of the working
  tree the anchor stands on: both checks ask an artefact when one of them
  changed, an answer naming no file makes the anchor dead, and the files
  count as anchored surface;
- a resolver that times out, exits non-zero, prints garbage or answers in
  another shape gives no answer: the anchor is unresolved, the page flagged,
  never passed;
- a resolver's script is provisioned as a validator's is.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import command_runner, provisioning
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_repository as fr
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, document, friction_config, guide

RESOLVER = "scripts/resolve.py"

# A resolver for `source` anchors: a source `<value>` is captured at
# `sources/<value>.md`, and denotes nothing without it. It refuses to answer
# unless run as the query policy runs it — the anchor value and `--json` as its
# arguments, the offline marker set, the base override removed, from the
# project root — and logs each value it is asked for to `$RESOLVER_LOG`, a file
# outside the project.
RESOLVING = """\
import json, os, sys
value, flag = sys.argv[1:]
offline = os.environ.get("PKIT_OFFLINE") == os.environ.get("UV_OFFLINE") == "1"
if flag != "--json" or not offline or "PKIT_CHECK_BASE" in os.environ:
    sys.exit("not run under the query policy")
if os.environ.get("RESOLVER_LOG"):
    with open(os.environ["RESOLVER_LOG"], "a") as log:
        log.write(value + "\\n")
captured = f"sources/{value}.md"
print(json.dumps({"paths": [captured] if os.path.isfile(captured) else []}))
"""

SOURCE_ANCHORS = {"path": ["src/cli/**"], "source": ["iso-8601"]}
CAPTURED = {"sources/iso-8601.md": "ISO 8601, as captured.\n"}


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


def _start(adopter: AdopterRepo, files: dict[str, str], config: str | None = None) -> None:
    """Commit the base state on `main` (the install and the fixture capability
    included) and branch `feature` off it."""
    adopter.write({CONFIG: config or friction_config(), **SOURCE, **files})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _sources(adopter: AdopterRepo, script_body: str = RESOLVING) -> None:
    """The fixture capability `sources`, registering the kind `source` with its resolver."""
    _register(adopter.root, "sources", kinds={"source": "resolve"}, script_body=script_body)


def _of_anchor(findings: tuple[fc.Finding, ...], anchor: fd.Anchor) -> list[fc.Finding]:
    return [f for f in findings if f.anchor == anchor]


SOURCE_ANCHOR = fd.Anchor("source", "iso-8601")


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
    assert "never started" not in refused.message
    assert result.failing


# --- a registered resolver, run under the query policy ------------------------------------


def test_the_change_check_asks_when_a_file_the_resolver_answers_changed(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The base override is set, and never reaches the resolver (its script refuses it).
    monkeypatch.setenv("PKIT_CHECK_BASE", "main")
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})

    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    assert _of_anchor(fc.run_change_check(repo.root, "main").findings, SOURCE_ANCHOR) == []

    repo.commit("the standard is captured anew", {"sources/iso-8601.md": "ISO 8601, 2019.\n"})
    result = fc.run_change_check(repo.root, "main")
    [asked] = _of_anchor(result.findings, SOURCE_ANCHOR)
    assert asked.kind is fc.FindingKind.FRICTION
    assert asked.message.startswith(
        "changed in this diff (sources/iso-8601.md) and carries no answer"
    )
    assert result.failing


def test_the_whole_repository_check_finds_the_anchor_stale_after_its_file_changed(
    repo: AdopterRepo,
) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    current = fr.run_repository_check(repo.root)
    assert [r.state for r in current.artefact_reports] == [fr.ArtefactState.CURRENT]
    assert [f for f in current.findings if f.anchor == SOURCE_ANCHOR] == []

    changed = repo.commit("the standard is captured anew", {"sources/iso-8601.md": "2019.\n"})
    stale = fr.run_repository_check(repo.root)
    assert [r.state for r in stale.artefact_reports] == [fr.ArtefactState.STALE]
    [finding] = [f for f in stale.findings if f.anchor == SOURCE_ANCHOR]
    assert finding.kind is fr.RepositoryFindingKind.STALE
    assert finding.origin is not None and finding.origin.sha == changed


def test_a_resolver_runs_once_per_anchor_value_for_a_run(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    log = tmp_path_factory.mktemp("resolver") / "asked"
    monkeypatch.setenv("RESOLVER_LOG", str(log))
    _sources(repo)
    both = {"source": ["iso-8601", "rfc-3339"]}
    other = document("other", anchors=both, at="2026-10-01T09:00:00Z", outcome="updated")
    _start(
        repo,
        {
            "docs/guide.md": guide(anchors=both),
            "docs/other.md": other,
            **CAPTURED,
            "sources/rfc-3339.md": "RFC 3339.\n",
        },
    )
    fr.run_repository_check(repo.root)
    assert sorted(log.read_text(encoding="utf-8").split()) == ["iso-8601", "rfc-3339"]


def test_an_answer_naming_no_file_makes_the_anchor_dead_in_both_checks(repo: AdopterRepo) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={"source": ["iso-9999"]})})
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    [dead] = fc.run_change_check(repo.root, "main").findings
    assert dead.kind is fc.FindingKind.DEAD_ANCHOR
    assert dead.message == (
        "its resolver names no file for it; whether this diff removed what it denoted cannot be "
        "told, since a resolver answers for the working tree alone"
    )
    [whole] = [f for f in fr.run_repository_check(repo.root).findings if f.anchor is not None]
    assert (whole.kind, whole.message) == (
        fr.RepositoryFindingKind.DEAD_ANCHOR,
        "its resolver names no file for it",
    )


def test_the_files_a_resolver_answers_are_anchored_surface(repo: AdopterRepo) -> None:
    _sources(repo)
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED, "sources/x.md": "x\n"}
    _start(repo, files, friction_config(surface=["sources/**"]))
    result = fr.run_repository_check(repo.root)
    assert (result.surface, result.uncovered) == (2, ("sources/x.md",))


# --- no answer: the anchor is unresolved, the page flagged, never passed ------------------

ANSWERING = "import json\nprint(json.dumps({!r}))\n"


@pytest.mark.parametrize(
    ("script_body", "said"),
    [
        pytest.param(
            "import sys\nsys.stderr.write('the capture index is missing\\n')\nsys.exit(3)\n",
            "command 'resolve' exited 3: the capture index is missing",
            id="non-zero-exit",
        ),
        pytest.param(
            "print('sources/iso-8601.md')\n",
            "command 'resolve' did not print a JSON document on its standard output",
            id="garbage",
        ),
        pytest.param(
            ANSWERING.format({"files": ["sources/iso-8601.md"]}),
            "command 'resolve' printed no resolver answer: expected exactly",
            id="another-key",
        ),
        pytest.param(
            ANSWERING.format({"paths": "sources/iso-8601.md"}),
            "command 'resolve' answered `paths` that is not a list",
            id="not-a-list",
        ),
        pytest.param(
            ANSWERING.format({"paths": ["sources/iso-8601.md", "../outside.md"]}),
            "command 'resolve' answered '../outside.md', which is not a file of the working tree",
            id="outside-the-tree",
        ),
        pytest.param(
            ANSWERING.format({"paths": ["sources"]}),
            "command 'resolve' answered 'sources', which is not a file of the working tree",
            id="a-folder",
        ),
    ],
)
def test_a_resolver_that_gives_no_answer_leaves_the_anchor_unresolved(
    repo: AdopterRepo, script_body: str, said: str
) -> None:
    _sources(repo, script_body)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    _assert_unresolved(repo, said)


# Serial: the bound is one second, which a machine busy with other test workers misses.
@pytest.mark.serial
def test_a_resolver_that_overruns_its_bound_gives_no_answer(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sources(repo, "import time\ntime.sleep(60)\n")
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    _assert_unresolved(repo, "command 'resolve' did not answer within 1 s")


def _assert_unresolved(repo: AdopterRepo, said: str) -> None:
    """The anchor the base already carried is unresolved in both checks — the change
    check flags the page, failing in enforcing mode, though the diff did not add the
    anchor — and the explanation never shows it current."""
    result = fc.run_change_check(repo.root, "main")
    [unresolved] = _of_anchor(result.findings, SOURCE_ANCHOR)
    assert unresolved.kind is fc.FindingKind.UNRESOLVED_KIND
    assert unresolved.message.startswith(
        "its resolver gave no answer, so whether this diff changed what it denotes cannot be told: "
    )
    assert said in unresolved.message
    assert unresolved in result.failing

    whole = fr.run_repository_check(repo.root)
    [reported] = [f for f in whole.findings if f.anchor == SOURCE_ANCHOR]
    assert reported.kind is fr.RepositoryFindingKind.UNRESOLVED_KIND
    assert said in reported.message

    explained = CliRunner().invoke(main, ["friction", "explain", "docs/guide.md", "--json"])
    assert explained.exit_code == 0, explained.output
    assert '"state": "unresolved-kind"' in explained.output


# --- provisioning ---------------------------------------------------------------------------


def test_a_resolver_s_script_is_provisioned_as_a_validator_s_is(repo: AdopterRepo) -> None:
    metadata = "# /// script\n# dependencies = []\n# ///\n"
    _register(repo.root, "sources", kinds={"source": "resolve"}, script_body=metadata + RESOLVING)
    _register(repo.root, "tickets", kinds={"ticket": "resolve"}, contract=False)
    [command] = provisioning.query_commands(repo.root)
    assert (command.owner, command.reference) == ("sources", "resolve")
    provisioned = provisioning.provision(command, dry_run=True)
    assert provisioned.state is provisioning.State.WOULD_PROVISION
