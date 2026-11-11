"""Tests for a capability's write categories and the defaults written for them
(COR-073, ADR-088 points 2 to 6): the query's answer, the writer's check of it,
the written line and its mark, and the fill commands — `pkit agents reconcile`,
`pkit agents adopt` and the status report — that write, move and report them."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import click
import pytest

from project_kit import agents_overlay as ao
from project_kit import write_categories as wcat

REPO = Path(__file__).resolve().parents[1]
OWNERSHIP = REPO / ".pkit" / "lifecycle" / "ownership.py"

CATEGORY = "drawing.work"
OVERLAY = Path(".pkit") / "agents" / "project" / "overlay.yaml"

# The default query: prints the project root's `answer.json`, or exits 3 without one.
QUERY = """#!/usr/bin/env python3
import pathlib, sys
answer = pathlib.Path("answer.json")
if not answer.is_file():
    print("no answer.json", file=sys.stderr)
    sys.exit(3)
print(answer.read_text())
"""


def _project(tmp_path: Path, *, overlay: str = "", query: bool = True) -> Path:
    """A project with the capability `drawing` registered, shipping `designer`, which
    owns `drawing.work`, answered by `default-work` unless *query* is False."""
    root = tmp_path / "proj"
    (root / ".pkit" / "lifecycle").mkdir(parents=True)
    shutil.copy2(OWNERSHIP, root / ".pkit" / "lifecycle" / "ownership.py")
    (root / ".pkit" / "manifest.yaml").write_text(
        "schema_version: 1\nbackbone_version: 1.0.0\ncomponents:\n"
        "  - kind: capability\n    name: drawing\n"
        "    manifest: .pkit/capabilities/drawing/project/manifest.yaml\n"
        "    origin: kit-shipped\n",
        encoding="utf-8",
    )
    cap = root / ".pkit" / "capabilities" / "drawing"
    (cap / "agents").mkdir(parents=True)
    (cap / "scripts").mkdir()
    (cap / "agents" / "designer.md").write_text(
        f"---\nname: designer\ndescription: Draws.\nowns:\n  - <{CATEGORY}>\n---\n\n# Designer\n",
        encoding="utf-8",
    )
    script = cap / "scripts" / "default-work.py"
    script.write_text(QUERY, encoding="utf-8")
    script.chmod(0o755)
    entry = "    default-query: default-work\n" if query else ""
    (cap / "package.yaml").write_text(
        "schema_version: 2\ncomponent:\n  kind: capability\n  name: drawing\n  version: 0.1.0\n"
        "description: Drawing.\nrequires_backbone: '>=0.1.0'\ncommands:\n  default-work:\n"
        "    script: scripts/default-work.py\n    help: Where the designer works.\n"
        f"    query-contract: true\nwrite_categories:\n  {CATEGORY}:\n    owner: designer\n"
        f"{entry}",
        encoding="utf-8",
    )
    (root / ".pkit" / "agents" / "project").mkdir(parents=True)
    (root / OVERLAY).write_text(overlay, encoding="utf-8")
    return root


def _answer(root: Path, *paths: str, note: str | None = None) -> None:
    document: dict[str, object] = {"paths": list(paths)}
    if note is not None:
        document["note"] = note
    (root / "answer.json").write_text(json.dumps(document), encoding="utf-8")


def _overlay(root: Path) -> str:
    return (root / OVERLAY).read_text(encoding="utf-8")


def _asked_in_process(root: Path, category: wcat.WriteCategory) -> wcat.Answer | wcat.NoAnswer:
    """The query's answer, read as the script would print it, without its process."""
    answer = root / "answer.json"
    if category.default_query is None:
        return wcat.Answer(paths=())
    if not answer.is_file():
        return wcat.NoAnswer(f"command {category.default_query!r} exited 3: no answer.json")
    return wcat.read_answer(json.loads(answer.read_text(encoding="utf-8")), "default-work")


