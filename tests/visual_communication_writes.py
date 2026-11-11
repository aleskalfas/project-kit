"""Writes that fail, for the visual-communication tests: a command run in this process
finds a file it cannot move into its place, as on a full disk, or one it cannot remove, as
where another program holds it.

A command writes the files of one run as one change (`files.Change`): each file is staged
beside its place, then moved there, the records last. A move that fails here fails once
the files before it are in place, so a test sees the command take them back.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Collection
from pathlib import Path
from typing import Any

import pytest

#: What a command says of a file it could not move into its place here.
FULL = os.strerror(errno.ENOSPC)


def failing(
    monkeypatch: pytest.MonkeyPatch,
    *,
    write: Collection[str] = (),
    remove: Collection[str] = (),
) -> None:
    """Moving a file or a folder whose name `write` holds into its place fails as on a full
    disk, and removing a file whose name `remove` holds fails as where another program
    holds it, for the length of the test. Every other move and removal goes on."""
    replace, rename, unlink = os.replace, os.rename, os.unlink

    def moved(move: Any) -> Any:
        def failing_move(source: Any, destination: Any, *args: Any, **kwargs: Any) -> None:
            if Path(destination).name in write:
                raise OSError(errno.ENOSPC, FULL, str(destination))
            move(source, destination, *args, **kwargs)

        return failing_move

    def failing_unlink(path: Any, *args: Any, **kwargs: Any) -> None:
        if Path(path).name in remove:
            raise OSError(errno.EBUSY, os.strerror(errno.EBUSY), str(path))
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "replace", moved(replace))
    monkeypatch.setattr(os, "rename", moved(rename))
    monkeypatch.setattr(os, "unlink", failing_unlink)
