"""living-docs' connection points (#1004; living-docs DEC-001 point 7, COR-052, COR-053).

The capability provides the `pkit::documentation` role and defines two data
points under it — `readers` (`union`, the default `user` and `maintainer`
always included, inert `fail`) and `reading-evidence` (`union`, no default,
inert `fallback`) — and contributes to the work-tracking role's
`pkit::work-tracking:doc-check` with its command filler, `fill-doc-check`.

Three layers:

- the pieces — the package declaration, the two companion schemas, reading the
  readers point's document, the obligations a friction report gives rise to;
- reader resolution through the real backbone, in an adopter repository: a
  page's reader resolves against the point or fails naming the page and the
  readers the point holds; an out-of-step contributor leaves the whole point
  unresolved, which the validator reports once rather than per page;
- the contribution through the real backbone: obligations in
  project-management's shape, read from the whole-repository friction check,
  and inert when no work-tracking provider is installed.

The capability's scripts are pointed at this interpreter in the adopter copy,
and the `pkit` they read through is the real CLI under this interpreter
(`pkit_on_path`), so no test reaches `uv` or the network.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import document as friction_document

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "living-docs"
PM_CAPABILITY = REPO / ".pkit" / "capabilities" / "project-management"
LD = Path(".pkit") / "capabilities" / "living-docs"
PM = Path(".pkit") / "capabilities" / "project-management"
CONFIG = ".pkit/project/config.yaml"

ROLE = "pkit::documentation"
READERS = "pkit::documentation:readers"
EVIDENCE = "pkit::documentation:reading-evidence"
DOC_CHECK = "pkit::work-tracking:doc-check"
READERS_FILLER = "tech-docs/pkit/fillers/pkit/documentation/readers.yaml"


def _library(name: str) -> ModuleType:
    """A module of the capability's script library, under a name of its own: the
    library is `_lib` in every capability, so it is never imported by that name."""
    spec = importlib.util.spec_from_file_location(
        f"living_docs_lib_{name}", CAPABILITY / "scripts" / "_lib" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


readers_lib = _library("readers")
doc_check_lib = _library("doc_check")


def _package() -> dict[str, Any]:
    return YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))


def _schema(root: Path, name: str) -> Draft202012Validator:
    schema = json.loads((root / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


# --- the pieces --------------------------------------------------------------------------


def test_the_package_provides_the_role_and_declares_both_points_and_the_contribution() -> None:
    package = _package()
    connections = package["connections"]
    assert connections["roles"] == [ROLE]
    accepts = connections["extension-points"]["accepts"]
    assert set(accepts) == {READERS, EVIDENCE}

    readers = accepts[READERS]
    assert {k: readers[k] for k in ("schema_version", "schema", "combination", "inert")} == {
        "schema_version": 1,
        "schema": "readers.schema.json",
        "combination": "union",
        "inert": "fail",
    }
    assert readers["default"]["participation"] == "always"
    assert [entry["id"] for entry in readers["default"]["value"]] == ["user", "maintainer"]

    evidence = accepts[EVIDENCE]
    assert evidence == {
        "schema_version": 1,
        "schema": "reading-evidence.schema.json",
        "description": evidence["description"],
        "combination": "union",
        "inert": "fallback",
    }
    for point in (readers, evidence):
        assert point["description"].strip()
        assert (CAPABILITY / "schemas" / point["schema"]).is_file()

    (contribution,) = connections["extensions"]["contributes"]
    assert contribution == {
        "point": DOC_CHECK,
        "schema_version": 1,
        "command": "fill-doc-check",
        "description": contribution["description"],
    }
    command = package["commands"]["fill-doc-check"]
    assert command["query-contract"] is True
    assert (CAPABILITY / command["script"]).is_file()


def test_the_default_readers_fit_the_readers_schema() -> None:
    schema = _schema(CAPABILITY, "readers.schema.json")
    default = _package()["connections"]["extension-points"]["accepts"][READERS]["default"]["value"]
    assert list(schema.iter_errors(default)) == []


@pytest.mark.parametrize(
    "entry",
    [
        {"id": "guest"},
        {"id": "Guest", "description": "A visitor."},
        {"id": "guest", "description": ""},
        {"id": "guest", "description": "A visitor.", "needs": "x"},
        "guest",
    ],
)
def test_the_readers_schema_refuses_a_malformed_entry(entry: Any) -> None:
    assert not _schema(CAPABILITY, "readers.schema.json").is_valid([entry])


EVIDENCE_ENTRY = {
    "id": "docs/guide.md@1a2b3c4",
    "path": "docs/guide.md",
    "commit": "1a2b3c4",
    "outcome": "passed",
    "description": "A simulated user followed the guide end to end.",
}


def test_the_reading_evidence_schema_keys_an_entry_by_page_and_commit() -> None:
    schema = _schema(CAPABILITY, "reading-evidence.schema.json")
    assert schema.is_valid([EVIDENCE_ENTRY])
    for broken in (
        {**EVIDENCE_ENTRY, "id": "docs/guide.md"},
        {**EVIDENCE_ENTRY, "commit": "HEAD"},
        {**EVIDENCE_ENTRY, "outcome": "flaky"},
        {k: v for k, v in EVIDENCE_ENTRY.items() if k != "path"},
        {**EVIDENCE_ENTRY, "extra": 1},
    ):
        assert not schema.is_valid([broken]), broken


def test_reading_the_readers_point_document() -> None:
    resolved = {
        "address": READERS,
        "defined": True,
        "resolved": True,
        "entries": [{"id": "user"}, {"id": "maintainer"}, {"id": "operator"}],
    }
    assert readers_lib.readers_of(resolved) == readers_lib.Readers(
        True, ids=("maintainer", "operator", "user")
    )
    unresolved = {
        "address": READERS,
        "defined": True,
        "resolved": False,
        "why": "a filler meant to answer is inert, and the point's inert policy is `fail`",
        "fillers": [
            {
                "name": "analysis",
                "supplies": "value",
                "state": "inert",
                "reason": "it targets version 2",
            },
            {"name": "living-docs", "supplies": "always", "state": "passed over", "reason": "x"},
        ],
    }
    assert readers_lib.readers_of(unresolved).why == (
        "a filler meant to answer is inert, and the point's inert policy is `fail` — inert: "
        "analysis (value): it targets version 2"
    )
    undefined = {"address": READERS, "defined": False, "resolved": False, "why": "no provider"}
    assert readers_lib.readers_of(undefined) == readers_lib.Readers(
        False, why="it is not defined: no provider"
    )


def test_no_document_from_the_backbone_leaves_the_readers_unresolved() -> None:
    def old_backbone(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "connections", "resolve", READERS, "--json"]
        return subprocess.CompletedProcess(argv, 2, "", "Error: No such command 'connections'.\n")

    readers = readers_lib.read_readers(old_backbone)
    assert not readers.resolved
    assert readers.why.endswith(
        "exited 2 without its document: Error: No such command 'connections'."
    )

    def absent(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(argv[0])

    assert "could not be run" in readers_lib.read_readers(absent).why


REPORT: dict[str, Any] = {
    "dormant": False,
    "artefacts": [
        {"location": "docs/guide.md", "state": "stale"},
        {"location": "docs/deferred.md", "state": "deferred"},
        {"location": "docs/current.md", "state": "current"},
        {"location": "tech-docs/decisions/ADR-001-a.md", "state": "stale"},
    ],
    "findings": [
        {
            "location": "docs/guide.md",
            "kind": "stale",
            "anchor": {"kind": "path", "value": "src/a.py"},
        },
        {"location": "docs/guide.md", "kind": "stale", "anchor": None},
        {
            "location": "docs/guide.md",
            "kind": "over-broad",
            "anchor": {"kind": "path", "value": "**"},
        },
        {
            "location": "docs/deferred.md",
            "kind": "deferred",
            "anchor": {"kind": "path", "value": "src/c.py"},
        },
        {
            "location": "tech-docs/decisions/ADR-001-a.md",
            "kind": "stale",
            "anchor": {"kind": "path", "value": "src/a.py"},
        },
    ],
    "measures": {"unanchored": [], "uncovered_surface": ["src/z.py", "src/d.py"]},
}
PAGES = ["docs/current.md", "docs/deferred.md", "docs/guide.md"]


def test_friction_debt_on_pages_and_uncovered_surface_become_obligations() -> None:
    obligations = doc_check_lib.obligations(REPORT, PAGES, "tech-docs")
    assert obligations == [
        {
            "id": "friction:page-stale:docs/deferred.md",
            "source": "friction",
            "reason": "page-stale",
            "document": "docs/deferred.md",
            "description": (
                "deferred: path src/c.py deferred — pkit friction explain docs/deferred.md"
            ),
        },
        {
            "id": "friction:page-stale:docs/guide.md",
            "source": "friction",
            "reason": "page-stale",
            "document": "docs/guide.md",
            "description": (
                "stale: path src/a.py changed, moved with no revalidation — "
                "pkit friction explain docs/guide.md"
            ),
        },
        {
            "id": "friction:code-undocumented:src/d.py",
            "source": "friction",
            "reason": "code-undocumented",
            "document": "tech-docs/**",
            "path": "src/d.py",
            "description": "src/d.py is in the declared surface and nothing anchors it — "
            "anchor it from a page",
        },
        {
            "id": "friction:code-undocumented:src/z.py",
            "source": "friction",
            "reason": "code-undocumented",
            "document": "tech-docs/**",
            "path": "src/z.py",
            "description": "src/z.py is in the declared surface and nothing anchors it — "
            "anchor it from a page",
        },
    ]
    # In project-management's shape, as its point's companion schema holds it.
    assert list(_schema(PM_CAPABILITY, "doc-check.schema.json").iter_errors(obligations)) == []
    envelope = doc_check_lib.envelope(obligations)
    assert envelope == {"schema_version": 1, "value": obligations}


def test_a_page_whose_friction_cannot_be_judged_is_no_answer() -> None:
    report = {**REPORT, "artefacts": [{"location": "docs/guide.md", "state": "unreachable"}]}
    with pytest.raises(
        doc_check_lib.NoAnswer, match=r"friction on docs/guide\.md cannot be judged"
    ):
        doc_check_lib.obligations(report, PAGES, "tech-docs")
    # Only a page's: an unjudged artefact that is not a page leaves the answer whole.
    answer = doc_check_lib.obligations(report, ["docs/other.md"], "docs")
    assert [(o["reason"], o["document"]) for o in answer] == [
        ("code-undocumented", "docs/**"),
        ("code-undocumented", "docs/**"),
    ]


def test_a_dormant_check_owes_nothing() -> None:
    assert doc_check_lib.obligations({"dormant": True, "artefacts": []}, PAGES, "docs") == []


# --- reader resolution through the backbone ------------------------------------------------


def _to_this_interpreter(repo: AdopterRepo, script: Path) -> None:
    path = repo.root / script
    body = path.read_text(encoding="utf-8").split("\n", 1)[1]
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")


def _page(reader: str) -> str:
    return f"---\nreader: {reader}\nkind: signpost\n---\n\n# A page\n"


@pytest.fixture
def docs_project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """An adopter with living-docs installed, two separate roots, a page in each."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    for script in ("validate.py", "fill-doc-check.py"):
        _to_this_interpreter(repo, LD / "scripts" / script)
    config = {
        "name": "adopter",
        "docs": {"user": "docs/", "internal": "tech-docs/"},
        "friction": {"mode": "warning", "surface": ["src"]},
    }
    repo.write(
        {
            CONFIG: json.dumps(config, indent=2) + "\n",
            "docs/guide.md": _page("user"),
            "tech-docs/README.md": _page("maintainer"),
        }
    )
    return repo