@pytest.fixture(autouse=True)
def in_process(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test but the runner's own reads the query's answer in this process."""
    if request.node.get_closest_marker("process") is None:
        monkeypatch.setattr(wcat, "ask", _asked_in_process)


# --- the written line (ADR-088 point 4) ---------------------------------------


def test_a_write_appends_the_line_with_its_mark_and_a_comment() -> None:
    document = wcat.OverlayDocument("workflow-docs:\n  - README.md\n")
    document.write(CATEGORY, ["visual/"])
    assert document.text == (
        "workflow-docs:\n  - README.md\n\n"
        f"{wcat.WRITTEN_COMMENT}\n"
        f'{CATEGORY}: ["visual/"]  # pkit-written: ["visual/"]\n'
    )
    assert not wcat.WRITTEN_COMMENT.startswith(f"# {CATEGORY}")  # never read as a stub
    assert document.still_as_written(CATEGORY) == ["visual/"]


def test_a_bare_key_is_filled_and_a_commented_stub_left() -> None:
    bare = wcat.OverlayDocument(f"a: []\n{CATEGORY}:\nb: []\n")
    assert not bare.gives_value(CATEGORY, "designer")
    bare.write(CATEGORY, ["visual/"])
    assert bare.text.splitlines()[1:3] == [
        wcat.WRITTEN_COMMENT,
        f'{CATEGORY}: ["visual/"]  # pkit-written: ["visual/"]',
    ]
    assert bare.text.splitlines()[3] == "b: []"

    stub = wcat.OverlayDocument(f"# {CATEGORY}:\n#   - <path>\n")
    stub.write(CATEGORY, [])
    assert stub.text.startswith(f"# {CATEGORY}:\n#   - <path>\n")
    assert stub.data()[CATEGORY] == []


def test_a_path_named_true_reads_back_as_a_string() -> None:
    document = wcat.OverlayDocument("")
    document.write(CATEGORY, ["true", "~", "a, b #c"])
    assert document.data()[CATEGORY] == ["true", "~", "a, b #c"]
    assert document.still_as_written(CATEGORY) == ["true", "~", "a, b #c"]


@pytest.mark.parametrize(
    "line",
    [
        f'{CATEGORY}: ["art/"]  # pkit-written: ["visual/"]',  # the value edited
        f'{CATEGORY}: ["visual/"]',  # the mark removed
        f"{CATEGORY}: [visual/]  # pkit-written: [true]",  # types that differ
        f"{CATEGORY}:\n  - visual/",  # another form
    ],
    ids=["edited", "no-mark", "differs-by-type", "block-form"],
)
def test_a_line_a_person_touched_is_the_projects(line: str) -> None:
    document = wcat.OverlayDocument(line + "\n")
    assert document.still_as_written(CATEGORY) is None
    assert document.gives_value(CATEGORY, "designer")


def test_an_owners_override_gives_a_value() -> None:
    document = wcat.OverlayDocument(f"overrides:\n  designer:\n    {CATEGORY}: [art/]\n")
    assert document.gives_value(CATEGORY, "designer")
    assert not document.gives_value(CATEGORY, "someone-else")


def test_a_move_rewrites_that_one_line() -> None:
    text = f'top: [a]\n# keep\n{CATEGORY}: ["visual/"]  # pkit-written: ["visual/"]\ntail: []\n'
    document = wcat.OverlayDocument(text)
    document.move(CATEGORY, ["art/"])
    assert document.text == text.replace('["visual/"]', '["art/"]')


# --- the answer (point 2) -----------------------------------------------------


@pytest.mark.parametrize(
    ("document", "says"),
    [
        ([], "no JSON object"),
        ({"paths": "visual/"}, "is no list"),
        ({"paths": [], "extra": 1}, "extra"),
        ({"paths": ["/abs"]}, "not relative"),
        ({"paths": ["a/../b"]}, "`..` segment"),
        ({"paths": ["*.md"]}, "glob"),
        ({"paths": [], "note": "two\nlines"}, "no line of text"),
    ],
    ids=["not-an-object", "not-a-list", "unknown-key", "absolute", "dotdot", "glob", "note"],
)
def test_a_document_of_another_shape_is_no_answer(document: object, says: str) -> None:
    answer = wcat.read_answer(document, "default-work")
    assert isinstance(answer, wcat.NoAnswer)
    assert says in answer.reason


def test_no_path_is_an_answer() -> None:
    assert wcat.read_answer({"paths": []}, "q") == wcat.Answer(paths=())


@pytest.mark.process("the default query runs through the runner the query commands share")
def test_the_query_runs_from_the_root_and_its_failure_is_no_answer(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (category,) = wcat.installed(root)
    assert isinstance(wcat.ask(root, category), wcat.NoAnswer)
    _answer(root, "visual/", note="the recorded location")
    assert wcat.ask(root, category) == wcat.Answer(("visual/",), "the recorded location")


# --- the check (point 3) ------------------------------------------------------


def _refusal(root: Path, *paths: str, others: list[tuple[str, str]] | None = None) -> str | None:
    from project_kit import lifecycle_ownership

    (category,) = wcat.installed(root)
    return wcat.refusal(
        root, category, paths, others or [], lifecycle_ownership.load_ownership(root)
    )


def test_a_clear_answer_passes(tmp_path: Path) -> None:
    assert _refusal(_project(tmp_path), "visual/", "docs/drawings/") is None


@pytest.mark.parametrize(
    ("path", "says"),
    [
        (".pkit/capabilities/drawing/project/", "own folder"),
        (".pkit/capabilities/", "own folder"),
        (".pkit/agents/core/", "overwrites"),
    ],
    ids=["its-project-folder", "holding-its-folder", "managed"],
)
def test_one_failing_path_refuses_the_answer_whole(tmp_path: Path, path: str, says: str) -> None:
    reason = _refusal(_project(tmp_path), "visual/", path)
    assert reason is not None and says in reason and path in reason


def test_a_path_out_through_a_link_is_refused(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (tmp_path / "outside").mkdir()
    (root / "linked").symlink_to(tmp_path / "outside")
    reason = _refusal(root, "linked/")
    assert reason is not None and "outside the repository" in reason


def test_a_path_another_agent_owns_is_refused_naming_it(tmp_path: Path) -> None:
    reason = _refusal(_project(tmp_path), "docs/", others=[("architect", "docs/architecture")])
    assert reason is not None and "architect" in reason and "docs/architecture" in reason


# --- reconcile, adopt and the status report (point 6) -------------------------


def test_reconcile_shows_then_writes_a_missing_default(tmp_path: Path) -> None:
    root = _project(tmp_path, overlay="workflow-docs: [README.md]\n")
    _answer(root, "visual/")

    _added, report = ao.reconcile_overlay(root, write=False)
    assert f"{CATEGORY} = visual/" in report and "would write" in report
    assert CATEGORY not in _overlay(root)

    added, report = ao.reconcile_overlay(root, write=True)
    assert added == [CATEGORY]
    assert f'{CATEGORY}: ["visual/"]  # pkit-written: ["visual/"]' in _overlay(root)
    assert f"# {CATEGORY}:" not in _overlay(root)  # no stub besides


def test_a_category_with_no_default_is_written_empty(tmp_path: Path) -> None:
    root = _project(tmp_path, query=False)
    ao.reconcile_overlay(root, write=True)
    assert f"{CATEGORY}: []  # pkit-written: []" in _overlay(root)


def test_reconcile_moves_a_value_still_as_written(tmp_path: Path) -> None:
    root = _project(tmp_path, overlay='drawing.work: ["visual/"]  # pkit-written: ["visual/"]\n')
    _answer(root, "art/")

    _added, report = ao.reconcile_overlay(root, write=False)
    assert "visual/ → art/" in report
    ao.reconcile_overlay(root, write=True)
    assert _overlay(root) == 'drawing.work: ["art/"]  # pkit-written: ["art/"]\n'


@pytest.mark.parametrize(
    "overlay",
    [
        'drawing.work: ["mine/"]  # pkit-written: ["visual/"]\n',
        "drawing.work: [mine/]\n",
        "overrides:\n  designer:\n    drawing.work: [mine/]\n",
    ],
    ids=["edited", "set-by-the-project", "the-owners-override"],
)
def test_reconcile_keeps_a_value_the_project_set(tmp_path: Path, overlay: str) -> None:
    root = _project(tmp_path, overlay=overlay)
    _answer(root, "art/")
    ao.reconcile_overlay(root, write=True)
    assert _overlay(root) == overlay


def test_reconcile_refuses_an_answer_and_names_why(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _answer(root, ".pkit/")
    _added, report = ao.reconcile_overlay(root, write=True)
    assert "refused" in report and ".pkit/" in report
    assert CATEGORY not in _overlay(root)


def test_reconcile_names_a_query_with_no_answer(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _added, report = ao.reconcile_overlay(root, write=True)
    assert "no answer from" in report and "exited 3" in report
    assert CATEGORY not in _overlay(root)


def test_the_status_report_shows_a_written_default_its_query_moved(tmp_path: Path) -> None:
    root = _project(tmp_path, overlay='drawing.work: ["visual/"]  # pkit-written: ["visual/"]\n')
    _answer(root, "art/")
    report = ao.render_status(root)
    assert "WRITTEN DEFAULTS" in report and "art/" in report
    assert "pkit agents reconcile" in report
    assert "visual/" in _overlay(root) and "art/" not in _overlay(root)  # wrote nothing


def test_adopt_writes_the_declared_answer_and_creates_no_folder(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _answer(root, "visual/")
    result = ao.adopt_agent(root, "designer", deploy_fn=lambda _root, _name: True)
    assert CATEGORY in result.categories_wired
    assert f'{CATEGORY}: ["visual/"]' in _overlay(root)
    assert not (root / "visual").exists()


def test_adopt_over_content_takes_consent(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "visual").mkdir()
    (root / "visual" / "deck.html").write_text("<p>", encoding="utf-8")
    _answer(root, "visual/")
    with pytest.raises(click.ClickException):
        ao.adopt_agent(root, "designer", deploy_fn=lambda _root, _name: True)
    assert CATEGORY not in _overlay(root)
    ao.adopt_agent(root, "designer", yes=True, deploy_fn=lambda _root, _name: True)
    assert f'{CATEGORY}: ["visual/"]' in _overlay(root)


def test_adopt_refuses_a_default_it_cannot_write(tmp_path: Path) -> None:
    root = _project(tmp_path)
    with pytest.raises(click.ClickException, match="no default can be written"):
        ao.adopt_agent(root, "designer", deploy_fn=lambda _root, _name: True)


def test_an_undeclared_dotted_category_is_warned_of(tmp_path: Path) -> None:
    root = _project(tmp_path, overlay="gone.work: [x/]\noverrides:\n  a:\n    gone.more: []\n")
    keys = [u.key for u in ao.undeclared_capability_categories(root)]
    assert keys == ["gone.work", "overrides.a.gone.more"]
    assert "UNDECLARED CAPABILITY CATEGORIES" in ao.render_status(root)
