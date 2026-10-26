"""living-docs reports what a page mentions and does not anchor (#2099; DEC-001 point 6).

Only what a page anchors grounds a statement (RS-LDOC-001), so a page that names
a file, a record, a rule or a command and anchors nothing of it is never asked
when that thing changes. Where RS-LDOC-001 binds on a page, `pkit living-docs
validate` reports each such mention, with an anchor that would cover it, and
never fails on one:

- **what a mention is**: a path to a file the repository holds, in a code span
  or a link, a decision record's id or point, a rule's id and a `pkit` command
  — never one in fenced code or a comment, a path to nothing, a placeholder, or
  a record or a rule the backbone does not resolve;
- **what covers it**: the files each path anchor stands on, as the backbone
  gives them (`path_anchors` in `pkit friction artefacts --json`), an anchor on
  the record, the point or the rule, and for a command the script that
  implements it or the section that documents it;
- **the mark**: an HTML comment `<!-- unanchored: <reason> -->` right after a
  mention passes that one passage over, and a mark that passes over nothing is
  reported;
- **where it binds**: a page RS-LDOC-001 does not bind on is not read.

The findings document holds one report per page, and the human view lists each
mention. The validator runs as the backbone runs it, with the real `pkit` on
PATH, so no test reaches `uv` or the network.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests import test_living_docs_spaces as spaces
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.test_living_docs_spaces import SCRIPT, errors, outside_every_space, run

GUIDE = "docs/guide.md"


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """The clean project of the spaces' tests: living-docs installed, two separate
    roots, a page per space's entry, a decision record and both spaces' definitions,
    whose scopes make RS-LDOC-001 bind on the user space's pages."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    script = repo.root / SCRIPT
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    spaces.declare(repo)
    repo.write(
        {
            "README.md": spaces.PAGE,
            GUIDE: spaces.PAGE,
            "tech-docs/README.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Tech\n",
            f"{spaces.DEFINITIONS}/user.md": spaces._definition("USER"),
            f"{spaces.DEFINITIONS}/technical.md": spaces._definition("TECH"),
        }
    )
    return repo


def _page(body: str, front: str = "") -> str:
    return f"---\nreader: user\nkind: signpost\n{front}---\n\n# Guide\n\n{body}\n"


def _anchored(body: str, anchors: str, front: str = "") -> str:
    return _page(body, f"{front}pkit:\n  friction:\n    anchors: {anchors}\n")


