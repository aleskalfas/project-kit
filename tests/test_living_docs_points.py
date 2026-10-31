"""living-docs' connection points (#1004; living-docs DEC-001 point 7, COR-052, COR-053).

The capability provides the `pkit::documentation` role and defines two data
points under it — `readers` (`union`, the default `user` and `maintainer`
always included, inert `fail`) and `reading-evidence` (`union`, no default,
inert `fallback`) — and contributes to the work-tracking role's
`pkit::work-tracking:doc-check` with its command filler, `fill-doc-check`, and
to its `pkit::work-tracking:fixers` with a static value naming its agent as the
fixer of pages (#1746; DEC-001 points 5 and 7).

Three layers:

- the pieces — the package declaration, the two companion schemas, reading the
  readers point's document, the obligations a friction report gives rise to, and
  the report versions read (one without `schema_version` as version 1);
- reader resolution through the real backbone, in an adopter repository: a
  page's reader resolves against the point or fails naming the page and the
  readers the point holds; an out-of-step contributor leaves the whole point
  unresolved, which the validator reports once rather than per page;
- the contribution through the real backbone: obligations in
  project-management's shape, read from the whole-repository friction check,
  and inert when no work-tracking provider is installed; and project-management's
  check over them, where an uncovered path is met only once a page anchors it;
- the fixer through the real backbone: project-management's checks pass the
  declaration with the agent as deployed, and report it were the agent to do
  more than propose.

The capability's scripts run in the test's own process: the validator's and the
filler's `main`, every `pkit` they read through answered by the backbone's CLI
in this process too, and the fillers `pkit connections resolve` starts, started
in this process through the runner's one lookup (`tests/in_process.py`). The
filler reads in threads, so its in-process `pkit` calls are made one at a time
(`one_call_at_a_time`). project-management's checks of the fixers point are its
public functions, called in this process. Four tests keep a real process, each
marked with why. There the capability's scripts are pointed at this interpreter
in the adopter copy, and the `pkit` they read through is the real CLI under this
interpreter (`pkit_on_path`), so no test reaches `uv` or the network.
"""

from __future__ import annotations

import functools
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path
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
from tests.in_process import (
    QUERY_ENVIRONMENT,
    InProcessPkit,
    Runner,
    load,
    route_pkit,
    run_main,
    start_in_process,
)
from tests.test_living_docs_spaces import _answering

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

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
FIXERS = "pkit::work-tracking:fixers"
PAGE_TYPE = "living-docs:page"
AGENT = "living-docs"
DEPLOYED_AGENT = REPO / ".claude" / "agents" / f"{AGENT}.md"
READERS_FILLER = "tech-docs/pkit/fillers/pkit/documentation/readers.yaml"


#: Two modules of the capability's script library, loaded with its `_lib` kept apart.
readers_lib, doc_check_lib = load("living-docs", "readers", "doc_check")


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

    contributes = {c["point"]: c for c in connections["extensions"]["contributes"]}
    assert set(contributes) == {DOC_CHECK, FIXERS}
    contribution = contributes[DOC_CHECK]
    assert contribution == {
        "point": DOC_CHECK,
        "schema_version": 1,
        "command": "fill-doc-check",
        "description": contribution["description"],
    }
    command = package["commands"]["fill-doc-check"]
    assert command["query-contract"] is True
    # It reads history at HEAD beyond the working tree, and never settled state or a
    # base: the base a pull request is compared with bounds the consumer's diff.
    assert command["reads"] == ["history"]
    assert (CAPABILITY / command["script"]).is_file()


def test_the_agent_is_declared_the_fixer_of_pages_as_a_static_value() -> None:
    """DEC-001 points 5 and 7; project-management DEC-056 point 1: one entry, for a
    type of the capability's own registry, naming an agent it ships, given as a
    static value that project-management's companion schema takes."""
    package = _package()
    (fixers,) = [
        c for c in package["connections"]["extensions"]["contributes"] if c["point"] == FIXERS
    ]
    assert "command" not in fixers
    assert fixers["schema_version"] == 1
    assert fixers["value"] == [{"id": PAGE_TYPE, "agent": AGENT, "description": "your pages"}]
    assert fixers["description"].strip()
    assert _schema(PM_CAPABILITY, "fixers.schema.json").is_valid(fixers["value"])
    owner, _, name = PAGE_TYPE.partition(":")
    assert owner == package["component"]["name"]
    assert name in package["friction"]["types"]
    assert (CAPABILITY / "agents" / AGENT / f"{AGENT}.md").is_file()


def test_the_default_readers_fit_the_readers_schema() -> None:
    schema = _schema(CAPABILITY, "readers.schema.json")
    default = _package()["connections"]["extension-points"]["accepts"][READERS]["default"]["value"]
    assert list(schema.iter_errors(default)) == []


#: A path a reader takes through the pages (DEC-001 point 7): what they come to do,
#: and the pages they read in order, each named by its path from the repository's root.
RESTART_PATH = {
    "description": "Restarts the service after a failure.",
    "pages": ["README.md", "docs/runbooks/index.md", "docs/runbooks/restart.md"],
}


def test_the_readers_schema_takes_an_entry_with_paths_and_one_without() -> None:
    """An entry may carry the paths its reader takes; the defaults carry none."""
    entries = [
        {"id": "operator", "description": "Runs the service.", "paths": [RESTART_PATH]},
        {"id": "guest", "description": "A visitor.", "paths": []},
        {"id": "auditor", "description": "Checks the service.", "paths": [{"pages": ["a.md"]}]},
        {"id": "visitor", "description": "Reads the guide once."},
    ]
    assert list(_schema(CAPABILITY, "readers.schema.json").iter_errors(entries)) == []


def _with_path(path: Any) -> dict[str, Any]:
    return {"id": "operator", "description": "Runs the service.", "paths": [path]}


@pytest.mark.parametrize(
    "entry",
    [
        {"id": "guest"},
        {"id": "Guest", "description": "A visitor."},
        {"id": "guest", "description": ""},
        {"id": "guest", "description": "A visitor.", "needs": "x"},
        "guest",
        # A path is the pages a reader reads in order, never a glob of files.
        {"id": "operator", "description": "Runs the service.", "paths": ["docs/runbooks/**"]},
        {"id": "operator", "description": "Runs the service.", "paths": "docs/guide.md"},
        _with_path({"description": "Restarts the service."}),
        _with_path({"pages": []}),
        _with_path({"pages": ["docs/runbooks/**"]}),
        _with_path({"pages": ["docs/guide.txt"]}),
        _with_path({"pages": ["/docs/guide.md"]}),
        _with_path({"pages": ["../docs/guide.md"]}),
        _with_path({"pages": ["docs/../guide.md"]}),
        _with_path({"pages": ["docs/guide.md#install"]}),
        _with_path({"pages": ["docs\\guide.md"]}),
        _with_path({"pages": ["docs/guide.md"], "description": ""}),
        _with_path({"pages": ["docs/guide.md"], "goal": "x"}),
    ],
)
def test_the_readers_schema_refuses_a_malformed_entry(entry: Any) -> None:
    assert not _schema(CAPABILITY, "readers.schema.json").is_valid([entry])


