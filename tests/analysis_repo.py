"""An adopter with software-analysis installed, and its commands run as the backbone runs them.

Shared by the software-analysis tests (`test_software_analysis*.py`): the
paths the capability's places resolve to with the internal root at
`tech-docs/`, `prepare` for an adopter repository, and the stamp, run as the
dispatcher runs `pkit analysis new`.

The stamp, the links and the overview run in the test's own process
(`run_in_process`): each script's `main`, its `pkit` calls answered by the
backbone's CLI in this process (`tests/in_process.py`). So a template's stamps
start no process of `pkit` or of a script (#2319). `run_script` runs a script as
a subprocess under this interpreter, its `uv run --script` shebang pointed at
it, for a test whose point is the process. The `pkit` such a script reads
through is the real CLI under this interpreter (the `pkit_on_path` fixture), so
nothing reaches `uv` or the network.

`installed` builds the adopter each test module's `project` fixture returns, with
`$PKIT_CHECK_BASE` removed: the backbone names the scripts' base from it when
set, and a developer's own value must not decide what these repositories answer.
The adopter is a copy of a template built once per test session, `prepare`d —
or `prepare_seeded`, the shape a module's `seeded` fixture returns, the seed
stamped and filled (#1204).
"""

from __future__ import annotations

import functools
import json
import re
import shutil
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
from tests import in_process
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, Prepare

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "software-analysis"
SA = Path(".pkit") / "capabilities" / "software-analysis"
NEW = SA / "scripts" / "new.py"
VALIDATE = SA / "scripts" / "validate.py"
#: The command that writes the links between terms and views (DEC-004 point 7).
LINK = SA / "scripts" / "link.py"
#: The command that writes each analysis's overview (DEC-003 point 8).
OVERVIEW_SCRIPT = SA / "scripts" / "overview.py"
#: The command that writes each requirement's fingerprint of its texts (DEC-006 point 6).
OBLIGATION = SA / "scripts" / "obligation.py"
NUMBERS = SA / "scripts" / "check-numbers.py"
CONFIG = ".pkit/project/config.yaml"
RECORDED = f"{SA.as_posix()}/project/docs-locations.yaml"
#: The project's own structures, in the capability's project tier (DEC-001 point 1).
STRUCTURES = f"{SA.as_posix()}/project/structures.yaml"
#: The capability's settings file, and the setting `prepare` writes there: no overview
#: (DEC-003 point 8). The overview's own tests keep one
#: (`test_software_analysis_overview.py`), so a test of any other rule sees no finding,
#: no file and no line of the stamp's that the overview adds. A test that writes the
#: settings file writes the setting too.
SETTINGS = f"{SA.as_posix()}/project/config.yaml"
NO_OVERVIEW = "overview: false\n"
SETTINGS_TEXT = "pkit_schema: software-analysis:config\nschema_version: 1\n" + NO_OVERVIEW

ANALYSIS = "tech-docs/analysis"
ACTORS = f"{ANALYSIS}/use-case-model/actors"
GLOSSARY = f"{ANALYSIS}/glossary.md"
#: The domain model's folder, one file per view (software-analysis DEC-004 point 4).
DOMAIN_MODEL = f"{ANALYSIS}/domain-model"
USE_CASES = f"{ANALYSIS}/use-case-model/use-cases"
JOURNEYS = f"{ANALYSIS}/use-case-model/journeys"
RECORDS = f"{ANALYSIS}/revalidations"
#: The overview's folder of held documents, and its file (software-analysis DEC-003 point 8).
OVERVIEW = f"{ANALYSIS}/overview"
OVERVIEW_FILE = f"{OVERVIEW}/README.md"
#: The three kinds of requirement's places, one folder each under `requirements/`, which
#: is no place itself (software-analysis DEC-002 point 3).
QUALITY = f"{ANALYSIS}/requirements/quality"
FUNCTIONAL = f"{ANALYSIS}/requirements/functional"
CONSTRAINTS = f"{ANALYSIS}/requirements/constraints"

#: The branch that stands for the default branch in these repositories.
MAIN = "main"

#: The method rule set, as the adopter holds it, and a set of the project's own through
#: which it binds on the whole analysis: `SAN` takes no scope, so its rules bind only
#: through such a set (DEC-001 point 1; COR-051 point 7).
SAN_REL = f"{SA.as_posix()}/rule-sets/san.md"
ANALYSIS_SET = "tech-docs/rule-sets/analysis.md"
ANALYSIS_SET_TEXT = (
    "---\nrule-set: ANALYSIS\nversion: 1.0.0\ninherits: [software-analysis:SAN@2]\n"
    "scope:\n  types: [software-analysis:actor, software-analysis:term, "
    "software-analysis:use-case, software-analysis:journey, "
    "software-analysis:quality-requirement, software-analysis:functional-requirement, "
    "software-analysis:constraint, software-analysis:domain-model-view]\nrules: {}\n---\n\n"
    "# ANALYSIS — the project's rules for its analysis\n"
)


