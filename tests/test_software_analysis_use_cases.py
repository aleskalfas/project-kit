"""software-analysis fills the work-tracking role's use-case point (#889; DEC-001 point 8).

`pkit::work-tracking:use-cases` is the point the provider of the work-tracking
role defines: the use cases settled on the default branch. software-analysis
contributes its use cases to it through a command filler, `fill-use-cases`,
which declares `reads: [settled]`.

- the filler on its own, its `pkit` and `git` stood in for: it reads the
  default branch's commit — never the base — and what that commit holds, asks
  git nothing, keeps ids as written and withdrawn use cases in, answers empty
  on a default branch with no commit yet, and gives no answer — non-zero, with
  nothing on standard output — when a reading fails or a use case cannot be
  read in full;
- the contribution through the real backbone, beside a provider of the
  work-tracking role: what the default branch holds, never the working tree;
  empty before the first commit; no answer where a settled use case cannot be
  read.

The capability's scripts are pointed at this interpreter in the adopter copy,
and the `pkit` they read through is the real CLI under this interpreter
(`pkit_on_path`), so no test reaches `uv` or the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.friction_check import BASE_ENV
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    CAPABILITY,
    SA,
    USE_CASES,
    installed,
    prepare_seeded,
    stamped,
)

FILL = SA / "scripts" / "fill-use-cases.py"
POINT = "pkit::work-tracking:use-cases"
PROVIDER = "project-management"

SHA = "78981922613b2afb6025042ff6bd878ac1994e85"
OTHER = "d670460b4b4aece5915caf5c68d12f560a9fe3e4"
PLACE = "docs/analysis/use-case-model/use-cases"


# --- the filler on its own ------------------------------------------------------------------


def _base(commit: str | None = SHA, **branch: Any) -> dict[str, Any]:
    """A `pkit repository base --json` document: the default branch at `commit`, and
    a base named for the run at another commit, which a filler never reads."""
    return {
        "schema_version": 1,
        "default_branch": {
            "name": "main",
            "source": "default",
            "ref": "origin/main" if commit else None,
            "commit": commit,
            "resolved": "remote" if commit else None,
            "problem": None,
            "unborn": False,
            **branch,
        },
        "base": {
            "ref": "release",
            "source": "environment",
            "tip": OTHER,
            "fork": OTHER,
            "outdated": False,
            "resolved": "local",
            "problem": None,
        },
        "head": {"commit": OTHER, "unborn": False, "problem": None},
    }


def _use_case(number: str, **fields: Any) -> dict[str, Any]:
    """One use case as `pkit friction artefacts --json` lists it."""
    path = f"{PLACE}/{number}-a-goal.md"
    own = {"id": number, "title": f"Goal {number}", "status": "active", "actor": "ACT-tester"}
    return {
        "path": path,
        "kind": "document",
        "location": path,
        "fields": {**own, **fields},
        "anchors": {"artefact": ["ACT-tester"]},
    }


def _artefacts(*use_cases: Mapping[str, Any], files: Any = None) -> dict[str, Any]:
    """A `pkit friction artefacts --json` document holding `use_cases` in the
    capability's place for them; `files` lists that place's files when they are not
    one readable file per use case."""
    place = {
        "source": "capability:software-analysis",
        "declared": True,
        "location": {"name": "analysis", "path": "docs/analysis"},
        "written": "use-case-model/use-cases",
        "path": PLACE,
    }
    listed = [{"path": u["path"], "places": [0], "fields": u["fields"]} for u in use_cases]
    return {
        "schema_version": 1,
        "places": [place],
        "files": listed if files is None else files,
        "artefacts": list(use_cases),
        "held": [],
        "held_files": [],
    }


def _answer(document: Any, code: int = 0) -> dict[str, Any]:
    stdout = document if isinstance(document, str) else json.dumps(document)
    return {"stdout": stdout, "exit": code}


#: A `pkit` that answers from `answers.json` beside it, by its first argument, and a
#: `git` that answers nothing; each writes the command it was run with to `calls.log`.
_PKIT = """#!{python}
import json
import sys
from pathlib import Path

here = Path(__file__).parent
with (here / "calls.log").open("a", encoding="utf-8") as log:
    log.write(json.dumps(["pkit", *sys.argv[1:]]) + "\\n")
