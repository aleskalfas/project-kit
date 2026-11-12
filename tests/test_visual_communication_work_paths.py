"""`pkit visual work-paths` (DEC-030 point 5, COR-073 point 3): the default of the
graphic-designer's grant, the location of the visual work. The recorded location, else
`visual/` where a writing command would take it, else no path with the reason; and no
answer where the configuration cannot be read. The capability declares the category it
answers, owned by the designer. Run in this process (`tests/in_process.py`); it starts no
`pkit`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from project_kit import write_categories
from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CAPABILITY,
    CONFIG,
    bound,
    project,
    write,
    yaml_text,
)

(work_paths,) = load("visual-communication", "work-paths.py")

BINDING = "pkit_schema: visual-communication:config\nschema_version: 1\n"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(work_paths, *args, cwd=root)


def answer(root: Path) -> dict[str, object]:
    shown = run(root, "--json")
    assert shown.returncode == 0, shown.stderr
    return json.loads(shown.stdout)


def test_with_nothing_there_it_answers_the_default(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert answer(root) == {"paths": ["visual/"]}


def test_it_answers_the_location_the_configuration_records(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / CONFIG, BINDING + "location: art/figures\n")
    write(root / "visual" / "notes.txt", "not the visual work\n")
    assert answer(root) == {"paths": ["art/figures/"]}


def test_a_default_that_holds_the_work_or_nothing_is_answered(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "visual").mkdir()
    assert answer(root) == {"paths": ["visual/"]}
    write(root / "visual" / "libraries" / "libraries.yaml", yaml_text(bound("libraries")))
    assert answer(root) == {"paths": ["visual/"]}


def test_a_default_that_holds_other_files_is_never_granted(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual" / "notes.txt", "not the visual work\n")
    found = answer(root)
    assert found["paths"] == []
    assert "holds files that are not the visual work" in str(found["note"])
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.startswith("no path: `visual/` holds files")


def test_a_default_that_cannot_be_the_location_is_never_granted(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual", "a file, not a folder\n")
    found = answer(root)
    assert found["paths"] == []
    assert "is not a folder" in str(found["note"])


def test_a_configuration_it_cannot_take_gives_no_answer(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / CONFIG, BINDING + "location: .pkit/visual\n")
    shown = run(root, "--json")
    assert shown.returncode == 1
    assert shown.stdout == ""
    assert "under `.pkit/`" in shown.stderr
    write(root / CONFIG, BINDING + "location: [unclosed\n")
    assert run(root, "--json").returncode == 1


def test_it_prints_each_path_on_a_line_of_its_own(tmp_path: Path) -> None:
    root = project(tmp_path)
    shown = run(root)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout == "visual/\n"


def test_its_answer_is_one_a_writer_of_a_default_reads(tmp_path: Path) -> None:
    root = project(tmp_path)
    read = write_categories.read_answer(answer(root), "work-paths")
    assert read == write_categories.Answer(paths=("visual/",))
    write(root / "visual" / "notes.txt", "not the visual work\n")
    read = write_categories.read_answer(answer(root), "work-paths")
    assert isinstance(read, write_categories.Answer)
    assert read.paths == ()


def test_the_capability_declares_the_designers_category_with_this_query() -> None:
    (category,) = write_categories.declared_in("visual-communication", CAPABILITY)
    assert (category.name, category.owner, category.default_query) == (
        "visual-communication.work",
        "graphic-designer",
        "work-paths",
    )
    designer = write_categories.capability_agents(CAPABILITY)["graphic-designer"]
    assert write_categories.owned_placeholders(designer) == {"visual-communication.work"}