def _validate(repo: AdopterRepo) -> dict[str, Any]:
    """The validator's findings document, run as the backbone runs it."""
    completed = subprocess.run(
        [sys.executable, str(repo.root / LD / "scripts" / "validate.py"), "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _errors(document: dict[str, Any]) -> list[tuple[str, str]]:
    return [(f["location"], f["message"]) for f in document["findings"] if f["severity"] == "error"]


def _readers_line(document: dict[str, Any]) -> str:
    (line,) = [line for line in document["summary"] if line.startswith("readers")]
    return line


def _contribute_readers(repo: AdopterRepo, value: list[Any], *, version: int = 1) -> None:
    """Another capability contributing readers to the point, at `version`."""
    name = "analysis-test"
    cap = repo.pkit / "capabilities" / name
    cap.mkdir(parents=True, exist_ok=True)
    package = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": name, "version": "0.1.0"},
        "description": "An analysis capability, for the test.",
        "requires_backbone": ">=0.0.0",
        "connections": {
            "extensions": {
                "contributes": [{"point": READERS, "schema_version": version, "value": value}]
            }
        },
    }
    with (cap / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(repo.root, backbone)


def test_every_page_reader_resolves_against_the_default_readers(docs_project: AdopterRepo) -> None:
    document = _validate(docs_project)
    assert _errors(document) == []
    assert _readers_line(document) == (
        "readers (pkit::documentation:readers): maintainer, user; 2 page reader(s) checked."
    )


def test_a_page_whose_reader_does_not_resolve_fails_naming_the_page_and_the_readers(
    docs_project: AdopterRepo,
) -> None:
    docs_project.write({"docs/guide.md": _page("guest")})
    ((location, message),) = _errors(_validate(docs_project))
    assert location == "docs/guide.md:/reader"
    assert message == (
        "docs/guide.md is for reader 'guest', which does not resolve: the readers point "
        "pkit::documentation:readers holds ['maintainer', 'user'] — name one of them, or add "
        f"'guest' to the point in the project's filler, {READERS_FILLER} (DEC-001 points 4 and 7)."
    )


def test_the_project_filler_adds_a_reader(docs_project: AdopterRepo) -> None:
    docs_project.write(
        {
            "docs/guide.md": _page("guest"),
            READERS_FILLER: (
                "schema_version: 1\nvalue:\n"
                "  - {id: guest, description: A visitor who reads the guide once.}\n"
            ),
        }
    )
    document = _validate(docs_project)
    assert _errors(document) == []
    assert "guest, maintainer, user" in _readers_line(document)


def test_a_capability_s_readers_are_added_beside_the_defaults(docs_project: AdopterRepo) -> None:
    _contribute_readers(docs_project, [{"id": "operator", "description": "Runs the service."}])
    docs_project.write({"docs/guide.md": _page("operator")})
    document = _validate(docs_project)
    assert _errors(document) == []
    assert "maintainer, operator, user" in _readers_line(document)


def test_an_out_of_step_contributor_leaves_the_whole_readers_point_unresolved(
    docs_project: AdopterRepo,
) -> None:
    """Under `fail` the point does not resolve on the defaults that survived, so no
    page's reader is checked — reported once, not per page (DEC-001 point 7)."""
    _contribute_readers(
        docs_project, [{"id": "operator", "description": "Runs the service."}], version=2
    )
    docs_project.write({"docs/other.md": _page("guest")})
    document = _validate(docs_project)
    ((location, message),) = _errors(document)
    assert location == READERS
    assert message.startswith(
        "readers unresolved — a filler meant to answer is inert, and the point's inert policy "
        "is `fail` — inert: analysis-test (value): it targets version 2; the point is at "
        "version 1. No page's reader can be checked until the point resolves"
    )
    assert _readers_line(document) == "readers unresolved: 3 page reader(s) not checked."
    # The backbone names it too, as the inert filler of a `fail` point.
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "connections"])
    assert result.exit_code == 1
    assert "'analysis-test' to 'pkit::documentation:readers' is inert" in result.output