def accepting_san(repo: AdopterRepo) -> dict[str, str]:
    """What to write so `SAN`'s rules bind on the whole analysis, the format rule and the
    append-only rule: the adopter's copy of `SAN` with each rule accepted, as it ships
    them since the maintainer accepted both (#1370), and a set of the project's own that
    inherits it."""
    text = (repo.root / SAN_REL).read_text(encoding="utf-8")
    return {
        SAN_REL: text.replace("status: proposed", "status: accepted"),
        ANALYSIS_SET: ANALYSIS_SET_TEXT,
    }


def proposing_san(repo: AdopterRepo) -> dict[str, str]:
    """What to write so each rule of `SAN` is proposed: the adopter's copy of `SAN` with
    each rule set back to proposed, a fixture for a test of what a proposed rule does,
    since `SAN` ships its rules accepted (#1370)."""
    text = (repo.root / SAN_REL).read_text(encoding="utf-8")
    return {SAN_REL: text.replace("status: accepted", "status: proposed")}


def with_status(text: str, rule: str, status: str) -> str:
    """A rule set's `text` with `rule`'s status set to `status`, the other rules as they
    were: a fixture, not the acceptance procedure."""
    changed, count = re.subn(
        rf"(^  {re.escape(rule)}:\n    status: )[a-z]+$", rf"\g<1>{status}", text, flags=re.M
    )
    assert count == 1, f"no status of {rule} to set"
    return changed


_yaml: Any = YAML(typ="safe")


def load_lib(*names: str) -> tuple[ModuleType, ...]:
    """`_lib` modules of the capability's scripts, imported together as the scripts import
    them, through the one loader (`tests/in_process.py`, `load`): `_lib` is on the path
    only while they load, since another capability's `_lib` is not importable beside it."""
    return in_process.load(CAPABILITY / "scripts", *names)


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
    `tech-docs/`, `src/` holding code to anchor, the settings keeping no overview
    (`SETTINGS_TEXT`), and all of it committed on `main`."""
    for script in sorted((repo.root / SA / "scripts").glob("*.py")):
        body = script.read_text(encoding="utf-8").split("\n", 1)[1]
        script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    repo.write(
        {
            CONFIG: "docs:\n  internal: tech-docs\n",
            "src/run.py": "print('run')\n",
            SETTINGS: SETTINGS_TEXT,
        }
    )
    repo.commit("install")
    return repo


# Four stamps, built once per session; the first test to ask pays them in its setup.
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
    """`script`, the adopter's copy, run as the dispatcher runs it: a process."""
    return subprocess.run(
        [sys.executable, str(repo.root / script), *args],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )


#: The `pkit` the `pkit_on_path` fixture puts first on PATH (`tests/conftest.py`): the
#: real CLI under this interpreter.
_REAL_PKIT = f'#!/bin/sh\nexec "{sys.executable}" -P -m project_kit "$@"\n'


def _real_pkit_first() -> bool:
    """Whether the `pkit` first on PATH is the real CLI under this interpreter, as
    `pkit_on_path` writes it. A `pkit` a test put before it, such as one that stands for
    an older backbone, is not."""
    found = shutil.which("pkit")
    try:
        return found is not None and Path(found).read_text(encoding="utf-8") == _REAL_PKIT
    except (OSError, UnicodeDecodeError):
        return False


def run_in_process(
    repo: AdopterRepo, script: Path, *args: str, pkit: in_process.Runner | None = None
) -> subprocess.CompletedProcess[str]:
    """`script` run as `run_script` runs it, but in the test's own process: the adopter's
    copy's `main` with `args`, from the repository's root, in the test's environment,
    standard output and standard error apart (`tests/in_process.py`, `run_main`). Its
    `pkit` calls go through the capability's one private function, `backbone._run`,
    unchanged. `pkit` answers them where given. Else the backbone's CLI answers them in
    this process where the real CLI is first on PATH, and otherwise the `pkit` first on
    PATH does, as a process."""
    scripts = (repo.root / script).parent
    loaded, backbone = in_process.load(scripts, script.name, "backbone")
    with pytest.MonkeyPatch.context() as patched:
        if pkit is not None or _real_pkit_first():
            in_process.route_pkit(patched, backbone, pkit)
        return in_process.run_main(loaded, *args, cwd=repo.root)


