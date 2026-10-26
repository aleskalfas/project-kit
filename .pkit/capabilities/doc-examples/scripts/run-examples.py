#!/usr/bin/env python3
"""doc-examples capability — run-examples: run each console example of a project's pages
as a test ([doc-examples:DEC-001-console-examples-as-tests]).

A page shows a command and what it prints in a `console` fence. This program runs
each such fence in a scratch project the project's own setup step builds, outside
the repository, and fails a fence whose output differs from the page's. The
capability's README states the contract a page is written against, which is the
capability's versioned surface (DEC-001 point 6); this docstring names where each
part of it lives in the code.

- **The pages (point 3):** read through the methodology's CLI, `pkit doc-examples
  pages --json`, which answers the pages, the repository's root and the project's
  configuration of the run (`read_selection`). This program reads no configuration
  and resolves no type itself.
- **The fences (point 2):** `console_fences` reads them, in a list item or a block
  quote too. One shell runs a fence's commands in order (`Shell`).
- **The scratch project (point 4):** the setup step builds it once (`_setup`), and
  each fence starts from it as the setup left it, at the same paths (`_restore`).
- **What varies (point 5):** the run's folders, the project's placeholders and the
  caller's values are written as placeholders before comparing (`substitutions`).
- **An update (point 7):** `--update` writes each command's new output into its page,
  once every page's commands ran with no write in the repository.
- **The guards (point 8):** limits of time and output on every command the run starts,
  and a write in the repository fails the run (`listing`).

It is a program of its own, never a command of the methodology's CLI, so no grant
of that CLI runs a page's commands (point 9). It needs only the standard library
and the methodology's CLI on `PATH`.

Usage, from the repository's root:

  .pkit/capabilities/doc-examples/scripts/run-examples.py              every page
  .pkit/capabilities/doc-examples/scripts/run-examples.py README.md    the pages named
  .pkit/capabilities/doc-examples/scripts/run-examples.py --update     write new output

Exit codes (point 10):
  0  every fence matches, no page holds one, or --update wrote every output that differed
  1  a fence fails
  2  the run cannot start: a selection it cannot read, a setup step or a placeholder's
     command that fails, or a page it cannot read
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import functools
import json
import os
import re
import secrets
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

#: The info string's first word that makes a fence a test.
LANGUAGE = "console"
#: Other names for a shell session, which a run reports and never runs (point 2).
SESSION_NAMES = frozenset(
    {
        "shell-session",
        "shellsession",
        "sh-session",
        "bash-session",
        "tcshcon",
        "doscon",
        "ps1con",
        "pwsh-session",
    }
)
PROMPT = "$ "
#: In a page's output, any text within one line.
ANY = "<any>"
#: Seconds a command of a page may run, by default.
DEFAULT_TIMEOUT = 60.0
#: Seconds a command of the setup step or of a placeholder may run, by default.
DEFAULT_SETUP_TIMEOUT = 600.0
#: Bytes a command may print.
OUTPUT_LIMIT = 1 << 20
#: The repository's git directory, left out of the listing: any process that reads the
#: repository's state may write in it.
GIT_DIR = ".git"
#: The settings the run fixes in every command's environment, beside `HOME`, `TMPDIR`
#: and `PATH` (point 4).
FIXED = {"LANG": "C", "LC_ALL": "C", "TERM": "dumb", "NO_COLOR": "1"}
#: The variable holding the repository's path, given to the setup step's commands.
REPOSITORY_VARIABLE = "DOC_EXAMPLES_REPOSITORY"
#: The CLI query that answers the pages and the run's configuration.
PAGES_COMMAND = ("pkit", "doc-examples", "pages", "--json")
#: Seconds that query may take.
PAGES_TIMEOUT = 300.0
#: The version of that answer this program reads.
SCHEMA_VERSION = 1

#: The placeholders of the run's folders (point 5).
PROJECT, HOME, TMP, SCRATCH, REPOSITORY = (
    "<project>",
    "<home>",
    "<tmp>",
    "<scratch>",
    "<repository>",
)
#: A project placeholder's name, and the name a caller's value is written as.
PROJECT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
#: A control character an update never writes: every C0 character but the tab, DEL,
#: and the line and paragraph separators a reader may take for a line's end.
CONTROL = re.compile(r"[\x00-\x08\x0a-\x1f\x7f\x85\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}]")

_QUOTE = re.compile(r"[ ]{0,3}>[ ]?")
_OPENING = re.compile(
    r"^(?P<quote>(?:[ ]{0,3}>[ ]?)*)"
    r"(?P<lead>(?:[ ]*(?:[-+*]|[0-9]{1,9}[.)])[ ]+)?[ ]*)"
    r"(?P<mark>`{3,}|~{3,})(?P<info>.*)$"
)


class CannotRun(Exception):
    """The run cannot start, or its setup step or a placeholder's command fails."""


