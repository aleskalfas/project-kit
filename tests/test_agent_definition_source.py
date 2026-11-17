"""The picker of an agent's definition and the lifecycle's reader of capability
records (COR-013 point 8, COR-017, ADR-087).

- the reader reads the registry, each capability's skips and the project's
  choices, and answers an unreadable record as unreadable: a backbone manifest
  that does not parse leaves the registry and the choices unreadable, a mapping
  of choices it cannot read leaves only the choices, and a capability's manifest
  only that capability's skips; a manifest at the capability's root is read
  before the one under its `project/`;
- the picker takes the project's place over every capability's and core's last,
  counts a capability's definition while the registry records the capability
  and the project has not skipped it, takes the capability the project chose,
  else the first by code points, whatever the locale, and reports each collision
  no choice settles and each choice that decides nothing;
- a place holding both layouts of a name has its definition refused, and still
  the agent; a folder without its canonical file ships none; a hidden entry
  ships nothing;
- what the picker cannot tell is scoped to the names an unreadable record decides;
- both modules keep the standard library at module level, and the digest is the
  file's SHA-256.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.backbone_manifest import register_capabilities

REPO = Path(__file__).resolve().parents[1]
PICKER = REPO / ".pkit" / "agents" / "definition_source.py"
RECORDS_READER = REPO / ".pkit" / "lifecycle" / "capability_records.py"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def picker() -> ModuleType:
    return _load(PICKER, "definition_source_under_test")


@pytest.fixture(scope="module")
def reader() -> ModuleType:
    return _load(RECORDS_READER, "capability_records_under_test")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    for place in ("core", "project"):
        (tmp_path / ".pkit" / "agents" / place).mkdir(parents=True)
    return tmp_path


def _agent(tree: Path, place: str, name: str, *, folder: bool = False) -> Path:
    """A definition of *name* at *place*: `core`, `project` or a capability's name."""
    base = (
        tree / ".pkit" / "agents" / place
        if place in ("core", "project")
        else tree / ".pkit" / "capabilities" / place / "agents"
    )
    path = base / name / f"{name}.md" if folder else base / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: From {place}.\n---\n", encoding="utf-8")
    return path


def _manifest(tree: Path, text: str) -> None:
    (tree / ".pkit" / "manifest.yaml").write_text(text, encoding="utf-8")


def _skip(tree: Path, capability: str, *names: str, at_root: bool = False) -> None:
    folder = tree / ".pkit" / "capabilities" / capability
    path = folder / "manifest.yaml" if at_root else folder / "project" / "manifest.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = "".join(f"    - kind: agent\n      name: {name}\n" for name in names)
    path.write_text(f"backend_state:\n  skipped:\n{entries}", encoding="utf-8")


def _choose(tree: Path, **choices: str) -> None:
    path = tree / ".pkit" / "manifest.yaml"
    lines = "".join(f"  {agent}: {capability}\n" for agent, capability in choices.items())
    path.write_text(path.read_text(encoding="utf-8") + f"agent_choices:\n{lines}", encoding="utf-8")


def _place(pick: object) -> str | None:
    agent = getattr(pick, "agent", None)
    return None if agent is None else agent.place


# --- the reader -----------------------------------------------------------------


def test_the_reader_reads_the_registry_skips_and_choices(reader: ModuleType, tree: Path) -> None:
    register_capabilities(tree, "alpha", "beta")
    _skip(tree, "alpha", "one", "two")
    _choose(tree, shared="beta")

    records = reader.read_records(tree)

    assert [c.name for c in records.capabilities] == ["alpha", "beta"]
    assert records.installed == frozenset({"alpha", "beta"})
    assert records.skips["alpha"].skipped == (("agent", "one"), ("agent", "two"))
    assert records.skips["alpha"].skips_agent("two")
    assert records.skips["beta"].skipped == ()
    assert records.choices == {"shared": "beta"}
    assert records.registry_unreadable is None and records.choices_unreadable is None


def test_a_project_with_no_backbone_manifest_records_no_capability(
    reader: ModuleType, tree: Path
) -> None:
    records = reader.read_records(tree)
    assert records.capabilities == () and records.choices == {}
    assert records.registry_unreadable is None


@pytest.mark.parametrize(
    "text",
    ["components: [\n", "- a list\n", "components: a string\n"],
    ids=["does-not-parse", "not-a-mapping", "components-not-a-list"],
)
def test_an_unreadable_backbone_manifest_leaves_registry_and_choices_unreadable(
    reader: ModuleType, tree: Path, text: str
) -> None:
    _manifest(tree, text)
    records = reader.read_records(tree)
    assert records.registry_unreadable is not None
    assert records.choices_unreadable == records.registry_unreadable
    assert records.capabilities == () and records.choices == {}


