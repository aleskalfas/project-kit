"""Anchor kinds a capability registers, and their resolvers (COR-050 point 2; #1261).

Every test stands up a real adopter repository with a fixture capability in it
— no shipped capability registers a kind (`tests.anchor_kind_capabilities`) —
whose `package.yaml` registers anchor kinds under `friction.kinds`, each naming
a `commands:` leaf:

- the one registry reads the key: the leaf's script and whether it declares
  the query contract; a kind the backbone resolves is never registered, a
  kind two capabilities register is refused for both, and a command naming no
  leaf says so before the declaration is looked for;
- `pkit validate`'s `packages` member reports a resolver without the
  declaration, as it reports a validator and a filler without it, and a kind
  registered twice at each registration;
- a resolver that may run is run under the query policy — `--json`, `--` and
  then the anchor value, the offline marker set, the base override removed,
  from the project root, once per anchor value, and never again in a check
  once it overran its bound — and answers the files the anchor stands on,
  read against the working tree's listing by the change check and against
  HEAD's files by the whole-repository check; both checks ask an artefact
  when one of them changed, and the files count as anchored surface;
- the change check fails what it can lay at the pull request: an anchor the
  diff added that resolves to nothing, an anchor it kept whose kind it left
  without a resolver, and a resolver's missing answer whoever added the
  anchor; an anchor it kept whose resolver names no file is reported, never
  failed;
- a resolver that times out, exits non-zero, prints garbage or answers in
  another shape gives no answer: the anchor is unresolved, never dead, and
  its artefact is not judged — its state is `unresolved`, never `current`,
  and `record-status` refuses it;
- validation and the writers admit an anchor, and a deferral, of any kind a
  word names; a kind nothing resolves is a report;
- what the engine sees of a change to what an anchor denotes — a rename, a
  file entering the answer, a repointed mapping whose file the answer names —
  and what it cannot, pinned as a stated limit: a file leaving the answer;
- a resolver's script is provisioned as a validator's is.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import command_runner, provisioning
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_repository as fr
from project_kit import friction_validate as fv
from project_kit import friction_write as fw
from project_kit.cli import main
from project_kit.manifest import read_backbone_manifest, write_backbone_manifest
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.anchor_kind_capabilities import ASKED, HANGING, RESOLVER, RESOLVING, register_kinds
from tests.friction_documents import CONFIG, SOURCE, T1, T2, document, friction_config, guide

# One whose source may be kept in two files: `sources/<value>.md` and an annex.
SEVERAL = (
    ASKED
    + """\
kept = [f"sources/{value}.md", f"sources/{value}-annex.md"]
print(json.dumps({"paths": [path for path in kept if os.path.isfile(path)]}))
"""
)
# One that finds a source through a shared index, and names the index with the file.
MAPPED = (
    ASKED
    + """\
index = "sources/index.json"
with open(index) as mapping:
    target = json.load(mapping).get(value)
print(json.dumps({"paths": [index, target] if target else []}))
"""
)
# One that names every file git tracks, whatever it is asked.
EVERYTHING = (
    ASKED
    + """\
import subprocess
tracked = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True).stdout
print(json.dumps({"paths": [path for path in tracked.split("\\0") if path]}))
"""
)

SOURCE_ANCHORS = {"path": ["src/cli/**"], "source": ["iso-8601"]}
CAPTURED = {"sources/iso-8601.md": "ISO 8601, as captured.\n"}


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The file the fixture resolver logs each value it is started for to."""
    log = tmp_path_factory.mktemp("resolver") / "asked"
    monkeypatch.setenv("RESOLVER_LOG", str(log))
    return log


def _start(adopter: AdopterRepo, files: dict[str, str], config: str | None = None) -> None:
    """Commit the base state on `main` (the install and the fixture capability
    included) and branch `feature` off it."""
    adopter.write({CONFIG: config or friction_config(), **SOURCE, **files})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _sources(adopter: AdopterRepo, script_body: str = RESOLVING) -> None:
    """The fixture capability `sources`, registering the kind `source` with its resolver."""
    register_kinds(adopter.root, "sources", kinds={"source": "resolve"}, script_body=script_body)


def _of_anchor(findings: tuple[fc.Finding, ...], anchor: fd.Anchor) -> list[fc.Finding]:
    return [f for f in findings if f.anchor == anchor]


SOURCE_ANCHOR = fd.Anchor("source", "iso-8601")


# --- the registry reads the key -------------------------------------------------------


