"""A temporary *adopter repository* for tests (#980).

A real `git init`ed directory with the backbone installed through
`project_kit.install.install_kit`, optionally chosen capabilities installed
through `project_kit.capabilities`, and — on request — a scripted commit
history (initial commit, a `git mv` rename, a squash-style merge) that later
work such as the friction engine (COR-050) can trace front-matter changes
across.

Three layers:

- `GitRepo` — git plumbing only: init, commit arbitrary edits with a
  controllable author/date, rename, branch, merge, squash-merge, read SHAs.
  Usable on its own for tests whose repo is not an adopter (e.g. a synthetic
  source kit).
- `AdopterRepo` — a `GitRepo` whose root carries an installed `.pkit/`, plus
  capability installation and the scripted `history`.
- `AdopterTemplates` — each shape of adopter built once per test session and
  copied for every test that asks for it (#1204).

The pytest fixtures (`make_adopter_repo`, `adopter_repo`) live in
`tests/conftest.py` and hand out copies of the templates, or call
`build_adopter_repo` below for a fresh build. See `tests/README.md` for when to
reach for which.
"""

from __future__ import annotations

import contextlib
import ctypes
import fcntl
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from project_kit import capabilities as caps
from project_kit import install as install_mod

# --- git plumbing ------------------------------------------------------------


@dataclass(frozen=True)
class Author:
    """A commit identity; rendered into the `GIT_*_NAME` / `GIT_*_EMAIL` env."""

    name: str
    email: str


DEFAULT_AUTHOR = Author(name="pkit-test", email="pkit-test@example.com")

