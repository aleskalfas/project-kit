"""Suite-wide fixtures. The adopter-repository fixtures wrap
`tests/adopter_repo.py`; see `tests/README.md` for the guide."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, build_adopter_repo


@pytest.fixture
def make_adopter_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MakeAdopterRepo:
    """Factory: `make_adopter_repo(capabilities=(...), history=False, chdir=True,
    root=tmp_path)` → an `AdopterRepo`. Call it with no arguments for the bare
    "git repo with the backbone installed, no commits" shape most CLI tests
    want; pass `root` to stand up a second adopter in the same test."""

    def _make(
        *,
        capabilities: Sequence[str] = (),
        history: bool = False,
        chdir: bool = True,
        root: Path | None = None,
    ) -> AdopterRepo:
        return build_adopter_repo(
            root if root is not None else tmp_path,
            monkeypatch=monkeypatch,
            capabilities=capabilities,
            history=history,
            chdir=chdir,
        )

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
    connections resolve`, `pkit friction check`. It bypasses the entry-point
    router, so no test reaches `uv` or the network. Returns its directory, which
    lies outside the adopter repository."""
    bin_dir = tmp_path_factory.mktemp("pkit-bin")
    pkit = bin_dir / "pkit"
    pkit.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m project_kit "$@"\n', encoding="utf-8")
    pkit.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bin_dir
