"""Reading git for the friction checks (COR-050): the primitives every friction reader shares.

This layer reads git and nothing else; it imports no other friction module, so
what artefacts declare (`friction_discovery`), an artefact's walk through its
history (`friction_history`) and both checks build on it without a cycle
(ADR-057 point 2).

- `run_git` runs one git command, `commit_of` resolves a name to a commit.
- `CommitTree` is one commit's files, read from git objects — nothing is
  checked out — with each file's mode and object (`entry`), gitlinks included.
- `DiffEntry` is one path a diff or a log lists; from `git log --raw` it
  carries the file's entry after the commit and at each parent, so whether a
  commit put a file back as it stood elsewhere is told by object id, with no
  further process. `parse_name_status` reads a `--name-status` listing.
- `BlobReader` is one `git cat-file --batch` process answering requests as
  they come, by `<commit>:<path>` or by object id.
- `TreeReader` gives the entry of a path at a commit — its mode and object —
  from the tree object of its folder, read through a `BlobReader`: no process
  per path, each folder of each commit read once.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import click

# How many characters of a commit the human output shows.
SHORT = 12

# A pure rename keeps a file's content: git's similarity score for it.
IDENTICAL = 100

# The mode of a link in a git tree.
LINK_MODE = "120000"

# The mode git writes for a path a side of a diff does not hold.
_ABSENT_MODE = "000000"

#: A file's entry in a git tree: its mode and its object id. Two states of a file
#: are the same when their entries are — content and mode alike (COR-050 point 5).
TreeEntry = tuple[str, str]


class FrictionCheckError(click.ClickException):
    """The check could not run: no git repository, no commit, a base that does not resolve."""


def run_git(
    root: Path, *args: str, stdin: bytes | None = None, accept: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, input=stdin, capture_output=True, check=False
        )
    except OSError as exc:
        raise FrictionCheckError(f"cannot run git: {exc}") from exc
    if completed.returncode not in accept:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise FrictionCheckError(
            f"`git {args[0]}` failed: {detail or f'exit status {completed.returncode}'}"
        )
    return completed


def commit_of(root: Path, name: str) -> str | None:
    """The commit `name` resolves to, or None."""
    completed = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}", accept=(0, 1)
    )
    commit = completed.stdout.decode().strip()
    return commit if completed.returncode == 0 and commit else None


def _tree_records(listed: bytes) -> Iterable[tuple[str, str, str, str]]:
    """`(path, mode, kind, object)` for each record of a NUL-separated `git ls-tree` listing."""
    for record in listed.split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        mode, kind, obj = meta.decode().split(" ")
        yield path.decode("utf-8", "surrogateescape"), mode, kind, obj


class CommitTree:
    """The files of one commit, read from git objects; nothing is checked out."""

    def __init__(self, root: Path, commit: str) -> None:
        self._root = root
        listed = run_git(root, "ls-tree", "-r", "-z", commit).stdout
        self._entries: dict[str, TreeEntry] = {}  # path -> (mode, object), gitlinks included
        self._blobs: dict[str, TreeEntry] = {}  # the files: a submodule is a commit, not a file
        for path, mode, kind, obj in _tree_records(listed):
            self._entries[path] = (mode, obj)
            if kind == "blob":
                self._blobs[path] = (mode, obj)
        self._files = tuple(sorted(self._blobs))

    def files(self) -> Sequence[str]:
        return self._files

    def entry(self, path: str) -> TreeEntry | None:
        """The mode and object at `path` — a file's, or a gitlink's — or `None`."""
        return self._entries.get(path)

    def read_bytes(self, paths: Sequence[str]) -> Mapping[str, bytes | None]:
        contents: dict[str, bytes | None] = dict.fromkeys(paths)
        wanted = [
            (rel, self._blobs[rel][1])
            for rel in dict.fromkeys(paths)
            if rel in self._blobs and self._blobs[rel][0] != LINK_MODE
        ]
        if not wanted:
            return contents
        batch = "".join(f"{obj}\n" for _rel, obj in wanted).encode()
        out = run_git(self._root, "cat-file", "--batch", stdin=batch).stdout
        offset = 0
        for rel, _obj in wanted:
            header_end = out.index(b"\n", offset)
            header = out[offset:header_end].split(b" ")
            if len(header) != 3:  # `<object> missing`: nothing to read
                offset = header_end + 1
                continue
            start = header_end + 1
            size = int(header[2])
            contents[rel] = out[start : start + size]
            offset = start + size + 1
        return contents


@dataclass(frozen=True)
class DiffEntry:
    """One path a diff or a log lists; `old_path` and `score` for a rename.

    From `git log --raw` it also carries the file's entry: `after`, its mode
    and object once the commit is made — `None` where the commit removed it —
    and `before`, its entry at each parent of the commit, in parent order,
    under its name there — `None` where that parent has no such file. A
    `--name-status` listing gives neither: `before` is then empty.
    """

    status: str  # git's status letter: A, M, D, R, T, U
    path: str  # the path at head; for a deletion, the removed path
    old_path: str | None = None
    score: int | None = None
    after: TreeEntry | None = None
    before: tuple[TreeEntry | None, ...] = ()

    @property
    def changes_content(self) -> bool:
        return not (self.status == "R" and self.score == IDENTICAL)

    @property
    def raw(self) -> bool:
        """Whether the listing gave the file's entries (`git log --raw`)."""
        return bool(self.before)