# --- reading a page ------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    """One command of a fence: the prompt's line `index` in the page, the command's
    `text`, the `output` the page shows, without the fence's indent and quote, and
    `end`, the index of the line after its output."""

    index: int
    text: str
    output: tuple[str, ...]
    end: int


@dataclass(frozen=True)
class Fence:
    """A fence of the page at `path`: the opening line's `index`, the `indent` its
    lines carry, `end`, the closing line's index, and its commands, or the `problem`
    that keeps it from running. `mark` is the opening's run of backticks or tildes,
    `quote` the block quote's markers its lines open with, and `language` the info
    string's first word."""

    path: str
    index: int
    indent: int
    end: int
    commands: tuple[Command, ...]
    problem: str | None = None
    mark: str = "```"
    quote: str = ""
    language: str = LANGUAGE

    @property
    def line(self) -> int:
        return self.index + 1

    def reads_as_markup(self, line: str) -> bool:
        """Whether `line`, written as output in this fence, would read as a command or
        close the fence."""
        if line.startswith(PROMPT) or line.rstrip() == PROMPT.rstrip():
            return True
        return _closing(self.mark).match(line) is not None

    def unwritable(self, lines: Sequence[str], secrets: Sequence[str] = ()) -> str | None:
        """Why an update cannot write `lines` as output in this fence, or None when it
        can: a line would read as a command or close the fence, holds a control
        character, which could end a line or hide text, holds `<any>`, or holds one of
        `secrets`, the values variables take from the caller."""
        if any(self.reads_as_markup(line) for line in lines):
            return "a line of it would read as a command or close the fence"
        if any(CONTROL.search(line) for line in lines):
            return "a line of it holds a control character, which could end a line or hide text"
        if any(ANY in line for line in lines):
            return f"a line of it holds `{ANY}`, which the next run would read as any text"
        if any(secret in line for line in lines for secret in secrets):
            return "a line of it holds a value a variable takes from you"
        return None

    def written(self, line: str) -> str:
        """`line` of output as the page holds it, in this fence's quote and indent."""
        if not line:
            return self.quote.rstrip()
        return self.quote + " " * self.indent + line


def read_page(path: Path) -> str:
    """A page's text, its lines ending at a line feed alone. A carriage return ends no
    line, unlike Python's default reading: the run reads the lines it writes, and a
    reviewer's diff shows them. Raises OSError or UnicodeDecodeError."""
    with path.open(encoding="utf-8", newline="") as page:
        return page.read().replace("\r\n", "\n")


def _closing(mark: str) -> re.Pattern[str]:
    """A line that closes a fence opened with `mark`."""
    return re.compile(rf"^ *{re.escape(mark[0])}{{{len(mark)},}}[ \t]*$")


def _body_start(lines: Sequence[str]) -> int:
    """The index of the first line after the page's front matter."""
    if lines and lines[0].rstrip() == "---":
        for index in range(1, len(lines)):
            if lines[index].rstrip() == "---":
                return index + 1
    return 0


def _unquoted(line: str, depth: int) -> str | None:
    """`line` without `depth` block-quote markers, or None when it lacks them: the
    block quote, and a fence in it, ended before it."""
    for _ in range(depth):
        found = _QUOTE.match(line)
        if found is None:
            return None
        line = line[found.end() :]
    return line


def _dedent(line: str, indent: int) -> str:
    """`line` with up to `indent` leading spaces removed, as a fence's content is."""
    spaces = len(line) - len(line.lstrip(" "))
    return line[min(spaces, indent) :]


def console_fences(lines: Sequence[str], path: str) -> list[Fence]:
    """Every fence of a page's `lines` that is a shell session, in order: a `console`
    fence, and a fence under another name for one, which holds no commands. A fence of
    another language is passed over whole, so a fence quoted inside it is none."""
    found: list[Fence] = []
    index = _body_start(lines)
    while index < len(lines):
        opening = _OPENING.match(lines[index])
        if opening is None or (opening["mark"][0] == "`" and "`" in opening["info"]):
            index += 1
            continue
        mark, quote = opening["mark"], opening["quote"]
        depth = quote.count(">")
        indent = len(opening["lead"])
        closing = _closing(mark)
        body: list[str] = []
        end, after = len(lines), len(lines)
        for later in range(index + 1, len(lines)):
            line = _unquoted(lines[later], depth)
            if line is None:
                end = after = later
                break
            if closing.match(line):
                end, after = later, later + 1
                break
            body.append(_dedent(line, indent))
        words = opening["info"].split()
        language = words[0] if words else ""
        if language == LANGUAGE:
            found.append(_fence(body, path, index, indent, end, mark, quote))
        elif language in SESSION_NAMES:
            found.append(Fence(path, index, indent, end, (), None, mark, quote, language))
        index = after
    return found


def _fence(
    body: Sequence[str], path: str, index: int, indent: int, end: int, mark: str, quote: str
) -> Fence:
    commands: list[Command] = []
    problem: str | None = None
    prompt: tuple[int, str] | None = None
    output: list[str] = []
    for offset, line in enumerate(body):
        at = index + 1 + offset
        if line.startswith(PROMPT) or line.rstrip() == PROMPT.rstrip():
            if prompt is not None:
                commands.append(Command(prompt[0], prompt[1], tuple(output), at))
            prompt, output = (at, line[len(PROMPT) :].rstrip()), []
        elif prompt is not None:
            output.append(line)
        elif line.strip() and problem is None:
            problem = (
                f"line {at + 1} comes before the fence's first command, "
                "a line that starts with `$ `"
            )
    if prompt is not None:
        commands.append(Command(prompt[0], prompt[1], tuple(output), end))
    if not commands and problem is None:
        problem = "the fence holds no command: no line starts with `$ `"
    return Fence(path, index, indent, end, tuple(commands), problem, mark, quote)