def new(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis new …`, run as the dispatcher runs it, against `main`, in the test's
    own process (`run_in_process`)."""
    return run_in_process(repo, NEW, *args, "--base", MAIN)


def stamped(repo: AdopterRepo, *args: str) -> str:
    """The id a successful stamp printed."""
    completed = new(repo, *args)
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip().splitlines()[-1].split()[1]


def link(repo: AdopterRepo) -> subprocess.CompletedProcess[str]:
    """`pkit analysis link`, run as the dispatcher runs it, in the test's own process: the
    links between the terms and the views written (DEC-004 point 7)."""
    completed = run_in_process(repo, LINK)
    assert completed.returncode == 0, completed.stderr
    return completed


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


#: Each kind of requirement's place, its name beside its id, and its last part:
#: *Rationale*, or *Imposed by* on a constraint (software-analysis DEC-002 points 2 to 4).
REQUIREMENT_PLACES = {
    "quality-requirement": (QUALITY, "Quality", "Rationale"),
    "functional-requirement": (FUNCTIONAL, "Functional", "Rationale"),
    "constraint": (CONSTRAINTS, "Constraint", "Imposed by"),
}


def requirement(
    kind: str = "quality-requirement",
    *,
    req_id: str = "REQ-004",
    title: str = "Show a run's result quickly",
    anchored: list[str] | None = None,
    heading: str | None = None,
    **fields: Any,
) -> str:
    """A requirement of `kind`, filled as its structure asks, written by hand: its front
    matter's `fields` added or changed, a field set to `None` left out, its `obligation`
    the fingerprint of its texts as `pkit analysis obligation` writes it unless given,
    each of `anchored` an artefact anchor beside its path anchor, and its `heading`, the
    line its body opens with — its id, its kind and its title unless given, none when
    empty."""
    _place, shown, last = REQUIREMENT_PLACES[kind]
    front: dict[str, Any] = {
        "id": req_id,
        "title": title,
        "status": "active",
        "statement": "The system shows a suite's result within two seconds of the run's end.",
        "measure": "None.",
        "applies-to": "Every run of a suite.",
        **fields,
    }
    if "obligation" not in fields:
        front["obligation"] = fingerprint({k: v for k, v in front.items() if v is not None}, kind)
    anchors: dict[str, list[str]] = {"path": ["src/run.py"]}
    if anchored:
        anchors["artefact"] = anchored
    written = "".join(f"{k}: {json.dumps(v)}\n" for k, v in front.items() if v is not None)
    head = f"# {req_id} · {shown} · {title}" if heading is None else heading
    return (
        f"---\n{written}pkit:\n  friction:\n    anchors: {json.dumps(anchors)}\n---\n\n"
        + (f"{head}\n\n" if head else "")
        + "**Verified by:** A timing test runs the suite and measures when its result shows.\n\n"
        + f"**{last}:** None.\n"
    )


def fingerprint(fields: dict[str, Any], kind: str = "quality-requirement") -> str:
    """A requirement's `obligation` for its front matter's `fields`, as `pkit analysis
    obligation` writes it where the texts lie in front matter, a text the fields leave out
    read as absent (software-analysis DEC-006 points 6 and 7)."""
    structure, obligation = _fingerprinting()
    declared: Any = structure.read_kinds()[kind]
    read = obligation.texts(fields, list, declared)
    return obligation.value(read, obligation.LINK_FORMS)


@functools.cache
def _fingerprinting() -> tuple[Any, Any]:
    """The capability's structure and fingerprint modules, loaded once for the session."""
    structure, obligation = load_lib("structure", "obligation")
    return structure, obligation


#: A shipped example's citation of the example project's own record, such as `(PRJ-003)`.
_EXAMPLE_CITATION = re.compile(r" \(PRJ-[0-9]+\)")


def fill(repo: AdopterRepo) -> None:
    """Every placeholder the stamp left in the analysis written over with its own words,
    as a person fills each — the check fails an artefact still holding one. Each part's
    hint is written over with its example. An example cites a record of the example's
    project, which no adopter here holds, so its citation is left out: the check would
    warn of one that resolves to nothing (software-analysis DEC-001 point 13). Then the
    links are written, as the authoring skill runs `pkit analysis link` after any artefact
    is written: a journey's step lines name their use cases by id, which link to them
    (DEC-001 point 14). Each requirement's `obligation` is then written anew, as a person
    runs `pkit analysis obligation` once its texts are written (DEC-006 point 6). The
    overview is generated, and holds nothing a person fills
    (DEC-003 point 8). An actor's `summary` is drawn there, so where an overview is kept,
    it is written anew after, as a person runs its command."""
    overviews = [
        p for p in (repo.root / ANALYSIS).rglob("README.md") if p.parent.name == "overview"
    ]
    for path in sorted((repo.root / ANALYSIS).rglob("*.md")):
        if (repo.root / RECORDS) in path.parents or path in overviews:
            continue
        text = HINT.sub(
            lambda m: _EXAMPLE_CITATION.sub("", m["example"]), path.read_text(encoding="utf-8")
        )
        path.write_text(_PLACEHOLDER.sub(r"\1", text), encoding="utf-8")
    linked = run_in_process(repo, LINK)
    assert linked.returncode == 0, linked.stderr
    if any((repo.root / ANALYSIS).rglob("requirements/*/**/*.md")):
        fingerprinted = run_in_process(repo, OBLIGATION)
        assert fingerprinted.returncode == 0, fingerprinted.stderr
    if overviews:
        written = run_in_process(repo, OVERVIEW_SCRIPT)
        assert written.returncode == 0, written.stderr


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
