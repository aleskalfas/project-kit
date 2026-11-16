"""Fetching an externally-sourced capability at its pin (COR-041; ADR-040).

A capability kept in another git repository is incubated there, at
`.pkit/capabilities/<name>/` (COR-031), and pulled whole into each project that
installs it, at a tag or a commit the project pins (ADR-040 point 1). This
module is that pull and nothing else: it reads the source with the person's own
git, takes the capability's subtree at exactly the pinned commit into a staging
folder of its own, and writes nothing in the project. Gating the staged tree,
copying it and registering it are the caller's (`capabilities`, the CLI, sync).

- **Credentials are the person's own** (point 2). pkit passes none and takes
  none: git's terminal prompt is off, as for the fetches of pkit's own releases
  (ADR-090 point 2), so a source that asks a credential no helper of the
  person's answers fails at once. A URL that carries a credential is refused, so
  none is passed in an argument, recorded in a manifest or printed.
- **Only the protocols a pin needs.** git reads the source over `https`,
  `ssh`, `git` or a local path, and no other transport, whatever the person's
  own `protocol.allow` setting turns on: the source is a manifest's, which
  anyone who commits to the project can edit, and a transport such as `ext`
  runs a command.
- **A pin is a tag or a commit's full id.** A ref that names a branch is
  refused: a branch as a pin waits on #3229, which builds the transition that
  moves a pin. A pin that records the commit its install fetched takes that
  commit only, so a tag moved at its source since is not followed (point 7).
- **Exactly the commit's content.** The subtree's files are read from git's
  objects, never checked out, so no filter, line-ending conversion or export
  attribute of either repository changes a byte, and no hook runs. The
  subtree's `project/` tier is left out, since that tier is each project's own
  (point 3), in whatever case its name is written: on a filesystem that ignores
  case, `PROJECT/` is the same folder.

Two failures, told apart for their callers (point 7): `FetchFailed`, a source
that cannot be reached, a ref it does not hold or no longer holds at the pin's
commit, or a credential it refuses, on which a command warns loudly and
activates nothing; and `FetchRefused`, a pin or a subtree pkit does not take,
which the command refuses.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from project_kit.manifest import CapabilityPin

# Where a capability is incubated in the repository that authors it (COR-031).
SOURCE_SUBTREE = ".pkit/capabilities"
# The capability's own tier, which no fetch takes (ADR-040 point 3), in any case.
_PROJECT_TIER = "project"
# The issue that builds the version transition that moves an installed
# capability's pin, with its fetch of a moved pin and a branch as a pin (ADR-040).
PIN_TRANSITION_ISSUE = "#3229"

# A commit's full id, SHA-1 or SHA-256, and what may be an abbreviated one.
_FULL_COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_SHORT_COMMIT = re.compile(r"[0-9a-f]{4,63}")

# The object modes of a tree's entries, as `git ls-tree` gives them.
_REGULAR = "100644"
_EXECUTABLE = "100755"
_SYMLINK = "120000"
_GITLINK = "160000"

# The variables that point git at another repository than the one a command
# names. A fetch run from a hook, or under another tool's git environment, must
# read none of them.
_GIT_LOCATORS = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_NAMESPACE",
    }
)
# git's switch for its terminal prompt (ADR-090 point 2).
_TERMINAL_PROMPT = "GIT_TERMINAL_PROMPT"
# git's list of the only transports it may use, which overrides every
# `protocol.allow` setting, and the transports a pin needs: a local path is
# git's `file`.
_PROTOCOL_ALLOW_LIST = "GIT_ALLOW_PROTOCOL"
_PIN_PROTOCOLS = "https:ssh:git:file"

# The ref the fetched commit is kept under in the staging repository.
_PINNED = "refs/pkit/pinned"
# How many of git's last lines of standard error a failure quotes.
_QUOTED_LINES = 4
# What stands for a credential wherever a URL that carries one is shown.
_CREDENTIAL_SHOWN = "<credential>"


class FetchFailed(Exception):
    """The source could not be read at the pin: it cannot be reached, it holds no
    such ref, its ref now names another commit than the pin records, or it
    refuses the credential (ADR-040 point 7). The caller warns loudly and
    activates nothing."""


class FetchRefused(Exception):
    """A pin, or a fetched subtree, that pkit does not take. The caller refuses,
    writing nothing."""


@dataclass(frozen=True)
class Fetched:
    """A capability's subtree, staged at the pinned commit."""

    path: Path  # <staging>/capabilities/<name>/, the subtree's files but its `project/`
    commit: str  # the full id of the commit the pin names