def test_the_registry_reads_each_installed_capability_s_kinds(repo: AdopterRepo) -> None:
    sources = register_kinds(repo.root, "sources", kinds={"source": "resolve", "path": "resolve"})
    register_kinds(repo.root, "tickets", kinds={"ticket": "resolve"}, contract=False)
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
    register_kinds(repo.root, "alpha", kinds={"source": "resolve"})
    register_kinds(repo.root, "beta", kinds={"source": "resolve"})
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
    register_kinds(repo.root, "sources", kinds={"source": "resolve"}, contract=False)
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
    register_kinds(
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


def test_a_resolver_runs_once_per_anchor_value_for_a_run(repo: AdopterRepo, asked: Path) -> None:
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
    assert sorted(asked.read_text(encoding="utf-8").split()) == ["iso-8601", "rfc-3339"]


def test_an_answer_naming_no_file_makes_the_anchor_dead_for_the_whole_repository_check(
    repo: AdopterRepo,
) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={"source": ["iso-9999"]})})
    [whole] = [f for f in fr.run_repository_check(repo.root).findings if f.anchor is not None]
    assert (whole.kind, whole.message) == (
        fr.RepositoryFindingKind.DEAD_ANCHOR,
        "its resolver names no file for it",
    )


# --- the change check fails what it can lay at the pull request -----------------------------

ENFORCING = friction_config(mode="enforcing")
DEAD_SOURCE = fd.Anchor("source", "iso-9999")
CHECK = ["friction", "check", "--base", "main"]


def _unregister(root: Path, name: str) -> None:
    """Uninstall the fixture capability `name`: out of the manifest, its folder removed."""
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components = [c for c in backbone.components if c.name != name]
    write_backbone_manifest(root, backbone)
    shutil.rmtree(root / ".pkit" / "capabilities" / name)


def test_an_anchor_already_dead_on_the_base_is_reported_and_fails_no_unrelated_change(
    repo: AdopterRepo,
) -> None:
    """One dead source on the default branch must not fail every later pull request
    (COR-050 point 12): the anchor is reported as dead with nobody to lay it at."""
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={"source": ["iso-9999"]})}, ENFORCING)
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    result = fc.run_change_check(repo.root, "main")
    [dead] = result.findings
    assert (dead.kind, dead.anchor) == (fc.FindingKind.DEAD_UNATTRIBUTED, DEAD_SOURCE)
    assert dead.message == (
        "its resolver names no file for it; whether this diff removed what it denoted cannot be "
        "told — the whole-repository check reports it as dead"
    )
    assert result.failing == () and not result.failed
    shown = CliRunner().invoke(main, CHECK)
    assert shown.exit_code == 0, shown.output
    assert "dead-unattributed" in shown.output and "Result: passed" in shown.output


def test_a_change_that_deletes_what_a_kept_anchor_denotes_passes_the_change_check(
    repo: AdopterRepo,
) -> None:
    """The stated limit (the lifecycle README, "What the engine cannot see"): a resolver
    is asked about the head alone, so the change check cannot lay the dead anchor at the
    change that killed it. It reports it; the whole-repository check finds it dead."""
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED}, ENFORCING)
    repo.commit("the captured standard is removed", {"sources/iso-8601.md": None})
    result = fc.run_change_check(repo.root, "main")
    [dead] = _of_anchor(result.findings, SOURCE_ANCHOR)
    assert dead.kind is fc.FindingKind.DEAD_UNATTRIBUTED
    assert not result.failed
    [whole] = [f for f in fr.run_repository_check(repo.root).findings if f.anchor == SOURCE_ANCHOR]
    assert whole.kind is fr.RepositoryFindingKind.DEAD_ANCHOR


def test_a_change_that_adds_a_dead_anchor_fails(repo: AdopterRepo) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide()}, ENFORCING)
    added = guide(anchors={"path": ["src/cli/**"], "source": ["iso-9999"]}, at=T2, because="x")
    repo.commit("anchor the guide to a source nobody captured", {"docs/guide.md": added})
    result = fc.run_change_check(repo.root, "main")
    [dead] = _of_anchor(result.findings, DEAD_SOURCE)
    assert (dead.kind, dead.message) == (
        fc.FindingKind.DEAD_ANCHOR,
        "its resolver names no file for it; the anchor was added in this diff",
    )
    assert dead in result.failing and result.failed


# Serial: the bound is one second, which a machine busy with other test workers misses.
@pytest.mark.serial
@pytest.mark.parametrize(("mode", "exit_code"), [("enforcing", 1), ("warning", 0)])
def test_a_resolver_that_gives_no_answer_fails_the_change_check_in_enforcing_mode_alone(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, mode: str, exit_code: int
) -> None:
    """A missing answer fails closed though the diff did not add the anchor: the check
    could not do its work, and a pass nobody earned costs more than a second run."""
    _sources(repo, HANGING)
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED}
    _start(repo, files, friction_config(mode=mode))
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    result = CliRunner().invoke(main, CHECK)
    assert result.exit_code == exit_code, result.output
    assert "no-answer" in result.output
    assert "command 'resolve' did not answer within 1 s — run again; if it gives none again" in (
        result.output
    )


def _a_second_registrant(root: Path) -> None:
    register_kinds(root, "tickets", kinds={"source": "resolve"})


def _the_declaration_dropped(root: Path) -> None:
    package = root / ".pkit/capabilities/sources/package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8").replace("    query-contract: true\n", ""),
        encoding="utf-8",
    )