#: A commit's full name under SHA-1, and under SHA-256.
SHA1 = "78981922613b2afb6025042ff6bd878ac1994e85"
SHA256 = "4f9be057f0ea5d2ba72fd2c810e8d7b9aa98b469f9a6c4d6d0e2a2d3e1c4b5a6"

EVIDENCE_ENTRY = {
    "id": f"docs/guide.md@{SHA1}#guide-walker.install",
    "path": "docs/guide.md",
    "commit": SHA1,
    "check": "guide-walker.install",
    "outcome": "passed",
    "description": "A simulated user followed the guide end to end.",
}


def test_the_reading_evidence_schema_keys_an_entry_by_page_commit_and_check() -> None:
    """Three parts (DEC-001 point 7): two fillers' results for one page at one
    commit stand side by side under their own checks; the commit by its full name."""
    schema = _schema(CAPABILITY, "reading-evidence.schema.json")
    assert schema.is_valid([EVIDENCE_ENTRY])
    other = {**EVIDENCE_ENTRY, "id": f"docs/guide.md@{SHA1}#project.read-aloud"}
    assert schema.is_valid([EVIDENCE_ENTRY, {**other, "check": "project.read-aloud"}])
    sha256 = {**EVIDENCE_ENTRY, "id": f"docs/guide.md@{SHA256}#guide-walker.install"}
    assert schema.is_valid([{**sha256, "commit": SHA256}])
    for broken in (
        {**EVIDENCE_ENTRY, "id": "docs/guide.md"},
        {**EVIDENCE_ENTRY, "id": f"docs/guide.md@{SHA1}"},  # no check
        {**EVIDENCE_ENTRY, "id": f"docs/guide.md@{SHA1[:7]}#guide-walker.install"},
        {**EVIDENCE_ENTRY, "commit": SHA1[:7]},  # a short name: one commit, one spelling
        {**EVIDENCE_ENTRY, "commit": "HEAD"},
        {k: v for k, v in EVIDENCE_ENTRY.items() if k != "check"},
        {**EVIDENCE_ENTRY, "check": "guide_walker.install"},
        {**EVIDENCE_ENTRY, "check": "Guide-walker"},
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
            "location": "docs/guide.md",
            "kind": "deferred",
            "anchor": {"kind": "path", "value": "src/e.py"},
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


def test_stale_pages_and_uncovered_surface_become_obligations() -> None:
    """A stale page names the page, whose answer in the diff meets it; an uncovered
    path names only the code, since only a page anchoring it meets it. A deferred
    page owes nothing — its deferral is the answer (DEC-053 point 4) — and a stale
    page's deferred anchor is not in what it owes."""
    obligations = doc_check_lib.obligations(REPORT, PAGES)
    assert obligations == [
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
            "path": "src/d.py",
            "description": "src/d.py is in the declared surface and nothing anchors it — "
            "anchor it from a page",
        },
        {
            "id": "friction:code-undocumented:src/z.py",
            "source": "friction",
            "reason": "code-undocumented",
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
        doc_check_lib.obligations(report, PAGES)
    # Only a page's: an unjudged artefact that is not a page leaves the answer whole.
    answer = doc_check_lib.obligations(report, ["docs/other.md"])
    assert [(o["reason"], o["path"]) for o in answer] == [
        ("code-undocumented", "src/d.py"),
        ("code-undocumented", "src/z.py"),
    ]


def _finding(kind: str, anchor_kind: str, value: str) -> dict[str, Any]:
    """A finding of `kind` on the guide's anchor `anchor_kind: value`."""
    return {
        "location": "docs/guide.md",
        "kind": kind,
        "anchor": {"kind": anchor_kind, "value": value},
    }


def _unjudged_guide(state: str | None, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """The report with the guide in `state`, carrying only `findings`, beside a current page."""
    return {
        **REPORT,
        "artefacts": [
            {"location": "docs/current.md", "state": "current"},
            {"location": "docs/guide.md", "state": state},
        ],
        "findings": findings,
    }


@pytest.mark.parametrize(
    ("state", "kinds"),
    [
        ("unresolved", ["no-answer"]),
        ("unresolved", ["no-answer", "unresolved-kind"]),
        ("unresolved", []),
        ("a-state-not-yet-invented", []),
        (None, []),
    ],
)
def test_a_page_the_check_did_not_do_its_work_on_is_no_answer(
    state: str | None, kinds: list[str]
) -> None:
    """A page whose anchor's resolver gave no answer — even beside an anchor of a kind
    nothing resolves — an `unresolved` page whose cause the check does not name, and a
    state this reading does not know are no judgment, never read as current: the point
    fails closed rather than owe too little."""
    findings = [_finding(kind, "source", f"s{n}") for n, kind in enumerate(kinds)]
    report = _unjudged_guide(state, findings)
    with pytest.raises(doc_check_lib.NoAnswer) as refused:
        doc_check_lib.obligations(report, PAGES)
    assert f"friction on docs/guide.md ({state}) was not judged" in str(refused.value)
    assert "docs/current.md" not in str(refused.value)
    # Only a page's: an unjudged artefact that is not a page leaves the answer whole.
    assert len(doc_check_lib.obligations(report, ["docs/current.md"])) == 2


def test_a_page_unjudged_only_on_a_kind_nothing_resolves_owes_what_its_other_anchors_owe() -> None:
    """An anchor of a kind nothing installed resolves is a declaration for the project
    to mend, not a check that could not answer (COR-050 point 12): the page owes what
    its other anchors owe, and the human view names the anchor."""
    unresolved = _finding("unresolved-kind", "source", "iso-8601")
    stale = _unjudged_guide("unresolved", [_finding("stale", "path", "src/a.py"), unresolved])
    obligations = doc_check_lib.obligations(stale, PAGES)
    assert [(o["reason"], o.get("document") or o["path"]) for o in obligations] == [
        ("page-stale", "docs/guide.md"),
        ("code-undocumented", "src/d.py"),
        ("code-undocumented", "src/z.py"),
    ]
    assert obligations[0]["description"] == (
        "stale: path src/a.py changed — pkit friction explain docs/guide.md"
    )
    assert list(_schema(PM_CAPABILITY, "doc-check.schema.json").iter_errors(obligations)) == []
    assert doc_check_lib.unresolved_kinds(stale, PAGES) == [("docs/guide.md", "source", "iso-8601")]
    # A deferred anchor beside it carries its answer: no page obligation, the surface still owed.
    deferred = _unjudged_guide("unresolved", [_finding("deferred", "path", "src/e.py"), unresolved])
    assert [(o["reason"], o["path"]) for o in doc_check_lib.obligations(deferred, PAGES)] == [
        ("code-undocumented", "src/d.py"),
        ("code-undocumented", "src/z.py"),
    ]
    assert doc_check_lib.unresolved_kinds(deferred, PAGES) == [
        ("docs/guide.md", "source", "iso-8601")
    ]


def test_a_page_answered_apart_owes_nothing_for_it() -> None:
    """Two revalidations of a page made apart are debt, not staleness: the check keeps
    the page `current`, `stale` or `deferred` and reports `answered-apart` beside it,
    with no anchor. A page the change leaves alone owes nothing for it, and a stale
    page owes only its changed anchors (project-management DEC-053 point 4, COR-062
    point 7). The filler reads the check's own result, as the backbone gives it."""
    apart = {"location": "docs/current.md", "kind": "answered-apart", "anchor": None}
    stale = {"location": "docs/guide.md", "kind": "answered-apart", "anchor": None}
    deferred = {"location": "docs/deferred.md", "kind": "answered-apart", "anchor": None}
    report = {**REPORT, "findings": [*REPORT["findings"], apart, stale, deferred]}
    read = doc_check_lib.read_friction(".", _check_answering(report))
    assert doc_check_lib.obligations(read, PAGES) == doc_check_lib.obligations(REPORT, PAGES)
    alone = {
        **REPORT,
        "artefacts": [{"location": "docs/current.md", "state": "current"}],
        "findings": [apart],
    }
    assert [o.get("document") for o in doc_check_lib.obligations(alone, PAGES)] == [None, None]
    assert doc_check_lib.unresolved_kinds(report, PAGES) == []


def test_a_dormant_check_owes_nothing() -> None:
    assert doc_check_lib.obligations({"dormant": True, "artefacts": []}, PAGES) == []


def _check_answering(document: dict[str, Any]) -> Any:
    """A runner answering `pkit friction check --all --json` with `document`."""

    def run(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "friction", "check", "--all", "--json"]
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    return run


@pytest.mark.parametrize("version", [2, None, "1"])
def test_a_check_of_another_version_is_no_answer(version: Any) -> None:
    """A version this capability does not read is no answer — the point fails closed —
    never read as the one it knows."""
    run = _check_answering({**REPORT, "schema_version": version})
    with pytest.raises(doc_check_lib.NoAnswer) as refused:
        doc_check_lib.read_friction(".", run)
    assert str(refused.value) == (
        f"`pkit friction check --all --json` answered schema_version {version!r}; "
        f"this capability reads 1"
    )


def test_a_check_that_judged_other_than_the_pages_handed_to_it_is_no_answer() -> None:
    """Standard input cannot tell a list cut short from a whole one, so the filler reads
    back what the check was asked to judge (`selection`): anything but the pages it
    handed — a page missing, a check that judged every artefact — is no answer, never
    fewer obligations (#2365)."""
    pages = ["docs/guide.md", "tech-docs/README.md"]
    whole = {**REPORT, "selection": {"named": pages, "absent": []}}
    doc_check_lib.judged_as_handed(whole, [*reversed(pages), pages[0]])
    doc_check_lib.judged_as_handed({"dormant": True, "artefacts": []}, pages)
    for selection in ({"named": pages[:1], "absent": []}, None):
        with pytest.raises(doc_check_lib.NoAnswer, match="not the 2 page"):
            doc_check_lib.judged_as_handed({**REPORT, "selection": selection}, pages)


def test_a_check_without_a_version_reads_as_the_first() -> None:
    """A backbone from before the key answers version 1."""
    assert doc_check_lib.read_friction(".", _check_answering(REPORT)) == REPORT
    versioned = {**REPORT, "schema_version": 1}
    assert doc_check_lib.read_friction(".", _check_answering(versioned)) == versioned


def _base_answering(document: dict[str, Any]) -> Any:
    """A runner answering `pkit repository base --json` with `document`."""

    def run(argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["pkit", "repository", "base", "--json"]
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    return run


def _with_head(commit: str | None, unborn: bool, problem: str | None) -> dict[str, Any]:
    head = {"commit": commit, "unborn": unborn, "problem": problem}
    return {"schema_version": 1, "default_branch": {}, "base": {}, "head": head}


def test_whether_head_names_a_commit_is_the_backbone_s_reading() -> None:
    """None yet is an answer, and nothing is owed; a HEAD git cannot read is no
    answer, in the backbone's words (COR-052 point 6)."""
    assert doc_check_lib.has_commit(".", _base_answering(_with_head("a" * 40, False, None)))
    assert not doc_check_lib.has_commit(".", _base_answering(_with_head(None, True, None)))
    unread = "git cannot read HEAD here: fatal: detected dubious ownership in repository"
    with pytest.raises(doc_check_lib.NoAnswer) as refused:
        doc_check_lib.has_commit(".", _base_answering(_with_head(None, False, unread)))
    assert str(refused.value) == unread
    # A backbone whose reading names no HEAD cannot say there is no commit yet.
    without = {"schema_version": 1, "default_branch": {}, "base": {}}
    with pytest.raises(doc_check_lib.NoAnswer, match="exited 0 without its document"):
        doc_check_lib.has_commit(".", _base_answering(without))


# --- reader resolution through the backbone ------------------------------------------------


def _to_this_interpreter(repo: AdopterRepo, script: Path) -> None:
    path = repo.root / script
    body = path.read_text(encoding="utf-8").split("\n", 1)[1]
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")


def _page(reader: str) -> str:
    return f"---\nreader: {reader}\nkind: signpost\n---\n\n# A page\n"


#: Where the spaces' definitions live with the internal root at `tech-docs/`.
DEFINITIONS = "tech-docs/living-docs/rule-sets"


def _definition(name: str, root: str) -> str:
    """A space's definition: LDOC inherited, scoped to the pages under `root`, so
    RS-LDOC-003 binds on them and their readers are checked (DEC-001 points 2
    and 3)."""
    return (
        f"---\nrule-set: {name}\nversion: 1.0.0\ninherits: [living-docs:LDOC@1]\n"
        f"scope: {{paths: [{root}/**], types: [living-docs:page]}}\nrules: {{}}\n---\n\n"
        f"# The {name.lower()} space's definition\n"
    )


#: Each space's entry point and definition, in living-docs' project configuration.
SPACES = {
    "pkit_schema": "living-docs:config",
    "schema_version": 1,
    "spaces": {
        "user": {"entry-point": "docs/guide.md", "definition": f"{DEFINITIONS}/user.md"},
        "technical": {
            "entry-point": "tech-docs/README.md",
            "definition": f"{DEFINITIONS}/technical.md",
        },
    },
}


@pytest.fixture
def docs_project(make_adopter_repo: MakeAdopterRepo, request: pytest.FixtureRequest) -> AdopterRepo:
    """An adopter with living-docs installed, two separate roots, a page in each, and
    each space's definition scoped to its root's pages. A test marked `process` reads
    through the real CLI under this interpreter (`pkit_on_path`)."""
    if request.node.get_closest_marker("process") is not None:
        request.getfixturevalue("pkit_on_path")
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
            f"{LD.as_posix()}/project/config.yaml": json.dumps(SPACES, indent=2) + "\n",
            f"{DEFINITIONS}/user.md": _definition("USER", "docs"),
            f"{DEFINITIONS}/technical.md": _definition("TECH", "tech-docs"),
        }
    )
    return repo


def one_call_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each call of the in-process `pkit` made one at a time, the next waiting for the
    one before to end: a call uses the process's directory, environment and standard
    streams, so it is not safe beside another in a thread, and the filler starts its
    three readings in threads (`InProcessPkit`). Each reading still starts when the
    filler starts it. A call made inside another, in its thread, goes on. A call handed
    a list on its standard input reads it whole before it waits its turn, as a process
    reads its input on its own: the filler hands the check the pages once another call,
    the pages' reading, has been answered."""
    call = InProcessPkit.__call__
    lock = threading.RLock()

    def one_at_a_time(self: InProcessPkit, *args: Any, **options: Any) -> Any:
        stdin = options.get("stdin")
        if stdin is not None:
            options["stdin"] = io.StringIO(stdin.read())
        with lock:
            return call(self, *args, **options)

    monkeypatch.setattr(InProcessPkit, "__call__", one_at_a_time)


def filled(root: Path, *args: str, pkit: Runner | None = None) -> subprocess.CompletedProcess[str]:
    """The documentation-check filler, as the backbone runs it: its `main` with `--json`,
    or `args` when given, in this process from `root`, in the environment the backbone
    gives a query. Every `pkit` it reads through is answered in this process, by `pkit`
    when given, each call one at a time (`one_call_at_a_time`)."""
    fill, backbone = load("living-docs", "fill-doc-check.py", "backbone")
    with pytest.MonkeyPatch.context() as patched:
        one_call_at_a_time(patched)
        route_pkit(patched, backbone, pkit)
        return run_main(fill, *(args or ("--json",)), cwd=root, env=QUERY_ENVIRONMENT)


def _validate(repo: AdopterRepo, *, pkit: Runner | None = None) -> dict[str, Any]:
    """The validator's findings document, as the backbone reads it: its `main` with
    `--json` in this process from the repository's root, in the environment the backbone
    gives a query, every `pkit` it reads through answered in this process, by `pkit`
    when given."""
    validate, backbone = load("living-docs", "validate.py", "backbone")
    with pytest.MonkeyPatch.context() as patched:
        route_pkit(patched, backbone, pkit)
        completed = run_main(validate, "--json", cwd=repo.root, env=QUERY_ENVIRONMENT)
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


def test_the_point_resolves_an_entry_that_carries_paths_and_one_that_carries_none(
    docs_project: AdopterRepo,
) -> None:
    """The paths an entry carries reach whoever reads the point, the agent's
    reader-review among them (DEC-001 points 6 and 7)."""
    docs_project.write(
        {
            "docs/guide.md": _page("operator"),
            "tech-docs/README.md": _page("guest"),
            READERS_FILLER: (
                "schema_version: 1\nvalue:\n"
                "  - id: operator\n"
                "    description: Runs the service in production.\n"
                "    paths:\n"
                "      - description: Restarts the service after a failure.\n"
                "        pages: [README.md, docs/runbooks/index.md, docs/runbooks/restart.md]\n"
                "  - {id: guest, description: A visitor who reads the guide once.}\n"
            ),
        }
    )
    result = CliRunner().invoke(main, ["connections", "resolve", READERS, "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["resolved"] is True
    values = {entry["id"]: entry["value"] for entry in document["entries"]}
    assert values["operator"]["paths"] == [RESTART_PATH]
    assert "paths" not in values["guest"]
    assert "paths" not in values["user"]
    validated = _validate(docs_project)
    assert _errors(validated) == []
    assert "guest, maintainer, operator, user" in _readers_line(validated)


def test_an_entry_whose_path_is_a_glob_leaves_the_point_unresolved(
    docs_project: AdopterRepo,
) -> None:
    """A path names the pages a reader reads, so a glob fits no path, and under
    `fail` the project's filler is inert and the whole point unresolved."""
    docs_project.write(
        {
            READERS_FILLER: (
                "schema_version: 1\nvalue:\n"
                "  - id: operator\n"
                "    description: Runs the service in production.\n"
                '    paths: ["docs/runbooks/**"]\n'
            ),
        }
    )
    result = CliRunner().invoke(main, ["connections", "resolve", READERS, "--json"])
    assert result.exit_code == 1, result.output
    document = json.loads(result.output)
    assert document["resolved"] is False
    (inert,) = [filler for filler in document["fillers"] if filler.get("state") == "inert"]
    assert "does not fit the point" in inert["reason"]


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


def test_the_point_is_read_only_when_some_page_names_a_reader(docs_project: AdopterRepo) -> None:
    """A `pkit` that answers nothing for the point is never asked while no page names
    a reader; once one does, no document is an unresolved point, never a pass. The
    places are read through `pkit` whatever the pages say, so only the point's read
    is broken."""
    broken = _answering(
        "connections", lambda argv, _own: subprocess.CompletedProcess(argv, 3, "", "")
    )
    docs_project.write(
        {"docs/guide.md": "# Not a page yet\n", "tech-docs/README.md": "# Nor this\n"}
    )
    document = _validate(docs_project, pkit=broken)
    assert _errors(document) == []
    assert _readers_line(document) == (
        "readers: no page names one yet, so pkit::documentation:readers is not read."
    )
    docs_project.write({"docs/guide.md": _page("user")})
    ((location, message),) = _errors(_validate(docs_project, pkit=broken))
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
        "schema_version": 1,
        "address": DOC_CHECK,
        "defined": False,
        "from": "resolution",
        "resolved": False,
        "outcome": "undefined",
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


def test_nothing_committed_owes_nothing(
    tracked_project: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = start_in_process(monkeypatch)
    one_call_at_a_time(monkeypatch)
    document, ours = _living_docs_entries(tracked_project)
    assert ("living-docs", "fill-doc-check.py") in [(s.parents[1].name, s.name) for s in started]
    assert document["resolved"], document["why"]
    assert ours == []
    filler = next(f for f in document["fillers"] if f["name"] == "living-docs")
    assert (filler["state"], filler["query_contract"]) == ("taken", True)
    assert filler["reads"] == [
        {"state": "history", "ref": "HEAD", "commit": None, "shallow": False}
    ]


def _fill_doc_check(root: Path) -> subprocess.CompletedProcess[str]:
    """The filler run as the backbone runs it, from `root`, as a process of its own, for
    a test marked `process`."""
    return subprocess.run(
        [sys.executable, str(root / LD / "scripts" / "fill-doc-check.py"), "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_history_not_yet_made_is_empty_and_history_cut_short_is_no_answer(
    docs_project: AdopterRepo, tmp_path: Path
) -> None:
    """The two cases a filler that reads history tells apart (COR-052 point 6): with
    no commit there is nothing owed and it answers `[]`; in a shallow clone that
    stops short of where a page was last judged it gives no answer, never `[]`."""
    unmade = filled(docs_project.root)
    assert unmade.returncode == 0, unmade.stderr
    assert json.loads(unmade.stdout) == {"schema_version": 1, "value": []}

    repo = docs_project
    page: dict[str, Any] = {"reader": "user", "kind": "signpost"}
    repo.write(
        {
            "src/a.py": "A = 1\n",
            "docs/guide.md": friction_document(None, anchors={"path": ["src/a.py"]}, **page),
        }
    )
    repo.commit("base")
    for version in (2, 3, 4):
        repo.commit(f"a {version}", {"src/a.py": f"A = {version}\n"})
    shallow = tmp_path / "shallow"
    repo.git("clone", "-q", "--depth", "2", f"file://{repo.root}", str(shallow))
    cut = filled(shallow)
    assert (cut.returncode, cut.stdout) == (1, ""), cut.stderr
    assert "git fetch --unshallow" in cut.stderr


def _git_asked_outside_pkit(
    tmp_path_factory: pytest.TempPathFactory, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """A `pkit` and a `git` first on PATH. The `pkit` marks every process it starts;
    the `git` writes its arguments, one line per call, to the first file returned —
    and to the second when the call comes from outside `pkit`, one the script under
    test makes of its own — then runs the real one."""
    real = shutil.which("git")
    assert real is not None
    bin_dir = tmp_path_factory.mktemp("git-outside-pkit")
    every, outside = bin_dir / "every", bin_dir / "outside"
    every.touch()
    outside.touch()
    marker = "PKIT_TEST_INSIDE_BACKBONE"
    scripts = {
        "pkit": f'#!/bin/sh\n{marker}=1\nexport {marker}\nexec "{pkit_on_path / "pkit"}" "$@"\n',
        "git": (
            f'#!/bin/sh\necho "$*" >> "{every}"\n'
            f'[ -n "${marker}" ] || echo "$*" >> "{outside}"\nexec "{real}" "$@"\n'
        ),
    }
    for name, body in scripts.items():
        (bin_dir / name).write_text(body, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return every, outside


@pytest.mark.process(
    "that the filler asks git nothing of its own is seen only by a git first on PATH, told "
    "apart by whether a pkit process started it"
)
def test_a_history_git_cannot_read_is_no_answer_and_the_filler_asks_git_nothing(
    docs_project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A commit is there and git cannot read it: the filler exits 1 and prints
    nothing — never `[]`, the answer only where there is no commit yet (COR-052
    point 6). Whether HEAD names a commit is the backbone's reading, `head` in
    `pkit repository base --json`: the filler asks git nothing of its own."""
    repo = docs_project
    head = repo.commit("base", {"src/a.py": "A = 1\n"})
    repo.lose_object(head)
    every, outside = _git_asked_outside_pkit(tmp_path_factory, pkit_on_path, monkeypatch)
    unread = _fill_doc_check(repo.root)
    assert (unread.returncode, unread.stdout) == (1, ""), unread.stderr
    assert unread.stderr == (
        f"error: HEAD names {head[:12]}, which git cannot read as a commit here; "
        "no obligations can be given.\n"
    )
    assert every.read_text(encoding="utf-8")  # the backbone asked, through this git
    assert outside.read_text(encoding="utf-8") == ""


#: The filler's three readings, each named by the two words after `pkit`.
HEAD, CHECK, PAGES_READ = "repository base", "friction check", "friction artefacts"

#: How long a reading waits for the others, in seconds, before it is taken to wait in vain.
PATIENCE = 5.0


def _reading(argv: Sequence[str]) -> str:
    return " ".join(argv[1:3])


def _met() -> Runner:
    """A `pkit` that answers each call in this process, the first call of each of the
    three readings only once all three have started: a reading started only after
    another was answered never comes, and the wait breaks (`threading.Barrier`)."""
    pkit = InProcessPkit()
    barrier = threading.Barrier(3, timeout=PATIENCE)
    waited: set[str] = set()
    guard = threading.Lock()

    def run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
        reading = _reading(argv)
        with guard:
            first = reading in (HEAD, CHECK, PAGES_READ) and reading not in waited
            waited.add(reading)
        if first:
            barrier.wait()
        return pkit(argv, **options)

    return run


def _failing(failing: Sequence[str]) -> Runner:
    """A `pkit` that answers each call in this process, or, for a reading `failing`
    names, exits 1 saying so; the reading of HEAD only once the other two have ended, so
    the readings that end first are never for that the ones named."""
    pkit = InProcessPkit()
    ended: set[str] = set()
    others_ended = threading.Event()
    guard = threading.Lock()

    def answer(argv: list[str], options: dict[str, Any]) -> subprocess.CompletedProcess[Any]:
        if _reading(argv) not in failing:
            return pkit(argv, **options)
        said = f"{_reading(argv)} failed on purpose\n"
        out: Any = ("", said) if options.get("text") else (b"", said.encode())
        if not options.get("capture_output"):
            sys.stderr.write(said)
            out = (None, None)
        completed = subprocess.CompletedProcess(argv, 1, *out)
        if options.get("check"):
            completed.check_returncode()
        return completed

    def run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
        reading = _reading(argv)
        if reading == HEAD:
            others_ended.wait(PATIENCE)
        try:
            return answer(list(argv), options)
        finally:
            with guard:
                ended.add(reading)
                if {CHECK, PAGES_READ} <= ended:
                    others_ended.set()

    return run


def test_the_filler_starts_its_three_readings_at_once(docs_project: AdopterRepo) -> None:
    """None of the three readings waits for another: each starts before any of them is
    answered — the check before it is handed the pages — and the answer is the one they
    give."""
    docs_project.write({"src/a.py": "A = 1\n"})
    docs_project.commit("base")
    alone = filled(docs_project.root)
    assert alone.returncode == 0, alone.stderr
    met = filled(docs_project.root, pkit=_met())
    assert (met.returncode, met.stdout) == (0, alone.stdout), met.stderr


@pytest.mark.parametrize(
    ("committed", "failing", "named"),
    [
        (True, ("friction check", "friction artefacts"), "`pkit friction check --all --json`"),
        (True, ("friction artefacts",), "the pages cannot be told"),
        (True, ("repository base", "friction check"), "`pkit repository base --json`"),
        (False, ("friction check", "friction artefacts"), None),
    ],
)
def test_the_filler_reads_its_answers_in_the_order_the_answer_depends_on_them(
    docs_project: AdopterRepo,
    committed: bool,
    failing: tuple[str, ...],
    named: str | None,
) -> None:
    """Read at once, the readings are still read in order — HEAD, the check, the
    places: the first that gives no answer is the one named, and with no commit
    nothing is owed, whatever the others gave, as when each waited for the last."""
    if committed:
        docs_project.write({"src/a.py": "A = 1\n"})
        docs_project.commit("base")
    answered = filled(docs_project.root, pkit=_failing(failing))
    if named is None:
        assert (answered.returncode, json.loads(answered.stdout)) == (
            0,
            {"schema_version": 1, "value": []},
        ), answered.stderr
        return
    assert (answered.returncode, answered.stdout) == (1, ""), answered.stderr
    assert answered.stderr.startswith(f"error: {named}"), answered.stderr
    assert answered.stderr.count("failed on purpose") <= 1


def test_the_filler_has_the_check_judge_the_pages_alone(docs_project: AdopterRepo) -> None:
    """The obligations read only the pages' judgements and the measures, so the filler
    asks the check to judge the pages and no other artefact, handing it the pages on its
    standard input (`--artefacts-from -`). However many other artefacts a change brings
    or makes stale, the check judges the pages alone, and what it reads of the rest —
    the uncovered surface — is the whole repository's still (#2365)."""
    repo = docs_project
    page: dict[str, Any] = {"reader": "user", "kind": "signpost"}
    records = {
        f"tech-docs/decisions/ADR-00{n}-a.md": friction_document(
            f"ADR-00{n}", anchors={"path": ["src/a.py"]}, title="A", status="accepted"
        )
        for n in range(1, 6)
    }
    repo.write(
        {
            "src/a.py": "A = 1\n",
            "src/b.py": "B = 1\n",
            "docs/guide.md": friction_document(None, anchors={"path": ["src/a.py"]}, **page),
            **records,
        }
    )
    repo.commit("base")
    repo.commit("change a", {"src/a.py": "A = 2\n"})
    pkit = InProcessPkit()
    checks: list[dict[str, Any]] = []

    def run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
        answered = pkit(argv, **options)
        if _reading(argv) == CHECK:
            checks.append(json.loads(answered.stdout))
        return answered

    answered = filled(repo.root, pkit=run)
    assert answered.returncode == 0, answered.stderr
    (argv,) = [call for call in pkit.calls if _reading(call) == CHECK]
    assert argv == ["pkit", "friction", "check", "--all", "--json", "--artefacts-from", "-"]
    (check,) = checks
    assert check["selection"] == {"named": ["docs/guide.md", "tech-docs/README.md"], "absent": []}
    assert [a["location"] for a in check["artefacts"]] == ["docs/guide.md"]
    assert check["measures"]["uncovered_surface"] == ["src/b.py"]
    assert [(o["reason"], o.get("document") or o.get("path")) for o in _value(answered)] == [
        ("page-stale", "docs/guide.md"),
        ("code-undocumented", "src/b.py"),
    ]


def _value(answered: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
    return json.loads(answered.stdout)["value"]


#: The filler's CPU time on project-kit's own tree, in units of the work `_yaml_unit`
#: does, may grow to this before the budget fails: twice the 19 units it took when the
#: budget was set, on 31 October 2026, when judging every artefact took 31. The filler
#: must answer well within the 30 s `pkit validate` gives a query command (#2365), so a
#: doubling of its work fails here first. What still grows with each change is the
#: reading of every answer file in history (ADR-079, Implications): raise the budget only
#: with the reason it grew.
DOC_CHECK_BUDGET = 38


def _yaml_unit() -> float:
    """The CPU time of a fixed piece of the work the filler's time is made of: a run of
    answer-file-shaped YAML parsed with the backbone's own loader, in pure Python. The
    budget is counted in it, so a runner slower than another counts the same."""
    entry = (
        "  - artefact: tech-docs/analysis/core/glossary.md#TERM-{n}\n"
        "    read:\n"
        + "".join(f"      - 2026102{d}T00000{d}Z-0000000{d}.yaml\n" for d in range(8))
        + "    revalidated:\n      at: 2026-10-30T04:15:20Z\n      outcome: unchanged\n"
        '      unchanged-because: "The page still says what the code does."\n'
    )
    text = "answers:\n" + "".join(entry.format(n=n) for n in range(40))
    loader = YAML(typ="safe", pure=True)
    start = time.process_time()
    for _ in range(20):
        loader.load(text)
    return time.process_time() - start


@pytest.mark.answers
def test_the_filler_answers_within_its_budget_on_project_kit_s_own_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The documentation check on this repository, history and answers included, as
    `pkit validate` runs it, every `pkit` it reads through and every resolver answered in
    this process: its CPU time holds within `DOC_CHECK_BUDGET`, counted in `_yaml_unit`s
    so a slow runner and a fast one count alike (#2365)."""
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if shallow.stdout.strip() != "false":
        pytest.skip("the check reads every artefact's history, which this clone does not hold")
    start_in_process(monkeypatch)
    unit = min(_yaml_unit() for _ in range(3))
    start = time.process_time()
    answered = filled(REPO)
    spent = time.process_time() - start
    assert answered.returncode == 0, answered.stderr
    assert spent / unit <= DOC_CHECK_BUDGET, (
        f"fill-doc-check took {spent:.1f} s of CPU, {spent / unit:.0f} units of "
        f"{unit:.3f} s, over its budget of {DOC_CHECK_BUDGET}: find what doubled its work "
        f"before raising the budget"
    )


@pytest.mark.process(
    "the filler's end-to-end test: pkit connections resolve starts fill-doc-check as the "
    "point's query filler, and the filler's view for a person runs as a process"
)
def test_the_filler_contributes_page_friction_and_uncovered_surface(
    tracked_project: AdopterRepo,
) -> None:
    """Through the backbone: the whole-repository check at HEAD, the pages among its
    artefacts, obligations in project-management's shape beside the mapping's. The
    stale page owes; the deferred one does not."""
    repo = tracked_project
    page: dict[str, Any] = {"reader": "user", "kind": "signpost"}
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
    assert [(o["id"], o.get("document"), o.get("path")) for o in ours] == [
        ("friction:page-stale:docs/guide.md", "docs/guide.md", None),
        ("friction:code-undocumented:src/d.py", None, "src/d.py"),
    ]
    assert ours[0]["description"] == (
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
    assert human.stdout.splitlines()[0] == "pkit::work-tracking:doc-check: 2 friction obligation(s)"
    # And `pkit validate` passes with the role, both points and the contribution.
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "packages", "--only", "connections"]
    )
    assert result.exit_code == 0, result.output


def test_a_page_anchored_on_a_part_owes_only_when_that_part_changes(
    tracked_project: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through the backbone, which reads each part anchor as the friction checks do
    (COR-050 points 2 and 5): a page anchored on one section of another page, on its
    lead, or on one point of a record owes an answer only when that part changed. A
    change elsewhere in the same page or record asks the others nothing, and the
    obligation names the part anchor that changed. The fillers start in this process."""
    start_in_process(monkeypatch)
    one_call_at_a_time(monkeypatch)
    repo = tracked_project
    page: dict[str, Any] = {"reader": "user", "kind": "signpost"}
    record = repo.root / LD / "decisions" / "DEC-001-living-docs-discipline.md"
    text = record.read_text(encoding="utf-8")
    heading = "### 3. What the shared rules require\n\n"
    assert heading in text
    repo.write(
        {
            "src/a.py": "A = 1\n",
            "docs/cli.md": friction_document(
                None,
                anchors={"path": ["src/a.py"]},
                body=(
                    "# CLI\n\nThe lead.\n\n## Output\n\nWhere it writes.\n\n"
                    "## Timeout\n\nThirty seconds.\n"
                ),
                **page,
            ),
            "docs/output.md": friction_document(
                None, anchors={"artefact": ["docs/cli.md#output"]}, **page
            ),
            "docs/timeout.md": friction_document(
                None, anchors={"artefact": ["docs/cli.md#timeout"]}, **page
            ),
            "docs/lead.md": friction_document(None, anchors={"artefact": ["docs/cli.md#"]}, **page),
            "docs/point-3.md": friction_document(
                None, anchors={"record": ["living-docs:DEC-001#3"]}, **page
            ),
            "docs/point-4.md": friction_document(
                None, anchors={"record": ["living-docs:DEC-001#4"]}, **page
            ),
        }
    )
    repo.commit("base")
    edited = text.replace(heading, f"{heading}A sentence added to point 3.\n\n", 1)
    repo.commit(
        "change one section and one point",
        {
            "docs/cli.md": friction_document(
                None,
                anchors={"path": ["src/a.py"]},
                body=(
                    "# CLI\n\nThe lead.\n\n## Output\n\nWhere it writes.\n\n"
                    "## Timeout\n\nSixty seconds.\n"
                ),
                **page,
            ),
            f"{LD.as_posix()}/decisions/DEC-001-living-docs-discipline.md": edited,
        },
    )

    resolved, ours = _living_docs_entries(repo)
    assert resolved["resolved"], resolved["why"]
    assert [(o["document"], o["description"]) for o in ours] == [
        (
            "docs/point-3.md",
            "stale: record living-docs:DEC-001#3 changed — pkit friction explain docs/point-3.md",
        ),
        (
            "docs/timeout.md",
            "stale: artefact docs/cli.md#timeout changed — pkit friction explain docs/timeout.md",
        ),
    ]
    assert list(_schema(PM_CAPABILITY, "doc-check.schema.json").iter_errors(ours)) == []


def _track(repo: AdopterRepo, config: str) -> None:
    """project-management's configuration, and the stamp its check's gate reads."""
    repo.write(
        {
            f"{PM}/project/config.yaml": (
                "schema_version: 1\ndefault_branch: main\nworkstreams: []\n" + config
            ),
            f"{PM}/project/bootstrap-stamp.yaml": (
                "schema_version: 1\n"
                "bootstrap:\n"
                "  completed_at: '2026-01-01T00:00:00+00:00'\n"
                "  capability_version: 0.0.0-test\n"
                "  by: bootstrap\n"
                "  repo:\n"
            ),
        }
    )


def _check_doc_mapping(repo: AdopterRepo, body: Path) -> subprocess.CompletedProcess[str]:
    """project-management's check of the branch against `base`, reading the point
    through the real `pkit` first on PATH. The base is named as a reference, read as
    named, so the backbone has nothing to say of it on standard error (COR-054)."""
    env = {k: v for k, v in os.environ.items() if k != "PKIT_OFFLINE"}
    script = repo.root / PM / "scripts" / "check-doc-mapping.py"
    return subprocess.run(
        [sys.executable, str(script), "--base", "refs/heads/base", "--pr-body-file", str(body)],
        cwd=repo.root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.process(
    "project-management's doc-mapping gate end to end, across two capabilities: it reads "
    "the point through pkit connections resolve, which starts the filler, and a CI gate "
    "is judged by its exit code and exact streams"
)
def test_an_uncovered_path_is_unmet_until_a_page_on_the_branch_anchors_it(
    tracked_project: AdopterRepo, tmp_path: Path
) -> None:
    """One branch in two states, through the real friction check, filler, point and
    check. A change under the internal root that anchors nothing leaves the path
    unmet, and so does a `## Doc impact` line naming it; once a page on the branch
    anchors the path, the filler — reading HEAD — no longer gives the obligation."""
    repo = tracked_project
    _track(
        repo,
        "code_path_to_doc_mapping:\n"
        "  rules:\n"
        "    - { code: 'lib/**', docs: [tech-docs/lib.md] }\n"
        "doc_check:\n"
        "  sources:\n"
        "    friction: enforcing\n",
    )
    repo.write({"src/d.py": "D = 1\n"})
    repo.commit("base")
    repo.git("branch", "base")
    body = tmp_path / "body.md"
    body.write_text(
        "## Doc impact\n- src/d.py: described in tech-docs/README.md\n", encoding="utf-8"
    )

    readme = _page("maintainer") + "\n`src/d.py` holds D.\n"
    repo.commit("describe d", {"tech-docs/README.md": readme})
    unmet = _check_doc_mapping(repo, body)
    assert (unmet.returncode, unmet.stdout, unmet.stderr) == (
        1,
        "check-doc-mapping: 1 rule(s), 1 changed file(s), mode=advisory\n"
        "check-doc-mapping: 1 contributed obligation(s) from friction\n"
        "  ✗ [friction] src/d.py → no page anchors it (code-undocumented); "
        "anchor `src/d.py` from a page\n",
        "\n[refused] 1 friction obligation(s) unanchored — anchor each path from a page; "
        "a `## Doc impact` line does not meet them.\n",
    )

    page = friction_document(
        None, anchors={"path": ["src/d.py"]}, reader="maintainer", kind="signpost"
    )
    repo.commit("anchor d", {"tech-docs/d.md": page})
    met = _check_doc_mapping(repo, body)
    assert (met.returncode, met.stdout, met.stderr) == (
        0,
        "check-doc-mapping: 1 rule(s), 2 changed file(s), mode=advisory\n"
        "check-doc-mapping: all touched mappings satisfied.\n",
        "",
    )


# --- the contribution to the fixers point ------------------------------------------------


def _fixer_verb(repo: AdopterRepo, verb: str) -> dict[str, Any]:
    """A fixer command of project-management, with `--json`, reading the point and
    the type registries through the real `pkit` first on PATH."""
    completed = subprocess.run(
        [sys.executable, str(repo.root / PM / "scripts" / f"{verb}.py"), "--json"],
        cwd=repo.root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _deploy_agent(repo: AdopterRepo, text: str) -> None:
    """The agent's file as the harness runs it, deployed in the adopter."""
    target = repo.root / ".claude" / "agents" / f"{AGENT}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _our_fixer(listed: dict[str, Any]) -> dict[str, Any]:
    (fixer,) = [f for f in listed["fixers"] if f["agent"] == AGENT]
    (entry,) = fixer["types"]
    return entry


#: project-management's reading and checks of the fixers point, loaded with its `_lib`
#: kept apart.
(pm_fixers,) = load("project-management", "fixers")


def _unbounded(pkit: Runner) -> Runner:
    """`pkit`, a call's `timeout` left out: nothing bounds a call answered in this
    process, as nothing bounds a command `start_in_process` starts."""

    def run(argv: Sequence[str], *, timeout: float | None = None, **options: Any) -> Any:
        return pkit(argv, **options)

    return run


def _checked(repo: AdopterRepo) -> tuple[Any, list[Any]]:
    """project-management's reading of the fixers point and its checks of each entry,
    its public functions called in this process, every `pkit` they read through
    answered here too."""
    pkit = _unbounded(InProcessPkit())
    point = pm_fixers.read_point(run=pkit)
    return point, pm_fixers.check(
        point, repo.root, types=functools.partial(pm_fixers.read_types, run=pkit)
    )


@pytest.mark.process(
    "the fixers point's end-to-end test: project-management's list-fixers and "
    "check-fixers, each a process reading the point through pkit, with living-docs' entry"
)
def test_the_fixer_of_pages_passes_project_management_s_checks(
    tracked_project: AdopterRepo,
) -> None:
    """The declaration through the real backbone, with project-management's checks:
    the capability's own type, an agent it ships and deploys, a static value, and an
    agent that only proposes. Nobody was asked, so nothing is granted."""
    _track(tracked_project, "")
    _deploy_agent(tracked_project, DEPLOYED_AGENT.read_text(encoding="utf-8"))
    listed = _fixer_verb(tracked_project, "list-fixers")
    assert listed["resolved"], listed["why"]
    assert _our_fixer(listed) == {
        "type": PAGE_TYPE,
        "description": "your pages",
        "origin": "living-docs",
        "answer": None,
        "problems": [],
    }
    checked = _fixer_verb(tracked_project, "check-fixers")
    assert checked["findings"] == []
    assert checked["summary"] == [
        f"{FIXERS}: 1 type(s) for 1 agent(s); 1 pass the checks, 0 granted"
    ]


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (
            (
                "tools: [Read, Glob, Grep, Bash, Write]",
                "tools: [Read, Glob, Grep, Bash, Write, Edit]",
            ),
            "holds Edit, a tool that changes existing files",
        ),
        (
            (
                "tools: [Read, Glob, Grep, Bash, Write]",
                "tools: [Read, Glob, Grep, Bash, Write, Agent]",
            ),
            "holds Agent, a tool that starts agents",
        ),
        (("owns: []", "owns: [docs/**]"), "claims paths (docs/**)"),
        (("tools: [Read, Glob, Grep, Bash, Write]\n", ""), "lists no tools"),
    ],
    ids=["edit", "agent", "owns", "no-tools"],
)
def test_a_fixer_of_pages_that_does_more_than_propose_starts_no_agent(
    tracked_project: AdopterRepo, change: tuple[str, str], problem: str
) -> None:
    """Were the agent's definition to change files, start agents, claim paths or take
    every tool, the checks would report the capability's entry, and it would start
    no agent."""
    _track(tracked_project, "")
    text = DEPLOYED_AGENT.read_text(encoding="utf-8")
    old, new = change
    assert text.count(old) == 1
    _deploy_agent(tracked_project, text.replace(old, new))
    point, checked = _checked(tracked_project)
    assert point.resolved, point.why
    assert (point.agents, [item.entry.type for item in checked]) == ((AGENT,), [PAGE_TYPE])
    (item,) = checked
    (reported,) = item.problems
    assert problem in reported.text, reported
    assert reported.severity == "report"
    assert not item.startable