answer = json.loads((here / "answers.json").read_text(encoding="utf-8"))[sys.argv[1]]
sys.stdout.write(answer["stdout"])
sys.exit(answer["exit"])
"""
_GIT = """#!/bin/sh
echo '["git"]' >> "$(dirname "$0")/calls.log"
exit 1
"""


def _fill(
    tmp_path: Path, repository: Mapping[str, Any], friction: Mapping[str, Any] | None = None
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    """The shipped filler run as the backbone runs it — `--json` alone, from the
    project root — with `repository` and `friction` what `pkit repository …` and
    `pkit friction …` answer: its ending, and every command it ran."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("pkit", _PKIT.format(python=sys.executable)), ("git", _GIT)):
        (bin_dir / name).write_text(text, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    answers = {"repository": repository, "friction": friction or _answer("", 1)}
    (bin_dir / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(CAPABILITY / "scripts" / "fill-use-cases.py"), "--json"],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(bin_dir)},
        capture_output=True,
        text=True,
        check=False,
    )
    log = bin_dir / "calls.log"
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    return completed, calls


def test_the_filler_reads_the_default_branch_s_commit_and_asks_git_nothing(
    tmp_path: Path,
) -> None:
    held = _artefacts(
        _use_case("UC-1000", status="draft"),
        _use_case("UC-002", status="withdrawn"),
        _use_case("UC-001", title="  Run a suite "),
    )
    completed, calls = _fill(tmp_path, _answer(_base()), _answer(held))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "schema_version": 1,
        "value": [
            {
                "id": "UC-001",
                "title": "Run a suite",
                "status": "active",
                "path": f"{PLACE}/UC-001-a-goal.md",
            },
            {  # withdrawn, and kept: its id is never used again
                "id": "UC-002",
                "title": "Goal UC-002",
                "status": "withdrawn",
                "path": f"{PLACE}/UC-002-a-goal.md",
            },
            {  # any lifecycle value but `withdrawn` is `active`
                "id": "UC-1000",
                "title": "Goal UC-1000",
                "status": "active",
                "path": f"{PLACE}/UC-1000-a-goal.md",
            },
        ],
    }
    # The default branch's commit, never the base named for the run; and no git call.
    assert calls == [
        ["pkit", "repository", "base", "--json"],
        ["pkit", "friction", "artefacts", "--at", SHA, "--json"],
    ]


def test_a_default_branch_with_no_commit_yet_holds_no_use_case(tmp_path: Path) -> None:
    completed, calls = _fill(tmp_path, _answer(_base(None, unborn=True)))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"schema_version": 1, "value": []}
    assert calls == [["pkit", "repository", "base", "--json"]]


def test_a_commit_holding_no_use_case_is_the_empty_answer(tmp_path: Path) -> None:
    completed, _calls = _fill(tmp_path, _answer(_base()), _answer(_artefacts()))
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"schema_version": 1, "value": []}


_READABLE = _use_case("UC-001")
_BROKEN = f"{PLACE}/UC-002-broken.md"


@pytest.mark.parametrize(
    ("repository", "friction"),
    [
        pytest.param(_answer("", 1), None, id="no-reading-of-the-default-branch"),
        pytest.param(_answer({**_base(), "schema_version": 2}), None, id="unknown-version"),
        pytest.param(
            _answer(_base(None, problem="origin/main is not fetched")), None, id="unreadable-branch"
        ),
        pytest.param(_answer(_base()), _answer("", 1), id="no-reading-of-the-commit"),
        pytest.param(
            _answer(_base()),
            _answer({**_artefacts(_READABLE), "schema_version": 2}),
            id="unknown-artefacts-version",
        ),
        pytest.param(
            _answer(_base()),
            _answer(
                _artefacts(
                    _READABLE,
                    files=[
                        {"path": _READABLE["path"], "places": [0], "fields": _READABLE["fields"]},
                        {"path": _BROKEN, "places": [0], "unreadable": "a mapping was expected"},
                    ],
                )
            ),
            id="front-matter-does-not-parse",
        ),
        pytest.param(
            _answer(_base()),
            _answer(
                _artefacts(
                    _READABLE,
                    files=[
                        {"path": _READABLE["path"], "places": [0], "fields": _READABLE["fields"]},
                        {"path": _BROKEN, "places": [0], "fields": None},
                    ],
                )
            ),
            id="no-front-matter",
        ),
        pytest.param(
            _answer(_base()), _answer(_artefacts(_READABLE, _use_case("UC-7"))), id="no-such-id"
        ),
        pytest.param(
            _answer(_base()),
            _answer(_artefacts(_READABLE, _use_case("UC-002", id=None))),
            id="no-id",
        ),
        pytest.param(
            _answer(_base()),
            _answer(_artefacts(_READABLE, _use_case("UC-002", title=" "))),
            id="no-title",
        ),
        pytest.param(
            _answer(_base()),
            _answer(_artefacts(_READABLE, {**_use_case("UC-001"), "path": _BROKEN})),
            id="two-hold-one-id",
        ),
    ],
)
def test_complete_or_no_answer(
    tmp_path: Path, repository: Mapping[str, Any], friction: Mapping[str, Any] | None
) -> None:
    """A failed reading, or one use case that cannot be read in full: non-zero, and
    nothing on standard output — never a shorter list."""
    completed, calls = _fill(tmp_path, repository, friction)
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "no use cases can be given" in completed.stderr
    assert ["git"] not in calls


