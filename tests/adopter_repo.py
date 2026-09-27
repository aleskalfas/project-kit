"""A temporary *adopter repository* for tests (#980).

A real `git init`ed directory with the backbone installed through
`project_kit.install.install_kit`, optionally chosen capabilities installed
through `project_kit.capabilities`, and — on request — a scripted commit
history (initial commit, a `git mv` rename, a squash-style merge) that later
work such as the friction engine (COR-050) can trace front-matter changes
across.

Two layers:

- `GitRepo` — git plumbing only: init, commit arbitrary edits with a
  controllable author/date, rename, branch, squash-merge, read SHAs. Usable
  on its own for tests whose repo is not an adopter (e.g. a synthetic source
  kit).
- `AdopterRepo` — a `GitRepo` whose root carries an installed `.pkit/`, plus
  capability installation and the scripted `history`.

The pytest fixtures (`make_adopter_repo`, `adopter_repo`) live in
`tests/conftest.py` and wrap `build_adopter_repo` below. See
`tests/README.md` for when to reach for which.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

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

    def _noop(_script: Path, _ctx: install_mod.InstallContext) -> None:
        return None

    monkeypatch.setattr(install_mod, "_run_adapter_primitive", _noop)
    install_mod.install_kit(root)

    adopter = AdopterRepo(root, source_kit=install_mod.find_source_kit())
    adopter.install_capabilities(*capabilities)
    if history:
        adopter.script_history()
    return adopter


MakeAdopterRepo = Callable[..., AdopterRepo]
"""Type of the `make_adopter_repo` factory fixture: `build_adopter_repo` with
`root` defaulting to `tmp_path` and `monkeypatch` bound."""
