"""Run each `console` fence of project-kit's own pages as a test (#1807).

A page shows a command and what it prints in a `console` fence: each command
after the prompt `$ `, its output below it (living-docs DEC-002 point 6). The
output is produced by a run, never typed, and a runner of the project's own
runs it. This is project-kit's runner, the design note's decision 7, option A
(`.pkit/scratchpad/done/2026-10-18-visual-elements.md`).

- **Which pages:** every artefact of living-docs' page type, `living-docs:page`,
  as the backbone's discovery types it, wherever it lies: in a place
  `friction.places` declares with that type, or in one living-docs declares.
  The pages are selected by their type, never by a documentation root.
- **Which fences:** a fenced code block whose info string's first word is
  `console`. A fence in any other language is never run, so a command that
  cannot run as a test goes in a fence of its shell's language, such as `sh`.
- **How a fence reads:** a line that starts with `$ ` is a command, and the
  lines after it, up to the next command, are its output. A line before the
  first command, or a fence with no command, fails the fence.
- **Where a command runs:** in a scratch project, never in the repository. The
  run builds one project, with project-kit installed from this checkout and
  committed, the first time a page holds a fence. Each fence runs in a copy of
  it, with a home and a temporary directory of its own, so no fence finds in its
  own area what another left. Each command runs on its own in `/bin/sh`, from
  the project's root, with its input closed. A `cd` or a variable does not
  carry over to the next command, and what a command writes in the project does.
- **What it is given:** an environment the run builds, with nothing of the
  caller's but `PATH`, behind this checkout's interpreter folder, so `pkit` is
  this checkout's. `HOME`, `TMPDIR` and the XDG folders lie in the fence's
  scratch area, git reads only the scratch home's configuration, which signs
  nothing and allows no SSH, and uv's cache is the run's own. So the run fetches
  what uv needs once, from the network.
- **What it is not:** a confinement. A command runs as the caller, and can read
  whatever the caller can, such as the caller's SSH configuration and keys, or
  on Linux the environment of the processes that started the run.
- **The limits:** a command that runs longer than `--timeout` seconds, or
  prints more than `OUTPUT_LIMIT` bytes, is stopped with every process left in
  its process group, and fails its fence. So does one that leaves a process
  holding its output. An interrupted run stops the command it is running.
- **What is compared:** what the command printed, its standard output and error
  together as a terminal shows them, with the page's output. The exit status
  is not compared. The spaces that end a line and the blank lines that end an
  output are left out on both sides.
- **Output that varies:** before comparing, the run writes `<project>`, `<home>`,
  `<tmp>` and `<repository>` for those folders' paths, and `<version>` for
  project-kit's version. In the page's output, `<any>` stands for any text within
  one line.
- **`--update`:** writes each command's output into its page where they differ,
  keeping each line of the page's that still matches, `<any>` included. A person
  reviews the new output like any change to the page (DEC-002 point 6). Output
  with a line that would read as a command or close the fence is never written,
  so nothing a command prints becomes a command of the next run.
- **A write outside the scratch area:** the run lists every file in the
  repository, with its size, times, mode and inode, and every folder, with its
  mode, before and after each command. A path added, removed or changed fails
  the test, and stops the run. The git index is left out, since any `git status`
  rewrites it. A folder that holds a repository of its own, such as a linked
  worktree, is not listed.

What it cannot detect: a write anywhere but the repository, such as in the
caller's home or the system's temporary folder by an absolute path, or in the
git directory a linked worktree shares, which lies outside the worktree. Nor a
change to the git index alone, a write undone before the command ends, a
process that leaves its process group and writes later, or anything the network
does. A write by another process at the same time it takes for the command's.
Nothing confines a command: the run detects, it does not prevent.

From the repository root:

    uv run python scripts/console_fences.py               # every page
    uv run python scripts/console_fences.py README.md     # one page
    uv run python scripts/console_fences.py --update      # write new output

Exit 0 when every fence matches, or no page holds one. Exit 1 when a fence
fails, and 2 when the run cannot start: no page can be read, a path named is
no page, or the scratch project cannot be built.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import functools
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from project_kit import friction_discovery, validators

ROOT = Path(__file__).resolve().parents[1]

#: living-docs' page type (COR-056): the pages this runner reads.
PAGE_TYPE = "living-docs:page"
#: The info string's first word that makes a fence a shell session to run.
LANGUAGE = "console"
PROMPT = "$ "
#: In a page's output, any text within one line.
ANY = "<any>"
#: Seconds a command may run.
DEFAULT_TIMEOUT = 60.0
#: Bytes a command may print.
OUTPUT_LIMIT = 1 << 20
#: Seconds each step of building the scratch project may run.
BUILD_TIMEOUT = 600.0
#: Paths in the repository that change without a write of the command's.
UNWATCHED = frozenset({".git/index"})

GITCONFIG = """\
[user]
\tname = Console Fences
\temail = console-fences@example.invalid
[init]
\tdefaultBranch = main
[commit]
\tgpgsign = false
[tag]
\tgpgsign = false
[protocol "ssh"]
\tallow = never
"""

_OPENING = re.compile(r"^(?P<indent> *)(?P<mark>`{3,}|~{3,})(?P<info>.*)$")


class CannotRun(Exception):
    """The run cannot start, or its scratch project cannot be built."""


# --- reading a page ------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    """One command of a fence: the prompt's line `index` in the page, the command's
    `text`, the `output` the page shows, the fence's indent removed, and `end`, the
    index of the line after its output."""

    index: int
    text: str
    output: tuple[str, ...]
    end: int


@dataclass(frozen=True)
class Fence:
    """A `console` fence of the page at `path`: the opening line's `index`, the
    `indent` its lines carry, `end`, the closing line's index, and its commands, or
    the `problem` that keeps it from running. `mark` is the opening's run of
    backticks or tildes."""

    path: str
    index: int
    indent: int
    end: int
    commands: tuple[Command, ...]
    problem: str | None = None
    mark: str = "```"

    @property
    def line(self) -> int:
        return self.index + 1

    def reads_as_markup(self, line: str) -> bool:
        """Whether `line`, written as output in this fence, would read as a command or
        close the fence."""
        if line.startswith(PROMPT) or line.rstrip() == PROMPT.rstrip():
            return True
        return _closing(self.mark).match(line) is not None


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


def _dedent(line: str, indent: int) -> str:
    """`line` with up to `indent` leading spaces removed, as a fence's content is."""
    spaces = len(line) - len(line.lstrip(" "))
    return line[min(spaces, indent) :]