def _the_command_dropped(root: Path) -> None:
    package = root / ".pkit/capabilities/sources/package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8").replace("  resolve:\n", "  renamed:\n", 1),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("take_away", "reason"),
    [
        pytest.param(
            lambda root: _unregister(root, "sources"),
            "no installed component registers a resolver for it",
            id="the-capability-uninstalled",
        ),
        pytest.param(
            _a_second_registrant,
            "the capabilities sources, tickets each register it",
            id="a-second-registrant",
        ),
        pytest.param(
            _the_declaration_dropped,
            "does not declare the query contract",
            id="the-declaration-dropped",
        ),
        pytest.param(
            _the_command_dropped,
            "is not declared in the `commands:` of sources",
            id="the-command-dropped",
        ),
    ],
)
def test_a_change_that_takes_a_kind_s_resolver_away_fails_on_every_kept_anchor_of_it(
    repo: AdopterRepo, take_away: Callable[[Path], None], reason: str
) -> None:
    """The base's registrations are read from the base commit, so the change that leaves
    a kind without a resolver that may run is the one that fails — not every change after."""
    _sources(repo)
    other = document("other", anchors={"source": ["iso-8601"]}, at=T1, outcome="updated")
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), "docs/other.md": other, **CAPTURED}
    _start(repo, files, ENFORCING)
    take_away(repo.root)
    repo.commit("the kind loses its resolver", files=None)

    result = fc.run_change_check(repo.root, "main")
    taken = _of_anchor(result.findings, SOURCE_ANCHOR)
    assert [f.location for f in taken] == ["docs/guide.md", "docs/other.md"]
    for finding in taken:
        assert finding.kind is fc.FindingKind.UNRESOLVED_KIND
        assert finding.message.startswith(
            "nothing installed resolves this kind, and this diff took its resolver away: "
        )
        assert reason in finding.message
    assert result.failed

    # Merged, the kind is unresolved at the base too: a later change is not failed on it.
    repo.checkout("main")
    repo.merge("feature")
    repo.checkout("later", create=True)
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    later = fc.run_change_check(repo.root, "main")
    assert _of_anchor(later.findings, SOURCE_ANCHOR) == [] and not later.failed


def test_a_kind_unresolved_at_the_base_and_at_head_is_the_whole_repository_check_s(
    repo: AdopterRepo,
) -> None:
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED}, ENFORCING)
    repo.commit("an unrelated change", {"README.md": "Readme.\n"})
    result = fc.run_change_check(repo.root, "main")
    assert result.findings == () and not result.failed
    [whole] = [f for f in fr.run_repository_check(repo.root).findings if f.anchor == SOURCE_ANCHOR]
    assert whole.kind is fr.RepositoryFindingKind.UNRESOLVED_KIND


def test_the_artefact_s_own_file_is_left_out_of_what_a_registered_anchor_is_asked(
    repo: AdopterRepo,
) -> None:
    """As for a path anchor: a page whose resolver names the page itself is not asked
    about its own edit."""
    _sources(repo, ANSWERING.format({"paths": ["docs/guide.md", "sources/iso-8601.md"]}))
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    repo.commit("reword the guide", {"docs/guide.md": guide(anchors=SOURCE_ANCHORS, body="New.")})
    assert _of_anchor(fc.run_change_check(repo.root, "main").findings, SOURCE_ANCHOR) == []

    repo.commit("the standard is captured anew", {"sources/iso-8601.md": "ISO 8601, 2019.\n"})
    [asked] = _of_anchor(fc.run_change_check(repo.root, "main").findings, SOURCE_ANCHOR)
    assert asked.message.startswith("changed in this diff (sources/iso-8601.md)")


def test_the_files_a_resolver_answers_are_anchored_surface(repo: AdopterRepo) -> None:
    _sources(repo)
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED, "sources/x.md": "x\n"}
    _start(repo, files, friction_config(surface=["sources/**"]))
    result = fr.run_repository_check(repo.root)
    assert (result.surface, result.uncovered) == (2, ("sources/x.md",))


# --- how a resolver is asked, and what its answer is read against --------------------------


def _kinds(repo: AdopterRepo) -> fd.AnchorKinds:
    """The registry's run over the working tree's one listing, as the change check takes it."""
    files = frozenset(fd.working_tree(repo.root).files())
    return fd.AnchorKinds(repo.root, fd.registered_anchor_kinds(repo.root), files)


@pytest.mark.parametrize("value", ["--help", "-x", "--json", "--"])
def test_a_value_is_never_read_as_an_option(repo: AdopterRepo, asked: Path, value: str) -> None:
    """The value comes last, after `--json` and the end-of-options marker."""
    _sources(repo)
    repo.write({f"sources/{value}.md": "Captured.\n"})
    resolution = _kinds(repo).resolve(fd.Anchor("source", value))
    assert resolution == fd.AnchorResolution(paths=(f"sources/{value}.md",))
    assert asked.read_text(encoding="utf-8").splitlines() == [value]


