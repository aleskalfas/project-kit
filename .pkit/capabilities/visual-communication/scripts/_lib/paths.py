"""A path in content (visual-communication DEC-056 points 2 and 5): what a field its component
marks as holding paths gives, each path naming one file of the repository, and how the check
of the content judges it.

- **Its form** (`form_problem`): the names of folders and a file, joined by `/`, from the
  repository's root, as a path anchor's value narrowed to one file (COR-050 point 2). It
  starts with no `/`, and holds no empty name, no `.` or `..`, no `\\`, no control
  character, and no `*`, `?` or `[`, so it is no glob.
- **Found in version control's list** (`Repository.judge`): letter for letter, among the
  paths git lists, those its index holds and those not yet tracked and not ignored
  (`location.repository_files`). The file system is never asked, so a file a sparse
  checkout leaves out of the working tree counts, every clone gives one answer for a
  committed file whatever its file system does with case, and a file the clone ignores, or
  a folder, names no document.
- **Never into what a piece handed out:** a path into the folder of a piece's version
  handed out, or into that of a published piece's copy, is refused, whether or not its file
  is listed (DEC-016 point 3).
- **Its message** names a file whose path differs only in case, a file that lies there and
  git ignores, and a folder, where one does. The file system is asked for that alone.

The check of the content judges every path on every run, never from the findings record,
since whether a path names a file depends on no file a scene is computed from (point 5).
"""

from __future__ import annotations

import unicodedata
from functools import cached_property
from pathlib import Path

from _lib import location
from _lib.fingerprint import CURRENT_COPY, HANDED_OUT

#: The labels of the findings on a path in content, each of which fails (DEC-056 point 5): a
#: path not of the form, one that names no file version control lists, and one into what a
#: piece handed out.
FORM = "path-form"
MISSING = "path-missing"
OUTPUT = "path-handed-out"

#: The characters a path never holds, since each would make it a glob.
_GLOB = ("*", "?", "[")


def form_problem(text: str) -> str | None:
    """Why `text` is no path of a file from the repository's root, in words; None where it
    is one (DEC-056 point 2)."""
    if not text:
        return "is empty: a path names a file from the repository's root"
    if text.startswith("/"):
        return "starts with `/`: a path starts at the repository's root, with no `/` before it"
    if "\\" in text:
        return "holds a `\\`: a path joins its names with `/`"
    if any(unicodedata.category(character) == "Cc" for character in text):
        return "holds a control character"
    glob = next((character for character in _GLOB if character in text), None)
    if glob is not None:
        return f"holds `{glob}`, which would make it a glob: a path names one file"
    steps = text.split("/")
    if "" in steps:
        return "holds an empty name, such as a doubled or a trailing `/`"
    if any(step in (".", "..") for step in steps):
        return "holds `.` or `..`: a path names each folder on the way from the repository's root"
    return None


class Repository:
    """The files of the repository at `root` that a path may name, listed once, the first
    time a path is judged; `pieces`, the folder of the location that holds the pieces,
    relative to `root`."""

    def __init__(self, root: Path, pieces: str) -> None:
        self.root = root
        self.pieces = pieces

    @cached_property
    def listed(self) -> frozenset[str]:
        """Every path version control lists. Raises location.GitFailed."""
        return frozenset(location.repository_files(self.root))

    def judge(self, text: str) -> tuple[str, str, str] | None:
        """What is wrong with the path `text`, as the label of its finding, why, in words
        that follow the path, and its fix; None where it names a file the repository holds.
        Raises location.GitFailed."""
        problem = form_problem(text)
        if problem is not None:
            return FORM, problem, "write the file's path from the repository's root"
        if self._handed_out(text):
            return (
                OUTPUT,
                "names a file a piece handed out, or a published piece's copy, which is an "
                "output: what it was made from lies in its piece's folder",
                "name the file the output was made from, in its piece's folder",
            )
        if text in self.listed:
            return None
        return (
            MISSING,
            f"names no file version control lists{self._near(text)}",
            "write the path of a file the repository holds, as it is renamed, or take the path out",
        )

    def _handed_out(self, text: str) -> bool:
        """Whether `text` leads into the folder of a piece's version handed out, or into
        that of a published piece's copy (DEC-016 point 3)."""
        prefix = f"{self.pieces}/"
        if not text.startswith(prefix):
            return False
        steps = text[len(prefix) :].split("/")
        return len(steps) > 2 and steps[1] in (HANDED_OUT, CURRENT_COPY)

    def _near(self, text: str) -> str:
        """What comes near a path no file answers, in words: a file whose path differs only
        in case, a folder of that path, or a file that lies there and git ignores."""
        alike = sorted(held for held in self.listed if held.lower() == text.lower())
        if alike:
            return f": it lists `{alike[0]}`, and a path names a file by its exact case"
        if any(held.startswith(f"{text}/") for held in self.listed):
            return ": it is a folder, and a path names one file"
        try:
            lies = (self.root / text).is_file()
            ignored = lies and bool(location.ignored(self.root, [text]))
        except (OSError, location.GitFailed):
            return ""
        if ignored:
            return ": the file lies there, and git ignores it, so no other clone holds it"
        return ""
