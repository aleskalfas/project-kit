"""visual-communication: the visual-author skill (#2781).

The skill walks whoever draws a piece through starting one and through its build loop.
Held here:

- **its shape**: a composite skill (COR-020) whose `composes` is exactly its two
  procedures, clean under `pkit refs validate`, deployed beside them and granted by the
  settings merge;
- **it matches the commands it walks**: every command it names is one the capability
  registers, with flags that command takes, and every field and report entry it names is
  one the capability reads or writes;
- **it matches the check**: every label the loop names is one `checks.md` holds, each with
  what to do, and every link it gives leads to a heading;
- **what it says is what happens**: the command `piece.md` runs stamps the `piece.yaml` it
  shows. In a project with no location, the deck and the figure `piece.md` stamps and fills,
  and the local component `build-loop.md` writes, render and pass the check, and a render
  passes over a mistyped key that the check reports. The brief `piece.md` writes holds its
  schema, names only what the deck holds, and fails the check once the deck renames a page
  it names.

The commands run in the test's own process (`tests/in_process.py`).
"""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import refs
from project_kit.document_parts import heading_slug
from tests.in_process import load, run_main
from tests.visual_communication_project import CAPABILITY, CONFIG, SCHEMAS, importable, project

add, new, render, check, svg, seam, files, reading = load(
    "visual-communication",
    "add.py",
    "new.py",
    "render.py",
    "check.py",
    "plugins.svg",
    "plugins.seam",
    "files",
    "reading",
)

REPO = Path(__file__).resolve().parent.parent
SKILL = CAPABILITY / "skills" / "visual-author"
DISPATCHER = SKILL / "visual-author.md"
PIECE_MD = SKILL / "piece.md"
LOOP_MD = SKILL / "build-loop.md"
DEPLOYED = REPO / ".claude" / "skills" / "visual-author"
PROCEDURES = ("piece.md", "build-loop.md")
PIECE = "first-talk"
FOLDER = f"visual/pieces/{PIECE}"
#: The command the skill points on to, and runs no step of.
POINTED_AT = {"export"}