def test_a_value_the_system_cannot_pass_is_no_answer(repo: AdopterRepo, asked: Path) -> None:
    _sources(repo)
    resolution = _kinds(repo).resolve(fd.Anchor("source", "iso\x008601"))
    assert resolution.paths == () and not resolution.overran
    assert resolution.no_answer is not None
    assert resolution.no_answer.startswith("command 'resolve' could not start: ")
    assert not asked.exists()  # never started


def test_a_command_naming_no_leaf_says_so_before_the_declaration_is_looked_for(
    repo: AdopterRepo,
) -> None:
    register_kinds(repo.root, "sources", kinds={"source": "no such command"}, contract=False)
    registry = fd.registered_anchor_kinds(repo.root)
    assert registry["source"].script is None
    reason = fd.unresolved_kind_reason("source", registry)
    assert reason == (
        "the resolver `no such command` that sources registers for it is not declared in the "
        "`commands:` of sources"
    )
    assert _kinds(repo).resolve(fd.Anchor("source", "iso-8601")).no_answer == reason


# Serial: the bound is one second, which a machine busy with other test workers misses.
@pytest.mark.serial
def test_a_resolver_that_overran_its_bound_is_not_started_again_in_the_run(
    repo: AdopterRepo, asked: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three values and a hanging resolver cost one bound, not three."""
    _sources(repo, HANGING)
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    kinds = _kinds(repo)
    first, second, third = (kinds.resolve(fd.Anchor("source", v)) for v in ("a", "b", "c"))
    assert first.overran and first.no_answer == "command 'resolve' did not answer within 1 s"
    for later in (second, third):
        assert later.no_answer == (
            "command 'resolve' was not started again: it overran its bound for 'a' earlier in "
            "this check"
        )
    assert asked.read_text(encoding="utf-8").splitlines() == ["a"]
    # Another run asks again: the rule holds for the length of one check.
    assert _kinds(repo).resolve(fd.Anchor("source", "b")).overran


def test_an_untracked_file_is_an_answer_for_the_change_check_and_none_at_head(
    repo: AdopterRepo,
) -> None:
    """The change check reads the working tree's listing, the whole-repository check
    HEAD's files: a resolver reads the disk either way, and a path HEAD does not hold
    is no answer there — never a file with no history, read as current."""
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={"source": ["draft"]})})
    repo.write({"sources/draft.md": "Not committed.\n"})

    draft = fd.Anchor("source", "draft")
    [question] = _of_anchor(fc.run_change_check(repo.root, "main").findings, draft)
    assert question.kind is fc.FindingKind.FRICTION  # alive: the diff added what it stands on
    assert question.message.startswith("changed in this diff (sources/draft.md)")

    whole = fr.run_repository_check(repo.root)
    [unheld] = [f for f in whole.findings if f.anchor == draft]
    assert "command 'resolve' answered 'sources/draft.md', which is not a file of HEAD" in (
        unheld.message
    )


def test_the_whole_repository_readers_read_head_s_registrations_never_the_working_tree_s(
    repo: AdopterRepo,
) -> None:
    """`--all`, `explain`, `debt` and `record-status` read HEAD and its history, the
    registrations included: an uncommitted edit to a capability's package leaves the
    kind as HEAD registers it. Only the resolver, a command, reads the disk."""
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    _the_declaration_dropped(repo.root)  # uncommitted: the working tree's registration is refused
    assert fd.unresolved_kind_reason("source", fd.registered_anchor_kinds(repo.root)) is not None

    whole = fr.run_repository_check(repo.root)
    assert [r.state for r in whole.artefact_reports] == [fr.ArtefactState.CURRENT]
    assert [f for f in whole.findings if f.anchor == SOURCE_ANCHOR] == []
    explained = CliRunner().invoke(main, ["friction", "explain", "docs/guide.md", "--json"])
    assert explained.exit_code == 0, explained.output
    assert json.loads(explained.output)["state"] == "current"


def test_a_link_the_repository_holds_is_a_file_of_the_answer(repo: AdopterRepo) -> None:
    """A link is a file of the listing, never followed: the anchor stands on the link."""
    _sources(repo)
    repo.write({"README.md": "Readme.\n", "docs/guide.md": guide(anchors=SOURCE_ANCHORS)})
    (repo.root / "sources").mkdir()
    (repo.root / "sources" / "iso-8601.md").symlink_to("../README.md")
    _start(repo, {})
    assert _kinds(repo).resolve(SOURCE_ANCHOR).paths == ("sources/iso-8601.md",)
    whole = fr.run_repository_check(repo.root)
    assert [f for f in whole.findings if f.anchor == SOURCE_ANCHOR] == []


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
            "command 'resolve' answered '../outside.md', which is not a file of",
            id="outside-the-tree",
        ),
        pytest.param(
            ANSWERING.format({"paths": ["sources"]}),
            "command 'resolve' answered 'sources', which is not a file of",
            id="a-folder",
        ),
        pytest.param(
            "import json, os\n"
            "print(json.dumps({'paths': [os.path.abspath('sources/iso-8601.md')]}))\n",
            "sources/iso-8601.md', which is not a file of",
            id="an-absolute-path",
        ),
        pytest.param(
            ANSWERING.format({"paths": ["sources/ignored.md"]}),
            "command 'resolve' answered 'sources/ignored.md', which is not a file of",
            id="a-file-git-ignores",
        ),
        pytest.param(
            ANSWERING.format({"paths": ["sources/iso-8601.md", 8601]}),
            "command 'resolve' answered 8601, which is not a file of",
            id="an-entry-that-is-not-text",
        ),
        pytest.param(
            ANSWERING.format({"paths": ["sources/iso-8601.md"], "as-of": "2019"}),
            "command 'resolve' printed no resolver answer: expected exactly",
            id="a-key-beside-paths",
        ),
    ],
)
def test_a_resolver_that_gives_no_answer_leaves_the_anchor_unresolved(
    repo: AdopterRepo, script_body: str, said: str
) -> None:
    _sources(repo, script_body)
    ignored = {".gitignore": "sources/ignored.md\n", "sources/ignored.md": "On disk only.\n"}
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED, **ignored})
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
    assert unresolved.kind is fc.FindingKind.NO_ANSWER
    assert unresolved.message.startswith(
        "its resolver gave no answer, so whether this diff changed what it denotes cannot be told: "
    )
    assert said in unresolved.message
    assert unresolved.message.endswith(
        " — run again; if it gives none again, `pkit sync`, or the resolver needs mending"
    )
    assert unresolved in result.failing

    whole = fr.run_repository_check(repo.root)
    [reported] = [f for f in whole.findings if f.anchor == SOURCE_ANCHOR]
    assert reported.kind is fr.RepositoryFindingKind.NO_ANSWER
    assert said in reported.message
    # The artefact is not judged: its state says so, and is never current.
    assert [r.state for r in whole.artefact_reports] == [fr.ArtefactState.UNRESOLVED]

    explained = CliRunner().invoke(main, ["friction", "explain", "docs/guide.md", "--json"])
    assert explained.exit_code == 0, explained.output
    explanation = json.loads(explained.output)
    assert explanation["state"] == "unresolved"
    # The anchor says why; the artefact's other anchors show their own state.
    assert {a["kind"]: a["state"] for a in explanation["anchors"]} == {
        "path": "current",
        "source": "no-answer",
    }
    [finding] = explanation["findings"]
    assert finding["clears"].startswith("run again; if its resolver gives no answer again")


# --- an artefact with an anchor that cannot be resolved is not judged ----------------------

GARBAGE = "print('sources/iso-8601.md')\n"


@pytest.mark.parametrize(
    ("resolver", "kind"),
    [
        pytest.param(None, "unresolved-kind", id="a-kind-nothing-resolves"),
        pytest.param(GARBAGE, "no-answer", id="a-resolver-that-gave-no-answer"),
    ],
)
def test_an_artefact_with_an_unresolved_anchor_is_counted_unresolved_never_current(
    repo: AdopterRepo, resolver: str | None, kind: str
) -> None:
    if resolver is not None:
        _sources(repo, resolver)
    other = document("other", anchors={"path": ["src/core/**"]}, at=T1, outcome="updated")
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), "docs/other.md": other, **CAPTURED}
    _start(repo, files)
    changed = repo.commit("change the CLI", {"src/cli/main.py": "print('v2')\n"})

    result = CliRunner().invoke(main, ["friction", "check", "--all", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["schema_version"] == 1
    assert report["states"] == {
        "current": 1,
        "deferred": 0,
        "stale": 0,
        "unreachable": 0,
        "unresolved": 1,
    }
    states = {a["location"]: a["state"] for a in report["artefacts"]}
    assert states == {"docs/guide.md": "unresolved", "docs/other.md": "current"}
    # Unresolved wins over stale, and what its other anchors owe is still listed.
    found = [(f["kind"], f["anchor"]["kind"]) for f in report["findings"]]
    assert found == [("stale", "path"), (kind, "source")]
    assert report["counts"][kind] == 1
    assert report["findings"][0]["origin"]["commit"] == changed

    debt = json.loads(CliRunner().invoke(main, ["friction", "debt", "--json"]).output)
    assert debt["counts"]["unresolved"] == 1
    assert debt["unresolved"] == [{"artefact": "guide", "location": "docs/guide.md"}]
    assert [entry["location"] for entry in debt["debt"]] == ["docs/guide.md"]
    listed = CliRunner().invoke(main, ["friction", "debt"]).output
    assert "NOT JUDGED — an anchor that cannot be resolved" in listed


def test_record_status_refuses_an_artefact_with_an_unresolved_anchor_and_writes_nothing(
    repo: AdopterRepo,
) -> None:
    """A status is a judgment: `current` is never stamped on a page nobody could judge,
    nor a `since` an unread anchor could predate."""
    _sources(repo, GARBAGE)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    before = (repo.root / "docs/guide.md").read_text(encoding="utf-8")
    result = CliRunner().invoke(main, ["friction", "record-status", "docs/guide.md", "--yes"])
    assert result.exit_code != 0
    assert (
        "docs/guide.md cannot be judged: an anchor of it cannot be resolved (source iso-8601: "
        "its resolver gave no answer, so whether it changed cannot be told: command 'resolve' "
        "did not print a JSON document on its standard output). Nothing was written."
    ) in " ".join(result.output.split())
    assert (repo.root / "docs/guide.md").read_text(encoding="utf-8") == before


def test_an_excluded_artefact_s_registered_anchors_are_checked_and_it_is_not_judged(
    repo: AdopterRepo,
) -> None:
    _sources(repo)
    generated = document("generated", anchors={"source": ["iso-9999"]}, at=T1, outcome="updated")
    _start(
        repo,
        {"docs/generated/page.md": generated, "docs/guide.md": guide(anchors=SOURCE_ANCHORS)},
        friction_config(exclude=["docs/generated"]),
    )
    result = fr.run_repository_check(repo.root)
    assert [r.location for r in result.artefact_reports] == ["docs/guide.md"]
    assert [(f.location, f.kind) for f in result.findings if f.anchor == DEAD_SOURCE] == [
        ("docs/generated/page.md", fr.RepositoryFindingKind.DEAD_ANCHOR)
    ]


# --- what the engine sees of a change, and what it cannot ------------------------------------


def test_the_file_a_resolver_names_is_followed_through_a_rename(repo: AdopterRepo) -> None:
    """Its history is read from git as a record's is: a change made under its old name
    counts, and a pure rename is no change."""
    _sources(repo)
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), "drafts/iso-8601.md": "As drafted.\n"}
    _start(repo, files)
    repo.rename("drafts/iso-8601.md", "sources/iso-8601.md")
    renamed = fr.run_repository_check(repo.root)
    assert [r.state for r in renamed.artefact_reports] == [fr.ArtefactState.CURRENT]

    repo.rename("sources/iso-8601.md", "drafts/iso-8601.md")
    changed = repo.commit("redraft the standard", {"drafts/iso-8601.md": "Redrafted.\n"})
    repo.rename("drafts/iso-8601.md", "sources/iso-8601.md")
    stale = fr.run_repository_check(repo.root)
    [finding] = [f for f in stale.findings if f.anchor == SOURCE_ANCHOR]
    assert finding.kind is fr.RepositoryFindingKind.STALE
    assert finding.origin is not None and finding.origin.sha == changed


def test_a_file_that_enters_the_answer_asks_the_artefact(repo: AdopterRepo) -> None:
    """Growth is seen: the file's adding commit lies after the revalidation point."""
    _sources(repo, SEVERAL)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    added = repo.commit("an annex to the standard", {"sources/iso-8601-annex.md": "Annex.\n"})

    [asked] = _of_anchor(fc.run_change_check(repo.root, "main").findings, SOURCE_ANCHOR)
    assert asked.kind is fc.FindingKind.FRICTION
    assert asked.message.startswith("changed in this diff (sources/iso-8601-annex.md)")
    whole = fr.run_repository_check(repo.root)
    [stale] = [f for f in whole.findings if f.anchor == SOURCE_ANCHOR]
    assert stale.kind is fr.RepositoryFindingKind.STALE
    assert stale.origin is not None and stale.origin.sha == added


def test_a_file_that_leaves_the_answer_is_not_seen(repo: AdopterRepo) -> None:
    """A stated limit (the lifecycle README, "What the engine cannot see"): the engine
    reads the history of the files the answer names now, so one of several removed is
    a change nobody is asked about — in either check. A path anchor over the same
    files sees the deletion; a capability keeps the limit small with one value in one
    file, whose removal leaves the anchor dead."""
    _sources(repo, SEVERAL)
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED}
    _start(repo, {**files, "sources/iso-8601-annex.md": "Annex.\n"})
    repo.commit("the annex is withdrawn", {"sources/iso-8601-annex.md": None})

    assert _of_anchor(fc.run_change_check(repo.root, "main").findings, SOURCE_ANCHOR) == []
    whole = fr.run_repository_check(repo.root)
    assert [f for f in whole.findings if f.anchor == SOURCE_ANCHOR] == []
    assert [r.state for r in whole.artefact_reports] == [fr.ArtefactState.CURRENT]