def carries_credential(url: str) -> bool:
    """True when *url* carries a credential in its user part.

    A URL with a scheme carries one where its user part holds a password, and an
    HTTP or HTTPS URL wherever it has a user part at all, since a token is often
    given there as the user. The scp-like form, `user@host:path`, carries one
    where its user part holds a colon. A local path carries none.
    """
    if "://" in url:
        parts = urlsplit(url)
        if parts.password is not None:
            return True
        return parts.scheme.lower() in ("http", "https") and parts.username is not None
    head, at, _rest = url.partition("@")
    return bool(at) and ":" in head and "/" not in head


def shown(url: str) -> str:
    """*url* as pkit prints it: its user part replaced where it carries a credential."""
    if not carries_credential(url):
        return url
    if "://" in url:
        parts = urlsplit(url)
        host = parts.netloc.rpartition("@")[2]
        return parts._replace(netloc=f"{_CREDENTIAL_SHOWN}@{host}").geturl()
    return f"{_CREDENTIAL_SHOWN}@{url.partition('@')[2]}"


def refuse_pin(pin: CapabilityPin) -> None:
    """Refuse, before git reads anything, a pin pkit does not take (`FetchRefused`).

    A source or a ref that is empty, or that starts with `-`, which git would read
    as an option; and a source that carries a credential, which pkit would pass
    in an argument and record (ADR-040 point 2).
    """
    if not pin.source.strip() or not pin.ref.strip():
        raise FetchRefused("a pin names a git source and a ref, and neither may be empty.")
    if pin.source.startswith("-") or pin.ref.startswith("-"):
        raise FetchRefused(
            "a git source or a ref may not start with `-`, which git would read as an option."
        )
    if carries_credential(pin.source):
        raise FetchRefused(
            f"the source {shown(pin.source)} carries a credential in its URL. pkit takes "
            "no credential of its own: it fetches with your git's own, so it would pass "
            "this one in an argument and record it in the capability's manifest "
            "(ADR-040 point 2). Give the URL without it, and let a git credential helper "
            "or an SSH key answer for you."
        )


@contextmanager
def fetched(pin: CapabilityPin, name: str) -> Generator[Fetched]:
    """The capability *name* staged at *pin*, in a temporary folder removed on exit.

    Raises `FetchRefused` or `FetchFailed` before it yields (`fetch`).
    """
    with tempfile.TemporaryDirectory(prefix="pkit-fetch-") as folder:
        yield fetch(pin, name, Path(folder))


def fetch(pin: CapabilityPin, name: str, staging: Path) -> Fetched:
    """Stage capability *name* from *pin* under *staging*, an empty folder (ADR-040 point 1).

    Its order: the pin is refused if pkit does not take it (`refuse_pin`); the
    source's tags and branches of that name are read (`git ls-remote`), which
    reaches the source with the person's credentials; a ref that names a tag is
    fetched as that tag, one that names a branch is refused, and one that is a
    commit's full id is fetched as that commit; where the pin records a commit,
    the commit fetched must be it; then the commit's
    `.pkit/capabilities/<name>/` is written under *staging*, its `project/` tier
    left out.

    Raises `FetchFailed` where the source cannot be reached, refuses the
    credential, holds no such tag or commit, or its tag now names another commit
    than the pin records; `FetchRefused` for a pin pkit
    does not take, a name that is no folder's, a ref that names a branch, a
    commit's abbreviated id, or a commit that holds no such capability, or holds
    in it a symbolic link or a submodule, which a capability's files never are.
    """
    refuse_pin(pin)
    if name in ("", ".", "..") or "/" in name or "\\" in name:
        raise FetchRefused(f"{name!r} is no capability's name.")
    where = shown(pin.source)
    want = _wanted(staging, pin, where)
    repo = staging / "source.git"
    _git_or_fail(staging, ["init", "-q", "--bare", str(repo)], f"a staging repository at {repo}")
    result = _git(
        staging,
        [
            f"--git-dir={repo}",
            "fetch",
            "-q",
            "--depth",
            "1",
            "--no-tags",
            pin.source,
            f"+{want}:{_PINNED}",
        ],
    )
    if result.returncode != 0:
        raise FetchFailed(f"fetching {pin.ref} from {where} failed: {_said(result)}")
    resolved = _git(
        staging, [f"--git-dir={repo}", "rev-parse", "--verify", f"{_PINNED}^{{commit}}"]
    )
    if resolved.returncode != 0:
        raise FetchRefused(f"{pin.ref} of {where} names no commit.")
    commit = resolved.stdout.decode().strip()
    if pin.commit is not None and commit != pin.commit:
        raise FetchFailed(
            f"{pin.ref} of {where} now names commit {commit}, not {pin.commit}, the commit "
            "the pin records: a pin takes only the commit its install fetched, so a tag "
            "moved at its source is not followed. To take the new commit, uninstall the "
            "capability and install it again"
        )
    entries = _subtree_entries(staging, repo, commit, name, pin, where)
    dest = staging / "capabilities" / name
    _write_entries(staging, repo, entries, dest, pin, where)
    return Fetched(path=dest, commit=commit)


