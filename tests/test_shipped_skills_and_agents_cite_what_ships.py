"""A shipped skill or agent cites only what the install ships (#2156, #2167).

A skill or an agent the methodology ships runs in the project it was installed
into. A file it names that the install does not ship is, there, a file of the
project's own or none at all. `decision-author` sent its reader to sections of
the methodology source's own `CONTRIBUTING.md`, which no install writes, so in
an adopter's repository those sections were never there. The core reviewers did
the same, and two skills cited records of the methodology source's own project,
a PRJ and an ADR record, which no install writes either: in an adopter's
repository that id names the adopter's own record, or none.

What the install ships is the bundle: the `.pkit/` trees `hatch_build.py` takes
file by file (`FILTERED_TREES`), less the project's side of the split, and the
single files `pyproject.toml` force-includes. `pkit init` and `pkit sync` copy
the backbone's areas from it, and `pkit capabilities install` a capability's
subtree. The project's side of the split (COR-001), which
`.pkit/lifecycle/ownership.py`'s `is_adopter_owned_by_tier` answers, is the
project's own: a skill may name a file there, such as the agents overlay. So is
what an installed component, such as an adapter, writes outside `.pkit/`: the
footprint its `package.yaml` declares, which `pkit visibility` reads, such as
the root `CLAUDE.md` the Claude Code adapter adds its rules include to.

A name is read the way a reader in the file's folder finds it: the nearest file
of that path in the file's folder or a folder above it, up to the repository's
root. So a bare `README.md` in a capability's skill is the capability's README,
and a bare `CONTRIBUTING.md` is the one at the root. A name that resolves to no
file this repository tracks names a file of the project's, such as a folder it
creates, and is not this test's to judge.

A record id counts where `pkit refs validate` reads one, in the front matter and
the body outside a fenced block, an HTML comment or a struck-through span. So an
id in a worked example's fence, an example project's own record, is no citation.
It is resolved as `pkit refs lookup` resolves it, and an id that names no record
this repository tracks is the project's to judge, as a name is.

Held here:

- every file a shipped skill or agent names that this repository tracks is one
  the bundle ships, one on the project's side of the split, or one an installed
  component writes
- every record a shipped skill or agent cites that this repository holds is one
  the bundle ships: a core record or a capability's, never a PRJ or an ADR
- no shipped skill or agent names the methodology source's example projects
- the checks flag a name or a record that does not ship, and pass one that does
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

from project_kit import refs, visibility

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


@cache
def _component_footprint() -> tuple[str, ...]:
    """What the installed components write outside `.pkit/`, as their
    `package.yaml` files declare it, each without a trailing slash."""
    return tuple(
        entry.rstrip("/")
        for entry in visibility.footprint(REPO)
        if not entry.startswith(".pkit/") and entry.rstrip("/") != ".pkit"
    )


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


def _a_component_writes(rel: str) -> bool:
    """True when *rel* is, or sits in, a path an installed component writes."""
    return any(rel == path or rel.startswith(f"{path}/") for path in _component_footprint())


def _resolve(shipped: str, name: str) -> str | None:
    """The tracked file *name* names, read from the folder of the file *shipped*."""
    folder = PurePosixPath(shipped).parent
    for base in (folder, *folder.parents):
        candidate = os.path.normpath(os.path.join(str(base), name))
        if candidate.startswith(".."):
            continue
        if candidate in _tracked():
            return candidate
    return None


def unshipped_names(shipped: str, text: str) -> list[str]:
    """Each file *text*, a shipped skill's or agent's file at *shipped*, names that the
    install does not ship, as `<name> -> <file>`, in the order the text names them."""
    found: list[str] = []
    for match in _FILE_NAME.finditer(text):
        name = match.group(1)
        rel = _resolve(shipped, name)
        if rel is None or _ships(rel) or _the_projects_own(rel) or _a_component_writes(rel):
            continue
        entry = f"{name} -> {rel}"
        if entry not in found:
            found.append(entry)
    return found


def unshipped_records(text: str) -> list[str]:
    """Each record *text* cites that this repository holds and the install does not
    ship, as `<id> -> <file>`, sorted by id."""
    found: list[str] = []
    for record_id in sorted(refs.extract_body_refs(text).records):
        path = refs.resolve_record(REPO, record_id, files=_tracked())
        if path is None:
            continue
        rel = path.relative_to(REPO).as_posix()
        if not _ships(rel):
            found.append(f"{record_id} -> {rel}")
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


def _shipped_agents() -> list[str]:
    """Every file of an agent the install ships: core's, and each capability's."""
    capability_agent = re.compile(r"\.pkit/capabilities/[^/]+/agents/.+\.md")
    return sorted(
        rel
        for rel in _tracked()
        if rel.endswith(".md")
        and (rel.startswith(".pkit/agents/core/") or capability_agent.fullmatch(rel))
    )


def _shipped() -> list[str]:
    return _shipped_skills() + _shipped_agents()


# --- the shipped skills and agents --------------------------------------------


def test_there_are_shipped_skills_and_agents_to_check() -> None:
    shipped = _shipped()
    assert ".pkit/skills/core/decision-author.md" in shipped
    assert ".pkit/capabilities/project-management/skills/pm/pm.md" in shipped
    assert ".pkit/agents/core/methodology-reviewer.md" in shipped
    assert ".pkit/capabilities/project-management/agents/pm-reviewer.md" in shipped


@pytest.mark.parametrize("shipped", _shipped())
def test_a_shipped_skill_or_agent_names_only_files_the_install_ships(shipped: str) -> None:
    text = (REPO / shipped).read_text(encoding="utf-8")
    unshipped = unshipped_names(shipped, text)
    assert not unshipped, (
        f"{shipped} names files the install does not ship, so an installed project "
        f"lacks them: {unshipped}. Put what it needs in the skill or the agent, or in "
        "a document the install ships, such as an area's README."
    )


@pytest.mark.parametrize("shipped", _shipped())
def test_a_shipped_skill_or_agent_cites_only_records_the_install_ships(shipped: str) -> None:
    text = (REPO / shipped).read_text(encoding="utf-8")
    unshipped = unshipped_records(text)
    assert not unshipped, (
        f"{shipped} cites records of the methodology source's own project, which an "
        f"installed project lacks, or holds as records of its own: {unshipped}. State "
        "what the record decides, or point to a document the install ships."
    )


@pytest.mark.parametrize("shipped", _shipped())
def test_a_shipped_skill_or_agent_names_no_example_project(shipped: str) -> None:
    text = (REPO / shipped).read_text(encoding="utf-8")
    named = sorted(set(_EXAMPLE_PROJECTS.findall(text)))
    assert not named, f"{shipped} names the methodology source's example projects: {named}"


# --- the checks ---------------------------------------------------------------

_CORE_SKILL = ".pkit/skills/core/an-example.md"
_CAPABILITY_SKILL = ".pkit/capabilities/project-management/skills/pm/an-example.md"
_CORE_AGENT = ".pkit/agents/core/an-example.md"


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


def test_the_check_flags_a_file_an_agent_names_that_the_install_does_not_ship() -> None:
    text = 'reads:\n  paths:\n    - CONTRIBUTING.md\n---\nPer `CONTRIBUTING.md` → "Axiom".'
    assert unshipped_names(_CORE_AGENT, text) == ["CONTRIBUTING.md -> CONTRIBUTING.md"]


@pytest.mark.parametrize(
    "shipped,text",
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
        (_CORE_AGENT, "reads:\n  paths:\n    - CLAUDE.md\n---\nThe project's `CLAUDE.md`."),
        (_CORE_AGENT, "Its deployed copy, `.claude/agents/critic.md`."),
        (_CORE_AGENT, "The core rules, `.pkit/rules/core.md`, rule 10."),
    ],
)
def test_the_check_passes_a_file_the_install_ships(shipped: str, text: str) -> None:
    assert unshipped_names(shipped, text) == []


@pytest.mark.parametrize(
    "text,flagged",
    [
        ("Bumps follow the surface-change rule (per PRJ-002).", ["PRJ-002"]),
        ("reads:\n  records:\n    - PRJ-008\n    - ADR-047\n", ["ADR-047", "PRJ-008"]),
        ("The channel ([pkit:PRJ-008]; realized in ADR-047).", ["ADR-047", "PRJ-008"]),
        ("the binary name is fine after `PRJ-001` fixed it", ["PRJ-001"]),
    ],
)
def test_the_check_flags_a_record_the_install_does_not_ship(text: str, flagged: list[str]) -> None:
    ids = [entry.split(" -> ")[0] for entry in unshipped_records(text)]
    assert ids == flagged


@pytest.mark.parametrize(
    "text",
    [
        "Universal applicability (COR-014), the artifact roles (COR-006).",
        "reads:\n  records:\n    - COR-005\n",
        "The merge gate's verdict ([project-management:DEC-028-agent-as-approver-paths]).",
        "A record of your own, `PRJ-NNN`, or an ADR's id, `ADR-NNN`.",
        "An id no record holds: ADR-999.",
        "```yaml\nshortfalls:\n  - record: ADR-006#2\n```\n",
        "<!-- once PRJ-002 lands -->",
    ],
)
def test_the_check_passes_a_record_the_install_ships(text: str) -> None:
    assert unshipped_records(text) == []