# Scripted-history commits are spaced a day apart from this instant so their
# order is unambiguous however git sorts them.
HISTORY_EPOCH = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class GitRepo:
    """Thin wrapper over a git working tree rooted at `root`.

    Every mutating method returns the SHA of the commit it produced so tests
    can assert against exact commits rather than positions in a log.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def init(cls, root: Path, *, branch: str = "main") -> GitRepo:
        """`git init` at `root` with a local identity and signing off, so commits
        succeed regardless of the developer's global git config."""
        root.mkdir(parents=True, exist_ok=True)
        repo = cls(root)
        repo.git("init", "-q", f"--initial-branch={branch}")
        repo.git("config", "user.name", DEFAULT_AUTHOR.name)
        repo.git("config", "user.email", DEFAULT_AUTHOR.email)
        repo.git("config", "commit.gpgsign", "false")
        # No automatic maintenance: a commit would otherwise detach `gc --auto`,
        # whose writes under .git (info/refs, objects/info/packs, the multi-pack
        # index) land at any later moment and break a byte-for-byte reading of
        # the repository (#1065). Set from the first commit, so nothing is ever
        # in flight.
        repo.git("config", "gc.auto", "0")
        repo.git("config", "maintenance.auto", "false")
        return repo

    def git(
        self,
        *args: str,
        check: bool = True,
        author: Author | None = None,
        date: datetime | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run `git <args>` in the repo. `author` / `date` set both the author
        and committer identity / timestamp for that one invocation."""
        env = _identity_env(author, date)
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=check,
            capture_output=True,
            text=True,
            env=env,
        )

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").stdout.strip()

    def lose_object(self, sha: str) -> None:
        """Take the loose object `sha` out of the object store: what names it still
        does, and git can no longer read it — history that exists and cannot be read,
        whatever the machine's git configuration. Commits made here stay loose
        (`gc.auto` is off)."""
        path = self.root / ".git" / "objects" / sha[:2] / sha[2:]
        path.chmod(0o644)
        path.unlink()

    def current_branch(self) -> str:
        """The checked-out branch name; works on an unborn branch too."""
        return self.git("symbolic-ref", "--short", "HEAD").stdout.strip()

    def shas(
        self, path: str | None = None, *, follow: bool = False, rev: str = "HEAD"
    ) -> list[str]:
        """Commit SHAs reaching `rev`, newest first; optionally restricted to
        `path` (with `--follow` to trace it across renames)."""
        args = ["log", "--format=%H", rev]
        if follow:
            args.append("--follow")
        if path is not None:
            args += ["--", path]
        out = self.git(*args).stdout.split()
        return out

    def write(self, files: Mapping[str, str | None]) -> None:
        """Write (`str`) or delete (`None`) each `path -> content` under the root
        without staging anything."""
        for rel, content in files.items():
            path = self.root / rel
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

    def commit(
        self,
        message: str,
        files: Mapping[str, str | None] | None = None,
        *,
        author: Author | None = None,
        date: datetime | None = None,
    ) -> str:
        """Apply `files` (see `write`) and commit them. With `files=None` every
        change in the working tree is staged (`git add -A`) instead. Returns the
        new commit's SHA."""
        if files is None:
            self.git("add", "-A")
        else:
            self.write(files)
            self.git("add", "-A", "--", *files.keys())
        self.git("commit", "-q", "-m", message, author=author, date=date)
        return self.head()

    def rename(
        self,
        src: str,
        dst: str,
        message: str | None = None,
        *,
        author: Author | None = None,
        date: datetime | None = None,
    ) -> str:
        """`git mv src dst` and commit it; a pure rename so `--follow` sees
        identical content on both sides."""
        (self.root / dst).parent.mkdir(parents=True, exist_ok=True)
        self.git("mv", src, dst)
        message = message or f"rename {src} -> {dst}"
        self.git("commit", "-q", "-m", message, author=author, date=date)
        return self.head()

    def checkout(self, branch: str, *, create: bool = False) -> None:
        args = ["checkout", "-q"]
        if create:
            args.append("-b")
        self.git(*args, branch)

    def merge(
        self,
        branch: str,
        message: str | None = None,
        *,
        author: Author | None = None,
        date: datetime | None = None,
    ) -> str:
        """Merge `branch` into the current branch with a merge commit
        (`--no-ff`, never a fast-forward): two parents, the side commits
        reachable from the result through the second. Returns the merge
        commit's SHA."""
        message = message or f"merge {branch}"
        self.git("merge", "-q", "--no-ff", "-m", message, branch, author=author, date=date)
        return self.head()

    def squash_merge(
        self,
        branch: str,
        message: str | None = None,
        *,
        author: Author | None = None,
        date: datetime | None = None,
    ) -> str:
        """Squash `branch` into the current branch as a single commit (the
        GitHub "squash and merge" shape: one parent, the side commits stay
        reachable only through `branch`). Returns the squash commit's SHA."""
        self.git("merge", "--squash", "-q", branch)
        message = message or f"squash-merge {branch}"
        self.git("commit", "-q", "-m", message, author=author, date=date)
        return self.head()


def _identity_env(author: Author | None, date: datetime | None) -> dict[str, str] | None:
    """Env overrides for one git invocation, or `None` to inherit unchanged."""
    if author is None and date is None:
        return None
    env = dict(os.environ)
    if author is not None:
        env.update(
            GIT_AUTHOR_NAME=author.name,
            GIT_AUTHOR_EMAIL=author.email,
            GIT_COMMITTER_NAME=author.name,
            GIT_COMMITTER_EMAIL=author.email,
        )
    if date is not None:
        stamp = date.isoformat()
        env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    return env


# --- the adopter repository --------------------------------------------------


@dataclass(frozen=True)
class ScriptedHistory:
    """SHAs and paths of the scripted commit history `build_adopter_repo`
    lays down when asked for one.

    Main line, oldest first: `initial` (the installed `.pkit/` + `seed_path`
    with front matter `title` / `status`), `rename` (`seed_path` moved to
    `renamed_path`, content untouched), `squash_merge` (both `side` commits
    landed as one). `side` holds the two commits on `side_branch`: the first
    edits `status` in `renamed_path`, the second adds `side_path`.

    So: the last commit that changed `status` is `squash_merge`; the last that
    changed `title` is `initial` — reachable from `renamed_path` only by
    following the rename.
    """

    initial: str
    rename: str
    side: tuple[str, str]
    squash_merge: str
    seed_path: str = "notes/alpha.md"
    renamed_path: str = "docs/alpha.md"
    side_path: str = "docs/beta.md"
    side_branch: str = "topic"


SEED_CONTENT = "---\ntitle: Alpha\nstatus: draft\n---\n\nAlpha body.\n"
SEED_CONTENT_REVIEWED = SEED_CONTENT.replace("status: draft", "status: review")
SIDE_CONTENT = "---\ntitle: Beta\nstatus: draft\n---\n\nBeta body.\n"


class AdopterRepo(GitRepo):
    """A `GitRepo` with the backbone installed at `<root>/.pkit/`."""

    def __init__(self, root: Path, *, source_kit: Path) -> None:
        super().__init__(root)
        self.source_kit = source_kit
        self.history: ScriptedHistory | None = None

    @property
    def pkit(self) -> Path:
        return self.root / ".pkit"

    def install_capabilities(self, *names: str) -> None:
        """Install kit-shipped capabilities in the given order, refusing (as the
        CLI does) when a declared dependency is not installed yet."""
        for name in names:
            source = caps.find_capability_in_source(self.source_kit, name)
            if source is None:
                raise ValueError(f"no capability named {name!r} in {self.source_kit}")
            conflicts = caps.check_capability_dependencies(
                self.root, source.package.requires_capabilities
            )
            if conflicts:
                missing = ", ".join(c.dep_name for c in conflicts)
                raise ValueError(
                    f"capability {name!r} needs {missing} installed first — "
                    f"list dependencies before dependents"
                )
            caps.install_capability(self.root, source)

    def script_history(self) -> ScriptedHistory:
        """Lay down the scripted history described on `ScriptedHistory`.
        Expects an empty history (no commits yet); the working tree — the
        installed `.pkit/` — goes into the initial commit."""
        day = timedelta(days=1)
        seed, renamed, side_path, branch = (
            ScriptedHistory.seed_path,
            ScriptedHistory.renamed_path,
            ScriptedHistory.side_path,
            ScriptedHistory.side_branch,
        )
        main = self.current_branch()

        self.write({seed: SEED_CONTENT})
        initial = self.commit("initial: install backbone and seed notes", date=HISTORY_EPOCH)
        rename = self.rename(seed, renamed, date=HISTORY_EPOCH + day)

        self.checkout(branch, create=True)
        side_1 = self.commit(
            "topic: move alpha to review",
            {renamed: SEED_CONTENT_REVIEWED},
            date=HISTORY_EPOCH + 2 * day,
        )
        side_2 = self.commit(
            "topic: add beta", {side_path: SIDE_CONTENT}, date=HISTORY_EPOCH + 3 * day
        )
        self.checkout(main)
        squash = self.squash_merge(branch, "squash-merge topic", date=HISTORY_EPOCH + 4 * day)

        self.history = ScriptedHistory(
            initial=initial, rename=rename, side=(side_1, side_2), squash_merge=squash
        )
        return self.history


def build_adopter_repo(
    root: Path,
    *,
    monkeypatch: pytest.MonkeyPatch,
    capabilities: Sequence[str] = (),
    history: bool = False,
    chdir: bool = True,
) -> AdopterRepo:
    """Stand up an adopter repository at `root`.

    - `git init`s `root` and installs the backbone via `install_kit`, with the
      adapter shell primitives stubbed out (tests assert on tree shape; the
      bash primitives have their own coverage in `test_install.py`).
    - Installs `capabilities` in order (see `AdopterRepo.install_capabilities`).
    - With `history=True`, commits the install and lays down the scripted
      history; otherwise leaves the tree with zero commits, exactly as the
      per-file `installed_target` fixtures used to.
    - With `chdir=True`, changes the process cwd to `root` so `find_target_root`
      resolves it for CLI-driven tests.
    """
    GitRepo.init(root)
    if chdir:
        monkeypatch.chdir(root)
    stub_adapter_primitives(monkeypatch)
    install_mod.install_kit(root)

    adopter = AdopterRepo(root, source_kit=install_mod.find_source_kit())
    adopter.install_capabilities(*capabilities)
    if history:
        adopter.script_history()
    return adopter


def stub_adapter_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run no adapter shell primitive for the rest of the test, as every adopter
    repository built here is installed."""

    def _noop(_script: Path, _ctx: install_mod.InstallContext, *_args: str) -> None:
        return None

    monkeypatch.setattr(install_mod, "_run_adapter_primitive", _noop)


# --- templates: each shape built once per test session (#1204) ----------------

Prepare = Callable[[AdopterRepo], object]
"""A test module's own setting-up of an adopter — files written, scripts run,
commits made — kept in the adopter's template with the install."""


def prepared(adopter: AdopterRepo, prepare: Prepare) -> AdopterRepo:
    """`adopter` after `prepare`, run from the adopter's root, as a test runs it."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.chdir(adopter.root)
        prepare(adopter)
    return adopter


#: `clonefile(2)`'s flag that clones a symbolic link itself, not what it names.
_CLONE_NOFOLLOW = 0x0001


def _load_clonefile() -> Callable[[bytes, bytes, int], int] | None:
    """macOS's `clonefile(2)`: a whole tree copied in one call, each file sharing
    its blocks with the original until either side writes it. None elsewhere."""
    if sys.platform != "darwin":
        return None
    try:
        clonefile = ctypes.CDLL(None, use_errno=True).clonefile
    except (OSError, AttributeError):
        return None
    clonefile.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)
    clonefile.restype = ctypes.c_int
    return clonefile


_CLONEFILE = _load_clonefile()


def copy_tree(source: Path, dest: Path) -> None:
    """Copy every entry of `source` into `dest`, creating `dest` if need be.

    Every file is the copy's own — a test may write any of them and neither the
    source nor another copy sees it — so nothing is hard-linked. A clone where
    the platform has `clonefile(2)`, which costs a few calls whatever the size
    of the tree; a file-by-file copy where it has not, or where the filesystem
    refuses a clone."""
    dest.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        target = dest / entry.name
        if (
            _CLONEFILE is not None
            and _CLONEFILE(os.fsencode(entry), os.fsencode(target), _CLONE_NOFOLLOW) == 0
        ):
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.copytree(entry, target, symlinks=True)
        else:
            shutil.copy2(entry, target, follow_symlinks=False)


#: The checkout the suite runs from, where `python -m tests.adopter_repo` starts.
_CHECKOUT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class _Template:
    root: Path
    history: ScriptedHistory | None


_TemplateKey = tuple[tuple[str, ...], bool, str]


class AdopterTemplates:
    """Adopter repositories built once in a test session, each test handed a
    private copy (#1204).

    A template is built the first time a test asks for its shape — the
    capabilities installed, the scripted history or none, and the test module's
    `prepare` — under `directory`, and kept for the rest of the session. The
    processes of one session, its pytest-xdist workers, share `directory`: the
    first to ask for a shape builds it holding the shape's lock, and any other
    waits on the lock, then copies what was built.

    The install runs in an interpreter of its own, started with `environment` —
    the one the session began with — so nothing a test has patched in its
    process or set in its environment reaches a template, whichever test asks
    first. A `prepare` runs in the process of the test that asks first, from the
    template's root.
    """

    def __init__(self, directory: Path, environment: Mapping[str, str]) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self._directory = directory
        self._environment = dict(environment)
        self._known: dict[_TemplateKey, _Template] = {}

    def copy(
        self,
        root: Path,
        *,
        capabilities: Sequence[str] = (),
        history: bool = False,
        prepare: Prepare | None = None,
    ) -> AdopterRepo:
        """An adopter at `root`, a copy of the template of its shape."""
        return _copied(self._template(tuple(capabilities), history, prepare), root)

    def _template(
        self, capabilities: tuple[str, ...], history: bool, prepare: Prepare | None
    ) -> _Template:
        key = (capabilities, history, _name_of(prepare))
        template = self._known.get(key)
        if template is not None:
            return template
        if prepare is None:

            def build(root: Path) -> ScriptedHistory | None:
                return self._install(root, capabilities, history)

        else:
            installed = self._template(capabilities, history, None)

            def build(root: Path) -> ScriptedHistory | None:
                prepared(_copied(installed, root), prepare)
                return installed.history

        template = self._known[key] = self._built(key, build)
        return template

    def _built(
        self, key: _TemplateKey, build: Callable[[Path], ScriptedHistory | None]
    ) -> _Template:
        """The template `key` names, built with `build` unless a process sharing the
        directory has built it. Built holding the key's lock, into a directory that
        takes the template's name once it is whole, its scripted history written
        beside it first."""
        name = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
        root = self._directory / name
        record = self._directory / f"{name}.json"
        with _locked(self._directory / f"{name}.lock"):
            if not root.exists():
                building = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=self._directory))
                record.write_text(json.dumps(_shas(build(building))), encoding="utf-8")
                building.rename(root)
        return _Template(root, _history(json.loads(record.read_text(encoding="utf-8"))))

    def _install(
        self, root: Path, capabilities: tuple[str, ...], history: bool
    ) -> ScriptedHistory | None:
        """Build the adopter at `root` in an interpreter of its own (`_main`)."""
        wanted = {"root": str(root), "capabilities": list(capabilities), "history": history}
        done = subprocess.run(
            [sys.executable, "-m", __name__, json.dumps(wanted)],
            cwd=_CHECKOUT,
            env=self._environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            raise RuntimeError(f"building the adopter template {wanted} failed:\n{done.stderr}")
        return _history(json.loads(done.stdout))


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    """`path` locked for this process alone through the block (`flock(2)`); the
    operating system frees it when the process ends, however it ends."""
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _shas(history: ScriptedHistory | None) -> dict[str, Any] | None:
    """`history`'s SHAs as JSON holds them."""
    if history is None:
        return None
    return {
        "initial": history.initial,
        "rename": history.rename,
        "side": list(history.side),
        "squash_merge": history.squash_merge,
    }


def _history(shas: Mapping[str, Any] | None) -> ScriptedHistory | None:
    """The scripted history `_shas` wrote."""
    if shas is None:
        return None
    side_1, side_2 = shas["side"]
    return ScriptedHistory(
        initial=shas["initial"],
        rename=shas["rename"],
        side=(side_1, side_2),
        squash_merge=shas["squash_merge"],
    )


def _copied(template: _Template, root: Path) -> AdopterRepo:
    """An adopter at `root` copied from `template`, its scripted history with it."""
    copy_tree(template.root, root)
    adopter = AdopterRepo(root, source_kit=install_mod.find_source_kit())
    adopter.history = template.history
    return adopter


def _name_of(prepare: Prepare | None) -> str:
    """What a template knows its `prepare` by: the function's full name — so it
    must be one only one function has."""
    if prepare is None:
        return ""
    name = f"{prepare.__module__}.{prepare.__qualname__}"
    if "<" in prepare.__qualname__:
        raise ValueError(
            f"prepare={name} is not a module-level function: a template is known by "
            "its prepare's name, which a lambda or a nested function shares with others"
        )
    return name


def _main(wanted: str) -> None:
    """`python -m tests.adopter_repo '{"root": ..., "capabilities": [...],
    "history": ...}'`: build that adopter, and print its scripted history's SHAs as
    JSON — `null` when it has none. The install's own output is not printed."""
    shape = json.loads(wanted)
    with pytest.MonkeyPatch.context() as monkeypatch, contextlib.redirect_stdout(io.StringIO()):
        adopter = build_adopter_repo(
            Path(shape["root"]),
            monkeypatch=monkeypatch,
            capabilities=shape["capabilities"],
            history=shape["history"],
            chdir=False,
        )
    print(json.dumps(_shas(adopter.history)))


MakeAdopterRepo = Callable[..., AdopterRepo]
"""Type of the `make_adopter_repo` factory fixture: a copy of an
`AdopterTemplates` template at `root` (default `tmp_path`), or a fresh
`build_adopter_repo` with `monkeypatch` bound."""


if __name__ == "__main__":
    _main(sys.argv[1])