_YAML_FENCE = re.compile(r"^```yaml\n(?P<block>.*?)^```", re.MULTILINE | re.DOTALL)
_PLAIN_FENCE = re.compile(r"^```\n(?P<block>.*?)^```", re.MULTILINE | re.DOTALL)
_COMMAND = re.compile(r"pkit visual ([a-z][a-z-]*)")
_SPAN = re.compile(r"`(pkit visual [^`]*)`")
_FLAG = re.compile(r"(--[a-z][a-z-]*)")
_LINK = re.compile(r"\]\((?P<target>[^)#\s]+)(?:#(?P<anchor>[^)\s]+))?\)")
_HEADING = re.compile(r"^#{1,6} (?P<title>.+)$", re.MULTILINE)
_LABEL = re.compile(r"`([a-z][a-z-]*)`")


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a render makes when it draws."""
    importable(monkeypatch, svg)
    yield
    seam.unregister("svg")


def _front(path: Path) -> dict[str, Any]:
    _, front, _body = path.read_text(encoding="utf-8").split("---\n", 2)
    return YAML(typ="safe").load(front) or {}


def _texts() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in (DISPATCHER, *(SKILL / name for name in PROCEDURES))
    }


def _section(text: str, heading: str) -> str:
    """The text under `heading`, up to the next heading of its level or above."""
    level = len(heading) - len(heading.lstrip("#"))
    _, found, rest = text.partition(f"{heading}\n")
    assert found, heading
    ending = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return rest[: ending.start()] if ending else rest


def _rows(text: str) -> list[list[str]]:
    """Each table row of `text`, its header and rule left out, as its cells."""
    lines = [line for line in text.splitlines() if line.startswith("|")]
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if set(cells[0]) <= {"-"} or cells[0] in {"Label", "Field", "Library", "Entry", "It says"}:
            continue
        rows.append(cells)
    return rows


def _fences(path: Path, schema: str) -> list[str]:
    return [
        found["block"]
        for found in _YAML_FENCE.finditer(path.read_text(encoding="utf-8"))
        if f"pkit_schema: visual-communication:{schema}\n" in found["block"]
    ]


# --- its shape ---------------------------------------------------------------------------------


def test_the_skill_composes_its_two_procedures() -> None:
    front = _front(DISPATCHER)
    assert front["name"] == "visual-author"
    assert sorted(front["composes"]) == sorted(PROCEDURES)
    assert sorted(p.name for p in SKILL.iterdir()) == sorted([*PROCEDURES, DISPATCHER.name])


def test_the_dispatcher_routes_to_each_procedure_and_they_carry_no_front_matter() -> None:
    routes = _section(DISPATCHER.read_text(encoding="utf-8"), "## Pick the operation")
    for name in PROCEDURES:
        assert f"`{name}`" in routes
        assert (SKILL / name).read_text(encoding="utf-8").startswith("# ")


def test_refs_find_nothing_in_the_skill() -> None:
    folder = str(SKILL.relative_to(REPO))
    assert [i for i in refs.validate_corpus(REPO) if i.location.startswith(folder)] == []
    (skill,) = [a for a in refs.load_artifacts(REPO) if a.name == "visual-author"]
    assert (skill.kind, skill.capability) == ("skill", "visual-communication")


def test_the_skill_is_deployed_beside_its_procedures_and_granted() -> None:
    assert (DEPLOYED / "SKILL.md").resolve() == DISPATCHER.resolve()
    for name in PROCEDURES:
        assert (DEPLOYED / name).resolve() == (SKILL / name).resolve()
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "Skill(visual-author)" in settings["permissions"]["allow"]


def test_the_readme_names_the_skill_under_drawing_a_piece() -> None:
    readme = (CAPABILITY / "README.md").read_text(encoding="utf-8")
    assert "`visual-author`" in _section(readme, "## What this capability ships")
    assert "`visual-author`" in _section(readme, "## Drawing a piece")


# --- it matches the commands it walks ----------------------------------------------------------


def _commands() -> dict[str, Any]:
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    return package["commands"]


def _flags(command: str) -> set[str]:
    """Each flag the script of `command` declares."""
    script = (CAPABILITY / _commands()[command]["script"]).read_text(encoding="utf-8")
    return set(re.findall(r'"(--[a-z][a-z-]*)"', script))


def test_every_command_it_names_is_one_the_capability_registers() -> None:
    named = {command for text in _texts().values() for command in _COMMAND.findall(text)}
    assert named <= set(_commands())
    assert {"add", "render", "check", "look", "pages"} <= named


def test_it_declares_each_command_it_runs() -> None:
    named = {command for text in _texts().values() for command in _COMMAND.findall(text)}
    wrapped = set(_front(DISPATCHER)["metadata"]["wraps_commands"])
    assert wrapped == {f"pkit visual {command}" for command in named - POINTED_AT} | {
        "pkit validate"
    }


@pytest.mark.parametrize("name", ["visual-author.md", *PROCEDURES])
def test_every_flag_it_gives_is_one_its_command_takes(name: str) -> None:
    text = (SKILL / name).read_text(encoding="utf-8")
    for span in _SPAN.findall(text):
        for flag in _FLAG.findall(span):
            assert flag in _flags(span.split()[2]), span
    taken = set().union(*(_flags(command) for command in _commands()))
    assert set(_FLAG.findall(text)) <= taken


def test_each_field_piece_md_chooses_is_one_a_piece_takes_and_each_required_one_is_chosen() -> None:
    schema = json.loads((SCHEMAS / "piece.schema.json").read_text(encoding="utf-8"))
    chosen = {
        row[0].strip("`")
        for row in _rows(
            _section(PIECE_MD.read_text(encoding="utf-8"), "## 2. Choose what the piece is")
        )
    }
    assert chosen <= set(schema["properties"])
    assert set(schema["required"]) - {"pkit_schema", "schema_version"} <= chosen


def test_each_report_entry_the_loop_names_is_one_a_run_writes() -> None:
    reader = (CAPABILITY / "scripts" / "look.py").read_text(encoding="utf-8")
    #: An entry the reader reaches through a constant the viewing module names.
    named = (CAPABILITY / "scripts" / "_lib" / "viewing.py").read_text(encoding="utf-8")
    entries = _rows(_section(LOOP_MD.read_text(encoding="utf-8"), "## 3. Read"))
    assert len(entries) == 7
    for row in entries:
        (entry,) = _LABEL.findall(row[0])
        assert (
            f'["{entry}"]' in reader or f'.get("{entry}")' in reader or f' = "{entry}"' in named
        ), entry
        assert row[2], entry


# --- it matches the check ----------------------------------------------------------------------


def _by_finding() -> str:
    return _section(LOOP_MD.read_text(encoding="utf-8"), "### By finding")


def test_each_label_the_loop_names_is_one_the_check_reports_with_what_to_do() -> None:
    reference = (CAPABILITY / "checks.md").read_text(encoding="utf-8")
    rows = _rows(_by_finding())
    labels = [label for row in rows for label in _LABEL.findall(row[0])]
    assert {"content-key", "text-overflow", "gets-less", "lock-missing", "loss"} <= set(labels)
    assert len(labels) == len(set(labels))
    for label in labels:
        assert f"`{label}`" in reference, label
    assert all(row[1] for row in rows)


def test_each_table_of_labels_follows_a_link_to_checks_md() -> None:
    by_finding = _by_finding()
    tables = re.findall(r"^(.*)\n\n\| Label \|", by_finding, re.MULTILINE)
    assert len(tables) == 4
    for lead in tables:
        assert "(../../checks.md#" in lead, lead


def test_the_render_s_own_facts_it_names_are_ones_the_check_page_holds() -> None:
    reference = (CAPABILITY / "checks.md").read_text(encoding="utf-8")
    for label in ("held-clash", "held-end", "lock-below", "lock-kept"):
        assert f"`{label}`" in _by_finding()
        assert f"`{label}`" in reference


@pytest.mark.parametrize("path", [DISPATCHER, PIECE_MD, LOOP_MD], ids=lambda path: path.name)
def test_each_link_leads_to_a_file_and_a_heading(path: Path) -> None:
    for found in _LINK.finditer(path.read_text(encoding="utf-8")):
        target = (path.parent / found["target"]).resolve()
        assert target.is_file(), found[0]
        if found["anchor"]:
            page = target.read_text(encoding="utf-8")
            slugs = {heading_slug(h["title"]) for h in _HEADING.finditer(page)}
            assert found["anchor"] in slugs, found[0]


# --- what it says is what happens --------------------------------------------------------------


def _add_as_written(root: Path) -> None:
    """Each `pkit visual add` of `piece.md`'s first step, run in its order."""
    commands = _PLAIN_FENCE.search(PIECE_MD.read_text(encoding="utf-8"))
    assert commands is not None
    for line in commands["block"].splitlines():
        assert line.startswith("pkit visual add "), line
        added = run_main(add, line.split()[3], cwd=root)
        assert added.returncode == 0, added.stderr


