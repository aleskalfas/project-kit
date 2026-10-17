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

import importlib
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML
from scripts import prose_lint as pl

from project_kit import document_parts
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
#: The project's own structures, in the capability's project tier (DEC-001 point 1).
STRUCTURES = f"{SA.as_posix()}/project/structures.yaml"

ANALYSIS = "tech-docs/analysis"
ACTORS = f"{ANALYSIS}/use-case-model/actors"
GLOSSARY = f"{ANALYSIS}/glossary.md"
USE_CASES = f"{ANALYSIS}/use-case-model/use-cases"
JOURNEYS = f"{ANALYSIS}/use-case-model/journeys"
RECORDS = f"{ANALYSIS}/revalidations"

#: The branch that stands for the default branch in these repositories.
MAIN = "main"

#: The method rule set, as the adopter holds it, and a set of the project's own through
#: which it binds on the whole analysis: `SAN` takes no scope, so its rules bind only
#: through such a set (DEC-001 point 1; COR-051 point 7).
SAN_REL = f"{SA.as_posix()}/rule-sets/san.md"
ANALYSIS_SET = "tech-docs/rule-sets/analysis.md"
ANALYSIS_SET_TEXT = (
    "---\nrule-set: ANALYSIS\nversion: 1.0.0\ninherits: [software-analysis:SAN@0]\n"
    "scope:\n  types: [software-analysis:actor, software-analysis:term, "
    "software-analysis:use-case, software-analysis:journey]\nrules: {}\n---\n\n"
    "# ANALYSIS — the project's rules for its analysis\n"
)


def accepting_san(repo: AdopterRepo) -> dict[str, str]:
    """What to write so the format rule binds on the whole analysis: the adopter's copy of
    `SAN` with its rule flipped to accepted, as a fixture and not the acceptance procedure,
    and a set of the project's own that inherits it."""
    text = (repo.root / SAN_REL).read_text(encoding="utf-8")
    return {
        SAN_REL: text.replace("status: proposed", "status: accepted", 1),
        ANALYSIS_SET: ANALYSIS_SET_TEXT,
    }


_yaml: Any = YAML(typ="safe")


def load_lib(*names: str) -> tuple[ModuleType, ...]:
    """Pure `_lib` modules of the capability's scripts, imported together as the scripts
    import them: `_lib` is on the path only while they load, since another capability's
    `_lib` is not importable beside it."""
    scripts = str(CAPABILITY / "scripts")

    def ours() -> list[str]:
        return [k for k in sys.modules if k == "_lib" or k.startswith("_lib.")]

    saved = {k: sys.modules.pop(k) for k in ours()}
    sys.path.insert(0, scripts)
    try:
        return tuple(importlib.import_module(f"_lib.{name}") for name in names)
    finally:
        sys.path.remove(scripts)
        for key in ours():
            del sys.modules[key]
        sys.modules.update(saved)


def field_hint(kind: str, name: str) -> str:
    """A front-matter field's declared hint as the stamp writes it, its placeholder (#1593)."""
    structure, render = load_lib("structure", "render")
    declared: Any = structure.read_kinds()[kind]
    render_: Any = render
    return render_.field_hint(next(f for f in declared.fields if f.name == name))


def actor_at(actor_id: str) -> str:
    """An actor's file: `ACT-<slug>.md`, named by its id, in the actors' folder."""
    return f"{ACTORS}/{actor_id}.md"


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


# Slow: four stamps, built once per session; the first test to ask pays it in its setup.
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
    front_matter, _body = document_parts.split_front_matter(text)
    assert front_matter is not None
    return load(front_matter)


#: A text in angle brackets, as a template writes a placeholder.
_PLACEHOLDER = re.compile(r"<([^<>\n]+)>")

#: A part's hint as the stamp writes it, its example after it (#1366).
HINT = re.compile(r"<!-- pkit:hint .*? Example: (?P<example>.*?) -->")

#: The writing rules whose mechanical parts the text the capability ships keeps to
#: (#1351): no sentence over 25 words, and no semicolon. They are a floor any project's
#: rules accept, and carry none of one project's style.
FLOOR = ("RS-WRITE-005", "RS-WRITE-008")


def below_floor(text: str) -> list[str]:
    """`<line> <rule>: <message>` for each break of the floor in a given text, its
    front matter's values and its body, read as the prose lint reads them
    (`scripts/prose_lint.py`). Each placeholder's brackets are taken off first, as
    `fill` does: the lint reads a line that is only `<…>` as an HTML tag, and skips it."""
    entries = [entry for entry in pl.load_entries() if entry.rule in FLOOR]
    assert sorted(entry.rule for entry in entries) == sorted(FLOOR)
    found = pl.lint_text(_PLACEHOLDER.sub(r"\1", text), entries)
    return [f"{f.line} {f.rule}: {f.message}" for f in found]


def fill(repo: AdopterRepo) -> None:
    """Every placeholder the stamp left in the analysis written over with its own words,
    as a person fills each — the check fails an artefact still holding one. Each part's
    hint is written over with its example."""
    for path in sorted((repo.root / ANALYSIS).rglob("*.md")):
        if (repo.root / RECORDS) in path.parents:
            continue
        text = HINT.sub(r"\g<example>", path.read_text(encoding="utf-8"))
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
