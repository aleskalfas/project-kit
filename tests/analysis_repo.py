"""An adopter with software-analysis installed, and its commands run as the backbone runs them.

Shared by the software-analysis tests (`test_software_analysis*.py`): the
paths the capability's places resolve to with the internal root at
`tech-docs/`, `prepare` for an adopter repository, and the stamp, run as the
dispatcher runs `pkit analysis new`. The scripts run as subprocesses under
this interpreter — their `uv run --script` shebang pointed at it — and the
`pkit` they read through is the real CLI under this interpreter (the
`pkit_on_path` fixture), so nothing reaches `uv` or the network.

`installed` builds the adopter each test module's `project` fixture returns, with
`$PKIT_CHECK_BASE` removed: the backbone names the scripts' base from it when
set, and a developer's own value must not decide what these repositories answer.
The adopter is a copy of a template built once per test session, `prepare`d —
or `prepare_seeded`, the shape a module's `seeded` fixture returns: stamping
the seed starts some two dozen `pkit` processes, more than most tests of these
modules cost in all (#1204).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import friction_discovery as fd
from project_kit.friction_check import BASE_ENV
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, Prepare

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "software-analysis"
SA = Path(".pkit") / "capabilities" / "software-analysis"
NEW = SA / "scripts" / "new.py"
VALIDATE = SA / "scripts" / "validate.py"
NUMBERS = SA / "scripts" / "check-numbers.py"
CONFIG = ".pkit/project/config.yaml"
RECORDED = f"{SA.as_posix()}/project/docs-locations.yaml"

ANALYSIS = "tech-docs/analysis"
ACTORS = f"{ANALYSIS}/use-case-model/actors.md"
GLOSSARY = f"{ANALYSIS}/glossary.md"
USE_CASES = f"{ANALYSIS}/use-case-model/use-cases"
JOURNEYS = f"{ANALYSIS}/use-case-model/journeys"
RECORDS = f"{ANALYSIS}/revalidations"

#: The branch that stands for the default branch in these repositories.
MAIN = "main"

_yaml: Any = YAML(typ="safe")


def load(text: str) -> Any:
    return _yaml.load(text)


def prepare(repo: AdopterRepo) -> AdopterRepo:
    """The adopter's scripts pointed at this interpreter, the internal root at
    `tech-docs/`, `src/` holding code to anchor, and all of it committed on `main`."""
    for script in sorted((repo.root / SA / "scripts").glob("*.py")):
        body = script.read_text(encoding="utf-8").split("\n", 1)[1]
        script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    repo.write({CONFIG: "docs:\n  internal: tech-docs\n", "src/run.py": "print('run')\n"})
    repo.commit("install")
    return repo


def prepare_seeded(repo: AdopterRepo) -> None:
    """`prepare`, then `seed`: an actor, two use cases and a journey, filled."""
    prepare(repo)
    seed(repo)


def installed(
    make_adopter_repo: MakeAdopterRepo,
    monkeypatch: pytest.MonkeyPatch,
    *,
    then: Prepare = prepare,
) -> AdopterRepo:
    """An adopter with software-analysis installed and `then` laid on it — `prepare`,
    unless a module-level function that calls it is named — `$PKIT_CHECK_BASE` unset.
    A copy of the template `then` was built into once; the test needs `pkit_on_path`
    when `then` stamps."""
    monkeypatch.delenv(BASE_ENV, raising=False)
    return make_adopter_repo(capabilities=("software-analysis",), prepare=then)


def run_script(repo: AdopterRepo, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo.root / script), *args],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )


def new(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis new …`, run as the dispatcher runs it, against `main`."""
    return run_script(repo, NEW, *args, "--base", MAIN)


def stamped(repo: AdopterRepo, *args: str) -> str:
    """The id a successful stamp printed."""
    completed = new(repo, *args)
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip().splitlines()[-1].split()[1]


def front(repo: AdopterRepo, rel: str) -> dict[str, Any]:
    """A stamped file's front matter."""
    text = (repo.root / rel).read_text(encoding="utf-8")
    front_matter, _body = fd.split_front_matter(text)
    assert front_matter is not None
    return load(front_matter)


#: A text in angle brackets, as a template writes a placeholder.
_PLACEHOLDER = re.compile(r"<([^<>\n]+)>")


def fill(repo: AdopterRepo) -> None:
    """Every placeholder the stamp left in the analysis written over with its own words,
    as a person fills each — the check fails an artefact still holding one."""
    for path in sorted((repo.root / ANALYSIS).rglob("*.md")):
        if (repo.root / RECORDS) in path.parents:
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(_PLACEHOLDER.sub(r"\1", text), encoding="utf-8")


def seed(repo: AdopterRepo, *, filled: bool = True) -> None:
    """An actor, two use cases and a journey through them, stamped — and, unless
    `filled` is false, their placeholders filled."""
    stamped(repo, "actor", "tester", "--path", "src/**")
    stamped(repo, "use-case", "run-suite", "--actor", "ACT-tester", "--path", "src/run.py")
    stamped(repo, "use-case", "read-report", "--actor", "ACT-tester")
    steps = ("--step", "UC-001", "--step", "UC-002")
    stamped(repo, "journey", "first-run", "--actor", "ACT-tester", *steps)
    if filled:
        fill(repo)