def test_a_repointed_mapping_asks_the_artefact_when_the_answer_names_the_mapping_file(
    repo: AdopterRepo,
) -> None:
    """What the answer must name: every file whose content decides what the value
    denotes, a file that maps the value to them included. The mapped file did not
    change; the mapping did, and the mapping is named."""
    _sources(repo, MAPPED)
    index = {"iso-8601": "sources/2004.md"}
    files = {
        "docs/guide.md": guide(anchors=SOURCE_ANCHORS),
        "sources/index.json": json.dumps(index),
        "sources/2004.md": "ISO 8601:2004.\n",
        "sources/2019.md": "ISO 8601-1:2019.\n",
    }
    _start(repo, files)
    repointed = repo.commit(
        "the standard is now its 2019 edition",
        {"sources/index.json": json.dumps({"iso-8601": "sources/2019.md"})},
    )

    [asked] = _of_anchor(fc.run_change_check(repo.root, "main").findings, SOURCE_ANCHOR)
    assert asked.kind is fc.FindingKind.FRICTION
    assert asked.message.startswith("changed in this diff (sources/index.json)")
    whole = fr.run_repository_check(repo.root)
    [stale] = [f for f in whole.findings if f.anchor == SOURCE_ANCHOR]
    assert stale.kind is fr.RepositoryFindingKind.STALE
    assert stale.origin is not None and stale.origin.sha == repointed