def _wanted(staging: Path, pin: CapabilityPin, where: str) -> str:
    """What to fetch for *pin*: its tag's ref name, or its commit's full id.

    Reads the source's tag and branch of the ref's name (`git ls-remote`), which
    is also where an unreachable source, or one that refuses the credential,
    fails (`FetchFailed`). A tag wins over a branch of the same name, as git's own
    lookup has it.
    """
    tag, branch = f"refs/tags/{pin.ref}", f"refs/heads/{pin.ref}"
    result = _git(staging, ["ls-remote", pin.source, tag, branch])
    if result.returncode != 0:
        raise FetchFailed(f"{where} could not be read: {_said(result)}")
    listed = {
        line.partition("\t")[2] for line in result.stdout.decode(errors="replace").splitlines()
    }
    if tag in listed:
        return tag
    if branch in listed:
        raise FetchRefused(
            f"{pin.ref} names a branch of {where}, not a tag or a commit. A branch as a pin "
            f"waits on {PIN_TRANSITION_ISSUE}, which builds the transition that moves a pin. "
            "Pin a tag, or a commit's full id."
        )
    if _FULL_COMMIT.fullmatch(pin.ref):
        return pin.ref
    if _SHORT_COMMIT.fullmatch(pin.ref):
        raise FetchRefused(
            f"{pin.ref} is neither a tag of {where} nor a commit's full id. A commit is pinned "
            "by its full id, so the pin names exactly one commit: `git rev-parse "
            f"{pin.ref}` in a clone of the source gives it."
        )
    raise FetchFailed(f"{where} holds no tag {pin.ref}, and {pin.ref} is no commit's full id.")


def _subtree_entries(
    staging: Path, repo: Path, commit: str, name: str, pin: CapabilityPin, where: str
) -> list[tuple[str, str, PurePosixPath]]:
    """Each file of the commit's `.pkit/capabilities/<name>/` but its `project/` tier,
    as (mode, object id, path relative to the subtree).

    A first folder whose name folds to `project` in any case is that tier: on a
    filesystem that ignores case it is the same folder, so a fetched
    `PROJECT/manifest.yaml` would land on the project's own manifest."""
    prefix = PurePosixPath(SOURCE_SUBTREE) / name
    listed = _git_or_fail(
        staging,
        [f"--git-dir={repo}", "ls-tree", "-r", "-z", "--full-tree", commit, "--", f"{prefix}/"],
        f"the tree of {pin.ref} of {where}",
    )
    found = False
    entries: list[tuple[str, str, PurePosixPath]] = []
    for record in listed.stdout.split(b"\0"):
        if not record:
            continue
        found = True
        meta, _tab, raw_path = record.partition(b"\t")
        mode, _kind, oid = meta.decode().split(" ")
        rel = PurePosixPath(raw_path.decode("utf-8", errors="surrogateescape")).relative_to(prefix)
        if rel.parts[0].casefold() == _PROJECT_TIER:
            continue
        if any(part in ("", ".", "..") for part in rel.parts):
            raise FetchRefused(f"{prefix}/{rel} of {where} at {pin.ref} is no path pkit writes.")
        if mode == _SYMLINK:
            raise FetchRefused(
                f"{prefix}/{rel} of {where} at {pin.ref} is a symbolic link. A fetched "
                "capability is taken as files only, so a link could not reach outside it."
            )
        if mode == _GITLINK:
            raise FetchRefused(
                f"{prefix}/{rel} of {where} at {pin.ref} is a submodule, which a fetched "
                "capability cannot hold: it is pulled whole from one repository."
            )
        if mode not in (_REGULAR, _EXECUTABLE):
            raise FetchRefused(f"{prefix}/{rel} of {where} at {pin.ref} has git mode {mode}.")
        entries.append((mode, oid, rel))
    if not found:
        raise FetchRefused(f"{where} holds no capability at {prefix}/ at {pin.ref}.")
    return entries