def console_fences(lines: Sequence[str], path: str) -> list[Fence]:
    """Every `console` fence of a page's `lines`, in order. A fence of another
    language is passed over whole, so a `console` fence quoted inside it is not one."""
    found: list[Fence] = []
    index = _body_start(lines)
    while index < len(lines):
        opening = _OPENING.match(lines[index])
        if opening is None or (opening["mark"][0] == "`" and "`" in opening["info"]):
            index += 1
            continue
        mark = opening["mark"]
        closing = _closing(mark)
        end = next(
            (later for later in range(index + 1, len(lines)) if closing.match(lines[later])),
            len(lines),
        )
        words = opening["info"].split()
        if words and words[0] == LANGUAGE:
            found.append(_fence(lines, path, index, len(opening["indent"]), end, mark))
        index = end + 1
    return found


def _fence(lines: Sequence[str], path: str, index: int, indent: int, end: int, mark: str) -> Fence:
    commands: list[Command] = []
    problem: str | None = None
    prompt: tuple[int, str] | None = None
    output: list[str] = []
    for at in range(index + 1, end):
        line = _dedent(lines[at], indent)
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
    return Fence(path, index, indent, end, tuple(commands), problem, mark)


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


Substitutions = Sequence[tuple[re.Pattern[str], str]]


def substitutions(
    paths: Mapping[str, Path], version: str | None
) -> list[tuple[re.Pattern[str], str]]:
    """The placeholder each path stands for, as written and resolved, and `<version>`
    for `version`: the longest text first, so no path is replaced inside a longer one."""
    texts: dict[str, str] = {}
    for placeholder, path in paths.items():
        for form in (str(path), str(path.resolve())):
            texts[form] = placeholder
    pairs = [(re.escape(text), placeholder) for text, placeholder in texts.items()]
    if version:
        pairs.append((rf"(?<![\d.]){re.escape(version)}(?!\d|\.\d)", "<version>"))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return [(re.compile(pattern), placeholder) for pattern, placeholder in pairs]


def normalised(output: str, replace: Substitutions) -> list[str]:
    """A command's output as it is compared, its varying parts replaced."""
    text = output.replace("\r\n", "\n")
    for pattern, placeholder in replace:
        text = pattern.sub(placeholder, text)
    return compared(text.split("\n"))


