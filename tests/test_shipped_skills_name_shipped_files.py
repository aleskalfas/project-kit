"""A shipped skill names only files the install ships (#2156).

A skill the methodology ships runs in the project it was installed into. A file
it names that the install does not ship is, there, a file of the project's own
or none at all. `decision-author` sent its reader to sections of the methodology
source's own `CONTRIBUTING.md`, which no install writes, so in an adopter's
repository those sections were never there.

What the install ships is the bundle: the `.pkit/` trees `hatch_build.py` takes
file by file (`FILTERED_TREES`), less the project's side of the split, and the
single files `pyproject.toml` force-includes. `pkit init` and `pkit sync` copy
the backbone's areas from it, and `pkit capabilities install` a capability's
subtree. The project's side of the split (COR-001), which
`.pkit/lifecycle/ownership.py`'s `is_adopter_owned_by_tier` answers, is the
project's own: a skill may name a file there, such as the agents overlay.

A name is read the way a reader in the skill's folder finds it: the nearest file
of that path in the skill's folder or a folder above it, up to the repository's
root. So a bare `README.md` in a capability's skill is the capability's README,
and a bare `CONTRIBUTING.md` is the one at the root. A name that resolves to no
file this repository tracks names a file of the project's, such as a folder it
creates, and is not this test's to judge.

Held here:

- every file a shipped skill names that this repository tracks is one the
  bundle ships, or one on the project's side of the split
- no shipped skill names the methodology source's example projects
- the check flags a name that does not ship, and passes one that does
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import subprocess
import tomllib
from functools import cache
from pathlib import Path, PurePosixPath
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[1]

# A file name: path characters ending in a file extension. Not preceded by a
# character that makes it part of a template (`<name>.md`), a glob (`*.yaml`),
# a URL (`https://…`) or a longer name, and not followed by a word character.
_FILE_NAME = re.compile(
    r"(?<![\w./<>{}*:@-])"
    r"((?:[\w.-]+/)*[\w-][\w.-]*\.(?:md|ya?ml|json|py|sh|toml|txt))"
    r"(?![\w])"
)

#: The methodology source's example projects, which no adopter has.
_EXAMPLE_PROJECTS = re.compile(r"\bexample-(?:brownfield|greenfield)\b")


@cache
def _tracked() -> frozenset[str]:
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True
    ).stdout.decode()
    return frozenset(filter(None, listing.split("\0")))


@cache
def _ownership() -> ModuleType:
    """The ownership module, loaded by path as the build hook loads it."""
    spec = importlib.util.spec_from_file_location(
        "_ownership_for_skills", REPO / ".pkit" / "lifecycle" / "ownership.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def _filtered_trees() -> tuple[str, ...]:
    """`FILTERED_TREES` from `hatch_build.py`, read without importing hatchling."""
    tree = ast.parse((REPO / "hatch_build.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "FILTERED_TREES"
            and isinstance(node.value, ast.Tuple)
        ):
            return tuple(
                e.value
                for e in node.value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            )
    raise AssertionError("FILTERED_TREES not found in hatch_build.py")


@cache
def _force_included() -> frozenset[str]:
    """The single files `pyproject.toml` force-includes into the wheel."""
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return frozenset(pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"])


def _ships(rel: str) -> bool:
    """True when the bundle carries the repository-relative file *rel*."""
    if rel in _force_included():
        return True
    if not rel.startswith(".pkit/"):
        return False
    kit_rel = rel.removeprefix(".pkit/")
    in_a_tree = any(kit_rel.startswith(f"{tree}/") for tree in _filtered_trees())
    return in_a_tree and not _ownership().is_adopter_owned_by_tier(kit_rel)


def _the_projects_own(rel: str) -> bool:
    """True when *rel* sits on the project's side of the split."""
    return rel.startswith(".pkit/") and _ownership().is_adopter_owned_by_tier(
        rel.removeprefix(".pkit/")
    )


def _resolve(skill: str, name: str) -> str | None:
    """The tracked file *name* names, read from the folder of the skill *skill*."""
    folder = PurePosixPath(skill).parent
    for base in (folder, *folder.parents):
        candidate = os.path.normpath(os.path.join(str(base), name))
        if candidate.startswith(".."):
            continue
        if candidate in _tracked():
            return candidate
    return None