def test_an_anchor_whose_resolver_names_most_of_the_tracked_files_is_over_broad(
    repo: AdopterRepo,
) -> None:
    """The over-broad rule is not a kind's (COR-050 point 7)."""
    _sources(repo, EVERYTHING)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS)})
    result = fr.run_repository_check(repo.root)
    [broad] = [f for f in result.findings if f.kind is fr.RepositoryFindingKind.OVER_BROAD]
    assert broad.anchor == SOURCE_ANCHOR
    assert broad.message.startswith("stands on ") and "tracked files (100%)" in broad.message
    assert broad.message.endswith("have its resolver name less, or anchor to a narrower value")


def test_the_over_broad_share_counts_the_named_files_exclusions_leave_in(
    repo: AdopterRepo,
) -> None:
    """The share's whole is the tracked files `friction.exclude` leaves in, and the files a
    resolver names are counted among them: one naming every file stands on all of them,
    100%, never more."""
    _sources(repo, EVERYTHING)
    vendored = {f"vendor/lib{n}.py": f"N = {n}\n" for n in range(3)}
    files = {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **vendored}
    _start(repo, files, friction_config(exclude=["vendor"]))
    result = fr.run_repository_check(repo.root)
    [broad] = [f for f in result.findings if f.kind is fr.RepositoryFindingKind.OVER_BROAD]
    counted = re.match(r"stands on (\d+) of (\d+) tracked files \(100%\)", broad.message)
    assert counted is not None, broad.message
    assert counted[1] == counted[2]