def test_the_point_is_read_only_when_some_page_names_a_reader(
    docs_project: AdopterRepo,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `pkit` that answers nothing is never asked while no page names a reader;
    once one does, no document is an unresolved point, never a pass."""
    broken = tmp_path_factory.mktemp("broken-pkit")
    (broken / "pkit").write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
    (broken / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{broken}{os.pathsep}{os.environ['PATH']}")
    docs_project.write(
        {"docs/guide.md": "# Not a page yet\n", "tech-docs/README.md": "# Nor this\n"}
    )
    document = _validate(docs_project)
    assert _errors(document) == []
    assert _readers_line(document) == (
        "readers: no page names one yet, so pkit::documentation:readers is not read."
    )
    docs_project.write({"docs/guide.md": _page("user")})
    ((location, message),) = _errors(_validate(docs_project))
    assert location == READERS
    assert "`pkit connections resolve pkit::documentation:readers --json` exited 3" in message


# --- the contribution to the documentation-check point -----------------------------------


def test_the_contribution_is_inert_without_a_work_tracking_provider(
    docs_project: AdopterRepo,
) -> None:
    """No capability provides the work-tracking role: the contribution is reported
    as having no active provider, never as an error, and its filler never runs."""
    (docs_project.root / LD / "scripts" / "fill-doc-check.py").write_text(
        "#!/bin/sh\nexit 1\n", encoding="utf-8"
    )
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "connections"])
    assert result.exit_code == 0, result.output
    assert "pkit::work-tracking → no provider installed" in result.output
    assert f"living-docs contributes {DOC_CHECK!r}: no active provider" in result.output
    assert "0 error(s), 0 warning(s)." in result.output
    resolved = CliRunner().invoke(main, ["connections", "resolve", DOC_CHECK, "--json"])
    assert json.loads(resolved.output) == {
        "address": DOC_CHECK,
        "defined": False,
        "resolved": False,
        "value": None,
        "why": "role 'pkit::work-tracking' has no active provider",
    }


@pytest.fixture
def tracked_project(docs_project: AdopterRepo) -> AdopterRepo:
    """The docs project with project-management installed, its doc-check filler
    under this interpreter."""
    docs_project.install_capabilities("project-management")
    _to_this_interpreter(docs_project, PM / "scripts" / "fill-doc-check.py")
    return docs_project


def _living_docs_entries(repo: AdopterRepo) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = CliRunner().invoke(main, ["connections", "resolve", DOC_CHECK, "--json"])
    document = json.loads(result.output)
    return document, [e["value"] for e in document["entries"] if e["origin"] == "living-docs"]


def test_nothing_committed_owes_nothing(tracked_project: AdopterRepo) -> None:
    document, ours = _living_docs_entries(tracked_project)
    assert document["resolved"], document["why"]
    assert ours == []
    filler = next(f for f in document["fillers"] if f["name"] == "living-docs")
    assert (filler["state"], filler["query_contract"]) == ("taken", True)


def test_the_filler_contributes_page_friction_and_uncovered_surface(
    tracked_project: AdopterRepo,
) -> None:
    """Through the backbone: the whole-repository check at HEAD, the pages among its
    artefacts, obligations in project-management's shape beside the mapping's."""
    repo = tracked_project
    page = {"reader": "user", "kind": "signpost"}
    repo.write(
        {
            "src/a.py": "A = 1\n",
            "src/b.py": "B = 1\n",
            "src/c.py": "C = 1\n",
            "src/d.py": "D = 1\n",
            "docs/guide.md": friction_document(None, anchors={"path": ["src/a.py"]}, **page),
            "docs/current.md": friction_document(None, anchors={"path": ["src/b.py"]}, **page),
            "docs/deferred.md": friction_document(
                None,
                anchors={"path": ["src/c.py"]},
                deferred=[("path", "src/c.py", "the rewrite lands next")],
                **page,
            ),
            # A decision record anchored to the same code: stale too, but never a page.
            "tech-docs/decisions/ADR-001-a.md": friction_document(
                "ADR-001", anchors={"path": ["src/a.py"]}, title="A", status="accepted"
            ),
        }
    )
    repo.commit("base")
    repo.commit("change a", {"src/a.py": "A = 2\n"})

    resolved, ours = _living_docs_entries(repo)
    assert resolved["resolved"], resolved["why"]
    assert [(o["id"], o["document"]) for o in ours] == [
        ("friction:page-stale:docs/deferred.md", "docs/deferred.md"),
        ("friction:page-stale:docs/guide.md", "docs/guide.md"),
        ("friction:code-undocumented:src/d.py", "tech-docs/**"),
    ]
    assert ours[1]["description"] == (
        "stale: path src/a.py changed — pkit friction explain docs/guide.md"
    )
    assert list(_schema(PM_CAPABILITY, "doc-check.schema.json").iter_errors(ours)) == []
    # The filler's own view, for a person, says the same.
    human = subprocess.run(
        [sys.executable, str(repo.root / LD / "scripts" / "fill-doc-check.py")],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert human.returncode == 0, human.stderr
    assert human.stdout.splitlines()[0] == "pkit::work-tracking:doc-check: 3 friction obligation(s)"
    # And `pkit validate` passes with the role, both points and the contribution.
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "packages", "--only", "connections"]
    )
    assert result.exit_code == 0, result.output