# --- the scratch area ----------------------------------------------------------------


@dataclass(frozen=True)
class Scratch:
    """Where a fence's commands run: the `project`, and the `home` and `tmp` they get."""

    project: Path
    home: Path
    tmp: Path

    @classmethod
    def made(cls, base: Path) -> Scratch:
        scratch = cls(base / "project", base / "home", base / "tmp")
        for folder in (scratch.home, scratch.tmp):
            folder.mkdir(parents=True)
        (scratch.home / ".gitconfig").write_text(GITCONFIG, encoding="utf-8")
        return scratch


def environment(scratch: Scratch, uv_cache: Path, bin_dir: Path) -> dict[str, str]:
    """The whole environment a command runs with: the caller's `PATH` behind
    `bin_dir`, and nothing else of the caller's."""
    home = scratch.home
    return {
        "PATH": os.pathsep.join([str(bin_dir), os.environ.get("PATH", os.defpath)]),
        "HOME": str(home),
        "TMPDIR": str(scratch.tmp),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "UV_CACHE_DIR": str(uv_cache),
        "UV_PYTHON_DOWNLOADS": "never",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "PKIT_NO_ROUTE": "1",
    }


Builder = Callable[[Path, Mapping[str, str]], None]


def build_project(project: Path, env: Mapping[str, str]) -> None:
    """Make `project` a repository with project-kit installed from this checkout, the
    install committed. Raises CannotRun naming the step that failed."""
    project.mkdir(parents=True)
    steps = (
        ["git", "init", "-q"],
        ["pkit", "init", "--root", str(project)],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "Install project-kit"],
    )
    for step in steps:
        try:
            done = subprocess.run(
                step,
                cwd=project,
                env=dict(env),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=BUILD_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CannotRun(
                f"the scratch project cannot be built: `{' '.join(step)}`: {exc}"
            ) from exc
        if done.returncode != 0:
            said = (done.stdout + done.stderr).strip().splitlines()[-20:]
            raise CannotRun(
                f"the scratch project cannot be built: `{' '.join(step)}` exited "
                f"{done.returncode}:\n" + "\n".join(f"  {line}" for line in said)
            )


# --- running a command -----------------------------------------------------------------


@dataclass(frozen=True)
class Ran:
    """What a command printed, at most `OUTPUT_LIMIT` bytes of it, and why the run
    stopped it, if it did: `time` or `size`."""

    output: str
    stopped: str | None = None


def _stop_group(group: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(group, signal.SIGKILL)


def _ended(process: subprocess.Popen[bytes]) -> bool:
    """Whether `process` has ended. On Linux it is left unreaped, so its id cannot yet
    be another process group's. Elsewhere it is reaped, since macOS has `waitid`
    only from Python 3.13: the moment until its group is killed is left open."""
    if sys.platform == "linux":
        flags = os.WEXITED | os.WNOHANG | os.WNOWAIT
        return os.waitid(os.P_PID, process.pid, flags) is not None
    return process.poll() is not None


def run_command(
    command: str, cwd: Path, env: Mapping[str, str], timeout: float, limit: int = OUTPUT_LIMIT
) -> Ran:
    """Run `command` in `/bin/sh` from `cwd`, in a process group of its own, with its
    input closed, for at most `timeout` seconds and `limit` bytes of output.

    However it ends, timed out, too long, done, or the run interrupted, its process
    group is killed, so whatever it left running in the group stops. A process that
    left the group and holds the output is left behind once the time is up."""
    process = subprocess.Popen(
        ["/bin/sh", "-c", command],
        cwd=cwd,
        env=dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pipe = process.stdout
    assert pipe is not None
    received = bytearray()
    stopped: str | None = None
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(pipe, selectors.EVENT_READ)
            while stopped is None:
                left = deadline - time.monotonic()
                if left <= 0:
                    stopped = "time"
                elif selector.select(left):
                    chunk = os.read(pipe.fileno(), 65536)
                    if not chunk:
                        break
                    received += chunk
                    if len(received) > limit:
                        stopped = "size"
        pause = 0.005
        while stopped is None and not _ended(process):
            if time.monotonic() >= deadline:
                stopped = "time"
            else:
                time.sleep(pause)
                pause = min(pause * 2, 0.05)
    finally:
        _stop_group(process.pid)
        pipe.close()
        process.wait()
    return Ran(bytes(received[:limit]).decode("utf-8", errors="replace"), stopped)


Listing = dict[str, tuple[int, ...]]


def listing(root: Path) -> Listing:
    """Every path under `root` with what a write changes: a file's or a link's mode,
    size, modification and change times and inode, a folder's mode. A folder holding a
    `.git` of its own is another repository, and is left out with what it holds."""
    found: Listing = {}
    for folder, folders, files in os.walk(root):
        here = Path(folder)
        folders[:] = [name for name in folders if not (here / name / ".git").exists()]
        for name in (*folders, *files):
            path = here / name
            relative = path.relative_to(root).as_posix()
            if relative in UNWATCHED:
                continue
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


# --- the run -------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """What failed, at a page's line. `rewritable` when `--update` writes it right: a
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
    updated: list[str] = field(default_factory=list[str])
    stopped: bool = False


def pages(root: Path) -> list[str]:
    """The paths of every artefact living-docs' page type types, or counts as in a tie,
    as the backbone's discovery reads them. Raises CannotRun when the configuration
    cannot be read."""
    problem = friction_discovery.unreadable_configuration(root)
    if problem is not None:
        raise CannotRun(f"{problem}; `pkit validate` reports it")
    discovery = validators.as_one_run(lambda: friction_discovery.discover_artefacts(root))
    types = discovery.types
    return sorted(
        {
            artefact.path
            for artefact in discovery.artefacts
            if artefact.kind is friction_discovery.ArtefactKind.DOCUMENT
            and PAGE_TYPE in types.of(artefact).counts_as
        }
    )


def _version(root: Path) -> str | None:
    try:
        return (root / ".pkit" / "VERSION").read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def _rewritten(lines: list[str], fence: Fence, outputs: Mapping[int, list[str]]) -> list[str]:
    """`lines` with the output of each command of `fence` that `outputs` names replaced,
    in the fence's indent, the blank lines that ended it kept."""
    body: list[str] = []
    for command in fence.commands:
        body.append(lines[command.index])
        own = lines[command.index + 1 : command.end]
        new = outputs.get(command.index)
        if new is None:
            body.extend(own)
            continue
        blank = len(own) - len(compared(own))
        body.extend(" " * fence.indent + line if line else "" for line in new)
        body.extend([""] * blank)
    return [*lines[: fence.index + 1], *body, *lines[fence.end :]]


def run_pages(
    root: Path,
    paths: Sequence[str],
    *,
    update: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    build: Builder = build_project,
    bin_dir: Path | None = None,
    scratch_parent: Path | None = None,
) -> Report:
    """Run every `console` fence of the pages at `paths`, relative to `root`, and with
    `update` write the new output of each command whose output differs into its page.
    The scratch area is made under `scratch_parent`, the system's temporary folder by
    default, and the scratch project built in it by `build` only when a fence can run."""
    report = Report(pages=len(paths))
    texts: dict[str, str] = {}
    for path in paths:
        try:
            texts[path] = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CannotRun(f"the page {path} cannot be read: {exc}") from exc
    runnable: dict[str, list[Fence]] = {}
    for path, text in texts.items():
        for fence in console_fences(text.split("\n"), path):
            report.fences += 1
            if fence.problem is None:
                runnable.setdefault(path, []).append(fence)
            else:
                report.findings.append(Finding(path, fence.line, fence.problem))
    if not runnable:
        return report
    bin_dir = bin_dir if bin_dir is not None else Path(sys.executable).parent
    run_dir = Path(tempfile.mkdtemp(prefix="pkit-console-fences-", dir=scratch_parent))
    try:
        if _inside(run_dir, root):
            raise CannotRun(f"the scratch area {run_dir} lies inside the repository")
        uv_cache = run_dir / "uv-cache"
        template = Scratch.made(run_dir / "build")
        build(template.project, environment(template, uv_cache, bin_dir))
        version = _version(root)
        for number, (path, fences) in enumerate(runnable.items(), 1):
            ran: list[tuple[Fence, dict[int, list[str]]]] = []
            for count, fence in enumerate(fences, 1):
                scratch = Scratch.made(run_dir / f"page-{number}-fence-{count}")
                shutil.copytree(template.project, scratch.project, symlinks=True)
                placeholders = {
                    "<repository>": root,
                    "<project>": scratch.project,
                    "<home>": scratch.home,
                    "<tmp>": scratch.tmp,
                }
                outputs = _run_fence(
                    root,
                    fence,
                    scratch,
                    environment(scratch, uv_cache, bin_dir),
                    substitutions(placeholders, version),
                    timeout,
                    report,
                )
                if report.stopped:
                    return report
                ran.append((fence, outputs))
            if update and any(outputs for _fence, outputs in ran):
                lines = texts[path].split("\n")
                for fence, outputs in reversed(ran):
                    lines = _rewritten(lines, fence, outputs)
                (root / path).write_text("\n".join(lines), encoding="utf-8")
                report.updated.append(path)
        return report
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def _run_fence(
    root: Path,
    fence: Fence,
    scratch: Scratch,
    env: Mapping[str, str],
    replace: Substitutions,
    timeout: float,
    report: Report,
) -> dict[int, list[str]]:
    """Run `fence`'s commands in order, adding a finding for each that fails; the
    output to write for each command whose output differs, by its prompt's index."""
    outputs: dict[int, list[str]] = {}
    before = listing(root)
    for command in fence.commands:
        report.commands += 1
        line = command.index + 1
        ran = run_command(command.text, scratch.project, env, timeout)
        after = listing(root)
        written = changed(before, after)
        before = after
        if written:
            shown = [f"  {path}" for path in written[:20]]
            if len(written) > 20:
                shown.append(f"  and {len(written) - 20} more")
            report.findings.append(
                Finding(
                    fence.path,
                    line,
                    f"`{command.text}` wrote outside the scratch project, in the repository; "
                    "the run stops here",
                    tuple(shown),
                )
            )
            report.stopped = True
            return outputs
        if ran.stopped is not None:
            why = (
                f"ran longer than {timeout:g} seconds, or left a process holding its output"
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
            return outputs
        expected = compared(command.output)
        actual = normalised(ran.output, replace)
        if output_matches(expected, actual):
            continue
        diff = difflib.unified_diff(expected, actual, "the page", "the run", lineterm="", n=2)
        rewritable = not any(fence.reads_as_markup(row) for row in actual)
        message = f"`{command.text}` printed other output than the page shows"
        if not rewritable:
            message += (
                "; `--update` leaves it, since a line of it would read as a command "
                "or close the fence"
            )
        report.findings.append(
            Finding(
                fence.path,
                line,
                message,
                tuple(f"  {row}" for row in diff),
                rewritable=rewritable,
            )
        )
        if rewritable:
            outputs[command.index] = updated_output(expected, actual)
    return outputs


def render(report: Report) -> str:
    """The run's findings, each at its page's line, then what it updated and a summary."""
    if not report.fences:
        return f"No `console` fence in {report.pages} page(s).\n"
    findings = sorted(report.findings, key=lambda finding: (finding.path, finding.line))
    out = [finding.render() for finding in findings]
    out.extend(f"updated {path}: review its new output" for path in report.updated)
    if report.stopped:
        out.append("stopped: a command wrote in the repository, and no later fence ran")
    out.append(
        f"{report.commands} command(s) run, in {report.fences} fence(s) of "
        f"{report.pages} page(s): {len(report.findings) or 'no'} finding(s)"
    )
    return "\n".join(out) + "\n"


def exit_status(report: Report, *, update: bool) -> int:
    """0 when nothing failed, or when `--update` wrote every output that differed; 1
    otherwise."""
    if update and not report.stopped:
        return 1 if any(not finding.rewritable for finding in report.findings) else 0
    return 1 if report.findings else 0


def main(argv: Sequence[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(
        prog="console_fences.py",
        description="Run each `console` fence of project-kit's pages as a test.",
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
        help=f"seconds a command may run (default {DEFAULT_TIMEOUT:g})",
    )
    args = parser.parse_args(argv)
    # The run's own lazy imports write no bytecode into the repository it watches.
    sys.dont_write_bytecode = True
    try:
        every = pages(root)
        named = [Path(page).as_posix() for page in args.pages]
        unknown = [page for page in named if page not in every]
        if unknown:
            raise CannotRun(f"no artefact typed {PAGE_TYPE}: {', '.join(unknown)}")
        report = run_pages(root, named or every, update=args.update, timeout=args.timeout)
    except CannotRun as exc:
        print(f"console fences: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(report))
    return exit_status(report, update=args.update)


def _terminated(signum: int, _frame: object) -> None:
    """End the run on SIGTERM as on an interrupt: the command running is stopped with
    its process group, and the scratch area is removed."""
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _terminated)
    sys.exit(main())