def unshipped_names(skill: str, text: str) -> list[str]:
    """Each file *text*, a shipped skill at *skill*, names that the install does not
    ship, as `<name> -> <file>`, in the order the text names them."""
    found: list[str] = []
    for match in _FILE_NAME.finditer(text):
        name = match.group(1)
        rel = _resolve(skill, name)
        if rel is None or _ships(rel) or _the_projects_own(rel):
            continue
        entry = f"{name} -> {rel}"
        if entry not in found:
            found.append(entry)
    return found


def _shipped_skills() -> list[str]:
    """Every file of a skill the install ships: core's, and each capability's."""
    capability_skill = re.compile(r"\.pkit/capabilities/[^/]+/skills/.+\.md")
    return sorted(
        rel
        for rel in _tracked()
        if rel.endswith(".md")
        and (rel.startswith(".pkit/skills/core/") or capability_skill.fullmatch(rel))
    )


# --- the shipped skills -------------------------------------------------------


def test_there_are_shipped_skills_to_check() -> None:
    skills = _shipped_skills()
    assert ".pkit/skills/core/decision-author.md" in skills
    assert ".pkit/capabilities/project-management/skills/pm/pm.md" in skills


@pytest.mark.parametrize("skill", _shipped_skills())
def test_a_shipped_skill_names_only_files_the_install_ships(skill: str) -> None:
    text = (REPO / skill).read_text(encoding="utf-8")
    unshipped = unshipped_names(skill, text)
    assert not unshipped, (
        f"{skill} names files the install does not ship, so an installed project "
        f"lacks them: {unshipped}. Put what the skill needs in the skill, or in a "
        "document the install ships, such as an area's README."
    )


@pytest.mark.parametrize("skill", _shipped_skills())
def test_a_shipped_skill_names_no_example_project(skill: str) -> None:
    text = (REPO / skill).read_text(encoding="utf-8")
    named = sorted(set(_EXAMPLE_PROJECTS.findall(text)))
    assert not named, f"{skill} names the methodology source's example projects: {named}"


# --- the check ----------------------------------------------------------------

_CORE_SKILL = ".pkit/skills/core/an-example.md"
_CAPABILITY_SKILL = ".pkit/capabilities/project-management/skills/pm/an-example.md"


@pytest.mark.parametrize(
    "text,flagged",
    [
        ("Read `CONTRIBUTING.md`'s **Adding a core record** section.", ["CONTRIBUTING.md"]),
        ('See CONTRIBUTING.md\'s "Lead with meaning".', ["CONTRIBUTING.md"]),
        ("reads:\n  paths:\n    - CONTRIBUTING.md\n", ["CONTRIBUTING.md"]),
        ("The suite is described in `tests/README.md`.", ["tests/README.md"]),
        ("The tree's index, `.pkit/README.md`.", [".pkit/README.md"]),
        ("The release guide, `.pkit/release/README.md`.", [".pkit/release/README.md"]),
        ("[the guide](../../../CONTRIBUTING.md#running-checks)", ["../../../CONTRIBUTING.md"]),
    ],
)
def test_the_check_flags_a_file_the_install_does_not_ship(text: str, flagged: list[str]) -> None:
    names = [entry.split(" -> ")[0] for entry in unshipped_names(_CORE_SKILL, text)]
    assert names == flagged


@pytest.mark.parametrize(
    "skill,text",
    [
        (_CORE_SKILL, "Read `.pkit/decisions/README.md`'s **Schema** section."),
        (_CORE_SKILL, "Its `README.md` says what it ships."),
        (_CORE_SKILL, "The overlay, `.pkit/agents/project/overlay.yaml`."),
        (_CORE_SKILL, "The version, `.pkit/VERSION`, and `.pkit/scratchpad/README.md`."),
        (_CORE_SKILL, "[COR-025](../../decisions/core/COR-025-adr-decision-space.md)"),
        (_CORE_SKILL, "Stamp `.pkit/capabilities/<name>/README.md`, then `schemas/*.yaml`."),
        (_CORE_SKILL, "A project's own `docs/architecture/decisions/ADR-001-x.md`."),
        (_CAPABILITY_SKILL, "Run `scripts/create-issue.py`, as the `README.md` says."),
        (_CAPABILITY_SKILL, "Its config, `project/config.yaml`."),
        (_CAPABILITY_SKILL, "See https://example.com/CONTRIBUTING.md for theirs."),
    ],
)
def test_the_check_passes_a_file_the_install_ships(skill: str, text: str) -> None:
    assert unshipped_names(skill, text) == []