# --- the contribution through the real backbone ------------------------------------------------


def _resolve() -> dict[str, Any]:
    """`pkit connections resolve <the point> --json`, in the adopter."""
    result = CliRunner().invoke(main, ["connections", "resolve", POINT, "--json"])
    return json.loads(result.output)


@pytest.fixture
def tracked(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The seeded project — an actor, two use cases and a journey, stamped in the
    working tree — beside a provider of the work-tracking role."""
    repo = installed(make_adopter_repo, monkeypatch, then=prepare_seeded)
    repo.install_capabilities(PROVIDER)
    return repo


def _held(resolved: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(entry["id"], entry["status"]) for entry in resolved["value"]]


def test_the_point_holds_what_the_default_branch_holds(tracked: AdopterRepo) -> None:
    head = tracked.commit("the analysis")
    resolved = _resolve()
    assert resolved["outcome"] == "resolved" and resolved["origin"] == "software-analysis"
    assert resolved["value"] == [
        {
            "id": "UC-001",
            "title": "Run suite",
            "status": "active",
            "path": f"{USE_CASES}/UC-001-run-suite.md",
        },
        {
            "id": "UC-002",
            "title": "Read report",
            "status": "active",
            "path": f"{USE_CASES}/UC-002-read-report.md",
        },
    ]
    (filler,) = resolved["fillers"]
    assert filler["supplies"] == "command 'fill-use-cases'"
    assert filler["reads"] == [{"state": "settled", "ref": "main", "commit": head}]

    # A use case stamped on a branch has not settled; a withdrawn one stays.
    tracked.checkout("work", create=True)
    stamped(tracked, "use-case", "export", "--actor", "ACT-tester")
    path = tracked.root / USE_CASES / "UC-002-read-report.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("status: active", "status: withdrawn"),
        encoding="utf-8",
    )
    tracked.commit("a third use case, and one withdrawn")
    assert _held(_resolve()) == [("UC-001", "active"), ("UC-002", "active")]
    tracked.checkout("main")
    tracked.merge("work")
    assert _held(_resolve()) == [
        ("UC-001", "active"),
        ("UC-002", "withdrawn"),
        ("UC-003", "active"),
    ]


def test_a_settled_use_case_that_cannot_be_read_is_no_answer(tracked: AdopterRepo) -> None:
    broken = f"{USE_CASES}/UC-002-read-report.md"
    tracked.write({broken: "---\nid: [unclosed\n---\n\n# UC-002\n"})
    tracked.commit("the analysis, one use case broken")
    resolved = _resolve()
    assert resolved["outcome"] == "no-answer" and resolved["value"] is None
    (filler,) = resolved["fillers"]
    assert filler["state"] == "inert"
    # `fallback`: the point is unread, and `pkit validate` warns and does not fail.
    result = CliRunner().invoke(main, ["--color", "never", "validate", "--only", "connections"])
    assert result.exit_code == 0, result.output
    assert f"to {POINT!r} is inert: command 'fill-use-cases' exited 1" in result.output
    assert f"{broken}'s front matter does not parse; no use cases can be given" in result.output
    assert "0 error(s), 1 warning(s)" in result.output


def test_empty_before_the_first_commit(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A default branch nothing has been committed to holds no use case: the filler is
    started, and answers the empty list."""
    monkeypatch.delenv(BASE_ENV, raising=False)
    repo = make_adopter_repo(capabilities=("software-analysis", PROVIDER))
    script = repo.root / FILL
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    resolved = _resolve()
    assert resolved["outcome"] == "resolved" and resolved["value"] == []
    (filler,) = resolved["fillers"]
    assert filler["reads"] == [{"state": "settled", "ref": "main", "commit": None}]