@pytest.mark.parametrize("choices", ["[a, b]", "{shared: 3}", "{shared: ''}"])
def test_choices_that_do_not_read_leave_only_the_choices_unreadable(
    reader: ModuleType, tree: Path, choices: str
) -> None:
    register_capabilities(tree, "alpha")
    path = tree / ".pkit" / "manifest.yaml"
    path.write_text(path.read_text(encoding="utf-8") + f"agent_choices: {choices}\n", "utf-8")
    records = reader.read_records(tree)
    assert records.registry_unreadable is None
    assert records.choices_unreadable is not None
    assert records.installed == frozenset({"alpha"})


def test_an_unreadable_capability_manifest_leaves_only_its_skips_unreadable(
    reader: ModuleType, tree: Path
) -> None:
    register_capabilities(tree, "alpha", "beta")
    broken = tree / ".pkit" / "capabilities" / "alpha" / "project" / "manifest.yaml"
    broken.parent.mkdir(parents=True)
    broken.write_text("<<<<<<< HEAD\nbackend_state: [\n", encoding="utf-8")
    records = reader.read_records(tree)
    assert records.skips["alpha"].unreadable is not None
    assert records.skips["alpha"].skipped == ()
    assert records.skips["beta"].unreadable is None


def test_the_manifest_at_the_capabilitys_root_is_read_first(reader: ModuleType, tree: Path) -> None:
    _skip(tree, "alpha", "under-project")
    _skip(tree, "alpha", "at-root", at_root=True)
    assert reader.read_skips(tree, "alpha").skipped == (("agent", "at-root"),)


# --- the picker's order -----------------------------------------------------------


def test_the_project_wins_then_a_capability_then_core(picker: ModuleType, tree: Path) -> None:
    register_capabilities(tree, "alpha")
    for place in ("project", "alpha", "core"):
        _agent(tree, place, "all-three")
    _agent(tree, "alpha", "cap-and-core")
    _agent(tree, "core", "cap-and-core")
    _agent(tree, "core", "core-only")

    picks = picker.pick(tree).picks

    assert _place(picks["all-three"]) == "project"
    assert _place(picks["cap-and-core"]) == "capability:alpha"
    assert _place(picks["core-only"]) == "core"
    assert [d.place for d in picks["all-three"].definitions] == [
        "project",
        "capability:alpha",
        "core",
    ]


def test_an_unregistered_capabilitys_definition_does_not_count(
    picker: ModuleType, tree: Path
) -> None:
    """Its folder stays on disk after an uninstall, and ships nothing (COR-017)."""
    _manifest(tree, "components: []\n")
    _agent(tree, "gone", "lonely")
    _agent(tree, "gone", "shared")
    _agent(tree, "core", "shared")

    picks = picker.pick(tree).picks

    assert picks["lonely"].agent is None
    assert "not installed" in picks["lonely"].none
    assert _place(picks["shared"]) == "core"
    assert picks["shared"].definitions[0].counts is False


def test_a_skipped_definition_does_not_count(picker: ModuleType, tree: Path) -> None:
    register_capabilities(tree, "alpha")
    _agent(tree, "alpha", "shared")
    _agent(tree, "core", "shared")
    _skip(tree, "alpha", "shared")

    pick = picker.pick(tree).picks["shared"]

    assert _place(pick) == "core"
    assert "skipped" in pick.definitions[0].why_not


def test_the_first_capability_by_code_points_wins_and_is_a_collision(
    picker: ModuleType, tree: Path
) -> None:
    """`a-z` before `ab`, as code points order them, where a locale's collation would
    order them the other way."""
    register_capabilities(tree, "ab", "a-z")
    _agent(tree, "ab", "shared")
    _agent(tree, "a-z", "shared")

    answer = picker.pick(tree)

    assert _place(answer.picks["shared"]) == "capability:a-z"
    assert [(c.name, c.capabilities, c.winner) for c in answer.collisions] == [
        ("shared", ("a-z", "ab"), "a-z")
    ]


def test_the_projects_choice_settles_a_collision(picker: ModuleType, tree: Path) -> None:
    register_capabilities(tree, "alpha", "beta")
    _agent(tree, "alpha", "shared")
    _agent(tree, "beta", "shared")
    _choose(tree, shared="beta")

    answer = picker.pick(tree)

    assert _place(answer.picks["shared"]) == "capability:beta"
    assert answer.collisions == () and answer.idle_choices == ()


def test_a_name_the_project_ships_is_no_collision(picker: ModuleType, tree: Path) -> None:
    register_capabilities(tree, "alpha", "beta")
    for place in ("project", "alpha", "beta"):
        _agent(tree, place, "shared")
    assert picker.pick(tree).collisions == ()