# --- comparing output ------------------------------------------------------------------


def compared(lines: Sequence[str]) -> list[str]:
    """`lines` as they are compared: each without the spaces that end it, and without
    the blank lines that end them."""
    kept = [line.rstrip() for line in lines]
    while kept and not kept[-1]:
        kept.pop()
    return kept


@functools.lru_cache(maxsize=1024)
def _pattern(expected: str) -> re.Pattern[str]:
    return re.compile(".*".join(re.escape(part) for part in expected.split(ANY)), re.DOTALL)


def line_matches(expected: str, actual: str) -> bool:
    """Whether a line the page shows matches a line the command printed: the same
    text, where each `<any>` stands for any text."""
    if ANY not in expected:
        return expected == actual
    return _pattern(expected).fullmatch(actual) is not None


def output_matches(expected: Sequence[str], actual: Sequence[str]) -> bool:
    return len(expected) == len(actual) and all(map(line_matches, expected, actual))


def updated_output(expected: Sequence[str], actual: Sequence[str]) -> list[str]:
    """`actual`, with each line that a line of `expected` matches written as `expected`
    writes it, its `<any>` kept: the longest run of matching lines, in order, is kept."""
    rows, columns = len(expected), len(actual)
    longest = [[0] * (columns + 1) for _ in range(rows + 1)]
    for row in range(rows - 1, -1, -1):
        for column in range(columns - 1, -1, -1):
            if line_matches(expected[row], actual[column]):
                longest[row][column] = longest[row + 1][column + 1] + 1
            else:
                longest[row][column] = max(longest[row + 1][column], longest[row][column + 1])
    written: list[str] = []
    row = column = 0
    while column < columns:
        if (
            row < rows
            and line_matches(expected[row], actual[column])
            and longest[row][column] == longest[row + 1][column + 1] + 1
        ):
            written.append(expected[row])
            row, column = row + 1, column + 1
        elif row < rows and longest[row + 1][column] >= longest[row][column + 1]:
            row += 1
        else:
            written.append(actual[column])
            column += 1
    return written


def whole(text: str) -> str:
    """A pattern matching `text` only where it stands whole, never as part of a longer
    word or number. A text that opens with a digit is whole unless a digit or a dot
    comes before it, and one that ends with a digit unless a digit, or a dot and a
    digit, come after it. A text that opens or ends with a letter or an underscore is
    whole unless a letter, a digit or an underscore comes beside it on that side."""
    before = after = ""
    first, last = text[0], text[-1]
    if first in "0123456789":
        before = r"(?<![0-9.])"
    elif first.isalpha() or first == "_":
        before = r"(?<!\w)"
    if last in "0123456789":
        after = r"(?![0-9]|\.[0-9])"
    elif last.isalpha() or last == "_":
        after = r"(?!\w)"
    return before + re.escape(text) + after


@dataclass(frozen=True)
class Substitutions:
    """The texts written as placeholders before comparing, in one pattern: the longest
    first, so no text is replaced inside a longer one."""

    pattern: re.Pattern[str] | None
    placeholders: tuple[str, ...]

    def apply(self, text: str) -> str:
        if self.pattern is None:
            return text
        return self.pattern.sub(lambda found: self.placeholders[(found.lastindex or 1) - 1], text)


def substitutions(
    folders: Mapping[str, Path], texts: Mapping[str, str] | None = None
) -> Substitutions:
    """The run's `folders`, each written as its placeholder anywhere, as written and
    resolved, and each of `texts`, by its placeholder, where it stands whole."""
    found: dict[str, tuple[str, str]] = {}
    for placeholder, folder in folders.items():
        for form in (str(folder), str(folder.resolve())):
            found[form] = (re.escape(form), placeholder)
    for placeholder, text in (texts or {}).items():
        if text:
            found.setdefault(text, (whole(text), placeholder))
    ordered = sorted(found.items(), key=lambda item: len(item[0]), reverse=True)
    if not ordered:
        return Substitutions(None, ())
    pattern = re.compile("|".join(f"({regex})" for _text, (regex, _p) in ordered))
    return Substitutions(pattern, tuple(placeholder for _t, (_r, placeholder) in ordered))


def normalised(output: str, replace: Substitutions) -> list[str]:
    """A command's output as it is compared, its varying parts replaced."""
    return compared(replace.apply(output.replace("\r\n", "\n")).split("\n"))


# --- the selection --------------------------------------------------------------------


@dataclass(frozen=True)
class Selection:
    """What the CLI answers: the repository's `root`, the `pages` the run reads, and the
    project's configuration of the run, read by the CLI (DEC-001 points 3 to 5)."""

    root: Path
    pages: tuple[str, ...]
    setup: tuple[str, ...] = ()
    path: tuple[str, ...] = ()
    environment: Mapping[str, str | None] = field(default_factory=dict[str, "str | None"])
    placeholders: Mapping[str, str] = field(default_factory=dict[str, str])


