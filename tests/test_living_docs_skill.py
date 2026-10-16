"""living-docs: the docs-author skill (#1617).

The skill walks an author through `pkit living-docs new` for a page and for a
space. Held here:

- **its shape**: a composite skill (COR-020) whose `composes` is exactly its
  sub-procedures, clean under `pkit refs validate`, deployed beside them and
  granted by the settings merge;
- **it matches the command it pairs with**: every `pkit living-docs new` form
  its walkthroughs give names a form the command has, with flags that form
  takes, so the skill cannot drift from the command unnoticed.

What the command writes passing validation once filled is `test_living_docs_new.py`'s.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import refs

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "living-docs"
SKILL = CAPABILITY / "skills" / "docs-author"
DISPATCHER = SKILL / "docs-author.md"
DEPLOYED = REPO / ".claude" / "skills" / "docs-author"
NEW = CAPABILITY / "scripts" / "new.py"

#: Each sub-procedure, and the form of `pkit living-docs new` it walks.
SUB_PROCEDURES = {"page.md": "page", "space.md": "space"}

_FENCE = re.compile(r"^```\n(?P<block>.*?)^```", re.MULTILINE | re.DOTALL)


def _front(path: Path) -> dict[str, Any]:
    _, front, _body = path.read_text(encoding="utf-8").split("---\n", 2)
    return YAML(typ="safe").load(front) or {}


# --- its shape ---------------------------------------------------------------------------------


def test_the_skill_composes_one_sub_procedure_per_form() -> None:
    front = _front(DISPATCHER)
    assert front["name"] == "docs-author"
    assert sorted(front["composes"]) == sorted(SUB_PROCEDURES)
    assert sorted(p.name for p in SKILL.iterdir()) == sorted([*SUB_PROCEDURES, DISPATCHER.name])
    assert "pkit living-docs new" in front["metadata"]["wraps_commands"]


def test_refs_find_nothing_in_the_skill() -> None:
    folder = str(SKILL.relative_to(REPO))
    assert [i for i in refs.validate_corpus(REPO) if i.location.startswith(folder)] == []
    (skill,) = [a for a in refs.load_artifacts(REPO) if a.name == "docs-author"]
    assert (skill.kind, skill.capability) == ("skill", "living-docs")


def test_the_skill_is_deployed_beside_its_sub_procedures_and_granted() -> None:
    assert (DEPLOYED / "SKILL.md").resolve() == DISPATCHER.resolve()
    for name in SUB_PROCEDURES:
        assert (DEPLOYED / name).resolve() == (SKILL / name).resolve()
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "Skill(docs-author)" in settings["permissions"]["allow"]


# --- it matches the command it pairs with ------------------------------------------------------


def _help(form: str) -> str:
    completed = subprocess.run(
        [sys.executable, str(NEW), form, "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


@pytest.mark.parametrize(("name", "form"), sorted(SUB_PROCEDURES.items()))
def test_every_command_the_walkthrough_gives_is_one_the_stamp_takes(name: str, form: str) -> None:
    blocks = [
        m["block"]
        for m in _FENCE.finditer((SKILL / name).read_text(encoding="utf-8"))
        if m["block"].startswith("pkit living-docs new ")
    ]
    assert blocks, f"{name} gives no `pkit living-docs new` command"
    options = _help(form)
    for block in blocks:
        for command in re.split(r"\n(?=pkit )", block.strip()):
            assert command.split()[3] == form, command
            for flag in set(re.findall(r"(--[a-z][a-z-]*)", command)):
                assert re.search(rf"(?<![\w-]){re.escape(flag)}\b", options), (name, flag)