def tree_entry(mode: str, obj: str) -> TreeEntry | None:
    """A side of a raw listing as an entry: `None` where that side holds no file."""
    return None if mode == _ABSENT_MODE else (mode, obj)


def parse_name_status(tokens: Sequence[str]) -> list[DiffEntry]:
    """The entries of a NUL-separated `--name-status` listing, as `git diff` and `git log` print it.

    A rename or copy is three tokens (`R<score>`, old, new); anything else two
    (status, path). A copy adds its new path and leaves the source alone.
    """
    entries: list[DiffEntry] = []
    index = 0
    while index < len(tokens):
        code = tokens[index]
        letter = code[:1]
        if letter in ("R", "C"):
            old, new = tokens[index + 1], tokens[index + 2]
            index += 3
            if letter == "R":
                score = int(code[1:]) if code[1:].isdigit() else None
                entries.append(DiffEntry("R", new, old, score))
            else:
                entries.append(DiffEntry("A", new))
            continue
        entries.append(DiffEntry(letter, tokens[index + 1]))
        index += 2
    return entries


class BlobReader:
    """One `git cat-file --batch` process, answering requests as they come."""

    def __init__(self, root: Path) -> None:
        try:
            self._process = subprocess.Popen(
                ["git", "cat-file", "--batch"],
                cwd=root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise FrictionCheckError(f"cannot run git: {exc}") from exc

    def read(self, commit: str, path: str) -> bytes | None:
        """The blob at `path` in `commit`, or `None` when the commit holds no file there."""
        if "\n" in path:
            return None
        return self._request(f"{commit}:{path}")

    def read_object(self, obj: str) -> bytes | None:
        """The blob `obj` names, or `None` when it names none this repository holds."""
        return self._request(obj)

    def read_tree(self, commit: str, folder: str) -> bytes | None:
        """The tree object of `folder` in `commit` — the root's for `""` — or `None` when
        the commit holds no such folder."""
        if "\n" in folder:
            return None
        name = f"{commit}:{folder}" if folder else f"{commit}^{{tree}}"
        return self._request(name, b"tree")

    def _request(self, name: str, kind: bytes = b"blob") -> bytes | None:
        assert self._process.stdin is not None and self._process.stdout is not None
        try:
            self._process.stdin.write(f"{name}\n".encode("utf-8", "surrogateescape"))
            self._process.stdin.flush()
            header = self._process.stdout.readline().split()
            # `<name> missing` or `<name> ambiguous` end in that word; a hit is
            # `<object> <type> <size>`, and neither an object name nor a type
            # holds a space, so a path with spaces cannot be mistaken for one.
            if not header or header[-1] in (b"missing", b"ambiguous") or len(header) != 3:
                return None
            size = int(header[2])
            data = self._process.stdout.read(size)
            self._process.stdout.read(1)  # the newline after the content
        except (OSError, ValueError) as exc:
            raise FrictionCheckError(f"`git cat-file` failed: {exc}") from exc
        return data if header[1] == kind else None

    def close(self) -> None:
        if self._process.stdin is not None:
            self._process.stdin.close()
        self._process.wait()


def _tree_object(raw: bytes, size: int) -> dict[str, TreeEntry]:
    """The entries of a raw tree object, by name: `<mode> <name>\\0<object>` each, the
    object `size` bytes long; a mode written short (`40000`) padded as `ls-tree` prints it."""
    found: dict[str, TreeEntry] = {}
    offset = 0
    while offset < len(raw):
        space = raw.index(b" ", offset)
        end = raw.index(b"\0", space)
        mode = raw[offset:space].decode().rjust(6, "0")
        name = raw[space + 1 : end].decode("utf-8", "surrogateescape")
        found[name] = (mode, raw[end + 1 : end + 1 + size].hex())
        offset = end + 1 + size
    return found


class TreeReader:
    """The entry — mode and object — of a path at a commit, gitlinks included, read from
    the tree object of the path's folder through one `BlobReader`, each folder of each
    commit once for the reader's life. A path the commit does not hold has none."""

    def __init__(self, blobs: BlobReader) -> None:
        self._blobs = blobs
        self._trees: dict[tuple[str, str], dict[str, TreeEntry]] = {}

    def entry(self, commit: str, path: str) -> TreeEntry | None:
        folder, _, name = path.rpartition("/")
        key = (commit, folder)
        found = self._trees.get(key)
        if found is None:
            raw = self._blobs.read_tree(commit, folder)
            found = {} if raw is None else _tree_object(raw, len(commit) // 2)
            self._trees[key] = found
        return found.get(name)

    def entries(self, commit: str, paths: Iterable[str]) -> dict[str, TreeEntry | None]:
        """The entry of each of `paths` at `commit`, `None` where it holds none."""
        return {rel: self.entry(commit, rel) for rel in paths}
