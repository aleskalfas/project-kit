"""project-kit's friction gate, met the way a pull request meets it (#1008).

ADR-055 point 5 runs the friction change check in enforcing mode from
`scripts/check.sh`, a required status on `main`. These tests drive the
installed `pkit` — the console script installed with the package under test —
as a process in a fixture repository, so what they assert is the exit status a
check job reads:

- a page anchored to a file the pull request changes, left without an answer,
  fails the check in enforcing mode; revalidated through `pkit friction
  revalidate … --outcome unchanged --because …` and committed, it answers the
  change and the check passes;
- the escape hatch (CONTRIBUTING.md, "The escape hatch") is the one line
  `mode: enforcing` → `mode: warning`, made in the pull request itself: the
  check reads the mode the pull request carries, so the same stale page is
  then reported and the check passes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sysconfig
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, guide

PAGE = "docs/guide.md"
# Block style, as project-kit writes its own configuration: the mode is one line.
ENFORCING = "name: adopter\nfriction:\n  mode: enforcing\n  places:\n    - docs\n"


def _pkit(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the `pkit` installed with the package under test, in `repo`."""
    scripts = sysconfig.get_path("scripts")
    pkit = shutil.which("pkit", path=scripts)
    if pkit is None:
        pytest.fail(f"no `pkit` is installed in {scripts}")
    return subprocess.run([pkit, *args], cwd=repo.root, capture_output=True, text=True, check=False)


def _check(repo: AdopterRepo) -> tuple[int, dict[str, Any]]:
    """The change check against `main`: its exit status and its JSON document."""
    done = _pkit(repo, "friction", "check", "--base", "main", "--json")
    assert done.stdout, done.stderr
    return done.returncode, json.loads(done.stdout)


def _findings(document: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """(kind, location, answer) per finding, in report order."""
    return [(f["kind"], f["location"], f["answer"]) for f in document["findings"]]


@pytest.fixture
def stale(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """A pull request, `feature` off `main`, that changes the file the page
    anchors and leaves the page as it was."""
    repo = make_adopter_repo()
    repo.write({CONFIG: ENFORCING, **SOURCE, PAGE: guide()})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit("change the CLI only", {"src/cli/main.py": "print('cli v2')\n"})
    return repo


def test_a_stale_page_fails_the_pull_request_and_its_revalidation_passes_it(
    stale: AdopterRepo,
) -> None:
    status, document = _check(stale)
    assert (status, document["mode"], document["failed"]) == (1, "enforcing", True)
    assert _findings(document) == [("friction", PAGE, None)]

    because = "the CLI change is internal: every command the guide shows is as described"
    revalidated = _pkit(
        stale,
        "friction",
        "revalidate",
        PAGE,
        "--outcome",
        "unchanged",
        "--because",
        because,
        "--yes",
    )
    assert revalidated.returncode == 0, revalidated.stdout + revalidated.stderr
    stale.commit("revalidate the guide", files=None)

    status, document = _check(stale)
    assert (status, document["failed"]) == (0, False)
    assert _findings(document) == [("answered", PAGE, "unchanged")]


def test_the_escape_hatch_is_a_one_line_flip_in_the_pull_request(stale: AdopterRepo) -> None:
    flip = ENFORCING.replace("mode: enforcing", "mode: warning")
    stale.commit("flip the friction mode to warning", {CONFIG: flip})
    assert stale.git("diff", "--numstat", "main", "--", CONFIG).stdout.split() == ["1", "1", CONFIG]

    status, document = _check(stale)
    assert (status, document["mode"], document["failed"]) == (0, "warning", False)
    assert _findings(document) == [("friction", PAGE, None)]
