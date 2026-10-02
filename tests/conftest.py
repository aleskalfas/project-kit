"""Suite-wide fixtures. The adopter-repository fixtures wrap
`tests/adopter_repo.py`; see `tests/README.md` for the guide."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from project_kit import command_runner, run_cache, session_guard
from tests.adopter_repo import (
    AdopterRepo,
    AdopterTemplates,
    MakeAdopterRepo,
    Prepare,
    build_adopter_repo,
    prepared,
    stub_adapter_primitives,
)

#: What a run of the command runner sets in the environment of what it runs.
RUN_VARIABLES = (command_runner.DEADLINE_ENV, command_runner.STRAYS_ENV, run_cache.CACHE_ENV)


@pytest.fixture(autouse=True)
def outside_any_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts outside any run of the command runner, whatever started
    the suite — a `pkit validate` whose validator runs it, say: no inherited
    deadline, strays directory or run cache (the lifecycle README, "A run
    inside a run")."""
    for name in RUN_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def outside_any_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts outside any harness session, whatever started the
    suite: no session's anchor, so the cross-repository guard a backbone
    command runs (`session_guard`) answers the same in a session and in CI. A
    test that needs a session sets the anchor itself."""
    monkeypatch.delenv(session_guard.CLAUDE_CODE_ANCHOR, raising=False)


@pytest.fixture(scope="session")
def adopter_templates(tmp_path_factory: pytest.TempPathFactory) -> AdopterTemplates:
    """The adopter repositories this session has built, each copied for the tests
    that ask for its shape. Its pytest-xdist workers share them: a worker's base
    temporary directory lies in the session's, where the templates are. Set up
    before any function-scoped fixture of the first test that needs it, so the
    environment it keeps for the install is the one the session began with —
    outside any run, as every test starts."""
    base = tmp_path_factory.getbasetemp()
    session = base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base
    environment = {k: v for k, v in os.environ.items() if k not in RUN_VARIABLES}
    return AdopterTemplates(session / "adopter-templates", environment)


@pytest.fixture
def make_adopter_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, adopter_templates: AdopterTemplates
) -> MakeAdopterRepo:
    """Factory: `make_adopter_repo(capabilities=(...), history=False, chdir=True,
    root=tmp_path, prepare=None, fresh=False)` → an `AdopterRepo`. Call it with no
    arguments for the bare "git repo with the backbone installed, no commits"
    shape most CLI tests want; pass `root` to stand up a second adopter in the
    same test.

    The adopter is a copy of a template the session built once for its shape
    (`AdopterTemplates`); `prepare`, a module-level function, is a module's own
    setting-up, kept in the template too. `fresh=True` builds it in this test
    instead, as does a `root` that already holds anything: a test of the install
    itself — one that patches it, reads what it prints or puts something in the
    way of it — needs its own run of it (`tests/README.md`)."""

    def _make(
        *,
        capabilities: Sequence[str] = (),
        history: bool = False,
        chdir: bool = True,
        root: Path | None = None,
        prepare: Prepare | None = None,
        fresh: bool = False,
    ) -> AdopterRepo:
        target = root if root is not None else tmp_path
        if fresh or (target.exists() and any(target.iterdir())):
            adopter = build_adopter_repo(
                target,
                monkeypatch=monkeypatch,
                capabilities=capabilities,
                history=history,
                chdir=chdir,
            )
            return adopter if prepare is None else prepared(adopter, prepare)
        stub_adapter_primitives(monkeypatch)
        adopter = adopter_templates.copy(
            target, capabilities=capabilities, history=history, prepare=prepare
        )
        if chdir:
            monkeypatch.chdir(target)
        return adopter

    return _make


@pytest.fixture
def adopter_repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """An adopter repository at `tmp_path` with the backbone installed and the
    scripted history laid down (`adopter_repo.history` holds the SHAs)."""
    return make_adopter_repo(history=True)


@pytest.fixture
def pkit_on_path(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A `pkit` that is the real CLI under this interpreter, first on PATH, for the
    capability scripts a test runs that read through the backbone — `pkit
    connections resolve`, `pkit friction check`, `pkit friction artefacts`. It
    bypasses the entry-point
    router, so no test reaches `uv` or the network. Returns its directory, which
    lies outside the adopter repository."""
    bin_dir = tmp_path_factory.mktemp("pkit-bin")
    pkit = bin_dir / "pkit"
    pkit.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m project_kit "$@"\n', encoding="utf-8")
    pkit.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bin_dir
