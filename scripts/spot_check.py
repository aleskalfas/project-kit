"""Planted-bug spot-check: do a module's new tests catch every bug its old tests caught?

A change may convert tests that start a process into tests that call the code
in their own process, as #2313's slices did (`tests/README.md`, "Running the suite"). It proves the
conversion lost no check this way. It plants bugs in the code the tests cover, one
at a time. On each, it runs the tests as they were at a base commit, and as they
are now. Every bug an old test caught must be caught by a new test.

Usage:
  uv run python scripts/spot_check.py BUGS --base REF [--old-path DIR]... [--old-helper FILE]...
      [--workers N] TEST...

BUGS is a JSON file: a list of bugs, each `{"id", "file", "find", "replace"}`.
`find` must appear exactly once in `file`, a path from the repository root. Each
TEST is a test module, or one test of it (`path::name`), as the working tree
holds it. Its old version is `git show REF:path`, written beside it for the run as
`_spot_old_<module>.py` and removed after. `--old-path` puts a folder on the
import path of the old run alone, for an old module that loads a capability's
`_lib` modules by their files. `--old-helper` puts a module the tests import, a
path from the repository root, at its version at REF in its own place for the old
run alone, for a change that converted a helper the old tests share. A test
counts a bug as caught when it fails. An error in its setting-up or tearing-down,
such as the process guard's, does not count. The planted file and each helper are
put back after each run, whatever happens.

Exit codes:
  0  every bug some old test caught, some new test caught too
  1  a bug the old tests caught, the new tests missed
  2  a usage error, a bug that cannot be planted, a run that could not be read, or
     tests that fail before any bug is planted
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
#: What the old version of a test module is called, beside the new one, for the run.
OLD_PREFIX = "_spot_old_"


class Refused(Exception):
    """The spot-check cannot run; the message says why."""


@dataclass(frozen=True)
class Bug:
    """One bug to plant: `find` replaced by `replace` in `file`."""

    id: str
    file: str
    find: str
    replace: str


def read_bugs(text: str, root: Path = REPO) -> list[Bug]:
    """The bugs a BUGS file lists, each checked to be plantable as written."""
    bugs = [Bug(**entry) for entry in json.loads(text)]
    if not bugs:
        raise Refused("the file lists no bug")
    for bug in bugs:
        path = root / bug.file
        if not path.is_file():
            raise Refused(f"bug {bug.id}: {bug.file} is not a file")
        found = path.read_text(encoding="utf-8").count(bug.find)
        if found != 1:
            raise Refused(f"bug {bug.id}: its text appears {found} time(s) in {bug.file}, not once")
    return bugs


def old_name(test: str) -> str:
    """The node id of `test` in its module's old version."""
    path, _, name = test.partition("::")
    old = Path(path).with_name(f"{OLD_PREFIX}{Path(path).name}").as_posix()
    return f"{old}::{name}" if name else old


def failures(junit: str) -> set[str]:
    """The tests a run's JUnit report says failed: each a failure in the test itself."""
    root = ElementTree.fromstring(junit)
    return {
        f"{case.get('classname')}::{case.get('name')}"
        for case in root.iter("testcase")
        if case.find("failure") is not None
    }


@dataclass(frozen=True)
class Verdict:
    """What the old and the new tests caught of one bug."""

    bug: str
    old: int
    new: int

    @property
    def lost(self) -> bool:
        """The old tests caught it and the new ones did not."""
        return self.old > 0 and self.new == 0


@contextmanager
def planted(bug: Bug, root: Path = REPO) -> Iterator[None]:
    """`bug` planted in its file for the block, the file put back after, whatever happens."""
    path = root / bug.file
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(bug.find, bug.replace, 1), encoding="utf-8")
    try:
        yield
    finally:
        path.write_text(text, encoding="utf-8")