def _reports(document: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [
        (f["location"], f["message"]) for f in document["findings"] if f["severity"] == "report"
    ]


def _mention_line(document: Mapping[str, Any]) -> str:
    (line,) = [line for line in document["summary"] if line.startswith("mentions")]
    return line


def _listed(repo: AdopterRepo) -> list[str]:
    """The mentions the human view lists, each as `<line>: <kind> `<name>` → <anchor>`."""
    completed = subprocess.run(
        [sys.executable, str(repo.root / SCRIPT)],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = completed.stdout.splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("mention(s) a page")]
    if not heads:
        return []
    return [line.strip() for line in lines[heads[0] + 1 :] if line.startswith("    ")]


def _guide(project: AdopterRepo, text: str, **files: str) -> dict[str, Any]:
    project.write({GUIDE: text, **files})
    return run(project)


# --- a file ---------------------------------------------------------------------------


def test_a_file_the_page_names_and_does_not_anchor_is_reported_never_failed(
    project: AdopterRepo,
) -> None:
    document = _guide(project, _page("Start `src/app.py` first."), **{"src/app.py": "pass\n"})
    assert errors(document) == []
    ((location, message),) = _reports(document)
    assert location == GUIDE
    assert message.startswith(f"{GUIDE} mentions 1 file(s) that its anchors do not cover")
    assert (
        "`<!-- unanchored: <reason> -->`" in message and "(RS-LDOC-001; DEC-001 point 6)" in message
    )
    assert "1 the page's anchors do not cover" in _mention_line(document)
    assert _listed(project) == ["8: path `src/app.py` → path: [src/app.py]"]


def test_a_path_anchor_standing_on_the_file_grounds_it(project: AdopterRepo) -> None:
    document = _guide(
        project, _anchored("Start `src/app.py` first.", "{path: [src/**]}"), **{"src/app.py": "x\n"}
    )
    assert _reports(document) == []
    assert "0 the page's anchors do not cover" in _mention_line(document)


def test_what_names_no_file_the_repository_holds_is_no_mention(project: AdopterRepo) -> None:
    body = (
        "A missing `src/gone.py`, a name `app.py`, a placeholder `src/<name>.py`, a glob "
        "`src/**`, a folder `src/` and a URL [the site](https://example.com/a.md).\n\n"
        "```\nsrc/app.py\n```\n\n<!-- `src/app.py` -->\n\n~~`src/app.py`~~"
    )
    document = _guide(project, _page(body), **{"src/app.py": "x\n"})
    assert _reports(document) == []
    assert "0 mention(s)" in _mention_line(document)


def test_a_code_span_is_read_from_the_root_and_failing_that_from_the_page_s_folder(
    project: AdopterRepo,
) -> None:
    project.write({"docs/shots/a.txt": "x\n"})
    _guide(project, _page("See `shots/a.txt`."))
    assert _listed(project) == ["8: path `docs/shots/a.txt` → path: [docs/shots/a.txt]"]


def test_a_link_to_a_section_of_a_page_is_grounded_by_that_section_or_the_whole_page(
    project: AdopterRepo,
) -> None:
    project.write({"docs/ref.md": _page("## Use\n\nHow.")})
    _guide(project, _page("Read [how to use it](ref.md#use)."))
    assert _listed(project) == ["8: path `docs/ref.md` → artefact: [docs/ref.md#use]"]
    for anchor in ("docs/ref.md#use", "docs/ref.md"):
        document = _guide(
            project, _anchored("Read [how to use it](ref.md#use).", f"{{artefact: [{anchor}]}}")
        )
        assert _reports(document) == [], anchor


# --- a record -------------------------------------------------------------------------


def test_a_record_and_its_point_are_reported_with_the_record_anchor(project: AdopterRepo) -> None:
    _guide(project, _page("A page rests on its anchors (COR-050 points 2 and 5)."))
    assert _listed(project) == ["8: record `COR-050#2` → record: [COR-050#2, COR-050#5]"]


def test_an_anchor_on_the_whole_record_or_on_each_point_grounds_the_mention(
    project: AdopterRepo,
) -> None:
    body = "A page rests on its anchors (COR-050 point 5)."
    for anchors in ("{record: [COR-050]}", "{record: ['COR-050#5']}"):
        assert _reports(_guide(project, _anchored(body, anchors))) == [], anchors
    _guide(project, _anchored(body, "{record: ['COR-050#2']}"))
    assert _listed(project) == ["11: record `COR-050#5` → record: [COR-050#5]"]


def test_a_capability_s_decision_is_read_in_each_of_its_forms(project: AdopterRepo) -> None:
    body = (
        "Spaces ([living-docs:DEC-001-living-docs-discipline] point 1), and "
        "living-docs DEC-002, and `living-docs:DEC-001#4`."
    )
    _guide(project, _page(body))
    assert _listed(project) == [
        "8: record `living-docs:DEC-001#1` → record: [living-docs:DEC-001#1]",
        "8: record `living-docs:DEC-002` → record: [living-docs:DEC-002]",
        "8: record `living-docs:DEC-001#4` → record: [living-docs:DEC-001#4]",
    ]
    document = _guide(
        project, _anchored(body, "{record: ['living-docs:DEC-001', 'living-docs:DEC-002']}")
    )
    assert _reports(document) == []


def test_a_record_the_backbone_does_not_resolve_is_no_mention(project: AdopterRepo) -> None:
    document = _guide(project, _page("No such record: COR-999, nor DEC-001 out of a capability."))
    assert _reports(document) == []


def test_a_link_to_a_record_s_file_mentions_the_record(project: AdopterRepo) -> None:
    _guide(
        project, _page("See [the record](../.pkit/decisions/core/COR-050-anchors-and-friction.md).")
    )
    assert _listed(project) == ["8: record `COR-050` → record: [COR-050]"]


# --- a command ------------------------------------------------------------------------


def test_a_capability_s_command_is_grounded_by_its_script(project: AdopterRepo) -> None:
    body = "Run `pkit living-docs validate --json`."
    _guide(project, _page(body))
    (listed,) = _listed(project)
    assert listed.startswith("8: command `pkit living-docs validate` → ")
    assert listed.endswith("or path: [.pkit/capabilities/living-docs/scripts/validate.py]")
    script = ".pkit/capabilities/living-docs/scripts/validate.py"
    assert _reports(_guide(project, _anchored(body, f"{{path: [{script}]}}"))) == []


def test_a_backbone_command_is_grounded_by_the_reference_that_documents_it(
    project: AdopterRepo,
) -> None:
    body = "Run `uv run pkit validate`."
    _guide(project, _page(body))
    (listed,) = _listed(project)
    # The adopter's CLI reference lies in no place, so it is anchored by its path.
    assert listed == (
        "8: command `pkit validate` → path: [.pkit/cli/README.md], which documents it in its "
        "section headed ``validate``"
    )
    assert _reports(_guide(project, _anchored(body, "{path: [.pkit/cli/README.md]}"))) == []


def test_text_in_a_code_span_that_is_no_command_is_no_mention(project: AdopterRepo) -> None:
    document = _guide(project, _page("`pkit --version`, `pkit`, `pkg sync` and `git status`."))
    assert _reports(document) == []


# --- the mark -------------------------------------------------------------------------


def test_a_marked_passage_is_passed_over_and_counted(project: AdopterRepo) -> None:
    body = (
        "`src/app.py` <!-- unanchored: named only as where the app starts -->, "
        "COR-050 point 5 <!-- unanchored: named, not relied on --> and "
        "`pkit living-docs validate` <!-- unanchored: the command is named, not described -->."
    )
    document = _guide(project, _page(body), **{"src/app.py": "x\n"})
    assert _reports(document) == []
    assert "3 passage(s) marked unanchored on purpose" in _mention_line(document)


def test_a_mark_passes_over_its_passage_alone(project: AdopterRepo) -> None:
    """A mark covers the mention right before it, so a later passage that rests on the
    same thing is still read, and so is an earlier mention on the mark's line."""
    body = (
        "`src/app.py` and COR-050 <!-- unanchored: named only -->.\n\n"
        "`src/app.py` prints the greeting."
    )
    _guide(project, _page(body), **{"src/app.py": "x\n"})
    assert _listed(project) == ["8: path `src/app.py` → path: [src/app.py]"]


def test_a_mark_that_passes_over_nothing_is_reported(project: AdopterRepo) -> None:
    body = (
        "Nothing named <!-- unanchored: no longer named -->.\n\n"
        "`src/app.py` <!-- unanchored -->\n\n"
        "COR-050 <!-- unanchored: covered now -->"
    )
    document = _guide(project, _anchored(body, "{record: [COR-050]}"), **{"src/app.py": "x\n"})
    idle = [(loc, msg) for loc, msg in _reports(document) if loc.startswith(f"{GUIDE}:")]
    assert [loc for loc, _msg in idle] == [f"{GUIDE}:11", f"{GUIDE}:13", f"{GUIDE}:15"]
    whys = [msg.split("since ", 1)[1].split(". ", 1)[0] for _loc, msg in idle]
    assert whys == [
        "it follows no mention on its line",
        "it gives no reason after `unanchored:`",
        "the mention it follows is one the page's anchors cover",
    ]
    assert all("(DEC-001 point 6)" in msg for _loc, msg in idle)
    # A mark that gives no reason passes nothing over: the mention is still reported.
    assert GUIDE in [loc for loc, _msg in _reports(document)]
    assert errors(document) == []


# --- a rule ---------------------------------------------------------------------------


def test_a_rule_is_grounded_by_an_anchor_on_the_rule(project: AdopterRepo) -> None:
    body = "A page names its reader ([living-docs:RS-LDOC-003])."
    _guide(project, _page(body))
    assert _listed(project) == ["8: rule `RS-LDOC-003` → artefact: [RS-LDOC-003]"]
    assert _reports(_guide(project, _anchored(body, "{artefact: [RS-LDOC-003]}"))) == []
    assert _reports(_guide(project, _page("No such rule: RS-LDOC-999."))) == []


# --- where it binds -------------------------------------------------------------------


def test_a_page_rs_ldoc_001_does_not_bind_on_is_not_read(project: AdopterRepo) -> None:
    outside_every_space(project)
    body = "`src/app.py`, and a mark that follows nothing <!-- unanchored -->"
    project.write({"docs/drafts/a.md": _page(body), "src/app.py": "x\n"})
    document = run(project)
    assert errors(document) == []
    assert [loc for loc, _m in _reports(document) if loc.startswith("docs/drafts")] == []
    assert "1 page(s) RS-LDOC-001 does not bind on, not read" in _mention_line(document)