def _write_entries(
    staging: Path,
    repo: Path,
    entries: list[tuple[str, str, PurePosixPath]],
    dest: Path,
    pin: CapabilityPin,
    where: str,
) -> None:
    """Write each entry's content under *dest*, read in one `git cat-file --batch`,
    with its executable bit."""
    dest.mkdir(parents=True)
    if not entries:
        return
    request = b"".join(f"{oid}\n".encode() for _mode, oid, _rel in entries)
    batch = _git_or_fail(
        staging,
        [f"--git-dir={repo}", "cat-file", "--batch"],
        f"the files of {pin.ref} of {where}",
        stdin=request,
    )
    data, at = batch.stdout, 0
    for mode, oid, rel in entries:
        header_end = data.find(b"\n", at)
        header = data[at:header_end].split(b" ")
        if header_end < 0 or len(header) != 3 or header[1] != b"blob":
            raise FetchFailed(f"git could not read {oid} ({rel}) of {where} at {pin.ref}.")
        size = int(header[2])
        start = header_end + 1
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[start : start + size])
        target.chmod(0o755 if mode == _EXECUTABLE else 0o644)
        at = start + size + 1


def _environment() -> dict[str, str]:
    """This process's environment for git, its locators removed, its terminal
    prompt off and its transports those a pin needs, so the person's own
    credential helper, SSH key and URL rewrites answer, nothing waits at a
    terminal (ADR-040 point 2, ADR-090 point 2), and no source a manifest names
    reaches a transport that runs a command."""
    environment = {key: value for key, value in os.environ.items() if key not in _GIT_LOCATORS}
    environment[_TERMINAL_PROMPT] = "0"
    environment[_PROTOCOL_ALLOW_LIST] = _PIN_PROTOCOLS
    return environment


def _git(
    staging: Path, args: list[str], *, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run git in *staging* with no hook and no automatic maintenance, either of
    which the person's configuration could otherwise start in the staging folder."""
    hooks = staging / "no-hooks"
    hooks.mkdir(exist_ok=True)
    command = [
        "git",
        "-c",
        f"core.hooksPath={hooks}",
        "-c",
        "gc.auto=0",
        "-c",
        "maintenance.auto=false",
        *args,
    ]
    try:
        return subprocess.run(
            command,
            cwd=staging,
            input=stdin,
            capture_output=True,
            env=_environment(),
            check=False,
        )
    except FileNotFoundError as exc:
        raise FetchFailed("git is not installed, or not on PATH.") from exc


def _git_or_fail(
    staging: Path, args: list[str], what: str, *, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """`_git`, raising `FetchFailed` naming *what* where git fails."""
    result = _git(staging, args, stdin=stdin)
    if result.returncode != 0:
        raise FetchFailed(f"git could not read {what}: {_said(result)}")
    return result


def _said(result: subprocess.CompletedProcess[bytes]) -> str:
    """git's last lines of standard error, each with its control characters removed,
    so neither a long answer nor a terminal escape reaches the person's terminal."""
    lines = [
        "".join(ch for ch in line if ch.isprintable()).strip()
        for line in result.stderr.decode(errors="replace").splitlines()
    ]
    said = [line for line in lines if line][-_QUOTED_LINES:]
    return " / ".join(said) if said else f"git exited {result.returncode}"