def _new_as_written(root: Path, *, figure: bool = False) -> Path:
    """`pkit visual new` as `piece.md`'s step 3 runs it, or with the top and the export it
    names for the figure; the piece's folder."""
    text = PIECE_MD.read_text(encoding="utf-8")
    (line,) = (
        found["block"]
        for found in _PLAIN_FENCE.finditer(text)
        if found["block"].startswith("pkit visual new ")
    )
    if figure:
        assert "stamped with `--top foundations/figure` and `--export svg`" in text
        line = line.replace("--top foundations/deck", "--top foundations/figure")
        line = line.replace("--export pdf", "--export svg")
    stamped = run_main(new, *shlex.split(line)[3:], cwd=root)
    assert stamped.returncode == 0, stamped.stderr
    return root / FOLDER


def _write_piece(root: Path, written: str, content: str | None = None) -> Path:
    """The `written` piece, `deck` or `figure`, stamped as `piece.md` stamps it, its content
    `content`, or the one `piece.md` writes for it."""
    deck, figure = _fences(PIECE_MD, "content")
    folder = _new_as_written(root, figure=written == "figure")
    if content is None:
        content = figure if written == "figure" else deck
    (folder / "content.en.yaml").write_text(content, encoding="utf-8")
    return folder


def _rendered_and_passed(root: Path) -> None:
    rendered = run_main(render, PIECE, cwd=root)
    assert rendered.returncode == 0, rendered.stderr
    assert "\nfails:" not in f"\n{rendered.stdout}", rendered.stdout
    for args in ((PIECE,), ()):
        checked = run_main(check, *args, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
        assert checked.returncode == 0, checked.stdout


def test_the_piece_yaml_piece_md_shows_is_the_one_its_command_stamps(tmp_path: Path) -> None:
    root = project(tmp_path)
    _add_as_written(root)
    (piece,) = _fences(PIECE_MD, "piece")
    folder = _new_as_written(root)
    assert (folder / "piece.yaml").read_text(encoding="utf-8") == piece
    assert sorted(path.name for path in folder.iterdir()) == [
        "brief.yaml",
        "content.en.yaml",
        "piece.yaml",
    ]


@pytest.mark.parametrize("written", ["deck", "figure"])
def test_a_piece_written_by_piece_md_renders_and_passes_where_no_location_is(
    tmp_path: Path, written: str
) -> None:
    root = project(tmp_path)
    assert not (root / CONFIG).exists()
    _add_as_written(root)
    assert "location: visual" in (root / CONFIG).read_text(encoding="utf-8")
    folder = _write_piece(root, written)
    stamped = reading.read_yaml(folder / "piece.yaml")
    assert files.shape_problems(stamped, "piece") == []
    assert "lock" not in stamped
    _rendered_and_passed(root)
    assert set(reading.read_yaml(folder / "piece.yaml")["lock"]) == {
        "foundations",
        "neutral",
        "starter",
    }


def test_before_the_first_render_the_check_reports_no_lock_as_piece_md_says(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    _add_as_written(root)
    _write_piece(root, "deck")
    checked = run_main(check, PIECE, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert checked.returncode == 1
    assert "[lock-missing]" in checked.stdout


def test_the_local_component_of_the_loop_draws_and_passes(tmp_path: Path) -> None:
    root = project(tmp_path)
    _add_as_written(root)
    folder = _write_piece(root, "deck")
    content = (folder / "content.en.yaml").read_text(encoding="utf-8")
    (component,) = _fences(LOOP_MD, "component")
    (folder / "components").mkdir()
    (folder / "components" / "note.yaml").write_text(component, encoding="utf-8")
    fence = next(
        found["block"]
        for found in _YAML_FENCE.finditer(LOOP_MD.read_text(encoding="utf-8"))
        if found["block"].startswith("visual:\n")
    )
    filled = YAML(typ="safe").load(content)
    filled["slides"][1].update(YAML(typ="safe").load(fence))
    (folder / "content.en.yaml").write_text(json.dumps(filled), encoding="utf-8")
    _rendered_and_passed(root)


def test_the_brief_of_piece_md_holds_its_schema_and_names_what_its_deck_holds(
    tmp_path: Path,
) -> None:
    (brief,) = _fences(PIECE_MD, "brief")
    assert files.shape_problems(YAML(typ="safe").load(brief), "brief") == []
    root = project(tmp_path)
    _add_as_written(root)
    folder = _write_piece(root, "deck")
    content = (folder / "content.en.yaml").read_text(encoding="utf-8")
    (folder / "brief.yaml").write_text(brief, encoding="utf-8")
    _rendered_and_passed(root)
    (folder / "content.en.yaml").write_text(
        content.replace("id: parts", "id: three-parts"), encoding="utf-8"
    )
    checked = run_main(check, PIECE, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert checked.returncode == 1
    assert f"{FOLDER}/brief.yaml#pages.parts  [brief-page]" in checked.stdout


def test_a_render_passes_over_a_mistyped_key_and_the_check_reports_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    _add_as_written(root)
    deck, _figure = _fences(PIECE_MD, "content")
    _write_piece(root, "deck", deck.replace("head: Content", "heading: Content"))
    rendered = run_main(render, PIECE, cwd=root)
    assert rendered.returncode == 0, rendered.stderr
    assert "heading" not in rendered.stdout
    checked = run_main(check, PIECE, cwd=root, env={"PKIT_COMMAND_DEADLINE": None})
    assert checked.returncode == 1
    place = f"{FOLDER}/content.en.yaml#slides[parts].visual.items[content].heading  [content-key]"
    said = "`starter/card` takes no field or option `heading`; did you mean `head`?"
    assert place in checked.stdout
    assert said in checked.stdout
    quoted = LOOP_MD.read_text(encoding="utf-8")
    assert place in quoted
    assert said in quoted