def shown(base: str, path: str, root: Path = REPO) -> str:
    """The file at `path` as `base` holds it. Refused when it holds none."""
    done = subprocess.run(
        ["git", "show", f"{base}:{path}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise Refused(f"{base} holds no {path}: {done.stderr.strip()}")
    return done.stdout


@contextmanager
def old_modules(tests: Sequence[str], base: str, root: Path = REPO) -> Iterator[None]:
    """Each test module's version at `base`, written beside it for the block."""
    written: list[Path] = []
    try:
        for module in sorted({test.partition("::")[0] for test in tests}):
            path = root / old_name(module)
            path.write_text(shown(base, module, root), encoding="utf-8")
            written.append(path)
        yield
    finally:
        for path in written:
            path.unlink(missing_ok=True)


@contextmanager
def old_helpers(helpers: Sequence[str], base: str, root: Path = REPO) -> Iterator[None]:
    """Each helper module at its version at `base`, in its own place for the block, and
    put back after, whatever happens."""
    kept: dict[Path, str] = {}
    try:
        for helper in helpers:
            old = shown(base, helper, root)
            path = root / helper
            kept[path] = path.read_text(encoding="utf-8")
            path.write_text(old, encoding="utf-8")
        yield
    finally:
        for path, text in kept.items():
            path.write_text(text, encoding="utf-8")


def run(tests: Sequence[str], workers: int, env: Mapping[str, str], root: Path = REPO) -> set[str]:
    """The tests that fail in one run of `tests`. Refused when the run could not be read:
    the tests could not be collected, or pytest stopped. Its report is kept in the agent
    workspace while it is read."""
    workspace = root / ".agent-workspace"
    workspace.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spot-check-", dir=workspace) as d:
        report = Path(d) / "report.xml"
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-n",
                str(workers),
                f"--junitxml={report}",
                *tests,
            ],
            cwd=root,
            env=dict(env),
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode not in (0, 1) or not report.is_file():
            tail = "\n".join(done.stdout.splitlines()[-15:])
            raise Refused(f"the run of {' '.join(tests)} exited {done.returncode}:\n{tail}")
        return failures(report.read_text(encoding="utf-8"))


def spot_check(
    bugs: Sequence[Bug],
    tests: Sequence[str],
    *,
    base: str,
    old_path: Sequence[str] = (),
    old_helper: Sequence[str] = (),
    workers: int = 4,
    say: Callable[[str], None] = print,
) -> list[Verdict]:
    """Run the old and the new `tests` with no bug, then on each bug. Refused when they
    fail before any bug is planted."""
    new_env = dict(os.environ)
    old_env = dict(os.environ)
    if old_path:
        paths = [str(REPO / p) for p in old_path]
        old_env["PYTHONPATH"] = os.pathsep.join([*paths, os.environ.get("PYTHONPATH", "")])
    olds = [old_name(test) for test in tests]

    def old_run() -> set[str]:
        with old_helpers(old_helper, base):
            return run(olds, workers, old_env)

    verdicts: list[Verdict] = []
    with old_modules(tests, base):
        before = old_run(), run(tests, workers, new_env)
        if any(before):
            raise Refused(f"tests fail before any bug is planted: {sorted(set().union(*before))}")
        for bug in bugs:
            with planted(bug):
                verdict = Verdict(bug.id, len(old_run()), len(run(tests, workers, new_env)))
            say(f"{bug.id}: {verdict.old} old test(s) caught it, {verdict.new} new test(s)")
            verdicts.append(verdict)
    return verdicts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spot_check.py",
        description="Plant bugs one at a time, and say whether the new tests catch every bug "
        "the old tests caught.",
    )
    parser.add_argument("bugs", type=Path, help="the JSON file listing the bugs to plant")
    parser.add_argument("tests", nargs="+", help="test modules, or tests, as now")
    parser.add_argument("--base", required=True, help="the commit that holds the old tests")
    parser.add_argument("--old-path", action="append", default=[], help="import path, old run")
    parser.add_argument(
        "--old-helper", action="append", default=[], help="a helper module at REF, old run"
    )
    parser.add_argument("--workers", type=int, default=4, help="pytest-xdist workers per run")
    args = parser.parse_args(argv)
    try:
        bugs = read_bugs(args.bugs.read_text(encoding="utf-8"))
        verdicts = spot_check(
            bugs,
            args.tests,
            base=args.base,
            old_path=args.old_path,
            old_helper=args.old_helper,
            workers=args.workers,
        )
    except (Refused, OSError, ValueError, TypeError) as exc:
        print(f"spot-check refused: {exc}", file=sys.stderr)
        return 2
    lost = [v.bug for v in verdicts if v.lost]
    caught = sum(1 for v in verdicts if v.old > 0)
    missed = ", ".join(lost) or "none"
    print(f"the old tests caught {caught} of {len(verdicts)} bug(s); the new tests missed {missed}")
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