# --- validation and the writers admit an anchor of any kind a word names ---------------------

VALIDATE_FRICTION = ["validate", "--only", "friction"]


def _unresolved_reports(repo: AdopterRepo) -> list[fv.FrictionFinding]:
    return [
        f
        for f in fv.validate_friction(repo.root).findings
        if f.kind is fv.FrictionFindingKind.UNRESOLVED_KIND
    ]


def test_validation_admits_an_anchor_of_a_kind_an_installed_capability_registers(
    repo: AdopterRepo,
) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    assert fv.validate_friction(repo.root).findings == ()
    result = CliRunner().invoke(main, VALIDATE_FRICTION)
    assert result.exit_code == 0, result.output
    assert "0 error(s), 0 report(s)" in result.output


def test_validation_reports_a_kind_nothing_registers_and_passes(repo: AdopterRepo) -> None:
    """Uninstalling a capability must not fail validation: the kind is a report."""
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    [report] = fv.validate_friction(repo.root).findings
    assert (report.kind, report.severity) == (
        fv.FrictionFindingKind.UNRESOLVED_KIND,
        fv.Severity.REPORT,
    )
    assert report.where == "docs/guide.md /pkit/friction/anchors/source"
    assert report.message.startswith(
        "anchor kind 'source' is unresolved: no installed component registers a resolver for it."
    )
    result = CliRunner().invoke(main, VALIDATE_FRICTION)
    assert result.exit_code == 0, result.output
    assert "0 error(s), 1 report(s)" in result.output
    assert "docs/guide.md:/pkit/friction/anchors/source" in result.output


def test_a_misspelt_kind_is_reported_with_the_nearest_known_kind(repo: AdopterRepo) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={"pth": ["src/cli/**"], "sorce": ["iso-8601"]})})
    reports = {f.pointer.rsplit("/", 1)[1]: f.message for f in _unresolved_reports(repo)}
    assert reports["pth"].endswith("Did you mean 'path'?")
    assert reports["sorce"].endswith("Did you mean 'source'?")
    assert fv.validate_friction(repo.root).errors == ()


