"""An adopter with software-analysis installed, and its commands run as the backbone runs them.

Shared by the software-analysis tests (`test_software_analysis*.py`): the
paths the capability's places resolve to with the internal root at
`tech-docs/`, `prepare` for an adopter repository, and the stamp, run as the
dispatcher runs `pkit analysis new`. The scripts run as subprocesses under
this interpreter — their `uv run --script` shebang pointed at it — and the
`pkit` they read through is the real CLI under this interpreter (the
`pkit_on_path` fixture), so nothing reaches `uv` or the network.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from project_kit import friction_discovery as fd
from tests.adopter_repo import AdopterRepo

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "software-analysis"
SA = Path(".pkit") / "capabilities" / "software-analysis"
NEW = SA / "scripts" / "new.py"
VALIDATE = SA / "scripts" / "validate.py"
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


def seed(repo: AdopterRepo) -> None:
    """An actor, two use cases and a journey through them, stamped."""
    stamped(repo, "actor", "tester", "--path", "src/**")
    stamped(repo, "use-case", "run-suite", "--actor", "ACT-tester", "--path", "src/run.py")
    stamped(repo, "use-case", "read-report", "--actor", "ACT-tester")
    steps = ("--step", "UC-001", "--step", "UC-002")
    stamped(repo, "journey", "first-run", "--actor", "ACT-tester", *steps)