def test_each_choice_that_decides_nothing_is_reported(picker: ModuleType, tree: Path) -> None:
    register_capabilities(tree, "alpha", "beta")
    _agent(tree, "alpha", "skipped-one")
    _agent(tree, "beta", "skipped-one")
    _skip(tree, "alpha", "skipped-one")
    _agent(tree, "alpha", "elsewhere")
    _choose(tree, **{"skipped-one": "alpha", "elsewhere": "beta", "orphan": "gone"})

    idle = {c.name: (c.capability, c.why) for c in picker.pick(tree).idle_choices}

    assert idle["orphan"] == ("gone", "capability gone is not installed")
    assert idle["elsewhere"] == ("beta", "capability beta ships no agent named elsewhere")
    assert idle["skipped-one"][1] == "the project skipped capability alpha's agent skipped-one"


# --- layouts ------------------------------------------------------------------------


def test_both_layouts_refuse_the_definition_and_it_stays_the_agent(
    picker: ModuleType, tree: Path
) -> None:
    _agent(tree, "project", "twice")
    _agent(tree, "project", "twice", folder=True)
    _agent(tree, "core", "twice")

    pick = picker.pick(tree).picks["twice"]

    assert _place(pick) == "project"
    assert pick.refused is not None and "keep one" in pick.refused
    assert pick.file is None


def test_a_folder_without_its_canonical_file_and_a_hidden_entry_ship_none(
    picker: ModuleType, tree: Path
) -> None:
    (tree / ".pkit" / "agents" / "core" / "empty").mkdir()
    (tree / ".pkit" / "agents" / "core" / "empty" / "notes.md").write_text("x", "utf-8")
    (tree / ".pkit" / "agents" / "core" / ".hidden.md").write_text("x", "utf-8")
    (tree / ".pkit" / "capabilities" / ".cache" / "agents").mkdir(parents=True)
    (tree / ".pkit" / "capabilities" / ".cache" / "agents" / "x.md").write_text("x", "utf-8")
    assert dict(picker.pick(tree).picks) == {}


# --- what it cannot tell ----------------------------------------------------------------


def test_an_unreadable_registry_leaves_only_capability_names_untold(
    picker: ModuleType, tree: Path
) -> None:
    _manifest(tree, "components: [\n")
    _agent(tree, "alpha", "cap-only")
    _agent(tree, "alpha", "mine")
    _agent(tree, "project", "mine")
    _agent(tree, "core", "core-only")

    picks = picker.pick(tree).picks

    assert picks["cap-only"].untold is not None and picks["cap-only"].agent is None
    assert _place(picks["mine"]) == "project"
    assert _place(picks["core-only"]) == "core"


def test_unreadable_choices_leave_only_contested_names_untold(
    picker: ModuleType, tree: Path
) -> None:
    register_capabilities(tree, "alpha", "beta")
    path = tree / ".pkit" / "manifest.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "agent_choices: [x]\n", "utf-8")
    _agent(tree, "alpha", "shared")
    _agent(tree, "beta", "shared")
    _agent(tree, "alpha", "alone")

    picks = picker.pick(tree).picks

    assert picks["shared"].untold is not None
    assert _place(picks["alone"]) == "capability:alpha"


def test_one_unreadable_manifest_leaves_only_its_capabilitys_names_untold(
    picker: ModuleType, tree: Path
) -> None:
    register_capabilities(tree, "alpha", "beta")
    broken = tree / ".pkit" / "capabilities" / "alpha" / "project" / "manifest.yaml"
    broken.parent.mkdir(parents=True)
    broken.write_text("backend_state: [\n", encoding="utf-8")
    _agent(tree, "alpha", "from-alpha")
    _agent(tree, "beta", "from-beta")

    picks = picker.pick(tree).picks

    assert picks["from-alpha"].untold is not None
    assert _place(picks["from-beta"]) == "capability:beta"


# --- the modules ----------------------------------------------------------------------


def test_the_digest_is_the_files_sha256(picker: ModuleType, tree: Path) -> None:
    path = _agent(tree, "core", "hashed")
    assert picker.digest(path) == "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("module", [PICKER, RECORDS_READER], ids=lambda p: p.name)
def test_each_module_imports_only_the_standard_library_at_module_level(module: Path) -> None:
    """The agent runner and the deploy load them under a Python with no YAML
    library; the reader imports it inside the function that reads (ADR-087)."""
    roots: list[str] = []
    for node in ast.parse(module.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Import):
            roots += [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append(node.module.split(".")[0])
    third_party = {r for r in roots if r not in sys.stdlib_module_names and r != "__future__"}
    assert not third_party