def test_a_refused_registration_is_a_report_on_the_anchor_and_fails_at_the_registration(
    repo: AdopterRepo,
) -> None:
    register_kinds(repo.root, "alpha", kinds={"source": "resolve"})
    register_kinds(repo.root, "beta", kinds={"source": "resolve"})
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    [report] = fv.validate_friction(repo.root).findings
    assert (report.kind, report.severity) == (
        fv.FrictionFindingKind.UNRESOLVED_KIND,
        fv.Severity.REPORT,
    )
    assert "the capabilities alpha, beta each register it" in report.message
    assert "Did you mean" not in report.message  # the kind is known: its registration is refused
    assert CliRunner().invoke(main, VALIDATE_FRICTION).exit_code == 0
    packages = CliRunner().invoke(main, ["validate", "--only", "packages"])
    assert packages.exit_code == 1, packages.output
    assert "anchor kind 'source' is registered by beta too" in packages.output


@pytest.mark.parametrize("kind", ["Source", "my kind", "source_2", "-source"])
def test_a_kind_that_is_not_a_word_is_a_malformed_block(repo: AdopterRepo, kind: str) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={kind: ["iso-8601"]})})
    [error] = fv.validate_friction(repo.root).errors
    assert error.kind is fv.FrictionFindingKind.MALFORMED_BLOCK
    assert error.pointer == "/pkit/friction/anchors"
    assert CliRunner().invoke(main, VALIDATE_FRICTION).exit_code == 1


def test_the_values_of_a_registered_kind_take_the_shape_of_the_three(repo: AdopterRepo) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors={"source": []})})
    [error] = fv.validate_friction(repo.root).errors
    assert error.kind is fv.FrictionFindingKind.MALFORMED_BLOCK
    assert error.pointer == "/pkit/friction/anchors/source"


def test_a_deferral_of_a_registered_kind_validates_and_one_naming_no_anchor_dangles(
    repo: AdopterRepo,
) -> None:
    _sources(repo)
    deferred = guide(anchors=SOURCE_ANCHORS, deferred=[("source", "iso-8601", "the 2019 edition")])
    _start(repo, {"docs/guide.md": deferred, **CAPTURED})
    assert fv.validate_friction(repo.root).findings == ()

    dangling = guide(anchors=SOURCE_ANCHORS, deferred=[("source", "iso-9999", "no such anchor")])
    repo.write({"docs/guide.md": dangling})
    [error] = fv.validate_friction(repo.root).errors
    assert error.kind is fv.FrictionFindingKind.DANGLING_DEFERRAL
    assert "deferral names source anchor 'iso-9999'" in error.message


def test_the_writers_write_a_block_carrying_an_anchor_of_a_registered_kind(
    repo: AdopterRepo,
) -> None:
    _sources(repo)
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})

    def friction(*args: str) -> str:
        result = CliRunner().invoke(main, ["friction", *args, "--yes"])
        assert result.exit_code == 0, result.output
        return result.output

    def block() -> dict[str, Any]:
        [artefact] = fd.discover_artefacts(repo.root).artefacts
        return artefact.friction

    friction("revalidate", "docs/guide.md", "--outcome", "unchanged", "--because", "still ISO 8601")
    assert block()["revalidated"]["unchanged-because"] == "still ISO 8601"
    friction(
        "defer", "docs/guide.md", "--anchor", "source:iso-8601", "--reason", "the 2019 edition"
    )
    assert block()["revalidated"]["deferred"] == [
        {"anchor": {"kind": "source", "value": "iso-8601"}, "reason": "the 2019 edition"}
    ]
    head = repo.commit("revalidate and defer", files=None)
    friction("record-status", "docs/guide.md")
    assert block()["last-check"] == {"state": "deferred", "as-of": head}
    assert fv.validate_friction(repo.root).findings == ()


def test_a_writer_writes_a_block_whose_kind_nothing_resolves(repo: AdopterRepo) -> None:
    """The report is no refusal: with the capability uninstalled the artefact can still
    be revalidated — to drop the anchor, say."""
    _start(repo, {"docs/guide.md": guide(anchors=SOURCE_ANCHORS), **CAPTURED})
    fw.write(fw.plan_revalidate(repo.root, "guide", outcome="unchanged", because="as before"))
    [artefact] = fd.discover_artefacts(repo.root).artefacts
    assert artefact.revalidated is not None
    assert artefact.revalidated["unchanged-because"] == "as before"


# --- provisioning ---------------------------------------------------------------------------


def test_a_resolver_s_script_is_provisioned_as_a_validator_s_is(repo: AdopterRepo) -> None:
    metadata = "# /// script\n# dependencies = []\n# ///\n"
    register_kinds(
        repo.root, "sources", kinds={"source": "resolve"}, script_body=metadata + RESOLVING
    )
    register_kinds(repo.root, "tickets", kinds={"ticket": "resolve"}, contract=False)
    [command] = provisioning.query_commands(repo.root)
    assert (command.owner, command.reference) == ("sources", "resolve")
    provisioned = provisioning.provision(command, dry_run=True)
    assert provisioned.state is provisioning.State.WOULD_PROVISION
