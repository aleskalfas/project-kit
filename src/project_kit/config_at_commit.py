"""A backbone configuration key at a commit (ADR-057 point 2).

A key a record counts as the default branch holds it is read from a commit, never
from the working tree, which the change being judged holds. The delegate's name is
such a key (COR-064 point 2), the key that turns the landing check's refusal on is
another (COR-066 point 4), and so is the decision-debt key (COR-067 point 4). Each
caller's record says which commit. Every reader of such a key calls `key_at`, and no
other module reads one so.

It stands on artefact discovery's reading of a file at a state
(`friction_discovery.read_mapping_at`), and reads forgivingly (COR-048 point 4): a
file that does not parse, or a value the key does not take, gives a warning and the
default, and `pkit validate` is what fails on either. A key, its block or the file
absent gives the default with nothing to say (COR-048 point 3), so a misspelt key
reads as absent.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit import friction_discovery as fd
from project_kit.friction_git import SHORT, CommitTree
from project_kit.project_config import PROJECT_CONFIG_RELPATH


@dataclass(frozen=True)
class KeyAtCommit:
    """One key as a commit holds it.

    `value` is what a reader uses: the value written, or the default. `written` says
    the commit's file gives the value, and `warning` why a value there was read as the
    default, for a reader to print."""

    key: str
    commit: str
    value: Any
    written: bool = False
    warning: str | None = None


def key_at(
    target_root: Path,
    tree: CommitTree,
    key: str,
    *,
    default: Any,
    accepts: Callable[[Any], bool],
    expected: str,
) -> KeyAtCommit:
    """The dotted `key` as the commit `tree` holds it. `accepts` says whether a written
    value is one the key takes, and `expected` names what it takes, for the warning."""
    config, unread = fd.read_mapping_at(target_root, tree, PROJECT_CONFIG_RELPATH.as_posix())
    here = f"{PROJECT_CONFIG_RELPATH.as_posix()} at {tree.commit[:SHORT]}"
    reads = f"{key} reads as {default!r}, and `pkit validate` fails on it"
    if unread is not None:
        return KeyAtCommit(key, tree.commit, default, warning=f"{here} {unread}; {reads}")
    node: Mapping[str, Any] = config
    *blocks, leaf = key.split(".")
    for block in blocks:
        if block not in node:
            return KeyAtCommit(key, tree.commit, default)
        inner = node[block]
        if not isinstance(inner, Mapping):
            warning = f"{here}: `{block}` is not a mapping of keys; {reads}"
            return KeyAtCommit(key, tree.commit, default, warning=warning)
        node = cast(Mapping[str, Any], inner)
    if leaf not in node:
        return KeyAtCommit(key, tree.commit, default)
    value = node[leaf]
    if accepts(value):
        return KeyAtCommit(key, tree.commit, value, written=True)
    warning = f"{here}: {key} {value!r} is not {expected}; {reads}"
    return KeyAtCommit(key, tree.commit, default, warning=warning)


__all__ = ["KeyAtCommit", "key_at"]