def read_selection(cwd: Path, argv: Sequence[str] = PAGES_COMMAND) -> Selection:
    """The pages and the run's configuration, as `pkit doc-examples pages --json`
    answers them from `cwd`. Raises CannotRun when it gives no answer."""
    shown = " ".join(argv)
    try:
        done = subprocess.run(
            list(argv),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=PAGES_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise CannotRun(f"`{shown}` gave no answer in {PAGES_TIMEOUT:g} seconds") from exc
    except OSError as exc:
        raise CannotRun(
            f"`{shown}` cannot run: {exc}; the run needs the methodology's CLI on PATH"
        ) from exc
    if done.returncode != 0:
        said = (done.stderr or done.stdout).strip().splitlines()[-10:]
        raise CannotRun(
            f"`{shown}` exited {done.returncode}" + "".join(f"\n  {line}" for line in said)
        )
    try:
        document = json.loads(done.stdout)
    except ValueError as exc:
        raise CannotRun(f"`{shown}` printed no JSON document: {exc}") from exc
    return selection_of(document, shown)


def selection_of(document: object, shown: str = " ".join(PAGES_COMMAND)) -> Selection:
    """The selection a pages document holds. Raises CannotRun on another shape."""
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise CannotRun(f"`{shown}` answered no document of schema_version {SCHEMA_VERSION}")
    try:
        root = document["root"]
        pages = document["pages"]
        setup = document.get("setup", [])
        path = document.get("path", [])
        environment = document.get("environment", {})
        placeholders = document.get("placeholders", {})
        if not (
            isinstance(root, str)
            and _strings(pages)
            and _strings(setup)
            and _strings(path)
            and isinstance(environment, dict)
            and all(value is None or isinstance(value, str) for value in environment.values())
            and isinstance(placeholders, dict)
            and _strings(list(placeholders.values()))
        ):
            raise TypeError("a key of another shape")
    except (KeyError, TypeError) as exc:
        raise CannotRun(f"`{shown}` answered a document this run cannot read: {exc}") from exc
    return Selection(
        Path(root), tuple(pages), tuple(setup), tuple(path), dict(environment), dict(placeholders)
    )


def _strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


# --- running commands in a shell -------------------------------------------------------


@dataclass(frozen=True)
class Ran:
    """What a command printed, at most `OUTPUT_LIMIT` bytes of it, its exit `status`,
    and why it was stopped, if it was: `time` or `size`, or `ended` when the shell
    ended with it."""

    output: str
    status: int | None = None
    stopped: str | None = None


def _quoted(text: str) -> str:
    """`text` as one word of a POSIX shell."""
    return "'" + text.replace("'", "'\\''") + "'"


class Shell:
    """One POSIX shell, in a process group of its own, that runs commands in order,
    each with its input closed: a `cd` or a variable carries over to the next command.
    Each command's standard output and error reach one pipe, and a mark only this run
    knows ends each command's output."""

    def __init__(self, cwd: Path, env: Mapping[str, str]) -> None:
        self.token = secrets.token_hex(16)
        self._mark = re.compile(rb"\n" + self.token.encode() + rb" ([0-9]+)\n")
        self.process = subprocess.Popen(
            ["/bin/sh"],
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self._pending = bytearray()
        self._closed = False

    def run(self, command: str, timeout: float, limit: int = OUTPUT_LIMIT) -> Ran:
        """Run `command` for at most `timeout` seconds and `limit` bytes of output. A
        command stopped at a limit stops the shell, with every process in its group."""
        stdin, stdout = self.process.stdin, self.process.stdout
        assert stdin is not None and stdout is not None
        script = f"eval {_quoted(command)} </dev/null\nprintf '\\n%s %s\\n' {self.token} \"$?\"\n"
        received, self._pending = self._pending, bytearray()
        try:
            os.write(stdin.fileno(), script.encode())
        except BrokenPipeError:
            return Ran(_text(received, limit), stopped="ended")
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(stdout, selectors.EVENT_READ)
            while True:
                found = self._mark.search(received)
                if found is not None:
                    self._pending = received[found.end() :]
                    return Ran(_text(received[: found.start()], limit), int(found.group(1)))
                if len(received) > limit + len(self.token) + 32:
                    self.close()
                    return Ran(_text(received, limit), stopped="size")
                left = deadline - time.monotonic()
                if left <= 0:
                    self.close()
                    return Ran(_text(received, limit), stopped="time")
                if selector.select(left):
                    chunk = os.read(stdout.fileno(), 65536)
                    if not chunk:
                        self.close()
                        status = self.process.returncode
                        return Ran(_text(received, limit), status, stopped="ended")
                    received += chunk

    def close(self) -> None:
        """Stop the shell and every process left in its group. Its group is killed
        before the shell is waited for, so its id is no other group's yet."""
        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self.process.pid, signal.SIGKILL)
        for pipe in (self.process.stdin, self.process.stdout):
            if pipe is not None:
                with contextlib.suppress(OSError):
                    pipe.close()
        self.process.wait()

    def __enter__(self) -> Shell:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _text(received: bytes | bytearray, limit: int) -> str:
    return bytes(received[:limit]).decode("utf-8", errors="replace")


# --- the repository's guard ----------------------------------------------------------


Listing = dict[str, tuple[int, ...]]


def listing(root: Path) -> Listing:
    """Every path under `root` with what a write changes: a file's or a link's mode,
    size, modification and change times and inode, a folder's mode. The git directory
    is left out with what it holds. A folder holding a `.git` of its own, another
    repository, is listed but not what it holds, so a new one is seen. A linked
    worktree's `.git` file is listed."""
    found: Listing = {}
    for folder, folders, files in os.walk(root):
        here = Path(folder)
        listed = [name for name in folders if name != GIT_DIR]
        folders[:] = [name for name in listed if not (here / name / GIT_DIR).exists()]
        for name in (*listed, *files):
            path = here / name
            relative = path.relative_to(root).as_posix()
            try:
                status = path.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(status.st_mode):
                found[relative] = (status.st_mode,)
            else:
                found[relative] = (
                    status.st_mode,
                    status.st_size,
                    status.st_mtime_ns,
                    status.st_ctime_ns,
                    status.st_ino,
                )
    return found


def changed(before: Listing, after: Listing) -> list[str]:
    """The paths added, removed or changed between two listings."""
    paths = before.keys() | after.keys()
    return sorted(path for path in paths if before.get(path) != after.get(path))


class Guard:
    """The repository's listing, carried from each look to the next. So a write is seen
    whenever it lands: during a command, between two commands, or after a fence's last
    one, by a process a command left."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._last = listing(root)

    def wrote(self) -> list[str]:
        """The paths written in the repository since the last look."""
        now = listing(self.root)
        found = changed(self._last, now)
        self._last = now
        return found


def _shown_paths(paths: Sequence[str]) -> tuple[str, ...]:
    shown = [f"  {path}" for path in paths[:20]]
    if len(paths) > 20:
        shown.append(f"  and {len(paths) - 20} more")
    return tuple(shown)


# --- the scratch area ----------------------------------------------------------------


@dataclass(frozen=True)
class Scratch:
    """The run's scratch area, `base`: the scratch `project`, its `home` and `tmp`, and
    the project and the home as the setup left them, under `saved`."""

    base: Path

    @property
    def project(self) -> Path:
        return self.base / "project"

    @property
    def home(self) -> Path:
        return self.base / "home"

    @property
    def tmp(self) -> Path:
        return self.base / "tmp"

    @property
    def saved(self) -> Path:
        return self.base / "saved"

    def folders(self, root: Path) -> dict[str, Path]:
        """Each of the run's folders by its placeholder."""
        return {
            REPOSITORY: root,
            SCRATCH: self.base,
            PROJECT: self.project,
            HOME: self.home,
            TMP: self.tmp,
        }

    def make(self) -> None:
        for folder in (self.project, self.home, self.tmp):
            folder.mkdir()

    def save(self) -> None:
        """Keep the project and the home as the setup left them."""
        self.saved.mkdir()
        for folder in (self.project, self.home):
            shutil.copytree(folder, self.saved / folder.name, symlinks=True)

    def restore(self) -> None:
        """The project and the home as the setup left them, at the paths where they were
        built, and an empty temporary folder."""
        for folder in (self.project, self.home, self.tmp):
            _remove(folder)
        for folder in (self.project, self.home):
            shutil.copytree(self.saved / folder.name, folder, symlinks=True)
        self.tmp.mkdir()


def _remove(path: Path) -> None:
    """Remove `path` and what it holds, a folder a command left read-only included. A
    link is removed, never followed, and no mode is changed outside `path`."""
    top = os.path.normpath(path)
    tried: set[str] = set()

    def retry(_function: object, failed: str, *_rest: object) -> None:
        failed = os.path.normpath(failed)
        if failed in tried:
            return
        tried.add(failed)
        if failed != top:
            with contextlib.suppress(OSError):
                os.chmod(os.path.dirname(failed), 0o700)
        if os.path.isdir(failed) and not os.path.islink(failed):
            with contextlib.suppress(OSError):
                os.chmod(failed, 0o700)
            _rmtree(failed)
        else:
            with contextlib.suppress(OSError):
                os.unlink(failed)

    def _rmtree(folder: str) -> None:
        if sys.version_info >= (3, 12):
            shutil.rmtree(folder, onexc=retry)
        else:  # pragma: no cover - the interpreter the tests run on is newer
            shutil.rmtree(folder, onerror=retry)

    if path.is_symlink():
        path.unlink()
    elif path.exists():
        _rmtree(top)


def expanded(value: str, folders: Mapping[str, Path]) -> str:
    """`value` with each of the run's placeholders written as its folder."""
    for placeholder, folder in folders.items():
        value = value.replace(placeholder, str(folder))
    return value


def environment(
    selection: Selection,
    folders: Mapping[str, Path],
    caller: Mapping[str, str],
) -> dict[str, str]:
    """The whole environment every command runs with: the caller's `PATH` behind the
    folders the project names, the project's variables, and the settings the run fixes.
    Nothing else of the caller's reaches a command."""
    env: dict[str, str] = {}
    for name, value in selection.environment.items():
        if value is None:
            if name in caller:
                env[name] = caller[name]
        else:
            env[name] = expanded(value, folders)
    path = [expanded(entry, folders) for entry in selection.path]
    env.update(FIXED)
    env["HOME"] = str(folders[HOME])
    env["TMPDIR"] = str(folders[TMP])
    env["PATH"] = os.pathsep.join([*path, caller.get("PATH", os.defpath)])
    return env


def caller_values(selection: Selection, caller: Mapping[str, str]) -> dict[str, str]:
    """Each value a variable takes from the caller, by the placeholder it is written as:
    the variable's name in upper case. An empty value is written nowhere."""
    return {
        f"<{name.upper()}>": caller[name]
        for name, value in selection.environment.items()
        if value is None and caller.get(name)
    }


# --- the run -------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """What failed, at a page's line. `rewritable` when an update writes it right: a
    command that ran printed other output than the page shows."""

    path: str
    line: int
    message: str
    detail: tuple[str, ...] = ()
    rewritable: bool = False

    def render(self) -> str:
        return "\n".join([f"{self.path}:{self.line}: {self.message}", *self.detail])


@dataclass
class Report:
    pages: int = 0
    fences: int = 0
    commands: int = 0
    findings: list[Finding] = field(default_factory=list[Finding])
    notes: list[Finding] = field(default_factory=list[Finding])
    updated: list[str] = field(default_factory=list[str])
    stopped: bool = False


@dataclass(frozen=True)
class Limits:
    """Seconds a command of a page may run, and one of the setup step or a placeholder."""

    timeout: float = DEFAULT_TIMEOUT
    setup_timeout: float = DEFAULT_SETUP_TIMEOUT


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def _rewritten(lines: list[str], fence: Fence, outputs: Mapping[int, list[str]]) -> list[str]:
    """`lines` with the output of each command of `fence` that `outputs` names replaced,
    in the fence's quote and indent, the blank lines that ended it kept."""
    depth = fence.quote.count(">")
    body: list[str] = []
    for command in fence.commands:
        body.append(lines[command.index])
        own = lines[command.index + 1 : command.end]
        new = outputs.get(command.index)
        if new is None:
            body.extend(own)
            continue
        blank = 0
        while blank < len(own) and not (_unquoted(own[-1 - blank], depth) or "").strip():
            blank += 1
        body.extend(fence.written(line) for line in new)
        body.extend(own[len(own) - blank :])
    return [*lines[: fence.index + 1], *body, *lines[fence.end :]]


def run_pages(
    selection: Selection,
    paths: Sequence[str] | None = None,
    *,
    update: bool = False,
    limits: Limits | None = None,
    scratch_parent: Path | None = None,
    caller: Mapping[str, str] | None = None,
) -> Report:
    """Run every `console` fence of the pages at `paths`, by default every page the
    selection holds, and with `update` write the new output of each command whose output
    differs into its page, once every page's commands ran with no write in the
    repository. The scratch area is made under `scratch_parent`, the system's temporary
    folder by default, and the setup step runs only when a fence can run."""
    root = selection.root
    limits = Limits() if limits is None else limits
    caller = dict(os.environ) if caller is None else caller
    paths = list(selection.pages if paths is None else paths)
    report = Report(pages=len(paths))
    texts: dict[str, str] = {}
    for path in paths:
        try:
            texts[path] = read_page(root / path)
        except (OSError, UnicodeDecodeError) as exc:
            raise CannotRun(f"the page {path} cannot be read: {exc}") from exc
    runnable: dict[str, list[Fence]] = {}
    for path, text in texts.items():
        for fence in console_fences(text.split("\n"), path):
            if fence.language != LANGUAGE:
                report.notes.append(
                    Finding(
                        path,
                        fence.line,
                        f"a `{fence.language}` fence is a shell session no run checks: "
                        f"name it `{LANGUAGE}` to run it, or give it its shell's language",
                    )
                )
                continue
            report.fences += 1
            if fence.problem is None:
                runnable.setdefault(path, []).append(fence)
            else:
                report.findings.append(Finding(path, fence.line, fence.problem))
    if not runnable:
        return report
    written: dict[str, list[str]] = {}
    secrets = caller_values(selection, caller)
    scratch = Scratch(Path(tempfile.mkdtemp(prefix="doc-examples-", dir=scratch_parent)))
    try:
        if _inside(scratch.base, root):
            raise CannotRun(f"the scratch area {scratch.base} lies inside the repository")
        scratch.make()
        guard = Guard(root)
        run = _Run(selection, scratch, environment(selection, scratch.folders(root), caller))
        _setup(run, guard, limits, secrets)
        scratch.save()
        texts_of = _placeholders(run, guard, limits, secrets)
        texts_of.update(secrets)
        replace = substitutions(scratch.folders(root), texts_of)
        last = runnable[next(iter(runnable))][0]
        for path, fences in runnable.items():
            ran: list[tuple[Fence, dict[int, list[str]]]] = []
            for fence in fences:
                scratch.restore()
                last = fence
                outputs = _run_fence(run, guard, fence, replace, limits, report, secrets)
                if report.stopped:
                    return report
                ran.append((fence, outputs))
            if update and any(outputs for _fence, outputs in ran):
                lines = texts[path].split("\n")
                for fence, outputs in reversed(ran):
                    lines = _rewritten(lines, fence, outputs)
                written[path] = lines
    finally:
        _remove(scratch.base)
    late = guard.wrote()
    if late:
        _stop(report, last, f"a process the run left wrote in the repository after {_LAST}", late)
        return report
    for path, lines in written.items():
        try:
            now = read_page(root / path)
        except (OSError, UnicodeDecodeError):
            now = None
        if now != texts[path]:
            report.findings.append(
                Finding(
                    path,
                    1,
                    "the page changed while the run read it, so its new output is not written",
                )
            )
            continue
        (root / path).write_text("\n".join(lines), encoding="utf-8")
        report.updated.append(path)
    return report


@dataclass(frozen=True)
class _Run:
    """What every command of the run is started with: the selection, the scratch area,
    and the environment the run built."""

    selection: Selection
    scratch: Scratch
    env: Mapping[str, str]

    def given_repository(self) -> dict[str, str]:
        """The environment with the repository's path, as the setup step and the
        placeholders' commands are given it."""
        return {**self.env, REPOSITORY_VARIABLE: str(self.selection.root)}


#: Where a late write is said to land, in a finding.
_LAST = "its last command"


def _guarded(shell: Shell, guard: Guard, command: str, timeout: float) -> tuple[Ran, list[str]]:
    """Run `command` in `shell`, and the paths written in the repository since the last
    look, which are taken for the command's."""
    ran = shell.run(command, timeout)
    return ran, guard.wrote()


def _setup(run: _Run, guard: Guard, limits: Limits, secrets: Mapping[str, str]) -> None:
    """Build the scratch project: the setup step's commands, in order, in one shell, from
    the empty project folder. Raises CannotRun naming the command that failed, or a
    write in the repository, by a command or by a process one left."""
    if not run.selection.setup:
        return
    with Shell(run.scratch.project, run.given_repository()) as shell:
        for command in run.selection.setup:
            ran, wrote = _guarded(shell, guard, command, limits.setup_timeout)
            what = f"the setup step's command `{command}`"
            _refuse(what, ran, wrote, limits.setup_timeout, secrets)
    _refuse("a process the setup step left", Ran("", 0), guard.wrote(), 0, secrets)


def _placeholders(
    run: _Run, guard: Guard, limits: Limits, secrets: Mapping[str, str]
) -> dict[str, str]:
    """The text each of the project's placeholders stands for: the one line its command
    printed, run once in the scratch project after the setup step."""
    texts: dict[str, str] = {}
    for name, command in run.selection.placeholders.items():
        with Shell(run.scratch.project, run.given_repository()) as shell:
            ran, wrote = _guarded(shell, guard, command, limits.setup_timeout)
        what = f"the command of the placeholder `<{name}>`, `{command}`,"
        _refuse(what, ran, wrote + guard.wrote(), limits.setup_timeout, secrets)
        lines = ran.output.strip("\n").split("\n")
        if len(lines) != 1 or not lines[0].strip():
            printed = "more than one line" if len(lines) > 1 else "no text"
            raise CannotRun(f"{what} printed {printed}: a placeholder stands for one line")
        texts[f"<{name}>"] = lines[0].strip()
    return texts


def _masked(text: str, secrets: Mapping[str, str]) -> str:
    """`text` with each value a variable takes from the caller written as its
    placeholder, wherever it stands, and each control character escaped."""
    for placeholder, value in secrets.items():
        text = text.replace(value, placeholder)
    return _escaped(text)


def _escaped(text: str) -> str:
    """`text` with each control character an update never writes shown as an escape, so
    a report shows what a terminal would otherwise act on."""
    return CONTROL.sub(lambda found: repr(found.group())[1:-1], text)


def _refuse(
    what: str, ran: Ran, wrote: Sequence[str], timeout: float, secrets: Mapping[str, str]
) -> None:
    """Raise CannotRun when the command `what` names wrote in the repository, was
    stopped, or failed. What it printed is shown with the caller's values masked."""
    if wrote:
        raise CannotRun(f"{what} wrote in the repository:\n" + "\n".join(_shown_paths(wrote)))
    if ran.stopped is not None or ran.status != 0:
        why = {
            "time": f"ran longer than {timeout:g} seconds",
            "size": f"printed more than {OUTPUT_LIMIT} bytes",
        }.get(ran.stopped or "", f"exited {ran.status}")
        said = ran.output.strip().splitlines()[-20:]
        shown = "".join(f"\n  {_masked(line, secrets)}" for line in said)
        raise CannotRun(f"{what} {why}{shown}")


def _stop(report: Report, fence: Fence, what: str, wrote: Sequence[str]) -> None:
    """A write in the repository: a finding at `fence`, and the run stops."""
    report.findings.append(
        Finding(
            fence.path,
            fence.line,
            f"{what}, outside the scratch project; the run stops here",
            _shown_paths(wrote),
        )
    )
    report.stopped = True


def _run_fence(
    run: _Run,
    guard: Guard,
    fence: Fence,
    replace: Substitutions,
    limits: Limits,
    report: Report,
    secrets: Mapping[str, str],
) -> dict[int, list[str]]:
    """Run `fence`'s commands in order in one shell, adding a finding for each that
    fails; the output to write for each command whose output differs, by its prompt's
    index. A write in the repository stops the run, whether a command made it or a
    process the fence left made it before its shell was stopped."""
    outputs: dict[int, list[str]] = {}
    with Shell(run.scratch.project, run.env) as shell:
        for position, command in enumerate(fence.commands):
            report.commands += 1
            line = command.index + 1
            ran, wrote = _guarded(shell, guard, command.text, limits.timeout)
            if wrote:
                report.findings.append(
                    Finding(
                        fence.path,
                        line,
                        f"`{command.text}` wrote outside the scratch project, in the repository; "
                        "the run stops here",
                        _shown_paths(wrote),
                    )
                )
                report.stopped = True
                return outputs
            if ran.stopped in ("time", "size"):
                why = (
                    f"ran longer than {limits.timeout:g} seconds"
                    if ran.stopped == "time"
                    else f"printed more than {OUTPUT_LIMIT} bytes"
                )
                report.findings.append(
                    Finding(
                        fence.path,
                        line,
                        f"`{command.text}` {why}; the fence's later commands did not run",
                    )
                )
                break
            _compare(fence, command, ran, replace, report, outputs, secrets)
            if ran.stopped == "ended" and position + 1 < len(fence.commands):
                report.findings.append(
                    Finding(
                        fence.path,
                        line,
                        f"`{command.text}` ended the fence's shell; "
                        "the fence's later commands did not run",
                    )
                )
                break
    late = guard.wrote()
    if late:
        what = f"a process the fence left wrote in the repository after {_LAST}"
        _stop(report, fence, what, late)
    return outputs


def _compare(
    fence: Fence,
    command: Command,
    ran: Ran,
    replace: Substitutions,
    report: Report,
    outputs: dict[int, list[str]],
    secrets: Mapping[str, str],
) -> None:
    """Compare what `command` printed with the page. The report shows the difference
    with the caller's values masked wherever they stand, and its control characters
    escaped."""
    expected = compared(command.output)
    actual = normalised(ran.output, replace)
    if output_matches(expected, actual):
        return
    diff = difflib.unified_diff(expected, actual, "the page", "the run", lineterm="", n=2)
    unwritable = fence.unwritable(actual, tuple(secrets.values()))
    message = f"`{command.text}` printed other output than the page shows"
    if unwritable is not None:
        message += f"; `--update` leaves it, since {unwritable}"
    report.findings.append(
        Finding(
            fence.path,
            command.index + 1,
            message,
            tuple(f"  {_masked(row, secrets)}" for row in diff),
            rewritable=unwritable is None,
        )
    )
    if unwritable is None:
        outputs[command.index] = updated_output(expected, actual)


def render(report: Report) -> str:
    """The run's findings and notes, each at its page's line, then what it updated and a
    summary."""
    out = [note.render() for note in sorted(report.notes, key=lambda n: (n.path, n.line))]
    if not report.fences:
        out.append(f"No `{LANGUAGE}` fence in {report.pages} page(s).")
        return "\n".join(out) + "\n"
    findings = sorted(report.findings, key=lambda finding: (finding.path, finding.line))
    out.extend(finding.render() for finding in findings)
    out.extend(f"updated {path}: review its new output" for path in report.updated)
    if report.stopped:
        out.append(
            "stopped: a command wrote in the repository, no later fence ran, "
            "and no page was updated"
        )
    out.append(
        f"{report.commands} command(s) run, in {report.fences} fence(s) of "
        f"{report.pages} page(s): {len(report.findings) or 'no'} finding(s)"
    )
    return "\n".join(out) + "\n"


def exit_status(report: Report, *, update: bool) -> int:
    """0 when nothing failed, or when an update wrote every output that differed; 1
    otherwise."""
    if update and not report.stopped:
        return 1 if any(not finding.rewritable for finding in report.findings) else 0
    return 1 if report.findings else 0


def main(argv: Sequence[str] | None = None, cwd: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run-examples.py",
        description=(
            "Run each console example of the project's pages as a test, in a scratch "
            "project the project's setup step builds (doc-examples DEC-001)."
        ),
    )
    parser.add_argument("pages", nargs="*", metavar="PAGE", help="run only these pages")
    parser.add_argument(
        "--update", action="store_true", help="write each command's new output into its page"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"seconds a command of a page may run (default {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--setup-timeout",
        type=float,
        default=DEFAULT_SETUP_TIMEOUT,
        metavar="SECONDS",
        help=(
            "seconds a command of the setup step or of a placeholder may run "
            f"(default {DEFAULT_SETUP_TIMEOUT:g})"
        ),
    )
    args = parser.parse_args(argv)
    # The run's own lazy imports write no bytecode into the repository it watches.
    sys.dont_write_bytecode = True
    here = Path.cwd() if cwd is None else cwd
    try:
        selection = read_selection(here)
        named = [_named(page, here, selection.root) for page in args.pages]
        unknown = [page for page in named if page not in selection.pages]
        if unknown:
            raise CannotRun(f"not among the pages the run reads: {', '.join(unknown)}")
        report = run_pages(
            selection,
            named or None,
            update=args.update,
            limits=Limits(args.timeout, args.setup_timeout),
        )
    except CannotRun as exc:
        print(f"doc-examples: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(report))
    return exit_status(report, update=args.update)


def _named(page: str, here: Path, root: Path) -> str:
    """A page named on the command line, relative to the repository's root."""
    path = Path(page)
    if not path.is_absolute():
        path = here / path
    with contextlib.suppress(ValueError):
        return path.resolve().relative_to(root.resolve()).as_posix()
    return Path(page).as_posix()


def _terminated(signum: int, _frame: object) -> None:
    """End the run on SIGTERM or SIGHUP as on an interrupt: the shell running is stopped
    with its process group, and the scratch area is removed. The shell's group lies in a
    session of its own, so a closed terminal sends it no hangup of its own."""
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _terminated)
    signal.signal(signal.SIGHUP, _terminated)
    sys.exit(main())
